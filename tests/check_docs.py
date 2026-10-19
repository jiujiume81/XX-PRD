#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs-consistency：I-01 约定的 5 项最小检查（不碰 guide.html）。

1. 5 个示例文件存在
2. README 引用可达：markdown 链接 + 行内代码文件名 + img src，输出 refs=N whitelist=M dead=0
3. references/*.md 的文件数与 README 里的"NN 份参考文档"一致
4. 版本一致：SKILL.md frontmatter = CHANGELOG.md 最新条目（本地若存在
   ../iterations/I-01/release.md 也一并比对）
5. EXTERNAL：容器零外部依赖（D9 换判据）—— 判 src/href 外链、@import url(http、
   CSS url(http、fetch(http、XHR.open(..., http、importScripts(http；
   SVG 命名空间 http://www.w3.org/2000/svg 不算违规（不联网）

明确不做（归 XX-009 / I-02）：读 guide.html、比对阶段数/卡点数/术语。
用法: python3 tests/check_docs.py
退出码: 0 = 5 项全过, 1 = 有差异
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SKILL = ROOT / "SKILL.md"
CHANGELOG = ROOT / "CHANGELOG.md"
RELEASE = ROOT.parent / "iterations" / "I-01" / "release.md"

# 产物名 / 占位符 / 安装副本路径 —— 不是仓库内文件，检查时必须显式列出
WHITELIST = {
    "slices.json",              # prd_slice.py 的输入产物
    "devspec.json",             # 容器导出的开发交接包
    "AGENT.md",                 # 同上
    "XX-PRD.html",              # 交付产物
    "XX-PRD.data.json",         # 可选外置数据文件（04 §974）
    "skills/XX-PRD/XX-PRD/SKILL.md",  # 安装副本的错误路径示例（README:62）
    ".md",                      # 导出格式说明，不是文件名
    "{产品}.devspec.json",      # 占位符
}

FILE_EXT = re.compile(r"\.(html|json|md|py|png|zip|yml|yaml)$")


def check_examples():
    files = sorted((ROOT / "assets" / "examples").glob("example-0*.json"))
    if len(files) == 5:
        print("PASS examples: 5/5 存在")
        return True
    print("FAIL examples: 期望 5 个 example-0*.json，实际 %d 个" % len(files))
    return False


def resolve(ref):
    """按仓库根 → scripts/ → assets/examples/ 依次解析，返回是否存在。"""
    for cand in (ROOT / ref, ROOT / "scripts" / ref, ROOT / "assets" / "examples" / ref):
        if cand.exists():
            return True
    return False


def check_readme_refs():
    raw = README.read_text(encoding="utf-8")
    refs = []

    for m in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", raw):
        t = m.group(1).strip()
        if t.startswith(("http", "#", "mailto")):
            continue
        refs.append(t.split("#")[0])

    for m in re.finditer(r"`([^`\n]+?)`", raw):
        t = m.group(1).strip()
        if FILE_EXT.search(t):
            refs.append(t)

    for m in re.finditer(r'<img[^>]+src="([^"]+)"', raw):
        refs.append(m.group(1).strip())

    refs = [r for r in refs if r]
    whitelisted = sorted(set(r for r in refs if r in WHITELIST))
    dead = [r for r in refs if r not in WHITELIST and not resolve(r)]

    # whitelist 计的是**去重后的条数**，下面逐条列出，两者必须对得上
    print(
        "refs=%d whitelist=%d dead=%d"
        % (len(refs), len(whitelisted), len(dead))
    )
    for r in whitelisted:
        print("  whitelist: %s" % r)
    for r in dead:
        print("  DEAD: %s" % r)

    if dead:
        print("FAIL readme-refs: %d 条引用不可达" % len(dead))
        return False
    print("PASS readme-refs")
    return True


def check_reference_count():
    actual = len(list((ROOT / "references").glob("*.md")))
    raw = README.read_text(encoding="utf-8")
    m = re.search(r"(\d+)\s*份参考文档", raw)
    if not m:
        print("FAIL references-count: README 中找不到「NN 份参考文档」")
        return False
    claimed = int(m.group(1))
    if claimed != actual:
        print("FAIL references-count: README 写 %d，实际 %d" % (claimed, actual))
        return False
    print("PASS references-count: %d 份（README 与实际一致）" % actual)
    return True


def read_skill_version():
    text = SKILL.read_text(encoding="utf-8")
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    v = re.search(r"^version:\s*(.+?)\s*$", m.group(1), re.M)
    return v.group(1).strip().strip('"\'') if v else None


def read_changelog_version():
    text = CHANGELOG.read_text(encoding="utf-8")
    m = re.search(r"^##\s*\[?v?(\d+\.\d+\.\d+)\]?", text, re.M)
    return m.group(1) if m else None


def read_release_version():
    if not RELEASE.exists():
        return None
    text = RELEASE.read_text(encoding="utf-8")
    m = re.search(r"版本\s*[:：]\s*v?(\d+\.\d+\.\d+)", text)
    if m:
        return m.group(1)
    m = re.search(r"v?(\d+\.\d+\.\d+)", text)
    return m.group(1) if m else None


def check_versions():
    skill = read_skill_version()
    changelog = read_changelog_version()
    release = read_release_version()

    print(
        "versions: skill=%s changelog=%s release=%s"
        % (skill or "MISSING", changelog or "MISSING", release or "未生成(S6 前可缺省)")
    )

    if not skill or not changelog:
        print("FAIL versions: SKILL.md 或 CHANGELOG.md 缺版本号")
        return False

    bad = []
    if skill != changelog:
        bad.append("SKILL.md(%s) != CHANGELOG(%s)" % (skill, changelog))
    if release is not None and release != skill:
        bad.append("release.md(%s) != SKILL.md(%s)" % (release, skill))

    if bad:
        print("FAIL versions: " + "; ".join(bad))
        return False
    print("PASS versions: %s" % skill)
    return True



CONTAINER = ROOT / "assets" / "container" / "index.html"

# 六类"真的会联网"的引用；SVG 命名空间（xmlns="http://www.w3.org/2000/svg"）不在其中
EXTERNAL_PATTERNS = [
    ("src", r'src\s*=\s*["\']https?://'),
    ("href", r'href\s*=\s*["\']https?://'),
    ("import-url", r'@import\s+url\(\s*["\']?https?://'),
    ("css-url", r'url\(\s*["\']?https?://'),
    ("fetch", r'fetch\(\s*["\']https?://'),
    ("xhr", r'\.open\(\s*["\'][A-Za-z]+["\']\s*,\s*["\']https?://'),
    ("importScripts", r'importScripts\(\s*["\']https?://'),
]


def check_external():
    """D9：判"六类真实外链"而非 grep https?://（后者会把 SVG 命名空间算进来）。"""
    text = CONTAINER.read_text(encoding="utf-8")
    hits = []
    for label, pat in EXTERNAL_PATTERNS:
        for m in re.finditer(pat, text):
            hits.append((label, m.group(0)[:80]))

    print("EXTERNAL=%d" % len(hits))
    for label, frag in hits:
        print("  EXTERNAL[%s]: %s" % (label, frag))

    if hits:
        print("FAIL external: 容器存在 %d 处外部资源引用" % len(hits))
        return False
    print("PASS external: 无外部资源引用（SVG 命名空间不计）")
    return True

def main():
    results = [
        check_examples(),
        check_readme_refs(),
        check_reference_count(),
        check_versions(),
        check_external(),
    ]
    if all(results):
        print("PASS docs-consistency: 5/5")
        return 0
    print("FAIL docs-consistency: %d/5 通过" % sum(results))
    return 1


if __name__ == "__main__":
    sys.exit(main())
