# Demo 逆向规则（从 Vibe-Coding Demo 抽取需求）

> 场景：产品经理用 AI 写了个可运行的 Demo，评审后需要把它"展开"成 PRD + 原型。
> Demo 代码是**压缩的**，协作需要**展开的**信息。本文件给出三条抽取规则 + 一条对齐规则。

---

## 1. 核心映射：路由 → 模块、分支 → 规则、状态变化 → 状态机

| 逆向目标 | 抽取来源 | 具体做法 |
|---|---|---|
| **模块清单** | 路由表 / 页面目录 | 一级路由 ≈ 模块；路由分组 ≈ 模块分组 |
| **页面清单** | 路由表 | 每个路由 ≈ 一个页面；嵌套路由 ≈ 页面内 Tab/子视图 |
| **业务规则** | 条件分支 | 每个 `if/else`、`switch`、守卫（guard）≈ 一条规则 |
| **状态机** | 状态变量变化 | 状态变量的赋值点 ≈ 状态转移 |
| **交互** | 事件处理器 | `onClick/onChange/onSubmit` ≈ 一条 interaction |
| **组件树** | 组件嵌套 | JSX/template 嵌套结构 ≈ componentTree |
| **页面状态** | 条件渲染 | 由 loading/error/empty 变量控制的渲染分支 ≈ 页面状态 |
| **数据模型** | 类型定义 / 表结构 | interface/type/schema ≈ 实体与字段 |
| **权限** | 鉴权判断 | 角色判断分支 ≈ 权限规则 |

---

## 2. 规则一：从路由抽模块

**步骤：**
1. 列出所有路由定义（React Router / Vue Router / Next.js pages / 小程序 app.json）。
2. 按**路径前缀**聚合：`/tasks/*` → 模块「任务管理」。
3. 识别**布局路由**（Layout 包裹的），它不产生模块，只产生全局壳。
4. 识别**参数路由**（`/tasks/:id`），它是同一模块下的详情页，不是新模块。
5. 输出模块清单时，为每个模块标注 `priority`：有独立数据模型的通常 P0。

**示例：**
```
/                    → 概览（模块：概览，P1）
/tasks               → 任务列表（模块：任务管理，P0）
/tasks/:id           → 任务详情（模块：任务管理，P0）
/settings/profile    → 个人设置（模块：设置，P2）
```
→ 抽出 3 个模块：概览、任务管理、设置。

**注意：** 路由 ≠ 模块。若两个路由共享同一份数据模型和同一组操作，它们属于同一模块（列表 + 详情）。

---

## 3. 规则二：从分支抽规则

**步骤：**
1. 扫描所有条件判断：`if` / `else if` / `switch` / `&&` 短路 / 三元 / 守卫函数。
2. 区分三类分支：
   - **校验分支** → 规则（必填、长度、格式、额度）
   - **权限分支** → 权限规则
   - **业务分支** → 业务规则（状态相关、计算相关）
3. 每条分支翻译成一条 EARS 条目：
   - 校验失败分支 → `unwanted` 句式（"如果…那么…"）
   - 正常分支 → `event-driven` 句式
   - 权限分支 → `unwanted` 或 `option`
4. 把"魔法数字"显式化为规则值（`if (len > 50)` → "标题 ≤ 50 字"）。

**示例：**
```js
function canSubmit(form) {
  if (!form.title) return false;              // 规则：标题必填
  if (form.title.length > 50) return false;   // 规则：标题 ≤ 50 字
  if (user.role !== 'member') return false;   // 规则：仅项目成员可创建
  return true;
}
```
→ 抽成 `REQ-*-001` 的 `rule` 字段 + 3 条 `acceptance`。

**注意：** Demo 里常有**未处理的边界**（没有 else 的分支）。这些是**缺口**，要写成 `openQuestions`，不要默认"就是不做"。

---

## 4. 规则三：从状态变化抽状态机

**步骤：**
1. 找出所有**表示业务状态的变量**（如 `status`、`state`、`phase`、`stage`）。
2. 收集该变量的**所有取值**（字面量、枚举、常量表）→ 状态集合。
3. 收集该变量的**所有赋值点**（`setStatus(...)`、`status = ...`、接口返回后赋值）→ 转移集合。
4. 对每个赋值点，回溯**触发它的动作**（按钮点击 / 接口成功 / 定时器）→ `trigger`。
5. 回溯赋值前的判断条件 → `guard`。
6. 找初始值（`useState('todo')` / 默认值）→ `initial`。
7. 检查是否有**不可达状态**（定义了但没赋值）→ 要么补转移，要么删掉并记入 openQuestions。

**示例：**
```js
const [status, setStatus] = useState('todo');
// ...
if (status === 'todo')    setStatus('doing');    // 触发：开始
if (status === 'doing')   setStatus('blocked');  // 触发：标记阻塞
if (status === 'blocked') setStatus('doing');    // 触发：解除阻塞
if (status === 'doing')   setStatus('done');     // 触发：完成
```
→ 状态 `[todo, doing, blocked, done]`，转移 4 条，`initial = todo`。

**注意：**
- Demo 常用布尔量代替状态机（`isDone`、`isBlocked`）→ 要**归一化**成单变量状态机，否则状态组合会爆炸。
- 隐式状态（如"已提交但未审核"）在 Demo 里可能只是一个 flag → 要显式提升为状态。

---

## 5. 对齐规则：Demo 与 PRD 的差异必须显式化

逆向出的内容**不等于**需求。必须做一次差异对齐：

| 差异类型 | 处理方式 |
|---|---|
| Demo 有、PRD 需求里没有 | 判定是"必要能力"还是"临时实现"，前者补成需求，后者记 openQuestion |
| PRD 需求有、Demo 没有 | 标记为**未实现**，写进需求但 `source: inferred` |
| Demo 的行为与描述不一致 | 以**用户确认的描述**为准，把 Demo 行为作为反例写入 |
| Demo 里的硬编码 | 提升为**配置项/规则**，写进 `rule` |
| Demo 里的 mock 数据 | 转成**示例数据**，写进原型的 `data`，并标注"示例数据" |

**产出：** 一张差异表 + 更新后的 `requirements`（`source: "demo"`）+ `openQuestions`。

---

## 6. 逆向产出检查清单

- [ ] 路由全部映射到模块或页面，无遗漏
- [ ] 每个模块至少 1 条 P0 需求
- [ ] 每个条件分支都翻译成了规则或明确记入 openQuestions
- [ ] 每个业务状态变量都建了状态机，且无孤立状态
- [ ] 布尔标志已归一化为状态机
- [ ] 魔法数字已显式化
- [ ] Demo 与需求描述的差异已列表对齐
- [ ] 逆向出的需求 `source` 标为 `demo`，AI 补全的标为 `inferred`
- [ ] 逆向出的组件树保留了 Demo 的嵌套结构，但 `type` 已映射到白名单

---

## 7. 组件类型映射表（Demo 框架 → 白名单）

| Demo 里常见 | 映射到 |
|---|---|
| `<div class="card">` | `Card` |
| `<button>` / `<a class="btn">` | `Button` |
| `<input>` / `<textarea>` | `Input` / `TextArea` |
| `<select>` | `Select` |
| `<ul><li>` 列表 | `List` + `List.Item` |
| `<table>` | `Table` |
| `<nav>` / 侧边栏 | `Menu` / `Sider` |
| `<header>` | `Header` |
| `<dialog>` / 遮罩层 | `Modal` |
| 抽屉/侧滑面板 | `Drawer` |
| 徽标/状态点 | `Badge` / `Tag` |
| 空状态占位 | `Empty` |
| 加载骨架 | `Skeleton` / `Spin` |
| 统计数字块 | `Statistic` |
| 图表 canvas/svg | `Chart` |
| 未识别的自定义组件 | 保留结构，用最近的语义组件近似 + 记 openQuestion |
