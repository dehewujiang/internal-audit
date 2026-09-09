# _shared/scripts 脚本说明

本目录为 internal-audit 平台核心脚本。绝大多数接入各 SKILL.md 工作流（见 CLAUDE-project.md 工具清单）。

**有一个例外，特意记录如下：**

## 增量制度分析（analysis_manifest.py + incremental_analysis_gate.py）

- **功能**：制度文件哈希检测（diff/mark/status）+ 增量分析三闸机（check/verify/finalize）——用于"制度中途更新时，只重新分析变化的部分，未变的文件用旧 JSON 交叉验证"，省 token。
- **真实历史（2026-09-01 git 复查纠正）**：这两个脚本**不是"从未接入"——它们接入过，两天后被整体拆除**。
  - **2026-07-15**（提交 `9b7305d`）：脚本创建**同日即接入** document-organizer——SKILL.md 新增"增量分析（闸机强制）"整章（mode 表 full/incremental/no_change/repair + check/verify/finalize 三闸机调用点），workflow.md 新增"Step -1：增量检测闸机"，工具清单加 5 条命令。
  - **2026-07-17**（提交 `f8e3f2b`）：接入被**整体回退**——SKILL.md 删 131 行、workflow.md 删 89 行，增量章节全部移除。但脚本文件本身保留未删。
  - **拆除动机（[推测] 依据同批改动推断）**：7-17 是一次**全系统简化瘦身**（87 文件、+1740/-6377 行），提交信息"templates simplified, SKILL.md track marker constraint"。同批被拆的还有 7-15 刚加的 decision_log 硬性要求、5.0 格式硬校验、业务对象索引（两遍法）、verification_status 状态机铁律、行业基准细化（277 行→39 行）及 3 份旧方案文档。增量分析是"SKILL.md 瘦身运动"的连带牺牲品，**并非被单独否决**；7-17 后脚本成孤儿，2026-08-12 被记为"全库 0 引用"（记录只描述了现状，丢失了这段接入-拆除史）。
- **为什么保留而非删除**：脚本设计完备且理念与系统一致（参照 ADR-006 程序增量更新）。真实审计中制度"偶尔更新、很少发生"，当前全量重跑成本可接受，故**暂不接线**。若删除，git 历史可随时找回（最后一次修改 2026-07-15）。
- **何时启用**：未来若制度更新变频繁、全量重跑 token 成本变高，恢复接线前**先决策用哪种方案**：(a) 恢复旧脚本接入（git 历史 `9b7305d` 可回放当时的 SKILL.md 接入方式）；(b) 按 7-17 之后的"轻量 SKILL.md"哲学重写一版更薄的增量说明。2026-08-06 起制度分析已强制 `document_info.version/effective_date`（防废止制度污染），增量检测与版本字段天然互补。
