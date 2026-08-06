# 最近一次工作记录

## 完成了什么
本次 session（2026-08-06）以"内部审计专家 + 系统评估"视角对全系统做了一次深度体检，并完成四轮整改闭环（版本 2026-08-06-1/2/3 均已部署双项目）。

### ① 体检评估（产出决策依据）
- 按流水线逐环节评估（立项/制度/访谈/程序/执行/攻防/报告/横切闸机），发现：制度版本字段"设计有执行无强制"、constitution 12/13/14 条静默丢失、快照 4 处实质漂移、知识库混源污染、调查方法合规风险、统计抽样框架缺失等

### ② 坏路径全量修复 + 孤儿文档接入（VERSION 2026-08-06-1，commit a8dd3d2 + c4128d8）
- 36 处 `~/.claude` 残留（12 文件）按三标准替换：`audit-topics/`、`_shared/scripts/`、`.claude/skills/{skill}/`（ADR-023）
- dynamic_questions.md 接入 Step 0.4（配置空白检测→追问→回写 my-config）；incremental_update.md 接入 Step 0.5（phase_gate 信号→增量模式）；output_template 补十/十一章

### ③ 宪法恢复 + 证据标准统一 + 知识库过滤（VERSION 2026-08-06-2，commit fa412dd + 9ab8c13）
- constitution 恢复 11-14 条 + 阶段流转规则 + 启动协议（20ad90b 误删回归，ADR-022）
- cceer_standards A+B→A+E；validate-finding 必填补 consequence；对抗验证 30%/50% 阈值补回
- 知识库混源过滤（2.2/2.3/3.1/3.2 → 附录A/B）；U8 残留清零

### ④ 阶段二闸机体系（VERSION 2026-08-06-3，commit fa143a4 + 7fd2c46）
- Step 4.5 程序结构化闸机（program_ir_parser → validate-program --ir → 激活轨道校验）+ 三重屏障
- 新建 validate-catalog.py / validate-index.py（R05/R06）；制度版本强制（N6）

### ⑤ 阶段三开发治理（commit 26c511d，不部署）
- 5 份快照重写对齐源文件（4 处实质漂移修正）；compare-snapshots.py + pre-commit hook（R08）；人工抽查清单（R09 交付物，实测由用户执行）

## 为什么这样做
评估发现的问题清单驱动：坏路径导致运行时反复降级询问、宪法条款丢失等于制度允许 AI 绕过闸机、快照漂移使回归对比失效、混源污染让程序生成跑偏。核心原则：文档-代码一致性靠机器检查（hook+校验器）而非 LLM 自觉。

## 遇到问题
- constitution 11-14 条被 20ad90b 静默误删（git 取证恢复）
- 8-05 记录"grep 验证无残留"是假阳性（实际 44 处）——已写入 feedback 教训
- 文档字段名与代码多次不一致（R05 方案 slot_id vs 实际 id/file）

## 未完成事项
- R09 实际抽查（用户手工执行，commit 标注 `已人工回归: [项目] [评级]`）
- N8 调查方法合规分级（用户搁置——"小黑屋/威胁施压"内容仍在文档中）
- 统计抽样方法 reference（用户搁置）
- 广东长华程序 v1.0→v3.0 升级（用户搁置）
- B1.1/L1.1 证据迁移决策（待用户）
- `data/evaluations/2026-07-17.jsonl` 是否已并入源仓库（待确认）
- memory 收工提交（本次）

## 下一步建议
1. 跑一次真实审计验证新闸机行为（Step 0.4 配置追问 / Step 0.5 增量分流 / Step 4.5 程序拦截）
2. 用户执行 R09 人工抽查并反馈 RED 级问题
3. 决策 B1.1/L1.1 迁移、广东长华升级排期
4. 重启 opencode 使部署项目新 SKILL.md 生效
