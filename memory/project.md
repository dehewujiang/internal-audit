# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态（2026-08-11）
🟢 8-11 完成架构加固计划（C1-C7 + F波验证，VERSION 2026-08-11-3）：
- C1 数据流总图（DATAFLOW.md，六阶段全链路 + 断点观察）
- C2 宪法瘦身（constitution.md ≤85 行，14 条语义零丢失 + 触发指针；CLAUDE-project.md 漂移 bug 修复）
- C3 纳米测试原则（ADR-026 + OPS 新增规则/脚本前检查清单）
- C4 R09 标准用例积累（tests/fixtures/regression/ p2026-001-hr P1→P2 回归对，脱敏）
- C5 闸机边界验证（phase_gate/audit_gate 职责无重叠、无死角）
- C6 审计推理日志试点（phase_gate.py 新增 log-decision 子命令 + finding 新增 decision_rationale.risk_level_reason，REASON-LOG.md 设计定稿）
- C7 最小必要上下文（INPUT-BUDGET.md + SKILL.md 读取指令静态裁剪，design-assessments 用验证状态过滤）
- 追加：SKILL.md 变更自动检测与回归机制（tests/prompt_snapshots/regression-check.py + pre-commit hook 影响卡片 + RED 拦截）

8-06 历史：完成四轮整改闭环（version 2026-08-06-1/2/3/4，均已部署双项目）：
① 全量坏路径修复（36 处残留 → 三标准路径）+ 两个孤儿文档接入（dynamic_questions → Step 0.4 配置补齐、incremental_update → Step 0.5 模式分流）；
② constitution 恢复 11-14 条硬约束 + 阶段流转规则 + 启动协议（20ad90b 误删回归）+ 证据标准统一 A+E + 对抗验证阈值 + 知识库混源过滤 + U8 清零；
③ 阶段二（Step 4.5 程序结构化闸机 + 激活轨道校验 + validate-catalog/validate-index 双校验器 + 制度版本强制）+ 阶段三（5 份快照重写 + pre-commit 快照漂移 hook + 人工抽查清单）；
④ 第四轮（VERSION 2026-08-06-4）：审计程序新增「设计理由」「测试目的」两列（8 张表），执行中发现并修复存量矛盾——模板表头缺「程序编号/判定标准/取证方式」导致 Step 4.5 闸机必然拦截，已按 fixture v1.1 真实结构对齐；Step 4.5 命令 `--ir` 布尔开关修正（commits 0746f5c→cd72e98）。
9 项风险整改（R01-R09）除 R09 实际抽查（用户手工执行）外全部闭环。四重闸机 + 快照 hook 运行正常。

## 已完成功能
- 12 个 skill + 2 evaluators + 8 个校验脚本（validate-finding/program/report/policy-analysis/interview/json + **validate-catalog/validate-index**）+ 4 个新脚本（data_executor/audit_gate/check_mandatory_coverage + compare-snapshots 开发工具）
- 四重闸机体系（流程/质量/授权/调度）
- ProgramIR 解析器（program_ir_parser.py）——审计程序 MD → 结构化 IR
- 审计程序模板含「设计理由」「测试目的」两列（6 轨道 + 增量章节，2026-08-06-4）
- 证据 v2.0 集中存储（_evidence_catalog.json + _files/）
- PaddleOCR 引擎（中文识别率 75-85%）
- 一键部署/增量升级（setup-project.ps1 + update-project.ps1）
- 跨项目查询（projects-index.json + queries.py）
- Prompt 版本管理（tests/prompt_snapshots/ 5 个关键快照）

## 系统结构
- 核心仓库: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 工具脚本: `_shared/scripts/`（phase_gate, validate-* ×5, queries, data_executor, audit_gate, check_mandatory_coverage, project_init, program_ir_parser, evidence_catalog, bump-version）
- 部署脚本: `setup-project.ps1` + `update-project.ps1`
- 项目版 CLAUDE: `CLAUDE-project.md`
- 操作手册: `OPS.md`
- 项目注册表: `audit-topics/projects-index.json`（2 个项目已注册）
- 架构加固产物: `DATAFLOW.md`（数据流总图）、`INPUT-BUDGET.md`（上下文裁剪规则）、`REASON-LOG.md`（推理日志设计）、`tools/tool-exhaustion.md`（工具穷举规范）、`tests/prompt_snapshots/regression-check.py` + `pre-commit.hook`（SKILL 变更检测）、`tests/fixtures/regression/`（R09 回归用例）

## 已部署项目
- P-2026-001: 武汉长源 人力资源管理 phase_3
- P-2026-002: 广东长华 人力资源管理 phase_2

## 当前最大风险
- 🔴 N8 调查方法合规分级未做（fraud_investigation_methods 含"小黑屋/威胁施压"内容，涉及用户个人合规风险）——用户搁置，建议尽早
- 🔴 部署项目 VERSION.lock 停在 08-06-4——架构加固成果（宪法瘦身/推理日志/上下文裁剪）未上现场，待用户按升级流程部署
- 🟡 R09 实际抽查未做（清单已交付，用户手工执行）
- 🟡 未提交改动散落：coding-safety.md 分级验证改动未提交、.omo/.workbuddy 运行痕迹未收纳 gitignore、data/evaluations/2026-05-12.jsonl 删除未确认
- 🟡 广东长华程序 v1.0→v3.0 升级搁置（缺"取证方式"列无法生成 catalog）

## 下一步
1. 处理未提交改动（coding-safety.md 分级验证提交、.omo/.workbuddy 收进 .gitignore、data/evaluations 删除确认）— 2026-08-12 待办
2. 用户按升级流程部署加固成果到双项目（VERSION.lock 08-06-4 → 08-11-3）
3. 用户执行 R09 人工抽查（清单见 tests/prompt_snapshots/test_prompt_regression.md，commit 标注 `已人工回归: [项目] [评级]`）
4. C6 推理日志试点评估（跑 1 个真实审计后决定全量铺开）
5. 决策 N8 合规分级（个人合规风险，建议优先）
