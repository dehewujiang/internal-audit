# Finding JSON Schema

> **使用说明**：在生成 finding 时，按此 schema 输出 JSON 文件。写入路径为 `internal-audit-workspace/findings/F-YYYY-NNN.json`。

## 完整 Schema

```json
{
  "schema_version": "1.2.0",
  "finding_id": "F-2026-001",
  "origin": "design|execution",
  "design_observation_id": "D-001",
  "audit_program": "存货管理审计",
  "audit_date": "2026-04-03",
  "category": "内控缺陷|舞弊风险|合规问题|效率问题",
  "risk_level": "高|中|低",
  "title": "一句话描述问题（格式：[主体][具体行为/状态][量化程度或时间范围]）",
  "description": "详细描述",
  "criteria": "审计依据（引用具体制度条款/行业标准，不得用模糊表述）",
  "condition": "实际发现的情况（必须包含：时间范围+样本总量+异常数量+异常比例+代表性案例）",
  "cause": "根本原因分析（必须追溯至控制设计层或控制环境层，禁止停在'操作人员未遵守'）",
  "cause_category": "ENV-01|ENV-02|ENV-03|ENV-04|DES-01|DES-02|DES-03|DES-04|DES-05|EXEC-01",
  "consequence": "潜在影响（量化实际损失或估算潜在损失，包含非财务影响）",
  "recommendation": "整改建议（针对根因+具体措施+验收标准+建议时限）",
  "responsible": "整改责任人",
  "deadline": "整改期限",
  "status": "待整改",
  "verification_method": "设计观察的实地验证方法（仅origin=design时填写）",
  "evidence": [
    {
      "name": "文件名",
      "source": "来源系统",
      "source_type": "system_export|manual_record|photo|text_description",
      "reliability_grade": "A|B|C|D|E",
      "obtained_date": "获取日期",
      "obtained_by": "获取人",
      "storage_path": "存储路径",
      "integrity_hash": "哈希值（如有）",
      "completeness": "complete|partial|insufficient"
    }
  ],
  "related_procedures": ["关联的审计程序"],
  "related_control": "CP-XXX",
  "evidence_completeness": {
    "coverage": "complete|partial|insufficient",
    "time_range_match": true,
    "sample_size_adequate": true,
    "source_reliability": "high|medium|low",
    "cross_source_consistent": true,
    "overall_rating": "充分|部分充分|不足"
  },
  "data_analysis": {
    "total_records": 0,
    "flagged_records": 0,
    "flag_rate": "0%",
    "financial_impact": 0
  },
  "intuition_analysis": {
    "constellation_detected": {
      "name": "星座名称|null",
      "confidence": "高|中|低|null",
      "elements_matched": ["要素1", "要素2"],
      "elements_missed": ["要素3"],
      "exclusion_checked": true,
      "exclusion_result": "无合理排除理由|有合理排除理由"
    },
    "counter_intuitive_flags": ["红旗1", "红旗2"],
    "temporal_patterns": ["时间模式1"],
    "second_order_thinking": {
      "covering_up": "掩盖检验分析",
      "beneficiary": "受益者检验分析",
      "cascade_failure": "连锁失效检验分析",
      "timing": "时机检验分析"
    },
    "recommendation": "建议扩大调查范围|null"
  },
  "professional_skepticism": {
    "simplest_explanation": "最简解释检验结果",
    "independent_verification": "独立验证检验结果",
    "fraud_cover_test": "舞弊掩盖检验结果",
    "alternative_explanation": "替代解释检验结果",
    "evidence_sufficiency": "证据充分性检验结果",
    "doubtful_count": 0,
    "overall_pass": true
  },
  "management_response": {
    "response": "被审计方回复内容",
    "response_date": "回复日期",
    "management_action_plan": "管理层整改计划",
    "target_completion_date": "计划完成日期",
    "auditor_assessment": "充分|不充分|需补充证据"
  },
  "business_validation": {
    "overall_assessment": "业务现实性评估结论",
    "score": 8.5,
    "key_gaps": ["发现与业务现实的偏差"],
    "recommendations": ["对 finding 描述的修正建议"]
  },
  "debate_sessions": [
    {
      "role": "辩论角色名",
      "difficulty": "初级|中级|高级",
      "key_points": "关键论点摘要",
      "conclusion": "审计方应对策略"
    }
  ]
}
```

## 字段约束

### evidence[].storage_path

| 来源 | 填写方式 | 示例 |
|------|---------|------|
| 从 evidence 目录读取 | 自动填入文件的完整相对路径 | `evidence/存货管理审计_2025年度/A-001_入库完整性穿行测试/SAP入库记录.xlsx` |
| 通过对话发送 | 手动填写"对话中发送"，无法指向文件系统 | `对话中发送` |

**硬规则**：evidence 目录读取的证据，`storage_path` 必须填写实际路径，不得留空。

### evidence[].reliability_grade

| 等级 | 含义 | 示例 | 结论可信度 |
|:----:|------|------|-----------|
| A | 系统直接导出（含时间戳） | SAP事务代码导出清单 | 高 |
| B | 系统截图/PDF报表 | 系统审批流程截图 | 中高 |
| C | 手工记录 | 手工盘点表 | 中等 |
| D | 口头描述 | 员工访谈记录 | 低 |
| E | 第三方证据 | 银行流水、工商信息 | 最高 |

**硬规则**：
- 每个 evidence 条目必须标注 `reliability_grade`
- 无精确匹配时，取最接近的较低等级
- 高风险 finding 必须有 ≥1 个 A级或E级证据支撑，否则标记"证据等级不足"

### origin

| 值 | 含义 | 必填字段 | 示例 |
|----|------|---------|------|
| `design` | 设计观察经实地验证后升级 | design_observation_id, verification_method | "制度未规定呆滞料处理流程，导致300万元呆滞料积压" |
| `execution` | 制度有规定但实际未执行 | 无额外必填 | "制度要求每月盘点，实际Q1仅盘点1次" |

### management_response

| 字段 | 说明 |
|------|------|
| response | 被审计方回复内容 |
| response_date | 回复日期 |
| management_action_plan | 管理层整改计划 |
| target_completion_date | 计划完成日期 |
| auditor_assessment | 审计师评估：充分/不充分/需补充证据 |
