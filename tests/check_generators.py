#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查示例与生成器是否一致（XX-014）。

做法：把 assets/examples 整体复制到临时目录，在副本里跑 03/04/05 三个生成器，
再与仓库内的 JSON 做**归一化比对**（json.dumps(sort_keys=True)），
避免 CRLF / 缩进 / 键顺序这类格式化差异被误判成漂移。

用法:
    python3 tests/check_generators.py

输出:
    每个用例一行 OK / DRIFT: example-0N
退出码:
    0 = 三个生成器重跑后与仓库 JSON 完全一致
    1 = 存在漂移或生成器执行失败
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXDIR = ROOT / "assets" / "examples"

# (产物 JSON, 生成器, 期望 capabilities 条数, 期望 system:true 处数)
CASES = [
    ("example-03-nav-tree.json", "gen_example03.py", 6, 3),
    ("example-04-master-detail.json", "gen_example04.py", 3, 0),
    ("example-05-behavior-model.json", "gen_example05.py", 10, None),
]


def norm(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def count_system(data):
    n = 0
    for sm in data.get("stateMachines", []):
        for t in sm.get("transitions", []):
            if t.get("system") is True:
                n += 1
    return n


def main():
    bad = 0
    with tempfile.TemporaryDirectory(prefix="xx-prd-gen-") as td:
        tmp = Path(td) / "examples"
        shutil.copytree(EXDIR, tmp)

        for target, gen, want_caps, want_system in CASES:
            proc = subprocess.run(
                [sys.executable, str(tmp / gen)], capture_output=True, text=True
            )
            if proc.returncode != 0:
                print("DRIFT: %s（生成器执行失败 rc=%d）" % (target[:-5], proc.returncode))
                sys.stderr.write(proc.stderr.strip()[-500:] + "\n")
                bad += 1
                continue

            want = json.loads((EXDIR / target).read_text(encoding="utf-8"))
            got = json.loads((tmp / target).read_text(encoding="utf-8"))

            if norm(want) != norm(got):
                print("DRIFT: %s" % target[:-5])
                bad += 1
                continue

            caps = len(got.get("capabilities", []))
            if want_caps is not None and caps != want_caps:
                print("DRIFT: %s（capabilities=%d，期望 %d）" % (target[:-5], caps, want_caps))
                bad += 1
                continue

            if want_system is not None and count_system(got) != want_system:
                print(
                    "DRIFT: %s（system:true=%d，期望 %d）"
                    % (target[:-5], count_system(got), want_system)
                )
                bad += 1
                continue

            extra = ""
            if want_caps is not None:
                extra = " caps=%d" % caps
            if want_system:
                extra += " system=%d" % want_system
            print("OK: %s%s" % (target[:-5], extra))

    if bad:
        print("FAIL generators: %d 个用例漂移" % bad)
        return 1
    print("PASS generators: 3/3 一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
