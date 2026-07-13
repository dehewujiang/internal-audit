# 最近一次工作记录

## 完成了什么
本次 session（2026-07-13）改进了 CLAUDE.md 和 CLAUDE-project.md 的文档完整性。

### CLAUDE.md（技能源码仓库版）— 6 项增量改进
1. 加标准头部（`# CLAUDE.md` + guidance 说明）
2. 修正技能数量 8→12（实际有 12 个 SKILL.md）
3. 新增 Skill → Phase 对照表（12 个技能 × 6 个审计阶段）
4. 新增部署架构说明（junction/stable 双模式 + 部署后目录结构）
5. 扩展关键文件表（+CLAUDE-project.md、OPS.md、VERSION.json、setup/update 脚本）
6. 新增 `_shared/scripts/` 一句话速查表（14 个脚本 + 外部评估脚本）

### CLAUDE-project.md（审计项目运行版）— 4 项同步改进
1. 加标准头部
2. 新增 Skill → Phase 对照表
3. 新增 `_shared/scripts/` 速查表
4. 新增 Architecture gotchas（current-audit.json 标志位、workspace 子目录映射）
5. 新增 Key files to know 表（含 topic.json）

### 两份文件的差异保持设计意图
- CLAUDE.md 多「部署架构」和「规则加载」— 开发视角
- CLAUDE-project.md 多 topic.json 引用 — 干活视角
- 共享的 12 个章节内容完全对齐

## 为什么这样做
ADR-010 拆分 CLAUDE.md/CLAUDE-project.md 的决策仍然有效，但两份文件缺少技能阶段映射和脚本速查表，未来 Claude 实例需要读多个文件才能建立全局视图。增量补充不改变既有架构。

## 遇到什么问题
- 无

## 未完成事项
- 无

## 下一步建议
1. 如有新 skill 或脚本变更，同步更新两张速查表
2. 已有项目需跑 `update-project.ps1` 才能拿到 CLAUDE-project.md 的更新
