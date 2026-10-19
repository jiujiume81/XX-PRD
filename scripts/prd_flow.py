#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prd_flow.py — XX-PRD 流程闸门（把 8 阶段与卡点 A/B 落盘，变成可校验的状态）

为什么需要它：
  SKILL.md 里的「卡点」原本只是叙述。叙述没有状态、不可校验，
  模型每轮重新判断「是不是该问了」，判断权在模型手里 —— 于是卡点会被跳过。
  这个脚本把流程写成文件，让「没过闸点」变成一个能返回非 0 退出码的事实。

用法:
    python3 prd_flow.py start  --product "设备巡检管理系统" [--dir .]
    python3 prd_flow.py submit clarify [--dir .] [--note "…"]
    python3 prd_flow.py approve A --by user [--dir .] [--note "…"]
    python3 prd_flow.py guard build|export|write-json [--dir .]
    python3 prd_flow.py status [--dir .]

退出码: 0 = 允许, 1 = 被闸门拦下, 2 = 用法/文件错误
"""
import json
import os
import subprocess
import sys
from datetime import datetime

WF_NAME = "XX-PRD.workflow.json"
HERE = os.path.dirname(os.path.abspath(__file__))

# 阶段定义：id / 名称 / 必须落盘的产物 / 产物最小体量（字节）
STAGES = [
    {"id": "clarify", "name": "① 需求澄清", "need": [
        ("shaping/positioning.md", 120),
        ("shaping/user-flows.md", 120),
        ("shaping/modules.md", 100),
        ("shaping/pages.md", 120),
        ("shaping/open-questions.json", 40),
    ]},
    {"id": "ears", "name": "② 需求分析（EARS + 状态机）", "need": [
        ("shaping/requirements.md", 200),
    ]},
    {"id": "behavior", "name": "③ 行为建模（任务 / 命令 / 页面职责）", "need": [
        ("shaping/behavior.md", 200),
    ]},
    {"id": "plan", "name": "④ 切片计划", "need": [
        ("shaping/slices.json", 80),
    ]},
    {"id": "build", "name": "⑤ 逐片生成原型 + PRD", "need": []},
    {"id": "review", "name": "⑥ 标注评审迭代", "need": []},
    {"id": "finalize", "name": "⑦ 原型定稿", "need": []},
    {"id": "export", "name": "⑧ 生成最终 PRD + 导出", "need": []},
]
STAGE_ID = [s["id"] for s in STAGES]
PLACEHOLDER = ("TODO", "待补充", "待定", "TBD", "…")


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def die(msg, code=2):
    print(f"✗ {msg}")
    sys.exit(code)


def wf_path(d):
    return os.path.join(d, WF_NAME)


def load(d):
    p = wf_path(d)
    if not os.path.exists(p):
        die(f"未找到 {WF_NAME}。先运行：python3 scripts/prd_flow.py start --product \"<产品名>\"", 1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(d, wf):
    wf["updatedAt"] = now()
    with open(wf_path(d), "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)


def stage_rec(wf, sid):
    for s in wf["stages"]:
        if s["id"] == sid:
            return s
    return None


def check_open_questions(path):
    """P0 问题不允许还挂着 open，这是澄清闸门的硬条件。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"open-questions.json 解析失败：{e}"]
    qs = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(qs, list) or not qs:
        return ["open-questions.json 里没有 questions[]，或为空"]
    errs = []
    for q in qs:
        if str(q.get("priority", "")).upper() != "P0":
            continue
        st = str(q.get("status", "open")).lower()
        if st == "open":
            errs.append(f"P0 问题 {q.get('id', '?')} 仍未回答（status=open）")
        elif not str(q.get("answer", "")).strip():
            errs.append(f"P0 问题 {q.get('id', '?')} 标为 {st} 但 answer 为空")
    return errs


def check_artifact(d, rel, min_bytes):
    """产物必须存在、有体量、不是占位符堆出来的。"""
    p = os.path.join(d, rel)
    if not os.path.exists(p):
        return [f"缺少产物 {rel}"]
    size = os.path.getsize(p)
    if size < min_bytes:
        return [f"{rel} 只有 {size} 字节（至少 {min_bytes}），像是空壳"]
    if rel.endswith(".md"):
        with open(p, encoding="utf-8", errors="ignore") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        if lines:
            junk = sum(1 for l in lines if any(k in l for k in PLACEHOLDER))
            if junk / len(lines) > 0.5:
                return [f"{rel} 过半内容是占位符（TODO/待补充），不能算完成"]
    return []


def check_stage(d, stage):
    errs = []
    for rel, mb in stage["need"]:
        errs += check_artifact(d, rel, mb)
        if rel.endswith("open-questions.json") and os.path.exists(os.path.join(d, rel)):
            errs += check_open_questions(os.path.join(d, rel))
    if stage["id"] == "plan" and not errs:
        errs += check_slices(d)
    if stage["id"] == "behavior" and not errs:
        errs += check_behavior(d)
    return errs


def check_slices(d):
    """切片计划交给 prd_slice.py 校验，避免两套标准。"""
    script = os.path.join(HERE, "prd_slice.py")
    plan = os.path.join(d, "shaping/slices.json")
    if not os.path.exists(script):
        return []  # 单独使用本脚本时不强依赖
    r = subprocess.run([sys.executable, script, "plan", plan], capture_output=True, text=True)
    if r.returncode != 0:
        rows = [l.strip()[6:] for l in (r.stdout + r.stderr).splitlines()
                if l.strip().startswith("ERROR")]
        if not rows:
            rows = ["见 prd_slice.py plan 的输出"]
        return [f"切片计划未通过校验：{x}" for x in rows[:6]]
    return []


def check_behavior(d):
    """行为建模的产物里必须真的有三张表，否则等于没建模。"""
    p = os.path.join(d, "shaping/behavior.md")
    with open(p, encoding="utf-8") as f:
        txt = f.read()
    need = {"任务清单": ("任务", "task"), "命令策略": ("命令", "capabilit"), "页面职责": ("职责", "contract")}
    errs = []
    for label, keys in need.items():
        if not any(k in txt.lower() for k in keys):
            errs.append(f"behavior.md 缺少「{label}」部分")
    return errs


def cmd_start(d, product):
    if os.path.exists(wf_path(d)):
        die(f"{WF_NAME} 已存在。要继续请用 submit / status；要重来请先移走旧文件。", 1)
    wf = {
        "schema": "xx-prd-workflow/1",
        "product": product,
        "createdAt": now(),
        "updatedAt": now(),
        "stage": "clarify",
        "stages": [{"id": s["id"], "name": s["name"], "status": "pending",
                    "submittedAt": None, "note": ""} for s in STAGES],
        "gates": {
            "A": {"status": "pending", "approvedAt": None, "by": None, "note": ""},
            "B": {"status": "pending", "approvedAt": None, "by": None, "note": ""},
        },
        "slices": {"planApproved": False, "done": []},
    }
    save(d, wf)
    print(f"✓ 已初始化 {WF_NAME}（产品：{product}）")
    print("  当前阶段：① 需求澄清 —— 本轮只允许产出澄清包并等待用户回答，")
    print("  禁止写 data.json、禁止复制容器。")
    print("  完成 5 份 shaping 产物后：python3 scripts/prd_flow.py submit clarify")


def cmd_submit(d, sid, note):
    if sid not in STAGE_ID:
        die(f"未知阶段 {sid}。可选：{', '.join(STAGE_ID)}")
    wf = load(d)
    idx = STAGE_ID.index(sid)
    for prev in STAGES[:idx]:
        if stage_rec(wf, prev["id"])["status"] != "done":
            die(f"不能跳阶段：先完成并 submit 「{prev['name']}」", 1)

    stage = next(s for s in STAGES if s["id"] == sid)
    errs = check_stage(d, stage)
    if errs:
        print(f"✗ 「{stage['name']}」未通过闸门检查：")
        for e in errs:
            print(f"    - {e}")
        sys.exit(1)

    rec = stage_rec(wf, sid)
    rec["status"] = "done"
    rec["submittedAt"] = now()
    rec["note"] = note or ""

    nxt = STAGES[idx + 1]["id"] if idx + 1 < len(STAGES) else None
    wf["stage"] = nxt or "export"

    save(d, wf)
    print(f"✓ 「{stage['name']}」已提交")

    if sid == "behavior":
        print("\n  已到【卡点 A】。把「需求条目 + 状态机 + 命令策略表 + 页面职责表 + 待澄清问题」")
        print("  交给用户逐条确认。用户点头后执行：")
        print('    python3 scripts/prd_flow.py approve A --by user --note "确认需求与命令策略"')
        print("  未 approve 之前，禁止写任何 pages[] / componentTree。")
    elif sid == "plan":
        print("\n  已到【卡点 B】。把切片清单（含每片体量与验收范围）交给用户确认。")
        print('    python3 scripts/prd_flow.py approve B --by user --note "确认切片顺序"')
    elif nxt:
        print(f"  下一阶段：{next(s['name'] for s in STAGES if s['id'] == nxt)}")


def cmd_approve(d, gate, by, note):
    if gate not in ("A", "B"):
        die("卡点只能是 A 或 B")
    wf = load(d)

    if gate == "A":
        for sid in ("clarify", "ears", "behavior"):
            if stage_rec(wf, sid)["status"] != "done":
                die("卡点 A 前置未完成：clarify / ears / behavior 必须都已 submit", 1)
    else:
        if wf["gates"]["A"]["status"] != "approved":
            die("卡点 A 尚未批准，不能进入卡点 B", 1)
        if stage_rec(wf, "plan")["status"] != "done":
            die("卡点 B 前置未完成：先 submit plan（切片计划）", 1)

    g = wf["gates"][gate]
    g["status"] = "approved"
    g["approvedAt"] = now()
    g["by"] = by or "user"
    g["note"] = note or ""
    if gate == "B":
        wf["slices"]["planApproved"] = True
        wf["stage"] = "build"
    save(d, wf)
    print(f"✓ 卡点 {gate} 已批准（{g['approvedAt']}，by {g['by']}）")
    if gate == "A":
        print("  现在可以进入切片计划：产出 shaping/slices.json 后 submit plan")
    else:
        print("  现在可以逐片生成。每片：生成片段 → prd_slice.py check → merge → 校验器。")


def cmd_guard(d, target):
    wf = load(d)
    A = wf["gates"]["A"]["status"] == "approved"
    B = wf["gates"]["B"]["status"] == "approved"

    if target in ("build", "write-json", "pages"):
        if not A:
            die("被卡点 A 拦下：需求与行为模型尚未确认，禁止生成原型数据。", 1)
        print("✓ 通过：卡点 A 已批准，可以逐片生成")
    elif target == "export":
        if not B:
            die("被卡点 B 拦下：切片计划尚未确认，禁止导出交付物。", 1)
        plan = os.path.join(d, "shaping/slices.json")
        if os.path.exists(plan):
            with open(plan, encoding="utf-8") as f:
                sl = json.load(f).get("slices", [])
            left = [s.get("id") for s in sl if s.get("status") != "done"]
            if left:
                print(f"! 仍有 {len(left)} 个切片未完成：{', '.join(map(str, left))}")
                sys.exit(1)
        print("✓ 通过：卡点 B 已批准，切片全部完成")
    else:
        die(f"未知 guard 目标 {target}。可选：build / write-json / pages / export")


def cmd_status(d):
    wf = load(d)
    print(f"产品：{wf['product']}   更新于 {wf.get('updatedAt', '')}")
    print("-" * 56)
    for s in wf["stages"]:
        mark = "✓" if s["status"] == "done" else "·"
        print(f"  {mark} {s['name']}")
    print("-" * 56)
    for k, g in wf["gates"].items():
        st = "已批准" if g["status"] == "approved" else "待确认"
        print(f"  卡点 {k}: {st}" + (f"（{g['approvedAt']} by {g['by']}）" if g["approvedAt"] else ""))
    nxt = next((s for s in wf["stages"] if s["status"] != "done"), None)
    print("-" * 56)
    print(f"  下一步：{nxt['name'] if nxt else '全部完成'}")
    if nxt:
        need = [r for r, _ in next(s for s in STAGES if s["id"] == nxt["id"])["need"]]
        if need:
            print(f"  需要产物：{', '.join(need)}")
        print(f"  完成后：python3 scripts/prd_flow.py submit {nxt['id']}")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    args = argv[1:]
    d = "."
    note = ""
    product = ""
    by = "user"
    pos = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--dir":
            d = args[i + 1]; i += 2
        elif a == "--note":
            note = args[i + 1]; i += 2
        elif a == "--product":
            product = args[i + 1]; i += 2
        elif a == "--by":
            by = args[i + 1]; i += 2
        else:
            pos.append(a); i += 1
    d = os.path.abspath(d)

    if cmd == "start":
        if not product:
            die("start 需要 --product \"<产品名>\"")
        cmd_start(d, product)
    elif cmd == "submit":
        if not pos:
            die("submit 需要阶段 id")
        cmd_submit(d, pos[0], note)
    elif cmd == "approve":
        if not pos:
            die("approve 需要 A 或 B")
        cmd_approve(d, pos[0].upper(), by, note)
    elif cmd == "guard":
        if not pos:
            die("guard 需要目标：build / export")
        cmd_guard(d, pos[0])
    elif cmd == "status":
        cmd_status(d)
    else:
        die(f"未知命令 {cmd}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
