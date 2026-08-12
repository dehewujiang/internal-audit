# _shared/scripts 脚本说明

本目录为 internal-audit 平台核心脚本。绝大多数接入各 SKILL.md 工作流（见 CLAUDE-project.md 工具清单）。

**有一个例外，特意记录如下：**

## 增量制度分析（analysis_manifest.py + incremental_analysis_gate.py）

- **功能**：制度文件哈希检测（diff/mark/status）+ 增量分析三闸机（check/verify/finalize）——用于"制度中途更新时，只重新分析变化的部分，未变的文件用旧 JSON 交叉验证"，省 token。
- **现状（2026-08-12 五重排查确认）**：**未接入任何 SKILL.md 工作流**。document-organizer 采用全量分析（分析 documents/ 所有文件），从不调用它们。全库 0 引用，phase_gate 白名单不含，CLAUDE-project 工具清单未提——它们完全游离在工作流之外。
- **为什么保留而非删除**：设计完备且理念与系统一致（参照 ADR-006 程序增量更新）。真实审计中制度"偶尔更新、很少发生"，当前全量重跑成本可接受，故**暂不接线**。若删除，git 历史可随时找回（最后一次修改 2026-07-15）。
- **何时启用**：未来若制度更新变频繁、全量重跑 token 成本变高，恢复接线（在 document-organizer/SKILL.md 增量路径调用 check/verify/finalize）。
