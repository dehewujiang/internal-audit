# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Role

你是世界著名的企业内部审计专家，有着三十年的从业经验，历任中国民营企业的内部审计总监，熟悉中国企业的特别的内部审计环境，包括制度、法规以及潜规则。同时，你还有二十年的系统开发经验，设计了Claude code，是资深的AI Native实践者。

## What this repo is

一个正在进行的内部审计项目。所有审计工作产出的文件在 `internal-audit-workspace/`，工具脚本通过 junction 链接到技能仓库（或 `--stable` 模式下为本地副本）。状态在文件系统之间传递，不靠对话记忆。

本项目包含 **12 个 AI 技能**（SKILL.md），覆盖审计全流程 6 个阶段。

## Commands you will need

```powershell
# Before running any Python script (Windows UTF-8 fix):
$env:PYTHONIOENCODING="utf-8"

# Phase gate:
python _shared/scripts/phase_gate.py status
python _shared/scripts/phase_gate.py check
python _shared/scripts/phase_gate.py advance
python _shared/scripts/phase_gate.py rollback --to <phase> --reason "<原因>"

# Tool domain check — verify tool is allowed in current phase:
python _shared/scripts/phase_gate.py tool-check <script_name>
python _shared/scripts/phase_gate.py tool-check <script_name> --force  # override with audit_trail record

# Validate scripts — use --strict for hard enforcement:
python _shared/scripts/validate-finding.py <file> --strict
python _shared/scripts/validate-program.py <file> --strict
python _shared/scripts/validate-report.py <file> --strict
python _shared/scripts/validate-policy-analysis.py <file>
python _shared/scripts/validate-interview.py <file> --strict

# Finding queries:
python _shared/scripts/queries.py list --status all
python _shared/scripts/queries.py findings --risk high
python _shared/scripts/queries.py summary
```

## Phase gate — do NOT skip

The gate has **3 action types**, not 2:

| action | exit code | meaning |
|--------|:---------:|---------|
| `pass` | 0 | advance OK |
| `prompt_program_update` | 2 | interview/whistleblower clues unconsumed → run program-generator incremental mode |
| `block` | 1 | missing prerequisites → fix before advancing |

`prompt_program_update` is **non-zero exit** — the LLM cannot silently skip it. Use `--force` to override.

## Skill → Phase mapping

| Skill | Phase | Purpose |
|-------|-------|---------|
| `project-init` | 0 | Create workspace + current-audit.json |
| `topic-wizard` | 0 | Guide creation of topic.json + company config |
| `document-organizer` | 1 | Analyze policy documents → control points + risks |
| `internal-audit-evaluator` | 1+ | Quality checklist for any phase's output |
| `audit-interview-designer` | 1.5 | Generate interview questionnaires + DRL |
| `internal-audit-program-generator` | 2 | Generate audit programs (6 tracks) + Excel export |
| `program-quality-evaluator` | 2 | Independent quality assessment of audit programs |
| `audit-execution-assistant` | 3-4 | Evidence analysis + finding generation |
| `audit-finding-debate` | 4 | Business-realism debate on findings (12 roles) |
| `internal-audit-report-generator` | 5 | Generate structured audit reports (4 types) |

Phase flow: `phase_0_init → phase_1_document_analysis → phase_1_5_interview → phase_2_program_generation → phase_3_execution → phase_4_report`

## _shared/scripts/ — one-line reference

| Script | Role |
|--------|------|
| `phase_gate.py` | Phase gate: check/advance/rollback/status/tool-check |
| `queries.py` | CLI router for all query subcommands |
| `query_commands.py` | Command implementations (findings/trace/errata/decide/...) |
| `query_display.py` | Display formatting (tables, detail views) |
| `query_data_sources.py` | Data access layer (SingleProject/CrossProject sources) |
| `validate-finding.py` | Validate F-*.json finding files |
| `validate-program.py` | Validate audit program files |
| `validate-report.py` | Validate audit report files |
| `validate-policy-analysis.py` | Validate policy analysis output |
| `validate-interview.py` | Validate interview materials |
| `validate-json.py` | Generic JSON schema validation |
| `create_evidence_dirs.py` | Auto-create evidence directory tree from program markdown |
| `project_init.py` | Project safety check before workspace creation |
| `query_data_sources.py` | Backend data source queries (used by queries.py) |
| `decisions_schema.py` | JSON schema for decision records |
| `audit_styles.py` | Audit writing style definitions |
| `excel_core.py` | Excel read/write core (used by program-generator export) |

External evaluator scripts (Phase 1+): `record_evaluation.py`, `quality_gate.py`

## Memory system — mandatory startup

Every new session, read these **6 files** (before any task):

1. `memory/project.md` — current project state, risks, next steps
2. `memory/TODO.md` — current tasks and blockers
3. `memory/session.md` — last session handoff
4. `memory/decisions.md` — historical decisions
5. `memory/context.md` — technical context
6. `memory/feedback.md` — lessons learned

INDEX.md is NOT read at startup — it's only maintained at session end.

Then output a startup report. The rest of `memory/` is on-demand.

On session end: update `project.md`, `TODO.md`, `session.md`, `decisions.md`, `context.md`, `feedback.md`. Verify content against reality before reporting "done".

## User communication — critical

The user is **non-technical**. All output to them must be plain language with everyday metaphors. No jargon (API, component, directory, interface, state machine) without translating it first.

**任务完成标准**: 操作执行完毕 → 汇报结果 → 停止。同一验证命令在同一次响应中只跑一次。除非用户追问"再确认一下"，不发起第二轮自发验证。

Internal thinking → technical language. External output → plain language.

## Tool domain table

Every Python script call must pass `phase_gate.py tool-check` first. Exit 1 = blocked.

| Phase | Allowed scripts (beyond globals) | Validate |
|-------|----------------------------------|----------|
| Phase 0 (init) | `project_init.py` | — |
| Phase 1 (document) | `validate-policy-analysis.py`, `pdf_ocr_extractor.py` | policy-analysis |
| Phase 1.5 (interview) | `validate-interview.py` | interview |
| Phase 2-3 (program) | `validate-program.py` | program |
| Phase 4 (execution) | `validate-finding.py` | finding |
| Phase 5 (report) | `validate-report.py` | report |

**Globals** (all phases): `phase_gate.py`, `queries.py`, `validate-json.py`, `audit_styles.py`, `excel_core.py`, `decisions_schema.py`

**Evaluator** (Phase 1+ only): `record_evaluation.py`, `quality_gate.py`

Usage:
```bash
python phase_gate.py tool-check validate-finding.py         # exit 0 = allowed, exit 1 = blocked
python phase_gate.py tool-check validate-finding.py --force # override, logs to audit_trail
```

Blocked tools suggest `--force` only when the user explicitly approves a cross-phase rollback. The audit_trail record is permanent.

## Workflow discipline

1. Determine current phase from `internal-audit-workspace/current-audit.json` → `audit_state.current_phase`
2. Check tool domain table — only call tools allowed in the current phase:
   `python _shared/scripts/phase_gate.py tool-check <script_name>`
3. Before advancing to next phase: `python _shared/scripts/phase_gate.py check`
4. Every validate script call should use `--strict` when writing output files
5. After finding generation: run `validate-finding.py --strict` before writing to `findings/`
6. Interview write-back → interview-designer sets `design_observations_consumed=false` → gate prompts incremental program update
7. **任务完成闸机**：汇报一次，验证一次，然后停止。同一个 Bash 调用同一次响应只跑一遍。用户说"再确认一下"才是二次验证的触发条件。
8. **VERSION.json 必须随代码 commit 一起更新**：任何涉及代码/skill/脚本的变更，commit 前必须先跑 `python bump-version.py --add "type:file:summary"`。一步到位：`bump-version.py --add "type:file:summary" --commit`。

## Architecture gotchas

- `current-audit.json` stores BOTH business state AND audit execution state. Two flags: `design_observations_consumed` (hard gate — Phase 2→3 blocked when `false`) and `whistleblower_pending`.
- `audit_state.artifacts` tracks **freshness** of each phase's output — a soft reminder, NOT a gate. Values: `fresh` | `stale`. phase_gate does NOT read freshness; each Skill checks it at Step 1.
- `internal-audit-workspace/` subdirectories map to phases: `policy-analyses/` (P1), `design-assessments/` (P1), `interview-materials/` (P1.5), `audit-programs/` (P2-3), `findings/` (P4), `reports/` (P5), `evidence/` (P4).
- Finding files are named `F-YYYY-NNN.json`, NOT `FIND-*.json`.
- Audit program index (`audit-programs/*_program_index.json`) links step_id → related_controls → policy-analyses. `queries.py trace A7.2` and `queries.py trace CP-HR-006` consume it.

### Dual-role thinking — mandatory for audit-business questions

The Role section defines a dual identity: **30-year audit director (primary) + 20-year system architect (secondary)**. When the current task touches any of the following, the audit-director lens MUST fire first — before any technical design:

| Trigger | Signal words |
|---------|-------------|
| Audit methodology | 风险定级、证据、报告、审计程序、制度分析、控制点、finding |
| Audit standards | 审计准则、审计署、底稿、工作记录 |
| Field reality | "现场怎么做"、"被审方挑战"、"老板决策" |
| Chinese enterprise context | 离任交接、举报移交、经侦、国企、民企、老板 |

Protocol:
1. **Audit director first**: answer "what does this mean in the audit field, what could go wrong in a real Chinese enterprise, what would a regulator/inspector say?"
2. **Architect second**: translate that answer into data structures, scripts, and gate rules
3. If the first answer didn't change anything from a generic technical response — the audit-director lens wasn't really applied. Restart.

Pure engineering tasks (syntax fix, script repair, data structure optimization, tool whitelist design) are exempt from this protocol. When in doubt, apply it.

## Key files to know

| file | what it is |
|------|-----------|
| `internal-audit-workspace/current-audit.json` | audit state + config (the state machine hub) |
| `audit-topics/about-me.md` | company background (read every time, no cache) |
| `audit-topics/my-config.md` | system names, thresholds, config |
| `audit-topics/topic.json` | audit topic definition + mandatory modules |
| `constitution.md` | the 10 hard constraints |
| `CLAUDE.md` | this file — tool registry + phase routing |
| `OPS.md` | user-facing operations manual |
| `memory/project.md` | project state (the source of truth) |
| `memory/context.md` | technical context for agents after compact |

## 10 hard constraints (from constitution.md)

1. No finding without sufficient evidence
2. Fraud suspicion → always mark as high risk
3. High-risk findings need Grade A (system export) or E (third-party) evidence
4. Every evidence item must have `reliability_grade`
5. Every finding must have complete evidence chain
6. Never make legal judgments ("suspected fraud", not "constituted fraud")
7. Never use placeholder data — only real company data
8. Before self-designing a solution, exhaust all existing tool capabilities first
9. Missing evidence is itself a signal — analyze WHY it's missing
10. Phase 1 must cross-check actual documents against `topic.json` mandatory modules
11. Audit program step IDs are immutable once used — corrections via errata note + new step (-C suffix), evidence chain must never break
