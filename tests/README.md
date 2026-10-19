# tests/ · 容器回归

一条命令验证"改动没破坏既有能力"：

```bash
bash tests/run.sh          # 退出码 0 = 全绿
CHROME=/path/to/chrome bash tests/run.sh
```

- 退出码：`0` 全绿 / `1` 有失败或漂移 / `2` 找不到 Chrome / `3` 另一个 `run.sh` 正在同目录跑（单实例锁）
- 依赖：`python3`、Node 不需要，Chrome（headless）、`harness.js`
- 只读 `assets/`，不修改任何产品文件；中间产物写到 `tests/.build/`（已 gitignore）

## 6 个用例与冻结基线

| 用例 | 数据来源 | 断言数（基线） |
|---|---|---|
| `00-embedded` | `assets/container/index.html` 自带的 `#iprd-data` | 94 |
| `01-taskboard` | `example-01-task-board.json` | 137 |
| `02-refund` | `example-02-refund-flow.json` | 123 |
| `03-navtree` | `example-03-nav-tree.json` | 136 |
| `04-masterdetail` | `example-04-master-detail.json` | 150 |
| `05-behavior` | `example-05-behavior-model.json` | 117 |
| **合计** | | **757** |

判据是**逐用例逐项对齐**：任一行 `ok` 与基线不等，或 `fails>0`，该用例即 FAIL、脚本 exit 1。
条数变少必须定位到"哪一条断言被条件跳过"（harness 会打印 `--   <原因>`），**不允许改基线数字**。

## 文件

| 文件 | 作用 |
|---|---|
| `harness.js` | 断言集合，由 `build_cases.py` 注入页面后原地执行；结果写进 `<div id="__testout" data-fails="N">` |
| `build_cases.py` | 渲染容器 + 注入示例 JSON 与 harness → 测试用 HTML |
| `check_generators.py` | 在临时副本里重跑 `gen_example0{3,4,5}.py`，与仓库 JSON 做归一化比对（`sort_keys=True`），不一致打印 `DRIFT: example-0N` |
| `check_docs.py` | 文档一致性 5 项：示例存在 / README 引用（`refs=N whitelist=M dead=0`）/ references 计数 / 版本三处 / `EXTERNAL` |
| `check_placeholders.py` | DoD #8：全仓扫 `TODO` / `TBD` / `待补充` / `待填`，命中必须落在 `ALLOW` 显式清单内（路径 + 片段 + 理由），否则 exit 1 |
| `run.sh` | 编排：生成器一致性 → 6 用例 headless 回归 → 汇总 |

## 加用例

在 `run.sh` 的 `CASES` 里加一行 `名称|示例文件|基线条数`，并先在本地跑出真实条数**人工核对**后再写死基线。
新增用例必须是"新增一行"，不得改动既有 6 行的基线。

## 断言约定（所有计数型输出）

**计数必须等于明细行数**：凡是打印 `xxx=N` 的检查，必须同时逐条列出这 N 项，`N == 明细行数`。
历史踩坑：`check_docs.py` 曾因白名单未去重打印 `whitelist=9` 却只列 8 行，计数与明细对不上，等于断言没被验证过。
例：`refs=23 whitelist=8 dead=0` 后面必须跟 8 行白名单明细；G3 验收按这条规则核。

**文档说明类命中应入 `ALLOW` 并写理由，不得靠改写措辞规避。** 说明"禁止 TODO"的文档本身不是占位——
把规则写清楚，比为了让检查变绿而写含糊更有价值；`ALLOW` 是白名单，不是"改写清单"。

**占位符检查的判定单位是「（文件, 行, 模式）」，不是「行」。** 同一行含两个占位词算两条命中；
`ALLOW` 必须逐模式覆盖（`marker` 里要含该模式本身），**不允许"这一行已经允许过了"就整行放行**。
历史漏洞：白名单命中曾按行判定，在已允许行尾追加一个 `TODO` 仍然 PASS、`PLACEHOLDER` 计数也不变——
和 E-01/E-02 同型（检查看起来在工作，实际给白名单行留了后门），已改为按命中判定。
**注意粒度**：模式级计数只判"该行是否出现该模式"，同一行重复出现的同一模式算 **1 次**；对"占位符"够用，
但若复用到需要逐次计数的场景（如外链计数 `EXTERNAL=n`），必须换成出现次数口径（`str.count()`），不能直接沿用本脚本。

## 已知约束

- Chrome 每次尝试用**全新且路径不同**的 `--user-data-dir=tests/.build/profiles/<case>/a1|a2`：复用 profile 会串上一个用例的 `localStorage`（页面状态、缩放、当前页），历史踩过。
- 删目录一律用 `python3 -c 'shutil.rmtree(...)'`，**不要用 `rm -rf`**：本机 `rm` 可能是带 bulk 阈值（50 文件）的安全删除包装器，Chrome profile 有 150+ 文件，会被拦成 `SAFE_DELETE_BULK_CONFIRM_REQUIRED` 且**静默不删**，于是 profile 被复用 → `01/02/05` 稳定少 1~2 条断言（`TOTAL ok=754`），看起来像产品回归，实际是测试环境自伤。
- **已知坑 · 排查顺序**：如果看到 `01/02/05` **各少 1~2 条断言**（例如 `ok=136/122/116`、`TOTAL ok=754`），**先查 profile 是否被复用，不要先怀疑产品**：
  1. `ls -A tests/.build/profiles/<case>` 是否有上一轮残留（正常应为空）；
  2. `cat tests/.build/<case>.chrome.log` 看同一 case 是否出现两次 `attempt`、`exit` 是否异常；
  3. `grep -c SAFE_DELETE <日志>`，非 0 说明删除被包装器拦了，profile 没被清掉；
  4. 只有以上都排除，再去看 `tests/.build/<case>.dom.html` 里哪几条断言失败。
  历史上这条坑曾把一次"测试环境自伤"误判为产品回归，多花了整轮排查。
- **单实例锁**：`tests/.build/.run.lock/` 用 `mkdir` 原子占位。并发跑同一工作区会互相覆盖 `.build/` 的 html/dom/profile，产出的数字不可信；第二个实例直接 `exit 3` 并打印持锁 pid，不静默排队。进程被 SIGKILL 留下的残锁会按 pid 判活自动回收。
- **`$var` 后面紧跟中文/全角符号时必须写 `${var}`**。macOS 自带 bash 3.2 会把全角括号的首字节并进变量名，`set -u` 下直接 `unbound variable` 中止整套回归，表现为"偶发失败"。最小复现：
  ```bash
  bash -c 'set -u; last_rc=0; echo "exit=$last_rc），重试"'   # bash: last_rc?: unbound variable
  bash -c 'set -u; last_rc=0; echo "exit=${last_rc}），重试"'  # exit=0），重试
  ```
  扫描命令：`grep -nE '\$[A-Za-z_][A-Za-z0-9_]*[^ -~]' tests/*.sh tests/*.py`（应为空）。
- 单用例偶发页面未跑完（拿不到 `__testout`）会重试一次，**重试必须可见**：`CASE` 行带 `retry=0/1`，末行 `TOTAL ... retries=<n>`。重试成功仍 exit 0，但 `retries>0` 不算干净通过。
- 每次 Chrome 调用的退出码、DOM 字节数与 stderr 尾部写入 `tests/.build/<case>.chrome.log`（空 DOM 时 `CASE` 行会标 `(no __testout, exit=N)`），排查时先看这个文件。
- **稳定性判据**：连续 3 次 `bash tests/run.sh` 全 PASS 且 `retries=0` 才算通过；`retries>0` 要记录在案。
- `pkill` 用 `^"$CHROME".*--headless` 锚定命令行开头：不锚定会连"命令行里恰好含这串字"的外层 shell 一起杀掉（曾出现 `Terminated: 15`）。
- **文本断言禁用 `grep '\|'`**：macOS 的 BSD grep 不支持基本正则交替，会静默返回空。需要交替请用 `grep -E` 或 `python3 -c`（本目录脚本均已遵守）。
- 生成器漂移是**硬断言**（XX-014）：`check_generators.py` 不过，`run.sh` 直接 exit 1，不跑浏览器。
