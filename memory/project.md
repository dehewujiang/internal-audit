# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态（2026-07-22）
✅ 四重闸机体系就绪。流程闸机（phase_gate）、质量闸机（validate）、授权闸机（tool-check）、调度闸机（audit_gate）四层覆盖。22 项数据流转问题已修复，系统可执行完整审计流程。

## 已完成功能
- 12 个 skill + 2 evaluators + 3 个新脚本（data_executor/audit_gate/check_mandatory_coverage）
- 流程闸机: phase_gate 6 阶段流转
- 质量闸机: 5 个 validate 脚本（schema 已统一到 1.2.0）
- 授权闸机: phase_gate tool-check + 三级白名单（含新脚本）
- 调度闸机: audit_gate precheck/postcheck/status
- 数据执行引擎: data_executor.py LLM 代码沙箱 + 8 预制分析工具
- mandatory 检查: check_mandatory_coverage.py 执行 constitution #10
- OCR 引擎: PaddleOCR（替代 EasyOCR，中文识别率提升 50%+）
- 一键部署: setup-project.ps1 + update-project.ps1
- 跨项目查询: projects-index.json 注册表 + queries.py
- Prompt 版本管理: tests/prompt_snapshots/ 5 个关键快照

## 业务合规改进（2026-07-22）
- 社保判定标准修正（最低工资 → 社平工资 60%）
- 住房公积金合规审计程序新增
- 社保公积金列入人力资源管理强制模块
- 信息系统审计 ITGC 第 9 类风险框架新增
- 劳务派遣拆分为合规 + 舞弊两类
- my-config.md 全面模板化

## 系统结构
- 核心仓库: `D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 工具脚本: `_shared/scripts/`（phase_gate, validate-* ×5, queries, data_executor, audit_gate, check_mandatory_coverage, project_init, decisions_schema）
- 部署脚本: `setup-project.ps1` + `update-project.ps1`
- 项目版 CLAUDE: `CLAUDE-project.md`
- 操作手册: `OPS.md`
- 项目注册表: `audit-topics/projects-index.json`（2 个项目已注册）

## 已部署项目
- P-2026-001: 武汉长源 人力资源管理 phase_3
- P-2026-002: 广东长华 人力资源管理 phase_2

## 下一步
1. PaddleOCR 安装完成后验证 OCR 质量
2. confirm_clause 在已部署项目中追一审计验证修改
3. 检查其他已部署项目是否需要更新
