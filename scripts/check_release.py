#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DoD 1–11 发布准入检查：一条命令给出逐项名称与结论（XX-016）。

为什么需要它：
  治理 §8.2 的第 1–9 项原本散在 4 个脚本与若干裸命令里，靠人逐条记得跑。
  分散 + 人工的检查不会被真正执行——E-01/E-02/E-03 三条勘误都证明了这一点。
  这里把它们收敛成一个退出码：非 0 即不许发布。

  第 10、11 项（反样本守卫 / 形态判据）是 I-09 第二阶段追加的，**编号必须排在 9 之后、
  不许插队**：`release.md` 与历史交付说明都按编号引用，改动既有编号等于让所有历史记录指向错的项。
  它们单独存在的理由与上一条同源——**门一直知道产物不达标、产物照样交付**：
  CAPA 反样本能到 `FAIL=21` 还发得出去，不是判据没做，是闸门里没有它。
  两项各自 status、各自 detail，**不许合并成一句「检查通过」**（INV-13）。

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
    0 = 十一项均 PASS 或 SKIP（SKIP 会在 RESULT 行计数）
    1 = 任一项 FAIL（含 DoD 10 的"反样本红错了地方"与 DoD 11 的"教材变红"——那与产物缺陷同责）
    2 = 环境不可用（找不到 Chrome / python3 / bash，run.sh 被锁，
        或 `.build` 清理被 safe-delete 拦截导致本轮结果不可信）
    3 = 用法错误
"""
import filecmp
import io
import json
import os
import re
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
    """DoD 1：5 个示例结构 + 语义校验（走 validate_prd_json.py 自带的 --json 出口）。

    **example-05 走 --profile=delivery，其余 4 个走默认档**（XX-021）。
    为什么必须有一个真实调用者：delivery 档如果只是"能加上"，它就是第二个无人使用的闸门——
    与「规则写了但页面没落地」同型的病。example-05 是本仓库唯一把 任务 → 命令 →
    页面契约 → 转移 UI → 需求交互 全链路补齐的 few-shot，适合当交付档的正例；
    另外 4 个示例补齐是下一条迭代的事，本轮只保证它们默认档不红。
    detail 行带 `profile=delivery:example-05-behavior-model.json`，让"这一档真的被跑了"
    可被 grep 断言。
    """
    files = sorted(
        os.path.join(ROOT, "assets", "examples", f)
        for f in os.listdir(os.path.join(ROOT, "assets", "examples"))
        if f.startswith("example-0") and f.endswith(".json")
    )
    if not files:
        return STATUS_FAIL, "找不到 assets/examples/example-0*.json", []
    n_err = n_warn = 0
    details, fails = [], []
    strict_files = {"example-05-behavior-model.json"}
    for path in files:
        rel = os.path.relpath(path, ROOT)
        base = os.path.basename(path)
        strict = base in strict_files
        argv = [sys.executable, os.path.join(SCRIPTS, "validate_prd_json.py"), "--json"]
        if strict:
            argv.append("--profile=delivery")
        proc = subprocess.run(argv + [path], capture_output=True, text=True)
        try:
            rep = json.loads(proc.stdout)
        except ValueError:
            return STATUS_FAIL, "%s 的 --json 输出无法解析（rc=%d）" % (rel, proc.returncode), first_lines(proc.stderr)
        for item in rep:
            n_err += len(item["errors"])
            n_warn += len(item["warns"])
            for e in item["errors"]:
                fails.append("%s: %s" % (os.path.basename(item["target"]), e))
    details.append("%d/%d errors=%d warnings=%d profile=delivery:%s"
                   % (len(files), len(files), n_err, n_warn, ",".join(sorted(strict_files))))
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


def _run_digest(text):
    """从 `run.sh` 输出里取「失败在哪」——**取末尾的失败行，不取开头**。

    原来用 `first_lines(text, 8)`：取的是**开头 8 行**，而 run.sh 的失败信息在末尾，
    于是 DoD 2 偶发红时一个字都没留下 —— 「没有输出 ≠ 没有失败」的现场版。
    抓含 `FAIL` / `✗` / `CASE` / `Error` 的行，最多 8 行；一个都抓不到就退回最后 5 行。
    """
    rows = [l.rstrip() for l in text.splitlines() if l.strip()]
    hits = [l for l in rows if re.search(r"FAIL|✗|CASE|Error", l)]
    return [l.strip()[:160] for l in (hits[:8] or rows[-5:])]


def _first_bad_case(text):
    """失败 CASE 名。四支判定靠它区分「确定性红」（同一 CASE）与「不确定红」（不同 CASE）。"""
    for line in text.splitlines():
        if not re.search(r"\[FAIL\]|fails=[1-9]|✗", line):
            continue
        m = re.search(r"CASE\s+(\S+)", line)
        if m:
            return m.group(1)
    m = re.search(r"CASE\s+(\S+)", text)
    return m.group(1) if m else "?"


def _two_run_verdict(rc1, rc2, case1, case2):
    """两次回归的判定（纯函数，便于逐支自证）。调用方已排除 SAFE_DELETE 与 rc∈{2,3}。

    | 两次 | 判 | 理由 |
    |---|---|---|
    | 都绿 | PASS | 由调用方在单次就返回，走不到这里 |
    | 都红且 CASE 相同 | FAIL | 确定性红，是真红 |
    | 都红但 CASE 不同 | ENV | 不确定，须人查 |
    | 一绿一红 | ENV | 本轮结果不可信，**不是**"重跑后绿了" |
    """
    if rc2 == 0:
        return STATUS_ENV, "一绿一红，本轮结果不可信（不是「重跑后绿了」）"
    if case1 != case2:
        return STATUS_ENV, "两次红在不同 CASE，须人查"
    return STATUS_FAIL, "两次同一 CASE，确定性红"


def check_regression(_docs, _ph, _gen):
    """DoD 2：容器回归全绿，且 retries 不得超过上限（勘误 E-03）。

    额外守一条**清洁性**判据：`tests/run.sh` 的 `clean_dir` 依赖删除能力，
    删除被拦时它不报错，只是 `.build` 里的旧 profile 留着 → 下一轮脏跑
    （实测同一份代码可跑出 757/0、754/4、666/18）。日志里
    `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]` 就是它留下的痕迹。
    这种红不是"回归失败"而是"本轮结果不可信"，必须判 ENV，不许判 FAIL——
    否则会把环境问题报成代码问题，正是 E-01/E-02/E-03 同型的混淆。

    **偶发红必须留下 CASE 名**（2026-10-26，四支）。`run.sh` 是**确定性断言**：
    确定性测试偶发红只可能是环境噪声，或 CASE 自己非确定（时间/随机/顺序依赖）——
    两种都得先拿到 CASE 名才谈得上修，所以 instrument 不是可选项。
    `rc != 0` 时**再跑一次**，按两次结果判：

    | 两次结果 | 判 | 理由 |
    |---|---|---|
    | 都绿 | PASS | — |
    | 都红且首个失败 CASE 相同 | FAIL | 确定性红，是真红 |
    | 都红但 CASE 不同 | ENV | 不确定，须人查 |
    | 一绿一红 | ENV | 本轮结果不可信，**不是**"重跑后绿了" |
    | 有 SAFE_DELETE 拦截 | ENV | 已有分支，保持 |

    **不许只保留第二次的结果** —— 那是用重跑换绿；两段摘要都必须在 detail 或后续行里。
    """
    bash = shutil.which("bash")
    if not bash:
        return STATUS_ENV, "找不到 bash", []

    def once():
        p = subprocess.run([bash, os.path.join(TESTS, "run.sh")], capture_output=True, text=True)
        t = p.stdout + p.stderr
        tot = [l for l in t.splitlines() if l.startswith("TOTAL ")]
        rty = [l for l in t.splitlines() if l.startswith("RETRIES=")]
        return p.returncode, t, (rty[0] if rty else (tot[0] if tot else "无 TOTAL/RETRIES 行"))

    rc, text, brief = once()
    blocked = [l for l in text.splitlines() if "SAFE_DELETE" in l]
    if blocked:
        note = "`.build` 清理被拦截，本轮结果不可信（%s）" % _safe_delete_note(blocked[0])
        if len(blocked) > 1:
            note += "，共 %d 处" % len(blocked)
        return STATUS_ENV, note, _run_digest(text)[:2]
    if rc == 0:
        return STATUS_PASS, brief, []
    if rc in (2, 3):
        # run.sh 自己的退出码三义：2/3 = 环境或锁，不是回归失败。重跑没有意义。
        return STATUS_ENV, brief + "（run.sh rc=%d，环境或锁）" % rc, _run_digest(text)

    # 红了：再跑一次，**两段都留下**。
    rc2, text2, brief2 = once()
    blocked2 = [l for l in text2.splitlines() if "SAFE_DELETE" in l]
    case1, case2 = _first_bad_case(text), _first_bad_case(text2)
    # rc=0 的那次没有「首个失败」，别硬填一个 CASE 名（读数不支撑结论）。
    head = "第1次 rc=%d 首个失败 %s ｜ 第2次 rc=%d 首个失败 %s" % (
        rc, case1, rc2, case2 if rc2 else "无")
    lines = ([l.strip()[:160] for l in blocked2[:1]]
             + ["RUN1 └ " + x for x in _run_digest(text)]
             + ["RUN2 └ " + x for x in _run_digest(text2)])
    if blocked2:
        return STATUS_ENV, head + " ｜ 第2次 `.build` 清理被拦截，本轮结果不可信", lines
    st, why = _two_run_verdict(rc, rc2, case1, case2)
    extra = ("（%s）" % brief2) if st == STATUS_FAIL else ""
    return st, head + " ｜ " + why + extra, lines


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
    """DoD 7：安装副本同步。本机无副本时 SKIP（CI 恒无），不当作 PASS。

    **自己在副本里跑不算 PASS**：此时 ROOT 与 INSTALL_COPY 指向同一目录，
    `_manifest` 比的是自己跟自己，恒等恒绿。0.5.1 收口时实测到过——
    从 `~/.workbuddy/skills/XX-PRD/scripts/` 运行，打出
    「PASS 43 个文件逐字节一致（HEAD=unversioned）」，看着像证据，
    其实一个字都没比过。与 TREE 同一类病：判据在跑，判的不是它宣称的东西。
    """
    if not os.path.isdir(INSTALL_COPY):
        return STATUS_SKIP, "无 %s（CI 上恒无）" % INSTALL_COPY, []
    if os.path.realpath(ROOT) == os.path.realpath(INSTALL_COPY):
        return STATUS_SKIP, "在安装副本内运行（ROOT 与 INSTALL_COPY 同一目录），无可比对象", []
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


def check_reject_guard(_docs, _ph, _gen):
    """DoD 10：反样本**仍红在登记过的那几条上**（红错地方与不红同责）。

    为什么这条必须在门里：I-09 的立项根因不是"判据没做"，而是**门一直知道产物不达标、
    产物照样交付**。CAPA 反样本能到 `PASS=11 FAIL=21` 还发得出去，就是因为它不在 ITEMS 里。
    规范写了、代码零命中，和"四处 ERROR 无人实现"同型。

    比对面（集合相等）只写在 `tests/check_reject.py` 一处，这里**调用**它的 `main()`，
    不复制比对逻辑 —— 否则两处口径分叉时，门的绿灯会说谎。

    rc 三义必须分开（接线最容易踩的坑：压成一个布尔）：
      0 = `RESULT PASS` 逐条相等        → PASS
      1 = `RESULT FAIL` 集合不符/未登记 → FAIL
      2 = `EnvError`（Chrome 找不到）   → ENV
    混色的后果与 E-01/E-02/E-03 同型：「Chrome 没装」会被读成「反样本没问题」，
    或者反过来把真缺陷藏进"环境问题"。

    detail 不只写 PASS：要能自证比的是哪几页、每档几条
    （`pages=2 逐条相等（15/15 16/16 16/16 12/12）`）——
    只打 PASS 的话，"比了 0 条也算 PASS"这种退化看不出来。
    **不符的那档也要在括号里**（`16/15✗`）：全是相等对的括号会把 FAIL 读成"多了一个通过项"。
    """
    try:
        import check_reject as rej      # 局部 import：既有九项都是三参签名，不为新增项改调用约定
    except Exception as ex:
        # import 失败与"守卫发现反样本变绿"都是 FAIL，但**处置相反**（一个修路径/环境，
        # 一个改产物或改基线）—— detail 必须自己说清，同色就是让读的人自己猜。
        return STATUS_FAIL, "import check_reject 失败：%s: %s" % (type(ex).__name__, ex), []
    try:
        rej.S.find_chrome()             # 自己先判环境，别指望子调用替本项认领 ENV
    except rej.S.EnvError as ex:
        return STATUS_ENV, "Chrome 不可用：%s" % ex, []
    rc, out = silence(rej.main, [])
    pages = [l.split("== page ", 1)[1].strip() for l in out.splitlines() if l.startswith("== page ")]
    # 两种行都要收：相等行是 `1440 期望 15 条 / 实际 15 条`，不符行是
    # `1440 不符（期望 16 条 / 实际 15 条）`。只认前一种时，**恰恰是不符那档被漏掉**，
    # 括号里只剩三对相等数，于是"有 1 档不符"这句结论在读数里找不到依据。
    pairs = []
    for line in out.splitlines():
        m = re.match(r"\s+(\d{4})\s+(?:期望 (\d+) 条 / 实际 (\d+) 条"
                     r"|不符（期望 (\d+) 条 / 实际 (\d+) 条）)", line)
        if m:
            exp, act = (m.group(2), m.group(3)) if m.group(2) is not None else (m.group(4), m.group(5))
            pairs.append((m.group(1), exp, act, exp != act))
    counts = " ".join("%s/%s%s" % (exp, act, "✗" if bad else "") for _vw, exp, act, bad in pairs)
    resline = next((l for l in out.splitlines() if l.startswith("RESULT ")), "")
    if rc == 0:
        if not pairs:
            # rc=0 但一条比对行都没有 —— 「比了 0 条」与「逐条相等」必须不同色。
            return STATUS_FAIL, "rc=0 但没有可解析的逐档比对行（比了 0 条不算通过）", first_lines(out, 4)
        return STATUS_PASS, "pages=%d 逐条相等（%s）｜页 %s" % (len(pages), counts, "、".join(pages)), []
    if rc == 1:
        bad = [l.strip() for l in out.splitlines()
               if ("少红" in l or "多红" in l or "不符" in l or "量具不可信" in l
                   or "没有登记" in l or "找不到反样本" in l or "没有可跑" in l)]
        nbad = sum(1 for p in pairs if p[3])
        detail = "pages=%d 有 %d 档不符（%s）" % (len(pages), nbad, counts or "无可比档")
        return STATUS_FAIL, detail, bad[:8] or first_lines(resline, 1)
    return STATUS_ENV, "check_reject rc=%d：%s" % (rc, resline or "无 RESULT 行"), []


# DoD 11 的目标**写死**（需求单 :884 定的是 example-06）。不参数化、不跟着
# `default_targets()` 走：哪天 example-06 从默认目标里掉出去（`is_work_list_page`
# 认不出它了），门会安静地去判**别的文件**还说 PASS —— 那正是本节要防的假绿。
SHAPE_TARGET = os.path.join(ROOT, "assets", "examples", "example-06-dense-list.json")


def check_shape_gate(_docs, _ph, _gen):
    """DoD 11：形态判据在 `example-06` 上必须绿（`PASS=55 FAIL=0 SKIP=1` 这一组）。

    为什么这条必须在门里：与 DoD 10 同源 —— CAPA 产物 `PASS=11 FAIL=21` 照样交付，
    说明**判据即便做了，也没人替发布签字**。DoD 10 管"反样本还红不红"，这条管"教材还绿不绿"。

    **scope 必须写进 detail**：门只判 example-06，不判其余示例，更不能被读成"全量通过"。
    全量模式（不带参数）不是门的一部分 —— 它对 `example-05` 的 `RESULT INCOMPLETE`
    是**真实答案**（教材只造了 6 行、自称 1286 条，见 XX-046），不该由门来背，
    也不许在这里被"平均"掉。

    `SKIP=1` 那条**必须点名**。理由：`skip_allowed()` 的静态白名单只有 `P8/P13/P17`，
    `P2a/P2b` 靠值里的 `SKIP(行数 N < M，` 条件放行。哪天那 1 条 SKIP 换了**理由**、
    id 还在名单里，行数与结论都已不同 —— 不打出来没人看得见。所以"数得出 SKIP 条数、
    却点不出是哪一条"直接判 FAIL（读数不支撑结论）。

    rc 语义（两种 rc=2 必须分开）：
      0                      → PASS
      1（含 RESULT INCOMPLETE）→ FAIL，detail 带原句
      2 且 `find_chrome()` 抛  → ENV（wrapper 自己先判，不指望子进程）
      2 其它（"没有可跑的产物"）→ **FAIL**：那是产物/路径缺陷，映射成 ENV 就把它藏进"环境问题"，
                                与 E-01/E-02/E-03 同型。
    """
    try:
        import check_ui_shape as su
    except Exception as ex:
        return STATUS_FAIL, "import check_ui_shape 失败：%s: %s" % (type(ex).__name__, ex), []
    try:
        su.find_chrome()
    except su.EnvError as ex:
        return STATUS_ENV, "Chrome 不可用：%s" % ex, []
    if not os.path.isfile(SHAPE_TARGET):
        return STATUS_FAIL, "目标产物不存在：%s（写死的目标不许静默换成别的文件）" % \
            os.path.relpath(SHAPE_TARGET, ROOT), []
    proc = subprocess.run([sys.executable, os.path.join(TESTS, "check_ui_shape.py"), SHAPE_TARGET],
                          cwd=ROOT, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    scope = "fixture=%s rc=%d" % (os.path.basename(SHAPE_TARGET), proc.returncode)
    m = re.search(r"^TOTAL PASS=(\d+) FAIL=(\d+) SKIP=(\d+)", out, re.M)
    if not m:
        # 走的是 main() 的"没有可跑的产物"（rc=2，TOTAL 行之前就返回）或其他未预期路径。
        return STATUS_FAIL, scope + " ｜ 没有判出结论（无 TOTAL 行）", first_lines(out, 6)
    npass, nfail, nskip = (int(x) for x in m.groups())
    resline = next((l for l in out.splitlines() if l.startswith("RESULT")), "")
    ids = re.search(r"SKIP 判据 = \[(.*?)\]", out)
    skip_ids = [x.strip() for x in ids.group(1).split(",") if x.strip()] if ids else []
    titles = {}
    for line in out.splitlines():
        mm = re.match(r"\s+(P\w+)\s+(.+?)\s{2,}现值", line)
        if mm:
            titles[mm.group(1)] = mm.group(2).strip()
    if nskip and not skip_ids:
        return STATUS_FAIL, scope + " ｜ SKIP=%d 但打不出是哪一条（读数不支撑结论）" % nskip, first_lines(out, 6)
    if any(not titles.get(i) for i in skip_ids):
        # 抽不到标题时宁可判 FAIL，也不要打 `P17「?」`：那是"读数不支撑结论"的最小形态。
        return STATUS_FAIL, scope + " ｜ SKIP=%s 但抽不到标题（读数不支撑结论）" % skip_ids, first_lines(out, 6)
    skip_s = ("无 SKIP" if not nskip else
              "%s SKIP=%s" % ("唯一" if nskip == 1 else "共",
                              "、".join("%s「%s」" % (i, titles.get(i, "?")) for i in skip_ids)))
    tail = " ｜ 未判：其余示例（全量模式另跑）"
    if proc.returncode != 0:
        ow = re.search(r"SKIP-OUT-OF-WHITELIST=\[[^\]]*\]", out)
        bad = [l.strip() for l in out.splitlines()
               if re.match(r"\s+P\w+\s", l) and re.search(r"(FAIL|INC!)\s*$", l)]
        detail = "%s PASS=%d FAIL=%d SKIP=%d ｜ 原句：%s%s%s" % (
            scope, npass, nfail, nskip, resline.replace("RESULT ", "", 1) or "无 RESULT 行",
            (" ｜ " + ow.group(0)) if ow else "", tail)
        return STATUS_FAIL, detail, bad[:8] or first_lines(out, 6)
    return STATUS_PASS, "%s PASS=%d FAIL=%d SKIP=%d ｜ %s%s" % (
        scope, npass, nfail, nskip, skip_s, tail), []


# ---------------------------------------------------------------- 骨架

def check_r_group(_docs, _ph, _gen):
    """DoD 12：R1–R4 十五条判定的绿样本 + 逐条造红（`tests/check_r1_r4.py`）。

    为什么独立一条 DoD，不并进 DoD 1：
    DoD 1 判的是「示例不红」，而 R1–R4 需要的输入（`fieldRegistry` / `sourceTerms` /
    `dataModel.relations` / `capabilities[].stage`）在**全部示例里都不存在** —— 在示例上只能得到
    13 条 INCOMPLETE，既证明不了判据能红，也证明不了能绿。而给示例补这些数据会出事：
    示例没有源文档，编一份 `sourceTerms` 再登记等量条目，R1-c 的「计数闭合」就变成恒等式
    （登记 N 条、源点名 N 条，永远相等）—— 那是**把判据变绿**，不是产物变合格。

    所以本项用专用夹具（`tests/fixtures/fixture-r1-r4.json`，自带源清单与登记表）+ 15 个单点变体：
    基线必须 15/15 全 PASS，每个变体必须让**目标判据**由 PASS 变 ERROR，连带变色须逐条登记。
    """
    argv = [sys.executable, os.path.join(ROOT, "tests", "check_r1_r4.py")]
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
    out = (proc.stdout or "") + (proc.stderr or "")
    last = next((l for l in reversed(out.splitlines()) if l.startswith("RESULT")), "")
    base = next((l for l in out.splitlines() if l.startswith("PASS 基线")), "")
    detail = "｜".join(x for x in (base, last) if x) or (last or "无 RESULT 行")
    if proc.returncode != 0:
        bad = [l for l in out.splitlines()
               if l.startswith("FAIL") or l.strip().startswith("·")]
        return STATUS_FAIL, detail, bad[:8] or first_lines(out, 6)
    return STATUS_PASS, detail, []


def check_props_contract_dod(_docs, _ph, _gen):
    """DoD 13：props 契约与 SS-01 三态（references/04 §6.8）。

    为什么要单独一项：SS-01 的 INCOMPLETE 有三种来源，处置完全不同 ——
      ① 契约缺失 / 与容器不同步  = **工具链缺失**，任何档都非 0（不修就没法判）；
      ② 产物里没有节点级 props    = 没有可判输入，不许当 PASS；
      ③ 真正越界                  = 产物 ERROR。
    DoD 1 只看 errors/warns，会把 ① 读成绿；本项把 ① 的退出码、② 的措辞、③ 的点名
    三件事各验一次，缺一件就是「判据在、闸门没装」。

    三步都不改仓库文件：契约缺失那一态靠进程内把常量指到不存在的路径来模拟。
    """
    script = os.path.join(SCRIPTS, "props_contract.py")
    proc = subprocess.run([sys.executable, script, "--check"],
                          capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0:
        return STATUS_FAIL, "契约与容器不同步", first_lines((proc.stdout or "") + (proc.stderr or ""), 5)

    ex3 = os.path.join(ROOT, "assets", "examples", "example-03-nav-tree.json")
    ex6 = os.path.join(ROOT, "assets", "examples", "example-06-dense-list.json")
    vp = os.path.join(SCRIPTS, "validate_prd_json.py")
    p3 = subprocess.run([sys.executable, vp, ex3], capture_output=True, text=True, cwd=ROOT)
    p6 = subprocess.run([sys.executable, vp, ex6], capture_output=True, text=True, cwd=ROOT)
    out6 = (p6.stdout or "") + (p6.stderr or "")
    if p3.returncode != 0:
        return STATUS_FAIL, "绿样本 example-03 被判红", first_lines(p3.stdout or p3.stderr, 5)
    if p6.returncode == 0 or "Alert).props.text" not in out6:
        return STATUS_FAIL, "造红失败：example-06 应点名 Alert.text 且非 0", first_lines(out6, 6)
    if "疑似写错节点" in out6 or "疑似写错节点" in (p3.stdout or ""):
        return STATUS_FAIL, "仍出现「疑似写错节点」（WARN 口径未删）", []

    # 第三态：契约缺失 → INCOMPLETE 且**任何档**非 0（进程内模拟，不动文件）
    import importlib.util
    spec = importlib.util.spec_from_file_location("_vpr", vp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    contract = mod._PROPS_CONTRACT
    unsupported = mod._PROPS_UNSUPPORTED
    mod._PROPS_CONTRACT = os.path.join(ROOT, ".no-such-dir", "props-contract.json")
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mod.run([ex3], as_json=False)
    txt = buf.getvalue()
    if rc == 0 or "INCOMPLETE [SS-01]" not in txt:
        return STATUS_FAIL, "契约缺失时未按「工具链缺失」非 0 退出（rc=%d）" % rc, first_lines(txt, 4)

    # 第四态：**清单哈希**不符 → INCOMPLETE。只校容器会漏掉「改了清单没重生成」，
    # 契约里留一份过期理由表且没有任何门会发现（§6.8.3）。
    mod._PROPS_CONTRACT = contract
    import tempfile
    tmpd = tempfile.mkdtemp(prefix="xx050-")
    try:
        tampered = os.path.join(tmpd, "props-unsupported.json")
        doc = json.load(open(unsupported, encoding="utf-8"))
        doc["entries"][0]["why"] += "（DoD 探针：篡改一个字节）"
        json.dump(doc, open(tampered, "w", encoding="utf-8"), ensure_ascii=False)
        mod._PROPS_UNSUPPORTED = tampered
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc_hash = mod.run([ex3], as_json=False)
        txt_hash = buf.getvalue()
    finally:
        mod._PROPS_UNSUPPORTED = unsupported
        shutil.rmtree(tmpd, ignore_errors=True)
    if rc_hash == 0 or "INCOMPLETE [SS-01]" not in txt_hash:
        return STATUS_FAIL, "清单内容变了却没判 INCOMPLETE（rc=%d）" % rc_hash, first_lines(txt_hash, 4)
    if "不支持清单条目不一致" not in txt_hash:
        return STATUS_FAIL, "清单不符的 INCOMPLETE 没点出是哪几条条目", first_lines(txt_hash, 4)

    # 第五态：R6 —— 声明宽度与渲染对不上必须**说出来**（不是「取值非法」）。
    rep = mod.Report("<DoD13 R6 造红>")
    mod.check_props_contract({"pages": [{"id": "page-dod", "componentTree": {
        "id": "n-dod-dr", "type": "Drawer", "props": {"title": "T", "width": 600}}}]}, rep)
    r6 = " ".join(rep.errors)
    if "声明 600" not in r6 or "渲成 560px" not in r6:
        return STATUS_FAIL, "R6 未对 width:600 判红或消息未写出「声明 600、渲成 560」", first_lines(r6, 3)

    info = next((l.strip(" ·") for l in (p3.stdout or "").splitlines() if "props 消费闭合" in l), "")
    return STATUS_PASS, ("契约同步｜绿样本 03 SS-01 绿｜造红 06 点名 Alert.text｜缺契约 rc=%d｜"
                         "清单篡改 rc=%d｜R6 600→560 已点名｜%s" % (rc, rc_hash, info[:50])), []


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
    ("反样本守卫（红在登记项上）", check_reject_guard),
    ("形态判据（示例 example-06）", check_shape_gate),
    ("需求准确性 R1–R4（绿样本 + 逐条造红）", check_r_group),
    ("props 契约与 SS-01 三态", check_props_contract_dod),
]


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv:
        print("未知参数：%s（本脚本只有 --help）" % " ".join(argv))
        return 3

    # 首行：先声明判的是哪棵树，再谈逐项结论。脏不脏与判据无关，只影响"这次绿算不算数"。
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
