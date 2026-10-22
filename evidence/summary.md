# 本批交付（2026-10-22）：探索车道闭环（第一批）

1. **执行留痕**：每次沙箱执行都在输出目录留下 `code.py`（代码原文）和 `run.json`（源文件 sha256、开始/结束时间、状态、行数、列数、timeout）；卡死改为子进程到点被杀，默认 30 秒（`--timeout` 可调）；Excel 可用 `-d "别名=路径#工作表"` 指定工作表，文件路径本身含 `#` 时按整条路径处理。
2. **底稿工具**：新增 `explore_paper.py`——`new` 生成 `底稿.md` + `底稿.json` 骨架并自动写入源文件 sha256；`check` 自检，事实没有依据文件、线索没有下一步证据一律拦下（exit 2）。
3. **配套**：新项目自动建 `evidence/explore/`、`evidence/reconcile/`、`reconcile/`；OPS/AGENTS/CLAUDE 已同步；`evidence/explore/` 已加入 `.gitignore`，真实数据不入库。

**验收**：红阶段原始日志 `evidence/red.log`（23 条断言失败）→ 绿（34 条断言全过）；全量 10 个测试通过；真实工作簿指定 sheet 读到 88 行并落痕；样例底稿自检 `action=pass`；独立验收小工裁决 **通过**（`evidence/review.json`）。
**还剩**：`CLAUDE-project.md` 部署版待补 `explore_paper.py` 一行；口径卡第二批（row_formula/cross_table）未开工；`data_executor.py`/`explore_paper.py` 超 300 行的拆分评估留待后续。
