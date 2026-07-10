# draft: interview-designer-v3
intent: clear
review_required: true
status: approved

## High-accuracy review
- Round 1: Momus APPROVE (3 advisory), Oracle CONDITIONALLY APPROVE (3 blockers + 4 high → all fixed)
- Round 2: Momus OKAY, Oracle APPROVE (3 minor → all fixed same-turn)
- Fixes in round 2: T16 anchor corrected (Step 6), TL;DR count 18→16, T17 location specs fixed

## Decisions
- C5 scope: B — 全线软过时提醒（audit_state.artifacts + fresh/stale），不改闸机
- ~~P0 evaluator fix~~ REMOVED: record_evaluation.py 和 quality_gate.py 存在且功能完整，evaluator v2.0 保留它们作为存储管道
- validate script depth: Excel 结构 + 内容规则（open-ended ratio, DRL count）
- C5 vs design_observations_consumed: 互补非替代。consumed=硬闸机, freshness=软提醒

## Components
| id | component | outcome | status |
|:---|:---|:---|:---|
| C1 | interview-designer/SKILL.md | 增加6个章节 | todo |
| C2 | interview_templates.md | 扩展到8领域 | todo |
| C3 | validate-interview.py | 新建校验脚本 | todo |
| ~~C4~~ | ~~跨 skill Step 5.4~~ | REMOVED — 脚本存在且活跃 | n/a |
| C5 | 管线 stale 机制 | audit_state.artifacts + freshness | todo |
| C6 | Mode A JSON副输出 | 每Excel配JSON问题清单 | todo |

## Metis findings
- GAP-1 (CRITICAL): record_evaluation.py 和 quality_gate.py 存在且活跃 — C4 移除
- GAP-2: C5 与 design_observations_consumed 关系已澄清 — 互补非替代
- GAP-7: 依赖顺序修正 — C5(Wave 3) 先于 C1 的 T5/T6 stale 行为定义
