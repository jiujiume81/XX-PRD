#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付档「需求/转移 → 页面交互」绑定的集合断言（XX-019 / XX-020）。

为什么要有这个脚本，而不是在验收里写 `count == 17`：
  「会变的量不得写成常量」（G7）。期待值必须**从产物里推**，机器算出来的集合
  和校验器报出来的集合逐个比对；写死数字的断言，在产物一变时要么假绿（数字凑上）
  要么假红（人改期望值），两种都不算证据。

四条断言：
  A. 集合相等：{XX-019 报出的转移 id} == {非 system 且 ui 缺失的转移 id}
  B. 集合包含（--snapshot）：{人工审计的 8 条真缺按钮} ⊆ A 的集合
  C. 集合相等：{XX-020 报出的需求 id} == {ui 缺失的需求 id}
  D. 集合包含（--snapshot）：{人工审计的 3 条真缺口} ⊆ C 的集合

A/C 是机器判据，任何 PRD 都能跑；B/D 是人工审计快照，只对 2026-10-21 的
QMS 来料检测产物成立（见 FB-20261021-01 §五），别的产物跑会假红，所以要显式开启。

**id 从报错文本里抓**，不从 validate 的内部对象里抓：这样同时验证了「报错文本能被
grep 出 id」。格式一变，抓出来是空集，A 立刻红——比格式悄悄变了、断言还绿着强。

用法:
    python3 tests/check_ui_binding.py <prd.data.json>
    python3 tests/check_ui_binding.py <prd.data.json> --snapshot

退出码: 0 = 四条断言全过, 1 = 有断言失败, 2 = 用法错误 / 文件不存在
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import validate_prd_json as V  # noqa: E402

# 2026-10-21 人工审计快照（FB-20261021-01 §五）：这 8 条转移在 QMS 产物里
# 页面上根本没有对应按钮；3 条需求补上声明后仍找不到入口。
# 它们是**人工结论**，不是机器判据——所以写成子集，而不是相等。
SNAPSHOT_TRANSITIONS = ["nt-3", "it-4", "it-5", "st-2", "st-3", "st-4", "st-5", "nr-3"]
SNAPSHOT_REQUIREMENTS = ["REQ-ITK-006", "REQ-ITK-007", "REQ-NTC-004"]

RE_TRANSITION = re.compile(r"\[XX-019\] 转移 ([A-Za-z0-9_-]+)")
RE_REQUIREMENT = re.compile(r"\[XX-020\] 需求 ([A-Za-z0-9_-]+)")


def check(name, got, want, mode):
    """mode='eq' 逐个比对（保留重复），mode='subset' 判包含。"""
    if mode == "eq":
        ok = got == want
        expr = "=="
    else:
        missing = [x for x in want if x not in got]
        ok = not missing
        expr = "⊇"
    print("%s  %s  %s（got=%d, want=%d）" % ("PASS" if ok else "FAIL", name, expr,
                                             len(got), len(want)))
    if not ok:
        if mode == "eq":
            only_got = [x for x in got if x not in want]
            only_want = [x for x in want if x not in got]
            if only_got:
                print("        多报：" + ", ".join(sorted(only_got)))
            if only_want:
                print("        漏报：" + ", ".join(sorted(only_want)))
        else:
            print("        缺失：" + ", ".join(sorted(x for x in want if x not in got)))
    return ok


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    path = argv[0]
    snapshot = "--snapshot" in argv[1:]
    if not os.path.exists(path):
        print("文件不存在：%s" % path)
        return 2

    data = json.load(open(path, encoding="utf-8"))
    rep = V.Report(path, "delivery")
    V.validate(data, rep, strict=True)

    got_t = [m.group(1) for e in rep.errors for m in [RE_TRANSITION.search(e)] if m]
    got_r = [m.group(1) for e in rep.errors for m in [RE_REQUIREMENT.search(e)] if m]

    # 期望值从产物推导（不是常量）。用 list 保留重复：it-6 / it-7 的 trigger 一模一样，
    # 若用 set() 去重，A 会少一条而仍然「相等」——那是判据自己在骗自己。
    want_t = [t.get("id") for sm in data.get("stateMachines") or []
              for t in sm.get("transitions") or []
              if not V.transition_is_system(t) and "ui" not in t]
    want_r = [r.get("id") for r in data.get("requirements") or [] if "ui" not in r]

    print("产物：%s" % path)
    print("转移 %d 条（非 system 且缺 ui：%d），需求 %d 条（缺 ui：%d）"
          % (sum(len(sm.get("transitions") or []) for sm in data.get("stateMachines") or []),
             len(want_t), len(data.get("requirements") or []), len(want_r)))

    # 产物自身的重复缺陷提示（不影响判据，但别让它悄悄被 set 吃掉）
    seen, dup = {}, []
    for sm in data.get("stateMachines") or []:
        for t in sm.get("transitions") or []:
            key = t.get("trigger")
            if key and key in seen:
                dup.append("%s / %s 的 trigger 相同：「%s」" % (seen[key], t.get("id"), key))
            seen.setdefault(key, t.get("id"))
    for d in dup:
        print("注意  %s（产物缺陷，用 list 比对才不会漏计数）" % d)

    ok = True
    ok &= check("A 集合相等", sorted(got_t), sorted(want_t), "eq")
    if snapshot:
        ok &= check("B 集合包含", got_t, SNAPSHOT_TRANSITIONS, "subset")
    ok &= check("C 集合相等", sorted(got_r), sorted(want_r), "eq")
    if snapshot:
        ok &= check("D 集合包含", got_r, SNAPSHOT_REQUIREMENTS, "subset")
    if not snapshot:
        print("跳过  B/D（人工审计快照只对 QMS 2026-10-21 产物成立，需 --snapshot 显式开启）")

    print("RESULT %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
