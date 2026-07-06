# 控制点提取规范

## 控制点类型及识别方法

### 1. 审批权限控制

**识别关键词**："审批"、"批准"、"签字"、"审核"

**提取模板**：
```
制度原文：[原文引用]
提取的控制点：
- 控制类型：审批权限控制
- 控制对象：[如：采购、费用、人事]
- 审批权限：[金额阈值/事项类型]
- 审批层级：[具体审批人]
- 审批方式：[书面/系统/会签]
```

**输出程序基线模板**（供program-generator消费，不是完整审计程序）：
```yaml
baseline_audit_program:
  - objective: 验证[控制对象]是否经过适当审批
  - sample_criteria: [条件，如：金额>X]的[对象]
  - evidence_source: [系统/文件]
  - test_steps: [获取审批记录, 检查审批, 验证时间]
  - pass_criteria: [标准描述]
```

> ⚠️ 注意：baseline_audit_program只是程序基线模板，不是完整审计程序。
> 完整的审计程序（含实质性测试、舞弊调查、边界探测等）由internal-audit-program-generator在Phase 3生成。

---

### 2. 职责分离控制

**识别关键词**："职责分离"、"不相容"、"分别"、"不同人员"

**提取模板**：
```
制度原文：[原文引用]
提取的控制点：
- 控制类型：职责分离控制
- 分离要求：[具体分离要求]
- 涉及岗位：[岗位列表]
- 风险描述：[未分离的风险]
```

**输出程序基线模板**（供program-generator消费，不是完整审计程序）：
```yaml
baseline_audit_program:
  - objective: 验证[岗位1]与[岗位2]是否职责分离
  - sample_criteria: [时间段]的[业务记录]
  - evidence_source: [系统权限/业务单据]
  - test_steps: [获取单据A和单据B, 比对执行人, 识别兼任]
  - pass_criteria: [标准描述]
```

> ⚠️ 注意：baseline_audit_program只是程序基线模板，不是完整审计程序。
> 完整的审计程序由internal-audit-program-generator在Phase 3生成。

---

### 3. 定期检查控制

**识别关键词**："定期"、"每月"、"每季度"、"每年"、"按时"

**提取模板**：
```
制度原文：[原文引用]
提取的控制点：
- 控制类型：定期检查控制
- 检查频率：[时间周期]
- 检查对象：[检查范围]
- 检查内容：[具体检查项]
```

**输出程序基线模板**（供program-generator消费，不是完整审计程序）：
```yaml
baseline_audit_program:
  - objective: 验证[检查对象]是否[频率]进行检查
  - sample_criteria: 最近[N]个周期的检查记录
  - evidence_source: [检查报告/系统记录]
  - test_steps: [获取检查报告, 检查频率, 分析差异处理]
  - pass_criteria: [标准描述]
```

> ⚠️ 注意：baseline_audit_program只是程序基线模板，不是完整审计程序。
> 完整的审计程序由internal-audit-program-generator在Phase 3生成。

---

### 4. 文档记录控制

**识别关键词**："记录"、"登记"、"台账"、"留存"、"归档"

**提取模板**：
```
制度原文：[原文引用]
提取的控制点：
- 控制类型：文档记录控制
- 记录要求：[具体记录要求]
- 记录对象：[需要记录的内容]
- 保存期限：[保存要求]
```

**输出程序基线模板**（供program-generator消费，不是完整审计程序）：
```yaml
baseline_audit_program:
  - objective: 验证[记录对象]是否完整记录
  - sample_criteria: [时间段]的[业务样本]
  - evidence_source: [台账/系统记录]
  - test_steps: [检查台账完整性, 核对记录与实物, 检查要素]
  - pass_criteria: [标准描述]
```

> ⚠️ 注意：baseline_audit_program只是程序基线模板，不是完整审计程序。
> 完整的审计程序由internal-audit-program-generator在Phase 3生成。

---

### 5. 流程型控制提取（Process-Embedded Control Extraction）

> **本方法与前述1-4类关键词方法并行使用**，解决流程型描述中的隐含控制识别问题。

#### 适用场景

当制度文本中的控制信息**嵌入在流程描述中**而非以"控制语言"（审批/分离/定期/记录）声明时，使用本方法。

**典型流程型控制**：
- "仓库核对送货单与采购订单后签收入库" → 隐含审批控制 + 职责分离
- "一联交财务，一联留存" → 隐含文档流转控制
- "同时通知质检部取样检验" → 隐含职责分离（收货≠检验）

#### 提取方法

**不直接搜索关键词**，而是通过流程重建间接识别：

```
流程描述文本 → 角色-动作-对象三元组 → 流程序列 → 节点控制分析 → 流程型控制点
```

**节点控制分析四维检视**：

| 检视问题 | 命中条件 | 对应控制类型 | 示例 |
|---------|---------|-------------|------|
| 这个动作是否需要授权？ | 动作属于核准/核对/确认性质 | 审批权限控制 | "核对无误后签收"→隐含审批 |
| 这个动作和前后动作是否可由同一人执行？ | 相邻节点角色相同但逻辑上应分离 | 职责分离控制 | "仓库收货"→"仓库做账"→应分离 |
| 这个动作是否有触发条件或执行频率？ | 有频率/条件标注但无独立验证 | 定期检查控制 | "每月末盘点"→有频率但需确认有独立监盘 |
| 这个动作是否有书面输出物？ | 节点产生单据、记录、报告 | 文档记录控制 | "填入库单一联财务"→隐含记录 |

#### 来源标注

流程型提取的每个控制点必须标注 `source_method`，取值：
- `【流程重建】`：纯流程重建识别，原文无显性控制语言
- `【流程重建-交叉验证】`：流程重建识别且原文有关联性控制语言（非直接关键词命中）
- `【规则型+流程重建】`：两种方法都识别到的控制点（合并保留）

#### 与关键词方法的协作机制

| 场景 | 优先方法 | 说明 |
|------|---------|------|
| 原文有显性控制语言 | 关键词方法 | 规则型优先级高于流程重建 |
| 原文无显性控制语言但有流程描述 | 流程重建 | 流程重建补充规则型遗漏 |
| 两种方法都识别到同一控制 | 合并 | 标注 `【规则型+流程重建】` |
| 两种方法结论冲突 | 规则型为准 | 标注冲突解决方式 |

#### 详细规范

详见 [process_reconstruction.md](./process_reconstruction.md)

---

## JSON输出格式规范

### control_points 字段结构

```json
{
  "control_points": [
    {
      "id": "CP-001",
      "type": "审批权限控制|职责分离控制|定期检查控制|文档记录控制",
      "requirement": "制度原文要求",
      "source": "第3.2条",
      "source_file": "采购管理制度",
      "source_version": "v2.1",
      "source_method": "规则型|流程重建|规则型+流程重建",
      "extraction_detail": "节点分析：核对动作属于核准性质，隐含审批控制",
      "rule_text_found": true|false,
      "business_area": "采购审批",
      "risk_level": "高|中|低",
      "design_effectiveness": "有效|无效|部分有效",
      "design_issue": "设计无效时的原因说明",
      "version_status": "新增|修改|删除|不变",
      "baseline_audit_program": {
        "objective": "验证大额采购是否经过适当审批",
        "sample_criteria": "金额>5万元的采购订单",
        "evidence_source": "ERP系统审批记录",
        "test_steps": ["获取记录", "检查审批", "验证时间"],
        "pass_criteria": "100%有总经理审批记录"
      }
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 控制点编号，格式 CP-XXX |
| `type` | enum | 控制点类型：审批权限、职责分离、定期检查、文档记录 |
| `requirement` | string | 制度原文的具体要求 |
| `source` | string | 来源条款位置 |
| `source_file` | string | 来源文件名 |
| `source_version` | string | 来源文件版本 |
| `source_method` | enum | 提取方法：规则型（关键词命中）、流程重建（流程型推断）、规则型+流程重建（双通道合并） |
| `extraction_detail` | string | 提取推理过程说明（流程重建方法必填，说明四维检视的哪一维命中） |
| `rule_text_found` | bool | 原文是否存在显性控制语句（流程重建方法标记为false） |
| `business_area` | string | 所属业务领域 |
| `risk_level` | enum | 高/中/低 |
| `design_effectiveness` | enum | 设计有效性判断：有效/无效/部分有效 |
| `design_issue` | string | 设计无效时的原因说明 |
| `version_status` | enum | 版本变化状态 |
| `baseline_audit_program` | object | 程序基线模板（供program-generator消费） |
