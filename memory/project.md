# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态（2026-09-11）
系统功能完整（12 skill + 四重闸机 + 新桌子 ledger），近期在做**规则与记忆体系的瘦身**：

- **闸机三档**（ADR-031）：原先"有警告"和"有阻断"在闸机眼里一样、都拦——系统里没有"提醒你一下但放你过"这个档位。现在认三档，并给五个校验脚本加了防崩溃保护
- **规则去重**：项目级规则副本（22 份）全清，统一由 `~/.claude/rules/` 提供；`project-doctrine` 转为按需加载，常驻量 354→274 行
- **记忆瘦身**：`decisions.md` 清掉实施清单（449→372 行）；新立规矩——只写"为什么"，不写"改了什么"
- **未上现场**：以上成果均未部署到两个现场项目（见「当前最大风险」）

> 更早的批次（坑2 第一批 / 新桌子 ledger / 架构加固 C1-C7 / 四轮整改）见 `decisions.md` 的 ADR 与 `context.md`——本文件只写"现在是什么样"。

## 已完成功能
- 12 个 skill + 2 evaluators + 8 个校验脚本（validate-finding/program/report/policy-analysis/interview/json + validate-catalog/validate-index）+ 4 个辅助脚本（data_executor/audit_gate/check_mandatory_coverage + compare-snapshots）
- 四重闸机体系（流程 / 质量 / 授权 / 调度）
- ProgramIR 解析器——审计程序 MD → 结构化 IR
- 审计程序模板含「设计理由」「测试目的」两列（6 轨道 + 增量章节）
- 证据 v2.0 集中存储（`_evidence_catalog.json` + `_files/`）
- PaddleOCR 引擎（中文识别率 75-85%）
- 一键部署 / 增量升级（setup-project.ps1 + update-project.ps1）
- 跨项目查询（projects-index.json + queries.py）
- Prompt 版本管理（tests/prompt_snapshots/ 5 个关键快照）
- 新桌子 ledger（8 文件 + 五家接读写 + 部署链同步 + 闸机 checklist 命令）

## 系统结构
- 核心仓库: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 工具脚本: `_shared/scripts/`（phase_gate, validate-* ×5, queries, data_executor, audit_gate, check_mandatory_coverage, project_init, program_ir_parser, evidence_catalog, bump-version）
- 部署脚本: `setup-project.ps1` + `update-project.ps1`
- 项目版 CLAUDE: `CLAUDE-project.md`
- 操作手册: `OPS.md`
- 项目注册表: `audit-topics/projects-index.json`（2 个项目已注册）
- 架构加固产物: `DATAFLOW.md`、`INPUT-BUDGET.md`、`REASON-LOG.md`、`tools/tool-exhaustion.md`、`tests/prompt_snapshots/regression-check.py` + `pre-commit.hook`、`tests/fixtures/regression/`
- 规则体系（2026-09-11 起）: 唯一来源 `D:\Nut\00_my_digital\12_AGI\rules\`（8 份），经 `~/.claude/rules/agi` 符号链接对所有项目生效；**项目级不再保存副本**，改源即全局生效

## 已部署项目
- P-2026-001: 武汉长源 人力资源管理 phase_3
- P-2026-002: 广东长华 人力资源管理 phase_2

## 当前最大风险
- 🔴 **现场项目版本落后**——两个现场项目的 VERSION.lock 停在老版，新桌子 ledger（09-04-5）、架构加固（08-11-3）、闸机修复（09-10-2）均未上现场。待用户按 `update-project.ps1` 升级
- 🔴 **N8 调查方法合规分级未做**——`fraud_investigation_methods` 含"小黑屋 / 威胁施压"内容，涉及用户个人合规风险。用户搁置，建议尽早
- 🔴 **坑2 漏洞2/3 主体未做**——程序覆盖率分母改上游独立清单、证据等级系统打章；前置依赖未满足（上游 schema 未统一、design-assessments 全库零实例）
- 🟡 **R09 实际抽查未做**——清单已交付，用户手工执行
- 🟡 **广东长华程序 v1.0→v3.0 升级搁置**——缺"取证方式"列，无法生成 catalog

## 下一步
1. 按 `update-project.ps1` 把三个版本的建设成果部署到双项目
2. 用户执行 R09 人工抽查（清单见 `tests/prompt_snapshots/test_prompt_regression.md`，commit 标注 `已人工回归: [项目] [评级]`）
3. 决策 N8 合规分级（个人合规风险，建议优先）
4. 坑2 漏洞2 主体之前，先做上游 schema 统一
