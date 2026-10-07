# EDA 理念对本项目的启示分析

> 背景：用户引用观点指出，工业领域要有效应用 AI，必须先建立"设计自动化基础设施"，借鉴芯片行业 EDA 工具链与中间表示（IR）规范，让 AI 扮演"综合器"角色而非替代验证流程。本分析将这一观点对照本项目（汽车零部件企业 AI 辅助内部审计）的实际代码与架构展开。

---

## 一句话结论

**本项目不是"需不需要"建 EDA 式基础设施的问题——它已经在建了，而且建的方向是对的。** `constitution.md` 的"地铁闸机模型"、`phase_gate.py` 的三态退出码、`validate-*.py --strict` 写入前阻断、`project_init.py` 硬安全检查，这一整套就是本项目自发长出来的"EDA 基础设施"。ADR-005 明确写下"用代码闸机替代 LLM 记忆"，这跟芯片行业"用 DRC/LVS 替代工程师肉眼检查"是同一个道理。

**但基础设施还不完整。** 两处关键缺口让 AI 综合器的产出无法被确定性流程完整兜底：① 中间表示不统一（审计程序是 Markdown，代码没法校验它的内部逻辑）；② 校验覆盖不全（程序生成、访谈设计两个环节没有对应的 validate 脚本，工具分域也只是"纸面规定"没有代码拦截）。补上这两块，本项目的"设计自动化基础设施"才算闭环。

---

## 问题一：是否需要先构建类似 EDA 的设计自动化基础设施？当前规范化不足在哪？

### 1.1 需要，而且已经自发开建——这是项目最大的优点

芯片 EDA 的核心不是某个聪明算法，而是**一套让多个工具能可靠协作的"底座"**：统一的中间表示（RTL/网表/GDSII）、确定性的规则检查（DRC/LVS）、不可绕过的签核流程（tape-out 前必须过所有检查）。没有这个底座，再好的综合器也只是"看起来能用"。

本项目对照来看，底座的四个构件已经成型：

| EDA 构件 | 本项目对应物 | 位置 |
|---------|------------|------|
| 设计规则约束 | 10 条硬底线 | `constitution.md`「不可违反的约束」 |
| 阶段签核闸机 | `phase_gate.py` 三态退出码（pass/block/prompt_program_update） | `_shared/scripts/phase_gate.py` |
| 确定性规则检查 | 5 个 validate 脚本 + `--strict` 写入前阻断 | `_shared/scripts/validate-*.py` |
| 安全前置检查 | `project_init.py` 覆盖检测 + 配置检测 | `_shared/scripts/project_init.py` |

最关键的一点：**ADR-005 记录了项目自己想通了这个道理**——"LLM 会忘记、会跳过、会被 compact 压缩丢失上下文；代码的 exit code 是确定性行为，不依赖 LLM 自觉"。这正是 EDA 哲学的内核：**把"应该做的事"从"提醒 AI 做"升级为"代码不让它不做"**。

### 1.2 当前规范化不足的五个具体点

把 EDA 标准往项目实际代码上套，能清楚看到哪几块还没补齐：

**缺口 A：审计程序的中间表示是 Markdown，不是结构化 JSON——代码无法校验它的内部逻辑。**
`validate-program.py` 实际只能做四件事（见代码）：查占位符 `_X_`/`{{}}`、查开关型判断词（是/否/有/无）、查轨道标识（A-F）、查是否引用公司具体事实。这些都是**正则文本扫描**，不是结构校验。它没法回答"每个风险点是否都有对应程序""取数来源字段是否填了""六轨道的程序编号是否连续"这类问题——因为程序是 Markdown，这些信息没有结构化字段承载。这就像芯片综合器输出的网表如果是个 Word 文档，DRC 工具根本无从读起。

**缺口 B：两个环节没有 validate 脚本。**
`memory/project.md` 自己列的已知缺口：finding-debate 缺 Step 5、interview-designer 缺 `validate-interview.py`。审计程序（最关键的中间产物）虽然有 `validate-program.py`，但如上所述只是文本扫描，没有真正的 schema 级校验。对比 finding 的 `validate-finding.py` 做了 8 项结构化校验（schema 合规、根因存在性、根因深度、CCEER 五要素、证据等级、直觉引擎、根因-证据匹配、决策理由），程序校验的深度远远不够。

**缺口 C：工具分域只是纸面规定，没有代码拦截。**
`context.md` 活跃风险第 3 条明确写着："🟡 工具未按 phase 分域——LLM 可能在不对的阶段用不对的工具。CLAUDE.md 已有 phases 字段但无代码级拦截。" 芯片流程里，一个 P&R 工具不会让你在综合没跑完时就调用它——流程是工具链强制的。本项目目前靠 LLM 自觉读 CLAUDE.md 的 phases 字段，这正是 EDA 要消灭的那种"靠自觉"。

**缺口 D：无可观测性——决策追溯不完整。**
`context.md` 第 4 条："🟡 无可观测性——决策理由、证据链追溯不完整。" `phase_gate.py` 有 `audit_trail`（记录阶段切换），`validate-finding.py` 检查 `decision_rationale` 字段，但这是零散的、不是系统性的。芯片 EDA 每一步都有日志和版本，能回溯"这个网表是哪个综合参数跑出来的"。本项目的 `current-audit.json` 同时承载业务状态和执行状态（AGENTS.md 自己标注的 gotcha），耦合度高，追溯链不完整。

**缺口 E：current-audit.json 职责过载。**
AGENTS.md 明确指出："`current-audit.json` 同时承载业务状态和审计执行状态"。EDA 里设计约束、工艺参数、流程状态是分开的；本项目把审计主题、风险域、阶段状态、消费标记（`design_observations_consumed`/`whistleblower_pending`）、审计轨迹全塞在一个文件里，任何一个字段被 LLM 误改都可能连锁影响。

---

## 问题二：AI 应定位为综合器还是其他角色？如何确保关键验证/sign-off 由确定性流程完成？

### 2.1 当前定位基本正确，但表述不够统一

本项目各 SKILL.md 对 AI 角色的自我定位其实已经接近"综合器"：

- `internal-audit-program-generator/SKILL.md`：自称"内部审计推理引擎，不是通用模板工厂"——把制度分析（输入）综合成审计程序（输出），这正是综合器。
- `audit-execution-assistant/SKILL.md`：自称"引导者和分析者，不是替代者"，明确列出"不能替代实地盘点、不能登录系统、不能代替访谈、不能做法律定性"——这是清晰的综合器边界。
- `constitution.md`：自称"自主判断和决策的审计智能体"——这个表述偏强，跟"综合器"定位有张力。

**结论：AI 应定位为综合器，不应定位为"自主决策智能体"。** 综合器的本质是：把上游输入（制度分析、访谈线索、证据数据）按照规则"编译"成下游产物（程序、finding），但**产物是否合格由独立的确定性校验判定，不由综合器自己说了算**。`constitution.md` 里"自主判断和决策"的表述建议收敛为"自主推理，但结论受闸机和校验约束"——一字之差，责任归属完全不同。

### 2.2 项目已经做对的：用代码闸机把验证从 AI 手里拿走

这一点项目已经走在正确路上，值得肯定：

- **阶段签核不由 AI 决定**：`phase_gate.py` 的 `check_exit_conditions()` 是纯 Python 代码，检查的是文件是否存在、字段是否为空，AI 改不了 exit code。`advance` 前先 `check`，block 就 exit 1，prompt_program_update 就 exit 2——AI 无法"自己把闸机搬开"（constitution.md 原话）。
- **写入前阻断**：`validate-finding.py --strict` 在 finding 写入 `findings/` 前跑 8 项校验，不通过就 exit 1。这是"产出即校验"，综合器不能直接把半成品塞进下游。
- **快照回滚**：`snapshot_audit_state()` 每次前进前存快照，保留最近 20 个，错了能回退——对应 EDA 的版本管理。
- **硬底线代码化**：10 条约束里，"高风险必须有 A/E 级证据""证据必须有 reliability_grade"这些已经被 `validate-finding.py` 的 `check_evidence_grade` 和 `check_cause_evidence_gap` 落成代码，不是靠 LLM 记忆。

### 2.3 还没做到的：两处 sign-off 仍依赖 AI 自觉

**漏点 1：审计程序没有真正的 sign-off。**
程序生成后写进 `audit-programs/`，`validate-program.py` 只做文本扫描（见 1.2 缺口 A）。也就是说，程序的"质量"目前完全由 program-generator 这个综合器自己保证，没有独立校验说"这个程序合格，可以放行给执行阶段"。这就像综合器跑完没有 DRC，直接把网表扔给布局布线。

**漏点 2：工具分域无代码拦截（1.2 缺口 C）。**
AI 可能在 Phase 1 就调 execution-assistant，或者跳过 phase_gate 直接干活。EDA 里这是不可能的——工具链按顺序串联，前一步没过下一步工具不启动。本项目需要把"当前阶段允许调哪些 skill"从 CLAUDE.md 的文字描述变成代码检查（比如在 skill 入口加一个 `phase_guard` 调用，对不上当前阶段就 exit 1）。

**漏点 3：报告生成前的 sign-off 不完整。**
`phase_gate.py` 对 phase_3→phase_4 只检查"findings/ 有没有 F-*.json"和"report_type 有没有选"，但不检查 finding 本身是否通过了 `validate-finding.py`。也就是说，理论上 AI 可以写一个不合规的 finding 文件放进去，phase_gate 照样放行。需要让 phase_gate 在检查 findings 目录时，顺带校验每个文件都过了 `validate-finding.py --strict`。

---

## 问题三：应建立哪些中间表示规范和工具链？

借鉴芯片 EDA 的"统一 IR + 工具链各司其职 + 确定性校验"三层结构，本项目应建立以下规范：

### 3.1 中间表示（IR）规范——把所有阶段产物结构化

芯片 EDA 的 IR（RTL→网表→GDSII）每个都有严格 schema，工具间只通过 IR 通信。本项目的"IR"就是各阶段输出的 JSON 文件，但目前规范程度参差：

| 阶段产物 | 当前格式 | 问题 | 建议 |
|---------|---------|------|------|
| 制度分析 `policy-analyses/*.json` | JSON | 有 `validate-policy-analysis.py` 但无 --strict | 补 --strict，定义完整 schema |
| 设计观察 `design-assessments/*_设计观察.json` | JSON | 无独立校验 | 补 `validate-design-observation.py` |
| **审计程序 `audit-programs/*`** | **Markdown** | **代码无法校验内部逻辑** | **升级为结构化 JSON（核心改造）** |
| 审计发现 `findings/F-*.json` | JSON | 校验最完整（8 项） | 已达标，作为其他 IR 的样板 |
| 证据 `evidence/` | 文件 + 元数据 | 无统一 schema | 定义 evidence schema（含 reliability_grade 必填） |
| 状态 `current-audit.json` | JSON | 业务状态+执行状态耦合 | 拆分为 `audit-context.json`（业务）+ `audit-state.json`（执行） |

**最关键的是审计程序的 JSON 化。** 建议定义如下结构（借鉴 finding 的成熟度）：

```
audit-program.json
├── program_id / version / audit_topic / audit_purpose
├── activated_tracks: [A, B, C, ...]        ← 轨道激活，可被 phase_gate 校验
├── risk_points: [{ risk_id, severity, source }]   ← 风险点清单
├── procedures: [{                           ← 程序清单（结构化）
│     proc_id, track, linked_risk_id,
│     name, data_source, steps[],
│     quantitative_criteria,                 ← 量化标准（可校验非开关型）
│     expected_evidence_grade                ← 预期证据等级
│   }]
├── company_facts_referenced: [...]          ← 引用的公司事实（可校验≥N条）
└── quality_check: { placeholder_free, ... }
```

这样 `validate-program.py` 就能从"正则扫文本"升级为"结构化校验"：每个 risk_id 是否都有对应程序、量化标准是否非开关型、轨道激活与审计目的是否匹配——全部可代码判定。

### 3.2 工具链规范——每个工具单一职责，入口出口契约化

芯片 EDA 工具链的每个工具都有明确的 INPUT/OUTPUT 契约。本项目 `geb-l3.md` 规则已经要求 Python 脚本带 L3 头（INPUT/OUTPUT/POS），`compat.md` 规定 `_shared/scripts/` 公共接口是永久契约。应把这个规范延伸到所有 skill：

- 每个 SKILL.md 明确声明：INPUT（读哪些文件）→ OUTPUT（写哪个目录、什么格式）→ GATE（调用哪个 validate/phase_gate）
- 程序生成器的 OUTPUT 从 Markdown 改为 JSON（同时保留一份 Markdown 给人看，但 JSON 是"正本"）
- 每个 skill 入口加 phase guard 调用，不在允许阶段就拒绝执行

### 3.3 校验工具链——补齐三个空缺

对照 finding 的 8 项校验标杆，补齐：

1. **`validate-program.py` 升级**：从文本扫描升级为结构化 schema 校验（依赖 3.1 的 JSON 化）
2. **`validate-interview.py` 新建**：校验访谈回填的 design_observations 是否符合格式、source_role 校验规则是否满足（操作员需≥2 信源）
3. **`validate-report.py` 增强**：校验报告中每个 finding 引用是否都对应一个已通过 `validate-finding.py` 的文件

### 3.4 可观测性规范——决策留痕

芯片 EDA 每步有日志，能回溯。本项目应建立统一的 `audit_trail` 规范（目前 `phase_gate.py` 有雏形但不系统）：
- 每个 validate 脚本输出结构化校验报告（已有 JSON 输出模式）
- 每次 skill 执行记录：输入文件 hash、输出文件 hash、调用的 validate 结果、退出码
- 这些记录写入 `internal-audit-workspace/audit-trail/`，独立于 `current-audit.json`

---

## 问题四：对下一步架构设计和流程改进的具体建议

按优先级排序（P0=阻塞 AI 综合器闭环，P1=显著提升可靠性，P2=锦上添花）：

### P0-1：审计程序 JSON 化（解决缺口 A，最高优先级）

**做什么**：定义 `audit-program.json` schema，program-generator 输出 JSON 正本 + Markdown 副本（给人读）。`validate-program.py` 升级为结构化校验。

**为什么是 P0**：这是唯一一个"AI 综合器的核心产出无法被代码校验"的环节。不解决它，程序生成阶段的 sign-off 就是空的，下游 execution-assistant 拿到的程序质量全靠 AI 自觉。这相当于芯片综合器没有 DRC。

**影响面**：`internal-audit-program-generator/SKILL.md` 的 Step 4 输出格式、`validate-program.py` 重写、`audit-execution-assistant/SKILL.md` 的 Step 0 读取逻辑。

### P0-2：工具分域代码拦截（解决缺口 C）

**做什么**：写一个 `phase_guard.py`，skill 入口调用，传入 skill 名 + 当前 phase，不在允许列表就 exit 1。phase 允许表从 CLAUDE.md 的文字描述固化成代码常量。

**为什么是 P0**：`context.md` 自己标黄的活跃风险。不解决，AI 可能在错误阶段调用错误工具，破坏流水线一致性——EDA 里这叫"流程违规"，是绝对不允许的。

### P1-1：phase_gate 检查 finding 合规性（解决漏点 3）

**做什么**：`phase_gate.py` 的 `check_exit_conditions()` 在 phase_3 检查时，不只查 `findings/` 有没有文件，还逐个跑 `validate-finding.py --strict`，有不合规的就 block。

**为什么是 P1**：防止"写了个空壳 finding 文件就过关"。目前 phase_gate 只查文件存在性，是个漏洞但不算最严重（因为 finding 生成时本身会调 validate）。

### P1-2：补 validate-interview.py + finding-debate Step 5（解决缺口 B）

**做什么**：按 finding 校验的思路，为访谈回填产物写校验脚本；为 finding-debate 补 Step 5 质量回溯。

**为什么是 P1**：项目自己列的已知缺口，补上后全环节都有校验覆盖。

### P1-3：current-audit.json 拆分（解决缺口 E）

**做什么**：拆成 `audit-context.json`（审计主题、范围、公司背景引用——业务不变量）+ `audit-state.json`（当前阶段、消费标记、audit_trail——执行可变量）。

**为什么是 P1**：降低耦合，避免执行状态误改影响业务上下文。对应 EDA 里"设计约束"和"流程状态"分离。

### P2-1：统一可观测性（解决缺口 D）

**做什么**：建立 `audit-trail/` 目录，每个 skill 和 validate 脚本写入结构化执行记录。

**为什么是 P2**：提升可追溯性，但不阻塞当前流水线运转。等 P0/P1 稳定后再做。

### P2-2：constitution.md 角色表述收敛

**做什么**：把"自主判断和决策的审计智能体"调整为"自主推理、受闸机约束的审计综合器"。

**为什么是 P2**：表述调整，但影响 AI 对自身边界的认知，长期重要。

---

## 路线图总览

```
当前状态：EDA 底座已成型 70%（闸机+validate+安全检查），但两处缺口让闭环断开
   │
   ├─ P0-1 程序 JSON 化 ────────→ 补上"综合器产出可校验"这块最关键的拼图
   ├─ P0-2 工具分域拦截 ────────→ 让"纸面流程"变成"代码流程"
   │
   ├─ P1-1 phase_gate 校验 finding → 签核更严
   ├─ P1-2 补 interview validate ──→ 全环节校验覆盖
   ├─ P1-3 拆分 current-audit ─────→ 状态解耦
   │
   └─ P2 可观测性 + 角色表述 ─────→ 长期可靠性
   │
目标：AI 综合器（program-generator / execution-assistant）负责"生成"，
      确定性闸机（phase_gate + validate-*）负责"签核"，
      两者职责分离，AI 永远不能自己给自己盖章。
```

---

## 附：本项目与 EDA 的逐项对照表

| EDA 概念 | EDA 实现 | 本项目对应 | 状态 |
|---------|---------|-----------|------|
| 中间表示 IR | RTL / 网表 / GDSII | 各阶段 JSON 文件 | ⚠️ 程序仍是 Markdown |
| 综合器 | 逻辑综合器 | program-generator / execution-assistant | ✅ 定位正确 |
| 确定性验证 | DRC / LVS | validate-*.py 脚本 | ⚠️ 覆盖不全 |
| 签核放行 | Tape-out 前全检 | phase_gate.py advance | ✅ 已建，有漏点 |
| 设计规则 | 工艺设计规则 | constitution.md 10 条硬底线 | ✅ 部分已代码化 |
| 流程强制 | 工具链串联 | CLAUDE.md phases 字段 | ❌ 无代码拦截 |
| 版本回滚 | 版本管理 | snapshot_audit_state | ✅ 已建 |
| 可观测性 | 全流程日志 | audit_trail（零散） | ⚠️ 不系统 |

一句话：**本项目不需要"从头建 EDA 基础设施"，它需要"把已经开始建的 EDA 基础设施补完"——重点是程序 JSON 化和工具分域拦截这两块。补完之后，AI 综合器和确定性签核的职责分离才算真正成立。**
