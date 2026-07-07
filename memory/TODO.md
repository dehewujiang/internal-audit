# TODO

## #进行中
- 无

## #待办
- 更新各 SKILL.md 的 Step 5 引用新的 validate 脚本和 program-quality-evaluator
- 更新 report-generator SKILL.md 删除"功能1：管理审计发现"
- 🟢 P2：为关键决策点（风险评级、finding 定级）加决策理由记录
- 🟢 P2：模型分级——制度分析用便宜模型，辩论用强模型
- 🔵 P3：每个 skill 返回结构化摘要给 LLM 做下一步决策
- 🟡 P2：queries.py 全文搜索 finding 正文
- 🟢 P3：queries.py 制度分析查询
- 🟢 P3：queries.py 跨实体追溯

## #阻塞
- 无

## #已完成（2026-07-07）
- 🔴 P0-1：加轻量阶段状态机（phase_gate.py）✅
- 🔴 P0-2：硬规则代码化（validate-program.py, validate-policy-analysis.py, validate-report.py）✅
- 🟡 P1-1：按 phase 分域暴露 skill（CLAUDE.md + constitution.md 更新）✅
- 🔴 queries.py 重构：从 evaluator 搬到 _shared/scripts/，升格为独立查询工具 ✅
- 🔴 program-quality-evaluator 新增：四层评估体系 ✅
- 🟡 P1-2：建 5 个 eval cases + run_evals.py ✅
- 🔴 启动协议：constitution.md 新增启动协议节 ✅
