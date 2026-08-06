# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态（2026-08-06）
🟢 8-06 完成三轮整改闭环（version 2026-08-06-1/2/3，均已部署双项目）：
① 全量坏路径修复（36 处残留 → 三标准路径）+ 两个孤儿文档接入（dynamic_questions → Step 0.4 配置补齐、incremental_update → Step 0.5 模式分流）；
② constitution 恢复 11-14 条硬约束 + 阶段流转规则 + 启动协议（20ad90b 误删回归）+ 证据标准统一 A+E + 对抗验证阈值 + 知识库混源过滤 + U8 清零；
③ 阶段二（Step 4.5 程序结构化闸机 + 激活轨道校验 + validate-catalog/validate-index 双校验器 + 制度版本强制）+ 阶段三（5 份快照重写 + pre-commit 快照漂移 hook + 人工抽查清单）。
9 项风险整改（R01-R09）除 R09 实际抽查（用户手工执行）外全部闭环。四重闸机 + 快照 hook 运行正常。

## 已完成功能
- 12 个 skill + 2 evaluators + 8 个校验脚本（validate-finding/program/report/policy-analysis/interview/json + **validate-catalog/validate-index**）+ 4 个新脚本（data_executor/audit_gate/check_mandatory_coverage + compare-snapshots 开发工具）
- 四重闸机体系（流程/质量/授权/调度）
- ProgramIR 解析器（program_ir_parser.py）——审计程序 MD → 结构化 IR
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
- 快照过期（3/5 有实质漂移）→ 后续改动无法回归对比
- 对抗验证定量阈值丢失 → 轨道 B 判定退化
- 证据等级门槛矛盾（A+B vs A+E）→ 模型读到不同文件遵循不同标准

## 下一步
1. 用户确认优化后的整改方案
2. 启动阶段一：R01（统一证据门槛）→ R02（补阈值）→ R03（更新快照）
3. 阶段二：R04（ProgramIR 闸机接入工作流）→ R05/R06（补齐校验脚本）→ R07（覆盖修复闭环）
