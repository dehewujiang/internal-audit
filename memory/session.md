# 最近一次工作记录

## 完成了什么
本次 session（2026-10-08）：**重设计第一步"关双轨"实施**（commit `94b8f1f`，21 文件 +307/-306）。前置产出：`新架构设计稿_2026-10-08.md`（commit `d77b00a`，不管老项目版）+ 第一步实施细案（12 改动点，用户拍板 A-a/B-不管老项目后开工）。

### 清单
1. **查询只认桌子**（`query_data_sources.py`）：单项目查询/搜索/汇总删旧格式分支；汇总改桌子统计（保 total/by_risk/by_status/by_origin/by_year 五键，by_year 恒空）；跨项目 `_iter_all` 加桌子行（`load_audit_tables/load_table_findings` 加可选 `ws` 参数，老调用不动）；关键词对桌子行直查文本（否则 index 过滤误杀）
2. **来龙去脉卡**（`query_commands.py`）：主查找加桌子兜底（按编号/`source.ref` 对单号）；同源关联对桌子行返回空（已知缺口，函数自述"缺纸就空着"）
3. **闸机两处**：`phase_gate.py` phase_3 出口加"或桌子 left≥1 行"（否则新项目永远卡死）；`audit_gate.py` 报告 precheck 改一行描述（实测纯文字提醒，零风险）
4. **删 `validate-index.py`**：R06 随 index 停写而消亡；`validate-catalog.py` 保留（保证据柜，不是双轨——纠正设计稿一处）
5. **4 份 SKILL 并到写桌子**：执行（结论只上桌+index停写+上桌后跑门卫查硬度 A-a）、报告（删 R06 节+历史对比只认新账不管老项目 B）、吵架（按编号对单号）、问话（历史发现读桌子两格）
6. **快照同步**：`cceer_chain.snap`（尾部"输出 finding"改"上桌+门卫"，保 decision_rationale 句）+ `root_cause_challenge.snap` 加 dated 注记——源+快照同改
7. **文档工具表同步**：AGENTS.md/CLAUDE.md/CLAUDE-project.md/DATAFLOW.md/INPUT-BUDGET.md 删 validate-index 行
8. **B1 事前红测试**（`tests/fixtures/redesign/`）：红（2 条失败，旧格式仍被读）→ 绿，全过
9. **VERSION.json**：已 bump 到 2026-10-08-1（`--help` 误触 bump 一次，changes 手工补 10 条未再推高）

### 验证（全[运行确认]）
- B1 红转绿；8 旧测试全过；回归 GREEN=2 RED=0；快照过；pre-commit 三道（影响卡片+回归+快照）全过才放行
- `test_batch3_queries.py` 无需改（实测全过：它无旧格式查询断言）——细案 #11 作废
- `compare_years` 单项目分支不动（无 index 自然回"无数据可比较"，与 B 决策自洽）

### 关键决策（用户拍板）
- **A-a**：终检用门卫（`ledger/check.py` 查硬度），草稿期 validate-finding 原样保留
- **B**：历史对比不管老项目；桌子行暂无年份信息，跨年口径待新账积累后定

## 遇到问题
- 测试 import 失败：`REPO_ROOT` 少算一层（`tests/fixtures/redesign/xxx.py` 到仓库根要上 4 层）——已记 feedback
- `search()` 返回 match-dict 无 `_from_table` 键，断言改按 `finding_id` T- 前缀——已记 feedback
- `bump-version.py --help` 也会推高版本——已记 feedback
- 第一次提交被快照闸机拦（cceer/root_cause 未同步）：compare-snapshots 只读暂存区，未 add 前手动跑永远过——已记 feedback；按 R08 源+快照同改后放行
- 快照尾行改写时一度丢了 decision_rationale 句，自查补回

## 未完成事项
- **R09 真人回归新增 4 份 SKILL 改动**：执行/报告/吵架/问话的"只读桌子"行为待下次真项目验证（记 TODO）
- **重设计第二步（写入口收权）**：未开工，等用户拍
- cceer/root_cause 快照 10-07 欠账行（本次只加了 10-08 行，之前缺的 dated 行仍缺）——TODO 原有项保留
