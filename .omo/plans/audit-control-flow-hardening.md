# audit-control-flow-hardening - Work Plan

## TL;DR (For humans)

**你要得到什么**：内部审计流水线的"硬闸机"加固——16 项改动，让 phase_gate、validate 脚本、project-init 在代码层强制拦截，不依赖 LLM 自觉。改完后：访谈忘了更新程序→闸机拦住；审计目的没选→闸机拦住；about-me 缺失→闸机拦住；有问题的 finding 想写入文件→脚本拒绝；project-init 想覆盖已有项目→脚本退出。

**为什么是这方案**：之前的系统审计发现全系统 28 个用户提示点中有 11 个是 LLM 自觉执行的，遗忘即灾难。本方案用代码替代 LLM 记忆——phase_gate.py 新增 7 个检查条件 + `--force` + `prompt_program_update` action，5 个 validate 脚本加 `--strict` 写入前阻断，project_init.py 硬安全检查。

**不改什么**：interview-designer、execution-assistant、report-generator、finding-debate 的核心业务逻辑不变。不新增 skill。不改 document-organizer 的制度分析算法。

**工作量**：3 波次 + 5 个前置修复，约 21 个 todo。Wave 0（前置）5 项，Wave 1（基础层）7 项，Wave 2（功能层）13 项，Wave 3（交付层）2 项。波次内可并行。

**风险**：最大风险是 phase_gate.py 改动后与旧 current-audit.json 的向后兼容（已通过 T0.2 兼容读取解决）。其次是与 interview-designer 的 flag 联动（已通过 T2.13 解决）。

**已确认决策**：P0+P1 全覆盖，project-init 做 Python 脚本。

## Scope

**IN**: 16 项改动覆盖全系统 8 个组件，消除 LLM 遗忘关键用户提示的风险，让制度分析→访谈→程序生成→执行→报告的流水线在代码层有硬闸机兜底。

**OUT**: interview-designer、execution-assistant、report-generator、finding-debate 的核心业务逻辑不变。不新增 skill。不改 document-organizer 的制度分析算法。

**改动文件清单**（共 15 个文件）：

| 文件 | 类型 | 组件 |
|------|------|:--:|
| `_shared/scripts/phase_gate.py` | 修改 | C2 |
| `_shared/scripts/validate-finding.py` | 修改 | C4 |
| `_shared/scripts/validate-report.py` | 修改 | C4 |
| `_shared/scripts/validate-program.py` | 修改 | C4 |
| `_shared/scripts/validate-policy-analysis.py` | 修改 | C7 |
| `_shared/scripts/project_init.py` | **新增** | C5 |
| `constitution.md` | 修改 | — (闸机规则同步) |
| `current-audit.json` (project-init SKILL.md 内嵌模板) | 修改 | C3 |
| `program-generator/SKILL.md` | 修改 | C1 |
| `program-generator/references/instruction_details.md` | 修改 | C1 |
| `program-generator/references/output_template.md` | 修改 | C1 |
| `program-generator/references/incremental_update.md` | **新增** | C1 |
| `execution-assistant/SKILL.md` | 修改 | C6 |
| `finding-debate/SKILL.md` | 修改 | C6 |
| `report-generator/SKILL.md` | 修改 | C6 |
| `document-organizer/references/workflow.md` | 修改 | C7 |
| `interview-designer/SKILL.md` | 修改 | C2/C6 |
| `project-init/SKILL.md` | 修改 | C5 |

## Verification strategy

- Python 脚本（4 个修改 + 1 个新增）：每改完一个立即用真实/模拟数据跑一次，输出 stdout 确认 action 值正确
- SKILL.md 修改（6 个文件）：grep 确认 MANDATORY_OUTPUT / MANDATORY_GATE 标记位置正确，确认无残留占位符
- 跨组件一致性：phase_gate 检查条件中引用的 current-audit.json 字段名与 C3 schema 一致；validate 脚本的错误信息与 SKILL.md 中的处理指引一致
- 不验证：LLM 行为（无法在 plan 阶段验证 SKILL.md 是否真的让 LLM 不遗忘——这属于集成测试，由端到端测试覆盖）

## 阶段映射表（方案 vs phase_gate.py 内部名称）

phase_gate.py 使用语义化阶段名，方案使用业务编号。以下为精确对应：

| 方案阶段 | phase_gate.py 内部字符串 | 说明 |
|---------|------------------------|------|
| Phase 0 | `phase_0_init` | 项目初始化 |
| Phase 1 | `phase_1_document_analysis` | 制度分析 |
| Phase 1.5 | `phase_1_5_interview` | 访谈 |
| Phase 2-3 | `phase_2_program_generation` | 程序生成（进入条件在 phase_1_5 退出时检查） |
| Phase 4 | `phase_3_execution` | 审计执行（进入条件在 phase_2 退出时检查） |
| Phase 5 | `phase_4_report` | 报告生成（进入条件在 phase_3 退出时检查） |

**T1.1 的检查**绑定于 `phase_2_program_generation` 进入前（即 `current_phase = "phase_1_5_interview"` 退出时）。
**T1.2 的检查**绑定于 `phase_3_execution` 进入前（即 `current_phase = "phase_2_program_generation"` 退出时）。
**T1.3 的检查**绑定于 `phase_4_report` 进入前（即 `current_phase = "phase_3_execution"` 退出时）。

---

## 前置修复（必须在 Wave 1 之前完成）

### T0.1: phase_gate.py 新增 --skills-dir 参数

**问题**：T1.1 引用了 `skills_dir` 变量但 phase_gate.py 无此参数。

**修复**：在 phase_gate.py 的 argparse 中为 `check` 和 `advance` 子命令新增 `--skills-dir` 可选参数。默认值使用环境变量 `INTERNAL_AUDIT_SKILLS_DIR`，若均未设置则从 workspace 路径向上推断（`workspace/../../` 即 skills 目录）。

### T0.2: phase_gate.py 迁移 audit_purpose 读取路径

**问题**：现有代码从 `audit_state.known_facts.audit_purpose` 读取，T1.4 将 `audit_purpose` 放在 `audit_state` 下（去掉了 known_facts 层级）。

**修复**：修改现有 `check_exit_conditions` 中的 audit_purpose 检查（约 line 84-85），改为同时读取两个位置：优先读 `audit_state.audit_purpose`（新），回退到 `audit_state.known_facts.audit_purpose`（旧）。

### T0.3: validate-finding.py 修复 FIND- 前缀

**问题**：`--findings-dir` 模式搜索 `FIND-*` 前缀，但实际文件为 `F-*` 前缀。

**修复**：将 validate-finding.py line 602 的 `fn.startswith("FIND-")` 改为 `fn.startswith("F-") and fn.endswith(".json")`。

### T0.4: 新增 interview-designer 写 flag 的任务

**问题**：`design_observations_consumed` flag 需要 interview-designer 在追加风险线索后设为 false，但原方案未包含此任务。

**修复**：在 Wave 2 新增 T2.13。

---

## Execution strategy

3 波次推进 + 前置修复，波次内可并行（无文件冲突），波次间有依赖：

```
Wave 1 (基础层) ──→ Wave 2 (功能层) ──→ Wave 3 (交付层)
C2 + C3 + C4          C1 + C5 + C6 + C7     C8
phase_gate            program-generator      git commit
schema                project_init           memory update
write-blockers        annotations
                      document-organizer
```

依赖关系：
- C1（增量模式）依赖 C2（phase_gate 的 prompt 动作）和 C3（新字段）
- C5（project_init.py）独立，但 project-init SKILL.md 的修改与 C6 同类，放同一波
- C7（document-organizer）独立
- C8（commit）依赖 Wave 1+2 全部完成

---

## Todos

### Wave 0: 前置修复（必须先于 Wave 1 完成）

---

#### T0.1: phase_gate.py — 新增 --skills-dir CLI 参数 + exit code for prompt action

**References**: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\phase_gate.py`

**Changes**: 在 argparse 中为 `check` 和 `advance` 子命令新增 `--skills-dir` 可选参数。默认值：优先读环境变量 `INTERNAL_AUDIT_SKILLS_DIR`，其次从 workspace 向上推断。

同时修改 `cmd_check` 的 exit code 逻辑：`prompt_program_update` 返回 exit 2（非零），带 `--force` 时降为 0 并附 warnings。这保证 LLM 不跳过闸机——必须显式 `--force` 才能绕过。

**Acceptance**: `phase_gate.py check --skills-dir /path` 正常；`prompt_program_update` 返回 exit 2；`--force` 时降为 exit 0。

**Commit**: `fix: phase_gate --skills-dir + non-zero exit for prompt action`

---

#### T0.2: phase_gate.py — 迁移 audit_purpose 读取路径

**References**: 同上 phase_gate.py line 83-85

**Changes**: 修改现有 `check_exit_conditions` 中 `audit_purpose` 读取逻辑（约 line 84-85），改为：
```python
audit_purpose = (
    state.get("audit_purpose")  # 新位置 (T1.4)
    or state.get("known_facts", {}).get("audit_purpose")  # 旧位置（兼容）
    or data.get("audit_purpose")  # 顶层（兼容）
)
```

**Acceptance**: 三种路径任一有值 → 通过；全部为空 → 提示"审计目的未选择"。

**QA**:
- Happy: `audit_state.audit_purpose = "舞弊调查"` → pass
- Happy: `audit_state.known_facts.audit_purpose = "内控评估"` → pass
- Failure: 所有路径为空 → block

**Commit**: `fix: phase_gate audit_purpose read from migrated schema path`

---

#### T0.3: validate-finding.py — 修复 FIND- 前缀为 F-

**References**: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\validate-finding.py` line 602

**Changes**: 将 `fn.startswith("FIND-")` 改为 `fn.startswith("F-") and fn.endswith(".json")`。

**Acceptance**: `--findings-dir` 模式能匹配 `F-2026-001.json` 格式的文件。

**QA**: 创建 findings/ 目录含 `F-2026-001.json` → `--findings-dir findings/` → 找到文件

**Commit**: `fix: validate-finding use F- prefix consistent with finding naming`

---

#### T0.5: constitution.md — 同步新增 prompt_program_update action 规则

**References**: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\constitution.md` 第 75-77 行

**Changes**:
在闸机规则中新增第三条：

```markdown
- action=prompt_program_update → 程序未覆盖所有风险线索，需先执行 program-generator 增量模式补齐。补齐后重新运行 phase_gate.py check。不可跳过。
```

同时更新 `--force` 语义说明：`--force` 可降级 `prompt_program_update` 为 warning（放行但提示），不可降级 `block`。

**Acceptance**: constitution.md 明确包含 prompt_program_update 的处理条款。

**Commit**: `feat: constitution add prompt_program_update gate rule`

---

### Wave 1: 基础层 — 闸机 + Schema + 写入阻断

---

#### T1.1: phase_gate.py — 新增 check Phase 2-3 进入条件

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\phase_gate.py` — 当前脚本（读后改）
- `current-audit.json` — 字段：`audit_state.audit_purpose`, `audit_state.about_me_exists`
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\constitution.md` 第 65-90 行 — 阶段流转规则

**Changes**:
在 `check_exit_conditions(ws, current_phase, data)` 中 `current_phase == "phase_1_5_interview"` 段（当前为 `pass`）新增：

```python
# 检查1: 审计目的是否已选定
audit_purpose = (
    state.get("audit_purpose")  # 新 T1.4 schema
    or state.get("known_facts", {}).get("audit_purpose")  # 旧 schema 兼容
    or data.get("audit_purpose")
)
if not audit_purpose:
    issues.append({"type": "block", "msg": "审计目的未选择。请返回 program-generator Step 1 完成目的选择。"})

# 检查2: about-me.md 是否存在
skills_dir = Path(args.skills_dir) if args.skills_dir else ws.parent.parent
about_me_path = skills_dir / "audit-topics" / "about-me.md"
if not about_me_path.exists():
    issues.append({"type": "block", "msg": "about-me.md 不存在。请先完成公司背景配置。"})
```

**注意**: `check_exit_conditions` 当前返回 `{"ready": bool, "missing": list}`。新增 `prompt_program_update` action 后，需要重构返回格式为统一的 `issues` 列表（含 type 字段），并在 `cmd_check` 中据此生成 `action`。变动的完整范围：`check_exit_conditions` + `cmd_check` + `cmd_advance`，保持向后兼容的 `ready`/`missing` 字段作为衍生输出。`ws` 是函数已有的参数名（workspace Path），代码片段中统一使用 `ws`。

**Acceptance criteria**:
- `phase_gate.py check --to phase_2` 在 audit_purpose 为空时返回 `action=block`
- `phase_gate.py check --to phase_2` 在 about-me.md 缺失时返回 `action=block`
- 两项都满足时返回 `action=pass`

**QA**: 
- Happy: 创建模拟 current-audit.json（audit_purpose="舞弊调查"，about-me.md 存在）→ 运行 check → stdout 含 `"action": "pass"`
- Failure: 创建 current-audit.json（audit_purpose 为空）→ 运行 check → stdout 含 `"action": "block"` 且 messages 包含"审计目的未选择"
- Failure: 删除 about-me.md → 运行 check → stdout 含 `"action": "block"` 且 messages 包含"about-me.md 不存在"

**Commit**: `feat: phase_gate check audit_purpose and about-me.md before Phase 2`

---

#### T1.2: phase_gate.py — 新增 prompt_program_update action

**References**:
- 同上 phase_gate.py
- `current-audit.json` — 字段：`audit_state.design_observations_consumed`, `audit_state.whistleblower_pending`
- 本次对话中的设计方案："代码做闸机，LLM 做执行"

**Changes**:
在 `current_phase == "phase_2_program_generation"` 段新增（Phase 4 入口 = phase_3_execution 进入前检查）：

```python
# 检查3: design-assessments 是否有未消费的访谈线索
if not data.get("audit_state", {}).get("design_observations_consumed", True):
    design_dir = ws / "design-assessments"
    if design_dir.exists():
        for f in design_dir.glob("*_设计观察.json"):
            content = json.loads(f.read_text(encoding="utf-8"))
            clues = [obs for obs in content.get("design_observations", [])
                     if obs.get("type") == "risk_clue" and obs.get("status") == "pending"]
            if clues:
                issues.append({
                    "type": "prompt_update",
                    "msg": f"{len(clues)}条访谈线索尚未纳入审计程序",
                    "suggested_skill": "internal-audit-program-generator (增量模式)",
                    "trigger": "interview"
                })

# 检查4: 是否有未处理的举报
if data.get("audit_state", {}).get("whistleblower_pending"):
    issues.append({
        "type": "prompt_update",
        "msg": "举报材料尚未纳入审计程序",
        "suggested_skill": "internal-audit-program-generator (增量模式)",
        "trigger": "whistleblower"
    })
```

`cmd_check` 的决策逻辑更新为：
```python
if any(i["type"] == "block" for i in issues):
    action = "block"
elif any(i["type"] == "prompt_update" for i in issues):
    action = "prompt_program_update"  # exit code 2（非零），--force 时降为 0
else:
    action = "pass"
```

**关键**: `--force` 只降级 `prompt_update` → warning，不退让 `block` → pass。用户不可绕过 block 级缺失。

**Acceptance criteria**:
- design_observations_consumed=false 且有 pending risk_clue → `action=prompt_program_update`
- whistleblower_pending=true → `action=prompt_program_update`
- 两者都为 false/true → `action=pass`
- 加 `--force` 后 prompt_update 不阻断 → `action=pass` 但含 warnings

**QA**:
- Happy: 创建 design-assessments/test_设计观察.json（含 pending risk_clue），current-audit 标记 unconsumed → `action=prompt_program_update`
- Happy: current-audit 标记 whistleblower_pending=true → `action=prompt_program_update`
- Failure: 无 risk_clue 且无举报 → `action=pass`
- Failure: 同上 + `--force` → `action=pass` 且 warnings 非空

**Commit**: `feat: phase_gate prompt_program_update for interview/whistleblower gaps`

---

#### T1.3: phase_gate.py — 新增 report_type 和 findings 检查

**References**: 同上 phase_gate.py

**Changes**:
在 Phase 5 entry checks 中新增：

```python
# 检查5: 报告类型是否已选定
if not current_audit.get("audit_state", {}).get("report_type"):
    issues.append({"type": "block", "msg": "报告类型未选择。请返回 report-generator 选择报告类型（标准/专项/舞弊/跟踪）。"})

# 检查6: findings 目录是否存在且非空
findings_dir = workspace_dir / "findings"
if not findings_dir.exists() or not any(findings_dir.glob("F-*.json")):
    issues.append({"type": "block", "msg": "findings 目录为空。请先完成 Phase 4 审计执行。"})
```

**Acceptance criteria**:
- report_type 为空 → `action=block`
- findings 目录无 F-*.json → `action=block`

**QA**:
- Happy: report_type="标准" + findings 有文件 → pass
- Failure: report_type 为空 → block
- Failure: findings 目录为空 → block

**Commit**: `feat: phase_gate check report_type and findings before Phase 5`

---

#### T1.4: current-audit.json — schema 扩展

**References**:
- `current-audit.json` 实际文件（先找现有实例确认当前 schema）
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\project-init\SKILL.md` — 创建 current-audit.json 的逻辑

**Changes**:
在 `audit_state` 对象中新增 3 个字段：

```json
{
  "audit_state": {
    "current_phase": "phase_1",
    "audit_purpose": "",
    "report_type": "",
    "program_version": "v1.0",
    "design_observations_consumed": true,
    "whistleblower_pending": false,
    "program_update_history": []
  }
}
```

字段说明：
| 字段 | 类型 | 默认值 | 更新时机 |
|------|------|--------|---------|
| `audit_purpose` | string | `""` | program-generator Step 1 用户选择后写入 |
| `report_type` | string | `""` | report-generator Step 2 用户选择后写入 |
| `design_observations_consumed` | bool | `true` | interview-designer 回写后设 false；program-generator 增量更新后设 true |
| `whistleblower_pending` | bool | `false` | 用户提交举报后设 true；增量更新后设 false |
| `program_version` | string | `"v1.0"` | 每次增量更新后递增 |
| `program_update_history` | array | `[]` | 每次增量更新追加一条记录 |

**Acceptance criteria**:
- 所有新字段存在且有默认值
- phase_gate.py 读取时不因字段缺失而崩溃（向后兼容：缺字段用默认值）
- project-init 创建的新项目自动包含新字段

**QA**:
- Happy: 创建新 current-audit.json → 含全部 6 个新字段且默认值正确
- Failure: 创建缺少新字段的旧格式 JSON → phase_gate.py 不崩溃，使用默认值

**Commit**: `feat: extend current-audit.json schema with gate control fields`

---

#### T1.5: validate-finding.py — 写入前阻断

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\validate-finding.py` — 当前脚本

**Changes**:
当前 validate-finding.py 返回 `action=block/warn/pass` 但 LLM 可选忽略。改为：

1. 新增 `--strict` CLI flag（argparse 新增参数）
2. 在 `main()` 函数末尾，统计检查结果后：
   - 若存在 blocker 且 `--strict` → `sys.exit(1)`
   - 若存在 blocker 但无 `--strict` → 保持原有 exit 0 + 打印信息的行为（向后兼容）
   - 若只有 warning → 打印到 stderr，`sys.exit(0)`

**不新增独立函数**。直接在现有 `main()` 流程末端添加 exit code 判断，避免维护两份流程。

3. 同步更新 execution-assistant SKILL.md Step 3f-2 的调用方式：新增 `--strict` 标志。

**Acceptance criteria**:
- `validate-finding.py <valid_finding.json> --strict` → exit 0
- `validate-finding.py <invalid_finding.json> --strict` → exit 1 + stderr 含具体错误
- 不带 `--strict` 的调用行为不变

**QA**:
- Happy: 有效 finding JSON → `--strict` → exit 0
- Failure: 缺失 reliability_grade 的 finding → `--strict` → exit 1
- Failure: 缺失 title 的 finding → `--strict` → exit 1

**Commit**: `feat: validate-finding.py --strict mode blocks on action=block`

---

#### T1.6: validate-report.py — 写入前阻断

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\validate-report.py` — 当前脚本

**Changes**: 与 T1.5 对称。新增 `--strict` flag，action=block 时 exit 1。

**Acceptance criteria**: 同 T1.5 但针对 report 格式校验。

**QA**: 同 T1.5，使用含占位符 `{{}}` 的报告 → exit 1。

**Commit**: `feat: validate-report.py --strict mode blocks on action=block`

---

#### T1.7: validate-program.py — 写入前阻断（T1.5/T1.6 补充）

**References**: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\validate-program.py`

**Changes**: 与 T1.5 对称。新增 `--strict` flag，action=block 时 exit 1。同时更新 program-generator SKILL.md Step 5 中的调用方式使用 `--strict`。

**Acceptance**: 同 T1.5 但针对 program 格式校验。

**QA**: 使用含缺字段的程序 JSON → `--strict` → exit 1

**Commit**: `feat: validate-program.py --strict mode`

---

### Wave 2: 功能层 — 增量程序 + Project-Init + 标注

---

#### T2.1: program-generator — instruction_details.md Step 0.3 扩展

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\internal-audit-program-generator\references\instruction_details.md` 第 24-53 行

**Changes**:
在 Step 0.3 末尾新增子节 "#### 7. 读取设计观察（用于增量更新模式）"：

```markdown
#### 7. 读取设计观察（用于增量更新模式）

检查 `internal-audit-workspace/design-assessments/` 中的 JSON 文件，提取：
- `design_observations[]` 中 `type="risk_clue"` 且 `status="pending"` 的条目
- 每个条目的 `source_role` / `source_id` / `interview_snippet` / `contradiction`
- 每一条转化为【访谈类-线索】风险输入 Step 2

同时检查 current-audit.json 中的 `whistleblower_pending`：
- 若为 true → 提示用户提供举报内容 → 生成【举报类-线索】风险
```

**Acceptance criteria**: LLM 执行增量模式时能读到 design-assessments 内容并转化为风险线索。

**Commit**: `feat: program-generator reads design-assessments for incremental mode`

---

#### T2.2: program-generator — 新增 incremental_update.md

**References**:
- 本次对话中设计的增量更新流程（第十章结构、版本链、标注格式）

**Changes**: 新建文件 `references/incremental_update.md`，内容包括：

1. **触发条件**：phase_gate 返回 `prompt_program_update` 时
2. **Step 0**：读取现有程序 v1.0 + design-assessments + 举报内容
3. **Step 1**：筛选需补充的线索（与已有程序的风险编号比对，无覆盖的才新增）
4. **Step 2**：生成增量程序章节
5. **输出结构**：
```markdown
# 十、访谈补充程序（v1.1）
## 10.1 访谈新增风险线索
## 10.2 访谈矛盾确认
## 10.3 增量测试程序（按轨道分类）
## 10.4 更新后覆盖确认

# 十一、举报补充程序（v1.2）（如适用）
```
6. 版本控制：更新 current-audit.json 的 program_version 和 program_update_history
7. 编号规则：增量章节用 S01/S02...（避免与 v1.0 的 R01/R02 冲突）

**Acceptance criteria**: LLM 读取此文件后能完整执行一次增量更新流程。涵盖以下边缘情况：
- `design-assessments/` 为空或无 JSON 文件 → 返回"无待消费线索"，正常退出
- 单个 JSON 解析失败 → 跳过并记录警告，不阻断其余文件
- 同一线索出现于多个文件 → 按 `id` 去重，保留首次出现
- `design_observations_consumed=true` 但仍有 pending risk_clue（flag 与数据不一致）→ 仍处理线索，并在输出中标注 ⚠️ "flag 不一致"

**Commit**: `feat: program-generator incremental update mode reference`

---

#### T2.3: program-generator — SKILL.md 新增 Step 6

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\internal-audit-program-generator\SKILL.md`
- 新文件 `references/incremental_update.md`

**Changes**:
在 Step 5 之后新增：

```markdown
## Step 6：增量更新模式（条件触发）

**触发条件**：phase_gate.py 返回 `action=prompt_program_update` 时进入。

**前置确认**：向用户展示待补充线索清单，逐条确认是否纳入。用户可取消不需要的线索。

**执行**：按 `references/incremental_update.md` 执行增量生成。

**输出后操作**：
- 更新 `current-audit.json`：
  - 根据 trigger 类型设 `design_observations_consumed=true` 或 `whistleblower_pending=false`
  - `program_version` 递增
  - `program_update_history` 追加记录
```

**Acceptance criteria**: SKILL.md 中有完整的 Step 6 定义，引用 incremental_update.md。

**Commit**: `feat: program-generator SKILL.md Step 6 incremental mode`

---

#### T2.4: program-generator — output_template.md 增量章节模板

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\internal-audit-program-generator\references\output_template.md`

**Changes**: 在原模板末尾（第九章之后）新增第十章和十一章的模板，包含：
- 10.1 访谈新增风险线索表（补充编号 S01...、风险名称、来源标注【访谈类-线索】、原风险对应）
- 10.2 访谈矛盾确认表（矛盾编号 C01...、控制点、说法A/B、验证程序）
- 10.3 增量测试程序（按轨道 A/C 分类，标注来源【访谈补充：岗位-日期】）
- 10.4 更新后覆盖确认表
- 第十一章（举报）结构同上，标注【举报类-线索】

**Acceptance criteria**: 模板包含完整的增量章节结构，LLM 可按模板输出。

**Commit**: `feat: program-generator output template for incremental chapters`

---

#### T2.5: project_init.py — 新脚本

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\project-init\SKILL.md` — 理解创建流程
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\` — 放置位置

**Changes**: 新建 `_shared/scripts/project_init.py`，功能：

```python
#!/usr/bin/env python3
"""
[INPUT]: 依赖 --workspace <path> --topic <name> --force(可选)
[OUTPUT]: 检查通过 → exit 0；检查不通过 → exit 1 + stderr
[POS]: 审计项目初始化安全检查，在 mkdir/写文件之前调用
"""

import sys
import json
import argparse
from pathlib import Path

def check_config_files(skills_dir: Path) -> bool:
    """检查 about-me.md 和 my-config.md 是否存在（不受 --force 影响）"""
    ok = True
    for fname in ["about-me.md", "my-config.md"]:
        fp = skills_dir / "audit-topics" / fname
        if not fp.exists():
            print(f"警告: {fp} 不存在。请先创建。", file=sys.stderr)
            ok = False
    return ok

def check_workspace_overwrite(workspace_path: Path, force: bool) -> bool:
    """检查 internal-audit-workspace/current-audit.json 是否已存在"""
    ca = workspace_path / "current-audit.json"
    if ca.exists():
        if force:
            print(f"警告: {ca} 已存在，--force 模式将覆盖。", file=sys.stderr)
            return True
        print(f"错误: {ca} 已存在。覆盖现有项目将丢失数据。", file=sys.stderr)
        print("如需覆盖，请先手动删除或备份现有项目，或使用 --force。", file=sys.stderr)
        return False
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--skills-dir", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    skills = Path(args.skills_dir)

    errors = []
    if not check_workspace_overwrite(workspace, args.force):
        errors.append("workspace_overwrite")
    if not check_config_files(skills):  # config 检查不受 --force 影响
        errors.append("config_missing")

    if errors:
        sys.exit(1)
    print("安全检查通过。")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

**Acceptance criteria**:
- 目标 workspace 已有 current-audit.json → exit 1 + stderr 含"已存在"
- about-me.md 缺失 → exit 1 + stderr 含"不存在"
- 两项都满足 → exit 0 + stdout "安全检查通过"
- `--force` 跳过 workspace 检查 → 仍会检查 config

**QA**:
- Happy: 新建空 workspace + about-me.md 存在 → exit 0
- Failure: workspace 有 current-audit.json → exit 1
- Failure: about-me.md 缺失 → exit 1

**Commit**: `feat: project_init.py safety checks for project creation`

---

#### T2.6: project-init SKILL.md — 集成 project_init.py

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\project-init\SKILL.md`

**Changes**:
在 Step 3（创建目录结构）之前插入：

```markdown
### Step 2.5：安全检查（强制）

在创建任何文件之前，运行：

```bash
python ~/.claude/skills/internal-audit/_shared/scripts/project_init.py \
  --workspace <workspace_path> \
  --skills-dir ~/.claude/skills/internal-audit/
```

若 exit code != 0 → 展示错误信息给用户，停止创建。用户修正后重试。
若 exit code = 0 → 继续 Step 3。
```

**Acceptance criteria**: SKILL.md 明确要求在 Step 3 之前运行 project_init.py，exit code != 0 时停止。

**Commit**: `feat: project-init SKILL.md integrates project_init.py safety gate`

---

#### T2.7: execution-assistant SKILL.md — 未消费线索提醒

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\audit-execution-assistant\SKILL.md` Step 1

**Changes**:
在 Step 1 "程序执行引导" 中，展示当前程序清单后，新增一个段落：

```markdown
**未消费设计观察提醒**（如有）：

若 Step 0 读取的 design-assessments 中存在以下内容，必须在程序清单下方展示：

```
⚠️ 以下访谈线索尚未纳入当前审计程序，建议在执行中关注：

| 来源编号 | 线索摘要 | 来源岗位 | 建议操作 |
|---------|---------|---------|---------|
| D-015 | 成品丝超期无系统预警 | 仓管员-李某 | 执行 A-xxx 时重点关注，或输入"新增"补充专项测试 |
| D-018 | 废料处置无专人负责 | 仓管员-赵某 | 执行废料相关程序时交叉验证 |

如无未消费线索 → 不展示此段落。
```
```

**Acceptance criteria**:
- design-assessments 中有 pending risk_clue → Step 1 输出包含此提醒表
- 无 risk_clue 或全部已消费 → Step 1 输出不含此提醒表

**Commit**: `feat: execution-assistant Step 1 unconsumed clues reminder`

---

#### T2.8: execution-assistant SKILL.md — MANDATORY_OUTPUT 标记

**References**:
- 同上执行助手 SKILL.md
- 系统审计中识别出的 3 个关键菜单点

**Changes**:
在以下三处菜单模板上方各加一行 `<!-- MANDATORY_OUTPUT: 每次进入此步骤时必须输出以下菜单，不可省略 -->`：

1. **Step 1 程序引导菜单**（"完成/跳过/替代/新增/删除/帮助/路径"）
2. **Step 1a 变更确认**（替代/新增/删除 各自的确认为）
3. **Step 3 Finding 记录菜单**（"A) 记录 B) 待确认 C) 忽略"）

同时在整个 SKILL.md 顶部新增一节：

```markdown
## MANDATORY_OUTPUT 标记说明

本文档中所有 `MANDATORY_OUTPUT` 标记的段落，在对应步骤中必须输出，不可省略或简化。
若条件不满足（如无需变更），仍需输出"当前步骤无变更需求"而非直接跳过。
```

**Acceptance criteria**: grep 确认 3 处菜单上方均有 MANDATORY_OUTPUT 标记。

**Commit**: `feat: execution-assistant MANDATORY_OUTPUT on critical menus`

---

#### T2.9: finding-debate SKILL.md — MANDATORY_GATE 标记

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\audit-finding-debate\SKILL.md`

**Changes**:
在 Step 0（模式选择）和 Step 2（难度 + 角色选择）的菜单上方各加：

```markdown
<!-- MANDATORY_GATE: 未完成此选择前不得进入后续步骤。 -->
```

同时在顶部新增 MANDATORY_GATE 说明（与 T2.8 的 MANDATORY_OUTPUT 对称）。

**Acceptance criteria**: grep 确认 2 处 MANDATORY_GATE 标记。

**Commit**: `feat: finding-debate MANDATORY_GATE on mode/role selection`

---

#### T2.10: report-generator SKILL.md — 强制 queries.py 列出 findings

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\internal-audit-report-generator\SKILL.md` 场景1 Step 1

**Changes**:
report-generator SKILL.md 存在两个 Step 1（场景级 line 76 和详细流程级 line 326）。修改策略：

1. 场景级 Step 1（line 76）：改为强制调用 queries.py：
```markdown
### Step 1：选择 findings（强制）

1. 运行 `python ~/.claude/skills/internal-audit/_shared/scripts/queries.py list --status all`
2. 展示 findings 列表，用户选择后存入 `current-audit.json` 的 `audit_state.selected_findings`
```

2. 详细流程级 Step 1（line 326）：保持现有的 queries.py 引用，不重复修改。上方加注释指向场景级定义。

<!-- MANDATORY_GATE: 未完成 findings 选择前不得进入 Step 2 -->

**Acceptance criteria**: SKILL.md 明确要求运行 queries.py，不允许 LLM 自行"列出"。

**Commit**: `feat: report-generator forced queries.py for finding selection`

---

#### T2.11: document-organizer — validate-policy-analysis.py OCR 检测

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\validate-policy-analysis.py`

**Changes**:
在 schema 检查后新增检查项。集成方式：在 `main()` 函数的批量处理循环中（处理完单个文件后），若文件 total_controls > 0 且 analyzed_controls == 0，追加一个 blocker 到结果列表。

```python
def check_ocr_completeness(data: dict, filename: str) -> list:
    """检查是否有制度分析文件因 OCR 未执行而为空"""
    issues = []
    total = data.get("summary", {}).get("total_controls", 0)
    analyzed = data.get("summary", {}).get("analyzed_controls", total)
    if total > 0 and analyzed == 0:
        issues.append({
            "type": "block",
            "msg": f"{filename}: 总控制点 {total} 个，已分析 0 个。可能原因：PDF 为扫描件，OCR 未执行。请先运行 OCR 工具。"
        })
    return issues
```

**注意**: `check_ocr_completeness` 接收单个文件的数据和文件名（与现有 validate 流程的接口一致），在 `main()` 中处理每个文件后调用，而非独立遍历目录。

**Acceptance criteria**:
- 有 analyzed_controls=0 但 total_controls>0 的 JSON → validate 返回 block
- 正常分析的 JSON → 不触发

**QA**:
- Failure: 创建模拟 JSON（total=15, analyzed=0）→ validate 返回 block，信息含"OCR"
- Happy: 创建模拟 JSON（total=15, analyzed=15）→ validate 返回 pass

**Commit**: `feat: validate-policy-analysis detects unscanned PDF results`

---

#### T2.12: document-organizer — workflow.md verification 状态机

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\document-organizer\references\workflow.md`

**Changes**:
在 verification_status 取值说明处新增硬规则：

```markdown
### verification_status 状态机（强制）

verification_status 取值流转规则：

```
待确认 ──→ 用户显式确认（输入"确认"）──→ 已确认
待确认 ──→ 用户显式否定（输入"不成立"）──→ 不成立
已确认 ──→ 不可回退（除非用户明确要求"重新审视"）
```

<!-- MANDATORY_RULE: LLM 不得自行将"待确认"改为"已确认"。必须等待用户输入明确的确认指令。 -->
```

**Acceptance criteria**: workflow.md 中明确禁止 LLM 自行升级 verification_status。

**Commit**: `feat: document-organizer verification status state machine rule`

---

#### T2.13: interview-designer SKILL.md — 回写后更新 design_observations_consumed

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\audit-interview-designer\SKILL.md` 模式 B 分流输出部分

**Changes**:
在模式 B 的 "分流输出" 段末尾，追加一步：

```markdown
### 回写后状态更新

若本次分流产生了新的 risk_clue（写入 design-assessments），更新 current-audit.json：
- `audit_state.design_observations_consumed = false`

若本次分流产生了矛盾的 contradiction 标记（追加到已有设计观察），同样设 `design_observations_consumed = false`。

若本次分流仅产生配置更新或流程事实（无新 risk_clue），不修改 flag。
```

**Acceptance**: interview-designer 模式 B 执行后，有新 risk_clue 时 `design_observations_consumed` 为 false。

**QA**: 模拟回写含 risk_clue → 检查 current-audit.json 中 flag 为 false

**Commit**: `feat: interview-designer sets design_observations_consumed on write-back`

---

### Wave 3: 交付层 — Commit + 记忆更新

---

#### T3.1: Git commit — 全部变更

**References**: `git status` 输出

**Changes**:
按波次分组提交：

```bash
# 先提交已完成的 RP/CF 跨引用（3个文件）
git add internal-audit-program-generator/references/instruction_details.md
git add internal-audit-program-generator/references/output_template.md
git add internal-audit-program-generator/references/step2_risk_identification.md
git commit -m "feat: RP/CF ID cross-referencing in program-generator source annotations"

# Wave 0 + Wave 1 提交
git add _shared/scripts/phase_gate.py
git add _shared/scripts/validate-finding.py
git add _shared/scripts/validate-report.py
git add _shared/scripts/validate-program.py
git add constitution.md
git commit -m "feat: phase_gate hardening + validate --strict write-blockers + constitution update"

# Wave 2 提交
git add _shared/scripts/project_init.py
git add _shared/scripts/validate-policy-analysis.py
git add internal-audit-program-generator/
git add audit-execution-assistant/SKILL.md
git add audit-finding-debate/SKILL.md
git add internal-audit-report-generator/SKILL.md
git add document-organizer/
git add project-init/SKILL.md
git add audit-interview-designer/SKILL.md
git commit -m "feat: program incremental update + project_init + MANDATORY annotations + OCR detection"
```

**Acceptance criteria**: `git status` 干净，所有变更已提交。`git log --oneline -8` 显示以上提交。

**Commit**: （本身是交付步骤，提交信息如上）

---

#### T3.2: 记忆文件更新

**References**:
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\memory\project.md`
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\memory\INDEX.md`
- `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\memory\context.md`

**Changes**:
- project.md：更新"已完成功能"（新增 16 项改动），"当前状态"改为"P0+P1 闸机加固完成"，"最大风险"更新，清空"下一步"
- INDEX.md：更新 project.md 摘要
- context.md：更新时间戳 + 新增"闸机加固（2026-07-08）"条目

**Acceptance criteria**: 三个文件反映真实状态，无矛盾。

**Commit**: `chore: update memory files for control flow hardening`

---

## Final verification wave

全部 todo 完成后，按以下顺序并行验证：

**F1 — plan compliance audit**：grep 所有被修改文件中是否遗漏了任何计划内的变更点。对照组件清单逐项确认。

**F2 — cross-component consistency**：
- phase_gate.py 引用的字段名 vs current-audit.json schema → 一致
- project_init.py 的 exit code vs project-init SKILL.md 的处理指引 → 一致
- validate 脚本的 --strict flag vs execution-assistant SKILL.md 的调用方式 → 一致

**F3 — no regression**：
- 不带 --strict 的 validate 脚本调用 → 行为不变
- 不触发新检查条件的 phase_gate 调用 → 行为不变
- 不涉及增量的 program-generator 首次生成 → 行为不变

**F4 — scope fidelity**：确认无越权修改（未改 interview-designer、document-organizer 分析逻辑、report-generator 核心逻辑、finding-debate 辩论逻辑）。

---

## Commit strategy

按波次分组，每波 1-2 个原子提交。总计约 7 个提交。提交信息遵循 `type: description` 格式（feat/fix/chore）。

---

## Success criteria

1. phase_gate.py 在以下条件时返回 block：audit_purpose 为空、about-me 缺失、report_type 未选、findings 为空
2. phase_gate.py 在以下条件时返回 prompt_program_update：有未消费访谈线索、有未处理举报
3. validate-finding.py --strict 在 block 时 exit 1
4. validate-report.py --strict 在 block 时 exit 1
5. project_init.py 在已有项目时 exit 1
6. program-generator SKILL.md 有完整 Step 6 增量更新定义
7. execution-assistant Step 1 含未消费线索提醒段落
8. 3 个 SKILL.md 中关键菜单有 MANDATORY_OUTPUT/GATE 标记
9. report-generator Step 1 要求运行 queries.py
10. validate-policy-analysis.py 检测 analyzed=0 的结果
11. document-organizer workflow.md 含 verification 状态机规则
12. 所有变更通过 git 提交，记忆文件已更新
