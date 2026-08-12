# 最近一次工作记录

## 完成了什么
本次 session（2026-08-12）：规则体系重构 + 验证分层 + 坑2 诊断 + 纳米测试审查 + 记忆补档。

### ① 规则体系重构（源/12_AGI/全局 + internal-audit 副本同步）
- 验证优先原则落地：verification-first → 并入 coding-safety → 拆分为 **coding-safety（编码专用，带 paths）** + **work-principles（通用，无 frontmatter 全量）**
- work-principles 新增「〇、验证分层」L1/L2/L3 + 任务理解确认同步分层（L1 一句话 / L2/L3 全套）
- 全局 + 12_AGI CLAUDE.md 前置约束改指 work-principles
- **实测发现（关键）**：internal-audit/.claude/rules 与 .workbuddy/rules 是**复制副本，非 junction**（删除联动测试证明）——改源需手动同步三处

### ② 坑2 验证优先诊断（已记档待整改）
四重闸机逐个核查 → 4 漏洞：① 程序覆盖率自证（validate-program 的 risk_register 是程序自列，覆盖率分母应改上游独立清单）② 证据等级 AI 自标（reliability_grade 由 AI 填，应 data_executor 自动 A / OCR 自动 C / AI 只标 E）③ 制度校验看转述（validate-policy-analysis 读 AI JSON 不读原始制度）④ 报告二手汇总（不根治）。记 TODO 待排期。

### ③ 纳米测试三问 25 脚本审查
- **2 孤儿**：analysis_manifest + incremental_analysis_gate（全库 0 引用，document-organizer 全量分析从不调用；判定设计超前、制度偶尔更新需求未触发）→ **保留待接线**，记录 `_shared/scripts/README.md`
- **1 偏重**：create_evidence_dirs（名为建目录实为 457 行解析器 + 3 处死代码 + 与 evidence_catalog 重叠）→ 重构候选，记 TODO
- 核心 20 个三问通过

### ④ 记忆补档 + 仓库卫生
- 8-11 架构加固收工记忆补写（project/TODO/session/context/INDEX）
- 未提交改动处理（coding-safety 分级验证提交、.omo/.workbuddy 收进 .gitignore、data/evaluations 删除确认）

## 为什么这样做
规则按适用面分层（编码 vs 通用）+ 验证按任务强度分层，消除重复矛盾与 token 浪费；坑2 照出两个此前未发现的真漏洞（程序自证覆盖、证据自标等级）。

## 遇到问题
- **junction 假设错误**：我基于文档（context.md 曾写 junction）假设复制是 junction，动手挪移导致混乱；用户纠正"在源上更新"。实测删除联动证明是复制。**教训：动目录结构前先实测物理关系（fsutil/inode/联动测试），别信文档。**
- 12_AGI\CLAUDE.md 有大量预存未提交改动（沟通风格版→全局元规则版），只提交需谨慎避免捆绑。

## 未完成事项
- 坑2 整改（4 漏洞待排期，实施前出规划模型）
- 部署加固成果到双项目（VERSION.lock 08-06-4 → 08-11-3）
- R09 抽查 / C6 试点评估 / N8 合规分级决策
- 规则三处副本无自动同步（复制非 junction）

## 下一步建议
1. 坑2 整改排期（漏洞2 程序覆盖率 + 漏洞3 证据打章优先）
2. 用户部署双项目
3. R09 / C6 / N8 逐项决策
