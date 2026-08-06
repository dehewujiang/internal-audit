# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态（2026-08-06）
🟢 8-06 完成四轮整改闭环（version 2026-08-06-1/2/3/4，均已部署双项目）：
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

## 已部署项目
- P-2026-001: 武汉长源 人力资源管理 phase_3
- P-2026-002: 广东长华 人力资源管理 phase_2

## 当前最大风险
- 🔴 N8 调查方法合规分级未做（fraud_investigation_methods 含"小黑屋/威胁施压"内容，涉及用户个人合规风险）——用户搁置，建议尽早
- 🟡 R09 实际抽查未做（清单已交付，用户手工执行）
- 🟡 广东长华程序 v1.0→v3.0 升级搁置（缺"取证方式"列无法生成 catalog）

## 下一步
1. 用户执行 R09 人工抽查（清单见 tests/prompt_snapshots/test_prompt_regression.md，commit 标注 `已人工回归: [项目] [评级]`）
2. 跑一次真实审计验证新闸机行为（Step 0.4 配置追问 / Step 0.5 增量分流 / Step 4.5 程序拦截 + 两列生成）
3. 决策 N8 合规分级、广东长华升级、B1.1/L1.1 迁移
4. 重启 opencode 使部署项目新 SKILL.md 生效
