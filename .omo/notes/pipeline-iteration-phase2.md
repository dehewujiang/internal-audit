# 管线迭代更新架构二期 — 任务清单

记录日期：2026-07-09
前置条件：interview-designer-v3 执行完毕

## 背景

一期（interview-designer-v3）只覆盖了"访谈回填→标记程序 stale→程序可更新"的单向闭环。
真实审计是迭代的，以下四个方向仍需建设。

## 待建方向

### 1. document-organizer 增量分析
- 追加制度文件 → 增量重分析（不推翻已有 policy-analyses）
- 增量分析完成后 → 标记下游 `artifacts["policy-analyses"].freshness = "stale"`
- 下游（interview、program）感知 policy-analyses 变更后可选择刷新

### 2. execution→interview 回流信号
- 执行中发现新线索 → execution-assistant 可输出"建议补充访谈"信号
- 信号写入 design-assessments（type=execution_clue）
- interview-designer 增量模式读取 → 生成追加访谈问题

### 3. finding 新鲜度标记
- 当上游 artifact（程序、设计观察、证据）变更时 → finding 标记 `freshness: "stale"`
- 审计师决定是否重新评估 finding（不自动触发——finding 涉及结论，不能自动重写）
- report-generator 读取 findings 时感知 stale 标记

### 4. report 感知下游变更
- finding 新增/修改 → `artifacts["reports"].freshness = "stale"`
- report-generator 增量模式：只刷新变更的部分，不动已有章节

## 需要的统一基础设施

### artifacts 升级：从 fresh/stale 到版本号
- 当前设计：fresh | stale（二元标记）
- 实际需要：版本号 + 变更日志（`version: 2`, `changelog: ["2026-07-10 新增访谈线索 D-015"]`）
- 版本号使 stale 判断可追溯——不只在"当前是否 fresh"，还能回答"上次刷新基于哪个版本"

### 全管线可观测性
- 每个决策点记录：谁（哪个 skill）、什么时候、基于什么输入、做了什么判断
- audit_trail 当前已有基础框架（phase_gate 写入），需扩展到所有 skill 的决策点

## 存档

此文件在 interview-designer-v3 执行期间存入 memory/TODO.md #待办 区域。
