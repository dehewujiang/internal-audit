# 最近一次工作记录

## 完成了什么
本次 session（2026-07-26）完成了证据集中存储与智能匹配架构 v2.0 的设计、实现和部署。

### 方案设计（多轮讨论）
- **问题**：证据按程序文件夹存放，一份文件被多个程序引用需复制多份
- **方案**：集中存储 `_files/` + 证据清单 `_evidence_catalog.json`
- **槽位生成**：Python 从程序 Markdown "取证方式"列自动提取（非 LLM）
- **匹配策略**：Python 结构指纹（列名/行数）→ LLM 综合判断 → 用户确认
- **OCR 定位**：PaddleOCR 验证通过（90%+ 准确率）但 20min/8页，不用于匹配阶段
- **证据状态**：三区展示（已匹配 / 缺失 / 未匹配文件），用户可见完整进度

### 代码实现
1. `create_evidence_dirs.py` — 新增 catalog 生成（4 函数）+ `_files/` 目录
2. `evidence_catalog.py` — **新建**：catalog CRUD + 文件扫描 + 关键词匹配
3. `SKILL.md` — 更新证据路径 + 匹配流程
4. `constitution.md` + `finding_schema.md` — 路径格式更新

### 验证
- catalog 生成：用真实程序生成 162 槽位，33 个多程序共享
- 文件扫描/匹配：功能正常

### 部署
- 武汉长源/广东长华已回退，等用户手动 `update-project.ps1` 部署

### 项目命名规则固化
- `project_name` 必须等于项目文件夹名
- 已写入 `project-init/SKILL.md` 模板和禁止事项
- 两个已有项目已同步修正

### 提交
- `20ad90b` feat: 证据集中存储与智能匹配架构
- `4c54f39` chore: 清理临时目录
- `0b8fdee` chore: bump version
- `790216a` deploy + 命名规则
- `c70bbb6` docs: 命名规则固化

## 为什么这样做
多对多的证据-程序关系不能用树状文件夹表达。集中存储 + 结构化清单是最小代价的实现。

## 遇到问题
1. **PowerShell 工具在当前会话中静默输出**：`echo "hello"` 也无输出，导致 `update-project.ps1` 无法执行。改用 Python + Bash 手动完成文件同步。
2. **部署流程错误**：先跑了 `create_evidence_dirs.py` 创建目录和 catalog，但跳过了 `update-project.ps1`（应先用它同步 `_shared/`、`tools/` 和 VERSION.lock）。用户要求回退后自行手动部署。
3. **忘记跑 bump-version.py**：代码变更 commit 前未跑，违反了 `feedback.md` 硬规则。

## 未完成事项
- `update-project.ps1` 部署由用户手动执行
- P-2026-002 广东长华程序 v1.0 缺少"取证方式"列，需升级到 v3.0 才能自动生成 catalog

## 下一步建议
1. 用户手动 `bump-version.py` → `update-project.ps1` 部署两个项目
2. 部署后在武汉长源项目中验证完整流程：扔文件 → 说"帮我匹配" → 确认 → 执行程序
