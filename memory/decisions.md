# 决策记录

## ADR-001
日期：2026-05（估算）
背景：需要为 Flan 的审计工作搭建 AI 辅助系统
备选方案：
- A) 单一审计 agent，接收自然语言指令执行全部流程
- B) 多个独立 skill，通过文件系统传递状态
最终选择：B
原因：
- Flan 需要控制每个环节的质量，单一 agent 的黑箱不可接受
- 审计各阶段（制度分析→程序生成→证据收集→报告）天然可切分
- 文件系统作为状态传递机制，可审计、可回滚、不丢数据
影响：确定了"技能流水线"的架构 DNA

## ADR-002
日期：2026-05（估算）
背景：审计程序模板化 vs 定制化的选择
备选方案：
- A) 预设审计程序模板，按主题套用
- B) 六轨道动态激活，基于审计目的决定测试策略
最终选择：B
原因：
- Flan 强调不同审计目的（舞弊/内控/合规/效率）需要的程序完全不同
- 模板化无法应对舞弊调查等需要实质性测试的场景
- 轨道 B（舞弊实质性测试）的对抗验证机制是核心差异点
影响：program-generator 采用了六轨道架构

## ADR-003
日期：2026-05（估算）
背景：制度分析出的问题是否应直接写入审计报告
备选方案：
- A) 制度分析发现问题→直接作为审计发现写报告
- B) 区分"设计观察（假设）"和"审计发现（结论）"，前者需实地验证才能升级
最终选择：B
原因：
- 审计方法论的核心是"证据驱动结论"
- 制度文本的缺陷不一定导致实际控制失效（可能有补偿性控制）
- 未经验证的"纸面问题"被被审计方反驳会严重损害报告公信力
影响：建立了 design-assessments/ → findings/ 的升级路径，origin 字段区分来源

## ADR-004
日期：2026-07-06
背景：基于 19 条 AI Agent 标准对项目进行架构评审
备选方案：
- A) 继续当前模式（人工编排），逐步优化各 skill
- B) 先做架构修补（状态机、硬规则代码化），再优化 skill
最终选择：B
原因：
- 评审显示控制流（F8）和硬规则可靠性（F17）是架构级短板
- 当前系统"Flan 不在就跑不起来"，人工编排是最大的单点故障
- 状态机和硬规则代码化的改造成本低（各半天），收益高
影响：P0 阶段状态机 + P0 硬规则代码化排到最高优先级

## ADR-005
日期：2026-07-08
背景：系统审计发现全系统 28 个用户提示点中有 11 个依赖 LLM 自觉执行，遗忘即灾难。需要决定用代码还是文档来保证关键流程不被遗漏。
备选方案：
- A) 在 SKILL.md 中加强硬性描述（MANDATORY_OUTPUT/GATE 标记）
- B) 用代码闸机替代 LLM 记忆（phase_gate exit code、validate --strict exit 1、project_init.py exit 1）
最终选择：B
原因：
- LLM 会忘记、会跳过、会被 compact 压缩丢失上下文
- 代码的 exit code 是确定性行为，不依赖 LLM 自觉
- phase_gate 的闸机模型（地铁闸机）已经存在，只需扩展条件即可
- SKILL.md 标记（MANDATORY_OUTPUT）作为辅助增强，不作为唯一保证
影响：phase_gate 新增 7 个检查条件 + prompt_program_update action；5 个 validate 脚本全部接入 --strict；project_init.py 硬安全检查取代 SKILL.md 软性描述

## ADR-006
日期：2026-07-08
背景：访谈（Phase 1.5）在程序生成（Phase 2-3）之前执行，但程序生成器不消费访谈结果。实际工作中程序初稿和访谈准备应该并行。
备选方案：
- A) 调整阶段顺序，把访谈移到程序生成之后
- B) 程序生成器增加增量更新模式，v1.0（初稿）→ 访谈 → v1.1（补充）
最终选择：B
原因：
- 现实中审计组长写程序的同时审计员已在约人访谈，不可能等访谈全做完再动笔
- 程序初稿基于制度分析生成，访谈后做增量补充（第十章/十一章），不推翻初稿
- 举报材料同理，在任意阶段到达时增量补充
影响：program-generator 新增 Step 6 增量更新模式；phase_gate 支持 Phase 2-3 重入；访谈回写后 design_observations_consumed flag 触发闸机提示

## ADR-007
日期：2026-07-08
背景：project-init 涉及两个不可逆操作——覆盖已有项目（数据丢失）和缺失配置时强行创建（下游全报错）。需要决定用 SKILL.md 还是 Python 脚本保证安全。
备选方案：
- A) 在 SKILL.md 中加强硬性检查步骤描述
- B) 写 project_init.py 脚本，在 mkdir/写文件前做硬检查
最终选择：B
原因：
- 覆盖已有项目是数据丢失场景，不能靠 LLM 自觉
- Python 脚本的 exit 1 是确定性行为，LLM 无法绕过
- 与 phase_gate、validate --strict 形成一致的"代码闸机"模式
影响：_shared/scripts/project_init.py 创建；project-init SKILL.md 在 Step 3 前强制调用该脚本

## ADR-009
日期：2026-07-10
背景：系统在多处文档引用"工具分域规则表"但该表从未存在，LLM 可在任何阶段调用任何工具。
备选方案：
- A) 在 CLAUDE.md 补上那张软性表格，靠 LLM 自觉
- B) 用代码闸机（phase_gate tool-check + exit 1）硬阻断跨阶段工具调用
最终选择：B（+ A 作为辅助）
原因：
- 与 phase_gate check、validate --strict 形成统一的"代码闸机"模型
- 数据结构设计（PHASE_TOOLS dict + GLOBAL_TOOLS set + EVALUATOR_TOOLS set）消除分支，每个阶段只维护 1-2 个专属工具名
- --force 留逃生门（回退场景），写入 audit_trail 永久可追溯
影响：phase_gate.py 新增 tool-check 子命令 + 82 行代码；CLAUDE.md 新增 Tool domain table 节

## ADR-010
日期：2026-07-10
背景：CLAUDE.md 过去被直接拷贝到审计项目，但它包含大量开发专用内容（rules junction、architecture gotchas、key files），对审计运行时是噪音。
备选方案：
- A) 继续用同一个 CLAUDE.md，在文件内用注释区分"开发用"和"运行用"
- B) 拆分 CLAUDE.md（开发版）和 CLAUDE-project.md（运行版），setup-project.ps1 拷贝后者
最终选择：B
原因：
- 一个文件两个读者 = 两边都不满意。开发需要知道 rules 怎么 junction，运行需要知道闸机怎么用——这不是同一份文档
- setup-project.ps1 已经处理拷贝逻辑，拆分成本为零
- 运行版砍了 4 节（~40%内容），更聚焦
影响：新建 CLAUDE-project.md；setup-project.ps1 改为拷贝 CLAUDE-project.md → CLAUDE.md

## ADR-011
日期：2026-07-10
背景：setup-project.ps1 最初只 junction skills 和拷贝两个配置文件，漏了 _shared/、tools/、audit-topics/、memory/ 四条血管。
备选方案：
- A) 在文档里写"记得手动创建这些目录"
- B) 脚本一站式完成所有 junction/copy/mkdir + 末尾自检
最终选择：B
原因：
- 部署遗漏是灾难性的——缺 _shared/ 闸机全瘫，缺 tools/ OCR 失败，缺 memory/ session 协议中断
- 脚本末尾自检 8 个关键路径，部署完立即知道缺了什么
- 与 project_init.py 形成"部署安全 + 运行时安全"的里外两层
影响：setup-project.ps1 重写（24行→140行）；明确区分 junction（不改动源码）和 copy（可独立定制）和 mkdir（项目专属数据）

## ADR-008（续）
背景：评估 document-organizer 提取完整性的四个弱点及下游弥补能力。四个弱点：1) 提取完整性无法保证（漏控制点）；2) 跨段落隐含控制无法拼接；3) 风险判断依赖主观推理；4) 两次分析结果不一致。
评估结论：
- 弱点1：被 program-generator 的三条独立风险来源（经验/系统/公司）有效兜底，残余风险低
- 弱点2：program-generator 无法弥补——它拿不到制度原文，只能消费已被提取的碎片，残余风险高
- 弱点3：事实锚定规则和量化标准检查改善了"多严重"的判定，但没治"是不是风险"的根，残余风险中
- 弱点4：当前系统完全没有跨次一致性检查，残余风险高
影响：弱点2需要从 document-organizer 输入端解决（全文搜索拼上下文或先做控制索引再做详情）；弱点4需要加"两次提取+差异对比"或"与上次结果比较"机制。两项记入 TODO.md 待办。

## ADR-012
日期：2026-07-10
背景：系统支持两个部署模式——开发环境（黄金源，需要实时同步）和运行环境（审计项目，需要行为稳定）。Junction 实时同步虽然方便但意味着一处改坏全盘崩溃。
备选方案：
- A) 保持 junction 作为唯一部署方式，依赖开发纪律保证不破坏旧项目
- B) 新增 --stable 模式（copy 替代 junction），锁版本 + 提供增量升级能力
最终选择：B
原因：Junction 违反"Never break userspace"原则——正式审计项目需要确定性。增量升级让 Flan 先看差异再决定升不升。
影响：setup-project.ps1 新增 --stable + VERSION.lock.json；新建 update-project.ps1 + VERSION.json

## ADR-013
日期：2026-07-10
背景：审计关键判断（为什么这样定级/选范围/出结论？）散落在 LLM 对话文本中，无法结构化查询，无法在审计后被挑战时举证。
备选方案：
- A) 依赖 LLM 自然记录理由
- B) 定义 9 个标准化决策点 + SKILL.md 强制输出 + validate 硬检查 + queries.py decide 查询
最终选择：B
原因：审计准则要求记录"重大判断依据"，被审计方挑战时不能答"AI 当时这么判的"。代码闸机比 LLM 自觉可靠。
影响：decisions_schema.py；4 个 SKILL.md 补 decision_log；4 个 validate 补决策检查项；queries.py decide

## ADR-014
日期：2026-07-10
背景：审计项目数据各自存储在项目文件夹，Flan 开新项目时看不到历史 finding/程序/趋势。"同一主题去年审计了什么？"、"这个供应商之前出过问题吗？"——审计日常三问全答不了。
备选方案：
- A) 保持单项目数据模型，靠人工翻阅历史文件夹
- B) 建 projects-index.json 注册表 + queries.py --cross-project 跨项目查询
最终选择：B
原因：改动成本极低（一张表 + 现有命令加 --cross-project 参数），不破坏任何现有逻辑。
影响：新建 projects-index.json；queries.py 新增 CrossProjectSource 类 + register 子命令 + 4 个命令 --cross-project 扩展

## ADR-015
日期：2026-07-10
背景：queries.py 膨胀到 1327 行，4 个命令（findings/search/compare/summary）各内嵌单项目/跨项目数据获取分支，同一 if/else 模式写了 4 遍。
备选方案：
- A) 保持单文件，在函数内部进一步提取公共子函数
- B) 引入 DataSource 抽象层 + 拆成两个文件（queries.py 795 行 + query_data_sources.py 536 行）
最终选择：B
原因：
- 分支消除（好品味原则）：通过 DataSource 协议让"数据从哪来"变成构造参数，而非运行时判断。4 个 if/cross-project 分支 → 0。
- 数据结构优先：SingleProjectSource 和 CrossProjectSource 实现相同接口，调用方不感知差异。
- 内部接口不变：CLI 子命令名、参数、输出格式全部保持。queries.py 无 Python 导入者——纯 CLI 调用。
- 撤回成本极低：一次 git revert。
影响：queries.py 1327→795 行；新建 query_data_sources.py 536 行；cmd_* 函数从平均 90 行压到 20-35 行。

## ADR-016
日期：2026-07-14
背景：源仓库 10 个审计技能在根目录，`.claude/skills/` 只有 2 个 geb-* 技能。`setup-project.ps1` 从根目录逐个部署（正确），`update-project.ps1` stable 模式整目录复制 `.claude/skills/`（只有 2 个），导致每次更新丢失 10 个审计技能。
备选方案：
- A) 修复 `update-project.ps1` 让它也从根目录读取技能列表（保持两个来源一致）
- B) 统一到 `.claude/skills/` 作为唯一来源，setup 和 update 都从这读
最终选择：B
原因：
- Claude Code 本身只看 `.claude/skills/` 发现技能——源仓库自己在本地也应该是自洽的
- 统一来源消除"两个脚本读不同目录"的结构性不一致
- 通过 junction 建立映射（不挪目录），保持向后兼容
影响：
- `.claude/skills/` 下新增 10 个目录 junction
- `setup-project.ps1` 改为扫描 `.claude/skills/` 自动发现（消除硬编码列表）
- `update-project.ps1` stable 模式改为逐技能合并
- `.claude/settings.json` 和 `.claude/rules/` 补充到部署流程

## ADR-017
日期：2026-07-22
背景：全系统数据流转审查发现 27 个问题，其中 validate-finding.py 校验的 schema 与 finding_schema.md 定义完全不同。这导致 audit-execution-assistant 按新 schema 生成的 finding 必定校验失败。
备选方案：
- A) 修改 finding_schema.md 以匹配 validate-finding.py 的旧 schema
- B) 重写 validate-finding.py 以匹配 finding_schema.md 的新 schema 1.2.0
最终选择：B
原因：
- finding_schema.md 1.2.0 的扁平结构（title/risk_level/origin/evidence[]）更适合 LLM 生成
- 旧 schema（finding_title/finding_metadata/risk_classification）是嵌套结构，LLM 容易出错
- 统一后 report-generator、finding-debate 也使用同一套字段名
影响：validate-finding.py check_schema_compliance 重写；filename 匹配 FIND- → F-；finding_schema.md 补充辩论字段；CLAUDE-project.md 更新引用

## ADR-018
日期：2026-07-22
背景：三个新需求出现：1) LLM 无法处理数万行数据 → 需要 Python 预处理；2) LLM 推理前后的校验脚本可能被跳过 → 需要硬闸机；3) constitution #10 制度完整性检查一直无执行代码。
备选方案：
- A) 在 SKILL.md 中加强描述性检查流程，靠 LLM 自觉
- B) 新增三个确定性 Python 脚本
最终选择：B
原因：
- 与 ADR-005/ADR-009 一致：代码闸机是唯一可靠的执行保障
- data_executor 解决 LLM token 窗口限制问题（与 ADR-005 的"LLM 会忘"同理——LLM 也读不完大数据）
- audit_gate 填补了"生成后、输出前"的空窗期——phase_gate 管阶段，validate 管格式，但"刚生成完"这一步无人看守
- check_mandatory_coverage 把 constitution #10 从纯文本约束变成可执行检查
影响：
- 新增 _shared/scripts/data_executor.py（沙箱 + 8 预制工具）
- 新增 _shared/scripts/audit_gate.py（precheck/postcheck/status）
- 新增 _shared/scripts/check_mandatory_coverage.py（mandatory 模块覆盖检查）
- phase_gate GLOBAL_TOOLS 和 PHASE_TOOLS 扩展
- CLAUDE-project.md 新增升级指令和质量闸机调用点

## ADR-019
日期：2026-07-22
背景：EasyOCR 在中文扫描件上的识别率仅 50-60%，大量制度文档被标记为"【OCR待确认】"，导致 Phase 1 制度分析不完整。
备选方案：
- A) 保持 EasyOCR，增加人工核对指引
- B) 升级到 PaddleOCR（百度开源，专门为中文优化）
最终选择：B
原因：
- PaddleOCR 中文识别率 75-85%，提升约 50%
- 改动量极小（~30 行代码，替换 import 和 API 适配）
- 模型离线运行，数据不出本机
- 一次性下载成本（~500MB）换取长期识别质量提升
影响：tools/pdf_ocr_extractor.py 引擎替换；模型存储路径 D:\90_software\PaddleOCR

## ADR-020
日期：2026-07-29
背景：整改方案 R04 提出新建 `risks_identified.json` 作为风险覆盖度校验的数据源，但系统已有 `program_ir_parser.py` 能从审计程序 Markdown 解析出 ProgramIR JSON（含 `risk_register` + `coverage` 字段），且 `validate-program.py --ir` 已有 `check_ir_coverage_rate()` 做结构化覆盖检查。
备选方案：
- A) 按原方案新建 risks_identified.json，在 validate-program.py 新增 check_risk_coverage() 读取它做逐项比对
- B) 用现有 ProgramIR + `--ir` 模式，把缺失的"接入工作流"补上（在 SKILL.md 中增加 Step 4.5 调用脚本闸机）
最终选择：B
原因：
- ProgramIR 的 risk_register 字段已包含 risk_id + title + desc + type，与 risks_identified.json 的信息完全重叠。另建等于维护两套数据，违反单一事实源原则
- `program_ir_parser.py` 的解析逻辑（风险清单→覆盖度→未覆盖列表）已实现且经过验证，不应重复建设
- 真正缺的不是"检查逻辑"，而是"工作流接入"——SKILL.md 没有在任何步骤调用这套脚本
- 改动量更小：只改 SKILL.md 增加 Step 4.5，不新建文件、不改 Python 代码
影响：整改方案 R04 从"建新文件+新函数"改为"接入现有体系"；R07 同步对齐 ProgramIR 方案

## ADR-021
日期：2026-08-04
背景：证据 v2.0 架构（2026-07-26 部署）虽把存储集中到 `evidence/_files/`，但 `audit-execution-assistant/SKILL.md` 规则层仍教 LLM 按程序建子目录（`evidence/{project_name}/{程序编号}_{程序关键词}/`），界面示例层却用 `evidence/_files/`——规则与示例打架。`create_evidence_dirs.py` 也在一次建 74 个空程序目录。同一份证据被复制到多个程序文件夹，集中存储名存实亡。
备选方案：
- A) 保留程序目录结构，把 `_files/` 作为备份/归档层叠加
- B) 取消程序目录，全部集中 `_files/`；修 SKILL.md 矛盾；catalog 检查从"用户说帮我匹配才触发"改为 Step 1 默认动作
最终选择：B
原因：
- 程序目录结构是 v1.0 遗留，v2.0 的核心价值就是"一份证据只存一份"——保留程序目录等于否定 v2.0 本身
- SKILL.md 规则层和示例层打架是 LLM 行为不一致的根因，必须统一
- catalog 检查默认化让"证据-程序映射"成为执行时的默认动作，而非依赖用户记得喊"帮我匹配"
- `create_evidence_dirs.py` 建 74 个空目录是 v1.0 残留行为，与 v2.0 集中存储矛盾
影响：
- `audit-execution-assistant/SKILL.md` 证据路径统一为 `evidence/_files/`，catalog 检查改为 Step 1 默认动作
- `create_evidence_dirs.py` 取消按程序建目录，只建 `evidence/_files/` + `_evidence_catalog.json`
- VERSION.json `2026-07-26-3 → 2026-08-04-1`，commit `b4a0611`
- 部署到武汉长源 + 广东长华，端到端验证通过（162 槽位 catalog，scan→match→status→update 闭环）
- 武汉长源现场清理 70 个空程序目录；B1.1/L1.1 含 60 个真实证据文件按保护规则保留（finding 引用未迁移，待用户决策）

## ADR-022
日期：2026-08-06
背景：git 历史发现 commit `20ad90b`（2026-07-26 证据集中存储改造，本意只改 evidence 目录说明）**静默删除了 constitution 第 11-14 条硬约束 + "阶段流转规则（地铁闸机模型）" + "启动协议"两大章节**。VERSION.json 有 12/13/14 条的添加记录（5eaaa6f/37ff9f9），无删除记录。运行版 CLAUDE-project.md 完整保留 14 条（权威文本）。
备选方案：
- A) 不恢复（认为 11 条已由 incremental_update 承接，12-14 条可用其他方式约束）
- B) 恢复 11-14 条（以 CLAUDE-project.md 为权威文本）+ 恢复阶段流转规则与启动协议（修订版对齐 phase_gate.py 现状）
最终选择：B
原因：
- 12/13/14 条是"防 LLM 拆质量闸机"的宪法级条款（脚本不可用时禁自行替代/可用时必须走/输出必须声明来源），丢失等于制度上允许 AI 绕过校验
- 11 条【证据链不可断裂】在运行版仍存在——不恢复会导致 constitution（13 条）与 CLAUDE-project.md（14 条）不一致，两文件对齐正是治理目标
- incremental_update.md 勘误模式是 11 条的"操作细则"，不是替代——宪法定原则、细则给流程，互补
- 阶段流转规则/启动协议：CLAUDE-project.md 只有部分替代（phase gate 命令说明、memory 启动协议），"回退必须用户确认""AI 不得跳闸机""审计状态启动协议"无替代
影响：
- constitution.md 恢复 14 条硬约束 + 阶段流转规则 + 启动协议（阶段名与 phase_gate.py PHASES 核对一致）
- 恢复内容经 git show 5eaaa6f 取证，commit `fa412dd`

## ADR-023
日期：2026-08-06
背景：全量排查发现 36 处 `~/.claude/skills/internal-audit/...` 坏路径残留（12 个文件）。8-05 修复只覆盖 execution-assistant 4 处，却记录"grep 验证无残留"（假阳性）。`~/.claude` 目录已删除，全部失效；部署项目（stable copy）不带路径改写，坏路径原样进项目，LLM 每次按失效路径找配置 → 触发降级（反复问用户公司信息）。
备选方案：
- A) 全部替换为源仓库根相对路径（internal-audit-evaluator/...）——部署项目无效
- B) 三标准：公司数据→`audit-topics/`、共享脚本→`_shared/scripts/`、跨技能引用→`.claude/skills/{skill}/...`（唯一双环境通吃写法）
最终选择：B
原因：
- CLAUDE-project.md（运行版）本身就是项目根相对标准（audit-topics/、_shared/scripts/），对齐它
- `.claude/skills/` 在源仓库是 junction（指向技能目录）、在部署项目是 stable copy/junction——两种环境都能解析
- execution-assistant 8-05 已修 `_shared/scripts/` 方向正确，但 evaluator 引用（internal-audit-evaluator/SKILL.md）在部署项目仍失效，本次一并修正
影响：12 个文件 36 处替换 + 部署双项目（VERSION 2026-08-06-1）；git 提交 `a8dd3d2`

## ADR-024
日期：2026-08-06
背景：R05/R06/N6 需要决定新校验的强度（block 阻断 vs warn 提示）。
备选方案：
- A) 全部 block（严格）
- B) 按数据损坏后果分级：catalog/index 校验用 block；制度版本字段用 warn
最终选择：B
原因：
- `_evidence_catalog.json` 损坏会误导"证据缺失/已收集"判定，`index.json` 漂移会让报告汇总统计出错——损坏后果是"错误的审计结论"，必须 block
- 存量 policy-analyses JSON 普遍无 document_info 版本字段，block 会卡死存量项目；新输出由 SKILL.md 强制必填，脚本 warn 提示补齐
- 与既有 validate 脚本的分级逻辑一致（schema/ocr block 级，其余 warn 级）
影响：
- 新建 `validate-catalog.py`、`validate-index.py`（block 级，exit 1/2）
- `validate-policy-analysis.py` 新增 `document_version` warn 级检查
- execution-assistant Step 1、report-generator Step 1 挂接调用；commit `fa143a4`

## ADR-025
日期：2026-08-06
背景：add-design-columns 执行中，测试四连发现 output_template.md 模板表头**从来**不含「程序编号/判定标准/取证方式」列，而 Step 4.5 闸机的解析器（`_is_program_table` 要求表头含"程序编号/补充编号"）和校验器（硬查判定标准/取证方式）要求这些列——严格按模板生成的程序必然被闸机拦截。模板与真实产出结构长期脱节（真实产出如 fixture v1.1 一直带这些列），闸机接入（当日 R04）才暴露。
备选方案：
- A) 修改解析器放宽程序表识别（去掉"程序编号"表头要求）
- B) 模板表头对齐真实产出结构（fixture v1.1 为基准），零脚本改动
最终选择：B
原因：
- 真实产出本来就带这些列（LLM 一直这么生成），模板是简化失真——修模板让"文档-机器要求"一致，而非放宽机器要求迁就失真文档
- 零脚本改动符合本任务"Must NOT 改 .py"的边界；解析器按表头关键词找列，加"程序编号/判定标准/取证方式"列不影响其字段映射
- 模板对齐后 Step 4.5 闸机成为"LLM 按模板生成即通过"的良性闭环
影响：
- output_template.md 8 张表表头对齐真实结构 + 两新列（commit 26d4cc2）
- 顺带修正 SKILL.md Step 4.5 命令 `--ir <path>` → `--ir --strict`（实测 --ir 是布尔开关，commit 181000f）
- 重测全链路 PASS；VERSION 2026-08-06-4 部署双项目
