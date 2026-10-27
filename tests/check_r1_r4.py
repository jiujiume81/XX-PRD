#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R1–R4 造红自证（references/13-requirements-accuracy.md）。

为什么单独一个脚本、不塞进 check_ui_shape：
R1–R4 是**纯 JSON 判定**（引用解析 / 计数闭合 / 集合比较），不需要 Chrome。
放进形态门会让「不需要浏览器就能判的东西」被迫排在一个浏览器后面，且它跑在
`--selfcheck` 的注入框架里会被 CSS 注入机制带偏（R 组没有 CSS 可注入）。

判定方式：
  ① 基线：`tests/fixtures/fixture-r1-r4.json` 上 15 条必须**全 PASS**（有绿点才谈得上「能红」）；
  ② 逐条：每个变体只改一个字段 → 目标判据必须由 PASS 变成 ERROR/INCOMPLETE；
  ③ 连带：非目标判据变色必须逐条写在 `allow` 里并给理由，否则判失败。
     —— 允许连带不是放水：改 actor 必然同时影响 R2-c / R4-b 这类共享输入，硬要求"只红一条"
     会逼人把变体制成假数据。

用法：
    python3 tests/check_r1_r4.py            # 逐条跑一遍
    python3 tests/check_r1_r4.py -v         # 同时打印每个变体的全组状态
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import validate_prd_json as V  # noqa: E402

FIX = os.path.join(HERE, "fixtures", "fixture-r1-r4.json")


def _run(doc):
    """用交付档跑（strict=True 让 R4-d 的 warn_only 升 ERROR —— 否则它永远不红）。"""
    rep = V.Report(FIX, "delivery")
    V.validate(doc, rep, strict=True)
    return dict(rep.r_group), rep


# ---------------- 变体定义 ----------------
def _set_fr(i, **kv):
    def f(d):
        d["fieldRegistry"][i].update(kv)
    return f


def _set_cap(i, **kv):
    def f(d):
        d["capabilities"][i].update(kv)
    return f


def _set_owns(page_i, owns):
    def f(d):
        d["pages"][page_i]["contract"]["owns"] = owns
    return f


def _add_stage_col(d):
    """按 id 找子表节点再加列 —— 不按下标硬编码：夹具一改结构，下标路径就断。"""
    def find(n):
        if isinstance(n, dict):
            if n.get("id") == "n-fx-md-detail":
                return n
            for c in (n.get("children") or []):
                r = find(c)
                if r:
                    return r
        return None

    node = find(d["pages"][0]["componentTree"])
    node["props"]["columns"].append({"title": "阶段", "dataIndex": "stage", "width": 80})


CASES = [
    # rid, 说明, 改动, 允许连带变色的 rid（写清理由）
    ("R1-a", "把 f-01 的 block 指到不存在的节点",
     _set_fr(0, block="n-does-not-exist"), []),
    ("R1-b", "把 f-01 的 block 指到存在、但文本里没有「任务单号」的按钮节点",
     _set_fr(0, block="n-fx-btn-submit"), []),
    ("R1-c", "源点名词清单加一条「退货原因」，登记表不加",
     lambda d: d["sourceTerms"].append("退货原因"), []),
    ("R1-d", "把 f-01 的 scope 改 out 但不写 reason",
     _set_fr(0, scope="out"), []),
    ("R2", "源清单加一条同时含「明细」「两种」的词，触发词命中 2 而裁决仍是 1",
     lambda d: d["sourceTerms"].append("措施明细（两种类型）"), []),
    ("R2-a", "把 f-02 也标 oneToMany:true，但 relations 里仍只有 1 条 1:N",
     _set_fr(1, oneToMany=True), ["R2"]),
    ("R2-b", "把子实体状态改为主实体的同一集合（子集 → 投影）",
     lambda d: d["stateMachines"][1].update(
         states=[{"id": "open", "name": "进行中", "type": "normal"},
                 {"id": "closed", "name": "已关闭", "type": "success"}]),
     ["R4-c"]),
    ("R2-c", "把子实体两条命令的 actor 都改成与父实体相同",
     lambda d: (d["capabilities"][0].update(actor=["u-exec"]),
                d["capabilities"][1].update(actor=["u-exec"])), ["R4-b"]),
    ("R2-d", "给子表加一列「阶段」（两类单据被合并的典型证据）",
     _add_stage_col, []),
    ("R3", "把 page-verify 的 contract.actor 换成一个不存在的角色",
     lambda d: d["pages"][1]["contract"].update(actor=["u-qa-x"]), []),
    ("R3-b", "清空 page-task-hub 的 contract.owns（提交命令无处安放）",
     _set_owns(0, []), []),
    ("R4-a", "删掉 cap-m-verify 的 stage（验证环节消失）",
     lambda d: d["capabilities"][1].pop("stage", None), []),
    ("R4-b", "把 cap-m-verify 的 actor 改成与 submit 相同，且不申请 sameActorOk",
     _set_cap(1, actor=["u-exec"]), ["R2-c"]),
    ("R4-c", "把 cap-m-verify 的 from 改成不含 submit.to 的状态",
     _set_cap(1, **{"from": ["done"]}), []),
    ("R4-d", "清空 cap-m-verify 的 effects，且状态机没有 parentEffect",
     _set_cap(1, effects=[]), []),
]


def main():
    verbose = "-v" in sys.argv
    base_doc = json.load(open(FIX, encoding="utf-8"))
    base, _ = _run(copy.deepcopy(base_doc))

    fails = []
    if any(s != "PASS" for s in base.values()):
        bad = {k: v for k, v in base.items() if v != "PASS"}
        fails.append(f"基线不是全 PASS：{bad}")
        print(f"FAIL 基线：{len(base) - len(bad)}/{len(base)} PASS —— {bad}")
    else:
        print(f"PASS 基线：{len(base)} 条全 PASS（{len(base)}/{len(base)}）")

    ok = 0
    for rid, why, mutate, allow in CASES:
        doc = copy.deepcopy(base_doc)
        mutate(doc)
        try:
            got, rep = _run(doc)
        except Exception as e:  # 变体让校验器崩了，也是失败
            fails.append(f"{rid}：变体使校验器异常 {e}")
            print(f"FAIL {rid} 校验器异常：{e}")
            continue
        tgt = got.get(rid)
        changed = {k for k in got if got[k] != base.get(k)}
        unexpected = changed - {rid} - set(allow)
        if tgt == "PASS":
            fails.append(f"{rid} 未变红（仍是 PASS）")
            print(f"FAIL {rid} 未变红 —— {why}")
        elif unexpected:
            fails.append(f"{rid} 连带打到未登记的 {sorted(unexpected)}")
            print(f"FAIL {rid} 连带越界：{sorted(unexpected)}（{why}）")
        else:
            ok += 1
            extra = f"（连带 {sorted(changed - {rid})} 已登记）" if changed - {rid} else ""
            print(f"PASS {rid} → {tgt}{extra}")
        if verbose:
            print(f"     全组：{json.dumps(got, ensure_ascii=False)}")

    print("=" * 68)
    if fails:
        for f in fails:
            print(f"  · {f}")
        print(f"RESULT FAIL —— {ok}/{len(CASES)} 个变体按预期变红")
        return 1
    print(f"RESULT PASS —— {ok}/{len(CASES)} 个变体逐条按预期变红，"
          f"基线 {len(base)}/{len(base)} 全 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
