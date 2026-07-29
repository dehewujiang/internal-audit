# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态（2026-07-29）
🟡 系统架构评估完成，9 项风险整改方案（`风险整改方案_2026-07-29.md`）已核验优化，待执行。四重闸机体系运行正常。证据 v2.0 已部署到 2 个在审项目。

## 已完成功能
- 12 个 skill + 2 evaluators + 5 个校验脚本 + 3 个新脚本（data_executor/audit_gate/check_mandatory_coverage）
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
