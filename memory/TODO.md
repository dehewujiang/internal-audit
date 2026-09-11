# TODO

## 进行中
（无）

## 待办

### 🔴 高优先
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

## 已完成（2026-09-11）
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
