# 技术上下文
更新时间：2026-07-08

## 核心模块关系
```
internal-audit/
├── constitution.md           ← 全局硬约束 + 闸机规则（含 prompt_program_update）
├── CLAUDE.md                 ← 工具清单 + 规则说明
├── .claude/rules/            ← junction → D:\Nut\00_my_digital\12_AGI\rules\
├── _shared/scripts/          ← phase_gate.py + 5 个 validate-*.py + project_init.py + queries.py
├── audit-topics/             ← about-me.md + my-config.md（公司/系统配置）
├── [8 个 skill 目录]/        ← 各含 SKILL.md + references/
└── memory/                   ← 项目记忆（本目录）
```

## 8 个 Skill 流水线
```
project-init / topic-wizard  (Phase 0: 项目初始化)
        ↓
document-organizer           (Phase 1: 制度分析 → policy-analyses/ + design-assessments/)
        ↓
audit-interview-designer     (Phase 1.5: 访谈问卷 + 回填 → interview-materials/)
        ↓
program-generator            (Phase 2-3: 六轨道审计程序 → audit-programs/)
        ↓
execution-assistant          (Phase 4: 执行程序 → findings/)
        ↓ (可选)
finding-debate               (Phase 4.5: 攻防辩论)
        ↓
report-generator             (Phase 5: 汇总报告 → reports/)
evaluator (*): 各 skill Step 5 引用，质量评估框架
```

## 关键技术约束
- 状态传递：全部通过文件系统（JSON/Markdown），不通过内存
- current-audit.json：同时承载业务状态和审计执行状态，支持快照回滚
- 证据等级：A-E 五级，高风险 finding 必须有 A 或 E 级证据
- 制度分析：双通道并行（规则型关键词 + 流程型重建）
- 审计程序：六轨道按目的动态激活

## 技术决策摘要
- 选择多 skill 而非单体 agent（ADR-001）
- 选择六轨道动态激活而非模板套用（ADR-002）
- 选择区分"设计观察 vs 审计发现"（ADR-003）
- 选择优先架构修补再优化 skill（ADR-004）

## 当前活跃风险
1. 🔴 无阶段状态机——流程靠人工编排，Flan 是单点故障
2. 🔴 硬规则靠 LLM 记忆——"必须/禁止"约束没有代码兜底
3. 🟡 工具未按 phase 分域——LLM 可能调错 skill
4. 🟡 无可观测性——决策理由、证据链追溯不完整

## 用户长期目标
Flan 希望这套系统不只是他自己的辅助工具，而是能让他从"操作员"变成"审核员"——系统自己管流程，他只做关键决策。
