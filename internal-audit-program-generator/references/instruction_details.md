# 详细步骤说明

## Step 0.3: 读取制度分析报告（详细）

### 时机

Step 0.1 和 0.2 完成后，Step 1 之前。

### 检查路径

`internal-audit-workspace/policy-analyses/` 中的 JSON 文件。

### 重要原则

**制度分析是合规性审计的充分条件，不是完整审计程序的充分条件。**

| 审计类型 | 制度分析能否覆盖？ | 实际输入来源 | 覆盖审计类型 |
|---------|------------------|-------------|-------------|
| **合规性审计** | ✅ 完全覆盖 | 制度分析报告 | 合规性审计 |
| **舞弊调查** | ⚠️ 部分覆盖 | 制度分析提供控制漏洞 + 行业舞弊手法推演 | 舞弊调查 |
| **运营效率审计** | ❌ 不覆盖 | 实际数据与行业/目标对标 | 效率审计 |
| **系统配置风险** | ❌ 不覆盖 | ERP/MES实际配置推演 | 系统审计 |

### 如找到 JSON 文件，执行以下操作

#### 1. 提取 baseline_audit_program

收集所有控制点的 `baseline_audit_program`，这些作为**合规性轨道（轨道A）**的程序基线，必须包含。

#### 2. 提取 control_gaps

筛选 `verification_status="已确认"` 的 control_gaps，这些作为【制度类-设计缺陷】风险输入 Step 2。

#### 3. 提取 design_effectiveness="无效" 的控制点

这些作为【制度类-设计缺陷】风险输入 Step 2。

#### 4. 提取 risk_points

所有 `severity="高"` 的 risk_points，这些作为已有风险识别输入 Step 2。

#### 5. 提取 conflicts

所有制度冲突，这些作为特殊风险输入 Step 2。

#### 6. 构建制度ID→信息映射表

遍历每个 JSON 文件：
- 读取 `document_info.name`（如"NPM001成品仓库管理标准"）
- **遍历该文件中的全部四类编号**，建立映射表供 Step 2 来源标注使用：

| ID类型 | 映射内容 | 示例 |
|--------|---------|------|
| `control_points[].id`（CP-XXX） | → 制度名称 | `{"CP-N001-07": "NPM001成品仓库管理标准"}` |
| `control_gaps[].id`（CG-XXX） | → 制度名称 | `{"CG-N007-02": "NPM007材料仓库管理标准"}` |
| `risk_points[].id`（RP-XXX） | → 制度名称 + 风险描述摘要 | `{"RP-007": "NPM005废料管理办法 — 废料处置缺少定期检查"}` |
| `conflicts[].id`（CF-XXX） | → 冲突摘要 | `{"CF-001": "NPM003采购部职责 vs NPM007材料仓库管理标准 — 审批权归属冲突"}` |

- 存储在工作内存中，供 Step 2 查询使用

#### 7. 读取设计观察（用于增量更新模式）
检查 `internal-audit-workspace/design-assessments/` 中的 JSON 文件：
- `design_observations[]` 中 `type="risk_clue"` 且 `status="pending"` → 转为【访谈类-线索】风险
- 每个条目的 `source_role`/`source_id`/`interview_snippet`/`contradiction` 作为风险描述依据
- 同时检查 current-audit.json `whistleblower_pending` → 生成【举报类-线索】风险

### 如未找到 JSON 文件

- 跳过 Step 0.3
- 在输出中注明："本次未读取制度分析报告，合规性轨道缺少基线程序，风险识别仅基于行业经验和公司特征"
- 后续步骤正常执行

### 数据映射

| document-organizer JSON字段 | program-generator处理 | 输入到 | 覆盖审计类型 |
|----------------------------|----------------------|--------|-------------|
| `control_points[].baseline_audit_program` | 提取为程序基线 | 轨道A（必须包含） | 合规性审计 |
| `control_points[] where design_effectiveness="无效"` | 转为【制度类-设计缺陷】风险 | Step 2 风险识别 | 合规性审计 |
| `control_gaps[] where verification_status="已确认"` | 转为【制度类-设计缺陷】风险 | Step 2 风险识别 | 合规性审计 |
| `risk_points[] where severity="高"` | 转为【制度类-设计缺陷】风险 | Step 2 风险识别 | 合规性审计（走轨道A） |
| `conflicts[]` | 转为【公司类-推演】风险 | Step 2 风险识别 | 合规性+舞弊参考 |
