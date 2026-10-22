#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs-consistency：I-01 约定的 5 项最小检查（不碰 guide.html）。

1. 示例清单：`assets/examples/example-0N-*.json` 与 `EXPECTED_EXAMPLES` **逐个名字比对**
   （缺一个 / 多一个 / 换一个都失败；不是数个数）
2. README 引用可达：markdown 链接 + 行内代码文件名 + img src，输出 refs=N whitelist=M dead=0
3. references/*.md 的文件数与 README 里的"NN 份参考文档"一致
4. 版本一致：SKILL.md frontmatter = CHANGELOG.md 最新条目（本地若存在
   ../iterations/I-NN/release.md 也一并比对；取**编号最大**的那一轮，见 _latest_release）
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


def _latest_release():
    """取 ../iterations 下**编号最大**的 I-*/release.md，而不是写死某一轮。

    写死 I-01 的后果（I-02 实测）：轮次一换，本轮自己的 release.md 永远读不到，
    却读到了上一轮的值——DoD 6 于是"三处都比了"，但第三处比错了文件。
    ADR：iterations/ 属治理 §12 工作区维护区，不入仓库，CI 上不存在 → 返回 None。
    排序用目录名字典序，对 I-01…I-99 成立；**I-100 会排到 I-10 前面**，
    到那时须改成按数字排序（此处不提前上复杂度，但把限制写明）。

    **两位零填充是命名约定，不是事实**：`sorted(key=parent.name)` 等价于按编号
    排序，只在 `I-01`…`I-99` 全部零填充的前提下成立；哪天出现 `I-7` 这种写法，
    字典序会把它排到 `I-10` 之后。
    将来改成 `key=lambda p: int(p.parent.name[2:])` 后，遇到 `I-tmp` 会抛
    `ValueError`——**那是看得见的失败，不许用 `try/except` 退回字典序**。
    静默退回字典序，与本轮消灭兜底正则是同一件事：判据还得跑，但判的已经不是
    它宣称的东西，且失败被洗成成功。
    """
    base = ROOT.parent / "iterations"
    if not base.is_dir():
        return None
    cands = sorted(base.glob("I-*/release.md"), key=lambda p: p.parent.name)
    return cands[-1] if cands else None


RELEASE = _latest_release()

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


# 示例库的**清单**（不是数量）。每一个都对应一份教材范本 + 一个 gen 脚本
# （`assets/examples/gen_example0N.py`），并由 `tests/check_generators.py` 做归一化比对。
#
# 为什么写名字而不是数字（I-07 第二批裁定）：数量相等**不蕴含集合相等**。
# 6 个文件里把 example-03 换成 example-09，`len()==6` 照样通过，而 README 与生成器
# 全都对不上。所以这里逐名比对：缺一个 / 多一个 / 换一个都失败。
# 加 `example-06-dense-list.json`（I-07 F3 的作业型列表页范本）是结构性同步：
# 清单变长 = 要求更严，不是放宽。
EXPECTED_EXAMPLES = (
    "example-01-task-board.json",
    "example-02-refund-flow.json",
    "example-03-nav-tree.json",
    "example-04-master-detail.json",
    "example-05-behavior-model.json",
    "example-06-dense-list.json",
)


def check_examples():
    actual = set(p.name for p in (ROOT / "assets" / "examples").glob("example-0*.json"))
    expect = set(EXPECTED_EXAMPLES)
    missing = sorted(expect - actual)      # 清单里有、盘上没有
    extra = sorted(actual - expect)        # 盘上有、清单里没有（含「换了名字」）
    if not missing and not extra:
        print("PASS examples: %d/%d 存在（按名单逐个比对）"
              % (len(actual), len(expect)))
        return True
    if missing:
        print("FAIL examples: 缺少 %d 个 —— %s" % (len(missing), ", ".join(missing)))
    if extra:
        print("FAIL examples: 多出 %d 个（不在清单里 / 被换过名）—— %s"
              % (len(extra), ", ".join(extra)))
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
    """只认**显式版本字段**，拿不到就返回 None。

    删掉了原来那句兜底 `re.search(r"v?(\\d+\\.\\d+\\.\\d+)", text)`：它抓的是全文第一个
    x.y.z，在 I-01/release.md 里下一步就会撞上 Chrome 版本号（`155.0.8059.39`）。
    兜底正则的坏处不是"偶尔抓错"，而是**它永远能返回一个值、永远不报错**，
    于是判据看起来在跑、实际判的不是它宣称的东西（与 E-01/E-02 同型）。

    **冒号式必须锚行首**（E-06）：不锚的话，任何一句提到"版本"的正文都会被当成
    字段。I-02 实测：往 release.md 写一行"日志抄录：版本：0.6.0 的容器跑出 757
    断言"，未加锚的 `re.search` 会取到句子中间的 0.6.0，于是 DoD 6 从 SKIP 翻成
    PASS、`NOT-VERIFIED` 也跟着消失。删兜底正则解决的是"**永远**能返回值"，
    加行首锚解决的是"**能从不该取的位置**取值"——同一个病的两半：判据在跑，
    判的不是它宣称的东西，只是后者更隐蔽，发作方向是把 SKIP 洗成 PASS。
    """
    if RELEASE is None or not RELEASE.exists():
        return None
    text = RELEASE.read_text(encoding="utf-8")
    # 表格行：| 版本号 | `0.5.0`（暂定…） |
    m = re.search(r"(?m)^\|\s*版本号\s*\|\s*`?v?(\d+\.\d+\.\d+)`?", text)
    if not m:
        # 冒号行：`版本：0.5.0` / `版本: v0.5.0`，允许列表/引用/缩进前缀。
        # `(?m)^[\s>*\-]*` 是 E-06 的修复：没有它，句中"……版本：0.6.0 的容器……"
        # 也会命中，把 SKIP 洗成 PASS。
        m = re.search(r"(?m)^[\s>*\-]*版本\s*[:：]\s*v?(\d+\.\d+\.\d+)", text)
    return m.group(1) if m else None


def release_source():
    """release.md 的来源（相对工作区根），便于在输出里自证"读的是哪份"。"""
    if RELEASE is None or not RELEASE.exists():
        return "none"
    return os.path.relpath(str(RELEASE), str(ROOT.parent))


def check_versions():
    skill = read_skill_version()
    changelog = read_changelog_version()
    release = read_release_version()

    print(
        "versions: skill=%s changelog=%s release=%s"
        % (skill or "MISSING", changelog or "MISSING", release or "none")
    )
    print("release-source: %s" % release_source())

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
