# JSON输出格式完整规范

## 根结构

```json
{
  "schema_version": "1.0.0",
  "schema_changelog": {
    "1.0.0": "初始版本"
  },
  "document_info": {
    "name": "采购管理制度",
    "version": "v2.1",
    "effective_date": "2024-01-01",
    "department": "采购部",
    "analyzed_date": "2026-04-03",
    "analyzer": "document-organizer v2.0",
    "analysis_scope": "single|batch",
    "previous_versions": ["v1.0", "v2.0"],
    "version_diff_available": true
  },
  "control_points": [...],
  "control_gaps": [...],
  "risk_points": [...],
  "conflicts": [...],
  "summary": {...}
}
```

## document_info 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 文档名称 |
| `version` | string | 版本号 |
| `effective_date` | string | 生效日期 |
| `department` | string | 适用部门 |
| `analyzed_date` | string | 分析日期 |
| `analyzer` | string | 分析工具版本 |
| `analysis_scope` | enum | single(单文件) / batch(批量) |
| `previous_versions` | array | 历史版本列表 |
| `version_diff_available` | boolean | 是否有版本对比报告 |

## summary 字段

```json
{
  "summary": {
    "total_controls": 12,
    "effective_controls": 8,
    "ineffective_controls": 3,
    "control_gaps": 1,
    "risk_points": 4,
    "conflicts": 1,
    "overall_design_rating": "良好|需改进|存在重大缺陷",
    "version_changes_summary": "v2.1相比v2.0：新增3个控制点，修改2个控制点"
  }
}
```

## conflicts 字段结构

```json
{
  "conflicts": [
    {
      "id": "CF-001",
      "description": "冲突描述",
      "doc_a": {
        "name": "...",
        "section": "...",
        "rule": "...",
        "version": "v2.1"
      },
      "doc_b": {
        "name": "...",
        "section": "...",
        "rule": "...",
        "version": "v1.3"
      },
      "risk": "...",
      "recommendation": "..."
    }
  ]
}
```

## 输出必须包含的字段

根据 SKILL.md 要求，JSON输出必须包含：
- `schema_version` 字段
- `control_points` 数组
- `control_gaps` 数组
- `risk_points` 数组
- `conflicts` 数组（如有）
- `summary` 对象
- `baseline_audit_program` 数组（每个控制点输出一个基线测试模板，供 program-generator 消费）

## baseline_audit_program 字段结构

```json
{
  "baseline_audit_program": [
    {
      "control_point_id": "PUR-AP-001",
      "objective": "测试目标（一句话）",
      "sample_criteria": "样本选择标准",
      "evidence_source": "证据来源系统/文档",
      "test_steps": ["步骤1", "步骤2", "步骤3"],
      "pass_criteria": "通过标准"
    }
  ]
}
```
