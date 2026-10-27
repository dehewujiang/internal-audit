# 最近一次工作记录

## 完成了什么
本次 session（2026-10-22）：**探索车道闭环（第一批）**（commit `2041b60`，VERSION 2026-10-22-1，16 文件 +1158/-48）；另产出「设备维修履历」探索底稿（格式样例，用户认可结构），并把「非技术用户权限提示」规矩升到全局常驻规则。

### 清单
1. **data_executor**：执行后落 `code.py` + `run.json`（源文件 sha256、起止时间、状态、行数、列数、列名）；超时改为**子进程到点被杀**（默认 30 秒，`--timeout` 可调）；`-d 别名=路径#工作表` 指定工作表；路径本身含 `#` 时不误切；出错 CLI exit 2
2. **新增 explore_paper.py**：`new` 建骨架（自动写源文件 size/sha256，已有文件拒绝覆盖）；`check` 自检（事实缺依据 / 依据文件不存在 / 线索缺下一步证据 / 线索依据不是已登记事实 id / conclusion 非布尔 → exit 2）
3. **配套**：`project-init` 建 `evidence/explore`、`evidence/reconcile`、`reconcile`；OPS/AGENTS/CLAUDE 同步；`.gitignore` 挡真实数据产物、白名单测试日志、忽略 `subagents.jsonl`
4. **测试**：新增两个测试文件，红 23 条 → 绿 34 条；全量 10 个测试全过；独立验收小工裁决「通过」（`evidence/review.json`）
5. **探索底稿样例**：`evidence/explore/2026-10-22_设备维修履历/`（MES 维修履历 5356 行 + 采购样本 88 行；18 条事实、9 条线索；自检 pass）——只在本机，不入库
6. **全局规则**：`12_AGI/claude/rules/core.md`〈2. 决策归属〉加「不可逆操作先问四件事（改/删什么、为什么、能否恢复、建议选几）」；源库未提交（用户选 A：等规则目录搬家做完整批提交）
7. **部署 AU_TEST**：`AU_TEST_基建工程` 2026-10-10-1 → **2026-10-22-1**（7 项升级 0 失败；备份 `.backup\20261022-160502`；部署后冒烟：`data_executor` 落 code.py/run.json、columns=2、sha 64 位）

### 验证（全[运行确认]）
- 红阶段 `evidence/red.log`（HEAD 干净 worktree 跑的 23 条失败）→ 绿 `evidence/test.log`（10 测试全过）
- 真实工作簿指定 sheet：`#2025设备推进` → 88 行 3 列；复跑前后 `code.py`/`result.csv` sha256 一致
- 样例底稿 `explore_paper.py check` → `action=pass`
- pre-commit：回归 GREEN=2 RED=0、快照一致性通过

### 关键决策（用户拍板）
- 口径卡加 `row_formula`、`cross_table` 两类（随执行器一起做）；**勾稽执行器搁置**（用户未想好）
- 数据安全选 A：`evidence/explore/` 不入库，只留本地
- 全局规矩只改源、源库暂不提交
- **2026-10-22 用户确认：武汉长源、广东长华两个老项目已结束，不再部署**；部署欠账关闭，R09 载体待定

## 遇到问题
- 验收小工抓出两处「证据记录不实」：`run.json` 声称记了「行列数」实际只有行数；`evidence/run.json` 里的命令缺 `-c/-o`，照抄跑不通。已修（补 columns/column_names + 完整命令实跑）并复验通过。
- 红阶段日志一度被绿日志覆盖，事后无法自证「测试先红」→ 改用 HEAD 干净 worktree 重跑留证。

## 未完成事项
- **勾稽执行器 + 口径卡两类**：搁置，等用户想好
- `data_executor.py`(584行) / `explore_paper.py`(369行) 拆分评估
- R09 增项：`project-init` SKILL 改动待人工抽查
- `CLAUDE-project.md` 部署运行版已补 `explore_paper.py`（本次收尾完成）
