# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态
✅ 全部架构改进任务完成（2026-07-07），TODO 已清空。下次可按需新增任务或跑端到端测试。

## 已完成功能
- 8 个 skill 各自可以独立运作（document-organizer、interview-designer、program-generator、execution-assistant、finding-debate、report-generator、project-init、topic-wizard）
- evaluator 质量评估框架（各 skill Step 5 引用）
- 19 条 AI Agent 标准架构评审（2026-07-06，综合 3.2/5）
- 母仓库 rules/ 通过 junction 链接到本项目 `.claude/rules/`
- Memory 系统就绪
- **P0-1**: phase_gate.py 阶段状态机（地铁闸机模型），6 阶段流转 + 前进/回退/快照
- **P0-2**: 3 个 validate 脚本（validate-program.py, validate-policy-analysis.py, validate-report.py）
- **P1-1**: CLAUDE.md 工具清单新增 phases 字段，按阶段分域暴露 skill
- **queries.py**: 从 evaluator 搬到 _shared/scripts/，升格为独立查询工具
- **program-quality-evaluator**: 四层评估体系（覆盖度+检测力+可执行性+防绕过）
- **P1-2**: 5 个 eval cases + run_evals.py 运行器
- **启动协议**: constitution.md 新增每次对话开始必须执行的启动流程

## 正在开发
- 各 SKILL.md 的 Step 5 引用新的 validate 脚本和 program-quality-evaluator
- report-generator SKILL.md 删除"功能1：管理审计发现"

## 最大风险
SKILL.md 的 Step 5 尚未引用新的 validate 脚本和 program-quality-evaluator——LLM 不知道这些工具存在。

## 下一步
1. 更新各 SKILL.md 的 Step 5 引用新的 validate 脚本
2. 更新 report-generator SKILL.md 删除"功能1：管理审计发现"
3. commit 全部变更

## 系统结构
- 核心仓库：`D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 规则来源：`.claude/rules/` → 通过 junction 链接 `D:\Nut\00_my_digital\12_AGI\rules\`
- 公司背景：`audit-topics/about-me.md` + `audit-topics/my-config.md`
- 工具脚本：`_shared/scripts/`（validate-finding.py, validate-program.py, validate-policy-analysis.py, validate-report.py, phase_gate.py, queries.py）
- 程序质量评估：`program-quality-evaluator/SKILL.md`
- 审计项目：每个审计主题独立目录，输出到 `internal-audit-workspace/`

## 相关决策
见 decisions.md
