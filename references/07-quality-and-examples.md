# 质量验收标准与反例（Quality Criteria）

> 用于自检产物、也用于给用户解释"为什么这份 PRD 合格"。
> 完整 few-shot 示例见 `assets/examples/`：
> - `example-01-task-board.json` — Web 中后台单模块（列表 + 详情），双页面；**列表行/行内按钮 → 详情页带参跳转**；含 `dataModel` 与「创建任务主流程」流程图
> - `example-02-refund-flow.json` — 移动端多角色审批流 + 状态机；含 `dataModel` 与「退款申请与审批流程」流程图
> - `example-03-nav-tree.json` — **多模块 + 多级页面**（4 模块 / 8 页面 / 4 个子页面），用于验证左侧树形导航；含行级跳转、按钮级跳转、删除确认弹窗、5 实体 `dataModel`、3 张流程图
> - `example-04-master-detail.json` — **主子表（MasterDetail）**：巡检任务管理（主表 9 行 + 子表巡检项联动、子表可展开收起、单选圆点、查询条 / 工具条 / 分页脚）；含修改抽屉（Drawer）、删除对话框（Modal）、带参详情页
>   > 该示例由 `assets/examples/gen_example04.py` 生成，改数据请改脚本再重跑，不要手改 JSON
> - `example-05-behavior-model.json` — **行为建模（角色 × 状态 × 命令）+ 页面职责切分**：采购订单 6 状态 / 4 角色 / 5 页面 / 10 条命令策略；演示「置灰 / 隐藏 / 点了才拒绝」三种策略、按角色拆页（申请 / 审批 / 到货登记）、`contract` 与 `owns` 唯一性、命令策略矩阵
>   > 该示例由 `assets/examples/gen_example05.py` 生成，改数据请改脚本再重跑，不要手改 JSON

---

## 1. 五维验收标准

### 维度 1：澄清充分性（Clarification）

| 检查项 | 通过标准 |
|---|---|
| 产品定位 | 有一句话定位 + 定位陈述 + ≥1 条非目标 |
| 用户角色 | ≥1 个角色，含诉求与痛点 |
| 用户流 | ≥1 条闭环主路径（有入口有出口） |
| 模块清单 | 每个模块有目标与优先级 |
| 页面清单 | 每个页面有路由、目标、入口、出口 |
| 待澄清问题 | P0 问题全部有答案或默认值 |

### 维度 2：需求规范性（EARS）

| 检查项 | 通过标准 |
|---|---|
| 句式正确 | `pattern` 与 `trigger` 填写一致 |
| 单一响应 | 每条需求只描述一个响应 |
| 无主观词 | 无"友好/快速/合理/尽量/美观/尽可能" |
| 无实现细节 | 无表名/接口路径/框架名 |
| 可验收 | 每条 ≥2 条 acceptance，含边界/异常 |
| 可追溯 | 每条有 moduleId，页面相关有 pageId |
| 来源标注 | `source` 正确，`inferred` 有对应 openQuestion |

### 维度 3：原型完整性（Prototype）

| 检查项 | 通过标准 |
|---|---|
| 可渲染 | JSON 通过校验，容器无报错、无未知类型警告 |
| 状态覆盖 | 每页 ≥4 态（默认/加载/空/异常） |
| 交互可用 | 主路径上的关键按钮点击有反馈（改状态/跳转/提示） |
| 组件规范 | 全部 `type` 在白名单内 |
| 视觉规范 | 使用 AntD token，状态色语义正确 |
| 数据真实 | 示例数据像真实数据（非"foo/bar/测试1"） |
| 窄栏可读 | 左/右栏挤压中栏时，靠容器缩放（25%~300%）+ 平移即可看全；**不得靠删页面/减列/缩字号腾空间** |
| 跳转走通 | 主路径上的页面用 `navigate` 串起来（列表→详情→返回），不是孤岛；带参跳转的目标页能独立渲染（`states[].vars` 有默认值） |
| 流程图齐全 | 每页 ≥1 个 `type:"flow"` 小节（主路径 + 关键分支），有 start/end、decision 出边带 label、无孤岛节点 |
| 关系图成立 | 顶部「关系图」里所有页面都出现，且**可达**；连线数与 `navigate` + `entryFrom` 一致。**「可达」的判定式见 `04-container-schema.md` §0.2「页面图与可达性」**：从 `meta.currentPageId` 出发、**只沿 `navigate` 跳转边** BFS 可达全部页面（`entryFrom` 画的虚线只作诊断，**不算进路**）；不许拿左栏导航切换当替代 |
| 关系图可读 | 卡片不重叠、分层连续（无巨宽空白）；图在视口里居中、缩放后滚动范围精确；拖拽后位置稳定（重绘/刷新不弹回），卡片不会被拖出可视区 |
| 流程图可读 | 流程图在窄 PRD 栏里按**原尺寸**渲染（横向滚动），不因栏窄被压扁；图注旁「⤢ 放大」可全屏看整体 |
| 主子表联动 | 单页数据层级多时用 `MasterDetail`：主表选行 → 子表按 `bind`/`bindTo` 过滤；子表可展开收起、显示条数、空明细有文案；点操作列按钮**不会**误触发选行 |
| 容器选型正确 | 长表单（>15 字段）不用对话框、无 dialogception、详情不用对话框承载、抽屉里没有多 tab 工作台（见 `08-container-choice.md`） |
| **动作可用性** | 非全状态可用的按钮都引用 `capability`，不写死 `disabled`；切换单据状态时按 `policy` 置灰 / 隐藏 / 点了才拒绝；置灰按钮点击有原因提示 |
| **状态转移有入口** | 状态机每条人工转移都有对应命令入口；系统自动流转标 `system: true` |
| **页面职责清晰** | 每页有 `contract`（一条任务 / 一个主体 / 一组 `owns`）；同一命令不被两个页面 owns；不同角色/提交边界的表单没有揉在一页 |

### 维度 4：结构一致性（Consistency）

| 检查项 | 通过标准 |
|---|---|
| 双向可定位 | PRD 板块 ↔ 原型页面 ↔ 需求条目可互相跳转 |
| 状态机一致 | 状态机的状态在原型里可见，转移有触发元素 |
| 标注闭环 | open 标注均已处理或显式标注待处理 |
| 无悬空引用 | 所有 `xxId` 都能找到对应实体 |
| ID 稳定 | 重生成原型后已有 `n-` id 不变 |

### 维度 5：可交付性（Deliverable）

| 检查项 | 通过标准 |
|---|---|
| 单文件可用 | 双击 HTML 即可打开，无需服务器、无需联网 |
| 可缩放 | 支持 25%~300% 缩放与平移；「适应宽度」后无横向滚动条 |
| 标注不漂移 | 缩放/平移后气泡仍贴合锚定节点（跨 100%~152% 偏差 < 0.8%） |
| 可编辑 | PRD 文本可在容器内编辑并自动保存 |
| 可导出 | 支持截图 PNG、关系图全图 PNG、Markdown 导出 |
| 布局可控 | 右栏 PRD 可折叠/展开（含恢复把手），splitter 拖到极值后**仍能拖回**（像素制 + 双侧钳制 + 双击复位） |
| 审核友好 | 可一键隐藏过程产物（审核开关） |
| 可交互演示 | 能当场演示主路径给评审 |
| 跳转可分享 | URL hash（`#/page-id`）即当前页，刷新/前进后退都停在原页；页面内「返回」不跳出容器 |

### 维度 6：机器可读性（AI-Consumable）

> 目标是"把这份产物丢给 AI 编码助手，它能直接开工"。判断标准是**信息是否在 JSON 里，而不是在自然语言里**。

| 检查项 | 通过标准 |
|---|---|
| 组件树可生成 | 每个页面有 `componentTree`，`type` 全在白名单内、`props` 语义明确 |
| 路由可生成 | 每页有 `route`；层级用 `parentId` 表达 |
| 页面图可生成 | `interactions` 里的 `navigate` 足以还原 `pageGraph`（关系图与 devspec 同源） |
| 行为可生成 | 每个可点元素有 `interactions`，`actions[]` 在白名单内，目标 id 可解析 |
| 状态可生成 | 每页 `states[]` 的 `vars` + `overrides` 能完整表达四态差异 |
| 数据可生成 | 有 `dataModel.entities[]`（含 `pk`/`fk`/枚举候选值）；派生指标在 `derived[]` 且有 `fallback` |
| 验收可生成 | `requirements[].acceptance[]` 逐条可写成测试用例 |
| 未确认项显式化 | `devNotes` 把 `open` / `assumed` / `inferred` / `draft` / `missing` 都列出来，AI 不会瞎猜 |
| 一键交付 | 「⬇ 开发交接」能导出 `devspec.json` + `AGENT.md` + 可复制的 AI 交接指令 |

---

## 2. 反例集（Anti-Patterns）

### 反例 1：需求不可验证

```jsonc
// ❌ 错误
{ "expected": "系统给用户友好的提示", "acceptance": ["提示友好"] }
// ✅ 正确
{ "expected": "系统在提交按钮下方显示红色文本『标题不能超过 50 字』",
  "acceptance": ["标题输入 51 字时，按钮下方出现红色文本且提交按钮禁用"] }
```

### 反例 2：一条需求塞多个响应

```jsonc
// ❌ 错误
{ "trigger": "点击提交", "expected": "系统保存数据并且刷新列表并且弹出提示并且发送邮件" }
// ✅ 正确：拆成 4 条需求，各自单一响应
```

### 反例 3：原型状态缺失

```jsonc
// ❌ 错误：只有默认态
"states": [{ "id": "s-default", "name": "默认态" }]
// ✅ 正确：四态齐全
"states": [
  { "id": "s-default", "name": "默认态" },
  { "id": "s-loading", "name": "加载态" },
  { "id": "s-empty",   "name": "空态" },
  { "id": "s-error",   "name": "异常态" }
]
```

### 反例 4：状态机有孤立状态

```jsonc
// ❌ 错误：'archived' 无入边无出边
"states": [{"id":"todo"},{"id":"done"},{"id":"archived"}],
"transitions": [{"from":"todo","to":"done"}]
// ✅ 正确：补转移，或删除该状态并在 openQuestions 说明
```

### 反例 5：交互目标指向不存在的节点

```jsonc
// ❌ 错误：componentTree 里没有 n-btn-xxx
{ "on": { "event": "click", "target": "n-btn-xxx" }, "actions": [] }
// ✅ 正确：target 必须是组件树里真实存在的 id
```

### 反例 6：标注只提出问题、不闭环

```jsonc
// ❌ 错误：AI 改了原型但没回写标注
{ "id": "an-1", "text": "按钮要置灰", "status": "open", "replies": [] }
// ✅ 正确
{ "id": "an-1", "text": "按钮要置灰", "status": "resolved",
  "replies": [{ "author": "AI", "text": "已为 n-btn-submit 增加 disabled 绑定，见 s-default.overrides" }] }
```

### 反例 7：使用未知组件类型

```jsonc
// ❌ 错误
{ "type": "SuperCustomGrid" }
// ✅ 正确：映射到白名单
{ "type": "Table", "props": { "columns": [...], "data": [...] } }
```

### 反例 8：示例数据敷衍

```jsonc
// ❌ 错误
"data": [{ "title": "测试1", "owner": "张三" }, { "title": "测试2" }]
// ✅ 正确
"data": [
  { "title": "完成登录页联调", "status": "进行中", "owner": "林可", "due": "2026-10-18" },
  { "title": "修复导出 CSV 中文乱码", "status": "阻塞", "owner": "陈默", "due": "2026-10-16" }
]
```

### 反例 9：切片清单未确认就写全文

```
❌ AI 一次性输出 12 个页面的完整 PRD + 原型
✅ AI 先给切片清单（每片：一个角色 / 一个目标 / 能独立验收）→ 用户确认 → 逐片产出（一轮一片）
❌ 需求丢进去直接开始画原型，澄清与卡点全跳过
✅ prd_flow.py start → submit → approve A → 切片 → approve B → 逐片
```

### 反例 10：涨跌配色用反

```jsonc
// ❌ 错误（中国市场）
{ "type": "Statistic", "props": { "value": "+3.2%", "trend": "up", "color": "green" } }
// ✅ 正确：涨红跌绿
{ "type": "Statistic", "props": { "value": "+3.2%", "trend": "up", "color": "red" } }
```

### 反例 11：为"腾空间"删信息

```jsonc
// ❌ 错误：中栏被左右栏挤窄了，于是把表格列从 6 列砍到 3 列、页面从 8 个合并成 4 个
// ✅ 正确：数据一字不改，让用户在容器里缩放/平移查看；页面层级用 pages[].parentId 表达
//    （评审看细节时 ⌘+滚轮放大，纵览时点「适应宽度」缩回，标注全程不跑位）
```

### 反例 12：把原型做成一堆孤岛

```jsonc
// ❌ 错误：有列表页也有详情页，但列表行点不动；或跳转写死每行一条 interaction（4 行写 4 条，改数据就失配）
{ "on": { "event": "click", "target": "n-table" },            // 整张表一个目标：点哪都跳同一处，也没法带行数据
  "actions": [{ "type": "navigate", "pageId": "page-detail" }] }

// ❌ 错误：带参跳转的目标页没有默认值，从导航树直接进这页就是空字段
"states": [{ "id": "s-default", "vars": {} }]

// ✅ 正确：行可点 + 一条通配 + 按行带参 + 目标页有默认值
// 列表页：props.rowClick = true，操作列用 columns[].actions 声明 key
{ "on": { "event": "click", "target": "n-table__row_*" },
  "actions": [{ "type": "navigate", "pageId": "page-goods-detail",
                "params": { "goodsName": "{{row.name}}" } }] }
// 详情页：{{goodsName}} 渲染，且 s-default.vars 里留一份默认值
```

### 反例 13：合成节点 id 猜错基节点

```jsonc
// ❌ 错误：弹窗底部按钮用的是 Modal 节点 id，不是 props.modalId
//    （showModal 引用 modalId="m-del"，但合成 id 是 n-modal-del__ok）
{ "on": { "event": "click", "target": "m-del__ok" } }        // 校验器报「基节点 m-del 不存在」

// ❌ 错误：__back 只能挂 Header、__ok/__cancel 只能挂 Modal、__row_/__act_ 只能挂 Table
{ "on": { "event": "click", "target": "n-btn-new__ok" } }     // 校验器报「__ok 只能挂在 Modal 上」

// ✅ 正确：先看节点 id 与类型，再写合成 id
{ "on": { "event": "click", "target": "n-modal-del__ok" } }
```

> 另外：`{{row.字段}}` 只有在「点表格行 / 行内按钮」时才有 row 上下文。写在普通按钮的 params 上，校验器会给 WARN，容器也求不出值（保留原文，页面上会看到 `{{row.xxx}}`）。

### 反例 14：流程图只有一个节点 / 全是孤岛

```jsonc
// ❌ 错误：只有节点没有边，画出来是一堆散点，看不出流程
{ "type": "flow", "nodes": [{"id":"a","label":"开始"},{"id":"b","label":"结束"}], "edges": [] }
// 校验器：WARN「节点 b 是孤岛」

// ❌ 错误：decision 的出边没有 label，分支语义丢失
{ "kind": "decision", "id": "d" }  +  { "from":"d", "to":"e" }   // 是"通过"还是"驳回"？
// ✅ 正确：判定节点每条出边都带 label，且图上有 start / end
{ "from": "d", "to": "e", "label": "通过" }
{ "from": "d", "to": "f", "label": "驳回" }

// ❌ 错误：图里写的是"进入商品页"，正文/原型里却是 page-goods-list，AI 对不上
// ✅ 正确：节点 sub 直接写真实路由 / 真实节点 id（/goods、n-table__act_*_delete）
```

### 反例 15：把数据模型只写在正文里

```jsonc
// ❌ 错误：正文写「核销率 = 已核销 / 已领取，已领取为 0 时显示 —」，
//    但 JSON 里没有任何实体/字段/派生定义 → AI 只能自己编类型、编表名、编接口
"prd": { "sections": [{ "heading": "业务规则", "body": "核销率 = 已核销 / 已领取…" }] }

// ✅ 正确：实体 + 字段（含类型/约束/主外键）+ 派生字段（含 fallback 与 reqId）
"dataModel": {
  "entities": [{ "id": "e-coupon", "name": "Coupon", "table": "coupons",
    "fields": [{ "name": "taken", "type": "integer", "required": true },
               { "name": "used",  "type": "integer", "required": true }] }],
  "derived": [{ "name": "核销率", "expr": "used / taken", "fallback": "taken = 0 时展示「—」",
                "usedBy": ["page-coupon-list"], "reqId": "REQ-MKT-001" }]
}

// ❌ 错误：一个实体标了两个 pk，或一个都没有
"fields": [{ "name": "a", "key": "pk" }, { "name": "b", "key": "pk" }]   // 校验器 ERROR
"fields": [{ "name": "a", "type": "string" }]                             // 校验器 WARN
// ❌ 错误：enum 没写候选值
{ "name": "status", "type": "enum" }
// ✅ 正确
{ "name": "status", "type": "enum", "constraint": "draft|pending|on_shelf|off_shelf" }
```

### 反例 16：关系图上一堆散点（页面之间没有边）

```
❌ 8 个页面全靠左侧导航切换，interactions 里一个 navigate 都没有
   → 「关系图」里 8 张卡片互不相连，设计和前端看不出页面关系
✅ 主路径用 navigate 串起来（列表行 → 详情、详情 → 编辑、保存 → 回列表），
   entryFrom 补上信息架构入口，关系图自动分层展开成有向图
```

### 反例 17：把右栏拖死了

```
❌ 把 PRD 面板的 splitter 拖到最右（PRD 最小），发现拖不回来 —— 只能刷新页面重来
   根因：中栏写 `flex:0 0 <ratio>%`（钳在 0.25~0.8）+ 右栏 `flex:1 1 auto`（基准=内容宽），
        两侧互相挤压后 splitter 的落点与鼠标位置脱钩
✅ 现在：右栏像素定宽 + 双侧最小宽钳制（≥300px、中栏 ≥320px），拖拽线性可逆；
   双击 splitter 一键复位；面板头「›」/ 原型栏「PRD ‹」可折叠，右侧竖向把手可展开；
   宽度与折叠态都写 localStorage，刷新后保持
```

### 反例 18：主子关系被平铺成两张表

```
❌ 页面里上下放两张 Table，点上面一行下面那张纹丝不动
   → 用户以为页面卡了；评审时被问「点这行下面会变吗」，答不上来
   → 校验器提示：`xxx` 下平铺了 2 张 Table，若存在主从关系建议用 MasterDetail
✅ 用 MasterDetail 包起来，声明 bind / bindTo：
   - 主表加 radio（单选圆点标出当前行）
   - 子表 data 写全量，容器按 bind 过滤
   - 子表标题栏显示「· 共 N 条」，可展开收起
   - 点主表行自动展开子表；无明细时显示 emptyText，不留空白
```

### 反例 19：用对话框承载长表单

```
❌ Modal 里塞了 20 个 FormItem —— 滚动、校验、键盘体验全崩；用户填到一半误点遮罩全丢
   → 校验器直接 ERROR：对话框 `n-xxx` 承载了 20 个表单字段（阈值 15）
✅ ≤15 字段且需边填边参照列表 → Drawer（关闭保留父页筛选/滚动）
   多 section / 分步向导 / 需长期停留 → 新页面（pages[] + navigate，可存草稿）
   只有「单字段快速改」才用 Modal
```

### 反例 20：对话框套对话框（dialogception）

```
❌ Modal 里再弹一个 Modal 做二级确认 —— 遮罩叠遮罩，用户分不清当前在哪一层
   → 校验器直接 ERROR：对话框 `n-outer` 里又嵌了对话框（n-inner）
✅ 第二层改用 Drawer（保留第一层上下文）或直接跳到新页面
   危险操作的确认留在第一层用 Popconfirm / 底部按钮即可
```

### 反例 21：bind / bindTo 写错，子表永远为空

```
❌ 主表字段是 no，子表关联字段是 taskNo，但只写了 bind: "no"（bindTo 默认同 bind）
   → 子表一条都匹配不到，页面看起来「正常」，只是明细永远是空的
   → 这类错误肉眼几乎发现不了（校验器也只能查字段是否存在，查不出同名不同义）
✅ 显式写 bindTo；容器运行期会自检并打警告：
   「主子表 n-md：主表 `no` 的值（ONSETE-20261016-0043）在子表字段 `taskId` 中匹配不到任何行」
```

---

### 反例 22：单据有多个状态，按钮却永远可点

```
❌ 状态机写了 草稿/待审批/已审批/已关闭，页面上的「提交审批」「编辑」「取消」全是普通按钮
   → 已审批的单子还能提交，已关闭的还能编辑
   → 用户不知道「现在能干什么」，开发也不知道该在哪一层拦
✅ 每个动作写一条 capability：actor + from + policy + reason，按钮引用 props.capability
   → 页面加 entity，顶部切「单据状态」，逐个状态验证按钮表现
   → 校验器：状态机的人工转移没有 capability 覆盖 → ERROR
```

### 反例 23：所有不可用都做成隐藏

```
❌ policy 一律 hidden：草稿有 5 个按钮，待审批剩 2 个，已关闭剩 1 个
   → 按钮忽隐忽现，用户每次都要重新找「刚才那个按钮去哪了」
✅ 默认 disabled（置灰 + 说明原因）；只有「暴露会误导」或「越权信息」才 hidden
```

### 反例 24：三个角色的表单与详情揉在一个页面

```
❌ 一页里：客服填写区 + 主管审批区 + 财务放款区，靠 mode 变量切换
   → 每个角色都要滚过另外两个人的区域；权限无法表达；提交边界说不清
✅ 按任务拆页（申请 / 审批 / 放款），靠 entity 状态机串联；
   每页写 contract（task / actor / entity / owns / submitBoundary / doneWhen）
   → 校验器：同一 capability 被两个页面 owns → ERROR
```

### 反例 25：只写成功路径的验收

```
❌ 需求验收：「点击通过后订单变为已审批」
   → 状态不符、权限不足、并发冲突全没验，开发只能自己拍脑袋
✅ 至少一条验收写非法路径：
   「非待审批状态下「通过」按钮置灰，点击提示当前状态」
   「订单已被他人处理时提示刷新，不做覆盖」
```

---

## 3. 自检命令

```bash
# 结构校验（悬空引用 / ID 唯一性 / 白名单 / 四态覆盖 / EARS 门禁
#          / 流程图节点与边 / dataModel 主外键 / 主子表结构 / 容器选型 / 机器可读性
#          / 命令策略一致性 / 状态转移覆盖 / 页面职责契约 / 多功能混页提示）
python3 scripts/validate_prd_json.py <产物.json>

# 也可以直接校验容器产物 HTML（会从 #iprd-data 抽数据）
python3 scripts/validate_prd_json.py XX-PRD.html
```

输出 `PASS` 才可交付；有 `ERROR` 必须修复；`WARN` 需人工判断。
`dataModel` 缺失、`devNotes` 有 `missing` 项时，交付给 AI 开发前应先补齐。

---

## 4. 交付话术模板

> 已按你的需求产出 **{N} 个模块 / {M} 个页面 / {K} 条 EARS 需求**。
> 容器已生成：`XX-PRD.html`（双击打开，无需联网）。
> - 左栏是**树形页面导航**（模块 → 页面 → 子页面），点节点切页；右栏是可编辑 PRD（可折叠，拖窄了双击分割条即复位）
> - 中栏是可交互原型，可缩放/平移：`⌘/Ctrl`+滚轮放大细节，点「适应宽度」缩回纵览
> - 顶部「**关系图**」是全局展开的页面关系图：分层布局 + 带跳转标签的连线，一眼看清页面关系；可拖拽、缩放、导出全图
> - PRD 正文里内嵌**流程图**（起止/判定/分支），和原型、需求一一对应
> - **数据层级多的页面用了主子表**：主表选中一行，子表立刻联动出该行的明细，子表还能展开收起
> - **按钮可用性跟着单据状态走**：顶部切「单据状态」，可当场看到哪些按钮置灰、哪些隐藏、哪些点了才拒绝；
>   置灰按钮点下去会说明原因（例如「仅「待初审」可审批，当前为「已放款」」）
> - **每个页面只干一件事**：不同角色的任务（填写 / 审批 / 到货登记）拆在各自页面，靠状态串联，不揉在一屏
> - **原型能走通主路径**：点表格行/按钮会真的跳页并带上该行数据，页面内「返回」不会跳出容器
> - 地址栏 `#/page-id` 就是当前页，可以直接把某个页面的链接发给同事；浏览器前进/后退可用
> - 直接点原型任意位置可加标注气泡；点「⇪ 标注指令」一键导出结构化修改指令给我
> - 顶部「审核模式」可隐藏过程产物，方便发给产研评审
> - 「导出」支持当前页截图 PNG、关系图全图 PNG、整份 Markdown
> - 「**⬇ 开发交接**」一键导出 `devspec.json`（机器可读的唯一真源）+ `AGENT.md`（实现约定）
>   + 一段可直接粘给 AI 编码助手的交接指令 —— 交给研发或让 AI 开始写代码时用这个
>
> 本轮我推断的假设有 {X} 条，列在"待澄清问题"里，你确认或让我按默认值处理。
