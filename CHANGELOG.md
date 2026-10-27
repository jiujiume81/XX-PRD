# 变更记录

本文件记录 XX-PRD 的版本变更、兼容性影响与升级方式。
格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。
**每个条目必须含 `breaking` 字段**（是 / 否 + 一句说明），用于判断能否安全升级。

> **状态：`0.10.0` 为本版（2026-10-27 交付）；`0.9.0` 已于 2026-10-26 交付（`0ab52d6`）；`0.8.0` 已于 2026-10-22 交付（`88a3ab1`）；`0.7.0` 已于 2026-10-21 交付（`077290a`）；`0.6.0` 已于 2026-10-21 发布（`2d51574`）；`0.5.0` 已于 2026-10-20 发布（`5409cbf`）。**
> **`0.10.0` 只新增判据，不动任何既有阈值**：`run.sh` 仍是 `TOTAL ok=757`，`CASES` 与 `-ne 757` 未改；
> `P1–P25`、`S-01/S-02a/S-02b`、`V-01`、`W/T` 组的阈值与结论一字未动。
> **但存量产物会多红** —— 新判据抓到的都是既有缺陷（`reject-01` 上的 `L-01` / `C-01` / `A-03`），
> 这是它们存在的理由，不是回归。
> `0.5.1` **从未单独发布**，其变更（`RETRIES_MAX` 默认 0）并入 `0.6.0` 一同交付 ——
> 所以升级 `0.5.0 → 0.6.0` 的人同时承受 `[0.5.1]` 的 breaking（"绿"变严）与 `[0.6.0]` 的新增字段。
> `[0.5.0]` 段里仍标「待核」的条目是**发布当时的核验目标**，其结论以 `iterations/I-01/release.md`
> 与 `iterations/I-02/build.md` 记录的实测为准——本文件不重复断言，也不因发布而在事后补写"已验证"。
> （「待核」「未验证」**不在占位词表里**：词表只收 5 个"未填内容"类的词，见 `scripts/placeholder-vocab.json`；
> 这两个词描述的是**核验状态**而非**未填内容**，所以 DoD 8 不会因它们判红——`tests/check_placeholders.py`
> 实测 `PASS placeholders: 16 处命中均已在显式允许清单内`。**留着它们既诚实、也不妨碍放行。**）
> `[0.5.1]` 段对应的核验命令：`bash tests/run.sh`（回归）、`python3 tests/check_generators.py`（生成器一致性）。

## [未发布] - 2026-10-27（XX-050：props 契约与 SS-01）

**breaking: 是（两条：① `TextArea.rows` 让已写 `rows` 的产物变高；② 存量产物会在 SS-01 上多红）**

### 新增判据 SS-01「props 消费闭合」（`references/04` §6.8）

容器是逐字段手写读 `props` 的（`p.xxx`），没有整包透传：写一个容器没读的键 = 写了不生效，
**而且不报错**；几何判据只量像素，对这类键完全免疫。所以另立一条**只读声明**的判据。
白名单由 `scripts/props_contract.py` 从容器源码机械提取，**不许手写**（手写的白名单一定会在
某次改容器后悄悄分叉）。

三态：`PASS` / `ERROR`（键不在该 type 的可读集，或值域不合法）/ `INCOMPLETE`（契约缺失、
无法解析、与容器逐类型比对不一致 —— 后三种是**工具链缺失**，任何档都非 0 退出）。

**不设 WARN**：「键被别的类型读过」不是作者的处境差异，是键写错了节点。判成 WARN 就是假绿 ——
`example-06` 的两个 `Alert` 把正文写在 `props.text`（Alert 只读 `message`），画面是两条
**空白告警条**，而 WARN 口径下退出码仍是 0。

### 容器新增 5 项读取（`assets/container/index.html`）

| 键 | 语义 | 兼容性 |
|---|---|---|
| `Drawer.placement` | `right`(默认)/`left`/`top`/`bottom` | 只新增取值；`right` 的渲染与旧版逐像素相同（实测 `w=400 x=476` 不变）。写非法值 → 容器 `warn()` 并退回 `right`，**不静默** |
| `FormItem.extra` | 常态说明文字，恒为 `--ant-text-3` | 新增；老产物 0 处使用 |
| `TextArea.rows` | `min-height = max(64, 21×rows+14)` | **破坏性**：`example-02` 的 `n-apply-ta-desc` 实测 64 → 77px（`rows:3`）。`check_ui_shape` 不测那一页，所以回归数字不变 —— 这一条只能靠本行留痕 |
| `Card.bordered` | 1px 边框 + 去投影（CSS 早已写好，渲染器从未加 class） | 新增；CAPA 里 15 处 `bordered:true` 此前全是空转 |
| `Alert.visible` | **不新增读取**：`renderNode` 的通用处理早已对**所有** type 生效（`props.visible===false → display:none`），`visible` 进契约的 `shared` 集 | 无变化。实测旧版就渲染成 `DIV.ant-alert display:none`，此前「写了 false 照样显示」的说法不成立 |

### 契约生成器重写（`scripts/props_contract.py`）

- **两种注册都认**：`R.X=function` 与 `R['List.Item']=function`。此前只认前者，
  渲染器数少一个（67 → 实际 **68**），`renderItem` 模板一进判据就是整类假红。
- **函数体用括号配平**（跳过字符串/模板串/正则/注释），不再用「下一个 `R.*` 起点」。
  旧口径把 `R.Frame` 之后 11 万字符（文件尾 46%）算成 Frame 读的键。
- **helper 闭包**：渲染器体里以 `p` 为首参调用的同文件函数（`buildFilterBar(p,ctx)`）算它的读取点；
  **只认 `p` 作首参** —— `getPath(o,p)` 那种普通形参不算，否则 `p.split` 会进白名单。
- **注释与字符串里的 `p.xxx` 不计**：注释写「Col 读不到 p.gutter」不该让 Row 凭空多一个可读键。
- 清单真源改为 `references/props-unsupported.json`（扁平 `entries[]` + `type:"*"` 通配，17 条）。
  **文件缺失或格式不符 → 生成器 ERROR 退出**，不许静默 0 条。
- `sourceSha256` 降级为诊断；`--check` 与 SS-01 都改成**逐类型比对**。
  整文件 sha 对「改一行注释」过敏（全线 INCOMPLETE），对「清单换格式」却失明。

### 闸门

- SS-01 的 `INCOMPLETE`（工具链缺失）**任何档都非 0**；R 组的 `INCOMPLETE`（存量产物缺
  `contract` / `fieldRegistry`）仍按原口径默认不拦。两类不再混在一个退出码里。
- `check_release.py` 新增 **DoD 13**：契约同步 + 绿样本（`example-03`，分母 80）+ 造红
  （`example-06` 点名 `Alert.text` ×2）+ 契约缺失时非 0，三态各验一次。

### 存量产物读数（**未修，属 XX-051/052 的范围**）

| 示例 | SS-01 | 说明 |
|---|---|---|
| `example-01` | ERROR ×1 | `Descriptions.bordered` |
| `example-02` | ERROR ×5 | `Descriptions.bordered`、`InputNumber.min/max/step`、`Upload.multiple` |
| `example-03` | PASS（分母 80） | 绿样本 |
| `example-04` | ERROR ×1 | `Space.style` |
| `example-05` | ERROR ×2 | `Table.rowKey`、`Descriptions.size` |
| `example-06` | ERROR ×4 | `Alert.text`×2、`Descriptions.size`、`InputNumber.placeholder`、`Table.rowKey` |

`run.sh` 仍是 `TOTAL ok=757`（`137/123/136/150/117` 全部未动）；`check_ui_shape` 仍是
`PASS=105 FAIL=20 SKIP=15`，与接线前逐字相同。

## [0.10.0] - 2026-10-27

**breaking: 是（新增四条判据，存量产物会多红）** —— 只新增、不改任何既有阈值。
`P1–P25`、`S-01/S-02a/S-02b`、`V-01`、`W/T` 组的阈值与结论一字未动，`run.sh` 的 `CASES` 与 `-ne 757` 也未动。
新增的判据在**旧产物上会红**，那是它们存在的理由，不是回归：

| 判据 | 条款 | 阈值 | 在 `reject-01` 上的读数 |
|---|---|---|---|
| `L-01` | 区块级 `margin`/`padding`/`gap` 的 4px 栅格 | 取值 ⊆ `{0,4,8,12,16,24,32,40,48}` | **FAIL**：`breadcrumb` gap `6`、`alert` gap `10` |
| `C-01` | 内容区有彩度颜色去重数 | ≤ 6 种 | list **FAIL**（9 种）；overdue PASS（3 种） |
| `A-01` | 同列文本起始边极差 | ≤ 1px | 四档 PASS（该页列对齐没问题） |
| `A-03` | 区块左边界极差 | ≤ 1px | list **FAIL**（两表格 312 vs 327，差 15）；overdue `SKIP`（1 个区块） |

**做法上有一条值得留档**：这四条**先做量具、跑出分布，再接线**（`afb2211` 的同一条纪律）。
量出来的第一件事就是「教材 `example-06` 的卡片数是 **0**」—— 于是 `L-02`（卡片用边框、浮层用投影）
当场被判为「现有产物里没有分母」，不能接线；`A-02` 卡在「`type:'num'` 与 `text-align:right`
不是同一件事」；`C-02` 要跨页比同一状态词，而 `evaluate()` 是单页的。
三条都留在 `XX-044`/`XX-048` 里，**没有为了让验收好看而临时发明一个口径**。

自证 `--selfcheck` **36/36**（原 32 + 新增 4 条注入）；`check_reject` 四档 **18/19/17/14** 逐条相等，
反样本**一个字没改** —— 它是 2026-10-23 的真实现场，为了让新判据变绿去改它等于篡改证据。

**规范侧同期一处裁定（不改代码，改的是需求口径）**：「我的任务」这类功能的形态，v1 是
「工作台待办卡片 + 导航指向筛选后的同一张列表、不新增独立页」的**默认项**（因为源需求没说形态）。
2026-10-27 Owner 明确「**应该是独立窗口**」→ `13` §3.3 改写为「Owner 裁定 = **独立页面 + 导航入口**」，
并新增判据 **R3-b**（有提交命令的角色必须有独立待办页；只有「从别人的单据页借道」的入口不算）。
同批修掉 R3 第 3 条的字段名错误：原文 `p.contract.entryFrom`，而两个产物的入口都在 `pages[].entryFrom`
（`contract.entryFrom` 逐页为 `None`），按原文实现**会把教材也判成「无入口」**。

**同期另一件事：R1–R4 十五条判定从「条文」变成「闸门」（`XX-041` 第一批）**

`13` 自 v1 起就有 R1–R4，但 `validate_prd_json.py` 里一条都没有（`fieldRegistry` / `oneToMany` /
`verify` 零命中）。本版全部实现，并引入**第三种状态 `INCOMPLETE`**：

| 状态 | 含义 | 处置 |
|---|---|---|
| `PASS` | 判了，通过 | — |
| `ERROR` | 判了，不通过 | 改数据 |
| `INCOMPLETE` | **判据在，产物里没有可判的输入** | 补数据；**不许当 PASS** |

默认档 `INCOMPLETE` 不拦（存量产物写于规则之前，一次全红只会让人关掉检查）；`--require-r` 下与非 0 退出等价。

- 绿样本：`tests/fixtures/fixture-r1-r4.json` —— **15/15 PASS**、`errors=0`
- 逐条造红：`tests/check_r1_r4.py` —— **15/15 个单点变体按预期变红**，连带变色须逐条登记
- 进闸门：`check_release.py` 新增 **DoD 12**（不并入 DoD 1，理由见该函数注释：示例没有源文档，
  给它们编一份 `sourceTerms` 会让 R1-c 的计数闭合变成恒等式）

**真实反样本上的读数**（`reject-01-capa-qms`）：`PASS=0 / ERROR=2 / INCOMPLETE=13`。
两条红正是人工评审当初指出的缺陷 —— `R2-d` 子表出现「阶段」列、`R3` `u-executor` 无独立入口。
**不是靠造红，是判据抓到了真实现场。**

**仍未达成的一项（如实记）**：`XX-041` 验收第 1 条要求 CAPA 上 `R1 ≥2 / R2 ≥2 / R3=1 / R4 ≥2`
条 ERROR，目前只有 `R2-d` + `R3` —— 其余因反样本缺 `fieldRegistry` / `relations` / `stage` 报
`INCOMPLETE`。补反样本数据是下一批，**不用「判据已实现」代替它**。

**本版不含什么**（避免 pull 到的人误以为判据已全覆盖）：
- `L-02`（卡片边框 / 浮层投影）、`A-02`（数值列）、`C-02`（跨页同状态词同色）三条**仍未接线**，
  各自卡在分母与口径，登记在 `XX-044` / `XX-048`。
- `F3` 上下文持久化（`decisions.json`，`XX-042`）、`check_ui_shape` 并入 CI（`XX-036`）未做。

## [0.9.0] - 2026-10-26

**breaking: 是（仅第三阶段的判定口径，其余部分只新增）** —— 反样本、量具、`measure_reject.py`
这些只新增，不动既有行为，也不动 `run.sh` 的 `CASES` 与 `check_docs` 的示例清单。
但 **I-09 第三阶段改了三处判定口径，旧产物会在新口径下集中变红 —— 这是设计目的，不是回归**：

| 判据 | 原口径 | 新口径 | 旧产物后果 |
|---|---|---|---|
| `S-01` 字号 | 「≤3 档 **且** 集合 ⊆ `{18,14,12}`」 | **只判集合**（档数降为读数） | 形如 `{12,13,14}` 的 3 档页面**由绿变红**（`example-05` 就是） |
| `S-02a` 行高上限 | 无（未接线） | 单行数据行 `≤34`，分母 = 行内行盒数 ==1 | `example-05` 单行 39 → 红；CAPA list 分母 0 → 条件式 `SKIP` |
| `S-02b` 正文行高比 | 无（未接线） | 正文 `lineHeight ÷ fontSize ∈ [1.40,1.60]`（排除按钮与标题） | 三份产物实测均 1.57 → 绿 |
| `P9` 行高一致性 | 「极差 ≤2 **且** 最高 ≤34」 | **只判组内极差 ≤2**，上限归 `S-02a` | `example-05` 的 `P9` **由红转绿**（`{39:6}` 单值 → 极差 0），`S-02a` 接手同一缺陷 |

**升级时看 `EXPECTED_FAIL` 的两个数字**：`22`（S 组落地）→ `20`（`P9` 搬家后），
两笔分开记账，**不是放宽** —— 详见本节末尾「搬家记账」。

**本版不含什么（pull 之前先看）**：I-09 需求单共 17 条，本版交付的是**第一、二阶段的规范层 + 第三阶段的判据与反样本**。
以下**未随 0.9.0 交付**，各有登记条目、不靠这份说明兜：F3 上下文持久化（`shaping/decisions.json` 与 `prd_flow` 四个挂钩点，
`XX-042`，仓库内 0 处命中）；`check_ui_shape` 并入 CI 独立作业（`XX-036`，`ci.yml` 仍是 5 个作业）；
R1–R4 的校验器实现（`XX-041`，`validate_prd_json.py` 里 R1–R4 零命中 —— `13` 目前是**规范条文，不是闸门**）；
L-01/L-02/C-01 三条仍是人工（`XX-048`）。**判据覆盖面以 `12` 速查表的执行者列为准，不以「I-09 已交付」为准。**

### 新增

- **反样本 `assets/examples/reject-01-capa-qms/`（I-09 任务 A）**：2026-10-23 一次真实客户测试
  （新锂想 QMS · 纠正预防措施 CAPA）被判「不达标」的产物，**原样冻结**（`CAPA-PRD.data.json`
  297 354 B，`sha256 f03572560515ac22cb7c6e0593a982afb05cf5ed5344530eb949902e81f148dc`），
  外带用户当时看到的那一页截图与 `REJECT.md`（来源 / 为什么留 / 期望判定结果 / 读数陷阱）。
  **它不是教材**：教材仍是 `example-06-dense-list.json`；它只用于「让门有一样长期可复现的难看东西可判」。
  不放 `CAPA-PRD.html`（388 KB 生成物，可由 data.json 重生成）。
  位置在 `assets/examples/` 的**子目录**且以 `reject-` 开头，`check_docs` / `check_ui_shape` /
  `check_release` 的 `example-*` glob 与 `listdir` 均取不到它（`check_generators` 会多拷一份，不参与比对）。
- **`tests/measure_reject.py`（I-09 任务 B）**：反样本的四组几何量——列宽（声明率 +
  每列 `th.offsetWidth` / 可用宽 / 文字自然宽）、表头行盒数与裁切、内容宽与视口占比、
  以及「短字段（≤6 全角字 或 含 Tag/Button）单元格折行数」—— 与 P20 的分母同一个口径，免得两个工具对同一句话报两个数。
  另有 **`needW`**（这列本来需要多宽才不折：克隆**最内层**文本元素量它的 nowrap 外宽，
  按其自身字号——Tag 12px / td 13–14px，不能拿父元素字号乘字数，差 1/7 就会把放得下的列判红）
  与 **两档产品态内容宽**（复用 `productStage()` 建好的同一个舞台、只改舞台宽 1440/1600，
  不另写一套克隆，免得两份口径分叉）。
  **复用 `check_ui_shape` 的 `PROBE`（`measure()` + `productStage()`）与 `build_case_src()` /
  `run_viewport()`**，只在 `emit()` 前追加一段私有测量，不另造渲染路径（两套探针一分叉，
  门量到的和用户看到的就不是同一份 DOM）。

### 修复（量具缺陷，**不是口径变更**：阈值、SKIP 白名单、判据定义一条没动）

- **P7 把 `"52px"` 读成「未声明」**（`props_of()` 的 `float(w)`）。真实产物 CAPA 的 11 列写的是
  `"52px"` / `"330px"` 这种**带单位字符串**，`float()` 抛 ValueError → 记成未声明，于是
  「11/11 全声明 + `tableLayout:auto`」被报成「`0/9 = 0%`」，并把病因从「没锁布局」
  误诊成「没写列宽」。现按容器 `colWidthStyle()` 同一口径解析：纯数字按 px、`Npx` 取 N、
  `N%` **计入声明率但不计入 Σ 预算**（百分比与 px 不可加）、认不出的单位单独打印并按未声明计。
  修复后 CAPA 两页的 P7 都是 `11/11=100% / auto`、`9/9=100% / auto` —— **仍红，红在 `fixed` 那一半**；
  `example-05` 的 `2/7=29%` 与 `example-06` 的 `8/8=100% / fixed` 不变（V8 的 18 条逐条相等）。
- **门判了「别的页」**。旧默认按 `is_work_list_page` 取第一张「Content 直属 Table」的页：
  CAPA 的 `page-capa-list`（主表包在 `MasterDetail` 里）被跳过，门去判了 `page-capa-overdue` ——
  **同一份产物判哪页决定结论**，而两页的 `PASS` 总数碰巧都是 11，差异被盖住。
  现默认判 `meta.currentPageId`（容器开页停的那页）当且仅当它是列表页候选；`props_of()`
  在 Content 直属无表时退到 MasterDetail 的第一张表，并在 P7 的 note 里写明「主表取自
  master-detail」；报告主行新增「判页依据」，并列出「还有哪几张候选本轮未判」；
  新增 `--all-pages` 逐页全判，**分页单列计数、不跨页合并**。
  `check_docs` / `check_release` 的示例清单不受影响（非递归 glob，反样本在子目录且不以 `example-` 开头）。
- **教材 `example-06` 的 `th 序号` 被裁 4px**（866 档：列宽 48 / 可用宽 24 / 「序号」两字 28）。
  是教材的数据问题，不是量具误差——1600 档列宽 57 时不裁。按「修教材不修阈值」处理：
  `序号 48 → 54`（52 时可用宽恰好 28 = 文字宽，零余量，换个字体度量就又被裁，所以留 2px），
  `任务单号 188 → 182` 挪 6，**Σ 仍 = 866**；改的是 `gen_example06.py` 再重跑，不手改 JSON。
  重跑后 `measure_reject.py … example-06 --page page-iqc-list` 两档都是「表头：被裁 0/8 列」，
  `任务单号` 的 `needW` 161.8 仍有 20px 余量，`run.sh` 仍 757。

### 新增

- **反样本守卫 `tests/check_reject.py` + `assets/examples/reject-01-capa-qms/expected-fails.json`（I-09 任务 C）**：
  反样本必须**一直红在登记过的那几条上**，比对用**集合相等**（少红 = 判据被放宽，多红 = 新缺陷或判据变严，
  两种都要人解释）。基线**不由脚本自动写入**：`--suggest` 只打 stdout，更新基线必须是一次显式提交 ——
  自动改基线等于把守卫关掉，而且关掉之后一切看起来仍然绿。已做负例注入自证：删掉基线里一条
  `P15` → 输出「多红 1 条」且 `rc=1`；还原 → `rc=0`。
  **是否并入交付闸门、白名单怎么算，等需求单定**；本脚本暂不进 `run.sh`。

### 新增（I-09 第一阶段判据：P20–P25 + W-00 挂到 P7）

口径出处是 `references/12-visual-standard.md`（幻神写），运行层只负责实现，**阈值一条没动**：
`P1–P19` 原样、`SKIP_WHITELIST` 仍是 `P8/P13/P17`、`run.sh` 仍 757。

- **`P7` 改为承载 `W-00`**（`fixed` 与「每列 `width`」成对，缺一即 FAIL）。值改成
  `declared=11/11 (100%) fixed=false → FAIL(原因=fixed)`，理由枚举 `declared / fixed / both`。
  **不拆 P7a/P7b**：拆开之后 `0/8 + fixed` 会读出「P7b 绿」的半绿，而「只 fixed 不写 width」
  不是解法（8 列各 108px、长列被裁）。声明率阈值仍 80%（本轮不动）。
- **新增 `P20–P25`**，一条 P 只承载一条条款：
  | P | 条款 | 判据 | 为什么要单独一条 |
  |---|---|---|---|
  | `P20` | T-01 短字段折行 | 分母 = 含 Tag/Button 的格 ∪ 整格文本 ≤6 全角字的格；量**最内层元素**的 Range 行盒数，阈值 0 | 量 `td` 会把「Tag 一行 + 格内第二行空着」混进读数 |
  | `P21` | T-02 长文本出口 | 没配 `ellipsis` / `wrap+maxLines:2` / 移出表格，且渲染 ≥2 行 → FAIL | 「靠浏览器默认换行」是本文件唯一明确禁止的排版方式 |
  | `P22` | T-03 行数上限 | 任何单元格 ≤2 行，且格高 ≤ 行高×2 + padding×2 + 1 | 允许多行但没上限，T-01 就退化成「最多三行」 |
  | `P23` | T-04 表头被裁 | 分母 = 表头 ≤6 全角字的列；`scrollWidth > clientWidth+1` 即被裁，阈值 0，按档位分列 | `nowrap` 只防折行，不防裁切；失败形态变了，判据得跟着变 |
  | `P24` | W-01 列宽下限 | 声明宽 ≥ `needW = ceil(实测文本宽)+24+(Tag 16)+(可排序 20)`，另守 ≥48 | 量实测不量字数；用估算式当判据，红绿取决于估得准不准 |
  | `P25` | W-02 声明=渲染 | 逐列 `\|渲染 − 声明×k\| ≤ 2`，`k = 表宽/Σ声明` | Σ 在 fixed 下恒等于表宽，比 Σ 等于自证 |
- **`W-03` 的顺序写进代码**：`W-00` 不成立时 `P24` 判 FAIL(前置不成立) 而不是 SKIP ——
  SKIP 会让存量产物在这条上免检（与 `P18` 同一处理），而「列宽没生效」本身就不合规。
  原始读数（每列 `声明 / needW`）仍然打印，改的人不用自己再量一遍。
- **探针新增的量**（`tables[].audit[]`）：每列的 `needVal/needHdr/thW/hdrClip/hdrUnits/
  maxLines/maxTdH/shortCells/shortWrapped/multiLong/overCells`。全部**按列聚合**再回传 ——
  逐格回传会让 `#__shapeout` 的 data-json 膨胀十倍，而判据只关心每列的极值与计数。
- **容器 `R.Table` 支持列级 `wrap: true` + `maxLines: 2`**（`cell-wrap` + `cell-clamp`）。
  `maxLines` **只接受 2**：收到别的值归一成 2 并 `warn`，不静默照收 —— 3 行以上会吃光行高预算
  （`tr ≤34` 只够一行 21），而「允许多行但没上限」等于把 T-01 变成「最多三行」。

**容器「每列都有 width 就自动 fixed」的兜底：量过了，不做。** `run.sh` 757 不受影响，
但它在**渲染时把反样本修好了**：CAPA 的 `类型` 从 62 回到 72、短字段折行 `33/39 → 0/39`、
`P7` 两页由红转绿。反样本必须能复现用户当时看到的失败，所以只让 `P7` 照红，不做兜底。

### 已知（本轮只记录，不改判据）

- **形态门仍不在交付闸门里**：`run.sh` / CI / `prd_flow.py guard export` 都没调 `check_ui_shape.py`，
  所以 CAPA 那 31 条 FAIL 至今拦不住交付。要不要进闸门、以什么形式进，等需求单定。
- `P7` 已按需求单定案（`W-00` 的载体，不拆 P7a/P7b），见上。
- `is_work_list_page()`（P2b/P11/P13 的「列表页」定义）仍是「Content 直属有 Table」，
  **不认主子表式列表页**；本轮只改了「挑哪页」与「量哪张主表」，没有动这个定义。
- `P25` 的 `k` 只在「每列都有 px 宽」时做比例换算：有列没写宽（或混了百分比宽）时
  `k = 表宽/Σ声明` 不再是那个比例，换算出来的偏差是假的，此时退回原值比较。

### 新增（I-09 第二阶段：V-01 接入 + 解析拆分）

口径出处仍是 `references/12-visual-standard.md` §1（幻神 v6）；**`P1–P25` 的阈值与
`SKIP_WHITELIST` 一条没动，`run.sh` 仍 757**。

- **`V-01` 成为这条脚本里第一个三态判据**：`PASS` / `FAIL` / `INCOMPLETE`。
  `INCOMPLETE` 只在**量具不可信**时出现——内容盒宽为 0、父节点 `clientWidth=0`（不可见）、
  导航宽为负——它**既不记 PASS 也不记 FAIL**：记 PASS 是静默绿，记 FAIL 是把量具 bug 算到产物头上。
  `main()` 单独计数并退非 0（`RESULT INCOMPLETE`），`run_one()` 多回传一个 `inc`。
- **只在产品态量**：评审态画布只有 1122 宽（工具外壳 + PRD 面板），拿它算这条式子等于
  让产品为一个它控制不了的侧栏买单。`productStage()` 因此接受舞台宽：`P2a` 仍固定
  1440×900（那就是它的判据），`V-01` 按当前视口宽各建一次。舞台**留在 DOM 里**
  （`measure_reject.py` 的 `rejectExtras()` 要按 id 取它改宽量两档），下次调用先拆旧的。
- **实测四行产物（两条判据的两档读数全 0）**：
  | 产物 | 1440 归因差 / 铺满差 | 1600 归因差 / 铺满差 |
  |---|---|---|
  | `example-06` | 减法 `1440−1232=208` / 真实 `208` → **0** ｜ **0** | 减法 `1600−1392=208` / 真实 `208` → **0** ｜ **0** |
  | CAPA `page-capa-list` | 减法 `1440−1440=0` / 真实 `0` → **0** ｜ **0** | 减法 `1600−1600=0` / 真实 `0` → **0** ｜ **0** |
  | CAPA `page-capa-overdue` | 同上（导航在壳里，产品态无页内导航） | 同上 |
  口径自证行同时打：`内容1184+padding48=1232 vs offsetWidth1232 差+0`（CAPA `1392+48=1440`）。
  **这个断言不能拿 `clientWidth` 做**：① 减掉的 padding 正是 ③ 加回来的，`①+③ ≡ clientWidth`
  是定义恒等式、永远为真 —— 那是一条恒绿判据。改成对 `content.offsetWidth` 差 ≤3px（`offsetWidth`
  含 border、`clientWidth` 不含 border 也不含滚动条，±3 是这几项差异的上界），超了打
  `BORDER_OR_SCROLLBAR` 标签；**不许把式子改成 `offsetWidth + border + scrollbar` 去凑读数**。
- **`INCOMPLETE` 的原因固化三个 TOKEN**：`CONTENT_ZERO` / `PARENT_INVISIBLE` / `NAV_OUT_OF_RANGE`，
  输出固定 `INCOMPLETE(口径错) 原因=<TOKEN>`。守卫按 **TOKEN 相等**断言，不按条数 ——
  「条数相同、集合不同」这坑本仓库踩过（CAPA 两页 FAIL 数都是 21，红的却各是各的）。
  三条各有一条造红注入（`.ant-content{display:none}` / `.ant-layout.h{display:none}` /
  内容 `min-width:900` 塞进 600 父盒 → 导航宽 `600−900=−300`）。
  这一档连判据②都会红（父宽 600 ≠ 视口 1440），所以 **INCOMPLETE 必须排在两条判据前面** ——
  否则「父节点选错了」会被记成产物的 `cause=N-c`，量具 bug 记到产物头上。
- **主判据换成「归因差」，闭合式降级改名「父节点铺满」**（本轮最重要的一次改动，team-lead 裁定）：
  把 `①内容宽 + ②导航宽 + ③padding` 展开即得 `①+②+③ ≡ 父.offsetWidth − b`
  （`b` = content 左右 border）——**只要父节点没被换掉，闭合差恒为 0**。它判的从来是
  「父节点有没有铺满视口」，不是「内容宽有没有适配」；`max-width:1024` 下被压窄留下的空档 416
  会被减法式当成导航宽（`1440−1024=416`），三数之和仍是 1440、闭合差 0 **判绿**。
  **一条恒等式不能当判据。** 现行两条式子、结论只看第一条：
  | | 式子 | 判什么 |
  |---|---|---|
  | **归因差**（主判据） | `abs(减法导航 − 真实导航) ≤ 8` | 丢掉的宽度**是不是被导航合法占走**（`N-a`/`N-b` 靠这条红） |
  | **父节点铺满**（副判据，原闭合式改名） | `abs(父.offsetWidth − b − 视口) ≤ 8` | 父节点有没有被**换小**（`N-c` 靠这条） |
  真实导航 = **横着占位、且与内容并排**的同级兄弟宽之和，判据是**纯几何三条**：
  ① 纵向重叠 `r.top < c.bottom && r.bottom > c.top`；② 水平不相交
  `r.right <= c.left+1 || r.left >= c.right-1`；③ `position ∈ {static, relative, sticky}`。
  **不看 class**：`Sider`/`Menu` 是 class 约定，自定义元素做导航时白名单会算成 0
  （减法 208 − 真实 0 = 误红 208）。代入验：`div.ant-sider` 208 ✓；CAPA 的 `div.ant-header`
  纵向不重叠 ✗（不判重叠会求和成 1440、合格产物被判 FAIL）；打开的抽屉 `absolute` 被 ③ 排除。
  内容区**没有**任何纵向重叠兄弟时，真实导航 = 0 是**正常**（全宽内容区），**不许**因此报 INCOMPLETE ——
  「找不到导航」和「没有导航」在实现里长得一模一样，但前者该报错、后者该放行。
  视口口径**钉死 `window.innerWidth`**（含滚动条），与 `父.offsetWidth` 同口径；用
  `documentElement.clientWidth` 在有纵向滚动条时恒差 15px = **静默红**（比静默绿更难查）。
  归因差超 8px **不许加容差**；`MISMATCH` 标签**取消**——归因差不成立本身就是红，不需要再挂一个
  「两数不一致但结论照旧」的旁注（那是恒等式判据留下的补丁）。`parentElement` 与 `offsetParent`
  不一致只打 `PARENT_MISMATCH`：交叉校验，**不是判据、不是 INCOMPLETE、不进 TOKEN 表**。
  输出行（两条式子都打，三数和只作展示）：
  `V-01 1440 父节点=div.ant-layout.h 宽1440 内容1184 导航208[减法 1440−1232 / 真实 208 归因差 0] padding48 归因差0 铺满差0 ｜ 三数和1440(恒等，只作展示)`。
- **`N-e` 降为诊断行，不判红**（team-lead 裁定）：`N-e 诊断: 内容宽 1184→1344 增量+160 / 视口增量160（不判红）`。
  它唯一能单独红的输入是「两档 padding 不同」（`@1440 padding:24` / `@1600 padding:30` → 增量 148≠160），
  而屏幕变宽多留白是**正当设计**；它想抓的「两档都写成常数」已由归因差 @1600 抓住
  （内容锁 1184 → 减法 416 / 真实 208 → 归因差 208）。一条只在合法产物上红的判据会逼下一个人
  去加容差，**比恒绿更糟**。不占编号、缺陷计数 0、FAIL 集不受影响。
- **`N-d`（zoom / `transform:scale`）独立判红**：缩放把布局宽与 `clientWidth` 解耦，
  `zoom:.9` 下闭合差仍是 0。归因差这一档**也能**红（实测 `内容1321 导航71 归因差137`），
  但它只说得出「有宽度不知去向」，说不出「是测量被改掉了」——`cause=N-d` 仍然要留。
- **`cause` 值的通用纪律**：每一条 `cause`，要么有输入能产出它，要么在文档里写明「不可达」及原因。
  `N-a`/`N-b`/`N-d` 各有自证注入；**`N-c`（外层换壳）在产物空间内不可达** —— 容器把
  `Layout.props.style.width` 直接落到节点上，而 `R.Layout` **根本不消费 width/style**
  （实测给 Layout 加 `props.style.width=1200`、`props.width=1200`，父节点仍是 1440），
  产物写了宽只会走 `N-b`；换壳只能来自容器代码自己。
  **`N-b` 现在同样不可达**（本轮实测）：`R.Content` / `R.Layout` 都不消费 `width` / `style` ——
  给 Content 加 `props.width=1080` 与 `props.style.width="1080px"`，内容宽都还是 1184；
  `n_b_width_hits()` 只读 JSON，所以它今天是个**定位器**、不是可达分支。规范里 N-b 那行
  （`1080` → 内容 1032 / 减法 360 / 归因差 152）是**代数读数**，不是实测 —— 能实测的只有
  N-a（`V01_maxw`：归因差 208）。容器哪天开始消费 `width`，这两条才活。
  **但它不再只是「记账」**：另配手写 HTML 壳样本 `tests/fixtures/fixture-nc-manual-shell.html`
  （**非容器产物**，名字里标出来，`example-*` 的 glob 取不到），内联 `width:1100px` 包住内容区，
  断言**两条式子都要比对**：`归因差 0 ｜ 铺满差 340`。那个 0 才是样本存在的理由 ——
  它证明「归因差覆盖 N-c」是错的（壳一包，减法与真实同时变 0、互相抵消）；只贴「340 红了」等于没证。
- **自证覆盖 16 → 24 条**（需求单要求「n 含全部新增条目」；本轮再补 `P2a`/`P2b` 两条 → **26**，见下一条）：补上此前**从未红过**的三条——
  `P7_fixed_off`（`tableLayout:auto` → `FAIL(原因=fixed)`）、`P7_decl_low`（摘两列 width →
  `6/8=75%` → `FAIL(原因=declared)`；**只摘一列是 87.5%，会 PASS**，注入必须打到 80% 门槛以下）、
  `P21_no_exit`（摘 `ellipsis` 并强制换行 → 无出口长文本列被抓）、`P22_exceed`（压到 48px →
  3 行以上），加上 V-01 的 `V01_zoom` / `V01_maxw` 与三条 `INCOMPLETE` 造红，
  以及 N-c 手写壳样本一条（`tests/fixtures/fixture-nc-manual-shell.html`，归因差 0 / 铺满差 340）。
  这条样本**不进 `INJECTIONS`**：它改的是整份 DOM 而不是 JSON/CSS，塞进「基线产物 + 注入」那套循环里，
  P1–P25 会一起把手写壳当产物判，翻红清单全是噪音，要证的那对数会被淹掉。
  **P22 此前只是 T-01 注入的「允许连带」，那是旁证不是证据** —— 顺带把一个坑写进代码：
  `P7_decl_low` 与 `P21_no_exit` 的连带红（auto 布局下七八条判据读数同时变）不是判据重叠，
  而是「布局没锁时下游读数全部失去意义」——这正好说明 W-00 为什么是前置。
- **`main_table()` 改名 `resolve_list_table()`，与 `is_work_list_page()` 拆开**：
  前者答「哪张表是主表」（任何页都该能答，只用于取原始量），后者答「算不算作业型列表页」
  （形态类判据的适用范围，**定义一个字没动**）。验收：CAPA `page-capa-list` 11 列
  （source=master-detail）、`page-capa-overdue` 9 列（content-direct）；
  `example-06` 外包一层 `MasterDetail` 后仍取到 8 列主表，`is_work_list_page` 仍按原定义返回 `False`。
- **`P24` 的分母改口径：按「可断性」判，`0/8` → `0/6`**（team-lead 裁定，本轮唯一的读数变更）。
  `needW` 的语义是「放得下一整条不可断的内容」，这条语义的判据**不是字数、更不是渲染行数**，
  而是这列的值里有没有**可断点**：① 空格分词 ≥3 个；② 连续 CJK >6 字。两条都不成立 = token。
  **不能用「渲染 ≤1 行」当分母**（我第一版就是这么写的，被否）：行数由**被修的列宽**决定 ——
  列越窄越折行，越会被判成长文本列而**出分母**，于是「越坏的列越免检」；这与
  `Σ col.offsetWidth ≡ 表宽` 同一族毛病：拿结果当判据的输入。
  新分母 = 未声明出口 **且** 值不可断的列。`example-06` 代入：`序号/任务单号/批次号/取样·样品/状态/操作`
  六列进（token），`物资名称/质检标准` 出（声明了 `ellipsis`）→ 仍 `0/6`，数与分类依据都对。
  `任务单号`（`IQC-20261018-0342`，19 个半角字）**留在分母里**：它按字宽会被判成「长文本」而漏掉，
  可它正是 W-01 该管的列 —— 一个不可断的编码放不下就只能裁。
  输出带排除说明：`低于下限 0/6 列；另有 2 列声明了出口（物资名称 ellipsis、质检标准 ellipsis），不入分母`，
  值可断的列另计 `另有 N 列值可断（长文本，归 T-02/T-03：…），不入分母`；
  **三数（needW/声明/渲染）对所有列照打**，只是不计入分母 —— 不打，下次有人会以为这两列没量过
  （诊断信息不随分母缩水）。
  前置红改为 `FAIL(cause=prereq:W-00)` 并在值里带**声明侧**读数
  ——声明值在 JSON 里、与布局无关，这一半永远可判。
- **`P2a`/`P2b` 的行数前置改成「单轨 + 用 `total` 判造少」（XX-045）**：
  原先「行数 <20 就 SKIP」，且 SKIP 不带条件 —— 那让 `assets/examples/` 里 6 行的教材永久免检。
  新规则一条、两种结论，**靠事实分**：
  ```
  允许 SKIP   ⟺ 示例行数 < 所需 且（无分页器 或 total < 所需）
              → P2a SKIP(行数 6 < 14，total 未声明)
  INCOMPLETE  ⟺ total ≥ 所需 且 示例行数 < 所需
              → P2a INCOMPLETE(INSUFFICIENT_ROWS) total 1286 ≥ 14，行数 6
  ```
  ① 不按「谁给的文件」判（同一份文件换个目录结论就变 = 身份判定）；
  ② `total` 是 `P13` 已在读的现成字段，正是 `REJECT.md` 那条「少造数据换 SKIP」的正面回答；
  ③ 教材与产物一视同仁。**`INCOMPLETE(INSUFFICIENT_ROWS)` 是 P 组自己的 TOKEN**，
  与 V-01 的 `CONTENT_ZERO`/`PARENT_INVISIBLE`/`NAV_OUT_OF_RANGE` 并列但不混用。
  V13 白名单随之**条件化**：`skip_allowed()` 看 SKIP 值里有没有 `SKIP(行数 N < 所需，…)`，
  **不只看 id** —— 只按 id 放行等于把「少造几行」变成通行证。
  实测三条验收：补到 14 行 → `P2a PASS / P2b PASS@1600、FAIL@1440`（不再 SKIP）；
  去掉分页器 → `SKIP(行数 6 < 14，total 未声明)`；`total:342` → `INCOMPLETE(INSUFFICIENT_ROWS)`；
  同一份文件放 `/tmp` 再跑结论相同。
  **顺带暴露一件事（要人定）**：`example-05` 自己写着 `pagination.total = 1286`，却只渲染 6 行，
  按新规则它是 `INCOMPLETE(造少)` 而不是 SKIP —— 全量模式因此仍是 `RESULT INCOMPLETE`，
  原因从「白名单外 SKIP」变成「教材自己声明了 1286 条、只造了 6 行」。
  **（已定，见本段 `XX-046`：`total → 6`，2026-10-26；此处保留的是当时的现场描述，不要当待议项读。）**
- **`P23` 的三类排除分别计数**（不加总）：
  `被裁 0/10 列@1234；另有 1 列表头 >6 全角字、2 列空表头、0 列无裁切盒，不入分母`。
  三类分别是「表头太长（归 T-03 + `ellipsisTitle`）」/「空表头（`rowSelection`/`radio` 槽位，
  永远不可能红）」/「没有 `overflow-x:hidden|clip` 的裁切盒（本条不适用，不是量过没裁）」——
  合成一个「另有 N 列」时，看报告的人分不清「判据放过了它」还是「它根本不适用」。
  零也照打，否则 `0/9` 与 `0/10` 的差别没人看得见，下次有人改成 0/10 也没人发现。
  **`P23` 的分母仍是「表头 1~6 全角字」，与 `P24` 的值可断性是两套口径**（一个量表头标签、
  一个量列值），不合并 —— 合并只会让其中一条错。
- **`P25`（W-02）的条文语义写成「每列是否按同一个比例缩放」**，不是「允许偏差 ≤2」；`k` 必须进报告；
  `@866 k=1.000` 时与原式**逐字节等价**（这是「没有放宽」的唯一证据）；**`k` 的合法性不归本条**
  （8 列全声明 100、Σ=800 时本条也应 PASS）。并写死一条禁令：**不许顺手判 `abs(Σ声明×k − 表宽)`** ——
  `k` 由 `表宽 ÷ Σ声明` 推出，这个断言恒真，判它是拿定义当判据（与 P17 的
  `Σ col.offsetWidth ≡ 表宽` 同一个陷阱）。
- **`REJECT.md` 加第 6 条纪律**：任何在渲染期自动修正产物缺陷的兜底，都会同时解除反样本的复现能力。
  兜底前必须先在反样本上跑一遍；改绿了就不许进容器，要留在判据侧（理由用「自动补 fixed」那次的实测：
  `类型` 62→72、折行 `33/39 → 0/39`、P7 两页转绿）。同时把 §4.3 的 P24 标成
  「**(前置) 由 P7 引起，不计入独立缺陷数**」——回归基线允许一条病红两次，缺陷计数不允许。
- **`measure_reject.py --th-span`（T-04 锚点自证）**：把每个 `th` 的文本包一层 `<span>` 再量，
  并与**不包 span 的那次逐档比对**（同一个脚本跑两遍，不靠人手动跑两次）：
  教材 `0/8 → 0/8`；把 `序号` 改回 48 的负例 `1/8 → 1/8`。
  若锚点还是「最内层元素」，inline 的 `clientWidth/scrollWidth` 恒 `0/0`，负例会读成 `0/8`
  —— 这一对数是唯一能证明锚点选对了的输入。
- **`expected-fails.json` 的 `_meta` 措辞改成「期望、不是现状快照」**：并在
  `measured_with` 里写明「V-01 接入后 CAPA 四组全 PASS、FAIL 集一条未动，**因此本次不重登**
  ——重登只会把同一份期望抄一遍，抄的动作本身就是把「期望」变成「快照」」。
- **`--selfcheck` 覆盖 24 → 26 条：`P2a`/`P2b` 的第三态各补一条注入**（幻神裁定：断言按 TOKEN 相等）。
  这两条判据的 SKIP / INCOMPLETE **不进 FAIL 集合**，只比「注入后多了哪几条红」等于什么都没证 ——
  「少造几行换一个 SKIP」在自证里也会是绿的。所以新增断言形态 `want_rows`：
  **按 `(状态, 值)` 相等**，值用正则整串锚定（不比中文尾巴，但必须锚住括号里的 TOKEN 与实测数）。
  - `P2b_rows_skip`：砍到 6 行**并摘掉 `total`** → `P2b SKIP(行数 6 < 9，total 未声明)`；
  - `P2b_rows_total`：只砍到 6 行、不动 `total`（`example-06` 自己写着 342）→
    `P2b INCOMPLETE(INSUFFICIENT_ROWS) total 342 ≥ 9，行数 6`。
  两条成对存在：摘掉 total 那一支才是 `SKIP`，留着 total 才是「造少」——
  只有一条的话，「SKIP 与 INCOMPLETE 的分界」就只剩文档里那句话。
- **发布门 9 → 11 项：反样本守卫 + 形态判据进闸门（DoD 10 / DoD 11）**（team-lead 裁定，发布门口径变更）。
  CAPA 反样本能到 `PASS=11 FAIL=21` 还发得出去，不是判据没做，是**闸门里没有它** ——
  与「四处 ERROR 无人实现」同型：规范写了、代码零命中。
  - **DoD 10 `check_reject_guard()`**：调用 `tests/check_reject.py` 的 `main()`（比对面「集合相等」
    只写在这一处，不复制），**rc 三义分开**：`0 → PASS`（逐条相等）/ `1 → FAIL`（集合不符、基线没登记）/
    `2 → ENV`（Chrome 找不到）。混色的后果与 E-01/E-02/E-03 同型：Chrome 没装会被读成「反样本没问题」，
    或反过来把真缺陷藏进「环境问题」。detail 自证：`pages=2 逐条相等（15/15 16/16 16/16 12/12）｜页 …`；
    **不符那档也必须进括号**（`16/15✗`）—— 全是相等对的括号会把 FAIL 读成「多了一个通过项」，
    第一版正是这样：解析只认相等行，恰恰把不符那档漏掉了。
    `rc=0` 但解析不到任何逐档比对行 → **FAIL**（比了 0 条不许算通过）；
    `import check_reject` 失败单独成一句 FAIL（与「守卫发现反样本变绿」处置相反：一个修路径/环境，
    一个改产物或改基线，同色就是让读的人自己猜）。
  - **DoD 11 `check_shape_gate()`**：目标**写死** `assets/examples/example-06-dense-list.json`，
    不跟着 `default_targets()` 走 —— 哪天 example-06 掉出默认目标，门会安静地去判别的文件还说 PASS。
    detail 自带 scope，防止被读成「全量通过」：
    `fixture=example-06-dense-list.json rc=0 PASS=55 FAIL=0 SKIP=1 ｜ 唯一 SKIP=P17「列宽预算闭合（验收态 866）」｜ 未判：其余示例（全量模式另跑）`。
    （标题里那对括号是**范围信息**——P17 只判 866 档；削掉它这条 detail 就答不了「判的是哪一档」，
    所以嵌套时改**外层括号**形态，不删标题内容。）
    那条 `SKIP=1` **必须点名**：`skip_allowed()` 的静态白名单只有 `P8/P13/P17`，`P2a/P2b` 靠值里的
    `SKIP(行数 N < M，` 条件放行；哪天那 1 条换了**理由**、id 还在名单里，行数与结论都已不同。
    所以「数得出 SKIP 条数却点不出是哪一条」直接判 FAIL。
    `rc=2` 的两种来源分开：`find_chrome()` 抛 → ENV；`main()` 的「没有可跑的产物」→ **FAIL**
    （那是产物/路径缺陷，映射成 ENV 就把它藏进「环境问题」）。`rc=1` 时 `RESULT INCOMPLETE`
    与 `RESULT FAIL` 都映射 FAIL，但 detail 带原句。
  - **编号只追加不插队**：DoD 10/11 排在 9 之后，1–9 的编号一个字没动 —— `release.md` 与历史交付说明按编号引用。
    另**不并进 `run.sh`**：`run.sh` 的语义是容器回归（757 基线），退出码三义已定，混进去就分不清了。
  - **两项各自 status、各自 detail**，不出现「检查通过」这种合并结论（INV-13）。
- **`DoD 2` 偶发红必须留下 CASE 名（四支判定）**：`run.sh` 是确定性断言，确定性测试偶发红
  只可能是环境噪声，或 CASE 自己非确定（时间/随机/顺序依赖）—— 两种都得先拿到 CASE 名才谈得上修。
  原来的 `first_lines(text, 8)` 取的是**开头 8 行**，而失败信息在末尾，于是那条偶发红一个字都没留下
  （「没有输出 ≠ 没有失败」的现场版）。现在：
  - 摘要抓含 `FAIL` / `✗` / `CASE` / `Error` 的行（取前 8 行），抓不到再退回最后 5 行；
  - `rc=1` 时**再跑一次**，两段摘要都打印（`RUN1 └` / `RUN2 └`），**不许只留第二次** —— 那是用重跑换绿；
  - 判定五支：都绿 PASS ｜ 都红且首个失败 CASE 相同 **FAIL**（确定性红）｜ 都红但 CASE 不同 **ENV** ｜
    一绿一红 **ENV**（本轮不可信，**不是**"重跑后绿了"）｜ 有 `SAFE_DELETE` 拦截 **ENV**（原分支保持）；
  - `rc∈{2,3}`（run.sh 自己的环境/锁）仍直接 ENV，不重跑。
  自证：纯函数 `_two_run_verdict` 逐支断言，另用**有状态假 run.sh**（第一次红、第二次绿）走真 subprocess
  路径，断言 `ENV 一绿一红` 且两段摘要都在。
- **接线自证「会红」**（只证明新增项是绿的，等于没证明）：
  - DoD 10：往 `expected-fails.json` 某档塞不存在的 `P99_not_exist` →
    `FAIL  pages=2 有 1 档不符（16/15✗ 16/16 16/16 12/12）`、`少红 1 条：P99_not_exist`，其余十项状态不变 → 还原；
  - DoD 11：临时把目标改成 `reject-01-capa-qms/CAPA-PRD.data.json` →
    `FAIL  fixture=CAPA-PRD.data.json rc=1 PASS=15 FAIL=31 SKIP=10 ｜ 原句：FAIL` → 还原。
  - 现状如实：`RESULT FAIL 10/11（未通过：安装副本同步）｜TREE DIRTY(n)` —— 旧的那条真红没变，
    新增两项绿，**不拿它把整体包装成绿**。
- **`example-05` 教材数据自洽（XX-046）：采纳「改 `total`」，否决「补数据」**。
  做法：`gen_example05.py` 的 `pagination` 由 `total:1286 / pageSize:10` 改为真实行数 6
  （代码写 `len(ORDER_ROWS)`，total 与 pageSize 同源），重跑生成器出 JSON，**不手改**。
  根因不是「少写几行」，是 **`total` 一个字段承担两个语义**（分页演示 / 数据量证据，`P2a/P2b` 读后者）——
  同族：`width` 声明 vs 渲染、`Σ col.offsetWidth ≡ 表宽`。
  **① 补数据被否**：`ORDERS` 六条 `status` 是 `草稿/待审批/已审批/部分到货/已关闭/已取消`，两两不同且与
  `STATUS_COLORS` 六键一一对应；补到 14 行进来的只能是**重复状态** —— 那是改掉这份「行为模型」
  教材的用途，不是修数据。`pageSize` 必须一起改：`pageSize 10 > total 6` 本身自相矛盾。
  - **`P13@1440/1600` 移出 `EXPECTED_FAIL`，这是「条件消失」，不是判据放宽**：`P13` 的
    `total < 100 → SKIP`（`:1931`）先后被假 `total` 挡住，真实 `total=6` 时「`pageSize ≥ 20`」
    这个要求根本不成立（一页放 6 条就是全部）。阈值一个字没动，`SKIP_WHITELIST` 也没新增 P13。
    **不写这句，V8 少 2 条读起来就是「改样本换绿」**。
  - `P2a/P2b` 从 `INCOMPLETE(INSUFFICIENT_ROWS)` 变
    `SKIP(行数 6 < 所需，total 6 < 所需)`（`P2a` 所需 14；`P2b` 按档 9/12，各自传自己的 need）；
  - `P16` 仍 PASS —— 容器 `index.html:1757` 只看 `pagination` 这个 prop 在不在（对象为真），
    `total/pageSize` 改了也照渲分页脚，所以不落 `SKIP(无分页脚)`；
  - **验收口径（team-lead/幻神重写）**：全量模式**不得出现** `INCOMPLETE`、**不得出现**
    `SKIP-OUT-OF-WHITELIST`、**V8 FAIL 集逐条相等** —— 达标看这三件，**不看结论行颜色**。
    `RESULT FAIL` 是预期结论（example-05 还有 **22** 条登记红：原 18 条 + I-09 第三阶段 S 组新增 4 条，
    见下），不许为它变绿去改判据或把
    example-05 摘出 `default_targets()`（那是把登记红样本踢出覆盖）。
- **结论段不再早退（XX-047）**：原来 `bad_skip → tinc → v8_bad` 三级 `return 1`，
  后果是**只要有一条 INCOMPLETE，V8 的比对结论就永远进不了结论段** —— example-05 造少那段时间
  正是如此，「红的是不是该红的那几条」被一句 INCOMPLETE 压掉了。现在抽成 `conclude()`：
  三条事实先全部算完，第一句按优先级（判据没跑 > 量具不可信 > V8 不符），**其余事实同段打出**。
  文案改成两个数：`3 行 INCOMPLETE（P2a、P2b）` —— 只打条数时「2 判据 × 2 档 = 4」会被读成
  「4 条判据」，幻神就是这样误判「P2b 的分母也是 14」（实际 `TARGET_ROWS_REVIEW = {1440: 9, 1600: 12}`，
  `_rows_gate` 由调用点各自传 need）。自证 26 → **27** 条：构造**同时**有 INCOMPLETE 与 V8 不符的输入，
  断言结论段**两个关键词都在**（只断言一个，早退回来照样过）。
- **`P2a/P2b` 条件式 SKIP 的常驻自证（27 → 28）**：样本 `tests/fixtures/fixture-p2-rows-skip.json`
  （6 行、`pagination` 里**只有 `pageSize`、没有 `total` 键**），每次 `--selfcheck` 都重跑，断言三行
  `(状态, 值)` 精确对 —— `P2a@1440 SKIP(行数 6 < 14，total 未声明)`、
  `P2b@1440 SKIP(行数 6 < 9，…)`、`P2b@1600 SKIP(行数 6 < 12，…)` —— 外加**该行不在 `bad_skip` 里**。
  少后半句就是同义反复：证明「它会 SKIP」不等于证明「这个 SKIP 有正当条件」，而 V13 的理由是后者。
  样本放 `tests/fixtures/` 不放 `assets/examples/`：后者每多一份要同步 `check_docs.EXPECTED_EXAMPLES`、
  `README` 引用、`check_generators` 的 `gen_exampleNN.py` 三处；`default_targets()` 只 glob
  `example-*.json`，放 `fixtures/` 也不会被全量模式收进去。
  四种 `pagination` 写法里只有两种同时满足「有分页脚」与「total 未声明」：`{"pageSize": 6}` 或 `true`；
  `{"total": 6, …}` 挂正则（值变 `total 6 < 14`），不写 `pagination` 挂 P16（裸 `SKIP(无分页脚)`，不在白名单）。
  **不靠整轮 `RESULT PASS` 收货**：`default_targets()` 里有 example-05 的登记红，全量模式结构上不可能 PASS。
- 第一阶段的 `V-01` 只做式子验证、不做判据（需求单第二阶段）；第二阶段已接入（见上）。
  `cause` 的定位仍在一套算式里，没有另立阈值；`N-c` 不可达的理由见上一条通用纪律。

### 新增（I-09 第三阶段：S-01 / S-02a / S-02b，先量后定阈值）

**这一步的来历**：`references/12` 把 S-01/S-02 标了 `人工`，不是没写，是阈值来源从没被实测过
（`12:38` 写死这条禁令）。所以先补一份**只读量具** `tests/measure_type.py`（不进 `run.sh`、
不占编号、输出里没有 PASS/FAIL/阈值），在三份产物 × 四态上出分布，再按分布定判据。
量具的分母自证两处：`文本节点 = 空文本 + script/style + 无盒 + 同元素重复 + 计入分母`；
`S-02② 表格内文字 + 表格外文字 = 分母`。对不上就是分母漏项，不用靠感觉。

- **S-01 判集合，不判档数**。`12` 原文「≤3 档 **且** ⊆ {18,14,12}」里，前半句是**恒真条款** ——
  子集 ⊆ 三元集已蕴含档数 ≤3（同族：`①+③≡clientWidth`、`Σ(声明×k)≡表宽`）。
  只数档数会放过 `{11,13,15}`（3 档全错）；只判集合才问得出「是哪些值」。
  **example-05 是这条判据的现成负例**：字号集合 `{12,13,14}` 是 3 档，`P19`（≤3 档）绿，
  `S-01` 红 —— 这就是「档数判据会放过 3 档全错」的实例。档数、主档占比降为读数打印
  （占比不适合当判据：连续量、阈值只能拍，且会把 CAPA 里 1 个 11px 的箭头稀释到看不见）。
  与 `P19` 是**已知重叠**，`S-01` 更强；本轮 `P1–P25` 冻结，`P19` 一个字没动。
- **S-02a 只判「单行行」的行高**。`T-02` 允许 `wrap + maxLines:2`，而合规两行行必然 >34
  （14×1.57×2+padding≈58）。对全部 `tr` 判 ≤34 会把合规两行判成缺陷 —— CAPA `page-capa-list`
  的 `58/68/78` 就是这件事。分母 = 行内文本行盒数 == 1 的数据行；分母 0 走
  `SKIP(分母 0：无单行数据行…)`，加进**条件式**白名单（看值里的条件，不看 id）。
  行盒数**按每个文本节点各自量**：对整格 `selectNodeContents` 取 rects 会把单元格盒子自己
  也算一个 rect，单行格全被读成 2 行（实测 example-06 的 20 行全变「多行」，分母直接变 0）。
- **S-02b 的「正文」排除控件与标题，且两类各自计数**。控件（`button/.ant-btn`）的
  `line-height:1` 是控件规范值；标题（h1–h6）的紧行高（1.44）属标题 token。不排除时三份产物
  会各红 6/4/3 条 —— **全是按钮**。比值分母是 `font-size`，不是行盒高。区间 `[1.40,1.60]`
  沿用 `12 §S-02`，本轮不新定阈值。
- **新增判据全部配了能红的注入（自证 28 → 31）**：`S01_size_19`（按钮 14→19，集合多一档）、
  `S02a_row_high`（td padding 加到 14，单行行 34→52）、`S02b_line_height_1`（正文标签
  `line-height:1`，正文比读成 1.00）。**S-02b 在三份产物上本来就全绿，没有这条注入的话
  「它判了」和「它永远绿」在报告上完全一样。**
- **两处基线显式重登，逐条写「新判据抓到的既有缺陷，不是判据变严」**：
  `EXPECTED_FAIL` 增 `S-01@1440/1600`、`S-02a@1440/1600`（example-05：13∉集合；单行行 6 行全 39>34）；
  `reject-01/expected-fails.json` 增 list 两档 `S-01`、overdue 两档 `S-01` 与 `@1600` `S-02a`
  （overdue@1440 的 S-02a 是分母 0 → SKIP，不进 FAIL 集）。
- **顺手登记一处「期望本身有误」**：CAPA `page-capa-list` 的 12 行**全部是 ≥2 行盒**，按 S-02a 的口径
  `P9`（极差/最高 ≤34）在它上面是**假红**。本轮 `P1–P19` 冻结，所以 `P9` 仍留在期望集里 ——
  这条写进 `expected-fails.json` 的 `relog_2026_10_26_s.watch_out`，否则下一轮会以为 S-02a 与 P9 冲突。
- **读数变化（全量模式，第三阶段收口后实测）**：`TOTAL PASS=83→93`、`FAIL=18→20`、`SKIP=11` 不变；
  `V8 20/20 逐条相等`；无 `INCOMPLETE`、无 `SKIP-OUT-OF-WHITELIST`；`RESULT FAIL` 是预期结论
  （来自 `example-05` 的 20 条登记红，不是门坏了）。
- **没动的**：`P1–P25` 的**阈值**、`SKIP_WHITELIST` 静态三项（仍 `P8/P13/P17`）、
  `run.sh` 的 `CASES` 与 `-ne 757`（`run.sh` 走 `tests/harness.js`，与 `check_ui_shape` 不是一套）。
- **`references/12` 速查表第 10/11 行已由 `人工` 翻成 `shape`**（幻神，`8f76c8d`）：
  `S-01` 与 `S-02a / S-02b` 三处执行者与代码一致；`L-01`/`L-02`/`C-01` 三行仍是 `人工`，属下一轮。
- **`P9` 与 `S-02a` 的分工已落地（team-lead 本轮明示解冻 `P9`，只改判据形态）**：
  删 `mx <= ROW_MAX_H`（上限归 `S-02a`），只判**组内**极差、按行内行盒数**逐值**分组
  （`p9_by[int(lines)]`，不是「单行 / 多行」两桶 —— 两桶会把 `2 行盒 n=1 + 3 行盒 n=1`
  写成「多行 2」，读起来像存在 n≥2 的组）。两条条件式 SKIP：
  `SKIP(有效数据行 N < 2，无表格数据行)` 与 `SKIP(无任一行盒组 ≥2 行：<逐值组清单>)`，
  `skip_allowed()` 按 **id + 值前缀**放行，**`P9` 不进静态白名单**。
  实测（`P9_row_spread` 注入，20 行）：奇数行 **56** / 偶数行 **34** / 同组极差 **22**，该组 n=20。
  `S02a_row_high` 的 allow 已去掉 `P9`（全行等高时组内极差 0，它不该红 —— 留着会把改对的行为判成回归）。
- **搬家记账（两笔分开，不是放宽）**：`EXPECTED_FAIL` `20 →（S 组落地）22 →（P9 移出）20`；
  移出的是 `P9@1440`、`P9@1600`，`S-02a` 早就在名单里，所以是**净 −2**。
  反样本侧四档同步移除 `P9`（list 17→16、16→15；overdue 14→13、17→16），
  每组的 `(行盒数, n, 极差)` 写死在 `relog_2026_10_26_p9` 里。
  **CAPA 的 `58` 与 `78` 是不同组**（2 行盒 / 3 行盒），旧口径那个 20 差正是跨组差，
  逐值分组后它不进 `P9` —— 这是「跨组极差不是判据」的实例，不是把红藏起来。

## [0.8.0] - 2026-10-22

**breaking: 否** —— 没有新增必填字段，存量 PRD 升级当天不会因为缺字段报错。两处**可见默认态**变了
（列表页开页默认折叠 PRD、抽屉按声明宽渲染），都有恢复路径（点右上角「PRD」/「全宽预览」；抽屉本就没声明宽的不变），
且都是把「声明了什么就渲染什么」这件事补齐，不是改产品形态。

### 新增

- **`tests/check_ui_shape.py`（XX-030，P1–P19）**：作业型列表页的形态与密度门。每视口 21 行
  （P3 拆 P3a 栅格 / P3b 总高），两档视口（1600×1000 → 内容宽 1026；1440×900 → 866）。
  关键判据：一屏整行数（产品态 1440×900 与评审态两档分开报）、筛选区两行三列与控件宽**预算制**
  （列宽−84 ±2 且 ≥160）、行高 ≤34 且跨行极差 ≤2、固定表头、列宽预算闭合（声明 = 渲染 ±2）、
  省略号「配了的集合 == 真溢出的集合」、页内字号 ≤3 档、评审态默认 pane 宽。
  `--selfcheck` 10 条反例注入 + 覆盖不足判 `INCOMPLETE`；`V8` 把 example-05 的期望 FAIL 集**逐条写死**比对；
  `V13` 把 SKIP 白名单化（只允许 P8/P13/P17，越界 `RESULT INCOMPLETE` 并非 0 退出）。
- **密度档 `.ant-table.xs`（D1）**：14px / padding 5px / 行高实测 34，一屏行数从 11 提到 18（产品态）。
- **筛选区渲染器 `filterBar:'grid3'`（D6）**：`.fb-grid` 三列（column-gap 24 / row-gap 10）+ `.fb-field`
  （label 76 右对齐、控件 `flex:1`、上限 320）+ `.fb-actions`（重置 → 查询 → 收起）；`resetId`/`queryId` 落到按钮上。
- **F6 折叠（REQ-18）**：作业型列表页**开页自动折叠 PRD、保留 nav**，首次给一条 toast 提示，
  `.pane-head` 新增「全宽预览」按钮（一键折 nav + PRD，再点还原）。判定口径与判据同一口径
  （Content 直属子树有 Table 且带 `pagination`）。**不写 localStorage**；**每页只首次生效** ——
  用户手动展开后被切页/回退不会被再折回去。
- **教材范本 `example-06-dense-list.json`（XX-032）**：8 列 Σ=866、`tableLayout:fixed`、20 行、六态、
  `rowClick → showDrawer`（560 宽，内含 6 列子表）。生成器 `gen_example06.py` 带
  `assert sum(widths) == 866` 自锁，任一列 +1 即 `AssertionError`。

### 修复

- **列宽声明在 DOM 上没生效（§3.8 头号缺陷）**：`th` 的 `style` 是 `width:48`——无单位，CSS 判非法并忽略，
  866 档 8 列全部渲染 `108.25px`。补 `px` 后逐列「声明/渲染/差」全 `0.0`。
- **`h1` 18px 被 `.ant-content .ant-typography{font-size:14px}` 覆盖**：改成 `:not(h1)`，页面恢复标题层级。
- **顶栏 `.sel{font-size:13px}` 命中了分页的 `<span class="pg sel">`**：类名复用撞车，改成 `select.sel`，
  P19 从 4 档降到 3 档 `[12,14,18]`。
- **操作列 inline `gap:10px` 在 88px 列里挤成折行**：改到 `.ant-td-action` 类上（xs 档 6px），行高回到 34、极差 0。
- **抽屉「声明 560 / 渲染 420」（R10）**：`R.Drawer` 从不读 `p.width`，`.ant-drawer.w-lg` 又从来没人加类，
  渲染恒 420，而 P11 读的是 JSON 声明 —— 与「列宽缺 px」同型。现在 `R.Drawer` 读 `p.width`
  （≥560 走 `w-lg`，其它数值 inline），**P11 改为打开抽屉量 `offsetWidth`**，打「渲染 x / 声明 y」，
  打不开则 SKIP（白名单外 → 整轮 INCOMPLETE），不退回声明值兜底。
- **`check_docs` 示例清单按数量比对**：数量相等不蕴含集合相等，改为与 `EXPECTED_EXAMPLES` **逐名比对**，
  缺 / 多 / 换名都失败。
- **`validate_prd_json.py` 筛选区合成 id 反向校验**：声明了 `props.queryId`/`resetId` 却找不到对应按钮 → ERROR。

### 变更

- P2a 产品态舞台去壳（不再自带假 Sider、不再加舞台 padding、`100vh` 按舞台高换算）；
  P4 改预算制；P12 分层唯一；P17 单档化 + 补渲染宽半边；P4/P18 前置不成立由 SKIP 改判 FAIL。
  **口径变更的逐条理由保存在发布记录（治理区，不随仓库分发），仓库内只保留结论表** ——
  不在这里写治理区路径：解压后那是死链。
- **口径对账修正 8 处（规范层，不改判据与容器）**：判决后的口径与规范文字对齐，折进本版不另开版本号。

### 已知

- **example-05 仍有 18 条 FAIL**（9 条判据 × 两档），名单写死在 `EXPECTED_FAIL`，少一条多一条都会报差异项。
  同时它打 `SKIP-OUT-OF-WHITELIST=[P2a,P2b]` + `RESULT INCOMPLETE` —— 那是设计，不是回归。
- **P2b 的 9 / 12 是 `floor(表格可视高 ÷ 行高)`，可视高含表头 34px**，所以截图里能数的**整行**是 8 / 11，
  第 9 / 12 行被底边裁掉一条。现值已改成两数并打（`9 折算 / 8 整行`），**公式与阈值本轮不动** ——
  改它会让目标值一起变（9/12 → 8/11），那是把「差一行」洗成「达标」。要改走变更单。
- **F4（QMS 5 个列表页）未做**：本轮无 QMS 产物，没有 before 基线，留到 I-08。

## [0.7.0] - 2026-10-21

**breaking: 否** —— 三道新门都是**新增脚本**，不改变既有断言基线（`run.sh` 仍 757）；`guards[]` /
`effects[]` 是可选字段，缺失不报错。唯一会让人当天变红的是「删不掉目录」，而那是一次诚实的 ENV。

### 新增

- **`tests/check_ui_scale.py`（XX-028）**：R1–R9 十条静态取值纪律做成退出码门 ——
  彩色 ≤12、字号 ≤5 档且不脱档、字重 ⊆{400,500,600}、圆角不脱档、间距不脱栅、
  1px 描边 ≤45、阴影 ≤3、令牌区外硬编码彩色 =0、存在 body/.ant-table 级 `tabular-nums` 声明。
  带 §6.5 的四种切片守卫（`ENV-ANCHOR` / `ENV-SHORT` / `ENV-RATIO` / `ENV-TOTAL`，首词互不相同）
  与 `--selfcheck`（11 条反例 + 4 条守卫，精确集合断言）。
- **`tests/check_layout.py`（XX-028）**：G1a/G1b/G2/G3/G4a/G4b/G4c 七条几何判据，headless Chrome +
  注入探针，五档视口（1600/1440/1080/900/700）。G1 的三数分开打（目标/可见/豁免），
  豁免只认 `getClientRects().length === 0`，ENV 四条守卫「应用已初始化」用
  `actual === expected`（`expected` 取 `page.states.length`）。
- **`guards[]` / `effects[]` 字段级校验（XX-023）**：`kind` 只有 `block`/`warn`，`text` 不得为空，
  元素必须是对象，整体必须是数组 —— 写错即 ERROR（两档一致），缺失不报。
  条数单列一行 `行为补充：guards=N（K/M 条需求） effects=…`。
- **`tests/clean_dir.py` + `run.sh` 清理留痕（XX-029）**：删除失败不再被 `ignore_errors` 吞掉，
  统一打印 `CLEAN_FAILED=<绝对路径> (OSError 文本)`；锁残骸与跑前清理失败 → `exit 2`
  （不带着脏 state 起跑），`trap EXIT` 的收尾清理失败 → 只留痕、**不改真实退出码**。
  新增 `$TMPDIR` 可写性前置（`TMPDIR=/nonexistent` → rc 2 并打印实际取值）。

### 变更

- `references/04` 的 `guards[]` / `effects[]` 从「**暂不校验**」改为「字段级已校验」；
  `references/09` 新增 §2.5；`SKILL.md` 阶段② 增加「前置校验落位」步骤（位于行为建模之前）。

### 已知

- **两道新门当前是红的**，且红在真实缺陷上：静态档 10 项超限（彩色 35/12、字号 19/5、
  描边 77/45、阴影 11/3、R9 命中 0 …），几何档 3 项（G1b@1080 违规 2、G2 面板头折行 3 处、
  G3 折行单元格 37 个）。A 类令牌收敛与 B 类层级修复尚未开始 —— 那才是让门转绿的活。
  **新增脚本不属于 DoD 1–9**（见 `项目治理/迭代/I-05-UI审美方案.md` §6.4），
  所以发布门 `RESULT 9/9` 与这两道门是红的可以同时成立；不要用发布门绿去推断审美门绿。

## [0.6.0] - 2026-10-21

**breaking: 否** —— 新增字段全部可选，默认档行为不变：缺 `ui` 只是 WARN，存量 PRD 升级当天不会变红。
破坏性变更只发生在**显式加 `--profile=delivery`** 的那一次运行里。

### 新增

- **行为模型绑定到界面（XX-019 / XX-020）**：`stateMachines[].transitions[].ui` 与
  `requirements[].ui` 引入统一的三态声明 —— `{"interactionId":"ix-xxx"}` /
  `{"kind":"system"}` / `{"kind":"page-enter"}`（第三个仅 requirement）。system 判定三入口等价：
  `system:true`、`role:"system"`、`ui.kind:"system"`，共用 `transition_is_system()` 一处实现。
  解决的问题：QMS 实测里 17 条人工转移有 8 条界面无入口，而校验器如实报 `errors=0`。
- **`--profile=delivery` 校验档（XX-021）**：`tasks` / `capabilities` / `pages[].contract` /
  `ui` 缺失即 ERROR 并非 0 退出；默认档保持宽松以护住存量产物。本档有真实调用者 ——
  `scripts/check_release.py` 的 DoD 1 对 `example-05` 走 delivery。

### 修复

- **XX-019 的悬空 `interactionId` 升为 ERROR（两档一致）**：`validate_prd_json.py:900` 原先走
  `gate()`（默认档只 WARN），而同一语义规则在 `ui.pageId` 不存在（`:894`）与 XX-020 的
  `interactionId` 不在页面（`:815`）都是硬 ERROR。悬空引用是「写错了」不是「没写」，不享受宽松；
  L1 类（缺 `pageId` / 缺 `interactionId` / `ui` 不是对象）仍走 `gate()`。
- **`tests/run.sh` 的 Chrome profile 移出工作树**：改到 `$TMPDIR/xx-prd-profiles.XXXXXX`，每轮
  `mktemp -d` 一个目录、`trap` 退出时清理。原先把 profile 放在 `tests/.build/profiles/`，
  本机 safe-delete 会拦截 `run.sh` 内部 python 子进程的批量删除（单条命令会触发升级、子进程不会），
  `clean_dir()` 用 `ignore_errors=True` 于是**静默失败** → 跨轮复用 profile 带旧 localStorage →
  实测 `TOTAL ok=754 fails=4`（分布 `01 -1 / 02 -2`）。修复后同一棵树连跑两次均为 `ok=757 fails=0`，
  反证（固定路径 + 不清理）能稳定复现 754/4。
- **`run.sh` 新增 `PROFILES_DIR=<path>` 输出**：让"这轮用的哪个 profile 目录、跑完删没删"可核对，
  不用再靠推断。

### 核验方式

`python3 scripts/check_release.py`（DoD 1–9 全过，`TREE` 与 `RESULT` 自带 self-proof）；
`bash tests/run.sh` 连跑两次均 `ok=757 fails=0 retries=0`。


## [0.5.1] - 2026-10-20

**breaking: 是** —— **"绿"的含义变严**：`RETRIES_MAX` 默认 0，以前"重试后成功"算通过，现在判 `exit 1`。
依赖既有绿灯的流水线需显式设 `RETRIES_MAX`，且上限会打进输出（`RETRIES=<n> (max=<m>)`）。
数据契约（`schemaVersion`）与命令、目录结构均无破坏性变更。
（本节标题现含 `x.y.z`，`check_docs.py` 的 `^##\s*\[?v?(\d+\.\d+\.\d+)\]?` 会把它读作最新版本——
这正是需要的：`CHANGELOG` 最新 = `SKILL.md` 的 `version` = 当轮 `release.md`。）

### 新增

- **发布准入一条命令**：`scripts/check_release.py` 把治理 §8.2 的 DoD 1–9 收敛成一个退出码
  （0 全过含 SKIP / 1 任一项 FAIL / 2 环境不可用 / 3 用法错误），每项一行结论、失败项缩进贴下游原始失败行；
  `SKIP` 计入 `skipped` 且原因落到具体文件，`skipped>0` 时另打 `NOT-VERIFIED:` 行。
  **breaking: 否** —— 纯新增脚本，不改任何既有命令的行为。
- **占位词唯一数据源**：`scripts/placeholder-vocab.json`（6 词，按 `scopes` 分 `doc` / `artifact`；
  `…` 仅 `artifact`，因中文文档里它是正常标点，进文档扫描会误报）。`tests/check_placeholders.py`
  与 `scripts/prd_flow.py` 共用这一份，不再各自硬编码。
  **breaking: 否** —— 词表内容与两处原有关键字集合等价（本轮新增的那一个词原先只在 `prd_flow` 侧生效）。
- **TREE 自证**：`scripts/check_release.py` 首行先声明"本轮判的是哪棵树"——
  `TREE <sha> clean` / `TREE <sha> DIRTY(<N>)` / `TREE unversioned`；`DoD 7` 的 PASS detail
  追加 `（HEAD=<sha>）`，脏树时 `RESULT` 行尾追加 `｜TREE DIRTY(<N>)`。
  起因是 0.5.1 收口时的一次真实误判：源仓库与安装副本**同时是脏的**，`DoD 7` 比出"两边一样脏"
  而判 PASS，`9/9` 看着全绿；事后只能靠人工回忆 `git status` 才发觉。**脏树不改退出码**，
  它不是失败，只是让"绿"带上"绿在哪棵树上"的证据。
  **breaking: 否** —— 输出多一行；退出码语义（0/1/2/3）与九项判据均未变。
- **DoD 7 自比假绿**（本轮新发现，与 TREE 同源）：脚本原先只在"没有安装副本"时 SKIP，
  没管"**自己就在安装副本里跑**"——此时 `ROOT` 与 `INSTALL_COPY` 是同一目录，`_manifest`
  自己跟自己比，恒等恒绿。实测从 `~/.workbuddy/skills/XX-PRD/scripts/` 运行会打出
  `PASS 43 个文件逐字节一致（HEAD=unversioned）`，看着像证据，其实一个字都没比过。
  改为同一目录时 SKIP，并进 `NOT-VERIFIED` 行。
  **breaking: 否** —— 只在"在副本内运行"这一种情况下把 PASS 改成 SKIP，仓库侧与 CI 侧行为不变。

### 变更

- **`retries` 进退出码**（勘误 E-03）：`tests/run.sh` 新增 `RETRIES_MAX`（默认 0）与
  `RETRIES=<n> (max=<m>) PASS|FAIL` 行；`retries > RETRIES_MAX` 判 `exit 1`，非法值前置 `exit 2`。
  **breaking: 是** —— **"绿"的含义变严**：`RETRIES_MAX` 默认 0，以前"重试后成功"算过，现在判 `exit 1`；
  依赖既有绿灯的流水线需显式设 `RETRIES_MAX`（上限会打进输出）。757 条断言与逐用例
  `94/137/123/136/150/117` 未变——**变的是判定口径，不是用例数量**。
- **占位符检查改用词表**：`tests/check_placeholders.py` 的模式不再硬编码；`SELF` 豁免从单文件扩为
  路径集合（含数据文件本身）；ALLOW 由 13 条收敛到 11 条（删 2 条指向已消失源码的死条目，加 3 条）。
  **breaking: 否** —— 判定粒度仍是"（文件, 行, 模式）"，`unallowed=0` 仍是通过判据。
- **`README.md` 与 `guide.html` 文案重写**：只改散文，不动结构。`guide.html` 的 `<b>` 由 242 降至 51、
  `——` 由 36 降至 0、`「」` 由 93 降至 48；标签计数（`section/h2/h3/h4/div/p/table/tr/td/th/code`）
  与改前**逐一相等**，HTML 解析零错配。术语统一为「本技能」，并把"容器"的两个含义拆开——
  指交付容器 `index.html` 时仍称"容器"，指对话框/抽屉/新页面的选择时改称"承载容器"。
  **breaking: 否** —— 纯文案，无锚点、无 `id`、无字段名变更。
- **两处文档事实修正**：`README.md` 结尾的当前版本由 `0.5.0` 改为 `0.5.1`（原先滞后一版，
  且没有任何校验器覆盖它）；`guide.html` 首屏统计的参考文档数由 `10` 改为 `11`
  （`references/*.md` 实测 11 份，`README.md` 早已写的 11）。`68 组件白名单` 经核验正确
  （`05-component-states.md` §2 共 71 行表项、去重 68 个组件名），未改。
  **breaking: 否**。

### 修复

- **DoD 6 读错文件 + 兜底正则永远有答案**（勘误 E-05）：`tests/check_docs.py` 原先把 release 路径写死
  成 `I-01`，本轮自己的 `release.md` 永远读不到；且 `read_release_version()` 的第二条正则是
  "全文第一个 `x.y.z`"——实测在 `I-01/release.md` 里会抓到 `155.0.8059`（Chrome 版本）且**永不报错**。
  改为取 `iterations/` 下编号最大一轮、只认显式版本字段（表格行 / 冒号行）、并打印
  `release-source: <路径|none>` 自证读了哪份。
  **breaking: 否** —— 输出多一行 `release-source:`；`versions:` 行在无版本时由
  `未生成(S6 前可缺省)` 改为 `none`，若有外部脚本解析该行需同步。

## [0.5.0] - 2026-10-19

**breaking: 否** —— 本版无 `schemaVersion` 变更（`1.0` / `1.1` 产物均可在本版容器渲染），
无命令与目录结构的破坏性调整；新增文件均为增量。

### 新增

- **回归测试入库**：`tests/` 收录 harness、构建脚本与 `run.sh`，一条命令覆盖 6 个用例
  （`00-embedded` + `example-01`~`05`）。**待核**：目标为 757 条断言、`fails=0`，
  以 G4 前 `bash tests/run.sh` 的实际输出为准。
- **CI 门禁**：`.github/workflows/ci.yml` 五个作业 —— `examples-validate` / `py-syntax` /
  `docs-consistency` / `tests-static` / `container-regression`，push 与 PR 均触发。
  **待核**：`container-regression`（`ubuntu-latest` + `CHROME=/usr/bin/google-chrome`）
  的真实性待首次 push 后确认，此前标"未验证"。
- **版本标识**：`SKILL.md` frontmatter 新增 `version` 字段；本文件随之建立。
- **许可**：新增 `LICENSE`（MIT）。

### 修复

- `README.md` 参考文档数量由 10 修正为 11；移除指向仓库外 `demo-po-behavior.html` 的引用，
  改为截图 + 「用容器加载 `example-05` 看交互版」。
- **生成器与示例产物漂移**：重跑 `gen_example03/04/05.py` 会丢失 `capabilities`（`example-04` 3→0、
  `example-03` 6→0）与 3 处 `"system": true`。修复方向为"以仓库 JSON 为真源、反向修生成器"。
  **待核**：须满足 `python3 tests/check_generators.py` 退出码 0、重跑生成器后零差异、
  `example-04` 仍 3 条 / `example-03` 仍 6 条且含 3 处 `"system": true`；未满足则改记为"未完成，见 I-01 偏差"。

### 兼容性

| 项 | 本版 | 说明 |
|---|---|---|
| 技能包版本 | `0.5.0` | `SKILL.md` frontmatter 的 `version` |
| 数据契约 `schemaVersion` | `1.0` / `1.1` | 未变；`1.1` 为含 `tasks` / `capabilities` / `contract` 的行为建模产物 |
| 容器 | 单文件、零依赖 | 未改渲染逻辑 |

### 升级方式

1. 覆盖安装技能目录（旧版本可直接替换，无迁移脚本）；
2. 已有 `.json` 产物无需改动，`1.0` / `1.1` 均可继续渲染；
3. 回退：换回上一版本的技能目录即可，本版未产生任何数据格式变更。
