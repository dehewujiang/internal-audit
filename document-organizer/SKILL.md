---
name: document-organizer
description: |
  自动分析企业内部制度文档（管理制度、流程文件、操作手册、岗位职责、内控手册等），
  智能提取关键控制点（审批权限、职责分离、定期检查、文档记录），
  识别制度风险点（流程断裂、权限集中、监督盲区、信息不对称），
  并输出结构化的控制点清单和风险点清单，供internal-audit-program-generator消费。
---

# 企业制度文档分析器

## 概述

**document-organizer** 是一个专门用于分析企业内部制度文档的AI工具，能够自动识别制度中的控制点、风险点，并输出结构化数据（JSON+Markdown）。

**职责边界**：
- ✅ 分析制度文档，提取控制点
- ✅ 识别风险点（流程断裂、权限集中等）
- ✅ 输出baseline_audit_program模板（供program-generator消费）
- ❌ 不生成完整审计程序（由internal-audit-program-generator负责）
- ❌ 不做风险推演（由internal-audit-program-generator负责）
- ❌ 不做实质性测试设计（由internal-audit-program-generator负责）

**核心原则**：
1. **批量分析优先**：以"制度体系"为单位分析，不孤立分析单份文件
2. **跨文件验证**：追踪制度间引用关系，避免误判"缺失"
3. **双输出**：同时生成Markdown（人类可读）和JSON（机器可读）
4. **版本追踪**：识别同一制度的不同版本，自动对比差异

## 核心功能

| 功能模块 | 说明 |
|---------|------|
| **文档类型识别** | 自动识别管理制度、流程文件、操作手册、岗位职责、表单模板、内控手册 |
| **批量扫描** | 扫描文件夹，建立"文件-章节-业务领域"索引 |
| **控制点提取** | 识别审批权限控制、职责分离控制、定期检查控制、文档记录控制 |
| **风险点识别** | 发现流程断裂点、权限集中点、监督盲区、信息不对称点 |
| **跨文件验证** | 追踪制度间引用关系，检测冲突，确认缺失（verification_status） |
| **版本对比** | 识别同一制度的不同版本，自动对比差异 |
| **程序基线输出** | 为每个控制点输出baseline_audit_program模板（供program-generator消费） |
| **JSON输出** | 结构化输出，供internal-audit-program-generator消费 |

## 支持的文档类型

| 文档类型 | 用途 | 分析重点 |
|---------|------|---------|
| **管理制度** | 某业务领域的管理规定 | 审批权限、控制要求 |
| **流程文件** | 业务流程描述和流程图 | 流程节点、风险点 |
| **操作手册** | 具体操作说明 | 执行方法、控制措施 |
| **岗位职责** | 部门和岗位的职责分工 | 职责分离、权限分配 |
| **表单模板** | 各类审批单、记录表 | 信息记录要求 |
| **内控手册** | 内部控制框架 | 控制体系、监督机制 |

## 触发场景

**明确触发词**：
- "分析这个制度文档"
- "提取控制点"
- "识别制度风险"
- "分析内控文档"
- "分析 internal-audit-workspace/documents/ 文件夹中的所有制度文件"

**模糊触发（上下文判断）**：
- 用户发送制度文件并询问"这个制度有什么问题"
- 用户说"帮我看看这份管理制度"
- 用户要求"根据制度提取控制点"

## 工作流程

详见 [references/workflow.md](./references/workflow.md)

**分治法（6+文件时必须使用）**：

```
Phase A：扫描（轻量）
→ 只读文件名和目录，不读全文
→ 建立"文件-章节-业务领域"索引
→ 上下文占用：~2,000 tokens

Phase B：逐个分析（每次只读一个文件）
→ 读取文件1全文 → 分析（流程重建 + 控制点提取） → 输出文件1.JSON
→ 读取文件2全文 → 分析（流程重建 + 控制点提取） → 输出文件2.JSON
→ ...（每次只读一个文件，上下文始终在10,000 tokens以内）

Phase C：汇总（只读JSON，不读原文）
→ 读取所有JSON（每个~800 tokens）
→ 交叉验证 → 生成综合报告
→ 上下文占用：N × 800 tokens（10个文件 = 8,000 tokens）
```

## 流程重建（提取隐含控制）

详见 [references/process_reconstruction.md](./references/process_reconstruction.md)

**定位**：与关键词方法**双通道并行**。对流程型描述（角色-动作-对象序列）先重建业务流转结构，再逐节点识别隐含控制点。解决"控制嵌入在流程叙述中而非声明式语句"的问题。

**适用判断**：文档含流程描述 → 执行流程重建；纯条款式制度/表单模板 → 跳过。

## 控制点提取

详见 [references/control-points.md](./references/control-points.md)

**双通道提取机制**：

```
            ┌─ 规则型提取（关键词+语义匹配）
制度原文 ──┼─ 适用于显性控制语句
            │   控制点类型：
            │   1. 审批权限控制 — "审批"、"批准"、"签字"
            │   2. 职责分离控制 — "职责分离"、"不相容"
            │   3. 定期检查控制 — "定期"、"每月"、"每季度"
            │   4. 文档记录控制 — "记录"、"登记"、"台账"
            │
            └─ 流程型提取（流程重建 → 节点分析）
            适用于流程描述中的隐含控制
            合并去重 → 完整控制点清单
```

## 风险点识别

详见 [references/risk-points.md](./references/risk-points.md)

**风险点类型**：
1. **流程断裂点** — 流程中缺少必要环节
2. **权限集中点** — 某人权力过大缺乏制衡
3. **监督盲区** — 某些活动缺乏监督
4. **信息不对称点** — 信息只有特定人员掌握

## 关键词搜索表

详见 [references/keyword-table.md](./references/keyword-table.md)

## 行业专项分析

详见 [references/industry-specific.md](./references/industry-specific.md)

## 输出格式规范

### Markdown + JSON 双输出

**输入位置**：`internal-audit-workspace/documents/` — 待分析的源制度文档

**输出位置**：
1. `internal-audit-workspace/policy-analyses/` — 完整分析报告（人类可读 + 机器可读）
2. `internal-audit-workspace/design-assessments/` — 设计观察（供Phase 4验证升级）

### JSON输出格式

详见 [references/json-schema.md](./references/json-schema.md)

### 设计观察格式

详见 [references/design-observation-format.md](./references/design-observation-format.md)

## 边界情况处理

详见 [references/edge-cases.md](./references/edge-cases.md)

## 示例

详见 [references/examples.md](./references/examples.md)

## 依赖工具

- `Read` - 读取文档内容
- `Glob` - 批量扫描文档
- `Write` - 生成分析报告（Markdown + JSON）
- `Grep` - 关键词搜索
- **`python tools/pdf_ocr_extractor.py`** - 处理PDF扫描件OCR转换（中文制度文件推荐使用EasyOCR引擎）

### 扫描件识别技术规范

详见 [references/workflow.md#step-7ocr扫描件处理（step-15）](./references/workflow.md#step-7ocr扫描件处理（step-15）)

**OCR工具说明**：

| OCR引擎 | 推荐场景 | 准确率 | 安装难度 |
|---------|---------|--------|---------|
| **EasyOCR** | 中文制度文件（默认） | ⭐⭐⭐⭐⭐ | pip install easyocr |
| Tesseract | 英文文档 | ⭐⭐⭐⭐ | 需安装系统级软件 |

**使用示例**：
```bash
# 单文件处理
python tools/pdf_ocr_extractor.py "internal-audit-workspace/documents/NPM001成品仓库管理标准C版.pdf"

# 批量处理（推荐用于制度分析）
python tools/pdf_ocr_extractor.py --batch "internal-audit-workspace/documents/" "ch_sim"
```

**OCR 输出文件说明**：

执行 OCR 后，会生成以下文件：

| 文件 | 说明 |
|------|------|
| `{文件名}_ocr.txt` | 纯文本内容，供 document-organizer 分析 |
| `{文件名}_ocr.json` | 结构化数据，包含每页识别详情 |
| `{文件名}_ocr_待办核对.md` | **⚠️ 重点：待办核对清单，标记可疑区域** |

**待办核对清单内容**：

OCR 会自动检测并标记以下需要人工核对的内容：

1. **低置信度文本**（识别不确定，如模糊字迹、印章遮挡）
2. **可能的表格区域**（OCR 难以完整还原表格结构）
3. **可能的印章/签名区域**（影响法律效力判断）
4. **特殊字符/乱码**（识别错误）

**⚠️ 重要提示**：

- **OCR 准确率通常为 90-98%，并非 100%**
- **所有扫描件分析前，必须先查看 `{文件名}_ocr_待办核对.md`**
- **重点关注**：金额数字、日期、审批人姓名、表格数据
- **用户职责**：对照原始 PDF 核对标记区域，自行纠正错误
- **修正方法**：编辑 `{文件名}_ocr.txt` 文件，添加 `[人工修正]` 注释

**示例待办核对清单**：

```markdown
# OCR 识别待办核对清单

## 第 3 页

### 🔍 低置信度文本（需核对）
- 识别内容: `审批金额 50O0 元`
  - 置信度: 0.42
  - 建议: 置信度低，建议人工核对 → 可能是"50000"而非"50O0"

### 📊 可能的表格区域
- 可能的表格区域
  - 检测到的行数: 5
  - 文本块数量: 15
  - 建议: 建议人工核对表格内容的完整性和准确性

### 🖋️ 可能的印章/签名区域
- 识别内容: `财务专用章`
  - 置信度: 0.85
  - 建议: 可能是印章或签名，建议核对
```

## 注意事项

1. **准确性优先**：
   - 确保控制点提取准确
   - 风险描述具体明确
   - 审计程序可操作

2. **完整性检查**：
   - 对照[关键词表](./references/keyword-table.md)检查是否有遗漏
   - 使用检查清单验证

3. **质量控制**：
   - 每个控制点标注原文出处
   - 风险点说明具体后果
   - 审计程序包含量化标准

4. **用户确认**：
   - 复杂判断点询问用户
   - 行业特殊要求请用户补充

5. **批量分析优先**：
   - 优先分析整个制度体系，而非单份文件
   - 单文件分析时，所有control_gaps标记verification_status="待确认"

6. **JSON输出必须包含**：
   - `schema_version` 字段
   - `control_points` 数组
   - `control_gaps` 数组
   - `risk_points` 数组
   - `conflicts` 数组（如有）
   - `summary` 对象

7. **双目录输出**（批量分析时）：
   - `policy-analyses/`：完整分析报告（JSON + Markdown）
   - `design-assessments/`：设计观察（D-XXX 编号，供 Phase 4 验证升级）

---

## Step 5：质量评估（引用评估框架）

**执行前加载**：`D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/SKILL.md`，定位 **policy_analysis** 的检查清单。

**时机**：批量分析完成，输出全部 JSON 后自动执行。

### 5.0 格式硬校验（validate-policy-analysis.py，不可跳过）

在所有推理检查之前，先用确定性脚本做结构校验：

```bash
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/_shared/scripts/validate-policy-analysis.py policy-analyses/ --json
```

| 输出 | 处理 |
|------|------|
| action=block | 根据 blockers 逐项修正，重新运行直到通过 |
| action=warn | 标记 warnings，可接受则继续 |
| action=pass | 继续进入 5.1 |

### 5.1 格式检查

| 检查项 | 执行方式 | 自动修正？ |
|--------|---------|:---------:|
| JSON schema 合规 | 检查 control_points、control_gaps、risk_points、summary 数组是否存在且非空 | ✅ 自动补空数组 |
| schema_version 字段 | 所有 JSON 文件是否包含 schema_version | ✅ 自动补 "1.0" |

### 5.2 推理检查：控制点可追溯性

从输出的控制点中随机抽取 **3 个**，检查：

```
① 【可追溯性】该控制点是否指向原文具体条款/行号？（非概括性描述）
② 【跨文件引用】如涉及跨制度引用，verification_status 是否标注？
③ 【设计观察】设计观察（D-XXX）是否已输出到 design-assessments/？
```

### 5.3 质量判定

| 条件 | 判定 | 行动 |
|:----:|------|------|
| 所有检查通过 | ✅ 正常输出 | 通知用户 Phase 1 完成 |
| schema 不通过 | 🔴 禁止输出 | 修正后重新输出 |
| 控制点可追溯性 ❌ | ⚠️ 标记 | 通知用户补充原文引用 |

### 5.4 结果存储

```bash
echo '{json格式检查结果}' > /tmp/eval_result.json
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/record_evaluation.py --input /tmp/eval_result.json
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/quality_gate.py --input /tmp/eval_result.json
```

---

**提示**：使用本skill时，建议先确认文档路径和类型，然后查看生成的分析报告，最后确认审计程序是否符合实际需求
