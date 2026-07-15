# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态
✅ **三重闸机体系就绪（2026-07-10）**。流程闸机（phase_gate check/advance）、质量闸机（validate --strict）、授权闸机（tool-check）三层覆盖。setup-project.ps1 一键部署到审计项目。

## 已完成功能
- 12 个 skill + evaluator + program-quality-evaluator，全可独立运作
- **流程闸机**: phase_gate 6 阶段流转 + 7 检查条件 + prompt_program_update
- **质量闸机**: 5 个 validate 脚本 + --strict 写入前阻断
- **授权闸机（2026-07-10）**: phase_gate tool-check + 三级白名单（PHASE_TOOLS/GLOBAL_TOOLS/EVALUATOR_TOOLS），exit 1 硬阻断 + --force 逃生门
- **双重身份协议（2026-07-10）**: CLAUDE.md Workflow discipline 新增 Dual-role thinking 拦截
- **部署优化（2026-07-10）**: VERSION.json + setup-project.ps1 --stable 模式 + VERSION.lock.json + update-project.ps1 增量升级
- **决策追溯（2026-07-10）**: decisions_schema.py（9 个决策点）+ 4 个 SKILL.md decision_log + 4 个 validate 决策检查 + queries.py decide
- **跨项目查询（2026-07-10）**: projects-index.json 注册表 + queries.py register + --cross-project（findings/summary/search/compare）
- **操作手册（2026-07-10）**: OPS.md 纯中文操作说明
- project_init.py: 覆盖检测 + 配置检测
- program-generator: 增量更新模式
- queries.py: 独立查询工具（795 行，DataSource 抽象层消除单项目/跨项目分支，+ 536 行 query_data_sources.py）
- **setup-project.ps1 重写（2026-07-10）**: 三 junction（skills/_shared_/tools_）+ 拷贝 CLAUDE-project.md + mkdir 三个数据目录 + 末尾自检 + --stable 模式 + 部署提示 register
- **CLAUDE-project.md（2026-07-10）**: 审计项目专用精简版 CLAUDE.md
- **文档完整性改进（2026-07-13）**: CLAUDE.md + CLAUDE-project.md 新增技能阶段映射表、脚本速查表、部署架构说明、Architecture gotchas，两份文件 12 章节完全对齐
- **审计程序追溯链（2026-07-13）**: program_index.json 伴生文件 + queries.py trace 三向追溯（finding/步骤/控制点双向链接）
- **缺口补齐（2026-07-10）**: interview-designer Step 5.0 validate 调用、finding-debate Step 5 辩论充分性自检
- **P0-1 程序 JSON 化（2026-07-14）**: `program_ir_parser.py`（MD→ProgramIR 确定性解析器）+ `validate-program.py --ir`（覆盖度/判定标准量化/数据来源比例三项 block）。AI 仍输出 MD，Flan 工作流零改动。ProgramIR 是 program_index.json 超集（schema 2.0.0，steps[] 兼容），替代 LLM 手写 JSON。闭环/工具/mandatory实质/查证有效性仍留 LLM。

## 正在开发
- 无

## 已知缺口（非阻塞）
| 缺口 | 说明 |
|------|------|
| 无 | — |

## 最近修复（2026-07-14）
**技能注册缺陷**：源仓库 `.claude/skills/` 只有 2 个 geb-* 技能，10 个审计技能在根目录未注册。`update-project.ps1` 的 stable 模式整目录覆盖导致部署项目技能被清空。
- **修复1**：`.claude/skills/` 下创建 10 个目录 junction 指向根目录技能
- **修复2**：`setup-project.ps1` 改为扫描 `.claude/skills/` 自动发现技能（消除硬编码列表）
- **修复3**：`update-project.ps1` stable 模式改为逐技能合并（不是整目录覆盖）
- **修复4**：补充 `.claude/settings.json` 和 `.claude/rules/` 部署

## 最大风险
🟢 无阻塞级风险。五层防御（三重闸机 + 决策追溯 + 跨项目可观测性）。

## 系统结构
- 核心仓库：`D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 规则来源：`.claude/rules/` → junction → `D:\Nut\00_my_digital\12_AGI\rules\`
- 工具脚本：`_shared/scripts/`（phase_gate, validate-* ×5, decisions_schema, queries, project_init）
- 部署脚本：`setup-project.ps1` + `update-project.ps1` — 部署 + 增量升级
- 项目版 CLAUDE：`CLAUDE-project.md` — 审计项目拷贝此文件
- 操作手册：`OPS.md` — 面向审计师的操作说明书
- 项目注册表：`audit-topics/projects-index.json` — 跨项目查询的数据索引

## 下一步
1. 实际审计项目中使用，积累实战反馈
2. 如有需要：project-init 自动注册到 projects-index.json