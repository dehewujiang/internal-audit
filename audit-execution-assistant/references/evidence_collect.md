# 证据收集与匹配（Step 1 / Step 0.1）

> SKILL.md Step 1 与 Step 2（0 / 0.1）的完整细节。正文只留路牌，干活时读这里。

### Step 1：程序执行引导

对每个审计程序，引导用户提供所需证据。

**默认动作（catalog 检查）**：读取 catalog 前，先运行结构校验（R05 闸机）：
```bash
python _shared/scripts/validate-catalog.py evidence/_evidence_catalog.json --strict
```
- action=block → 提示用户 catalog 损坏（结构/计数不一致），修复后再继续，禁止在损坏状态下误判证据缺失或放行不完整证据
- action=pass/warn → 继续。然后读取 `evidence/_evidence_catalog.json`，按当前程序编号（如 A1.1）在槽位的 `source_programs` 中定位本程序证据槽位，展示收集状态（✅已收集 / ❌缺失）。证据到达后默认运行 `python _shared/scripts/evidence_catalog.py match <workspace>` 并展示匹配状态表（详见 Step 2.0.1）。

**证据存放路径规则（v2.0 集中存储）**：

```
evidence/
├── _files/                      ← 所有证据集中存放（只放一份，不按程序分目录）
└── _evidence_catalog.json       ← 证据清单（Phase 2 账表生成时兼容导出）
```

**关键变化（v2.0）**：
- 所有证据文件只放一份到 `evidence/_files/`，不再复制到每个程序目录，也不按程序建立子目录
- 引用关系记录在账上 `evidence_slots` 表的 `source_programs` 字段（兼容导出 `_evidence_catalog.json`）
- 证据槽位由 `ledger.py init-evidence-slots` 从程序 Markdown 的"取证方式"列自动生成（解析与 validate-program 同源）

**Step 1 执行时的证据状态展示**：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 程序 A1.1：考勤数据手工传递篡改
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

需要的证据（来自 catalog）：
  ✅ 打卡系统导出文件        → _files/考勤原始记录_2026.xlsx
  ✅ 人事科考勤汇总表          → _files/人事科考勤汇总表_2026.xlsx
  ❌ 考勤调整单                → 未收集

⚠️ 缺失 1 项证据。输入"跳过"继续，或补充后重新载入。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 程序 [N/总数]：[程序名称]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 目标：[程序目标]
📊 需要的证据：
  1. [证据1]
  2. [证据2]
📁 取数来源：[系统/文件]
📂 证据存放路径：
  evidence/_files/

  请将导出的原始证据文件放入 evidence/_files/ 目录，完成后告诉我。

⚠️ 注意事项：[如有]

操作选项：
- "完成" → 我去读取 evidence 目录中的文件
- "跳过" → 进入下一程序
- "替代" → 这个证据拿不到，帮我换个方法
- "新增" → 执行中发现新风险，补充一个程序
- "删除" → 这个程序不适用，删掉
- "帮助" → 说明如何获取该证据
- "路径" → 我重新显示证据存放路径
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 0.1：证据匹配与收集（默认执行，无需用户显式触发）

前提：Phase 2 已生成 `_evidence_catalog.json`（所有槽位的 `file` 初始为 `null`），
用户已将收集到的文件放入 `_files/` 目录。

**默认流程**：每个程序执行前先按当前程序编号（如 A1.1）在 catalog 槽位的 `source_programs` 中定位本程序证据槽位，展示收集状态（✅已收集 / ❌缺失）。证据到达 `_files/` 后默认运行以下匹配流程：

```
Step 0.1a — Python 扫描文件结构指纹：
  python _shared/scripts/evidence_catalog.py scan <workspace>
  → 获取每个文件的名称、类型、列名（Excel/CSV）、行数

Step 0.1b — Python 初步匹配：
  python _shared/scripts/evidence_catalog.py match <workspace>
  → 文件名关键词 + 列名匹配，输出初步匹配建议

Step 0.1c — LLM 综合判断 + 用户确认（展示全量状态表）：
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📋 证据收集状态总览
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅ 已匹配（N/TOTAL）
  | 槽位 | 证据名称 | 匹配文件 | 关联程序 | 置信度 |
  | EVD-003 | Excel工资表 | 2025年薪资数据.xlsx | A5.1,B5.1,... | 高 |

  ❌ 缺失（M/TOTAL）
  | 槽位 | 证据名称 | 关联程序 | 取数来源 |
  | EVD-025 | 考勤调整单 | A1.1 | 管理部 |

  ⚠️ 未匹配文件
  | 文件名 | 最可能槽位 | 操作 |
  | 临时截图.png | — | [指定槽位] [移除] |
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**未匹配文件的处理**：
- 手动指定到已有槽位 → 调用 `evidence_catalog.py update --slot <id> --file <path>`
- 在 catalog 中新增槽位 → 追加到 items 数组并保存
- 误放的文件 → 从 `_files/` 移除

**确认后**：LLM 调用 `evidence_catalog.py update` 逐条写回 catalog，填充 `file` 字段。
