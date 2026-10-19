#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prd_slice.py — 把「一次性生成整个系统」拆成「垂直切片逐片交付」

用法:
    python3 prd_slice.py plan <slices.json>              # 校验切片计划
    python3 prd_slice.py check <slice-fragment.json> [--plan slices.json]
    python3 prd_slice.py merge <f1.json> <f2.json> ... -o <data.json> [--plan slices.json]
    python3 prd_slice.py done <sliceId> --plan <slices.json>   # 该片验收通过后标记完成

切片单位是「用户故事最小闭环」：一个角色、一个目标、一条主路径、
一组只属于它的命令与状态转移，能独立验收。功能闭环（模块级）通常跨角色跨页面，
作为切片单位太大，只当上限参考。

退出码: 0 = 通过, 1 = 有问题, 2 = 用法错误
"""
import json
import os
import sys

# 单片上限：超过就必须再切，否则单轮输出过大、质量会掉
MAX_PAGES = 4
MAX_CAPS = 6
MAX_REQ = 12
MAX_NODES = 80

FIELDS = ("title", "actor", "goal", "task", "pages", "capabilities", "acceptance")
LIST_KEYS = ("pages", "requirements", "capabilities", "stateMachines", "tasks",
             "users", "modules", "components", "openQuestions", "annotations", "boardPlan")


def die(msg, code=2):
    print(f"✗ {msg}")
    sys.exit(code)


def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        die(f"{p} 解析失败：{e}")


def count_nodes(obj):
    """按 id 前缀 n- 数组件节点，避开 toolbar 属性式条目。"""
    n = 0
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if str(cur.get("id", "")).startswith("n-"):
                n += 1
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return n


# ---------------------------------------------------------------- plan

def cmd_plan(path):
    data = load(path)
    if not isinstance(data, dict):
        die("切片计划必须是对象")
    slices = data.get("slices")
    if not isinstance(slices, list) or not slices:
        die("切片计划缺少非空的 slices[]")

    errs, warns, infos = [], [], []
    seen_id, seen_page, seen_cap = {}, {}, {}

    for s in slices:
        sid = s.get("id", "?")
        if sid in seen_id:
            errs.append(f"切片 id 重复：{sid}")
        seen_id[sid] = s
        if not str(sid).startswith("s-"):
            warns.append(f"切片 {sid} 的 id 建议用 s- 前缀")

        for f in FIELDS:
            v = s.get(f)
            if v in (None, "", [], {}):
                errs.append(f"切片 {sid} 缺少字段 {f}")

        pages = s.get("pages") or []
        caps = s.get("capabilities") or []
        acc = s.get("acceptance") or []

        if len(pages) > MAX_PAGES:
            errs.append(f"切片 {sid} 有 {len(pages)} 个页面 > 上限 {MAX_PAGES}，请继续拆")
        if len(caps) > MAX_CAPS:
            errs.append(f"切片 {sid} 有 {len(caps)} 条命令 > 上限 {MAX_CAPS}")
        if len(acc) > MAX_REQ:
            errs.append(f"切片 {sid} 有 {len(acc)} 条验收 > 上限 {MAX_REQ}")

        est = s.get("estimate") or {}
        if est.get("nodes") and est["nodes"] > MAX_NODES:
            errs.append(f"切片 {sid} 预估 {est['nodes']} 个节点 > 上限 {MAX_NODES}")

        for p in pages:
            if p in seen_page:
                errs.append(f"页面 {p} 同时出现在 {seen_page[p]} 与 {sid}：一个页面只能属于一个切片")
            seen_page[p] = sid
        for c in caps:
            if c in seen_cap:
                errs.append(f"命令 {c} 同时出现在 {seen_cap[c]} 与 {sid}：一条命令只有一个主页面")
            seen_cap[c] = sid

        actor = s.get("actor")
        if isinstance(actor, list) and len(actor) > 1:
            warns.append(f"切片 {sid} 有多个角色 {actor}：可能不是单个用户故事，考虑拆开")

    # 依赖：存在性 + 环
    ids = set(seen_id)
    for sid, s in seen_id.items():
        for dep in s.get("dependsOn") or []:
            if dep not in ids:
                errs.append(f"切片 {sid} 依赖不存在的切片 {dep}")
            if dep == sid:
                errs.append(f"切片 {sid} 依赖自己")
    order = topo(seen_id, errs)

    total_pages = sum(len(s.get("pages") or []) for s in slices)
    total_req = sum(len(s.get("acceptance") or []) for s in slices)
    infos.append(f"{len(slices)} 个切片 / {total_pages} 个页面 / {total_req} 条验收")
    if order:
        infos.append("建议执行顺序：" + " → ".join(order))

    report(errs, warns, infos, "切片计划")
    return 0 if not errs else 1


def topo(seen, errs):
    """返回拓扑序；有环则记 ERROR 并返回空。"""
    indeg = {k: 0 for k in seen}
    out = {k: [] for k in seen}
    for k, s in seen.items():
        for dep in s.get("dependsOn") or []:
            if dep in seen:
                out[dep].append(k)
                indeg[k] += 1
    q = [k for k, v in indeg.items() if v == 0]
    order = []
    while q:
        cur = q.pop(0)
        order.append(cur)
        for nx in out[cur]:
            indeg[nx] -= 1
            if indeg[nx] == 0:
                q.append(nx)
    if len(order) != len(seen):
        errs.append("切片依赖存在环，无法排出执行顺序")
        return []
    return order


# ---------------------------------------------------------------- check

def cmd_check(path, plan_path=None):
    frag = load(path)
    if not isinstance(frag, dict):
        die("切片片段必须是对象")
    sid = frag.get("sliceId")
    errs, warns, infos = [], [], []

    pages = frag.get("pages") or []
    reqs = frag.get("requirements") or []
    caps = frag.get("capabilities") or []
    nodes = count_nodes(frag)

    if not sid:
        errs.append("片段缺少 sliceId")
    if not pages:
        errs.append("片段没有 pages[]")
    if len(pages) > MAX_PAGES:
        errs.append(f"片段有 {len(pages)} 个页面 > 上限 {MAX_PAGES}")
    if len(reqs) > MAX_REQ:
        errs.append(f"片段有 {len(reqs)} 条需求 > 上限 {MAX_REQ}")
    if len(caps) > MAX_CAPS:
        errs.append(f"片段有 {len(caps)} 条命令 > 上限 {MAX_CAPS}")
    if nodes > MAX_NODES:
        errs.append(f"片段有 {nodes} 个组件节点 > 上限 {MAX_NODES}（当前 {nodes}）")

    # 每页必须能独立渲染：至少一个状态带 vars 默认值
    for p in pages:
        pid = p.get("id", "?")
        states = p.get("states") or []
        has_default = any(isinstance(s, dict) and isinstance(s.get("vars"), dict) and s["vars"] for s in states)
        if not has_default:
            errs.append(f"页面 {pid} 没有带默认 vars 的状态，单独打开会渲染不出来")
        if len(states) < 4 and not p.get("notApplicableStates"):
            errs.append(f"页面 {pid} 状态不足 4 个且未声明 notApplicableStates")
        ctr = p.get("contract")
        if not ctr:
            errs.append(f"页面 {pid} 缺少 contract（页面职责契约）")
        else:
            # actor 写成字符串会被容器按字符遍历，这里提前拦住
            if isinstance(ctr.get("actor"), str):
                errs.append(f"页面 {pid} contract.actor 必须是数组（[user id]），不能写成字符串")
            sb = ctr.get("submitBoundary")
            if sb and sb not in ("single", "staged", "none"):
                errs.append(f"页面 {pid} contract.submitBoundary 只能是 single / staged / none，当前 {sb!r}")
            if not ctr.get("owns"):
                errs.append(f"页面 {pid} contract.owns 为空：这个页面到底发起哪条命令？")
        if not any(isinstance(x, dict) and x.get("type") == "flow" for x in (p.get("prd") or {}).get("sections") or []):
            warns.append(f"页面 {pid} 没有 type:\"flow\" 的流程图小节")

    # 验收必须覆盖非法路径：只有成功路径等于只写了一半
    for r in reqs:
        acc = r.get("acceptance") or []
        if len(acc) < 2:
            errs.append(f"需求 {r.get('id', '?')} 的 acceptance 少于 2 条（需含正常路径与边界/异常）")

    # 片段声明的命令必须都在计划里属于本片
    if plan_path:
        plan = load(plan_path)
        mine = next((s for s in plan.get("slices", []) if s.get("id") == sid), None)
        if not mine:
            errs.append(f"计划里找不到切片 {sid}")
        else:
            allowed = set(mine.get("capabilities") or [])
            extra = [c.get("id") for c in caps if c.get("id") not in allowed]
            if extra:
                errs.append(f"片段里有不属于本片的命令：{', '.join(map(str, extra))}")
            own = set()
            for p in pages:
                own |= set((p.get("contract") or {}).get("owns") or [])
            cross = [c for c in own if c not in allowed]
            if cross:
                errs.append(f"contract.owns 出现别的切片的命令：{', '.join(map(str, cross))}")

    infos.append(f"片段 {sid}：{len(pages)} 页 / {len(reqs)} 需求 / {len(caps)} 命令 / {nodes} 节点")
    report(errs, warns, infos, "切片片段")
    return 0 if not errs else 1


# ---------------------------------------------------------------- merge

def merge_list(dst, src, key, errs, lname, union_keys=()):
    """按 id 合并；union_keys 里的列表字段取并集（同一模块跨多片时 pageIds 会各写一部分）。"""
    index = {x.get(key): x for x in dst if isinstance(x, dict)}
    for x in src:
        if not isinstance(x, dict) or key not in x:
            errs.append(f"{lname} 里有缺 {key} 的条目")
            continue
        k = x[key]
        if k not in index:
            dst.append(x)
            index[k] = x
            continue

        tgt = index[k]
        if json.dumps(tgt, sort_keys=True, ensure_ascii=False) == json.dumps(x, sort_keys=True, ensure_ascii=False):
            continue

        merged_any = False
        for uk in union_keys:
            if isinstance(tgt.get(uk), list) and isinstance(x.get(uk), list):
                for v in x[uk]:
                    if v not in tgt[uk]:
                        tgt[uk].append(v)
                merged_any = True
        if merged_any:
            a = {kk: vv for kk, vv in tgt.items() if kk not in union_keys}
            b = {kk: vv for kk, vv in x.items() if kk not in union_keys}
            if json.dumps(a, sort_keys=True, ensure_ascii=False) != json.dumps(b, sort_keys=True, ensure_ascii=False):
                errs.append(f"{lname} id 冲突：{k} 除 {','.join(union_keys)} 外字段不一致")
        else:
            errs.append(f"{lname} id 冲突：{k} 在两片里内容不同")


def merge_data_model(dst, src, errs):
    for ek in ("entities", "relations", "derived"):
        d = dst.setdefault(ek, [])
        index = {x.get("id") or x.get("name"): x for x in d if isinstance(x, dict)}
        for x in src.get(ek, []) or []:
            k = x.get("id") or x.get("name")
            if k not in index:
                d.append(x); index[k] = x
                continue
            tgt = index[k]
            if ek == "entities":
                tf = {f.get("name"): f for f in tgt.get("fields", []) if isinstance(f, dict)}
                for f in x.get("fields", []) or []:
                    fn = f.get("name")
                    if fn in tf:
                        if tf[fn].get("type") != f.get("type"):
                            errs.append(f"字段类型冲突：{k}.{fn} 在前片是 {tf[fn].get('type')}，本片是 {f.get('type')}")
                    else:
                        tgt.setdefault("fields", []).append(f); tf[fn] = f
            elif json.dumps(tgt, sort_keys=True) != json.dumps(x, sort_keys=True):
                errs.append(f"dataModel.{ek} 冲突：{k}")


def cmd_merge(files, out, plan_path=None):
    if not files:
        die("merge 需要至少一个片段")
    merged = {"schemaVersion": "1.1", "slices": []}
    errs, infos = [], []
    dm = {}

    for f in files:
        frag = load(f)
        sid = frag.get("sliceId", os.path.basename(f))
        sub = []
        cmd_check_silent(f, plan_path, sub)
        errs += [f"[{sid}] {e}" for e in sub]
        merged["slices"].append(sid)
        for k, v in frag.items():
            if k == "sliceId":
                continue
            if k == "dataModel":
                merge_data_model(dm, v or {}, errs)
            elif k in LIST_KEYS and isinstance(v, list):
                merged.setdefault(k, [])
                merge_list(merged[k], v, "id", errs, k,
                           union_keys=("pageIds",) if k == "modules" else ())
            elif k in ("meta", "product", "schemaVersion"):
                if k in merged and merged[k] != v:
                    errs.append(f"顶层字段 {k} 在多个片段里不一致")
                else:
                    merged[k] = v
            else:
                merged.setdefault(k, v)

    if dm:
        merged["dataModel"] = dm

    if errs:
        report(errs, [], infos, "合并")
        return 1

    with open(out, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2)
    infos.append(f"已合并 {len(files)} 个片段 → {out}")
    infos.append(f"页面 {len(merged.get('pages', []))} / 需求 {len(merged.get('requirements', []))} "
                 f"/ 命令 {len(merged.get('capabilities', []))} / 节点 {count_nodes(merged)}")
    report([], [], infos, "合并")
    print("  下一步：python3 scripts/validate_prd_json.py " + out)
    return 0


def cmd_check_silent(path, plan_path, sink):
    """给 merge 复用：把 check 的错误收集起来而不打印。"""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            rc = cmd_check(path, plan_path)
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1
    if rc != 0:
        for line in buf.getvalue().splitlines():
            s = line.strip()
            if s.startswith("- "):
                sink.append(s[2:])


# ---------------------------------------------------------------- done

def cmd_done(sid, plan_path, out=None, merge_files=None):
    """把切片标记为完成；只有 check 通过的片段才算数。"""
    if not plan_path:
        die("done 需要 --plan <slices.json>")
    plan = load(plan_path)
    rows = plan.get("slices") or []
    target = next((s for s in rows if s.get("id") == sid), None)
    if not target:
        die(f"计划里没有切片 {sid}")
    if out and os.path.exists(out):
        print(f"  · 已合并产物：{out}")
    target["status"] = "done"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    left = [s.get("id") for s in rows if s.get("status") != "done"]
    print(f"✓ 切片 {sid} 已标记完成；剩余 {len(left)} 个：{', '.join(map(str, left)) or '无'}")
    return 0


# ---------------------------------------------------------------- report

def report(errs, warns, infos, title):
    print("=" * 60)
    print(f"{title}")
    for i in infos:
        print(f"  · {i}")
    for w in warns:
        print(f"  WARN  {w}")
    for e in errs:
        print(f"  ERROR {e}")
    print(f"  => {'FAIL' if errs else 'PASS'}  (errors={len(errs)}, warnings={len(warns)})")
    print("=" * 60)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    plan_path = None
    out = None
    pos = []
    i = 0
    while i < len(rest):
        if rest[i] == "--plan":
            plan_path = rest[i + 1]; i += 2
        elif rest[i] == "-o":
            out = rest[i + 1]; i += 2
        else:
            pos.append(rest[i]); i += 1

    if cmd == "plan":
        if not pos:
            die("plan 需要切片计划路径")
        return cmd_plan(pos[0])
    if cmd == "check":
        if not pos:
            die("check 需要切片片段路径")
        return cmd_check(pos[0], plan_path)
    if cmd == "merge":
        if not out:
            die("merge 需要 -o <输出路径>")
        return cmd_merge(pos, out, plan_path)
    if cmd == "done":
        if not pos:
            die("done 需要切片 id")
        return cmd_done(pos[0], plan_path, out)
    die(f"未知命令 {cmd}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
