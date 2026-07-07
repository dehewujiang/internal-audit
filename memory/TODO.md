# TODO

## #进行中
- 无

## #待办
- 无

## #搁置
- 🟢 P2：模型分级——制度分析用便宜模型，辩论用强模型。已搁置（2026-07-07）：当前架构下 Skill 工具不支持 model 参数，且单人使用 token 成本可控。待以下条件满足后重新评估：(1) 多人协作上线，成本上升；(2) Claude Code 支持 skill 级 model 覆盖。
- 🔵 P3：每个 skill 返回结构化摘要给 LLM 做下一步决策。已搁置（2026-07-07）：单人使用每次省 30 秒翻文件，ROI 极低。待团队化或高频使用（>5 项目/天）后重新评估。

## #阻塞
- 无

## #已完成（2026-07-07）
- 🔴 P0-1：加轻量阶段状态机（phase_gate.py）
- 🔴 P0-2：硬规则代码化（validate-program.py, validate-policy-analysis.py, validate-report.py）
- 🟡 P1-1：按 phase 分域暴露 skill（CLAUDE.md + constitution.md 更新）
- 🔴 queries.py 重构：从 evaluator 搬到 _shared/scripts/，升格为独立查询工具
- 🔴 program-quality-evaluator 新增：四层评估体系
- 🟡 P1-2：建 5 个 eval cases + run_evals.py
- 🔴 启动协议：constitution.md 新增启动协议节
- 更新各 SKILL.md Step 5 引用新的 validate 脚本和 program-quality-evaluator
- 更新 report-generator SKILL.md 删除「功能1：管理审计发现」
- 🟢 P2：为关键决策点（风险评级、finding 定级）加决策理由记录（decision_rationale）
- 🟡 P2：queries.py 全文搜索 finding 正文（search 子命令，递归搜索所有 JSON 字段）
- 🟢 P3：queries.py 制度分析查询（analyses 子命令）
- 🟢 P3：queries.py 跨实体追溯（trace 子命令：finding ↔ design observation ↔ control point）
