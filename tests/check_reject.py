#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反样本守卫：`assets/examples/reject-01-capa-qms/` 必须**一直红在它该红的那几条上**。

为什么需要这条守卫（与 V8 同源）：

反样本的价值在于「它永远不合格」。一旦某天有人为了让反样本变绿而去改判据
（放宽阈值、把 FAIL 改成 SKIP、或者把它从目标里摘出去），反样本会**静默失去意义**：
它还在仓库里、还能跑，但它证明不了任何事。所以判据自己要有下一条判据管着。

比对面 = **集合相等**，不是「FAIL 数 ≥ N」：
  · 少一条 = 判据被放宽 / 编造了个新分支 / 页面没真判 → 必须解释；
  · 多一条 = 新缺陷或判据变严 → 也必须解释。
  数量相等不蕴含集合相等（这一个教训在本仓库的 `check_docs.EXPECTED_EXAMPLES` 上
  刚被证明过，随后又在 CAPA 的两页上重演：两页 FAIL 数都是 21，红的却各是各的）。

基线**不由本脚本自动写入**：
  `expected-fails.json` 是「人签过字的期望」，改它必须是一次显式的提交动作。
  想看当前实测集，用 `--suggest`（只打 stdout，不落盘）。这样「更新基线」与
  「跑一次看看」不会混成同一个按键 —— 否则它就会变成 I-01 那种「判据在跑，判的不是它宣称的东西」。

用法:
    python3 tests/check_reject.py                 # 逐页比对，逐条打差异
    python3 tests/check_reject.py --verbose       # 附带形态门的完整输出
    python3 tests/check_reject.py --suggest       # 只打实测 FAIL 集（不比对、不写盘）

退出码:
    0 = 每页每个视口的 FAIL 集都与基线逐条相等
    1 = 有差异（少红 / 多红 / 页面没判）
    2 = 环境问题（Chrome / 探针）
"""
import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_ui_shape as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REJECT_DIR = ROOT / "assets" / "examples" / "reject-01-capa-qms"
SAMPLE = REJECT_DIR / "CAPA-PRD.data.json"
BASELINE = REJECT_DIR / "expected-fails.json"


def load_baseline():
    if not BASELINE.exists():
        raise SystemExit("找不到基线 %s —— 反样本没有期望判定就等于没有守"
                         % BASELINE.relative_to(ROOT))
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def measure(chrome, page_id):
    """跑一页两档，返回 {"1440": set(), "1600": set()}。形态门自己的输出被吞掉，由 --verbose 决定要不要看。"""
    buf = io.StringIO()
    with redirect_stdout(buf):
        _p, _f, _s, _sk, fails, inc = S.run_one(chrome, str(SAMPLE), page_id)
    got = {"1440": set(), "1600": set()}
    for item in fails:
        pid, vw = item.rsplit("@", 1)
        got.setdefault(vw, set()).add(pid)
    # INCOMPLETE 不进 FAIL 集，但也**绝不算红**：反样本上出现 INCOMPLETE 说明量具坏了，
    # 那会让某条本该红的判据悄悄不判 —— 集合相等就变成了一句空话。这里把它当成坏结果抛出来。
    if inc:
        got["_incomplete"] = {"%d 条 INCOMPLETE" % inc}
    return got, buf.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser(description="反样本必须保持红（集合相等）")
    ap.add_argument("--verbose", action="store_true", help="打印形态门的完整输出")
    ap.add_argument("--suggest", action="store_true", help="只打实测 FAIL 集，不比对、不写盘")
    a = ap.parse_args(argv)

    try:
        chrome = S.find_chrome()
    except S.EnvError as ex:
        print(str(ex))
        return 2

    if not SAMPLE.exists():
        print("找不到反样本 %s" % SAMPLE)
        return 1

    if a.suggest:
        data = json.loads(SAMPLE.read_text(encoding="utf-8"))
        out = {"measured_by": "tests/check_reject.py --suggest",
               "pages": {}, "counts": {}}
        for page, _kind in S.page_candidates(data):
            pid = page.get("id")
            got, log = measure(chrome, pid)
            if got.get("_incomplete"):
                print("WARN %s 有量具不可信：%s（--suggest 的集合里不含它，别当成「没红」）"
                      % (pid, ", ".join(sorted(got["_incomplete"]))), file=sys.stderr)
            out["pages"][pid] = {vw: sorted(ids) for vw, ids in sorted(got.items())
                                 if vw != "_incomplete"}
            out["counts"][pid] = {vw: len(ids) for vw, ids in sorted(got.items())}
            if a.verbose:
                print(log)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    base = load_baseline()
    pages = base.get("pages") or {}
    if not pages:
        print("基线里一个页面都没有 —— 这不是「全过」，是「没登记」")
        return 1

    bad = 0
    for pid, per_vp in pages.items():
        got, log = measure(chrome, pid)
        if a.verbose:
            print(log)
        print("\n== page %s" % pid)
        if got.get("_incomplete"):
            bad = 1
            print("   量具不可信：%s —— INCOMPLETE 既不是绿也不是红，但它让某条该红的判据没判"
                  % ", ".join(sorted(got["_incomplete"])))
        for vw in sorted(per_vp):
            exp = set(per_vp[vw])
            act = got.get(vw, set())
            miss, extra = sorted(exp - act), sorted(act - exp)
            if not miss and not extra:
                print("   %s 期望 %d 条 / 实际 %d 条 —— 逐条相等"
                      % (vw, len(exp), len(act)))
                continue
            bad = 1
            print("   %s 不符（期望 %d 条 / 实际 %d 条）" % (vw, len(exp), len(act)))
            if miss:
                print("     少红 %d 条（判据被放宽 / 该判的没判）：%s"
                      % (len(miss), ", ".join(miss)))
            if extra:
                print("     多红 %d 条（新缺陷或判据变严）：%s"
                      % (len(extra), ", ".join(extra)))

    print("\n" + "-" * 70)
    if bad:
        print("RESULT FAIL  —— 反样本的红不再是「它该红的那几条」。"
              "先解释差异，再决定改产物还是改基线（改基线 = 一次显式提交）")
        return 1
    print("RESULT PASS  —— 反样本仍红在登记过的那几条上（逐条相等）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
