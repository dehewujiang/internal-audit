# TODO

## 进行中
- 坑2 整改第一批完成（2026-09-10，VERSION 2026-09-10-1，**在 worktree 分支，待合并回 master**）

## 待办（风险整改 — 已全部闭环 2026-08-06，详见下方已完成章节）

## 待办（其他）
- 📌 新桌子部署到双项目（VERSION 2026-09-04-5，用户按 update-project.ps1 执行；广东长华/武汉长华 VERSION.lock 仍老版）
- 📌 R09 人工抽查：4 次 SKILL 改动（报告 Step 2b/执行写桌子/问话/看制度/吵架）的钩子欠账，用户手工完整跑一遍报告后 commit 标注 `已人工回归: [项目] [评级]`
- 📌 拆小桌（worktree new-table，尘埃落定后；删前确认分支已并回）
- 📌 增量制度分析脚本（analysis_manifest.py + incremental_analysis_gate.py）已入库未接入（2026-08-12 确认：全库 0 引用、document-organizer 全量分析、CLAUDE-project 工具清单未提）。判定：设计超前、需求未触发（制度偶尔更新）→ 保留不删，待未来制度更新频繁时接线。记录见 `_shared/scripts/README.md`
- 📌 create_evidence_dirs.py 重构候选（2026-08-12 纳米测试三问发现）：名为建目录、实为 457 行解析器（97% 代码在生成证据清单）；3 处死代码（safe_dirname / 风险名称提取 / programs 参数，v2.1 取消程序目录后遗留）；与 evidence_catalog.py 职责重叠。功能在用（program-generator Step 4），不紧急 → 下次动 evidence 时重构（解析逻辑并入 evidence_catalog 或改名 + 删死代码）
- 🔴 坑2 整改（验证优先/防自证）：
  - ✅ 第一批（2026-09-10，VERSION 2026-09-10-1）：三把小刀 + 漏洞1——覆盖率漏表修复（program_ir_parser.py 删 break，分母 10→34）/ E 级证据定义矛盾修正（finding_rules.md L53）/ 报告可靠性上限声明（report-generator 模板 + SKILL 5.5）/ 漏洞1 原文抽查（validate-policy-analysis.py 独立通道 + tests/test_source_reconciliation.py 专项测试）。决策见 ADR-029
  - ⬜ 第二批：漏洞2 主体（覆盖率分母改上游独立清单）——前置依赖未满足：须先统一上游输出 schema（json-schema.md 声明与真实产物漂移）+ 积累 design-assessments 实例（全库零实例）
  - ⬜ 第三批：漏洞3 主体（证据等级系统盖章——data_executor 导出自动 A、OCR 自动 C+待确认、AI 只能标 E 并附来源）
  - 🔴 **新增**：audit_gate 退出码缺陷——只看退出码是否为 0，不区分 warn(1)/block(2)，导致"只提示不阻断"的设计全部失效（ADR-030 记录，本次以独立通道绕开）。建议单独排期修
  - ⬜ 附带发现：`validate-policy-analysis.py` 的 `check_control_points_traceability` 查的字段列表（source_section/source_doc/source_clause/原文出处）**不含真实产出最常用的 `source` 字段**，会对真实数据误报"缺少原文出处"。下次动该脚本时一并修
- 处理未提交改动（2026-08-12）：coding-safety.md 分级验证改动提交确认、.omo/.workbuddy 运行痕迹收进 .gitignore、data/evaluations/2026-05-12.jsonl 删除确认
- 部署架构加固成果到双项目（VERSION.lock 08-06-4 → 08-11-3，用户按 update-project.ps1 执行）
- C6 推理日志全量铺开：试点已完成，跑 1 个真实审计项目后评估（见 REASON-LOG.md）
- P-2026-002 广东长华程序从 v1.0 升级到 v3.0（缺少"取证方式"列，无法自动生成 catalog）— 用户搁置
- [可选] B1.1/L1.1 目录 60 个证据文件是否迁入 `_files/` 及同步更新 finding 引用路径（`findings/B1.1_考勤数据手工传递篡改_待核实异常.json` 的 evidence.files 硬编码引用）— 待用户决策
- R09 实际抽查：用户手工执行，commit 标注 `已人工回归: [项目] [GREEN/YELLOW/RED]`（清单见 tests/prompt_snapshots/test_prompt_regression.md）
- 部署后做一次完整证据匹配流程端到端测试 — 武汉长源已完成（2026-08-04，162 槽位闭环跑通）；广东长华待程序升级后做
- `data/evaluations/2026-07-17.jsonl`：删除旧快照前差异扫描发现的独有文件，拟并入源仓库但当前 `data/evaluations/` 目录为空，需确认是否已并入并提交
- 重启 opencode 使新配置生效（部署项目 SKILL.md 下次使用时生效）

## 搁置
- 🟢 模型分级（便宜模型 vs 强模型按需使用）— 单人使用 token 成本可控
- 🔵 每个 skill 返回结构化摘要 — ROI 极低
- 🔴 N8 调查方法合规分级（fraud_investigation_methods 小黑屋/威胁施压内容）— 用户搁置，涉及个人合规风险，建议尽早处理
- 🔵 统计抽样方法 reference — 用户搁置

## 阻塞
- 无

## 已完成（2026-09-04）
- ✅ 新桌子 ledger 架构：ledger/ 8 文件（管家/门卫/打勾纸/报告闸机/总览表格/格式/说明/冲压例子）+ 五家房间接读写（检查单房约定即接口未动）+ 四根线（写/读/拍照20张/老账）+ 硬度（高风险须A/E）+ 闸机 checklist 命令（旧锁零动）+ 部署链同步（setup/update/白名单/注册/打版 2026-09-04-5）+ 推远程（master 与 origin 一致）
- ✅ 真数验证：广东长华 11 张整搬门卫放行；F-004 上桌全程；撕一添鬼拦下；旧回归 2 绿 0 红、快照过；新建/升级两条部署路走通
- ✅ 图纸 `新桌子设计稿_2026-09-04.md` + 进度 `新桌子进度.md` + 试搭 `新桌子试搭/`（根下，未存档）
- ✅ 规则拆分：coding-safety（编码专用 paths）+ work-principles（通用全量，含验证分层 L1/L2/L3）；三处副本同步 + 两仓库提交
- ✅ 坑2 诊断：四重闸机核查出 4 漏洞并记档（程序覆盖率自证/证据等级自标/制度校验看转述/报告二手）
- ✅ 纳米测试三问：25 脚本审查（2 孤儿保留待接线 + 1 偏重重构候选 + 20 核心通过）
- ✅ 8-11 架构加固收工记忆补写 + 未提交改动处理（coding-safety/omo/workbuddy/data-evaluations）

## 已完成（2026-08-11）
- ✅ 架构加固计划 C1-C7 全部闭环（VERSION 2026-08-11-3，金源已提交）：C1 DATAFLOW.md / C2 宪法瘦身+漂移修复 / C3 纳米测试（ADR-026）/ C4 R09 回归用例（p2026-001-hr 脱敏，findings 待补）/ C5 闸机边界验证 / C6 推理日志试点（log-decision 命令 + decision_rationale.risk_level_reason）/ C7 INPUT-BUDGET + SKILL 读取裁剪
- ✅ SKILL.md 变更自动检测与回归机制（regression-check.py + pre-commit hook 影响卡片 + RED 拦截，b500675/4d21ef9）
- ✅ VERSION bump 2026-08-11-3（b6c6d3d 移除 validate-finding.py 死代码 import + bump）
- ⚠️ 8-11 收工记忆于 08-12 补写；无 feedback 教训记录，如执行中有教训待补充

## 已完成（2026-08-06）
- ✅ 全量坏路径修复（36 处/12 文件 → 三标准路径，ADR-023）+ 孤儿文档接入（dynamic_questions→Step 0.4、incremental_update→Step 0.5）+ output_template 补十/十一章（VERSION 2026-08-06-1，a8dd3d2/c4128d8，已部署）
- ✅ constitution 恢复 11-14 条 + 阶段流转规则 + 启动协议（20ad90b 误删回归，ADR-022）+ 证据标准统一 A+E（R01）+ consequence 必填（N5）+ 对抗阈值（R02）+ 混源过滤（N7）+ U8 清零（N14）（VERSION 2026-08-06-2，fa412dd/9ab8c13，已部署）
- ✅ 阶段二：Step 4.5 程序闸机+激活轨道校验（R04+R07+N15）+ validate-catalog.py（R05）+ validate-index.py（R06）+ 制度版本强制（N6）（VERSION 2026-08-06-3，fa143a4/7fd2c46，已部署）
- ✅ 阶段三：5 份快照重写（R03）+ compare-snapshots pre-commit hook（R08）+ 人工抽查清单（R09 交付物）（26c511d，不部署）
- ✅ CLAUDE.md/CLAUDE-project.md 工具清单登记 validate-catalog/validate-index + memory 收工更新
- ✅ 第四轮 add-design-columns（2026-08-06 下午）：审计程序新增「设计理由」「测试目的」两列（8 张表）+ 防套话约束 + 列宽；修复模板与 Step 4.5 闸机兼容矛盾（表头对齐真实结构，ADR-025）+ Step 4.5 命令 --ir 修正；VERSION 2026-08-06-4 已部署双项目，Final Wave PASS（0746f5c→cd72e98）

## 已完成（2026-08-05）
- ✅ SKILL.md 坏路径修复 + 重新部署（commit `0c8c97a`）
  - `audit-execution-assistant/SKILL.md` 4 处 `~/.claude/skills/internal-audit/...` 绝对路径改为项目本地相对路径（`_shared/scripts/validate-finding.py`、`internal-audit-evaluator/SKILL.md`）
  - bump VERSION.json `2026-08-04-1 → 2026-08-05-1`，commit `0c8c97a` `fix(skill): SKILL.md 路径修正`（2 文件）
  - 重新部署武汉长源 + 广东长华（VERSION.lock = 2026-08-05-1，SKILL.md 逐字节一致）
- ✅ `~/.claude/skills/internal-audit` 旧快照清理：2026-07-06 旧副本（非 junction）导致 13 个 tools/*.md 能力声明被 oh-my-openagent 误扫为 skill；已删除并保持删除状态
- ✅ feedback.md 追加 2026-08-05 教训（SKILL.md 禁止绝对路径硬规则）

## 已完成（2026-08-04）
- ✅ 证据 v2.0 集中存储工作流修复（计划：`.omo/plans/evidence-single-copy.md`）
  - 修 `audit-execution-assistant/SKILL.md` 证据路径矛盾（规则层 vs 界面示例层），统一为 `evidence/_files/`；catalog 检查改为 Step 1 默认动作
  - 修 `_shared/scripts/create_evidence_dirs.py`：取消按程序建 74 个空目录，只建 `_files/` + `_evidence_catalog.json`
  - bump VERSION.json `2026-07-26-3 → 2026-08-04-1`，commit `b4a0611` `fix(evidence): 证据 v2.0 集中存储工作流修复`（3 文件）
  - 部署到武汉长源 + 广东长华（`update-project.ps1`，VERSION.lock = 2026-08-04-1）
  - 端到端验证：武汉长源 162 槽位 catalog，scan→match→status→update 闭环跑通
  - 武汉长源现场清理：`_files.old`→`_files` 改名；删 70 个空程序目录；B1.1/L1.1（60 文件）按保护规则保留
  - 验证波 F1-F4 全部 APPROVE
- ✅ 检查 5 个已部署项目，武汉长源升级到最新版（2026-07-21-2）

## 已完成（2026-07-29）
- ✅ 风险整改方案核验：逐条对照源文件验证 9 项风险诊断准确性
- ✅ 风险整改方案优化：R04 修正（ProgramIR 方案替代 risks_identified.json）、R07 重写（三重屏障）、R08 补齐（有意变更 vs 无意漂移区分）、新增工作量预估和依赖关系图

## 已完成（2026-07-26）
- ✅ 证据集中存储与智能匹配架构设计 + 实现（4 脚本 + 2 文档）
- ✅ PaddleOCR 安装验证（核心识别率 90%+，20分钟/8页，不用于匹配阶段）
- ✅ 项目命名规则固化（project_name = 文件夹名）
- ✅ 证据 v2.0 部署到 P-2026-001 武汉长源 + P-2026-002 广东长华（用户手动完成）
- ✅ 8 次原子化 git 提交

## 已完成（2026-07-22）
- ✅ 四维度系统评估（35 项风险发现）
- ✅ 业务合规整改 12 项（社保标准/公积金/ITGC/派遣舞弊/my-config/OCR）
- ✅ 数据流转审查 27 项 → 22 项确认真实
- ✅ 数据流转整改 22 项（validate-finding 重写/audit_gate 参数/白名单/沙箱/mandatory 检查/schema 补齐/阶段编号/条款数）
- ✅ 2 个项目补登记到 projects-index.json
- ✅ 12 次原子化 git 提交

## 已完成（2026-07-14）
- ✅ 审计技能注册修复
- ✅ program_ir_parser.py MD→ProgramIR 解析器
- ✅ project-init Step 4.6 自动注册
