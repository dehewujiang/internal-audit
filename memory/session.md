# 最近一次工作记录

## 完成了什么
本次 session（2026-10-07）：**桌子v2.0 全量落地——从"复印件"改成"数据库"**，外加CI自动测试。全程master直做（前半段worktree开发，后半段文档/CI直接改），用户每个"继续/开始"都是明确点头。

### 清单（提交号）
1. 桌子v2.0核心（`42c4b92`，9文件400行）：schema_v2.json（账本+底稿两层，ingested取消，每行带source）+ 冲压车间_v2.json试点 + MIGRATION.md搬家说明书 + 4个SKILL.md改直接写桌 + ledger.py加--room/--ref/--status + query_data_sources.py认桌子（load_table_findings）
2. 存量整理（`31751db`，10文件820行）：闸机IR测试+新桌子设计稿+参考文件（之前session留下的）
3. 文档同步（`0fd49b8`，3文件18行）：DATAFLOW.md主图/CLAUDE-project.md架构备注/AGENTS.md工具清单
4. CI自动测试（`17b4f5b`，2文件81行）：.github/workflows/ci.yml + test_ledger_fixes.py跟上v2.0架构

### 验证
- 8个测试全绿（test_ledger_fixes 4条红→改测试检查add-line而非sweep→转绿）
- ledger.py实操测试：source字段写入/老命令兼容/空workspace不报错
- query_data_sources.py实操测试：load_table_findings/query_findings/search全通过
- 回归基线2 GREEN，快照检查过
- 已推远端（origin/master在`17b4f5b`）

## 为什么这样做
用户说"把桌子改成数据库"——大活，走preflight交考卷→worktree开发→试点→改写法→改查询→文档同步→CI。核心决策（ADR待补）：桌子=账本（记结论），底稿=备查（记过程）；老项目不搬家，只改查询命令。

## 遇到问题
- 三个deep工模型坏掉→停掉自己干（SKILL.md改动+ledger.py改动都是自己做的）
- load_table_findings空单号列表取值崩溃（`[0]`越界）→改为`ref_ids[0] if ref_ids else`兜底
- test_ledger_fixes.py检查"必须有sweep"→v2.0故意去掉sweep→测试跟着架构改
- 快照同步欠账（cceer_chain.snap/root_cause_challenge.snap）：本次没碰到所以不拦，下次改技能说明书要补

## 未完成事项
- 快照同步欠账（2个snap待补）
- 快照钩子/文档同步钩子：用户问"为什么漏了文档同步检查"，确认没钩子管这个，建议设一个但没设
- 项目级`_recon.py`清理（worktree里建的临时脚本，已删但值得留意）
- history遗留照旧：闸机接--ir、部署双项目、R09、N8

## 下一步建议
1. 补快照同步（改了4个SKILL.md，2个snap要跟着更新）
2. 设文档同步钩子（提交改了SKILL.md/ledger/时提醒检查AGENTS.md）
3. 拿个真实项目走一遍v2.0端到端，验证"直接写桌"在实战里好不好用
4. 考虑把worktree开发流程固化（用户已认可"开房"模式）
