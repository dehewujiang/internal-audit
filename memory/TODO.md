# TODO

## 进行中
- 无

## 待办（风险整改 — 已全部闭环 2026-08-06，详见下方已完成章节）

## 待办（其他）
- 🔴 坑2 整改（验证优先/防自证，2026-08-12 诊断完成、待排期实施）：
  - 漏洞2（最危险）：validate-program.py --ir 覆盖率分母改为上游独立风险清单（design-assessments + policy-analyses），防"程序自己列风险又自证覆盖"
  - 漏洞3：证据 reliability_grade 改为系统打章——data_executor 导出自动 A、OCR 自动 C+待确认、AI 只能标 E（第三方）并附来源
  - 漏洞1：validate-policy-analysis 抽查原始制度文本与提取 JSON 的对应（关键条款数一致），不只看 AI 转述
  - 漏洞4：报告不根治，记录"报告可靠性上限 = 前四环节最弱一环"
  - 实施前先出规划模型供审核；对应新增 ADR
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
