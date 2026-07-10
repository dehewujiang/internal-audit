# interview-designer-v3 - Work Plan
## TL;DR (For humans)

**你会得到什么**：一份能告诉审计师"先找谁、后找谁、注意什么红线、被拒了怎么办"的访谈方案，不再只是一张问题列表。

**为什么这样做**：当前 interview-designer 的方法论骨架是对的（来源权重、矛盾检测、智能分流），但它缺了三件审计访谈中"人"的事——找谁、怎么开场、对方不配合怎么办。同时整个管线假设"各阶段流水线推进"，但真实审计是迭代的——今天执行中发现线索，明天补访谈，后天更新程序。本方案解决这两层问题。

**不会做什么**：不重新设计闸机——闸机保安全底线，新鲜度做质量提醒。不碰 evaluator 的存储脚本（已验证它们正常工作中）。

**工作量**：5 波、16 个实现 todo + 4 个验证项、5 次提交。纯文本改动为主（SKILL.md 提示词 + 模板扩展），一个新建 Python 脚本。

**风险**：低。所有改动是增量追加，不修改已有接口。唯一的新数据结构（artifacts）不与现有闸机标志冲突。

**关键决策**：
- stale 标志是纯信息提醒，不触发闸机阻断
- record_evaluation.py / quality_gate.py 已验证存在——不删除、不修改
- 模板具体 8 领域已明确（生产、质量、设备、销售、薪酬）
## Scope

### IN
- interview-designer/SKILL.md 增加访谈策略层、伦理协议、非合作处理、追溯矩阵、增量 Mode A、stale 触发
- interview_templates.md 扩展至 8+ 业务领域（生产、质量、设备、销售、薪酬）+ 汽车零部件行业专项 + 舞弊访谈专项
- 新建 `_shared/scripts/validate-interview.py`（Excel 结构 + 内容规则 + --strict）
- `current-audit.json` 增加 `audit_state.artifacts` 节，支持全线制品新鲜度标记
- Mode A 增加 JSON 问题清单副输出（与 Excel 同目录、机器可读）
- CLAUDE.md 记录 `artifacts` 新字段和 stale 流转规则

### OUT
- 不重新设计 phase_gate 闸机模型
- **不删除或修改 evaluator 的 `record_evaluation.py` / `quality_gate.py`**（已验证：两个脚本存在且功能完整，evaluator v2.0 保留它们作为存储管道）
- 不改 interview-designer 之外的 skill 方法论
- 不修改 `_shared/scripts/` 中已有脚本的公开接口
- 不添加 `MANDATORY_GATE` 标记
- 不实现自动文件同步——stale 只是标记提醒

## Verification strategy

本方案的特殊性：改动主体是 SKILL.md（LLM 提示词），不是可执行代码。验证策略分层：
- **结构验证**：新增章节是否存在于 SKILL.md 中（grep 章节标题）
- **引用验证**：所有新增的文件路径是否可解析（文件存在性检查）
- **脚本验证**：validate-interview.py 跑实际 Excel 文件（构造合法 + 非法样本）
- **合同验证**：stale 机制是否在其他 skill 中被正确引用（grep `artifacts` 和 `freshness`）
- **端到端验证**：跑一次完整 Phase 1.5 流程（需人工配合提供回填数据）

## Execution strategy

6 波，按依赖拓扑排序。同一波内无依赖，可并行。

```
Wave 1: C1 核心方法论 — 基础章节（不依赖 C5 数据结构的 T1-T4）
  T1 → T2 → T3 → T4（同文件需串行编辑）

Wave 2: C2 模板扩展 + C6 JSON 副输出
  T7, T8, T9, T12, T18（同文件串行，其他并行）

Wave 3: C5 管线 stale 机制 → C1 的 stale/增量行为定义
  T14 → T11 → T5 → T6 → T16 → T17
  （顺序依赖：schema → 初始化模板 → stale 触发 → 增量模式 → fresh 恢复 → 文档）

Wave 4: C3 校验脚本（validate-interview.py）
  T10（独立，依赖 Wave 1-2 中定义的 Sheet 结构）

Wave 5: 最终验证波
  F1-F4（并行）
```

## Todos

### Wave 1 — C1：核心方法论基础章节（T1-T4）

#### T1：增加"访谈策略层"章节
- **References**：
  - 主文件：`~/.claude/skills/internal-audit/audit-interview-designer/SKILL.md`
  - 上游数据源：`internal-audit-workspace/policy-analyses/*.json`（控制点/缺口/风险点）
  - 公司信息：`~/.claude/skills/internal-audit/audit-topics/about-me.md`（组织架构）
  - 历史发现：`internal-audit-workspace/findings/index.json`
- **改动位置**：在现有"访谈设计原则"（约第 250 行）之前，插入新章节 `## 访谈策略层`
- **内容要求**：
  1. 基于 Phase 1 控制地图生成"访谈顺序拓扑图"——标注哪些岗位有制衡关系，建议先访谈被监督者再访谈监督者
  2. 按岗位角色生成"访谈人选映射表"（格式：`| 控制点 | 建议访谈岗位1 | 建议访谈岗位2(交叉验证) | 优先级 |`）
  3. 每个访谈标注预计时长（操作员 30-45min，中层 45-60min，高层 30min）
  4. 标注访谈间的前置依赖（"访谈 A 完成前不建议访谈 B，因为 A 的信息用于交叉验证 B"）
  5. 输出位置：Excel 增加 Sheet 4（"访谈计划表"）
- **Acceptance criteria**：
  - SKILL.md 中新增 `## 访谈策略层` 章节，含上述 5 项内容
  - Step 2（生成 Excel）的说明中增加 Sheet 4 列结构定义
  - 使用 `grep "访谈策略层\|访谈顺序\|人选映射\|前置依赖" ~/.claude/skills/internal-audit/audit-interview-designer/SKILL.md` 确认所有关键词存在
- **QA**：
  - Happy：读取一份包含 5 个控制缺口 + 3 个高风险点的 policy-analysis JSON → 生成的 Excel 包含 Sheet 4，至少有 3 行访谈映射
  - Failure：policy-analyses/ 为空 → 策略层输出"无法生成访谈策略：缺制度分析数据"，不崩溃

#### T2：增加"访谈伦理与法律护城河"章节
- **References**：
  - `~/.claude/skills/internal-audit/audit-interview-designer/SKILL.md`
  - IIA 标准 1100（独立性与客观性）
  - ISA 240（舞弊责任）
- **改动位置**：在 T1 的访谈策略层之后，插入新章节 `## 访谈伦理与法律护城河`
- **内容要求**：
  1. 访谈开场声明模板——含：审计目的、保密说明、归因/匿名选择、自愿参与声明、舞弊嫌疑处理说明
  2. 受访者权利告知书——含：拒绝回答权、撤回陈述权、查阅访谈记录权
  3. 分场景使用指引：常规内控访谈 vs 舞弊调查访谈（不同的声明措辞和法律要求）
  4. 输出位置：Sheet 3（访谈指南）的第一页增加"开场声明模板"小节
- **Acceptance criteria**：
  - SKILL.md 中新增 `## 访谈伦理与法律护城河` 章节
  - 章节含开场声明模板、权利告知书、分场景指引
  - Sheet 3 指南说明中明确要求首行打印开场声明
- **QA**：
  - Happy：生成的 Excel 的 Sheet 3 首行包含完整声明文本
  - Failure：缺失"舞弊嫌疑处理说明"段落 → Step 5 质量评估标记 ⚠️

#### T3：增加"非合作处理协议"章节
- **References**：
  - `~/.claude/skills/internal-audit/audit-interview-designer/SKILL.md`
- **改动位置**：在 T2 的伦理章节之后，插入新章节 `## 非合作处理协议`
- **内容要求**：
  1. 三种拒绝场景定义：
     - 场景A（无害）：正当理由（出差、病假）→ 记录 + 延期
     - 场景B（红线）：系统性回避（"没时间""我不了解"）→ 🚩 标记 + 升级到设计观察（type=non_cooperation）
     - 场景C（严重）：上级阻挠下属接受访谈 → 🚩🚩 升级为高风险设计观察 + 通知审计负责人
  2. 每种场景的记录模板（写入 `interview-materials/[主题]_非合作记录.md`）
  3. 非合作事件作为独立信号写入 `design-assessments/`
- **Acceptance criteria**：
  - SKILL.md 中新增 `## 非合作处理协议` 章节
  - 含 3 种场景定义 + 记录模板 + 升级路径
  - 信号写入格式遵循 design-observation schema（type=non_cooperation, severity=高）
- **QA**：
  - Happy：模拟"仓管员拒绝访谈"输入 → 生成非合作记录 + D-XXX 观察（type=non_cooperation）
  - Failure：场景C 未标记为"高"严重程度 → Step 5 检测到

#### T4：增加"Phase 1 输出→访谈问题 覆盖度追溯"（Step 5 推理检查新增项）
- **References**：
  - `~/.claude/skills/internal-audit/audit-interview-designer/SKILL.md` Step 5 章节（约第 264 行）
  - `~/.claude/skills/internal-audit/internal-audit-evaluator/SKILL.md` interview 检查清单
- **改动位置**：在 Step 5.2（推理检查）中，在现有 3 项检查之后新增第 4 项
- **内容要求**：
  1. 新增检查项：`④ 【覆盖度】每个 Phase 1 高风险控制缺口（severity=高 的 control_gap / risk_point）是否映射到 ≥1 个访谈问题？`
  2. 执行方式：读取 `policy-analyses/*.json`，提取 severity=高 的条目 → 与问卷问题逐一比对（关键词匹配 + 语义判断）
  3. 未覆盖项输出为列表，标记给用户
- **Acceptance criteria**：
  - SKILL.md Step 5.2 表格中新增第 4 行
  - evaluator SKILL.md 的 interview 检查清单同步新增此项
- **QA**：
  - Happy：Phase 1 有 3 个高缺口，问卷覆盖了 3 个 → 覆盖度 100%，通过
  - Failure：Phase 1 有 3 个高缺口，问卷只覆盖了 1 个 → 输出未覆盖缺口列表，标记 ⚠️

### Wave 2 — C2 + C6：模板扩展 + JSON 副输出

#### T7：新增 5 个业务领域模板
- **References**：
  - `~/.claude/skills/internal-audit/audit-interview-designer/references/interview_templates.md`
  - document-organizer 的行业分析：`~/.claude/skills/internal-audit/document-organizer/references/industry-specific.md`
- **改动位置**：在现有 3 个领域（存货、废料、采购）之后追加
- **新增领域**：生产管理、质量管理、设备管理、销售管理、薪酬与考勤
- **每个领域格式**：含 2-4 个模块，每个模块 2-4 个问题（含问题、追问提示、制度依据参考）
- **Acceptance criteria**：
  - `interview_templates.md` 含 8 个领域标题（原 3 + 新 5）
  - 每个新领域 ≥ 2 个模块，总新增问题 ≥ 30 个
- **QA**：
  - Happy：`grep "^## " interview_templates.md` 返回 8 个领域标题
  - Failure：新增领域的问题缺少"追问提示"列 → 标记缺失

#### T8：新增汽车零部件行业专项模板
- **References**：
  - `~/.claude/skills/internal-audit/audit-interview-designer/references/interview_templates.md`
  - program-generator 的舞弊手法参考：`~/.claude/skills/internal-audit/internal-audit-program-generator/references/automotive_reasoning_guide.md`
- **改动位置**：在 T7 的通用领域之后，新增章节 `## 汽车零部件行业专项`
- **内容要求**：
  1. 废料过磅环节：监磅控制、地磅数据篡改检测、过磅单流转
  2. 模具外协加工：定价机制、委外审批、回厂验收
  3. 成品丝/中间丝库龄管理：超期预警、复检流程、降级使用
  4. 每个专项含"红旗信号"清单（受访者回答中应警惕的信号）
- **Acceptance criteria**：
  - `interview_templates.md` 含 `## 汽车零部件行业专项` 章节
  - 含 ≥ 3 个行业专项子模块
- **QA**：
  - Happy：每个专项含 ≥ 1 个红旗信号
  - Failure：专项问题与通用模板高度重复 → 标记

#### T9：新增舞弊访谈专项
- **References**：
  - `~/.claude/skills/internal-audit/audit-interview-designer/references/interview_templates.md`
  - program-generator 的舞弊调查方法：`~/.claude/skills/internal-audit/internal-audit-program-generator/references/fraud_investigation_methods.md`
- **改动位置**：在 T8 行业专项之后，新增章节 `## 舞弊访谈专项`
- **内容要求**：
  1. 舞弊访谈与常规访谈的关键差异（目标、措辞、法律边界、证据处理）
  2. 提问技巧：漏斗式提问（从一般到具体）、沉默技术、时间线重建法
  3. 法律边界：不得诱供、不得承诺免责、不得冒充执法机构
  4. 证据保全：访谈录音/笔记的保管链要求
  5. 适用场景判断：何时从常规访谈升级为舞弊访谈
- **Acceptance criteria**：
  - `interview_templates.md` 含 `## 舞弊访谈专项` 章节
  - 含"升级为舞弊访谈的判断标准"清单
- **QA**：
  - Happy：`grep "不得诱供\|不得承诺免责\|保管链" interview_templates.md` 均命中
  - Failure：缺少升级判断标准 → 标记缺失

#### T12：更新 design-observation-format.md 的 type 枚举（增加 non_cooperation）
- **References**：
  - `~/.claude/skills/internal-audit/document-organizer/references/design-observation-format.md` 第 85 行（type 枚举定义）
- **改动位置**：`type` 字段的 enum 列表（第 85 行）
- **改动**：`control_gap / design_ineffective / risk_point / conflict / risk_clue` → 追加 `/ non_cooperation`
- **同时更新**：`summary.by_type` 示例中增加 `"non_cooperation": 0`
- **Acceptance criteria**：
  - `grep "non_cooperation" design-observation-format.md` 在 type enum 行命中
- **QA**：
  - T3 中 type=non_cooperation 的 design observation 写入 → 不会因 type 不在 enum 中而被 downstream 拒绝

#### T18：Mode A 增加 JSON 问题清单副输出
- **References**：
  - `~/.claude/skills/internal-audit/audit-interview-designer/SKILL.md` Step 2 章节
- **改动位置**：在 Step 2（生成 Excel）中，增加"同时生成 JSON 副文件"的子步骤
- **内容要求**：
  1. 输出路径：`internal-audit-workspace/interview-materials/[主题]_问题清单.json`
  2. JSON 结构：
  ```json
  {
    "audit_topic": "存货管理",
    "generated_date": "2026-07-09",
    "total_questions": 40,
    "modules": [
      {
        "name": "入库管理",
        "questions": [
          {"id": "Q1", "question": "...", "followup_hints": [...], "policy_ref": "...", "target_roles": ["仓管员", "采购员"]}
        ]
      }
    ],
    "coverage_trace": {
      "control_gaps_covered": ["D-001", "D-003"],
      "risk_points_covered": ["RP-N007-01", "RP-N008-03"],
      "uncovered_high_items": ["D-005"]
    }
  }
  ```
  3. 此 JSON 供管线其他节点编程消费（追溯矩阵、覆盖度检查）
  4. coverage_trace 字段填充方式：在 Step 5.2 执行 T4 的覆盖度检查后，将结果中的 covered/uncovered 列表手动填入此 JSON。若 JSON 晚于 Excel 生成（事后补生成），重新执行 Step 5.2 检查以获取覆盖度数据。
- **Acceptance criteria**：
  - SKILL.md Step 2 含 JSON 副输出规范
  - JSON 结构含 modules + coverage_trace
  - coverage_trace 的填充指令明确（见上方第 4 条）
- **QA**：
  - Happy：生成 Excel 后，同目录存在同名 JSON 文件，`total_questions` 匹配
  - Failure：JSON 中 coverage_trace.uncovered_high_items 非空 → 正常（这是覆盖度信息，非错误）

### Wave 4 — C3：校验脚本

#### T10：新建 validate-interview.py
- **References**：
  - 参照：`_shared/scripts/validate-finding.py` 的 `--strict` 模式设计
  - evaluator 框架 interview 检查清单（evaluator SKILL.md 第 79-83 行）
  - interview-designer SKILL.md Step 2 的列结构定义
- **新文件**：`D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\validate-interview.py`
- **L3 头部**：必须含 INPUT / OUTPUT / POS
- **检查项**：
  1. Excel 文件存在且可被 openpyxl 打开
  2. Sheet 1 表头 = `["模块", "序号", "问题", "追问提示", "制度依据", "访谈记录", "证据索引", "风险标记"]`
  3. Sheet 2 表头 = `["序号", "资料名称", "格式", "责任部门", "是否获取", "备注"]`
  4. Sheet 3 存在（不强制表头格式）
  5. Sheet 4 存在（不强制表头格式——访谈策略层为可选）
  6. 问题列（Sheet 1 列 C）非空行 ≥ 5
  7. 非"是否"类问题占比 ≥ 70%（与 evaluator 框架 interview 检查清单阈值一致）
  8. 制度依据列（Sheet 1 列 E）非空比例 ≥ 50%
  9. DRL（Sheet 2）条目数 ≥ 3
  10. `--strict` 模式下，任何检查失败 → exit 1
- **命令行接口**：`python validate-interview.py <file.xlsx> [--strict]`
- **输出格式**：JSON（与 validate-finding.py 一致）：
  ```json
  {"status": "pass|fail", "checks": [{"name": "...", "result": "pass|fail", "detail": "..."}], "overall": "pass|fail"}
  ```
- **Acceptance criteria**：
  - 文件存在于 `_shared/scripts/` 目录
  - 包含 L3 头部（INPUT / OUTPUT / POS）
  - 对合法 Excel 返回 overall=pass
  - 对缺 Sheet 2 的 Excel 返回 overall=fail
  - `--strict` 下 exit code 1
- **QA**：
  - Happy：构造合法 Excel（含 4 Sheet，10 个问题其中 8 个开放式，5 项 DRL）→ `python validate-interview.py test.xlsx --strict` → exit 0
  - Failure 1：构造非法 Excel（缺 Sheet 2）→ exit 1
  - Failure 2：构造合法 Excel 但开放问题比例 50% → 不传 --strict 时 overall=pass（warning），传 --strict 时 overall=fail

### Wave 3 — C5：管线 stale 机制

#### T14：定义 current-audit.json artifacts 节
- **References**：
  - `internal-audit-workspace/current-audit.json` 现有 `audit_state` 结构
  - CLAUDE.md 第 72 行（current-audit.json 存储规则）
- **改动**：在 `audit_state` 中增加 `artifacts` 字段
- **数据结构**：
  ```json
  "artifacts": {
    "policy-analyses": { "freshness": "fresh", "last_updated": "2026-07-09" },
    "audit-programs": { "freshness": "fresh", "last_updated": "2026-07-09" },
    "interview-materials": { "freshness": "fresh", "last_updated": "2026-07-09" },
    "design-assessments": { "freshness": "fresh", "last_updated": "2026-07-09" }
  }
  ```
- **freshness 取值**：`"fresh"` | `"stale"`
- **规则**：fresh = 自上次生成/更新后无新的上游数据注入。stale = 有新数据写入但下游尚未重新消费。
- **与现有 `design_observations_consumed` 的关系**：
  - `design_observations_consumed` = 布尔闸机标志（硬阻断 Phase 2→3，exit code 2）
  - `artifacts["audit-programs"].freshness` = 软提醒标志（不阻断任何闸机，仅提示审计师）
  - 两者互补非替代：consumed 管"访谈线索是否已被程序消化"（安全底线），stale 管"程序是否可能过时"（质量提醒）
  - 设置时机：Mode B 写回时同时设置 consumed=false（闸机）和 freshness=stale（提示）
  - phase_gate 不读取 freshness 字段——freshness 是纯信息层
- **Acceptance criteria**：
  - current-audit.json schema 文档（或 CLAUDE.md）记录 artifacts 结构
  - project-init/SKILL.md（生成 current-audit.json 的 Step 4.3 模板）包含 artifacts 默认值——见 T11
- **QA**：
  - Happy：新项目 current-audit.json 含 artifacts 节，所有 freshness="fresh"
  - Failure：artifacts 缺少某个必填键 → phase_gate check 时输出 warning

#### T11：更新 project-init/SKILL.md 的 current-audit.json 模板（含 artifacts 默认值）
- **References**：
  - `~/.claude/skills/internal-audit/project-init/SKILL.md` Step 4.3（生成 current-audit.json，约第 144-184 行）
  - T14 定义的 artifacts 数据结构
- **改动位置**：project-init SKILL.md 的 schema 1.1 模板（JSON 示例块）
- **改动**：在 `audit_state` 对象中增加 `"artifacts"` 字段，含 4 个条目，每项 freshness="fresh"
- **Acceptance criteria**：
  - `grep "artifacts" ~/.claude/skills/internal-audit/project-init/SKILL.md` 有结果
  - 模板中 artifacts 结构完整（含 policy-analyses, audit-programs, interview-materials, design-assessments）
- **QA**：
  - Happy：新项目初始化后 → current-audit.json 含 artifacts 节
  - Failure：artifacts 缺少某条目 → 后续 T5/T6 的 stale 触发无法定位对应键

#### T5：Mode B 增加"stale 标记"触发（SKILL.md 行为定义）
- **References**：
  - `~/.claude/skills/internal-audit/audit-interview-designer/SKILL.md` 模式B章节（约第 101 行）
  - T14 定义的 `audit_state.artifacts` 数据结构（本波已完成）
- **改动位置**：在 Mode B 分流输出之后，增加 `### 模式B-附加：制品新鲜度标记`
- **内容要求**：
  1. 当 risk_clue 写入 design-assessments/ 时，同步将 `audit_state.artifacts["audit-programs"].freshness` 设为 `"stale"`
  2. 当非合作事件写入 design-assessments/ 时，同样标记 stale
  3. 更新 current-audit.json 后输出提示："⚠️ 访谈发现新线索，审计程序可能需要更新"
- **Acceptance criteria**：
  - SKILL.md 含"制品新鲜度标记"小节
  - 明确 stale 触发条件（risk_clue 写入 / non_cooperation 写入）
  - 输出提示文本存在
- **QA**：
  - Happy：Mode B 写入 1 条 risk_clue → current-audit.json 中 artifacts 对应程序条目 freshness="stale"
  - Failure：Mode B 只更新了配置（my-config.md），无 risk_clue → freshness 不变

#### T6：Mode A 增加"增量问题生成"模式（SKILL.md 行为定义）
- **References**：
  - `~/.claude/skills/internal-audit/audit-interview-designer/SKILL.md` 工作流程章节（约第 31 行）
  - T14 定义的 artifacts stale 机制（增量模式由 stale 状态触发）
- **改动位置**：在"模式A：生成访谈问卷和DRL"之下，增加子模式 `### 模式A-增量：基于新线索补充问题`
- **内容要求**：
  1. 触发条件：`audit_state.artifacts["audit-programs"].freshness === "stale"`，或用户直接提供新风险线索
  2. 行为：不重新生成整份 Excel，只输出追加的问题（Markdown 列表或追加到现有 Excel）
  3. 输出：`interview-materials/[主题]_补充问题_YYYYMMDD.md`（含新问题 + 对应线索来源）
  4. 与全量 Mode A 的差异：只针对新线索生成问题，跳过已有覆盖的模块
- **Acceptance criteria**：
  - SKILL.md 含"模式A-增量"子章节
  - 触发条件明确引用 artifacts.stale
  - 增量输出文件命名规范明确
- **QA**：
  - Happy：提供 2 条新 risk_clue → 输出 6-8 个追加问题 → 不修改原始 Excel
  - Failure：新线索与已覆盖模块高度重叠 → 提示"该线索已有对应问题"，不重复生成

#### T16：program-generator 的 fresh 恢复
- **References**：
  - `~/.claude/skills/internal-audit/internal-audit-program-generator/SKILL.md`
- **改动位置**：在 program-generator SKILL.md 中，搜索章节标题 `## Step 6：增量更新模式（条件触发）`。在其"消费完成"步骤之后（`design_observations_consumed = true` 行之后）插入 freshness 更新逻辑；若 Step 6 章节不存在，在 Step 4 输出确认之后插入。
- **内容要求**：
  1. 生成/更新审计程序完成后，将 `artifacts["audit-programs"].freshness` 设为 `"fresh"`，`last_updated` 设为当前日期
  2. 增量模式完成（`design_observations_consumed=true`）后同步刷新
  3. 输出提示："✅ 审计程序已更新，制品状态：fresh"
- **Acceptance criteria**：
  - program-generator SKILL.md 含 freshness 更新逻辑
  - 输出提示文本存在
- **QA**：
  - Happy：增量模式完成后 → current-audit.json 中 audit-programs freshness="fresh"
  - Failure：生成失败 → freshness 保持 stale（不写 fresh）

#### T17：更新 CLAUDE.md 和 constitution.md 文档
- **References**：
  - `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\CLAUDE.md` 第 72 行
  - `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\constitution.md`
- **改动**：
  1. CLAUDE.md 的"Architecture gotchas"增加：`artifacts` 节 + freshness 流转规则
  2. constitution.md 在现有决策原则列表末尾（第 10 条之后，约第 64 行之后、第 65 行阶段流转规则之前）增加新原则：`11. 【制品新鲜度】各阶段输出产物在 audit_state.artifacts 中记录 freshness。上游数据变更时标记下游为 stale（提醒，不阻塞）。下游重新消费后恢复 fresh。`
- **Acceptance criteria**：
  - `grep "freshness\|artifacts.*stale" CLAUDE.md` 有结果
  - `grep "制品新鲜度" constitution.md` 有结果
- **QA**：
  - 新增文档段落被 git diff 识别

### Wave 5 — 最终验证波

（见 Final verification wave 章节）

---

## Final verification wave

全部并行执行。全部 APPROVE 才算通过。

#### F1：方案合规审计
- **目标**：确认所有改动符合 constitution.md 10 条硬约束
- **检查清单**：
  - [x] 约束 #7（不得使用示例或占位符）→ T10 validate 脚本的测试用例使用构造数据而非真实公司数据为允许（测试环境）
  - [x] 约束 #8（工具穷举检查）→ 本方案无自设计方案需求，所有改动利用现有工具
  - [x] 约束 #4（证据 reliability_grade）→ T3 非合作记录的 design observation 不涉及证据等级（非 finding）
- **通过标准**：10 条约束无一违反
- **证据**：输出合规检查清单（Markdown）

#### F2：代码质量审查
- **范围**：T10 `validate-interview.py`
- **检查项**：
  - [x] L3 头部存在（INPUT / OUTPUT / POS）
  - [x] 函数 ≤ 30 行（good-taste.md，标记为不紧急信号）
  - [x] 命令行接口清晰（argparse）
  - [x] 输出 JSON 格式与 `validate-finding.py` 一致
- **通过标准**：无 YELLOW/RED 警告
- **证据**：`geb-workflow` 检查输出

#### F3：实际脚本 QA
- **T10 脚本 QA**：构造 3 组 Excel（全合法、缺 Sheet、低开放问题比例），分别验证 exit code 和 JSON 输出
- **通过标准**：所有脚本 QA 通过
- **证据**：QA 执行日志

#### F4：范围一致性
- 对照本轮 Scope（IN/OUT），逐项检查
- 确认无 Scope Creep：没有多改的文件、没有多写的代码
- **通过标准**：IN 全部覆盖，OUT 无一触碰
- **证据**：`git diff --stat` + 逐文件核对

## Commit strategy

5 次原子提交，按波分组：

| 提交 | 消息 | 覆盖 |
|:---:|:---|:---|
| 1 | `feat(interview-designer): add strategy, ethics, non-cooperation, coverage trace` | T1-T4 (C1 基础) |
| 2 | `feat(interview-designer): expand templates 8 domains, industry-specific, fraud, JSON sidecar, schema update` | T7-T9, T12, T18 (C2+C6+schema) |
| 3 | `feat(pipeline): add artifacts freshness, stale/incremental behavior, fresh recovery, docs` | T14, T11, T5, T6, T16, T17 (C5+C1 stale) |
| 4 | `feat(validate): add validate-interview.py with --strict mode` | T10 (C3) |
| 5 | `docs(plan): final verification wave sign-off` | F1-F4 结果 |

- 每次提交前执行 `$env:PYTHONIOENCODING="utf-8"`（Windows UTF-8 修复）
- 每次提交附带简短 body 说明改动原因

## Success criteria

1. ✅ interview-designer SKILL.md 含 6 个新章节（策略层、伦理、非合作、追溯、增量模式、stale 触发）
2. ✅ interview_templates.md 从 3 领域扩展到 8 领域 + 行业专项 + 舞弊专项
3. ✅ `validate-interview.py` 可执行，`--strict` 模式拦截非法输出
4. ✅ `current-audit.json` 含 `artifacts` 节，Mode B 写回自动标记 stale，程序更新自动标记 fresh
5. ✅ CLAUDE.md / constitution.md 记录了 artifacts 和 freshness 机制
