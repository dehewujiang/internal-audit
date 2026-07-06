# 设计观察输出格式规范

## 目的

为 Phase 4（审计执行）提供可验证的设计观察清单，使 execution-assistant 的"设计观察→Finding 升级路径"生效。

## 筛选规则

从分析结果中筛选以下条目作为设计观察：

- `control_gaps[]` where `verification_status="已确认"` 或 `verification_status="待确认"`
- `risk_points[]` where `severity="高"`
- `control_points[]` where `design_effectiveness="无效"`
- `conflicts[]` 全部

## 编号规则

每个设计观察分配 `D-XXX` 编号，从 D-001 开始顺序递增。

## JSON输出格式

### 基础格式（Phase 1 document-organizer 来源）

```json
{
  "schema_version": "1.0.0",
  "audit_topic": "存货管理",
  "generated_date": "2026-04-03",
  "design_observations": [
    {
      "id": "D-001",
      "type": "control_gap",
      "source": "document-organizer",
      "title": "直拨外协材料缺乏财务对账机制",
      "description": "NPM007规定直拨外协材料由采购员签字确认，但未规定财务月度对账和独立监督",
      "source_doc": "NPM007材料仓库管理标准G版",
      "source_section": "第1.3节",
      "severity": "高",
      "verification_method": "抽查过去6个月直拨外协材料对账记录",
      "related_control": "CP-N007-02",
      "status": "pending",
      "verified_by_finding": null
    }
  ],
  "summary": {
    "total_observations": 1,
    "by_severity": { "高": 1, "中": 0, "低": 0 },
    "by_type": { "control_gap": 1 }
  }
}
```

### interview 来源追加格式（Phase 1.5 interview-designer 模式B）

interview 来源的条目追加到同一文件的 `design_observations[]` 数组，与 document-organizer 条目共存。`id` 编号连续。

```json
{
  "id": "D-015",
  "type": "risk_clue",
  "source": "interview",
  "source_role": "操作员",
  "source_id": "仓管员-李某",
  "interview_snippet": "成品丝30天到了系统不会报警，都是我们自己去翻台账才知道超期了",
  "title": "成品丝超期无系统预警（访谈确认）",
  "description": "仓管员反馈成品丝/中间丝存储到期系统无自动预警，依赖人工翻台账发现超期",
  "severity": "高",
  "verification_method": "抽查当前库存中第25-35天的成品丝，检查是否有系统预警记录",
  "status": "pending",
  "contradiction": [
    {
      "with_observation": "D-012",
      "content": "生管部长王某称系统有预警功能",
      "source_id": "生管部长-王某"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `id` | string | ✅ | 设计观察编号，格式 D-XXX |
| `type` | enum | ✅ | 类型：control_gap / design_ineffective / risk_point / conflict / risk_clue |
| `source` | string | ✅ | 来源："document-organizer"（Phase 1）或 "interview"（Phase 1.5） |
| `title` | string | ✅ | 一句话描述 |
| `description` | string | ✅ | 详细描述 |
| `source_doc` | string | ❌ | 来源制度文件（interview 来源可空） |
| `source_section` | string | ❌ | 来源条款位置（interview 来源可空） |
| `severity` | enum | ✅ | 严重程度：高/中/低 |
| `verification_method` | string | ✅ | 实地验证方法 |
| `related_control` | string | ❌ | 关联的控制点编号 |
| `status` | enum | ✅ | 状态：pending / verified / rejected |
| `verified_by_finding` | string | ❌ | 验证后生成的Finding编号 |

#### interview 来源专属字段（source="interview" 时必填）

| 字段 | 类型 | 说明 |
|------|------|------|
| `source_role` | enum | 受访者层级：操作员 / 中层 / 高层 / 第三方 / 匿名 |
| `source_id` | string | 受访者识别码，格式"岗位-姓氏"，如"仓管员-李某" |
| `interview_snippet` | string | 受访者原话引用（最少一句话），不得概括转述 |
| `contradiction` | array | 矛盾记录，格式 `[{with_observation, content, source_id}]` |

---

## Markdown输出格式

```markdown
# {审计主题} 设计观察

## 设计观察清单

| 编号 | 类型 | 标题 | 严重程度 | 来源制度 | 验证方法 | 状态 |
|------|------|------|---------|---------|---------|------|
| D-001 | control_gap | ... | 高 | ... | ... | pending |

## 详细说明

### D-001：{标题}
- **类型**：control_gap
- **描述**：...
- **来源**：《制度名称》第X条
- **严重程度**：高
- **验证方法**：...
- **状态**：pending（待Phase 4实地验证）
```

## 与 Finding 的升级关联

- Phase 4 执行审计时，execution-assistant 读取 `design-assessments/` 中的设计观察
- 针对每个 `D-XXX` 执行 `verification_method` 中定义的验证程序
- 验证通过 → 生成 `finding`，`origin="design"`，`design_observation_id="D-XXX"`
- 验证不通过 → 标记 `status="rejected"`，保留在 design-assessments/ 中

### interview 来源的特殊处理

interview 来源（`source="interview"`）的设计观察在执行验证时，需额外注意：

1. **`source_role` 决定验证优先级**：操作员来源（低权重）必须 ≥2 个独立信源交叉验证才能升级为 finding；中层/高层来源可直接作为验证起点
2. **`contradiction` 非空时**：验证程序必须包含"矛盾点排查"——例如同时访谈双方对质，或调取系统日志作为客观证据
3. **`interview_snippet` 在 finding 中引用**：如果 interview 来源的设计观察升级为 finding，`interview_snippet` 必须作为证据条目写入 finding 的 `evidence[]` 数组，标注 `reliability_grade="D"`（口头描述）
