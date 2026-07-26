# 项目长期记忆

## 关键约定
- 原子化提交：每次 git commit 只包含一个独立逻辑变更
- 提交信息格式：`type: 中文描述(P-number)`
- 验证模式：修改代码后必须执行验证计划中的对应测试用例
- Python 执行环境：`C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe`（含 pandas 2.3.2）

## 当前架构（2026-07-26）
- 12 个 Skill + 2 Evaluators + 4 个新脚本（data_executor/audit_gate/check_mandatory_coverage/evidence_catalog）
- 四重闸机：phase_gate / validate / tool-check / audit_gate
- Finding schema 1.2.0（title/risk_level/origin/evidence[]）
- PaddleOCR 替代 EasyOCR（已安装验证，核心文本识别率 90%+，但 20分钟/8页，不用于证据匹配阶段）

## 证据存储架构 v2.0（2026-07-26）
- 集中存储：`evidence/{project}/_files/` 存放所有共享证据（只放一份）
- 证据清单：`_evidence_catalog.json` 由 Python 从程序 Markdown "取证方式"列自动生成
- 匹配策略：Python 结构指纹（列名/行数/文件名）→ LLM 综合判断 → 用户确认
- 向后兼容：已有项目旧 evidence 结构不动，新项目启用新结构

## 项目命名规则（2026-07-26）
- `current-audit.json` 中的 `project_name` 必须与项目文件夹名保持一致
- 示例：文件夹 `AU_PL_260601_人力资源_武汉长源` → `project_name: "AU_PL_260601_人力资源_武汉长源"`

## 已部署项目
- P-2026-001: 武汉长源 人力资源管理 phase_3_execution
- P-2026-002: 广东长华 人力资源管理 phase_2_program_generation

## 用户偏好
- 搁置理由"民企不关注"：关联交易/个税/出口管制/反不正当竞争法
- 搁置理由"暂无公司授权"：加密存储/外部连接器/PIPL/持续监控
- 搁置理由"单人使用"：SQLite 架构升级
