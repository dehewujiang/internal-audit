# TODO

## 进行中
（无）

## 待办

### 🔴 高优先
- **R09 真人完整跑一遍**（跨session欠账+2026-10-07新增+2026-10-08再新增）：4 次 SKILL 改动（10-07 批）+ 2 个新环节（Step 4.6 红队攻击、debate 画像/实战援助）+ **4 份 SKILL 关双轨改动**（执行只上桌/报告只读桌子/吵架对单号/问话读桌子，commit `94b8f1f`）+ **任务板待查→已结全程**（立任务/查实转事实/查否作废）+ **对账门**
（孤儿拦/全覆盖放行）都要真人行为验证。验证点：①红队剧本是否落到具体程序行 ②debate 是否先问画像再开演 ③**新项目从执行到报告全程无 findings/ 落盘** ④**写入口拒收真实触发**（红格无 A/E 被 exit 2 打回）⑤**先贴后上顺序自然发生**⑥**`next` 看板各阶段可读**。commit 标注 `已人工回归: [项目] [评级]`
- **闸机接 `--ir`**（2026-09-10 发现）：`audit_gate.py` 调用 validate-program 时**从不传 `--ir`**，导致"覆盖率 / 判定标准 / 数据来源"三类阻断**从未生效**（而 `DATAFLOW.md:41` 与 program-generator `SKILL.md:426` 都写着应传）。属"加严"，与已完成的"松绑"（ADR-031）分开排期。两个副作用要先处理：`program_ir_parser` 导入失败 → exit 2 会误拦；`ir_parse` 解析失败只算 warn 会误放
- **部署到双项目**：三个版本的建设成果均未上现场——架构加固（08-11-3）、新桌子 ledger（09-04-5）、闸机修复（09-10-2）。用户按 `update-project.ps1` 执行；广东长华 / 武汉长华 VERSION.lock 仍停在老版
- **R09 人工抽查**：4 次 SKILL 改动（报告 Step 2b / 执行写桌子 / 问话 / 看制度 / 吵架）的钩子欠账。用户手工完整跑一遍报告后，commit 标注 `已人工回归: [项目] [评级]`（清单见 `tests/prompt_snapshots/test_prompt_regression.md`）
- **N8 调查方法合规分级**：`fraud_investigation_methods` 含"小黑屋 / 威胁施压"内容，涉及个人合规风险——用户搁置，建议尽早决策

### 坑2 整改（验证优先 / 防自证）
- ✅ 第一批（2026-09-10，ADR-029）：三把小刀 + 漏洞1 原文抽查 —— **已完成并合并 master**
- ⬜ **第二批**：漏洞2 主体（覆盖率分母改上游独立清单）——前置依赖未满足：须先统一上游输出 schema（`json-schema.md` 声明与真实产物漂移）+ 积累 design-assessments 实例（全库零实例）
- ⬜ **第三批**：漏洞3 主体（证据等级系统盖章——data_executor 导出自动 A、OCR 自动 C+待确认、AI 只能标 E 并附来源）
- ⬜ 附带发现：`validate-policy-analysis.py` 的 `check_control_points_traceability` 所查字段列表（source_section/source_doc/source_clause/原文出处）**不含真实产出最常用的 `source`**，会对真实数据误报"缺少原文出处"。下次动该脚本时一并修

### 其他
- **推远程**：三个仓库均有本地领先提交未推——`~/.claude/`（新建，尚未设远程）、`12_AGI/`、`internal-audit/`
- 增量制度分析脚本（`analysis_manifest.py` + `incremental_analysis_gate.py`）已入库未接入（全库 0 引用）。判定：设计超前、需求未触发 → 保留不删，待制度更新频繁时接线。记录见 `_shared/scripts/README.md`
- `create_evidence_dirs.py` 重构候选：名为建目录、实为 457 行解析器；3 处死代码（v2.1 取消程序目录后遗留）；与 `evidence_catalog.py` 职责重叠。功能在用，不紧急 → 下次动 evidence 时重构
- C6 推理日志全量铺开：试点已完成，跑 1 个真实审计项目后评估（见 `REASON-LOG.md`）
- P-2026-002 广东长华程序从 v1.0 升级到 v3.0（缺"取证方式"列，无法自动生成 catalog）— 用户搁置
- [可选] B1.1/L1.1 目录 60 个证据文件是否迁入 `_files/` 并同步更新 finding 引用路径（`findings/B1.1_考勤数据手工传递篡改_待核实异常.json` 的 evidence.files 为硬编码引用）— 待用户决策
- 部署后做一次完整证据匹配流程端到端测试（武汉长源已完成；广东长华待程序升级后做）
- `data/evaluations/2026-07-17.jsonl`：删除旧快照前扫描发现的独有文件，拟并入源仓库但该目录当前为空，需确认是否已并入

## 搁置
- 🟢 模型分级（便宜模型 vs 强模型按需使用）— 单人使用 token 成本可控
- 🔵 每个 skill 返回结构化摘要 — ROI 极低
- 🔵 统计抽样方法 reference — 用户搁置

## 阻塞
- 无

## 已完成（2026-10-08）
- ✅ **程序视图化实施**（一项任务一个提交）：validate-program 加--workspace跑账上对账（孤儿block）+编程序Step3先读账/4.5加参/增量改走任务板+快照同步+B5事前红全绿。ADR-041。R09增项：对账门真人验证
- ✅ **任务板第一步实施**（一项任务一个提交）：桌子加tasks(1.3，就地升级)+add-task/close-task写入口+门卫待查提醒+编程序2.4/执行结任务两处SKILL+3快照同步+B4事前红全绿。ADR-040（B方案：任务板非事实行，不复活已作废程序落格）。R09增项：任务板待查→已结真人验证
- ✅ **下一步命令第三步实施**（`490f124`，一项任务一个提交）：phase_gate 加 `next` 人话看板（能干/还缺/工具一次给全，只报不拦永远 exit 0，与 check/status 共存）+ B3 红转绿（7红→7绿）。ADR-039。SKILL 未动快照不触发
- ✅ **写入口收权第二步实施**（`0a3f60d`，一项任务一个提交）：add-evidence 加 `--grade` + add-line 红格无 A/E exit 2 拒收（只拦新增①a/一律拒收②a/删文件回退③a）+ check.py 改读桌子（两档不变）+ 旧测试迁移 + B2 红转绿（7红→13绿）。ADR-038。旧退出码不动（细案"统一"收回）
- ✅ **关双轨第一步实施**（`94b8f1f`，一项任务一个提交，checkpoint 合并）：查询只认桌子 + 停写旧格式 + 删 validate-index.py + 4 份 SKILL 并到写桌子 + 快照同步 + B1 事前红测试（红转绿）。用户拍板：A-a（终检用门卫，草稿 validate-finding 保留）、B（历史对比不管老项目）。ADR-037。设计稿纠正三处：validate-catalog 保留 / batch3 测试不用改 / compare_years 不动
- ✅ **重设计稿定稿**（`d77b00a`）：`新架构设计稿_2026-10-08.md`（一个写入口·一本账·一块任务板，不管老项目版）+ 脚本总数实测更正（31→32，漏数 query_display.py）

## 已完成（2026-10-07）
- ✅ **桌子v2.0 全量落地**（`42c4b92`+`31751db`+`0fd49b8`+`17b4f5b`，已推远端）：schema_v2.json（账本+底稿两层，ingested取消，每行带source）+ 冲压车间试点 + MIGRATION.md + 4个SKILL.md改直接写桌（add-line --room/--ref/--status）+ ledger.py加来源字段 + query_data_sources.py认桌子（load_table_findings，老项目兼容）+ 文档同步（DATAFLOW.md/CLAUDE-project.md/AGENTS.md）+ CI（GitHub Actions 8测试+JSON校验）。测试全绿
- ✅ **检测力升级**（`decec7a`）：原Step 3.7并入Step 4.6红队攻击（全轨道，剧本→裁判→修订→再攻≤2轮，实体red_team_attack.md）+ debate画像/实战援助（auditee_profile.md+live_coaching.md）+ 快照adversarial_validation.snap改指向 + test_ledger_fixes.py随迁。8测试全过+回归GREEN+快照闸机过
- ⬜ **快照同步欠账**：cceer_chain.snap / root_cause_challenge.snap 待补（4个SKILL.md改了，snap没跟上）
- ⬜ **文档同步钩子**：用户问"为什么漏了"，确认没钩子管"改完代码→检查AGENTS.md"，建议设一个

## 已完成（2026-09-15）
- ✅ **七方向五拨全部做完并提交**（方案底稿 `~/.claude/plans/eventual-mapping-twilight.md` 全绿）：第一拨收料三嗓子（`74c1a3f`）→ 第二拨账本回写+三修（`bf48dc7`，新测7组）→ 第三拨查询接线（`2b2c253`，新测7组）→ 第四拨追溯沟通卡（`919c8f6`，新测4组）→ 第五拨汇报包（`d5fac13`，新测4组）→ 预算补登记（`c3ed047`）。每拨事前红+旧套件回归全绿；R09抽查规模未触发；快照闸机同步3次。遗留：推远端、删小隔间、进度表列等领导拍板

## 已完成（2026-09-14）
- ✅ **程序风险去重上桌 + 三处实测 bug**：已合并 master（`616557e`，worktree 开发）。①`scan_policy` 只认 `id`/`risk_id`，真实产出用 `gap_id`/`rp_id`/`conflict_id` → 广东长华 33 条制度结论一条上不了桌，已加备选字段名；②`current-audit.json` 去项目根找，标准位置在 `internal-audit-workspace/` 里 → 抽 `_audit_state()` 两处都认；③`design_observations_consumed=true` 时设计观察整房不上桌（9-14 定口径）；④新增 `scan_programs` 收程序 2.1 风险清单（复用 `program_ir_parser.build_ir`），去重靠编号：制度类 `fact_anchors` 命中制度分析已有编号即跳过。实测广东长华 41 条 → 净上桌 35、跳过 6、0 污染。⑤生成器加两条：制度类风险沿用原编号；对抗验证补充建议/效率测算须立设计观察户口（否则死在程序文件尾部）。口径修正见 ADR-034。测试 94 断言，8b 事前红 6 条 / 8c 事前红 4 条
- ⬜ **两个待决小口子**（9-14 提出，用户未表态）：①`scan_design` 的"已消化"只认布尔 `true`，而 `incremental_update.md` 说该字段也可为"已处理编号列表"——若新项目写成列表，会误判为未消化而挂回桌面（一行可改）；②`program_ir_parser` 对广东长华那版表头只解析出 `risk_register`，"步骤"部分 0 个（本次只用风险清单，不受影响）——是否记入长期待办

## 已完成（2026-09-11）
- ✅ **新桌子补漏（A/B/C 三批）**：验货撞出的 9 个问题全修，已合并 master（`0bc2948`）。A 批纯代码（悔药边界崩溃 / 五零件崩溃兜底 exit 2 / 搬老账路径校验）；B 批逻辑+流程（高风险硬证据改扫全桌、建项目自动开桌、抽屉改真入口、五处"没有就跳过"改"桌子必在"）；C 批收料+宪法落地（新增 `sweep` 接 8 类来源按状态自动分格、宪法#10 信号池被门卫消费、宪法#9 新增 `add-gap` 三方向）。老桌子 1.0/1.1 就地升 1.2 不作废（ADR-032/033）。测试 74 条断言，改动前红 29 条。**C5（改宪法#10 指向）用户未点头，未做**
- ✅ **新桌子实测撞出 B 批埋的雷**：B2"建项目自动开桌"100% 会失败——`audit-table/` 目录那时还不存在，`save()` 不建父目录。已修 + 加测试锁死（`ledger.py:save`）
- ✅ **规则与记忆体系瘦身**：项目级规则副本 22 份全清（统一由 `~/.claude/rules/` 提供）；`project-doctrine` 转按需加载（常驻 354→274 行）；`decisions.md` 清实施清单（449→372 行）；启动协议改为"归档不进开场"；新增 `~/.claude/` 版本控制 + Stop hook（文件结构变化时提醒文档同步）

## 已完成（2026-09-10）
- ✅ 闸机三档语义修复（VERSION 2026-09-10-2，ADR-031）：`audit_gate.py` 认三档（0 通过 / 1 打印后放行 / ≥2 拦）+ 参数挪进 ACTIONS.args + UTF-8 输出修复；五脚本入口崩溃兜底（异常→exit 2）；`validate-interview.py` 退出码 1→2；`CLAUDE-project.md` 修两处既存错误；新增 `tests/test_audit_gate_tiers.py` + fixture
- ✅ 坑2 整改第一批（VERSION 2026-09-10-1，merge 851d4a2）：覆盖率漏表修复（分母 10→34）/ E 级证据定义矛盾修正 / 报告可靠性上限声明 / 制度校验原文抽查（ADR-029+030）
- ✅ 开发流程确立：worktree 作开发环境，完成后合并回 master

## 已完成（2026-09-04）
- ✅ 新桌子 ledger 架构：`ledger/` 8 文件 + 五家房间接读写 + 四根线 + 硬度（高风险须 A/E）+ 闸机 checklist 命令 + 部署链同步（VERSION 2026-09-04-5）+ 推远程
- ✅ 真数验证：广东长华 11 张整搬门卫放行；F-004 上桌全程；撕一添鬼拦下；旧回归 2 绿 0 红、快照过
- ✅ 规则拆分：coding-safety（编码专用带 paths）+ work-principles（通用全量）；坑2 诊断（四重闸机核查出 4 漏洞）；纳米测试三问 25 脚本审查

> 更早的批次（08-11 架构加固 C1-C7、08-06 四轮整改、08-04 证据 v2.0、07 月各批）见 `decisions.md` 的 ADR 与 git log——已完成的记录不再进本文件。
