# queries

## 能力
- 按风险等级/状态/关键词/年度/来源查询 findings
- 全文搜索 finding 正文（递归搜索所有 JSON 字段，显示匹配上下文）
- 查询制度分析结果（控制点/缺口/风险点统计，按主题筛选）
- 跨实体追溯（finding ↔ design observation ↔ control point ↔ 审计程序）
- 展示评估趋势（最近 N 天各内容类型的质量波动）
- 跨年份 finding 对比（相似度检测）
- 汇总统计（总数、风险分布、状态分布、来源分布、年度分布）

## 用法
```bash
python queries.py findings --risk 高
python queries.py findings --keyword 废料 --year 2026
python queries.py findings --status 待整改
python queries.py findings --by-origin design
python queries.py trend --content-type audit_program --days 90
python queries.py compare --topic 存货管理 --from 2025 --to 2026
python queries.py summary
python queries.py search "SAP 权限"
python queries.py analyses --topic 存货管理 --gaps
python queries.py trace F-2026-001
```

## 限制
- 只查询已有的 findings，不生成新的 finding
- 关键词搜索依赖 index.json 中预建的 by_keyword 索引
- 跨年对比基于标题字符相似度，不是语义相似度

## 输入
- findings/index.json
- findings/F-YYYY-NNN.json（单个 finding）
- evaluator JSONL 历史（趋势查询）

## 输出
- 文本格式（默认）或 JSON 格式

## 授权
level_0（全阶段可用）
