# PRD 结构规范

> PRD 的**结构必须与原型、标注、状态机一一对应**，这是"研发拿去能直接转技术文档"的前提。
> 四层结构：① PRD 文档层 → ② 原型层（组件树+交互+页面状态）→ ③ 标注层 → ④ 状态机层。

---

## 1. 四层结构的对应关系

```
PRD 板块 (boardPlan)
  └── 页面 (page)
        ├── PRD 块 (page.prd)          ← 文档层：目标/交互/规则/状态/验收
        ├── 原型 (page.componentTree)  ← 原型层：组件树
        │     ├── 交互 (page.interactions)   ← 交互层：事件 → 动作
        │     └── 页面状态 (page.states)     ← 状态层：状态变量 + 覆写
        ├── 标注 (page.annotations)     ← 标注层：评审意见 + 处理结果
        └── 需求 (requirements[pageId]) ← 需求层：EARS 条目
              └── 状态机 (stateMachines) ← 状态机层：实体生命周期
```

**对应铁律：**
1. `page.prd.sections` 里的每条"交互说明"，在 `page.interactions` 里必须有对应交互。
2. `page.prd.reqIds` 必须能在 `requirements` 里找到，且这些需求的 `pageId` 指向本页。
3. `page.states` 的每个状态，在 PRD 的"页面状态"小节里必须有说明。
4. 状态机里的每个状态，在原型里必须**可见**（Tag/Badge/状态条）。

---

## 2. 文档整体结构（最终交付的 PRD 大纲）

```markdown
# {产品名} 产品需求文档（PRD）

## 0. 文档信息
版本 / 日期 / 作者 / 变更记录 / 关联文档（原型链接、澄清文档）

## 1. 产品定位
（引用 01-clarification 的产品定位文档）

## 2. 范围说明
### 2.1 本期范围（In Scope）
### 2.2 非目标（Out of Scope）
### 2.3 依赖与约束

## 3. 用户与角色
角色表 + 权限矩阵

## 4. 用户流
每条流的主路径 + 分支 + 异常

## 5. 模块与页面总览
模块清单 + 页面清单 + **页面关系图**（容器顶部「关系图」按钮可查看全局展开的页面关系图：
分层布局 + 带标签的有向连线，一眼看清父子/跳转；对应 `devspec.json` 的 `pageGraph`）

## 6. 关键组件与状态定义
组件清单（引用 components[]）+ 业务状态色板

## 6.5 数据模型（dataModel）
实体清单 + 字段表（类型/约束/说明）+ 关系 + 索引 + 派生字段（口径与除零兜底）
→ 对应顶层 `dataModel`，容器在 PRD 里渲染成「数据模型」小节，并原样进 `devspec.json`

## 7. 状态机
每个实体的状态图（states + transitions 表）

## 8. 需求条目（EARS）
按模块分组，每条含 角色/触发/规则/状态机/预期/验收

## 9. 页面详述（按板块逐个）
### 9.x {页面名}（路由）
- 页面目标
- 页面结构（组件树摘要；**主子表要写出主表/子表与关联字段**）
- **主流程图**（`prd.sections[].type = "flow"`，容器渲染成内嵌 SVG 流程图）
- 交互说明（对应 interactions）
- **容器选型说明**（本页为什么用对话框 / 抽屉 / 新页面 / 主子表；准则见 `08-container-choice.md`）
- **跳转关系**（去往哪些页面 / 从哪些页面来；带参跳转写清带什么参、目标页怎么用）
- 页面状态（对应 states）
- 业务规则
- 数据模型（本页涉及的实体）
- 关联需求（reqIds）
- 原型（容器内可交互）
- 标注与处理记录（annotations）

## 10. 待澄清问题
## 11. 术语表
## 12. 附录：验收清单汇总
```

---

## 3. 原型层结构（组件树 + 交互 + 页面状态）

见 `references/04-container-schema.md` §6。要点：

| 子结构 | 字段 | 说明 |
|---|---|---|
| 组件树 | `componentTree` | 递归 Node，`id` 稳定唯一，`type` 走白名单 |
| 交互 | `interactions` | `on`(事件+目标) → `actions[]`(动作序列) |
| 页面状态 | `states` | `vars` + `overrides` + `visible/hidden` |

**跳转层（让原型能走通主路径）**：`navigate` 的 `pageId` / `stateId` / `params`，配合合成节点 id（`__row_<i>` / `__act_<i>_<key>` / `__back` / `__ok` / `__cancel`）与通配目标（`n-table__row_*`）。详见 `04-container-schema.md` §0.2。

**主子表层（单页数据层级多时用）**：`MasterDetail` 的 `bind` / `bindTo` 把主表与子表关联起来，
点主表行 → 子表联动。**一条主记录挂多条明细时用它，不要平铺两张表。** 详见 `04-container-schema.md` §6.7。

**容器选型层（对话框 / 抽屉 / 新页面）**：详情主从首选抽屉、长表单禁对话框、禁 dialogception。
详见 `08-container-choice.md`。

**原型层自检：**
- [ ] 组件树里每个可点击元素，都有对应交互或明确标注"无交互"
- [ ] 页面至少覆盖 默认/加载/空/异常 四态
- [ ] 状态变量命名与 `when` 表达式一致
- [ ] 所有 `on.target` 和 `overrides.target` 指向存在的 `n-` id 或合法合成 id
- [ ] 主路径上的页面**互相可达**（不是孤岛）：列表能进详情、详情能返回
- [ ] 带参跳转的目标页在 `states[].vars` 里有默认值，可独立渲染
- [ ] 写了 `{{row.字段}}` 的目标确实在表格行/行内按钮上
- [ ] **主从结构**（一条主记录挂多条明细）用了 `MasterDetail`，主表没有设 `rowClick`
- [ ] **容器选型**合规：`Modal` 字段 ≤ 15、无嵌套 `Modal`、详情不用 `Modal`、抽屉里没有多 tab 工作台

---

## 4. 标注层结构

见 `04-container-schema.md` §6.4。要点：

| 字段 | 说明 |
|---|---|
| `anchor.nodeId` | 锚定组件（推荐），原型重排后仍跟随 |
| `anchor.x/y` | 归一化坐标，兜底定位 |
| `category` | interaction / ui / data / copy / bug / question |
| `status` | open → resolved / rejected |
| `replies[]` | 处理记录，AI 处理后追加说明 |

> **锚定在缩放/平移下必须稳定**：`x/y` 是相对**画布盒**的 0~1 比值，气泡落位也用画布盒布局尺寸换算，因此与原型缩放倍率无关。评审时用户可以 `⌘/Ctrl`+滚轮放大看细节、再「适应宽度」缩回纵览，气泡始终贴在锚定节点上（回归测试：跨 100%~152% 偏差 < 0.8%）。实现约束见 `04-container-schema.md` §0.1。

**标注 → 修改 → 回写 的闭环：**
1. 用户在原型上打标注（`status: open`）。
2. 用户点容器顶部「⇪ 标注指令」，一键生成并复制一段结构化 prompt（见 §4.1）。
3. AI 读取该指令，逐条判断影响面（组件树 / 交互 / 状态 / 需求）。
4. AI 修改 JSON，把标注置 `resolved`，在 `replies` 追加"改了什么"。
5. 若标注影响 EARS 需求，同步更新 `requirements` 并在 PRD 里体现。
6. 容器刷新后标注显示为"已处理"，用户可复核。

### 4.1 标注指令（Annotation Brief）契约

容器导出的指令是一段**自包含、可直接消费**的 prompt，固定包含三节。AI 收到后应按其「输出要求」执行。

| 小节 | 内容 | 对 AI 的作用 |
|---|---|---|
| `## 上下文` | 产品名与版本、数据契约位置、本次范围（当前页 / 全部页面）、标注总数与待处理数 | 确定改动边界，避免越界修改 |
| `## 标注清单` | 按页面分组，每条含：序号、标注 `id`、`category`、`status`、**锚定节点 id + 类型 + 父节点**、**当前属性摘要**、渲染条件 `when`、用户意见原文、已有回复 | 免去 AI 自行检索组件树的成本，直接定位到要改的节点 |
| `## 输出要求` | 8 条硬性约束（见下） | 保证输出可被容器直接吃回去 |

**「输出要求」的 8 条约束（AI 必须遵守）：**
1. 逐条给出处理结论（采纳 / 部分采纳 / 需澄清），每条一句话说明理由。
2. 给出**最小改动**的 JSON 片段，写明改动路径；`n-` / `ix-` / `s-` / `an-` 开头的 id 必须保持不变。
3. 已处理的标注：`status` → `"resolved"`，`replies` 追加 `{ "author": "AI", "text": "…" }`。
4. 若影响 `requirements`，同步更新对应 REQ 的 `rule` / `expected` / `acceptance`。
5. 意图不明确时**不要猜**：保留 `status: "open"` 并提一个具体问题。
6. 新增或修改组件时，`type` 必须在 `references/05-component-states.md` 白名单内。
7. 改完运行 `python3 scripts/validate_prd_json.py <产物.json>`，0 error 再交付。
8. 只输出改动部分，不要重贴整个 JSON。

> 若用户没走「标注指令」而是直接在对话里说"改一下原型"，AI 也应自行按上述 8 条执行，不要等待指令。

---

## 5. 状态机层结构

见 `04-container-schema.md` §8。PRD 里状态机必须渲染成**表格 + 图**两种形式：

```markdown
### 状态机：任务状态机（Task）

| 状态 | 名称 | 类型 | 说明 |
|---|---|---|---|
| todo | 待办 | normal | 新建后默认 |
| doing | 进行中 | normal | 已指派并开始 |
| blocked | 阻塞 | warning | 被外部依赖卡住 |
| done | 已完成 | success | 终态 |

| # | 从 | 到 | 触发 | 角色 | 守卫条件 | 副作用 |
|---|---|---|---|---|---|---|
| t-1 | todo | doing | 负责人点击开始 | 项目负责人 | 有负责人 | 记录开始时间 |
| t-2 | doing | blocked | 标记阻塞 | 项目负责人 | — | — |
| t-3 | blocked | doing | 解除阻塞 | 项目负责人 | — | — |
| t-4 | doing | done | 标记完成 | 项目负责人 | 所有子任务完成 | 通知关注者 |
```

**状态机自检：**
- [ ] 有唯一 `initial` 状态
- [ ] 无孤立状态（除终态外每个状态都有入边和出边）
- [ ] 每条转移都有明确的 `trigger` 和 `role`
- [ ] 非法转移在 `unwanted` 类需求里有对应的拒绝行为

---

## 5.5 流程图小节（`prd.sections[].type = "flow"`）

PRD 正文里**至少要有一条主流程图**，用来表达"从哪来 → 经过什么判断 → 到哪去"。
容器会用与「关系图」同一套分层布局引擎（Kahn 拓扑分层 + 重心法排序 + 回边虚线）把它画成内嵌 SVG，
导出 PNG / Markdown 都不丢结构（Markdown 降级为箭头链路）。

**渲染约定（写 JSON 时不用管，但决定了图该怎么画）：**
- 流程图在 PRD 栏里**按原尺寸渲染**，比栏宽就横向滚动 —— 不会被压扁到看不清；
- 图注右侧有「⤢ 放大」，点开是全屏浮层（点遮罩 / Esc 可关），用于整体讲流程；
- 所以节点文案可以放心写长，不需要为了塞进窄栏而缩写。

```json
{
  "id": "sec-flow",
  "heading": "创建任务主流程",
  "type": "flow",
  "caption": "任务列表：新建 → 填写 → 提交 → 成功提示",
  "dir": "LR",
  "body": "可选：图前的一段说明（支持 Markdown）",
  "nodes": [
    { "id": "t1", "label": "进入任务列表", "sub": "/tasks", "kind": "start" },
    { "id": "t2", "label": "点击「新建任务」", "sub": "打开右侧抽屉" },
    { "id": "t3", "label": "标题是否合法？", "kind": "decision" },
    { "id": "t4", "label": "提交按钮置灰", "sub": "标题为空 / 超 50 字", "kind": "warn" },
    { "id": "t5", "label": "提交成功", "sub": "抽屉关闭 + 顶部提示" },
    { "id": "t6", "label": "弹出成功弹窗", "sub": "m-ok", "kind": "end" }
  ],
  "edges": [
    { "from": "t1", "to": "t2" },
    { "from": "t2", "to": "t3" },
    { "from": "t3", "to": "t4", "label": "否" },
    { "from": "t3", "to": "t5", "label": "是" },
    { "from": "t4", "to": "t3", "label": "修正标题" },
    { "from": "t5", "to": "t6" }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `heading` | ✅ | 小节标题，渲染为 `h3` |
| `type` | ✅ | 固定 `"flow"`；不写或写 `"text"` 则按普通正文处理 |
| `nodes[].id` | ✅ | 图内唯一；与 `edges` 的 from/to 对应 |
| `nodes[].label` | ✅ | 节点主文案（一行） |
| `nodes[].sub` | — | 副文案（路由、节点 id、状态名…），换行显示在下方 |
| `nodes[].kind` | — | `start` / `end` / `decision` / `warn` / `process`，决定描边配色 |
| `edges[].label` | — | 分支条件（"是/否/超时"），画在连线中点 |
| `caption` | 建议 | 图注；缺了校验器会 WARN（AI 拿到图也需要知道这图画的是什么） |
| `dir` | — | `"LR"`（默认，从左到右）/ `"TB"`（自上而下） |
| `body` | — | 图前说明文字，支持 Markdown |

**流程图自检：**
- [ ] 有且仅有 1 个 `kind:"start"` 与 ≥1 个 `kind:"end"`
- [ ] 每个 `decision` 节点的出边 ≥ 2 条，且每条都有 `label`
- [ ] 没有孤岛节点（每个节点至少被一条边引用）——校验器会 WARN
- [ ] 图里出现的路由 / 节点 id 与 `componentTree` / `interactions` 里的真实值一致
- [ ] 异常分支（拒绝/失败/超时）在图上可见，而不是只写在正文里

---

## 5.6 数据模型（顶层 `dataModel`）

PRD 只写"页面要什么"不够，研发还需要"数据长什么样"。`dataModel` 让 AI 能直接生成 TS 类型、mock 数据与接口契约。

```json
{
  "dataModel": {
    "entities": [{
      "id": "e-task",
      "name": "Task",
      "table": "task",
      "description": "一条可指派、可流转的最小工作单元",
      "pageIds": ["page-task-list", "page-task-detail"],
      "fields": [
        { "name": "id", "type": "string", "required": true, "key": "pk", "note": "ULID" },
        { "name": "title", "type": "string", "required": true, "constraint": "≤ 50 字", "note": "任务标题" },
        { "name": "status", "type": "enum", "required": true,
          "constraint": "todo|doing|blocked|done", "note": "见 sm-task 状态机" },
        { "name": "ownerId", "type": "string", "required": true, "key": "fk", "note": "→ user.id" },
        { "name": "dueDate", "type": "date", "required": false, "note": "早于今天且未完成即逾期" }
      ],
      "relations": [{ "type": "belongs_to", "target": "e-user", "via": "ownerId", "note": "负责人" }],
      "indexes": ["status", "ownerId", "dueDate"]
    }],
    "derived": [{
      "name": "逾期任务数",
      "expr": "count(task where dueDate < today and status != done)",
      "fallback": "无逾期时展示 0",
      "usedBy": ["page-task-list"],
      "reqId": "REQ-TASK-002"
    }]
  }
}
```

**硬约定：**
1. 每个实体**必须恰好一个** `key: "pk"` 字段（校验器 ERROR）；外键标 `key: "fk"`。
2. `type` 用实现无关的写法：`string` / `integer` / `number` / `boolean` / `date` / `datetime` / `enum` / `json` / `array<T>`。
3. 枚举必须把候选值写进 `constraint`（`a|b|c`），否则 AI 只能猜。
4. `relations[].target` 必须是本文件里存在的实体 id；关系方向按"当前实体 → 目标"写。
5. **派生字段（核销率、逾期数…）一律进 `derived`，不要只写在正文里**；必须写 `fallback`（除零 / 空值怎么显示），并挂 `reqId` 指回需求。
6. `pageIds` 声明该实体在哪些页面出现，容器据此在 PRD 里按页展示。

---

## 6. PRD 写作质量门禁

- [ ] 每条规则可验证，无主观词
- [ ] 每个页面有明确目标、入口、出口
- [ ] 每个交互都有触发条件、动作序列、结果
- [ ] 每个状态有进入/退出条件
- [ ] 异常分支覆盖率 ≥ 每模块 1 条
- [ ] 需求条目全部 `status: confirmed`
- [ ] 原型可交互且与 PRD 描述一致（容器内逐页走查）
- [ ] 所有 open 标注已处理或明确标注"待处理"

---

## 7. 导出约定

容器支持**四种**导出（顶栏按钮，从左到右）：

| 按钮 | 产物 | 用途 |
|---|---|---|
| 关系图 → 导出全图 | `{产品}-页面关系图.png` | 全局页面关系图（分层布局 + 跳转标签），给设计/前端讲架构 |
| 截图 | `{产品}-{页面}.png` | 当前页原型 |
| Markdown | `{产品}-PRD-v{版本}.md` | 完整 PRD 文档（流程图降级为箭头链路），供归档与二次编辑 |
| ⬇ 开发交接 | `{产品}.devspec.json` + `AGENT.md` | **机器可读的开发交接包**（见下） |

### 7.1 开发交接包（AI 可消费）

「⬇ 开发交接」抽屉里同时给出：

1. **`{产品}.devspec.json`** —— 唯一真源。结构：
   ```
   { $schema, generatedAt, meta, product, users, userFlows, modules,
     dataModel, components, stateMachines, requirements, boardPlan,
     glossary, openQuestions,
     pageGraph: { nodes[], edges[{from,to,labels,kind}] },
     devNotes: [{level, text}],              ← 待确认项（open/assumption/inferred/draft/missing）
     pages: [{ id, name, route, moduleId, parentId, goal, layout, defaultStateId,
               entryFrom, exitTo, componentTree, states, interactions, prd, annotations }] }
   ```
2. **`AGENT.md`** —— 阅读指引 + 实现约定：合成节点 id 表、action 字典、信息架构、页面关系图、
   数据模型、**逐页实现清单**、待确认项、验收清单。
3. **「AI 交接指令」** —— 一段可直接粘给 AI 编码助手（Claude Code / Cursor 等）的 prompt，
   写明了真源位置、7 条必须遵守的约定、以及交付形式。

**什么时候必须导出：** 当用户说"交给研发/交给 AI 开发/开始写代码/生成技术方案"时，
AI 应先确认 `devspec.json` 里 `devNotes` 为空或已注明，再交付。

---
