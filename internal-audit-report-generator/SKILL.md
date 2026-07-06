---
name: internal-audit-report-generator
description: |
  为汽车零部件企业内部审计工作生成结构化审计报告。
  技术实现: JSON配置 + _shared核心库 + Python脚本
  
  新增功能（v2.0）: findings → Excel 报告（发现汇总 / 评分表 / 管理层反馈）
  
  使用: report_generator.py --template full|summary
---

# 内部审计报告生成器

## 核心定位

**我是 Flan 专属的审计报告助手**，不是通用文档生成器。

**工作流定位**：
```
[审计程序生成器] → 执行审计 → [审计报告生成器] → 交付报告
      ↑_______________________________________________↓
                     发现记录（findings/*.json）
```

**设计原则**：
1. **结构化记录** — 强制填写关键字段，避免遗漏
2. **模板化生成** — 套用标准模板，格式统一
3. **渐进式积累** — findings 可复用、可追溯
4. **质量透明** — AI 生成内容质量可评估、可追踪

---

## 核心功能

### 功能1：管理审计发现（Finding Management）

**时机**：审计执行完成后，生成报告前

**职责边界**：本功能负责读取和管理已由 `audit-execution-assistant` 生成的 finding，不替代执行过程中的逐项取证。

**Finding 数据结构**（与 audit-execution-assistant schema 1.2.0 对齐）：

```json
{
  "schema_version": "1.2.0",
  "finding_id": "F-YYYY-NNN",
  "origin": "design|execution",
  "design_observation_id": "D-XXX|null",
  "audit_program": "审计程序名称",
  "audit_date": "2026-04-03",
  "category": "内控缺陷|舞弊风险|合规问题|效率问题",
  "risk_level": "高|中|低",
  "title": "一句话描述问题",
  "criteria": "审计依据（具体制度条款）",
  "condition": "实际发现的情况（量化）",
  "cause": "根本原因分析（到达控制设计/环境层）",
  "cause_category": "ENV-01|DES-01|DES-02|...",
  "consequence": "潜在影响（量化）",
  "recommendation": "整改建议（具体可执行）",
  "responsible": "整改责任人",
  "deadline": "整改期限",
  "status": "待整改|整改中|已整改|延期",
  "evidence": [{"name": "...", "source": "...", "reliability_grade": "A|B|C|D|E"}],
  "related_procedures": ["关联的审计程序"],
  "related_control": "CP-XXX",
  "management_response": {
    "response": "被审计方回复",
    "response_date": "回复日期",
    "management_action_plan": "整改计划",
    "target_completion_date": "计划完成日期",
    "auditor_assessment": "充分|不充分|需补充证据"
  }
}
```

**支持输入方式**：
- 交互式增强表单（推荐）：使用 `finding_capture_guide.md` 提供的Markdown表格引导填写
* 逐字段模式：回复 `字段=值`
* 批量模式：一次性发送多行字段
* 自然语言提取：粘贴描述自动解析
- 从自然语言提取：解析自由文本生成结构化数据

👉 **快速开始**：直接说"/new-finding"或"记录一个审计发现"

---

### 功能2：生成审计报告（Report Generation）

**时机**：审计完成后，需要输出正式报告

**报告类型**：

| 类型 | 文件 | 适用场景 |
|------|------|----------|
| 常规内部审计报告 | `templates/standard-audit-report.md` | 年度/季度例行审计 |
| 专项审计报告 | `templates/special-audit-report.md` | 废料/采购/销售等专项 |
| 舞弊调查报告 | `templates/fraud-investigation-report.md` | 舞弊专项（机密格式） |
| 整改跟踪报告 | `templates/follow-up-report.md` | 后续复查 |

**报告生成流程**：
1. **选择模板** → 2. **关联 findings** → 3. **填充变量** → 4. **生成输出**

**模板变量**（使用 `{{变量名}}` 占位）：
- `{{COMPANY_NAME}}` — 公司名称（从 about-me.md 读取）
- `{{AUDIT_PERIOD}}` — 审计期间
- `{{AUDIT_PROGRAM}}` — 审计程序名称
- `{{FINDINGS_COUNT}}` — 发现总数
- `{{FINDINGS_HIGH}}` / `{{FINDINGS_MEDIUM}}` / `{{FINDINGS_LOW}}` — 各风险级别数量
- `{{FINDINGS_ORIGIN_DESIGN}}` — origin="design" 的发现数量（制度设计缺陷经证实）
- `{{FINDINGS_ORIGIN_EXECUTION}}` — origin="execution" 的发现数量（制度有规定但未执行）
- `{{DESIGN_OBSERVATIONS_COUNT}}` — design-assessments/ 中未验证的设计观察数量
- `{{DESIGN_OBSERVATIONS_PENDING}}` — 待验证的设计观察清单
- `{{REPORT_DATE}}` — 报告日期（必须具体到日，禁止 `[  ]月[  ]日` 等占位符）
- `{{LEAD_AUDITOR}}` — 审计组长
- `{{OVERALL_CONCLUSION}}` — 综合结论（详见下方强制规则）

---

## 执行流程

### 场景1：基于已有发现生成报告

```
用户：把最近的3个发现汇总成一份报告

Step 1: 列出可用 findings（让用户选择）
Step 2: 询问报告类型
Step 3: 询问基本信息（审计期间、被审计部门、审计组长）
Step 4: 读取模板 → 填充变量 → 生成报告
Step 5: 询问保存位置
```

> ⚠️ 注意：逐项记录 finding 请使用 `audit-execution-assistant`，本技能仅负责审计完成后的发现汇总和报告生成。

### 场景3：与程序生成器联动

```
用户：基于刚才生成的废料处置程序，写一份执行报告

Step 1: 读取最近生成的审计程序文档（程序生成器输出）
Step 2: 提取"审计目标、范围、程序"作为报告背景章节
Step 3: 读取 findings/ 中已生成的发现（由 audit-execution-assistant 在执行过程中生成）
Step 4: 填充模板 → 生成带"已执行程序清单"的报告
```

### 场景4：完整审计报告（含制度设计评估）

```
用户：生成存货管理审计报告

Step 0: 读取 about-me.md（获取公司背景）
Step 1: 读取 design-assessments/*.md（制度设计评估）
        → 提取设计观察（design observations）
        → 注意：这些是未经实地验证的假设，不是审计发现
Step 2: 读取 findings/*.json（审计发现）
         → 按 origin 分类：design（经证实的设计缺陷）vs execution（执行类问题）
         → 按 risk_level 分类
         → 计算 {{FINDINGS_ORIGIN_DESIGN}} 和 {{FINDINGS_ORIGIN_EXECUTION}}
         → design类发现 → 填充第4.1章"设计类发现"
         → execution类发现 → 填充第4.2章"执行类发现"
Step 3: 读取 audit-programs/*.md（已执行程序）
        → 提取程序清单作为背景
Step 4: 选择报告模板
Step 5: 生成报告，结构如下：
        1. 审计背景与范围
        2. 已执行程序清单
        3. 制度设计评估（来自 design-assessments/）
           3.1 设计观察（未经实地验证的假设）
           3.2 制度冲突
           3.3 制度缺失
        4. 审计发现（来自 findings/，已经实地验证）
           4.1 设计类发现（origin="design"，制度设计缺陷经证实导致问题）
           4.2 执行类发现（origin="execution"，制度有规定但未执行）
           4.3 发现详情
         5. 综合结论（强制，详见下方"综合结论强制规则"）
            5.1 总体判断：内部控制整体有效/部分有效/无效
            5.2 系统性风险评级：高风险/中风险/低风险
            5.3 核心问题排序：按严重程度列出TOP 3问题
            5.4 与上期审计对比：新发现/重复发现/已整改/未整改（如有）
         6. 整改建议
            6.1 制度完善建议（针对设计类发现和设计观察）
            6.2 执行改进建议（针对执行类发现）
Step 6: 调用 internal-audit-evaluator 附加质量评估
Step 7: 保存到 reports/
```

### 综合结论强制规则（CRITICAL）

**所有场景下的报告生成都必须包含综合结论章节，禁止跳过。**

综合结论必须包含以下四要素，按顺序输出：

**5.1 总体判断** — 一句话总结审计结果：
```
示例格式：
"本次审计认为，公司存货管理内部控制 [整体有效/部分有效/无效]，[存在N项高风险问题需要立即整改]。"
```
判定逻辑：
| 高风险finding数量 | 总体判断 |
|:-----------------:|---------|
| 0 | 整体有效 |
| 1-2 | 部分有效 |
| ≥3 | 无效 |

**5.2 系统性风险评级** — 判断问题是系统性的还是孤立的：
```
- 系统性风险：该问题在同一流程/同一部门/同一系统中重复出现（如多个仓库都存在盘点问题）
- 孤立风险：该问题仅出现在单一环节或单一部门
```

**5.3 核心问题排序** — 按严重程度列出TOP 3问题，每项包含：
```
1. [问题名称]（风险等级）
   影响：一句话说明对业务的实际影响
   整改紧迫性：立即/1个月内/3个月内
```

**5.4 与上期审计对比** — 如有历史审计数据：
```
- 新发现：N项
- 重复发现：N项（上一期已指出但未整改）
- 已整改：N项（上一期问题已关闭）
- 未整改：N项（上一期问题仍未解决）
```

### 占位符禁止规则（新增）

**禁止在最终输出的报告中出现任何未填写的模板占位符**：

| 禁止模式 | 示例 | 强制要求 |
|---------|------|---------|
| `[  ]月[  ]日` | `2025年[  ]月[  ]日` | 必须填具体日期，无确切日期填"待确认"并标注原因 |
| `____` 下划线 | `报告编制：____` | 原则上保留签名栏，但如是最终版本必须填实际人名 |
| `{{变量名}}` 残留在输出中 | `{{COMPANY_NAME}}` | 输出前全文搜索 `{{`，任何残留必须替换 |
| `_X_万元` | `效率损失约_X_万元` | 必须基于数据估算，见程序生成器 Step 5.4 规则 |

**重要区分**：

| 内容来源 | 存储位置 | 性质 | 报告章节 |
|---------|---------|------|---------|
| 设计观察（未验证） | design-assessments/ | 假设 | 第3章"制度设计评估" |
| 设计类发现（已验证） | findings/ (origin="design") | 结论 | 第4.1章"设计类发现" |
| 执行类发现 | findings/ (origin="execution") | 结论 | 第4.2章"执行类发现" |

---

## 存储规范

### Findings 存储位置

```
internal-audit-workspace/
├── findings/
│   ├── F-2024-001.json      # 具体发现（按年份分类，schema 1.2.0）
│   ├── F-2024-002.json
│   └── ...
└── index.json               # 发现索引（便于检索）
```

> ⚠️ 注意：finding 由 `audit-execution-assistant` 在执行审计过程中生成，本技能仅负责读取和汇总。

### index.json 结构

```json
{
  "version": "1.0",
  "total_findings": 25,
  "by_year": {
    "2024": { "count": 15, "ids": ["F-2024-001", "..."] }
  },
  "by_program": {
    "废料处置审计": ["F-2024-003", "..."],
    "采购审计": ["..."]
  },
  "by_risk": {
    "高": ["F-2024-001", "..."],
    "中": ["..."],
    "低": ["..."]
  },
  "by_status": {
    "待整改": ["..."],
    "已整改": ["..."]
  },
  "by_origin": {
    "design": ["F-2024-001", "..."],
    "execution": ["F-2024-002", "..."]
  }
}
```

---

## 质量要求

### 发现记录质量检查清单

✅ **标题**：一句话说清问题（如"废料出售价格低于市场价15%"）
✅ **风险级别**：必须有明确判断依据
✅ **审计依据**：引用具体制度/法规条款
✅ **证据链**：可验证、可追溯
✅ **整改建议**：具体、可执行
✅ **责任人+期限**：闭环管理

### 报告生成质量检查清单

✅ **所有变量**均已替换（无残留 `{{}}`）
✅ **发现汇总表**风险分布准确
✅ **日期/金额**格式统一（无 `[  ]`、`_X_` 等占位符）
✅ **综合结论**已包含全部四要素（总体判断+风险评级+TOP3排序+历史对比）
✅ **附件清单**完整
✅ **审批流程**体现

---

## 禁止事项

- ❌ 禁止生成无审计依据的"发现"
- ❌ 禁止将臆测内容写进报告
- ❌ 禁止遗漏风险级别判断
- ❌ 禁止将舞弊调查结果披露给无关人员
- ❌ 禁止在未审批前标记报告"已批准"
- ❌ 禁止跳过综合结论章节
- ❌ 禁止输出含有未替换 `{{变量名}}`、`[  ]`、`____`、`_X_` 等占位符的报告
- ❌ 禁止综合结论仅有定性描述无定量依据（必须有finding数量和风险分布支撑）

---

## 参考资料

### 共享资料（与程序生成器共用）

| 文件 | 用途 |
|------|------|
| `../internal-audit-program-generator/references/about-me.md` | 公司背景 |
| `../internal-audit-program-generator/references/my-config.md` | 操作配置 |

### 本技能专用

| 文件 | 用途 |
|------|------|
| `templates/standard-audit-report.md` | 常规内审报告模板 |
| `templates/special-audit-report.md` | 专项审计报告模板 |
| `templates/fraud-investigation-report.md` | 舞弊调查报告模板（机密） |
| `templates/follow-up-report.md` | 整改跟踪报告模板 |
| `references/report-standards.md` | 报告编制规范 |

---

## 输出格式

### 发现记录

**文件路径**：`internal-audit-workspace/findings/F-YYYY-NNN.json`

**命名规则**：`F-{年份}-{三位序号}`

```
F-2024-001 = 2024年第1号发现
F-2024-015 = 2024年第15号发现
```

### 审计报告

**默认路径**：`internal-audit-workspace/reports/审计报告_{审计主题}_YYYYMMDD.md`

**格式**：Markdown（可直接打印或导出 DOCX/PDF）

---

## Step by Step：使用指南

### Step 0：读取背景（自动）

读取 about-me.md 和 my-config.md，获取公司信息和操作配置。

### Step 1：管理审计发现

**指令**：
- "汇总审计发现"
- "列出所有待整改发现"
- "查询 F-2024-003 详情"

> ⚠️ 注意：逐项记录 finding 请使用 `audit-execution-assistant`（触发词："执行审计过程中记录异常"）。本技能仅负责审计完成后的发现管理和报告生成。

**流程**：
1. 读取 `internal-audit-workspace/findings/index.json`
2. 列出可用 findings（按风险等级/状态/origin分类）
3. 支持查询、筛选、统计

### Step 2：生成审计报告

**指令**：
- "生成审计报告"
- "基于发现 F-2024-001 到 F-2024-005 写报告"
- "把最近的发现汇总成报告"

**流程**：
1. 选择 findings（手动指定或自动列出）
2. 选择报告模板
3. 填写报告基本信息
4. 填充模板，生成报告
5. **调用评估中枢** → 输出质量评估报告
6. 询问保存位置；报告末尾自动附加质量评估

### Step 3：质量评估（引用评估框架）

**执行前加载**：`D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/SKILL.md`，定位 **audit_report** 的检查清单。

**时机**：报告模板填充完成后，输出前自动执行。

#### 3.1 格式检查

| 检查项 | 执行方式 | 自动修正？ |
|--------|---------|:---------:|
| 模板变量替换完整性 | 全文搜索 `{{` `[  ]` `____` 占位符 | ✅ 发现即替换 |
| 发现汇总表准确性 | 汇总表中的高风险数量是否与实际 finding 数一致 | ⚠️ 通知用户确认 |

#### 3.2 推理检查：综合结论完整性

检查报告是否包含综合结论章节（第4章），并逐项验证四要素：

```
① 【总体判断】是否存在"整体有效/部分有效/无效"的判断语句？
② 【风险评级】是否存在系统性 vs 孤立的判断？
③ 【TOP3排序】是否按严重程度列出核心问题（每项含影响+紧迫性）？
④ 【历史对比】如有历史审计数据，是否存在对比？（如有则检查）
   → 从 findings/index.json 获取历史数据
```

**输出格式**：

```
综合结论完整性检查：
├─ ✅/❌ 总体判断：[存在/缺失]，内容：[判断语句]
├─ ✅/❌ 风险评级：[存在/缺失]
├─ ✅/❌ TOP3排序：[存在/缺失]，覆盖高风险finding？[是/否]
└─ ✅/❌ 历史对比：[存在/缺失/无历史数据]
```

#### 3.3 推理检查：发现-建议一致性

取报告中 risk_level="高" 的所有 finding，逐项检查：
- 报告第5章（管理建议）中是否有对应的整改建议
- 建议是否针对根因（而非表面问题）

发现任何高风险 finding 在管理建议中没有对应整改 → 标记 ❌

#### 3.4 质量判定

| 条件 | 判定 | 文档标记 |
|:----:|------|---------|
| 所有检查通过 | ✅ 可直接输出 | 无 |
| 仅格式检查 ❌（已自动修正）| ⚠️ 修正后输出 | 无 |
| 综合结论缺核心要素 | ⚠️ 建议补充 | ⚠️ |
| 高风险finding无对应整改建议 | 🔴 质量待审 | 🔴 |

#### 3.5 结果存储与质量门

评估完成后，将检查结果写入历史库并执行质量门：

```bash
echo '{json格式检查结果}' > /tmp/eval_result.json
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/record_evaluation.py --input /tmp/eval_result.json
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/quality_gate.py --input /tmp/eval_result.json
```

### Step 4：跟踪整改进度（可选）

**指令**：
- "查询 F-2024-003 整改进度"
- "列出所有待整改发现"
- "生成整改跟踪报告"

**功能**：
- 更新 finding 的 status 字段
- 生成整改跟踪报告
- 计算整改率等统计指标
