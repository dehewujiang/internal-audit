---
name: project-init
description: 一键创建新审计项目目录和配置文件。自动创建 internal-audit-workspace/ 目录结构、current-audit.json（含 audit_state）、CLAUDE.md、constitution.md。
---

# 审计项目初始化器

## 核心原则

**零代码复制。一句话创建审计项目。**

用户只需指定审计主题名称，系统自动：
1. 查找全局主题配置（`D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/{topic}/`）
2. 创建项目目录结构
3. 生成 `current-audit.json`
4. 生成精简 `CLAUDE.md`

---

## Step 1：获取审计主题

### 1.1 从用户输入提取主题

若用户明确指定主题（如"创建存货管理审计项目"），直接提取。

### 1.2 主题未明确时询问

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 请输入审计主题名称
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

示例：存货管理、采购付款、销售收款、固定资产、费用报销

已配置的主题：
   - 存货管理

请输入主题名称（或输入"新建"启动 topic-wizard）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 2：验证主题配置存在

### 2.1 检查主题目录

```bash
检查路径：
  D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/
  ├── about-me.md        （公司级，所有主题共用，必须存在）
  ├── my-config.md       （公司级，所有主题共用，必须存在）
  └── {topic}/
      └── topic.json     （主题特有默认值，必须存在）
```

### 2.2 缺失时处理

| 缺失文件 | 处理方式 |
|---------|---------|
| 整个目录不存在 | 提示："主题 '{topic}' 尚未配置。请先运行 topic-wizard 创建主题配置。" |
| 仅缺 topic.json | 自动从模板生成 |
| 仅缺 about-me.md | 提示用户创建（内容重要，不能自动生成） |
| 仅缺 my-config.md | 提示用户创建（内容重要，不能自动生成） |

---

### Step 2.5：安全检查（强制）

在创建任何文件之前，运行：

```bash
python _shared/scripts/project_init.py --workspace <workspace_path> --skills-dir <skills_dir>
```

若 exit code != 0 → 展示错误信息给用户，停止创建。用户修正后重试。
若 exit code = 0 → 继续 Step 3。

---

## Step 3：确认项目位置

### 3.1 默认位置

若用户在空目录或非项目目录中，在当前目录（CWD）创建。

### 3.2 已存在项目时

若 CWD 已包含 `internal-audit-workspace/current-audit.json`：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 当前目录已是审计项目

项目：{project_name}
主题：{audit_topic}
状态：{status}

是否创建新项目？
A) 在当前目录的子目录中创建（输入子目录名）
B) 覆盖现有项目（⚠️ 会丢失 workspace 数据）
C) 取消

请选择：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 3.3 用户指定路径

支持用户指定项目路径，如"在 D:\audit\存货管理2026\ 创建项目"。

---

## Step 4：创建项目结构

### 4.1 读取主题配置

从 `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/{topic}/topic.json` 读取：
- `topic_name`
- `topic_description`
- `audit_defaults`（focus, warehouses, processes, departments, risk_areas）
- `typical_documents`

### 4.2 创建目录

```
{project_dir}/
├── CLAUDE.md                      ← 精简版（指向全局工具）
├── internal-audit-workspace/
│   ├── current-audit.json         ← 项目状态 + 审计状态
│   ├── tools/                     ← 工具能力声明（从全局 tools/ 复制）
│   ├── documents/                 # 待分析的源文档（用户放入）
│   ├── policy-analyses/           # Phase 1 输出
│   ├── design-assessments/        # Phase 2 输出
│   ├── interview-materials/       # Phase 1.5 输出
│   ├── audit-programs/            # Phase 3 输出
│   ├── findings/                  # Phase 4 输出
│   ├── evidence/                  # Phase 4 证据存放（执行时由用户放入）
│   ├── debates/                   # Phase 4.5 输出
│   └── reports/                   # Phase 5 输出
```

### 4.3 生成 current-audit.json（schema 1.1，含 audit_state）

```json
{
  "schema_version": "1.1",
  "audit_topic": "{topic}",
  "project_id": "AU_{topic}_{date}",
  "project_name": "{topic}审计_{year}年度",
  "audit_period": {
    "start_date": "{当前年份}-01-01",
    "end_date": "{当前年份}-12-31"
  },
  "audit_focus": [来自 topic.json],
  "scope": {
    "warehouses": [来自 topic.json],
    "processes": [来自 topic.json],
    "departments": [来自 topic.json]
  },
  "risk_areas": [来自 topic.json],
  "document_list": [来自 topic.json],
  "status": "phase_1_document_analysis",
  "created_at": "{今天日期}",
  "updated_at": "{今天日期}",
  "audit_state": {
    "known_facts": {"company": "", "systems": "", "risk_areas": []},
    "evidence_pool": [],
    "programs": {"initial_list": [], "current_priority": [], "completed": [], "pending": [], "deferred": [], "added": []},
    "findings": {"draft": [], "confirmed": [], "rejected": []},
    "signals": [], "uncertainties": [], "backlog": [], "scope_changes": [],
    "summary": {"last_updated": "", "programs": "", "findings": "", "signals": "", "evidence": "", "pending_decisions": ""},
    "audit_trail": [],
    "current_focus": "",
    "audit_purpose": "",
    "report_type": "",
    "program_version": "v1.0",
    "design_observations_consumed": true,
    "whistleblower_pending": false,
    "program_update_history": []
  }
}
```

### 4.4 生成 CLAUDE.md

生成精简版 CLAUDE.md（~30行），仅包含：
- 角色定义（默认 Flan 审计专家）
- 运行宪法引用（constitution.md）
- 可用工具列表（引用 tools/ 目录）
- 当前项目信息（主题、编号、状态）
- 关键文件路径
- 核心规则

**不包含**：
- 触发词表（中央大脑自动决策，不需要）
- 五阶段工作流（中央大脑状态驱动，不需要）
- Excel 工具说明（全局管理）
- 详细规则说明（由宪法定义）

### 4.5 创建 tools/

- 将 `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/tools/*.md`（工具能力声明）复制到项目 `internal-audit-workspace/tools/`。
  ⚠️ 复制全部 13 个能力声明文件，忽略 tools/ 中的非能力说明文件（pdf_ocr_extractor.py、PDF_OCR_README.md）：document-organizer.md、execution-assistant.md、finding-debate.md、interview-designer.md、phase_gate.md、program-generator.md、program-quality-evaluator.md、queries.md、report-generator.md、validate-finding.md、validate-policy-analysis.md、validate-program.md、validate-report.md

> ⚠️ `constitution.md` 不复制到 workspace。setup-project.ps1 已经在项目根目录放置了宪法（与 CLAUDE.md 同级），workspace 是审计产物目录，不需要再放一份。

### 4.6 自动注册到跨项目索引

项目创建完成后，自动注册到 `projects-index.json`，使跨项目查询立即可用：

```bash
python _shared/scripts/queries.py register --path <project_dir> --topic <topic> --period <period>
```

- `<project_dir>`：Step 3 确认的项目目录绝对路径
- `<topic>`：审计主题名（与 current-audit.json 中的 `audit_topic` 一致）
- `<period>`：从 `audit_period` 提取，格式 `YYYY`（如 `2026`）。若 `audit_period` 为对象 `{start_date, end_date}`，取 `start_date` 前 4 位年份。

若注册命令失败（exit ≠ 0）：**不阻断项目创建**，显示警告 `⚠️ 跨项目索引注册失败，可稍后手动运行 queries.py register --path <project_dir>`，继续 Step 5。

---

## Step 5：确认输出

```
✅ 审计项目已创建

路径：{project_dir}
主题：{topic_name}
状态：phase_1_document_analysis

已创建：
✓ tools/（13个工具能力声明，存放于 internal-audit-workspace/tools/）
✓ internal-audit-workspace/current-audit.json（含 audit_state）
✓ internal-audit-workspace/documents/
✓ internal-audit-workspace/policy-analyses/
✓ internal-audit-workspace/design-assessments/
✓ internal-audit-workspace/interview-materials/
✓ internal-audit-workspace/audit-programs/
✓ internal-audit-workspace/findings/
✓ internal-audit-workspace/evidence/
✓ internal-audit-workspace/debates/
✓ internal-audit-workspace/reports/
✓ CLAUDE.md（项目根目录，setup-project.ps1 已创建）
✓ constitution.md（项目根目录，setup-project.ps1 已创建）
{auto_register_result}

下一步：
1. 将制度文档放入 internal-audit-workspace/documents/
2. 输入"分析制度"开始
```

---

## 禁止事项

- ❌ 禁止跳过主题配置验证
- ❌ 禁止在主题目录不存在时自动创建（必须引导用户走 topic-wizard）
- ❌ 禁止覆盖已有项目而不警告
- ❌ 禁止自动生成 about-me.md 或 my-config.md（内容须用户手动填写）
- ❌ 禁止在 CLAUDE.md 中硬编码项目特有路径
