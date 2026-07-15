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
