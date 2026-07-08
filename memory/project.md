# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态
✅ 核心架构改进完成（2026-07-07），Step 5 validate 脚本大部分已接入。两个遗留缺口（finding-debate 缺 Step 5、interview-designer 缺校验脚本）属设计空白，非遗漏。
⚠️ 今天（2026-07-08）改了 program-generator 的 3 个 references，扩展 RP/CF 编号跨引用，尚未 commit。

## 已完成功能
- 8 个 skill 各自可以独立运作（document-organizer、interview-designer、program-generator、execution-assistant、finding-debate、report-generator、project-init、topic-wizard）
- evaluator 质量评估框架（各 skill Step 5 引用）
- 19 条 AI Agent 标准架构评审（2026-07-06，综合 3.2/5）
- 母仓库 rules/ 通过 junction 链接到本项目 `.claude/rules/`
- Memory 系统就绪
- **P0-1**: phase_gate.py 阶段状态机（地铁闸机模型），6 阶段流转 + 前进/回退/快照
- **P0-2**: 4 个 validate 脚本（validate-program.py, validate-policy-analysis.py, validate-report.py, validate-finding.py）
- **P1-1**: CLAUDE.md 工具清单新增 phases 字段，按阶段分域暴露 skill
- **queries.py**: 从 evaluator 搬到 _shared/scripts/，升格为独立查询工具
- **program-quality-evaluator**: 四层评估体系（覆盖度+检测力+可执行性+防绕过）
- **P1-2**: 5 个 eval cases + run_evals.py 运行器
- **启动协议**: constitution.md 新增每次对话开始必须执行的启动流程
- **Step 5 validate 接入**（2026-07-07）：document-organizer ✅ / program-generator ✅ / execution-assistant ✅ / report-generator ✅
- **report-generator 重构**（2026-07-07）：删除"功能1：管理审计发现"，职责迁至 queries.py
- **RP/CF 编号跨引用**（2026-07-08）：program-generator 来源标注支持制度分析全部四类 ID（CP/CG/RP/CF）

## 正在开发
- （无）

## 已知缺口（非阻塞）
| 缺口 | 说明 |
|------|------|
| finding-debate 缺 Step 5 | 无质量评估步骤，无 validate 引用。可引用 internal-audit-evaluator 的 finding 检查清单 + validate-finding.py |
| interview-designer 缺校验脚本 | 无对应的 validate-interview.py，Step 5 只有软性检查无硬校验 |

## 最大风险
🟡 finding-debate 和 interview-designer 缺少格式硬校验兜底——输出质量依赖 LLM 自觉，无代码保证。

## 下一步
1. commit 今天的 RP/CF 跨引用变更（3 个 references 文件）
2. （可选）为 finding-debate 补 Step 5
3. （可选）为 interview-designer 写 validate-interview.py
4. 跑一次端到端测试验证流水线

## 系统结构
- 核心仓库：`D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 规则来源：`.claude/rules/` → 通过 junction 链接 `D:\Nut\00_my_digital\12_AGI\rules\`
- 公司背景：`audit-topics/about-me.md` + `audit-topics/my-config.md`
- 工具脚本：`_shared/scripts/`（validate-finding.py, validate-program.py, validate-policy-analysis.py, validate-report.py, phase_gate.py, queries.py）
- 程序质量评估：`program-quality-evaluator/SKILL.md`
- 审计项目：每个审计主题独立目录，输出到 `internal-audit-workspace/`

## 相关决策
见 decisions.md
