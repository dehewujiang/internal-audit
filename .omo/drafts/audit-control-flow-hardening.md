# Draft: audit-control-flow-hardening

## State
- intent: clear
- review_required: false
- status: approved
- pending_action: write .omo/plans/audit-control-flow-hardening.md
- scope: P0+P1 (16 items across 8 components)
- project-init: Python script (Q2-A)

## Decisions
- Q1: P0+P1 full scope (16 items) → B
- Q2: project-init as `_shared/scripts/project_init.py` → A

## Components ledger
| id | component | outcome | evidence |
|----|-----------|---------|----------|
| C1 | program-generator 增量模式 | 新增 Step 6 + interview/whistleblower | SKILL.md + instruction_details.md + output_template.md + new incremental_update.md |
| C2 | phase_gate.py 闸机增强 | 7 new checks + prompt action + --force | _shared/scripts/phase_gate.py |
| C3 | current-audit.json schema | 3 new fields | current-audit.json |
| C4 | validate write-blockers | validate-finding.py + validate-report.py blocked writes | 2 scripts |
| C5 | project_init.py | new: overwrite check + config check | _shared/scripts/project_init.py + project-init SKILL.md |
| C6 | SKILL.md enhancements | unconsumed clues reminder + MANDATORY + queries forced | 3 SKILL.md files |
| C7 | document-organizer hardening | OCR detection + verification state machine | validate-policy-analysis.py + workflow.md |
| C8 | Git commit + memory | all changes committed | git + memory/ files |

## Metis result
Session: ses_0bf769a63ffeAa4An8W5Q58pIX
Verdict: 3 BLOCKERS fixed (skills_dir, audit_purpose path, phase mapping), 5 CRITICAL addressed, 6 WARNINGS acknowledged.
Fixes applied: T0.1-T0.4 added, T1.1 code updated, T1.7 added, T2.13 added, T2.10 clarified, T3.1 path corrected.

## Momus result
Session: ses_0bf703fa9ffeTbBOyzyiAF3Llk
Verdict: APPROVE_WITH_NOTES — 1 BLOCKER (T3.1 non-existent file), 2 CRITICAL (output shape mismatch, undefined workspace_dir), 3 WARNING.
Fixes applied: T3.1 path corrected (commit SKILL.md change, not non-existent template file), code snippets updated (workspace_dir → ws), T1.2 integration clarified.

## Oracle result
Session: ses_0bf7028abffe37XwGEq9t4BZuk
Verdict: APPROVE_WITH_NOTES — 5 hard issues (H1 force logic, H2 prompt enforcement, H3 maintenance debt, H4 constitution update, H5 OCR wiring), 4 concerns (R1 edge cases, R2 no tests, R3 Windows path, R4 SKILL.md comment force).
Fixes applied: H1-H5 all addressed in plan; R1 edge cases documented in T2.2; R2 acknowledged (manual testing); R3 mitigated by env var; R4 tone adjusted in verification strategy.
Constitution.md added to change list.
