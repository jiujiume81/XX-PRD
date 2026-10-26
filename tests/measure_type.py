#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I-09 第三阶段：S-01（字号档数）/ S-02（行高）的**只读量具**。

这份脚本**不判 PASS/FAIL、不设阈值、不占判据编号**。它只回答一个问题：
「这几份产物上，S-01 / S-02 到底量出什么数」。阈值由人按实测裁定，然后才接线。

为什么不直接把 `references/12` 表里那两行从 `人工` 改成 `shape`：
那两行的阈值来源至今没被实测过（`12:38` 已写死这条禁令）。先把未经测量的数钉进判据，
下一轮就会看到「判据在自己从没量过的东西上判红」—— 与 `P24` 分母那次同型。

复用 `check_ui_shape` 的 `PROBE` / `build_case_src` / `run_viewport` / `VIEWPORTS`，
只在 `emit(d)` 之前插一段私有测量（与 `measure_reject.py` 同一手法）：
两套探针一旦分叉，「门量到的产物」与「人看到的页面」就不是同一份 DOM。

## 口径（量之前先定分母，否则「3 档」与「3 档但全错」同色）

- **分母** = 内容区内**有直接非空文本节点**的元素，每个元素只计一次；
  跳过 `script`/`style`、跳过无盒（`getClientRects().length === 0`）的节点。
  容器外壳（Sider / Header / `#prdToggle` 等评审态元素）**不在** `.ant-content` 里，天然不计入。
  **排除数逐类打出来**（空文本 / script-style / 无盒 / 同元素重复），四类相加 + 分母 = 文本节点总数，
  这一行就是分母的自证 —— 否则「分母 212」与「分母漏了一半」读起来一样。
- **S-01**：上述元素 `getComputedStyle().fontSize` 的**去重集合**与各档节点数。
- **S-02 ①**：表格 `tbody tr` 的高度（**排除 `thead`**：表头 34 与数据行 34 不是同一件事），
  报集合、最高值、表头行高（单列参考值，不计入）。
  一页可能有两张表（CAPA 的 `page-capa-list` 就是），所以**按表分桶、定位串带 `table[n]>`**，
  再合并上报；不分桶会把「两张表各自整齐」读成「一张表行高不一致」。
- **S-02 ②**：**表格外**有文字元素的 `line-height ÷ font-size`（分母是 `font-size`，不是行盒高）；
  `line-height: normal` 的元素单独计数，不混进比值里。被排除的表格内文字元素数单独打。

## 逐值可定位

每个档位不只给「31 个」，还给**能再点一次的定位串**（`tag.class` + 父级 `tag.class` + 同级序号），
按节点数降序取前 4 类，剩余打「另 N 类 M 个」。只给数字人没法复核。

## 两档分开报

- **产品态** 1440 / 1600（无外壳，内容宽 1184 / 1344）；
- **评审态** 1600x1000 / 1440x900（有外壳，内容宽 1026 / 866）。
给人看的档与给机器量的档不是一套，混在一行会把「档位差」读成「产物差」。

## 量具必须能报出「4 档」

`--inject-size 19` 给内容区若干文字元素改字号（内联样式会被 `productStage()` 的 clone 带进去，
所以两态都生效），S-01 必须读出 **4 档**。
读不出 4 的量具，说「3 档」等于什么都没说（与 `--th-span`、`V01_maxw` 同一个自证思路）。

## 坏样本上也要能量

`example-05`（18 条登记红）必须照样出分布。在好样本上量出漂亮数字，
说明不了它能在坏样本上量 —— 那是量具的强弱测试。

用法:
    python3 tests/measure_type.py assets/examples/example-06-dense-list.json
    python3 tests/measure_type.py FILE --page page-capa-list
    python3 tests/measure_type.py FILE --inject-size 19      # 量具自证：必须读出 4 档
    python3 tests/measure_type.py FILE --json

退出码: 0 = 量到了；2 = 环境不可用（Chrome / 探针未产出）
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_ui_shape as S  # noqa: E402

EXTRA_JS = r"""
  /* ---- S-01 / S-02 只读量具（I-09 第三阶段）。不判红，只报数。 ---- */
  function _cls(el){
    var cn=el.className;
    if(cn && cn.baseVal!==undefined) cn=cn.baseVal;
    if(typeof cn!=='string') return '';
    var ar=cn.trim().split(/\s+/).filter(Boolean);
    return ar.length? '.'+ar[0] : '';
  }
  /* 定位串：自己的 tag.class + 父级 tag.class + 同级序号。
     产品态 clone 会抹掉所有 id（productStage 里 e.id=''），所以不靠 id。 */
  function _sel(el){
    var self=el.tagName.toLowerCase()+_cls(el);
    var p=el.parentElement, s=self;
    if(p && p.tagName!=='BODY' && p.tagName!=='HTML')
      s=p.tagName.toLowerCase()+_cls(p)+'>'+self;
    var i=1, q=el;
    while((q=q.previousElementSibling)){ try{ if(q.matches(self)) i++; }catch(e){} }
    return s+'['+i+']';
  }
  function _bump(m, k, el){
    var b=m[k]||(m[k]={n:0,locs:{}});
    b.n++;
    var s=_sel(el); b.locs[s]=(b.locs[s]||0)+1;
  }
  /* 只留前 top 类，其余折成 rest —— 逐值清单要能看，不是把整页倒出来 */
  function _cap(m, top){
    var out={};
    for(var k in m){
      var b=m[k], arr=[];
      for(var L in b.locs) arr.push([L, b.locs[L]]);
      arr.sort(function(a,c){ return c[1]-a[1] || (a[0]<c[0]?-1:1); });
      out[k]={n:b.n, locs:arr.slice(0,top), rest:arr.slice(top),
              restN:arr.slice(top).reduce(function(t,x){return t+x[1];},0),
              distinct:arr.length};
    }
    return out;
  }
  function _textEls(root){
    var out=[], seen=new WeakSet();
    var meta={textNodes:0, empty:0, scriptStyle:0, noBox:0, dup:0, denom:0, tableEls:0};
    if(!root){ meta.denom=0; return {els:out, meta:meta}; }
    var tw=document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), n;
    while((n=tw.nextNode())){
      meta.textNodes++;
      if(!(n.nodeValue||'').trim()){ meta.empty++; continue; }
      var el=n.parentElement;
      if(!el){ meta.noBox++; continue; }
      if(el.closest('script,style')){ meta.scriptStyle++; continue; }
      if(!el.getClientRects().length){ meta.noBox++; continue; }   /* 无盒的不算：隐藏节点会把分母撑大 */
      if(seen.has(el)){ meta.dup++; continue; }                    /* 同一元素多个文本节点只计一次 */
      seen.add(el); out.push(el);
    }
    meta.denom=out.length;
    for(var i=0;i<out.length;i++){ if(out[i].closest('.ant-table')) meta.tableEls++; }
    return {els:out, meta:meta};
  }

  function _snap(root){
    var out={meta:null,
             fonts:{sizes:[],counts:{},buckets:{},total:0},
             tableRows:{sizes:[],counts:{},buckets:{},max:null,headH:[]},
             lineRatios:{ratios:[],counts:{},buckets:{},normal:0,excludedTable:0,total:0}};
    if(!root) return null;
    var te=_textEls(root), els=te.els;
    out.meta=te.meta;

    /* S-01：字号档数（分母 = 有直接文本的元素） */
    var fm={}, total=0;
    for(var i=0;i<els.length;i++){
      var fs=parseFloat(getComputedStyle(els[i]).fontSize);
      if(!(fs>0)) continue;
      var k=Math.round(fs*10)/10;
      _bump(fm, k, els[i]); total++;
    }
    out.fonts.counts={}; for(var fk in fm) out.fonts.counts[fk]=fm[fk].n;
    out.fonts.buckets=_cap(fm, 4); out.fonts.total=total;
    out.fonts.sizes=Object.keys(fm).map(Number).sort(function(a,b){return a-b;});

    /* S-02 ①：tbody 行高（排除表头）。
       一页可能有两张表（CAPA 的 page-capa-list 就是），所以**按表分桶**再合并上报：
       定位串带 `table[n]>`，否则「tbody tr[0]」说不清是哪张表的第 0 行，
       两表行高不同时人也分不清那是设计差还是缺陷。 */
    var tabs=root.querySelectorAll('.ant-table'), hm={}, hmax=null, hn=0, tinfo=[];
    for(var ti=0; ti<tabs.length; ti++){
      if(tabs[ti].parentElement && tabs[ti].parentElement.closest('.ant-table')) continue;  /* 嵌套表不重复计 */
      var trs=tabs[ti].querySelectorAll('tbody tr'), tj=0;
      for(var j=0;j<trs.length;j++){
        var h=trs[j].offsetHeight;
        if(!(h>0)) continue;
        var b=hm[h]||(hm[h]={n:0,locs:{}});
        b.n++; hn++;
        var rk=trs[j].getAttribute('data-row-key');
        var rl='table['+(ti+1)+']>tbody tr'+(rk?('[data-row-key="'+rk+'"]'):('['+j+']'));
        b.locs[rl]=(b.locs[rl]||0)+1; tj++;
        if(hmax===null || h>hmax) hmax=h;
      }
      tinfo.push({i:ti+1, rows:tj});
    }
    out.tableRows.counts={}; for(var hk in hm) out.tableRows.counts[hk]=hm[hk].n;
    out.tableRows.buckets=_cap(hm, 3); out.tableRows.max=hmax; out.tableRows.total=hn;
    out.tableRows.tables=tinfo;
    out.tableRows.sizes=Object.keys(hm).map(Number).sort(function(a,b){return a-b;});
    var ths=root.querySelectorAll('.ant-table thead tr');
    for(var t=0;t<ths.length;t++){ out.tableRows.headH.push(ths[t].offsetHeight); }

    /* S-02 ②：表格外文字元素的 line-height ÷ font-size（分母是 font-size） */
    var rm={}, normal=0, rt=0, excl=0;
    for(var q=0;q<els.length;q++){
      var el2=els[q];
      if(el2.closest('.ant-table')){ excl++; continue; }          /* 「正文」不含表格内文字 */
      var cs=getComputedStyle(el2);
      var fs2=parseFloat(cs.fontSize), lh=cs.lineHeight;
      if(!(fs2>0)) continue;
      if(!lh || lh==='normal'){ normal++; continue; }
      var px=parseFloat(lh);
      if(!(px>0)){ normal++; continue; }
      var r=Math.round(px/fs2*100)/100;
      _bump(rm, r, el2); rt++;
    }
    out.lineRatios.counts={}; for(var rk2 in rm) out.lineRatios.counts[rk2]=rm[rk2].n;
    out.lineRatios.buckets=_cap(rm, 4); out.lineRatios.normal=normal;
    out.lineRatios.excludedTable=excl; out.lineRatios.total=rt;
    out.lineRatios.ratios=Object.keys(rm).map(Number).sort(function(a,b){return a-b;});
    return out;
  }

    function typeExtras(){
    var out={review:null, reviewContentW:null, product:[], injected:(window.__injType||null)};
    var C=document.querySelector('#protoCanvas .ant-content');
    if(C){
      var scs=getComputedStyle(C);
      out.reviewContentW=num(C.clientWidth-parseFloat(scs.paddingLeft||0)-parseFloat(scs.paddingRight||0));
      out.review=_snap(C);
    }
    /* 产品态两档：productStage() 会**先拆再建**，所以每次建完立刻量，不留两层 */
    var widths=[1440,1600];
    for(var i=0;i<widths.length;i++){
      var st=null;
      try{ st=productStage(widths[i]); }catch(e){ st={err:String(e && e.message)}; }
      var ov=document.getElementById('__prodStage');
      var CC=ov? ov.querySelector('.ant-content') : null;
      out.product.push({w:widths[i], contentBoxW:(st&&st.contentBoxW)||null,
                        err:(st&&st.err)||null, snap:CC?_snap(CC):null});
    }
    return out;
  }
"""


def build_probe(inject=""):
    """在 PROBE 的 emit 之前插私有测量；measure() / productStage() 一字不改。

    注入必须放在 `measure()` **之后**：`measure()` 里会点 `#prdToggle` 折叠 PRD，
    那次重排会把内容区重绘一遍，之前写上去的内联 `font-size` 全被抹掉
    （首版把注入挂在容器的 `/*__INJECT__*/` 上，实测 S-01 仍是 3 档 —— 就是这个原因）。
    """
    marker = "    emit(d);"
    assert S.PROBE.count(marker) == 1, "PROBE 结构变了：emit(d) 不是唯一一处"
    body = "    try{ d.types=typeExtras(); }catch(exT){ d.types={err:'TYPE:'+exT.message}; }\n"
    if inject:
        body = "    try{ %s }catch(exI){}\n" % inject + body
    return S.PROBE.replace(marker, body + marker).replace(
        "waitInit(function(tries){", EXTRA_JS + "\nwaitInit(function(tries){")


INJECT_JS = (
    "(function(){var C=document.querySelector('#protoCanvas .ant-content');if(!C)return;"
    "var tw=document.createTreeWalker(C,NodeFilter.SHOW_TEXT,null),n,k=0,hit=[];"
    "while((n=tw.nextNode())&&k<6){if(!(n.nodeValue||'').trim())continue;"
    "var el=n.parentElement;if(!el||el.closest('.ant-table')||!el.getClientRects().length)continue;"
    # 只改 14px 这一档：把已有档位挪走不算「多出一档」（首版连 18px 的 h1 一起改，
    # 实测读出 {12、14、19} 仍是 3 档 —— 档数没增，反而把 18 弄没了）。
    "if(parseFloat(getComputedStyle(el).fontSize)!==14)continue;"
    # `.ant-btn{transition:.15s}` 是**全属性**过渡：改完立刻读 computed 会读到过渡起点（14px），
    # 首版因此读出「产品态 6 个、评审态 4 个」的假不一致。注入前先关掉过渡再强制重排。
    "el.style.transition='none';el.style.fontSize='%dpx';void el.offsetWidth;"
    "hit.push(_sel(el)+'→'+getComputedStyle(el).fontSize);k++;}"
    "window.__injType={n:k,locs:hit};})()"
)


def _key(s):
    """JS 对象的键是字符串（`'12'`），Python 侧 `sizes` 可能是 int/float —— 归一化后再查。"""
    if isinstance(s, float) and s.is_integer():
        return str(int(s))
    return str(s)


def _fmt_set(vals, counts, buckets, unit=""):
    if not vals:
        return "（空）｜分母 0"
    head = "{%s}（%d 档）" % ("、".join("%s%s" % (_fmt_num(v), unit) for v in vals), len(vals))
    rows = []
    for v in vals:
        k = _key(v)
        n = counts.get(k, counts.get(str(v), 0))
        b = (buckets or {}).get(k) or {}
        locs = b.get("locs") or []
        s = "%s%s %d 个" % (_fmt_num(v), unit, n)
        if locs:
            s += " ｜ " + "、".join("%s×%d" % (L, c) for L, c in locs)
            if b.get("rest"):
                s += " ｜ 另 %d 类 %d 个" % (len(b["rest"]), int(b.get("restN") or 0))
        elif n:
            s += " ｜ （定位串缺失）"
        rows.append("    " + s)
    return "\n".join([head] + rows)


def _fmt_num(v):
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _meta_line(m):
    if not m:
        return "  分母与排除：（量不到）"
    return ("  分母与排除：文本节点 %d ｜ 空文本 %d ｜ script/style %d ｜ 无盒 %d ｜ 同元素重复 %d "
            "｜ **计入分母 %d**（其中在 .ant-table 内 %d，S-01 计入、S-02② 排除）"
            % (m.get("textNodes", 0), m.get("empty", 0), m.get("scriptStyle", 0),
               m.get("noBox", 0), m.get("dup", 0), m.get("denom", 0), m.get("tableEls", 0)))


def _block(s, label):
    L = (["  %s" % label] if label else []) + [_meta_line(s.get("meta"))]
    L.append("  S-01 font-size 去重 %s" % _fmt_set(
        s["fonts"]["sizes"], s["fonts"]["counts"], s["fonts"].get("buckets")))
    tr = s["tableRows"]
    tabs = tr.get("tables") or []
    L.append("  S-02① 数据行高 最高 %s ｜ 表头行高 %s（不计入）｜ 数据行 %d 行（%s）"
             % (tr["max"],
                ("{%s}" % "、".join(str(x) for x in tr["headH"])) if tr["headH"] else "（无表头）",
                tr.get("total", 0),
                " / ".join("table[%d] %d 行" % (x["i"], x["rows"]) for x in tabs) or "无表"))
    L.append(_fmt_set(tr["sizes"], tr["counts"], tr.get("buckets"), "px"))
    lr = s["lineRatios"]
    denom = (s.get("meta") or {}).get("denom", 0)
    L.append("  S-02② 正文行高比（分母 font-size，不含表格内文字）｜line-height:normal 的元素 %d "
             "｜ 被排除的表格内文字元素 %d（%d+%d=%d，应与分母 %d 相等）"
             % (lr["normal"], lr.get("excludedTable", 0), lr.get("total", 0),
                lr.get("excludedTable", 0), lr.get("total", 0) + lr.get("excludedTable", 0), denom))
    L.append(_fmt_set(lr["ratios"], lr["counts"], lr.get("buckets")))
    return L


def _pretty(res):
    L = ["FILE %s" % res["file"], "PAGE %s（%s）" % (res["page"], res["pageName"]), "",
         "口径：分母 = 内容区内**有直接文本**的元素（每元素一次，跳过 script/style/无盒）；"
         "S-01 含表格内文字；S-02① 排除表头；S-02② 分母是 font-size 且不含表格内文字。",
         "定位串 = 父级.tag.class > 自身.tag.class[同级序号]（产品态 clone 抹 id，所以不用 id）。"]
    if res.get("inject_size"):
        inj = (res["runs"][0]["types"] or {}).get("injected") or {}
        L.append("注入：--inject-size %s，实际改了 %s 个内容区文字元素（两态都生效）"
                 % (res["inject_size"], inj.get("n", "?")))
        if inj.get("locs"):
            L.append("  注入点：" + "、".join(inj["locs"]))
    runs = res["runs"]
    prod = runs[0]["types"].get("product") or []
    for p in prod:
        s = p.get("snap")
        L.append("")
        L.append("产品态 %d（内容宽 %s）%s" % (p["w"], p.get("contentBoxW"),
                                          "  ERR=%s" % p["err"] if p.get("err") else ""))
        if not s:
            L.append("  （量不到：舞台里没有 .ant-content）")
            continue
        L += _block(s, "")
    # 两档外框下产品态读数是否一致（不一致说明舞台宽没锁死，读数是假的）
    if len(runs) > 1:
        a = runs[0]["types"].get("product") or []
        b = runs[1]["types"].get("product") or []
        for i in range(min(len(a), len(b))):
            sa, sb = a[i].get("snap"), b[i].get("snap")
            if sa and sb and sa["fonts"]["counts"] != sb["fonts"]["counts"]:
                L.append("  注：产品态 %s 在两档外框下读数不同（%s vs %s）"
                         % (a[i]["w"], sa["fonts"]["counts"], sb["fonts"]["counts"]))
    # 产品态（clone）与评审态（原 DOM）是否同一套档位：clone 会抹 id，理论上可能分叉
    r0 = (runs[0]["types"].get("review") or {}).get("fonts", {}).get("counts")
    p0 = ((runs[0]["types"].get("product") or [{}])[0].get("snap") or {}).get("fonts", {}).get("counts")
    if r0 and p0 and r0 != p0:
        L.append("  注：产品态与评审态字号计数不同（评审 %s vs 产品 %s）—— 产品态是 clone，"
                 "抹 id 后若有 id 选择器设字号会分叉，读数需按态分开看" % (r0, p0))
    for r in runs:
        w, h = r["vw"]
        L.append("")
        L.append("评审态 %dx%d（内容宽 %s）" % (w, h, r["types"].get("reviewContentW")))
        s = r["types"].get("review")
        if not s:
            L.append("  （量不到：没有 .ant-content）")
            continue
        L += _block(s, "")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="S-01 / S-02 只读量具（不出阈值、不判红）")
    ap.add_argument("file")
    ap.add_argument("--page")
    ap.add_argument("--json", action="store_true", help="只打机器可读 JSON")
    ap.add_argument("--inject-size", type=int, metavar="PX",
                    help="量具自证：把内容区若干文字元素改成该字号，S-01 必须读出「原档数+1」")
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

    S.PROBE = build_probe(INJECT_JS % a.inject_size if a.inject_size else "")
    tmp = Path(tempfile.mkdtemp(prefix="xx-prd-type-"))
    html = tmp / "case.html"
    src = Path(S.CONTAINER).read_text(encoding="utf-8")
    S.build_case_src(src, data, page["id"], html)

    runs = []
    for w, h in S.VIEWPORTS:            # (1600,1000) → 内容宽 1026；(1440,900) → 866
        d = S.run_viewport(chrome, html, w, h)
        if not d or not d.get("types") or d["types"].get("err"):
            print("ENV: 探针没有产出（%s）" % (d.get("types") if d else "no data"))
            return 2
        runs.append({"vw": [w, h], "types": d["types"]})

    res = {"file": str(path), "page": page.get("id"), "pageName": page.get("name"),
           "inject_size": a.inject_size, "runs": runs}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(_pretty(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
