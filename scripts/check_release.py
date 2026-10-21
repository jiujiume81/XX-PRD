#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DoD 1–9 发布准入检查：一条命令给出逐项名称与结论（XX-016）。

为什么需要它：
  治理 §8.2 的第 1–9 项原本散在 4 个脚本与若干裸命令里，靠人逐条记得跑。
  分散 + 人工的检查不会被真正执行——E-01/E-02/E-03 三条勘误都证明了这一点。
  这里把它们收敛成一个退出码：非 0 即不许发布。

设计原则（对应 I-02 preflight 的结论）：
  - **调用而不是复制**：能与既有脚本复用的一律 import 其函数（check_docs 的 5 个 check_*、
    check_placeholders.main、check_generators.main）、或调其 --json 出口
    （validate_prd_json.py）；只有必须开子进程的（run.sh 要 Chrome、compileall 是解释器开关）才
    subprocess。**不改任何既有判定逻辑**。
  - **逐项归因**：每项一行「名称 + 结论」，失败项缩进贴下游原始失败行。不允许只报
    「某个检查失败」——那等于把人肉排查的成本又还给了使用者。
  - **SKIP 不等于 PASS**：跳过必须在行内写原因，并在 RESULT 行统计 skipped 数；
    只要 skipped>0，RESULT 之后再打一行 `NOT-VERIFIED: <项名, …>`，点名"哪几项没被验证过"。
    当前两个 SKIP 源都写实到具体文件：DoD 6（`release.md` 是占位、无版本行，
    或 CI 上根本没有 `iterations/`）与 DoD 7（本机无安装副本）。
  - **TREE 自证**：首行先声明"本轮判的是哪棵树"——`TREE <sha> clean` /
    `TREE <sha> DIRTY(<N>)` / `TREE unversioned`。源仓库与安装副本同时是脏的时，
    DoD 7 会比出"两边一样脏"而 PASS（0.5.1 收口时确实发生过），全绿但判的是脏树。
    脏树不是失败，退出码不变，只是把事实印在脸上：RESULT 行尾带 `｜TREE DIRTY(<N>)`，
    DoD 7 的 PASS detail 带 `（HEAD=<sha>）`。

用法:
    python3 scripts/check_release.py
    RETRIES_MAX=1 python3 scripts/check_release.py     # 透传给 tests/run.sh

退出码:
    0 = 九项均 PASS 或 SKIP（SKIP 会在 RESULT 行计数）
    1 = 任一项 FAIL
    2 = 环境不可用（找不到 Chrome / python3 / bash，run.sh 被锁，
        或 `.build` 清理被 safe-delete 拦截导致本轮结果不可信）
    3 = 用法错误
"""
import filecmp
import io
import json
import os
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 同一棵树的另一种写法：git 命令一律 `-C REPO_ROOT`，不依赖进程 cwd——
# 本脚本会被从任意目录调用（例如 `python3 ~/.workbuddy/skills/XX-PRD/scripts/...`）。
REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS = os.path.join(ROOT, "tests")
SCRIPTS = os.path.join(ROOT, "scripts")
INSTALL_COPY = os.path.expanduser("~/.workbuddy/skills/XX-PRD")

# 安装副本比对时两边都排除的东西：构建产物、字节码缓存、编辑器垃圾
CMP_SKIP_DIRS = {".git", "__pycache__", ".build", "node_modules", ".venv", "dist"}
CMP_SKIP_FILES = {".DS_Store"}
CMP_SKIP_SUFFIX = (".pyc",)

STATUS_PASS, STATUS_FAIL, STATUS_SKIP, STATUS_ENV = "PASS", "FAIL", "SKIP", "ENV"


def wide_len(s):
    """按终端显示宽度算长度：CJK 全角字符占 2 列。用于对齐「名称」列。"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def pad(s, width):
    return s + " " * max(0, width - wide_len(s))


def silence(fn, *a, **kw):
    """静默调用既有脚本的函数，返回 (结果, 它打印的全部文本)。"""
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = fn(*a, **kw)
    return result, buf.getvalue()


def first_lines(text, n=6):
    rows = [r.rstrip() for r in text.splitlines() if r.strip()]
    return rows[:n]


# ---------------------------------------------------------------- TREE 自证

_TREE = {}


def tree_state():
    """本轮判的是哪棵树：`(行, sha, 脏文件数)`，结果缓存在 `_TREE` 里只算一次。

    三种取值，穷尽所有情况，不允许抛异常：
      - `TREE <sha> clean`    —— 有 .git 且 `git status --porcelain` 为空
      - `TREE <sha> DIRTY(N)` —— 有 .git 且 N 行改动（源 ↔ 副本同时脏时 DoD 7 会假绿）
      - `TREE unversioned`    —— 没有 .git（安装副本就是这种）或 git 不可用

    `git` 一律显式 `-C`，不靠 cwd；不传 `check=True`，rc≠0 一律降级成 unversioned。
    """
    if _TREE:
        return _TREE
    _TREE.update(line="TREE unversioned", sha=None, dirty=0)
    try:
        head = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True)
        status = subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
                                capture_output=True, text=True)
    except (OSError, ValueError):        # git 不存在 / 不是可执行文件
        return _TREE
    sha = head.stdout.strip()
    if head.returncode != 0 or status.returncode != 0 or not sha:
        return _TREE
    dirty = len([l for l in status.stdout.splitlines() if l.strip()])
    _TREE["sha"] = sha
    _TREE["dirty"] = dirty
    _TREE["line"] = ("TREE %s DIRTY(%d)" % (sha, dirty)) if dirty else ("TREE %s clean" % sha)
    return _TREE


# ---------------------------------------------------------------- 各项检查


def check_examples(_docs, _ph, _gen):
    """DoD 1：5 个示例结构 + 语义校验（走 validate_prd_json.py 自带的 --json 出口）。"""
    files = sorted(
        os.path.join(ROOT, "assets", "examples", f)
        for f in os.listdir(os.path.join(ROOT, "assets", "examples"))
        if f.startswith("example-0") and f.endswith(".json")
    )
    if not files:
        return STATUS_FAIL, "找不到 assets/examples/example-0*.json", []
    n_err = n_warn = 0
    details, fails = [], []
    for path in files:
        rel = os.path.relpath(path, ROOT)
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "validate_prd_json.py"), "--json", path],
            capture_output=True, text=True,
        )
        try:
            rep = json.loads(proc.stdout)
        except ValueError:
            return STATUS_FAIL, "%s 的 --json 输出无法解析（rc=%d）" % (rel, proc.returncode), first_lines(proc.stderr)
        for item in rep:
            n_err += len(item["errors"])
            n_warn += len(item["warns"])
            for e in item["errors"]:
                fails.append("%s: %s" % (os.path.basename(item["target"]), e))
    details.append("%d/%d errors=%d warnings=%d" % (len(files), len(files), n_err, n_warn))
    if n_err:
        return STATUS_FAIL, details[0], fails
    return STATUS_PASS, details[0], []


def _safe_delete_note(line):
    """从 `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED] {json}` 里取 count 与 target。"""
    try:
        payload = json.loads(line[line.index("{"):])
        targets = payload.get("targets") or []
        tgt = os.path.basename(str(targets[0]).rstrip("/")) if targets else "?"
        return "count=%s，target=%s" % (payload.get("count"), tgt)
    except (ValueError, TypeError):
        return line.strip()[:120]


def check_regression(_docs, _ph, _gen):
    """DoD 2：容器回归全绿，且 retries 不得超过上限（勘误 E-03）。

    额外守一条**清洁性**判据：`tests/run.sh` 的 `clean_dir` 依赖删除能力，
    删除被拦时它不报错，只是 `.build` 里的旧 profile 留着 → 下一轮脏跑
    （实测同一份代码可跑出 757/0、754/4、666/18）。日志里
    `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]` 就是它留下的痕迹。
    这种红不是"回归失败"而是"本轮结果不可信"，必须判 ENV，不许判 FAIL——
    否则会把环境问题报成代码问题，正是 E-01/E-02/E-03 同型的混淆。
    """
    bash = shutil.which("bash")
    if not bash:
        return STATUS_ENV, "找不到 bash", []
    proc = subprocess.run([bash, os.path.join(TESTS, "run.sh")], capture_output=True, text=True)
    text = proc.stdout + proc.stderr
    total = [l for l in text.splitlines() if l.startswith("TOTAL ")]
    retries = [l for l in text.splitlines() if l.startswith("RETRIES=")]
    detail = " ".join(retries) if retries else (total[0] if total else "无 TOTAL/RETRIES 行")
    blocked = [l for l in text.splitlines() if "SAFE_DELETE" in l]
    if blocked:
        note = "`.build` 清理被拦截，本轮结果不可信（%s）" % _safe_delete_note(blocked[0])
        if len(blocked) > 1:
            note += "，共 %d 处" % len(blocked)
        lines = [l.strip()[:160] for l in blocked[:2]] + ([total[0]] if total else [])
        return STATUS_ENV, note, lines
    if proc.returncode in (2, 3):
        return STATUS_ENV, detail + "（run.sh rc=%d，环境或锁）" % proc.returncode, first_lines(text, 3)
    if proc.returncode != 0:
        return STATUS_FAIL, detail, first_lines(text, 8)
    return STATUS_PASS, detail, []


def _import_check_modules():
    for p in (TESTS, SCRIPTS):
        if p not in sys.path:
            sys.path.insert(0, p)
    import check_docs  # noqa: E402
    import check_placeholders  # noqa: E402
    import check_generators  # noqa: E402
    return check_docs, check_placeholders, check_generators


def check_external(docs, _ph, _gen):
    """DoD 3：容器无外部资源加载（复用 check_docs.check_external，不复制正则）。"""
    ok, out = silence(docs.check_external)
    hit = [l for l in out.splitlines() if l.startswith("EXTERNAL=")]
    detail = hit[0] if hit else ""
    return (STATUS_PASS if ok else STATUS_FAIL), detail, first_lines(out) if not ok else []


def check_generators_match(_docs, _ph, gen):
    """DoD 4：示例与生成器一致（复用 check_generators.main）。"""
    rc, out = silence(gen.main)
    bad = [l for l in out.splitlines() if l.startswith("DRIFT")]
    detail = " ".join(l for l in out.splitlines() if l.startswith("PASS generators")) or "3/3 一致"
    if rc != 0:
        return STATUS_FAIL, detail.replace("PASS", "FAIL"), bad[:6]
    return STATUS_PASS, detail, []


def check_docs_consistency(docs, _ph, _gen):
    """DoD 5：文档口径（示例数 / README 引用可达 / references 计数）。"""
    results, out = [], ""
    for fn in (docs.check_examples, docs.check_readme_refs, docs.check_reference_count):
        ok, text = silence(fn)
        results.append(ok)
        out += text
    refs = [l for l in out.splitlines() if l.startswith("refs=")]
    counts = [l for l in out.splitlines() if l.startswith("PASS references-count")]
    detail = ", ".join(x for x in (refs[0] if refs else "", counts[0].replace("PASS ", "") if counts else "") if x)
    if all(results):
        return STATUS_PASS, detail, []
    return STATUS_FAIL, detail, first_lines(out, 8)


def check_versions(docs, _ph, _gen):
    """DoD 6：版本号一致。三种结局分得很细，因为它们的 actionable 指向完全不同。

    - 三处都有值且相等 → PASS，detail 里带 `release-source` 自证"读的是哪份"
    - release 读不到 → SKIP，但原因必须落到**具体文件**：
      `无 iterations/I-*/release.md`（CI 上恒如此）或
      `iterations/I-02/release.md 无版本行（S6 前占位）`（本轮如此）。
    - 有值但不等 → FAIL（由 check_docs 返回 False 驱动）

    历史：`check_docs.py:27` 曾把 release 路径写死成 I-01，于是本轮自己的
    release.md 永远读不到、却拿到了上一轮的值，输出还写"仅比两处"——两者都不成立。
    2026-10-20 已修（`_latest_release()` + 删兜底正则 + 打印 release-source）。
    """
    ok, out = silence(docs.check_versions)
    vline = [l for l in out.splitlines() if l.startswith("versions:")]
    sline = [l for l in out.splitlines() if l.startswith("release-source:")]
    detail = vline[0] if vline else ""
    src = sline[0].split(":", 1)[1].strip() if sline else "none"

    if not ok:
        # 第一行就是 detail 里那行 versions:，不再重复贴一遍
        return STATUS_FAIL, detail, [l for l in first_lines(out, 6) if not l.startswith("versions:")]

    if "release=none" in detail:
        reason = ("无 iterations/I-*/release.md" if src == "none"
                  else "%s 无版本行（S6 前占位）" % src)
        return STATUS_SKIP, "%s（release-source: %s；%s）" % (detail, src, reason), []

    return STATUS_PASS, "%s（release-source: %s）" % (detail, src), []


def _manifest(root):
    """列出目录下所有文件的 {相对路径: 字节数}，跳过构建产物与缓存。"""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in CMP_SKIP_DIRS)
        for name in sorted(filenames):
            if name in CMP_SKIP_FILES or name.endswith(CMP_SKIP_SUFFIX):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out[rel] = os.path.getsize(full)
    return out


def check_install_copy(_docs, _ph, _gen):
    """DoD 7：安装副本同步。本机无副本时 SKIP（CI 恒无），不当作 PASS。"""
    if not os.path.isdir(INSTALL_COPY):
        return STATUS_SKIP, "无 %s（CI 上恒无）" % INSTALL_COPY, []
    a, b = _manifest(ROOT), _manifest(INSTALL_COPY)
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    differ = sorted(k for k in set(a) & set(b)
                    if not filecmp.cmp(os.path.join(ROOT, k), os.path.join(INSTALL_COPY, k), shallow=False))
    if only_a or only_b or differ:
        detail = "仅源码 %d / 仅副本 %d / 内容不同 %d" % (len(only_a), len(only_b), len(differ))
        # **全量输出，不截断**：G3 的判据是"差异集逐行等于 git status --porcelain"，
        # 截成 3 行这条判据就无法执行，而被截掉的往往正是"改错文件"这种最该看见的信息。
        # 前缀区分三类：- 只在源码 / + 只在副本 / ~ 两边都有但字节不同。
        lines = (["-" + x for x in only_a] + ["+" + x for x in only_b] + ["~" + x for x in differ])
        return STATUS_FAIL, detail, lines
    # PASS detail 必须带 HEAD：不然"一致"只说清了两边相等，说不清相等的是哪棵树——
    # 两边同时脏时这条照样 PASS，只有印上 sha 才留得下证据。
    return STATUS_PASS, "%d 个文件逐字节一致（HEAD=%s）" % (len(a), tree_state()["sha"] or "unversioned"), []


def check_placeholders(_docs, ph, _gen):
    """DoD 8：无未填写的占位符（复用 check_placeholders.main）。"""
    rc, out = silence(ph.main)
    line = [l for l in out.splitlines() if l.startswith("PLACEHOLDER=")]
    detail = line[0] if line else ""
    if rc != 0:
        return STATUS_FAIL, detail, [l.strip() for l in out.splitlines() if "DENY" in l][:6]
    return STATUS_PASS, detail, []


def check_syntax(_docs, _ph, _gen):
    """DoD 9：语法检查（等价 CI 的 py-syntax 作业）。"""
    proc = subprocess.run([sys.executable, "-m", "compileall", "-q", "scripts", "tests"],
                          cwd=ROOT, capture_output=True, text=True)
    text = proc.stdout + proc.stderr
    if proc.returncode != 0:
        return STATUS_FAIL, "compileall rc=%d" % proc.returncode, first_lines(text, 6)
    return STATUS_PASS, "compileall scripts tests rc=0", []


# ---------------------------------------------------------------- 骨架

ITEMS = [
    ("全部示例结构 + 语义校验通过", check_examples),
    ("容器回归全绿", check_regression),
    ("容器无外部资源加载", check_external),
    ("示例与生成器一致", check_generators_match),
    ("文档口径一致", check_docs_consistency),
    ("版本号一致", check_versions),
    ("安装副本同步", check_install_copy),
    ("无未填写的占位符", check_placeholders),
    ("语法检查通过", check_syntax),
]


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv:
        print("未知参数：%s（本脚本只有 --help）" % " ".join(argv))
        return 3

    # 首行：先声明判的是哪棵树，再谈九项结论。脏不脏与判据无关，只影响"这次绿算不算数"。
    tree = tree_state()
    print(tree["line"])

    docs, ph, gen = _import_check_modules()
    rows, fails, skipped = [], 0, 0
    for i, (name, fn) in enumerate(ITEMS, 1):
        try:
            status, detail, fail_lines = fn(docs, ph, gen)
        except SystemExit as e:               # 被调脚本自身以 SystemExit 退出
            status, detail, fail_lines = STATUS_FAIL, "调用方退出：%s" % e, []
        except Exception as e:                # 任何异常都必须变成该项 FAIL，不许中断整轮
            status, detail, fail_lines = STATUS_FAIL, "%s: %s" % (type(e).__name__, e), []
        if status == STATUS_FAIL:
            fails += 1
        elif status == STATUS_SKIP:
            skipped += 1
        rows.append((i, name, status, detail, fail_lines))

    for i, name, status, detail, fail_lines in rows:
        print("DoD %2d  %s %-6s %s" % (i, pad(name, 30), status, detail))
        for line in fail_lines:
            print("        └ %s" % line)

    passed = sum(1 for r in rows if r[2] == STATUS_PASS)
    envs = [r for r in rows if r[2] == STATUS_ENV]
    skipped_items = [r[1] for r in rows if r[2] == STATUS_SKIP]
    tail = "skipped=%d" % skipped if skipped else "skipped=0"
    bad = ("，未通过：" + "、".join(r[1] for r in rows if r[2] == STATUS_FAIL)) if fails else ""
    # 脏树不改变退出码，但必须在结论行留痕：否则"全绿"会被当成"干净树上的全绿"。
    dirty_note = ("｜TREE DIRTY(%d)" % tree["dirty"]) if tree["dirty"] else ""
    if envs:
        # 环境不可用时退出码仍是 2，但**必须把已 FAIL 的项一并列出**：
        # 否则「某项真红 + 某项环境不可用」会被读成"只是环境问题"。
        print("RESULT ENV  %d/%d（%s，环境不可用：%s%s）%s"
              % (passed, len(rows), tail, "、".join(r[1] for r in envs), bad, dirty_note))
        if skipped_items:
            print("NOT-VERIFIED: " + ", ".join(skipped_items))
        return 2
    verdict = "PASS" if not fails else "FAIL"
    print("RESULT %s  %d/%d（%s%s）%s" % (verdict, passed, len(rows), tail, bad, dirty_note))
    if skipped_items:
        # SKIP 不阻断退出码，于是 CI 上"双 SKIP + rc=0"看起来是全绿。
        # 单独一行点名"哪几项没被验证过"：人扫一眼能看见，CI 也能 grep 断言。
        print("NOT-VERIFIED: " + ", ".join(skipped_items))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
