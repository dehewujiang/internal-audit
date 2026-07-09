# doc-organizer-accuracy - Work Plan

## TL;DR (For humans)

**你要得到什么**：document-organizer 跨章节控制点不再丢碎片——同一个控制的规则分散在多个章节时，LLM 能拿到完整上下文再分析。

**做法**：
1. 把行业基准表从"参考文档"升级为"可执行清单"——每个业务领域明确列出"应该有哪种控制"，作为分析时的对照表
2. 分析流程从"逐段扫描"改为"先建目录再写详情"——LLM 第一遍只做归类（哪些段落讲的是同一件事），第二遍拿完整上下文写控制点

**不改什么**：不重写 document-organizer 的核心逻辑。不新增 skill。只改 3 个已有文件。

**工作量**：约 1 天，单波次。

## Scope

**IN**:
- `document-organizer/references/industry_benchmarks.md` — 重构为可执行清单
- `document-organizer/references/workflow.md` — 新增两遍法流程
- `document-organizer/SKILL.md` — 更新工作流程引用

**OUT**: 不重写控制点提取算法。不改 validate-policy-analysis.py。不新增 Python 脚本。不改其他 skill。

## Execution strategy

单波次：行业基准升级 + 两遍法流程，三个任务可串行（后两个依赖第一个）：

```
T1.1 → T1.2 → T1.3
```

---

## Todos

---

#### T1.1: industry_benchmarks.md — 升级为可执行清单

**References**: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\document-organizer\references\industry_benchmarks.md`

**Changes**:

1. 在"制度基准框架"表格之后，新增"**各业务领域控制维度清单**"章节。对每个 P0/P1 领域，列出该领域**必须有**的控制维度（不是泛泛的"出入库审批"，而是按控制类型拆解）：

```markdown
## 各业务领域控制维度清单

### 采购管理（P0）
| 控制维度 | 控制类型 | 应覆盖的关键点 |
|---------|---------|--------------|
| 供应商准入 | 审批(AP) | 新供应商的准入审批流程、评估标准 |
| 采购审批 | 审批(AP) | 不同金额区间的审批层级、紧急采购例外流程 |
| 价格管理 | 审批(AP) + 记录(DR) | 比价/议价记录、价格审批 |
| 采购验收 | 职责分离(SS) + 记录(DR) | 采购人与验收人分离、验收记录 |
| 采购付款 | 审批(AP) + 职责分离(SS) | 付款审批与采购审批分离、三单匹配 |

### 存货管理（P0）
| 入库管理 | 审批(AP) + 记录(DR) | ... |
| 出库管理 | 审批(AP) + 记录(DR) | ... |
| 盘点管理 | 定期检查(RC) + 职责分离(SS) | ... |
| 呆滞料管理 | 定期检查(RC) | ... |
| 保管管理 | 职责分离(SS) | ... |
```

2. 每个 P0 领域至少 3 个控制维度，每个维度明确标注控制类型（AP/SS/RC/DR）和应覆盖的关键点。

3. 新增章节"**行业基准版本管理**"：

```markdown
## 行业基准版本管理

本文档是 document-organizer 提取完整性的对照基准。每次制度体系发生重大变化（新增业务线、更换 ERP、组织架构调整）后应审查本基准是否需要更新。

最后更新：[日期]
最后审查：[日期]
审查触发条件：公司业务范围变更 / 行业监管要求更新 / 审计发现持续暴露某领域控制缺失
```

**Acceptance**: 每个 P0/P1 业务领域都有至少 3 个带控制类型标签的控制维度。

**QA**: 
- Happy: 读完文件，统计 P0 领域数 × 平均控制维度数 ≥ 3
- Failure: 任何 P0 领域控制维度 < 3 → 不通过

**Commit**: `feat: upgrade industry_benchmarks to executable control dimension checklist`

---

#### T1.2: workflow.md — 新增两遍法流程

**References**: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\document-organizer\references\workflow.md`

**Changes**:

在现有"逐份深度分析"步骤之后、"流程重建"之前，插入"**Step X：业务对象索引建立**（新增）"：

```markdown
## Step X：业务对象索引建立（新增 — 始终执行）

**目的**：解决控制点规则分散在多个章节时 LLM 逐段分析无法拼接的问题。

### 第一遍：LLM 建索引

读完制度全文后，不提取控制点，只输出"业务对象索引"：

| 业务对象 | 涉及章节 | 控制类型 | 摘要 |
|---------|---------|---------|------|
| 采购审批 | 3.1, 5.3, 7.2 | AP | 正常流程(3.1)+紧急例外(5.3)+设备采购特例(7.2) |
| 盘点管理 | 6.1, 6.4, 附录B | RC+DR | 月度盘点(6.1)+差异处理(6.4)+盘点表模板(附录B) |
| ... | ... | ... | ... |

**索引规则**：
- 按"业务对象"归并，不是按章节归并
- 同一业务对象的所有相关段落必须在同一行
- 如果某业务对象只有一个段落提及，仍需列入索引（完整性要求）
- 控制类型列标注该业务对象涉及的控制类型（对照 control_taxonomy.md 的 AP/SS/RC/DR 分类）

### 第二遍：逐业务对象分析

对索引中的每个业务对象：
1. 从原文中提取所有相关段落的完整原文
2. 拼成一个文本块
3. 一次性喂给 LLM 分析该业务对象下的完整控制点

**输出**：每个业务对象产出一个控制点分析块，LDM 拿到的是完整上下文，不是碎片。
```

同时更新顶部的流程图为：

```
批量扫描文件夹
↓
建立"文件-章节-业务领域"索引
↓
版本识别
↓
【新增】业务对象索引（第一遍：只归类，不写详情）
↓
【新增】逐业务对象分析（第二遍：拿完整上下文写控制点）
↓
流程重建（提取隐含控制）
↓
关键词搜索 → 标注关键要求
↓
...
```

**Acceptance**: workflow.md 完整描述了两遍法流程，LLM 能据此执行。

**Commit**: `feat: add two-pass business object indexing to document-organizer workflow`

---

#### T1.3: SKILL.md — 更新工作流程引用

**References**: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\document-organizer\SKILL.md`

**Changes**:

在"工作流程"章节（约 line 68-70），将现有的简单引用更新为包含两遍法的说明：

```markdown
## 工作流程

详见 [references/workflow.md](./references/workflow.md)

**分析模式**：采用两遍法——
1. 第一遍：LLM 快速扫读全文，建立"业务对象索引"（哪些章节在讲同一件事）
2. 第二遍：对每个业务对象，把散落在各章节的原文归拢后一次性交给 LLM 分析，确保拿到的是完整上下文而非碎片

**分治法（6+文件时必须使用）**：
```

**Acceptance**: SKILL.md 明确描述了分析模式的变化。

**Commit**: `feat: update SKILL.md to reflect two-pass analysis mode`

---

## Final verification wave

全部完成后：

F1: industry_benchmarks.md — 确认每个 P0 领域的控制维度 ≥ 3
F2: workflow.md — grep 确认"业务对象索引"和"两遍法"出现
F3: SKILL.md — 确认引用两遍法分析模式

## Commit strategy

```
feat: upgrade industry_benchmarks + two-pass workflow
```

## Success criteria

1. industry_benchmarks.md 的每个 P0 领域有 ≥ 3 个带控制类型标签的控制维度
2. workflow.md 包含完整的两遍法流程描述
3. SKILL.md 明确引用两遍法分析模式
