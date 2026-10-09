# 初始化上下文：配置空白追问与模式判定（Step 0.4 / 0.5）

> SKILL.md Step 0 的完整细节。【强制】0.4 空白追问、0.5 模式判定，干活时读这里。

### 0.4 配置空白检测与动态追问（强制）

读取 my-config.md 后，检查与本次审计主题相关的关键配置项是否仍为空白（`【】` 占位符）：

| 审计主题 | 需检测的关键配置项 |
|---------|------------------|
| 采购/供应链 | 大额采购审批起点、外协加工流程、模具管理流程 |
| 生产/存货 | 废料处置流程、存货盘点流程 |
| 销售/收款 | VMI确认时点、主机厂对账方式、索赔/年降处理方式 |
| 费用/报销 | 差旅报销流程（审批层级、报销系统） |
| 人力资源 | 考勤系统、薪资计算方式 |

**处理规则**：
1. 相关配置项仍为 `【】` → 从 `references/dynamic_questions.md` 的问题矩阵选取 **1-2 个**对应问题向用户追问（每次只问 1-2 题，提供跳过选项）
2. 用户回答后 → 将答案回写 `audit-topics/my-config.md` 对应字段（只填空，不覆盖已有内容）
3. 用户选择"跳过" → 使用默认预设继续，不阻塞流程
4. 已填写的配置项不再追问

**追问格式**：
```text
为了更深地切中要害，请再补充一个业务细节：

👉 [来自 dynamic_questions.md 问题矩阵的问题]

(可直接回复，或回复"跳过"使用默认预设)
```

**回写示例**：
- 问题："废料处置归属？" → 答案写入 my-config.md「废料处置流程 → 处置权限归属」
- 问题："VMI 确认时点？" → 答案写入 my-config.md「销售与收款流程 → VMI确认时点」

**目的**：配置空白 = 风险识别盲区（事实锚定规则会使 AI 避开未配置的领域）。补齐后，Step 2 风险识别、轨道B 舞弊测试、访谈问卷锚定性全部受益。

### 0.3 读取制度分析报告（可选）

检查 `internal-audit-workspace/policy-analyses/*.json`，如存在则提取：
- `baseline_audit_program` → 轨道A基线程序
- `control_gaps` (verification_status="已确认") → Step 2 输入
- `risk_points` (severity="高") → Step 2 输入
- `conflicts` → Step 2 输入

**详细操作**：见 [instruction_details.md#step-03](./instruction_details.md#step-03)

### 0.5 模式判定：全新生成 vs 增量更新（强制）

运行 `python _shared/scripts/phase_gate.py check` 并检查是否存在已有审计程序：

| 条件 | 模式 | 处理 |
|------|------|------|
| 无已有程序（v1.0 不存在） | **全新生成** | 继续 Step 1 - Step 5 |
| 已有 v1.0 程序，且 phase_gate 返回 `action=prompt_program_update`（存在待处理线索） | **增量更新** | 执行 incremental_update.md 完整流程：读取现有程序 + 待处理线索（design-assessments 中 `status="pending"` 的项 / whistleblower_pending）→ 线索过滤 → 生成 S 序列补充程序（十、十一章）→ 状态回写。**完成后不再走 Step 1-5** |
| 已有 v1.0 程序，phase_gate 无更新信号 | 全新生成（覆盖） | 提示用户确认覆盖，确认后走 Step 1-5 |

**增量更新核心规则**（详见 incremental_update.md）：
- 编号 S01/S02...，不使用 R01（避免与 v1.0 冲突）
- 只追加不覆盖：v1.0 已有步骤和证据链永久保留
- 程序存在根本性错误时走「勘误模式」：勘误注记 + 追加 `-C` 修正步骤，禁止直接修改已有步骤
