#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-P25 + V-01：形态与密度判据（作业型列表页）。

P1–P19 的规格见 `项目治理/迭代/I-07-形态与密度方案.md` §6；P20–P25（I-09 第一阶段）
的规格见 `references/12-visual-standard.md` 的 T-01/T-02/T-03/T-04/W-01/W-02，
`P7` 另承载 `W-00`；`V-01`（内容宽与视口闭合，三态）见同一文件 §1。

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
    python3 tests/check_ui_shape.py FILE.json --page p-x  # 指定页面（默认见下方 pick_page_ex）
    python3 tests/check_ui_shape.py FILE.json --all-pages # 逐页全判，**分页单列计数，不合并**
    python3 tests/check_ui_shape.py --selfcheck           # 注入反例，验证判据能红在正确的规则上
    python3 tests/check_ui_shape.py --keep                # 保留临时 HTML

退出码:
    0 = 无 FAIL、无 INCOMPLETE、SKIP 全在白名单内、且 V8 的 FAIL 集与期望名单逐条相等
    1 = 有 FAIL，或出现白名单外的 SKIP（后者打 `RESULT INCOMPLETE`，见 V13），
        或有判据报 INCOMPLETE（量具不可信，见 V-01 的 p) 段），
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

  2026-10-26 I-09（CAPA 实测暴露的三处**量具缺陷**，都不是阈值变更）：
    j) **列宽解析与容器同源**（P7 假 0）。`props_of()` 原来 `float(w)`，`float("52px")`
       抛 ValueError → 记成「未声明」。真实产物 CAPA 的 11 列写的是 `"52px"` 这种带单位字符串，
       于是「11/11 全声明」被报成「0/9 = 0%」，连带把「写了列宽但没锁布局」误诊成「没写列宽」。
       现在按容器 `colWidthStyle()` 的口径解析：纯数字按 px、`Npx` 取 N、`N%` 计入声明率但
       **不计入 Σ 预算**（百分比与 px 不可加），无法解析的单位单独打印。阈值 80% 与 `fixed` 不动。
    k) **挑页与量主体表**。旧默认按 `is_work_list_page` 取第一张「Content 直属 Table」的页，
       于是 CAPA 的 `page-capa-list`（主表包在 `MasterDetail` 里）被跳过，门去判了列表页之外的
       `page-capa-overdue` —— **同一份产物判哪页决定结论（19 vs 21 条 FAIL），而两页的
       `PASS` 总数都是 11，巧合把差异盖住了**。现在：默认判 `meta.currentPageId`（容器开页停在
       的那页）若它是列表页候选；`props_of()` 找不到 Content 直属表时退到 MasterDetail 里的
       第一张表并**在 note 里写明来源**；候选页清单、以及「还有哪几张没判」打进报告；`--all-pages`
       逐页单列计数。**判据本身一条没动**（`content_direct_tables()` 仍是 P2/P11/P13 的口径）。

  2026-10-26 I-09 第一阶段（新增判据，P1–P19 的阈值与 SKIP 白名单一条没动）：
    l) **P7 承载 W-00**：`fixed` 与「每列 width」成对，缺一即 FAIL；值里带红的理由
       （`原因=declared|fixed|both`）。不拆 P7a/P7b —— 拆开会让「0/8 + fixed」读出半绿。
    m) **P20–P25** 一条 P 承载一条条款（T-01/T-02/T-03/T-04/W-01/W-02），判据定义与阈值
       全按 `references/12-visual-standard.md`，本文件只实现，不重新解释。
    n) **两处口径细节，踩过才知道**（写在这里，免得下一个人重踩）：
       ① 行数按**行盒 top 去重**数，不数 Range 的 rect 个数 —— `text-overflow:ellipsis` 下
          被裁的尾巴会被 Chrome 切成第二个 rect，与第一段同一个 top，数 rect 会把「被裁」
          读成「折行」（example-06 的两列 ellipsis 会读成 19/20、20/20 全折行）。
       ② needW 按**承载文本的最内层元素自身字号**量（Tag 12px / td 14px）。用单元格字号代算
          不是精度问题，是可判定性问题：example-06「状态」列按 Tag@12px 得 78（绿，与渲染一致）、
          按 td@14px 得 84（红），差的 4px 只取决于实现者选了哪个字号。
    o) **W-03 的顺序落进代码**：`W-00` 不成立时 `P24` 判 FAIL(前置不成立) 而非 SKIP，
       原始读数照打。SKIP 会让存量产物在这条上免检（与 P18 同一处理）。

  2026-10-26 I-09 第二阶段（V-01 + 解析拆分，P1–P25 的阈值一条没动）：
    p) **V-01 接入，且是这条脚本里第一个三态判据**（`PASS` / `FAIL` / `INCOMPLETE`）。
       ① `INCOMPLETE` 只在**量具自己不可信**时出现，原因固定三个 TOKEN：
          `CONTENT_ZERO`（内容盒不存在/宽为 0）、`PARENT_INVISIBLE`（父盒 clientWidth=0）、
          `NAV_OUT_OF_RANGE`（导航宽为负）。它既不是绿也不是红 —— 记成 PASS 是静默绿，
          记成 FAIL 是把量具 bug 算到产物头上。`main()` 里它单独计数并让退出码非 0
          （`RESULT INCOMPLETE`），不并进 PASS；守卫按 TOKEN 相等断言，不按条数。
          另有一条**口径自证**：`①+③` 对 `content.offsetWidth` 差 ≤3px，超了打
          `BORDER_OR_SCROLLBAR`（标签，不是状态）。**不能拿 clientWidth 做这个断言** ——
          ① 减掉的 padding 正是 ③ 加回来的，`①+③ ≡ clientWidth` 是恒等式、永远为真。
       ② **只在产品态舞台里量**。评审态画布只有 1122 宽（工具外壳 + PRD 面板），
          拿它算闭合式等于让产品为一个它控制不了的侧栏买单 —— I-07 已为此付过一次代价。
          所以 `productStage()` 接受舞台宽：P2a 固定 1440，V-01 用当前视口宽各建一次。
       ③ **主判据是「归因差」，不是闭合式**。把 `①内容宽 + ②导航宽 + ③padding` 展开即得
          `①+②+③ ≡ 父.offsetWidth − b`（`b` = content 左右 border）：**只要父节点没换掉，
          闭合差恒为 0**。它判的从来是「父节点有没有铺满视口」，不是「内容宽有没有适配」。
          所以 `max-width:1024` 下被压窄留下的空档 416 会被减法式当成导航宽（1440−1024=416），
          三数之和仍是 1440、闭合差 0 判绿 —— 一条恒等式不能当判据。
          现行两条式子、结论按第一条：
            · **归因差**（主判据）`|减法导航 − 真实导航| ≤ 8` —— 丢掉的宽度是不是被导航合法占走；
            · **父节点铺满**（副判据，原闭合式改名）`|父.offsetWidth − b − 视口| ≤ 8` —— 父节点有没有被换小。
          减法导航 = `父宽 − content.offsetWidth`；真实导航 = **横着占位、且与内容并排**的同级兄弟
          宽之和，判据是**纯几何三条**（纵向重叠 / 水平不相交 / `position ∈ static|relative|sticky`），
          **不看 class** —— class 是约定，自定义元素做导航时白名单会把它算成 0，合格产物被误红。
          CAPA 的 `div.ant-header`（宽 1440）纵向不重叠，不进真实导航（判重叠前它会把 1440 算进去，
          一份合格产物被判 FAIL，I-07 已为此付过一次代价）；抽屉是 `absolute`，被第三条排除。
          减法式与真实导航**不等本身就是红**（归因差），不再打 `MISMATCH` 之类的旁注标签 ——
          那是恒等式判据留下的补丁，本轮取消。`parentElement` 与 `offsetParent` 不一致只打
          `PARENT_MISMATCH`（交叉校验，不是判据、不是 INCOMPLETE）。
          视口口径钉死 `window.innerWidth`（含滚动条），与 `父.offsetWidth` 同口径；用
          `documentElement.clientWidth` 会在有纵向滚动条时恒差 15px = 静默**红**（比静默绿更难查，
          所有人都会以为产物真超标）。归因差超 8px **不许加容差**。
          `N-e`（两档内容宽增量 vs 视口增量）**只作诊断打印**、不判红：唯一能让它单独红的输入是
          「两档 padding 不同」（`@1440 padding:24` / `@1600 padding:30` → 增量 148≠160），
          而多留白是合法设计；它想抓的「两档写成常数」已由归因差 @1600 抓住。
          一条只在合法产物上红的判据会逼下一个人去加容差，比恒绿更糟。
       ④ **`cause` 值的通用纪律**：每一条 `cause`，要么有输入能产出它，要么在文档里写明
          「不可达」及原因。N-a（`max-width`，自证 `V01_maxw` 实测归因差 208）与 N-d（zoom）有注入；
          **N-b 目前也不可达**：`R.Content` / `R.Layout` 都不消费 `width`/`style`
          （实测给 Content 加 `props.width=1080` 与 `props.style.width="1080px"`，内容宽都还是 1184），
          而 `n_b_width_hits()` 只读 JSON —— 它今天是个定位器，不是可达分支。规范里 N-b 那行
          （`1080` → 内容 1032 / 减法 360 / 归因差 152）是**代数读数**，不是实测；容器哪天开始消费
          `width`，这条才活。**N-c（外层换壳）在产物空间内不可达** —— 本仓库容器把
          `Layout.props.style.width` 直接落到节点上（`R.Layout` 根本不消费 width/style，实测加
          `props.width=1200` 父节点仍是 1440），产物写了宽也只会走 N-b；换壳只能来自容器代码
          自己，不是产物能表达的形态。为了不让判据②变成「永远为绿的观察行」，另配一份**手写 HTML
          壳样本** `tests/fixtures/fixture-nc-manual-shell.html`（非容器产物，名字里标出来）：
          它同时打两个数 —— **归因差 0**（减法与真实同时变 0、互相抵消，证明 N-c 归因差抓不到）
          与**铺满差 340**（只有判据②能红）。只证「340 红了」等于没证。
       ⑤ N-d（zoom / transform:scale）**独立判红**：缩放把布局宽与 `clientWidth` 解耦，
          闭合差恰被磨平（zoom .9 时仍报 0）。归因差这一档**也能**红（缩放把 48px 记成没人占），
          但它只说得清「有宽度不知去向」，说不清「是被缩放改掉了测量本身」——
          `cause=N-d` 的用处就在这里，不因为它和归因差重叠就删掉。
       ⑥ 自证里有 `V01_zoom`（N-d 独立红）、`V01_maxw`（N-a 盲区）与三条 `INCOMPLETE` 造红；
          加上 `P7` 两个方向、`P21`、`P22` 各一条，再有 `P2b` 的两条**第三态**注入
          （`SKIP(… total 未声明)` 与 `INCOMPLETE(INSUFFICIENT_ROWS) total 342 ≥ 9，行数 6`），
          共 25 条注入，另加 N-c 手写壳样本 1 条、`P2a/P2b` 条件式 SKIP 样本 1 条、XX-047 结论段 1 条，
          自证覆盖 **28 条** ——
          **「新增判据每一条都要有一条能红的注入」**，P7 是本轮抓 CAPA 的主力，
          它自己没被证过能红，等于「门能判 ≠ 门会拦」。N-c 那条不进 `INJECTIONS`：它改的是整份 DOM
          而不是 JSON/CSS，塞进「基线产物 + 注入」那套循环里会让 P1–P25 一起把手写壳当产物判。
          两条 `P2b` 注入用 `want_rows` 断言 **(状态, 值)** 而不是 FAIL 集合：这两条的第三态
          （SKIP / INCOMPLETE）根本不进 FAIL 集，只比 FAIL 集的话「少造几行换个 SKIP」永远绿。
          XX-047 那条直接调 `conclude()` 喂构造输入（**同时**给 INCOMPLETE 与 V8 不符），
          断言结论段**两个关键词都在** —— 只断言一个，早退回来照样过。
    q) **`main_table()` 改名 `resolve_list_table()`，与 `is_work_list_page()` 拆开**：
       前者答「哪张表是主表」（任何页都该能答，只用于取原始量），后者答「算不算作业型列表页」
       （形态类判据的适用范围，**定义不变**）。混在一起时只能靠放宽「列表页」定义去迁就
       CAPA 的 `page-capa-list`，那会连带改掉 P2/P11/P13 的适用范围。
       验收：CAPA list 11 列 / overdue 9 列；example-06 外包一层 `MasterDetail` 后仍取到 8 列主表
       （source 从 content-direct 变 master-detail，`is_work_list_page` 仍按原定义返回 False）。
    r) **两处分母的「排除数」必须打出来**（team-lead 裁定，本轮读数会变）：
       · `P24` 分母 = **未声明出口、且这列的值不可断**（token：单号/日期/序号/状态/Tag 文本）；
         声明了 `ellipsis` / `wrap+maxLines` 的列与值可断的长文本列**出分母**（归 T-02/T-03）——
         `needW` 的语义是「放得下一整条不可断的内容」，对配了省略号的列不成立（CAPA 的
         `事实陈述` needW=532 > 整表 866，**不可满足**，那是「该走 T-02」的信号而不是加宽指令）。
         可断性只两条判据：空格分词 ≥3、连续 CJK >6；**判值文本，不判渲染行数** ——
         行数由被修的列宽决定，列越窄越折 → 越像长文本 → 越会被排除，那是「越坏越免检」的循环定义。
         `example-06` 因此从 `0/8` 变 `0/6`。三数（needW/声明/渲染）**仍对全列照打**。
         前置红改 `FAIL(cause=prereq:W-00)`，并把**声明侧**读数打进值里 ——
         声明值在 JSON 里、与布局无关，这一半永远可判，不该被 W-00 一起抹掉。
       · `P23` 分母排除**三类**（表头 >6 全角字 / 空表头 / 无裁切盒），**三个数分别计数、不加总**，
         落在同一行里：`被裁 0/10 列@1234；另有 1 列表头 >6 全角字、2 列空表头、0 列无裁切盒，不入分母`。
         合成一个「另有 N 列」时，看报告的人分不清「判据放过了它」还是「它根本不适用」；
         空表头（`rowSelection`/`radio` 的槽位）**永远不可能红**，必然为绿的分母比没有分母更危险。
         `P23` 的分母仍是「表头 1~6 全角字」，**与 `P24` 的值可断性是两套口径**（一个量表头标签、
         一个量列值），不许为了「统一」合并 —— 合并只会让其中一条错。

  2026-10-26 I-09 第三阶段（新增 S-01 / S-02a / S-02b，P1–P25 的阈值与 SKIP 白名单一条没动）：
    s) **S-01 判集合，不判档数**。`12` §S-01 原写「≤3 档 **且** ⊆ {18,14,12}」，而「子集 ⊆ 三元集」
       已蕴含「档数 ≤3」—— 前半句是**恒真条款**（与 `①+③≡clientWidth`、`Σ(声明×k)≡表宽` 同族）。
       只数档数会放过 `{11,13,15}`（3 档全错）；只判集合才问得出「是哪些值」。
       档数、主档占比降为读数打印（占比不适合当判据：连续量、阈值只能拍，且会把单点小档稀释掉）。
       与 `P19`（档数 ≤3）的关系：**已知重叠，S-01 更强**。example-05 实测 `P19 PASS / S-01 FAIL`
       —— `{12,13,14}` 是 3 档但含 13。`P19` 本轮不动（P1–P19 冻结），重叠如实登记进自证。
    t) **S-02a 的行高判据只对「单行行」成立**。`T-02` 允许 `wrap + maxLines:2`，而合规的两行行
       必然 >34（14×1.57×2+padding≈58）。对全部 `tr` 判 ≤34 会把合规两行判成缺陷 ——
       CAPA `page-capa-list` 的 `58/68/78` 就是这件事，**`P9` 在它上面是假红**（本轮不动 P9，
       只把这条事实登记进反样本重登说明）。分母 = 行内文本行盒数 == 1 的数据行；
       分母 0 → `SKIP(分母 0：无单行数据行…)`，走条件式白名单（值里带条件，不许裸 SKIP）。
       行盒数**按每个文本节点各自量**：对整格 `selectNodeContents` 取 rects 会把单元格盒子自己
       也算一个 rect（top 与文字不同），单行格全被读成 2 行 —— 实测 example-06 的 20 行全变「多行」，
       S-02a 分母直接变 0。
    u) **S-02b 的「正文」要把控件与标题分出去，且两类各自计数**。控件（`button/.ant-btn`）的
       `line-height:1` 是控件规范值；标题（h1–h6）的紧行高（1.44）属标题 token。
       不排除时三份产物会各红 6/4/3 条 —— 全是按钮。比值分母是 **font-size**，不是行盒高。
       这条目前三份产物**全绿**（正文比只有 1.57），所以它必须配一条能红的注入
       （正文 `line-height:1` → 读 1.00），否则又是「判据在跑，判的不是它宣称的东西」。
"""

import argparse
import html as htmlmod
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTAINER = ROOT / "assets" / "container" / "index.html"
EXDIR = ROOT / "assets" / "examples"
# 样本（**不是容器产物**）：与 `example-*` 分开放，`default_targets()` 的 glob 取不到。
P2_FIXTURE = ROOT / "tests" / "fixtures" / "fixture-p2-rows-skip.json"
NC_FIXTURE = ROOT / "tests" / "fixtures" / "fixture-nc-manual-shell.html"
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
# S-01 / S-02（I-09 第三阶段，`references/12` §S-01 / §S-02）。**判集合，不判档数**：
# 「≤3 档 且 ⊆ {18,14,12}」里的「≤3 档」是恒真条款 —— 子集 ⊆ 三元集已蕴含档数 ≤3。
# 只数档数会放过 `{11,13,15}`（3 档全错）；只判集合才问得出「是哪些值」。
S01_SET = (12.0, 14.0, 18.0)
LINE_RATIO_MIN = 1.40             # S-02② 正文行高比区间（12 §S-02 已写死，不新定）
LINE_RATIO_MAX = 1.60
SHORT_FIELD_MAX_UNITS = 6.0       # P20/P23 的分母口径：整格文本 / 表头文本 ≤6 全角字
CELL_MAX_LINES = 2                # P22：单元格行数上限（T-03，与 T-02 的 maxLines:2 同源）
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


def skip_allowed(row):
    """V13 的**条件化**白名单：SKIP 只允许「这条判据当前不适用」，分两种形态。

    ① 静态名单（`P8`/`P13`/`P17`）：判据结构上不适用，与数据无关；
    ② `P2a`/`P2b`：**只当**值里写着 `SKIP(行数 N < 所需…` 时才允许 —— 看的是**值里的条件**，
       不是名单里有没有这个 id。只按 id 放行等于把「少造几行数据」变成通行证
       （`REJECT.md` 记过这个作弊面）。
    不按文件路径判：同一份文件换个目录结论就变，那是**身份判定**，不是事实判定。
    """
    if row.get("id") in SKIP_WHITELIST:
        return True
    if row.get("id") in ("P2a", "P2b"):
        return bool(re.match(r"SKIP\(行数 \d+ < \d+，", row.get("value") or ""))
    # ③ `S-02a`/`S-02b`：判据的**分母**可以为 0（没有单行数据行 / 没有正文元素），
    #    这时「0 条超标」不等于达标 —— 与 P2a 同理，只认值里的条件，不认 id。
    if row.get("id") == "S-02a":
        return bool(re.match(r"SKIP\(分母 0：无单行数据行", row.get("value") or ""))
    if row.get("id") == "S-02b":
        return bool(re.match(r"SKIP\(分母 0：无正文元素", row.get("value") or ""))
    return False

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
        # 8 条判据 × 两档 = 16 条，两档同红：说明是产物问题，不是某一档的偶然。
        # P15 已不在名单里：F6 之后它真实翻绿（判据未改），见交付说明第二批 §4。
        # P13 已移出（XX-046），理由写在下面那一行，不是「顺手少一条」。
        "P3a@1440", "P3a@1600",
        "P4@1440",  "P4@1600",
        "P7@1440",  "P7@1600",
        "P9@1440",  "P9@1600",
        "P10@1440", "P10@1600",
        "P11@1440", "P11@1600",
        "P12@1440", "P12@1600",
        # P13 已移出（XX-046）：这两个红是**假 total 触发的** —— 教材原写 `total:1286`，
        # 于是 `:1931` 的 `total < 100 → SKIP` 分支走不到，只能判 `pageSize ≥ 20` 的红。
        # 真实 `total=6` 时那个要求根本不成立（一页放 6 条就是全部）。它是**条件消失，
        # 不是判据放宽**：阈值一个字没动，SKIP 白名单里也没有 P13 的新增项。
        "P18@1440", "P18@1600",
        # I-09 第一阶段新增：P24 承载 W-01（列宽下限）。它在 example-05 上红是**前置红**，
        # 不是「列宽算错了」—— 该页 P7 本就红（2/7 声明率 + auto），按 W-03 的顺序，
        # 列宽未生效时「声明 ≥ needW」不作判决依据，本行记 FAIL 而不是 SKIP
        # （SKIP 会让存量产物在这条上免检，与 P18 同一处理）。
        "P24@1440", "P24@1600",
        # I-09 第三阶段新增判据（S-01 / S-02a）：这两条红是**新判据抓到的既有缺陷**，
        # 不是判据变严 —— P1–P25 的阈值与 SKIP 白名单本轮一个字没动，S 组只是把
        # `references/12` 里一直标「人工」的那两行落成代码。
        #   S-01：该页字号集合是 {12、13、14}，13 ∉ {18、14、12}。P19 只数档数（3 档 ≤3）照绿 ——
        #         这就是「档数判据放过 3 档全错」的实例，也是 S-01 必须判集合的理由。
        #   S-02a：单行行 6 行全部 39 > 34。这批行确实是单行（行盒数 1），所以它红的是行高本身；
        #         与「合规两行被 ≤34 误判」不是同一件事（后者见 CAPA list 的 P9，本轮不动 P9）。
        "S-01@1440",  "S-01@1600",
        "S-02a@1440", "S-02a@1600",
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
  /* 文本行数：按**行盒 top 去重**计数，不数 rect 的个数。
     为什么不能用 rect 个数：`text-overflow:ellipsis` 的单元格里，被裁掉的尾巴在 Chrome 里
     会被切成第二个 text rect，但它与第一段**同一个 top** —— 数 rect 会把「被裁」读成「折行」
     （example-06 两列 ellipsis 会读出 19/20、20/20「全折行」，而屏幕上是一行文字加省略号）。 */
  function lineCount(el){
    var tops={}, cnt=0, tw=document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n;
    while((n=tw.nextNode())){
      if(!(n.nodeValue||'').trim()) continue;
      var r=document.createRange(); r.selectNodeContents(n);
      var rs=r.getClientRects();
      for(var i=0;i<rs.length;i++){
        if(rs[i].height<=0.5) continue;
        var k=Math.round(rs[i].top);
        if(!(k in tops)){ tops[k]=1; cnt++; }
      }
    }
    return cnt;
  }
  /* T-04 的锚点：**自己发生裁切的盒子**，不是「承载表头文本的最内层元素」。
     为什么不能量最内层：`overflow:hidden` 只拦它自己那一层；内层元素的宽度由内容决定时
     它**永远不会超出自己**，超出的是父盒。更糟的是文本包一层 <span> 时 span 是 inline，
     它的 clientWidth / scrollWidth **恒为 0/0**，`0 > 0+1` 恒假 —— 判据恒绿，
     而真发生裁切的那个 th 一次都没被看。「用对了 API、选错了对象」比写错公式更难发现。
     判定链：从目标往上找第一个 computed overflow-x ∈ {hidden, clip} 的盒子；
     找不到返回 null（= 这一列没有裁切盒，本条不适用，**不是绿也不是红**，不进分母）。
     与 T-01 的区别要记牢：T-01 判**折行**用 Range.getClientRects()（对 inline 有效，
     一行一个 rect）；T-04 判**裁切**用 scrollWidth/clientWidth（对 inline 恒 0/0）。
     两种判据的锚点类型不同，不能互换。 */
  function clippingBox(el){
    var cur=el;
    while(cur && cur!==document.documentElement){
      var ox=cs(cur).overflowX;
      if(ox==='hidden'||ox==='clip') return cur;
      cur=cur.parentElement;
    }
    return null;
  }
  /* V-01 的全部几何量（**产品态**里量：评审外壳的 canvas 只有 1122 宽，进去就没有闭合可言）。
     ①②③ 的口径是刻意的「一个不含 padding、一个含 padding」，见下方注释；四段输出都要打。 */
  function v01Geo(C){
    var s=cs(C), out={};
    /* ① 内容宽 = content-box（clientWidth − padding）。**不是 clientWidth**：
       clientWidth 已经含 padding，① 若直接取它，③ 再加一遍就把 padding 算两次
       （教材 1232+208+48 = 1488，@1440 差 48 → 判据把合格产物误红）。
       ② 导航宽 = 父宽 − content.offsetWidth（减法式，含 padding）—— 两条口径不同是刻意的，
       谁想「把两条统一成一个口径」，统一的结果只会是其中一条错。 */
    var padL=parseFloat(s.paddingLeft||0), padR=parseFloat(s.paddingRight||0);
    out.contentBoxW = num(C.clientWidth - padL - padR);
    out.contentClientW = num(C.clientWidth);
    out.contentOffsetW = num(C.offsetWidth);
    out.contentPadW = num(padL + padR);
    /* b = content 的左右 border。`①+③ = 父宽 − b` 推出来的那个 b 必须单独量：
       `父.offsetWidth` 含 border，`clientWidth` 不含，拿掉它「父节点铺满」才对得上视口。 */
    out.contentBorderW = num(parseFloat(s.borderLeftWidth||0) + parseFloat(s.borderRightWidth||0));
    /* 视口口径**钉死为 window.innerWidth**（含滚动条），与 `父.offsetWidth` 同口径。
       用 documentElement.clientWidth 会在有纵向滚动条时恒差 15px —— 那是静默**红**，
       比静默绿更难查，因为所有人会以为产物真超标。 */
    out.viewportW = num(window.innerWidth);
    /* 口径自证：① + ③ 必须 == content.clientWidth。padding 被算两次时一眼露馅。 */
    out.identity = num(out.contentBoxW + out.contentPadW);
    var PB = C.parentElement;
    var pbox = PB || document.documentElement;
    /* 父节点 = **直接父盒**。主口径不用 offsetParent：它的定义是「最近的**已定位**祖先」，
       静态父盒会被跳过（position:fixed 浮层包裹时跳得更远），而「被谁横向占走了」问的是直接父盒。 */
    out.parentIsDoc = !PB;
    out.parentTag = (pbox.tagName || "").toLowerCase();
    out.parentClass = (typeof pbox.className === "string" ? pbox.className : "").trim()
                      .split(/\s+/).filter(Boolean).slice(0, 2).join(".");
    out.parentClientW = num(pbox.clientWidth);   // 0 = display:none / 未挂载 / 被折叠
    /* 文档元素用 clientWidth：documentElement.offsetWidth 含滚动条，会引入 15px 级误差。 */
    out.parentW = PB ? num(pbox.offsetWidth) : num(pbox.clientWidth);
    /* 交叉校验（**不是判据、也不是 INCOMPLETE**）：`parentElement` 与 `offsetParent` 不一致时
       打 `PARENT_MISMATCH`。主口径仍是 parentElement —— offsetParent 是「最近的**已定位**祖先」，
       静态父盒会被跳过（position:fixed 浮层包裹时跳得更远），不能当主口径。 */
    var op = C.offsetParent;
    out.offsetParentTag = op ? (op.tagName || "").toLowerCase() : "none";
    out.offsetParentClass = (op && typeof op.className === "string")
        ? op.className.trim().split(/\s+/).filter(Boolean).slice(0, 2).join(".") : "";
    /* 量具舞台自己就是 position:fixed，它必然是内容的定位包含块 —— 那是**夹具**造成的，
       不是产物的定位祖先。不排除它，每份产物都会带一条常数噪音（读的人会学会无视它）。 */
    out.offsetParentIsStage = !!(op && op.id === "__prodStage");
    out.parentMismatch = !!op && op !== PB && !out.offsetParentIsStage;
    /* 真实导航 = **横着占位、且与内容并排**的同级兄弟宽之和。**纯几何，不看 class** ——
       class 是约定：某产物用自定义元素做导航时，class 白名单会把它算成 0，
       于是「减法导航 208 − 真实 0 = 归因差 208」，合格产物被误红。三条同时成立才算：
         ① 纵向重叠（`r.top < c.bottom && r.bottom > c.top`）—— 上面一整行的页头不是横向占位；
         ② 水平不相交（`r.right <= c.left + 1 || r.left >= c.right - 1`）—— 必须并排，不能叠着；
         ③ `position ∈ {static, relative, sticky}` —— absolute/fixed **不占流式宽**，是浮层；
            **排除 fixed 与排除 absolute 是同一个理由，不是遗漏**（team-lead 2026-10-26 定，驳回翻案）：
            抽屉/浮层常用 `position:fixed`，算进真实导航的话，CAPA 那种页面一开抽屉归因差直接爆红 ——
            它的宽度不是「从内容区减出去的那块」，而是「盖在内容区上的一层」。
       代入：example-06 的 `div.ant-sider`（208，左、并排、static）✓；
       CAPA 的 `div.ant-header` 纵向不重叠 ✗（不判重叠就会把 1440 全算进导航 → 误红）；
       抽屉 `absolute` 被 ③ 排除，不虚增。 */
    var sib=0, cr=C.getBoundingClientRect();
    if(PB){ for(var ci=0; ci<PB.children.length; ci++){
      var ch=PB.children[ci];
      if(ch===C) continue;
      var rr=ch.getBoundingClientRect();
      if(!(rr.top < cr.bottom && rr.bottom > cr.top)) continue;
      if(!(rr.right <= cr.left + 1 || rr.left >= cr.right - 1)) continue;
      var cpos=cs(ch).position;
      if(!(cpos==='static'||cpos==='relative'||cpos==='sticky')) continue;
      sib += ch.offsetWidth||0;
    } }
    out.sibNavW = num(sib);
    /* N-a：content 及其祖先上写死的 max-width（px）。只定位不单独判红。 */
    var mw=[];
    for(var a1=C; a1 && a1!==document.documentElement; a1=a1.parentElement){
      var mv=cs(a1).maxWidth || "none";
      if(/^\d+(\.\d+)?px$/.test(mv) && parseFloat(mv)>0) mw.push({
        tag:(a1.tagName||"").toLowerCase(),
        cls:(typeof a1.className==="string"?a1.className:"").trim().split(/\s+/).filter(Boolean)[0]||"",
        w:num(parseFloat(mv))});
    }
    out.maxWidthHits=mw;
    /* N-c：内容外层套了**显式 px 宽**的容器。只看 inline style ——
       computed width 对一切块级元素都是 px，分不出「写死」与「撑满」。 */
    var fx=[];
    for(var a2=C.parentElement; a2 && a2!==document.documentElement && a2.id!=='__prodStage'; a2=a2.parentElement){
      var iw=(a2.style && a2.style.width) ? String(a2.style.width) : "";
      if(/^\d+(\.\d+)?px$/.test(iw)) fx.push({tag:(a2.tagName||"").toLowerCase(),
        cls:(typeof a2.className==="string"?a2.className:"").trim().split(/\s+/).filter(Boolean)[0]||"",
        w:num(parseFloat(iw))});
    }
    out.fixedWrapHits=fx;
    /* N-d：zoom / transform:scale。**这条必须能独立判红**：zoom .9 下内容盒实际布局宽 1316 而
       clientWidth 报 1184，闭合差被磨平成 0 —— 一条闭合式挡不住「改测量本身」的输入。 */
    var zh=null;
    for(var a3=C; a3 && a3!==document.documentElement; a3=a3.parentElement){
      var st=cs(a3), zz=parseFloat(st.zoom);
      if(!isNaN(zz) && Math.abs(zz-1)>0.001){
        zh={tag:(a3.tagName||"").toLowerCase(),
          cls:(typeof a3.className==="string"?a3.className:"").trim().split(/\s+/).filter(Boolean)[0]||"",
          kind:"zoom", v:num(zz)}; break;
      }
      var tf=st.transform || "none";
      if(tf && tf!=="none"){
        var mm=tf.match(/^matrix\(([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),/);
        if(mm){
          var sx=parseFloat(mm[1]), sy=parseFloat(mm[4]);
          if(Math.abs(sx-1)>0.001 || Math.abs(sy-1)>0.001){
            zh={tag:(a3.tagName||"").toLowerCase(),
              cls:(typeof a3.className==="string"?a3.className:"").trim().split(/\s+/).filter(Boolean)[0]||"",
              kind:"scale", v:num(sx)}; break;
          }
        }
      }
    }
    out.scaleHit=zh;
    return out;
  }
  /* ---- I-09：W-01 needW / T-01 短字段分母 需要的三个量 ---- */
  /* 全角字宽（1 = 一个全角字）。半角按 0.557 计 —— 与视觉标准 §W-01 的估算算式同一系数
     （14px 下 7.8px ≈ 0.557em）。用它划「≤6 全角字」的分母边界，不用字符数：
     中英混排的「待检验 12」按字符数是 7，按字宽只有 5.3。 */
  function textUnits(s){
    var u=0;
    for(var i=0;i<(s||'').length;i++){
      var c=s.charCodeAt(i);
      u += (c>=0x2E80) ? 1 : ((c===0x20) ? 0.28 : 0.557);
    }
    return Math.round(u*100)/100;
  }
  /* 承载文本的最内层元素：自身有**直接非空文本节点**的元素。排除 root 自身 ——
     纯文本单元格的 root 就是 td，把 td 当「最内层」会量到整格宽而不是文字宽。 */
  function leafEls(root){
    var out=[], all=root.querySelectorAll('*');
    for(var i=0;i<all.length;i++){
      var e=all[i];
      for(var j=e.childNodes.length-1;j>=0;j--){
        var nd=e.childNodes[j];
        if(nd.nodeType===3 && (nd.nodeValue||'').trim()){ out.push(e); break; }
      }
    }
    return out;
  }
  /* 元素自然外宽：同字体、nowrap 的隐藏副本。用副本而不是 scrollWidth ——
     nowrap 元素被裁时 scrollWidth 是「溢出内容宽」，与「本来要占多宽」不是同一个数。 */
  function naturalW(el){
    var st=cs(el);
    var p=document.createElement('span');
    p.style.cssText='position:absolute;left:-9999px;top:0;visibility:hidden;white-space:nowrap;';
    p.style.fontFamily=st.fontFamily; p.style.fontSize=st.fontSize; p.style.fontWeight=st.fontWeight;
    p.style.fontStyle=st.fontStyle; p.style.letterSpacing=st.letterSpacing;
    p.textContent=(el.textContent||'').replace(/\s+/g,' ').trim();
    document.body.appendChild(p);
    var w=p.getBoundingClientRect().width;
    document.body.removeChild(p);
    return num(w);
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

    // ---- 评审态内容宽（折叠前量一次，只记录、不判）：PRD 面板是**工具外壳成本**，
    // 把它算进闭合式等于让产品为一个它控制不了的侧栏买单（I-07 已付过一次代价）。
    var s0=cs(C);
    out.reviewContentBoxW = num(C.clientWidth - parseFloat(s0.paddingLeft||0) - parseFloat(s0.paddingRight||0));

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
      /* ---- I-09 新判据（T-01/T-02/T-03/T-04 + W-01/W-02）的原始量 ----
         全部**按列聚合**再交给 Python 判：一个 20 行 × 12 列的表逐格回传会让
         `#__shapeout` 的 data-json 膨胀十倍，而判据只关心「这一列的极值 / 计数」。 */
      var audit=(function(){
        var outCols=[];
        for(var ai=0; ai<ths.length; ai++){
          var ath=ths[ai], sth=cs(ath);
          /* 量**文字宽**（W-01 的 needHdr、T-04 的分母）用最内层元素：那是字体度量，
             与上面的**裁切锚点**是两件事，不要混成一个。 */
          var hLeaf=leafEls(ath), hEl=hLeaf.length?hLeaf[0]:ath;
          var hW=naturalW(hEl)||0;
          var hPad=parseFloat(sth.paddingLeft||0)+parseFloat(sth.paddingRight||0);
          outCols.push({
            i:ai, title:txt(ath).slice(0,24),
            hdrUnits: textUnits(txt(ath)),
            hdrTextW: num(hW), hdrPadW: num(hPad),
            /* T-04：被裁 = **裁切盒**的 scrollWidth > clientWidth + 1（锚点见 clippingBox()）。
               三个读数都打出来 —— 只打布尔值，被裁 4px 和 被裁 400px 长得一样。
               hdrClip 为 null = 这一列没有裁切盒（本条不适用），它与 false 必须分开：
               false 是「量过了、没裁」，null 是「没有可量的盒子」。 */
            hdrClip: (function(){ var b=clippingBox(ath);
                      return b ? (b.scrollWidth > b.clientWidth + 1) : null; })(),
            hdrAnchor: (function(){ var b=clippingBox(ath);
                        return b ? (b===ath?'th':b.tagName.toLowerCase()) : 'none'; })(),
            hdrScrollW: (function(){ var b=clippingBox(ath); return b?num(b.scrollWidth):null; })(),
            hdrClientW: (function(){ var b=clippingBox(ath); return b?num(b.clientWidth):null; })(),
            thW: num(ath.offsetWidth),
            sortable: !!ath.querySelector('.ant-table-column-sorter'),
            chip:false, btn:false,
            needVal:0, needHdr: num(hW+hPad),
            maxLines:0, maxTdH:0, lineH:null, padY:null,
            cells:0, shortCells:0, shortWrapped:0, multiCells:0, multiLong:0, overCells:0,
            /* W-01 的分母按**可断性**判，判的是「这列的值是不是一个不可断的 token」——
               所以要把最长那条值原文带回 Python。它是**值文本**，与列宽、渲染行数无关
               （拿渲染行数当依据就是循环定义：列越窄越折行，越会被判成长文本而逃出分母）。 */
            longest:'',
            samples:[]
          });
        }
        for(var ri2=0; ri2<rows.length; ri2++){
          var tds=rows[ri2].querySelectorAll('td');
          if(tds.length<2) continue;
          for(var k2=0;k2<tds.length;k2++){
            var td2=tds[k2], col=outCols[k2];
            if(!col) continue;
            var s2=cs(td2);
            var padX=parseFloat(s2.paddingLeft||0)+parseFloat(s2.paddingRight||0);
            if(col.lineH==null){
              col.lineH=num(parseFloat(s2.lineHeight)||(parseFloat(s2.fontSize)||14)*1.5);
              col.padY=num(parseFloat(s2.paddingTop||0)+parseFloat(s2.paddingBottom||0));
            }
            var hasTag=!!td2.querySelector('.ant-tag'), hasBtn=!!td2.querySelector('.ant-btn,button');
            if(hasTag) col.chip=true;
            if(hasBtn) col.btn=true;
            var t2=txt(td2);
            if(!t2) continue;
            if(t2.length > (col.longest||'').length) col.longest = t2.slice(0, 120);
            var leaves=leafEls(td2), ln=0;
            if(leaves.length){ for(var q2=0;q2<leaves.length;q2++) ln=Math.max(ln,lineCount(leaves[q2])); }
            else ln=lineCount(td2);
            /* W-01 的分母：这一列的值本来需要多宽。多叶（一行多个按钮）取**和 + 间隙**，
               不取 max —— 「详情 开始」并排占的是两段宽的和，取 max 会低估（52 vs 80）。 */
            var valNeed=0;
            if(leaves.length){
              var sum2=0, mx2=0;
              for(var q3=0;q3<leaves.length;q3++){ var ow2=outerW(leaves[q3])||0; sum2+=ow2; if(ow2>mx2) mx2=ow2; }
              var gap2=parseFloat(s2.columnGap||0); if(!isFinite(gap2)) gap2=0;
              valNeed=(leaves.length>1)?(sum2+gap2*(leaves.length-1)):mx2;
            } else {
              valNeed=naturalW(td2)||0;
            }
            valNeed+=padX;
            if(valNeed>col.needVal) col.needVal=num(valNeed);
            col.cells++;
            if(ln>col.maxLines) col.maxLines=ln;
            var th2=td2.getBoundingClientRect().height;
            if(th2>col.maxTdH) col.maxTdH=num(th2);
            if(ln>1){
              col.multiCells++;
              /* 「长文本」多行格：短字段折行是 T-01 的事，别让它同时算进 T-02 的
                 「长文本没出口」—— 否则给 Tag 列加个 max-width，两条判据一起红，
                 数不清是「短字段折了」还是「长文本没出口」。 */
              if(textUnits(t2)>6 && !hasTag && !hasBtn) col.multiLong++;
              if(col.samples.length<3) col.samples.push({r:ri2,text:t2.slice(0,14),lines:ln,h:num(th2)});
            }
            /* T-03：超限 = 行数 >2，或格高 > 2 行 + 上下 padding + 1px 边框 */
            var lim=(col.lineH||21)*2+(col.padY||0)*2+1;
            if(ln>2 || th2>lim+0.5) col.overCells++;
            /* T-01 的分母：含 Tag/Button 的格，或整格文本 ≤6 全角字 */
            if(hasTag||hasBtn||textUnits(t2)<=6){
              col.shortCells++;
              if(ln>1) col.shortWrapped++;
            }
          }
        }
        return outCols;
      })();
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
        audit:audit,
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

    /* ---- S-02①：数据行的「行内文本行盒数」。
       T-02 允许 `wrap + maxLines:2`，而**合规的两行行必然 >34**（14×1.57×2+padding≈58）。
       所以「行高 ≤34」不能对全部 tr 判 —— 那一刀会把合规的两行判成缺陷
       （CAPA 的 58/68/78 就是这件事，P9 在它上面是假红）。分母只能是**单行行**。
       行盒数用 Range 的 client rects 数**不同 top**：一个 inline 盒可能被拆成多个 rect
       （Tag 里的文字、带 padding 的 span），数 rect 个数会把单行读成多行。 */
    out.rowLines=(function(){
      var tabs=C.querySelectorAll('.ant-table'), res=[];
      /* 行盒数只能按**每个文本节点**各自量：对整格 `selectNodeContents` 取 rects，浏览器会把
         单元格盒子自己也返回一个 rect（与文字行盒的 top 不同），于是每个单行格都读成 2 行
         —— 实测 example-06 的 20 行全部被读成「多行」，S-02a 分母直接变 0。 */
      function lines(td){
        var tops={}, n=0;
        var tw=document.createTreeWalker(td, NodeFilter.SHOW_TEXT, null), t;
        while((t=tw.nextNode())){
          if(!(t.nodeValue||'').trim()) continue;
          var el=t.parentElement;
          if(!el || !el.getClientRects().length) continue;
          var r=document.createRange(); r.selectNodeContents(t);
          var rs=r.getClientRects();
          for(var i=0;i<rs.length;i++){
            if(rs[i].height<=0) continue;
            var k=Math.round(rs[i].top);
            if(!tops[k]){ tops[k]=1; n++; }
          }
        }
        return n;
      }
      for(var ti=0; ti<tabs.length; ti++){
        /* 嵌套表跳过：否则外层 querySelectorAll 会把内层行再数一遍 */
        if(tabs[ti].parentElement && tabs[ti].parentElement.closest('.ant-table')) continue;
        var trs=tabs[ti].querySelectorAll('tbody tr'), arr=[];
        for(var j=0;j<trs.length;j++){
          var tds=trs[j].querySelectorAll('td');
          if(tds.length<2) continue;                 /* 与 P9 / P2 同口径：<2 格不算数据行 */
          var mx=0;
          for(var k2=0;k2<tds.length;k2++){ var l=lines(tds[k2]); if(l>mx) mx=l; }
          arr.push({table:ti+1, idx:j, h:trs[j].offsetHeight, lines:mx});
        }
        res.push({i:ti+1, rows:arr});
      }
      return res;
    })();

    /* ---- S-02②：正文行高比。分母排除两类，**两类各自单独计数、不许悄悄丢**：
       ① 控件（button / .ant-btn）：`line-height:1` 是控件规范值，不是正文；
       ② 标题（h1–h6）：紧行高（14px 字 / 18px 标题的 1.44）属于标题 token，不进正文分母。
       比值分母是 **font-size**，不是行盒高（两句都写在同一行里会读成同一件事）。
       `line-height:normal` 单独计数，不混进比值。 */
    out.typeAudit=(function(){
      var body={}, head={}, ctl={}, normal={body:0,head:0,ctl:0}, cnt={body:0,head:0,ctl:0};
      var tw=document.createTreeWalker(C, NodeFilter.SHOW_TEXT, null), n;
      while((n=tw.nextNode())){
        if(!(n.nodeValue||'').trim()) continue;
        var p=n.parentElement; if(!p) continue;
        if(!p.getClientRects().length) continue;
        var k=null;
        if(p.closest('button, .ant-btn')) k='ctl';
        else if(p.closest('h1,h2,h3,h4,h5,h6')) k='head';
        else if(p.closest('.ant-table')) continue;    /* 「正文」不含表格内文字 */
        else k='body';
        var s2=cs(p), fs=parseFloat(s2.fontSize), lh=s2.lineHeight;
        if(!(fs>0)) continue;
        cnt[k]++;
        if(!lh || lh==='normal'){ normal[k]++; continue; }
        var px=parseFloat(lh);
        if(!(px>0)){ normal[k]++; continue; }
        var r=Math.round(px/fs*100)/100;
        var b=(k==='ctl')?ctl:(k==='head'?head:body);
        b[r]=(b[r]||0)+1;
      }
      return {body:body, head:head, ctl:ctl, normal:normal, counts:cnt};
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
  function productStage(stageW){
    var W = stageW || 1440;
    var canvas=document.querySelector('#protoCanvas');
    if(!canvas) return {err:'NO_CANVAS'};
    /* 上一次调用留下的舞台要先拆：V-01 会按 1440/1600 各建一次，留着会叠两层 fixed 浮层
       （第二层盖住第一层，rect 全是相对各自舞台算的 —— 读数看不出问题、人会以为只有一层）。 */
    var prev=document.getElementById('__prodStage'); if(prev) prev.remove();
    var ov=document.createElement('div'); ov.id='__prodStage';
    ov.style.cssText='position:fixed;left:0;top:0;width:'+W+'px;height:900px;z-index:99999;'+
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

    var out={w:W,h:900};
    var C=clone.querySelector('.ant-content');
    var s=C?getComputedStyle(C):null;
    out.contentBoxW = C&&s? num(C.clientWidth - parseFloat(s.paddingLeft||0) - parseFloat(s.paddingRight||0)) : null;
    out.contentClientW = C? num(C.clientWidth) : null;
    /* V-01 只在**产品态**量：评审外壳的 canvas 只有 1122 宽，进去永远闭合不了 —— 那不是产物的问题。
       舞台宽 = 视口宽（1440/1600 各建一次），这样「两档视口」与「产品页本身的宽」是同一个数。 */
    out.v01 = C ? v01Geo(C) : null;
    var t=clone.querySelector('.ant-table');
    var wrap=t? (t.closest('.ant-table-wrap')||t.parentElement) : null;
    if(!wrap){ out.err='NO_TABLE'; out.v01 = C ? v01Geo(C) : null; return out; }
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
    /* 舞台**留在 DOM 里**：measure_reject.py 的 rejectExtras() 要复用同一个舞台改宽量两档
       （它按 id 取）。下一次 productStage() 调用会先拆掉旧的（见函数开头）。 */
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
    /* P2a 的产品态夹具固定 1440×900（判据就是「1440 无外壳」，换成别的宽等于改判据）。
       V-01 另建一次 = 当前视口宽：闭合式要问的正是「页面是否撑满这一档视口」，
       拿 1440 的舞台去回答 1600 的问题，差 160 会被当成产物缺陷。 */
    try{ d.product=productStage(1440); }catch(ex2){ d.product={err:'PRODUCT:'+ex2.message}; }
    try{ d.v01prod=productStage(window.innerWidth); }catch(ex3){ d.v01prod={err:'V01:'+ex3.message}; }
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


def md_tables(page):
    """MasterDetail 节点下挂的 Table（主子表式列表页的主表 / 子表），按树序。

    只给「挑页」与「量主表」用，**不参与任何判据**：`content_direct_tables()` 仍是
    P2/P11/P13 的「列表页」定义（改动它等于改口径，要单独裁定）。
    """
    out = []
    for n in iter_nodes(page.get("componentTree") or {}):
        if n.get("type") != "MasterDetail":
            continue
        out.extend(c for c in (n.get("children") or []) if c.get("type") == "Table")
    return out


def is_list_page(page):
    """**挑页**用的列表页口径 = 原 `is_work_list_page` ∪「主子表式列表页」。

    为什么加后者：CAPA 的 `page-capa-list`（用户实际看的那页）主表就在 `MasterDetail` 里，
    旧口径把它整个排除，门只好去判别的页 —— 判哪页决定结论，而 PASS 总数可能碰巧相同。
    门槛（分页 或 ≥5 行）沿用 `is_work_list_page`，避免把 2–3 行明细的详情页也算进来。
    """
    if is_work_list_page(page):
        return True
    for t in md_tables(page):
        p = t.get("props") or {}
        if p.get("pagination") or len(p.get("data") or []) >= 5:
            return True
    return False


def page_candidates(data):
    """所有列表页候选，按 `pages[]` 顺序：[(page, kind)]，kind ∈ content-table / master-detail。"""
    out = []
    for p in (data.get("pages") or []):
        if is_work_list_page(p):
            out.append((p, "content-table"))
        elif is_list_page(p):
            out.append((p, "master-detail"))
    return out


def pick_page_ex(data, want=None):
    """挑要判的页，并把「为什么是这页」一起返回：(page, reason, 候选 id 列表)。

    规则（新的在前，逐条都有理由）：
      ① `--page` 显式指定 —— 人点了名就判点名的那页，找不到直接报错不兜底；
      ② `meta.currentPageId`，**当且仅当**它是列表页候选。这是容器开页停的地方 =
         用户打开产物第一眼看到的那页；CAPA 的差一页就是这么来的；
      ③ 首个「Content 直属 Table」的作业型列表页（旧行为，example-05/06 走的还是这条）；
      ④ 首个「主子表式列表页」（③ 为空时才用）。
    返回 reason 是为了把它打进报告主行：**「判了哪页」必须是结论的一部分**，
    不能只在某条判据的 note 里出现。
    """
    pages = data.get("pages") or []
    cands = page_candidates(data)
    cand_ids = [p.get("id") for p, _ in cands]

    if want:
        for p in pages:
            if p.get("id") == want:
                return p, "显式 --page", cand_ids
        raise EnvError("找不到页面 %s（有：%s）"
                       % (want, ", ".join(p.get("id", "") for p in pages)))

    cur = (data.get("meta") or {}).get("currentPageId")
    if cur and cur in cand_ids:
        for p in cands:
            if p[0].get("id") == cur:
                return p[0], "meta.currentPageId（容器开页停在这页）", cand_ids

    for p, kind in cands:
        if kind == "content-table":
            return p, "首个作业型列表页（Content 直属 Table）", cand_ids
    if cands:
        return cands[0][0], "首个主子表式列表页（MasterDetail 内挂 Table）", cand_ids
    return None, "无列表页候选", cand_ids


def pick_page(data, want=None):
    return pick_page_ex(data, want)[0]


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


def align_audit(cols, au):
    """把 JSON 的列与 DOM 量到的列对齐，返回 [(col, audit), …]。

    容器在有 `rowSelection` / `radio` 时会在表头和数据行**最前面各插一列**，
    此时 DOM 列数比 JSON 多。直接 zip 会让整张表错位一列 —— 每一列都拿前一列的读数判，
    而且读数看起来完全正常（数字都在合理范围里）。所以按差值整体右移，不做逐列猜。
    """
    if not au or not cols:
        return []
    lead = max(0, len(au) - len(cols))
    return [(cols[i], au[i + lead]) for i in range(min(len(cols), len(au) - lead))]


def w01_need(col, a):
    """W-01 的 needW：`ceil(实测文本宽) + 24 + (Tag 16) + (可排序 20)`，再守 ≥48。

    量文本宽用的是**承载文本的最内层元素自身字号** + 自身 padding（见探针 `outerW()`）：
    Tag 列是 12px、正文是 14px。这条不是精度问题，是**可判定性**问题 ——
    `example-06` 的「状态」列按 Tag@12px 得 78（渲染 80，绿），按 td@14px 得 84（红），
    差的 4px 完全来自「实现者选了哪个字号」。不写死这条，同一份产物会随机红绿。
    """
    if col.get("ellipsis"):
        # ellipsis 列**只**量表头：值可以截断，表头不行。
        # 这里不能写成 max(值, 表头) —— 那等于要求「截断列也必须放得下完整值」，
        # 把「配了 ellipsis」这件事本身判红（example-06 的物资名称 125 < 值宽 192）。
        need = a.get("needHdr") or 0
    else:
        need = max(a.get("needVal") or 0, a.get("needHdr") or 0)
    if a.get("sortable"):
        need += 20
    return int(max(48, math.ceil(need - 1e-6)))


def needw_digest(pairs, n=6):
    return "，".join("%s 声明 %s / needW %s"
                     % (c.get("title"), fmt(c.get("declW")), fmt(w01_need(c, a)))
                     for c, a in pairs[:n]) or "—"


# ------------------------------------------------------------------ V-01
V01_TOL = 8          # 两次 clientWidth 取整 + 边框 + 亚像素累计；不是调出来的容差（§V-01）
V01_DELTA = 160      # 1600 − 1440，两档视口差本身，N-e 用它，不是魔数


def n_b_width_hits(page):
    """N-b 的定位量：Content/Layout 等布局节点的 props/style 里写死的 px 宽。

    这条藏在 JSON 里，DOM 上只能看到一个「刚好 1080 的盒子」—— 所以必须回到 JSON 找。
    只定位不单独判红：红的结论由 V-01 闭合式给，N-b 只是 cause 标签（另立判据会把同一个数算两次）。
    """
    hits = []
    for n in iter_nodes(page.get("componentTree") or {}):
        # **只认 Content / Layout**：Sider 的 `style.width=208` 是加数②（页内导航），
        # 把它算成「写死的容器」会让每一份有导航的产物都挂 cause=N-b。
        if n.get("type") not in ("Content", "Layout"):
            continue
        p = n.get("props") or {}
        for holder in (p.get("style") or {}, p):
            w = holder.get("width")
            if isinstance(w, (int, float)):
                hits.append("%s.%s=%s" % (n.get("type"), "style.width", w))
            elif isinstance(w, str) and re.match(r"^\d+(\.\d+)?px$", w.strip()):
                hits.append("%s.style.width=%s" % (n.get("type"), w.strip()))
            if hits:
                break
    return hits


def v01_row(dom, page, vw):
    """V-01：**归因差为主判据**，父节点铺满为副判据，两档各判。

    `|减法导航 − 真实导航| ≤ 8`            ← 主判据（`attrib`），结论按这条
    `|父.offsetWidth − b − 视口| ≤ 8`     ← 副判据「父节点铺满」（原闭合式改名）

    **为什么主判据不是闭合式**：`①+②+③` 展开就是 `父.offsetWidth − b`（`b`=content 左右 border），
    父节点没被换掉时**闭合差恒为 0** —— 它是恒等式，判的是「父节点铺满没铺满」，不是
    「内容宽适配没适配」。归因差判的才是后者：掉下去的宽度**是不是被导航合法占走了**，
    没占走的那部分就是缺陷（N-a / N-b 全靠这条红）。两条式子都打，结论只看归因差。

    **三态，不是两态**：`INCOMPLETE` 只在「量具自己不可信」时出现，原因**固定三个 TOKEN**
    （守卫按 TOKEN 相等断言，不按条数 —— 「条数相同、集合不同」这坑本仓库踩过）：
      · `CONTENT_ZERO`      —— 内容盒不存在 / 宽为 0（`.ant-content` 被移除或未渲染）；
      · `PARENT_INVISIBLE`  —— 父盒 `clientWidth=0`（display:none / 未挂载 / 被折叠）；
      · `NAV_OUT_OF_RANGE`  —— 导航宽为负（内容比父盒还宽 = 父节点选错或取错元素）。
    它既不是绿也不是红 —— 记成 PASS 是静默绿，记成 FAIL 是把量具 bug 算到产物头上。
    `MISMATCH` 标签本轮**取消**：归因差不成立本身就是红，不需要再挂一个「两数不一致但结论照旧」
    的旁注（那是恒等式判据留下的补丁）。
    N-a~N-e 是**定位标签**，红由本条给（`FAIL(cause=N-d)` 之类），不另立判据。
    **`cause` 纪律**：每个值要么有输入能产出它，要么写明「不可达」及原因。N-c（外层换壳）
    在产物空间内不可达，判据②仍能红 —— 由 `tests/fixtures/fixture-nc-manual-shell.html`
    那份手写壳证明（归因差 0 / 铺满差 340），见上方模块头 p)④。

    输出必须带父节点身份：只打一个导航宽时，「父节点选对」与「选错」在文本上分不出来，
    而人看到 INCOMPLETE 通常当成工具坏了，不会想到是量错了 —— 这件事只能靠这行字解决。
    """
    title = "内容宽与视口闭合（产品态）"
    thr = "归因差|减法−真实|≤%d；父节点铺满|父宽−b−视口|≤%d" % (V01_TOL, V01_TOL)

    def tag_of(t, c):
        return ("%s.%s" % (t, c)) if c else (t or "—")

    def inc(token, why, note=""):
        # 三态里的第三种：量具不可信。原因用固定 TOKEN，守卫可以按集合比。
        return {"id": "V-01", "title": title, "value": "—", "threshold": thr,
                "status": "INCOMPLETE",
                "note": "INCOMPLETE(口径错) 原因=%s —— %s%s"
                        % (token, why, ("；" + note) if note else "")}

    # **只在产品态舞台里量**：评审态画布只有 1122 宽（外壳 panner + PRD 面板），
    # 拿它算闭合式等于要求产品为一个它控制不了的侧栏买单 —— 那是评审工具的成本，不是产物缺陷。
    stage = dom.get("v01prod") or {}
    g = stage.get("v01") or {}
    # **`stage.err == 'NO_TABLE'` 不算量具故障**：V-01 要的四个量（内容盒 / 父盒 / 真实导航 /
    # 视口）与有没有表格无关。以前这里把 NO_TABLE 也拦下并记成 `CONTENT_ZERO` —— 那个 TOKEN
    # 说的是「内容盒不存在」，而实际是「没有表」，报错文案与原因对不上，守卫按 TOKEN 比就会误判。
    if not g or g.get("err"):
        return inc("CONTENT_ZERO", "产品态夹具里没有可量的内容盒（%s）"
                                   % (g.get("err") or "无 v01 读数"))

    cw, cli, off = g.get("contentBoxW"), g.get("contentClientW"), g.get("contentOffsetW")
    if cw is None or off in (None, 0) or abs(cw) < 1:
        # 内容和父盒同时「量不到」时要分清是哪一种：父盒也 0 → 父盒不可见（PARENT_INVISIBLE），
        # 只有内容是 0 → 内容盒不存在（CONTENT_ZERO）。两个 TOKEN 混成一个，守卫就没法按集合比。
        if (g.get("parentClientW") or 0) == 0:
            return inc("PARENT_INVISIBLE", "内容与父盒的 clientWidth 都为 0（%s）"
                       % tag_of("html" if g.get("parentIsDoc") else g.get("parentTag"),
                                "" if g.get("parentIsDoc") else g.get("parentClass")))
        return inc("CONTENT_ZERO", "内容盒宽为 0（clientWidth=%s / offsetWidth=%s）"
                                   % (fmt(cli), fmt(off)))
    pad = g.get("contentPadW")                      # ③ 内容左右 padding
    ident = g.get("identity")                       # ① + ③
    vw = stage.get("w") or vw                       # 闭合式里的「视口宽」= 舞台宽（就是建舞台时的视口宽）
    p_tag = "html" if g.get("parentIsDoc") else g.get("parentTag")
    p_cls = "" if g.get("parentIsDoc") else (g.get("parentClass") or "")
    p_name = tag_of(p_tag, p_cls) + ("(文档元素)" if g.get("parentIsDoc") else "")
    p_w = g.get("parentW")
    p_cli = g.get("parentClientW")
    nav = (p_w - off) if (p_w is not None) else None    # 减法导航（含 padding 口径）
    sib = g.get("sibNavW")                              # 真实导航（纵向重叠的同级 Sider/Menu）
    b = g.get("contentBorderW") or 0                    # content 左右 border
    vw_real = g.get("viewportW") or stage.get("w") or vw  # 视口 = window.innerWidth（含滚动条）
    # 主判据：减法算出的「导航宽」里，有多少没被真实导航占走。
    attrib = abs(nav - sib) if (nav is not None and sib is not None) else None
    # 副判据：父盒（去掉 content 的 border）是不是等于视口。负 = 父节点被换小了。
    # 父节点是文档元素时不判：`parentW` 取的是 clientWidth（不含滚动条），与 innerWidth 口径不同，
    # 差 15px 会变成静默红 —— 宁可这条不判，也不许改视口口径去迁就它。
    fill = None if g.get("parentIsDoc") else (
        (p_w - b - vw_real) if p_w is not None else None)
    scale = g.get("scaleHit")
    review = dom.get("reviewContentBoxW")

    # 三数和只作**展示**：它 ≡ 父宽 − b，与视口的关系就是「铺满差取负」，同一个数不判两次。
    tri = (cw + nav + pad) if (nav is not None and cw is not None and pad is not None) else None
    head = ("V-01 %s 父节点=%s 宽%s 内容%s 导航%s[减法 %s−%s / 真实 %s 归因差 %s] "
            "padding%s 归因差%s 铺满差%s ｜ 三数和%s(恒等，只作展示)")
    val = head % (fmt(vw_real), p_name, fmt(p_w), fmt(cw), fmt(nav),
                  fmt(p_w), fmt(cli), fmt(sib), fmt(attrib), fmt(pad),
                  fmt(attrib), fmt(abs(fill)) if fill is not None else "不判", fmt(tri))

    # ---- 口径自证：① + ③ 对 **content.offsetWidth**，差 ≤3px。
    # **不能拿 clientWidth 做这个断言**：① 减掉的 padding 正是 ③ 加回来的，
    # `①+③ ≡ clientWidth` 是定义恒等式、永远为真 —— 那是一条恒绿判据（本轮已撤掉）。
    # offsetWidth 含 border、clientWidth 不含 border 也不含滚动条，±3 是这几项差异的上界；
    # 超了打 `BORDER_OR_SCROLLBAR`（标签，不是新状态），**不许把式子改成
    # `offsetWidth + border + scrollbar` 去凑读数** —— 那是改判据迁就读数。
    idn = "口径自证 内容%s+padding%s=%s vs offsetWidth%s 差%s" % (
        fmt(cw), fmt(pad), fmt(ident), fmt(off),
        ("%+d" % (ident - off)) if (ident is not None and off is not None) else "—")
    if ident is None or off is None or abs(ident - off) > 3:
        idn += " ← BORDER_OR_SCROLLBAR（±3 超出：content 有 border/滚动条，或加数①口径不对）"
    note = idn
    if g.get("parentMismatch"):
        # 交叉校验标签：**不是判据、也不是 INCOMPLETE**。父节点主口径是 parentElement，
        # offsetParent 只是旁证（静态父盒会被它跳过），两者不一致时提示一句，不影响结论。
        note += "；PARENT_MISMATCH(父节点=%s / offsetParent=%s)" % (
            p_name, tag_of(g.get("offsetParentTag"), g.get("offsetParentClass")))
    if review is not None:
        note += "；评审态内容宽 %s（不代入本条）" % fmt(review)

    # ---- 量具不可信 → INCOMPLETE（原因固定 TOKEN），不许落 PASS/FAIL
    if p_cli in (None, 0) or p_w in (None, 0):
        return inc("PARENT_INVISIBLE", "%s.clientWidth=%s —— 父盒不可见（display:none / 未挂载 / 被折叠）"
                   % (p_name, fmt(p_cli)), note)
    # 越界只剩「负」这一侧可判：上界 `父宽 − content.offsetWidth` **就是 nav 本身**（恒等），
    # 写 `nav > (p_w - off)` 是一句恒假的断言。负 = 内容比父盒还宽 = 父节点选错或取错元素。
    if nav is None or nav < -0.5:
        return inc("NAV_OUT_OF_RANGE", "导航宽 %s < 0 —— 内容比父盒还宽" % fmt(nav), note)
    # ---- N-d 独立判红：zoom/scale 改的是**测量本身**，闭合式看不见它
    if scale:
        return {"id": "V-01", "title": title, "value": val, "threshold": thr,
                "status": "FAIL",
                "note": "cause=N-d 内容区被缩放：%s 的 %s=%s —— 闭合差被磨平，归因差只能说出"
                        "「有宽度不知去向」，说不出「测量被改掉了」，所以本条要自己红；%s"
                        % (tag_of(scale.get("tag"), scale.get("cls")), scale.get("kind"),
                           fmt(scale.get("v")), note)}

    # ---- 主判据：归因差。掉下去的宽度没被真实导航占走 → 红（N-a / N-b 靠这条）
    # **cause 由「先红的这条式子」决定**：归因差红 → 只可能是 N-a/N-b，不可能是 N-c
    # （外层换壳时减法与真实同时变 0、互相抵消，归因差是 0）。不写「先认 A 再认 B」的顺序规则，
    # 那条规则在两条式子同时红时会给出错标签。
    if attrib is not None and attrib > V01_TOL:
        cause, why = "", ""
        if g.get("maxWidthHits"):
            h = g["maxWidthHits"][0]
            cause, why = "N-a", "max-width=%spx@%s" % (h.get("w"), tag_of(h.get("tag"), h.get("cls")))
        else:
            nb = n_b_width_hits(page)
            if nb:
                cause, why = "N-b", nb[0]
        lead = ("cause=%s（%s）" % (cause, why)) if cause else \
               "未定位到 N-a/N-b 的形态（内容区写死了一个非整数的窄值）"
        # `fixedWrapHits` 只作诊断打印，不作 cause 依据（team-lead 裁定）。
        fx = g.get("fixedWrapHits") or []
        fxd = ("；外层固定宽候选（只作诊断，不作 cause 依据）：%s"
               % "、".join("%s %spx" % (tag_of(h.get("tag"), h.get("cls")), h.get("w"))
                          for h in fx[:3])) if fx else ""
        both = ""
        if fill is not None and abs(fill) > V01_TOL:
            # 两条式子同时红：结论仍取主判据，铺满差并列打出、带它自己的 cause（N-c）。
            both = "；另：铺满差 %s>%d 同时红（cause=N-c，第二行并列，不改变本行结论）" % (
                fmt(abs(fill)), V01_TOL)
        return {"id": "V-01", "title": title, "value": val, "threshold": thr,
                "status": "FAIL",
                "note": "%s；归因差 %s>%d：减法导航 %s 里只有 %s 真是导航占走的，另 %s 是内容被"
                        "压窄后留下的空档（空档被减法式当成了导航，所以闭合差仍是 0 —— "
                        "**闭合差 0 不能据此判绿**）%s；%s%s"
                        % (lead, fmt(attrib), V01_TOL, fmt(nav), fmt(sib), fmt(attrib),
                           both, note, fxd)}

    # ---- 判据②：父节点铺满。**先红的那条式子决定 cause** —— 这一条红只说一件事：
    # 父节点没铺满视口（被换小），也就是 N-c。
    # `fixedWrapHits` 不作 cause 依据，只作诊断打印：它是「内联 px 宽的祖先」这个启发式，
    # 拿它认 cause 会在两条式子同时红时给出错标签。
    # 唯一例外仍保留 N-b：若 JSON 里的宽**正好等于父宽**，那父节点就是被那条声明写窄的，
    # 归类该是「JSON 里写死宽」而不是「容器套壳」。
    if fill is not None and abs(fill) > V01_TOL:
        cause, why = "N-c", "父节点未铺满视口"
        for nm in n_b_width_hits(page):
            m = re.search(r"=(\d+(?:\.\d+)?)px?$", nm)
            if m and abs(float(m.group(1)) - p_w) <= 1:
                cause, why = "N-b", nm
                break
        fx = g.get("fixedWrapHits") or []
        fxd = ("；外层固定宽候选（只作诊断，不作 cause 依据）：%s"
               % "、".join("%s %spx" % (tag_of(h.get("tag"), h.get("cls")), h.get("w"))
                          for h in fx[:3])) if fx else "；外层无内联 px 宽的祖先（换壳不在 DOM 上）"
        return {"id": "V-01", "title": title, "value": val, "threshold": thr,
                "status": "FAIL",
                "note": "cause=%s（%s）；父节点铺满失败：父宽%s − border%s = %s，视口%s，差%+d（%s）%s；%s"
                        % (cause, why, fmt(p_w), fmt(b), fmt(p_w - b), fmt(vw_real), fill,
                           "负 = 父节点被换小了，不是内容变窄" if fill < 0 else "正 = 父节点比视口宽",
                           fxd, note)}

    return {"id": "V-01", "title": title, "value": val, "threshold": thr,
            "status": "PASS", "note": note}


def v01_cross(rows_by_vp):
    """N-e **只作诊断打印**：不参与 PASS/FAIL、不占编号、缺陷计数 0。

    两档的内容宽增量与视口增量并排打出来，是唯一一眼能看出「内容没跟着视口长」的读数。
    但它**不能当判据**：唯一能让它单独红的输入是「两档 padding 不同」
    （@1440 `padding:24`、@1600 `padding:30` → 内容增量 148 ≠ 160），
    而归因差 0、铺满差 0 —— 屏幕变宽多留白是**正当设计**，不是缺陷。
    一条只在合法产物上红的判据会逼下一个人去加容差，那比恒绿更糟。
    它想抓的「两档都写成常数」已经由**归因差 @1600** 抓住
    （内容锁 1184 → 减法导航 416 / 真实 208 → 归因差 208），不需要第二条。
    """
    ws = sorted(rows_by_vp)
    if len(ws) < 2:
        return ""
    w0, w1 = ws[0], ws[-1]
    r0 = next((r for r in rows_by_vp[w0] if r["id"] == "V-01"), None)
    r1 = next((r for r in rows_by_vp[w1] if r["id"] == "V-01"), None)
    if not r0 or not r1:
        return ""
    c0 = _v01_value_num(r0, "内容")
    c1 = _v01_value_num(r1, "内容")
    if c0 is None or c1 is None:
        return ""
    d, gap = c1 - c0, (w1 - w0)
    tail = "" if abs(d - gap) <= V01_TOL else "（差 %+d，只作诊断）" % (d - gap)
    return ("N-e 诊断: 内容宽 %d→%d 增量%+d / 视口增量%d%s（不判红）"
            % (c0, c1, d, gap, tail))


def _v01_value_num(row, key):
    m = re.search(key + r"(\d+(?:\.\d+)?)", row.get("value") or "")
    return float(m.group(1)) if m else None


def evaluate(props, dom, page, vw):
    """返回 rows。props=Python 侧从 JSON 读到的（列宽/pagination/Drawer），dom=几何。"""
    rows = []
    tables = dom.get("tables") or []
    t0 = tables[0] if tables else None
    cw = dom.get("contentBoxW")
    tier = accept_tier(cw)
    is_accept = tier is not None

    # ---- V-01 内容宽与视口闭合（产品态，三态：PASS / FAIL / INCOMPLETE）
    rows.append(v01_row(dom, page, vw))

    # ---- P1 统计卡
    verdict(rows, "P1", "列表页统计卡数", fmt(dom.get("statCount")), "0",
            "PASS" if dom.get("statCount") == 0 else "FAIL",
            "Content 内 .ant-stat；统计只允许独立统计页")

    # ---- P2a 产品态一屏行数
    prod = dom.get("product") or {}

    def _rows_gate(pid, tn, n, need):
        """`P2a`/`P2b` 的行数前置：**单轨、按事实分**（team-lead 裁定，XX-045）。

        ```
        允许 SKIP   ⟺ 示例行数 < 所需 且（无分页器 或 total < 所需）
        INCOMPLETE  ⟺ total ≥ 所需 且 示例行数 < 所需      →  TOKEN `INSUFFICIENT_ROWS`
        ```
        两条都是「事实不够 / 数据够却没造全」，与「文件放在哪个目录」无关 ——
        按目录判是身份判定，同一份文件换个目录结论就变。
        `total` 是 `P13` 已经在读的现成字段，不必加新字段；它才是「造少」的证据。
        值里必须带条件与实测值，**不许出现裸 SKIP**：否则「少造几行换一个 SKIP」又走得通。
        """
        total = props.get("total")
        if total is not None and total >= need:
            verdict(rows, pid, tn,
                    "INCOMPLETE(INSUFFICIENT_ROWS) total %s ≥ %d，行数 %d"
                    % (fmt(total), need, n), "≥%d" % need, "INCOMPLETE",
                    "数据够却没造全：`total` 声明这页有 %s 条，示例只渲染了 %d 行。"
                    "这不是「判据不适用」，是夹具造少了 —— 补行后重跑必须能判出 PASS/FAIL。"
                    % (fmt(total), n))
        else:
            why_total = "total 未声明" if total is None else "total %s < %d" % (fmt(total), need)
            verdict(rows, pid, tn, "SKIP(行数 %d < %d，%s)" % (n, need, why_total),
                    "≥%d" % need, "SKIP",
                    "示例数据只有 %d 行（< 所需 %d），且分页字段也说明不了造少 —— 本条不适用，"
                    "不是达标。" % (n, need))

    if prod.get("err") or prod.get("rowCount") is None:
        verdict(rows, "P2a", "产品态一屏整行数", "—", "≥%d" % TARGET_ROWS_PRODUCT,
                "SKIP", "产品态夹具未建立（%s）" % (prod.get("err") or "无表格"))
    elif prod.get("rowCount") < TARGET_ROWS_PRODUCT:
        _rows_gate("P2a", "产品态一屏整行数", prod["rowCount"], TARGET_ROWS_PRODUCT)
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
    elif t0.get("rowCount", 0) < target:
        _rows_gate("P2b", "评审态一屏整行数", t0.get("rowCount", 0), target)
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

    # ---- P7 列宽声明率 + table-layout（**运行时载体 = W-00**）
    #
    # W-00 是「fixed 与每列 width 成对，缺一即 FAIL」。**不拆成 P7a/P7b**：
    # 拆开之后 `0/8 + fixed` 会读出「P7b 绿」的半绿，而「只 fixed 不写 width」不是解法
    # （8 列各 108px、长列被裁）。所以一条判据、一个结论、把红的理由带上（declared / fixed / both）。
    # 「声明」= width 非空且能解成数值（`52` / `"52px"` 等价，见 parse_col_width）；
    # 百分比列也计入声明率，但**不进 Σ 预算**（P17）。阈值 80% 与 fixed 要求未改（team-lead 裁定）。
    cols = props["cols"]
    decl = [c for c in cols if c.get("declW") is not None or c.get("declPct") is not None]
    pct = props.get("declaredPct") or []
    bad_w = props.get("unparsableW") or []
    rate = (len(decl) / len(cols)) if cols else 0
    layout = (t0 or {}).get("tableLayout")
    decl_ok = bool(cols) and rate >= DECL_RATE_MIN
    fixed_ok = layout == "fixed"
    ok7 = decl_ok and fixed_ok
    why7 = "" if ok7 else ("both" if (not decl_ok and not fixed_ok)
                           else ("declared" if not decl_ok else "fixed"))
    note7 = "声明率按 columns 的 width 非空计，不按渲染后列宽；`52`/`\"52px\"` 视作同一声明"
    if not ok7:
        note7 += "；红的原因 = %s（declared=声明率不足 / fixed=布局未锁 / both=两者都缺）" % why7
    if pct:
        note7 += "；其中 %d 列为百分比宽（计入声明率，不计入 Σ 预算）" % len(pct)
    if bad_w:
        note7 += "；%d 列宽度无法解析（%s），按未声明计" % (
            len(bad_w), ", ".join("%s=%s" % (c.get("title"), c.get("declRaw")) for c in bad_w[:3]))
    if props.get("tableSource") not in (None, "content-direct"):
        note7 += "；主表取自 %s（Content 直属无 Table）" % props.get("tableSource")
    verdict(rows, "P7", "列宽声明率 / 布局（W-00）",
            "declared=%d/%d (%.0f%%) fixed=%s%s"
            % (len(decl), len(cols), rate * 100, str(fixed_ok).lower(),
               ("" if ok7 else " → FAIL(原因=%s)" % why7)),
            "≥80% 且 fixed", "PASS" if ok7 else "FAIL", note7)

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

    # ================= I-09 第三阶段：S-01 / S-02（references/12） =================
    # 与 P19 的关系说清楚：P19 判「档数 ≤3」，S-01 判「集合 ⊆{18,14,12}」。
    # 后者更强 —— `{12,13,14}` 是 3 档但含 13，P19 绿、S-01 红（example-05 实测）。
    # 两条都在，是因为 P1–P19 的阈值本轮**一个字不许动**（含 P19），重叠如实登记在自证里。

    # ---- S-01 字号集合（档数、主档占比只作读数，不参与判定）
    ft = dom.get("fontTiers") or {}
    S01_sizes = sorted(float(k) for k in ft.keys())
    S01_total = sum(int(v) for v in ft.values()) or 0
    if not S01_sizes:
        verdict(rows, "S-01", "字号集合（⊆{18、14、12}）", "—", "集合 ⊆ {18、14、12}", "SKIP",
                "量不到文本")
    else:
        outside = [s for s in S01_sizes if s not in S01_SET]
        top_s, top_n = max(ft.items(), key=lambda kv: (int(kv[1]), -float(kv[0])))
        val = "{%s}（%d 档）｜主档 %s 占 %.1f%%（n=%d）" % (
            "、".join(("%g" % s) for s in S01_sizes), len(S01_sizes),
            ("%g" % float(top_s)), (100.0 * int(top_n) / S01_total) if S01_total else 0.0, S01_total)
        sample = dom.get("fontTiersSample") or {}
        why = []
        for s in outside:
            k = ("%g" % s)
            srcs = sample.get(k) or sample.get(str(int(s)) if float(s).is_integer() else str(s)) or []
            why.append("%s ∉ 集合（%s）" % (k, "、".join(srcs) if srcs else "样本缺失"))
        verdict(rows, "S-01", "字号集合（⊆{18、14、12}）", val, "集合 ⊆ {18、14、12}",
                "PASS" if not outside else "FAIL",
                ("越界：%s ｜ " % "；".join(why) if why else "") +
                "档数与主档占比只作读数：档数相同的 `{11,13,15}` 与 `{12,14,18}` 同色，"
                "所以判据落在集合上")

    # ---- S-02① 单行数据行的行高（多行行不计入：T-02 允许 wrap，两行必然 >34）
    S02a_tabs = dom.get("rowLines") or []
    S02a_rows = [r for t in S02a_tabs for r in (t.get("rows") or [])]
    S02a_one = [r for r in S02a_rows if (r.get("lines") or 0) == 1]
    S02a_multi = [r for r in S02a_rows if (r.get("lines") or 0) >= 2]
    S02a_nolines = [r for r in S02a_rows if (r.get("lines") or 0) == 0]
    if not S02a_rows:
        verdict(rows, "S-02a", "单行行行高", "—", "单行行 ≤%d" % ROW_MAX_H, "SKIP", "无表格数据行")
    elif not S02a_one:
        verdict(rows, "S-02a", "单行行行高",
                "SKIP(分母 0：无单行数据行；多行 %d 行不计入，行盒 0 的 %d 行量不到)"
                % (len(S02a_multi), len(S02a_nolines)),
                "单行行 ≤%d" % ROW_MAX_H, "SKIP",
                "「0 条超标」与「没有单行行可判」不是同一件事 —— 分母为 0 时不许判绿")
    else:
        bad = [r for r in S02a_one if (r.get("h") or 0) > ROW_MAX_H]
        mx = max((r.get("h") or 0) for r in S02a_one)
        verdict(rows, "S-02a", "单行行行高",
                "超标 %d/%d ｜ 单行最高 %s ｜ 多行 %d 行不计入%s"
                % (len(bad), len(S02a_one), fmt(mx), len(S02a_multi),
                   ("（行盒 0 的 %d 行也量不到）" % len(S02a_nolines)) if S02a_nolines else ""),
                "单行行 ≤%d" % ROW_MAX_H, "PASS" if not bad else "FAIL",
                ("超标行：%s ｜ " % "、".join("table[%d]>tr[%d] %s" % (r["table"], r["idx"], fmt(r["h"]))
                                            for r in bad[:6]) if bad else "") +
                "分母只含**行内文本行盒数 == 1** 的数据行：T-02 允许 wrap+maxLines:2，"
                "合规两行行必然 >34，对全部 tr 判会把它误判成缺陷")

    # ---- S-02② 正文行高比（分母 font-size；排除控件与标题，两类各自计数）
    ta = dom.get("typeAudit") or {}
    S02b_body = ta.get("body") or {}
    S02b_head = ta.get("head") or {}
    S02b_ctl = ta.get("ctl") or {}
    S02b_normal = ta.get("normal") or {}
    S02b_cnt = ta.get("counts") or {}
    if not S02b_body:
        verdict(rows, "S-02b", "正文行高比",
                "SKIP(分母 0：无正文元素；标题 %d、控件 %d 均不计入，normal %d)"
                % (int(S02b_cnt.get("head") or 0), int(S02b_cnt.get("ctl") or 0),
                   int(S02b_normal.get("body") or 0)),
                "∈[%.2f, %.2f]" % (LINE_RATIO_MIN, LINE_RATIO_MAX), "SKIP",
                "分母为 0 时「0 个越界」不等于达标")
    else:
        def _rng(m):
            ks = sorted(float(k) for k in m.keys())
            return "{%s}（n=%d）" % ("、".join("%g" % k for k in ks),
                                    sum(int(v) for v in m.values()))
        outside2 = [(float(k), int(v)) for k, v in S02b_body.items()
                    if not (LINE_RATIO_MIN <= float(k) <= LINE_RATIO_MAX)]
        verdict(rows, "S-02b", "正文行高比（分母 font-size）",
                "正文 %s ｜ 标题 %s ｜ 控件 %s ｜ normal %d"
                % (_rng(S02b_body), _rng(S02b_head), _rng(S02b_ctl),
                   int(S02b_normal.get("body") or 0)),
                "∈[%.2f, %.2f]" % (LINE_RATIO_MIN, LINE_RATIO_MAX),
                "PASS" if not outside2 else "FAIL",
                ("越界：%s（%d 个）｜ " % ("、".join("%g×%d" % (k, n) for k, n in outside2),
                                          sum(n for _, n in outside2)) if outside2 else "") +
                "正文 = 表格外、非控件（`line-height:1` 是控件规范值）、非标题（紧行高属标题 token）")

    # ================= I-09 第一阶段新增：T-01~T-04 / W-01 / W-02 =================
    # P 号是运行时行号，注释里的 T-xx / W-xx 是 references/12-visual-standard.md 的条款号。
    # 一条 P 只承载一条条款（P7 例外：它承载 W-00，理由见该条 note）。
    au = (t0 or {}).get("audit") or []
    pairs = align_audit(cols, au)
    w00_ok = bool(cols) and rate >= DECL_RATE_MIN and layout == "fixed"

    # ---- P20 T-01 短字段折行（阈值 0，必须带分母）
    if not t0 or not au:
        verdict(rows, "P20", "T-01 短字段折行", "—", "折行 0 处", "SKIP", "无表格")
    else:
        short_n = sum((a.get("shortCells") or 0) for _, a in pairs)
        wrap_n = sum((a.get("shortWrapped") or 0) for _, a in pairs)
        bad20 = ["%s %d/%d" % (a.get("title"), a["shortWrapped"], a["shortCells"])
                 for _, a in pairs if (a.get("shortWrapped") or 0) > 0]
        if short_n == 0:
            verdict(rows, "P20", "T-01 短字段折行", "分母 0（无短字段格）", "折行 0 处", "SKIP",
                    "短字段格 0 个：分母为 0 时「0 处折行」不等于达标")
        else:
            verdict(rows, "P20", "T-01 短字段折行", "折行 %d/%d" % (wrap_n, short_n), "折行 0 处",
                    "PASS" if wrap_n == 0 else "FAIL",
                    "分母 = 含 Tag/Button 的格 ∪ 整格文本 ≤6 全角字的格；量承载文本的最内层元素"
                    "（Tag/Button/文本节点）的 Range 行盒数，>1 即折行"
                    + ("；折行列：" + "，".join(bad20) if bad20 else ""))

    # ---- P21 T-02 长文本必须三选一（ellipsis / wrap+maxLines:2 / 移出表格）
    if not t0 or not au:
        verdict(rows, "P21", "T-02 长文本出口", "—", "未声明出口列 0", "SKIP", "无表格")
    else:
        naked = [(c, a) for c, a in pairs
                 if not c.get("ellipsis") and not c.get("wrap") and not c.get("maxLines")
                 and (a.get("multiLong") or 0) > 0]
        vals = "，".join("%s %d 格" % (a.get("title"), a["multiLong"]) for _, a in naked)
        verdict(rows, "P21", "T-02 长文本出口", "未声明出口且 ≥2 行：%d 列" % len(naked),
                "0 列", "PASS" if not naked else "FAIL",
                "三选一 = ellipsis / wrap:true+maxLines:2 / 移出表格；"
                "「靠浏览器默认换行」是本文件唯一明确禁止的排版方式"
                + ("；命中：" + vals if vals else ""))

    # ---- P22 T-03 行数上限（≤2 行，且格高不超过 2 行）
    if not t0 or not au:
        verdict(rows, "P22", "T-03 行数上限", "—", "≤2 行", "SKIP", "无表格")
    else:
        over_cols = [(c, a) for c, a in pairs if (a.get("overCells") or 0) > 0]
        over_n = sum((a.get("overCells") or 0) for _, a in over_cols)
        worst = max([(a.get("maxLines") or 0) for _, a in pairs] or [0])
        det = "，".join("%s 最长 %d 行 / 格高 %s" % (a.get("title"), a.get("maxLines") or 0,
                                                   fmt(a.get("maxTdH")))
                       for _, a in over_cols[:4])
        verdict(rows, "P22", "T-03 行数上限", "超限 %d 格 / %d 列（最长 %d 行）"
                % (over_n, len(over_cols), worst), "≤2 行", "PASS" if over_n == 0 else "FAIL",
                "行盒数 >2，或格高 > 行高×2 + 上下 padding + 1；本页最长 %d 行" % worst
                + ("；超限列：" + det if det else ""))

    # ---- P23 T-04 表头不得被裁（0 容忍，分母 = 表头 ≤6 全角字的列，按档位分列打印）
    #
    # **锚点 = 裁切盒**（computed overflow-x ∈ {hidden, clip}），不是「承载文本的最内层元素」。
    # 后者会恒绿：文本包一层 <span> 时 span 是 inline，clientWidth/scrollWidth 恒 0/0，
    # `0 > 0+1` 恒假，真被裁的 th 一次都没被看。见探针 clippingBox() 的注释。
    if not t0 or not au:
        verdict(rows, "P23", "T-04 表头被裁", "—", "被裁 0 列", "SKIP", "无表格")
    else:
        anchors = {}
        for _, a in pairs:
            anchors[a.get("hdrAnchor") or "none"] = anchors.get(a.get("hdrAnchor") or "none", 0) + 1
        anchor_txt = "锚点=clippingBox（%s）" % "，".join(
            "%s %d 列" % (k, v) for k, v in sorted(anchors.items()))
        # 分母排除两类：① 空表头（rowSelection / radio 插进来的槽位列，本来就没有字）；
        # ② 没有裁切盒的列（hdrClip is None）—— 那是「本条不适用」，不是「量过了没裁」。
        den = [(c, a) for c, a in pairs
               if 0 < (a.get("hdrUnits") or 0) <= SHORT_FIELD_MAX_UNITS
               and a.get("hdrClip") is not None]
        clip = [(c, a) for c, a in den if a.get("hdrClip")]
        # 三类排除**分别计数、不加总**（team-lead 裁定）：合成一个「另有 N 列」时，看报告的人
        # 分不清「判据放过了它」还是「它根本不适用」。三类各自说出原因：
        #   ① 表头 >6 全角字 —— 那类列的长表头归 T-03 + ellipsisTitle，不是 T-04 的活；
        #   ② 空表头（rowSelection / radio 插进来的槽位）—— 永远不可能红，必然为绿的分母没有意义；
        #   ③ 无裁切盒（没有 overflow-x:hidden/clip）—— 「量过了没裁」与「没有可量的盒子」必须分开。
        # 三个数都必须出现在分母行里：「0/9」与「0/10」的差别没人看得见，下次改成 0/10 也没人发现。
        no_hdr = sum(1 for _, a in pairs if not (a.get("hdrUnits") or 0) > 0)
        long_hdr = sum(1 for _, a in pairs if (a.get("hdrUnits") or 0) > SHORT_FIELD_MAX_UNITS)
        no_box = sum(1 for _, a in pairs
                     if (a.get("hdrUnits") or 0) > 0 and a.get("hdrClip") is None)
        excl = ("；另有 %d 列表头 >%g 全角字、%d 列空表头、%d 列无裁切盒，不入分母"
                % (long_hdr, SHORT_FIELD_MAX_UNITS, no_hdr, no_box))
        det = "，".join("%s 可用 %s / 滚动 %s / 文字 %s"
                       % (a.get("title"), fmt(a.get("hdrClientW")), fmt(a.get("hdrScrollW")),
                          fmt(a.get("hdrTextW")))
                       for _, a in clip)
        if not den:
            verdict(rows, "P23", "T-04 表头被裁", "分母 0（无可量的裁切盒）@%s" % fmt(cw),
                    "被裁 0 列", "SKIP",
                    anchor_txt + "；没有 overflow:hidden/clip 的表头盒 —— 那一档根本不会「裁切」"
                    "（文字会溢出可见），本条不适用，不是达标" + excl)
        else:
            verdict(rows, "P23", "T-04 表头被裁",
                    "被裁 %d/%d 列@%s%s" % (len(clip), len(den), fmt(cw), excl),
                    "被裁 0 列", "PASS" if not clip else "FAIL",
                    anchor_txt + "；分母 = 表头文字 1~%g 全角字且**有裁切盒**的列；"
                    "被裁 = 裁切盒 scrollWidth > clientWidth + 1（nowrap 只保证不折行，不保证放得下）"
                    % SHORT_FIELD_MAX_UNITS + ("；被裁列：" + det if det else ""))

    # ---- P24 W-01 列宽下限（声明宽 ≥ needW，量实测不量字数）
    #
    # **分母 = 短列**（整格 ≤6 全角字的格，含 Tag/Button 格）。声明了出口的长文本列
    # （`ellipsis` / `wrap+maxLines`）**出分母** —— needW 的语义是「放得下一整条不可断的内容」，
    # 一旦声明了省略号，语义就变成「能放多少放多少，剩下的悬停看」，拿它要求该列显示全文
    # 等于和 T-02 互相取消。CAPA 的 `事实陈述` 就是这条：needW=532 > 整表 866，**不可满足**，
    # 那不是「该加宽 202px」的指令，是「该列该走 T-02 三选一」的信号。
    # 未声明出口的长文本列同样出分母：那是 T-02 的活（`未声明出口且 ≥2 行` 已经在抓）。
    # 出分母的列**仍照打 needW/声明/渲染**（诊断不缩水），只是不计入分母。
    def _exit_kind(c):
        if c.get("ellipsis"):
            return "ellipsis"
        if c.get("wrap") and c.get("maxLines"):
            return "wrap+maxLines"
        return None

    def _breakable(t):
        """这列的值有没有**可断点**（有 = 宽度需求由内容决定，归 T-02/T-03）。

        只有两条，别做 NLP：① 空格分隔的词 ≥3 个（`GB/T 2828.1 一般检验水平 II`）；
        ② 连续 CJK > 6 字（`高精度贴片电阻`、`不合格（潜在）事实陈述`）。
        其余一律当 **token**（`IQC-20261018-0342`、日期、序号、状态、Tag 文本）——
        token 断了就是错的，「整条必须放得下」这句话才对它们成立，那正是 needW 的定义域。

        **判的是值文本本身，不是渲染行数**。拿行数当分母依据是循环定义：行数由**被修的列宽**
        决定 —— 列越窄越折行，越会被判成长文本列而**出分母**，于是「越坏的列越免检」。
        这与 `Σ col.offsetWidth ≡ 表宽` 是同一族毛病：拿结果当判据的输入。
        """
        if not t:
            return False
        if len([w for w in re.split(r"\s+", t.strip()) if w]) >= 3:
            return True
        run = best = 0
        for ch in t:
            if "\u4e00" <= ch <= "\u9fff":
                run += 1
                if run > best:
                    best = run
            else:
                run = 0
        return best > 6

    p24_den, p24_out_decl, p24_out_broken = [], [], []
    for c, a in pairs:
        if c.get("declW") is None:
            continue
        ek = _exit_kind(c)
        if ek:
            p24_out_decl.append((str(c.get("title")), ek))
        elif _breakable(a.get("longest")):
            p24_out_broken.append(str(c.get("title")))
        else:
            p24_den.append((c, a))
    p24_excl = ""
    if p24_out_decl or p24_out_broken:
        parts = []
        if p24_out_decl:
            parts.append("另有 %d 列声明了出口（%s），不入分母" % (
                len(p24_out_decl),
                "、".join("%s %s" % (t, k) for t, k in p24_out_decl[:4])))
        if p24_out_broken:
            parts.append("另有 %d 列值可断（长文本，归 T-02/T-03：%s），不入分母" % (
                len(p24_out_broken), "、".join(p24_out_broken[:4])))
        p24_excl = "；".join(parts)

    if not t0 or not au:
        verdict(rows, "P24", "W-01 列宽下限", "—", "声明 ≥ needW", "SKIP", "无表格")
    elif not w00_ok:
        # W-03：四条不变量有顺序。1/2 不成立时（fixed 或声明率），3/4 的读数不作判决依据。
        # 判 FAIL 而不是 SKIP —— 与 P18 同一处理：SKIP 会让存量产物在这条上免检。
        # 但**声明侧读数必须照打**：声明值在 JSON 里，与布局无关，这一半永远可判。
        # cause 写明是哪一条前置（只写 prereq 等于没写原因）。
        low_d, pass_d = [], 0
        for c, a in p24_den:
            need = w01_need(c, a)
            if c["declW"] + 1e-6 < need:
                low_d.append((str(c.get("title")), c["declW"], need))
            else:
                pass_d += 1
        tight_d = min(p24_den, key=lambda p: ((p[0].get("declW") or 1e9) - w01_need(p[0], p[1])),
                      default=None)
        side = "声明侧 %d/%d 列达标" % (pass_d, len(p24_den))
        if tight_d:
            side += "（余量最小 %s %s/%s）" % (
                tight_d[0].get("title"), fmt(tight_d[0].get("declW")),
                fmt(w01_need(tight_d[0], tight_d[1])))
        if low_d:
            side += "，未达标：" + "，".join("%s %s<%s" % t for t in low_d[:4])
        verdict(rows, "P24", "W-01 列宽下限",
                "前置不成立 %s（%s）" % (side, "cause=prereq:W-00"), "声明 ≥ needW", "FAIL",
                "cause=prereq:W-00：W-03 顺序要求先 W-00（fixed + 每列 width）再谈列宽够不够 —— "
                "fixed 缺失时渲染 ≠ 声明，把差归因成「列宽不足」是错误归因；但让它闭嘴就是免检。"
                "声明值在 JSON 里、与布局无关，所以这一半照判照打。" + p24_excl
                + "；三数（needW/声明/渲染）全列诊断：" + needw_digest(pairs, n=len(pairs)))
    elif not p24_den:
        verdict(rows, "P24", "W-01 列宽下限", "分母 0（无可比的短列）", "声明 ≥ needW", "SKIP",
                "所有列都声明了出口或是长文本列 —— 本条的语义（放得下一整条不可断的内容）"
                "对它们不成立，归 T-02/T-03" + ("；" + p24_excl if p24_excl else "")
                + "；三数全列诊断：" + needw_digest(pairs, n=len(pairs)))
    else:
        low, pct_cols = [], []
        for c, a in p24_den:
            need = w01_need(c, a)
            if c["declW"] + 1e-6 < need:
                low.append((str(c.get("title")), c["declW"], need))
        pct_cols = [str(c.get("title")) for c, _ in pairs if c.get("declPct") is not None]
        tight = min(p24_den, key=lambda p: ((p[0].get("declW") or 1e9) - w01_need(p[0], p[1])))
        verdict(rows, "P24", "W-01 列宽下限",
                "低于下限 %d/%d 列%s" % (len(low), len(p24_den),
                                        ("；" + p24_excl) if p24_excl else ""),
                "声明 ≥ needW", "PASS" if not low else "FAIL",
                "needW = ceil(实测文本宽) + 24 + (Tag 16) + (可排序 20)，量的是**最内层元素自身字号**"
                "（Tag 12px / td 14px）—— 用单元格字号代算会让同一条判据随机红绿；"
                "分母 = 未声明出口且**值不可断**的列（token：单号/日期/序号/状态/Tag 文本），"
                "值可断的长文本列与声明了出口的列归 T-02/T-03；每列另守 ≥48。"
                "余量最小：%s 声明 %s / needW %s"
                % (tight[0].get("title"), fmt(tight[0].get("declW")),
                   fmt(w01_need(tight[0], tight[1])))
                + ("；低于下限：" + "，".join("%s 声明 %s < needW %s" % t for t in low[:5])
                   if low else "")
                + ("；百分比宽（与 px 不可加）：" + "、".join(pct_cols[:6]) if pct_cols else "")
                + "；三数全列诊断：" + needw_digest(pairs, n=len(pairs)))

    # ---- P25 W-02 声明必须等于渲染（逐列 ±2；主判据，不是 Σ）
    if not t0 or not au:
        verdict(rows, "P25", "W-02 声明=渲染", "—", "逐列 |差| ≤2", "SKIP", "无表格")
    else:
        k = 1.0
        all_px = bool(cols) and all(c.get("declW") is not None for c in cols)
        if (all_px and layout == "fixed" and (props.get("sumW") or 0) > 0
                and (t0.get("wrapClientW") or 0) > 0):
            k = float(t0["wrapClientW"]) / float(props["sumW"])
        # 有列没声明宽（或混了百分比宽）时不做比例换算：那时表宽要在「无宽列」与
        # 「有宽列」之间分配，k = 表宽/Σ声明 不再是那个比例，换算出来的偏差是假的。
        bad25, cmp25 = [], 0
        for c, a in pairs:
            if c.get("declW") is None or a.get("thW") is None:
                continue
            cmp25 += 1
            dev = abs(a["thW"] - c["declW"] * k)
            if dev > COL_W_TOL:
                bad25.append((str(c.get("title")), c["declW"], a["thW"], dev))
        no_decl = [str(c.get("title")) for c, _ in pairs if c.get("declW") is None]
        verdict(rows, "P25", "W-02 声明=渲染",
                "可比 %d 列，超差 %d 列（k=%s）" % (cmp25, len(bad25), "%.3f" % k),
                "逐列 |差| ≤%d" % COL_W_TOL, "PASS" if (cmp25 and not bad25) else "FAIL",
                "**语义是「每列是否按同一个比例缩放」，不是「允许偏差 ≤2」**。"
                "k = 表宽 / Σ声明：fixed 且 Σ < 表宽时浏览器把差值按比例摊给各列（1026 档 k=1.185）。"
                "@866 档 Σ=表宽 → k=1.000，逐列比较与原式**逐字节等价**（这是「没有放宽」的唯一证据）。"
                "k 的合法性（Σ 本身是否合理）**不归本条**，归 Σ 判据 —— 8 列全声明 100、Σ=800 时"
                "本条也应当 PASS。Σ 只作诊断，不作 PASS 依据 —— fixed 下 Σ渲染 ≡ 表宽 恒成立，"
                "**比 Σ 等于自证；同理也不能顺手判 abs(Σ声明×k − 表宽)**（k 由它推出，恒真）"
                + ("；无声明宽（未参与比较）：" + "、".join(no_decl[:6]) if no_decl else "")
                + ("；超差列：" + "，".join("%s 声明 %s 渲染 %s（差 %s）"
                                         % (t_, fmt(d), fmt(r), fmt(round(dev, 1)))
                                         for t_, d, r, dev in bad25[:5]) if bad25 else ""))

    return rows


# ------------------------------------------------------------------ props 侧
def parse_col_width(raw):
    """把 `columns[].width` 解成一个可判的数——与容器 `colWidthStyle()` 同一套口径。

    容器那边（`assets/container/index.html` 的 `colWidthStyle`）：纯数字串补 `px`，
    已带单位（`150px` / `20%`）原样写进 style。**所以 `"52px"` 和 `52` 在渲染上等价**，
    判据读 JSON 时也必须等价，否则「写没写」这件事会取决于写法而不是内容。

    旧实现 `float(w)` 对 `"52px"` 抛 ValueError → 记成「未声明」：CAPA 的 11/11 全声明
    被报成 `0/9 = 0%`，并且把病因从「没锁 table-layout」误诊成「没写列宽」。这是**量具 bug**，
    不是口径变更 —— 阈值（80% 与 fixed）一个字没动。

    返回 (px 值 or None, 百分数 or None, 原始单位串)。百分比单独返回而不并进 px：
    `20%` 与 `150px` 不能相加，Σ 预算（P17）只认 px 列，声明率两列都算「声明了」。
    """
    if raw is None:
        return None, None, None
    s = str(raw).strip()
    if not s:
        return None, None, None
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(px|%)?", s, re.I)
    if not m:
        return None, None, s            # 认不出的单位（em/vw/calc…）：既不算 px 也不算 %
    v = float(m.group(1))
    unit = (m.group(2) or "px").lower()
    if unit == "%":
        return None, v, "%"
    return v, None, "px"


def resolve_list_table(page):
    """解析「这一页的主表」：Content 直属优先，找不到再退到 MasterDetail 里的第一张。

    **与 `is_work_list_page()` 拆开的理由（幻神 v3 裁定）**：两者回答的是两个问题。
    - 本函数 = 「哪张表是主表」——**任何页**都该能答（详情页也有主表），只用于取列宽/分页等原始量；
    - `is_work_list_page()` = 「这算不算作业型列表页」——**形态类判据的适用范围**，定义不变。

    混在一起的时候，为了让 CAPA 的 `page-capa-list`（主表在 `MasterDetail` 里）能判，
    只能去放宽「列表页」的定义，那会连带改掉 P2/P11/P13 的适用范围 —— 改判据去迁就一张样本。
    拆开后：门槛/口径一个字不动，只是「量哪张表」多了一个入口。

    返回 (node, source)，source ∈ content-direct / master-detail / none。source 会打进
    P7 的 note —— 量的不是 Content 直属表时必须写明，否则「量到了」和「量的是哪张」脱钩。
    """
    ts = content_direct_tables(page)
    if ts:
        return ts[0], "content-direct"
    mds = md_tables(page)
    if mds:
        return mds[0], "master-detail"
    return None, "none"


def props_of(page, dom):
    """从 JSON 读那些「DOM 量不到 / 量了会被自证」的东西。"""
    t, tsrc = resolve_list_table(page)
    tp = (t or {}).get("props") or {}

    # 列宽：读声明值。渲染后的 offsetWidth 之和恒等于表宽（fixed 布局按比例缩放），
    # 用它验预算等于让判据自证——必须读 JSON 里写的 width。
    cols = []
    for c in (tp.get("columns") or []):
        px, pct, raw = parse_col_width(c.get("width"))
        cols.append({"title": c.get("title"), "declW": px, "declPct": pct,
                     "declRaw": raw if (px is None and pct is None) else None,
                     "ellipsis": bool(c.get("ellipsis") or c.get("ellipsisCol")),
                     "wrap": bool(c.get("wrap")), "maxLines": c.get("maxLines"),
                     "type": c.get("type"), "align": c.get("align")})
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
        # Σ 预算只加 px 列：`20%` 与 `150px` 不可加（见 parse_col_width）
        "sumW": sum(c["declW"] for c in cols if c["declW"]) if cols else None,
        "declaredPct": [c for c in cols if c["declPct"] is not None],
        "unparsableW": [c for c in cols if c.get("declRaw")],
        "tableSource": tsrc,
        "ellipsisCols": [c for c in cols if c["ellipsis"]],
        "total": total, "pageSize": page_size,
        "drawerCount": len(drawers), "drawerW": dr_w, "mdCount": len(md),
        "tableProps": tp,
    }


# ------------------------------------------------------------------ 报告
def render_case(name, page, dom_by_vp, rows_by_vp, why="—", cand_ids=None):
    all_rows = []
    for vw, rows in rows_by_vp.items():
        all_rows.extend(rows)
    p = sum(1 for r in all_rows if r["status"] == "PASS")
    f = sum(1 for r in all_rows if r["status"] == "FAIL")
    s = sum(1 for r in all_rows if r["status"] == "SKIP")
    inc = sum(1 for r in all_rows if r["status"] == "INCOMPLETE")
    # 出现过的 SKIP 判据 id（去重）—— 交给 main 做白名单比对（V13）
    skip_ids = sorted(set(r["id"] for r in all_rows if r["status"] == "SKIP"))
    # 其中**没有正当条件**的那些：V13 只对这批人说「你在没有正当理由的情况下没跑」。
    # 条件化白名单（P2a/P2b）看的是行里的条件文本，不只看 id —— 见 skip_allowed()。
    bad_skip = sorted(set(r["id"] for r in all_rows
                          if r["status"] == "SKIP" and not skip_allowed(r)))
    cand_ids = cand_ids or []
    print("\n" + "=" * 78)
    # 「判了哪页」必须在这一行：同一份产物判不同页会得到不同 FAIL 集（CAPA 实测 19 vs 21），
    # 把页 id 藏进某条判据的 note 里，读者会以为两次跑的是同一件事。
    print("CASE %s | page %s (%s) | 判页依据：%s | 两档视口 | retries=%d"
          % (name, page.get("id"), page.get("name"), why,
             sum(d.get("_retry", 0) for d in dom_by_vp.values())))
    unjudged = [x for x in cand_ids if x != page.get("id")]
    if unjudged:
        print("  另有 %d 张列表页候选**本轮未判**：%s —— 单页模式下结论只对 %s 成立"
              "（要逐页判用 --all-pages）"
              % (len(unjudged), ", ".join(unjudged), page.get("id")))
    print("  条数口径：P1–P19 共 20 条（P3 拆 P3a/P3b）；I-09 起新增 P20–P25 承载 "
          "T-01/T-02/T-03/T-04/W-01/W-02，第三阶段新增 S-01/S-02a/S-02b 承载 `12` §S-01/§S-02，"
          "另有 V-01（三态，产品态闭合）；每视口 %d 行"
          % len(next(iter(rows_by_vp.values()), [])))
    for vw, rows in rows_by_vp.items():
        d = dom_by_vp[vw]
        print("  -- %dx%d  内容宽 %s  pane %s（默认 %s）  列 %s"
              % (vw, d.get("vh"), fmt(d.get("contentBoxW")), fmt(d.get("paneW")),
                 fmt(d.get("paneDefaultW")), d.get("tableCount")))
        for r in rows:
            mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP",
                    "INCOMPLETE": "INC!"}.get(r["status"], r["status"])
            print("     %-4s %-28s 现值 %-30s 阈值 %-22s %s"
                  % (r["id"], r["title"], r["value"], r["threshold"], mark))
            if r["note"]:
                print("          ↳ %s" % r["note"])
    print("  PASS=%d FAIL=%d SKIP=%d%s（SKIP 不计为绿；本页单列，不与其它页合并）"
          % (p, f, s, (" INCOMPLETE=%d（量具不可信或夹具造少，既不是绿也不是红）" % inc) if inc else ""))
    # N-e 只在这里打一行诊断：**不判红、不占编号**（理由见 v01_cross 的 docstring）
    diag = v01_cross(rows_by_vp)
    if diag:
        print("  " + diag)
    if skip_ids:
        print("  SKIP 判据 = [%s]" % ",".join(skip_ids))
    return p, f, s, skip_ids, bad_skip


def run_one(chrome, json_path, page_id=None, keep=False, why=None):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    page, picked_why, cand_ids = pick_page_ex(data, page_id)
    why = why or picked_why
    if page is None:
        print("\nCASE %s —— SKIP（无列表页候选；判页依据：%s）"
              % (Path(json_path).name, why))
        return 0, 0, 0, [], set(), set(), []
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
        # N-e 已降为诊断（在 render_case 里打），这里不再有两档判定
        # V8 的比对单位是「判据@视口」：同一判据只在一档红、另一档绿，本身就是要看的信号。
        fails = set("%s@%d" % (r["id"], w)
                    for w, rs in rows_by_vp.items() for r in rs if r["status"] == "FAIL")
        # INCOMPLETE 必须单独回传：它既不是绿也不是红，合并进 PASS 就是静默绿。
        # 回传的是**判据 id 列表**（不是条数）：结论段要打「几行 + 去重后的哪几条」，
        # 只回条数时「2 判据 × 2 档 = 4 行」会被读成「4 条判据」（XX-047 的起因）。
        inc = [r["id"] for rs in rows_by_vp.values() for r in rs if r["status"] == "INCOMPLETE"]
        return render_case(Path(json_path).name, page, dom_by_vp, rows_by_vp,
                           why, cand_ids) + (fails, inc)
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


def main_all_pages(chrome, files, keep=False):
    """逐页全判（`--all-pages`）：**每页单列 PASS/FAIL/SKIP，绝不合并成一个总数**。

    为什么必须有这个模式：同一份产物判不同页会得到不同 FAIL 集（CAPA 实测 19 vs 21），
    而两页的 PASS 总数**碰巧都是 11** —— 合成一个 TOTAL 时这个差异会消失。
    「合并后看着一样」正是上一轮骗过人的地方，所以这里连一行跨页合计都不给。
    """
    any_fail = False
    bad_skip = set()
    for f in files:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        cands = page_candidates(data)
        if not cands:
            print("\nCASE %s —— SKIP（无列表页候选）" % Path(f).name)
            continue
        print("\n" + "#" * 78)
        print("# FILE %s —— 列表页候选 %d 张：逐页判，计数分行不合并"
              % (Path(f).name, len(cands)))
        got = []
        for page, kind in cands:
            p, fl, s, sk, _bad, _fs, inc = run_one(chrome, f, page.get("id"), keep,
                                        why="逐页全判（--all-pages）")
            got.append((page.get("id"), kind, p, fl, s, len(inc)))
            bad_skip.update(_bad)
            any_fail = any_fail or fl > 0 or bool(inc)
        print("\n  ---- 分页小计（%s，**不合并**）----" % Path(f).name)
        print("  %-26s %-16s %6s %6s %6s %6s" % ("page", "kind", "PASS", "FAIL", "SKIP", "INC"))
        for pid, kind, p, fl, s, inc in got:
            print("  %-26s %-16s %6d %6d %6d %6d" % (pid, kind, p, fl, s, inc))

    print("\n" + "-" * 78)
    print("TOTAL 不合并：上面每个 page 一行就是结论；跨页相加会把 19/21 这类差异抹平")
    # bad_skip 已经剔除了「有条件豁免」的那些（P8/P13/P17 + 带条件的 P2a/P2b），
    # 这里再减一次白名单是多余的，且会掩盖 skip_allowed() 的判断 —— 只排序。
    bad = sorted(bad_skip)
    if bad:
        print("SKIP-OUT-OF-WHITELIST=[%s]  白名单只允许 %s"
              % (",".join(bad), ",".join(SKIP_WHITELIST)))
        print("RESULT INCOMPLETE  —— 有判据在没有正当理由的情况下没跑")
        return 1
    if any_fail:
        print("RESULT FAIL  —— 至少一页有 FAIL（逐页看上面）")
        return 1
    print("RESULT PASS")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="P1-P19 形态与密度判据")
    ap.add_argument("files", nargs="*", help="产物 JSON（默认：assets/examples 里含列表页的示例）")
    ap.add_argument("--page", help="指定 pageId")
    ap.add_argument("--all-pages", action="store_true",
                    help="逐页判所有列表页候选；**分页单列计数，不合并**")
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

    if args.all_pages:
        return main_all_pages(chrome, files, args.keep)

    tp = tf = ts = 0
    inc_ids = []
    skip_seen = set()
    bad_seen = set()
    fails_by_file = {}
    for f in files:
        try:
            p, fl, s, sk, bad_one, fs, inc = run_one(chrome, f, args.page, args.keep)
        except EnvError as ex:
            print("\nCASE %s —— ENV: %s" % (Path(f).name, ex))
            return 2
        tp += p
        tf += fl
        ts += s
        inc_ids.extend(inc)
        skip_seen.update(sk)
        bad_seen.update(bad_one)
        fails_by_file[Path(f).name] = fs

    print("\n" + "-" * 78)
    print("TOTAL PASS=%d FAIL=%d SKIP=%d%s"
          % (tp, tf, ts, (" INCOMPLETE=%d" % len(inc_ids)) if inc_ids else ""))

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
    bad_skip = sorted(bad_seen)
    if bad_skip:
        print("SKIP-OUT-OF-WHITELIST=[%s]  白名单只允许 %s（另：P2a/P2b 与 S-02a/S-02b 走"
              "「值里带条件」的条件式放行）"
              % (",".join(bad_skip), ",".join(SKIP_WHITELIST)))
    return conclude(tf, inc_ids, bad_skip, v8_bad, v8_missing)


def conclude(tf, inc_ids, bad_skip, v8_bad, v8_missing):
    """结论段：**三条事实先全部算完，再决定第一句说什么**（XX-047）。

    原来的写法是三级早退（`bad_skip` → `tinc` → `v8_bad` 依次 `return 1`），后果是
    **只要有一条 INCOMPLETE，V8 的比对结论就永远进不了结论段** —— example-05 造少那段时间
    正是如此：「红的是不是该红的那几条」这个唯一有价值的结论被一句 INCOMPLETE 压掉了。
    现在按优先级给第一句（判据没跑 > 量具不可信 > V8 不符），**其余事实同段打出**。

    两个数都要打（XX-047）：`行数` 与**去重后的判据名**。只打 `%d 条` 时，
    「2 判据 × 2 档 = 4 行」会被读成「4 条判据」，进而被当成「P2b 的分母也是 14」的依据
    （实际 `TARGET_ROWS_REVIEW = {1440: 9, 1600: 12}`，分母由调用点各自传）。

    返回退出码：非 0 表示这一轮不能当"通过"。
    """
    n_inc, ids = len(inc_ids), sorted(set(inc_ids))
    inc_s = ("%d 行 INCOMPLETE（%s）" % (n_inc, "、".join(ids))) if n_inc else ""
    v8_s = ""
    if v8_bad:
        v8_s = "V8 FAIL 集与期望名单不符"
    elif v8_missing:
        v8_s = "V8 有 %d 个名单文件本轮没跑（没比对不等于比过了）" % v8_missing
    facts = [x for x in (inc_s, v8_s) if x]

    if bad_skip:
        line = "RESULT INCOMPLETE  —— 有判据在没有正当理由的情况下没跑（%s），" \
               "这不是「产物达标」，是「判据没判」" % "、".join(bad_skip)
    elif n_inc:
        # 量具自己不可信（父节点不可见 / 加数口径不一致 / 导航宽越界），或夹具造少。
        # 落成 PASS 是静默绿，落成 FAIL 是把工具 bug 算到产物头上 —— 只能报 INCOMPLETE 并退非 0。
        line = "RESULT INCOMPLETE  —— 量具不可信，或夹具造少（INSUFFICIENT_ROWS）；" \
               "先修这一半，再谈产物达不达标"
    elif v8_bad or v8_missing:
        if v8_bad and tf == 0:
            line = "RESULT INCOMPLETE  —— V8 的 FAIL 集与期望名单不符"
        else:
            line = "RESULT FAIL  —— V8 的 FAIL 集与期望名单不符：" \
                   "FAIL 总数只说明「红了几条」，说明不了「红的是不是该红的那几条」"
    else:
        print("RESULT %s" % ("PASS" if tf == 0 else "FAIL"))
        return 0 if tf == 0 else 1
    # 事实必须落在**同一段**：第一句说明结论，后面的分号说明"还有哪些事没被这条结论覆盖"。
    print(line + ("；" + "；".join(facts) if facts else ""))
    if bad_skip:
        print("  白名单只允许 %s —— 能 SKIP 的只有「这条判据当前不适用」，不是「这条判据我判不了」"
              % ",".join(SKIP_WHITELIST))
    if v8_bad:
        print("  V8 差异见上方「少红 / 多红」两行：那才是「红的是不是该红的那几条」的答案")
    return 1


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
    {"name": "P9_row_high", "kind": "css", "want": ["P9"],
     "allow": ["P2a", "P2b", "P18", "P20", "P21", "P22"],
     "allowWhy": "行高变大 → 一屏行数必然减少（P2a/P2b）；white-space:normal 让短字段折行（P20）、"
                 "长文本折成 3 行（P21/P22），且不再横向溢出 → 配了 ellipsis 的两列变成「装饰」，"
                 "P18 的集合相等必然不成立。全部是这个注入的真实后果，不是判据重叠",
     "payload": ".ant-table td{white-space:normal!important;padding-top:16px!important;padding-bottom:16px!important}"},
    {"name": "P10_sticky_off", "kind": "css", "want": ["P10"],
     "payload": ".ant-table th{position:static!important}"},
    # ---- js 类（在 measure 前塞元素）
    {"name": "P1_stat_back", "kind": "js", "want": ["P1"], "allow": ["P16", "P2b", "P19", "S-01"],
     # 允许的连带都是该注入的**真实后果**，不是「P1 与它们在测同一件事」：
     #   P16/P2b —— 统计卡占掉首屏高度，表格下移、分页被挤出屏；
     #   P19     —— 统计卡自带 24px 数值，页内字号从 3 档变 4 档 —— 这正是「列表页不许放
     #              统计卡」的第二条理由（第一条是抢高度），判据把它一起抓出来是对的；
     #   S-01    —— 同上，24 不在 {18,14,12} 里，集合判据也红。它与 P19 是同一批元素上的
     #              已知重叠（S-01 判集合、P19 只数档数），不是「P1 与 S-01 在测一件事」。
     # 若这些连带不出现，反而说明 P2b/P16/P19/S-01 没量到真实影响。
     "allowWhy": "统计卡占首屏高度（P16/P2b），并自带 24px 数值把字号推到 4 档（P19/S-01）—— 都是同一注入的真实后果",
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
    {"name": "P14_tag_2color", "kind": "js", "want": ["P14"], "allow": ["P18", "P20", "P24"],
     "allowWhy": "往首个单元格里塞两个标签：① 把它撑溢出 →「真溢出列集合」多一列没配 ellipsis 的"
                 "（P18 集合相等不成立）；② 序号列的 needW 从 41 涨到 2 个 Tag 的宽度 → 54 不再够（P24）；"
                 "③ 两个 Tag 在 54 宽的列里换行（P20）。三条都是这个注入的真实后果",
     "payload": "(function(){var tr=document.querySelector('#protoCanvas .ant-table tbody tr');if(!tr)return;"
                "var td=tr.querySelector('td');if(!td)return;"
                "for(var i=0;i<2;i++){var t=document.createElement('span');"
                "t.className='ant-tag red';t.textContent='加急';td.appendChild(t);}})();"},
    # ---- json 类（改 props 再渲染）
    {"name": "P13_page_size_10", "kind": "json", "want": ["P13"],
     "payload": lambda p: _mutate_table(p, lambda tp: _set_pg(tp, 10))},
    {"name": "P17_drop_one_width", "kind": "json", "want": ["P17"], "allow": ["P25"],
     "allowWhy": "摘掉一列 width 后，fixed 会把表宽在没有声明宽的列与有声明宽的列之间重分配，"
                 "「声明=渲染」对剩下的列必然不成立（P25 逐列脱钩）—— 这是同一个改动的另一面",
     "payload": lambda p: _mutate_table(p, lambda tp: _drop_width(tp))},
    {"name": "P18_ellipsis_all", "kind": "json", "want": ["P18"],
     "payload": lambda p: _mutate_table(p, lambda tp: _ellipsis_all(tp))},
    # ---- I-09 第一阶段新增：T-01 / T-04 / W-01 / W-02
    # T-01：把 Tag 的可用内宽压到 28px → 「不合格」三个字必折成两行。
    # 用 CSS 而不是改列宽：改列宽会连带 Σ（P17 红）、W-01（声明 < needW）、W-02（渲染≠声明），
    # 那样「多翻」来自注入手段而不是判据重叠，自证就说不清是哪条抓到的。
    # 注意不能只写 max-width：容器的 `.ant-tag` 是 `display:inline-flex;height:22px;line-height:1`，
    # 压窄了它只会**裁掉**文字、不会换行（折行要有可换的行盒）。要先把行盒打开。
    {"name": "T01_tag_wrap", "kind": "css", "want": ["P20"],
     "allow": ["P9", "P22", "P2a", "P2b"],
     "allowWhy": "Tag 折成两行 → 该列行高从 34 涨到 46（P9 极差、P22 格高），"
                 "一屏可见行数随之减少（P2a/P2b）。行高与一屏行数是折行的**必然**后果，"
                 "不是「T-01 与它们在测同一件事」",
     "payload": ".ant-table td .ant-tag{display:inline-block!important;height:auto!important;"
                "white-space:normal!important;line-height:18px!important;max-width:26px!important}"},
    # T-04：教材的「序号」在 866 档是 54（改前 48 被裁 4px）。改回 48 就必红 ——
    # 这是这条判据**现成的负例**，不需要另造产物。
    # 连带 P17（Σ 866→860）与 P24（48 < needW 52）是改列宽的真实后果：
    # 列宽动了，预算闭合与下限当然跟着动，那不是判据重叠。
    {"name": "T04_hdr_clip", "kind": "json", "want": ["P23"],
     "allow": ["P17", "P24"],
     "allowWhy": "序号 54→48 让 Σ 从 866 掉到 860（P17 预算闭合）且 48 < needW 52（P24）—— "
                 "改列宽必然连带动预算与下限，二者不是与 T-04 在测同一件事",
     "payload": lambda p: _mutate_table(p, lambda tp: _set_col_width(tp, "序号", 48))},
    # W-01：「状态」列声明 80、Tag 实际需要 78。压到 76 就低于下限（不折行，只差 2px）——
    # 用它证明这条判据量的是「声明 vs needW」，不是「屏幕上看不看得出折行」。
    {"name": "W01_below_need", "kind": "json", "want": ["P24"], "allow": ["P17", "P18"],
     "allowWhy": "80→76 让 Σ 从 866 掉到 862（P17 预算闭合红）；列窄到 76 后 Tag 撑出单元格，"
                 "「真溢出列集合」多一列没配 ellipsis 的（P18 集合相等红）—— 都是改宽的直接后果",
     "payload": lambda p: _mutate_table(p, lambda tp: _set_col_width(tp, "状态", 76))},
    # W-02：只改 DOM 上的列宽（不动 JSON 声明）→ 声明与渲染脱钩。
    # 这正是「声明 48 / 渲染 108」那类缺陷的形态，且只有逐列比较能抓到。
    {"name": "W02_render_drift", "kind": "css", "want": ["P25"], "allow": ["P17", "P8"],
     "allowWhy": "把首列渲染成 80px：Σ渲染 与 Σ声明 脱开（P17），且总宽超出内容宽 → 出现横向溢出（P8）。"
                 "P17 只判 866 档的预算闭合，P25 判任意档位的逐列脱钩，两者重叠但不等价",
     "payload": ".ant-table.fixed th:nth-child(1),.ant-table.fixed td:nth-child(1){width:80px!important}"},
    # ---- V-01：闭合式 + N-d 独立判红
    # N-d 是**唯一**能用来说明「为什么不能只留一条闭合式」的注入：zoom .9 下内容盒实际布局宽
    # 1316 而 clientWidth 报 1184，闭合差仍是 0 —— 闭合式看不见它，只能靠缩放检测独立判红。
    # 允许的连带都是缩放的**真实后果**：所有以内容宽为分母的判据（预算闭合、一屏行数、
    # 列宽下限/声明=渲染）都会跟着变，因为布局真的被缩了。
    {"name": "V01_zoom", "kind": "css", "want": ["V-01"],
     "allow": ["P11", "P2b", "P4", "P6", "P17", "P20", "P21", "P22", "P23", "P24", "P25", "P8"],
     "allowWhy": "zoom 把整个内容区的布局宽缩到 1/0.9：一屏行数（P2a/P2b）、栅格控件宽（P4）、"
                 "列宽预算（P17）、逐列声明=渲染（P25）、表头/短字段/长文本的行盒（P20–P23）、"
                 "左边界（P6）、溢出（P8）全部按新布局重算；Drawer 声明 560 渲染 504（P11）也是"
                 "同一个缩放的后果 —— 这些都不是「V-01 与它们在测同一件事」，"
                 "**关键是：这些红里没有一条叫得响「内容区被缩放了」**，所以 N-d 必须自己判红",
     "payload": ".ant-content{zoom:.9}"},
    # N-a：内容区写死上限 1024 → 1024+208+48 = 1280，@1440 差 160。闭合式抓它，N-a 只是 cause 标签。
    {"name": "V01_maxw", "kind": "css", "want": ["V-01"],
     "allow": ["P2b", "P4", "P17", "P20", "P21", "P22", "P23", "P24", "P25", "P8"],
     "allowWhy": "内容宽从 1184 掉到 1024 → 所有以内容宽为分母的判据按新宽重算（同 N-d 的连带清单）；"
                 "这些红说的是「窄了」，没有一条能说出「上限被写死」，这正是 cause=N-a 存在的理由",
     "payload": ".ant-content{max-width:1024px}"},
    # ---- 三条 INCOMPLETE 的造红（三态里的第三态：**量具不可信**，不是产物红）
    # 守卫按 TOKEN 相等断言，不按条数 —— 「条数相同、集合不同」这坑本仓库踩过（CAPA 两页 FAIL 数都是 21）。
    {"name": "V01_content_zero", "kind": "css", "want_inc": "CONTENT_ZERO",
     "allow": ["P1", "P2a", "P2b", "P3a", "P3b", "P4", "P5", "P6", "P7", "P8", "P9", "P10",
               "P11", "P12", "P13", "P14", "P15", "P16", "P17", "P18", "P19",
               "P20", "P21", "P22", "P23", "P24", "P25"],
     "allowWhy": "把 .ant-content 隐藏后页面上什么都不剩，其余判据只能 SKIP 或红 —— 但这条注入要证的"
                 "只有一件事：V-01 报的是 INCOMPLETE(原因=CONTENT_ZERO) 而不是 PASS 或 FAIL",
     "payload": ".ant-content{display:none!important}"},
    {"name": "V01_parent_hidden", "kind": "css", "want_inc": "PARENT_INVISIBLE",
     "allow": ["P1", "P2a", "P2b", "P3a", "P3b", "P4", "P5", "P6", "P7", "P8", "P9", "P10",
               "P11", "P12", "P13", "P14", "P15", "P16", "P17", "P18", "P19",
               "P20", "P21", "P22", "P23", "P24", "P25"],
     "allowWhy": "父盒 display:none 后内容盒也跟着不可见；要证的是「父节点不可见 → PARENT_INVISIBLE」"
                 "而不是被误报成 CONTENT_ZERO（两个 TOKEN 混成一个，守卫就没法按集合比）",
     "payload": ".ant-layout.h{display:none!important}"},
    {"name": "V01_nav_negative", "kind": "css", "want_inc": "NAV_OUT_OF_RANGE",
     "allow": ["P2b", "P4", "P17", "P24", "P25", "P8"],
     "allowWhy": "内容 min-width 900 塞进 600 的父盒 → 导航宽 = 600−900 = −300。"
                 "「内容比父盒还宽」说明父节点选错或取错元素，那是量具问题（INCOMPLETE），"
                 "不是产物缺陷（FAIL）—— 其余判据按新宽度重算是这个注入的真实后果",
     "payload": ".ant-layout.h{width:600px!important}.ant-content{min-width:900px!important}"},
    # ---- P7(W-00) 两个方向各一次：只证一个方向时，「原因=both」就分不出是哪个分支在起作用
    {"name": "P7_fixed_off", "kind": "json", "want": ["P7"],
     "allow": ["P17", "P18", "P20", "P21", "P22", "P24", "P25", "P2b", "P9"],
     "allowWhy": "只把 tableLayout 从 fixed 改成 auto（width 全保留）：列宽改由内容决定 → 配了 ellipsis 的列"
                 "不再真溢出（P18）、每列按内容定宽后长短列重排（P17/P25 的账本对不上）、长文本开始换行"
                 "（P20/P21/P22）、行高变化挤掉一屏行数（P9/P2b）、声明宽与实际宽脱钩后下限也换了参照（P24）。"
                 "**这组连带本身说明了 W-00 为什么是前置**：布局没锁时下游七八条判据的读数全部失去意义 —— "
                 "不是它们在测同一件事，而是它们量的是同一张已经变形的表",
     "payload": lambda p: _mutate_table(p, lambda tp: tp.update({"tableLayout": "auto", "fixed": False}))},
    {"name": "P7_decl_low", "kind": "json", "want": ["P7"],
     "allow": ["P17", "P24", "P2b", "P9"],
     "allowWhy": "摘掉两列的 width：声明率 8/8→6/8=75%（<80%，这才是 declared 那一半能红的条件 —— "
                 "只摘一列是 87.5%，会 PASS，注入就白做了）。Σ 掉 168（P17）；这两列在 fixed 下被按比例"
                 "重分配 → 列宽与行高变化（P9/P2b），声明侧下限的参照也变了（P24）—— 都是改列宽声明的直接后果",
     "payload": lambda p: _mutate_table(p, lambda tp: _drop_widths(tp, 2))},
    # ---- P21(T-02) 长文本没有出口：摘掉 ellipsis 并让这一列真的换行（nowrap 下摘了也不会多行）
    {"name": "P21_no_exit", "kind": "json", "want": ["P21"],
     "allow": ["P18", "P22", "P25", "P9", "P2b", "P24"],
     "allowWhy": "把「物资名称」的 ellipsis 摘掉并强制换行：① 有出口列集合少一个、真溢出集合不变（P18）；"
                 "② 该列折成多行 → 行高与行数（P9/P22/P2b）；③ 声明了出口的列少一个 → 分母变化（P24）；"
                 "④ 格内换行后单元格宽仍按 colgroup（P25 可能抖一列）。要证的只有一件事："
                 "「无出口的长文本列」能被 P21 抓到",
     "payload": lambda p: _mutate_table(p, lambda tp: _clear_ellipsis(tp, "物资名称")),
     "css_extra": ".ant-table.fixed th:nth-child(3),.ant-table.fixed td:nth-child(3)"
                  "{white-space:normal!important}"},
    # ---- P22(T-03) 行数上限：把一列压到 3 行以上（宽 48 + 允许换行）
    # ---- P2a/P2b 单轨（XX-045）：两条出口各一条注入。
    # 这两条判据的**第三态**（SKIP / INCOMPLETE）不进 FAIL 集合 —— 只比 FAIL 集的话，
    # 「少造几行换一个 SKIP」永远绿，自证等于没做。所以断言按 (状态, 值) 相等，见 want_rows。
    # 注入手段：把示例数据砍到 6 行（20→6）。只少造数据，不动列宽 ——
    # 动列宽会连带 P17/P24/P25，那「多翻」就说不清是哪条抓到的。
    # SKIP 那一支要**摘掉 total**：example-06 自己声明 total=342，只要行数一少
    # 就已经是「造少」（下面那条），走不到 SKIP。两个分支各造一次，否则
    # 「SKIP 与 INCOMPLETE 的分界」只剩文档里那句话。
    {"name": "P2b_rows_skip", "kind": "json", "want_rows": {
        "P2b": ("SKIP", r"^SKIP\(行数 6 < \d+，total 未声明\)$")},
     "payload": lambda p: _mutate_table(p, lambda tp: _clear_total(_rows_to(tp, 6)))},
    # 只砍行数、不动 total：产物自己写着 total=342 却只渲染 6 行 —— 这就是「造少」，
    # 判据必须报 INCOMPLETE(INSUFFICIENT_ROWS)，而不是拿「行数不够」换个 SKIP 了事。
    {"name": "P2b_rows_total", "kind": "json", "want_rows": {
        "P2b": ("INCOMPLETE", r"^INCOMPLETE\(INSUFFICIENT_ROWS\) total 342 ≥ \d+，行数 6$")},
     "payload": lambda p: _mutate_table(p, lambda tp: _rows_to(tp, 6))},
    {"name": "P22_exceed", "kind": "css", "want": ["P22"], "allow": ["P9", "P2b", "P2a", "P25", "P8", "P17"],
     "allowWhy": "把第 3 列（物资名称）压到 48px 并允许换行 → 长值折成 3 行以上：行高（P9）、一屏行数"
                 "（P2a/P2b）、列宽账本（P17/P25）与表格总宽（P8）都跟着变。这是「行数超限」的必然伴随，"
                 "不是 P22 与它们在测同一件事",
     "payload": ".ant-table.fixed th:nth-child(3),.ant-table.fixed td:nth-child(3)"
                "{width:48px!important;white-space:normal!important}"},
    # ---- I-09 第三阶段新增：S-01 / S-02a / S-02b 各一条能红的注入
    # 「新增判据每一条都要有一条能红的注入」——S-02b 在三份产物上本来就全绿，
    # 没有注入的话，「它判了」和「它永远绿」在报告上完全一样。
    # 选 `.ant-btn` 而不是正文元素：按钮在 S-02b 里已被排除（控件），改它的字号
    # 不会顺手把 S-02b 也打红，这样「多翻」只剩 P19 —— 而 P19 与 S-01 数字号档位
    # 是**已知重叠**（S-01 更强：`{12,13,14}` 3 档但含 13，P19 绿、S-01 红）。
    {"name": "S01_size_19", "kind": "css", "want": ["S-01"], "allow": ["P19", "P12", "P16"],
     "allowWhy": "按钮字号 14→19：① 去重集合多出 19 → S-01 红；② P19（档数 ≤3）同样红 —— "
                 "两条量同一批元素，已知重叠，S-01 更强；③ 按钮变宽变高把标题带与筛选区一起顶起来 → "
                 "P12 的 Δtop、P16 的分页 bottom 跟着变。②③ 都是「字号变大」的真实后果，"
                 "不是 S-01 与它们在测同一件事",
     "payload": ".ant-content .ant-btn{font-size:19px!important}"},
    # 行高 ≥34 的造红：加 padding 让单行行变高，**不改行盒数**（padding 不影响换行）——
    # 这样分母仍是那 20 行单行行，红的是「单行行超过了 34」本身。
    # 连带 P9（极差/最高）、P2a/P2b（一屏行数）是行高变大的必然结果。
    {"name": "S02a_row_high", "kind": "css", "want": ["S-02a"],
     "allow": ["P9", "P2a", "P2b"],
     "allowWhy": "td 上下 padding 各加到 14px → 单行行从 34 涨到 50：P9 的最高行高、P2a/P2b 的一屏行数"
                 "都跟着变，这是「行变高」的必然后果，不是 S-02a 与它们在测同一件事",
     "payload": ".ant-table td{padding-top:14px!important;padding-bottom:14px!important}"},
    # 正文行高比 1.57 → 1.00：只动表单标签（span.lb，表格外、非控件、非标题），
    # 让「正文」这一桶里出现越界值。若不降字号，比值恒为 line-height/font-size 的商，
    # 读得出来就说明判据量的是这一个商，而不是别的东西。
    {"name": "S02b_line_height_1", "kind": "css", "want": ["S-02b"],
     "payload": ".ant-content span.lb{line-height:1!important}"},
]


def _drop_widths(tp, n=2):
    """摘掉 n 列的 width（默认 2）。为什么是 2 不是 1：声明率阈值是 80%，
    8 列摘 1 列 = 87.5% 仍然 PASS —— 注入会「没红」，看上去像判据失效，其实是没打到门槛。
    从尾部摘（操作/状态），这两列不是 ellipsis 列，摘宽不会连带 P18。"""
    cols = tp.get("columns") or []
    for c in reversed(cols):
        if n <= 0:
            break
        if "width" in c:
            c.pop("width", None)
            n -= 1
    return tp


def _clear_ellipsis(tp, title):
    """只摘掉某一列的 ellipsis 声明，**不补 wrap/maxLines** —— 补了就等于给了新出口，
    P21 会认为「有出口」而不红（出口 = ellipsis / wrap+maxLines / 移出表格，任何一个成立都算）。
    摘掉之后该列默认是 nowrap（不会折行），所以必须配一条 CSS 强制它换行（见 P21_no_exit 的 css_extra）。"""
    for c in (tp.get("columns") or []):
        if c.get("title") == title:
            c.pop("ellipsis", None)
            c.pop("ellipsisCol", None)
            break
    return tp


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


def _rows_to(tp, n):
    """把示例数据砍到 n 行 —— 「造少」的注入手段（P2a/P2b 单轨，XX-045）。

    只砍 `data`，不动 `columns`：动列宽会连带 P17/P24/P25，
    自证里就分不清「行数判据抓到的」还是「列宽判据抓到的」。
    """
    d = tp.get("data")
    if isinstance(d, list):
        tp["data"] = d[:n]
    return tp


def _clear_total(tp):
    """摘掉 `pagination.total` —— 为了走到 `SKIP(… total 未声明)` 那一支。

    这一支不是「更宽松的出口」，是「连证据都没有」：没有 total 就分不清
    「这页本来只有 6 条」和「造少了」。所以判 SKIP 而不是 PASS —— 见 `_rows_gate`。
    """
    pg = tp.get("pagination")
    if isinstance(pg, dict):
        pg.pop("total", None)
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


def _set_col_width(tp, title, w):
    """按标题改一列的声明宽（自证用）。按**标题**不按下标：下标会被插列改掉。"""
    hit = 0
    for c in (tp.get("columns") or []):
        if c.get("title") == title:
            c["width"] = w
            hit += 1
    assert hit == 1, "自证注入找不到唯一的列「%s」（命中 %d 次）" % (title, hit)
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
                # 一条注入偶尔要同时改 JSON 与 CSS（比如「摘掉 ellipsis」+「强制换行」）：
                # 只有 JSON 侧摘声明时该列仍 nowrap、根本不折行，P21 数的是多行格，注入会不红。
                css = css + "\n" + (inj.get("css_extra") or "")
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
            want = inj.get("want") or []
            want_inc = inj.get("want_inc")
            want_rows = inj.get("want_rows") or {}
            targets = want or list(want_rows)
            # 前置①：目标判据在基线里必须绿。不绿不是「跳过」，是自证不成立 ——
            # 计入未覆盖，最终 RESULT 为 INCOMPLETE。
            missing = [w for w in targets if w not in base_pass]
            if missing:
                print("  %-18s SKIP（基线 %s 不绿，注入同类缺陷看不出变化；基线现值 %s）"
                      % (inj["name"], missing,
                         ", ".join("%s=%s" % (w, base_val.get(w, "—")) for w in missing)))
                ok_all = False
                continue
            if want or want_rows:
                print("  %-18s 基线 %s" % (inj["name"],
                                          ", ".join("%s=%s（%s）" % (w, base_val.get(w), "PASS")
                                                    for w in targets)))
            else:
                print("  %-18s 基线 V-01=%s（%s）" % (inj["name"], base_val.get("V-01"), "PASS"))
            rows = run(inj)
            now_fail = {r["id"] for r in rows if r["status"] == "FAIL"}
            now_val = {r["id"]: r["value"] for r in rows}
            flipped = now_fail - base_fail
            allow = set(inj.get("allow") or [])
            if want_rows:
                # 断言**按 (状态, 值) 相等**：这两条判据的红是 FAIL，但它的第三态是
                # SKIP / INCOMPLETE —— 两者都不进 FAIL 集合，只比 FAIL 集等于什么都没证。
                # 值用正则整串锚定，不比中文尾巴（措辞改了不该算自证失败），
                # 但**必须**锚住括号里的 TOKEN 与实测数：`SKIP(...)` 与
                # `INCOMPLETE(INSUFFICIENT_ROWS) total 342 ≥ 9，行数 6` 是两种不同的结论。
                bad_rows = []
                for pid, (exp_st, exp_re) in want_rows.items():
                    r0 = next((x for x in rows if x["id"] == pid), None)
                    st = (r0 or {}).get("status") or "—"
                    val = (r0 or {}).get("value") or ""
                    if not (st == exp_st and re.match(exp_re, val)):
                        bad_rows.append("%s 实测 %s %s ｜ 期望 %s 匹配 %s"
                                        % (pid, st, val or "—", exp_st, exp_re))
                extra = flipped - allow
                print("  %-18s 实测 %s %s%s"
                      % ("", ", ".join("%s %s" % (p, now_val.get(p)) for p in want_rows),
                         "  OK" if not bad_rows and not extra else "  SELFCHECK-FAIL",
                         ("  多翻：" + str(sorted(extra))) if extra else ""))
                for b in bad_rows:
                    print("          ↳ %s" % b)
                if allow and (flipped & allow):
                    print("          ↳ 允许的连带 %s：%s" % (sorted(flipped & allow), inj.get("allowWhy", "")))
                if not bad_rows and not extra:
                    covered += 1
                else:
                    ok_all = False
                continue
            if want_inc:
                # INCOMPLETE 不是 FAIL，所以走另一条断言：**按 TOKEN 相等**，不按条数。
                # 条数相同而集合不同这坑本仓库踩过（CAPA 两页 FAIL 数都是 21，红的却各是各的）。
                r01 = next((r for r in rows if r["id"] == "V-01"), None)
                m = re.search(r"原因=([A-Z_]+)", (r01 or {}).get("note") or "")
                got_tok = m.group(1) if m else "—"
                extra = flipped - allow
                ok = bool(r01) and r01["status"] == "INCOMPLETE" and got_tok == want_inc and not extra
                print("  %-18s V-01=%s 原因=%s 期望=%s %s%s"
                      % ("", (r01 or {}).get("status", "—"), got_tok, want_inc,
                         "OK" if ok else "SELFCHECK-FAIL",
                         ("  多翻：" + str(sorted(extra))) if extra else ""))
                if allow and (flipped & allow):
                    print("          ↳ 允许的连带 %s：%s" % (sorted(flipped & allow), inj.get("allowWhy", "")))
                if ok:
                    covered += 1
                else:
                    ok_all = False
                continue
            ok = set(want).issubset(flipped)
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
        # ---- N-c：手写壳样本（**不是容器产物**）。它不进 INJECTIONS，因为它改的不是 JSON/CSS，
        # 而是整份 DOM —— 塞进上面那套「基线产物 + 注入」的循环里，等于让 P1–P25 一起把手写壳
        # 当产物判，翻红清单会全是噪音，真正要证的那对数会被淹掉。
        print("  N-c 手写壳样本（fixture-nc-manual-shell.html，非容器产物）")
        nc_ok = nc_shell_check(chrome, tmp)
        if nc_ok:
            covered += 1
        else:
            ok_all = False
        total += 1
        # ---- XX-045 验收 ①：行数不足 + total 未声明 → 条件式 SKIP 必须被白名单放行
        if p2_skip_fixture_check(chrome, tmp):
            covered += 1
        else:
            ok_all = False
        total += 1
        # ---- XX-047：结论段不许早退（INCOMPLETE 压掉 V8 结论的同一次事故）
        if conclude_check():
            covered += 1
        else:
            ok_all = False
        total += 1
        print("  自证覆盖=%d/%d" % (covered, total))
        if covered < total or not ok_all:
            print("RESULT INCOMPLETE (selfcheck)：只证明了 %d/%d 条注入，"
                  "覆盖不足不得判 PASS" % (covered, total))
            return 1
        print("RESULT PASS (selfcheck)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def conclude_check():
    """XX-047 自证：INCOMPLETE 与 V8 不符**同时**存在时，结论段两句都得在。

    只断言一个关键词等于没证：老的三级早退写法在「只有 INCOMPLETE」时输出里也含
    `INCOMPLETE`，照样过得去；要证的是 **V8 的比对结论没被 INCOMPLETE 压掉**。
    另断言两个数：`3 行 INCOMPLETE（P2a、P2b）` —— 行数 3（两档重复计）、判据名去重后 2 个。
    只打条数的那版，`2 判据 × 2 档 = 4` 会被读成「4 条判据」（幻神就是这么质疑 P2b 分母的）。

    这是**结论段**的自证，所以直接调 `conclude()` 喂构造输入，不跑一遍渲染：
    要证的是"三条事实会不会互相压掉"，与量具无关；跑渲染只会让这条自证依赖 Chrome 抖动。
    """
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = conclude(3, ["P2a", "P2a", "P2b"], [], True, 0)
    out = buf.getvalue().strip()
    ok = (rc == 1
          and "RESULT INCOMPLETE" in out
          and "3 行 INCOMPLETE（P2a、P2b）" in out
          and "V8 FAIL 集与期望名单不符" in out)
    print("  %-18s %s ｜ %s" % ("XX-047 结论段", (out.splitlines() or ["（无输出）"])[0][:110],
                               "OK" if ok else "SELFCHECK-FAIL"))
    if not ok:
        print("          ↳ rc=%s ｜ 期望 rc=1 且同段含「3 行 INCOMPLETE（P2a、P2b）」"
              "与「V8 FAIL 集与期望名单不符」——只含一个说明还在早退" % rc)
    return ok


def p2_skip_fixture_check(chrome, tmp):
    """XX-045 验收 ①：**行数不足 + `total` 未声明** 时，`P2a/P2b` 的条件式 SKIP 必须被白名单放行。

    样本 `tests/fixtures/fixture-p2-rows-skip.json`（6 行；`pagination` 里**只有 `pageSize`、没有 `total` 键**）。
    断言三行 **(状态, 值) 精确对**，外加「该行不在 `bad_skip` 里」—— 后者才是 V13 的理由：
    证明了「它会 SKIP」不代表「这个 SKIP 有正当条件」，反过来说把验收写成「→ SKIP」是**同义反复**。

    为什么不要求整轮 `RESULT PASS`：`default_targets()` 里有 example-05 的登记红，
    全量模式结构上不可能 PASS。这里证的是「这一行 SKIP 被放行」。

    样本为什么不放 `assets/examples/`：那里每多一份要同步 `check_docs.EXPECTED_EXAMPLES`、
    `README` 引用可达、`check_generators` 的 `gen_exampleNN.py` **三处**；而
    `default_targets()` 只 glob `example-*.json`，放 `fixtures/` 也不会被全量模式收进去。

    四个写法里只有两种同时满足「有分页脚」与「total 未声明」：`{"pageSize": 6}` 或 `pagination: true`。
    `{"total": 6, ...}` 会挂在正则上（值变 `total 6 < 14`）；不写 `pagination` 会挂 P16
    （裸 `SKIP(无分页脚)`，不在白名单）。
    """
    want = {1440: [("P2a", r"^SKIP\(行数 6 < 14，total 未声明\)$"),
                   ("P2b", r"^SKIP\(行数 6 < 9，total 未声明\)$")],
            1600: [("P2b", r"^SKIP\(行数 6 < 12，total 未声明\)$")]}
    data = json.loads(P2_FIXTURE.read_text(encoding="utf-8"))
    page = pick_page(data)
    if page is None:
        print("  %-18s SELFCHECK-FAIL ｜ fixture 里没有作业型列表页" % "P2 条件式 SKIP")
        return False
    hp = tmp / "p2-skip.html"
    build_case(CONTAINER, data, page["id"], hp)
    ok_all, seen, bad_all = True, [], set()
    for w, _h in VIEWPORTS:
        d = run_viewport(chrome, hp, w, _h)
        rows = evaluate(props_of(page, d), d, page, w)
        bad_all |= {r["id"] for r in rows if r["status"] == "SKIP" and not skip_allowed(r)}
        for pid, rx in want.get(w, []):
            r0 = next((x for x in rows if x["id"] == pid), None)
            st = (r0 or {}).get("status") or "—"
            val = (r0 or {}).get("value") or ""
            good = st == "SKIP" and re.match(rx, val)
            seen.append("%s@%d %s%s" % (pid, w, val or st, "" if good else " ✗"))
            if not good:
                ok_all = False
    ok = ok_all and not bad_all
    print("  %-18s %s ｜ 白名单外 SKIP=%s ｜ %s"
          % ("P2 条件式 SKIP", " ｜ ".join(seen), sorted(bad_all) or "[]",
             "OK" if ok else "SELFCHECK-FAIL"))
    if not ok:
        print("          ↳ 期望 P2a/P2b 是 SKIP 且值匹配「行数 6 < 所需，total 未声明」，"
              "且不出现在白名单外 —— 放宽正则或改样本都不许")
    return ok


def nc_shell_check(chrome, tmp):
    """N-c 自证：**只断言两条式子的数**，不断言 PASS/FAIL（team-lead 裁定）。

    样本是 `tests/fixtures/fixture-nc-manual-shell.html`（手写 HTML 壳，内联 `width:1100px`）：
      · 归因差 = |减法 0 − 真实 0| = **0**      ← N-c 抓不到：壳一包，减法与真实同时变 0 互相抵消
      · 铺满差 = |1100 − 0 − 1440| = **340**    ← 只有判据②能红
    那个「0」才是这条样本存在的理由：它证明「归因差覆盖 N-c」是错的。

    **为什么不顺手断言 `FAIL(cause=N-c)`**：这条 fixture 是手写壳、不是产物。它的结论是
    「判据② 在这里能红」，不是「这份产物不合格」。一旦写成整体断言，以后有人会把它当
    「N-c 产物的标准形态」照抄 —— 那就把一条为了证明可达性的证据，变成了一个假的范式。
    状态照打，只作展示。
    """
    fx = Path(__file__).with_name("fixtures") / "fixture-nc-manual-shell.html"
    if not fx.is_file():
        print("           SELFCHECK-FAIL  样本缺失：%s" % fx)
        return False
    src = fx.read_text(encoding="utf-8")
    hp = Path(tmp) / "n-c.html"
    hp.write_text(src.replace("</body>", PROBE.replace("/*__INJECT__*/", "") + "</body>", 1),
                  encoding="utf-8")
    d = run_viewport(chrome, hp, 1440, 900)
    g = (d.get("v01prod") or {}).get("v01") or {}
    nav = (g.get("parentW") - g.get("contentOffsetW")) if g.get("parentW") is not None else None
    sib = g.get("sibNavW")
    attrib = abs(nav - sib) if (nav is not None and sib is not None) else None
    fill = (g.get("parentW") - (g.get("contentBorderW") or 0) - g.get("viewportW")) \
        if g.get("parentW") is not None else None
    row = v01_row(d, {}, 1440)
    # 断言只有两个数：归因差 ≈0（抓不到）与 |铺满差| ≈340（判据②能红）。
    ok = (attrib is not None and attrib <= V01_TOL
          and fill is not None and abs(abs(fill) - 340) <= 3)
    print("           归因差%s ｜ 铺满差%s ｜ %s ｜ %s"
          % (fmt(attrib), fmt(abs(fill)) if fill is not None else "—",
             row["status"], "OK" if ok else "SELFCHECK-FAIL"))
    print("           断言：归因差 ≤%d（0 = 抓不到，这一半必须成立）且 |铺满差| = 340±3"
          "（状态 %s 只作展示，不作断言）" % (V01_TOL, row["status"]))
    return ok


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
