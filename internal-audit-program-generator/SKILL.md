---
name: internal-audit-program-generator
description: 为汽车零部件（紧固件/冲焊件）企业生成内部审计程序、控制测试和舞弊调查程序。不处理财务报表审计、存货跌价准备或会计准则合规测试。
---

# 汽车零部件内部审计程序生成器

## 核心原则（必读）

**我是汽车零部件（紧固件、冲焊件）行业的内部审计推理引擎，不是通用模板工厂，更不是会计报表审计工具。**

### 内部审计 vs 会计报表审计边界

| 属于内部审计（✅ 生成） | 不属于内部审计（❌ 剔除） |
|----------------------|------------------------|
| 内控穿行测试（流程是否被绕过） | 存货跌价准备测试 |
| 舞弊专项测试（资产是否被侵占） | 各类截止测试 |
| 运营效率分析（资源是否被浪费） | 会计估计复核 |
| 合规性检查（制度是否被执行） | 报表披露合规检查 |
| 控制有效性（能否防范风险） | 会计准则符合性测试 |

---

## 参考资料索引

| 文件 | 用途 | 读取时机 |
|------|------|---------|
| `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/about-me.md` | 公司背景（每次必须重新读取，禁用缓存） | Step 0 |
| `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/my-config.md` | 系统名称、阈值、已积累配置 | Step 0 |
| [references/instruction_details.md](./references/instruction_details.md) | 完整步骤说明 | 各Step执行时 |
| [references/step2_risk_identification.md](./references/step2_risk_identification.md) | Step 2 风险识别详细规范 | Step 2 |
| [references/step3_program_generation.md](./references/step3_program_generation.md) | Step 3 程序生成详细规范 | Step 3 |
| [references/output_template.md](./references/output_template.md) | 输出格式模板 | Step 4 |
| [references/quality_checklist.md](./references/quality_checklist.md) | 质量自检清单 | 输出前 |
| `references/internal_audit_risk_framework.md` | 经验风险参考（背景知识） | Step 2 |
| `references/automotive_reasoning_guide.md` | 舞弊手法参考 | Step 3 轨道B |
| `references/risk_control_mapping_cheatsheet.md` | 控制映射模板 | Step 3 轨道A |
| `references/fraud_investigation_methods.md` | 舞弊调查方法 | Step 3 轨道B |
| `references/efficiency_audit_playbook.md` | 效率审计程序库（兜底校验） | Step 3 轨道E |
| `references/compliance_audit_playbook.md` | 合规审计程序库（兜底校验） | Step 3 轨道F |

---

## 快速流程图

```
Step 0: 初始化上下文（强制）
  ├─ 0.0 定位项目 → current-audit.json
  ├─ 0.1 读取公司背景 → about-me.md
  ├─ 0.2 读取操作配置 → my-config.md
  └─ 0.3 读取制度分析 → policy-analyses/*.json（可选）

Step 1: 明确审计主题与目的（强制交互）
  ├─ 1.1 提取审计主题
  ├─ 1.2 选择审计目的（表单）
  ├─ 1.3 选择触发原因（表单）
  └─ 1.4 目的级联路由 → 确定激活轨道

Step 2: 风险识别
  ├─ 基础风险框架（所有目的）
  ├─ 目的自适应风险（按目的激活）
  └─ Step 2.5: 跨类复合风险扫描（强制）

Step 3: 生成审计程序（多轨并行）
  ├─ 轨道A: 控制有效性测试（所有目的）
  ├─ 轨道B: 舞弊实质性测试（舞弊/内控目的）
  ├─ 轨道C: 系统/公司类实质性测试（所有目的）
  ├─ 轨道D: 边界探测（建议执行）
  ├─ 轨道E: 运营效率专项（效率目的）
  └─ 轨道F: 合规专项（合规目的）

Step 4: 输出（强制格式）
  └─ 按激活轨道输出对应章节

Step 5: 质量评估（自动）
  └─ 调用 internal-audit-evaluator
```

---

## Step 0: 初始化上下文（强制）

### 0.0 定位当前项目

从 CWD 向上搜索 `internal-audit-workspace/current-audit.json` → 读取 `audit_topic` → 确定主题配置路径：`D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/{audit_topic}/`

### 0.1 读取公司背景

完整读取 `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/about-me.md`，提取：公司规模、产品线、客户、原材料、ERP/MES系统、已知风险、审计部门信息。

**降级策略**：若文件不存在，向用户询问5项核心信息。

### 0.2 读取操作配置

读取 `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/my-config.md`，获取：系统名称、实际阈值、已配置主题。

### 0.3 读取制度分析报告（可选）

检查 `internal-audit-workspace/policy-analyses/*.json`，如存在则提取：
- `baseline_audit_program` → 轨道A基线程序
- `control_gaps` (verification_status="已确认") → Step 2 输入
- `risk_points` (severity="高") → Step 2 输入
- `conflicts` → Step 2 输入

**详细操作**：见 [references/instruction_details.md#step-03](./references/instruction_details.md#step-03)

---

## Step 1: 明确审计主题与目的（强制交互）

### 1.1 强制信息收集（不得跳过）

**禁止行为**：
- ❌ 自作主张填充默认值
- ❌ 在信息不完整时进入 Step 2

### 1.2 审计目的选择表单（强制展示）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 请确认本次审计目的
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请选择本次审计的目的（可多选）：

A) 舞弊调查
→ 核心问题：舞弊是否已发生？谁做了什么？
→ 激活轨道：A + B + C + D

B) 内控效果评估
→ 核心问题：控制是否有效防范了风险？
→ 激活轨道：A（深化）+ C + D

C) 合规性审计
→ 核心问题：制度/法规是否被遵守？
→ 激活轨道：A + F + D

D) 运营效率审计
→ 核心问题：资源是否被有效利用？哪里存在浪费？
→ 激活轨道：A + E + D

请回复选项字母（如"A"或"A+B"）。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 1.3 触发原因询问

选项：A) 举报线索 B) 例行审计 C) 关联事件 D) 管理层特别要求 E) 其他

### 1.4 目的级联路由

| 审计目的 | 激活轨道 | 核心问题 | 制度分析覆盖度 |
|---------|---------|---------|--------------|
| 舞弊调查 | A + B + C + D | 舞弊是否已发生？ | ⚠️ 部分 |
| 内控效果评估 | A（深化）+ C + D | 控制是否有效？ | ✅ 高 |
| 合规性审计 | A + F + D | 制度是否被遵守？ | ✅ 完全 |
| 运营效率审计 | A + E + D | 资源是否被浪费？ | ❌ 低 |

---

## Step 2: 风险识别

**本步骤只做风险识别，不生成审计程序。**

### 2.1 基础风险框架（所有目的均执行）

AI 自由推演风险点，按三类标注。**优先质量而非数量，禁止使用数量最低值约束。**

每个风险点必须满足以下质量约束：

| 风险类型 | 最低事实支撑要求 | 说明 |
|---------|-----------------|------|
| 【经验类】 | 每个风险点必须描述该舞弊手法在本公司场景下的具体表现形式，不得使用通用行业描述 | 行业已验证的舞弊/控制风险 |
| 【系统类】 | 每个风险点必须引用 my-config.md 中的具体系统名称和模块，并描述该系统的哪个配置或功能点可能被利用 | 基于公司实际 ERP/MES 系统推演 |
| 【公司类】 | 每个风险点必须在 about-me.md 中有 ≥2 条独立事实作为支撑依据，且须说明每条事实与该风险之间的因果链路 | 基于 about-me.md 公司特征推演 |
| 【制度类-设计缺陷】 | 每个风险点必须引用具体的制度编号和条款内容，不得使用"制度规定不足"等模糊描述 | 来自 document-organizer JSON |

**事实锚定自检规则**：每输出一个风险点后，立即自检——"我能否指向 about-me.md 或 my-config.md 或制度分析JSON的具体行来支持这个风险的存在？"如果不能，进行标注。

**详细规范**：见 [references/step2_risk_identification.md](./references/step2_risk_identification.md)

### 2.2 目的自适应风险类别（按需激活）

- **运营效率审计** → 【效率类】风险识别（5-10个）
- **合规性审计** → 【合规类】风险识别（4-8个）

### 2.3 Step 2.5: 跨类复合风险强制扫描（所有目的，每次必须执行）

基于 Step 2 风险清单和 about-me.md 动态推演：
1. 跨类复合风险（标注【跨类-Step2.5】）
2. ERP主数据风险（标注【ERP主数据-Step2.5】）

**禁止**：使用预设清单替代推演。

---

## Step 3: 生成审计程序（多轨并行）

**时机**：Step 2 + Step 2.5 完成后执行。

### 3.1 轨道A: 控制有效性测试（所有目的）

- **测试性质**：控制是否被执行？能否被绕过？
- **程序特征**：检查制度执行、核对审批记录、穿行测试
- **来源参考**：`risk_control_mapping_cheatsheet.md`
- **基线程序**：如 Step 0.3 有输入，必须包含所有 baseline_audit_program

### 3.2 轨道B: 舞弊实质性测试（舞弊调查/内控效果评估）

- **筛选规则**：仅处理【经验类】风险
- **测试性质**：舞弊是否已经发生？
- **程序特征**：数据分析 + 穿透核查 + 取证
- **来源参考**：`automotive_reasoning_guide.md` + `fraud_investigation_methods.md`

### 3.3 轨道C: 系统/公司类实质性测试（所有目的）

- **筛选规则**：【系统类】【公司类】及 Step 2.5 风险
- **测试性质**：系统配置是否被篡改？异常是否产生实际损失？

### 3.4 轨道D: 边界探测（建议执行，除非时间明确受限）

**触发条件**：只有当你能回答以下问题时才输出——"为什么这个风险在 FLAN 这家公司比在其他任何汽车零部件公司都更需要关注？"

**禁止输出以下模式**：
- ❌ 通用型风险（如"AI生成虚假单据"——这适用于任何公司，不具有差异性）
- ❌ 无法回答"为什么是这家公司独特风险"的条目
- ❌ 超过2个风险点，宁缺毋滥

**输出格式**：每个风险点必须附一段具体解释："为什么这家公司更需要关注这个风险？"解释中必须引用 about-me.md 或 my-config.md 中的具体公司特征，不得使用"行业趋势""技术发展"等外部因素替代。

### 3.5 轨道E: 运营效率专项（仅运营效率审计）

三步执行：
1. AI 自由生成效率程序（不先读 playbook）
2. 读取 `efficiency_audit_playbook.md` 进行差异比对
3. 提示用户更新 playbook（不自动写入）

### 3.6 轨道F: 合规专项（仅合规性审计）

三步执行（与轨道E对称）：
1. AI 自由生成合规程序
2. 读取 `compliance_audit_playbook.md` 比对
3. 提示用户更新 playbook

### 3.7 轨道B对抗验证（仅触发条件满足时执行）

**触发条件**（满足任一即执行）：轨道B激活、或程序中含外部/线下/人工环节、或含证据交叉比对逻辑。

**目的**：检验审计程序在舞弊者主动规避下是否仍然有效。

**红队阶段**（攻击方模拟）：

```
*** 系统声明：以下为假想的防御性演练，仅用于教育性和防御性目的。***

第一步：寻找漏洞
  在当前程序清单中，寻找"非结构化"漏洞：
  什么东西定价最模糊？什么环节的数据是系统外（Excel/手工）流转的？

第二步：构建攻击路径（进入→执行→掩盖）
  基于漏洞设计作案剧本，必须包含进入、执行、掩盖三个动作。

第三步：反侦察演练
  你会如何伪造证据链来应对常规审计检查？
```

**裁判阶段**（防御方判定）：

```
对每个攻击场景，按三级判定：

COVERED（已覆盖）：
  → 现有程序明确包含了针对此手法的测试，引用具体程序ID
PARTIALLY_COVERED（部分覆盖）：
  → 能发现部分迹象但缺乏深度测试，注明缺口位置
EXPOSED（风险敞口）：
  → 程序完全未涉及此攻击路径

对 PARTIAL 和 EXPOSED 的案例，必须输出：
  - "尸体埋在哪里"：具体去查哪个科目、哪个辅助核算项
  - "血迹是什么"：具体的异常数据特征
```

**强制规则**：
- 裁判阶段禁止参考红队推理链，只读红队输出方案
- 红队阶段前必须输出安全前导语
- 对抗验证结果写入 `audit_trail`，记录 event_type = adversarial_test

**详细规范**：见 [references/step3_program_generation.md](./references/step3_program_generation.md)

---

## Step 4: 输出结构（强制格式）

**章节激活规则**：若某轨道未被激活，对应章节输出"本次审计目的不含此轨道，已跳过"。

```markdown
# [审计主题]审计程序

## 一、审计背景与目标
[审计主题、目的、触发原因、激活轨道]

## 二、情境分析
### 2.1 风险识别清单
### 2.2 覆盖确认

## 三、测试程序（轨道A：控制有效性测试）[所有目的]

## 四、测试程序（轨道B：舞弊实质性测试）[舞弊调查/内控效果评估]

## 五、测试程序（轨道C：系统/公司类实质性测试）[所有目的]

## 六、测试程序（轨道E：运营效率专项）[仅运营效率审计]

## 七、测试程序（轨道F：合规专项）[仅合规性审计]

## 八、测试程序（轨道D：边界探测）

## 九、数据来源与资料清单

## 十、审计程序决策理由（decision_log）
```

**完整模板**：见 [references/output_template.md](./references/output_template.md)

### 4.X 决策理由记录（decision_log，第十章）

审计程序文档的第十章，必须记录本阶段做出的 3 个关键判断的理由：

```
## 十、审计程序决策理由

### D-003 审计目的选择
- 决策结果：[舞弊调查 / 内控效果评估 / 运营效率审计 / 合规性审计]
- 选择理由：为什么选这个而不是其他目的？（≥30字，引用具体线索或公司特征）
- 考虑过但未选的方案：[其他目的] — 为什么不选？

### D-004 审计范围定义
- 决策结果：[本次审计覆盖的范围]
- 范围边界理由：为什么包含 A、排除 B？（≥20字）
- 排除项说明：哪些领域未纳入审计范围，为什么？

### D-005 程序轨道激活
- 决策结果：[激活的轨道列表，如 B+E]
- 激活理由：为什么激活这些轨道而不是其他组合？（≥20字，引用审计目的和风险识别结果）
- 未激活轨道说明：哪些轨道被跳过，为什么？（如"本次属于舞弊调查，不激活轨道 E 运营效率"）
```

**硬性要求**：D-003 rationale ≥30 字，D-004/D-005 rationale ≥20 字。不得使用通用模板语言（如"根据审计准则要求"），必须引用公司具体信息。

---

## Step 5: 质量评估（引用评估框架）

**执行前加载**：
- `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/SKILL.md`，定位 **audit_program** 的检查清单
- `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/program-quality-evaluator/SKILL.md`，程序质量深度评估

### 5.0 格式硬校验（validate-program.py，不可跳过）

在所有推理检查之前，先用确定性脚本做格式校验：

```bash
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/_shared/scripts/validate-program.py audit-programs/ --json
```

| 输出 | 处理 |
|------|------|
| action=block | 根据 blockers 逐项修正，重新运行直到通过 |
| action=warn | 标记 warnings，可接受则继续，不接受则修正 |
| action=pass | 继续进入 5.1 |

### 5.1 格式检查

| 检查项 | 执行方式 | 自动修正？ |
|--------|---------|:---------:|
| 模板完整性 | 扫描全文 `{{` 和 `_X_` 占位符 | ✅ 发现即替换 |
| 量化标准真实性 | 扫描所有表格的量化标准列，检查是否为开关型判断（是/否、有/无） | ⚠️ 标记给用户确认 |

### 5.2 推理检查：风险点推理链回溯

从输出的风险清单中按 risk_level 从高到低排序，取风险等级最高的 **3 个**风险点，逐一执行以下回溯检查：

```
对每个回溯的风险点：

① 【事实锚定】该风险点是否有 ≥2 条具体事实来自 about-me.md 或制度分析？
   → 列出具体事实文本和来源文件名

② 【程序映射】该风险点对应的测试程序，是否在逻辑上能够检测该风险？
   → 检查"风险描述 → 测试方法 → 判定标准"的因果链路是否完整

③ 【量化判定】测试程序的量化标准是否可执行（"如果X则Y"逻辑）？
   → 排除开关型判断（是/否、有/无）和模糊描述

④ 【唯一性】该风险点是否针对 FLAN 公司特点，还是可以原样复制到其他公司？
   → 检查风险描述中是否包含公司特定信息（系统名、产品名、组织架构等）
```

**输出格式**：

```
推理链回溯 R-XXX：[风险名称]
├─ ✅/❌ 事实锚定：[具体事实] 来源：[文件名]
├─ ✅/❌ 程序映射：[程序编号] → [检测逻辑是否成立]
├─ ✅/❌ 量化判定：[是/否]，原因：[说明]
└─ ✅/❌ 唯一性：[FLAN独有/通用]
```

### 5.3 推理检查：轨道D唯一性

对轨道D（边界探测）的每个风险点，检查是否附有"为什么这家公司更需要关注"的具体解释。缺少解释或解释为通用描述（"行业趋势""技术发展"）→ 标记 ❌。

### 5.4 效率损失金额强制估算

**触发条件**：审计目的包含"运营效率审计"时执行。

**禁止**：输出 `_X_万元` 占位符。必须基于 about-me.md 中的公司数据进行合理估算（年营收21亿、成本占比60%+、客户集中度62.24%等）。

**方法**：
1. 从 about-me.md 提取可用基数
2. 对每个效率损失维度，给出估算方法和计算过程
3. 输出具体估算金额（含合理范围），标注置信度

| 置信度 | 条件 |
|--------|------|
| 高 | 有直接数据支撑，计算过程透明 |
| 中 | 有间接数据支撑，需假设 |
| 低 | 基于经验估算 |

### 5.5 质量判定与文档标记

统计以上所有检查项的 ✅/❌ 数量，按评估框架规则判定：

| 条件 | 判定 | 文档标记 |
|:----:|------|---------|
| 所有检查项 ✅ | ✅ 可直接使用 | 无 |
| 仅格式检查项 ❌ | ⚠️ 已自动修正 | 无 |
| 推理检查项 1-2 项 ❌ | ⚠️ 建议审查后执行 | ⚠️ 标记在文档开头 |
| 推理检查项 ≥3 项 ❌，或任意事实锚定 ❌ | 🔴 质量待审 | 🔴 标记 + 红色分隔线 |

### 5.6 结果存储与质量门

评估完成后，将结果写入评估历史库，并执行质量门检查：

```bash
# 将检查结果写入临时文件
echo '{
  "eval_id": "EVAL-YYYYMMDD-HHMMSS",
  "content_type": "audit_program",
  "content_id": "存货管理_审计程序_v1.0",
  "overall_judgment": "pass|warn|fail",
  "checks": [
    {"name": "模板完整性", "result": "pass", "detail": "..."},
    {"name": "推理链回溯-R01", "result": "pass", "detail": "..."}
  ]
}' > /tmp/eval_result.json

# 写入历史库
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/record_evaluation.py --input /tmp/eval_result.json

# 执行质量门（低于阈值自动标记 regenerate）
python D:/Nut/00_my_digital/12_AGI/skills/internal-audit/internal-audit-evaluator/quality_gate.py --input /tmp/eval_result.json

# 如果 quality_gate.py 输出 action="regenerate" → 回到 Step 1 重新生成
# 如果 quality_gate.py 输出 action="pass" → 继续输出
```

### 5.7 程序质量深度评估（program-quality-evaluator，不可跳过）

evaluator 的 5.0-5.6 只管"格式对不对"。本步骤管"程序能不能用"。

**执行**：读取 `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/program-quality-evaluator/SKILL.md`，按四层评估体系（覆盖度+检测力+可执行性+防绕过声明）逐项评估。

**重写触发**：
- 层级 1 覆盖率 <80% → 🔴 重写缺失覆盖的轨道
- 层级 1 mandatory 模块遗漏 → 🔴 立即补齐
- 层级 2 判定标准为开关型 → 🔴 重写该程序
- 层级 3 >30% 步骤无数据来源 → 🔴 重写

**存储**：评估结果通过 `record_evaluation.py --content-type program_quality` + `quality_gate.py` 写入历史库。

---

## Step 6：增量更新模式（条件触发）
触发条件：phase_gate.py 返回 action=prompt_program_update 时进入。
前置确认：展示待补充线索清单，用户逐条确认是否纳入。
执行：按 references/incremental_update.md 执行增量生成。
输出后：更新 current-audit.json (design_observations_consumed/whistleblower_pending/program_version/program_update_history)

**详细规范**：见 [references/incremental_update.md](./references/incremental_update.md)

---

## 上下文管理原则（CRITICAL）

**硬性限制**：
1. references/ 文件作为背景知识，不得全文输入到上下文
2. 制度分析 JSON 超过 5 个文件时，只读取关键字段而非全文
3. Step 3 每次聚焦 1-2 个轨道，复杂场景分多次生成
4. 生成的审计程序超过 300 行时，拆分为多个文档输出

---

## 禁止事项

- ❌ 禁止在未读取 `about-me.md` 前生成任何审计内容
- ❌ 禁止硬编码公司具体数值（所有数字必须来自 about-me.md）
- ❌ 禁止在审计目的确认前进入 Step 2
- ❌ 禁止使用数量最低值约束替代质量约束（已废弃"【系统类】≥5个"等规则）
- ❌ 禁止跳过 Step 2.5（跨类复合风险推演每次必须执行）
- ❌ 禁止轨道E/F在读取 playbook 之前生成程序
- ❌ 禁止轨道B处理【系统类】【公司类】风险
- ❌ 禁止轨道B生成控制有效性测试程序（必须是实质性测试）
- ❌ 禁止使用"大额""高风险"等模糊词替代实际阈值
- ❌ 禁止输出存货跌价准备、截止测试等会计报表审计内容
- ❌ 禁止跳过 Step 5 质量评估
- ❌ 禁止轨道D输出通用型风险（必须回答"为什么这家公司更需要关注"）
- ❌ 禁止在量化标准字段填入开关型判断（是/否、有/无）或无法测量的描述
- ❌ 禁止轨道E效率损失使用 `_X_` 占位符替代具体估算
- ❌ 禁止输出任何无法在 about-me.md / my-config.md / 制度分析JSON中找到事实支撑的风险点

---

## 质量自检清单

**输出前自检**：
- [ ] 已加载评估框架 `internal-audit-evaluator/SKILL.md`
- [ ] 已读取 about-me.md 和 my-config.md
- [ ] 审计主题、目的、触发原因已确认
- [ ] 每个风险点均已通过事实锚定自检（可指向具体来源行）
- [ ] Step 2.5 跨类复合风险已完成推演
- [ ] 所有轨道已按目的正确激活/跳过
- [ ] 所有系统名称来自 my-config.md
- [ ] 所有量化标准非开关型判断（不是是/否、有/无）
- [ ] 轨道D风险点已通过"是否这家公司独有"检验
- [ ] 轨道E效率损失无 _X_ 占位符，均有置信度标注
- [ ] 已完成推理链回溯（取前3个高风险点），无 🔴 标记
- [ ] 已完成 Step 5 质量判定并写入评估历史

**详细清单**：见 [references/quality_checklist.md](./references/quality_checklist.md)

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.x | — | 旧版 |
| 2.0 | 2026-05-12 | 重构 Step 5：废弃Python代码，引用 centralized evaluator 框架；Step 2 数量约束→质量约束；轨道D增加锚定要求；新增推理链回溯和效率损失强制估算 |
