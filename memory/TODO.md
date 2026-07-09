# TODO

## #进行中
- 无

## #待办
- 🟡 工具分时段硬拦截：当前 CLAUDE.md 有 phases 字段但无代码级强制，LLM 可能在不同阶段调用不对的工具。需要在闸机层面做 tool 白名单校验。
- 🟡 决策追溯体系：无统一的证据日志或裁决记录，出问题后查不清决策链路。需要建设 cross-pipeline 可观测性框架。
- 🟡 document-organizer 跨段落隐含控制：需从输入端解决——要么对整套制度做全文搜索后拼上下文再交给 LLM 分析，要么让 LLM 先做控制索引再逐控制点做详情提取。建议方案：topic.json 必查模块 → 按控制类型全文档搜索关键词 → 归类后 LLM 拿到完整上下文再分析。
- 🟡 document-organizer 输出一致性：需加"两次提取+差异对比"或"同份文档两次分析结果比较"机制，差异点标记为"待确认"。

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
