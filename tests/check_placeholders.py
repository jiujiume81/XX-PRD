#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DoD #8：交付文件里不得留未填写的占位符。

判据（E-02 修正后）：
  用 ERE 风格的显式字符串匹配（不用 `grep -rn "TODO\\|TBD"`——BSD grep 的 BRE 不支持 `\\|`，
  该写法恒返回 0，属假绿，见治理 §8 勘误 E-02）。
  命中分两类：允许清单内的（语义内容/断言模式）与未允许的；后者直接 exit 1。

输出遵循 tests/README.md 的断言约定：`PLACEHOLDER=<n> allowed=<m> unallowed=<k>`
后面必须跟着 n 行明细，一条命中一行。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB_FILE = os.path.join("scripts", "placeholder-vocab.json")


def load_patterns(scope):
    """词表唯一数据源是 scripts/placeholder-vocab.json（XX-016④），本文件不再硬编码词条。

    scope: "doc" = 本脚本的全库文档扫描；"artifact" = scripts/prd_flow.py 的 shaping 产物闸门。
    读失败或该作用域为空必须炸——静默退回空词表等于恒 PASS。
    """
    with open(os.path.join(ROOT, VOCAB_FILE), encoding="utf-8") as f:
        words = json.load(f)["words"]
    picked = tuple(item["w"] for item in words if scope in item.get("scopes", ()))
    if not picked:
        raise SystemExit("FAIL placeholders: %s 里没有 scope=%r 的词" % (VOCAB_FILE, scope))
    return picked


# `…` 只有 artifact 作用域：它在中文正文里是正常标点，进全库扫描会误报 46 处
# （references/ 24 处、SKILL/guide 各 4 处，见 iterations/I-02/preflight.md §1 证据 D）。
PATTERNS = load_patterns("doc")
EXTS = {".md", ".py", ".json", ".yml", ".yaml", ".sh", ".html", ".js", ".txt"}
SKIP_DIRS = {".git", "dist", "__pycache__", "node_modules", ".venv", ".build"}
# 扫描豁免：本文件与词表数据文件自身都含模式字面量。
# 判定粒度仍是"命中"（不做整行放行）；新增豁免必须写在这里并说明原因，
# 不允许把带占位词的产物塞进来——产物类命中走 ALLOW 三元组。
SELF = {
    "tests/check_placeholders.py",
    VOCAB_FILE,
}

# 显式允许清单：(相对路径, 该行必须包含的片段, 理由)
# 用"片段"而不是行号：文件行号会漂移，片段漂移了就该重新审一遍。
# 匹配规则（判定粒度是"命中"，不是"行"）：某行出现模式 p，必须有一条 ALLOW 同时满足
#   rel == path  且  p in marker  且  marker in line
# 即 marker 必须**含 p 本身**——否则同一行里新冒出来的另一个占位词会被这条白名单顺带放行。
ALLOW = [
    ("tests/harness.js", "/TODO\\(confirm\\)/",
     "断言模式本身：校验产物是否要求对未确认项打 TODO(confirm) 标注"),
    ("references/05-component-states.md", "阻塞、待补充",
     "组件状态枚举里的状态名，属设计术语不是未完成占位"),
    # 2026-10-20（XX-016④）删掉两条：prd_flow.py 的 PLACEHOLDER 常量与报错文案已改为
    # "读词表 + 按命中动态生成"，字面量消失，原 ALLOW（'PLACEHOLDER = ("TODO"...' 与
    # "（TODO/待补充）"）成了不再对得上的死条目。留着它们等于让白名单看起来还在管、其实不管（E-02 同理）。
    ("assets/container/index.html", "'待补充':'warning'",
     "状态中文名 → 徽标色的映射表"),
    ("assets/container/index.html", "// TODO(confirm)",
     "给用户产物里的提示模板，要求对未确认项打标"),
    # 文档说明类：文档在"讲规则本身"，不是留了未填内容。
    # 约定（tests/README.md）：这类命中入 ALLOW 并写理由，不得靠改写措辞规避。
    (".github/workflows/ci.yml", '"TODO\\|TBD\\|待补充"',
     "CI 注释在说明 E-02 的判据演进（旧命令长什么样、为什么假绿）"),
    ("tests/README.md", "`TODO` / `TBD` / `待补充` / `待填`",
     "文件表在描述该检查的扫描范围"),
    ("tests/README.md", '"禁止 TODO"',
     "README 在声明占位符规则本身"),
    ("tests/README.md", "追加一个 `TODO`",
     "README 在复述历史漏洞（按行判定会把同一行新增的占位词一起放行）"),
    # 「待定」2026-10-20 并入词表（XX-016④）后新增的三条：都是"在讲这个词本身的正当用法"，
    # 不是留了未填内容。按 E-02 纪律入 ALLOW 写理由，不改文案——
    # 尤其容器那处：改它就是改 assets/container/，会让 I-02 非目标 1 与 R3 的前提同时失效。
    ("references/01-clarification.md", '答不上来的写"待定"',
     "澄清引导语在教用户「拿不准就写这个词」，删掉等于删方法论"),
    ("references/05-component-states.md", '用于"此处待定"',
     "Placeholder 组件的用途说明，描述的是该组件的语义"),
    ("assets/container/index.html", "'待定区域'",
     "Placeholder 渲染器的默认占位文案（运行时 UI 文案，不是未填内容）"),
]


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if os.path.splitext(name)[1] not in EXTS:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel in SELF:
                continue
            yield rel, full


def allow_hit(rel, line, pat):
    """判定一条命中（文件 + 行 + 模式）是否被放行。

    三条同时成立才算 ALLOW：路径相同、marker 含该模式本身、marker 出现在该行。
    只看"该行有没有任一允许键"会漏检——同一行后追加另一个占位词会被顺带放行。
    """
    for path, marker, reason in ALLOW:
        if rel == path and pat in marker and marker in line:
            return marker, reason
    return None


def main():
    hits = []          # (rel, lineno, pat, snippet, marker|None, reason|None)
    for rel, full in iter_files(ROOT):
        try:
            text = open(full, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for pat in PATTERNS:
                if pat not in line:
                    continue
                hit = allow_hit(rel, line, pat)
                hits.append((rel, i, pat, line.strip()[:100],
                             hit[0] if hit else None, hit[1] if hit else None))

    allowed = [h for h in hits if h[5]]
    denied = [h for h in hits if not h[5]]
    print("PLACEHOLDER=%d allowed=%d unallowed=%d" % (len(hits), len(allowed), len(denied)))
    for rel, i, pat, snippet, marker, reason in hits:
        if reason:
            # 打出模式与匹配键：日后该行内容变了、路径:行还在时，能直接看出这条 ALLOW 是否还对得上
            print("  ALLOW %s:%d  [%s]  key=%r  <- %s" % (rel, i, pat, marker, reason))
        else:
            print("  DENY  %s:%d  [%s]  %s" % (rel, i, pat, snippet))

    if denied:
        print("FAIL placeholders: %d 处未在允许清单内（要么改掉，要么在 ALLOW 里写明理由）" % len(denied))
        return 1
    print("PASS placeholders: %d 处命中均已在显式允许清单内" % len(hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
