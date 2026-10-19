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
  "slots": { "extra": [ /* Node[] */ ] }   // 具名插槽（如 Card.extra / FormItem.help）
}
```

**Node 编写规则：**
- `id` 必须唯一且稳定 —— 交互和标注靠它锚定，重新生成原型时不要改已有 id。
- 只使用 `05-component-states.md` 白名单里的 `type`；未知类型容器会降级为 `<div>` 并打警告。
- 数据驱动的列表用 `props.data` + `props.renderItem` 声明，不要手写 N 个重复节点：
  ```jsonc
  { "id": "n-list", "type": "List", "props": { "data": ["a","b"], "renderItem": { "type":"List.Item", "props": { "title": "{{item}}" } } } }
  ```
  > `renderItem` 必须写在 **`props` 内**（写在节点级容器不认，会静默渲染成空列表；校验器会给 WARN）。模板占位用 `{{item.字段}}` / `{{item}}` / `{{index}}`。
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
      { "id": "t-1", "from": "todo",    "to": "doing", "trigger": "负责人点击开始", "role": "u-owner", "guard": "有负责人", "action": "记录开始时间" },
      { "id": "t-2", "from": "doing",   "to": "blocked","trigger": "标记阻塞",     "role": "u-owner", "guard": "", "action": "" },
      { "id": "t-3", "from": "blocked", "to": "doing", "trigger": "解除阻塞",     "role": "u-owner", "guard": "", "action": "" },
      { "id": "t-4", "from": "doing",   "to": "done",  "trigger": "标记完成",     "role": "u-owner", "guard": "所有子任务完成", "action": "通知关注者" }
    ]
  }
]
```

`transitions[].system: true` 表示**系统自动流转**（定时任务 / 支付回调 / 超时关闭），
校验器不会要求它有对应按钮。没有这个标记的人工转移，必须有一条 `capability` 覆盖，否则报 ERROR。

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
    "pattern": "event-driven",       // ubiquitous | event-driven | state-driven | option | unwanted
    "title": "创建任务",
    "role": "u-owner",               // 角色（引用 users.id）
    "trigger": "在任务列表页点击『新建任务』",   // 触发
    "rule": "任务标题必填且 ≤ 50 字；负责人可空", // 规则
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
