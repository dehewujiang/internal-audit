---
name: audit-interview-designer
description: |
  根据制度分析结果、公司背景和历史发现，自动生成定制化审计访谈问卷（Excel格式）和资料需求清单（DRL）。
  
  技术实现: 配置驱动（JSON模板）+ 核心库（_shared/scripts/）
---

# 审计访谈设计器

## 核心定位

**我不是通用的问题生成器，我是基于上下文的"知识缺口填补者"。**

我帮助用户：
- 从制度分析中识别"模糊地带"，生成确认性问题。
- 从行业风险中识别"高危环节"，生成探测性问题。
- 从历史发现中识别"旧疾"，生成整改追踪问题。
- 生成 Excel 格式的访谈问卷和资料需求清单（DRL），方便实地访谈。
- 访谈结果回填后，自动执行智能分流。

## 触发场景

**明确触发词**：
- "生成访谈问卷"
- "设计访谈提纲"
- "准备审计访谈"
- "生成资料需求清单"
- "回填访谈结果"

## 工作流程

### 模式A：生成访谈问卷和DRL

### Step 1：上下文分析与知识缺口识别

**输入源**：
1. `internal-audit-workspace/policy-analyses/*.json`（制度分析结果）
2. `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/about-me.md`（公司背景）
3. `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-program-generator/references/internal_audit_risk_framework.md`（**核心输入：过往审计经验与风险库**）
4. `internal-audit-workspace/findings/index.json`（历史发现，如存在）
5. `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-interview-designer/references/interview_templates.md`（各领域问题模板库）
6. 用户指定的审计主题/范围

**分析逻辑**：

| 输入源 | 分析动作 | 输出 |
|--------|---------|------|
| **制度分析** | 查找 `verification_status="待确认"` 或 `design_effectiveness="无效"` 的项 | 确认性问题 |
| **过往经验** | 读取 `internal_audit_risk_framework.md`，匹配审计主题相关的已验证风险 | 探测性问题（基于真实案例） |
| **公司背景** | 查找子公司结构、系统架构、特殊业务模式 | 针对性问题 |
| **历史发现** | 查找同主题的历史 Finding | 追踪性问题（整改验证） |
| **行业基准** | 基于 `document-organizer/references/industry_benchmarks.md` | 补充性问题（行业通用风险） |

### Step 2：生成 Excel 访谈问卷

**输出位置**：`internal-audit-workspace/interview-materials/[审计主题]_访谈问卷.xlsx`

**Sheet 1: 访谈问卷**

列结构：
| A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|
| 模块 | 序号 | 问题 | 追问提示 | 制度依据 | 访谈记录 | 证据索引 | 风险标记 |

- **模块**：按业务流程切分（如：入库管理、出库管理、盘点管理）
- **序号**：Q1, Q2, Q3...
- **问题**：开放式问题，以"请描述"、"如何"开头
- **追问提示**：2-3个追问方向
- **制度依据**：对应的制度条款（如"仓储管理制度 §3.1"）
- **访谈记录**：留空，供用户手写
- **证据索引**：留空，供用户记录收集到的证据编号
- **风险标记**：留空，供用户标记⚠️

**Sheet 2: 资料需求清单 (DRL)**

列结构：
| A | B | C | D | E | F |
|---|---|---|---|---|---|
| 序号 | 资料名称 | 格式 | 责任部门 | 是否获取 | 备注 |

**Sheet 3: 访谈指南与红旗提示（仅供审计师参考）**

列结构：
| 场景 | 红旗信号 | 应对策略 |

### Step 3：输出确认

生成后提示用户：
```
✅ 访谈问卷已生成：internal-audit-workspace/interview-materials/[主题]_访谈问卷.xlsx

包含：
- Sheet 1: 访谈问卷（[N]个问题，按[N]个模块分类）
- Sheet 2: 资料需求清单（[N]项资料）
- Sheet 3: 访谈指南与红旗提示

请打印或携带Excel进行实地访谈。完成后将填写好的内容发给我，我将自动分流处理。
```

### 模式B：回填访谈结果

当用户将填写好的访谈内容发给AI时，执行**智能分流**。

**前置操作**：读取 `design-assessments/[主题]_设计观察.json`，建立现有观察索引（`{id, title, description}`），用于矛盾检测。

**分流规则**：

| 内容类型 | 识别特征 | 去向 | 操作 |
|----------|---------|------|------|
| **配置更新** | 涉及系统名称、阈值、审批层级、频率等长期规则 | `my-config.md` | 追加或更新对应配置项 |
| **流程事实** | 涉及具体人员、当前做法、实际操作流程 | `interview-materials/[主题]_访谈记录.md` | 新建或追加访谈记录 |
| **风险线索** | 涉及控制缺失、执行偏差、系统问题 | `design-assessments/[主题]_设计观察.json` | 按访谈JSON格式追加到 design_observations[] |
| **证据/记录** | 涉及已获取的文件、数据、照片 | `evidence/[主题]/` | 记录证据清单，提示用户存放文件 |

#### 风险线索：访谈JSON格式

每条风险线索写入 `design-assessments/[主题]_设计观察.json` 的方式：

```
1. 读取现有 JSON 文件（如果不存在则新建框架）
2. 检查每条新线索是否存在 contradictions
3. 追加到 design_observations[] 数组
4. 更新 summary
```

**访谈来源的设计观察格式**（与 Phase 1 document-organizer 共用 schema，新增 interview 专属字段）：

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
  "short_term": "",
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

**`source_role` 取值和权重规则**：

| source_role | 含义 | 典型偏差 | 可靠性权重 | 处理建议 |
|------------|------|---------|:---------:|---------|
| 操作员 | 一线执行人员（仓管、司磅、质检） | 夸大困难、回避个人失误 | 低 | 必须交叉验证，不能单独作为 finding 依据 |
| 中层 | 部门负责人（科长、部长、主任） | 流程化描述、可能粉饰执行情况 | 中 | 可与制度对比验证 |
| 高层 | 总监、副总、总经理 | 战略视角，操作细节可能失真 | 中高 | 用于判断管理态度和资源承诺 |
| 第三方 | 外部审计、客户、供应商 | 各自利益导向 | 视情况 | 标注利益关联 |
| 匿名 | 举报、非公开信源 | 可能真实、可能恶意 | 需独立验证 | 舞弊调查时标注"需保护信源" |

#### 矛盾检测（Contradiction Check）

每条风险线索写入前，与 `design-assessments/[主题]_设计观察.json` 中已有的 observations 逐条比对：

```
检查逻辑：
  新线索的 title/description → 与每条现有观察的 title/description 比对
  如果双方描述的是同一控制点（主体相同），但结论相反：
    → 新线索标注 contradiction[]
    → 旧观察不修改（保留原始，不覆盖）
    → 在分流输出中标记 ⚠️ 矛盾

矛盾类型：
  A类（直接矛盾）：A说"有控制"，B说"无控制"
  B类（程度矛盾）：A说"完全执行"，B说"偶尔执行"
  C类（归因矛盾）：双方对控制是否存在无分歧，但对原因描述不一致
```

**分流输出**：

```
✅ 访谈结果已处理，分流示例如下：

📋 配置更新（2项）→ my-config.md
  - 审批阈值更新为 10 万元
  - 盘点频率确认为每月一次

📝 流程事实（3项）→ interview-materials/存货管理_访谈记录.md
  - 入库由仓储部李四负责
  - 出库需仓库主管签字
  - 盘点由财务部监盘

⚠️ 风险线索（2项）→ design-assessments/存货管理_设计观察.json
  - ⚠️ 废料处置无专人负责（仓管员-赵某，操作员）
    → 矛盾：仓储科长称有指定岗位，详见 D-016
  - 系统库存与实物存在时间差（计划员-钱某，中层）
  - 成品丝超期无系统预警（仓管员-李某，操作员）

📎 证据记录（1项）→ evidence/存货管理/
  - 3月份盘点表（请放入对应目录）
```

## Excel 生成技术规范

使用 Python 的 `openpyxl` 库生成 Excel 文件：

```python
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()

# Sheet 1: 访谈问卷
ws1 = wb.active
ws1.title = "访谈问卷"

# 设置表头
headers = ["模块", "序号", "问题", "追问提示", "制度依据", "访谈记录", "证据索引", "风险标记"]
for col, header in enumerate(headers, 1):
    cell = ws1.cell(row=1, column=col, value=header)
    cell.font = Font(bold=True, color="FFFFFF", size=11)
    cell.fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# 设置列宽
col_widths = [15, 8, 40, 30, 20, 30, 15, 10]
for i, width in enumerate(col_widths, 1):
    ws1.column_dimensions[get_column_letter(i)].width = width

# 冻结首行
ws1.freeze_panes = "A2"

# 添加数据行（根据实际内容）
# ...

# Sheet 2: DRL
ws2 = wb.create_sheet("资料需求清单")
# ...

# Sheet 3: 访谈指南
ws3 = wb.create_sheet("访谈指南")
# ...

wb.save(output_path)
```

## 访谈设计原则

1. **从宏观到微观**：先问流程全貌，再问具体控制点。
2. **开放式为主**：多用"请描述..."、"如何..."，少用"是否..."。
3. **交叉验证**：同一问题问不同岗位。
4. **关注例外**：正常流程通常有制度，例外流程才是风险所在。
5. **结合制度**：每个问题都应能对应到制度条款或风险点。

## 依赖工具

- `Read` - 读取制度分析 JSON、公司背景、历史发现
- `Bash` - 运行 Python 脚本生成 Excel
- `Write` - 写入访谈记录和更新 my-config.md

## Step 5：质量评估（引用评估框架）

**执行前加载**：`D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/SKILL.md`，定位 **interview** 的检查清单。

**时机**：访谈问卷生成后，输出 Excel 前自动执行。

### 5.1 格式检查

| 检查项 | 执行方式 | 自动修正？ |
|--------|---------|:---------:|
| 开放式问题比例 | 扫描问题列，计算非"是否"类问题占比 | ⚠️ <70% 通知用户 |
| DRL 完整性 | 资料需求清单(Sheet 2)是否至少有 5 项资料要求 | ⚠️ <5 项通知用户 |

### 5.2 推理检查：问题锚定性

随机抽取 **3 个**访谈问题，逐一检查：

```
① 【制度依据】该问题是否有对应的制度条款编号？（非空）
② 【锚定性】"探测性问题"是否基于公司具体特征而非行业通用？
   → 检查问题描述中是否包含公司特定信息（ERP类型、组织架构、历史事件）
③ 【追问提示】是否有至少 1 个追问方向？（非空）
```

### 5.3 质量判定

| 条件 | 判定 | 行动 |
|:----:|------|------|
| 所有检查通过 | ✅ 正常输出 | 生成 Excel |
| 开放式问题比例 <70% | ⚠️ 建议补充 | 输出 + 提示 |
| 任意问题无制度依据 | ⚠️ 通知用户 | 标记缺失项 |
| 探测性问题未锚定 | ⚠️ 建议修改 | 标记问题编号 |

### 5.4 结果存储

```bash
echo '{json格式检查结果}' > /tmp/eval_result.json
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/record_evaluation.py --input /tmp/eval_result.json
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/quality_gate.py --input /tmp/eval_result.json
```

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.0 | 2026-04-03 | 初始版本，支持 Excel 输出和智能分流 |
| 2.0 | 2026-05-12 | 新增 Step 5 质量评估框架，校验问题锚定性 |
