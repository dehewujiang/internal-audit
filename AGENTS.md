# AGENTS.md — internal-audit

## What this repo is

A collection of **8 AI skill prompts** (SKILL.md) and **Python tool scripts** for automotive-parts internal auditing. Not an application — no build, no server, no tests. State passes between phases exclusively through JSON/Markdown files in `internal-audit-workspace/`.

## Commands you will need

```powershell
# Before running any Python script (Windows UTF-8 fix):
$env:PYTHONIOENCODING="utf-8"

# Phase gate — ALWAYS run before advancing phases:
python _shared/scripts/phase_gate.py check
python _shared/scripts/phase_gate.py advance

# Validate scripts — use --strict for hard enforcement:
python _shared/scripts/validate-finding.py <file> --strict
python _shared/scripts/validate-program.py <file> --strict
python _shared/scripts/validate-report.py <file> --strict
python _shared/scripts/validate-policy-analysis.py <file>

# Project safety check (before creating workspace):
python _shared/scripts/project_init.py --workspace <path> --skills-dir <path>

# Finding queries:
python _shared/scripts/queries.py list --status all
```

## Phase gate — do NOT skip

The gate has **3 action types**, not 2:

| action | exit code | meaning |
|--------|:---------:|---------|
| `pass` | 0 | advance OK |
| `prompt_program_update` | 2 | interview/whistleblower clues unconsumed → run program-generator incremental mode |
| `block` | 1 | missing prerequisites → fix before advancing |

`prompt_program_update` is **non-zero exit** — the LLM cannot silently skip it. Use `--force` to override.

## Memory system — mandatory startup

Every new session, read these **first** (before any task):

1. `memory/project.md` — current project state, risks, next steps
2. `memory/INDEX.md` — file index

Then output a startup report. The rest of `memory/` is on-demand.

On session end: update `project.md`, `TODO.md`, `session.md`, `decisions.md`, `context.md`. Verify content against reality before reporting "done". If architecture changed, remind user to run `/init`.

## Rules loading — junction trick

`.claude/rules/` is a Windows directory junction → `D:/Nut/00_my_digital/12_AGI/rules/`. Rules load by path pattern, not by explicit reference. Key rules:
- `coding-safety.md` — impact assessment + verification before coding
- `good-taste.md` — eliminate branches, data-first
- `geb-l3.md` — L3 headers (INPUT/OUTPUT/POS) on .py files
- `memory_rules.md` — memory read/write protocol
- `compat.md` — public interfaces in `_shared/scripts/` are permanent contracts

**Exception**: SKILL.md files are LLM prompts, not code. `good-taste.md`'s "functions ≤ 30 lines" does not apply to them.

## User communication — critical

The user is **non-technical**. All output to them must be plain language with everyday metaphors. No jargon (API, component, directory, interface, state machine) without translating it first.

Internal thinking → technical language. External output → plain language.

## Architecture gotchas

- `current-audit.json` stores BOTH business state AND audit execution state. Two new flags were added (2026-07-08): `design_observations_consumed` and `whistleblower_pending` — interview-designer sets the former to `false`, program-generator increment resets it to `true`.
- `internal-audit-workspace/` is the output directory for ALL phases. Each subdirectory maps to a phase: `policy-analyses/` (P1), `design-assessments/` (P1), `interview-materials/` (P1.5), `audit-programs/` (P2-3), `findings/` (P4), `reports/` (P5), `evidence/` (P4).
- Finding files are named `F-YYYY-NNN.json`, NOT `FIND-*.json`. Validate scripts match `F-*`.
- `_shared/scripts/` is the shared tool directory. New Python scripts must have L3 headers. Public tool interfaces are permanent — do not break callers.
- `program-quality-evaluator/SKILL.md` is a standalone quality assessment tool. Only the program-generator Step 5 currently calls it.

## Workflow discipline

1. Determine current phase from `internal-audit-workspace/current-audit.json` → `audit_state.current_phase`
2. Check tool domain table in `CLAUDE.md` — only call tools allowed in the current phase
3. Before advancing to next phase: `python phase_gate.py check`
4. Every validate script call should use `--strict` when writing output files
5. After finding generation: run `validate-finding.py --strict` before writing to `findings/`
6. Interview write-back → interview-designer sets `design_observations_consumed=false` → gate prompts incremental program update

## Key files to know

| file | what it is |
|------|-----------|
| `audit-topics/about-me.md` | company background (read every time, no cache) |
| `audit-topics/my-config.md` | system names, thresholds, config |
| `constitution.md` | the 10 hard constraints (see §不可违反的约束) |
| `CLAUDE.md` | full tool registry + phase routing table |
| `memory/project.md` | user-facing project state (the source of truth) |
| `memory/context.md` | technical context for agents after compact |
| `.omo/plans/` | approved work plans |

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
