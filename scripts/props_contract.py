#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""props 契约：从容器源码**机械提取**「每个渲染器真正读了哪些 props 键」。

为什么必须有这个东西
--------------------
容器不是 React：没有组件库兜底，每种 `type` 各有一个渲染器，**逐字段手写读 props**
（`R.X=function(p,ctx,node){ … p.title … }`），全文件**没有整包透传**。于是一个键写错，
既不生效也不报错，而几何判据（`check_ui_shape`）只量像素，对「写在哪都不改变像素」的键完全免疫。

提取规则（XX-050 重写）
----------------------
1. **两种注册都要认**：`R.List=function(p,ctx,node){` 与 `R['List.Item']=function(…){`。
   只认前一种会漏掉 `List.Item`（L1899），renderItem 模板一进判据就是整类假红。
2. **函数体结束用括号配平**，跳过字符串 / 模板串 / 正则 / 注释。
   旧实现用「下一个 `R.*` 的起点」当终点，实测把 `R.Frame` 之后的 11 万字符（文件尾 46%）
   全算成 Frame 读的键，还把段间 helper 记给上一个渲染器 —— 一假红（`Table.queryId`）
   一假绿（`Transfer.queryId`）。
3. **helper 闭包**：渲染器体内调用的同文件普通函数（`buildFilterBar(p,ctx)` 这类）
   算该渲染器的读取点，helper 调 helper 也要求不动点。
4. **shared**：`renderNode` 里对所有 type 生效的通用预处理键（现在只有 `visible`）。
   它不属于任何一个渲染器，但每个 type 都可读。
5. **委托继承**：`R.X` 把整包 props 转给 `R.Y` → X ⊇ Y，求不动点。

用法
----
    python3 scripts/props_contract.py            # 生成 / 刷新契约文件
    python3 scripts/props_contract.py --check    # 只校验契约与容器源码是否一致

退出码
------
    0 = 成功 / 同步
    1 = 提取失败（0 个渲染器）、清单缺失或格式不符、契约与源码不一致
"""

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONTAINER = os.path.join(ROOT, "assets", "container", "index.html")
CONTRACT = os.path.join(ROOT, "assets", "container", "props-contract.json")
# 唯一真源：规范文件，不在 scripts/ 下（见 references/04-container-schema.md §6.8.5）
UNSUPPORTED = os.path.join(ROOT, "references", "props-unsupported.json")

# `R.Drawer=function(p,ctx,node){` / `R['List.Item']=function(p,ctx,node){`
REG_DOT = re.compile(r"(?<![\w$.])R\.([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*=\s*function\s*\(([^)]*)\)\s*\{")
REG_IDX = re.compile(r"(?<![\w$.])R\[\s*['\"]([^'\"]+)['\"]\s*\]\s*=\s*function\s*\(([^)]*)\)\s*\{")
# 普通 helper：`function buildFilterBar(p,ctx){`
REG_HELPER = re.compile(r"(?:^|\n)\s*function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{")

P_DOT = re.compile(r"\bp\.([A-Za-z_$][\w$]*)")
P_IDX = re.compile(r"\bp\[\s*['\"]([\w$]+)['\"]\s*\]")
GEN_DOT = re.compile(r"\bprops\.([A-Za-z_$][\w$]*)")
# 委托：`return R.X(p,…)` / `return R.X(Object.assign({},p,…))` / 方括号写法
DELEGATE_DOT = re.compile(
    r"return\s+R\.([A-Za-z_$][\w$.]*)\s*\(\s*(?:Object\.assign\(\{\}\s*,\s*)?p\b")
DELEGATE_IDX = re.compile(
    r"return\s+R\[\s*['\"]([^'\"]+)['\"]\s*\]\s*\(\s*(?:Object\.assign\(\{\}\s*,\s*)?p\b")
# 插槽：容器只通过 `renderSlot(node,'x')` / `slotFirst(node,'x')` 取，其余名字一律丢弃。
# 插槽名**按 type 判、不继承**（§6.8.1 R2）—— 只有委托继承那一层跟着渲染器走。
SLOT_CALL = re.compile(r"(?:renderSlot|slotFirst)\s*\(\s*node\s*,\s*['\"]([\w$-]+)['\"]")


class ContractError(Exception):
    pass


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def find_body_end(src, open_brace):
    """从 `{` 开始配平，返回配平的 `}` 之后的位置。跳过字符串/模板串/正则/注释。"""
    i = open_brace
    depth = 0
    n = len(src)
    prev_sig = ";"          # 上一个有意义字符，用来判断 `/` 是除号还是正则起点
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "\"'":
            q = c
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == q:
                    i += 1
                    break
                i += 1
            prev_sig = q
            continue
        if c == "`":
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == "`":
                    i += 1
                    break
                if src[i] == "$" and i + 1 < n and src[i + 1] == "{":
                    sub_end = find_body_end(src, i + 1)
                    i = sub_end
                    continue
                i += 1
            prev_sig = "`"
            continue
        if c == "/" and (prev_sig in "(,=:[!&|?{};+-*%~^<>" or prev_sig == ""):
            # 正则字面量
            i += 1
            in_class = False
            while i < n:
                ch = src[i]
                if ch == "\\":
                    i += 2
                    continue
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    i += 1
                    while i < n and src[i].isalpha():
                        i += 1
                    break
                i += 1
            prev_sig = "/"
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        if not c.isspace():
            prev_sig = c
        i += 1
    raise ContractError("括号不配平：从偏移 %d 开始" % open_brace)


def strip_noise(s, keep_strings=False):
    """去掉注释与字符串字面量（模板串里的 `${…}` 保留为代码），只留可执行文本。

    为什么必须去：注释里的 `p.<key>` 会被当成读取点。容器里唯一一处提到 `p.x` 的注释
    （`R.Row` 体内那句「Col 自己读不到 p.gutter」）碰巧不制造假键 —— `R.Row` 自己就写了
    `var g=(p.gutter||0)`。但这是巧合，不是保证：换一句注释写一个该渲染器不读的键，
    白名单里就多一个永远抓不到的假绿。被注释放行的白名单比没有白名单更危险。

    `keep_strings=True` 只去注释、保留字符串原文：**插槽名就在字符串里**
    （`renderSlot(node,'footer')`），连字符串一起去掉就一个也提不出来。
    """
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            j = s.find("\n", i)
            i = n if j < 0 else j
            out.append(" ")
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            j = s.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
            continue
        if c in "\"'":
            q = c
            k = i
            i += 1
            while i < n:
                if s[i] == "\\":
                    i += 2
                    continue
                if s[i] == q:
                    i += 1
                    break
                i += 1
            out.append(s[k:i] if keep_strings else q + q)
            continue
        if c == "`":
            k = i
            i += 1
            while i < n:
                if s[i] == "\\":
                    i += 2
                    continue
                if s[i] == "`":
                    i += 1
                    break
                if s[i] == "$" and i + 1 < n and s[i + 1] == "{":
                    j = find_body_end(s, i + 1)
                    out.append(strip_noise(s[i + 2:j - 1]))
                    i = j
                    continue
                i += 1
            out.append(s[k:i] if keep_strings else "``")
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _keys_in(body):
    code = strip_noise(body)
    return set(P_DOT.findall(code)) | set(P_IDX.findall(code))


def _first_param_ok(params):
    first = params.split(",")[0].strip()
    return first == "p"


def scan(src):
    """返回 (renderers, helpers)。

    renderers: {name: {"body": str, "start": int, "end": int}}
    helpers:   {name: {"body": str, "start": int, "end": int}}
    """
    renderers, helpers, spans = {}, {}, []
    for rx in (REG_DOT, REG_IDX):
        for m in rx.finditer(src):
            name = m.group(1)
            params = m.group(2)
            if not _first_param_ok(params):
                raise ContractError(
                    "渲染器 %s 的首参不是 p（%s）—— 契约按 `p.<key>` 取数，签名变了就要改提取器"
                    % (name, params.strip()))
            body_start = m.end() - 1
            end = find_body_end(src, body_start)
            body = src[body_start:end]
            code = strip_noise(body)
            if REG_DOT.search(code[1:]) or REG_IDX.search(code[1:]):
                raise ContractError(
                    "渲染器 %s 的函数体里又出现了 R.* 注册，括号配平可能失手" % name)
            if name in renderers:
                # 同名重复定义：取并集，别让后一次静默覆盖前一次
                renderers[name]["body"] += "\n" + body
                renderers[name]["code"] += "\n" + code
            else:
                renderers[name] = {"body": body, "code": code, "start": m.start(), "end": end}
            spans.append((m.start(), end))

    for m in REG_HELPER.finditer(src):
        name = m.group(1)
        if name in renderers:
            continue
        body_start = m.end() - 1
        end = find_body_end(src, body_start)
        body = src[body_start:end]
        helpers[name] = {"body": body, "code": strip_noise(body),
                         "start": m.start(), "end": end}

    # helper 不能落在渲染器体内（内层 function 表达式 / 回调不算「同文件 helper」）
    def inside_any(pos):
        return any(s <= pos < e for s, e in spans)

    helpers = {k: v for k, v in helpers.items() if not inside_any(v["start"])}
    return renderers, helpers


def _called_with_props(code, name):
    """helper 是否被**以 p 作为第一个实参**调用。

    只认 `buildFilterBar(p,ctx)` 这种写法。不认 `getPath(o,p)` / `parseAtom(t,p,vars)`：
    那些函数里的 `p` 是普通形参（路径串、位置对象），把它们也算进来，
    `p.split` / `p.i` 就成了合法 prop —— 一个被误报放行的白名单比没有更危险。
    """
    return re.search(r"\b%s\s*\(\s*p\s*[,)]" % re.escape(name), code) is not None


def extract(src):
    """返回 dict：byType / shared / nonPropP / renderers / rendererCount。"""
    renderers, helpers = scan(src)

    # 1) 直接读取点
    by_type = {name: _keys_in(info["body"]) for name, info in renderers.items()}
    helper_keys = {name: _keys_in(info["body"]) for name, info in helpers.items()}

    # 2) helper 闭包（helper 调 helper 也要求不动点）
    helper_calls = {name: {h for h in helpers if _called_with_props(info["code"], h)}
                    for name, info in helpers.items()}
    for _ in range(16):
        changed = False
        for name, calls in helper_calls.items():
            merged = set(helper_keys[name])
            for c in calls:
                merged |= helper_keys[c]
            if len(merged) > len(helper_keys[name]):
                helper_keys[name] = merged
                changed = True
        if not changed:
            break

    # 3) 渲染器 → 它调用的 helper
    for name, info in renderers.items():
        for h in helpers:
            if _called_with_props(info["code"], h):
                by_type[name] |= helper_keys[h]

    # 4) 委托继承：X 把整包 props 转给 Y → X ⊇ Y，求不动点
    delegates = {}
    for name, info in renderers.items():
        targets = DELEGATE_DOT.findall(info["code"]) + DELEGATE_IDX.findall(info["code"])
        delegates[name] = [t for t in targets if t != name and t in by_type]
    for _ in range(16):
        changed = False
        for name, targets in delegates.items():
            merged = set(by_type[name])
            for t in targets:
                merged |= by_type[t]
            if len(merged) > len(by_type[name]):
                by_type[name] = merged
                changed = True
        if not changed:
            break

    # 4') 插槽名同样机械提取：只认 `renderSlot(node,'x')` / `slotFirst(node,'x')`。
    # 委托渲染器拿到的还是同一个 node，所以插槽也跟着继承（与 props 同一套不动点）。
    slots = {name: set(SLOT_CALL.findall(strip_noise(info["body"], keep_strings=True)))
             for name, info in renderers.items()}
    for _ in range(16):
        changed = False
        for name, targets in delegates.items():
            merged = set(slots[name])
            for t in targets:
                merged |= slots[t]
            if len(merged) > len(slots[name]):
                slots[name] = merged
                changed = True
        if not changed:
            break

    # 5) shared：renderNode 的通用预处理（对所有 type 生效）
    m = re.search(r"function renderNode\s*\([^)]*\)\s*\{", src)
    if not m:
        raise ContractError("找不到 renderNode —— 通用键（shared）无从取")
    rn_end = find_body_end(src, m.end() - 1)
    shared = sorted(set(GEN_DOT.findall(src[m.start():rn_end])))

    # 6) 渲染器区块之外被读到的 p.xxx：只作可见性留存，**不进白名单**
    spans = sorted((info["start"], info["end"]) for info in renderers.values())
    rest, cur = [], 0
    for s, e in spans:
        rest.append(src[cur:s])
        cur = max(cur, e)
    rest.append(src[cur:])
    non_prop_p = sorted(_keys_in("\n".join(rest)))

    return {
        "rendererCount": len(by_type),
        "byType": {k: sorted(v) for k, v in sorted(by_type.items())},
        "slotsByType": {k: sorted(v) for k, v in sorted(slots.items()) if v},
        "shared": shared,
        "nonPropP": non_prop_p,
        "helperCount": len(helpers),
    }


def load_unsupported():
    if not os.path.exists(UNSUPPORTED):
        raise ContractError(
            "不支持清单缺失：%s\n"
            "  这是规范内容（references/04 §6.8.5），不是可选文件。缺了它，"
            "SS-01 命中时给不出「为什么不支持 + 改成什么」。" % os.path.relpath(UNSUPPORTED, ROOT))
    with open(UNSUPPORTED, encoding="utf-8") as f:
        doc = json.load(f)
    entries = doc.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ContractError("不支持清单格式不符：顶层缺少非空 entries[]（现为 %r）" % type(entries).__name__)
    index = {}
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise ContractError("entries[%d] 不是对象" % i)
        t, k = e.get("type"), e.get("key")
        why, instead = e.get("why"), e.get("instead")
        if not t or not k or not why or not instead:
            raise ContractError("entries[%d] 缺字段（type/key/why/instead 四个都必填）：%r" % (i, e))
        if t != "*":
            index["%s.%s" % (t, k)] = {"why": why, "instead": instead}
        else:
            index["*.%s" % k] = {"why": why, "instead": instead}
    return entries, index


def build():
    with open(CONTAINER, encoding="utf-8") as f:
        src = f.read()
    ex = extract(src)
    if ex["rendererCount"] == 0:
        print("ERROR 解析出 0 个渲染器 —— 容器源码结构变了，正则要跟着改", file=sys.stderr)
        return None
    entries, index = load_unsupported()
    all_keys = sorted({k for ks in ex["byType"].values() for k in ks} | set(ex["shared"]))
    return {
        "generatedBy": "scripts/props_contract.py",
        "source": "assets/container/index.html",
        # 两个 sha 只作**诊断**：判同步靠逐类型比对（见 --check 与 validate_prd_json 的 SS-01）。
        # 但**不支持清单**没有逐条比对可言（它是理由表，不参与 byType），只校容器会漏掉
        # 「改了清单没重生成」—— 契约里会留一份过期理由，没有任何门发现（§6.8.3）。
        "sourceSha256": sha256(CONTAINER),
        "unsupportedSha256": sha256(UNSUPPORTED),
        "sourceLines": src.count("\n") + 1,
        "renderers": ex["rendererCount"],
        "helpers": ex["helperCount"],
        "allKeys": all_keys,
        "byType": ex["byType"],
        "slotsByType": ex["slotsByType"],
        "shared": ex["shared"],
        "nonPropP": ex["nonPropP"],
        "unsupported": entries,
        "unsupportedIndex": index,
        "note": (
            "此文件由 scripts/props_contract.py 生成，**不要手改**。"
            "`shared` 是对所有 type 都生效的通用键（renderNode 统一处理，现为 visible）；"
            "`byType` 已包含渲染器调用的同文件 helper 与委托继承键。"
            "改容器后必须重跑生成器；validate_prd_json 的 SS-01 会运行时重算并与本文件逐类型比对，"
            "不一致即 INCOMPLETE（工具链缺失，任何档都非 0）。"
        ),
    }


def diff_docs(old, new):
    """契约文件的实质差异（不含 sha / note 这类纯诊断字段 —— 但两个 sha 例外）。"""
    out = []
    if old.get("renderers") != new.get("renderers"):
        out.append("渲染器数：契约 %s / 源码 %s" % (old.get("renderers"), new.get("renderers")))
    if sorted(old.get("shared") or []) != sorted(new.get("shared") or []):
        out.append("shared：契约 %s / 源码 %s" % (old.get("shared"), new.get("shared")))
    ob = {k: set(v) for k, v in (old.get("byType") or {}).items()}
    nb = {k: set(v) for k, v in (new.get("byType") or {}).items()}
    for t in sorted(set(ob) | set(nb)):
        if t not in nb:
            out.append("%s：源码里已没有这个渲染器" % t)
            continue
        if t not in ob:
            out.append("%s：契约里没有这个类型（源码有 %d 个键）" % (t, len(nb[t])))
            continue
        add, sub = sorted(nb[t] - ob[t]), sorted(ob[t] - nb[t])
        if add or sub:
            out.append("%s：源码多 %s / 契约多 %s" % (t, add or "-", sub or "-"))
    os_ = {k: set(v) for k, v in (old.get("slotsByType") or {}).items()}
    ns = {k: set(v) for k, v in (new.get("slotsByType") or {}).items()}
    for t in sorted(set(os_) | set(ns)):
        if os_.get(t, set()) != ns.get(t, set()):
            out.append("%s 插槽：源码多 %s / 契约多 %s"
                       % (t, sorted(ns.get(t, set()) - os_.get(t, set())) or "-",
                          sorted(os_.get(t, set()) - ns.get(t, set())) or "-"))
    # 清单哈希：不比对条目内容，只比源文件指纹。改了 `why` 一个字也算不同步。
    if old.get("unsupportedSha256") != new.get("unsupportedSha256"):
        out.append("不支持清单：契约 sha %s / 源文件 sha %s（清单改了没重生成 —— 契约里是过期理由表）"
                   % ((old.get("unsupportedSha256") or "缺失")[:12], new["unsupportedSha256"][:12]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验同步状态，不写文件")
    a = ap.parse_args()

    try:
        doc = build()
    except ContractError as e:
        print("ERROR %s" % e, file=sys.stderr)
        return 1
    if doc is None:
        return 1

    if a.check:
        if not os.path.exists(CONTRACT):
            print("ERROR 契约文件不存在：%s" % CONTRACT)
            return 1
        with open(CONTRACT, encoding="utf-8") as f:
            old = json.load(f)
        diffs = diff_docs(old, doc)
        if diffs:
            print("ERROR 契约与容器不同步（逐类型比对）：")
            for d in diffs:
                print("  - %s" % d)
            print("      修法：python3 scripts/props_contract.py")
            return 1
        print("PASS 契约同步：%d 个渲染器 / %d 个可读键 / shared=%s / 清单 %d 条 / 容器 sha %s / 清单 sha %s"
              % (doc["renderers"], len(doc["allKeys"]), ",".join(doc["shared"]) or "-",
                 len(doc["unsupported"]), doc["sourceSha256"][:12], doc["unsupportedSha256"][:12]))
        return 0

    os.makedirs(os.path.dirname(CONTRACT), exist_ok=True)
    with open(CONTRACT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("写入 %s" % os.path.relpath(CONTRACT, ROOT))
    print("  渲染器 %d 个 / 可读键 %d 个 / shared %d 个 / 同文件 helper %d 个 / "
          "区块外 p.xxx %d 个(不计入) / 不支持清单 %d 条"
          % (doc["renderers"], len(doc["allKeys"]), len(doc["shared"]), doc["helpers"],
             len(doc["nonPropP"]), len(doc["unsupported"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
