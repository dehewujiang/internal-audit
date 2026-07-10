# 技术上下文
更新时间：2026-07-10

## 核心模块关系

```
internal-audit/
├── CLAUDE.md                 ← 开发版（含 architecture gotchas, rules loading）
├── CLAUDE-project.md         ← 运行版（精简，setup-project.ps1 拷贝为审计项目 CLAUDE.md）
├── constitution.md           ← 全局硬约束 + 闸机规则
├── setup-project.ps1         ← 一键部署：junction(skills/_shared_/tools_) + copy + mkdir + 自检
├── .claude/rules/            ← junction → D:\Nut\00_my_digital\12_AGI\rules\
├── _shared/scripts/          ← phase_gate + 5 个 validate-* + project_init + queries
├── tools/                    ← pdf_ocr_extractor.py + 13 个能力声明
├── audit-topics/             ← 审计主题模板
├── [10 个 skill 目录]/        ← 各含 SKILL.md + references/
└── memory/                   ← 项目记忆（本目录）
```

## 三重闸机体系

```
流程闸机:  phase_gate check/advance          → exit 0/1/2（阶段转换）
质量闸机:  validate-*.py --strict             → exit 0/1（产物校验）
授权闸机:  phase_gate tool-check <script>     → exit 0/1（工具分域）
```

## 10 个 Skill 流水线（+ 2 evaluators）

```
project-init / topic-wizard  (Phase 0)
document-organizer           (Phase 1 → policy-analyses/ + design-assessments/)
audit-interview-designer     (Phase 1.5 → interview-materials/)
program-generator            (Phase 2-3 → audit-programs/)
execution-assistant          (Phase 4 → findings/)
finding-debate               (Phase 4.5, 可选)
report-generator             (Phase 5 → reports/)
evaluator (*): quality_gate + record_evaluation
program-quality-evaluator: 四层评估（program-generator Step 5.7 独有）
```

## 关键技术约束
- 状态传递：全部通过文件系统，不通过内存
- 工具分域：每个 Python 脚本调用前必须过 phase_gate tool-check
- current-audit.json：业务状态 + 审计执行状态 + 快照回滚
- 证据等级：A-E 五级，高风险 finding 必须 A 或 E
- 部署：setup-project.ps1 一键初始化审计项目（junction + copy + mkdir + 自检）
- 双 CLADE.md：开发版（CLAUDE.md，含架构细节）、运行版（CLAUDE-project.md，砍掉噪音）

## 当前活跃风险
1. 🟢 ~~🔴 无阶段状态机~~ — 已修复
2. 🟢 ~~🔴 硬规则靠 LLM 记忆~~ — 已修复
3. 🟢 ~~🟡 工具未按 phase 分域~~ — 已修复（tool-check + 三级白名单）
4. 🟡 无可观测性——决策追溯体系未建设
5. 🟢 ~~🟡 document-organizer 跨段落隐含控制~~ — 已修复（两遍法）
6. 🟡 document-organizer 输出一致性——同份文档两次分析结果可能不同

## 用户长期目标
Flan 从"操作员"变成"审核员"——系统自己管流程，他只做关键决策。
