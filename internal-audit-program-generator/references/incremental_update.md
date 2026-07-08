# 增量更新模式（Incremental Update）

> 本文件定义 program-generator 的**增量更新模式**：在已有 v1.0 审计程序基础上，
> 依据后续产生的设计观察线索（design-assessments）与举报线索（whistleblower）
> 补充生成新的测试程序章节，不重写原程序。

---

## 触发条件

`phase_gate.py` 返回 `action=prompt_program_update` 时进入本模式。

其含义：审计程序已存在 v1.0，但后续阶段（Phase 1.5 访谈 / Phase 4 执行）
产生了新的待处理线索（pending clue），需要增量补充审计程序。

**与全新生成的区别**：
- 全新生成：无 v1.0，走 Step 0-5 完整流程，编号 R01/R02...
- 增量更新：有 v1.0，走本文件 Step 0-2，编号 S01/S02...，只追加不覆盖

---

## Step 0：读取现有内容

按顺序读取三类输入：

### 0.1 读取现有 v1.0 审计程序
- 定位 `internal-audit-workspace/audit-programs/` 中的现有程序文档
- 提取**已有风险编号清单**（R01-Rxx），构建"已覆盖风险集合"
- 提取现有章节结构（一至九章），确认在其后追加十、十一章

### 0.2 读取设计观察（design-assessments）
- 扫描 `internal-audit-workspace/design-assessments/*.json`
- 筛选 `design_observations[]` 中 `type="risk_clue"` 且 `status="pending"` 的条目
- 每个条目提取：`id` / `source_role` / `source_id` / `interview_snippet` / `contradiction`

### 0.3 读取举报线索（whistleblower）
- 读取 `current-audit.json` 的 `whistleblower_pending` 字段
- 提取每条举报的线索摘要、涉及环节、涉及人员/部门

---

## Step 1：线索过滤（去重 + 覆盖检查）

对 Step 0 收集的所有 pending 线索，逐条判断是否需要纳入增量程序：

### 1.1 覆盖检查
将每条线索与 v1.0 已有风险集合（R01-Rxx）比对：
- **已覆盖**（线索指向的风险点，v1.0 已有对应测试程序）→ 丢弃，不重复生成
- **未覆盖**（v1.0 无对应程序）→ 进入 Step 2 生成

### 1.2 去重
- 同一 `id` 只处理一次
- 多个线索指向同一风险点时，合并为一条（保留最完整的证据描述）

### 1.3 前置确认（强制交互）
向用户展示**待补充线索清单**，逐条确认是否纳入：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 检测到 N 条待补充线索，请逐条确认是否纳入增量程序
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] 来源：仓管员/OBS-003（访谈线索）
    内容：盘点表事后补签，与制度矛盾
    覆盖状态：v1.0 未覆盖
    纳入？(y/n)
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

用户确认 `n` 的线索不生成程序，但仍标记为 consumed（避免重复提示）。

---

## Step 2：生成增量程序章节

对 Step 1 确认纳入的线索，生成补充测试程序。

### 2.1 编号规则
- 补充编号使用 **S01/S02/S03...**，**不得**使用 R01/R02（避免与 v1.0 冲突）
- S 序列跨章节连续：访谈补充用完 S0x 后，举报补充延续编号

### 2.2 章节归属
| 线索来源 | 输出章节 | 来源标注 |
|---------|---------|---------|
| design-assessments（risk_clue） | 十、访谈补充测试程序 | 【访谈类-线索】 |
| whistleblower_pending | 十一、举报补充测试程序 | 【举报类-线索】 |

### 2.3 程序质量要求
- 每条补充程序须包含：风险名称、来源标注、线索依据、测试程序、取数来源
- 测试程序须可执行（"如果X则Y"逻辑），禁止开关型判断（是/否、有/无）
- 访谈类线索须引用 `source_role`/`source_id`/`interview_snippet`/`contradiction`
- 举报类线索须引用举报线索摘要

**输出格式**：见 [output_template.md](./output_template.md) 第十、十一章模板。

---

## 边界情况处理

| 情况 | 处理方式 |
|------|---------|
| design-assessments 目录为空 / 无 pending 线索 | **正常退出**：提示"无待补充线索，v1.0 程序保持不变"，不生成十、十一章 |
| JSON 文件格式损坏（malformed） | **跳过并记录**：跳过该文件，在 audit_trail 记录 skip 事件及文件名，继续处理其余文件 |
| 重复线索（同 id 多次出现） | **按 id 去重**：只保留一条，合并证据描述 |
| 线索标志位不一致（如 status 缺失或与 pending 矛盾） | **处理但警告**：仍纳入待确认清单，但在清单中标注 ⚠️ 提示用户人工核实 |

---

## 输出后：状态回写

增量生成完成后，更新 `current-audit.json`：

| 字段 | 更新内容 |
|------|---------|
| `design_observations_consumed` | 追加本次已处理的 design_observation id 列表 |
| `whistleblower_pending` | 已生成程序的举报线索移出 pending（标记 consumed） |
| `program_version` | 版本号递增（如 v1.0 → v1.1） |
| `program_update_history` | 追加一条更新记录（时间、新增 S 编号、来源线索 id） |

**同时**：将新增的十、十一章追加到现有 audit-programs 程序文档末尾，不覆盖一至九章。

---

## 与主流程的关系

```
phase_gate.py check
  └─ action=prompt_program_update
       └─ SKILL.md Step 6
            └─ 本文件 Step 0 → Step 1 → Step 2 → 状态回写
                 └─ 输出：十、访谈补充 + 十一、举报补充
```
