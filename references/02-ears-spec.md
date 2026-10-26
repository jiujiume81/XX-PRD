# EARS 语法规范与需求条目结构

> EARS（Easy Approach to Requirements Syntax）用**固定句式**消除需求歧义。
> 本文件给出 5 种句式的模板、中文表达、以及条目结构中每个字段的逐字段说明与填写标准。

---

## 1. 五种 EARS 句式

| pattern | 名称 | 英文模板 | 中文句式 | 何时用 |
|---|---|---|---|---|
| `ubiquitous` | 普遍性 | The \<system\> shall \<response\>. | \<系统\> 应当 \<响应\>。 | 永远成立的约束（无触发条件） |
| `event-driven` | 事件驱动 | **When** \<trigger\>, the \<system\> shall \<response\>. | **当** \<触发\> **时**，\<系统\> 应当 \<响应\>。 | 由用户动作/外部事件触发 |
| `state-driven` | 状态驱动 | **While** \<state\>, the \<system\> shall \<response\>. | **当** \<处于某状态\> **时**，\<系统\> 应当 \<响应\>。 | 只要处于某状态就持续成立 |
| `option` | 可选特性 | **Where** \<feature is included\>, the \<system\> shall \<response\>. | **若** \<包含某特性\>，\<系统\> 应当 \<响应\>。 | 条件性/配置性能力 |
| `unwanted` | 异常处理 | **If** \<condition\>, **then** the \<system\> shall \<response\>. | **如果** \<异常条件\>，**那么** \<系统\> 应当 \<响应\>。 | 错误、故障、非法输入 |

**写法铁律：**
1. 一条需求只描述**一个**响应，禁止用"并且/以及"塞两个行为 → 拆成两条。
2. 禁止出现**主观词**：友好、快速、合理、尽量、美观、尽可能。
3. 禁止出现**实现细节**：数据库表名、接口路径、框架名（除非是硬约束）。
4. 必须**可验证**：读完能写出一条测试用例。
5. 响应必须写"系统做什么"，不是"用户做什么"。

---

## 2. 条目结构：逐字段说明

每条需求在 JSON 里是一个对象，字段与 EARS 句式一一映射：

```jsonc
{
  "id": "REQ-TASK-001",
  "moduleId": "m-task",
  "pageId": "page-task-list",
  "pattern": "event-driven",
  "title": "创建任务",
  "role": "u-owner",
  "trigger": "在任务列表页点击『新建任务』",
  "rule": "任务标题必填且 ≤ 50 字；负责人可空",
  "stateMachine": "sm-task",
  "expected": "系统在列表中新增一条状态为『待办』的任务，并提示创建成功",
  "acceptance": ["标题为空时提交按钮禁用", "创建成功后列表首行出现该任务"],
  "priority": "P0",
  "source": "user",
  "status": "confirmed"
}
```

### 2.1 `id` — 需求编号
- 格式 `REQ-<模块缩写>-<三位序号>`，如 `REQ-TASK-001`。
- 全局唯一，**永不复用**（删除后序号也不回收）。
- 编号一旦分配就锁定，评审、测试、代码注释都引用它。

### 2.2 `moduleId` / `pageId` — 归属
- `moduleId`：必填，指向 `modules[].id`。
- `pageId`：可空。纯后端/跨页规则可留空。
- 作用：让 PRD 板块与原型页面能双向定位到需求。

### 2.3 `pattern` — EARS 句式类型
- 取值见 §1 表格，**必填**。
- 决定句式模板：`event-driven` 必须有 `trigger`；`ubiquitous` 的 `trigger` 必须为空；`unwanted` 必须在 `acceptance` 里有对应的异常断言。

### 2.4 `title` — 需求标题
- 6–16 字，动词开头，如"创建任务""超时自动登出"。
- 不是句子，不要带句号。用于列表/目录展示。

### 2.5 `role` — 角色
- 引用 `users[].id`（如 `u-owner`）；系统行为写 `system`。
- **必须明确**，禁止写"用户"这种泛指 —— 不同角色规则可能不同。

### 2.6 `trigger` — 触发
- 写清 **谁 + 在哪个页面 + 做什么动作 + 什么条件**。
- 好：`在任务列表页点击『新建任务』按钮`
- 差：`用户操作时`（太泛）、`点击后`（缺主体和条件）
- `ubiquitous` 类留空字符串。

### 2.7 `rule` — 规则
- 约束、校验、计算、权限、默认值。多条用 `；` 分隔。
- 好：`标题必填且 ≤ 50 字；仅项目成员可创建；默认负责人为当前用户`
- 差：`标题要合理`（不可验证）
- 若该需求涉及状态流转，这里写流转的守卫条件（guard）。

### 2.8 `stateMachine` — 状态机
- 引用 `stateMachines[].id`；无关联则留空。
- 一旦填写，`acceptance` 里必须覆盖：**合法流转可执行 + 非法流转被拒绝**。

### 2.9 `expected` — 预期
- 系统在触发后的**可观察结果**，用"系统…"开头。
- 描述**结果状态**，不是实现过程。
- 好：`系统在列表中新增一条状态为『待办』的任务，并提示创建成功`
- 差：`调用 createTask 接口`（实现细节）

### 2.10 `acceptance` — 验收条件
- 数组，每条是**可执行、可判定真假**的断言（Given/When/Then 可省略但语义要完整）。
- 至少 2 条，含 1 条正常路径 + 1 条边界/异常路径。
- 好：`标题输入 51 字时，输入框下方出现红色提示且提交按钮禁用`
- 差：`功能正常`（不可判定）
- 建议写法：`当 {前置} 时，{动作}，则 {结果}`。

### 2.11 `priority`
- `P0`（必须有，否则不可发布）/ `P1`（重要）/ `P2`（可延后）。

### 2.12 `source` — 来源
- `user`（用户明确说的）/ `demo`（从 Demo 代码逆向）/ `inferred`（AI 推断）。
- **`inferred` 的条目必须在 `openQuestions` 里有对应确认项。**

### 2.13 `status`
- `draft`（待确认）/ `confirmed`（用户已确认）。只有 `confirmed` 才进最终 PRD。

### 2.14 本文件**不管**的三件事

本文件管的是「**一条**需求怎么写才不歧义」。下面三件事是「**一组**信息齐不齐」，属集合粒度，
写在 `13-requirements-accuracy.md`：

- 源文档点名的业务字段有没有落到某页某区块（R1 字段登记 / `fieldRegistry[]`）；
- 一对多语义（`分发至/各负责人/多个`）要不要建主子结构（R2）；
- 每个有命令的角色有没有待办入口、执行与验证是不是两个角色（R3 / R4）。

**分开的理由**：R2 / R4 的落点（`dataModel.relations` / `capabilities[].stage`）在阶段② 还不存在，
写在这里模型会读到但用不上；且混进来会让本文件从 213 行涨到 500+，两种粒度互相稀释。

---

## 3. 完整示例（覆盖 5 种句式）

```jsonc
[
  {
    "id": "REQ-TASK-001", "moduleId": "m-task", "pageId": "page-task-list",
    "pattern": "event-driven", "title": "创建任务", "role": "u-owner",
    "trigger": "在任务列表页点击『新建任务』按钮并提交表单",
    "rule": "标题必填且 ≤ 50 字；仅项目成员可创建；默认负责人为当前用户",
    "stateMachine": "sm-task",
    "expected": "系统新增一条状态为『待办』的任务并置于列表首行，提示『创建成功』",
    "acceptance": [
      "标题为空时，提交按钮置灰不可点击",
      "标题输入 51 字时，输入框下方出现红色提示且无法提交",
      "提交成功后抽屉关闭，列表首行出现该任务"
    ],
    "priority": "P0", "source": "user", "status": "confirmed"
  },
  {
    "id": "REQ-TASK-002", "moduleId": "m-task", "pageId": "page-task-list",
    "pattern": "state-driven", "title": "阻塞任务高亮", "role": "u-owner",
    "trigger": "",
    "rule": "当任务状态为『阻塞』时，列表行左侧显示红色竖条",
    "stateMachine": "sm-task",
    "expected": "系统对状态为『阻塞』的任务行持续显示红色标识",
    "acceptance": [
      "任务状态变为『阻塞』后，该行立即出现红色竖条",
      "任务状态离开『阻塞』后，红色竖条消失"
    ],
    "priority": "P1", "source": "inferred", "status": "draft"
  },
  {
    "id": "REQ-TASK-003", "moduleId": "m-task", "pageId": "page-task-detail",
    "pattern": "unwanted", "title": "并发编辑冲突", "role": "system",
    "trigger": "",
    "rule": "若同一任务被两人同时编辑并先后保存",
    "stateMachine": "",
    "expected": "系统拒绝后提交者的保存，并提示『该任务已被他人修改，请刷新后重试』",
    "acceptance": [
      "后提交者收到冲突提示且内容不被覆盖",
      "提示中提供『刷新』入口"
    ],
    "priority": "P1", "source": "inferred", "status": "draft"
  },
  {
    "id": "REQ-TASK-004", "moduleId": "m-task", "pageId": "",
    "pattern": "ubiquitous", "title": "操作留痕", "role": "system",
    "trigger": "",
    "rule": "所有任务状态变更均记录操作人、时间与前后状态",
    "stateMachine": "sm-task",
    "expected": "系统为每次状态变更生成一条不可删除的操作记录",
    "acceptance": [
      "任意一次状态变更后，操作记录新增一条且包含操作人/时间/前状态/后状态",
      "操作记录无法通过任何界面入口删除"
    ],
    "priority": "P0", "source": "user", "status": "confirmed"
  },
  {
    "id": "REQ-TASK-005", "moduleId": "m-task", "pageId": "page-task-list",
    "pattern": "option", "title": "批量导出", "role": "u-owner",
    "trigger": "",
    "rule": "若团队开通『数据导出』能力，列表页显示『导出』按钮",
    "stateMachine": "",
    "expected": "系统在列表工具栏展示『导出』按钮，点击后下载当前筛选结果的 CSV",
    "acceptance": [
      "未开通时列表页不出现『导出』按钮",
      "开通后点击导出，下载文件包含当前筛选条件对应的全部行"
    ],
    "priority": "P2", "source": "inferred", "status": "draft"
  }
]
```

---

## 4. EARS 反例与修正

| 反例 | 问题 | 修正 |
|---|---|---|
| 系统应当有良好的用户体验 | 不可验证、主观 | 系统应在用户提交表单后 200ms 内展示成功提示 |
| 用户点击按钮，系统弹窗并且保存数据 | 一条需求两个响应 | 拆成两条：`REQ-A 点击按钮弹出确认框`、`REQ-B 确认后保存数据` |
| 系统调用 `/api/task/create` 创建任务 | 实现细节 | 系统应新增一条任务并置于列表首行 |
| 系统应当快速加载列表 | 无量化 | 系统应在首屏 1s 内渲染前 20 条任务 |
| 如果没有权限就提示 | 缺主体/结果 | 如果当前角色无创建权限，那么系统应隐藏『新建任务』按钮 |
| 用户可以修改任务 | 太泛、无触发无结果 | 当项目负责人点击任务行的『编辑』时，系统应打开预填当前值的编辑抽屉 |

---

## 5. 质量门禁（EARS 自检清单）

产出需求后逐条自检，任一不通过则重写：

- [ ] `pattern` 与 `trigger` 的填写一致（`ubiquitous`/`state-driven`/`option` 的 `trigger` 为空）
- [ ] 每条需求只描述一个响应
- [ ] 无主观词（友好/快速/合理/尽量/美观/尽可能/优秀）
- [ ] 无实现细节（表名/接口路径/框架名）
- [ ] `expected` 以"系统"开头且是结果态
- [ ] `acceptance` ≥ 2 条，且含至少 1 条边界或异常断言
- [ ] 涉及 `stateMachine` 的，验收里覆盖"合法流转"与"非法流转拒绝"
- [ ] `source: "inferred"` 的条目在 `openQuestions` 中有对应确认项
- [ ] 需求之间无冲突（同一触发 + 同一条件不得有矛盾结果）
