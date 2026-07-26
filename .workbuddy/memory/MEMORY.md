# 项目长期记忆

## 关键约定
- 原子化提交：每次 git commit 只包含一个独立逻辑变更
- 提交信息格式：`type: 中文描述(P-number)`
- 验证模式：修改代码后必须执行验证计划中的对应测试用例
- Python 执行环境：`C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe`（含 pandas 2.3.2）

## 当前架构（2026-07-22）
- 12 个 Skill + 2 Evaluators + 3 个新脚本（data_executor/audit_gate/check_mandatory_coverage）
- 四重闸机：phase_gate / validate / tool-check / audit_gate
- Finding schema 1.2.0（title/risk_level/origin/evidence[]）
- PaddleOCR 替代 EasyOCR（安装中）

## 已部署项目
- P-2026-001: 武汉长源 人力资源管理 phase_3_execution
- P-2026-002: 广东长华 人力资源管理 phase_2_program_generation

## 用户偏好
- 搁置理由"民企不关注"：关联交易/个税/出口管制/反不正当竞争法
- 搁置理由"暂无公司授权"：加密存储/外部连接器/PIPL/持续监控
- 搁置理由"单人使用"：SQLite 架构升级
