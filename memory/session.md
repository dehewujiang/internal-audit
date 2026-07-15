# 最近一次工作记录

## 完成了什么
本次 session（2026-07-14）完成了审计技能注册修复。

### 问题诊断
用户报告部署项目 `AU_PL_260601_人力资源_武汉长源` 中 Claude Code 无法识别审计技能（如 `/internal-audit-program-generator`）。

**根因链**：
1. 源仓库 `.claude/skills/` 只有 geb-bootstrap 和 geb-workflow 两个技能
2. 10 个审计技能目录在仓库根目录，格式正确但未注册
3. `setup-project.ps1` 首次部署从根目录逐个部署 → 正确（10 个技能全在）
4. `update-project.ps1` stable 模式整目录复制 `.claude/skills/` → 覆盖成只有 2 个
5. 项目经历了 3 次 update，每次都被覆盖掉

### 修复内容
1. 源仓库 `.claude/skills/` 下创建 10 个目录 junction → 仓库本身能识别 12 个技能
2. `setup-project.ps1` 改为扫描 `.claude/skills/` 自动发现技能，消除硬编码列表
3. `setup-project.ps1` 新增 `.claude/settings.json` 和 `.claude/rules/` 部署
4. `update-project.ps1` stable 模式改为逐技能合并，不再整目录覆盖
5. 部署项目 `武汉长源` 已补齐 10 个技能 + settings.json + rules

### 提交
- `271ac1d` — 91 files, VERSION → 2026-07-14-15

## 为什么这样做
技能注册的一致性必须是基础设施级别的保证——两个部署脚本的行为不同源（一个从根目录读，一个从 `.claude/skills/` 读），必然导致部署后行为不一致。统一到 `.claude/skills/` 作为唯一来源，消除了这个系统性缺陷。

## 未完成事项
- 无

## 下一步建议
1. 在 `武汉长源` 项目中验证 `/internal-audit-program-generator` 可用
2. 如其他已部署项目也存在同样问题，重新运行 `setup-project.ps1 --stable` 补齐
