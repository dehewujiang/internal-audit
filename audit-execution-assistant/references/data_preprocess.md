# 大文件数据预处理（Step 2.0）

> SKILL.md Step 2.0 的完整细节。CSV/Excel 行数 > 200 时先过 Python，不直接全文读取。

当证据文件为 CSV/Excel 且行数 > 200 时，不要直接用 LLM 读取全量数据。执行以下预处理：

1. **了解数据结构**：调用 `python _shared/scripts/data_executor.py columns <文件路径>` 获取列名、类型和前 20 行样本
2. **了解可用工具**：调用 `python _shared/scripts/data_executor.py tools` 查看 8 个预制分析工具
3. **生成分析代码**：基于审计程序要求和数据结构，生成 pandas 分析代码。可调用预制工具作为快捷函数
4. **沙箱执行**：`python _shared/scripts/data_executor.py execute -c '<code>' -d '<alias>=<path>' -o <output_dir>`
5. **读取结果**：读取输出的 result.csv 和 JSON 摘要（通常仅几十到几百行异常数据）
6. **标注来源**：在分析报告中写明"全量分析：原始 X 行，异常 Y 行"

**前置工具函数列表**（可在代码中直接调用，无需 import）：

| 函数 | 用途 |
|------|------|
| `benford(df, col)` | 数字分布异常 |
| `dedup(df, cols)` | 重复值检测 |
| `gap(series)` | 序列断号检测 |
| `threshold(df, amount, date, limit)` | 审批阈值穿透 |
| `timeseries(df, date, value)` | 时间序列 Z-Score 异常 |
| `outlier(df, col, method)` | IQR/Z-Score 离群值 |
| `crossref(df_a, col_a, df_b, col_b)` | 两表关联交集 |
| `stratify(df, group, metric)` | 分层汇总对标 |

**安全约束**：
- 代码末尾必须赋值 `OUTPUT = <你的结果DataFrame>`
- 代码在沙箱中执行，禁止文件删除/系统调用/网络
- 30 秒超时，5000 行输出上限
- 若数据 ≤ 200 行，跳过此步骤，直接 LLM 分析
