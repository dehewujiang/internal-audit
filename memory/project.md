# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态
⚠️ 架构评审完成，P0/P1/P2 改进项已识别，尚未执行。

## 已完成功能
- 8 个 skill 各自可以独立运作（document-organizer、interview-designer、program-generator、execution-assistant、finding-debate、report-generator、project-init、topic-wizard）
- evaluator 质量评估框架（各 skill Step 5 引用）
- 19 条 AI Agent 标准架构评审（2026-07-06）
- 母仓库 rules/ 通过 junction 链接到本项目 `.claude/rules/`
- Memory 系统就绪

## 正在开发
- 无（在评审和改进规划阶段）

## 最大风险
系统靠人工编排驱动流程——Flan 自己判断"现在该调哪个 skill"。没有阶段状态机。换人跑不起来。

## 下一步最重要任务
按优先级：
1. 🔴 P0：加轻量阶段状态机（50 行代码），管住阶段流转
2. 🔴 P0：把硬规则从 SKILL.md 抽出来写成 Python 校验脚本
3. 🟡 P1：按 phase 分域暴露 skill
4. 🟡 P1：建 5 个 eval case 给 program-generator

## 系统结构
- 核心仓库：`D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 规则来源：`.claude/rules/` → 通过 junction 链接 `D:\Nut\00_my_digital\12_AGI\rules\`
- 公司背景：`audit-topics/about-me.md` + `audit-topics/my-config.md`
- 工具脚本：`_shared/scripts/`（validate-finding.py 等）
- 审计项目：每个审计主题独立目录，输出到 `internal-audit-workspace/`

## 相关决策
见 decisions.md
