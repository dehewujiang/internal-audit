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
| `audit-topics/about-me.md` | 公司背景（每次必须重新读取，禁用缓存） | Step 0 |
| `audit-topics/my-config.md` | 系统名称、阈值、已积累配置 | Step 0 |
| [references/instruction_details.md](./references/instruction_details.md) | 完整步骤说明 | 各Step执行时 |
| [references/step2_risk_identification.md](./references/step2_risk_identification.md) | Step 2 风险识别详细规范 | Step 2 |
| [references/step3_program_generation.md](./references/step3_program_generation.md) | Step 3 程序生成详细规范 | Step 3 |
| [references/ctx_init.md](./references/ctx_init.md) | Step 0.3/0.4/0.5 初始化与追问细则 | Step 0 |
| [references/red_team_attack.md](./references/red_team_attack.md) | 红队攻击：程序检测力对抗验证（剧本→回灌修订→再攻，≤2轮） | Step 4.6 |
| [references/output_template.md](./references/output_template.md) | 输出格式模板 | Step 4 |
| [references/output_and_gates.md](./references/output_and_gates.md) | Step 4/4.5/4.6 输出结构与闸机细则 | Step 4-4.6 |
| [references/quality_evaluation.md](./references/quality_evaluation.md) | Step 5 质量评估执行细则 | Step 5 |
| [references/quality_checklist.md](./references/quality_checklist.md) | 质量自检清单 | 输出前 |
| `references/internal_audit_risk_framework.md` | 经验风险参考（背景知识） | Step 2 |
| `references/automotive_reasoning_guide.md` | 舞弊手法参考 | Step 3 轨道B |
| `references/risk_control_mapping_cheatsheet.md` | 控制映射模板 | Step 3 轨道A |
| `references/fraud_investigation_methods.md` | 舞弊调查方法 | Step 3 轨道B |
| `references/efficiency_audit_playbook.md` | 效率审计程序库（兜底校验） | Step 3 轨道E |
| `references/compliance_audit_playbook.md` | 合规审计程序库（兜底校验） | Step 3 轨道F |
| `references/dynamic_questions.md` | 动态业务问题矩阵（配置空白时追问，回写 my-config） | Step 0.4 |
| `references/incremental_update.md` | 增量更新/勘误模式（phase_gate 信号触发，S 序列） | Step 0.5 |

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

Step 4.6: 红队攻击（强制）
  └─ 读取 references/red_team_attack.md 执行

Step 5: 质量评估（自动）
  └─ 调用 internal-audit-evaluator
```

---

## Step 0: 初始化上下文（强制）

### 0.0 定位当前项目

从 CWD 向上搜索 `internal-audit-workspace/current-audit.json` → 读取 `audit_topic` → 确定主题配置路径：`audit-topics/{audit_topic}/`

### 0.1 读取公司背景

完整读取 `audit-topics/about-me.md`，提取：公司规模、产品线、客户、原材料、ERP/MES系统、已知风险、审计部门信息。

**降级策略**：若文件不存在，向用户询问5项核心信息。

### 0.2 读取操作配置

读取 `audit-topics/my-config.md`，获取：系统名称、实际阈值、已配置主题。

### 0.3 读取制度分析报告（可选）

检查 `internal-audit-workspace/policy-analyses/*.json`，有则提取基线程序、控制缺口、高危风险点、冲突，细节见 [ctx_init.md](./references/ctx_init.md)。

### 0.4 配置空白检测与动态追问（强制）

检查 my-config.md 中相关配置项是否仍为 `【】` 空白，空白则从 `dynamic_questions.md` 问题矩阵追问 1-2 题、答后回写。完整表格与追问格式见 [ctx_init.md](./references/ctx_init.md)。

---

### 0.5 模式判定：全新生成 vs 增量更新（强制）

跑 `phase_gate.py check` 判模式：无旧程序→全新生成；有旧程序且有更新信号→走增量更新（S 序列，详见 [incremental_update.md](./references/incremental_update.md)；判定表见 [ctx_init.md](./references/ctx_init.md)）。增量更新完成后不再走 Step 1-5。

---

## Step 1: 明确审计主题与目的（强制交互）

### 1.1 强制信息收集（不得跳过）

**禁止行为**：
- ❌ 自作主张填充默认值
- ❌ 在信息不完整时进入 Step 2

### 1.2 审计目的选择表单（强制展示）

向用户展示四选目的表单（舞弊调查/内控效果/合规性/运营效率，可多选），按选择级联路由激活轨道。表单全文与级联路由表见 [output_and_gates.md](./references/output_and_gates.md) 和 [instruction_details.md](./references/instruction_details.md)。

### 1.3 触发原因询问

选项：A) 举报线索 B) 例行审计 C) 关联事件 D) 管理层特别要求 E) 其他

### 1.4 目的级联路由

级联路由表（目的→激活轨道→核心问题→制度分析覆盖度）见 [output_and_gates.md](./references/output_and_gates.md) Step 4.5 节同款表格。

---

## Step 2: 风险识别

**本步骤只做风险识别，不生成审计程序。**

### 2.1 基础风险框架（所有目的均执行）

AI 自由推演风险点，按三类（经验/系统/公司/制度设计）标注，每类有事实支撑的最低要求，禁止数量约束；已有制度编号（CG/RP/D/CF）直接沿用不重编。逐条自检能否指向具体来源行。质量约束表、防重复规则全文见 [step2_risk_identification.md](./references/step2_risk_identification.md)。

### 2.4 新假设落任务板（桌子在 `internal-audit-workspace/audit-table/*.json`，找不到就停下报告——宪法#12）

风险清单定稿后，无户口的新假设立任务（待查）、有户口的带 `--known-anchor` 不添行。命令见 [step2_risk_identification.md](./references/step2_risk_identification.md)。任务是假设不是结论，查实由执行关任务转事实行，这里只立不结。

### 2.2 目的自适应风险类别（按需激活）

- **运营效率审计** → 【效率类】风险识别（5-10个）
- **合规性审计** → 【合规类】风险识别（4-8个）

### 2.3 Step 2.5: 跨类复合风险强制扫描（所有目的，每次必须执行）

基于 Step 2 风险清单和 about-me.md 动态推演跨类复合风险与 ERP 主数据风险，**禁止**用预设清单替代推演。详见 [step2_risk_identification.md](./references/step2_risk_identification.md)。

---

## Step 3: 生成审计程序（多轨并行）

**时机**：Step 2 + Step 2.5 完成后执行。

**开始生成程序前（自检屏障一）**：
1. 将 Step 2 识别出的所有 risk_id 列在输出中（格式：`[自检] 待覆盖风险: R01, R02, ...`）
2. 每生成完一个轨道的程序后，在输出中再次列出该轨道已覆盖的 risk_id
3. 全部轨道完成后，输出 `[自检] 覆盖完整性确认: N/N 风险均已分配程序`
4. **先读账再写做法**：读任务板待查任务 + 事实行，风险清单章节逐条写明来源
   （无户口 `← T-xxx` / 有户口 `← CG-/RP-/CF-/D-xxx`）；测试指令只许给有来源的
   风险写做法，不许夹带无名风险——对不上账的会被 Step 4.5 对账门拦下：

   ```bash
   python _shared/scripts/validate-program.py <程序MD文件> --ir --strict --workspace <项目根目录>
   ```

> 作用：让 LLM 在生成过程中"看见"完整清单，减少上下文信息衰减导致的遗忘。这是防漏的第一重屏障；第二重是 Step 4.5 的脚本拦截，第三重是拦截后的修复闭环。

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

只输出能回答"为什么这家公司比别家更需要关注"的风险（引用 about-me/my-config 具体特征），禁止通用型风险，≤2个宁缺毋滥。完整触发条件与输出格式见 [step3_program_generation.md](./references/step3_program_generation.md)。

### 3.5 轨道E: 运营效率专项（仅运营效率审计）

三步：AI 自由生成 → 读 `efficiency_audit_playbook.md` 比对 → 提示用户更新 playbook（不自动写入）。

### 3.6 轨道F: 合规专项（仅合规性审计）

三步（与轨道E对称）：AI 自由生成 → 读 `compliance_audit_playbook.md` 比对 → 提示用户更新 playbook。

> **轨道B对抗验证已并入 Step 4.6**（2026-10-07）：裁判判定、阈值、户口规则全部在 [references/red_team_attack.md](./references/red_team_attack.md)。

---

## Step 4: 输出结构（强制格式）

按激活轨道输出九章节，章节激活规则、两列必填（设计理由/测试目的）、HTML 轨道标记、模板全文见 [output_and_gates.md](./references/output_and_gates.md) + [output_template.md](./references/output_template.md)。铁律：漏填两列或标记缺失都会被 Step 4.5 拦下。

---

## Step 4.5: 程序结构化校验（脚本闸机，屏障二）

四步闸机：IR 解析 → 结构化校验（`validate-program.py --ir --strict --workspace`）→ 激活轨道比对（缺轨道/缺标记一律 block）→ 修复闭环（只补遗漏段，不全部重来）。最后给桌子填抽屉入口（`set-drawer`）。完整命令与预期轨道表见 [output_and_gates.md](./references/output_and_gates.md)。

---

## Step 4.6: 红队攻击（检测力对抗验证，强制）

Step 5 管写得好不好，本环节管抓不抓得住：扮恶意内部人出攻击剧本 → 裁判三级判定（30%/50%阈值）→ 回灌修订再攻 ≤2 轮。全程按 [red_team_attack.md](./references/red_team_attack.md) 执行，剧本存档 `audit-programs/red-team/`，未修复盲区标注"执行时补偿性关注"。

---

## Step 5: 质量评估（引用评估框架）

先加载 evaluator 框架（audit_program 清单），声明已过脚本闸机，然后执行：5.1 格式检查 → 5.2 推理链回溯（前3高风险四问）→ 5.3 轨道D唯一性 → 5.4 效率损失强制估算（效率审计时）→ 5.5 质量判定 → 5.6 写评估历史+质量门（regenerate 则回 Step 1）。检查项细则、输出格式、命令全文见 [quality_evaluation.md](./references/quality_evaluation.md)。

---

## 上下文管理原则（CRITICAL）

**硬性限制**：
1. references/ 文件作为背景知识，不得全文输入到上下文
2. 制度分析 JSON 超过 5 个文件时，只读取关键字段而非全文
3. Step 3 每次聚焦 1-2 个轨道，复杂场景分多次生成
4. 生成的审计程序超过 300 行时，拆分为多个文档输出

---

## 禁止事项

硬禁令十条：未读 about-me 不生成、不硬编码公司数值、目的未确认不进 Step 2、不用数量约束替代质量约束、不跳过 Step 2.5、轨道E/F 未读 playbook 不生成、轨道B 不碰系统/公司类风险且只做实质性测试、模糊词禁止替代阈值、不做会计报表审计内容、不跳过质量评估与轨道D唯一性要求（完整十五条见 [quality_checklist.md](./references/quality_checklist.md)）。

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
- [ ] 已完成红队攻击（Step 4.6），剧本已存档，未修复盲区已标注
- [ ] 已完成 Step 5 质量判定并写入评估历史
- [ ] 每个程序的"设计理由"列已填写且非套话（锚定风险/手法/原理）
- [ ] 每个程序的"测试目的"列已填写且可观测（能发现什么异常/证明什么）

**详细清单**：见 [references/quality_checklist.md](./references/quality_checklist.md)

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.x | — | 旧版 |
| 2.0 | 2026-05-12 | 重构 Step 5：废弃Python代码，引用 centralized evaluator 框架；Step 2 数量约束→质量约束；轨道D增加锚定要求；新增推理链回溯和效率损失强制估算 |
| 2.1 | 2026-10-07 | 程序检测力合并：原 Step 3.7（轨道B对抗验证）整体并入新增 Step 4.6 红队攻击（剧本→裁判判定→回灌修订→再攻≤2轮，存档 red-team/），攻击范围扩至全轨道；实体在 references/red_team_attack.md |
