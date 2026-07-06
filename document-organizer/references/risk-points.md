# 风险点识别规范

## 风险点类型及识别方法

### 1. 流程断裂点

**定义**：流程中缺少必要环节或环节衔接不当

**识别方法**：
- 分析流程图中的断点
- 识别缺少的环节（如：审批后无验收）
- 识别环节顺序不合理

---

### 2. 权限集中点

**定义**：某人或某岗位权力过大，缺乏制衡

**识别方法**：
- 查找"全权负责"、"一人审批"
- 分析岗位职责描述
- 识别一人兼任多个不相容岗位

---

### 3. 监督盲区

**定义**：某些活动缺乏监督或检查

**识别方法**：
- 查找缺少"检查"、"监督"、"复核"的环节
- 识别无人负责的活动
- 识别长期未检查的活动

---

### 4. 信息不对称点

**定义**：某些信息只有特定人员掌握，缺乏透明度

**识别方法**：
- 查找"仅某人知晓"、"保密"、"内部掌握"
- 识别缺乏共享的信息
- 识别缺乏对账的信息

---

## JSON输出格式规范

### risk_points 字段结构

```json
{
  "risk_points": [
    {
      "id": "RP-001",
      "type": "流程断裂|权限集中|监督盲区|信息不对称",
      "description": "风险描述",
      "source": "第4.1条",
      "severity": "高|中|低",
      "related_control": "CP-XXX|CG-XXX|null",
      "related_control_status": "有效|无效|缺失",
      "recommendation": "改进建议"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 风险点编号，格式 RP-XXX |
| `type` | enum | 风险类型：流程断裂、权限集中、监督盲区、信息不对称 |
| `description` | string | 风险详细描述 |
| `source` | string | 来源条款位置 |
| `severity` | enum | 严重程度：高/中/低 |
| `related_control` | string | 关联的控制点编号或控制缺陷编号 |
| `related_control_status` | enum | 关联控制的状态 |
| `recommendation` | string | 改进建议 |

---

## control_gaps 字段结构

```json
{
  "control_gaps": [
    {
      "id": "CG-001",
      "type": "制度缺失|制度过时|制度不可操作",
      "area": "涉及的业务领域",
      "expected_control": "应该有的控制",
      "actual": "实际情况",
      "verification_status": "已确认|待确认|跨文件覆盖|引用待追踪",
      "verification_note": "需确认说明",
      "cross_doc_reference": {
        "referenced_by": "采购管理制度 §6.2",
        "referenced_doc": "仓储管理制度",
        "actual_control_found": true,
        "control_id_in_other_doc": "CP-015"
      },
      "risk_level": "高|中|低",
      "recommendation": "..."
    }
  ]
}
```

### verification_status 取值

| 状态 | 含义 | 后续动作 |
|------|------|---------|
| `已确认` | 已扫描全部相关制度，确认缺失 | 可直接作为设计缺陷 |
| `待确认` | 当前分析范围内未见，但可能有未纳入的文件 | 需要用户确认 |
| `跨文件覆盖` | A文件没有，但B文件有 | 标注来源，不作为缺失 |
| `引用待追踪` | A文件引用了B文件，但B文件尚未分析 | 暂停判定，等B文件分析完成 |
