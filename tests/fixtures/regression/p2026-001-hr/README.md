# p2026-001-hr — P1→P2 回归对（人力资源审计）

## 来源

- **项目**：P-2026-001（武汉长源，topic=人力资源管理，period=2026-H1）
- **提取路径**：`D:\01_CH\01_Doing\AU_PL_260601_人力资源_武汉长源\internal-audit-workspace\`
- **提取日期**：2026-08-11
- **提取内容**：
  - `input/policy-analysis_考勤管理规定_A5.json` ← `policy-analyses/长源_CHCY-QC-GL-002考勤管理规定_A5_analysis.json`（P1 document-organizer 真实产物）
  - `input/audit-program_人力资源管理_审计程序_v3.0.md` ← `audit-programs/人力资源管理_审计程序_v3.0.md`（P2 program-generator 真实产物，v3.0）

## 脱敏映射表

| 原文 | 脱敏后 | 类型 |
|:-----|:-------|:-----|
| 武汉长源（武汉长源冲焊件有限公司） | 公司A（公司A冲焊件有限公司） | 公司名 |
| 长源（公司简称/档案前缀） | 公司A | 公司名 |
| 武汉（地理位置） | 城市A | 地名（公司名组成部分） |
| 宁波长盛 | 公司B | 兄弟公司名 |
| 宁波长华 | 公司C | 兄弟公司名 |
| 广东长华 | 公司D | 兄弟公司名 |
| 一汽大众 / 上汽大众 | 客户1 / 客户2 | 客户名 |
| 比亚迪 | 客户3 | 客户名 |
| 特斯拉 | 客户4 | 客户名 |
| CHCY（制度编号前缀，疑似公司代码） | COA | 公司代码 |

脱敏规则：长词优先替换（如"武汉长源冲焊件有限公司"先于"武汉长源"）；替换后全文 grep 无残留（验证见 input/ 文件）。

## 用途

- **回归基准**：P1（制度分析）与 P2（程序生成）的真实输入输出对。`expected_output/` 记录两把校验闸机（`validate-policy-analysis.py`、`validate-program.py --ir --strict`）在提取日期的 exit code 与关键输出摘要。
- **回归信号**：当 SKILL.md / 校验脚本 / schema 变更后，用本用例重跑：
  1. `python _shared/scripts/validate-policy-analysis.py tests/fixtures/regression/p2026-001-hr/input/policy-analysis_考勤管理规定_A5.json`
  2. `python _shared/scripts/validate-program.py tests/fixtures/regression/p2026-001-hr/input/audit-program_人力资源管理_审计程序_v3.0.md --ir --strict`
  3. 对比 exit code 与关键指标（风险覆盖率、测试程序数、无数据来源步骤数）与 `expected_output/` 的差异，判定 GREEN/YELLOW/RED。
- **注意**：两把闸机提取日均返回 BLOCK（exit=2 / exit=1，缺 schema_version 与 6 处模糊判定标准）——这是源数据的真实状态，非脱敏引入，作为历史基线保留。

## findings 回归对（待补）

**待补**：P-2026-001 当前处于 phase_3_execution，findings_count=0，尚无真实 finding 产物。待该项目完成 P3 执行取证后，从 `findings/` 提取 1-2 份有定论的 finding（含 decision_rationale）作为 P3→P4 回归对补充到本案例或新增案例。
