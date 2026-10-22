#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-P19：形态与密度判据（作业型列表页）。规格见 项目治理/迭代/I-07-形态与密度方案.md §6。

为什么要有这把量尺（而不是继续用截图说话）：
  Owner 对列表页的判断是「像不像在用 Excel」「一屏能不能看到更多」——这类话可以被数出来：
  一屏几行、筛选区几行几列、控件多宽、行高多少、几档字号。数得出来就能做成门，
  数不出来的（配色好不好看、留白舒不舒服）才留给眼睛。

三条纪律（写在最前面，改脚本前先读）：

1. **两个口径必须分开报**。P2a 是产品态（无评审外壳，1440 全屏），P2b 是评审态（容器外壳
   192px + 页面导航）。只报产品态 = 拿给人看的页去验收；只报评审态 = 把工具成本当产品形态。
   两套都要有，且各自有目标值。
2. **带前置条件的判据，条件不成立必须 SKIP 并计数，不得 PASS**。P8/P13/P17 有前置
   （V10 只认这三条；P4/P18 的前置不成立时判 FAIL —— 存量产物不合格不能靠 SKIP 免检）。
   今天默认态内容宽 540，若 P8 在 540 上「不溢出」就静默 PASS，改造前后会同绿——
   这是上一轮假绿的形态，不能再犯。
3. **判据必须定义在「用户实际看到的态」上**。宽度链（1600 评审态）：
   pane 856 → 画布 796 → −sider 200 → −padding 48 → 内容 548。验收态是**折叠 PRD、保留 nav**，
   折叠后 1600 得 1026 档、1440 得 866 档。不切就量 = 在 548 里量 1026 的预算。

用法:
    python3 tests/check_ui_shape.py                       # 跑全部示例里含列表页的产物
    python3 tests/check_ui_shape.py FILE.json             # 只跑一个产物
    python3 tests/check_ui_shape.py FILE.json --page p-x  # 指定页面（默认自动挑第一个列表页）
    python3 tests/check_ui_shape.py --selfcheck           # 注入反例，验证判据能红在正确的规则上
    python3 tests/check_ui_shape.py --keep                # 保留临时 HTML

退出码:
    0 = 无 FAIL、SKIP 全在白名单内、且 V8 的 FAIL 集与期望名单逐条相等
    1 = 有 FAIL，或出现白名单外的 SKIP（后者打 `RESULT INCOMPLETE`，见 V13），
        或 example-05 的 FAIL 集与 `EXPECTED_FAIL` 不符 / 全量模式下该文件根本没跑（V8）
    2 = 环境问题（找不到 Chrome / 探针没产出 / 页面空集）

口径变更
  2026-10-22 首版。三处口径决定，均在此留痕：
    a) **验收档识别用 ±16 容差**。方案写 866 / 1026，是按「页内 sider 208」算的；容器
       `.ant-sider` 实宽 200，实测内容宽因此是 858 / 1018。若死等 866，前置条件永远不成立，
       P8/P17 会全 SKIP —— 那是假绿。故定义 ACCEPT_TOL=16，落在 866±16 即认作 866 档。
       报告里把实测内容宽与预算值并排打出来，口径差异一眼可见。
    b) **P6 量区块盒左边界，不量文本左边界**。文本左边界必然被 padding 分开（td 16 / alert 14），
       拿它当判据会让「设计对但 padding 不同」常红；区块盒才是视觉上的那条竖线。
       文本左边界作为参考列打印，不参与判定。
    c) **P2b / P16 的「视口底」用 innerHeight，不用 clientHeight**。前者是浏览器给的可视区，
       后者是元素自身高度；用错会把「表格被挤出屏」量成「表格很高」。

  2026-10-22 v2（I-07 返工，幻神 §3 裁定）。六处定义变更，全部有单号：
    d) **P4 改预算制**（§3.4）：控件宽 = 该档栅格列宽 − 84，±2 且 ≥160。
       旧的 240–320 是拿 1232 档的列宽 381 算的，866/1026 两档数学上不可达 ——
       那是「阈值本身就红」，不是产物错。非 grid3 的旧一行式**也按同一预算判**：
       它实测也是 `1 行 × 3 列`（P3a 看得见），栏宽能推；对它 SKIP 等于替存量产物免检，
       而 V10 允许 SKIP 的只有 P8/P13/P17。
    e) **P12 改分层唯一**（§3.5）：标题带内 primary 恰 1，全页 ≤2（第二个只能是筛选动作行的
       「查询」），标题带 primary 与 h1 的 top 差 ≤8，h1 ≥16px 且 ≥600。
       旧口径「全页恰 1」与本项目既定形态（查询是主色）必然冲突。
    f) **P17 单档化 + 补渲染宽**（§3.6 / §3.8）：只判 866 档，1026 档 SKIP 并打印列数与渲染宽；
       同时比 `th.offsetWidth` 与声明宽（±2）。只读 JSON 的 P17 放过过一次真 bug ——
       `width:48` 漏单位，8 列全渲染成 108.25，判据全绿。
    g) **P18 改集合相等**（§3.9）：配了 ellipsis 的列集合必须**等于**真溢出列集合。
       旧口径只要求「配了的列真溢出」，允许漏配的列悄悄裁字（任务单号/批次号就是这样被裁的）。
       非 `table-layout:fixed` 时**判 FAIL 而非 SKIP**：列宽由内容决定时 ellipsis 无从生效，
       这本身就不合规（与 P7 同源，不同面）；且 SKIP 会让存量产物（auto + 2/7 声明率）免检。
    h) **P2a 舞台去壳**（REQ-I07-02）：不再自带假 Sider、不再加舞台 padding，`--tw-max` 的
       `100vh` 按舞台高 900 换算。旧舞台量到的内容宽 936（应 1184），是假红。
    i) **自证基线切到 example-06**（REQ-I07-04）：`--base` 可指定，默认 example-06；
       基线不绿的目标判据计入「未覆盖」，覆盖 <10 时 RESULT 为 INCOMPLETE 并非 0 退出。
       旧版拿 example-05 当基线，10 条注入 6 条 SKIP 却打 RESULT PASS。
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
CONTAINER = ROOT / "assets" / "container" / "index.html"
EXDIR = ROOT / "assets" / "examples"
DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 两档视口。1600 是评审台常见尺寸，1440 是笔记本；两档都是「用户会打开看到的」。
VIEWPORTS = [(1600, 1000), (1440, 900)]

# 目标值（**决定**，不是测量结果）。改它要改 backlog 条目 XX-030，不能改脚本。
TARGET_ROWS_PRODUCT = 14          # P2a：产品态一屏整行数
TARGET_ROWS_REVIEW = {1440: 9, 1600: 12}   # P2b：评审态（含外壳）
FILTER_MAX_H = 148                # P3：筛选区总高（实测 139）
FILTER_COLS = 3                   # P3：栅格列数
ROW_MAX_H = 34                    # P9：行高（设计 32 + 行内盒 2，实测 34）
LEFT_EDGE_TOL = 4                 # P6：竖线极差
ACCEPT_W = {866: 8, 1026: 9}      # P17：验收档内容宽 → 列数
ACCEPT_TOL = 16                   # 口径 a：验收档识别容差
DECL_RATE_MIN = 0.80              # P7：列宽声明率
ELLIPSIS_MAX_COLS = 3             # P18：配 ellipsis 的列数上限
FONT_TIERS_MAX = 3                # P19：字号档数
PANE_MIN = {1440: 1182, 1600: 1342}   # P15：A 层默认 pane 宽

# P4 的预算常数：**从盒模型推出来的，不是拍的数**（I-07 §3.4）。
# .ant-filter-bar 的盒：padding 20×2 + border 1×2 + column-gap 24×2 → 3 等分列宽
#   列宽 = (内容宽 − 2×20 − 2×1 − 2×24) / 3 = (内容宽 − 90) / 3
#   控件宽 = 列宽 − label 76 − gap 8 = 列宽 − 84
# 866 档：(866−90)/3 = 258.7 → 174.7   ｜ 1026 档：(1026−90)/3 = 312.0 → 228.0
# 为什么不能写 240–320：240 是拿 1232 档的列宽 381 算出来的，866/1026 两档数学上不可达。
# 下限 160 保留 —— 它防的是「一行式 124px 控件」复发（§4.1 的原病），不是装饰。
FB_PAD = 20
FB_BORDER = 1
FB_GAP = 24
FB_LABEL = 76
FB_LABEL_GAP = 8
CTL_MIN_W = 160
CTL_TOL = 2                       # 控件宽与预算的容差
COL_W_TOL = 2                     # P17：渲染宽与声明宽的容差

# SKIP 的白名单（V13，I-07 第二批）。**只有这三条允许 SKIP，且各有硬理由**：
#   P8  —— 内容宽不在验收档（866 / 1026）时，「横向溢出」没有可比基准；
#   P13 —— 非列表页 / 没有分页控件时，pageSize 无从谈起；
#   P17 —— 列集在生成时定、不运行时切（D-3），1026 档只有同一套 866 列集，预算闭合不成立。
#
# 为什么要有这条守卫：第一版把 P4（legacy 筛选区）和 P18（非 fixed 布局）也写成了 SKIP，
# 于是 example-05 的 FAIL 从 22 掉到 16 —— 判据没放宽，但**不适用的判据不判了**，
# 门在存量产物上悄悄变松。这件事当时是靠人肉对数字发现的，纪律写在文档里没用。
# 现在改成客观守卫：SKIP 只允许「这条判据当前不适用」，**不允许**「这条判据我判不了」——
# 后者是脚本缺陷，不该由人每次去数。
SKIP_WHITELIST = ("P8", "P13", "P17")

# V8（I-07 第二批裁定）：example-05 的期望 FAIL 集，**逐条写死**。
#
# 原口径是「FAIL ≥20（改前 22）」。数字守不住 —— 这件事在 `check_docs.EXPECTED_EXAMPLES`
# 上刚被证明过：数量相等不蕴含集合相等（6 个里换掉 1 个，数量仍是 6）。
# 换成集合相等后，输出能回答「少了哪条 / 多出哪条」，也不用再让人心算「22 减几」。
#
# 进名单的门槛：该条在 example-05 上**应该红**（产物本身不合规），而不是「脚本没跑」
# —— 后者是 SKIP，由 V13 管。名单变动必须在交付说明里逐条解释来源，
# 否则「把一条红的挪进名单」和「放宽判据」是同一个效果。
EXPECTED_FAIL = {
    "example-05-behavior-model.json": {
        # 9 条判据 × 两档 = 18 条，两档同红：说明是产物问题，不是某一档的偶然。
        # P15 已不在名单里：F6 之后它真实翻绿（判据未改），见交付说明第二批 §4。
        "P3a@1440", "P3a@1600",
        "P4@1440",  "P4@1600",
        "P7@1440",  "P7@1600",
        "P9@1440",  "P9@1600",
        "P10@1440", "P10@1600",
        "P11@1440", "P11@1600",
        "P12@1440", "P12@1600",
        "P13@1440", "P13@1600",
        "P18@1440", "P18@1600",
    },
}


# ------------------------------------------------------------------ 探针
PROBE = r"""
<script>
(function(){
  function num(v){ return (typeof v==='number' && isFinite(v)) ? Math.round(v*10)/10 : null; }
  function rect(el){ var r=el.getBoundingClientRect();
    return {left:num(r.left),right:num(r.right),top:num(r.top),bottom:num(r.bottom),
            width:num(r.width),height:num(r.height)}; }
  function cs(el){ return getComputedStyle(el); }
  function txt(el){ return (el.textContent||'').replace(/\s+/g,' ').trim(); }

  // 文本左边界：只对**首个非空文本节点**取盒，不用元素盒（元素盒含 padding）
  function textLeft(el){
    if(!el) return null;
    var tw=document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n;
    while((n=tw.nextNode())){
      if(!(n.nodeValue||'').trim()) continue;
      var r=document.createRange(); r.selectNodeContents(n);
      var rs=r.getClientRects();
      for(var i=0;i<rs.length;i++) if(rs[i].width>0.5) return num(rs[i].left);
    }
    return null;
  }
  // 文本行盒数（>1 即折行）。只对文本节点数，不对容器数 —— 容器里多个块级子元素会各出一个盒。
  function wrappedLines(el){
    var out=0, tw=document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n;
    while((n=tw.nextNode())){
      if(!(n.nodeValue||'').trim()) continue;
      var r=document.createRange(); r.selectNodeContents(n);
      var rs=r.getClientRects(), c=0;
      for(var i=0;i<rs.length;i++) if(rs[i].height>0.5) c++;
      if(c>out) out=c;
    }
    return out;
  }
  function isGray(bg){
    var m=/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/.exec(bg||'');
    if(!m) return true;
    if(m[4]!==undefined && parseFloat(m[4])<0.05) return true;
    var r=+m[1],g=+m[2],b=+m[3];
    return (Math.max(r,g,b)-Math.min(r,g,b))<=12;
  }

  function content(){
    var list=document.querySelectorAll('#protoCanvas .ant-content');
    return list.length?list[0]:null;
  }

  function measure(){
    var out={ vw:window.innerWidth, vh:window.innerHeight,
              dpr:window.devicePixelRatio||1, settled:false };
    var C=content();
    if(!C){ out.err='NO_CONTENT'; return out; }
    out.err=null;

    // ---- P15：默认态 pane 宽（折叠前量，这是用户打开看到的宽度）
    var pane=document.querySelector('.pane-prototype');
    out.paneDefaultW = pane ? num(pane.clientWidth) : null;
    out.prdCollapsedAtStart = !!(document.querySelector('#panePrd') &&
        document.querySelector('#panePrd').classList.contains('collapsed'));

    // ---- 折叠 PRD，进入验收态。只切一次：已经折叠就不再点（F6 之后默认就是折叠的）
    var prd=document.querySelector('#panePrd');
    if(prd && !prd.classList.contains('collapsed')){
      var t=document.querySelector('#prdToggle');
      if(t) t.click();
      out.didCollapse=true;
    } else { out.didCollapse=false; }

    var C2=content(); if(!C2){ out.err='NO_CONTENT_AFTER'; return out; }
    var C=content();
    var s=cs(C);
    out.paneW = pane ? num(pane.clientWidth) : null;
    var canvas=document.querySelector('#protoCanvas');
    out.canvasW = canvas ? num(canvas.clientWidth) : null;
    out.contentBoxW = num(C.clientWidth - parseFloat(s.paddingLeft||0) - parseFloat(s.paddingRight||0));
    out.contentPadL = num(parseFloat(s.paddingLeft||0));
    out.contentLeftEdge = num(C.getBoundingClientRect().left + parseFloat(s.paddingLeft||0));

    // ---- P1：统计卡
    var stats=C.querySelectorAll('.ant-stat');
    out.statCount=stats.length;

    // ---- P5：三层噪音（border + bg + shadow 三者同时成立）。Drawer/Modal 内豁免
    function inOverlay(el){ return !!(el.closest('.ant-drawer-mask,.ant-modal-mask,.ant-drawer,.ant-modal')); }
    var noise=[], all=C.querySelectorAll('*');
    for(var i=0;i<all.length;i++){
      var el=all[i];
      if(inOverlay(el)) continue;
      var st=cs(el);
      var bw=parseFloat(st.borderTopWidth||0);
      var bg=st.backgroundColor||'';
      var bgOpaque = !(/rgba\(0, 0, 0, 0\)/.test(bg) || bg==='transparent');
      var sh=st.boxShadow||'none';
      if(bw>0 && bgOpaque && sh!=='none' && sh!=='') {
        noise.push({tag:el.tagName.toLowerCase(), cls:(el.className||'').toString().slice(0,60),
                    id:el.id||'', bw:num(bw), bg:bg, sh:sh.slice(0,40)});
      }
    }
    out.noise=noise; out.noiseCount=noise.length;

    // ---- 左边界四量（P6 主体用盒子；文本左边界只作参考列）
    function first(sel){ return C.querySelector(sel); }
    /* 标题带 = h1 所在的、`.ant-content` 的直接子块（P12 用它区分「主操作」与
       「筛选动作行的查询」）。取直接子块而不是最近父级：h1 外面通常还包一层
       Space（左半区），那一层里没有主操作。 */
    var h1=C.querySelector('h1');
    var band=h1?h1.closest('.ant-content > *'):null;
    var prim=[], btns=C.querySelectorAll('.ant-btn.primary');
    for(var i=0;i<btns.length;i++){
      if(inOverlay(btns[i])) continue;
      var rs=btns[i].getClientRects();
      if(!rs.length) continue;
      prim.push({id:btns[i].id||'', text:txt(btns[i]).slice(0,12), top:num(rs[0].top),
                 left:num(rs[0].left), w:num(rs[0].width),
                 band: !!(band && band.contains(btns[i])),
                 qact: !!btns[i].closest('.ant-filter-bar .fb-actions')});
    }
    out.primaryBtns=prim;
    out.bandFound=!!band;

    out.h1 = h1 ? {top:num(h1.getBoundingClientRect().top), left:num(h1.getBoundingClientRect().left),
                   size:num(parseFloat(cs(h1).fontSize)),
                   weight:(parseInt(cs(h1).fontWeight,10)||0), text:txt(h1).slice(0,20)} : null;

    var fbar=first('.ant-filter-bar'), qbar=first('.ant-query-bar');
    var twrap=first('.ant-table-wrap');
    var alert=first('.ant-alert');
    out.edges={
      primary: prim.length?prim[0].left:null,
      filterBar: fbar?num(fbar.getBoundingClientRect().left):(qbar?num(qbar.getBoundingClientRect().left):null),
      tableWrap: twrap?num(twrap.getBoundingClientRect().left):null,
      alert: alert?num(alert.getBoundingClientRect().left):null,
      contentEdge: out.contentLeftEdge
    };
    var fLabel = fbar ? fbar.querySelector('.fb-field .lb,.fb-field label') : (qbar?qbar.querySelector('.qf-label'):null);
    var cell0 = twrap ? twrap.querySelector('tbody tr td') : null;
    out.textEdges={
      primaryText: prim.length?textLeft(btns[0]):null,
      filterLabel: textLeft(fLabel),
      firstCell: textLeft(cell0),
      alertText: alert?textLeft(alert):null
    };

    // ---- P3/P4：筛选区形态与控件宽
    out.filter = (function(){
      var bar = fbar || qbar;
      if(!bar) return {exists:false, kind:null, h:null, rows:null, firstRowCount:null,
                       ctlW:[], ctlH:[], collapsed:false};
      var kind = fbar?'grid3':'legacy';
      var items = fbar ? Array.prototype.slice.call(fbar.querySelectorAll('.fb-field'))
                       : Array.prototype.slice.call(bar.querySelectorAll('.qf'));
      var tops={}, rows=0;
      items.forEach(function(it){ var t=Math.round(it.getBoundingClientRect().top); if(!(t in tops)){ tops[t]=0; } tops[t]++; });
      var keys=Object.keys(tops).map(Number).sort(function(a,b){return a-b;});
      var cw=[], ch=[];
      var ctlSel = fbar ? '.fb-field .ctl' : '.qf-ctl';
      Array.prototype.forEach.call(bar.querySelectorAll(ctlSel), function(c){
        var r=c.getBoundingClientRect(); if(r.width>0){ cw.push(num(r.width)); ch.push(num(r.height)); }
      });
      return {exists:true, kind:kind, h:num(bar.offsetHeight), rows:keys.length,
              firstRowCount: keys.length?tops[keys[0]]:0,
              ctlW:cw, ctlH:ch,
              collapsed: bar.classList.contains('collapsed')};
    })();

    // ---- 表格
    var tables=[], tlist=C.querySelectorAll('.ant-table');
    for(var ti=0; ti<tlist.length; ti++){
      var t=tlist[ti];
      if(inOverlay(t)) continue;
      var wrap=t.closest('.ant-table-wrap')||t.parentElement;
      var wr=wrap.getBoundingClientRect();
      var rows=t.querySelectorAll('tbody tr');
      var hs=[];
      for(var ri=0;ri<rows.length;ri++){
        var cells=rows[ri].querySelectorAll('td');
        if(cells.length<2) continue;              /* 空态/加载态那一行 colspan，不参与 */
        hs.push(rows[ri].offsetHeight);
      }
      var firstRowH = hs.length?hs[0]:null;
      var visH = Math.max(0, Math.min(wr.bottom, window.innerHeight) - Math.max(wr.top, 0));
      /* 列：读**声明值**。`col.offsetWidth` 之和在 table-layout:fixed 下恒等于表宽，
         用它验「预算闭合」等于自证——永远闭合。 */
      var ths=t.querySelectorAll('thead th');
      var colsInfo=[];
      for(var ci=0;ci<ths.length;ci++){
        var th=ths[ci];
        var declW = th.style.width?parseFloat(th.style.width):null;
        var cell = rows.length?rows[0].children[ci]:null;
        colsInfo.push({
          i:ci, title:txt(th).slice(0,16), declW: isFinite(declW)?num(declW):null,
          /* thW：**渲染宽**，P17 的另一半。只比 JSON 声明宽（Σ=866）而不管 DOM 上
             是多少，正是「声明 152 渲染 108」能长期假绿的原因 —— 见 R1 / §3.8。 */
          thW: num(th.offsetWidth),
          cellSW: cell?cell.scrollWidth:null, cellCW: cell?cell.clientWidth:null,
          cellOverflow: cell?cs(cell).textOverflow:null, cellWhiteSpace: cell?cs(cell).whiteSpace:null,
          cellSWcCW: (cell&&cell.scrollWidth>cell.clientWidth+1)
        });
      }
      /* P10：sticky 表头。先看声明，再看真滚 200px 后首个 th 是否还在 wrap 顶部 */
      var th0=t.querySelector('thead th');
      var st=th0?cs(th0):null;
      var stickyPos = st?st.position:null, stickyTop = st?st.top:null;
      var scrollTest=null;
      if(wrap.scrollHeight>wrap.clientHeight+4){
        var keep=wrap.scrollTop;
        wrap.scrollTop=200;
        var tr0=wrap.getBoundingClientRect(), hr=th0.getBoundingClientRect();
        scrollTest = (hr.top >= tr0.top-2 && hr.top <= tr0.top+2);
        wrap.scrollTop=keep;
      }
      var foot=document.querySelector('.ant-table-foot');
      /* 「整行」的独立数法：行底 ≤ wrap 底。与上面 floor(可见高/行高) 是两个数，
         差几行就说明「折算说 N 行、其实第 N 行被底边裁掉一条」。
         为什么两个都报：只报折算，读者分不清「9 行都看得见」和「第 9 行只剩一半」。 */
      var fullRows=0;
      for(var rf=0; rf<rows.length; rf++){
        var rb=rows[rf].getBoundingClientRect();
        if(rb.bottom<=wr.bottom+1 && rb.top>=wr.top-1) fullRows++;
      }
      tables.push({
        i:ti, id:t.id||'', tableLayout: cs(t).tableLayout,
        wrapClientW:num(wrap.clientWidth), wrapScrollW:num(wrap.scrollWidth),
        wrapTop:num(wr.top), wrapBottom:num(wr.bottom), visibleH:num(visH),
        rowCount:rows.length, rowHeights:hs, firstRowH:firstRowH,
        visibleRows: (firstRowH&&firstRowH>0)?Math.floor(visH/firstRowH):0,
        fullRows: fullRows,
        cols:colsInfo,
        stickyPos:stickyPos, stickyTop:stickyTop, stickyScrollOK:scrollTest,
        canScroll: wrap.scrollHeight>wrap.clientHeight+4,
        footBottom: foot?num(foot.getBoundingClientRect().bottom):null
      });
    }
    out.tables=tables;
    out.tableCount=tables.length;

    // ---- P11 的一半：MasterDetail 计数。抽屉宽改到 measure 末尾**打开后量**
    //      （R10：读 JSON 的 props.width 等于自证；见 measure 末尾的 drawerOpen 段），
    //      这里只数不渲染的 MasterDetail。
    out.masterDetailCount=C.querySelectorAll('.ant-md').length;

    // ---- P14：首行彩色标签
    out.firstRowTags=(function(){
      var tr=C.querySelector('.ant-table tbody tr'); if(!tr) return [];
      var tags=tr.querySelectorAll('.ant-tag'), out2=[];
      for(var i=0;i<tags.length;i++){
        var bg=cs(tags[i]).backgroundColor||'';
        out2.push({text:txt(tags[i]).slice(0,10), bg:bg, gray:isGray(bg)});
      }
      return out2;
    })();

    // ---- P19：内容区字号档（只统计有非空文本、有盒的元素）
    // 每档附 3 个样本（tag.class）：只报「4 档」而不说「哪 4 档、来自谁」，
    // 改的人得自己在 4000 行 CSS 里猜 —— 上一轮 10px 与 13px 就是这么漏掉的。
    out.fontTiers=(function(){
      var sizes={}, sample={}, tw=document.createTreeWalker(C, NodeFilter.SHOW_TEXT, null), n;
      while((n=tw.nextNode())){
        if(!(n.nodeValue||'').trim()) continue;
        var p=n.parentElement; if(!p) continue;
        var rs=p.getClientRects(); if(!rs.length) continue;
        var fs=parseFloat(cs(p).fontSize); if(!fs) continue;
        sizes[fs]=(sizes[fs]||0)+1;
        if(!sample[fs]) sample[fs]=[];
        if(sample[fs].length<3){
          sample[fs].push(p.tagName.toLowerCase()+(p.className?('.'+String(p.className).split(/\s+/).slice(0,2).join('.')):''));
        }
      }
      out.fontTiersSample=sample;
      return sizes;
    })();

    /* ---- P11 的另一半：抽屉宽（R10）——**打开再量**，不读声明。
       旧做法读 JSON 的 props.width：Drawer 默认关闭、DOM 里没有元素，于是
       「声明 560 / 渲染 420」能长期并存而 P11 一直是绿的 —— 那是把「测量困难」
       当成了「判据依据」。测量口径与 `08` §0.8 的验收方式对齐：打开抽屉量 offsetWidth。

       为什么放在 measure 末尾：抽屉里也有表格与文字，提前打开会污染 P5（噪音）、
       P14（首行标签）、P19（字号档）—— 那些判据量的都是「页面本身」，不是弹层。
       量完立刻关掉并重渲染，产品态（P2a）也不要带着弹层。 */
    out.drawerOpenVia=null; out.drawerOpenErr=null;
    out.drawerDomCount=0; out.drawerDomWidth=null; out.drawerDomClass=null;
    (function(){
      /* 先确认**本页真有 Drawer，且点行确实会开它**再动手。两个理由：
         ① 有的产物的 rowClick 是 navigate 而不是 showDrawer，点一下会换页；
            而 productStage（P2a）在 measure 之后跑 —— 那会量到另一张页面，
            报告上一切正常。这是「判据自己把画布换掉」这类最坏的错。
         ② 容器脚本的作用域**不外露**（实测 `typeof RT / curPage / renderProto` 全是
            `undefined`），所以「置状态再渲染」这条路在探针里走不通 —— 只能走真实交互。
            试不出来就 SKIP（P11 不在 V13 白名单 → 整轮 INCOMPLETE），不退回声明值。 */
      var data=null;
      try{ data=JSON.parse(document.getElementById('iprd-data').textContent); }catch(e){}
      /* build_case 把目标页顶到第 0 位并改了 meta.currentPageId —— 探针里 pages[0] 就是当前页 */
      var pg=data&&data.pages?data.pages[0]:null;
      var mid=null;
      try{
        (function walk(n){
          if(!n||typeof n!=='object'||mid) return;
          if(n.type==='Drawer'){ mid=(n.props&&n.props.modalId)||n.id; return; }
          (n.children||[]).forEach(walk);
        })(pg&&pg.componentTree);
      }catch(e){ out.drawerOpenErr='WALK:'+e.message; }
      var wired = !!(pg&&mid&&(pg.interactions||[]).some(function(ix){
        return (ix.actions||[]).some(function(a){
          return a && a.type==='showDrawer' && (a.drawerId||a.target)===mid;
        });
      }));
      if(!mid){ out.drawerOpenErr='NO-DRAWER-NODE'; return; }
      if(!wired && !document.querySelector('#protoCanvas .ant-drawer')){
        out.drawerOpenErr='NO-SHOWDRAWER-ACTION'; return;
      }

      var dEl=document.querySelector('#protoCanvas .ant-drawer');
      var wasOpen=!!dEl;
      if(!dEl){
        var row=document.querySelector('#protoCanvas .row-click');
        if(row){ try{ row.click(); out.drawerOpenVia='row-click'; }
                 catch(e){ out.drawerOpenErr='CLICK:'+e.message; } }
      }
      dEl=document.querySelector('#protoCanvas .ant-drawer');
      if(!dEl){
        /* 没有「置状态再渲染」的退路：容器脚本作用域不外露（RT/renderProto 都取不到），
           硬取只会抛 ReferenceError。这里如实记原因，由 P11 判 SKIP → 整轮 INCOMPLETE。 */
        out.drawerOpenErr=(out.drawerOpenErr||'')+':CLICK-NOT-OPENED';
        return;
      }
      out.drawerDomCount=1;
      out.drawerDomWidth=num(dEl.getBoundingClientRect().width);
      out.drawerDomClass=String(dEl.className||'');
      /* 量完关掉：产品态（P2a）是「没有弹层」的那一份。
         先走真实路径（点 drawer 里挂了 hideDrawer 的那个按钮），点不掉再把弹层节点从
         DOM 上摘掉 —— 摘之前 width 已经量过了，这一步不影响任何判据的数字。 */
      if(!wasOpen){
        try{
          var hideT=[];
          (pg.interactions||[]).forEach(function(ix){
            if(!ix||!ix.on) return;
            var has=(ix.actions||[]).some(function(a){
              return a && a.type==='hideDrawer' && (a.drawerId||a.target)===mid; });
            if(has&&ix.on.target) hideT.push(ix.on.target);
          });
          hideT.forEach(function(t){
            var btn=document.querySelector('#protoCanvas [data-node-id="'+t+'"]');
            if(btn) btn.click();
          });
        }catch(e){ out.drawerOpenErr=(out.drawerOpenErr||'')+' CLOSE:'+e.message; }
        var still=document.querySelector('#protoCanvas .ant-drawer');
        if(still){
          var mask=still.closest('.ant-drawer-mask');
          if(mask&&mask.parentNode) mask.parentNode.removeChild(mask);
        }
      }
    })();

    return out;
  }

  /* 产品态（P2a）：把渲染结果克隆进一个 1440×900、无评审外壳的舞台。
     为什么克隆而不是改窗口：`--window-size` 只能整页改，改了就没有评审态可比；
     而产品态要的正是「没有外壳」的那一份。锚点仍是 rect 与视口底的交集。

     三条口径（REQ-I07-02，改前三条全错，量到的不是产品态）：
     ① **舞台不再自带 208px 假 Sider**。克隆里已经有页面自己的 Sider，
        再加一条等于装两条导航：内容宽被压掉 208，实测 936（应 1184）。
     ② **舞台不再加左右 padding**（原 `padding:0 20px`）。20×2 是评审台的页边，
        不是产品页的页边，再压 40 → 936 = 1184 − 208 − 40，与实测吻合。
        1440 − 208（页内 sider）= 1232 clientWidth → 内容宽 1184。
     ③ `--tw-max` 里的 `100vh` 是**评审态**的视口高（857 / 757），舞台固定 900。
        原样继承会让 max-height 被 857 锁死（实测 wrap 高被压在 307）；
        而把公式里的 100vh 换成 900px 又会把评审外壳的 428px 余量在产品态再扣一次
        —— 产品态没有那条评审工具栏。所以产品态只钳到舞台高：表格最多占满 900，
        超出部分由舞台裁掉。P2a 量的本来就是「舞台里能露出几条完整行」，
        不是「表格自己声明了多高」。 */
  function productStage(){
    var canvas=document.querySelector('#protoCanvas');
    if(!canvas) return {err:'NO_CANVAS'};
    var ov=document.createElement('div'); ov.id='__prodStage';
    ov.style.cssText='position:fixed;left:0;top:0;width:1440px;height:900px;z-index:99999;'+
                     'background:#f5f5f5;display:flex;overflow:hidden';
    var body=document.createElement('div');
    body.style.cssText='flex:1 1 auto;min-width:0;overflow:auto;background:#f5f5f5';
    ov.appendChild(body);
    document.body.appendChild(ov);
    var clone=canvas.cloneNode(true);
    clone.id=''; clone.style.transform='none'; clone.style.width='100%';
    clone.querySelectorAll('[id]').forEach(function(e){ e.id=''; });
    /* ③ 视口高换算：只改**声明了 vh** 的那一条，不碰其它 maxHeight */
    Array.prototype.forEach.call(clone.querySelectorAll('.ant-table-wrap'), function(w){
      var cur=w.style.getPropertyValue('--tw-max')||'';
      if(cur && cur.indexOf('100vh')>=0) w.style.setProperty('--tw-max','900px');
    });
    body.appendChild(clone);

    var out={w:1440,h:900};
    var C=clone.querySelector('.ant-content');
    var s=C?getComputedStyle(C):null;
    out.contentBoxW = C&&s? num(C.clientWidth - parseFloat(s.paddingLeft||0) - parseFloat(s.paddingRight||0)) : null;
    out.contentClientW = C? num(C.clientWidth) : null;
    var t=clone.querySelector('.ant-table');
    var wrap=t? (t.closest('.ant-table-wrap')||t.parentElement) : null;
    if(!wrap){ out.err='NO_TABLE'; out.stage=ov; return out; }
    var wr=wrap.getBoundingClientRect(), or_=ov.getBoundingClientRect();
    var visH=Math.max(0, Math.min(wr.bottom, or_.bottom) - Math.max(wr.top, or_.top));
    var rows=t.querySelectorAll('tbody tr');
    var hs=[]; for(var i=0;i<rows.length;i++){ if(rows[i].querySelectorAll('td').length>=2) hs.push(rows[i].offsetHeight); }
    var firstRowH=hs.length?hs[0]:null;
    var foot=clone.querySelector('.ant-table-foot');
    out.tableTop=num(wr.top); out.visibleH=num(visH); out.rowCount=rows.length;
    out.firstRowH=firstRowH;
    out.visibleRows = (firstRowH&&firstRowH>0)?Math.floor(visH/firstRowH):0;
    out.wrapClientW=num(wrap.clientWidth);
    out.wrapScrollW=num(wrap.scrollWidth);
    out.wrapBottom=num(wr.bottom);
    out.footBottom=foot?num(foot.getBoundingClientRect().bottom):null;
    out.err=null;
    return out;
  }

  function emit(d){
    var el=document.createElement('div'); el.id='__shapeout';
    el.setAttribute('data-json', JSON.stringify(d));
    (document.body||document.documentElement).appendChild(el);
  }

  function waitInit(cb){
    var tries=0;
    function tick(){
      tries++;
      var sel=document.querySelector('#stateSelect');
      var node=document.getElementById('iprd-data');
      var ok=false;
      if(sel && node){
        try{
          var d=JSON.parse(node.textContent);
          var m=/^#\/?([A-Za-z0-9_\-]+)/.exec(location.hash||'');
          var pid=(m&&m[1])||(d.meta&&d.meta.currentPageId)||((d.pages||[])[0]||{}).id;
          var p=null; (d.pages||[]).forEach(function(x){ if(x.id===pid) p=x; });
          var want=p?((p.states||[]).length):0;
          ok = (sel.options.length===want);
        }catch(e){ ok=false; }
      }
      if(!ok && tries<600){ setTimeout(tick,16); return; }
      /* 折叠 PRD 后要等重排稳定。这里用 setTimeout 而不是两帧 rAF：
         headless 的 `--virtual-time-budget` 只快进定时器，rAF 在虚拟时间下可能一帧都不来
         —— 实测同一产物两次跑，一次产出一次不产出（ENV: 探针没有产出），就是这个原因。 */
      setTimeout(function(){ setTimeout(function(){ cb(tries); }, 32); }, 32);
    }
    if(document.readyState==='complete'){ setTimeout(tick,0); }
    else { window.addEventListener('load', function(){ setTimeout(tick,0); }); }
  }

  waitInit(function(tries){
    /*__INJECT__*/
    var d=null, e=null;
    try{ d=measure(); }catch(ex){ e='MEASURE:'+ex.message; }
    if(d){ d.tries=tries; d.settled=true; }
    else { d={settled:false, tries:tries, err:e}; }
    try{ d.product=productStage(); }catch(ex2){ d.product={err:'PRODUCT:'+ex2.message}; }
    emit(d);
  });
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


# ------------------------------------------------------------------ 夹具
PAGE_TYPES = ("Table",)


def iter_nodes(n):
    if not isinstance(n, dict):
        return
    yield n
    for c in (n.get("children") or []):
        for x in iter_nodes(c):
            yield x


def content_of(page):
    tree = page.get("componentTree") or {}
    for n in iter_nodes(tree):
        if n.get("type") == "Content":
            return n
    return None


def content_direct_tables(page):
    """Content 直属子树（只下钻 Space/Row/Col/Divider，不钻 Card/Form/Drawer）里的 Table。

    为什么不搜整棵树：详情页的明细表也在 Content 里，但被 Card/Descriptions 包着。
    「列表页」的表格是**内容区的主结构**，与标题带同一层。这个定义写在脚本里，
    换判据要同时改这里和 §6.2，否则「今天几个列表页」会各说各的。
    """
    C = content_of(page)
    if not C:
        return []
    out = []
    stack = list(C.get("children") or [])
    while stack:
        n = stack.pop(0)
        if not isinstance(n, dict):
            continue
        if n.get("type") == "Table":
            out.append(n)
        elif n.get("type") in ("Space", "Row", "Col", "Divider", "Content"):
            stack.extend(n.get("children") or [])
    return out


def is_work_list_page(page):
    """作业型列表页 = Content 直属有 Table，且带分页或 ≥5 行数据，且不含 MasterDetail。

    「或 ≥5 行」这一条是给没有分页的老产物留的；只有 2–3 行明细的详情页因此被排除。
    """
    tabs = content_direct_tables(page)
    if not tabs:
        return False
    if any(n.get("type") == "MasterDetail" for n in iter_nodes(page.get("componentTree") or {})):
        return False
    for t in tabs:
        p = t.get("props") or {}
        if p.get("pagination"):
            return True
        if len(p.get("data") or []) >= 5:
            return True
    return False


def pick_page(data, want=None):
    pages = data.get("pages") or []
    if want:
        for p in pages:
            if p.get("id") == want:
                return p
        raise EnvError("找不到页面 %s（有：%s）" % (want, ", ".join(p.get("id", "") for p in pages)))
    for p in pages:
        if is_work_list_page(p):
            return p
    return None


def build_case(container, data, page_id, out_html):
    """把目标页顶到第 0 位 + 改 meta.currentPageId，再注入探针。

    两处都要改：容器初始化按 LS → hash → meta.chapters → pages[0] 的优先级链挑页，
    只改一处会量到**另一张页面**，而报告上一切正常——这是最坏的一种错。
    """
    src = Path(container).read_text(encoding="utf-8")
    return build_case_src(src, data, page_id, out_html)


def run_viewport(chrome, html_path, width, height, retry=0):
    """跑一档视口。retry 只用于「没有产出」这一种故障，且必须把 retry 数打出来。

    为什么不静默重试：`run.sh` 的勘误 E-03 定过规矩——重试后通过不等于一次通过，
    retry>0 要进输出。这里同规矩：`RETRY=1` 打在 CASE 行上。
    """
    prof = tempfile.mkdtemp(prefix="xx-prd-shape-prof-")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
           "--disable-extensions", "--user-data-dir=" + prof,
           "--window-size=%d,%d" % (width, height),
           "--virtual-time-budget=12000", "--dump-dom", "file://" + str(html_path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
        if Path(prof).exists():
            print("CLEAN_FAILED=%s" % prof)
    dom = r.stdout or ""
    m = re.search(r'id="__shapeout"[^>]*data-json="([^"]*)"', dom)
    if not m:
        if retry < 1:
            print("  .. 未拿到探针产出（%dx%d），重试一次" % (width, height))
            return run_viewport(chrome, html_path, width, height, retry + 1)
        raise EnvError("探针没有产出（exit=%d, dom_bytes=%d）" % (r.returncode, len(dom)))
    d = json.loads(htmlmod.unescape(m.group(1)))
    if not d.get("settled"):
        if retry < 1:
            print("  .. 探针未稳定（%dx%d），重试一次" % (width, height))
            return run_viewport(chrome, html_path, width, height, retry + 1)
        raise EnvError("探针跑满 %s 帧仍未稳定（err=%s）" % (d.get("tries"), d.get("err")))
    d["_want"] = [width, height]
    d["_retry"] = retry
    return d


# ------------------------------------------------------------------ 判据
def fmt(v, unit=""):
    if v is None:
        return "—"
    if isinstance(v, float):
        return ("%.1f" % v) + unit
    return str(v) + unit


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def verdict(rows, pid, title, value, threshold, status, note=""):
    rows.append({"id": pid, "title": title, "value": value, "threshold": threshold,
                 "status": status, "note": note})


def accept_tier(content_w):
    """内容宽 → 验收档（866 / 1026），容差 ACCEPT_TOL。口径见文件头 CHANGELOG a。"""
    if content_w is None:
        return None
    for w in ACCEPT_W:
        if abs(content_w - w) <= ACCEPT_TOL:
            return w
    return None


def evaluate(props, dom, page, vw):
    """返回 rows。props=Python 侧从 JSON 读到的（列宽/pagination/Drawer），dom=几何。"""
    rows = []
    tables = dom.get("tables") or []
    t0 = tables[0] if tables else None
    cw = dom.get("contentBoxW")
    tier = accept_tier(cw)
    is_accept = tier is not None

    # ---- P1 统计卡
    verdict(rows, "P1", "列表页统计卡数", fmt(dom.get("statCount")), "0",
            "PASS" if dom.get("statCount") == 0 else "FAIL",
            "Content 内 .ant-stat；统计只允许独立统计页")

    # ---- P2a 产品态一屏行数
    prod = dom.get("product") or {}
    if prod.get("err") or prod.get("rowCount") is None:
        verdict(rows, "P2a", "产品态一屏整行数", "—", "≥%d" % TARGET_ROWS_PRODUCT,
                "SKIP", "产品态夹具未建立（%s）" % (prod.get("err") or "无表格"))
    elif prod.get("rowCount") < 20:
        verdict(rows, "P2a", "产品态一屏整行数", "夹具 %d 行" % prod["rowCount"],
                "≥%d" % TARGET_ROWS_PRODUCT, "SKIP", "夹具不足 20 行，行数可被「少造数据」作弊")
    elif (prod.get("contentBoxW") or 0) < 1100:
        # 守卫（REQ-I07-02 ③）：舞台口径错了就不判绿也不判红。
        # 产品态内容宽应 ≈1184（1440 − sider 208 − 0 边距）；小到 1100 以下
        # 说明舞台上又叠了外壳（多一条 Sider / 多一圈 padding），量到的不是产品态。
        verdict(rows, "P2a", "产品态一屏整行数", "内容宽 %s" % fmt(prod.get("contentBoxW")),
                "≥%d" % TARGET_ROWS_PRODUCT, "SKIP",
                "产品态口径错：内容宽 <1100，舞台上可能又叠了外壳")
    else:
        n = prod.get("visibleRows")
        verdict(rows, "P2a", "产品态一屏整行数（1440×900 无外壳）", fmt(n), "≥%d" % TARGET_ROWS_PRODUCT,
                "PASS" if (n or 0) >= TARGET_ROWS_PRODUCT else "FAIL",
                "内容宽 %s，表格起 %s，可见高 %s，行高 %s"
                % (fmt(prod.get("contentBoxW")), fmt(prod.get("tableTop")),
                   fmt(prod.get("visibleH")), fmt(prod.get("firstRowH"))))

    # ---- P2b 评审态一屏行数
    target = TARGET_ROWS_REVIEW.get(vw, TARGET_ROWS_REVIEW[1440])
    if not t0:
        verdict(rows, "P2b", "评审态一屏整行数", "—", "≥%d" % target, "SKIP", "页面无表格")
    elif t0.get("rowCount", 0) < 20:
        verdict(rows, "P2b", "评审态一屏整行数", "夹具 %d 行" % t0["rowCount"],
                "≥%d" % target, "SKIP", "夹具不足 20 行")
    else:
        n = t0.get("visibleRows")
        fr = t0.get("fullRows")
        # 两个数并打（team-lead 裁定 2）。判定仍只看「折算」，公式与阈值本轮都不动 ——
        # 改公式会把目标值一起动（9/12 → 8/11），那是把「差一行」洗成「达标」。
        # 但只报折算会让人分不清「9 行都看得见」和「第 9 行只剩半条」：
        # 折算的可见高是从 wrap 顶边算的，顶边之下第一行是**表头**，所以折算天然多算一行。
        verdict(rows, "P2b", "评审态一屏整行数（含外壳）",
                "%s 折算 / %s 整行" % (fmt(n), fmt(fr)), "≥%d" % target,
                "PASS" if (n or 0) >= target else "FAIL",
                "wrap %s→%s，可见高 %s，行高 %s；折算含表头（可见高从 wrap 顶边算），"
                "整行=行底≤wrap 底。差 %s 行即最后一行被底边裁掉一条"
                % (fmt(t0.get("wrapTop")), fmt(t0.get("wrapBottom")), fmt(t0.get("visibleH")),
                   fmt(t0.get("firstRowH")),
                   (n - fr) if (n is not None and fr is not None) else "—"))

    # ---- P3 筛选区栅格形态 + 总高
    f = dom.get("filter") or {}
    if not f.get("exists"):
        verdict(rows, "P3", "筛选区形态", "无筛选区", "2 行×3 列 且 ≤%d" % FILTER_MAX_H, "SKIP",
                "列表页应有筛选区；无筛选区时该条不成立")
    else:
        ok_shape = (f.get("rows") == 2 and f.get("firstRowCount") == FILTER_COLS)
        ok_h = (f.get("h") or 0) <= FILTER_MAX_H
        # 行列与高度分开打：只报「高度已达成」是假绿（去掉 label 换 placeholder 也能掉到 96）
        verdict(rows, "P3a", "筛选区栅格", "%s 行 × %s 列（%s）"
                % (fmt(f.get("rows")), fmt(f.get("firstRowCount")), f.get("kind")),
                "2 行 × 3 列", "PASS" if ok_shape else "FAIL")
        verdict(rows, "P3b", "筛选区总高", fmt(f.get("h"), "px"), "≤%d" % FILTER_MAX_H,
                "PASS" if ok_h else "FAIL")

    # ---- P4 控件宽（预算 = 该档栅格列宽 − 84，±2 且 ≥160；§3.4 的裁定）
    cw_list = [w for w in (f.get("ctlW") or []) if w]
    exp4 = None
    if cw is not None:
        col_w = (cw - 2 * FB_PAD - 2 * FB_BORDER - 2 * FB_GAP) / FILTER_COLS
        exp4 = col_w - FB_LABEL - FB_LABEL_GAP
    if not f.get("exists"):
        verdict(rows, "P4", "筛选控件宽（min/中位）", "无筛选区", "列宽−84 ±2 且 ≥%d" % CTL_MIN_W,
                "SKIP", "无筛选区")
    elif f.get("kind") != "grid3":
        # 旧一行式（.qf / .qf-ctl）：**不 SKIP**。
        # 一开始这里写的是 SKIP（「没有 3 列栅格，控件宽没有可比预算」），但它把门放空了：
        # legacy 筛选区实测就是 `1 行 × 3 列`（P3a 看得见），栏宽一样能用同一公式推出来；
        # 且 V10 只允许 P8/P13/P17 在前置不成立时 SKIP —— P4 不在名单里。
        # 所以按同一预算算，不达标就红：存量产物本来就是这个红，SKIP 等于替它免检。
        if exp4 is None or not cw_list:
            verdict(rows, "P4", "筛选控件宽（min/中位）", "—", "列宽−84 ±2 且 ≥%d" % CTL_MIN_W,
                    "SKIP", "量不到内容宽或控件宽")
        else:
            lo, mid = min(cw_list), median(cw_list)
            dev = max(abs(w - exp4) for w in cw_list)
            ok = dev <= CTL_TOL and exp4 >= CTL_MIN_W
            verdict(rows, "P4", "筛选控件宽（min/中位）",
                    "%s / %s（%s）" % (fmt(lo), fmt(mid), f.get("kind")),
                    "列宽−84=%s ±%d 且 ≥%d" % (fmt(round(exp4, 1)), CTL_TOL, CTL_MIN_W),
                    "PASS" if ok else "FAIL",
                    "控件所在布局是 legacy 一行式（同一档位仍按 3 列栅格预算判）："
                    "栏宽=(内容宽%s−2×%d−2×%d−2×%d)/3=%s，控件=栏宽−%d=%s；实测最大偏差 %s（n=%d）"
                    % (fmt(cw), FB_PAD, FB_BORDER, FB_GAP, fmt(exp4 + FB_LABEL + FB_LABEL_GAP),
                       FB_LABEL + FB_LABEL_GAP, fmt(round(exp4, 1)), fmt(dev), len(cw_list)))
    elif exp4 is None or not cw_list:
        verdict(rows, "P4", "筛选控件宽（min/中位）", "—", "列宽−84 ±2 且 ≥%d" % CTL_MIN_W,
                "SKIP", "量不到内容宽或控件宽")
    else:
        lo, mid = min(cw_list), median(cw_list)
        dev = max(abs(w - exp4) for w in cw_list)
        ok = dev <= CTL_TOL and exp4 >= CTL_MIN_W
        verdict(rows, "P4", "筛选控件宽（min/中位）", "%s / %s" % (fmt(lo), fmt(mid)),
                "列宽−84=%s ±%d 且 ≥%d" % (fmt(round(exp4, 1)), CTL_TOL, CTL_MIN_W),
                "PASS" if ok else "FAIL",
                "预算推导：栏宽=(内容宽%s−2×%d−2×%d−2×%d)/3=%s，控件=栏宽−%d=%s；"
                "实测最大偏差 %s（n=%d，高 %s）"
                % (fmt(cw), FB_PAD, FB_BORDER, FB_GAP,
                   fmt(round((cw - 2 * FB_PAD - 2 * FB_BORDER - 2 * FB_GAP) / FILTER_COLS, 1)),
                   FB_LABEL + FB_LABEL_GAP, fmt(round(exp4, 1)), fmt(round(dev, 1)),
                   len(cw_list), fmt(median(f.get("ctlH") or []))))

    # ---- P5 三层噪音
    nz = dom.get("noiseCount")
    sample = ""
    if dom.get("noise"):
        sample = "；样本 " + ", ".join(
            "%s.%s" % (x.get("tag"), x.get("cls", "").split()[0] if x.get("cls") else "")
            for x in dom["noise"][:3])
    verdict(rows, "P5", "三层噪音元素数（border+bg+shadow）", fmt(nz), "0",
            "PASS" if nz == 0 else "FAIL", "Drawer/Modal 豁免" + sample)

    # ---- P6 左边界竖线极差（区块盒口径，见 CHANGELOG b）
    # 只收**左对齐**的区块：内容区自身 / 筛选区 / 表格容器 / 提示条。
    # 主操作按钮不纳入 —— 它按设计靠右（标题带右端），拿它算极差会让「设计对」常红。
    # 它作为参考列打出来，用于回答「主操作是不是跑到筛选区里去了」（那是 P12 的事）。
    ed = dom.get("edges") or {}
    base = ed.get("contentEdge")
    picks = {k: v for k, v in ed.items()
             if k in ("filterBar", "tableWrap", "alert") and v is not None}
    if len(picks) < 2 or base is None:
        verdict(rows, "P6", "左边界竖线极差", "—", "≤%d" % LEFT_EDGE_TOL, "SKIP",
                "可比的左对齐区块 <2 个（筛选区 / 表格 / 提示条）")
    else:
        allv = list(picks.values()) + [base]
        spread = max(allv) - min(allv)
        verdict(rows, "P6", "左边界竖线极差（区块盒）", fmt(spread, "px"), "≤%d" % LEFT_EDGE_TOL,
                "PASS" if spread <= LEFT_EDGE_TOL else "FAIL",
                "竖线 " + " / ".join("%s=%s" % (k, fmt(v)) for k, v in sorted(picks.items()))
                + " / 内容=%s" % fmt(base)
                + "；参考：主操作 left=%s，文本左边界 " % fmt(ed.get("primary"))
                + " / ".join("%s=%s" % (k, fmt(v))
                             for k, v in sorted((dom.get("textEdges") or {}).items())
                             if v is not None))

    # ---- P7 列宽声明率 + table-layout
    cols = props["cols"]
    decl = [c for c in cols if c.get("declW")]
    rate = (len(decl) / len(cols)) if cols else 0
    layout = (t0 or {}).get("tableLayout")
    ok7 = cols and rate >= DECL_RATE_MIN and layout == "fixed"
    verdict(rows, "P7", "列宽声明率 / 布局",
            "%d/%d=%.0f%% / %s" % (len(decl), len(cols), rate * 100, layout or "—"),
            "≥80% 且 fixed", "PASS" if ok7 else "FAIL",
            "声明率按 columns 的 width 非空计，不按渲染后列宽")

    # ---- P8 横向溢出（验收态）
    if not t0:
        verdict(rows, "P8", "横向溢出", "—", "≤clientWidth+2", "SKIP", "无表格")
    elif not is_accept:
        verdict(rows, "P8", "横向溢出", "内容宽 %s" % fmt(cw), "≤clientWidth+2", "SKIP",
                "非验收态（内容宽需落在 866±%d 或 1026±%d）" % (ACCEPT_TOL, ACCEPT_TOL))
    else:
        sw, cl = t0.get("wrapScrollW"), t0.get("wrapClientW")
        ok = sw is not None and cl is not None and sw <= cl + 2
        verdict(rows, "P8", "横向溢出（验收态 %s）" % fmt(cw), "scroll %s / client %s" % (fmt(sw), fmt(cl)),
                "≤client+2", "PASS" if ok else "FAIL")

    # ---- P9 行高一致性
    hs = [h for h in (t0 or {}).get("rowHeights") or [] if h]
    if len(hs) < 2:
        verdict(rows, "P9", "行高一致性", "—", "极差≤2 且 ≤%d" % ROW_MAX_H, "SKIP", "有效数据行 <2")
    else:
        spread = max(hs) - min(hs)
        mx = max(hs)
        verdict(rows, "P9", "行高一致性（跨 tr）", "极差 %s / 最高 %s" % (fmt(spread), fmt(mx)),
                "极差≤2 且 ≤%d" % ROW_MAX_H, "PASS" if spread <= 2 and mx <= ROW_MAX_H else "FAIL",
                "n=%d" % len(hs))

    # ---- P10 表头吸附
    if not t0:
        verdict(rows, "P10", "表头吸附", "—", "sticky/top:0", "SKIP", "无表格")
    else:
        pos, top = t0.get("stickyPos"), t0.get("stickyTop")
        ok = pos == "sticky" and top in ("0px", "0")
        sct = t0.get("stickyScrollOK")
        note = "声明 %s/%s；滚动验证 %s" % (pos, top, "NA(不可滚)" if sct is None
                                            else ("PASS" if sct else "FAIL"))
        if sct is False:
            ok = False
        verdict(rows, "P10", "表头吸附", "%s / top %s" % (pos or "—", top or "—"),
                "sticky/top:0", "PASS" if ok else "FAIL", note)

    # ---- P11 详情形态（R10：渲染侧判据，不再读 JSON 声明）
    #
    # 旧版读 `props.width` 并注明「Drawer 默认关闭时不渲染 DOM，故读 JSON」。
    # 那句话是把**测量困难**当成了**判据依据**：声明 560、渲染 420 可以同时成立，
    # 而判据一直绿 —— 与 R1「width:48 缺 px」同型（声明与渲染脱钩，判据锚在声明上）。
    # 现在量的是**打开态**的 offsetWidth（探针在 measure 末尾打开再量）；
    # 声明值只打印，不参与判定。打不开 → SKIP（V13 白名单外 → 整轮 INCOMPLETE），
    # 绝不退回声明值判绿。
    dw = props["drawerW"]
    rend = dom.get("drawerDomWidth")
    via = dom.get("drawerOpenVia") or "—"
    operr = dom.get("drawerOpenErr")
    if props["drawerCount"] != 0 and rend is None:
        verdict(rows, "P11", "详情形态（Drawer 数/宽，MasterDetail 数）",
                "%d 个 drawer（声明 %s / 渲染 —）/ %d 个 MD"
                % (props["drawerCount"], fmt(dw), props["mdCount"]),
                "1 个 ≥560（渲染）且 0 个 MD", "SKIP",
                "抽屉打不开（%s），量不到渲染宽；"
                "不用声明值兜底 —— 那就退回假绿了"
                % (operr or "无 row-click 或没有挂 showDrawer 的交互"))
    else:
        ok11 = (props["drawerCount"] == 1 and rend is not None and rend >= 560
                and props["mdCount"] == 0)
        verdict(rows, "P11", "详情形态（Drawer 数/宽，MasterDetail 数）",
                "%d 个 drawer（声明 %s / 渲染 %s）/ %d 个 MD"
                % (props["drawerCount"], fmt(dw), fmt(rend), props["mdCount"]),
                "1 个 ≥560（渲染）且 0 个 MD", "PASS" if ok11 else "FAIL",
                "打开态实量 offsetWidth（%s）；声明值只打印，不参与判定" % via)

    # ---- P12 主操作唯一且与 h1 同行（§3.5 重写口径）
    #
    # 旧口径「全页恰 1 个 primary」与本项目的既定形态**必然冲突**：§4.2 的筛选动作行
    # 就是 `[重置][查询 primary][收起]`，AntD 查询表格的「查询」天生是主色。若坚持
    # 全页 1 个，只能把「查询」降级成默认按钮 —— 那是用判据改产品（Owner 已看过实物并认可）。
    # 新口径把「唯一」限定在标题带，全页放开到 2 且第二个只能是筛选动作行的查询：
    #   ① 标题带内 primary 恰 1 个（主操作）；
    #   ② 全页 primary ≤2，标题带以外的那个必须在 .fb-actions 里；
    #   ③ 标题带 primary 与 h1 的 top 差 ≤8（同一视觉行）；
    #   ④ h1 字号 ≥16 且 font-weight ≥600（页面得有标题层级）。
    prim = dom.get("primaryBtns") or []
    h1 = dom.get("h1")
    band_prim = [p for p in prim if p.get("band")]
    outside = [p for p in prim if not p.get("band")]
    ok_band = len(band_prim) == 1
    ok_total = len(prim) <= 2
    ok_second = all(p.get("qact") for p in outside)
    ok_h1 = bool(h1) and (h1.get("size") or 0) >= 16 and (h1.get("weight") or 0) >= 600
    dt = abs((band_prim[0].get("top") or 0) - (h1.get("top") or 0)) if (band_prim and h1) else None
    ok_near = dt is not None and dt <= 8
    detail = "；".join(
        "「%s」%s" % (p.get("text"), "标题带" if p.get("band")
                     else ("筛选动作行" if p.get("qact") else "其它位置"))
        for p in prim) or "无 primary"
    if not prim:
        verdict(rows, "P12", "主操作唯一且与 h1 同行", "0 个 primary",
                "标题带 1 个 / 全页 ≤2", "FAIL", "列表页必须有主操作")
    elif not h1:
        verdict(rows, "P12", "主操作唯一且与 h1 同行", "%d 个 primary，无 h1" % len(prim),
                "标题带 1 个 / 全页 ≤2", "FAIL",
                "列表页必须有 h1（≥16px / ≥600）；%s" % detail)
    else:
        ok = ok_band and ok_total and ok_second and ok_near and ok_h1
        verdict(rows, "P12", "主操作（标题带 / 全页 / Δtop / h1）",
                "%d 个 / Δtop %s / h1 %s %s" % (len(prim), fmt(dt), fmt(h1.get("size")), h1.get("weight")),
                "带内 1 个，全页 ≤2，Δtop≤8，h1 ≥16 且 ≥600",
                "PASS" if ok else "FAIL",
                "分布：%s%s" % (detail,
                                "" if ok_h1 else "；h1 未达 16px/600"))

    # ---- P13 分页密度
    total, ps = props["total"], props["pageSize"]
    if total is None or total < 100:
        verdict(rows, "P13", "分页密度", "total=%s" % fmt(total), "total≥100 时 pageSize≥20",
                "SKIP", "total<100，无需加密分页")
    else:
        ok = ps is not None and ps >= 20
        verdict(rows, "P13", "分页密度", "pageSize=%s / total=%s" % (fmt(ps), fmt(total)),
                "pageSize≥20", "PASS" if ok else "FAIL")

    # ---- P14 每行彩色标签
    tags = dom.get("firstRowTags") or []
    colored = [t for t in tags if not t.get("gray")]
    ok14 = len(colored) <= 1
    verdict(rows, "P14", "首行彩色标签数", "%d（总 %d）" % (len(colored), len(tags)), "≤1",
            "PASS" if ok14 else "FAIL",
            "灰字不算彩色：" + (", ".join("%s[%s]" % (t.get("text"), t.get("bg")) for t in tags[:4]) or "无"))

    # ---- P15 评审态默认宽（A 层）
    pdw = dom.get("paneDefaultW")
    need = PANE_MIN.get(vw)
    if pdw is None or need is None:
        verdict(rows, "P15", "评审态默认 pane 宽", "—", "—", "SKIP", "非目标视口")
    else:
        verdict(rows, "P15", "评审态默认 pane 宽（A 层）", fmt(pdw, "px"), "≥%d" % need,
                "PASS" if pdw >= need else "FAIL",
                "开页默认态；%s" % ("已折叠 PRD" if dom.get("prdCollapsedAtStart") else "三栏全开"))

    # ---- P16 分页在首屏内
    fb = (t0 or {}).get("footBottom")
    if fb is None:
        verdict(rows, "P16", "分页在首屏内", "—", "bottom ≤ innerHeight", "SKIP", "无分页脚")
    else:
        vh = dom.get("vh")
        verdict(rows, "P16", "分页在首屏内", "bottom %s / vh %s" % (fmt(fb), fmt(vh)),
                "bottom ≤ vh", "PASS" if fb <= (vh or 0) else "FAIL")

    # ---- P17 列宽预算闭合（**只判 866 档**，§3.6）
    #
    # 为什么单档化：一份产物只有一套 columns（D-3：列集生成时定、不运行时切）。
    # 866 要 8 列、1026 要 9 列，除非造两份 JSON 或运行时切列 —— 前者会让两份教材必然漂移，
    # 后者已被 D-3 关闭。所以只判两端点里**更挤**的那一端；1026 必然放得下
    # （fixed 把多出的 160px 按比例摊给各列，P8 两档都判）。
    #
    # 两半都要判（§3.8）：
    #   ① 声明侧：Σ 声明宽 == 内容宽（±2）、列数 == 目标列数、每列 ≥48；
    #   ② **渲染侧**：每列 th 的 offsetWidth == 声明宽（±2）。
    # 只判①时，「width:48」漏写 px 的 bug 可以一路绿到底 —— 那是本轮的头号假绿。
    dom_cols = (t0 or {}).get("cols") or []
    width_detail = ""
    if cols:
        width_detail = "；列宽 声明/渲染/差：" + "，".join(
            "%s %s/%s/%s" % (c.get("title"),
                             fmt(c.get("declW")), fmt(dc.get("thW")),
                             fmt(round((dc.get("thW") or 0) - (c.get("declW") or 0), 1))
                             if dc.get("thW") is not None and c.get("declW") is not None else "—")
            for c, dc in zip(cols, dom_cols))
    if not t0:
        verdict(rows, "P17", "列宽预算闭合", "—", "|Σ−内容宽|≤2 且渲染=声明±2", "SKIP", "无表格")
    elif tier != 866:
        verdict(rows, "P17", "列宽预算闭合", "内容宽 %s / Σ声明 %s / %d 列 / 渲染宽 %s"
                % (fmt(cw), fmt(props["sumW"]), props["colCount"], fmt((t0 or {}).get("wrapClientW"))),
                "|Σ−内容宽|≤2 且渲染=声明±2", "SKIP",
                "列集目标档 866（D-3：列集生成时定、不运行时切）；该档 %d 列按比例拉伸 → "
                "渲染宽 %s / 声明 Σ %s，预算闭合只在 866 档判"
                % (props["colCount"], fmt((t0 or {}).get("wrapClientW")), fmt(props["sumW"])))
    else:
        want_cols = ACCEPT_W[tier]
        bad_w = [(c.get("title"), c.get("declW"), d.get("thW"))
                 for c, d in zip(cols, dom_cols)
                 if c.get("declW") is None or d.get("thW") is None
                 or abs(d["thW"] - c["declW"]) > COL_W_TOL]
        ok = (props["sumW"] is not None and cw is not None
              and abs(props["sumW"] - cw) <= 2
              and props["colCount"] == want_cols
              and all(c.get("declW") and c["declW"] >= 48 for c in cols)
              and not bad_w)
        verdict(rows, "P17", "列宽预算闭合（验收态 %s）" % fmt(cw),
                "Σ %s / 内容宽 %s / %d 列（应 %d）%s"
                % (fmt(props["sumW"]), fmt(cw), props["colCount"], want_cols,
                   "" if not bad_w else " / 渲染不符 %d 列" % len(bad_w)),
                "|Σ−内容宽|≤2 且 渲染=声明±2", "PASS" if ok else "FAIL",
                "每列 ≥48" + width_detail
                + ("" if not bad_w else "；越差列：" + ", ".join(
                    "%s 声明 %s 渲染 %s" % (t, fmt(dw), fmt(rw)) for t, dw, rw in bad_w)))

    # ---- P18 省略号按列配置（两个条件同时成立，§3.9）
    #  ① 配了 ellipsis 的列 ≤3（多了就是「全都截断」，等于没有信息层级）；
    #  ② **配了的列集合 == 真溢出列集合**。旧实现只要求「配了的列都真溢出」，
    #     于是漏配的列可以悄悄裁字 —— 任务单号 / 批次号正是这样被裁了两轮没人发现。
    ell_idx = [i for i, c in enumerate(cols) if c.get("ellipsis")]
    dom_cells = (t0 or {}).get("cols") or []
    overflowing = [c["i"] for c in dom_cells if c.get("cellSWcCW")]
    layout18 = (t0 or {}).get("tableLayout")
    if not cols:
        verdict(rows, "P18", "省略号按列配置", "—", "≤3 列且集合相等", "SKIP", "无列")
    elif layout18 != "fixed":
        # 前置：只有 fixed 布局（+ nowrap）才会「裁字」。auto 布局下单元格改折行，
        # scrollWidth 永远不会超过 clientWidth —— 「真溢出列集合」恒为空。
        #
        # 这里**判 FAIL 而不是 SKIP**：SKIP 会让存量产物（example-05 是 auto + 2/7 声明率）
        # 在这条上免检，等于悄悄把门放空。语义上「列宽不由声明决定」时，任何 ellipsis 配置
        # 都无从生效 —— 这本身就是不合规，只是它和 P7 是同一缺陷的两个面（P7 管声明率，
        # P18 管省略号效果），不是重复计数。V10 允许 SKIP 的只有 P8/P13/P17。
        lay = layout18 or "—"
        verdict(rows, "P18", "省略号按列配置",
                "前置不成立：tableLayout=%s，配了 %d 列 ellipsis（生效与否量不到）"
                % (lay, len(ell_idx)),
                "≤%d 列且集合相等" % ELLIPSIS_MAX_COLS, "FAIL",
                f"前置不成立：tableLayout={lay} —— 列宽由内容决定，配了 ellipsis 也不生效。"
                f"这不是「没配置」，是「配了也没用」；先让 P7 过"
                f"（列宽声明率 ≥80% 且 fixed）再谈省略号")
    else:
        def names(idx):
            return "/".join(str(cols[i].get("title")) for i in idx if i < len(cols)) or "无"
        ok = len(ell_idx) <= ELLIPSIS_MAX_COLS and sorted(ell_idx) == sorted(overflowing)
        miss = [i for i in overflowing if i not in ell_idx]
        extra = [i for i in ell_idx if i not in overflowing]
        verdict(rows, "P18", "省略号按列配置",
                "配了 %d 列（%s），真溢出 %d 列（%s）"
                % (len(ell_idx), names(ell_idx), len(overflowing), names(overflowing)),
                "≤%d 列且集合相等" % ELLIPSIS_MAX_COLS, "PASS" if ok else "FAIL",
                "漏配（会裁字）：%s；空配（装饰）：%s；溢出判据 scroll>client+1"
                % (names(miss) if miss else "无", names(extra) if extra else "无"))

    # ---- P19 字号档
    ft = dom.get("fontTiers") or {}
    sizes = sorted(float(k) for k in ft.keys())
    if not sizes:
        verdict(rows, "P19", "列表页字号档", "—", "≤%d 档" % FONT_TIERS_MAX, "SKIP", "量不到文本")
    else:
        ok = len(sizes) <= FONT_TIERS_MAX
        sample = dom.get("fontTiersSample") or {}
        detail = "；".join("%s→%s" % (round(s, 1), "/".join(
            sample.get(str(int(s)) if float(s).is_integer() else str(s), []) or sample.get("%.0f" % s, [])))
            for s in sizes)
        verdict(rows, "P19", "列表页字号档", "%d 档 %s" % (len(sizes), [round(s, 1) for s in sizes]),
                "≤%d 档" % FONT_TIERS_MAX, "PASS" if ok else "FAIL",
                "各档来源（前 3 个样本）：%s" % (detail or "—"))

    return rows


# ------------------------------------------------------------------ props 侧
def props_of(page, dom):
    """从 JSON 读那些「DOM 量不到 / 量了会被自证」的东西。"""
    C = content_of(page)
    tables = content_direct_tables(page)
    t = tables[0] if tables else None
    tp = (t or {}).get("props") or {}

    # 列宽：读声明值。渲染后的 offsetWidth 之和恒等于表宽（fixed 布局按比例缩放），
    # 用它验预算等于让判据自证——必须读 JSON 里写的 width。
    cols = []
    for c in (tp.get("columns") or []):
        w = c.get("width")
        try:
            w = float(w) if w is not None and str(w).strip() != "" else None
        except (TypeError, ValueError):
            w = None
        cols.append({"title": c.get("title"), "declW": w,
                     "ellipsis": bool(c.get("ellipsis") or c.get("ellipsisCol"))})
    pg = tp.get("pagination") if isinstance(tp.get("pagination"), dict) else {}
    total = (pg or {}).get("total")
    page_size = (pg or {}).get("pageSize")

    drawers = [n for n in iter_nodes(page.get("componentTree") or {}) if n.get("type") == "Drawer"]
    dr_w = None
    if drawers:
        p = drawers[0].get("props") or {}
        w = p.get("width")
        if isinstance(w, (int, float)):
            dr_w = w
        elif isinstance(w, str) and w.strip().isdigit():
            dr_w = int(w.strip())
        elif "w-lg" in str(p.get("class") or "") or "w-lg" in str(p.get("className") or ""):
            dr_w = 560

    md = [n for n in iter_nodes(page.get("componentTree") or {}) if n.get("type") == "MasterDetail"]

    return {
        "cols": cols, "colCount": len(cols),
        "sumW": sum(c["declW"] for c in cols if c["declW"]) if cols else None,
        "ellipsisCols": [c for c in cols if c["ellipsis"]],
        "total": total, "pageSize": page_size,
        "drawerCount": len(drawers), "drawerW": dr_w, "mdCount": len(md),
        "tableProps": tp,
    }


# ------------------------------------------------------------------ 报告
def render_case(name, page, dom_by_vp, rows_by_vp):
    all_rows = []
    for vw, rows in rows_by_vp.items():
        all_rows.extend(rows)
    p = sum(1 for r in all_rows if r["status"] == "PASS")
    f = sum(1 for r in all_rows if r["status"] == "FAIL")
    s = sum(1 for r in all_rows if r["status"] == "SKIP")
    # 出现过的 SKIP 判据 id（去重）—— 交给 main 做白名单比对（V13）
    skip_ids = sorted(set(r["id"] for r in all_rows if r["status"] == "SKIP"))
    print("\n" + "=" * 78)
    print("CASE %s | page %s (%s) | 两档视口 | retries=%d"
          % (name, page.get("id"), page.get("name"),
             sum(d.get("_retry", 0) for d in dom_by_vp.values())))
    print("  条数口径：P1–P19 共 20 条；P3 按 §6.2 注拆为 P3a（栅格）/ P3b（总高），故每视口 21 行")
    for vw, rows in rows_by_vp.items():
        d = dom_by_vp[vw]
        print("  -- %dx%d  内容宽 %s  pane %s（默认 %s）  列 %s"
              % (vw, d.get("vh"), fmt(d.get("contentBoxW")), fmt(d.get("paneW")),
                 fmt(d.get("paneDefaultW")), d.get("tableCount")))
        for r in rows:
            mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}[r["status"]]
            print("     %-4s %-28s 现值 %-30s 阈值 %-22s %s"
                  % (r["id"], r["title"], r["value"], r["threshold"], mark))
            if r["note"]:
                print("          ↳ %s" % r["note"])
    print("  PASS=%d FAIL=%d SKIP=%d（SKIP 不计为绿）" % (p, f, s))
    if skip_ids:
        print("  SKIP 判据 = [%s]" % ",".join(skip_ids))
    return p, f, s, skip_ids


def run_one(chrome, json_path, page_id=None, keep=False):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    page = pick_page(data, page_id)
    if page is None:
        print("\nCASE %s —— SKIP（无作业型列表页）" % Path(json_path).name)
        return 0, 0, 0, [], set()
    tmp = Path(tempfile.mkdtemp(prefix="xx-prd-shape-"))
    html = tmp / "case.html"
    try:
        build_case(CONTAINER, data, page["id"], html)
        dom_by_vp, rows_by_vp = {}, {}
        for w, h in VIEWPORTS:
            d = run_viewport(chrome, html, w, h)
            dom_by_vp[w] = d
            props = props_of(page, d)
            rows_by_vp[w] = evaluate(props, d, page, w)
        # V8 的比对单位是「判据@视口」：同一判据只在一档红、另一档绿，本身就是要看的信号。
        fails = set("%s@%d" % (r["id"], w)
                    for w, rs in rows_by_vp.items() for r in rs if r["status"] == "FAIL")
        return render_case(Path(json_path).name, page, dom_by_vp, rows_by_vp) + (fails,)
    finally:
        if keep:
            print("CASE_HTML=%s" % html)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def default_targets():
    out = []
    for f in sorted(EXDIR.glob("example-*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if any(is_work_list_page(p) for p in (d.get("pages") or [])):
            out.append(str(f))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="P1-P19 形态与密度判据")
    ap.add_argument("files", nargs="*", help="产物 JSON（默认：assets/examples 里含列表页的示例）")
    ap.add_argument("--page", help="指定 pageId")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="注入反例，验证判据能红")
    ap.add_argument("--base", help="--selfcheck 的基线产物（默认 example-06-dense-list.json）")
    args = ap.parse_args(argv)

    try:
        chrome = find_chrome()
    except EnvError as ex:
        print(str(ex))
        return 2

    if args.selfcheck:
        return selfcheck(chrome, args.base)

    files = args.files or default_targets()
    if not files:
        print("没有可跑的产物：assets/examples 里一个作业型列表页都没有")
        return 2

    tp = tf = ts = 0
    skip_seen = set()
    fails_by_file = {}
    for f in files:
        try:
            p, fl, s, sk, fs = run_one(chrome, f, args.page, args.keep)
        except EnvError as ex:
            print("\nCASE %s —— ENV: %s" % (Path(f).name, ex))
            return 2
        tp += p
        tf += fl
        ts += s
        skip_seen.update(sk)
        fails_by_file[Path(f).name] = fs

    print("\n" + "-" * 78)
    print("TOTAL PASS=%d FAIL=%d SKIP=%d" % (tp, tf, ts))

    # V8：不是「FAIL 数够不够」，是「红的是不是原来那几条」。
    # 少一条 = 判据被放宽或失效；多一条 = 新缺陷或判据变严。两种都要人说清楚。
    #
    # **名单里的文件没跑，也必须说话**（第二批补）。原先这句是 `continue`：只要这一轮
    # 没跑 example-05，V8 一个字都不打就跳过 —— 而 `default_targets()` 是靠
    # `is_work_list_page` 挑文件的，哪天 example-05 的列表页被改成非作业型，它就静默
    # 从默认目标里掉出去，V8 跟着消失，输出看起来只是「少跑了一个文件」。
    # 这和「用数量代替清单」是同一类：**判据没跑，结论却是绿的**。
    # 分两种模式处置，理由是「点了名」和「没点名」不是一回事：
    #   全量模式（不带参数）：名单文件必须在场，不在 → 未比对 → 不算过；
    #   单文件模式（带 FILE）：本来就只问这一个文件，名单其它文件打一行「未比对」即可，
    #   否则 `check_ui_shape example-06` 这条验收命令会被无关文件拖成红。
    full_mode = not args.files
    v8_bad = False
    v8_missing = 0
    for name, exp in EXPECTED_FAIL.items():
        if name not in fails_by_file:
            if full_mode:
                v8_missing += 1
                v8_bad = True
                print("V8 未比对：%s 不在本轮目标里 —— 全量模式下「该比而没比」不算过"
                      "（期望名单 %d 条，一条都没核对）" % (name, len(exp)))
            else:
                print("V8 未比对：%s（单文件模式，本轮点名的是 %s）"
                      % (name, ", ".join(sorted(fails_by_file)) or "—"))
            continue
        act = fails_by_file[name]
        miss, extra = sorted(exp - act), sorted(act - exp)
        if not miss and not extra:
            print("V8 FAIL 集比对：%s 期望 %d 条 / 实际 %d 条 —— 逐条相等"
                  % (name, len(exp), len(act)))
            continue
        v8_bad = True
        print("V8 FAIL 集比对：%s 不符（期望 %d 条 / 实际 %d 条）"
              % (name, len(exp), len(act)))
        if miss:
            print("  少红 %d 条（判据被放宽或没跑）：%s" % (len(miss), ", ".join(miss)))
        if extra:
            print("  多红 %d 条（新缺陷或判据变严）：%s" % (len(extra), ", ".join(extra)))

    # V13：白名单外的 SKIP = 判据自己没跑，不是产物不达标。
    # 单独打一行，让人一眼看到「哪几条这次没真正判」。
    bad_skip = sorted(skip_seen - set(SKIP_WHITELIST))
    if bad_skip:
        print("SKIP-OUT-OF-WHITELIST=[%s]  白名单只允许 %s"
              % (",".join(bad_skip), ",".join(SKIP_WHITELIST)))
        print("RESULT INCOMPLETE  —— 有判据在没有正当理由的情况下没跑，"
              "这不是「产物达标」，是「判据没判」")
        return 1
    if v8_bad:
        if tf == 0 and v8_missing:
            print("RESULT INCOMPLETE  —— V8 有 %d 个名单文件本轮没跑；"
                  "「没比对」不等于「比过了」" % v8_missing)
        else:
            print("RESULT FAIL  —— V8 的 FAIL 集与期望名单不符："
                  "FAIL 总数只说明「红了几条」，说明不了「红的是不是该红的那几条」")
        return 1
    print("RESULT %s" % ("PASS" if tf == 0 else "FAIL"))
    return 0 if tf == 0 else 1


# ------------------------------------------------------------------ 自证
# 自证要成立，两个前置条件必须写明（否则输出的 OK 和「判据全对」一模一样）：
#   ① 基线本身必须是绿的 —— 拿一条已经 FAIL 的判据注入同类缺陷，失败集不变，
#      「注入前后都红」看起来和「判据有效」完全一样；
#   ② 注入必须只打红目标判据 —— 连带别的判据一起红，说明两条在测同一件事，应当合并。
# 所以自证先打印基线现值，再把「基线不绿」的注入显式标 SKIP，最后列出多翻的判据。
#
# 三种注入，覆盖三类判据：
#   css —— 改样式（P4/P6/P9/P10 这类几何判据）
#   js  —— 在 measure 之前往 DOM 里塞元素（P1/P5/P14 这类「有没有这个东西」的判据）
#   json —— 改 props（P7/P11/P13/P17/P18 这类读 JSON 的判据）

INJECTIONS = [
    # ---- css 类
    {"name": "P4_ctl_narrow", "kind": "css", "want": ["P4"],
     "payload": ".ant-filter-bar .fb-field .ctl{min-width:120px!important;flex:0 0 auto!important;max-width:none!important}"},
    # P6 的注入用 transform 位移，不用 margin：margin 会同时改栅格列宽（→ P4 连带红、
    # 表格变窄 → P17 渲染宽连带红），那样「多翻」来自注入手段而不是判据重叠。
    # transform 不影响布局，只移动盒子 —— P6 量的正是盒子左边界。
    {"name": "P6_filter_shift", "kind": "css", "want": ["P6"],
     "payload": ".ant-content .ant-filter-bar{transform:translateX(-12px)}"},
    {"name": "P9_row_high", "kind": "css", "want": ["P9"], "allow": ["P2a", "P2b", "P18"],
     "allowWhy": "行高变大 → 一屏行数必然减少（P2a/P2b）；同时 white-space:normal 让文本改折行、"
                 "不再横向溢出 → 配了 ellipsis 的两列变成「装饰」，P18 的集合相等必然不成立。"
                 "两者都是这个注入的真实后果，不是判据重叠",
     "payload": ".ant-table td{white-space:normal!important;padding-top:16px!important;padding-bottom:16px!important}"},
    {"name": "P10_sticky_off", "kind": "css", "want": ["P10"],
     "payload": ".ant-table th{position:static!important}"},
    # ---- js 类（在 measure 前塞元素）
    {"name": "P1_stat_back", "kind": "js", "want": ["P1"], "allow": ["P16", "P2b", "P19"],
     # 允许的连带都是该注入的**真实后果**，不是「P1 与它们在测同一件事」：
     #   P16/P2b —— 统计卡占掉首屏高度，表格下移、分页被挤出屏；
     #   P19     —— 统计卡自带 24px 数值，页内字号从 3 档变 4 档 —— 这正是「列表页不许放
     #              统计卡」的第二条理由（第一条是抢高度），判据把它一起抓出来是对的。
     # 若这些连带不出现，反而说明 P2b/P16/P19 没量到真实影响。
     "allowWhy": "统计卡占首屏高度（P16/P2b），并自带 24px 数值把字号推到 4 档（P19）—— 都是同一注入的真实后果",
     "payload": "(function(){var C=document.querySelector('#protoCanvas .ant-content');if(!C)return;"
                "var e=document.createElement('div');e.className='ant-stat';"
                "e.innerHTML='<div class=\"s-t\">在检批次</div><div class=\"s-v\">42</div>';"
                "C.insertBefore(e,C.firstChild);})();"},
    {"name": "P5_card_3layer", "kind": "js", "want": ["P5"],
     "payload": "(function(){var C=document.querySelector('#protoCanvas .ant-content');if(!C)return;"
                "var e=document.createElement('div');e.className='ant-card';"
                "e.style.cssText='border:1px solid #d9d9d9;background:#fff;"
                "box-shadow:0 1px 2px rgba(0,0,0,.06);height:40px';"
                "C.appendChild(e);})();"},
    {"name": "P14_tag_2color", "kind": "js", "want": ["P14"], "allow": ["P18"],
     "allowWhy": "往首个单元格里塞两个标签会把它撑溢出（序号列只有 48），于是「真溢出列集合」"
                 "多了一列没配 ellipsis 的 —— P18 的集合相等条件必然不成立，是该注入的真实后果",
     "payload": "(function(){var tr=document.querySelector('#protoCanvas .ant-table tbody tr');if(!tr)return;"
                "var td=tr.querySelector('td');if(!td)return;"
                "for(var i=0;i<2;i++){var t=document.createElement('span');"
                "t.className='ant-tag red';t.textContent='加急';td.appendChild(t);}})();"},
    # ---- json 类（改 props 再渲染）
    {"name": "P13_page_size_10", "kind": "json", "want": ["P13"],
     "payload": lambda p: _mutate_table(p, lambda tp: _set_pg(tp, 10))},
    {"name": "P17_drop_one_width", "kind": "json", "want": ["P17"],
     "payload": lambda p: _mutate_table(p, lambda tp: _drop_width(tp))},
    {"name": "P18_ellipsis_all", "kind": "json", "want": ["P18"],
     "payload": lambda p: _mutate_table(p, lambda tp: _ellipsis_all(tp))},
]


def _first_table_node(page):
    tabs = content_direct_tables(page)
    return tabs[0] if tabs else None


def _mutate_table(page, fn):
    t = _first_table_node(page)
    if t is not None:
        fn(t.setdefault("props", {}))
    return page


def _set_pg(tp, ps):
    pg = tp.get("pagination")
    if isinstance(pg, dict):
        pg["pageSize"] = ps
    return tp


def _drop_width(tp):
    """摘掉**一列**的 width 声明（不是两列）。

    为什么挑带 ellipsis 的那一列：fixed 布局会把剩余空间补给无声明列 —— 该列
    原本 125、补到 125，渲染完全不变，于是只有 P17（Σ 与列数账本）红。
    若摘掉的是「任务单号」，它会从 188 掉到 108 → 开始裁字 → P18 连带红，
    「多翻」来自注入位置而不是判据重叠，自证就说不清是 P17 还是 P18 抓到的。
    只摘一列而不是两列：两列会让声明率跌到 6/8=75% < 80%，P7 连带红。
    """
    for c in (tp.get("columns") or []):
        if c.get("ellipsis") and "width" in c:
            c.pop("width", None)
            return tp
    for c in (tp.get("columns") or [])[1:2]:
        c.pop("width", None)
    return tp


def _ellipsis_all(tp):
    for c in (tp.get("columns") or []):
        c["ellipsis"] = True
    return tp


def selfcheck(chrome, base_file=None):
    """在基线产物上逐条注入反例，验证「判据会红在正确的规则上」。

    三条硬规矩（每条都对应一次踩过的坑）：

    ① **基线必须自己先绿**。拿一条本来就 FAIL 的判据注入同类缺陷，失败集不变，
       「注入前后都红」看起来和「判据有效」一模一样。
       所以基线默认切到 example-06（F6 之后那里 21 条全绿，PASS=21 FAIL=0 SKIP=0）——
       拿 example-05 当基线时，10 条注入里有 6 条 SKIP（P4/P9/P10/P13/P17/P18 在基线本就不绿），
       实际只证明了 4 条，脚本却打 `RESULT PASS`。那是「SKIP 洗成 PASS」，与本轮要
       消灭的假绿同型。
    ② **覆盖不够就不是 PASS**。覆盖 <10 时打 `RESULT INCOMPLETE` 并非 0 退出 ——
       一个「证明了 4 条」的自证和一个「证明了 10 条」的自证，不能有同样的输出。
    ③ **每条注入都要打印基线现值**。只打 OK 的话，读者无法判断「注入前它到底多绿」，
       也就无法判断这条注入是不是在测一个已经半红的判据。
    """
    if base_file is None:
        base_file = EXDIR / "example-06-dense-list.json"
    base_file = Path(base_file)
    if not base_file.is_file():
        print("SELFCHECK 基线产物不存在：%s" % base_file)
        return 2
    data0 = json.loads(base_file.read_text(encoding="utf-8"))
    page0 = pick_page(data0)
    if page0 is None:
        print("SELFCHECK 基线 %s 里没有作业型列表页" % base_file.name)
        return 2
    tmp = Path(tempfile.mkdtemp(prefix="xx-prd-shape-sc-"))
    print("SELFCHECK 基线产物：%s / page %s（1440×900）" % (base_file.name, page0["id"]))
    ok_all = True
    covered = 0
    try:
        def run(inj=None):
            data = json.loads(json.dumps(data0))
            page = pick_page(data, page0["id"])
            css = js = ""
            if inj:
                if inj["kind"] == "css":
                    css = inj["payload"]
                elif inj["kind"] == "js":
                    js = inj["payload"]
                elif inj["kind"] == "json":
                    inj["payload"](page)
            src = Path(CONTAINER).read_text(encoding="utf-8")
            if css:
                src = src.replace("</style>", "\n/* inject: %s */\n%s\n</style>" % (inj["name"], css), 1)
            hp = tmp / "c.html"
            build_case_src(src, data, page["id"], hp, inject_js=js)
            d = run_viewport(chrome, hp, 1440, 900)
            return evaluate(props_of(page, d), d, page, 1440)

        base = run()
        base_fail = {r["id"] for r in base if r["status"] == "FAIL"}
        base_pass = {r["id"] for r in base if r["status"] == "PASS"}
        base_skip = {r["id"] for r in base if r["status"] == "SKIP"}
        base_val = {r["id"]: r["value"] for r in base}
        print("  基线 1440：PASS=%d FAIL=%d SKIP=%d" % (len(base_pass), len(base_fail), len(base_skip)))
        print("  基线 PASS 集合 = %s" % sorted(base_pass))
        if base_fail:
            print("  基线 FAIL 集合 = %s（注入的目标判据若落在这里，自证不成立）"
                  % sorted(base_fail))
        if not base_pass:
            print("  基线一条都不绿 —— 自证不成立（注入同类缺陷不改变失败集），先修产物再自证")
            return 1

        for inj in INJECTIONS:
            want = inj["want"]
            # 前置①：目标判据在基线里必须绿。不绿不是「跳过」，是自证不成立 ——
            # 计入未覆盖，最终 RESULT 为 INCOMPLETE。
            missing = [w for w in want if w not in base_pass]
            if missing:
                print("  %-18s SKIP（基线 %s 不绿，注入同类缺陷看不出变化；基线现值 %s）"
                      % (inj["name"], missing,
                         ", ".join("%s=%s" % (w, base_val.get(w, "—")) for w in missing)))
                ok_all = False
                continue
            print("  %-18s 基线 %s" % (inj["name"],
                                      ", ".join("%s=%s（%s）" % (w, base_val.get(w), "PASS") for w in want)))
            rows = run(inj)
            now_fail = {r["id"] for r in rows if r["status"] == "FAIL"}
            now_val = {r["id"]: r["value"] for r in rows}
            flipped = now_fail - base_fail
            ok = set(want).issubset(flipped)
            allow = set(inj.get("allow") or [])
            extra = flipped - set(want) - allow
            print("  %-18s 翻红=%-20s 期望=%-8s %s%s"
                  % ("", sorted(flipped) or "[]", sorted(want),
                     "OK" if ok and not extra else "SELFCHECK-FAIL",
                     ("  多翻：" + str(sorted(extra))) if extra else ""))
            print("  %-18s 注入后 %s" % ("", ", ".join("%s=%s" % (w, now_val.get(w)) for w in want)))
            if allow and (flipped & allow):
                print("          ↳ 允许的连带 %s：%s" % (sorted(flipped & allow), inj.get("allowWhy", "")))
            if ok and not extra:
                covered += 1
            else:
                ok_all = False
        total = len(INJECTIONS)
        print("  自证覆盖=%d/%d" % (covered, total))
        if covered < total or not ok_all:
            print("RESULT INCOMPLETE (selfcheck)：只证明了 %d/%d 条注入，"
                  "覆盖不足不得判 PASS" % (covered, total))
            return 1
        print("RESULT PASS (selfcheck)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def build_case_src(src, data, page_id, out_html, inject_js=""):
    """同 build_case，但接受已经改过 CSS 的容器源码（自证注入用）。"""
    pages = data.get("pages") or []
    pages = [p for p in pages if p.get("id") == page_id] + [p for p in pages if p.get("id") != page_id]
    d = dict(data)
    d["pages"] = pages
    meta = dict(d.get("meta") or {})
    meta["currentPageId"] = page_id
    d["meta"] = meta
    payload = json.dumps(d, ensure_ascii=False)
    m = re.search(r'(<script type="application/json" id="iprd-data">)(.*?)(</script>)', src, re.S)
    if not m:
        raise EnvError("容器里找不到 #iprd-data")
    src = src[:m.start(2)] + "\n" + payload + "\n" + src[m.end(2):]
    probe = PROBE.replace("/*__INJECT__*/", inject_js or "")
    src = src.replace("</body>", probe + "</body>", 1)
    Path(out_html).write_text(src, encoding="utf-8")
    return out_html


if __name__ == "__main__":
    sys.exit(main())
