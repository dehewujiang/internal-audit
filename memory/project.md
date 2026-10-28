# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态（2026-10-27）
系统功能完整（12 skill + 四重闸机 + 新桌子 ledger + CI），近期完成**桌子v2.0改数据库**与**检测力升级**，10-08 起落**关双轨三小步 + 任务板第一步**，10-20 起落**审计数据能力第一批（勾稽口径卡 + 画像器）**，10-22 落**探索车道闭环（第一批）**，10-27 落**舞弊线补强一批**：

- **探索车道闭环**（`2041b60`，VERSION 2026-10-22-1）：`data_executor` 执行留痕（`code.py`+`run.json`：源文件 sha/起止/行列数）+ 子进程真超时 + `#工作表` 选择；新增 `explore_paper.py`（new 建骨架自动写 sha、check 拦「事实无依据/线索无下一步证据」）；`project-init` 建 `evidence/explore`+`evidence/reconcile`+`reconcile`；真实数据产物 `.gitignore` 阻挡，测试红/绿日志白名单归档。红 23→绿 34，全量 10 测试过，独立验收「通过」

- **舞弊线补强**（10-27，7 提交已 push）：推理指南 10→14 场景（定点/质量/物流/基建）+ 按图索骥 + 必查表 22 条（B-17 互吹）+ 校验 warn（`fraud_must_cover`）+ 红队洗白专杀 + 执行转案选项；待验收三笔用户明确先不验
- **存货试点四件**（11-01，新项目 `AU_PL_261101_存货`，只动新项目）：钩子A+C（只提醒）+ 白名单3条 + 三问基线（6暂定值）+ 出图 `make_chart.py`；接线已验证，待用户真用验收4条，跑顺回灌金源（ADR-048）
- **my-config 反写试点接线**（10-28，`899d994` + VERSION `2a12075` 已同步进存货项目，项目现为 2026-10-28-1）：方案 + 三 skill 反写规则（A 制度摘 / B 口说待验 / C 验过转正）；升级曾覆盖项目本地 `make_chart.py` 与 settings.json 钩子/白名单，已从 `.backup/20261028-112909` 恢复并验证；待存货真跑验收三条（ADR-049）
- **桌子v2.0**（ADR待补）：桌子从"复印件"改成"数据库"——账本（记结论，唯一原件）+ 底稿（记过程，自动生成）。技能直接写桌（add-line --room/--ref/--status），不再写本子再抄（sweep只留给老项目搬家用）。ingested抄写本子取消，每行自带来源标记。查询认桌子（老项目兼容）
- **检测力升级**（ADR-036，decec7a）：程序生成必过 **Step 4.6 红队攻击**——恶意内部人出攻击剧本→裁判三级判定→回灌修订→再攻≤2轮，原轨道B对抗验证(3.7)并入。debate 新增被审计人画像（情境驱动扮演）+ 实战援助（贴真实被审方原话→判回避/矛盾/转移话题+追问草稿）
- **CI自动测试**（2026-10-07；2026-10-22 起 10 个测试）：GitHub Actions 每次提交跑测试 + JSON 校验
- **关双轨第一步**（ADR-037，`94b8f1f`）：查询只认桌子（单项目/跨项目/汇总/来龙去脉卡），结论只上桌不再落盘（index 停写），`validate-index.py` 删除（校验脚本 8→7），4 份 SKILL 并到写桌子（执行/报告/吵架/问话），上桌后门卫查硬度接终检。历史对比不管老项目。B1 事前红测试红转绿；R09 待新项目真人验证
- **写入口收权第二步**（ADR-038，`0a3f60d`）：add-evidence 加 `--grade` + 红格无 A/E exit 2 拒收（只拦新增/一律拒收/删文件回退）+ 门卫改读桌子（两档不变）+ B2 红转绿（7红→13绿）；R09 待新项目真人验证
- **下一步命令第三步**（ADR-039，`490f124`）：phase_gate 加 `next` 人话看板（能干/还缺/工具一次给全，只报不拦，与 check/status 共存）+ B3 红转绿；三步走完，完整重设计未开工
- **任务板第一步**（ADR-040）：桌子加 tasks(1.3)+add-task/close-task 写入口+门卫待查提醒+编程序 2.4/执行结任务+B4 事前红转绿；程序推演无户口新假设先落任务板，查实转事实行
- **程序视图化**（ADR-041）：validate-program 加--workspace跑账上对账（孤儿block）+编程序先读账再写做法/增量改走任务板+B5 事前红转绿
- **回退消失**（ADR-042）：两道rollback改拒收指引+宪法#8#9改道留痕+四处文档同步+B6事前红转绿；拍照保留待A5换历史表
- **快照换历史表**（ADR-043）：落盘追流水+原子改名+拍照函数删除旧目录保留+宪法#8改字+B7事前红转绿
- **答卷收尾+收料删除**（ADR-044）：--json答卷行+B8事前红+sweep/import删除+旧测试迁移
- **勾稽口径卡 v1.0**（ADR-045，`8d8cde4`）：relations.json（只认 detail_to_total）+ validate-relations 三硬停两道门 + 词典/模板；口径卡放项目 reconcile/（升级不覆盖）
- **画像器 v1.0**（ADR-045，`bb2c3fe`）：profile_table.py 分块扫描产定长画像（20 万行 8.6s）；`bb2c3fe` 已 push GitHub（用户拍板覆盖不推旧决定）
- **未上现场**：以上成果均未部署到两个现场项目（见「当前最大风险」）

> 更早的批次（坑2 第一批 / 新桌子 ledger / 架构加固 C1-C7 / 四轮整改）见 `decisions.md` 的 ADR 与 `context.md`——本文件只写"现在是什么样"。

## 已完成功能
- 12 个 skill + 2 evaluators + 8 个校验脚本（validate-finding/program/report/policy-analysis/interview/json/catalog/relations）+ 辅助脚本（data_executor/data_health_check/profile_table/explore_paper/audit_gate/check_mandatory_coverage + compare-snapshots）
- 四重闸机体系（流程 / 质量 / 授权 / 调度）
- ProgramIR 解析器——审计程序 MD → 结构化 IR
- 审计程序模板含「设计理由」「测试目的」两列（6 轨道 + 增量章节）
- 证据 v2.0 集中存储（`_evidence_catalog.json` + `_files/`）
- PaddleOCR 引擎（中文识别率 75-85%）
- 一键部署 / 增量升级（setup-project.ps1 + update-project.ps1）
- 跨项目查询（projects-index.json + queries.py）
- Prompt 版本管理（tests/prompt_snapshots/ 5 个关键快照）
- 新桌子 ledger（8 文件 + 五家接读写 + 部署链同步 + 闸机 checklist 命令）
- **桌子 v2.0 账本+底稿两层**（schema_v2.json：直接写桌带来源标记，ingested取消）
- **CI 自动测试**（GitHub Actions：10 个测试 + JSON 校验）

## 系统结构
- 核心仓库: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 工具脚本: `_shared/scripts/`（phase_gate, validate-* ×8, queries, data_executor, data_health_check, profile_table, explore_paper, audit_gate, check_mandatory_coverage, project_init, program_ir_parser, evidence_catalog, bump-version）
- 部署脚本: `setup-project.ps1` + `update-project.ps1`
- 项目版 CLAUDE: `CLAUDE-project.md`
- 操作手册: `OPS.md`
- 项目注册表: `audit-topics/projects-index.json`（2 个项目已注册）
- 架构加固产物: `DATAFLOW.md`、`INPUT-BUDGET.md`、`REASON-LOG.md`、`tools/tool-exhaustion.md`、`tests/prompt_snapshots/regression-check.py` + `pre-commit.hook`、`tests/fixtures/regression/`
- 规则体系（2026-09-11 起；2026-10 起源库搬到 `12_AGI\claude\`）: 唯一来源 `D:\Nut\00_my_digital\12_AGI\claude\rules\`，经 `~/.claude/rules` 符号链接对所有项目生效；**项目级不再保存副本**，改源即全局生效

## 已部署项目
- P-2026-001: 武汉长源 人力资源管理 phase_3 —— **已结束（2026-10-22 用户确认）**
- P-2026-002: 广东长华 人力资源管理 phase_2 —— **已结束（2026-10-22 用户确认）**
- AU_TEST_基建工程：测试项目，**已升级 2026-10-22-1**（2026-10-22，备份 `.backup\20261022-160502`）

## 当前最大风险
- 🟡 **R09 载体待定**——原双项目（武汉长源/广东长华）已结束；建议在 AU_TEST_基建工程（先升 10-22-1）或新项目跑，待用户确认
- 🔴 **N8 调查方法合规分级未做**——`fraud_investigation_methods` 含"小黑屋 / 威胁施压"内容，涉及用户个人合规风险。用户搁置，建议尽早
- 🔴 **坑2 漏洞2/3 主体未做**——程序覆盖率分母改上游独立清单、证据等级系统打章；前置依赖未满足（上游 schema 未统一、design-assessments 全库零实例）

## 下一步
1. **R09 人工抽查**：原双项目已结束，载体待定（建议 AU_TEST_基建工程先升 10-22-1，或新项目）；清单见 `tests/prompt_snapshots/test_prompt_regression.md`，含本次 `project-init/B3` 改动；commit 标注 `已人工回归: [项目] [评级]`。
2. **决策 N8 合规分级**（个人合规风险，建议优先）。
3. **勾稽执行器 + 口径卡两类**（`row_formula`/`cross_table`）：用户 2026-10-22 明确搁置，等想好再开。
4. 文档/技术债收尾：两个超 300 行脚本拆分评估；`CLAUDE-project.md` 已补 `explore_paper.py`；设计稿 §10 已同步。

> 2026-10-22 用户确认：武汉长源、广东长华两个老项目已结束，部署欠账关闭；`update-project.ps1` 仅在有新现场项目时再跑。
