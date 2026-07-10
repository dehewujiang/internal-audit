---
name: internal-audit-evaluator
description: |
  内部审计内容质量评估框架。
  为审计程序、审计发现、审计报告、政策分析、访谈问卷5种内容类型定义检查清单。
  不包含评估逻辑的Python实现，所有评估由 LLM 在各自 Skill 的 Step 5 中按本框架执行。
  （v2.0 重构：从 Python 关键词计数迁移到 LLM 结构化推理评估）
---

# 审计内容质量评估框架

## 定位

**本文件不是执行代码，是权威定义。** 定义每种内容类型的检查清单和质量判定规则。各 Skill 的 Step 5 引用本框架，按对应检查清单执行评估。

```
internal-audit-evaluator/SKILL.md  ← 你在这里审查评估标准
        ↓ 引用
program-generator/SKILL.md Step 5  ← 实际执行评估
execution-assistant/SKILL.md Step 5
report-generator/SKILL.md Step 5
document-organizer/SKILL.md Step 5
interview-designer/SKILL.md Step 5
```

## 评估类型

所有检查项归为三类：

| 类型 | 含义 | 耗时 | 典型检查 |
|------|------|------|---------|
| **格式检查** | 输出是否符合约定的格式和schema | ~30s | 占位符残留、JSON schema、必填字段 |
| **推理检查** | 输出中的推理链是否完整、可信 | ~2min | 事实锚定、程序映射、根因深度、证据等级 |
| **行动检查** | 评估结果是否触发了行动 | ~10s | 低于阈值是否标记、是否写入历史 |

## 每种内容类型的检查清单

### audit_program（审计程序）

| 检查项     | 类型  | 说明                    | 执行方式         |
| ------- | :-: | --------------------- | ------------ |
| 模板完整性   | 格式  | 扫描全文 {{ 和 _X_ 占位符     | 全文搜索         |
| 量化标准真实性 | 格式  | 量化标准字段中是否有开关型判断（是/否）  | 扫描所有表格的量化标准列 |
| 风险点事实锚定 | 推理  | 前3个高风险风险点 × 是否≥2条事实支撑 | 推理链回溯        |
| 风险-程序映射 | 推理  | 高风险风险的测试程序能否实际检测该风险   | 逐项比对         |
| 轨道D唯一性  | 推理  | 边界探测的风险是否为公司独有        | 逐项判断         |
| 效率损失估算  | 推理  | _X_ 占位符是否已替换为基于数据的估算  | 检查轨道E        |

### finding（审计发现）

| 检查项 | 类型 | 说明 | 执行方式 |
|--------|:----:|------|---------|
| JSON schema 合规 | 格式 | 必填字段是否完整 (finding_id, origin, title, criteria, condition, cause, recommendation, evidence) | schema 校验 |
| 证据等级完整性 | 格式 | 所有 evidence 条目是否有 reliability_grade | 逐条检查 |
| 证据等级充分性 | 推理 | 高风险finding是否有 ≥1 个 A级或E级证据 | 检查证据数组 |
| 根因分析深度 | 推理 | cause 是否到达控制设计层或控制环境层（禁止停在"操作人员未遵守"） | 检查 cause 字段的抽象层级 |
| CCEER 五要素 | 格式 | Criteria, Condition, Cause, Effect, Recommendation 是否完整 | 检查每个要素存在 |
| 建议可执行性 | 推理 | recommendation 是否有具体措施 + 责任人 + 期限 | 检查建议字段 |

### audit_report（审计报告）

| 检查项 | 类型 | 说明 | 执行方式 |
|--------|:----:|------|---------|
| 模板变量替换完整性 | 格式 | 全文搜索 `{{` `[  ]` `____` 占位符 | 全文搜索 |
| 综合结论完整性 | 推理 | 结论是否包含 总体判断 + 风险评级 + TOP3排序 + 历史对比 | 检查第4章 |
| 发现-建议一致性 | 推理 | 每个高风险finding是否有对应的整改建议 | 逐项比对 |
| 风险分布合理性 | 推理 | 高风险finding与报告总体判断是否一致 | 高风险≥3但"总体判断=有效"则标记矛盾 |

### policy_analysis（政策分析）

| 检查项 | 类型 | 说明 | 执行方式 |
|--------|:----:|------|---------|
| JSON schema 合规 | 格式 | 控制点、风险点、控制缺口数组是否存在 | schema 校验 |
| 跨文件引用完整性 | 推理 | 标注"待确认"的项是否有后续确认记录 | 检查 verification_status |
| 控制点可追溯性 | 推理 | 每个控制点是否指向原文具体条款（非概括性描述） | 检查 source_section |

### interview（访谈问卷）

| 检查项 | 类型 | 说明 | 执行方式 |
|--------|:----:|------|---------|
| 开放式问题比例 | 格式 | 非"是否"类问题占比是否≥70% | 扫描问题列 |
| 问题-制度关联 | 推理 | 每个问题是否有对应的制度依据 | 检查制度依据列 |
| 探测性问题锚定性 | 推理 | 探测性问题是否基于公司具体特征（非行业通用） | 逐条判断 |

## 质量判定规则

每个 Skill 的 Step 5 执行完检查清单后，按以下规则输出判定：

| 条件 | 判定 | 文档标记 | 是否需要用户确认？ |
|------|------|---------|:----------------:|
| 所有检查项通过 | ✅ 可直接使用 | 无 | 否 |
| 仅格式检查项不通过 | ⚠️ 建议修正后使用 | ⚠️ 标记在文档开头 | 否（LLM可自动修正） |
| 推理检查项 1-2 项不通过 | ⚠️ 建议审查后使用 | ⚠️ | 是 |
| 推理检查项 ≥3 项不通过，或任意事实锚定检查不通过 | 🔴 质量待审 | 🔴 标记在文档开头 + 红色分隔线 | 是，建议重生成 |
| JSON schema 不通过 | 🔴 格式错误，禁止输出 | — | 是，必须修正后重输 |

**自动修正规则**：格式检查不通过时，LLM 应自动修正后重新输出，无需用户介入。"自动修正"不包括推理检查——推理问题必须由用户判断。

## 结果存储

所有 Step 5 执行后，评估结果写入 `storage.py` 的 JSONL 历史库：

```python
# 每个 Skill 的 Step 5 执行结束后，调用 storage.save_evaluation()
# 记录内容：eval_id, content_type, timestamp, overall_judgment, checks[]
# overall_judgment: "pass" | "warn" | "fail"
# checks: 每个检查项的 {name, result, detail}
```

这使你可以随时查询历史质量趋势：
- `get_score_trend(30)` → 最近30天各内容类型的质量波动
- `load_evaluations(content_type="audit_program", min_score=7)` → 找质量低于7分的程序
- `export_to_csv("evaluation_history.csv")` → 导出给管理层看

## 本框架的修改流程

如需增减检查项：

```
1. 修改本文件（internal-audit-evaluator/SKILL.md）
2. 对应 Skill 的 Step 5 自动引用新检查项
3. 如果你看到哪个 Skill 的输出评估不符合本框架，那是我执行错了，告诉我修正
```

## 与旧版的兼容

v2.0 废弃了以下文件和模块：
- `hub.py` — 评估中枢（死代码，从未被实际调用）
- `evaluators/program_quality.py` — 关键词计数评估器（替代为推理链回溯）
- `evaluators/context_validation.py` — 含语法错误，从未成功运行
- `evaluators/evidence_rating.py` — 关键词计数评估器（替代为 reliability_grade 校验）
- `evaluators/__init__.py` 中的 @evaluator 装饰器、_EVALUATORS 注册表（不再需要）

保留：
- `storage.py` — JSONL 历史存储（正常工作中，继续使用）
- `formatter.py` — Markdown 渲染（可能需调整，但核心逻辑保留）
