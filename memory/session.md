# 最近一次工作记录

## 完成了什么
本次 session（2026-09-10）：坑2 整改第一批（三把小刀 + 漏洞1）在 worktree 完成（VERSION 2026-09-10-1）。

### 为什么这次只做这些
坑2 有四个漏洞。漏洞2/3 主体前置依赖没满足（上游 design-assessments 全库零实例、编号体系对不上 RK-AT-001 vs R01、上游格式自身漂移），地基不平不能上闸机。漏洞1 必须先于漏洞2——上游不可靠，拿它当分母等于拿不可靠清单当判分标准。所以先打三把零风险的小刀 + 补源头。

### ① 三把小刀
- **覆盖率漏表**：`program_ir_parser.py` 第 341 行的 `break` 让《风险识别清单》只读首表（2.1.1），分母残缺——回归基准里"风险点 40 个"与"覆盖率 100%（10 个风险）"并排自相矛盾。删 break 后分母 10→34，exit 不变
- **E 级定义矛盾**：`finding_rules.md` L53 校验矩阵把 E（第三方）打成"不足"，与 evidence_standards/宪法第3条/ledger `HARD_GRADES` 打架（R01 统一 A+E 时漏网的文件）
- **报告可靠性声明**：standard 模板加固定段 + report-generator SKILL 综合结论四要素→五要素

### ② 漏洞1 原文抽查
`validate-policy-analysis.py` 新增：按 `doc_name` 找原件（`_ocr.txt` / docx 标准库抽字 / txt），抽条款号与 JSON 的 `control_points[].source` 比对。中文数字归一化（第二条 ↔ 第2条）。

### ③ 关键设计：独立通道
实测发现 `audit_gate.py:147-152` 只看退出码是否为 0，不区分 warn(1)/block(2)——新检查设 warn 照样被拦。所以结果单列顶层字段 `source_reconciliation`、不进 `checks`、不参与 `action`。ADR-030 记录，闸机缺陷待单独修。

### ④ 测试
- 回归基线 `regression-check.py`：2 绿 0 红
- 新增 `tests/test_source_reconciliation.py` + fixture（正反例）——独立通道不被退出码基线覆盖，只能专项断言
- 全部行为改动做了回退验证（撤销 → 复现旧行为 → 恢复）

## 为什么这样做
见 ADR-029（分批实施）与 ADR-030（独立通道绕开闸机退出码缺陷）。

## 遇到问题
- `bump-version.py` 每次调用都推进版本号：连跑 5 次 `--add` 把版本推到 `2026-09-10-6`，手工改回 `-1`
- 造测试数据时暴露条款号格式差异（原文中文数字 vs JSON 阿拉伯数字）——不归一化会大量误报

## 未完成事项
- **合并回 master**（本次成果还在 worktree 分支 `worktree-new-table`）
- 漏洞2 主体（前置：统一上游 schema + 积累 design-assessments 实例）
- 漏洞3 主体（证据等级系统盖章）
- 闸机退出码缺陷修复（建议单独排期）
- 附带发现：`validate-policy-analysis.py` 的 traceability 检查不认 `source` 字段（真实产出最常用）
- 历史遗留：双项目升级 / R09 人工抽查 / N8 合规分级

## 下一步建议
1. 把本次改动合并回 master
2. 排期修闸机退出码语义（影响所有"只看不拦"的设计）
3. 漏洞2 主体之前，先做上游 schema 统一
