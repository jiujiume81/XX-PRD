# 变更记录

本文件记录 XX-PRD 的版本变更、兼容性影响与升级方式。
格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。
**每个条目必须含 `breaking` 字段**（是 / 否 + 一句说明），用于判断能否安全升级。

> **状态：`0.7.0` 为本版（未发布）；`0.6.0` 已于 2026-10-21 发布（`2d51574`）；`0.5.0` 已于 2026-10-20 发布（`5409cbf`）。**
> **`0.7.0` 只加门与字段，不动断言基线**：`run.sh` 仍是 `TOTAL ok=757`，`CASES` 与 `-ne 757` 未改。
> `0.5.1` **从未单独发布**，其变更（`RETRIES_MAX` 默认 0）并入 `0.6.0` 一同交付 ——
> 所以升级 `0.5.0 → 0.6.0` 的人同时承受 `[0.5.1]` 的 breaking（"绿"变严）与 `[0.6.0]` 的新增字段。
> `[0.5.0]` 段里仍标「待核」的条目是**发布当时的核验目标**，其结论以 `iterations/I-01/release.md`
> 与 `iterations/I-02/build.md` 记录的实测为准——本文件不重复断言，也不因发布而在事后补写"已验证"。
> （「待核」「未验证」**不在占位词表里**：词表只收 5 个"未填内容"类的词，见 `scripts/placeholder-vocab.json`；
> 这两个词描述的是**核验状态**而非**未填内容**，所以 DoD 8 不会因它们判红——`tests/check_placeholders.py`
> 实测 `PASS placeholders: 16 处命中均已在显式允许清单内`。**留着它们既诚实、也不妨碍放行。**）
> `[0.5.1]` 段对应的核验命令：`bash tests/run.sh`（回归）、`python3 tests/check_generators.py`（生成器一致性）。

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
