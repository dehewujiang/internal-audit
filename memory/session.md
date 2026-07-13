# 最近一次工作记录

## 完成了什么
本次 session（2026-07-13）关闭了"project-init 不会自动注册到跨项目索引"的非阻塞缺口。

### 改动：project-init SKILL.md 新增 Step 4.6 自动注册
- 在 Step 4.5（constitution.md + tools/ 创建）和 Step 5（确认输出）之间，插入 Step 4.6
- 项目创建完成后自动执行 `queries.py register --path <project_dir> --topic <topic> --period <period>`
- 参数从 current-audit.json 自动提取：topic = audit_topic，period = audit_period.start_date 前 4 位年份
- 注册失败不阻断项目创建——exit ≠ 0 时仅显示警告，继续 Step 5
- Step 5 确认输出中增加 `{auto_register_result}` 占位（成功显示项目 ID，失败显示警告）
- project.md 已知缺口表从"1 项"归零

## 为什么这样做
`queries.py register` 的 Path→topic→period 信息在 project_init.py 执行时尚未落地（current-audit.json 还没写入），不适合塞进 Python 脚本。但 SKILL.md 是 LLM 执行的编排器，Step 4.5 之后所有文件已就绪——此时 `scan_project()` 能自动从 current-audit.json 读取 topic 和 phase，`queries.py register` 开箱即用，零代码改动。

## 遇到什么问题
- 无

## 未完成事项
- 无

## 下一步建议
1. 实际审计项目中使用 project-init，验证注册链路端到端
2. 如有需要：让 setup-project.ps1 --stable 模式下的项目也自动注册（当前 setup-project.ps1 不涉及，它是部署工具链不是创建项目）
