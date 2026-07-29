# 技术上下文
更新时间：2026-07-29

## 核心模块关系

```
internal-audit/
├── CLAUDE.md                 ← 开发版（含 architecture gotchas, rules loading）
├── CLAUDE-project.md         ← 运行版（精简，setup-project.ps1 拷贝为审计项目 CLAUDE.md）
├── constitution.md           ← 10 条全局硬约束
├── setup-project.ps1         ← 一键部署：扫描 .claude/skills/ 自动发现技能
├── update-project.ps1        ← 增量升级：逐技能合并而非整目录覆盖
├── .claude/
│   ├── skills/               ← 12 个技能（2 geb-* + 10 个审计 junction）
│   ├── settings.json         ← extraRules 配置
│   └── rules/                ← junction → D:\Nut\00_my_digital\12_AGI\rules\
├── _shared/scripts/          ← 核心脚本（phase_gate + 5 validate-* + queries + data_executor + audit_gate + check_mandatory_coverage + project_init + program_ir_parser + evidence_catalog + bump-version）
├── tools/                    ← pdf_ocr_extractor.py（PaddleOCR）+ 13 个能力声明
├── audit-topics/             ← 审计主题模板（人力资源管理、存货管理）
├── tests/prompt_snapshots/   ← 5 个 prompt 快照 + 回归测试指南
├── [10 个 skill 目录]/        ← 各含 SKILL.md + references/
└── memory/                   ← 项目记忆（本目录）
```

## 技能注册架构（2026-07-14 修复）

- **唯一来源**：`.claude/skills/` — 仓库根目录的 10 个审计技能通过 junction 映射于此
- **部署一致性**：setup 和 update 都从 `.claude/skills/` 读取技能列表

## 四重闸机体系

```
流程闸机:  phase_gate check/advance          → exit 0/1/2（阶段转换）
质量闸机:  validate-*.py                      → exit 0/1（产物校验）
授权闸机:  phase_gate tool-check <script>     → exit 0/1（工具分域）
调度闸机:  audit_gate precheck/postcheck       → exit 0/1（LLM 推理前后硬闸机）
```

## ProgramIR 体系（覆盖度校验基础设施，已存在但未接入工作流）

- `program_ir_parser.py` — 审计程序 Markdown → ProgramIR JSON（含 risk_register + coverage + uncovered_risks）
- `validate-program.py --ir` — 结构化校验模式（check_ir_coverage_rate: 覆盖率<80%→block; check_ir_criterion: 开关词/模糊词检查; check_ir_data_source: 空数据源>30%→block）
- **缺口**：program-generator SKILL.md 的 Step 5 是纯 LLM 推理检查，不调用上述脚本。需在 Step 4 和 Step 5 之间插入 Step 4.5 调用脚本闸机。

## 已发现的 9 项风险（2026-07-29）

| ID | 风险 | 状态 |
|:---|:---|:---|
| R01 | cceer_standards.md A+B vs SKILL.md A+E 矛盾 | 待修 |
| R02 | 对抗验证 30%/50% 定量阈值丢失 | 待修 |
| R03 | 5/5 prompt 快照过期（2 确认漂移，3 待逐份对比） | 待修 |
| R04 | ProgramIR 闸机未接入工作流 | 待修 |
| R05 | 缺 validate-catalog.py | 待修 |
| R06 | 缺 validate-index.py | 待修 |
| R07 | 风险→程序覆盖修复闭环缺失 | 待修（随 R04） |
| R08 | 缺 git pre-commit 快照对比 hook | 待修（依赖 R03） |
| R09 | 缺端到端回归测试 | 待修 |

## 10 个 Skill 流水线

```
project-init / topic-wizard  (Phase 0)
document-organizer           (Phase 1 → policy-analyses/ + design-assessments/)
audit-interview-designer     (Phase 1.5 → interview-materials/)
program-generator            (Phase 2-3 → audit-programs/)
execution-assistant          (Phase 3 → findings/)
finding-debate               (Phase 3.5, 可选)
report-generator             (Phase 4 → reports/)
```

## 关键技术约束
- 状态传递：全部通过文件系统，不通过内存
- finding schema 1.2.0（扁平结构：title/risk_level/origin/evidence[]）
- 证据等级 A-E 五级，高风险 finding 必须 A 或 E
- 项目命名：project_name 必须等于项目文件夹名
- data_executor 安全：import 白名单（仅 pandas/numpy）+ threading.Timer 超时

## 已部署项目
| ID | 项目 | 主题 | 阶段 |
|:---:|------|------|------|
| P-2026-001 | 武汉长源 | 人力资源管理 | phase_3_execution |
| P-2026-002 | 广东长华 | 人力资源管理 | phase_2_program_generation |

## 用户长期目标
Flan 从"操作员"变成"审核员"——系统自己管流程，他只做关键决策。
