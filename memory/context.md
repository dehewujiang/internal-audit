# 技术上下文
更新时间：2026-08-06

## 核心模块关系

```
internal-audit/
├── CLAUDE.md                 ← 开发版（含 architecture gotchas, rules loading）
├── CLAUDE-project.md         ← 运行版（精简，setup-project.ps1 拷贝为审计项目 CLAUDE.md）
├── constitution.md           ← 14 条硬约束 + 阶段流转规则 + 启动协议（2026-08-06 恢复）
├── setup-project.ps1         ← 一键部署：扫描 .claude/skills/ 自动发现技能
├── update-project.ps1        ← 增量升级：逐技能合并而非整目录覆盖
├── .claude/
│   ├── skills/               ← 12 个技能（2 geb-* + 10 个审计 junction）
│   ├── settings.json         ← extraRules 配置
│   └── rules/                ← junction → D:\Nut\00_my_digital\12_AGI\rules\
├── _shared/scripts/          ← 核心脚本（phase_gate + 7 validate-* + queries + data_executor + audit_gate + check_mandatory_coverage + project_init + program_ir_parser + evidence_catalog + bump-version）
├── tools/                    ← pdf_ocr_extractor.py（PaddleOCR）+ 13 个能力声明
├── audit-topics/             ← 审计主题模板（人力资源管理、存货管理）
├── tests/prompt_snapshots/   ← 5 个 prompt 快照 + compare-snapshots 漂移检测 hook
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

## ProgramIR 体系（2026-08-06 已接入工作流，R04 闭环）

- `program_ir_parser.py` — 审计程序 Markdown → ProgramIR JSON（含 risk_register + coverage + uncovered_risks；兼容增量章节 S 编号与 -C 勘误后缀）
- `validate-program.py --ir` — 结构化校验模式（覆盖率<80%→block; 开关词/模糊词检查; 空数据源>30%→block）
- **接入点**：program-generator SKILL.md Step 4.5（解析→校验→激活轨道比对→修复闭环）；Step 3 有自检屏障一；Step 5 有前置声明

## 已发现的 9 项风险（2026-08-06 全部闭环，除 R09 实际抽查）

| ID | 风险 | 状态 |
|:---|:---|:---|
| R01 | cceer_standards.md A+B vs SKILL.md A+E 矛盾 | ✅ 统一 A+E（fa412dd） |
| R02 | 对抗验证 30%/50% 定量阈值丢失 | ✅ 补回（fa412dd） |
| R03 | 5/5 prompt 快照过期 | ✅ 重写对齐（26c511d） |
| R04 | ProgramIR 闸机未接入工作流 | ✅ Step 4.5 接入（fa143a4） |
| R05 | 缺 validate-catalog.py | ✅ 新建+挂接（fa143a4） |
| R06 | 缺 validate-index.py | ✅ 新建+挂接（fa143a4） |
| R07 | 风险→程序覆盖修复闭环缺失 | ✅ 三重屏障（fa143a4） |
| R08 | 缺 git pre-commit 快照对比 hook | ✅ compare-snapshots + hook（26c511d） |
| R09 | 缺端到端回归测试 | ⏳ 抽查清单已交付，实际抽查用户执行 |

## 新增治理（2026-08-06 批次）
- constitution 14 条硬约束（恢复 11-14：证据链/禁自行替代/必走技能/声明来源）+ 阶段流转规则 + 启动协议
- 三标准路径：`audit-topics/`（公司数据）、`_shared/scripts/`（脚本）、`.claude/skills/{skill}/`（跨技能）
- 知识库混源过滤：非制造业场景在 internal_audit_risk_framework 附录A / cheatsheet 附录B
- 制度版本强制：document_info.version/effective_date 必填（warn 级校验，存量兼容）

## 第四轮（2026-08-06 下午，VERSION 2026-08-06-4，已部署双项目）

- 审计程序模板新增「设计理由」「测试目的」两列（output_template.md 8 张表：6 轨道 + S1/S2 增量章节）；SKILL.md Step 4 两列必填要求 + 防套话约束 + 自检清单 2 项；program_templates.json 列宽补 30,30
- **模板表头对齐真实产出结构**（ADR-025）：8 表全部含「程序编号/判定标准/取证方式」列（解析器 `_is_program_table` 与闸机硬查要求）——修复模板与 Step 4.5 闸机的兼容矛盾（测试四连暴露）
- **Step 4.5 命令修正**：`validate-program.py --ir <path>` → `--ir --strict`（--ir 为布尔开关，实测）
- commits: 0746f5c / e133e2b / 26d4cc2 / 181000f / cd72e98

## 架构加固批次（2026-08-11，VERSION 2026-08-11-3，金源已提交、未部署现场）

- **C1 数据流总图**：根目录 `DATAFLOW.md`（六阶段 P0-P4 + 贯穿机制 + 断点观察：推理轨迹无落点 / design-assessments 读 4 次 / 证据缺失闭环待确认）
- **C2 宪法瘦身**：constitution.md ≤85 行，14 条语义零丢失 + 触发指针（tools/tool-exhaustion.md、CLAUDE-project.md「启动协议」、incremental_update.md、phase_gate.py）；CLAUDE-project.md 漂移修复（"10 hard"→实际条数）+ check_mandatory_coverage 命令补登记
- **C3 纳米测试**：ADR-026（新增规则/脚本前自问三问）+ OPS.md 检查清单
- **C4 R09 回归用例**：`tests/fixtures/regression/p2026-001-hr/`（input policy-analysis+audit-program / expected_output validate 输出 / README 脱敏映射；findings 待项目完成后补）
- **C6 推理日志试点**：`phase_gate.py` 新增 `log-decision --scene --decision --basis` 子命令 → append_audit_trail 写 event_type="decision"（detail 格式 `{场景}:{决策}:{依据}`）；finding 复用已有 `decision_rationale` 对象新增子键 `risk_level_reason`（validate-finding.py [DR] 校验 warn 级、仅高风险触发）；audit_gate `_log_to_trail`（{event,source} schema）保持不动——两套 schema 并存（REASON-LOG.md 记录，铺开阶段统一）；`queries.py decide` 读已有子键不受影响；铺开条件 = 跑 1 个真实审计后评估
- **C7 最小必要上下文**：根目录 `INPUT-BUDGET.md`（7 skill 输入清单 + 裁剪规则，两档：文件级/字段级）；SKILL.md 读取指令改静态过滤（grep 禁"你认为/根据需要"）；execution-assistant 读 design-assessments 按**验证状态**过滤（严禁按 source——两种来源都需验证，宪法 #9/#13）；全量读仅限当前阶段产物；制度文件（P1）禁止裁剪
- **追加机制**：SKILL.md 变更自动检测——`tests/prompt_snapshots/regression-check.py` + pre-commit.hook（影响卡片引导 + RED 拦截），回应 C7 改 SKILL.md 暴露的快照闸机缺口

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
