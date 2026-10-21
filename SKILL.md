---
name: XX-PRD
version: 0.7.0
description: 产品经理需求分析与原型设计工作台。把口头需求/一句话想法/Vibe-Coding Demo 收敛成「可交互原型 + EARS 规范 PRD + 标注对齐」三合一的单文件 HTML 容器，基于 Ant Design 5 设计（内置压缩版 AntD token 与组件语义，并据此推导容器选型 / 主子表 / 跳转 / 视觉等设计准则），先做行为建模（角色 × 状态 × 命令 + 页面职责）再画原型，产出可交付给 AI 直接开发的开发交接包；流程带闸门（澄清与切片清单必须经用户确认，由脚本校验），大需求按用户故事最小闭环逐片交付。当用户要写 PRD、做需求分析、澄清需求、画原型、做需求评审、把 Demo 逆向成文档、对齐产研理解、生成产品需求文档或交互原型时使用。触发词：PRD、需求分析、需求澄清、原型、原型图、可交互原型、EARS、用户流、模块清单、页面清单、状态机、标注、评审、Demo 逆向、需求文档、产品文档、设计准则、设计原则、Ant Design、AntD、主子表、主从表、对话框选型、抽屉、页面关系图、开发交接、命令策略、按钮置灰、状态流转、多状态单据、页面切分、功能拆分。
---

# XX-PRD — 需求分析与原型设计工作台

把"压缩的 Demo / 模糊的想法"展开成"产研可直接消费的 PRD + 可交互原型"，并在同一个容器里完成**评审、标注、对齐、导出**。

## 开工第一件事：过闸门，不是写文档

这个 skill 的流程**不靠"记得要问"，靠脚本拦**。开工先建流程状态，每阶段落盘，卡点由脚本记录：

```bash
python3 scripts/prd_flow.py start --product "<产品名>"   # 建流程状态（XX-PRD.workflow.json）
python3 scripts/prd_flow.py status                        # 看当前阶段 + 下一步 + 缺哪些产物
python3 scripts/prd_flow.py submit <stage>                # 该阶段产物齐了才提交
python3 scripts/prd_flow.py approve A --by user           # 卡点必须显式批准
python3 scripts/prd_flow.py guard build                   # 生成原型前自检
```

| 卡点 | 位置 | 未批准会怎样 |
|---|---|---|
| **A** | 澄清 + EARS + 行为建模之后 | `guard build` 退出码非 0 → **禁止写 `pages[]` / `componentTree`** |
| **B** | 切片计划之后 | `guard export` 退出码非 0 → **禁止导出交付物** |

**首轮红线（违反即返工）**

- 首轮回复**只允许**三样东西：澄清问题（5~7 个，能给选项就给选项）、你的假设与默认值、非目标。**不得**出现 JSON / HTML / 组件树 / schema 片段 / 「我先搭个原型」。
- 用户给的需求**再详细也不等于澄清完成**：`shaping/` 里 5 份产物没落盘、P0 问题没答案，就不算澄清完。
- 卡点 A 批准前写的任何原型代码都是白做。宁可多问一轮，不要返工一片。

> 这道闸门是补出来的：此前 8 阶段与卡点只写在文档里，没有状态、不可校验，
> 于是"需求丢进去就直接生成原型"反复发生。现在卡点是一个文件 + 一个退出码。

## 核心产物

| 产物 | 形式 | 说明 |
|---|---|---|
| 流程状态 | `XX-PRD.workflow.json` | 8 阶段 + 卡点 A/B 的落盘状态，`scripts/prd_flow.py` 维护 |
| 澄清产物 | `shaping/*.md` + `open-questions.json` | 产品定位 / 用户流 / 模块清单 / 页面清单 / 待澄清问题 |
| **切片计划** | `shaping/slices.json` | **用户故事级交付单元**，卡点 B 的确认对象 |
| 数据契约 | `XX-PRD.data.json` | 唯一真源，容器渲染 + 校验 + 导出都基于它 |
| **行为模型** | `tasks[]` + `capabilities[]` + `pages[].contract` | **角色 × 状态 × 命令 + 页面职责**，按钮可用性与页面切分的依据 |
| 交付容器 | `XX-PRD.html` | **单文件**，双击即开，无需服务器/联网 |
| PRD 文档 | 容器内右栏（可编辑，含**内嵌流程图**）/ 导出 `.md` | EARS 规范 |
| 可交互原型 | 容器内中栏 | 组件树 + 交互 + 页面状态 + **主子表联动** + **单据状态模拟** |
| 页面关系图 | 容器内顶部「关系图」 | 全局展开的分层有向图，一眼看清页面关系 |
| 开发交接包 | `{产品}.devspec.json` + `AGENT.md` | **机器可读**，供 AI/研发直接开工 |
| 标注 | 容器内原型上的气泡 | 用户提意见 → AI 改原型 |
| 本指南 | `guide.html` | skill 的**自解释文档**：工作流 / 设计准则（AntD 基线 + 7 条设计原则）/ PRD 结构 / 产物功能 |

---

## 工作流（8 个阶段，含 2 个人工确认卡点）

```
① 澄清 → ② 需求分析(EARS+状态机) → ③ 行为建模(任务/命令/页面职责)
   →【卡点A：确认需求 + 行为模型】→ ④ 切片计划 →【卡点B：确认切片清单】
   → ⑤ 逐片生成（每片：片段 → check → merge → validate → done）
   → ⑥ 标注评审迭代 → ⑦ 原型定稿 → ⑧ 生成最终 PRD + 导出
```

每个阶段的产出都要**落盘并 `submit`** 才算完成。`submit` 会检查该阶段的产物是否真的存在、
有体量、不是占位符 —— 所以"口头说做完了"在这里不成立。

> **③ 为什么必须单独一个阶段**：只做 EARS + 状态机，信息是**分开记录**的 ——
> 角色在 `users`、状态在 `stateMachines`、按钮在组件树里，三者之间没有强制对应关系。
> 结果就是「单据五个状态、按钮永远可点」「三个角色的表单揉在一页」这类看起来正常、用起来别扭的产物。
> 行为建模就是把这条语义链**显式写出来**，再据此画原型。

### 阶段 ① 需求澄清

1. 读 `references/01-clarification.md`。
2. 按 9 个维度提问，**每轮 5~7 个问题**，能给选项就不给开放题。
3. 产出 4 份 shaping 文档：产品定位 / 用户流 / 模块清单 / 页面清单（模板见该文件 §3）。
4. 产出待澄清问题，P0 必须有答案或默认值。
5. **落盘**到 `shaping/`：`positioning.md` / `user-flows.md` / `modules.md` / `pages.md` / `open-questions.json`
   （问题格式：`{"questions":[{"id":"q-1","question":"…","priority":"P0","status":"resolved|assumed","answer":"…"}]}`）。
6. `prd_flow.py submit clarify`。闸门会拦：产物缺失、体量过小、过半是占位符、P0 还挂着 `open`。
7. 「澄清完成判据」全部满足且 submit 通过，才进入阶段 ②。

**若输入是 Vibe-Coding Demo 代码**：跳到 `references/06-demo-reverse.md`，按"路由抽模块、分支抽规则、状态变化抽状态机"三条规则逆向，再回到本流程对齐。

### 阶段 ② 需求分析（EARS）

1. 读 `references/02-ears-spec.md`。
2. 逐条产出 EARS 条目，字段：`角色/触发/规则/状态机/预期/验收`。
3. 建状态机（`stateMachines`），覆盖实体生命周期。**系统自动流转标 `system: true`**（定时任务 / 支付回调 / 超时关闭）。
4. 跑 §5 质量门禁自检，不通过则重写。
5. **前置校验落位 `guards[]`（在做行为建模之前）**：源文档里凡是出现
   `必须` / `不得` / `禁止` / `否则` / `仅当` / `至少` / `不能` 的句子，逐条对应一条
   `guards[]`，`kind` 取 `block`（不满足就拦住）或 `warn`（提示但放行）；
   推进后系统自动做的事写进 `effects[]`。
   **可判定口径**：源文档里这类句子有 N 条，`guards[]` 至少 N 条；
   哪条没落位，在 `shaping/requirements.md` 里逐条写明理由（例如「由后端校验，界面不体现」）。
   判定不靠"我记得问了"——校验器会数条数并打在 `行为补充：guards=…` 这行上。
   **只在散文里写等于没写**：QMS 实测里「发起检验前必须先编质检标准」全靠散文，
   换一个模型读 PRD 就丢了，而它同时决定发起检验节点、质检标准落位、7 条硬校验三件事。
6. 落盘 `shaping/requirements.md`，然后 `prd_flow.py submit ears`。

### 阶段 ③ 行为建模（任务 / 命令策略 / 页面职责）

**这一步不能跳过**，读 `references/09-behavior-model.md` + `references/10-page-decomposition.md`。

1. **业务任务 `tasks[]`**：谁 / 想完成什么 / 判断依据 / 什么算完成。任务是页面切分的**唯一依据**。
2. **命令策略 `capabilities[]`**：每条业务动作一行 —— 角色、允许状态 `from`、守卫 `guard`、
   不可用策略 `policy`（`hidden` / `disabled` / `reject`）、拒绝原因 `reason`、结果 `to`、失败恢复 `onFail`。
3. **反向补状态机**：每条人工转移要么有对应 capability，要么标 `system: true`；缺的补上。
4. **页面职责 `pages[].contract`**：`task` / `actor` / `entity` / `owns`（负责发起的命令）/
   `submitBoundary` / `doneWhen`。**一条命令只能有一个主页面**。
5. **按职责切页面**：命中任一拆分信号（角色不同 / 生命周期阶段不同 / 提交边界不同 / 信息超两屏 /
   权限差异大 / 入口不同）就拆；五条合并判据全中才合。
6. 自检 `09` §8 的 12 条 + `10` §8 的 12 条。
7. 把「任务清单 / 命令策略 / 页面职责」三张表落盘到 `shaping/behavior.md`（缺任一张，`submit` 会被拦），
   然后 `prd_flow.py submit behavior`。

**【卡点 A】把需求清单 + 状态机 + 命令策略表 + 页面职责表 + 待澄清问题给用户确认。**
未确认不进下一阶段。命令策略表要让用户逐条确认「这个状态下这个按钮该不该可点」。

### 阶段 ④ 切片计划（取代原「板块计划」）

**为什么换**：`板块` 从来没被定义到可执行颗粒度。一个大需求里一个模块几十个页面，
"按板块"仍然是巨块，单轮输出必然衰减。改成**用户故事最小闭环**为交付单元。

1. 读 `references/11-slice-delivery.md`。
2. 拆成用户故事级切片，写入 `shaping/slices.json`：每片一个角色 / 一个目标 / 一条闭合主路径 / 能独立验收。
3. 单片上限：**≤4 页面 / ≤6 命令 / ≤12 需求 / ≤80 组件节点**。超了继续拆，不要硬塞。
4. `python3 scripts/prd_slice.py plan shaping/slices.json` 通过
   —— 会拦住页面或命令被两片同时认领、依赖成环、超上限、缺字段。
5. `prd_flow.py submit plan`。
6. **【卡点 B】用户确认切片清单与顺序**：每片的范围、体量、验收边界都要看得明白，
   而不是只看一个模块名。确认后 `prd_flow.py approve B --by user`。
7. `boardPlan` 仍要写进数据契约（容器的板块导航用它），但它现在**由切片清单推导**，不是拍脑袋的板块顺序。

### 阶段 ⑤ 逐片生成原型 + PRD

**一轮只做一片**，六步走完再下一片：

```bash
# 1. 写片段 slices/s-01.json（只含本片页面 / 需求 / 命令 / 状态机增量 / 数据模型新增字段）
# 2. 单片自检
python3 scripts/prd_slice.py check slices/s-01.json --plan shaping/slices.json
# 3. 合并全部已完成片段
python3 scripts/prd_slice.py merge slices/*.json -o XX-PRD.data.json --plan shaping/slices.json
# 4. 整份校验（这里查跨片引用是否闭合）
python3 scripts/validate_prd_json.py XX-PRD.data.json
# 5. 标记完成
python3 scripts/prd_slice.py done s-01 --plan shaping/slices.json
# 6. 跑下一片
```

1. 读 `references/04-container-schema.md`（数据结构）+ `references/05-component-states.md`（组件白名单）
   + `references/11-slice-delivery.md`（片段格式与上限）。
2. `check` 不过不合并；`validate` 有 ERROR 不进下一片。单片阶段允许"引用了别的切片的页面"这类跨片错误，
   合并后必须为 0。
3. 每页必须产出：
   - `componentTree`（组件树，`type` 走白名单，`id` 稳定）
   - `states`（**≥4 态**：默认/加载/空/异常）
   - `interactions`（主路径关键动作有反馈）
   - `prd.sections`（页面目标 / **主流程图 `type:"flow"`** / 交互说明 / **动作可用性** / 业务规则 / 页面状态 / 验收）
   - `contract`（阶段③已定，落到页面上）
4. **业务按钮引用 `capability`，不要写死 `disabled`**：`props.capability`（页面级）、
   `columns[].actions[].capability`（行级）。页面声明 `entity` 后，顶部出现「单据状态」下拉，
   可以逐个状态切换验证按钮表现。
5. 同步维护 `components`（关键组件与状态定义）与 **`dataModel`**（实体 / 字段 / 主外键 / 关系 / 派生字段）。
6. **单页数据层级多时用主子表**：一条主记录挂多条明细（任务→巡检项、订单→商品行）用 `MasterDetail`
   把主表与子表关联起来，点行联动、子表可展开收起；**不要平铺两张表**。契约见 `04-container-schema.md` §6.7。
7. **表单录入 / 详情先选容器**：读 `references/08-container-choice.md`，按决策树确定用
   对话框 / 抽屉 / 新页面（长表单禁对话框、禁 dialogception、详情主从首选抽屉）。选错了校验器会 ERROR。
8. 每片合并后让容器渲染一次，确认无警告；顶部「关系图」应保持连通，**不能因为分片而出现孤岛页**。

### 阶段 ⑥ 标注评审迭代

1. 用户在容器里点原型加标注（`status: open`）。
2. **推荐入口**：用户点容器顶部「⇪ 标注指令」，一键生成/复制一段结构化 prompt 交给你。
   该指令已自动带上每条标注的**锚定节点、节点类型、当前属性摘要、渲染条件**，无需用户手工描述上下文。
3. AI 逐条判断影响面（组件树 / 交互 / 状态 / 需求 / **命令策略**）。
4. 修改 JSON → 标注置 `resolved` → `replies` 追加"改了什么"。
5. 若影响 EARS 需求或命令策略，同步更新 `requirements` / `capabilities` 与 PRD。
6. 重复直到无 open 标注。

### 阶段 ⑦ 原型定稿

- 走查：组件树与 PRD 描述一致、状态机状态在原型可见、四态齐全。
- **逐个切换「单据状态」**：每个状态下按钮的可用性是否符合命令策略；置灰按钮点下去是否有原因提示。
- 走查关系图：所有页面都在图上且连通，没有孤岛页。
- 打开「审核模式」检查：过程产物隐藏后，PRD + 原型是否自洽。

### 阶段 ⑧ 生成最终 PRD + 导出

1. 按 `references/03-prd-structure.md` 的 §2 大纲组装完整 PRD。
2. 导出 Markdown（`{产品名}-PRD-v{版本}.md`）、关键页截图 PNG、关系图全图 PNG。
3. 跑 `scripts/validate_prd_json.py` 校验，全 PASS 才交付。
4. **若用户要交给研发 / 让 AI 开始写代码**：点顶部「⬇ 开发交接」导出
   `{产品}.devspec.json` + `AGENT.md`，并复制其中的「AI 交接指令」。
   交付前确认 `devNotes` 里没有 `missing` 项（缺 `dataModel` / `modules` / `requirements` 会被标出来）。

---

## 容器使用（交付给用户的操作）

生成 `XX-PRD.html`（复制 `assets/container/index.html`，把数据内联进 `#iprd-data`）。

| 区域/按钮 | 作用 |
|---|---|
| 左栏 · 页面导航 | **树形目录：模块 → 页面 → 子页面**（多模块/多级页面时用它切换，不用顶部页签） |
| 导航筛选 | 按模块名 / 页面名 / 路由 / 页面 id 过滤，自动保留命中项的祖先链路 |
| 导航角标 | 页面行右侧显示该页待处理（`open`）标注数量 |
| 顶栏面包屑 | 显示「模块 / 父页面 / … / 当前页 + 路由」，模块名与页面名相同时去重 |
| ☰ / ‹ | 收起 / 展开左栏；左栏宽度可拖拽，均记入 localStorage |
| 中栏 | 可交互原型（JSON→UI 渲染，**页面间可跳转、可带参、可返回**；单页数据层级多时用**主子表**：主表选行 → 子表联动） |
| 中栏 · 缩放 | 工具条 `−  100%  +` `适应宽度`；左栏/右栏占位后原型被挤压时用它放大细节或缩略纵览 |
| 中栏 · 平移 | 拖拽画布即可平移；也可开「✋ 平移」模式、按住空格、或鼠标中键拖拽 |
| 中栏 · 跳转 | 点表格行 / 行内按钮 / 页面里的按钮会按 `interactions` 跳页；URL hash（`#/page-id`）即当前页，可分享、可浏览器前进后退；页面内「返回」不会跳出容器 |
| 右栏 | PRD 文档（可直接编辑，自动存 localStorage）；正文里的 `type:"flow"` 小节渲染成**内嵌 SVG 流程图**（原尺寸、可横向滚动，点「⤢ 放大」全屏看整体）；`dataModel` 渲染成「数据模型」小节；`capabilities` 渲染成**命令策略矩阵**（行 = 命令，列 = 状态，✓/—，点状态名可切换） |
| 右栏 · 折叠 | 面板头「›」或原型栏「PRD ‹」收起，右侧出现竖向「PRD」把手可展开；拖分割条调宽，**双击分割条复位**（拖到极值也能拖回）；宽度与折叠态记 localStorage |
| 状态切换 | 一键切 默认/加载/空/异常 态 |
| **单据状态** | 页面声明 `entity` 后出现：切换业务生命周期状态（草稿/待审批/已审批…），当场验证按钮该可用、置灰还是隐藏；置灰按钮点下去会说明原因 |
| 关系图 | **全局展开的页面关系图**：分层布局 + 带跳转标签的有向连线（回边/入口虚线、当前页相关高亮）；图在视口里居中、缩放后滚动范围精确；可拖卡片、切纵横、缩放、适应、**导出全图 PNG**；点卡片进入该页 |
| 标注模式 | 点原型任意位置加气泡；点气泡看/改/删 |
| ⇪ 标注指令 | **把标注导出为一段可直接交给 AI 的修改指令**（含锚定节点上下文），支持复制 / 下载 .md / 范围与筛选切换 |
| ⬇ 开发交接 | 导出 `{产品}.devspec.json`（机器可读唯一真源）+ `AGENT.md`（实现约定）+ 可复制的「AI 交接指令」 |
| 审核模式 | 隐藏过程产物（shaping 文档），只留 PRD+原型 |
| 导出 | 当前页截图 PNG / 关系图全图 PNG / 整份 Markdown |
| 保存 | 自动存 localStorage，可"重置为 AI 版本" |

> **页面数 ≥ 6 或存在多级页面时**：务必用 `pages[].parentId` 表达层级，让左栏树能呈现结构；扁平化地把所有页面平铺会让评审时找不到位置。

> **原型被左/右栏挤压时**：不要靠缩小浏览器窗口或删页面来腾空间。中栏自带缩放（25%~300%）与平移：
> - `⌘/Ctrl` + 滚轮 → 以光标为锚点缩放；`⌘/Ctrl` + `0` / `+` / `-` → 复位 / 放大 / 缩小
> - 「适应宽度」把原型压回中栏可视宽（等价 100%），不会产生横向滚动条
> - 空格拖拽 / 鼠标中键拖拽 → 临时平移；「✋ 平移」按钮 → 常驻平移模式
> - 平移模式与标注模式**互斥**（开一个自动关另一个），避免"想拖画布却点出气泡"
>
> 缩放下**标注气泡仍严格贴合锚定节点**（归一化坐标 + 画布盒基准，与 zoom 无关）。所以评审时可以先放大看细节、再缩回纵览，标注不会跑位。

> **让原型「能走通主路径」**：不要把所有页面都做成孤岛。列表 → 详情的跳转成本很低：
> - 表格加 `props.rowClick: true`，操作列用 `columns[].actions` 声明按钮；
> - 写**一条通配** interaction（`n-table__row_*` / `n-table__act_*_<key>`）就能覆盖所有行；
> - `navigate.params` 里用 `{{row.字段}}` 按行带参（在源页求值），目标页用 `{{变量名}}` 渲染；
> - 目标页记得在 `states[].vars` 里留默认值，这样单独打开它也正常；
> - `Header` 加 `props.back: true` 就有返回箭头；`Modal` 的 `__cancel` 内建关闭弹窗。
>
> 评审时最常被问的就是「点这里会去哪」——跳转接得上，PRD 才站得住。

> **让 PRD「一眼看懂流程」**：PRD 正文里至少放一条主流程图，别只写文字步骤：
> - 在 `prd.sections` 里加一节 `{ "type": "flow", "heading": "主流程", "caption": "…", "nodes": [...], "edges": [...] }`
> - 节点用 `kind` 区分 `start` / `end` / `decision` / `warn`；`sub` 写真实路由或真实节点 id
> - 判定节点的每条出边都要有 `label`（"是/否/通过/驳回"）
> - 容器会用与「关系图」同一套分层布局引擎把它画成内嵌 SVG，导出 Markdown 时降级为箭头链路
> - 图在窄 PRD 栏里**按原尺寸渲染并横向滚动**（不缩到看不清），图注旁「⤢ 放大」可全屏看整体 —— 所以节点文案可以写完整，不必为塞进窄栏而缩写
>
> 契约见 `references/03-prd-structure.md` §5.5。

> **数据层级多就用主子表**：一条主记录下挂着若干明细时，别把两张表平铺成兄弟节点：
> - 用 `MasterDetail` 包住两张 `Table`（`children[0]`=主表，`children[1]`=子表）
> - 声明关联字段：`bind`（主表字段）+ `bindTo`（子表字段）；**两表字段不同名时 bindTo 必须显式写**
> - 主表开 `props.radio: true`（单选圆点标出当前行），**不要设 `rowClick`**（点行 = 选中行）
> - 子表 `data` 写**全量**明细，容器按 `bind` 过滤；子表可展开收起、标题显示「共 N 条」
> - 要跳页请用主表 `columns[].actions` 里的按钮（`n-table__act_*_detail`）——点按钮不会误触发选行
> - 主表可配列表页三件套：`query`（查询条）/ `toolbar`（操作条）/ `pagination`（分页脚）
>
> 契约见 `references/04-container-schema.md` §6.7，示例见 `assets/examples/example-04-master-detail.json`。

> **表单录入 / 详情先选对容器**：选错容器是 B2B 最常见的体验债，校验器会直接拦：
> - 轻量确认（≤3 字段、危险操作确认）→ `Modal`；对照上下文、边填边看 → `Drawer`；复杂长程 → 新页面
> - **长表单（>15 字段）禁用 `Modal`**、**禁止 `Modal` 套 `Modal`**（校验器 ERROR）
> - **详情主从首选 `Drawer`**，别用 `Modal`（展不开关联信息与操作区）
> - 抽屉里不要塞 ≥3 个 tab 的工作台，应升级为新页面
> - 详情页（新页面）必须在 `states[].vars` 里留默认值，保证可独立渲染
>
> 决策树 / 五维矩阵 / 反模式见 `references/08-container-choice.md`。

> **按钮可用性别写死，交给命令策略**：单据有多个状态时，最容易被漏掉的就是「这个状态能不能点」：
> - 每条业务动作写一条 `capability`：`actor`（谁能做）+ `from`（什么状态能做）+ `policy`（不能做时怎么办）
> - `policy` 三选一：`hidden`（不该知道）/ `disabled`（存在但当前不行，默认选它）/ `reject`（点了才拒绝）
> - `reason` 要写清「当前状态 + 允许状态」，例如「仅「待初审」可审批，当前为「已放款」」
> - 按钮写 `props.capability`，表格行内写 `columns[].actions[].capability` —— **不要写 `disabled: true`**
> - 页面加 `entity`，顶部就能切「单据状态」逐个验证；置灰按钮点下去会说明原因，不是无反应
>
> 方法见 `references/09-behavior-model.md`，示例见 `assets/examples/example-05-behavior-model.json`。

> **页面按任务切，不要按功能堆**：把多个功能的表单与详情塞进一页，是 B2B 原型最常见的「信息很全但没法用」：
> - 每个页面写 `contract`：一条 `task` + 一个主体 `entity` + 一组 `owns`（负责发起的命令）
> - **一条命令只能有一个主页面**，其他页面引用同一个 `capability.id`，不另写一套禁用逻辑
> - 命中任一拆分信号就拆：角色不同 / 生命周期阶段不同 / 提交边界不同 / 信息超两屏 / 权限差异大 / 入口不同
> - 五条合并判据**全中**才合：同角色、同对象、同决策、同提交边界、同屏可读
> - 拆完要接得上：每个页面有 `entryFrom`、返回回「来的地方」、提交后回列表并保留筛选
>
> 判据与反模式见 `references/10-page-decomposition.md`。

> **让产物「AI 能直接开发」**：光有好看的 PRD 不够，关键信息必须在 JSON 里：
> - `dataModel.entities[]` 写实体与字段（类型 / 约束 / `pk` / `fk` / 枚举候选值），派生指标进 `derived[]` 并写 `fallback`
> - 页面关系由 `interactions` 里的 `navigate` 自动抽成 `pageGraph`，所以**跳转写全 = 关系图自动成立**
> - 未确认的东西不要藏：`openQuestions` / `status:"draft"` / `source:"inferred"` 会被汇总进 `devNotes`
> - 交付时用顶部「⬇ 开发交接」一键导出 `devspec.json` + `AGENT.md` + AI 交接指令

---

## 关键约定（必须遵守）

1. **单文件优先**：交付物是单个 HTML，数据内联，双击可用，不依赖 CDN。
2. **先定 Schema 再产出**：任何 JSON 都必须符合 `references/04-container-schema.md`。
3. **ID 作用域**：全局实体（`u-`/`m-`/`page-`/`flow-`/`c-`/`sm-`/`REQ-`/`bp-`/`q-`）全局唯一；页内实体（`n-`/`ix-`/`s-`/`an-`）只需页内唯一。
4. **ID 稳定**：`n-` 节点 id 一旦分配，重生成原型时不得更改（标注靠它锚定）。
5. **组件白名单**：`type` 只能用 `references/05-component-states.md` 列出的值；未知类型会被容器降级并打警告。
6. **四态必备**：每页至少 默认/加载/空/异常；确实不适用的用 `notApplicableStates` 显式声明。
7. **EARS 门禁**：无主观词、无实现细节、单一响应、可验收。
8. **涨红跌绿**：涉及涨跌/收益，涨用红色、跌用绿色（中国市场惯例）。
9. **推断必标**：AI 推断的内容 `source: "inferred"` 且写进 `openQuestions`。
10. **交付前必跑校验**：`python3 scripts/validate_prd_json.py <产物.json>`，出现 `ERROR` 必须修复后才能交付。
11. **不越卡点**：卡点 A/B 未确认，不继续推进。
12. **跳转要接得上**：主路径上的页面用 `navigate` 串起来；带参跳转用 `{{row.字段}}` / `{{变量}}`，目标页必须能用默认值独立渲染。
13. **合成节点 id 别猜**：`<节点 id>__back` / `__ok` / `__cancel` / `__row_<i>` / `__act_<i>_<key>` 由容器内建（详见 `references/04-container-schema.md` §0.2）；弹窗按钮用的是 **Modal 节点 id**，不是 `props.modalId`。
14. **每页要有流程图**：`prd.sections` 里至少一个 `type:"flow"` 小节；有 `start`/`end`、判定出边带 `label`、无孤岛节点（校验器会 WARN）。
15. **数据模型不能只在正文里**：实体/字段/主外键/关系写进顶层 `dataModel`，派生指标进 `derived[]` 且必须有 `fallback`；`enum` 必须把候选值写进 `constraint`。
16. **交付给 AI/研发时必须给交接包**：`devspec.json` + `AGENT.md`，且 `devNotes` 里没有 `missing` 项。
17. **主子表不要平铺**：一条主记录挂多条明细时用 `MasterDetail`（主表 + 子表联动），`bind`/`bindTo` 写清关联字段，主表不设 `rowClick`。
18. **容器选型合规**：长表单（>15 字段）不用 `Modal`、禁止 `Modal` 套 `Modal`、详情不用 `Modal` 承载、抽屉里不塞多 tab 工作台。
19. **表字段语义要能一眼看懂**：`columns[].type` 用对（`index` 序号 / `tag` 状态 / `action` 操作列 / `progress` 进度）；状态标签的颜色映射在全站统一。
20. **设计基线是 Ant Design 5**：原型直接复用 AntD 的 token 与组件语义（`--ant-*` 变量、同名组件），不自由发挥配色与形态。上面第 17/18 条并非孤立规矩，而是设计原则（自然 / 确定 / 意义 / 亲密性 / 直截了当 / 即时反应 / 可生长）推导出来的结果 —— 完整推导见 `guide.html` §2。
21. **先建模，再画页面**：`tasks[]` → `capabilities[]` → `pages[].contract` 必须在生成原型**之前**完成；没有行为模型就画页面，按钮只能靠「常见后台长相」补，必然漏掉状态与权限。
22. **按钮可用性来自 `capability`，不写死 `disabled`**：每个业务按钮（纯查看类除外）都要指向一条 `capability`；`policy` 默认 `disabled`（置灰 + 说明原因），不是一律 `hidden`。
23. **一条命令只有一个主页面**：`contract.owns` 里声明的命令不得被第二个页面重复 owns；其他页面可以引用同一个 `capability.id`，但不能各写一套逻辑。
24. **状态机的每条人工转移都要有入口**：要么有 `capability` 覆盖，要么标 `system: true`（定时任务 / 回调 / 超时）。校验器会 ERROR。
25. **验收必须覆盖非法路径**：每条关联状态机的需求，至少一条验收写「状态不符 / 权限不足 / 并发冲突时被拒绝」，只写成功路径等于只写了一半。
26. **流程状态必须落盘**：开工先 `prd_flow.py start`，每阶段 `submit`，卡点 `approve`。没有 `XX-PRD.workflow.json` 就开始写文档，等于没有流程 —— 卡点会随上下文一起消失。
27. **卡点未批不得产出**：`guard build` 不通过，不许写 `pages[]` / `componentTree`；`guard export` 不通过，不许导出。这条**优先于**任何"先做个样子看看"的要求。
28. **切片交付，不整包生成**：一轮只做一片；单片超限（4 页面 / 6 命令 / 12 需求 / 80 节点）必须再拆。`merge` 冲突就回头统一理解，不要改后者覆盖。
29. **单片可独立验收**：每片做完要能单独打开、单独评审、单独说"对/不对"；做不到就说明切错了。

---

## 参考文件索引

| 文件 | 何时读 |
|---|---|
| `references/01-clarification.md` | 阶段①：澄清提问、4 份文档模板、完成判据 |
| `references/02-ears-spec.md` | 阶段②：EARS 句式、条目字段逐项说明、门禁 |
| `references/03-prd-structure.md` | 阶段⑤⑧：PRD 大纲、五层结构对应关系 |
| `references/04-container-schema.md` | 全程：**数据契约**（先读这个） |
| `references/05-component-states.md` | 阶段⑤：组件白名单、状态矩阵、骨架模板 |
| `references/06-demo-reverse.md` | Demo 逆向：三条抽取规则 + 对齐规则 |
| `references/07-quality-and-examples.md` | 全程：验收标准、反例、交付话术 |
| `references/08-container-choice.md` | 阶段⑤：**容器选型准则**（对话框 / 抽屉 / 新页面 / 主子表）+ 反模式 |
| `references/09-behavior-model.md` | 阶段③：**行为建模**（任务 / 命令策略 / 状态 × 角色 × 动作 / 失败恢复 / 权限三粒度） |
| `references/10-page-decomposition.md` | 阶段③：**页面职责与功能切分**（合并五判据 / 拆分七信号 / 四类揉法） |
| `references/11-slice-delivery.md` | 阶段④⑤：**切片协议**（用户故事最小闭环 / 单片上限 / 片段格式 / 合并规则 / 反例） |
| `assets/container/index.html` | 阶段⑤：复制为交付容器 |
| `assets/examples/*.json` | 阶段⑤：全链路 few-shot，照着写（`example-05` 是行为建模范例） |
| `scripts/validate_prd_json.py` | 每次产出后：结构 + 行为语义校验 |
| `scripts/prd_flow.py` | 全程：**流程闸门**（8 阶段与卡点 A/B 落盘，`guard` 拦越级） |
| `scripts/prd_slice.py` | 阶段④⑤：切片计划校验 / 单片校验 / 合并 / 标记完成 |

---

## 快速开始

用户说"帮我写个 XX 的 PRD / 原型"时：

1. **先建流程状态**：`python3 scripts/prd_flow.py start --product "<产品名>"`。这一步不做，后面全会乱。
2. 读 `references/04-container-schema.md` 建立数据认知，读 `references/01-clarification.md`。
3. 抛第一轮 5~7 个澄清问题，**本轮到此为止**，等用户回答 —— 不许夹带任何原型内容。
4. 按 ①→③ 推进，每阶段把产物落盘到 `shaping/` 并 `submit`；到卡点 A 停下等确认。
5. 卡点 A 批准后做切片计划（阶段④：`shaping/slices.json` + `prd_slice.py plan`），卡点 B 确认切片清单。
6. 逐片生成：`check → merge → validate → done`，一片一片来（先看 `example-05` 学行为建模、`11-slice-delivery.md` 学片段格式）。
7. 全部 done → `guard export` 通过 → 复制容器、内联数据、跑校验、交付并说明操作方式。

> **用户想先了解这个 skill 是干什么的**：直接打开 `guide.html` —— 它是本 skill 的自解释文档
> （工作流 / 设计准则 / PRD 内容结构 / 产物功能说明），单文件、零依赖、可导出 PDF。
> 它同时也是一份很好的"交付说明"：把 `XX-PRD.html` 和 `guide.html` 一起给用户，用户自己就能看懂怎么操作。
