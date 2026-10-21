#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G1a/G1b/G2/G3/G4a/G4b/G4c：几何判据（headless Chrome + 注入探针）。

规格见 项目治理/迭代/I-05-UI审美方案.md §6.3/§6.4/§6.5。三条纪律先写在最前面：

1. **判据用相对量，不写死像素和个数。** `.actions` 的直接子元素结构会被 B-1 的分组改掉，
   所以目标集合按选择器枚举（button/select/input/textarea/a[href]/[role=button]），不按"数一眼"。
2. **三个数分开打**：目标 / 可见 / 豁免。合并成一个数之后，没人分得清"少了一个按钮"
   （目标变小）和"多了一个隐藏元素"（豁免变大）—— 这两种故障的处置完全相反。
3. **量尺寸去 1600，判裁切回 1080。** 1080 档量到的是 flex 收缩之后的布局：
   实测 #stateSelect@1080 = 34px（文字已截断）而 @1600 = 190px，一个 34px 的下拉框
   在 `right <= clientWidth` 下完全合格。用它证明"设计放得下"是量错了对象。

用法:
    python3 tests/check_layout.py              # 全档跑一遍
    python3 tests/check_layout.py --selfcheck  # G-2 自证：注入缺陷必须红在正确的判据上
    python3 tests/check_layout.py --keep       # 保留临时 HTML 便于手工核对
    CHROME=/path/to/chrome python3 tests/check_layout.py

退出码:
    0 = 七个判据全 PASS
    1 = 有违规
    2 = 环境问题（找不到 Chrome / 探针没产出 / ENV 守卫不成立）

口径变更
    2026-10-21 首版。G1 拆 a/b 两档：G1a@1600 判"放得下"，G1b@1080 是 B-1 的验收目标档
    （今天红 2：btnDevkit、btnReset）。B-1 落地后 1080 的失效形态会从"裁出视口"变成
    "换行到第二行"，届时 violation(1080) 归 0 而纵向多出 14px —— 那是口径变更点，
    必须重定基线并在本节留一行记录，不能只把数字改小。
"""

import argparse
import html as htmlmod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTAINER = ROOT / "assets" / "container" / "index.html"
DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 视口档位（宽, 高, 用途）。高度只是"够不够放"的背景，所有判据都是横向或相对量。
VIEWPORTS = [
    (1600, 1000, "G1a"),      # 自然尺寸档：flex 不收缩，判「放得下」
    (1440, 900, "G2G3"),      # 面板头不折行 / 表格行高不抖
    (1080, 675, "G1b"),       # B-1 的验收目标档
    (900, 675, "REF"),        # 单调链中间档，只报不判
    (700, 675, "REF"),
]

# G4b 的预算：实际会用掉 2×30(btn) + 6(gap) − 52(min-height) = 14px。
# 24 是**决定**（留 10px 余量），不是测量结果；改它要改 backlog 条目 XX-028，不能改脚本。
G4B_BUDGET = 24
# G2：面板头子元素不超过一行的高度上限。22 是**决定**（行高 20 + 上下各 1px 描边余量）。
G2_MAX_HEAD_CHILD_HEIGHT = 22   # 只做参考列，不参与判定（见 G2 的注释）


PROBE = r"""
<script>
(function(){
  function num(v){ return (typeof v==='number' && isFinite(v)) ? Math.round(v*10)/10 : null; }
  function rect(el){ var r=el.getBoundingClientRect();
    return {left:num(r.left),right:num(r.right),top:num(r.top),bottom:num(r.bottom),
            width:num(r.width),height:num(r.height)}; }
  function label(el,i){ return el.id || (el.tagName.toLowerCase()+'#'+i); }

  // expected 的取法必须与容器一致（index.html:4046 的优先级链），否则 ENV 守卫自己会假红。
  // 用 profile 是干净的（每次 run 一个 mktemp 目录）⇒ LS.pageId 为空，只剩 hash / meta / pages[0]。
  function expectedStates(){
    var node=document.getElementById('iprd-data'); if(!node) return {expected:-1,pageId:'?'};
    var d; try{ d=JSON.parse(node.textContent); }catch(e){ return {expected:-1,pageId:'?'}; }
    var m=/^#\/?([A-Za-z0-9_\-]+)/.exec(location.hash||'');
    var pid=(m&&m[1]) || (d.meta&&d.meta.currentPageId) || ((d.pages||[])[0]||{}).id;
    var p=null; (d.pages||[]).forEach(function(x){ if(x.id===pid) p=x; });
    if(!p) return {expected:-1,pageId:pid};
    return {expected:((p.states)||[]).length,pageId:pid,pageName:p.name||''};
  }

  function measure(){
    var out={vw:window.innerWidth, vh:window.innerHeight,
             clientWidth:document.documentElement.clientWidth};
    var roots=document.querySelectorAll('.topbar .actions');
    out.actionsCount=roots.length;
    if(roots.length!==1){ return out; }
    var acts=roots[0];

    // ENV: 关键 id 在位（三个最靠右的控件，分组后仍在 .actions 内）
    out.keyIds={};
    ['btnPng','btnMd','btnDevkit'].forEach(function(id){
      out.keyIds[id]=!!acts.querySelector('#'+id);
    });

    // ENV: 应用已初始化 —— 用 page.states.length 对账，不用 options.length > 0。
    // index.html:3823-3825 是先清空再逐个 append，任何中间时刻 actual ∈ [1, expected-1]，
    // '> 0' 会把半初始化判成正常。而 expected=0/actual=0 是合法产物（无状态页）。
    var es=expectedStates();
    var sel=document.querySelector('#stateSelect');
    out.expected=es.expected; out.pageId=es.pageId;
    out.actual=sel?sel.options.length:-1;

    // G1: 目标集合 = .actions 内所有可交互叶节点（不是直接子元素：分组 wrapper 用
    // display:contents 时没有盒，若按"直接子元素"枚举会被整体豁免，包着的按钮一个都不检查）
    var SEL='button, select, input, textarea, a[href], [role=button]';
    var targets=acts.querySelectorAll(SEL);
    out.targets=[];
    for(var i=0;i<targets.length;i++){
      var el=targets[i], rs=el.getClientRects(), box=rect(el);
      out.targets.push({
        id: label(el,i), tag: el.tagName.toLowerCase(),
        visible: rs.length>0,
        inside: box.right<=document.documentElement.clientWidth+0.5,
        left: box.left, right: box.right, width: box.width
      });
    }

    // G2: 面板头不折行。
    // 为什么不用「子元素高度 <= 22」当判据：.pane-head 里有个 24px 高的按钮
    // （#prdToggle，自带 border+padding，实测所有视口下都是 24），它永远不会折行，
    // 却永远过不了 22 —— 那是「语义上必须的高度」，不是缺陷。用高度当代理量，
    // 会让判据在修好之后仍然红，人的动作就变成把 22 调大到 26。
    // 所以直接量「折行的文本」：只对**文本节点**数行盒。
    // 不能对容器元素数 —— Range 覆盖一个含多个块级子元素的容器时，每个子元素都出一个盒，
    // 实测把 #annoTools（58 个字符、24px 高）数成「10 行」，那是量法错，不是布局错。
    // 高度只作为参考列打出来，不参与判定。
    function wrappedTexts(root){
      var out=[], tw=document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), node;
      while((node=tw.nextNode())){
        var t=(node.nodeValue||'').trim();
        if(!t) continue;
        var r=document.createRange(); r.selectNodeContents(node);
        var rs=r.getClientRects(), n=0;
        for(var i=0;i<rs.length;i++){ if(rs[i].height>0.5) n++; }
        if(n>1){
          var p=node.parentElement;
          out.push({owner:(p&&(p.id||p.tagName.toLowerCase()))||'?', lines:n, text:t.slice(0,10)});
        }
      }
      return out;
    }
    out.paneHead=[];
    document.querySelectorAll('.pane-head').forEach(function(ph,pi){
      var pr=ph.getBoundingClientRect();
      var head={pane:pi, h:num(pr.height), scrollHeight:ph.scrollHeight,
                clientHeight:ph.clientHeight, kids:[], wrapped:wrappedTexts(ph)};
      for(var i=0;i<ph.children.length;i++){
        var el=ph.children[i], s=getComputedStyle(el);
        head.kids.push({id: label(el,i), tag: el.tagName.toLowerCase(),
                        h:num(el.getBoundingClientRect().height),
                        w:num(el.getBoundingClientRect().width),
                        display: s.display,
                        text: (el.textContent||'').trim().length});
      }
      out.paneHead.push(head);
    });

    // G3: 表格行高不抖。
    // **不能判「同一 tr 内 td 的 offsetHeight 极差」** —— CSS 表格里同一行的单元格会被
    // 拉伸到同一行高，所以那个极差结构上恒为 0。实测：给某列加 padding-top:12px 之后
    // 该行从 79 变成 91，而行内所有 td 仍是 91/91/…，极差照样 0。
    // 一条永远不会红的判据比没有判据更危险（它给"已验证"的信号）。
    // 真正要防的是"某列折行把整行撑高"，所以直接量每个 td 里文本的行盒数。
    out.rows=[];
    document.querySelectorAll('.ant-table tbody tr, table tbody tr').forEach(function(tr,ri){
      var tds=tr.querySelectorAll('td'); if(tds.length<2) return;
      var hs=[], wrapped=[];
      for(var i=0;i<tds.length;i++){
        hs.push(tds[i].offsetHeight);
        var w=wrappedTexts(tds[i]);
        if(w.length) wrapped.push({col:i, lines:Math.max.apply(null, w.map(function(x){return x.lines;})),
                                   text:w[0].text});
      }
      out.rows.push({row:ri, min:Math.min.apply(null,hs), max:Math.max.apply(null,hs),
                     spread: Math.max.apply(null,hs)-Math.min.apply(null,hs),
                     wrapped:wrapped, cols:tds.length});
    });

    // G4a/G4b/G4c：纵向三根轴
    var ws=document.querySelector('.workspace'), tb=document.querySelector('.topbar');
    out.actions={bottom:num(acts.getBoundingClientRect().bottom),
                 scrollHeight:acts.scrollHeight, clientHeight:acts.clientHeight,
                 scrollWidth:acts.scrollWidth, clientWidth:acts.clientWidth};
    out.workspaceTop=ws?num(ws.getBoundingClientRect().top):null;
    if(tb){
      var cs=getComputedStyle(tb);
      out.topbar={height:num(tb.getBoundingClientRect().height), minHeight:cs.minHeight,
                  flexShrink:cs.flexShrink};
    }
    out.settled=true;
    return out;
  }

  function emit(data){
    var d=document.createElement('div'); d.id='__layoutout';
    d.setAttribute('data-json', JSON.stringify(data));
    (document.body||document.documentElement).appendChild(d);
  }

  var tries=0;
  function tick(){
    tries++;
    var m=null, ok=false;
    try{ m=measure(); ok = m.settled && m.expected===m.actual && m.expected>=0; }catch(e){ ok=false; }
    // 初始化完成后再多等一帧，让 zoom/布局稳定；最多 600 帧（virtual time 下很快）
    if(!ok && tries<600){ setTimeout(tick,16); return; }
    if(m){ m.tries=tries; emit(m); } else { emit({settled:false, tries:tries}); }
  }
  if(document.readyState==='complete'){ setTimeout(tick,0); }
  else{ window.addEventListener('load', function(){ setTimeout(tick,0); }); }
})();
</script>
"""


class EnvError(Exception):
    pass


def find_chrome(explicit=None):
    cand = explicit or os.environ.get("CHROME") or DEFAULT_CHROME
    if not Path(cand).is_file():
        raise EnvError("找不到 Chrome: %s（用 CHROME=/path/to/chrome 指定）" % cand)
    return cand


def build_probe_html(container, extra_css=""):
    src = Path(container).read_text(encoding="utf-8")
    if "</body>" not in src:
        raise EnvError("容器里没有 </body>，无法注入探针")
    if extra_css:
        if "</style>" not in src:
            raise EnvError("容器里没有 </style>，无法注入反例 CSS")
        src = src.replace("</style>", "\n%s\n</style>" % extra_css, 1)
    return src.replace("</body>", PROBE + "</body>", 1)


def run_viewport(chrome, html_path, width, height, keep_dir):
    prof = tempfile.mkdtemp(prefix="xx-prd-layout-prof-")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
           "--disable-extensions", "--user-data-dir=" + prof,
           "--window-size=%d,%d" % (width, height),
           "--virtual-time-budget=10000", "--dump-dom", "file://" + str(html_path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    finally:
        # profile 放在 $TMPDIR 里（不在仓库内），删它不会被本机的批量删除策略拦掉。
        # 删不掉要留痕，不能静默继续 —— 跨轮复用 profile 会带旧 localStorage，
        # 实测会掉到 754/4 的假红（见 iterations/I-05/release.md）。
        shutil.rmtree(prof, ignore_errors=True)
        if Path(prof).exists():
            print("CLEAN_FAILED=%s" % prof)
    dom = r.stdout or ""
    m = re.search(r'id="__layoutout"[^>]*data-json="([^"]*)"', dom)
    if not m:
        raise EnvError("探针没有产出（exit=%d, dom_bytes=%d）：页面可能没跑完初始化"
                       % (r.returncode, len(dom)))
    data = json.loads(htmlmod.unescape(m.group(1)))
    if not data.get("settled"):
        raise EnvError("探针跑满 %s 帧仍未初始化完成（expected=%s actual=%s）"
                       % (data.get("tries"), data.get("expected"), data.get("actual")))
    data["_want"] = [width, height]
    return data


# ---------------------------------------------------------------- 判据
def evaluate(d):
    """返回 (rows, env_rows)。rows = [(id, 描述, 现值, 阈值, ok)]；env_rows = [(文本, ok)]"""
    env, rows = [], []

    # ENV 四条：无论过不过都各打一行。全过时一行不留，等于"我检查过了"不可见。
    env.append(("ENV 元素 .topbar .actions 唯一 %s"
                % ("PASS" if d.get("actionsCount") == 1 else
                   "ENV(命中 %s 个)" % d.get("actionsCount")),
                d.get("actionsCount") == 1))
    if d.get("actionsCount") != 1:
        return rows, env                      # 元素都选不对，后面的数没有意义

    keys = d.get("keyIds") or {}
    missing = [k for k, v in keys.items() if not v]
    env.append(("ENV 关键 id 在位 %s (%s)"
                % ("PASS" if not missing else "ENV(缺 %s)" % " ".join(missing),
                   " ".join(sorted(keys))),
                not missing))

    cw = d.get("clientWidth")
    env.append(("ENV 视口有效 %s (clientWidth=%s)"
                % ("PASS" if cw and cw > 0 else "ENV(clientWidth=%s)" % cw, cw),
                bool(cw and cw > 0)))

    exp, act = d.get("expected"), d.get("actual")
    env.append(("ENV 应用已初始化 %s (#stateSelect options=%s expected=%s)"
                % ("PASS" if exp == act and exp is not None and exp >= 0
                   else "ENV(expected=%s actual=%s)" % (exp, act), act, exp),
                exp == act and exp is not None and exp >= 0))

    if not all(ok for _, ok in env):
        return rows, env

    # ---- G1a / G1b：三个数分开打
    targets = d.get("targets") or []
    visible = [t for t in targets if t["visible"]]
    exempt = [t for t in targets if not t["visible"]]
    outside = [t["id"] for t in visible if not t["inside"]]
    shape = "目标=%d 可见=%d 豁免=%d(%s)" % (
        len(targets), len(visible), len(exempt),
        ",".join(t["id"] for t in exempt) or "无")
    w, h = d["_want"]

    if d.get("_slot") == "G1a":
        rows.append(("G1a", "自然尺寸档放得下",
                     "目标=%d 可见=%d 豁免=%d 违规=%d%s"
                     % (len(targets), len(visible), len(exempt), len(outside),
                        ("(" + ",".join(outside) + ")") if outside else ""),
                     "违规=0 @%dx%d" % (w, h), not outside, len(outside)))
    elif d.get("_slot") == "G1b":
        # B-1 的验收目标档。违规 ids 一起打：只给个数，改的人不知道从哪下手。
        rows.append(("G1b", "1080 档没被裁出视口",
                     "违规=%d%s" % (len(outside),
                                    ("(" + ",".join(outside) + ")") if outside else ""),
                     "违规=0 @%dx%d（B-1 落地后）" % (w, h), not outside, len(outside)))
    d["_shape"] = shape

    # ---- G2：面板头不折行（判「行盒数」，不判高度；高度只做参考列）
    if d.get("_slot") == "G2G3":
        heads = d.get("paneHead") or []
        wrapped = []                              # 折了行的文本节点
        overflow = []                             # 盒子高度装不下内容的头
        tallest = 0.0
        for hd in heads:
            if hd["scrollHeight"] > hd["clientHeight"] + 0.5:
                overflow.append("pane%d(%d>%d)" % (hd["pane"], hd["scrollHeight"], hd["clientHeight"]))
            for wnode in hd.get("wrapped") or []:
                wrapped.append("%s(%d行)" % (wnode["owner"], wnode["lines"]))
            for k in hd["kids"]:
                tallest = max(tallest, k["h"] or 0)
        rows.append(("G2", "面板头不折行",
                     "头=%d 折行子元素=%d 溢出的头=%d 最高子元素=%.1fpx"
                     % (len(heads), len(wrapped), len(overflow), tallest)
                     + (("(" + ",".join(wrapped[:6]) + ")") if wrapped else "")
                     + (("[" + ",".join(overflow[:4]) + "]") if overflow else ""),
                     "折行=0 且 溢出=0 @%dx%d（高度 22 只做参考，不判定）" % (w, h),
                     bool(heads) and not wrapped and not overflow,
                     (len(wrapped), len(overflow))))

        # ---- G3：表格行高不抖（判「有折行的单元格」，不判行内极差 —— 那个数结构上恒 0）
        rws = d.get("rows") or []
        bad = [r for r in rws if r.get("wrapped")]
        spread_max = max([r["spread"] for r in rws], default=0)
        rows.append(("G3", "表格行高不抖",
                     "行=%d 折行单元格=%d%s（行内极差恒为 %d：单元格被拉伸到同一行高，故不判定）"
                     % (len(rws), sum(len(r["wrapped"]) for r in bad),
                        (("(" + ",".join("r%d.c%d:%d行" % (r["row"], c["col"], c["lines"])
                                         for r in bad[:4] for c in r["wrapped"][:2]) + ")")
                         if bad else ""), spread_max),
                     "折行单元格=0 @%dx%d" % (w, h), rws and not bad,
                     sum(len(r["wrapped"]) for r in rws)))

    # ---- G4a：顶栏内容不越界（量 .actions，不量 .topbar）
    at, wt = (d.get("actions") or {}).get("bottom"), d.get("workspaceTop")
    if at is not None and wt is not None:
        ok = at <= wt + 0.5
        rows.append(("G4a", "顶栏内容不越界",
                     "actions.bottom=%.1f workspace.top=%.1f" % (at, wt),
                     "actions.bottom <= workspace.top + 0.5 @%dx%d" % (w, h), ok,
                     round(at - wt, 1)))

    # ---- G4b：顶栏高度预算（地板从 computed minHeight 读，不写字面量 52）
    tb = d.get("topbar") or {}
    mh = tb.get("minHeight")
    if mh and re.fullmatch(r"[\d.]+px", mh.strip()):
        budget = (tb.get("height") or 0) - float(mh.strip()[:-2])
        rows.append(("G4b", "顶栏高度预算",
                     "height=%.1f - minHeight=%.1f = %.1f" % (tb.get("height") or 0,
                                                              float(mh.strip()[:-2]), budget),
                     "<= %d @%dx%d" % (G4B_BUDGET, w, h), budget <= G4B_BUDGET,
                     round(budget, 1)))
    else:
        # minHeight 不是 px 就说明还没声明地板 —— B-1 还没落地。这时"预算"这个量不存在，
        # 报 N/A 并把原因打出来。既不能算通过（会假装验证过），也不能算违规
        # （会把"设计还没改"判成"改坏了"）。
        rows.append(("G4b", "顶栏高度预算",
                     "N/A（minHeight=%s 未声明地板，B-1 未落地）" % mh,
                     "<= %d @%dx%d" % (G4B_BUDGET, w, h), True, None))

    # ---- G4c：.actions 无纵向裁切
    if d.get("actions"):
        a = d["actions"]
        ok = a["scrollHeight"] <= a["clientHeight"] + 0.5
        rows.append(("G4c", ".actions 无纵向裁切",
                     "scrollHeight=%s clientHeight=%s" % (a["scrollHeight"], a["clientHeight"]),
                     "scrollHeight <= clientHeight + 0.5 @%dx%d" % (w, h), ok,
                     round(a["scrollHeight"] - a["clientHeight"], 1)))

    return rows, env


def render(results):
    """results = [(slot, data)]，按视口顺序。"""
    all_rows, all_env, chain = [], [], []
    for slot, d in results:
        rows, env = evaluate(d)
        all_env.extend((slot, d, e, ok) for e, ok in env)
        if not all(ok for e, ok in env):
            continue
        all_rows.extend((slot, d, r) for r in rows)
        # 每一档（含判据档）都进单调链：链要覆盖 700/900/1080/1600 四个点，
        # 只拿 REF 两档算会得出 "5@900 >= 7@700" 这种把顺序搞反的结论。
        targets = d.get("targets") or []
        outside = [t["id"] for t in targets if t["visible"] and not t["inside"]]
        chain.append((d["_want"][0], len(outside), outside))

    for slot, d, text, ok in all_env:
        w, h = d["_want"]
        print("  [%dx%d] %s" % (w, h, text))
    print()
    for slot, d, (rid, desc, actual, limit, ok, _v) in all_rows:
        w, h = d["_want"]
        print("%-4s %-16s %-52s 阈值 %-34s %s"
              % (rid, desc, actual, limit, "PASS" if ok else "FAIL"))
        if rid in ("G1a", "G1b"):
            print("      %s = %s" % (rid, d.get("_shape") or ""))

    if chain:
        print()
        for w, n, ids in chain:
            print("REF  %4d 违规=%d%s  %s"
                  % (w, n, ("(" + ",".join(ids) + ")") if ids else "",
                     "（判据档）" if w in (1600, 1080) else "（只报不判）"))
        # 单调链：violation(700) >= violation(900) >= violation(1080) >= violation(1600) == 0。
        # 逐档写死 2/0/0/0 会被一次按钮文案改动静默打死；而 B-1 落地时"裁切→换行"会让这条链
        # 合法地断开 —— 那时必须重定基线并在文件头写一行「口径变更」，不是把数字改小。
        ordered = sorted(chain, key=lambda x: x[0])        # 窄 → 宽（700 → 1600）
        vals = [n for _, n, _ in ordered]
        mono = all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))
        print("REF  单调链 %s  %s"
              % (" >= ".join("%d@%d" % (n, w) for w, n, _ in ordered),
                 "PASS" if mono else "断（口径变更点，需重定基线）"))

    env_bad = [x for x in all_env if not x[3]]
    fails = [r for _, _, r in all_rows if not r[4]]
    if env_bad:
        print("RESULT ENV（%d 条环境守卫不成立，不计入违规数）" % len(env_bad))
        return 2
    print("RESULT %s（%d 项违规）" % ("PASS" if not fails else "FAIL", len(fails)))
    return 0 if not fails else 1


# ---------------------------------------------------------------- 自证（§6.5 G-2）
# 自证只在 3 个判据档上跑：1600(G1a) / 1440(G2,G3) / 1080(G1b)。900/700 是 REF 中间档，
# 进自证只会让 6 个反例各多跑两次 Chrome，换不来额外的真相。
SELFCHECK_VIEWPORTS = [(1600, 1000, "G1a"), (1440, 900, "G2G3"), (1080, 675, "G1b")]

SELFCHECK_CASES = [
    # (名字, 注入的 CSS, expected, declared_extra)
    ("给 .actions 加 420px 左内边距（内容右移出视口）",
     ".topbar .actions{padding-left:420px}", {"G1a", "G1b"}, set()),
    ("把表格压成 240px 宽（每列挤到 40px，文本被迫折行）",
     ".ant-table{table-layout:fixed;width:240px}", {"G3"}, set()),
    ("面板头 flex-wrap 到第二行（装不下、溢出 38px 盒）",
     ".pane-head{flex-wrap:wrap}", {"G2"}, set()),
    ("把 .topbar 盒子压到 20px、内容仍 31px（盒子合规、内容越界）",
     ".topbar{height:20px}", {"G4a"}, set()),
    (".actions 高度被压到 20px（无滚动条的无提示裁切）",
     ".topbar .actions{max-height:20px}", {"G4c"}, set()),
    # 这条不断言集合：它要证的是"豁免判据不是 id 名单"，证据是形状里 豁免=1 → 豁免=0。
    # expected=None 表示只跑旁证，不做精确集合要求（硬凑一个集合就等于按结果改测试）。
    ("让 #entitySelect 显示出来（证明豁免不是 id 名单）",
     ".topbar .actions #entitySelect{display:inline-block!important}", None, set()),
]


def _state(result):
    """{判据 id -> (是否通过, 数值)}。自证比的是这个，不是纯"通过/失败"——

    因为基线本来就红着（G1b 今天红 2、G2 今天折行），对一条已经红的判据再注入同类缺陷，
    通过/失败集根本不变，反例会"增量=[]"地静默通过。第一版就是这么错的。

    但也不能只比数值：G4a 的数值是连续量（actions.bottom − workspace.top），
    把 .actions 压矮 8px 会让它从 -11 变成 -19，而它仍然合规 —— 纯数值差分会把
    "没坏"判成"坏了"。所以两段：通过状态变了算变化；本来就红着的，数值变了才算变化。
    """
    rows, env = evaluate(result)
    if not all(ok for _, ok in env):
        raise EnvError("ENV 守卫不成立，无法评估")
    return {r[0]: (r[4], r[5]) for r in rows}


def _changed(base, fx):
    out = set()
    for rid, (ok_now, val_now) in fx.items():
        ok_before, val_before = base.get(rid, (None, None))
        if ok_now != ok_before:
            out.add(rid)
        elif not ok_before and val_now != val_before:
            out.add(rid)              # 本来红着，现在红得更多 —— 也是"变坏"
    return out


def selfcheck(container, chrome):
    html = Path(tempfile.mkdtemp(prefix="xx-prd-layout-sf-")) / "base.html"
    html.write_text(build_probe_html(container), encoding="utf-8")
    base, base_shapes, base_fails = {}, {}, set()
    for w, h, slot in SELFCHECK_VIEWPORTS:
        d = run_viewport(chrome, html, w, h, None)
        d["_slot"] = slot
        try:
            base.update(_state(d))
        except EnvError as ex:
            print("基线就跑不动：%s" % ex)
            return 2
        rows, _ = evaluate(d)
        base_fails |= {r[0] for r in rows if not r[4]}
        base_shapes[w] = d.get("_shape")

    print("基线失败集 %s" % (sorted(base_fails) or "（全绿）"))
    print("基线数值 %s（同一条判据出现在多档时取最后一档）"
          % json.dumps(base, ensure_ascii=False, sort_keys=True))
    print("基线形状 %s" % json.dumps(base_shapes, ensure_ascii=False))
    print("== G-2：注入缺陷后，**数值发生变化**的判据必须精确等于 expected ∪ declared_extra")

    ok_all = True
    for name, extra, expected, declared in SELFCHECK_CASES:
        f = Path(tempfile.mkdtemp(prefix="xx-prd-layout-fx-")) / "fx.html"
        f.write_text(build_probe_html(container, extra), encoding="utf-8")
        fx, shapes = {}, {}
        for w, h, slot in SELFCHECK_VIEWPORTS:
            d = run_viewport(chrome, f, w, h, None)
            d["_slot"] = slot
            try:
                fx.update(_state(d))
            except EnvError as ex:
                print("  %-46s ENV 守卫被反例打破：%s  SELFCHECK-FAIL" % (name, ex))
                ok_all = False
                break
            shapes[w] = d.get("_shape")
        else:
            changed = _changed(base, fx)
            if expected is None:
                ok = True                     # 只跑旁证，见该 case 的注释
                want = set()
            else:
                want = expected | declared
                ok = changed == want
            ok_all = ok_all and ok
            print("  %-46s 变化=%-24s 期望=%-24s %s"
                  % (name, sorted(changed) or "[]", sorted(want) or "[]",
                     "OK" if ok else "SELFCHECK-FAIL"))
            if not ok:
                print("      expected 未动：%s｜多报：%s"
                      % (sorted(expected - changed), sorted(changed - want)))
            if "entitySelect" in extra:
                before, after = base_shapes.get(1080, ""), shapes.get(1080, "")
                print("      豁免证明 @1080：注入前 %s ｜ 注入后 %s" % (before, after))
                if "豁免=1" not in before or "豁免=0" not in after:
                    print("      豁免仍在按名单判（应按「有没有盒」判）SELFCHECK-FAIL")
                    ok_all = False

    print("RESULT %s (selfcheck)" % ("PASS" if ok_all else "FAIL"))
    return 0 if ok_all else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="G1-G4 几何判据")
    ap.add_argument("container", nargs="?", default=str(DEFAULT_CONTAINER))
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--keep", action="store_true", help="保留临时 HTML")
    args = ap.parse_args(argv)

    try:
        chrome = find_chrome()
    except EnvError as ex:
        print(str(ex))
        return 2
    if not Path(args.container).is_file():
        print("找不到容器文件: %s" % args.container)
        return 2

    if args.selfcheck:
        return selfcheck(args.container, chrome)

    tmpdir = Path(tempfile.mkdtemp(prefix="xx-prd-layout-"))
    html = tmpdir / "probe.html"
    html.write_text(build_probe_html(args.container), encoding="utf-8")
    results = []
    try:
        for w, h, slot in VIEWPORTS:
            d = run_viewport(chrome, html, w, h, tmpdir)
            d["_slot"] = slot
            results.append((slot, d))
    except EnvError as ex:
        print(str(ex))
        return 2
    finally:
        if args.keep:
            print("PROBE_HTML=%s" % html)
        else:
            shutil.rmtree(tmpdir, ignore_errors=True)
    return render(results)


if __name__ == "__main__":
    sys.exit(main())
