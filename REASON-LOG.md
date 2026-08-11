# 审计推理日志设计（REASON-LOG.md）

## ① 背景与现状（已核实事实）

`audit_trail` 当前存在 **4 条写入路径、2 套 schema**：

| 写入路径 | 位置 | schema | 用途 |
|:---|:---|:---|:---|
| phase_gate.append_audit_trail | `_shared/scripts/phase_gate.py` 260-268（调用点：305 tool_force_override / 467 phase_advance / 508 phase_rollback） | `{timestamp, event_type, detail}` | 阶段状态机事件 |
| audit_gate._log_to_trail | `_shared/scripts/audit_gate.py` 186-206 | `{event, source}` | 闸机放行/拦截事件（不经 append_audit_trail） |

**已存在字段**：finding 的 `decision_rationale`（object），被 `query_commands.py:402`（`dr = finding.get("decision_rationale", {})`）消费，由 `queries.py decide` 命令提取 `risk_level` / `key_judgment`。

本设计**复用 `decision_rationale`，不新增顶层 finding 字段**，避免 finding schema 漂移。

## ② 落点规范 A：audit_trail `decision` 事件 + `log-decision` 写入通道

### A1. 事件定义

- 新增 `event_type = "decision"`，沿用 phase_gate 的 `{timestamp, event_type, detail}` schema。
- `detail` 格式：`{场景}:{决策}:{依据}`
  - 例：`程序选择:A7.2:证据A-E覆盖不足`
  - 例：`风险定级:高:回款周期超账期且无对账记录`
  - 例：`线索排除:X3:仅单信源且与制度一致，无需深挖`

### A2. 写入通道（试点）

`phase_gate.py` 新增 CLI 子命令：

```
python phase_gate.py log-decision --scene <场景> --decision <决策> --basis <依据>
```

- 内部调用 `append_audit_trail(data, "decision", f"{scene}:{decision}:{basis}")` 并 `save_audit`。
- **LLM 只能通过该 CLI 子命令写入 decision 事件，不得直接编辑 current-audit.json**——状态由确定性代码管理（宪法原则）。
- 遵循既有 advance/rollback 模式：写入前 `snapshot_audit_state` 备份。

### A3. audit_gate._log_to_trail 试点阶段保持不动

`_log_to_trail`（`{event, source}` schema）试点阶段**不改造、不统一**，避免扩大改动面。两套 schema 并存的事实与后续统一建议见 ④。

## ③ 落点规范 B：finding 复用 `decision_rationale`，新增 `risk_level_reason` 子键

### B1. 字段定义

- `decision_rationale.risk_level_reason`（string）：记录 risk_level 判定理由（一句话）。
- 试点阶段**可选**：`validate-finding.py` 以 warn 级校验（缺失不阻断，报告缺失清单），仅对 `risk_level="高"` 的 finding 触发。
- 全量铺开**转必填**。

### B2. 与 query_commands.py 的关系

- 试点阶段**不改 `decide` 查询逻辑**：`queries.py decide` 读取 `decision_rationale.risk_level` / `key_judgment` 等已有子键，新增子键不影响其读取。
- **铺开阶段补充**：`query_commands.py` 的 `_collect_decision_logs` 从 `audit_trail` 收集 `event_type="decision"` 事件，纳入决策日志展示。

## ④ 两套 schema 并存说明与后续统一建议

### 并存事实

audit_trail 内同时存在 phase_gate 的 `{timestamp, event_type, detail}` 与 audit_gate 的 `{event, source}` 两种条目，历史数据与试点新增的 decision 事件均混存于同一数组。试点阶段**接受并存**：两种 schema 各自服务于不同写入方（阶段状态机 / 闸机），互不干扰，且统一动作牵动既有消费者（如 status/rollback 展示逻辑），风险大于收益。

### 后续统一建议（铺开评估时再议，非试点动作）

- 方向：以 `{timestamp, event_type, detail}` 为主 schema，`_log_to_trail` 追加 `timestamp` 字段并向 `event_type` 对齐。
- 前置条件：盘点 audit_trail 全部消费者（读取方、展示方、校验方），确认统一不破坏任一消费者后再执行。
- 收益：单 schema 便于 `_collect_decision_logs` 统一收集与全量决策追溯。

## ⑤ 试点范围

1. **execution-assistant** 生成 finding 时，填写 `decision_rationale.risk_level_reason`（风险定级理由）。
2. **中央大脑**在以下三类关键决策，通过 `log-decision` 命令写 `event_type="decision"` 事件：
   - 程序选择
   - 风险定级
   - 线索排除

## ⑥ 全量铺开条件

试点运行 **1 个真实审计项目**后评估：

- 决策事件/理由的完整性（是否覆盖三类关键决策）；
- 对审计可追溯性的实际增益（复盘时能否还原决策链）；
- `risk_level_reason` 填写成本（是否影响 finding 产出效率）。

评估通过 → 全量铺开（`risk_level_reason` 转必填、`_collect_decision_logs` 收集 decision 事件、评估两套 schema 统一）；不通过 → 调整设计后重试试点。
