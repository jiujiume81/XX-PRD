#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示例生成器的共用层 —— 三个不变量在**生成时**强制，不靠事后扫描。

为什么要有这一层
----------------
`props` 是逐字段手写读的（容器里 `p.xxx`），写一个没被读的键既不生效也不报错；
页面可达性与 `doneWhen` 完整性同理，都是「产物看起来对、其实走不通」的形态。
靠生成完之后再扫一遍，等于把「生成器写错了」这件事交给下游去发现 ——
下游一旦漏掉一条，缺陷就静默进包。

所以三个不变量写在生成入口上：

  I1 props 键必须被该 type 读过（`byType` ∪ `shared` ∪ `slotsByType`，来自契约，不手写）
  I2 除 `meta.currentPageId` 外每页都能只沿 `navigate` 跳转边到达（强边可达）
  I3 有提交类能力的页必须写 `contract.doneWhen`

任一不满足 → 生成失败（`SystemExit(1)`），**不许把缺陷产物写进仓库**。

契约从 `assets/container/props-contract.json` 读，那是 `scripts/props_contract.py`
从容器源码机械提取出来的唯一真源。手写白名单一定会分叉，所以这里也读文件。

用法
----
    from genlib import finalize, dump, node

    doc = {...}
    finalize(doc, "example-0N")
    dump(doc, OUT)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "..", "container", "props-contract.json")


def _load_contract():
    with open(CONTRACT, encoding="utf-8") as f:
        return json.load(f)


_C = _load_contract()
BY_TYPE = _C["byType"]
SLOTS = _C.get("slotsByType") or {}
SHARED = set(_C.get("shared") or [])
ALLOWED = {t: set(keys) | SHARED | set(SLOTS.get(t, [])) for t, keys in BY_TYPE.items()}

# 这些键不是组件属性，是节点自身结构，不参与 props 校验
NODE_KEYS = {"id", "type", "children", "props"}


def node(type_name, id=None, children=None, **props):
    """构造一个节点。props 的键当场校验（fail fast，错误指到生成器那一行）。"""
    if type_name not in ALLOWED:
        raise SystemExit("genlib: 未知组件类型 %r（契约里 %d 个）" % (type_name, len(ALLOWED)))
    bad = sorted(set(props) - ALLOWED[type_name])
    if bad:
        raise SystemExit(
            "genlib: %s 不接受 props 键 %s\n  可读集：%s\n  明确不支持：见 "
            "references/props-unsupported.json" % (type_name, bad, sorted(ALLOWED[type_name])))
    n = {"id": id, "type": type_name}
    if children is not None:
        n["children"] = children if isinstance(children, list) else [children]
    n["props"] = props
    return n


# ------------------------------------------------------------------ 遍历
def _iter_nodes(n, path, out):
    if not isinstance(n, dict):
        return
    t = n.get("type")
    if t:
        out.append((path + "/" + str(n.get("id") or "?"), t, n.get("props") or {}))
        tpl = (n.get("props") or {}).get("renderItem")
        if isinstance(tpl, dict):
            _iter_nodes(tpl, path + "/" + str(n.get("id")) + ".renderItem", out)
        # 节点级 renderItem 是明确不支持的位置（R7），这里也照记
        if isinstance(n.get("renderItem"), dict):
            out.append((path + "/" + str(n.get("id")) + ".node.renderItem", "__R7__", {}))
    for ch in (n.get("children") or []):
        _iter_nodes(ch, path, out)


def _all_nodes(pages):
    out = []
    for p in pages:
        _iter_nodes(p.get("componentTree") or {}, p.get("id") or "?", out)
        for slot, keys in SLOTS.items():
            pass  # slots 已在 props 键校验里放过；其值本身作为节点由 children 覆盖
    return out


def check_props(doc):
    """I1：返回 [(位置, type, 键)] 违规列表。"""
    bad = []
    for path, t, props in _all_nodes(doc.get("pages") or []):
        if t == "__R7__":
            bad.append((path, "renderItem", "（节点级 renderItem 不在契约键空间内）"))
            continue
        allowed = ALLOWED.get(t)
        if allowed is None:
            bad.append((path, t, "（契约里没有这个 type）"))
            continue
        for k in props:
            if k not in allowed:
                bad.append((path, t, k))
    return bad


def check_reach(doc):
    """I2：强边可达。返回不可达页 id 列表。"""
    pages = doc.get("pages") or []
    ids = {p["id"] for p in pages}
    cur = ((doc.get("meta") or {}).get("currentPageId"))
    if cur not in ids:
        return ["<meta.currentPageId 未指向任何页>"]
    nav = {}
    for p in pages:
        out = []
        for it in (p.get("interactions") or []):
            for a in (it.get("actions") or []):
                if a.get("type") == "navigate" and isinstance(a.get("pageId"), str):
                    out.append(a["pageId"])
        nav[p["id"]] = out
    seen = {cur}
    q = [cur]
    while q:
        n = q.pop(0)
        for t in nav.get(n, []):
            if t in ids and t not in seen:
                seen.add(t)
                q.append(t)
    return [i for i in (p["id"] for p in pages) if i not in seen]


def submit_pages(doc, verbose=False):
    """有提交类能力的页（A′ 的分母）。三个结构性信号取并集，不按名字猜。"""
    caps_by_page = {}
    for c in (doc.get("capabilities") or []):
        pg = c.get("page")
        if not pg:
            continue
        if (c.get("to") or []) or (c.get("from") == []):
            caps_by_page.setdefault(pg, []).append(c.get("id"))
    pages = []
    for p in (doc.get("pages") or []):
        signals = list(caps_by_page.get(p["id"], []))
        acts = set()
        for it in (p.get("interactions") or []):
            for a in (it.get("actions") or []):
                if a.get("type") in ("gotoState", "setState", "setNode"):
                    acts.add(a["type"])
        if signals or acts:
            pages.append(p["id"])
    if verbose:
        print("    提交类页 %d：%s" % (len(pages), pages))
    return pages


def check_donewhen(doc):
    """I3：返回 (有 contract 却缺 doneWhen 的页, 连 contract 都没写的提交页)。

    规则：**有 `contract` 的提交页必须写 `doneWhen`**（有契约就要兑现承诺）。
    连 `contract` 都没写的页不在这里判，但**必须打出来**并对应一条 backlog ——
    「没建模 = 不用判」正是要防的那种免检，所以缺口要显式、可追踪，不许静默。
    """
    missing = []
    no_contract = []
    by_page = {p["id"]: p for p in (doc.get("pages") or [])}
    for pid in submit_pages(doc):
        c = (by_page[pid].get("contract") or {})
        if not c:
            no_contract.append(pid)
        elif not str(c.get("doneWhen") or "").strip():
            missing.append(pid)
    return missing, no_contract


# ------------------------------------------------------------------ 出口
def finalize(doc, name, quiet=False):
    """跑三个不变量；有违规就抛 SystemExit，绝不写出缺陷产物。"""
    problems = []

    bad = check_props(doc)
    if bad:
        problems.append("I1 props 键不被读（%d 处）：" % len(bad))
        for path, t, k in bad[:12]:
            problems.append("    %s  %s.props.%s" % (path, t, k))
        if len(bad) > 12:
            problems.append("    …… 另 %d 处" % (len(bad) - 12))

    miss = check_reach(doc)
    if miss:
        problems.append("I2 强边不可达（%d 页）：%s" % (len(miss), miss))

    dw, no_contract = check_donewhen(doc)
    if dw:
        problems.append("I3 有 contract 却缺 doneWhen（%d 页）：%s" % (len(dw), dw))

    if problems:
        raise SystemExit("%s 生成失败 ——\n%s\n" % (name, "\n".join(problems)))

    if not quiet:
        pages = len(doc.get("pages") or [])
        print("  %-12s I1 ✓（%d 页全键可读）  I2 ✓（%d 页强边可达）  I3 ✓（%d 页有 doneWhen）"
              % (name, pages, pages, len(submit_pages(doc)) - len(no_contract)))
        if no_contract:
            print("  %-12s 缺口（显式，见 XX-056）：%d 个提交页没有 contract，故不判 doneWhen：%s"
                  % (name, len(no_contract), no_contract))
    return doc


def dump(doc, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("  written %s (%d bytes)" % (os.path.relpath(path), os.path.getsize(path)))
    return path
