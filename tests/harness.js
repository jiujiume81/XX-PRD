(function () {
  function run() {
    var out = [], failN = 0;
    function ok(m) { out.push('ok   ' + m); }
    function fail(m) { out.push('FAIL ' + m); failN++; }
    function info(m) { out.push('--   ' + m); }
    function $(s) { return document.querySelector(s); }
    function $$(s) { return Array.prototype.slice.call(document.querySelectorAll(s)); }
    function click(el) { el.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
    function txt(el) { return (el && el.textContent || '').trim(); }
    function pById(list, id) { return list.filter(function (x) { return x.id === id; })[0] || {}; }
    /* 展开导航树里所有可折叠节点（不触发页面跳转） */
    function expandAll() {
      for (var pass = 0; pass < 8; pass++) {
        var closed = $$('#navTree .caret').filter(function (c) {
          return !c.classList.contains('open') && !c.classList.contains('leaf');
        });
        if (!closed.length) return;
        closed.forEach(function (c) { click(c); });
      }
    }
    /* 判断 pid 是否为「命中筛选」的页面的祖先 */
    function isAncestorOfHit(pid, pages, f) {
      var hit = false;
      pages.forEach(function (p) {
        var s = ((p.name || '') + ' ' + (p.route || '') + ' ' + (p.id || '') + ' ' + (p.goal || '')).toLowerCase();
        if (s.indexOf(f) < 0) return;
        var cur = p, guard = 0;
        while (cur && cur.parentId && guard++ < 20) {
          if (cur.parentId === pid) { hit = true; return; }
          cur = pById(pages, cur.parentId);
        }
      });
      return hit;
    }

    try {
      var data = JSON.parse(document.getElementById('iprd-data').textContent);
      var pages = data.pages || [];
      var mods = data.modules || [];
      var bootHash = location.hash;

      /* 1 左侧导航树：模块分组 */
      expandAll();
      var groups = $$('#navTree .nav-row.grp');
      var orphanN = pages.filter(function (p) {
        var okMod = p.moduleId && mods.some(function (m) { return m.id === p.moduleId; });
        var viaList = mods.some(function (m) { return (m.pageIds || []).indexOf(p.id) >= 0; });
        return !okMod && !viaList;
      }).length;
      var expGroups = mods.length + (orphanN ? 1 : 0);
      groups.length === expGroups
        ? ok('导航渲染 ' + groups.length + ' 个模块分组（声明 ' + mods.length + ' 个模块' + (orphanN ? ' + 未分组' : '') + '）')
        : fail('模块分组 ' + groups.length + ' ≠ 期望 ' + expGroups);
      if (orphanN) {
        txt($('#navTree')).indexOf('未分组') >= 0 ? ok('无归属页面已归入「未分组」（' + orphanN + ' 页）')
                                                 : fail('未分组分组缺失');
      }

      /* 2 导航树：页面节点齐全 */
      var rows = $$('#navTree [data-page-id]');
      rows.length === pages.length
        ? ok('导航渲染 ' + rows.length + ' 个页面节点，与页面数一致')
        : fail('页面节点 ' + rows.length + ' ≠ 页面数 ' + pages.length);
      txt($('#navCount')) === (pages.length + ' 页')
        ? ok('导航计数显示「' + txt($('#navCount')) + '」')
        : fail('导航计数错误：' + txt($('#navCount')));

      /* 3 多级页面：父子缩进与层级 */
      var nested = pages.filter(function (p) { return p.parentId && pById(pages, p.parentId).id; });
      if (nested.length) {
        var allOk = nested.every(function (p) {
          var self = $('#navTree [data-page-id="' + p.id + '"]');
          var par = $('#navTree [data-page-id="' + p.parentId + '"]');
          if (!self || !par) return false;
          var si = parseInt(self.style.paddingLeft, 10), pi = parseInt(par.style.paddingLeft, 10);
          return si > pi;
        });
        allOk ? ok('多级页面渲染正确：' + nested.length + ' 个子页面缩进深于父页面')
              : fail('多级页面缩进/父子关系不正确');
      } else info('当前数据集无嵌套页面（parentId）');

      /* 4 面包屑 */
      var curId = ($('#navTree .nav-row.sel') || {}).getAttribute ? $('#navTree .nav-row.sel').getAttribute('data-page-id') : '';
      var curPage = pById(pages, curId) || pages[0];
      var crumb = txt($('#navCrumb'));
      (crumb && crumb.indexOf(curPage.name) >= 0)
        ? ok('面包屑显示当前位置：' + crumb)
        : fail('面包屑未显示当前页「' + curPage.name + '」，实际：' + crumb);
      /* 面包屑应含祖先链 */
      if (curPage.parentId) {
        var anc = pById(pages, curPage.parentId);
        crumb.indexOf(anc.name) >= 0 ? ok('面包屑包含父级「' + anc.name + '」') : fail('面包屑缺少父级链路');
      }

      /* 5 原型渲染 */
      var nc = $$('#protoCanvas [data-node-id]').length;
      nc > 5 ? ok('原型渲染 ' + nc + ' 个组件节点') : fail('原型节点过少：' + nc);

      /* 6 未知组件降级 */
      var unk = $$('#protoCanvas .ant-unknown').length;
      unk === 0 ? ok('无未知组件降级') : fail('存在 ' + unk + ' 个未知组件降级块');

      /* 7 容器内部警告 */
      var wc = txt($('#warnCount'));
      wc === '0' ? ok('容器内部零警告') : fail('容器内部产生 ' + wc + ' 条警告');

      /* 8 组件覆盖 */
      var comps = { '表格': '.ant-table', '菜单': '.ant-menu .mi', '统计卡': '.ant-stat .s-v',
        '状态标签': '.ant-tag', '按钮': '.ant-btn', '步骤条': '.ant-step', '卡片': '.ant-card',
        '描述列表': '.ant-desc .d-item', '上传区': '.ant-upload', '提示条': '.ant-alert',
        '时间线': '.ant-timeline .ti', '设备框': '.ant-frame' };
      var hits = [];
      for (var k in comps) { var n = $$('#protoCanvas ' + comps[k]).length; if (n) hits.push(k + '×' + n); }
      ok('当前页渲染组件：' + (hits.join('、') || '（无）'));

      /* 9 PRD 面板 */
      var secN = $$('#prdBody .prd-sec').length;
      secN >= 5 ? ok('PRD 渲染 ' + secN + ' 个章节') : fail('PRD 章节过少：' + secN);
      var reqN = $$('#prdBody .prd-req-table tbody tr').length;
      reqN ? ok('PRD 需求表渲染 ' + reqN + ' 行') : fail('PRD 需求表未渲染');
      var edN = $$('#prdBody [contenteditable="true"]').length;
      edN ? ok('PRD 可编辑区域 ' + edN + ' 个') : fail('PRD 无 contenteditable 区域');

      /* 10 状态切换 */
      var sel = $('#stateSelect');
      var stN = (curPage.states || []).length;
      sel.options.length === stN
        ? ok('状态下拉 ' + sel.options.length + ' 项，与页面状态数一致')
        : fail('状态下拉 ' + sel.options.length + ' 项 ≠ 状态数 ' + stN);
      var base = $$('#protoCanvas [data-node-id]').length, changed = 0, serr = 0;
      for (var i = 0; i < sel.options.length; i++) {
        sel.value = sel.options[i].value;
        try { sel.dispatchEvent(new Event('change')); } catch (e) { serr++; }
        var now = $$('#protoCanvas [data-node-id]').length;
        if (now !== base || $$('#protoCanvas .ant-skel-line').length ||
            $$('#protoCanvas .st-disabled').length ||
            $$('#protoCanvas [style*="display: none"]').length) changed++;
      }
      serr === 0 ? ok(sel.options.length + ' 个状态逐一切换无异常') : fail(serr + ' 个状态切换抛错');
      changed >= 2 ? ok(changed + '/' + sel.options.length + ' 个状态产生可见视觉差异（覆写生效）')
                   : fail('仅 ' + changed + ' 个状态有视觉差异，覆写可能失效');
      if (sel.options.length) { sel.value = sel.options[0].value; sel.dispatchEvent(new Event('change')); }

      /* 11 交互模拟 */
      var ixs = curPage.interactions || [];
      if (ixs.length) {
        /* 挑一个「在原型里真实存在」的目标：优先字面 id，其次把通配展开成第 0 行/第 0 行的按钮 */
        function expandWild(t) {
          return String(t).replace('__row_*', '__row_0').replace(/__act_\*_/, '__act_0_');
        }
        var tgt = null, el = null;
        ixs.forEach(function (ix) {
          if (el) return;
          var t = (ix.on || {}).target;
          if (!t) return;
          var cand = $('#protoCanvas [data-node-id="' + t + '"]');
          if (!cand && t.indexOf('*') >= 0) cand = $('#protoCanvas [data-node-id="' + expandWild(t) + '"]');
          if (cand) { tgt = t; el = cand; }
        });
        if (!el) { tgt = ixs[0].on.target; el = $('#protoCanvas [data-node-id="' + tgt + '"]'); }
        if (el) {
          var before = $('#protoCanvas').innerHTML.length;
          click(el);
          var after = $('#protoCanvas').innerHTML.length;
          var ov = $$('#protoCanvas .ant-modal-mask, #protoCanvas .ant-drawer-mask').length;
          var ts = $$('#toastWrap .toast').length;
          (after !== before || ov || ts)
            ? ok('点击交互目标「' + tgt + '」有响应（DOM 变化 / 浮层 / 轻提示）')
            : fail('点击「' + tgt + '」无任何响应');
        } else fail('交互目标「' + tgt + '」在原型中找不到元素');
      } else info('当前页无交互定义');

      /* 12 导航跳转 + 面包屑同步 */
      var originId = ($('#navTree .nav-row.sel') || {}).getAttribute ? $('#navTree .nav-row.sel').getAttribute('data-page-id') : '';
      var other = $$('#navTree [data-page-id]').filter(function (r) { return r.getAttribute('data-page-id') !== originId; })[0];
      if (other) {
        var oid = other.getAttribute('data-page-id');
        var oname = pById(pages, oid).name || '';
        click(other);
        var selNow = $('#navTree .nav-row.sel');
        var selId = selNow ? selNow.getAttribute('data-page-id') : '';
        selId === oid ? ok('点击导航节点切换到「' + oname + '」') : fail('导航点击未切换（现为 ' + selId + '）');
        txt($('#navCrumb')).indexOf(oname) >= 0 ? ok('面包屑同步为「' + txt($('#navCrumb')) + '」')
                                                : fail('面包屑未同步：' + txt($('#navCrumb')));
        var backRow = $('#navTree [data-page-id="' + originId + '"]');
        if (backRow) click(backRow);
      } else info('数据集仅 1 页，跳过导航跳转测试');

      /* 13 导航筛选 */
      var nf = $('#navFilter');
      if (nf && pages.length >= 2) {
        var frag = (pages[pages.length - 1].id || '').toLowerCase();
        nf.value = frag;
        nf.dispatchEvent(new Event('input', { bubbles: true }));
        var frows = $$('#navTree [data-page-id]');
        function hitText(p) {
          return ((p.name || '') + ' ' + (p.route || '') + ' ' + (p.id || '') + ' ' + (p.goal || '')).toLowerCase();
        }
        var bad = frows.filter(function (r) {
          var pid = r.getAttribute('data-page-id');
          return hitText(pById(pages, pid)).indexOf(frag) < 0 && !isAncestorOfHit(pid, pages, frag);
        });
        /* 「显示的行数应少于总页数」只在数据集里确实存在「既不命中、也不是命中项祖先」的页面时才成立；
           当筛选词命中的是某页的子页面时，父页面作为祖先链本就应该一起显示。 */
        var shouldShrink = pages.some(function (p) {
          return hitText(p).indexOf(frag) < 0 && !isAncestorOfHit(p.id, pages, frag);
        });
        (frows.length >= 1 && bad.length === 0 && (!shouldShrink || frows.length < pages.length))
          ? ok('筛选「' + frag + '」命中 ' + frows.length + ' 页，且仅显示命中项及其祖先'
               + (shouldShrink ? '' : '（命中项为子页面，祖先链一并保留）'))
          : fail('筛选异常：显示 ' + frows.length + ' / ' + pages.length + '，越权项 ' + bad.length);
        nf.value = '';
        nf.dispatchEvent(new Event('input', { bubbles: true }));
        $$('#navTree [data-page-id]').length === pages.length
          ? ok('清空筛选后恢复全部 ' + pages.length + ' 个页面节点')
          : fail('清空筛选未恢复');
      } else info('数据集页面不足，跳过筛选测试');

      /* 14 导航折叠 / 展开 */
      var pane = $('#paneNav');
      click($('#navCollapse'));
      pane.classList.contains('collapsed') ? ok('收起导航：左栏已折叠') : fail('收起导航失败');
      click($('#btnNav'));
      !pane.classList.contains('collapsed') ? ok('顶栏按钮可重新展开导航') : fail('展开导航失败');

      /* 15 全局画布（页面关系图） */
      /* 期望边数：navigate 动作 + entryFrom 兜底（同名去重） */
      var expEdge = 0, edgeSeen = {};
      pages.forEach(function (p) {
        (p.interactions || []).forEach(function (ix) {
          (ix.actions || []).forEach(function (a) {
            if (a.type !== 'navigate' || !a.pageId || !pById(pages, a.pageId)) return;
            var k = p.id + '>' + a.pageId;
            if (edgeSeen[k]) return; edgeSeen[k] = 1; expEdge++;
          });
        });
        (p.entryFrom || []).forEach(function (src) {
          if (!pById(pages, src)) return;
          var k2 = src + '>' + p.id;
          if (edgeSeen[k2]) return; edgeSeen[k2] = 1; expEdge++;
        });
      });

      click($('#btnCanvas'));
      $('#canvasOverlay').classList.contains('on') ? ok('关系图浮层已打开') : fail('关系图未打开');
      var cn = $$('#coWorld .co-node').length;
      cn === pages.length ? ok('关系图渲染 ' + cn + ' 张页面卡片，与页面数一致')
                          : fail('关系图卡片 ' + cn + ' ≠ 页面数 ' + pages.length);
      var ce = $$('#coSvg .co-edge').length;
      (ce === expEdge && expEdge > 0)
        ? ok('关系图连线 ' + ce + ' 条，与 navigate + 入口关系一致')
        : (expEdge === 0 ? info('数据集无页面间跳转，跳过连线数量校验')
                         : fail('关系图连线 ' + ce + ' ≠ 期望 ' + expEdge));
      $$('#coSvg .co-elabel').length ? ok('关系图连线带触发标签（' + $$('#coSvg .co-elabel').length + ' 个）')
                                     : info('数据集无带标签的跳转');
      $$('#coLegend div').length >= 3 ? ok('关系图图例齐全（实线/虚线/高亮）') : fail('关系图图例不足');
      $$('#coWorld .co-node.co-cur').length === 1 ? ok('关系图标记出当前页卡片') : fail('关系图未标记当前页');
      /* 卡片尺寸必须正常（曾因 .sel 类名与顶栏 <select> 冲突被压成 190×30） */
      var badSize = $$('#coWorld .co-node').filter(function (n) {
        return n.offsetWidth < 200 || n.offsetHeight < 150;
      });
      badSize.length === 0
        ? ok('关系图 ' + $$('#coWorld .co-node').length + ' 张卡片尺寸正常（≥200×150）')
        : fail('关系图有 ' + badSize.length + ' 张卡片尺寸异常，最小 '
               + Math.min.apply(null, badSize.map(function (n) { return n.offsetWidth; })) + '×'
               + Math.min.apply(null, badSize.map(function (n) { return n.offsetHeight; })));
      /* 卡片不得重叠 */
      var cnEls = $$('#coWorld .co-node'), ovN = 0;
      for (var oi = 0; oi < cnEls.length; oi++) {
        for (var oj = oi + 1; oj < cnEls.length; oj++) {
          var ra2 = cnEls[oi].getBoundingClientRect(), rb2 = cnEls[oj].getBoundingClientRect();
          if (ra2.left < rb2.right - 1 && rb2.left < ra2.right - 1 &&
              ra2.top < rb2.bottom - 1 && rb2.top < ra2.bottom - 1) ovN++;
        }
      }
      ovN === 0 ? ok('关系图卡片无重叠') : fail('关系图有 ' + ovN + ' 对卡片重叠');
      /* 分层布局：层必须连续（不能出现空层）。
         曾因环未断导致层号发散 —— 相邻层的 x 间距从 346 变成 3096，图上出现巨宽空白。 */
      var xs = []; $$('#coWorld .co-node').forEach(function (n) { if (xs.indexOf(n.offsetLeft) < 0) xs.push(n.offsetLeft); });
      xs.sort(function (a, b) { return a - b; });
      var maxGap = 0;
      for (var xi = 1; xi < xs.length; xi++) maxGap = Math.max(maxGap, xs[xi] - xs[xi - 1]);
      var pitch = 236 + 110;
      (xs.length <= pages.length && (xs.length < 2 || maxGap <= pitch * 1.5))
        ? ok('关系图分层连续：' + xs.length + ' 层，最大层间距 ' + maxGap + 'px（环上节点未发散）')
        : fail('关系图分层发散：' + xs.length + ' 层，最大层间距 ' + maxGap + 'px');
      var wW = parseFloat($('#coWorld').style.width) || 0;
      wW <= pages.length * 400 + 900
        ? ok('关系图世界宽度合理：' + wW + 'px')
        : fail('关系图世界宽度异常：' + wW + 'px');
      /* 分层布局：LR 下同一层的卡片 x 相同，且存在层级递增 */
      var cxs = $$('#coWorld .co-node').map(function (n) { return n.offsetLeft; });
      var uniqX = {}; cxs.forEach(function (x) { uniqX[x] = 1; });
      Object.keys(uniqX).length <= cxs.length ? ok('关系图按层落位（' + Object.keys(uniqX).length + ' 个层列 / ' + cxs.length + ' 张卡片）')
                                              : fail('关系图未按层落位');
      /* 缩放 */
      var z0c = $('#coZoom').textContent;
      click($('#coOut'));
      $('#coZoom').textContent !== z0c ? ok('关系图缩小：' + z0c + ' → ' + $('#coZoom').textContent)
                                       : fail('关系图缩小无效');
      click($('#coIn'));
      $('#coZoom').textContent === z0c ? ok('关系图放大回到 ' + z0c) : fail('关系图放大未复原：' + $('#coZoom').textContent);
      click($('#coFit'));
      ok('关系图「适应」可执行，当前 ' + $('#coZoom').textContent);
      /* 方向切换 */
      var dirBtn = $$('#coDir button').filter(function (b) { return b.getAttribute('data-dir') === 'TB'; })[0];
      if (dirBtn) {
        click(dirBtn);
        dirBtn.classList.contains('on') ? ok('关系图切到纵向排布') : fail('纵向按钮未激活');
        $$('#coWorld .co-node').length === pages.length ? ok('切换方向后卡片数量不丢') : fail('切换方向后卡片丢失');
        var lrBtn = $$('#coDir button').filter(function (b) { return b.getAttribute('data-dir') === 'LR'; })[0];
        click(lrBtn);
        lrBtn.classList.contains('on') ? ok('关系图切回横向排布') : fail('横向按钮未激活');
      }
      /* 拖拽卡片 → 位置落盘 → 自动排列复位 */
      var card0 = $$('#coWorld .co-node')[0];
      if (card0) {
        var autoLeft = card0.offsetLeft;
        var cr = card0.getBoundingClientRect();
        card0.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: cr.left + 40, clientY: cr.top + 20 }));
        document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: cr.left + 160, clientY: cr.top + 120 }));
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: cr.left + 160, clientY: cr.top + 120 }));
        var movedLeft = card0.offsetLeft;
        movedLeft > autoLeft ? ok('拖拽卡片生效：left ' + autoLeft + ' → ' + movedLeft) : fail('拖拽卡片无效');
        info('DBG after-drag: left='+card0.offsetLeft+' styleLeft='+card0.style.left+' worldW='+$('#coWorld').style.width+' innerW='+$('#coInner').style.width+' zoom='+$('#coZoom').textContent+' scrollC='+$('#coScroll').clientWidth+'x'+$('#coScroll').clientHeight);
        info('DBG LS='+String(localStorage.getItem('iprd::'+(data.meta&&data.meta.product||''))));
        click($('#btnCanvas')); /* 触发重绘，验证位置是否落盘 */
        info('DBG after-redraw: LS='+String(localStorage.getItem('iprd::'+(data.meta&&data.meta.product||'')))+' left='+$$('#coWorld .co-node')[0].offsetLeft);
        var card0b = $$('#coWorld .co-node')[0];
        Math.abs(card0b.offsetLeft - movedLeft) < 2
          ? ok('拖拽位置已保存，重绘后仍保持（left=' + card0b.offsetLeft + '）')
          : fail('拖拽位置未保存：' + card0b.offsetLeft + ' ≠ ' + movedLeft);
        click($('#coArrange'));
        var card0c = $$('#coWorld .co-node')[0];
        Math.abs(card0c.offsetLeft - autoLeft) < 2
          ? ok('「自动排列」把卡片复位回信息架构布局（left=' + card0c.offsetLeft + '）')
          : fail('自动排列未复位：' + card0c.offsetLeft + ' ≠ ' + autoLeft);
      }
      /* 拖拽落盘坐标必须稳定 —— 位置用「内容盒原点 + pad」这一套坐标。
         曾用「pad - 包围盒minX」做归一化：被拖的卡片一旦成为最左上，偏移量跟着变，
         落盘坐标会被二次平移，表现为「拖完一刷新就弹回原位」（单页数据集必现）。 */
      var cSave = $$('#coWorld .co-node')[0];
      if (cSave) {
        var p1a = cSave.offsetLeft;
        var r1 = cSave.getBoundingClientRect();
        cSave.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: r1.left + 30, clientY: r1.top + 15 }));
        document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: r1.left + 90, clientY: r1.top + 75 }));
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: r1.left + 90, clientY: r1.top + 75 }));
        var p1b = cSave.offsetLeft;
        click($('#btnCanvas'));
        var p1c = $$('#coWorld .co-node')[0].offsetLeft;
        (p1b > p1a && Math.abs(p1c - p1b) < 2)
          ? ok('拖拽落盘坐标稳定：' + p1a + ' → ' + p1b + ' → 重绘后 ' + p1c)
          : fail('拖拽落盘坐标漂移：' + p1a + ' → ' + p1b + ' → 重绘后 ' + p1c);
        click($('#coArrange'));
      }

      /* 内容盒 = 卡片包围盒 + pad（多留一档会让「适应」永远铺不满视口） */
      var innerW = parseFloat($('#coInner').style.width) || 0;
      var cardMaxR = 0;
      $$('#coInner .co-node').forEach(function (n) { cardMaxR = Math.max(cardMaxR, n.offsetLeft + n.offsetWidth); });
      Math.abs(innerW - (cardMaxR + 60)) < 2
        ? ok('内容盒尺寸 = 卡片包围盒 + pad（' + innerW + 'px）')
        : fail('内容盒尺寸异常：' + innerW + ' vs ' + (cardMaxR + 60));

      /* 缩放盒 = 内容盒 × zoom → 滚动范围与实际内容严格一致（z>1 也不会被裁） */
      var wW2 = parseFloat($('#coWorld').style.width) || 0;
      var zNow = (parseInt($('#coZoom').textContent, 10) || 100) / 100;
      /* zoom 显示值是四舍五入到 1% 的，所以容差要按 0.5% 的量级给 */
      var zTol = innerW * 0.006 + 2;
      Math.abs(wW2 - innerW * zNow) <= zTol
        ? ok('缩放盒 = 内容盒 × zoom（' + wW2 + 'px @ ' + Math.round(zNow * 100) + '%）')
        : fail('缩放盒与内容盒不一致：' + wW2 + ' vs ' + innerW + '×' + zNow + '（容差 ' + Math.round(zTol) + '）');

      /* 居中：图比视口小时应左右居中，而不是挤在左上角 */
      var scW = $('#coScroll').clientWidth;
      if (wW2 < scW - 4) {
        var offL = $('#coWorld').offsetLeft;
        Math.abs(offL - (scW - wW2) / 2) < 4
          ? ok('关系图在视口内居中（左边距 ' + offL + 'px）')
          : fail('关系图未居中：左边距 ' + offL + ' ≠ ' + Math.round((scW - wW2) / 2));
      } else { info('关系图已占满视口宽度，跳过居中检查'); }

      /* 卡片不能被拖到内容盒左上角之外（负坐标在滚动容器里不可达） */
      var cEdge = $$('#coWorld .co-node')[0];
      if (cEdge) {
        var re = cEdge.getBoundingClientRect();
        cEdge.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: re.left + 40, clientY: re.top + 20 }));
        document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: re.left - 3000, clientY: re.top - 3000 }));
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: re.left - 3000, clientY: re.top - 3000 }));
        (cEdge.offsetLeft >= 59 && cEdge.offsetTop >= 59)
          ? ok('拖向左上角时钳制在内容盒内（left=' + cEdge.offsetLeft + ', top=' + cEdge.offsetTop + '）')
          : fail('卡片被拖出内容盒：left=' + cEdge.offsetLeft + ', top=' + cEdge.offsetTop);
        click($('#coArrange'));
      }

      /* ★ 拖拽结束后浏览器会补一个 click（mousedown/mouseup 同一元素）——
         必须被吃掉，否则「调整卡片位置」会被当成「点击卡片」，顺手跳页并关掉关系图。 */
      var cDrag = $$('#coWorld .co-node')[0];
      if (cDrag) {
        var pageBefore = renderedPageId();
        var rd = cDrag.getBoundingClientRect();
        cDrag.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: rd.left + 40, clientY: rd.top + 20 }));
        document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: rd.left + 140, clientY: rd.top + 120 }));
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: rd.left + 140, clientY: rd.top + 120 }));
        cDrag.dispatchEvent(new MouseEvent('click', { bubbles: true }));   /* 浏览器补发的那个 click */
        ($('#canvasOverlay').classList.contains('on') && renderedPageId() === pageBefore)
          ? ok('★ 拖拽后补发的 click 被吃掉：未误跳页、关系图仍打开')
          : fail('拖拽后误跳页：overlay=' + $('#canvasOverlay').classList.contains('on')
                 + ' page=' + renderedPageId() + '（原 ' + pageBefore + '）');
        click($('#coArrange'));
      }

      /* 点击卡片进入该页（真实点击必然先有 mousedown，这里照实模拟） */
      var targetPage = pages.filter(function (p) { return p.id !== renderedPageId(); })[0];
      if (targetPage) {
        var cardT = $$('#coWorld .co-node').filter(function (n) { return n.getAttribute('data-page-id') === targetPage.id; })[0];
        if (cardT) {
          var rt2 = cardT.getBoundingClientRect();
          cardT.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: rt2.left + 40, clientY: rt2.top + 20 }));
          cardT.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          (renderedPageId() === targetPage.id && !$('#canvasOverlay').classList.contains('on'))
            ? ok('点击卡片进入「' + targetPage.name + '」并关闭关系图')
            : fail('点击卡片未切页：' + renderedPageId());
          navTo((data.meta || {}).currentPageId || pages[0].id);
        }
      }
      if ($('#canvasOverlay').classList.contains('on')) click($('#coClose'));
      !$('#canvasOverlay').classList.contains('on') ? ok('关系图可返回主界面') : fail('关系图未关闭');

      /* 16 审核开关 */
      click($('#btnReview'));
      $('#btnShaping').style.display === 'none' ? ok('审核模式下过程产物入口已隐藏') : fail('审核模式未隐藏过程产物');
      click($('#btnReview'));
      $('#btnShaping').style.display !== 'none' ? ok('退出审核模式后入口恢复') : fail('退出审核模式未恢复');

      /* 17 过程产物抽屉 */
      click($('#btnShaping'));
      var sdN = $$('#sdBody .sd-item').length;
      sdN >= 5 ? ok('过程产物抽屉渲染 ' + sdN + ' 个板块') : fail('过程产物抽屉内容不足：' + sdN);
      click($('.side-drawer [data-close]'));

      /* 18 标注列表 */
      click($('#btnAnnoList'));
      ok('标注列表抽屉可打开');
      click($('.side-drawer [data-close]'));

      /* 19 标注修改指令（先切到「有标注」的页面，否则指令里不会有标注清单） */
      var annoPage = pages.filter(function (p) { return (p.annotations || []).length; })[0];
      if (!annoPage) {
        info('数据集无任何标注，跳过标注修改指令断言');
      } else {
      if (annoPage.id !== renderedPageId()) navTo(annoPage.id);
      click($('#btnPrompt'));
      var ta = $('#sdBody textarea');
      if (ta && ta.value) {
        var v = ta.value;
        var s1 = /## 上下文/.test(v), s2 = /## 标注清单/.test(v), s3 = /## 输出要求/.test(v);
        (s1 && s2 && s3) ? ok('标注指令含「上下文 / 标注清单 / 输出要求」三节（' + v.length + ' 字符）')
                         : fail('标注指令缺小节 ctx=' + s1 + ' list=' + s2 + ' out=' + s3);
        (/锚定节点/.test(v) && /当前属性摘要/.test(v))
          ? ok('标注指令带上了锚定节点与当前属性上下文') : fail('标注指令缺少锚定节点上下文');
        /`an-/.test(v) ? ok('标注指令含标注 id 与状态') : fail('标注指令缺少标注 id');
        /resolved/.test(v) ? ok('标注指令含回写要求（status → resolved）') : fail('标注指令缺少回写要求');
        /validate_prd_json/.test(v) ? ok('标注指令要求改完跑校验器') : fail('标注指令未要求校验');
        var segs = $$('#sdBody .ant-radio-group .ant-check');
        if (segs[1]) {
          click(segs[1]);
          var v2 = ($('#sdBody textarea') || {}).value || '';
          (v2 !== v && /全部页面/.test(v2)) ? ok('切换「全部页面」后指令重新生成') : fail('切换范围后指令未更新');
          var nonOpen = 0;
          pages.forEach(function (pg) {
            (pg.annotations || []).forEach(function (a) { if (a.status !== 'open') nonOpen++; });
          });
          var flt = $$('#sdBody .ant-btn.sm')[0];
          if (flt) {
            click(flt);
            var v3 = ($('#sdBody textarea') || {}).value || '';
            if (nonOpen > 0) {
              v3 !== v2 ? ok('切换「含已处理」后指令重新生成（数据集含 ' + nonOpen + ' 条已处理标注）')
                        : fail('筛选切换后指令未更新');
            } else {
              v3 === v2 ? ok('数据集无已处理标注时「含已处理」输出一致（符合预期）')
                        : fail('无已处理标注但输出发生变化');
            }
          } else fail('未找到筛选控件');
        } else fail('未找到范围切换控件');
      } else fail('标注指令抽屉未生成内容');
      }
      click($('.side-drawer [data-close]'));

      /* 20 导出按钮 */
      ($('#btnPng') && $('#btnMd')) ? ok('截图导出 / Markdown 导出按钮齐备') : fail('导出按钮缺失');

      /* 21 缩放：按钮生效且画布几何尺寸随之变化 */
      var wrapEl = $('#protoWrap'), scrollEl = $('#protoScroll');
      var z0 = txt($('#zVal')), w0 = wrapEl.getBoundingClientRect().width;
      click($('#zIn'));
      var z1 = txt($('#zVal')), w1 = wrapEl.getBoundingClientRect().width;
      (z1 !== z0 && w1 > w0 * 1.05)
        ? ok('放大生效：' + z0 + ' → ' + z1 + '，画布宽度 ' + Math.round(w0) + ' → ' + Math.round(w1) + 'px')
        : fail('放大未生效：' + z0 + '→' + z1 + '，宽度 ' + Math.round(w0) + '→' + Math.round(w1));
      click($('#zOut'));
      txt($('#zVal')) === z0 ? ok('缩小回到 ' + z0) : fail('缩小异常：' + txt($('#zVal')));

      /* 22 适应宽度：画布铺满舞台可视宽，且不产生横向滚动 */
      click($('#zIn')); click($('#zIn'));
      var zBig = txt($('#zVal'));
      click($('#zFit'));
      var stageEl = $('#protoStage');
      var wFit = wrapEl.getBoundingClientRect().width;
      var scW = stageEl.clientWidth - 28; /* 舞台内容宽（扣掉左右各 14px 内边距） */
      var noHScroll = scrollEl.scrollWidth <= scrollEl.clientWidth + 1;
      (Math.abs(wFit - scW) <= 3 && noHScroll)
        ? ok('适应宽度：' + zBig + ' → ' + txt($('#zVal')) + '，画布宽 ' + Math.round(wFit)
             + 'px = 舞台可视宽 ' + scW + 'px，无横向滚动')
        : fail('适应宽度异常：画布宽 ' + Math.round(wFit) + 'px，舞台可视宽 ' + scW
             + 'px，横向滚动=' + (noHScroll ? '无' : '有'));

      /* 23 缩放后标注不漂移：归一化坐标与「视觉位置」双重校验 */
      function bubbleStylePos() {
        return $$('#annoLayer .bubble').map(function (b) { return b.style.left + '|' + b.style.top; });
      }
      function bubbleVisualPos() {
        var cv = $('#protoCanvas'), cr = cv.getBoundingClientRect();
        return $$('#annoLayer .bubble').map(function (b) {
          var r = b.getBoundingClientRect();
          return (((r.left + r.width / 2 - cr.left) / cr.width) * 100).toFixed(2) + '|' +
                 (((r.top + r.height / 2 - cr.top) / cr.height) * 100).toFixed(2);
        });
      }
      click($('#zIn')); click($('#zIn'));
      var zNow = txt($('#zVal'));
      var styleBefore = bubbleStylePos(), visBefore = bubbleVisualPos();
      click($('#zOut'));
      var styleAfter = bubbleStylePos(), visAfter = bubbleVisualPos();
      var styleSame = styleBefore.length === styleAfter.length &&
                      styleBefore.every(function (v, i) {
                        var a = v.split('|'), b = styleAfter[i].split('|');
                        return Math.abs(parseFloat(a[0]) - parseFloat(b[0])) < 0.02 &&
                               Math.abs(parseFloat(a[1]) - parseFloat(b[1])) < 0.02;
                      });
      var visSame = visBefore.length === visAfter.length &&
                    visBefore.every(function (v, i) {
                      var a = v.split('|'), b = visAfter[i].split('|');
                      return Math.abs(+a[0] - +b[0]) < 0.6 && Math.abs(+a[1] - +b[1]) < 0.6;
                    });
      (styleSame && visSame)
        ? ok('缩放 ' + zNow + ' → ' + txt($('#zVal')) + ' 后 ' + styleBefore.length
             + ' 个气泡的归一化坐标与视觉位置均不变（标注不漂移）')
        : fail('缩放后标注漂移：坐标 ' + styleBefore.join(',') + ' → ' + styleAfter.join(',')
             + '；视觉 ' + visBefore.join(',') + ' → ' + visAfter.join(','));

      /* 23b 已存在的锚定标注：气泡视觉中心须与目标元素视觉中心重合（精确锚点校验在 23c） */
      var anchoredBubs = $$('#annoLayer .bubble').filter(function (b) {
        return !!b.getAttribute('data-anno-id'); });
      anchoredBubs.length
        ? info('当前页已有 ' + anchoredBubs.length + ' 个标注气泡（锚点精确校验见 23c）')
        : info('当前页尚无标注气泡，锚点精确校验见 23c');

      /* 23c 锚定标注跨 6 档缩放贴合校验（原「缩放后气泡漂移」bug 的回归测试）
         引擎在 IIFE 内不暴露内部状态，故全程走 UI：进标注模式 → 点最小可锚定节点 → 退出
         → 从弹层读回锚点 nodeId → 多档缩放比对气泡视觉中心与目标元素视觉中心的偏差 */
      click($('#zVal')); /* 复位 100% */
      var beforeIds = $$('#annoLayer .bubble').map(function (b) { return b.getAttribute('data-anno-id'); });
      click($('#btnAnnotate'));
      var cand = $$('#protoCanvas [data-node-id]').filter(function (nd) {
        var r = nd.getBoundingClientRect(); return r.width > 30 && r.height > 14; });
      cand.sort(function (a, b) {
        var ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
        return ra.width * ra.height - rb.width * rb.height; });
      var tgt0 = cand[0];
      if (tgt0) {
        var tr0 = tgt0.getBoundingClientRect();
        tgt0.dispatchEvent(new MouseEvent('click', { bubbles: true,
          clientX: tr0.left + tr0.width / 2, clientY: tr0.top + tr0.height / 2 }));
      }
      var apTxt = ($$('.anno-pop .ap-anchor')[0] || {}).textContent || '';
      var mNid = apTxt.match(/锚点:\s*([A-Za-z0-9_\-]+)/);
      var nid0 = mNid ? mNid[1] : null;
      var newB = $$('#annoLayer .bubble').filter(function (b) {
        return beforeIds.indexOf(b.getAttribute('data-anno-id')) < 0; })[0];
      var nidBub = newB ? newB.getAttribute('data-anno-id') : null;
      click($('#btnAnnotate')); /* 退出标注模式 */

      if (nid0 && nidBub) {
        function anchorDev() {
          var cv3 = $('#protoCanvas'), c3 = cv3.getBoundingClientRect();
          var e3 = cv3.querySelector('[data-node-id="' + nid0 + '"]');
          var bEl = $$('#annoLayer .bubble').filter(function (b) {
            return b.getAttribute('data-anno-id') === nidBub; })[0];
          if (!e3 || !bEl) return null;
          var er3 = e3.getBoundingClientRect(), b3 = bEl.getBoundingClientRect();
          return Math.max(
            Math.abs((er3.left + er3.width / 2 - c3.left) / c3.width - (b3.left + b3.width / 2 - c3.left) / c3.width) * 100,
            Math.abs((er3.top + er3.height / 2 - c3.top) / c3.height - (b3.top + b3.height / 2 - c3.top) / c3.height) * 100);
        }
        var devs = [];
        function snap() { var d = anchorDev(); devs.push(txt($('#zVal')) + '→' + (d == null ? 'N/A' : d.toFixed(3) + '%')); }
        snap();
        click($('#zIn')); snap();
        click($('#zIn')); snap();
        click($('#zIn')); snap();
        click($('#zOut')); snap();
        click($('#zOut')); snap();
        var nums = devs.map(function (s) { return Number(s.split('→')[1].replace('%', '')); })
                       .filter(function (v) { return !isNaN(v); });
        var worst = nums.length ? Math.max.apply(null, nums) : 999;
        (nums.length === 6 && worst < 0.8)
          ? ok('锚定标注「' + nid0 + '」跨 6 档缩放（100%~152%）气泡视觉中心始终贴合目标元素，最大偏差 '
               + worst.toFixed(3) + '%')
          : fail('锚定标注随缩放漂移：' + devs.join(' / '));
        click($('#zVal')); /* 复位 100% */
        /* 清理探针标注 */
        var bubNow = $$('#annoLayer .bubble').filter(function (b) {
          return b.getAttribute('data-anno-id') === nidBub; })[0];
        if (bubNow) {
          click(bubNow);
          var bDelBtn = $$('.anno-pop .ant-btn').filter(function (b) { return txt(b) === '删除'; })[0];
          if (bDelBtn) click(bDelBtn);
        }
      } else {
        info('点击未命中可锚定节点（' + (apTxt || '无弹层') + '），跳过锚定缩放校验');
      }

      /* 24 缩放状态下点击画布，标注落位仍为归一化坐标 */
      click($('#zIn'));
      click($('#btnAnnotate'));
      var wr2 = wrapEl.getBoundingClientRect();
      var n0 = $$('#annoLayer .bubble').length;
      $('#protoCanvas').dispatchEvent(new MouseEvent('click', {
        bubbles: true, clientX: wr2.left + wr2.width / 2, clientY: wr2.top + wr2.height / 2 }));
      var bubs = $$('#annoLayer .bubble');
      var nb = bubs[bubs.length - 1];
      var lx = nb ? parseFloat(nb.style.left) : NaN, ly = nb ? parseFloat(nb.style.top) : NaN;
      (bubs.length === n0 + 1 && Math.abs(lx - 50) < 1.5 && Math.abs(ly - 50) < 1.5)
        ? ok('缩放 ' + txt($('#zVal')) + ' 下点击画布中心，新标注落位 ' + lx.toFixed(1) + '% / ' + ly.toFixed(1) + '%')
        : fail('缩放后标注落位错误：新增 ' + (bubs.length - n0) + ' 个，left=' + lx + ' top=' + ly);
      ($('.anno-pop') && $('.anno-pop').getBoundingClientRect().width > 0)
        ? ok('新建标注后弹层保持打开（可直接输入意见）') : fail('新建标注后弹层被立即关闭');
      click($('#btnAnnotate'));

      /* 25 平移模式 + 与标注模式互斥 */
      click($('#zPan'));
      var panOn = scrollEl.classList.contains('pan') && $('#zPan').classList.contains('on');
      panOn ? ok('平移模式开启：光标变抓手，可拖拽移动画布') : fail('平移模式未生效');
      click($('#btnAnnotate'));
      var mutual = !scrollEl.classList.contains('pan') && $('#btnAnnotate').classList.contains('on');
      mutual ? ok('平移模式与标注模式互斥（开标注自动关平移）') : fail('两种模式未互斥');
      click($('#btnAnnotate'));
      click($('#zPan')); click($('#zPan'));
      !scrollEl.classList.contains('pan') ? ok('可正常退出平移模式') : fail('无法退出平移模式');

      /* 26 键盘快捷键重置 */
      document.dispatchEvent(new KeyboardEvent('keydown', { key: '0', ctrlKey: true, bubbles: true }));
      txt($('#zVal')) === '100%' ? ok('⌘/Ctrl + 0 重置为 100%') : fail('快捷键重置失败：' + txt($('#zVal')));

      /* ================= 跳转能力（本轮新增） ================= */
      function findNode(page, nid) {
        var stack = [page.componentTree], guard = 0;
        while (stack.length && guard++ < 5000) {
          var n = stack.shift();
          if (!n || typeof n !== 'object') continue;
          if (n.id === nid) return n;
          (n.children || []).forEach(function (c) { stack.push(c); });
          for (var k in (n.slots || {})) (n.slots[k] || []).forEach(function (c) { stack.push(c); });
        }
        return null;
      }
      function curPageId() {
        var m = /^#\/?([A-Za-z0-9_\-]+)/.exec(location.hash || '');
        return m ? m[1] : null;
      }
      function navTo(id) {
        expandAll();
        var row = $('#navTree [data-page-id="' + id + '"]');
        if (row) { click(row); return true; }
        var s = $('.nav-scroll'); if (s) s.scrollTop = 0;
        row = $('#navTree [data-page-id="' + id + '"]');
        if (row) { click(row); return true; }
        return false;
      }
      function renderedPageId() {
        var sel = $('#navTree .nav-row.sel');
        return sel ? sel.getAttribute('data-page-id') : null;
      }
      function resolveRowTpl(tpl, row) {
        return String(tpl).replace(/\{\{\s*row\.([A-Za-z0-9_]+)\s*\}\}/g, function (m, f) {
          return row && row[f] != null ? String(row[f]) : m;
        });
      }

      /* 28 hash 路由：URL 即当前页真源 */
      var initId = (/^#\/?([A-Za-z0-9_\-]+)/.exec(bootHash || '') || [])[1] || null;
      var metaId = (data.meta || {}).currentPageId;
      (initId && initId === metaId)
        ? ok('URL hash 路由建立基线：location.hash = #/' + initId + '（与 meta.currentPageId 一致）')
        : fail('hash 基线错误：hash=' + (location.hash || '(空)') + '，meta=' + metaId);

      /* 29 行级跳转：一条通配 interaction 服务所有行 + {{row.x}} 带参 */
      var rowIx = null;
      pages.forEach(function (p) {
        if (rowIx) return;
        (p.interactions || []).forEach(function (ix) {
          if (rowIx) return;
          var t = (ix.on || {}).target || '';
          var m = /^(.*)__row_\*$/.exec(t);
          if (!m) return;
          var nav = (ix.actions || []).filter(function (a) { return a.type === 'navigate'; })[0];
          if (!nav) return;
          var tbl = findNode(p, m[1]);
          var rows = (tbl && tbl.props && tbl.props.data) || [];
          if (rows.length < 2) return;
          rowIx = { page: p, ix: ix, tableId: m[1], nav: nav, rowIdx: 1, row: rows[1] };
        });
      });
      if (!rowIx) {
        info('本用例无「行级跳转」配置，跳过行级跳转断言');
      } else {
        navTo(rowIx.page.id);
        var rowEl = $('#protoCanvas [data-node-id="' + rowIx.tableId + '__row_' + rowIx.rowIdx + '"]');
        rowEl ? ok('Table `' + rowIx.tableId + '` 的第 ' + rowIx.rowIdx + ' 行拿到合成节点 id（rowClick 生效）')
              : fail('未找到行节点 ' + rowIx.tableId + '__row_' + rowIx.rowIdx);
        if (rowEl) {
          click(rowEl);
          var after = curPageId();
          after === rowIx.nav.pageId
            ? ok('点行跳转到 `' + rowIx.nav.pageId + '`，hash 同步为 #/' + after)
            : fail('点行未跳转：当前 ' + after + '，期望 ' + rowIx.nav.pageId);
          /* 带参校验：params 里的 {{row.x}} 应被替换成该行的真实值，并在目标页可见 */
          var expVals = [], bodyTxt = txt($('#protoCanvas'));
          for (var pk in (rowIx.nav.params || {})) {
            var pv = rowIx.nav.params[pk];
            if (typeof pv !== 'string' || pv.indexOf('{{row.') < 0) continue;
            var ev = resolveRowTpl(pv, rowIx.row);
            expVals.push(pk + '=' + ev);
            bodyTxt.indexOf(ev) >= 0 ? ok('带参跳转：' + pk + ' 由 {{row.*}} 求值为「' + ev + '」并显示在目标页')
                                     : fail('带参跳转未生效：目标页看不到 ' + pk + '=' + ev);
          }
          if (!expVals.length) info('该行级跳转的 params 未使用 {{row.*}}，跳过带参断言');

          /* 30 返回：Header 返回箭头（合成 id <headerId>__back） */
          var backEl = $('#protoCanvas [data-node-id$="__back"]');
          if (backEl) {
            click(backEl);
            curPageId() === rowIx.page.id
              ? ok('Header 返回箭头（__back）回到 `' + rowIx.page.id + '`，未跳出容器')
              : fail('返回失败：当前 ' + curPageId() + '，期望 ' + rowIx.page.id);
          } else {
            info('目标页无 Header 返回箭头，跳过返回断言');
          }
        }
      }

      /* 31 按钮就近命中：点行内操作按钮不应误触发整行跳转 */
      var actIx = null;
      pages.forEach(function (p) {
        if (actIx) return;
        (p.interactions || []).forEach(function (ix) {
          if (actIx) return;
          var t = (ix.on || {}).target || '';
          var m = /^(.*)__act_\*_([A-Za-z0-9_\-]+)$/.exec(t);
          if (!m) return;
          var hasNav = (ix.actions || []).some(function (a) { return a.type === 'navigate'; });
          var tbl = findNode(p, m[1]);
          var rows = (tbl && tbl.props && tbl.props.data) || [];
          if (!rows.length) return;
          actIx = { page: p, ix: ix, tableId: m[1], key: m[2], nav: hasNav, row: rows[0] };
        });
      });
      if (!actIx) {
        info('本用例无「通配行内按钮」配置，跳过就近命中断言');
      } else {
        navTo(actIx.page.id);
        var btnEl = $('#protoCanvas [data-node-id="' + actIx.tableId + '__act_0_' + actIx.key + '"]');
        btnEl ? ok('行内操作按钮拿到合成节点 id（' + actIx.tableId + '__act_*_' + actIx.key + '）')
              : fail('未找到行内按钮 ' + actIx.tableId + '__act_0_' + actIx.key);
        if (btnEl) {
          var t0 = $$('#toastWrap .toast').length, before = curPageId();
          click(btnEl);
          var t1 = $$('#toastWrap .toast').length;
          if (actIx.nav) {
            curPageId() !== before ? ok('点行内按钮跳转生效（' + before + ' → ' + curPageId() + '）')
                                   : fail('点行内按钮未跳转');
          } else {
            (curPageId() === before && t1 > t0)
              ? ok('就近命中：点行内按钮只执行按钮动作，未误触发整行跳转')
              : fail('就近命中失败：页面 ' + before + ' → ' + curPageId() + '，提示 ' + t0 + ' → ' + t1);
            /* 按钮文案里的 {{row.x}} 也应在源页按行求值 */
            var msg = (actIx.ix.actions || []).filter(function (a) { return a.type === 'message'; })[0];
            if (msg && String(msg.text).indexOf('{{row.') >= 0) {
              var ev2 = resolveRowTpl(msg.text, actIx.row);
              var lastToast = $$('#toastWrap .toast').slice(-1)[0];
              (lastToast && txt(lastToast).indexOf(ev2.replace(/^已[^：]*：/, '')) >= 0)
                ? ok('按钮提示里的 {{row.*}} 按该行求值：' + ev2)
                : fail('按钮提示未按行求值：期望含「' + ev2 + '」，实际「' + (lastToast ? txt(lastToast) : '') + '」');
            }
          }
        }
      }

      /* 32 弹窗底部按钮合成 id：<Modal 节点 id>__ok / __cancel */
      var modalCands = [];
      pages.forEach(function (p) {
        (p.interactions || []).forEach(function (ix) {
          var a = (ix.actions || []).filter(function (x) { return x.type === 'showModal'; })[0];
          if (!a) return;
          var mid = a.modalId;
          /* 底部按钮的合成 id 是 `<Modal 节点 id>__ok/__cancel`；
             showModal 引用的是 props.modalId，两者不一定同名，必须先解析出节点 id。 */
          var node = null;
          (function walk(x) {
            if (node || !x || typeof x !== 'object') return;
            if (x.type === 'Modal' && (x.props || {}).modalId === mid) { node = x; return; }
            (x.children || []).forEach(walk);
            for (var k in (x.slots || {})) (x.slots[k] || []).forEach(walk);
          })(p.componentTree);
          modalCands.push({ page: p, ix: ix, modalId: mid, nodeId: node ? node.id : mid });
        });
      });
      /* 挑一个「触发元素真的在当前 DOM 里」的候选：有的 showModal 挂在抽屉内的按钮上，
         抽屉默认关闭时按钮不在 DOM 中，直接跳过它继续找。 */
      var modalIx = null;
      for (var mi = 0; mi < modalCands.length && !modalIx; mi++) {
        var cand = modalCands[mi];
        navTo(cand.page.id);
        var probe = $('#protoCanvas [data-node-id="' + cand.ix.on.target.replace('*', '0') + '"]');
        if (probe) modalIx = cand;
      }
      if (!modalIx && modalCands.length) info('本用例 ' + modalCands.length + ' 个 showModal 的触发元素均不在默认视图中，跳过弹窗断言');
      if (!modalIx) {
        info('本用例无 showModal 交互，跳过弹窗按钮断言');
      } else if (modalIx) {
        var trig = $('#protoCanvas [data-node-id="' + modalIx.ix.on.target.replace('*', '0') + '"]');
        if (trig) {
          click(trig);
          var mask = $('.ant-modal-mask');
          mask ? ok('showModal 打开弹窗（modalId=' + modalIx.modalId + '）') : fail('弹窗未打开');
          var okBtn = $('#protoCanvas [data-node-id="' + modalIx.nodeId + '__ok"]');
          var cancelBtn = $('#protoCanvas [data-node-id="' + modalIx.nodeId + '__cancel"]');
          okBtn ? ok('弹窗底部按钮拿到合成节点 id：' + modalIx.nodeId + '__ok'
                     + (cancelBtn ? ' / __cancel' : '') + '（modalId=' + modalIx.modalId + '）')
                : fail('弹窗底部按钮未生成合成 id（Modal 节点 ' + modalIx.nodeId + '）');
          if (cancelBtn) {
            click(cancelBtn);
            $('.ant-modal-mask') ? fail('点 __cancel 后弹窗未关闭') : ok('点弹窗 __cancel 关闭弹窗');
          } else if (okBtn) { click(okBtn); }
        } else {
          fail('找不到弹窗触发元素 ' + modalIx.ix.on.target.replace('*', '0')
               + '（期望页面 ' + modalIx.page.id + '，实际渲染 ' + renderedPageId() + '）');
        }
      }

      /* 33 hashchange 驱动切页（浏览器前进/后退同路径） */
      var other = pages.filter(function (p) { return p.id !== renderedPageId(); })[0];
      if (other) {
        location.hash = '#/' + other.id;
        window.dispatchEvent(new HashChangeEvent('hashchange'));
        (renderedPageId() === other.id && curPageId() === other.id)
          ? ok('hash 变化驱动切页：#' + other.id + ' → 原型与导航树都切到 `' + other.id + '`')
          : fail('hashchange 未切页：渲染页 ' + renderedPageId() + '，hash ' + curPageId());
        var beforeBad = renderedPageId();
        location.hash = '#/page-not-exist';
        window.dispatchEvent(new HashChangeEvent('hashchange'));
        (renderedPageId() === beforeBad && curPageId() === beforeBad)
          ? ok('非法 hash 不切页且被拉回：停留在 `' + beforeBad + '`，URL 复原为 #/' + beforeBad)
          : fail('非法 hash 处理异常：渲染页 ' + renderedPageId() + '，hash ' + curPageId());
      }
      navTo((data.meta || {}).currentPageId || pages[0].id);

      /* 27 拖拽平移：先放大到画布溢出，再中键拖拽，验证滚动位置真的改变 + 抑制误触发 */
      click($('#zIn')); click($('#zIn')); click($('#zIn')); /* → 152% */
      var hasOverflow = scrollEl.scrollWidth > scrollEl.clientWidth + 1 ||
                        scrollEl.scrollHeight > scrollEl.clientHeight + 1;
      var sl0 = scrollEl.scrollLeft;
      var sr = scrollEl.getBoundingClientRect();
      scrollEl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 1, clientX: sr.left + 120, clientY: sr.top + 120 }));
      document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: sr.left + 40, clientY: sr.top + 40 }));
      document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: sr.left + 40, clientY: sr.top + 40 }));
      var sl1 = scrollEl.scrollLeft;
      (hasOverflow && sl1 > sl0)
        ? ok('中键拖拽平移画布：' + txt($('#zVal')) + ' 下向左上拖 80px，scrollLeft ' + sl0 + ' → ' + sl1)
        : fail('中键拖拽未平移画布：溢出=' + hasOverflow + '，scrollLeft ' + sl0 + ' → ' + sl1);
      var t0 = $$('#toastWrap .toast').length;
      var tgtEl = $('#protoCanvas [data-node-id]');
      if (tgtEl) {
        tgtEl.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        var t1 = $$('#toastWrap .toast').length;
        t1 === t0 ? ok('拖拽平移后紧随的 click 被抑制，未误触发交互')
                  : fail('拖拽后仍误触发交互（新增 ' + (t1 - t0) + ' 条提示）');
      } else info('当前页无节点，跳过误触发检查');
      click($('#zVal')); /* 复位 100% */

      /* ============ 本轮新增：右栏 PRD 折叠 + splitter 可逆拖拽 ============ */
      var wsEl = document.querySelector('.workspace');
      var prdEl = $('#panePrd');
      var spEl = $('#splitter');
      /* F6 起，作业型列表页**开页默认折叠 PRD**（保留导航）。本段测的是
         「面板能显示 + 可拖到下限 + 能拖回来」，前提是它得先展开。
         断言本身一条没放宽（仍是「有宽度 / 有下限 / 能恢复」），补的只是前提；
         条数不变，所以 757 基线不受影响。

         前置用 `=== 480` 而不是 `> 0`：容器是先清空再 append 的，中间态也会 >0，
         「根本没展开」和「展开了」在 >0 下长得一模一样。480 是 run.sh 的视口
         （1680×1000）下展开后的实测宽 —— 默认宽就 480、没被钳制。
         前置不成立就不跑拖拽：带着错的初态跑出来的「拖不动 / 拖不回」不是产物的问题。 */
      var PRD_EXPECT_W = 480;
      var prdWasCollapsed = prdEl.classList.contains('collapsed');
      if (prdWasCollapsed) {
        info('F6：开页默认折叠 PRD（列表页），先展开再测面板宽度');
        click($('#prdToggle'));
      }
      var w0 = prdEl.offsetWidth;
      var prdPreOk = (w0 === PRD_EXPECT_W);
      prdPreOk
        ? ok('PRD 面板可见，宽度 ' + w0 + 'px（'
             + (prdWasCollapsed ? 'F6 自动折叠 → 手动展开' : '开页即展开') + '）')
        : fail('前置不成立：展开后宽 = ' + w0 + 'px（期望 ' + PRD_EXPECT_W + '）—— 不带着这个宽度继续跑拖拽');

      function dragSplitter(clientX) {
        var sr = spEl.getBoundingClientRect();
        spEl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: sr.left + 3, clientY: sr.top + 40 }));
        document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: clientX, clientY: sr.top + 40 }));
        document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: clientX, clientY: sr.top + 40 }));
      }
      var wsr = wsEl.getBoundingClientRect();

      if (prdPreOk) {
        dragSplitter(wsr.right - 4);            /* 拖到最右 → PRD 收到最小 */
        var wMin = prdEl.offsetWidth;
        (wMin >= 280 && wMin <= w0 + 1)
          ? ok('splitter 拖到最小：PRD 收缩到 ' + wMin + 'px（有下限，不塌成 0）')
          : fail('PRD 最小宽度异常：' + wMin);

        dragSplitter(wsr.right - 760);          /* ★ 关键回归：还能不能拖回来 */
        var wBack = prdEl.offsetWidth;
        wBack > wMin + 100
          ? ok('★ 拖到最小后可原路拖回：' + wMin + ' → ' + wBack + 'px（旧版百分比 flex 在此卡死）')
          : fail('拖到最小后无法恢复：' + wMin + ' → ' + wBack);
      } else {
        info('前置不成立：跳过 splitter 拖拽三项（不带着错误初态造结论）');
      }

      click($('#prdCollapse'));
      var collapsed = prdEl.classList.contains('collapsed');
      var restoreDisp = getComputedStyle($('#prdRestore')).display;
      (collapsed && restoreDisp !== 'none')
        ? ok('收起 PRD：右栏折叠，右侧出现「PRD」竖向恢复把手')
        : fail('收起异常 collapsed=' + collapsed + ' restoreDisplay=' + restoreDisp);
      prdEl.offsetWidth === 0 ? ok('收起后 PRD 占位为 0，中栏吃满剩余宽度') : fail('收起后仍占位 ' + prdEl.offsetWidth + 'px');

      click($('#prdRestore'));
      (!prdEl.classList.contains('collapsed') && prdEl.offsetWidth > 200)
        ? ok('点恢复把手展开 PRD，宽度还原为 ' + prdEl.offsetWidth + 'px')
        : fail('展开异常 width=' + prdEl.offsetWidth);

      click($('#prdToggle'));
      prdEl.classList.contains('collapsed') ? ok('原型栏「PRD ‹」按钮可收起右栏') : fail('顶栏按钮收起失败');
      click($('#prdToggle'));
      !prdEl.classList.contains('collapsed') ? ok('再点一次可展开（两处入口状态同步）') : fail('顶栏按钮展开失败');

      dragSplitter(wsr.right - 320);
      var wNarrow = prdEl.offsetWidth;
      spEl.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
      var wReset = prdEl.offsetWidth;
      wReset !== wNarrow ? ok('双击 splitter 复位到默认宽度 ' + wReset + 'px') : info('双击复位后宽度未变：' + wReset);

      /* ============ 本轮新增：PRD 内嵌流程图 ============ */
      var flowSecs = [];
      pages.forEach(function (p) {
        ((p.prd || {}).sections || []).forEach(function (s) {
          if (s.type === 'flow') flowSecs.push({ page: p.id, sec: s });
        });
      });
      if (flowSecs.length) {
        var f0 = flowSecs[0];
        navTo(f0.page);
        var diaN = $$('#prdBody .flow-diagram').length;
        diaN ? ok('PRD 渲染出内嵌流程图（本页 ' + diaN + ' 个，数据集共 ' + flowSecs.length + ' 个）')
             : fail('PRD 未渲染流程图');
        var fsvg = $('#prdBody .flow-diagram svg');
        if (fsvg) {
          var fn = fsvg.querySelectorAll('.fd-node').length;
          var fe = fsvg.querySelectorAll('.fd-edge').length;
          (fn === (f0.sec.nodes || []).length && fe === (f0.sec.edges || []).length)
            ? ok('流程图节点/边数量正确：' + fn + ' 节点 / ' + fe + ' 边')
            : fail('流程图数量不符：' + fn + '/' + fe + ' ≠ ' + (f0.sec.nodes || []).length + '/' + (f0.sec.edges || []).length);
          fsvg.querySelectorAll('.fd-node .lbl').length === fn
            ? ok('流程图 ' + fn + ' 个节点都有文字标签') : fail('流程图存在无标签节点');
          var expLbl = (f0.sec.edges || []).filter(function (e) { return e.label; }).length;
          fsvg.querySelectorAll('.fd-elabel').length === expLbl
            ? ok('流程图边标签数量正确（' + expLbl + ' 个）') : fail('流程图边标签数量不符');
          fsvg.querySelector('marker') ? ok('流程图带箭头 marker') : fail('流程图缺箭头 marker');
          var styled = fsvg.querySelectorAll('.fd-node.start').length + fsvg.querySelectorAll('.fd-node.end').length
                     + fsvg.querySelectorAll('.fd-node.decision').length;
          styled >= 2 ? ok('流程图区分起止 / 判定节点样式（' + styled + ' 个）') : info('流程图未使用起止/判定样式');
          var cap = $('#prdBody .prd-flow-cap');
          cap && cap.textContent ? ok('流程图带图注：' + cap.textContent.slice(0, 22)) : info('流程图无图注');
          fsvg.outerHTML.indexOf('NaN') < 0 ? ok('流程图 SVG 无 NaN 坐标') : fail('流程图存在 NaN 坐标');
          var fw = parseFloat(fsvg.getAttribute('width')), fh = parseFloat(fsvg.getAttribute('height'));
          (fw > 100 && fh > 30) ? ok('流程图尺寸合理：' + fw + '×' + fh) : fail('流程图尺寸异常：' + fw + '×' + fh);
        }
          /* 流程图按「原尺寸」渲染：窄 PRD 栏里横向滚动，而不是缩到看不清 */
          var diaWrap = fsvg.parentNode;
          var naturalW = parseFloat(fsvg.getAttribute('width'));
          var drawnW = fsvg.getBoundingClientRect().width;
          drawnW >= naturalW - 1
            ? ok('流程图按原尺寸渲染（' + Math.round(drawnW) + 'px，未被压缩）')
            : fail('流程图被压缩：' + Math.round(drawnW) + ' < ' + naturalW);
          getComputedStyle(diaWrap).overflowX !== 'visible'
            ? ok('流程图容器可横向滚动（overflow-x:' + getComputedStyle(diaWrap).overflowX + '）')
            : fail('流程图容器未开启横向滚动，宽图会被压扁');

          /* 「放大」浮层：整体看清流程 */
          var zb = $('#prdBody .flow-diagram .ant-btn');
          if (zb) {
            click(zb);
            var fzOn = $('#flowZoom').classList.contains('on') && $$('#fzBody svg').length === 1;
            fzOn ? ok('流程图「放大」浮层可打开并渲染 SVG') : fail('流程图放大浮层异常');
            if (fzOn) {
              click($('#fzClose'));
              !$('#flowZoom').classList.contains('on') ? ok('流程图放大浮层可关闭') : fail('放大浮层未关闭');
            }
          } else { info('流程图未提供「放大」入口'); }

          /* 流程图按「原尺寸」渲染：窄 PRD 栏里横向滚动，而不是缩到看不清 */
          var diaWrap = fsvg.parentNode;
          var naturalW = parseFloat(fsvg.getAttribute('width'));
          var drawnW = fsvg.getBoundingClientRect().width;
          drawnW >= naturalW - 1
            ? ok('流程图按原尺寸渲染（' + Math.round(drawnW) + 'px，未被压缩）')
            : fail('流程图被压缩：' + Math.round(drawnW) + ' < ' + naturalW);
          getComputedStyle(diaWrap).overflowX !== 'visible'
            ? ok('流程图容器可横向滚动（overflow-x:' + getComputedStyle(diaWrap).overflowX + '）')
            : fail('流程图容器未开启横向滚动，宽图会被压扁');

          /* 「放大」浮层：整体看清流程 */
          var zb = $('#prdBody .flow-diagram .ant-btn');
          if (zb) {
            click(zb);
            var fzOn = $('#flowZoom').classList.contains('on') && $$('#fzBody svg').length === 1;
            fzOn ? ok('流程图「放大」浮层可打开并渲染 SVG') : fail('流程图放大浮层异常');
            if (fzOn) {
              click($('#fzClose'));
              !$('#flowZoom').classList.contains('on') ? ok('流程图放大浮层可关闭') : fail('放大浮层未关闭');
            }
          } else { info('流程图未提供「放大」入口'); }

        var badFlow = 0;
        flowSecs.forEach(function (f) {
          navTo(f.page);
          if (!$$('#prdBody .flow-diagram svg').length) badFlow++;
        });
        badFlow === 0 ? ok(flowSecs.length + ' 个流程图全部渲染成功') : fail(badFlow + ' 个流程图未渲染');
      } else info('数据集未包含 type="flow" 的 PRD 小节');

      /* ============ 本轮新增：dataModel 数据模型小节 ============ */
      var ents = ((data.dataModel || {}).entities) || [];
      if (ents.length) {
        var dmHit = 0, dmRows = 0;
        pages.forEach(function (p) {
          navTo(p.id);
          var cards = $$('#prdBody .dm-entity');
          if (cards.length) { dmHit++; dmRows += $$('#prdBody .dm-table tbody tr').length; }
        });
        dmHit > 0 ? ok('PRD 渲染「数据模型」小节（' + dmHit + '/' + pages.length + ' 个页面命中实体，共 ' + dmRows + ' 行字段）')
                  : fail('PRD 未渲染数据模型小节');
        navTo(pages[0].id);
        var dmCard = $('#prdBody .dm-entity');
        if (dmCard) {
          var dmFlds = dmCard.querySelectorAll('.dm-table tbody tr').length;
          dmFlds > 0 ? ok('数据模型以字段表呈现（' + dmFlds + ' 行）') : fail('数据模型无字段表');
          (txt(dmCard).indexOf('pk') >= 0 || txt(dmCard).indexOf('PK') >= 0)
            ? ok('数据模型标注了主键约束') : info('该实体未标注主键');
        }
      } else info('数据集未包含 dataModel');

      /* ============ 本轮新增：开发交接包（AI 可消费） ============ */
      click($('#btnDevkit'));
      $('#sideDrawer').classList.contains('on') ? ok('「开发交接」抽屉可打开') : fail('开发交接抽屉未打开');
      var dkTa = $('#sdBody textarea');
      if (dkTa && dkTa.value) {
        var pv = dkTa.value;
        (/你是资深前端工程师/.test(pv) && /devspec\.json/.test(pv))
          ? ok('AI 交接指令含角色设定 + devspec.json 引用') : fail('交接指令缺少角色/真源引用');
        (pv.indexOf('componentTree') >= 0 && pv.indexOf('pageGraph') >= 0
          && pv.indexOf('dataModel') >= 0 && pv.indexOf('acceptance') >= 0)
          ? ok('交接指令逐条列出 componentTree / pageGraph / dataModel / acceptance 真源')
          : fail('交接指令缺少关键约定');
        /TODO\(confirm\)/.test(pv) ? ok('交接指令要求对未确认项打 TODO(confirm)') : fail('交接指令未约束未确认项');
        pv.indexOf(String(pages.length)) >= 0 ? ok('交接指令写入了页面数 ' + pages.length) : info('交接指令未写页面数');
        pv.length > 600 ? ok('交接指令长度 ' + pv.length + ' 字符') : info('交接指令偏短：' + pv.length);
      } else fail('开发交接抽屉未生成 AI 指令文本');

      var dkBtns = $$('#sdBody .ant-btn').map(function (b) { return txt(b); });
      dkBtns.some(function (t) { return /devspec\.json/.test(t); }) ? ok('抽屉提供 devspec.json 下载入口') : fail('缺少 devspec.json 下载');
      dkBtns.some(function (t) { return /AGENT\.md/.test(t); }) ? ok('抽屉提供 AGENT.md 下载入口') : fail('缺少 AGENT.md 下载');
      var dkNoteTxt = $$('#sdBody .dk-note').map(function (n) { return n.textContent; }).join(' | ');
      (/页面/.test(dkNoteTxt) && /实体/.test(dkNoteTxt))
        ? ok('抽屉含机器可读性自检统计') : fail('抽屉缺少自检统计：' + dkNoteTxt.slice(0, 60));

      var tA = $$('#toastWrap .toast').length;
      var agBtn = $$('#sdBody .ant-btn').filter(function (b) { return /AGENT\.md/.test(txt(b)); })[0];
      if (agBtn) {
        agBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        $$('#toastWrap .toast').length > tA ? ok('可生成并导出 AGENT.md（无异常）') : info('AGENT.md 导出未产生提示');
      }
      var tB = $$('#toastWrap .toast').length;
      var jsBtn = $$('#sdBody .ant-btn').filter(function (b) { return /devspec\.json/.test(txt(b)); })[0];
      if (jsBtn) {
        jsBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        $$('#toastWrap .toast').length > tB ? ok('可生成并导出 devspec.json（无异常）') : info('devspec.json 导出未产生提示');
      }
      click($('.side-drawer [data-close]'));
      !$('#sideDrawer').classList.contains('on') ? ok('开发交接抽屉可关闭') : fail('抽屉未关闭');

      /* Markdown 导出（含流程图文本降级）不抛错 */
      var tC = $$('#toastWrap .toast').length;
      click($('#btnMd'));
      $$('#toastWrap .toast').length > tC ? ok('Markdown 导出可执行（流程图已降级为文本链路）') : fail('Markdown 导出异常');

      /* 关系图在含 flow/dataModel 的数据集上仍可用 */
      click($('#btnCanvas'));
      $$('#coWorld .co-node').length === pages.length ? ok('关系图在新数据集上仍完整渲染') : fail('关系图卡片缺失');
      click($('#coClose'));

      /* ============ 本轮新增：主子表（MasterDetail）============ */
      function nodesByType(nd, type, out) {
        out = out || [];
        if (!nd || typeof nd !== 'object') return out;
        if (nd.type === type) out.push(nd);
        (nd.children || []).forEach(function (c) { nodesByType(c, type, out); });
        for (var k in (nd.slots || {})) (nd.slots[k] || []).forEach(function (c) { nodesByType(c, type, out); });
        return out;
      }
      var mdPage = null, mdNode = null;
      pages.forEach(function (p) {
        if (mdNode) return;
        var hit = nodesByType(p.componentTree, 'MasterDetail', []);
        if (hit.length) { mdPage = p; mdNode = hit[0]; }
      });

      if (!mdNode) {
        info('数据集无 MasterDetail（主子表），跳过主子表断言');
      } else {
        /* 静态：children 必须正好 2 个 Table；主表不能设 rowClick */
        var kids = mdNode.children || [];
        (kids.length === 2 && kids[0].type === 'Table' && kids[1].type === 'Table')
          ? ok('MasterDetail 结构合法：children = [主表 Table, 子表 Table]')
          : fail('MasterDetail children 不合法：' + kids.map(function (c) { return c.type; }).join(','));
        !((kids[0].props || {}).rowClick)
          ? ok('主子表主表未设 rowClick（点行 = 选中行）')
          : fail('主子表主表设了 rowClick，会与「点行选中」冲突');

        var mTbl = kids[0], dTbl = kids[1];
        var mdProps = mdNode.props || {};
        var bind = mdProps.bind || 'id', bindTo = mdProps.bindTo || bind;
        var mRows = (mTbl.props && mTbl.props.data) || [];
        var dRows = (dTbl.props && dTbl.props.data) || [];
        function expCount(row) {
          return dRows.filter(function (r) { return String(r[bindTo]) === String(row[bind]); }).length;
        }

        navTo(mdPage.id);
        var mdEl = $('#protoCanvas .ant-md');
        mdEl ? ok('主子表容器渲染成功（' + mdPage.id + '）') : fail('未渲染出 .ant-md');

        /* 列表页三件套 */
        var qN = (mTbl.props.query || []).length;
        if (qN) {
          $$('#protoCanvas .ant-query-bar .qf').length === qN
            ? ok('主表查询条渲染 ' + qN + ' 个条件字段')
            : fail('查询条字段数 ' + $$('#protoCanvas .ant-query-bar .qf').length + ' ≠ ' + qN);
        }
        var tbN = (mTbl.props.toolbar || []).length;
        if (tbN) {
          $$('#protoCanvas .ant-list-toolbar button').length >= tbN
            ? ok('主表操作条渲染 ' + tbN + ' 个按钮')
            : fail('操作条按钮数不足：' + $$('#protoCanvas .ant-list-toolbar button').length + ' < ' + tbN);
        }
        if (mTbl.props.pagination) {
          var foot = $('#protoCanvas .ant-table-foot');
          (foot && /共\s*[\d,]+\s*条/.test(foot.textContent))
            ? ok('主表分页脚渲染「共 N 条 + 每页显示 + 页码」')
            : fail('分页脚缺失或格式异常');
        }

        /* 单选圆点 + 默认选中首行 */
        $$('#protoCanvas .md-master .ant-radio-dot').length >= mRows.length
          ? ok('主表渲染 ' + mRows.length + ' 个单选圆点（标记当前行）')
          : fail('单选圆点缺失：' + $$('#protoCanvas .md-master .ant-radio-dot').length);
        var selN0 = $$('#protoCanvas .md-master tbody tr.md-sel').length;
        var dotOn0 = $$('#protoCanvas .md-master .ant-radio-dot.on').length;
        (selN0 === 1 && dotOn0 === 1)
          ? ok('默认恰好选中 1 行（高亮 + 圆点点亮）')
          : fail('默认选中态异常：高亮 ' + selN0 + ' 行 / 点亮 ' + dotOn0 + ' 个圆点');

        function domDetailCount() {
          var box = $('#protoCanvas .md-detail-body');
          if (!box) return -1;
          if (box.querySelector('.ant-empty-inline')) return 0;
          return box.querySelectorAll('tbody tr').length;
        }
        var selRow0 = $$('#protoCanvas .md-master tbody tr.md-sel')[0];
        var idx0 = $$('#protoCanvas .md-master tbody tr').indexOf(selRow0);
        var exp0 = expCount(mRows[idx0] || {});
        domDetailCount() === exp0
          ? ok('子表按 bind 过滤正确：默认行匹配 ' + exp0 + ' 条明细')
          : fail('子表过滤错误：DOM ' + domDetailCount() + ' ≠ 期望 ' + exp0);

        var cntTxt = txt($('#protoCanvas .md-count'));
        exp0 > 0 ? (cntTxt.indexOf(String(exp0)) >= 0
                      ? ok('子表标题栏显示条数：' + cntTxt)
                      : fail('子表标题条数不符：' + cntTxt + '（期望含 ' + exp0 + '）'))
                 : info('默认行无明细，跳过条数文案校验');

        /* 点其它行 → 子表联动 */
        var pick = -1;
        for (var i = 0; i < mRows.length; i++) {
          if (i === idx0) continue;
          if (expCount(mRows[i]) !== exp0) { pick = i; break; }
        }
        if (pick < 0) pick = mRows.length > 1 ? (idx0 === 0 ? 1 : 0) : -1;
        if (pick >= 0) {
          var trs = $$('#protoCanvas .md-master tbody tr');
          click(trs[pick]);
          var selN1 = $$('#protoCanvas .md-master tbody tr.md-sel').length;
          var newIdx = $$('#protoCanvas .md-master tbody tr').indexOf($$('#protoCanvas .md-master tbody tr.md-sel')[0]);
          var exp1 = expCount(mRows[pick]);
          (selN1 === 1 && newIdx === pick)
            ? ok('点第 ' + (pick + 1) + ' 行后唯一选中该行')
            : fail('点行后选中态错误：高亮 ' + selN1 + ' 行，落在第 ' + (newIdx + 1) + ' 行（期望 ' + (pick + 1) + '）');
          domDetailCount() === exp1
            ? ok('子表随选中行联动：第 ' + (pick + 1) + ' 行 → ' + exp1 + ' 条明细')
            : fail('子表未联动：DOM ' + domDetailCount() + ' ≠ 期望 ' + exp1);

          /* 无明细的行 → 子表空态 */
          var zeroIdx = -1;
          for (var z = 0; z < mRows.length; z++) { if (expCount(mRows[z]) === 0) { zeroIdx = z; break; } }
          if (zeroIdx >= 0) {
            click($$('#protoCanvas .md-master tbody tr')[zeroIdx]);
            var emp = $('#protoCanvas .md-detail-body .ant-empty-inline');
            emp && txt(emp).length
              ? ok('无明细行显示子表空态文案：' + txt(emp).slice(0, 20))
              : fail('无明细行未显示子表空态');
            click($$('#protoCanvas .md-master tbody tr')[pick]);
          } else info('该数据集所有主表行都有明细，跳过子表空态断言');
        } else info('主表只有 1 行，跳过选行联动断言');

        /* 子表展开 / 收起 */
        var head = $('#protoCanvas .md-detail-head');
        var dBox = $('#protoCanvas .md-detail');
        click(head);
        dBox.classList.contains('collapsed')
          ? ok('点子表标题栏可收起')
          : fail('子表未收起');
        var collapsedH = $('#protoCanvas .md-detail-body').getBoundingClientRect().height;
        collapsedH < 2 ? ok('收起后子表内容不可见（高度 ' + collapsedH + 'px）') : fail('收起后子表仍可见');
        click(head);
        !dBox.classList.contains('collapsed') ? ok('再点标题栏可展开') : fail('子表未展开');

        /* 点主表行会「自动展开」子表 */
        if (pick >= 0) {
          click(head);                       /* 先收起 */
          click($$('#protoCanvas .md-master tbody tr')[pick]);
          !dBox.classList.contains('collapsed')
            ? ok('收起状态下点主表行会自动展开子表')
            : fail('点主表行未自动展开子表');
        }

        /* 点操作列按钮不得被当成「选行」 */
        var keys = [];
        ((mTbl.props.columns || []).filter(function (c) { return c.type === 'action'; })[0] || {}).actions
          && ((mTbl.props.columns || []).filter(function (c) { return c.type === 'action'; })[0].actions || [])
              .forEach(function (a) { if (a && a.key) keys.push(String(a.key)); });
        var actKey = null;
        keys.forEach(function (k) {
          if (actKey) return;
          var navs = (mdPage.interactions || []).filter(function (ix) {
            return new RegExp('__act_[0-9*]+_' + k + '$').test((ix.on || {}).target || '');
          }).some(function (ix) { return (ix.actions || []).some(function (a) { return a.type === 'navigate'; }); });
          if (!navs) actKey = k;
        });
        var actBtn = actKey ? $('#protoCanvas .md-master [data-node-id$="__act_0_' + actKey + '"]') : null;
        if (actBtn) {
          var before = $$('#protoCanvas .md-master tbody tr.md-sel')[0];
          var beforeIdx = $$('#protoCanvas .md-master tbody tr').indexOf(before);
          click(actBtn);
          var after = $$('#protoCanvas .md-master tbody tr.md-sel')[0];
          var afterIdx = $$('#protoCanvas .md-master tbody tr').indexOf(after);
          afterIdx === beforeIdx
            ? ok('点操作列按钮「' + actKey + '」不会误触发选行')
            : fail('点操作列按钮误触发选行：第 ' + (beforeIdx + 1) + ' → 第 ' + (afterIdx + 1) + ' 行');
          var cancel = $('#protoCanvas [data-node-id$="__cancel"]');
          if (cancel) { click(cancel); ok('弹层可用合成 id __cancel 关闭'); }
        } else info('未找到不触发跳转的操作列按钮，跳过「不误触发选行」断言');

        /* 无 dialogception（容器选型硬规则） */
        $$('#protoCanvas .ant-modal .ant-modal').length === 0
          ? ok('无对话框嵌套对话框（dialogception）')
          : fail('存在 dialogception');
      }


      /* ===== 行为建模：命令策略（capabilities） =====
         断言不写死业务域：预期值全部按数据契约自算，故对 5 个示例通用 */
      try {
        var caps = data.capabilities || [];
        var sms = data.stateMachines || [];
        function smOf(ent) { return sms.filter(function (m) { return m.entity === ent; })[0] || null; }
        function stName(sm, id) {
          var s = ((sm && sm.states) || []).filter(function (x) { return x.id === id; })[0];
          return s ? s.name : id;
        }
        function capById2(id) { return caps.filter(function (x) { return x.id === id; })[0] || null; }
        function fromHas(c, st) { var f = c.from || []; return f.length === 0 || f.indexOf(st) >= 0; }
        /* 状态名 / 状态 id 都认（数据里两种写法都有） */
        function normSt(m, v) {
          if (!m || v == null) return v;
          if ((m.states || []).some(function (x) { return x.id === v; })) return v;
          var byName = (m.states || []).filter(function (x) { return x.name === v; })[0];
          return byName ? byName.id : v;
        }

        /* 先切到「声明了 entity 且能找到状态机」的页面，否则页面级按钮与状态下拉无从验证 */
        var entPage = pages.filter(function (p) { return p.entity && smOf(p.entity); })[0];
        if (entPage && entPage.id !== renderedPageId()) navTo(entPage.id);

        var curId = (/^#\/?([A-Za-z0-9_\-]+)/.exec(location.hash || '') || [])[1];
        var curPageObj = pages.filter(function (p) { return p.id === curId; })[0] || pages[0] || {};
        var ent = curPageObj.entity;
        var selE = $('#entitySelect');
        /* 某实体当前的业务状态：优先取顶栏下拉（仅当前页实体有），否则回落到状态机 initial */
        function curStateOf(e) {
          var m = smOf(e);
          if (!m) return null;
          if (selE && selE.getAttribute('data-entity') === e && selE.value) return selE.value;
          return m.initial || ((m.states || [])[0] || {}).id;
        }
        var curState = ent ? curStateOf(ent) : null;
        var sm = ent ? smOf(ent) : null;
        /* 行内动作按「行自身的 status」求值（行级），页面按钮按「单据状态」求值（页面级） */
        function stateFor(c, el) {
          var m = smOf(c.entity || ent);
          if (el && el.__iprdRow) return normSt(m, el.__iprdRow[c.stateField || 'status']);
          return curStateOf(c.entity || ent);
        }

        if (!caps.length) {
          info('未声明 capabilities（行为建模层为空），跳过命令策略断言');
        } else {
          ok('声明 ' + caps.length + ' 条命令策略（角色 × 状态 × 动作）');

          /* a) 每条策略的 entity 必须有状态机，否则「状态」无从谈起 */
          var noSm = caps.filter(function (c) { return !smOf(c.entity); });
          noSm.length === 0
            ? ok('每条命令策略的 entity 都能找到对应状态机')
            : fail('命令策略缺状态机：' + noSm.map(function (c) { return c.id + '(' + c.entity + ')'; }).join(', '));

          /* b) 当前单据状态下，DOM 里每个业务按钮的表现必须与策略一致
                逐按钮取「该命令所属实体」的状态，故不要求当前页声明 entity */
          var btns = $$('#protoCanvas [data-capability]');
          if (btns.length) {
            var bad = [];
            btns.forEach(function (b) {
              var c = capById2(b.getAttribute('data-capability'));
              if (!c) return;
              var expOk = fromHas(c, stateFor(c, b));
              var actOk = b.getAttribute('data-cap-state') === 'on';
              if (expOk !== actOk) {
                bad.push(c.id + '（应' + (expOk ? '可用' : '不可用') + '，实际' + (actOk ? '可用' : '不可用') + '）');
              } else if (!expOk && (b.getAttribute('data-cap-policy') || 'disabled') !== 'reject') {
                if (!(b.getAttribute('title') || '').trim()) bad.push(c.id + ' 不可用但没有原因说明');
              }
            });
            var bEnt = ent || (capById2(btns[0].getAttribute('data-capability')) || {}).entity;
            bad.length === 0
              ? ok('单据状态「' + stName(smOf(bEnt), curStateOf(bEnt)) + '」下 ' + btns.length + ' 个业务按钮的可用性与策略一致')
              : fail('按钮可用性与命令策略不一致：' + bad.join('；'));
          } else {
            info('当前页没有渲染带 capability 的按钮，跳过按钮可用性断言');
          }

          /* c) hidden 策略：不可用时应完全不渲染（DOM 里没有） */
          var hid = caps.filter(function (c) {
            var f = c.from || [];
            return c.policy === 'hidden' && f.length && !fromHas(c, curStateOf(c.entity || ent));
          });
          if (hid.length) {
            var leaked = hid.filter(function (c) { return $('#protoCanvas [data-capability="' + c.id + '"]'); });
            leaked.length === 0
              ? ok('hidden 策略的命令在当前状态不渲染（' + hid.length + ' 条）')
              : fail('hidden 策略仍被渲染：' + leaked.map(function (c) { return c.id; }).join(', '));
          }

          /* d) 点置灰按钮：只提示原因，不跳页（在「有置灰按钮」的状态下验一次） */
          var blockedTested = false;
          function testBlocked(tag) {
            var blocked = $$('#protoCanvas [data-cap-state="off"]').filter(function (b) {
              return (b.getAttribute('data-cap-policy') || 'disabled') === 'disabled';
            })[0];
            if (!blocked) return false;
            var h0 = location.hash;
            click(blocked);
            location.hash === h0
              ? ok('点置灰按钮不跳页（只给出原因）' + (tag ? '［' + tag + '］' : ''))
              : fail('点置灰按钮发生了跳页：' + h0 + ' → ' + location.hash);
            $$('#toastWrap .toast').length
              ? ok('点置灰按钮给出可见提示：' + txt($$('#toastWrap .toast').pop()))
              : info('未捕获到 toast，跳过提示断言');
            blockedTested = true;
            return true;
          }

          /* e) 切换单据状态 → 按钮可用性必须整体重算 */
          if (selE && selE.getAttribute('data-entity') === ent && selE.options.length > 1) {
            var before = {};
            $$('#protoCanvas [data-capability]').forEach(function (b) {
              before[b.getAttribute('data-capability')] = b.getAttribute('data-cap-state');
            });
            var target = null;
            (sm.states || []).forEach(function (s) {
              if (target || s.id === curState) return;
              var diff = caps.some(function (c) { return c.entity === ent && fromHas(c, curState) !== fromHas(c, s.id); });
              if (diff) target = s.id;
            });
            if (!target) {
              (sm.states || []).forEach(function (s) { if (!target && s.id !== curState) target = s.id; });
            }
            selE.value = target;
            selE.dispatchEvent(new Event('change', { bubbles: true }));
            var flipped = 0, wrong = [];
            $$('#protoCanvas [data-capability]').forEach(function (b) {
              var c = capById2(b.getAttribute('data-capability'));
              if (!c) return;
              var expOk = fromHas(c, stateFor(c, b));
              var actOk = b.getAttribute('data-cap-state') === 'on';
              if (expOk !== actOk) wrong.push(c.id);
              var now = b.getAttribute('data-cap-state');
              if (before[c.id] !== undefined && before[c.id] !== now) flipped++;
            });
            wrong.length === 0
              ? ok('切到单据状态「' + stName(sm, target) + '」后可用性全部重算正确（' + flipped + ' 个按钮状态发生变化）')
              : fail('切状态后可用性错误：' + wrong.join(', '));
            if (flipped === 0) info('该状态下没有按钮发生变化（策略可能未覆盖相邻状态）');
            /* 在这个状态下再验一次「点置灰按钮只提示、不跳页」 */
            if (!blockedTested) testBlocked(stName(sm, target));
            /* 复原，避免影响后续断言 */
            selE.value = curState;
            selE.dispatchEvent(new Event('change', { bubbles: true }));
          } else {
            info('当前页无「单据状态」下拉（page=' + (curPageObj.id || '?') + ' entity=' + ent
              + ' sel=' + (selE ? ((selE.getAttribute('data-entity') || '-') + '/' + selE.options.length + '项') : 'null')
              + '），跳过状态切换断言');
          }

          /* f) 点置灰按钮：只提示原因，不跳页（初始状态下补一次） */
          if (!blockedTested) testBlocked('初始状态');

          /* g) 右栏命令策略矩阵行数 = 该实体声明的命令数；列数 = 状态数 */
          var expectRows = caps.filter(function (c) {
            return ent ? ((c.entity || ent) === ent) : (c.page === curPageObj.id);
          });
          var mrows = $$('.cap-matrix tbody tr');
          if (mrows.length && expectRows.length) {
            mrows.length === expectRows.length
              ? ok('命令策略矩阵渲染 ' + mrows.length + ' 行（与 capabilities 一致）')
              : fail('命令策略矩阵 ' + mrows.length + ' 行 ≠ 该实体命令 ' + expectRows.length + ' 条');
            var mSm = smOf(ent || (expectRows[0] || {}).entity);
            var mcols = $$('.cap-matrix thead th').length - 1;
            if (mSm) {
              mcols === (mSm.states || []).length
                ? ok('命令策略矩阵列数 = 状态机状态数（' + mcols + '）')
                : fail('命令策略矩阵列数 ' + mcols + ' ≠ 状态数 ' + (mSm.states || []).length);
            }
          } else {
            info('右栏未渲染命令策略矩阵，跳过');
          }
        }
      } catch (e2) {
        fail('命令策略断言异常：' + e2.message);
      }

    } catch (e) {
      fail('测试异常：' + e.message + ' @ ' + String(e.stack || '').split('\n')[1]);
    }

    var box = document.createElement('div');
    box.id = '__testout';
    box.setAttribute('data-fails', String(failN));
    box.textContent = '\n' + out.join('\n') + '\n';
    document.body.appendChild(box);
  }
  if (document.readyState === 'complete') setTimeout(run, 700);
  else window.addEventListener('load', function () { setTimeout(run, 700); });
})();
