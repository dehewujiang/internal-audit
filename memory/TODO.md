# TODO

## #进行中
- 无

## #待办
- validate-program.py 可选增加对 program_index.json 的校验（非阻塞，等实战反馈）

## #已完成（2026-07-13）
- ✅ project-init 自动注册到 projects-index.json：SKILL.md 新增 Step 4.6，项目创建完成后自动调用 `queries.py register`。注册失败不阻断创建流程，仅警告提示。关闭了"跨项目索引需手工注册"的非阻塞缺口。

## #搁置
- 🟢 P2：模型分级——制度分析用便宜模型，辩论用强模型。已搁置（2026-07-07）：当前架构下 Skill 工具不支持 model 参数，且单人使用 token 成本可控。待以下条件满足后重新评估：(1) 多人协作上线，成本上升；(2) Claude Code 支持 skill 级 model 覆盖。
- 🔵 P3：每个 skill 返回结构化摘要给 LLM 做下一步决策。已搁置（2026-07-07）：单人使用每次省 30 秒翻文件，ROI 极低。待团队化或高频使用（>5 项目/天）后重新评估。

## #阻塞
- 无

## #已完成（2026-07-08）
- 🔴 P0+P1：控制流闸机加固（audit-control-flow-hardening），16 项改动，6 次提交
  - 闸机检查升级：新增 7 个检查条件（审计目的、公司背景、访谈线索、举报、报告类型等），加了"建议处理"级别的提醒
  - 质检脚本加硬拦截：5 个检查脚本加 --strict 模式，查出问题直接喊停
  - 项目创建加安全检查：建项目前先扫一遍有没有旧项目、有没有配置，有问题直接退出
  - 审计程序加"补丁"模式：访谈做完后可以给程序打补丁，不推翻初稿
  - 操作说明书加强：3 个文档加"这段不准跳过"的强制标注
  - 证据目录补漏：project-init 忘了建证据存放目录，已补上

## #已完成（2026-07-10）
- ✅ 工具分时段硬拦截：phase_gate.py 新增 `tool-check` 子命令 + PHASE_TOOLS/GLOBAL_TOOLS/EVALUATOR_TOOLS 三级白名单，CLAUDE.md 补工具域表，constitution.md 更新引用。exit 1 硬阻断 + --force 逃生门。
- ✅ 部署优化（开发→运行快速切换）：VERSION.json 黄金源版本清单 + setup-project.ps1 --stable 模式 + VERSION.lock.json 版本锁定 + update-project.ps1 增量升级
- ✅ 决策追溯体系：decisions_schema.py（9 个决策点）+ 6 个 SKILL.md 输出格式补 decision_log + 4 个 validate 脚本补决策理由检查 + queries.py decide 子命令
- ✅ OPS.md：用户操作手册初版（面向审计师 Flan，纯中文）
- ✅ 跨项目数据参考：projects-index.json 项目注册表 + queries.py register/list/remove + findings/summary/search/compare --cross-project

## #已完成（2026-07-09）
- ✅ document-organizer 跨段落隐含控制：已实施两遍法（业务对象索引→逐对象分析），industry_benchmarks.md 已全面重写为可执行控制维度清单（15域，52处控制类型标签）。

## #已完成（2026-07-07）
- 🔴 P0-1：加轻量阶段状态机（phase_gate.py）
- 🔴 P0-2：硬规则代码化（validate-program.py, validate-policy-analysis.py, validate-report.py）
- 🟡 P1-1：按 phase 分域暴露 skill（CLAUDE.md + constitution.md 更新）
- 🔴 queries.py 重构：从 evaluator 搬到 _shared/scripts/，升格为独立查询工具
- 🔴 program-quality-evaluator 新增：四层评估体系
- 🟡 P1-2：建 5 个 eval cases + run_evals.py
- 🔴 启动协议：constitution.md 新增启动协议节
- 更新各 SKILL.md Step 5 引用新的 validate 脚本和 program-quality-evaluator
- 更新 report-generator SKILL.md 删除「功能1：管理审计发现」
- 🟢 P2：为关键决策点（风险评级、finding 定级）加决策理由记录（decision_rationale）
- 🟡 P2：queries.py 全文搜索 finding 正文（search 子命令，递归搜索所有 JSON 字段）
- 🟢 P3：queries.py 制度分析查询（analyses 子命令）
- 🟢 P3：queries.py 跨实体追溯（trace 子命令：finding ↔ design observation ↔ control point）
