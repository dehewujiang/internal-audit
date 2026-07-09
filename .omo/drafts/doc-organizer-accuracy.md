# Draft: doc-organizer-accuracy

## State
- intent: clear
- review_required: false
- status: approved
- scope: industry_benchmarks upgrade + two-pass workflow only (no dual-run comparison)
- 3 files, single wave

## Decisions
- Weakness 2 (cross-section implicit controls): two-pass method (LLM index → per-object analysis)
- Weakness 4 (output consistency): deferred, not included in this plan
- industry_benchmarks.md becomes executable checklist with per-domain control dimensions

## Components
| id | component | outcome | evidence |
|----|-----------|---------|----------|
| T1.1 | industry_benchmarks.md | P0 domains have ≥3 control dimensions with type tags | industry_benchmarks.md |
| T1.2 | workflow.md | two-pass business object indexing flow | workflow.md |
| T1.3 | SKILL.md | two-pass mode referenced | SKILL.md |
