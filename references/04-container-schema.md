# 容器 JSON Schema（数据契约 v1.0）

> 这是整套 Skill 的**唯一数据契约**。容器渲染引擎、EARS 条目、标注系统、导出逻辑全部依赖它。
> 生成任何产物前，先读本文件；产出的所有 JSON 必须能被 `scripts/validate_prd_json.py` 校验通过，并能被 `assets/container/index.html` 渲染。
>
> **分片交付时**：每个切片写的是本文件的**子集**（多一个 `sliceId`），由
> `scripts/prd_slice.py merge` 合并成完整的 `XX-PRD.data.json`。片段格式、合并规则与单片上限
> 见 `references/11-slice-delivery.md`。

---

## 0. 顶层结构总览

```jsonc
{
  "meta":         { ... },   // 元信息 / 渲染控制
  "product":      { ... },   // 产品定位（shaping 产物）
  "users":        [ ... ],   // 用户角色
  "tasks":        [ ... ],   // 业务任务（角色想完成的事，页面切分的依据）
  "userFlows":    [ ... ],   // 用户流
  "modules":      [ ... ],   // 模块清单
  "dataModel":    { ... },   // 数据实体 / 字段 / 关系 / 派生字段（供 AI 生成类型与接口）
  "pages":        [ ... ],   // 页面清单 + 原型（componentTree/states/interactions/annotations/contract）
  "components":   [ ... ],   // 关键组件与状态定义（设计/前端复用）
  "stateMachines":[ ... ],   // 状态机
  "capabilities": [ ... ],   // 命令策略：角色 × 状态 × 动作（按钮可用性的唯一依据）
  "requirements": [ ... ],   // EARS 需求条目
  "boardPlan":    [ ... ],   // PRD 板块计划
  "glossary":     [ ... ],   // 术语表
  "openQuestions":[ ... ]    // 待澄清问题
}
```

**引用关系（前缀区分类型）：**

| 前缀 | 实体 | 唯一性范围 | 被谁引用 |
|---|---|---|---|
| `u-` | user | 全局 | userFlows.role、requirements.role、stateMachines.transitions.role、capabilities.actor、pages.contract.actor |
| `m-` | module | 全局 | pages.moduleId、requirements.moduleId |
| `page-` | page | 全局 | modules.pageIds、pages.entryFrom/exitTo、pages.parentId、interactions.navigate、capabilities.page |
| `task-` | task | 全局 | pages.contract.task |
| `flow-` | userFlow | 全局 | — |
| `e-` | dataModel entity | 全局 | dataModel.entities[].relations.target、derived.usedBy、capabilities.entity |
| `c-` | component | 全局 | pages.componentTree 的 `ref` |
| `sm-` | stateMachine | 全局 | requirements.stateMachine、pages.stateMachine |
| `cap-` | capability | 全局 | pages.contract.owns、节点 `props.capability`、`columns[].actions[].capability` |
| `REQ-` | requirement | 全局 | boardPlan.reqIds、pages.prd.reqIds、capabilities.requirement |
| `bp-` | boardPlan | 全局 | — |
| `q-` | openQuestion | 全局 | — |
| `n-` | componentTree node | **页内** | interactions.on.target、states.overrides.target、annotations.anchor.nodeId |
| `ix-` | interaction | **页内** | — |
| `s-` | pageState | **页内** | pages.defaultStateId |
| `an-` | annotation | **页内** | — |
| `sec-` | prd section | **页内** | — |
| `<节点 id>__back` / `__ok` / `__cancel` / `__row_<i>` / `__act_<i>_<key>` | 合成节点 | **页内** | 容器内建，可直接写进 interactions.on.target（见 §0.2） |

> **唯一性规则**：全局实体必须全局唯一；`n-` / `ix-` / `s-` / `an-` 只需在**所属页面内**唯一（因此多个页面都可以有 `s-default`）。容器同一时刻只渲染一个页面，页内唯一即可正确锚定。

---

## 0. 页面层级与左侧导航（容器左栏渲染规则）

容器左栏是一棵**模块 → 页面 → 子页面**的树，数据全部来自 `modules` 与 `pages`，无需额外字段：

| 树节点 | 数据来源 | 说明 |
|---|---|---|
| 模块分组 | `modules[]` | 按数组顺序渲染；**声明了但没有页面的模块也会显示**，标注「该模块暂无页面」 |
| 顶级页面 | `pages[]` 中**没有 `parentId`** 的页面 | 归入 `page.moduleId` 对应模块 |
| 子页面 | `pages[]` 中有 `parentId` 的页面 | 挂在其 `parentId` 指向的页面之下，可多层嵌套（容器最多渲染 6 层） |
| 未分组 | — | `moduleId` 缺失且不在任何 `modules[].pageIds` 中的页面，自动归入「未分组」 |

**页面归属模块的判定顺序**：`page.moduleId`（须能在 `modules` 中找到）→ 反查 `modules[].pageIds` 是否包含该页 → 都失败则归入「未分组」。

**子页面声明**：

```jsonc
{
  "id": "page-goods-edit",
  "moduleId": "m-goods",
  "parentId": "page-goods-list",     // 可选。指向同模块内的父页面，形成多级页面
  "name": "商品编辑",
  "route": "/goods/:id/edit"
}
```

> **约定**：
> 1. `parentId` 必须指向**已存在**的页面，且不得成环（校验器会报 ERROR）。
> 2. 建议父子页面属于同一 `moduleId`；跨模块挂载时子页面会显示在**父页面所在模块**下（校验器给 WARN）。
> 3. 用 `parentId` 表达的是**信息架构上的层级**（如「列表 → 详情 / 编辑」），不是路由嵌套；`route` 仍按真实路径填写。
> 4. 只有 1 个模块 1 个页面时树自动退化为单节点，无需特殊处理。

**容器在树上提供的交互**：模块行点击折叠/展开、页面行点击切换页面、筛选框按「模块名 / 页面名 / 路由 / 页面 id / 目标」过滤（自动保留命中项的祖先链路）、待处理标注数量角标、当前页高亮并自动滚动到可见区域、左栏可整体收起（顶栏 `☰` 恢复）、左栏宽度可拖拽（写入 localStorage）。

**顶栏面包屑**同时展示「模块 / 父页面 / … / 当前页 + 路由」；模块名与页面名相同时自动去重。

---

## 0.1 原型缩放/平移与标注锚定（容器中栏渲染规则）

左栏树 + 右栏 PRD 会挤压中栏，因此中栏原型自带**缩放 + 平移**，评审时先放大看细节、再缩回纵览。

| 操作 | 触发方式 |
|---|---|
| 放大 / 缩小 | 工具条 `−` / `+`；或 `⌘/Ctrl` + 滚轮（**以光标为锚点**）；或 `⌘/Ctrl` + `+` / `-` |
| 复位 100% | 点 `100%` 数字；或 `⌘/Ctrl` + `0` |
| 适应宽度 | 点「适应宽度」，把原型压回中栏可视宽（结果等价 100%，**不产生横向滚动条**） |
| 平移 | 直接拖拽画布；或按住 `空格` 拖拽；或鼠标**中键**拖拽；或开「✋ 平移」常驻模式 |

- 缩放范围 **25% ~ 300%**；`100%` 的定义是「基准宽 = 中栏可视宽」，所以默认状态刚好铺满、无横向滚动。
- 缩放倍率写入 localStorage（键 `iprd::<产品名>` 下的 `zoom`），刷新后保持。
- **平移模式与标注模式互斥**：开一个自动关另一个，避免"想拖画布却点出一个气泡"。
- 拖拽平移结束后紧邻的那次 `click` 会被抑制（160ms 内），不会误触发原型交互。

### 标注锚定的不变量（AI 不要破坏）

标注用**归一化坐标**记录位置，比值落在 `0~1`，基准是**画布盒**（不是外层缩放容器）：

```jsonc
"anchor": { "nodeId": "n-btn-new", "x": 0.5, "y": 0.5 }
//         ↑ 优先：锚定到组件树节点，气泡视觉中心恒等于该节点的视觉中心
//                             ↑ 兜底：nodeId 缺失或节点找不到时，按 x/y 比值自由落位
```

| 不变量 | 原因 |
|---|---|
| 气泡落位用 `left: x%`（相对画布盒），落位基准必须是**画布盒的布局尺寸** | 分子分母同处缩放坐标系，比值才与 zoom 无关 |
| 外层缩放容器（`.prototype-wrap`）的**布局宽必须恒等于基准宽**，缩放只由 `transform: scale()` 承担 | 若布局宽随 zoom 增长，`getBoundingClientRect().width` 会变成 `baseW*z²`，归一化坐标被除以 z 而**漂移**（v1.0 曾有此 bug，已修） |
| `n-` 节点 id 一经分配不得更改 | 标注靠 `data-node-id` 锚定；改 id = 所有标注丢失锚点 |
| 节点被删/改名后，该节点上的标注自动降级为自由落位 | 容器按 `nodeId` 查不到元素时回落到 `x/y` |

> **对 AI 的要求**：原型被挤压时**不要**通过删页面、减表格列、缩字号来"腾空间"——那是信息损失。正确做法是让用户在容器里缩放/平移，或把页面拆成 `parentId` 层级。回归测试覆盖：锚定气泡跨 6 档缩放（100%~152%）视觉中心偏差 < 0.8%（实测 0.002%）。

---

## 0.2 页面跳转与交互寻址（容器渲染规则）

原型不是死图：容器支持**页面间跳转、带参跳转、返回、页内定位**，并且表格的「行」和「行内按钮」都能被精确寻址。

### 跳转的三条通道

| 通道 | 触发方式 | 说明 |
|---|---|---|
| URL hash | `#/page-id` | **当前页的第一真源**。可直接分享链接、可用浏览器前进/后退；刷新后停在原页 |
| 左栏导航树 | 点页面行 | 与 hash 双向同步 |
| 交互动作 | `navigate` / `back` | 原型内点击驱动 |

- 容器启动时若 hash 为空，按 `localStorage.pageId` → `meta.currentPageId` → `pages[0]` 兜底，并用 `history.replaceState` 建立 hash 基线（所以**第一次点浏览器后退不会退出容器**）。
- hash 指向不存在的页面时**不切页、不白屏**，并把 hash 拉回当前页，保持「URL = 当前页」这条不变量。
- `hashchange` 会清空容器自有的返回栈，避免与浏览器历史栈打架。

### 返回栈与「绝不跳出容器」

```jsonc
// 容器内「返回」的解析顺序（goBack）
// 1. 自有返回栈 RT.navStack（每次 navigate 入栈）
// 2. 信息架构兜底：当前页 entryFrom[] 里第一个存在的页面
// 3. 都没有 → toast「已是起始页」，不做任何跳转
```

> 因此**用 `entryFrom` 声明入口页**是有价值的：它既是文档，也是「返回」的兜底。孤岛页面（`entryFrom` 为空且不是入口页）会退化成「无路可退」。

### 合成节点 id（容器内建，可被 interactions 引用）

有些「可点目标」在 `componentTree` 里并不存在独立节点，容器会在渲染时按规则合成 id。**这些 id 可以直接写进 `interactions[].on.target` 或 `actions[].scrollTo`**：

| 合成 id | 挂在哪个组件上 | 生效前提 | 语义 |
|---|---|---|---|
| `<Header 节点 id>__back` | `Header` | `props.back: true` | 返回箭头，**内建 back 动作**（点它就走 `goBack()`） |
| `<Table 节点 id>__row_<i>` | `Table` | `props.rowClick: true` | 第 i 行（0 起） |
| `<Table 节点 id>__act_<i>_<key>` | `Table` | `columns[].actions` 里声明了 `key` | 第 i 行操作列的第 `key` 个按钮 |
| `<Modal 节点 id>__ok` / `__cancel` | `Modal` | `props.footer !== false` | 弹窗底部「确定」/「取消」。`__cancel` **内建关闭该弹窗** |
| `props.queryId`（**作者声明，非合成**） | `Table` | `props.filterBar === 'grid3'` 且写了 `queryId` | 「查询」按钮的节点 id，渲成 `data-node-id`，可被 `on.target` 引用 |
| `props.resetId`（**作者声明，非合成**） | `Table` | 同上 | 「重置」按钮的节点 id，同上 |

> ⚠️ 最后两行与上面几行**性质不同**：`__back` / `__row_*` / `__act_*` / `__ok` 是容器按基节点 id 合成的；`queryId` / `resetId` 是**作者自己起的名字**，容器只负责把它写到按钮的 `data-node-id` 上。
> 因此写错不会被「合成规则」兜住 —— 校验器会做**反向校验**：声明了 `queryId` / `resetId` 却在产物里找不到对应按钮，直接报 ERROR（悬空引用）。

> ⚠️ 弹窗按钮的合成 id 用的是 **Modal 节点 id**，不是 `props.modalId`。两者常常同名但**语义不同**：`showModal` / `hideModal` 引用 `modalId`，交互寻址引用节点 id。校验器会对写错的基节点直接报 ERROR。

### 通配目标：一条 interaction 服务所有行

序号位可以写 `*`：

```jsonc
{ "on": { "event": "click", "target": "n-table__row_*" } }        // 任意一行
{ "on": { "event": "click", "target": "n-table__act_*_view" } }   // 任意一行的「查看」
```

**就近命中（closest）**：容器用 `e.target.closest('[data-node-id]')` 找点击目标，所以点「行内按钮」命中的是按钮本身，**不会**同时触发整行跳转。于是「点行进详情、点按钮只做按钮的事」可以共存，不需要额外写法。

### 行上下文与 `{{expr}}` 插值

点表格行 / 行内按钮时，容器会把**该行的数据**并入求值作用域，于是 params、message 文案都能按行求值：

```jsonc
{
  "on": { "event": "click", "target": "n-table__row_*" },
  "actions": [{
    "type": "navigate", "pageId": "page-goods-detail",
    "params": { "goodsName": "{{row.name}}", "goodsSku": "{{row.sku}}" }
  }]
}
```

| 写法 | 可用位置 | 说明 |
|---|---|---|
| `{{row.字段}}` | 行/行内按钮上的 `navigate.params`、`message.text`、`setState.value` | 取**该行**的数据；在**源页**求值 |
| `{{变量名}}` | 同上 | 取页面状态变量（`states[].vars` / `setState` 写入的） |
| `{{row}}` | 同上 | 整行对象（JSON 序列化，调试用） |

**求值作用域（就近覆盖）**：`{ ...页面状态变量, row: 该行数据, ...该行字段 }`。
所以 `{{row.name}}` 和 `{{name}}` 都能取到该行的 `name`；页面变量与行字段同名时**页面变量优先**（避免行数据意外覆盖业务状态）。

**params 在源页求值**：这是必须的——若留到目标页求值，会先被目标页 `states[].vars` 的默认值覆盖，`{{row.name}}` 就取不到源页的行数据了。求值结果写入 `RT.vars`，再被目标页的 `{{变量名}}` 渲染出来。

**目标页要有默认值**：给「会被带参跳转进来」的页面在 `states[].vars` 里写一份默认值，这样用户直接从导航树进这页时也不会看到空字段：

```jsonc
{ "id": "s-default", "name": "默认态",
  "vars": { "goodsName": "轻量羽绒外套", "goodsSku": "GD-1001", "goodsStatus": "已上架" } }
```

**插值渲染**：`{{expr}}` 会在**渲染后**替换节点里的文本节点，以及 `title` / `placeholder` 属性。表达式求不出来时**保留原文**（例如页面上会显示 `{{goodsName}}`），让配置错误看得见，而不是静默变空白。

> 插值只支持容器安全表达式求值的子集：变量/属性路径、数字与字符串字面量、`true`/`false`/`null`、比较、逻辑、括号。**不支持函数调用**。

### 页内定位 `scrollTo`

```jsonc
{ "type": "scrollTo", "target": "n-table" }   // 把画布滚到该节点并高亮 1.3s（配合放大查看）
{ "type": "scrollTo" }                        // 回到画布顶部
```

---

## 0.3 页面关系图（容器顶栏「关系图」）

容器把 `interactions` 里的 `navigate` 动作与 `entryFrom` 反向抽成一张**有向图**，
用分层布局（layered / Sugiyama 简化版）全局展开，方便设计和前端一眼看清页面关系。

**边的来源（无需额外配置，改 `interactions` 即自动更新）：**

| 边 | 来源 | 画法 |
|---|---|---|
| 跳转边 | `pages[].interactions[].actions[]` 中 `type:"navigate"` | 实线；标签取 `interaction.name`（缺失则取触发节点文案） |
| 入口边 | `pages[].entryFrom[]`（且该方向没有跳转边） | 虚线；标签固定「入口」 |
| 回边 | 指向层号不更大的边 | 虚线（避免图变成环状缠绕） |
| 高亮 | 与当前页相连的边 | 主色加粗 |

**布局规则：** 先用 DFS 找出回边（指向栈上节点的边）并从图中摘掉得到 DAG →
在 DAG 上 Kahn 拓扑 + 最长路径分层 → 同层重心法（barycenter）排 2 轮减少交叉 →
按层最大主尺寸对齐落坐标。方向可切「横向（LR）/ 纵向（TB）」。

> 断环必须在分层**之前**。少了这一步，环上节点在「最长路径松弛」里会每轮 +1、永不收敛，
> 层号一路涨到迭代上限 —— 画出来是一张巨宽的图 + 横贯全屏的连线（`example-03` 有 4 个回环，必现）。

**交互：** 拖拽卡片调整位置（写 `localStorage`，重绘后保持）· 点击卡片进入该页 ·
滚轮平移 / `⌘`+滚轮缩放 · 「自动排列」清空人工位置回到信息架构布局 · 「适应」铺满视口 ·
「导出全图」把整张关系图导成 PNG（走 `exportElementPng`，与「截图」同一套序列化）。

**盒模型与坐标约定（改画布代码前务必先读）：**

```
#coScroll  ← 滚动容器
└─ #coWorld  ← 缩放盒：尺寸 = 内容盒 × zoom，margin:auto 在视口里精确居中；
│              它的尺寸同时就是滚动范围（不多不少，z>1 也不会被裁）
   └─ #coInner ← 内容盒：未缩放尺寸 = 卡片包围盒 + pad，缩放只走它的 transform
      ├─ svg#coSvg
      └─ .co-node × N
```

- **卡片坐标只有一套**：以内容盒左上角为原点、`pad`(=60) 为最小边距。
  拖拽落盘的就是这套坐标（`LS.canvasPos[id] = {x: 卡片left - pad, y: 卡片top - pad}`）。
  **不要再做「pad − 包围盒 minX」这类归一化**：被拖的卡片一旦成为最左上，偏移量会跟着变，
  落盘坐标就被二次平移 —— 表现为「拖完一刷新又弹回去」（单页数据集必现）。
- 卡片被钳制在 `pad` 之内（负坐标在滚动容器里不可达，拖过去就等于弄丢了）；
  拖到右/下会调用 `syncCoContentBox()` 把内容盒撑大，保证滚得到。
- 卡片 class 用 `.co-node.co-cur` 标记当前页，**不能用 `.sel`** —— 顶栏状态选择器 `<select class="sel">`
  有 `.sel{height:30px;max-width:190px}`，同优先级下会把卡片压成 190×30。

**因此：** 只要 `interactions` 写全了跳转，关系图就是信息架构的**自动真源**；
`devspec.json` 的 `pageGraph` 与它同源，AI 拿到的是同一张图。

---

## 0.4 右栏 PRD 面板（折叠 / 宽度）

| 操作 | 行为 |
|---|---|
| 拖 `#splitter` | 右栏 PRD 像素定宽；钳制在 `[300px, min(可用宽×72%, 可用宽−6−320px)]` |
| 双击 `#splitter` | 复位到默认 480px |
| `#prdCollapse`（PRD 面板头「›」）/ `#prdToggle`（原型栏「PRD ‹」） | 收起右栏，右侧出现竖向「PRD」恢复把手 |
| `#prdRestore`（把手） | 展开右栏并还原上次宽度 |
| 折叠态 / 宽度 | 写入 `localStorage`，刷新后保持 |

> **实现约束（AI 不要改回百分比）**：右栏宽度是**像素**且只改 `#panePrd`，
> 中栏保持 `flex:1 1 auto`。历史 bug 是把中栏写成 `flex:0 0 <ratio>%`（钳在 0.25~0.8）
> 同时右栏写 `flex:1 1 auto`（基准=内容宽，宽表格时内容宽很大），两者互相挤压后
> splitter 的实际位置与鼠标位置脱钩，表现为「拖到最小后拖不回来」。

---

## 0.5 容器选型（对话框 / 抽屉 / 新页面）

**完整准则见 `references/08-container-choice.md`**（决策树 / 五维矩阵 / 反模式）。
这里只列**校验器会强制拦住的硬规则**：

| 规则 | 级别 |
|---|---|
| `Modal` 内叶子表单字段（Input/Select/…）> **15** 个 → 长表单禁用对话框 | ERROR |
| `Modal` 里嵌套 `Modal`（dialogception） | ERROR |
| `Modal` 内字段 > 8 个（疑似「详情」用对话框承载） | WARN |
| `Drawer` 内有 ≥3 个 tab 的工作台（应升级为新页面） | WARN |

**速记**：轻量确认用 `Modal`，对照上下文用 `Drawer`，复杂长程用新页面（`pages[]` + `navigate`）；
详情主从首选 `Drawer`；一条主记录挂多条明细用 `MasterDetail`（§6.7）。

---

## 0.6 命令策略与业务状态模拟（按钮可用性）

**完整方法见 `references/09-behavior-model.md`。** 这里只讲容器怎么消费它。

B2B 原型最常见的缺陷是「单据有多个状态，按钮却永远可点」。容器把这件事变成**数据驱动**：

```jsonc
// 根级
"capabilities": [
  { "id": "cap-po-approve", "name": "通过", "entity": "PurchaseOrder",
    "actor": ["u-manager"], "from": ["pending"], "policy": "disabled",
    "reason": "仅「待审批」订单可以审批", "to": "approved",
    "page": "page-po-approve", "requirement": "REQ-PO-002" }
]
// 页面声明它作用在哪个实体上（顶部会出现「单据状态」下拉）
{ "id": "page-po-approve", "entity": "PurchaseOrder", "stateMachine": "sm-po" }
// 按钮引用命令，而不是写死 disabled
{ "id": "n-ap-btn-approve", "type": "Button",
  "props": { "text": "通过", "type": "primary", "capability": "cap-po-approve" } }
```

| policy | 渲染结果 | 点击行为 |
|---|---|---|
| `hidden` | 不渲染 | — |
| `disabled` | 灰底灰字 + `cursor:not-allowed` + `title=reason` | **可点**，弹出 reason 提示（不是静默无反应） |
| `reject` | 正常外观 + 虚线警告色 | 正常执行交互；无交互时兜底提示 reason |

**状态来源分两种**（容器自动判断）：

| 场景 | 取值 |
|---|---|
| 表格行内动作（`columns[].actions[].capability`） | 该行 `status` 字段（中文状态名或状态 id 都认，可用 `stateField` 改名） |
| 详情/表单页按钮（`props.capability`） | 顶部「单据状态」下拉选中的模拟状态；默认取状态机的 `initial` |

**右栏 PRD 自动生成「命令策略矩阵」**（行 = 命令，列 = 状态，✓/—），点状态名即可切换模拟 —— 评审时不用改 JSON。

**状态标签别写死**：页面声明了 `entity` 时，容器会往插值上下文里注入两个只读变量，
让「状态标签」跟着下拉一起变（否则切到「待审批」了，页面上还挂着「草稿」的 Tag）：

| 变量 | 值 |
|---|---|
| `{{__entState}}` | 当前单据状态的中文名（草稿 / 待审批 / 已审批 …） |
| `{{__entStateId}}` | 当前单据状态的 id（draft / pending / approved …） |

```jsonc
{ "id": "n-d-tag", "type": "Tag", "props": { "text": "{{__entState}}", "color": "blue" } }
```

**校验器硬规则**：

| 规则 | 级别 |
|---|---|
| 状态机存在但没有任何 `capabilities` | WARN |
| 状态机的人工转移没有对应 capability，且未标 `system: true` | ERROR |
| `from` / `to` 引用了状态机里不存在的状态 | ERROR |
| `policy` 为 `hidden`/`disabled` 且 `from` 非空，但没有 `reason` | ERROR |
| `actor` 不在 `users[]`、`entity` 不在 `dataModel.entities[]` | ERROR |
| `contract.owns` 引用了不存在的 capability，或同一条命令被两个页面 owns | ERROR |
| 页面绑定 `entity` 却没有 `contract` | WARN |

---

## 1. `meta` — 元信息与渲染控制

```jsonc
"meta": {
  "schemaVersion": "1.1",          // "1.0"（无行为建模）/ "1.1"（含 tasks/capabilities/contract）
  "product": "团队任务看板",         // 产品名（顶栏标题）
  "version": "0.1.0",              // 产物版本
  "createdAt": "2026-10-15T10:42:00+08:00",
  "updatedAt": "2026-10-15T11:30:00+08:00",
  "reviewMode": false,             // 审核模式：true 时容器隐藏 shaping 过程产物，只留 PRD+原型
  "currentPageId": "page-task-list",// 容器初始打开的页面
  "defaultPanel": "both"           // both | prototype | prd
}
```

---

## 2. `product` — 产品定位

```jsonc
"product": {
  "name": "团队任务看板",
  "oneLiner": "让 10 人以下小团队在 5 分钟内完成一次任务同步",   // 一句话定位
  "positioning": "面向研发小团队…（定位陈述，2-4 句）",
  "targetUsers": ["研发小团队负责人", "开发工程师"],
  "coreValue": "用最少的操作成本对齐任务状态",
  "nonGoals": ["不做跨组织权限体系", "不做甘特图"],   // 非目标：明确不做什么
  "metrics": [
    { "name": "任务创建耗时", "target": "< 15s", "type": "leading" },
    { "name": "周活团队数",   "target": "> 200", "type": "lagging" }
  ]
}
```

---

## 3. `users` — 用户角色

```jsonc
"users": [
  {
    "id": "u-owner",
    "name": "项目负责人",
    "description": "对项目进度负责，需要掌握全局状态",
    "goals": ["快速了解阻塞项", "分配任务"],
    "painPoints": ["信息散落在多个群聊"]
  }
]
```

---

## 4. `userFlows` — 用户流

```jsonc
"userFlows": [
  {
    "id": "flow-create-task",
    "name": "创建并指派任务",
    "role": "u-owner",
    "goal": "把口头需求落成一条可追踪的任务",
    "steps": [
      { "id": "st-1", "name": "进入任务列表", "pageId": "page-task-list", "note": "" },
      { "id": "st-2", "name": "点击新建",     "pageId": "page-task-list", "note": "打开抽屉表单" },
      { "id": "st-3", "name": "填写并指派",   "pageId": "page-task-list", "note": "" },
      { "id": "st-4", "name": "查看详情",     "pageId": "page-task-detail", "note": "" }
    ]
  }
]
```

---

## 5. `modules` — 模块清单

```jsonc
"modules": [
  {
    "id": "m-task",
    "name": "任务管理",
    "goal": "承载任务的创建、查看、流转",
    "priority": "P0",                 // P0 | P1 | P2
    "pageIds": ["page-task-list", "page-task-detail"],
    "dependsOn": []                   // 其他模块 id
  }
]
```

---

## 6. `pages` — 页面清单 + 原型（核心）

每个页面 = **一份组件树 + 一组页面状态 + 一组交互 + 一组标注 + 页面级 PRD**。

```jsonc
"pages": [
  {
    "id": "page-task-list",
    "moduleId": "m-task",
    "parentId": null,                 // 可选。有值时成为该页面的子页面（左侧导航树按此嵌套）
    "name": "任务列表页",
    "route": "/tasks",
    "goal": "让负责人一眼看到所有任务及其状态",
    "entryFrom": ["page-home"],
    "exitTo": ["page-task-detail"],
    "entity": "Task",                 // 可选：本页操作的业务实体（有它 + 状态机 → 顶部出现「单据状态」下拉）
    "stateMachine": "sm-task",        // 可选：可省略，按 entity 自动匹配
    "contract": {                     // 页面职责契约（见 references/10-page-decomposition.md）
      "task": "task-track",           // 服务哪条业务任务
      "actor": ["u-owner"],           // 主要使用者
      "entity": "Task",               // 主体对象，须与 page.entity 一致
      "owns": ["cap-task-start"],     // 本页负责发起的命令（一条命令只能有一个主页面）
      "submitBoundary": "none",       // single | staged | none
      "doneWhen": "任务已开始或被标记完成"
    },
    "layout": "sider-content",        // blank | header-content | sider-content | header-sider-content
    "defaultStateId": "s-default",
    "notApplicableStates": [],        // 四态中确实不适用的，显式声明，如 ["empty"]
    "componentTree": { /* Node，见 §6.1 */ },
    "states": [ /* PageState，见 §6.2 */ ],
    "interactions": [ /* Interaction，见 §6.3 */ ],
    "annotations": [ /* Annotation，见 §6.4 */ ],
    "prd": { /* PrdBlock，见 §6.5 */ }
  }
]
```

### 6.1 `componentTree` — 组件树 Node

```jsonc
{
  "id": "n-root",                  // 全局唯一，n- 前缀
  "type": "Layout",                // 组件类型，见 references/05-component-states.md
  "ref": "c-app-shell",            // 可选：引用 components[] 中的复用定义
  "props": {                       // 组件属性（AntD 风格）
    "title": "任务看板",
    "direction": "horizontal"
  },
  "state": "normal",               // normal | loading | disabled | error | success | active | empty
  "when": "",                      // 条件渲染表达式，空=总是渲染。例："status === 'draft'"
  "children": [ /* Node[] */ ],
  "slots": { "extra": [ /* Node[] */ ] }   // 具名插槽。**插槽名按 type 不同**（如 Card.extra / Drawer.footer），
                                           // 写错 type 不读的插槽会被静默丢弃 —— 见 §6.8 R2
}
```

**Node 编写规则：**
- `id` 必须唯一且稳定 —— 交互和标注靠它锚定，重新生成原型时不要改已有 id。
- 只使用 `05-component-states.md` 白名单里的 `type`；未知类型容器会降级为 `<div>` 并打警告。
- 数据驱动的列表用 `props.data` + `props.renderItem` 声明，不要手写 N 个重复节点：
  ```jsonc
  { "id": "n-list", "type": "List", "props": { "data": ["a","b"], "renderItem": { "type":"List.Item", "props": { "title": "{{item}}" } } } }
  ```
  > `renderItem` 的**规范位置是 `props.renderItem`**。写在节点级时容器**会兼容读**（`R.List` 的 `p.renderItem||node.renderItem`），所以列表**照常渲染**，不是空列表 —— 这条老说法是错的（I-11 更正）。但那个位置不在契约键空间内：校验器会按节点级未知字段给 WARN，SS-01 也**判 ERROR 并要求挪进 `props`**（见 §6.8.2 R7）。模板占位用 `{{item.字段}}` / `{{item}}` / `{{index}}`。
- 条件渲染优先用 `when` 表达式，而不是拆两棵子树。
- 需要「从别处带参跳进来」的字段，用 `{{变量名}}` 写在 `props` 里（见 §0.2），并给页面 `states[].vars` 写默认值。

### 6.2 `states` — 页面状态（PageState）

页面状态 = 一组**状态变量初值** + **对组件树的覆写**。切换状态即"模拟"到该场景。

```jsonc
"states": [
  {
    "id": "s-default",
    "name": "默认态",
    "description": "列表有数据，无筛选",
    "vars": { "status": "draft", "loading": false, "filter": "" },
    "overrides": [                                  // 覆写某个节点的 props/state
      { "target": "n-btn-submit", "prop": "disabled", "value": false }
    ],
    "hidden": [],                                   // 隐藏的节点 id
    "visible": []                                   // 若非空，则只显示这些节点（其余隐藏）
  },
  {
    "id": "s-loading",
    "name": "加载态",
    "description": "首次进入请求中",
    "vars": { "loading": true },
    "overrides": [ { "target": "n-table", "prop": "loading", "value": true } ]
  },
  {
    "id": "s-empty",
    "name": "空态",
    "vars": { "loading": false, "count": 0 },
    "overrides": [ { "target": "n-table", "prop": "empty", "value": true } ]
  },
  {
    "id": "s-error",
    "name": "异常态",
    "vars": { "error": "网络异常" },
    "overrides": [ { "target": "n-alert", "prop": "visible", "value": true } ]
  }
]
```

**必备状态**：每个页面至少覆盖 `默认态 / 加载态 / 空态 / 异常态` 四态。
若某态对当前页面**确实不适用**（例如纯表单页没有「空态」），必须在页面级用 `notApplicableStates` 显式声明，而不是默默省略——校验器会据此跳过检查并记录原因：

```jsonc
{
  "id": "page-refund-apply",
  "notApplicableStates": ["empty"],   // 纯表单页无空态，显式声明
  "states": [ ... ]
}
```

允许的值：`default` | `loading` | `empty` | `error`。

### 6.3 `interactions` — 交互

```jsonc
"interactions": [
  {
    "id": "ix-submit",
    "name": "提交任务",
    "on": { "event": "click", "target": "n-btn-submit" },   // 事件：click | change | submit | focus | blur | hover
    "conditions": ["status === 'draft'"],                   // 可选，满足才执行
    "actions": [                                            // 顺序执行
      { "type": "setState", "key": "loading", "value": true },
      { "type": "delay", "ms": 600 },
      { "type": "setState", "key": "status", "value": "submitted" },
      { "type": "message", "level": "success", "text": "提交成功" },
      { "type": "navigate", "pageId": "page-task-detail" }
    ]
  }
]
```

**`on.target` 可以是**：组件树里的真实节点 id、**合成节点 id**（见 §0.2）、或**带 `*` 的通配 id**。

**支持的 action 类型（白名单）：**

| type | 参数 | 说明 |
|---|---|---|
| `setState` | `key`, `value` | 设置页面状态变量，触发 `when` 重算。`value` 支持 `{{expr}}` |
| `setNode` | `target`, `prop`, `value` | 直接改某节点属性（如 disabled） |
| `gotoState` | `stateId` | 切到某个页面状态 |
| `navigate` | `pageId`, `stateId?`, `params?` | 跳转页面。`stateId` 指定目标页的初始状态；`params` 是对象，写入目标页变量，值支持 `{{expr}}` |
| `back` | — | 返回上一页（自有栈 → `entryFrom` 兜底，绝不跳出容器） |
| `scrollTo` | `target?` | 页内滚动到某节点并高亮 1.3s；省略 target 则回到画布顶部 |
| `message` | `level`(success/info/warning/error), `text` | 顶部轻提示。`text` 支持 `{{expr}}` |
| `showModal` / `hideModal` | `modalId` | 弹窗 |
| `showDrawer` / `hideDrawer` | `drawerId` | 抽屉 |
| `reset` | — | 复位到 `defaultStateId` |
| `delay` | `ms` | 延迟，用于模拟异步 |

**跳转的两条硬约定**：

1. **带参跳转的 params 在「源页」求值**，所以可以在里面写 `{{row.x}}`（点表格行时）或 `{{某状态变量}}`。
2. **目标页必须能独立渲染**：给 `states[].vars` 写默认值，别让页面只在「被带参跳进来」时才正常。校验器会检查 `navigate.stateId` 是否是目标页的状态、`params` 是否为对象。

### 6.4 `annotations` — 标注

标注是**评审沟通的载体**，用户点原型任意位置加气泡，AI 读取后改原型。

```jsonc
"annotations": [
  {
    "id": "an-1",
    "pageId": "page-task-list",
    "anchor": {
      "nodeId": "n-btn-submit",     // 可选：锚定到节点（推荐，改动后仍能跟随）
      "x": 0.42, "y": 0.31          // 归一化坐标（0~1），相对原型画布
    },
    "text": "提交按钮应该置灰直到表单校验通过",
    "category": "interaction",      // interaction | ui | data | copy | bug | question
    "author": "PM",
    "status": "open",               // open | resolved | rejected
    "createdAt": "2026-10-15T11:05:00+08:00",
    "replies": [
      { "author": "AI", "text": "已改为 disabled 绑定校验状态", "createdAt": "..." }
    ]
  }
]
```

**AI 处理标注的约定**：读取所有 `status === "open"` 的标注 → 逐条修改 `componentTree`/`states`/`interactions` → 把标注 `status` 改为 `resolved` 并在 `replies` 追加处理说明。

### 6.5 `prd` — 页面级 PRD 块（PrdBlock）

```jsonc
"prd": {
  "summary": "本页承载任务的全量浏览与快捷创建。",
  "sections": [
    { "id": "sec-goal",   "heading": "页面目标",   "body": "markdown 正文…" },
    { "id": "sec-ix",     "heading": "交互说明",   "body": "1. 点击…\n2. …" },
    { "id": "sec-rules",  "heading": "业务规则",   "body": "…" },
    { "id": "sec-states", "heading": "页面状态",   "body": "…" },
    { "id": "sec-flow",   "heading": "主流程", "type": "flow",   // ← 流程图小节
      "caption": "新建任务 → 提交 → 成功",
      "dir": "LR",
      "nodes": [ { "id": "t1", "label": "进入列表", "sub": "/tasks", "kind": "start" },
                 { "id": "t2", "label": "标题合法？", "kind": "decision" },
                 { "id": "t3", "label": "提交成功", "sub": "抽屉关闭", "kind": "end" } ],
      "edges": [ { "from": "t1", "to": "t2" },
                 { "from": "t2", "to": "t3", "label": "是" } ] },
    { "id": "sec-accept", "heading": "验收条件",   "body": "- [ ] …" }
  ],
  "reqIds": ["REQ-TASK-001", "REQ-TASK-002"]    // 关联的 EARS 条目
}
```

**`sections[]` 的两种形态：**

| `type` | 渲染 | 可编辑 | 说明 |
|---|---|---|---|
| 省略 / `"text"` | Markdown 正文（`contenteditable`，本地自动保存） | ✅ | 常规小节 |
| `"flow"` | **内嵌 SVG 流程图**（+ 可选 `body` 正文 + `caption` 图注） | ❌ | 节点/边契约见 `03-prd-structure.md` §5.5 |

> `flow` 小节用与「关系图」同一套分层布局引擎（Kahn 拓扑分层 + 重心法排序 + 回边虚线），
> 导出 Markdown 时降级为箭头链路（`**节点**：A → B` + `**流转**：A —[label]→ B`），不丢结构。

---

## 6.6 顶层 `dataModel` — 数据实体（机器可读）

```jsonc
"dataModel": {
  "entities": [{
    "id": "e-task",            // e- 前缀，全局唯一
    "name": "Task",            // 大驼峰实体名（AI 直接生成 TS interface 名）
    "table": "task",           // 物理表名
    "description": "一条可指派、可流转的最小工作单元",
    "pageIds": ["page-task-list", "page-task-detail"],   // 在哪些页面出现（PRD 按页展示）
    "fields": [
      { "name": "id",     "type": "string",  "required": true, "key": "pk", "note": "ULID" },
      { "name": "title",  "type": "string",  "required": true, "constraint": "≤ 50 字" },
      { "name": "status", "type": "enum",    "required": true, "constraint": "todo|doing|blocked|done" },
      { "name": "ownerId","type": "string",  "required": true, "key": "fk", "note": "→ user.id" }
    ],
    "relations": [ { "type": "belongs_to", "target": "e-user", "via": "ownerId" } ],
    "indexes": ["status", "ownerId"]
  }],
  "derived": [{
    "name": "逾期任务数",
    "expr": "count(task where dueDate < today and status != done)",
    "fallback": "无逾期时展示 0",        // 必写：除零 / 空值怎么显示
    "usedBy": ["page-task-list"],
    "reqId": "REQ-TASK-002"
  }]
}
```

| 字段 | 必填 | 校验 |
|---|---|---|
| `entities[].id` | ✅ | `e-` 前缀，全局唯一（ERROR） |
| `entities[].name` | ✅ | 实体名，重复 WARN |
| `entities[].table` | 建议 | 缺失 WARN（AI 会自行猜表名） |
| `entities[].fields` | ✅ | 非空（ERROR）；字段名实体内唯一（ERROR）；`type` 缺失 WARN |
| `fields[].key` | — | 每实体**恰好一个** `"pk"`（0 个 WARN / >1 个 ERROR），外键标 `"fk"` |
| `entities[].relations[].target` | ✅ | 必须是已存在的实体 id（ERROR） |
| `entities[].pageIds` | — | 必须是已存在的页面 id（ERROR） |
| `derived[].expr` / `fallback` | 建议 | 缺失 WARN |
| `derived[].reqId` | — | 必须是已存在的 REQ id（ERROR） |

> `type` 用实现无关写法：`string` / `integer` / `number` / `boolean` / `date` / `datetime` / `enum` / `json` / `array<T>`。
> 枚举必须把候选值写进 `constraint`（`a|b|c`）。派生指标一律进 `derived`，不要只写在正文里。

---

## 6.7 `MasterDetail` — 主子表（单页数据层级多时用）

**什么时候用**：一条主记录下挂着若干明细，用户需要**边扫主表、边看某一条的明细**。
一条巡检任务 → 若干巡检项；一张订单 → 若干商品行；一台设备 → 若干保养记录。

```jsonc
{
  "id": "n-md-task", "type": "MasterDetail",
  "props": {
    "bind": "no",              // 主表行的哪个字段用于匹配子表
    "bindTo": "taskNo",        // 子表的哪个字段与之匹配（省略则默认同 bind）
    "detailTitle": "巡检项",    // 子表标题栏文案（省略则取子表 props.title）
    "collapsible": true,       // 子表可展开收起（默认 true）
    "defaultCollapsed": false, // 初始是否收起
    "autoSelectFirst": true,   // 默认选中首行，避免子表一开始是空的（默认 true）
    "showAllWhenEmpty": false, // 无选中行时是否显示全部明细（默认 false，显示 emptyText）
    "emptyText": "请先在上方选择一条巡检任务",
    "detailTools": [{ "text": "列设置", "icon": "setting" }]
  },
  "children": [
    { "id": "n-task-table", "type": "Table", "props": { /* 主表 */ } },
    { "id": "n-item-table",  "type": "Table", "props": { /* 子表 */ } }
  ]
}
```

**结构约定（校验器强制）：**

| 规则 | 级别 |
|---|---|
| `children` 必须**正好 2 个**，且都是 `Table`（`[0]`=主表，`[1]`=子表） | ERROR |
| `bind` 必须是**主表数据**里存在的字段 | ERROR |
| `bindTo`（或 `bind`）必须是**子表数据**里存在的字段 | ERROR |
| 主表**不能**设 `props.rowClick`（点行 = 选中行） | ERROR |

**行为约定：**

1. **主表行点击 = 选中行**（不是跳页）。选中行加单选圆点 + 浅蓝底色；子表立即按 `bind` 过滤。
   要在主表上跳页，请用 `columns[].actions` 里的按钮（`n-xxx__act_*_detail`），
   容器会区分「点操作列按钮」与「点行」—— 点按钮**不会**同时触发选行。
2. **子表的 `data` 写全量**（所有主记录的明细），容器负责过滤。不要预先过滤好再写进去。
3. **子表可展开收起**：点标题栏（或左侧 ▾ 箭头）切换；点主表某行会**自动展开**子表。
   折叠态记在 `RT.mdCollapsed`（不落 localStorage，属会话内 UI 状态）。
4. **子表标题栏显示条数**：`· 共 N 条`，让用户知道该行挂了多少明细。
5. **空明细**：该行没有明细时显示 `props.emptyText`（默认「该行暂无明细」），不留空白。
6. **画布缩略图**里主子表以只读方式渲染（默认选中首行），不会污染当前页的选中态。

**运行期自检**：若主表选中行的 `bind` 值在子表 `bindTo` 字段里**一条都匹配不到**，
而子表本身是有数据的，容器会打一条警告（「检查 bind / bindTo 是否写对」）——
这类错误肉眼极难发现，因为页面看起来正常，只是子表永远为空。

> 主表配套的列表页三件套（`query` 查询条 / `toolbar` 操作条 / `pagination` 分页脚）
> 见 `references/05-component-states.md` §2.4。可运行示例：`assets/examples/example-04-master-detail.json`。

---

## 6.8 props 可读性契约（写了必须被读）

> 本节管**声明侧**：产物里写了、容器没读，会怎样。
> 它与 `check_ui_shape`（量渲染结果）互补 —— 几何判据对一个「写在哪都不改变像素」的键**完全免疫**。

### 6.8.1 为什么单列

容器不是 React：背后没有组件库兜底。每种 `type` 各有一个渲染器（**共 68 个**；注册有两种写法：`R.X=function(...)` 与 `R['List.Item']=function(...)`，后者漏掉就是一个类型整体判假红），
**逐字段手写读 props**（`R.X=function(p,ctx,node){ … p.title … }`），**没有整包透传**。

> **引用容器位置的约定（I-11 定）**：本节一律用**函数名 + 代码片段**锚定，**不靠行号**；万不得已给行号时，**必须同时写明版本**（`bbcf8cc` / 工作树 / dirty），读者默认按片段搜。两条约定各防一种病：
>
> - **行号漂移**：每加一个读取点，后面每行都后移。按行号翻会翻到不相干的代码，然后怀疑自己看错（实测：`3a1bb09` 的 `props.visible===false` 在 1216，`bbcf8cc` 在 1228，差 12 行）。
> - **版本混用**：**拿未提交的工作树去评判一个已交付提交**。教训很具体 —— 工作树里看到「宽度对账」那个函数，就断言「判据早就有、报告者误判」，而 `bbcf8cc` 里它根本不存在（出现 **0 次**，是返工才加的）。**工作树的代码不能当「已交付」的证据**：要断言「交付点有什么」，必须 `git show <sha>:<path>`。
>
> 两者同族：**能看到 ≠ 看到的是那一版**。
于是一个键写错，症状分四种，**没有一种会自己报错**：

| 症状 | 典型输入 | 画面 | 只有谁能看见 |
|---|---|---|---|
| 写了没人读 | `Upload.multiple` | 与不写**完全一样** | 声明侧 |
| 读了但读在别的类型上 | `Alert.text`（Alert 的正文键是 `message`） | 告警条空白，图标和边框都在 | 声明侧 |
| 值类型不对，开关失效 | `visible:"false"`（字符串） | 该隐藏的**照常显示**，方向相反 | 声明侧 |
| 键放错层级 | `renderItem` 写到节点级 | **照常渲染**（容器在 `R.List` 里兼容读 `node.renderItem`）—— 位置错但能跑，最难发现的一种 | 校验器的节点级未知字段 WARN + SS-01 的 R7（判 ERROR，要求挪进 `props`） |

**几何判据抓不到前三种**：它们的共性是「输出像素不变」，而 `check_ui_shape` 只量像素。
**`validate_prd_json.py` 的节点级未知字段检查也抓不到**：它比的是 `set(node) - NODE_KEYS`，
`props` 是白名单里的一个键，里面的内容它一个都不看。
所以必须另立一条**只读声明**的判据，就是本节的 SS-01。

### 6.8.2 什么算「可读」：四类键，四种取法

| 类别 | 定义 | 现阶段成员 | 怎么取 |
|---|---|---|---|
| **通用键** | 由 `renderNode` 对所有节点统一处理，不属任何单个渲染器 | `visible`（`false` → `display:none`；`true` → 恢复） | 契约的 `shared` 集，**对每个 type 都算可读** |
| **类型键** | 该 `type` 的渲染器（**含它调用的同文件 helper**）真正读的键 | 见契约 `byType` | 提取器闭包，见 §6.8.3 |
| **委托键** | `R.X` 把整包 props 转给 `R.Y`，X 自己不再读 | `Radio→Checkbox`、`TimePicker→DatePicker`、`Cascader→Select` | `X ⊇ Y`，按链求**不动点** |
| **插槽键** | `node.slots.NAME`，不是 props | `Header.extra`、`Card.extra/cover/actions`、`Drawer.footer`、`Result.extra` | 按 type 单独取，**不继承** |

> **通用键 `visible` 的语义边界**：它只做 `display:none` —— 节点**仍在 DOM**、尺寸为 0，
> 不要给被隐藏的节点挂标注（锚点会落到容器左上角）；要真正不生成节点，用节点级 `when`（渲染前就返回 null）。
> 也**不许在单个渲染器里重复实现它**：`R.Alert` 里加 `return null` 会被 `renderNode` 兜底成 `<span>`，
> 节点从 `DIV` 变 `SPAN`，按 class 取的截图与断言会一起失效。`visible` 必须是**布尔**：字符串 `"false"` 让 `===false` 不成立 → 开关失效、方向相反（R5）。

**七条规则（R1–R7）**

| # | 规则 | 违反的后果 |
|---|---|---|
| **R1** | 写进 `props` 的每个键，必须在**该 type** 的可读集里 | ERROR：声明空转 |
| **R2** | `slots` 的键同理，**按 type 判**，不许拿「全局有过就算」 | ERROR：插槽被静默丢弃（`FormItem` **一个插槽都不读**，只有 `children` 与 `help`/`extra` 两个 prop） |
| **R3** | 通用键（`visible`）不受 R1 约束，**每个 type 都可用** | 把它当「Alert 专属」会造出假红 |
| **R4** | 委托继承必须**机械求不动点**，不许手写补 | 手写必分叉：加一个委托渲染器就多一批假红 |
| **R5** | 值域也是契约：枚举与类型写错同样是 ERROR | `placement:"center"` 会静默退化成 `right`；`visible:"false"` 会静默失效 |
| **R6** | `Drawer` 的声明必须等于渲染：① `top`/`bottom` **不吃 `width`**，同时写 → ERROR；② `width` 必须是数字（`"600px"` 经 `Number()` 得 NaN → 静默回 420）；③ 只有 **420 / 560** 两档，`≥560 且 ≠560`（如 600）会渲成 560 → ERROR | ① 声明 560、渲成满宽；② 声明 `600px`、渲成 420；③ 声明 600、渲成 560。三条画面都「看起来正常」，只有量出来才知道 |
| **R7** | `props.renderItem` 里的**节点模板**同样是节点，受 R1–R6 约束，**无 `id` 也必须在范围内**（`renderItem` 是**单对象**，不是数组）。模板**只能**放在 `props.renderItem`：写在节点级 `node.renderItem` 时容器**兼容读**（能渲染），但那个位置不在契约键空间内 → **ERROR**，修法是挪进 `props`。寻址与取值见下表 | 只遍历 `children`/`slots` 会整棵漏掉；按 `id` 过滤会让模板节点静默跳过 —— 两种都是假绿。位置错的那条更麻烦：它**能跑**，所以只有声明侧判得出来 |

**R7 的寻址格式（模板节点怎么点名）**

模板节点常常没有 `id`，而且**加 `id` 也解决不了寻址**：`cloneTpl`（`assets/container/index.html`，找把 `id` 改写成 `<原 id｜tpl>-<行号>-<自增序号>` 的那三行，即 `x.id=(x.id||'tpl')+'-'+idx+'-'+(++uid)`）在渲染时改写每个模板节点的 `id`。也就是说作者写不写 `id`，运行期拿到的都不是它 —— 既不能拿 `data-node-id` 反查声明位置，也不能靠补 `id` 让消息可读。所以寻址只走**声明结构**：

```
<页面>/<节点段>( /<节点段> )*
节点段 := <id>(<type>)                 带 id 的节点：直接用 id
        | children[<k>](<type>)       无 id 的兄弟：在 children 里的原始下标（0 起，不跳过任何元素）
        | slots.<name>[<k>](<type>)   插槽里的节点（cloneTpl 也遍历 slots，所以 R2 同样适用）
        | props.renderItem(<type>)    模板根：持有它的那个节点的 props.renderItem
```

| 位置 | 路径写法 |
|---|---|
| 列表节点自己的键 | `合同列表/order-list(List).props.title` |
| 模板根（`List.Item`）的键 | `合同列表/order-list(List).props.renderItem(List.Item).props.title` |
| 模板里**第二个**同类型子节点 | `…props.renderItem(List.Item).children[1](Tag).props.color` |
| 模板里再套一层模板 | `…renderItem(List.Item).children[0](List).props.renderItem(Text).props.content` |

| 问题 | 规定 |
|---|---|
| 报错消息怎么点名 | 打**整条路径** + `.props.<key>`，**不要求**作者给模板节点补 `id`（补了也会被改写，见上） |
| 同一模板里出现两个同类型节点怎么区分 | 靠上层下标 `children[k]` / `slots.<name>[k]`。**没有 `renderItem[k]` 这种写法** —— 一份模板渲染 N 行数据仍然只有**一个**地址，所以模板内的错只报**一次**（重复出现只体现在分母的「M 处出现」里） |
| `{{item.xxx}}` 算不算「值」，值域判据进不进去判 | 算，但按**声明侧原值**判、不展开插值；键名照判（插值不是写死键的挡箭牌）。值域：`subst()` 只产出**字符串**（同文件找 `if(typeof v!=='string') return v;` 的 `function subst`，它把 `{{item.x}}` 一律换成 `String(x)` 或 `''`），而 `visible` 判的是 `props.visible===false`（`renderNode` 里那句 `if(props.visible===false) el.style.display='none'`）→ **布尔键与数值键写插值一律 ERROR**（`visible:"{{item.on}}"` 永远不隐藏；`Drawer.width:"{{item.w}}"` 在声明侧核不出 420/560 两档，见 R6）。**字符串键**（`title` / `description` / `content` 等）允许插值，不做内容校验 |

> **两条禁令**：① 不许把「给模板节点加 `id`」当修法 —— 那等于要求作者**为了能报错而写**，而且加了也会被改写；② 不许用「`data` 是空的所以跳过」当理由 —— SS-01 遍历的是**声明树**，与有没有数据行无关。`renderItem` 整段不存在才是「没有可判对象」，此时不报错，也**不是** INCOMPLETE。
>
> **顺带记一条容器缺口**（不在 SS-01 职责内，别指望判据拦）：`cloneTpl` 只替换 `props` 里的字符串值，**节点级 `when` 不参与插值** —— 模板里写 `when:"{{item.x}}"` 会走表达式求值，结果与数据行无关（求值失败按 `true` 处理并 warn，或取不到值恒假），所以模板内目前**没有「按行隐藏」的合法写法**。`visible` 也救不了（插值必失效）。要按行隐藏，只能等容器补 `renderItem` 的行内条件，或把行做成子节点由 `data` 驱动。
>
> **边界**：本节只管**节点 `props` 的一级键**与**插槽名**。
> `columns[]` / `items[]` / `query[]` / `options[]` 这些**数组元素的内部字段**不在本判据内
> （它们的契约在 `05` 各 type 行的括号说明里）。不划这条边界，键空间会无限膨胀。

### 6.8.3 白名单从哪来（不许手写）

| 项 | 约定 |
|---|---|
| 生成器 | `scripts/props_contract.py`，从容器源码机械提取（必须同时认 `R.X=` 与 `R['X']=` 两种注册） |
| 契约文件 | `assets/container/props-contract.json`，带**两个**哈希：容器 `sourceSha256` + 不支持清单 `unsupportedSha256` |
| 提取闭包 | 渲染器函数体 **+ 它调用链上的同文件函数**（`buildFilterBar` / `buildQueryBar` 等），可传递。**机械判定只有一条**：调用点**第一个实参恰好是 props 形参**才跟进（现状所有渲染器首参都叫 `p`，所以等价于「第一个实参写作 `p`」）；看实参位置，不看函数名 |
| 不跟进的调用 | `getPath(o,p)`（那个 `p` 是**路径串**，`p.split`）、`parseAtom(t,p,vars)`（那个 `p` 是 **token 位置对象** `{i:0}`，`p.i`）—— 它们的 `p` 不是 props。不加这条会凭空长出 `split` / `i` 两个「合法键」，是**假绿**；同理不跟进动态分发（`fn(props,…)` 里的 `fn` 是变量，跟进去会把所有类型串成一锅） |
| 注释与字符串 | 词法扫描必须跳过 `//`、`/* */`、字符串 / 模板串 / 正则字面量后再取 `p.<key>`。容器里确有注释提到 `p.xxx`（`R.Row` 那句「Col 自己读不到 `p.gutter`」），它今天不制造假键（`R.Row` 真的读 `p.gutter`）；但**白名单被注释放行比没有白名单更危险**：下一条注释写一个不存在的键，就多一个永远抓不到的假绿 |
| 前提 | 所有渲染器**首参必须叫 `p`**（现状 68/68）。提取器据此取数；真要改名，它必须**非 0 退出并说明签名变了**，不许静默取到 0 个键 |
| 禁用的取法 | 「按 `R.*` 区块切段」—— 段与段之间的 helper 会被算成**上一个渲染器**的键。实测：`queryId` / `resetId` 由 `buildFilterBar` 读，切段法把它们记在 `Transfer` 名下，于是 `Table.queryId` 变「疑似写错节点」、`Transfer.queryId` 变「合法」——**一假红一假绿** |
| 同步 | 任一枚哈希与其源文件不符 → **INCOMPLETE**，不许判 PASS（判一份过期白名单比不判更危险）。只校容器是**不够的**：改了清单不重生成，契约里会留一份过期的理由表，没有任何门会发现 |
| 清单缺失 / 格式不符 | 生成器**非 0 退出、不写契约**。宁可没有契约（→ INCOMPLETE），也不许产出一份「条目 0、理由全丢」的契约 —— 那种退化看起来一切正常 |

> **为什么必须机械提取**：手写白名单不会当场错，它会在某次改容器后**悄悄分叉** ——
> 那种错没有报错、没有红、只有一份看起来很像样子的假绿。

### 6.8.4 SS-01 判定：三态、分母、消息

| 状态 | 触发 | 说明 |
|---|---|---|
| `PASS` | 所有 `(type,key)` 都在可读集 | 必须同时打出分母 |
| `ERROR` | 任一 `(type,key)` 越界 | 逐条点名，命中不支持清单时附**理由 + 替代写法** |
| `INCOMPLETE` | 契约缺失 / 无法解析 / 与容器不同步；**或**产物里一个节点级 props 都没有 | 「判据在、没有可判的输入」 |

| 口径 | 规定 |
|---|---|
| 分母 | `(type, key)` **去重**后的组合数，不是出现次数（`placement` 写 9 次也只是 1 个键） |
| 打印 | `分母 N 个 type×key（来源 M 处出现）` —— 两个数都要有，否则读不出覆盖面 |
| 不设 WARN | 「键被别的类型读过」不是作者的处境差异，是提取器归属没做对的痕迹。判成 WARN 就是**假绿**：实测 `example-06` 的 `Alert.text`（2 处，告警条整条空白）在 WARN 口径下永远是绿的 |
| 消息形态 | **整条路径** + `.props.<key>` + 结论 + 修法，段语法见 §6.8.2：普通节点 `页面/节点id(type).props.key`，模板节点 `…props.renderItem(List.Item).children[1](Tag).props.fooBar`（**不要求**补 `id`）。模板内的同一 `(type,key)` 只报**一次**，不按数据行重复。只报「未知字段」等于把题面丢回给作者。`id` 唯一性由 `validate_prd_json.py` 另判，本节只依赖它成立 |
| 闸门 | `ERROR` → 非 0 退出。`INCOMPLETE` 默认不拦（存量产物），但 `check_release.py` 必须把它当失败 —— 闸门自己没装好，不许算过 |

**SS-01 抓不到什么**（写在这里，免得下一个人以为它全能）：
它判的是「这个键有没有人读」，**不判「读得对不对」**。容器把 `message` 读成 `title` 这种
语义错读，键是合法的、渲染是错的，SS-01 会给绿 —— 那要靠标注与评审。

### 6.8.5 明确不支持的键：唯一真源在 `references/`

| 项 | 约定 |
|---|---|
| 文件 | **`references/props-unsupported.json`** |
| 为什么在这 | 它是**规范内容**（「这个键不生效，改用 X」），不是实现细节。放在 `scripts/` 下等于把规范写在工程目录里 |
| 谁读 | `scripts/props_contract.py` 只**读**它并原样并入契约；`validate_prd_json.py` 命中时用它生成修法。**仓库内不许有第二份副本** |
| 查找顺序 | 先 `(type, key)` 精确命中，再退到 `("*", key)`，都没有时用通用措辞 |
| 迁移顺序 | **先改读取路径、再删旧副本**。反了会静默降级：实测删掉 `scripts/` 旧文件后生成器仍 exit 0、不支持条目 0、无任何警告，而「理由 + 替代」整块消失 |
| 什么该进 | 「明知容器不读、且**不应该**读」的键。只是「还没实现」的不进来 —— 那是缺陷，不是裁决 |
| 每条必填 | `type` / `key` / `why`（为什么不支持）/ `instead`（改成什么）。**答不出 `instead` 的条目不许进**：只告诉人「不能写」而不给出口，下一次他会换个地方再写一遍 |

`05-component-states.md` §2 的 props 列是**语义承诺**（AntD 上应该长这样），
本文件是**可执行事实**（容器实际读了什么）。两者不一致时**以契约为准**，
差额要么补容器、要么进不支持清单 —— 不许两边各说一套。

### 6.8.6 造红（验收用，缺一条就是没接线）

> **这是 §6.8 全节的验收清单，不只属 SS-01**：最后一列「归属」= `backlog.json` 里的迭代卡号（治理工作区，不随包发布 —— 包内读者只需知道这行归哪张卡）。
> 表与卡必须同时改 —— 表是验收清单，卡是派工单，**两处两说就是两套口径**。

| 输入 | 期望 | 证明什么 | 归属 |
|---|---|---|---|
| `Table` 节点写 `rowKey` | ERROR，且消息带替代写法 | 全局 0 命中的键会被点名 | XX-050 |
| `FormItem` 写 `slots.extra` | ERROR | 插槽按 type 判，不吃「全局有过」 | XX-050 |
| `Alert` 写 `visible:"false"` | ERROR（类型） | 值域判据能红，不是只判键名 | XX-050 |
| `Drawer` 写 `width:600` / `"600px"` | 两条都 ERROR | 声明—渲染对账（600 会渲成 560；`600px` 会渲成 420） | XX-050 |
| 删掉 `assets/container/props-contract.json` | INCOMPLETE，且**不是** PASS | 判据缺失不许冒充通过 | XX-050 |
| 改 `references/props-unsupported.json` 任一条 `why` 而不重生成契约 | INCOMPLETE | 清单的哈希也参与同步，否则过期理由表无人发现 | XX-050 |
| `example-03-nav-tree.json` | PASS（80 个 type×key） | 绿样本：接线后不能把干净产物判红 | XX-050 |
| 在容器里加一句注释 `/* 读 p.fooBar */` 并重生成契约 | 任何 `byType` 都不含 `fooBar`；产物里写 `fooBar` **仍 ERROR** | 注释不是代码。白名单被注释放行 = 一个永远抓不到的假绿 | XX-050 |
| 查契约里有没有 `split` / `i` | 任何 `byType` 都不含 `split` / `i` | `getPath` / `parseAtom` 的 `p` 不是 props；不加这条会凭空长键 | XX-050 |
| 往 `List.renderItem` 模板里塞 `Upload.multiple` | ERROR，路径形如 `页面/列表id(List).props.renderItem(List.Item).props.multiple` | 模板内部在范围内，**且无 `id` 的模板节点不许被跳过** | XX-054 |
| 同一模板里放两个同类型 `Tag`，只给**第二个**写死键 | ERROR 只点 `children[1](Tag)`，不点 `children[0]` | 同类型兄弟靠下标区分；按 type 去重会把两个当成一个 | XX-054 |
| 把 `props.renderItem` 整段删掉 | **PASS**（不异常、不 INCOMPLETE） | 「不存在」与「找不到」在实现里长得一样；这条专防把「没有模板」判成「遍历失败」 | XX-054 |
| 把同一个模板从 `props.renderItem` 挪到节点级 `renderItem` | ERROR，消息含「挪进 `props`」 | 这个位置**能跑**（容器兼容读），不判就永远没人挪 —— 声明空转里最隐蔽的一类 | XX-054 |
| `data:[]` 的 `List` 但带模板、模板里有死键 | ERROR | 判据读声明树，与有没有数据行无关 | XX-054 |
| 模板里写 `visible:"{{item.on}}"` | ERROR（布尔键不许插值） | 插值经 `subst` 只会得到字符串，`===false` 永不成立 —— 写了等于没写 | XX-054 |

### 6.8.7 新增一个 props 键的流程（四步，缺一步必分叉）

```
1) 容器真的读它：在**该 type** 的渲染器（或其 helper）里出现 `p.<key>`
2) 重新生成契约：python3 scripts/props_contract.py   → sourceSha256 变
3) 若决定**不做**：写进 references/props-unsupported.json（why + instead）
4) 05 §2 该 type 行同步；`--check` 断言两者一致
```

> 只做第 1 步 = 契约过期 → 全线 INCOMPLETE；只做第 4 步 = 文档承诺一个不存在的键。
> 这四步的顺序不能换：**先有读取，再有白名单，最后才是文档**。

---

## 7. `components` — 关键组件与状态定义

给设计和前端直接复用的"零件说明书"。页面组件树通过 `ref` 引用。

```jsonc
"components": [
  {
    "id": "c-task-card",
    "name": "任务卡片",
    "antd": "Card",                      // 对应的 AntD 组件
    "description": "列表中的单条任务",
    "anatomy": ["状态徽标", "标题", "负责人头像", "截止时间"],
    "variants": [
      { "name": "default", "description": "常规" },
      { "name": "overdue", "description": "已逾期", "token": "color-error" }
    ],
    "states": ["normal", "hover", "selected", "loading"],
    "tokens": { "radius": "6px", "padding": "12px 16px", "shadow": "0 1px 2px rgba(0,0,0,.06)" },
    "spec": "标题单行省略；截止时间 < 今天时用 error 色"
  }
]
```

---

## 8. `stateMachines` — 状态机

```jsonc
"stateMachines": [
  {
    "id": "sm-task",
    "name": "任务状态机",
    "entity": "Task",
    "initial": "todo",
    "states": [
      { "id": "todo",   "name": "待办", "type": "normal" },
      { "id": "doing",  "name": "进行中", "type": "normal" },
      { "id": "blocked","name": "阻塞", "type": "warning" },
      { "id": "done",   "name": "已完成", "type": "success" }
    ],
    "transitions": [
      { "id": "t-1", "from": "todo",    "to": "doing", "trigger": "负责人点击开始", "role": "u-owner", "guard": "有负责人", "action": "记录开始时间",
        "ui": { "pageId": "page-task-list", "interactionId": "ix-task-start" } },
      { "id": "t-2", "from": "doing",   "to": "blocked","trigger": "标记阻塞",     "role": "u-owner", "guard": "", "action": "",
        "ui": { "pageId": "page-task-list", "interactionId": "ix-task-block" } },
      { "id": "t-3", "from": "blocked", "to": "doing", "trigger": "解除阻塞",     "role": "u-owner", "guard": "", "action": "",
        "ui": { "pageId": "page-task-list", "interactionId": "ix-task-unblock" } },
      { "id": "t-4", "from": "doing",   "to": "done",  "trigger": "标记完成",     "role": "u-owner", "guard": "所有子任务完成", "action": "通知关注者",
        "ui": { "pageId": "page-task-list", "interactionId": "ix-task-finish" } },
      { "id": "t-5", "from": "todo",    "to": "blocked","trigger": "超过 3 天无人认领，自动标记阻塞", "guard": "无负责人", "action": "通知组长",
        "ui": { "kind": "system" } }
    ]
  }
]
```

`transitions[].ui` 是这条转移的**界面落点**：人工转移写
`{ "pageId": "page-xxx", "interactionId": "ix-xxx" }`，
系统自动流转写 `{ "kind": "system" }`（没有按钮可点，不需要 `pageId`）。三态写法、L1/L2/L3 分层、
以及「`page-enter` 只能用在需求上」这条限制，见 `09-behavior-model.md` §2.4。

> 上面 4 个 `interactionId`（`ix-task-start` / `ix-task-block` / `ix-task-unblock` / `ix-task-finish`）
> 必须在 `pages[].interactions` 里真实存在，否则报 L2，**默认档与交付档都是 ERROR**。
> **这四个 id 是示意，本文没有在别处定义它们** —— §6.3 的 `interactions` 示例只展开了 `ix-submit`。
> 落地时按你页面的实际交互替换，不要把它们当真源照抄。写成指向不存在的 id，比不写更糟：
> 不写是"还没补"，写错是"声称补了"。

`transitions[].system: true`（或 `role: "system"`、或 `ui.kind: "system"`）表示**系统自动流转**
（定时任务 / 支付回调 / 超时关闭），校验器不会要求它有对应按钮。没有这个标记的人工转移，
必须有一条 `capability` 覆盖、且 `ui` 指得出页面里的按钮，否则报 ERROR。

---

## 8.5 `capabilities` — 命令策略（角色 × 状态 × 动作）

```jsonc
"capabilities": [
  {
    "id": "cap-task-start",          // cap- 前缀，全局唯一
    "name": "开始任务",               // 用户看到的动作名
    "entity": "Task",                // 作用于哪个实体
    "actor": ["u-owner"],            // 哪些角色可以执行（引用 users[].id）
    "from": ["todo"],                // 允许执行的业务状态；[] = 不限状态
    "guard": "任务已有负责人",         // 状态之外的前置条件
    "policy": "disabled",            // hidden | disabled | reject（不可用时怎么办）
    "reason": "仅「待办」任务可以开始，当前为「进行中」",  // 用户能据此行动的一句话
    "to": "doing",                   // 成功后进入的状态（无状态变化可省略）
    "effect": "记录开始时间",          // 副作用
    "page": "page-task-list",        // 主要出现位置
    "requirement": "REQ-TASK-004",   // 对应哪条 EARS 需求
    "onFail": "无负责人时提示先指派"    // 失败后用户能做什么
  }
]
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` / `name` / `entity` / `actor` / `from` / `policy` | ✓ | `from` 允许空数组，但字段必须写出来 |
| `reason` | policy 为 hidden/disabled **且 `from` 非空**时必填 | 不能写「状态不允许」这类空话 |
| `guard` | | 写具体条件，不要写「条件满足」 |
| `to` | | 必须能在状态机里找到 `from → to` 的转移 |
| `stateField` | | 行级取值字段名，默认 `status`（表格行内动作用） |
| `dataScope` | | 数据范围（如「仅本人名下」），配合列表默认筛选 |
| `onFail` | | 失败原因 + 下一步动作 |

> **一条命令只能有一个主页面**（`pages[].contract.owns`），其他页面可以引用同一个 `capability.id`，
> 但不能各自实现一套禁用逻辑 —— 这是防止「列表能删、详情不能删」的唯一手段。

---

## 9. `requirements` — EARS 需求条目

详细语法见 `references/02-ears-spec.md`。结构如下：

```jsonc
"requirements": [
  {
    "id": "REQ-TASK-001",
    "moduleId": "m-task",
    "pageId": "page-task-list",
    "ui": { "interactionId": "ix-task-create" },  // 这条需求落在哪个按钮上：三态之二/之三见下
    "pattern": "event-driven",       // ubiquitous | event-driven | state-driven | option | unwanted
    "title": "创建任务",
    "role": "u-owner",               // 角色（引用 users.id）
    "trigger": "在任务列表页点击『新建任务』",   // 触发
    "rule": "任务标题必填且 ≤ 50 字；负责人可空", // 规则
    "guards": [                      // 前置校验（页面上表现为阻断/提示）
      { "text": "标题为空时提交按钮禁用", "kind": "block" },
      { "text": "负责人为空时提示可稍后指派", "kind": "warn" }
    ],
    "effects": [                     // 成功后的副作用（写给研发看，不是渲染指令）
      { "text": "列表新增该任务", "target": "page-task-list" },
      { "text": "通知被指派人", "target": "REQ-NOTIFY-002" }
    ],
    "stateMachine": "sm-task",       // 关联状态机（可空）
    "expected": "系统在列表中新增一条状态为『待办』的任务，并提示创建成功", // 预期
    "acceptance": [                  // 验收条件（可测）
      "标题为空时提交按钮禁用",
      "创建成功后列表首行出现该任务",
      "创建成功后抽屉关闭"
    ],
    "priority": "P0",
    "source": "user",                // user | demo | inferred
    "status": "confirmed"            // draft | confirmed
  }
]
```

| 字段 | 必填 | 校验器 | 说明 |
|---|---|---|---|
| `ui` | 交付档必填 | **有**（XX-020） | 三选一：`{"interactionId":"ix-xxx"}` / `{"kind":"system"}` / `{"kind":"page-enter"}`。**不写 `pageId`**，用同级 `pageId` 定位；**写了是 L3 硬错（两档都 ERROR）**。分层 L1/L2/L3 见 §13.1 |
| `guards[]` | — | **有**（XX-023，字段级） | `{ "text": "...", "kind": "block" \| "warn" }`。`block` = 拦住提交，`warn` = 提示但放行。**写了就必须写对**：`kind` 不在 `block`/`warn` 里、`text` 为空、整体不是数组，都报 ERROR（两档一致）。**缺失不报错**（存量产物没有它） |
| `effects[]` | — | **有**（XX-023，字段级） | `{ "text": "...", "target": "页面 id \| 需求 id \| 实体字段" }`。`text` 必填；`target` 可空。同样只校验"写了以后的形状"，不校验"有没有写" |

> **这两行的严重度分层是有意的**：缺失 = WARN 都不给（存量产物合法），写错 = ERROR。
> 如果"缺失"也报错，5 个示例与所有历史产物会当场全红；如果"写错"只报 WARN，
> 那 `kind` 的枚举就等于不存在 —— 而这正是 XX-023 立项的原因：模型想到了前置校验，
> 却**没有地方写**，写进散文里换个模型读就丢（QMS 实测：「发起检验要先编质检标准」全靠散文）。
>
> 条数会单独打一行 `行为补充：guards=N（K/M 条需求） effects=…`。
> 只报"字段存在"是不够的：`guards: []` 和 7 条像话的守卫，在"字段存在"这个口径下完全一样。

---

## 10. `boardPlan` — PRD 板块计划

**卡点 B 的确认对象已从「板块」改为「切片清单」**（`shaping/slices.json`，见 `11-slice-delivery.md`）。
`boardPlan` 现在是切片清单在数据契约里的投影：每片对应一个或多个条目，用来驱动容器左栏的板块导航与 PRD 组装顺序，
**不再单独作为人工确认的颗粒度单位**。

```jsonc
"boardPlan": [
  { "id": "bp-1", "order": 1, "name": "任务列表", "pageId": "page-task-list", "moduleId": "m-task", "status": "done",  "reqIds": ["REQ-TASK-001"] },
  { "id": "bp-2", "order": 2, "name": "任务详情", "pageId": "page-task-detail","moduleId": "m-task", "status": "doing", "reqIds": [] }
]
```

`status`：`todo`（未开始）| `doing`（撰写中）| `done`（已完成）。

---

## 11. `glossary` / `openQuestions`

```jsonc
"glossary": [ { "term": "任务", "definition": "一条可指派、可流转的最小工作单元" } ],

"openQuestions": [
  { "id": "q-1", "question": "是否需要支持子任务？", "owner": "PM", "status": "open", "answer": "" }
]
```

---

## 12. 最小可渲染对象（Minimum Viable Document）

当用户只想快速看个原型时，至少要给：

```jsonc
{
  "meta": { "schemaVersion": "1.0", "product": "示例", "currentPageId": "page-1" },
  "pages": [{
    "id": "page-1", "name": "首页", "route": "/",
    "defaultStateId": "s-default",
    "componentTree": { "id": "n-root", "type": "Layout", "props": { "layout": "header-content" }, "children": [] },
    "states": [{ "id": "s-default", "name": "默认态", "vars": {}, "overrides": [] }],
    "interactions": [], "annotations": [],
    "prd": { "summary": "", "sections": [], "reqIds": [] }
  }],
  "modules": [], "users": [], "userFlows": [], "dataModel": { "entities": [] }, "components": [],
  "stateMachines": [], "requirements": [], "boardPlan": [], "glossary": [], "openQuestions": []
}
```

> 但**交付给研发 / 交给 AI 开发**时不是这个标准：至少要补齐 `modules` + `requirements`（EARS）
> + `dataModel`，否则 `devspec.json` 的 `devNotes` 会列出 `missing` 项，AI 只能自行发挥。
> 校验器也会给出「机器可读性」WARN。

---

## 13. 输出约定

1. 完整产物写为**单个 JSON 文件**（如 `XX-PRD.data.json`），与容器 `index.html` 同目录。
2. 容器通过 `<script type="application/json" id="iprd-data">` 内联数据，或 `fetch('./XX-PRD.data.json')` 读取；**交付时优先内联**（双击即可用，无跨域问题）。
3. 所有 ID 全局唯一；引用必须存在（校验脚本会检查悬空引用）。
4. 时间戳统一 ISO 8601 带时区。
5. 交付给 AI / 研发时，除了 `.html` 容器，还要给出 **`{产品}.devspec.json` + `AGENT.md`**（容器顶栏「⬇ 开发交接」一键导出）。

### 13.1 校验档位：默认档 vs `--profile=delivery`

```bash
python3 scripts/validate_prd_json.py <file.json|file.html>                     # 默认档
python3 scripts/validate_prd_json.py --profile=delivery <file.json|file.html>  # 交付档
```

两档跑的是**同一份检查代码**，只有一处开关不同（`validate(..., strict=)`）：新语义检查在默认档降为 WARN。
下面这张表按"缺了会怎样"写，不按代码结构写：

| 检查项 | 默认档 | `--profile=delivery` | 走哪个开关 |
|---|---|---|---|
| 顶层 `tasks` 缺失/为空 | **完全不检查**（连提示都没有） | ERROR | `strict` 分支（`validate` 开头） |
| 顶层 `capabilities` 缺失/为空 | 字段本身不问，但**通常会间接红**：页面 `contract.owns` 引用它时按悬空引用报 ERROR —— 实测默认档 **9 条** | ERROR：同一批悬空引用 **9 条 + 1 条**「缺少顶层 capabilities」= **10 条** | `strict` 分支 + 悬空引用检查 |
| `pages[].contract` **缺失** | 仅当该页 `entity` 有对应状态机时 WARN；否则**静默** | ERROR（不看 `entity`） | `strict` 分支（页面职责段） |
| `pages[].contract` **字段不全**（`CONTRACT_REQUIRED`） | ERROR | ERROR | 无条件 |
| `requirement.ui` 缺失（L1） | WARN | ERROR | `gate()` |
| `transitions[].ui` 缺失 / 缺 `pageId` / 缺 `interactionId` / `ui` 不是对象（L1） | WARN | ERROR | `gate()` |
| **L2 悬空引用**：`pageId` 不存在、`interactionId` 不在该页 `interactions` 中、需求有 `interactionId` 却无 `pageId` | **ERROR** | **ERROR** | 直接 `rep.error()` |
| **L3 结构错**：需求的 `ui` 不是对象、`kind` 非法、既无 `interactionId` 也无合法 `kind`、需求的 `ui` 里出现 `pageId` | **ERROR** | **ERROR** | 直接 `rep.error()` |

四处容易看错的地方：

- **默认档"不检查"和"WARN"不是一回事。** `tasks` 在默认档连警告都没有，且**没有下游检查能兜住它**
  （`tasks` 只参与 ID 唯一性）—— 跑通默认档，不能据此说"任务清单没问题"，只能说"没人问过它"。
  `capabilities` 不同：字段本身默认档不问，但页面 `contract.owns` 一旦引用它，删掉就红。
- **`contract` 默认档的静默依赖 `page.entity`。** 页面不写 `entity` 时，这条检查对它是隐形的；
  交付档不看 `entity`，每个页面都必须有 `contract`。
- **`capabilities` 那行是唯一"两档数字不同"的**：默认档 9 条、交付档 10 条（多出的 1 条是字段级的"缺少顶层
  `capabilities`"，那 9 条是同一个事实在下游 `contract.owns` 上的回声）。别以为交付档"更严"，它只是多报了 1 条
  本该自己报的。
- **L2 / L3 没有过渡期。** 只有 L1（"还没写"）两档有别；"写错了"在任何档位都是 ERROR。
  写一个指向不存在交互的 `interactionId`，比不写更糟：不写是漏，写错是**声称补过了**。

**交付档的唯一调用者**是 `scripts/check_release.py` 的 DoD 1，对 `assets/examples/example-05-behavior-model.json`
一个文件开 `--profile=delivery`（其余 4 个示例走默认档）。detail 行会带
`profile=delivery:example-05-behavior-model.json`，用来断言"这一档真的被跑了"——
**一个没有人调用的档位，等于第二扇不存在的门。**

默认档存在的理由只有一个：**存量产物**。没有 `ui` 的老 PRD 不能升级当天全线判红，
否则人的第一反应是关掉检查，而不是补齐链路。
