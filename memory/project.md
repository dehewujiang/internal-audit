# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态
✅ **三重闸机体系就绪（2026-07-10）**。流程闸机（phase_gate check/advance）、质量闸机（validate --strict）、授权闸机（tool-check）三层覆盖。setup-project.ps1 一键部署到审计项目。

## 已完成功能
- 8 个 skill + evaluator + program-quality-evaluator，全可独立运作
- **流程闸机**: phase_gate 6 阶段流转 + 7 检查条件 + prompt_program_update
- **质量闸机**: 5 个 validate 脚本 + --strict 写入前阻断
- **授权闸机（2026-07-10）**: phase_gate tool-check + 三级白名单（PHASE_TOOLS/GLOBAL_TOOLS/EVALUATOR_TOOLS），exit 1 硬阻断 + --force 逃生门
- **双重身份协议（2026-07-10）**: CLAUDE.md Workflow discipline 新增 Dual-role thinking 拦截，审计业务问题必须先走审计总监视角
- project_init.py: 覆盖检测 + 配置检测
- program-generator: 增量更新模式
- queries.py: 独立查询工具（findings/trend/compare/summary/search/analyses/trace）
- **setup-project.ps1 重写（2026-07-10）**: 三 junction（skills/_shared_/tools_）+ 拷贝 CLAUDE-project.md + mkdir 三个数据目录 + 末尾自检
- **CLAUDE-project.md（2026-07-10）**: 审计项目专用精简版 CLAUDE.md，砍掉开发专用四节（rules junction、architecture gotchas、key files、what this repo is）
- **缺口补齐（2026-07-10）**: interview-designer Step 5.0 validate 调用、finding-debate Step 5 辩论充分性自检

## 正在开发
- 🟡 部署流程优化：开发环境→运行环境快速切换方案讨论中

## 已知缺口（非阻塞）
| 缺口 | 说明 |
|------|------|
| finding-debate 缺 evaluator 引用 | 已有 Step 5 自检，但辩论产物是 finding 字段追加非独立文件，不适用 validate 脚本 |

## 最大风险
🟢 无阻塞级风险。三门闸机 + 双重身份协议构成了多层防御。

## 下一步
1. 完成部署流程优化（开发→运行切换方案）
2. 跑一次端到端测试验证全链路
3. 决策追溯体系（跨阶段证据日志）

## 系统结构
- 核心仓库：`D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 规则来源：`.claude/rules/` → junction → `D:\Nut\00_my_digital\12_AGI\rules\`
- 工具脚本：`_shared/scripts/`（phase_gate, validate-*, queries, project_init）
- 部署脚本：`setup-project.ps1` — 一键初始化审计项目骨架
- 项目版 CLAUDE：`CLAUDE-project.md` — 审计项目拷贝此文件

## 相关决策
见 decisions.md
