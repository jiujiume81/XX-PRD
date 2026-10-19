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
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATTERNS = ("TODO", "TBD", "待补充", "待填")
EXTS = {".md", ".py", ".json", ".yml", ".yaml", ".sh", ".html", ".js", ".txt"}
SKIP_DIRS = {".git", "dist", "__pycache__", "node_modules", ".venv", ".build"}
SELF = os.path.join("tests", "check_placeholders.py")  # 本文件含模式字面量，跳过自身

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
    ("scripts/prd_flow.py", 'PLACEHOLDER = ("TODO", "待补充", "待定", "TBD"',
     "占位符检测器的常量定义（这一行同时含三个模式，一条覆盖）"),
    ("scripts/prd_flow.py", "（TODO/待补充）",
     "校验器报错文案（同时含两个模式）"),
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
]


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if os.path.splitext(name)[1] not in EXTS:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel == SELF.replace(os.sep, "/"):
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
