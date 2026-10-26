#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I-09 任务 B：给「反样本」量四组几何事实（列宽 / 表头 / 内容宽 / 短字段折行）。

**不新造一套渲染与探针**：直接 import `check_ui_shape`，复用它的
`PROBE`（`measure()` + `productStage()`）、`build_case_src()`、`run_viewport()`、
`VIEWPORTS`。只在 PROBE 的 `emit(d)` 之前插一段私有测量函数，
把反样本需要的四个数打到同一个 `#__shapeout` 里。

为什么必须复用而不是另写：两套探针一旦分叉，「门量到的产物」与
「人看到的产品」就不是同一份 DOM —— 这轮所有争论都会变成量具之争。

用法:
    python3 tests/measure_reject.py assets/rejects/reject-01-capa-qms/CAPA-PRD.data.json
    python3 tests/measure_reject.py FILE --page page-capa-list [--json]

退出码: 0 = 量到了；2 = 环境不可用（Chrome / 探针未产出）
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_ui_shape as S  # noqa: E402

# 只在 emit 之前插一段；measure() / productStage() 一字不改。
EXTRA_JS = r"""
  /* ---- 反样本专用测量（I-09 B）。与 measure() 同一页、同一态（PRD 已折叠） ---- */
  function rejectExtras(){
    var C=document.querySelector('#protoCanvas .ant-content');
    var out={vw:window.innerWidth,vh:window.innerHeight};
    if(!C){ out.err='NO_CONTENT'; return out; }
    var scs=getComputedStyle(C);
    out.contentBoxW=num(C.clientWidth-parseFloat(scs.paddingLeft||0)-parseFloat(scs.paddingRight||0));

    /* 文本行盒数：按文本节点 client rect 的 top 去重计数。
       为什么不用 scrollHeight>clientHeight：那是「溢出」不是「折行」——
       td 里 flex 排的两个按钮（详情/确认）竖排时 scrollHeight 等于 clientHeight，
       但视觉上确实是两行。两个口径都报，判定以行盒数为准。 */
    function lineTops(el){
      var tops={},cnt=0,tw=document.createTreeWalker(el,NodeFilter.SHOW_TEXT,null),n;
      while((n=tw.nextNode())){
        if(!(n.nodeValue||'').trim()) continue;
        var r=document.createRange(); r.selectNodeContents(n);
        var rs=r.getClientRects();
        for(var i=0;i<rs.length;i++){
          if(rs[i].height<=0.5) continue;
          var k=Math.round(rs[i].top);
          if(!tops[k]){ tops[k]=1; cnt++; }
        }
      }
      return cnt;
    }
    /* 全角字宽（1 = 一个全角字；半角按 0.557，与视觉标准 §W-01 的估算系数同源）。
       与 check_ui_shape 的 P20 分母**同一个口径** —— 两个工具对同一句话报两个分母，
       下一次争论就会变成「谁的数才是对的」，而不是「产物对不对」。 */
    function textUnits(s){
      var u=0;
      for(var i=0;i<(s||'').length;i++){
        var c=s.charCodeAt(i);
        u += (c>=0x2E80) ? 1 : ((c===0x20) ? 0.28 : 0.557);
      }
      return Math.round(u*100)/100;
    }
    /* 文字自然宽：同字体、white-space:nowrap 的隐藏副本量一次。
       不拿 scrollWidth 当自然宽 —— nowrap 的 th 上 scrollWidth 是「被裁掉的内容宽」，
       与「这列文字本来要占多宽」不是同一个数。 */
    function naturalWidth(el){
      var st=getComputedStyle(el);
      var probe=document.createElement('span');
      probe.style.cssText='position:absolute;left:-9999px;top:0;visibility:hidden;white-space:nowrap;';
      probe.style.fontFamily=st.fontFamily; probe.style.fontSize=st.fontSize;
      probe.style.fontWeight=st.fontWeight; probe.style.fontStyle=st.fontStyle;
      probe.style.letterSpacing=st.letterSpacing;
      probe.textContent=(el.textContent||'').replace(/\s+/g,' ').trim();
      document.body.appendChild(probe);
      var w=probe.getBoundingClientRect().width;
      document.body.removeChild(probe);
      return num(w);
    }

    var tables=[],tl=C.querySelectorAll('.ant-table');
    for(var ti=0;ti<tl.length;ti++){
      var t=tl[ti];
      if(t.closest('.ant-drawer,.ant-modal')) continue;
      var wrap=t.closest('.ant-table-wrap')||t.parentElement;
      var ths=t.querySelectorAll('thead th'), thOut=[];
      for(var ci=0;ci<ths.length;ci++){
        var th=ths[ci], st=getComputedStyle(th);
        var padL=parseFloat(st.paddingLeft||0), padR=parseFloat(st.paddingRight||0);
        /* 裁切锚点与 check_ui_shape 的 P23 **共用同一个函数**（探针顶层的 clippingBox()）：
           同一个量两套量具，迟早要吵「谁的数才对」。这里原来直接量 th，等价于假设
           「th 永远有 overflow」—— 容器换实现（比如表头文字包一层 span）时会静默变恒绿。 */
        var cb=clippingBox(th);
        thOut.push({
          i:ci, title:(th.textContent||'').replace(/\s+/g,' ').trim().slice(0,24),
          w:num(th.offsetWidth),
          clientW: cb?cb.clientWidth:null, scrollW: cb?cb.scrollWidth:null,
          availW:num(th.clientWidth-padL-padR),
          naturalW:naturalWidth(th),
          whiteSpace:st.whiteSpace,
          anchor: cb?(cb===th?'th':cb.tagName.toLowerCase()):'none',
          clipped: cb?(cb.scrollWidth>cb.clientWidth+1):null,
          lines: lineTops(th)
        });
      }
      var rows=t.querySelectorAll('tbody tr'), rowsSeen=0;
      var shortTotal=0, shortWrapped=0, otherWrapped=0, sample=[], cellsSeen=0;

      /* ---- needW：这列**本来需要多宽**才不折（幻神 2026-10-26 指定口径）
         按「最内层文本承载元素」量：Tag 是 12px、td 是 14px。用 td 字号去量 Tag 里的字
         会大 1/7，把本来放得下的列判红（example-06 的「状态」列 80 就是这样被误判的）。
         做法：把叶子元素克隆一份、nowrap、量外宽（含它自己的 padding/border），
         再加上 td 的左右 padding。
         两种口径都算并都打出来（needInner / needTd），差异本身就是要给人看的数。 */
      function leafEls(td){
        var out=[];
        (function walk(n){
          for(var i=0;i<n.children.length;i++){
            var ch=n.children[i];
            if(!(ch.textContent||'').trim()) continue;
            var deeper=false;
            for(var j=0;j<ch.children.length;j++){
              if((ch.children[j].textContent||'').trim()){ deeper=true; break; }
            }
            if(deeper) walk(ch); else out.push(ch);
          }
        })(td);
        return out;
      }
      function outerW(el){
        var c=el.cloneNode(true);
        c.style.cssText='position:absolute;left:-9999px;top:0;visibility:hidden;'+
                        'white-space:nowrap;display:inline-block';
        document.body.appendChild(c);
        var w=c.getBoundingClientRect().width;
        document.body.removeChild(c);
        return num(w);
      }
      var need=(function(){
        var acc={};
        for(var ri2=0;ri2<rows.length;ri2++){
          var cs=rows[ri2].querySelectorAll('td');
          if(cs.length<2) continue;
          for(var k2=0;k2<cs.length;k2++){
            var td2=cs[k2];
            var txt2=(td2.textContent||'').replace(/\s+/g,' ').trim();
            if(!txt2) continue;
            if(!acc[k2]) acc[k2]={needInner:0,needSum:0,needTd:0,leaf:'',leafFont:'',tdFont:''};
            var st2=getComputedStyle(td2);
            var p2=parseFloat(st2.paddingLeft||0)+parseFloat(st2.paddingRight||0);
            var leaves=leafEls(td2);
            var maxInner=0, sumInner=0, leafDesc='', leafFont='';
            if(leaves.length){
              for(var q=0;q<leaves.length;q++){
                var w2=outerW(leaves[q])||0;
                maxInner=Math.max(maxInner,w2);
                sumInner+=w2;
                var lst=getComputedStyle(leaves[q]);
                leafDesc=leaves[q].tagName.toLowerCase()+
                         (leaves[q].className?('.'+String(leaves[q].className).split(/\s+/)[0]):'');
                leafFont=lst.fontSize;
              }
              if(leaves.length>1){
                var gap=parseFloat(getComputedStyle(td2).columnGap||0);
                if(!isFinite(gap)) gap=0;          /* columnGap:normal → parseFloat 是 NaN，会把整列 needSum 污染成 0 */
                sumInner+=gap*(leaves.length-1);
              }
            } else {
              maxInner=naturalWidth(td2)||0;
              sumInner=maxInner;
              leafDesc='(纯文本)'; leafFont=st2.fontSize;
            }
            var needInner=maxInner+p2, needSum=sumInner+p2, needTd=(naturalWidth(td2)||0)+p2;
            var slot=acc[k2];
            slot.needSum=Math.max(slot.needSum,num(needSum));
            slot.needTd=Math.max(slot.needTd,num(needTd));
            if(num(needInner)>slot.needInner){
              slot.needInner=num(needInner);
              slot.leaf=leafDesc; slot.leafFont=leafFont;
            }
            slot.tdFont=st2.fontSize;
          }
        }
        return acc;
      })();
      var needOut=[];
      for(var ck in need){
        var cc=need[ck], thw=(thOut[+ck]||{}).w;
        needOut.push({
          i:+ck, title:(thOut[+ck]||{}).title, renderedW:thw,
          needInner:cc.needInner, needSum:cc.needSum, needTd:cc.needTd,
          leaf:cc.leaf, leafFont:cc.leafFont, tdFont:cc.tdFont,
          fitsInner: thw!=null && cc.needInner<=thw+0.5,
          fitsTd: thw!=null && cc.needTd<=thw+0.5
        });
      }
      for(var ri=0;ri<rows.length;ri++){
        var cells=rows[ri].querySelectorAll('td');
        if(cells.length<2) continue;
        rowsSeen++;
        for(var k=0;k<cells.length;k++){
          var td=cells[k], txt=(td.textContent||'').replace(/\s+/g,' ').trim();
          if(!txt) continue;
          cellsSeen++;
          var lc=lineTops(td);
          var wrapped=(lc>1)||(td.scrollHeight>td.clientHeight+1);
          /* 「短字段」= 含 Tag/Button 的格 ∪ 整格文本 ≤6 全角字的格（与 P20 同分母）。
             旧口径是 /^[汉字]{1,6}$/ —— 它把「12/3」「10/2」这类数字格和含 Tag 的格
             全排除在外，分母只剩汉字格，于是「0/40 折行」看起来比真实情况好一倍。 */
          var isShort=(td.querySelector('.ant-tag,.ant-btn,button')!==null) || textUnits(txt)<=6;
          if(isShort){
            shortTotal++;
            if(wrapped){ shortWrapped++; if(sample.length<15) sample.push({r:ri,c:k,text:txt,lines:lc,h:td.offsetHeight}); }
          } else if(wrapped){ otherWrapped++; }
        }
      }
      tables.push({
        i:ti, layout:getComputedStyle(t).tableLayout, tableW:num(t.offsetWidth),
        wrapClientW:wrap.clientWidth, wrapScrollW:wrap.scrollWidth,
        rowCount:rowsSeen, cellsSeen:cellsSeen,
        th:thOut, need:needOut,
        shortFieldCells:shortTotal, shortFieldWrapped:shortWrapped,
        otherWrappedCells:otherWrapped, shortWrappedSample:sample
      });
    }
    out.tables=tables;

    /* ---- 产品态内容宽：复用 productStage() 已经建好的**同一个舞台**，只改舞台宽。
       同 DOM、同口径（去壳 / 单个 100vh 按 900 换算都已在 productStage 里做完），
       只把舞台宽度从 1440 换成 1600 —— 这样「两档产品态内容宽」是可比的两个数，
       而不是两套克隆代码各量一遍。 */
    out.stageWidths={};
    (function(){
      var ov=document.getElementById('__prodStage'); if(!ov) return;
      var C2=ov.querySelector('.ant-content'); if(!C2) return;
      var keep=ov.style.width;
      [1440,1600].forEach(function(w){
        ov.style.width=w+'px';
        var st=getComputedStyle(C2);
        out.stageWidths[w]=num(C2.clientWidth-parseFloat(st.paddingLeft||0)-parseFloat(st.paddingRight||0));
      });
      ov.style.width=keep;
    })();
    return out;
  }
"""


def build_probe():
    """在 PROBE 的 emit 之前插入私有测量，原有 measure/productStage 不动。"""
    marker = "    emit(d);"
    assert S.PROBE.count(marker) == 1, "PROBE 结构变了：emit(d) 不是唯一一处"
    return S.PROBE.replace(
        marker,
        "    try{ d.reject=rejectExtras(); }catch(ex3){ d.reject={err:'EXTRA:'+ex3.message}; }\n" + marker,
    ).replace('waitInit(function(tries){', EXTRA_JS + '\nwaitInit(function(tries){')


def collect_props(page):
    """JSON 侧：逗 MasterDetail 也钻进去，逐个 Table 报 columns[].width。

    check_ui_shape.props_of 只看 Content 直属子树（不钻 MasterDetail），
    所以列表页是「0/0」——这里的口径更宽，专门用来回答「模型到底写没写 width」。
    """
    out = []
    for n in S.iter_nodes(page.get("componentTree") or {}):
        if n.get("type") != "Table":
            continue
        pr = n.get("props") or {}
        cols = pr.get("columns") or []
        decl, widths = 0, []
        for c in cols:
            w = c.get("width")
            has = w is not None and str(w).strip() != ""
            if has:
                decl += 1
            widths.append({"title": c.get("title"), "width": w, "has": has})
        out.append({
            "id": n.get("id"), "size": pr.get("size"),
            "tableLayout": pr.get("tableLayout"), "fixed": pr.get("fixed"),
            "stickyHeader": pr.get("stickyHeader"),
            "colCount": len(cols), "declared": decl,
            "rate": (decl / len(cols)) if cols else None,
            "widths": widths,
        })
    return out


def measure_all(chrome, data, page, tmp, th_span):
    """跑两档视口，返回 res。`th_span=True` 时把表头文字包一层 <span> 再量（造红输入）。"""
    html = tmp / ("case-span.html" if th_span else "case.html")
    if th_span:
        # 只改「表头文本外面有没有一层元素」，不改任何几何：读数必须与不加 --th-span 完全一致。
        # 若从「被裁 1/8」变成「被裁 0/8」，说明判据量的还是内层元素（inline 的
        # clientWidth/scrollWidth 恒 0/0 → 恒绿）。
        inject = ("(function(){var ths=document.querySelectorAll('.ant-table thead th');"
                  "for(var i=0;i<ths.length;i++){var th=ths[i],t=null;"
                  "for(var j=0;j<th.childNodes.length;j++){var nd=th.childNodes[j];"
                  "if(nd.nodeType===3&&(nd.nodeValue||'').trim()){t=nd;break;}}"
                  "if(!t)continue;var sp=document.createElement('span');"
                  "sp.textContent=t.nodeValue;th.replaceChild(sp,t);}})();")
        src = Path(S.CONTAINER).read_text(encoding="utf-8")
        S.build_case_src(src, data, page["id"], html, inject_js=inject)
    else:
        S.build_case(S.CONTAINER, data, page["id"], html)

    res = {"file": None, "page": page.get("id"), "pageName": page.get("name"),
           "jsonTables": collect_props(page), "viewports": {}}
    for w, h in S.VIEWPORTS:
        d = S.run_viewport(chrome, html, w, h)
        res["viewports"]["%dx%d" % (w, h)] = {
            "contentBoxW": d.get("contentBoxW"),
            "paneW": d.get("paneW"),
            "paneDefaultW": d.get("paneDefaultW"),
            "prdCollapsedAtStart": d.get("prdCollapsedAtStart"),
            "contentRatio": round((d.get("contentBoxW") or 0) / w * 100, 1),
            "product": {k: d.get("product", {}).get(k)
                        for k in ("w", "h", "contentBoxW", "wrapClientW", "rowCount", "firstRowH")},
            "reject": d.get("reject"),
        }
    return res


def _clip_counts(res):
    """每个视口里每张表的 (被裁列数, 可比列数) —— span 自证要比的就是这一对数。"""
    out = {}
    for vp, d in res["viewports"].items():
        for t in ((d.get("reject") or {}).get("tables") or []):
            na = sum(1 for c in t["th"] if c.get("clipped") is None)
            out[(vp, t["i"])] = (sum(1 for c in t["th"] if c.get("clipped")),
                                 len(t["th"]) - na)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="反样本四组几何事实")
    ap.add_argument("file")
    ap.add_argument("--page")
    ap.add_argument("--json", action="store_true", help="只打机器可读 JSON")
    ap.add_argument("--th-span", action="store_true",
                    help="造红/防恒绿：把每个 th 的文本包一层 <span> 再量，"
                         "并与不包 span 的读数逐档比对（必须完全相同）。"
                         "T-04 的锚点若不是「裁切盒」而是「最内层元素」，这里会从红变绿")
    a = ap.parse_args(argv)

    try:
        chrome = S.find_chrome()
    except S.EnvError as ex:
        print(str(ex))
        return 2

    path = Path(a.file)
    data = json.loads(path.read_text(encoding="utf-8"))
    page = S.pick_page(data, a.page)
    if page is None:
        print("找不到作业型列表页（用 --page 指定）")
        return 2

    S.PROBE = build_probe()
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="xx-prd-reject-"))
    res = measure_all(chrome, data, page, tmp, a.th_span)
    res["file"] = str(path)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(_pretty(res))
        if a.th_span:
            # **双向比对，不靠读者手动跑两次**：表头文字外包一层 <span> 后，
            # 锚点若还是「最内层元素」，inline 的 clientWidth/scrollWidth 恒 0/0 →
            # 原本「被裁 1/8」会变成「被裁 0/8」。两个数不一致就是判据选了错的对象，
            # 而不是产物变好了 —— 那样这条判据在容器一改表头结构时就会静默恒绿。
            base = measure_all(chrome, data, page, tmp, False)
            ca, cb = _clip_counts(base), _clip_counts(res)
            print("")
            print("== span 自证（表头文字外包一层 <span>，列宽与几何一个字没改）")
            ok = True
            for k in sorted(ca, key=lambda x: (x[0], x[1])):
                va, vb = ca[k], cb[k]
                same = (va == vb)
                ok = ok and same
                print("   视口 %-9s 表#%d  不加 span 被裁 %d/%d  →  加 span 被裁 %d/%d  %s"
                      % (k[0], k[1], va[0], va[1], vb[0], vb[1], "相同" if same else "**不同**"))
            print("   结论：%s" % ("锚点=裁切盒，读数不随「有没有内层元素」改变"
                                 if ok else
                                 "读数变了 —— 锚点还在量最内层元素（inline 恒 0/0），必须改回 clippingBox"))
            if not ok:
                return 1
    return 0


def _pretty(res):
    L = []
    L.append("FILE %s" % res["file"])
    L.append("PAGE %s (%s)" % (res["page"], res["pageName"]))
    L.append("")
    L.append("== JSON 侧：columns[].width（口径：钻 MasterDetail）")
    for t in res["jsonTables"]:
        rate = "—" if t["rate"] is None else "%.0f%%" % (t["rate"] * 100)
        L.append("  Table %-12s size=%s tableLayout=%s fixed=%s sticky=%s  声明 %d/%d = %s"
                 % (t["id"], t["size"], t["tableLayout"], t["fixed"], t["stickyHeader"],
                    t["declared"], t["colCount"], rate))
        if t["widths"]:
            L.append("    " + " | ".join("%s=%s" % (c["title"], c["width"]) for c in t["widths"]))
    for vp, d in res["viewports"].items():
        L.append("")
        L.append("== 视口 %s" % vp)
        L.append("  内容宽 %s / 视口 %s → %s%%   pane %s（默认 %s）"
                 % (d["contentBoxW"], vp.split("x")[0], d["contentRatio"], d["paneW"], d["paneDefaultW"]))
        L.append("  产品态(1440×900 无外壳) 内容宽 %s" % d["product"]["contentBoxW"])
        r = d["reject"] or {}
        sw = r.get("stageWidths") or {}
        if sw:
            L.append("  产品态内容宽（同一舞台改宽）：%s"
                     % "  ".join("%s×900 → %s（%s%%）"
                                 % (k, v, round((v or 0) / int(k) * 100, 1))
                                 for k, v in sorted(sw.items())))
        for t in r.get("tables") or []:
            L.append("  表#%d layout=%s 表宽 %s  wrap client %s / scroll %s  数据行 %d"
                     % (t["i"], t["layout"], t["tableW"], t["wrapClientW"], t["wrapScrollW"], t["rowCount"]))
            L.append("    i  th.offsetWidth  可用宽  文字自然宽  th行盒  th被裁  表头")
            for c in t["th"]:
                L.append("    %-2d %-14s %-7s %-9s %-6s %-6s  %s"
                         % (c["i"], c["w"], c["availW"], c["naturalW"], c["lines"],
                            "Y" if c["clipped"] else "N", c["title"]))
            clipped = sum(1 for c in t["th"] if c.get("clipped"))
            multi = sum(1 for c in t["th"] if (c["lines"] or 0) > 1)
            na = sum(1 for c in t["th"] if c.get("clipped") is None)
            anch = {}
            for c in t["th"]:
                anch[c.get("anchor") or "none"] = anch.get(c.get("anchor") or "none", 0) + 1
            L.append("    表头：被裁 %d/%d 列，行盒>1 %d/%d 列；锚点=clippingBox（%s；%d 列无裁切盒，不进分母）"
                     % (clipped, len(t["th"]) - na, multi, len(t["th"]),
                        "，".join("%s %d" % (k, v) for k, v in sorted(anch.items())), na))
            L.append("    短字段（≤6 全角字 或 含 Tag/Button）单元格 %d 个，其中折行 %d 个；其它单元格折行 %d 个（总 %d 格）"
                     % (t["shortFieldCells"], t["shortFieldWrapped"], t["otherWrappedCells"], t["cellsSeen"]))
            for s in t["shortWrappedSample"]:
                L.append("      折行样本 r%d c%d 「%s」 行盒 %d / 格高 %s" % (s["r"], s["c"], s["text"], s["lines"], s["h"]))
            if t.get("need"):
                L.append("    needW（按最内层元素字号量；needInner=内层元素外宽+格 padding，"
                         "needTd=整格文字按 td 字号量）")
                L.append("    i  渲染宽   needInner needSum needTd   内层元素(字号)      结论")
                for c in t["need"]:
                    L.append("    %-2d %-8s %-9s %-7s %-8s %-20s %s"
                             % (c["i"], c["renderedW"], c["needInner"], c["needSum"], c["needTd"],
                                "%s@%s" % (c["leaf"], c["leafFont"]),
                                ("放得下" if c["fitsInner"] else "放不下")
                                + ("" if c["fitsInner"] == c["fitsTd"]
                                   else "（td 字号口径结论相反：%s）"
                                        % ("放得下" if c["fitsTd"] else "放不下"))))
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
