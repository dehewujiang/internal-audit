# 最小必要上下文规则（INPUT-BUDGET.md）

## ① 目的

为 7 个 skill 定义静态输入裁剪规则，解决跨阶段产物被重复全量读取的问题（design-assessments 被 P1.5/P2/P3/P4 全量读 4 次、audit-programs 被 P3/P4 读、findings 随审计累积增长）。判断者 = 本文档设计者，执行者 = 运行时 LLM（机械执行，不做"需要什么"的判断）。

**统一规则**：全量读仅限当前阶段产物；跨阶段产物一律按需（字段级/文件级）。

## ② 裁剪机制定义

### 静态规则（唯一正确实现）

- 裁剪 = 在 SKILL.md 中**写死静态过滤条件**（如"读取 design-assessments/ 中 status=`pending` 的设计观察"），条件在本文档设计期固化。
- 运行时 LLM 只执行指令，**不判断**"需要什么"。
- **禁止**写成"读取你认为需要的部分""根据需要读取"这类把判断权交给运行时 LLM 的表述（与项目确定性优先哲学相悖）。

### 裁剪粒度两档

| 档位 | 含义 | 适用场景 | 先例 |
|:---|:---|:---|:---|
| **文件级** | 读 index/清单/单份目标文件，代替全目录读取 | 产物累积增长（findings/audit-programs） | catalog 按程序编号定位；findings 读 index.json |
| **字段级** | 同一文件只读关键字段（含状态过滤） | 结构化 JSON 大表（design-assessments/policy-analyses） | policy-analyses 超 5 文件只读关键字段 |

### 明确不采用 RAG

不引入向量库/embedding/检索机制。理由：
1. RAG 检索结果不可复现，破坏审计可追溯性；
2. 输入均为 schema 化结构化 JSON，字段过滤优于向量检索；
3. 零依赖原则。

### 完整性三重保障

1. **设计期真实样本验证子集充分性**：本文档每节必答"子集是否足以支撑判断"；
2. **校验脚本确定性检查**：产出完整性由校验脚本对完整文件检查（validate-policy-analysis.py / validate-program.py / validate-finding.py / validate-index.py），不依赖 LLM 读了什么；
3. **规则写死可复现**：同一输入 + 同一指令 → 同一读取行为。

---

## ③ 各 skill 裁剪规则（7 节）

### 1. document-organizer（P1 制度分析）

**当前输入**
- `internal-audit-workspace/documents/` 制度源文件，逐份读全文（SKILL.md:81-82，141）
- 已有分治法（SKILL.md:72-89）：Phase A 只读文件名建立索引（文件级）、Phase B 每次只读一个文件全文、Phase C 只读 JSON 汇总（~800 tokens/份）

**裁剪规则**
- **P1 制度文件（documents/）全量读，严禁裁剪**（C 类，宪法 #7 制度分析完整性是审计正确性根基）
- 分治法即文件级裁剪的既有实践，保持不动

**修改点**
- 无新增裁剪（既有分治法已达标）

**子集充分性**：制度分析完整性不裁剪——不适用"子集"问题。

### 2. audit-interview-designer（P1.5 访谈）

**当前输入**
- `policy-analyses/*.json`（SKILL.md:38）
- `findings/index.json`（SKILL.md:41，已读索引而非全文——文件级先例）
- `design-assessments/[主题]_设计观察.json`，建立 `{id, title, description}` 索引用于矛盾检测（SKILL.md:158——已字段级）
- about-me.md（SKILL.md:39，C 类不裁剪）；risk_framework/interview_templates（背景知识，非全文输入）

**裁剪规则**
- policy-analyses：**字段级**——只读 `verification_status="待确认"` 或 `design_effectiveness="无效"` 的项（SKILL.md:49 已定义该查找逻辑，显式化为静态过滤条件）
- design-assessments：**字段级**——保持 `{id, title, description}` 三字段索引（已有）
- findings：**文件级**——保持读 index.json（已有）

**修改点**
- policy-analyses 读取指令显式化为静态字段过滤表述（写死"只读取 verification_status=待确认 或 design_effectiveness=无效 的项"）

**子集充分性**：确认性问题只针对待确认/无效项，过滤后子集完整覆盖提问依据。

### 3. internal-audit-program-generator（P2 程序生成）

**当前输入**
- `policy-analyses/*.json`，Step 0.3 已字段级提取：`control_gaps`（verification_status="已确认"）+ `risk_points`（severity="高"）+ `conflicts`（SKILL.md:101-105）
- 增量更新模式读 `design-assessments` 待处理线索（SKILL.md:151）
- current-audit.json（SKILL.md:87，C 类）；about-me.md / my-config.md（SKILL.md:91/97，C 类，禁用缓存）

**裁剪规则**
- policy-analyses：**字段级**——保持 Step 0.3 既有静态条件（已达标）
- design-assessments（增量模式）：**字段级**——只读 `status="pending"` 的待处理线索（与"线索过滤"语义一致，SKILL.md:151）

**修改点**
- 增量模式 design-assessments 读取指令加静态状态过滤：`status="pending"`（字段级）

**子集充分性**：已确认缺口/高风险风险点/冲突即 Step 2 风险识别的全部输入；已处理线索不参与，过滤后无信息损失。

### 4. audit-execution-assistant（P3 执行取证）—— 核心裁剪点

**当前输入**
- `audit-programs/` 最新审计程序文档（SKILL.md:59——已文件级定位最新一份）
- **`design-assessments/` 全量读取，无任何过滤（SKILL.md:62）← 问题点**
- 证据：catalog 按当前程序编号定位槽位（SKILL.md:120，文件级先例）
- findings/index.json（SKILL.md:616 更新前扫描）

**裁剪规则（design-assessments）**
- **字段级 + 状态过滤**：只读取 `status="pending"` 的设计观察（未被验证，**不限来源**）
- **铁律：按验证状态过滤，严禁按 source 过滤**——design-assessments 有两种来源（`document-organizer` 制度分析 / `interview` 访谈回填），两种来源的观察 execution-assistant 都有验证职责（SKILL.md:80-92：interview 来源需 ≥2 独立信源交叉验证、contradiction 矛盾排查），按 source 过滤会漏掉访谈线索（违反宪法 #9/#13）
- 验证状态字段 `status`（pending/verified/rejected）已确认存在且必填（document-organizer/references/design-observation-format.md:94），两种来源条目均带此字段 → 按状态过滤不漏任何来源

**修改点**
- SKILL.md:62 读取指令改为：`读取 design-assessments/ 中 status="pending" 的设计观察（不限来源）`——静态过滤，写死

**子集充分性**：Step 0.4 的职责本就是"记录**待验证**的设计观察清单"（SKILL.md:63），`verified`/`rejected` 观察已完成处置（进了 findings 或标记不成立，SKILL.md:74-77），无需再读。

### 5. audit-finding-debate（P3.5 业务攻防）

**当前输入**
- 单条 finding：用户提供 ID / 粘贴 JSON / 读 `findings/` 最新文件（SKILL.md:34）
- debate_framework INDEX.md（SKILL.md:35，按需加载）；角色卡按需加载（SKILL.md:60-61, 145）

**裁剪规则**
- 单文件按需读取已是最小，无强制裁剪
- 可选优化（文件级）：按用户提供的 finding ID 经 `findings/index.json` 定位（复用先例 2），代替目录扫描

**修改点**
- 无强制修改；可选：Step 0 定位目标 finding 时写明"经 index.json 按 ID 定位"

**子集充分性**：辩论对象是单条 finding，单文件读取即完整。

### 6. internal-audit-report-generator（P4 报告）

**当前输入**
- `design-assessments/*.json` **全量**（SKILL.md:152）← 裁剪点
- `findings/*.json` **全量**（SKILL.md:155）← 裁剪点（累积增长）
- `audit-programs/*.md` **全量**（SKILL.md:161）← 裁剪点
- about-me.md / my-config.md（SKILL.md:374，C 类不裁剪）

**裁剪规则**
- design-assessments：**字段级**——只读 `status="pending"` 的观察，字段限 `{id, title, type, severity, description, source}`（报告第 3 章定位是"未经实地验证的假设"，SKILL.md:153-154/241；`{{DESIGN_OBSERVATIONS_COUNT}}` 即未验证数量，SKILL.md:111）
- findings：**文件级**——先读 `findings/index.json` 列清单（{finding_id, origin, risk_level, title}），再逐份读取选中 finding 全文用于第 4 章（保持"读一份分析一份"，不一次性全量塞入）
- audit-programs：**文件级**——只读最新一份（与 P3 执行同一份），提取程序清单作背景（第 2 章"已执行程序清单"）

**修改点**
- 三处读取指令按上述静态条件改写（design-assessments 加 status 过滤 + 字段白名单；findings 改经 index.json；audit-programs 改读最新一份）

**子集充分性**：报告第 3 章只呈现未验证假设（已验证观察已进入第 4 章 findings 呈现）；index.json 提供完整 finding 清单（R06 闸机保证 index 与目录一致，SKILL.md:386-388）；背景章节只需程序清单不需 8 张表全文。

### 7. internal-audit-evaluator（质量评估框架）

**当前输入**
- **无工作区产物输入读取**——本 skill 是权威定义文档（SKILL.md:14"本文件不是执行代码，是权威定义"），由各 skill 的 Step 5 引用其检查清单执行评估

**裁剪规则**
- 无裁剪需求（不读取 policy-analyses / design-assessments / audit-programs / findings 任何产物文件）

**修改点**
- 无

**子集充分性**：不适用（无输入读取）。

---

## ④ C 类不裁剪清单（严禁裁剪）

| 项 | 文件 | 原因 |
|:---|:---|:---|
| 公司背景 | `audit-topics/about-me.md` | 新鲜度设计要求：每次必读、禁用缓存（program-generator SKILL.md:28"每次必须重新读取，禁用缓存"） |
| 操作配置 | `audit-topics/my-config.md` | 同上，阈值/配置随时可能变更 |
| P1 制度文件 | `internal-audit-workspace/documents/` | 制度分析完整性是审计正确性根基（宪法 #7），全量读 |
| 状态文件 | `internal-audit-workspace/current-audit.json` | 唯一状态文件，体积小，全量读 |

## ⑤ 已知先例样板清单（统一规则来源）

| # | 先例 | 位置 | 档位 |
|:---|:---|:---|:---|
| 1 | 证据 catalog 按当前程序编号定位槽位（source_programs），而非全目录扫描 | `audit-execution-assistant/SKILL.md:120` | 文件级 |
| 2 | findings 读 `index.json` 而非全文 | `audit-interview-designer/SKILL.md:41` | 文件级 |
| 3 | 制度分析 JSON 超过 5 个文件时，只读取关键字段而非全文 | `internal-audit-program-generator/SKILL.md:554` | 字段级 |

补充：interview-designer 对 design-assessments 只建 `{id, title, description}` 三字段索引（`audit-interview-designer/SKILL.md:158`）——字段级先例。

---

## 附：7 skill 裁剪一览

| skill | 阶段 | 裁剪动作 | 档位 |
|:---|:---|:---|:---|
| document-organizer | P1 | 不裁剪（分治法已达标；制度文件 C 类） | — |
| audit-interview-designer | P1.5 | policy-analyses 显式字段过滤；其余已达标 | 字段级 |
| internal-audit-program-generator | P2 | 增量模式 design-assessments 加 status=pending 过滤 | 字段级 |
| audit-execution-assistant | P3 | **design-assessments 按 status=pending 过滤（不限来源）** | 字段级 |
| audit-finding-debate | P3.5 | 无强制；可选经 index.json 定位 | — |
| internal-audit-report-generator | P4 | design-assessments 字段白名单+status 过滤；findings 经 index.json；audit-programs 只读最新 | 字段级+文件级 |
| internal-audit-evaluator | 框架 | 无输入读取，不裁剪 | — |
