# 技术上下文
更新时间：2026-09-11

**本文件是系统的技术快照**——只写"现在是什么样"。历史批次（为什么改、怎么改的）见 `decisions.md` 的 ADR 与 git log。

## 核心模块关系

```
internal-audit/
├── CLAUDE.md                 ← 开发版（含 architecture gotchas, rules loading）
├── CLAUDE-project.md         ← 运行版（精简，setup-project.ps1 拷贝为审计项目 CLAUDE.md）
├── constitution.md           ← 14 条硬约束 + 阶段流转规则 + 启动协议
├── setup-project.ps1         ← 一键部署：扫描仓库根（含 SKILL.md 的目录即技能）自动发现
├── update-project.ps1        ← 增量升级：逐技能合并而非整目录覆盖
├── .claude/
│   ├── skills/               ← 2 个 geb 原生真身 + 10 个审计技能 junction 门牌（非取货点，见 ADR-027）
│   └── settings.json
│   （注意：.claude/rules/ 已于 2026-09-11 移除——规则统一由 ~/.claude/rules/ 提供，见下）
├── _shared/scripts/          ← phase_gate + validate-* ×8 + queries + data_executor + audit_gate
│                                + check_mandatory_coverage + project_init + program_ir_parser
│                                + evidence_catalog + bump-version
├── ledger/                   ← 新桌子（见下）
├── tools/                    ← pdf_ocr_extractor.py（PaddleOCR）+ 13 个能力声明
├── audit-topics/             ← 审计主题模板（人力资源管理、存货管理）
├── tests/prompt_snapshots/   ← 5 个 prompt 快照 + compare-snapshots 漂移检测 hook
├── tests/fixtures/           ← 回归用例（regression / source_reconciliation / gate_tiers）
├── [10 个 skill 目录]/        ← 各含 SKILL.md + references/
└── memory/                   ← 项目记忆（本目录）
```

## 规则体系（2026-09-11 定型）

- **唯一来源**：`D:\Nut\00_my_digital\12_AGI\rules\`（8 份），经 `~/.claude/rules/agi` 符号链接对所有项目生效。**项目级不再保存副本**——改源即全局生效
- **加载方式由各文件头部的 `paths` 决定**：
  - 常驻（无 paths）：`work-principles.md`、`memory_rules.md`
  - 按需（有 paths）：`coding-safety.md`（源码文件）、`good-taste.md`、`geb-l3.md`、`project-doctrine.md`（源码文件）、`compat.md`（api/interface/public）、`memory-templates.md`（假路径，几乎不加载）
- **裁决表位置**：规则冲突时的优先级见 `~/.claude/CLAUDE.md`〈规则冲突裁决〉（2026-09-11 从 project-doctrine 迁入，因该文件改为按需加载）
- **`~/.claude/` 已纳入版本控制**（含 CLAUDE.md、settings.json、hooks、plans）

## 闸机体系

```
流程闸机:  phase_gate check/advance          → exit 0/1/2（阶段转换）
质量闸机:  validate-*.py                      → exit 0/1/2（产物校验）
授权闸机:  phase_gate tool-check <script>     → exit 0/1（工具分域）
调度闸机:  audit_gate precheck/postcheck       → exit 0/1（LLM 推理前后硬闸机）
```

**退出码语义（2026-09-10 统一）**：校验脚本 `0=通过 / 1=警告 / ≥2=阻断`；调度闸机认三档——`0` 放行、`1` 打印警告后放行、`≥2` 拦下。

**已知缺口**：`audit_gate.py` 调用 `validate-program.py` 时**从不传 `--ir`**，导致"覆盖率 / 判定标准 / 数据来源"三类阻断从未生效（文档却写着应传）。属待排期的"加严"项。

**两个易忘约束（已固化进 `ACTIONS[...]["args"]`）**：
- `validate-interview.py` **必须传** `--strict`——它非 strict 时无论成败都返回 0，闸机会永远放行
- `validate-report.py` / `validate-program.py` **刻意不传** `--strict`——它们的 strict 分支把"阻断"也映射成退出码 1，闸机将无法与"警告"区分

**崩溃兜底**：五个校验脚本入口均有 `try/except → exit(2)`，防止"脚本挂了"（Python 默认返回 1）被误判成"有警告"放行。

## 新桌子 ledger

```
ledger/
├── ledger.py        ← 管家：create/set-slot/add-evidence/link-finding/add-line/snaps/rollback/import（写前拍照留20张）
├── check.py         ← 日常门卫：三格有字/红格对号提醒/证据来源/抽屉 + --workspace 查高风险A/E硬度
├── checklist.py     ← 打勾纸：六句话看板，只读 workspace，exit 永远0
├── audit_table.py   ← 报告前闸机：单缺位/鬼号/红格无号 → exit 2
├── export.py        ← 总览表格：左边/证据/抽屉三页（复用 excel_core）
└── ledger.schema.json (v1.0) / README.md / examples/冲压车间.json
```

- **五家接法**（各 SKILL 只增行）：organizer→信号格 add-line / interview→信号格+证据 / execution→import 单张 / debate→set-slot 改字 / report→Step 2b 跑 audit_table.py；program-generator 未接（产出即抽屉检查表，约定即接口）
- **四根线**：写 / 读 / 拍照（20 张滚动+回头）/ 老账 + 高风险硬度（须 A/E 级证据）
- `phase_gate.py` 新增 `checklist` 子命令（转调 `ledger/checklist.py`）
- 设计原则（ADR-028）：**加法不减法**——只拦丢东西，不管顺序格式

## 技能注册架构（见 ADR-027）

- **唯一来源**：仓库根本身的 10 个技能目录——含 SKILL.md 的根目录即被视为可部署技能
- **门牌角色**：`.claude/skills/` 内 10 个审计技能为 junction 门牌，仅服务 AI 工具发现；**没有任何脚本把它当取货点读**——被清空只影响发现能力，一条重建命令即恢复
- geb-bootstrap / geb-workflow 以原生目录保留于 `.claude/skills/`（开发环境专用，不随项目部署）
- setup 和 update 都按 SKILL.md 标记扫根目录读取技能列表

## ProgramIR 体系

- `program_ir_parser.py` — 审计程序 Markdown → ProgramIR JSON（含 risk_register + coverage + uncovered_risks；兼容增量章节 S 编号与 -C 勘误后缀）
- `validate-program.py --ir` — 结构化校验模式（覆盖率 <80% → block；开关词/模糊词检查；空数据源 >30% → block）
- **接入点**：program-generator SKILL.md Step 4.5（解析→校验→激活轨道比对→修复闭环）
- **注意**：解析器收集《风险识别清单》时须收全 2.1.1~2.1.5 五张表（曾因 `break` 只读首表，覆盖率分母残缺）

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

## 三标准路径与制度治理

- **三标准路径**：`audit-topics/`（公司数据）、`_shared/scripts/`（脚本）、`.claude/skills/{skill}/`（跨技能）
- **制度版本强制**：`document_info.version` / `effective_date` 必填（warn 级校验，存量兼容）
- **知识库混源过滤**：非制造业场景在 `internal_audit_risk_framework` 附录A / `cheatsheet` 附录B
- **推理日志**（试点）：`phase_gate.py log-decision --scene --decision --basis` → audit_trail；finding 的 `decision_rationale.risk_level_reason`（warn 级、仅高风险触发）。铺开条件 = 跑 1 个真实审计后评估

## 关键技术约束

- 状态传递：全部通过文件系统，不通过内存
- finding schema 1.2.0（扁平结构：title / risk_level / origin / evidence[]）
- 证据等级 A-E 五级，高风险 finding 必须 A 或 E
- 项目命名：`project_name` 必须等于项目文件夹名
- `data_executor` 安全：import 白名单（仅 pandas/numpy）+ threading.Timer 超时
- **业务规则只写"为什么"**（本文件与 decisions.md）；"改了什么"交给 git

## 已部署项目

| ID | 项目 | 主题 | 阶段 |
|:---:|------|------|------|
| P-2026-001 | 武汉长源 | 人力资源管理 | phase_3_execution |
| P-2026-002 | 广东长华 | 人力资源管理 | phase_2_program_generation |

## 用户长期目标
Flan 从"操作员"变成"审核员"——系统自己管流程，他只做关键决策。
