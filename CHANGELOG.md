# 变更记录

本文件记录 XX-PRD 的版本变更、兼容性影响与升级方式。
格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。
**每个条目必须含 `breaking` 字段**（是 / 否 + 一句说明），用于判断能否安全升级。

> **状态：`0.5.0` 尚未发布。** 标「待核」的条目是本期计划内容，**不是已发生的事实**；
> G4 发布前必须用命令核验通过才可保留原有措辞，未通过则改写为"未完成，见 I-01 偏差"。
> 核验命令：`bash tests/run.sh`（回归）、`python3 tests/check_generators.py`（生成器一致性）。

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
