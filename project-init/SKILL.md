---
name: project-init
description: 一键创建新审计项目目录和配置文件。自动创建 internal-audit-workspace/ 目录结构、current-audit.json（含 audit_state）、CLAUDE.md、constitution.md。
---

# 审计项目初始化器

## 核心原则

**零代码复制。一句话创建审计项目。**

用户只需指定审计主题名称，系统自动：
1. 查找全局主题配置（`~/.claude/skills/internal-audit/audit-topics/{topic}/`）
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
  ~/.claude/skills/internal-audit/audit-topics/
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

从 `~/.claude/skills/internal-audit/audit-topics/{topic}/topic.json` 读取：
- `topic_name`
- `topic_description`
- `audit_defaults`（focus, warehouses, processes, departments, risk_areas）
- `typical_documents`

### 4.2 创建目录

```
{project_dir}/
├── CLAUDE.md                      ← 精简版（指向全局工具）
├── internal-audit-workspace/
│   ├── constitution.md            ← 中央大脑宪法（从全局复制或引用）
│   ├── current-audit.json         ← 项目状态 + 审计状态
│   ├── tools/                     ← 工具能力声明（从全局 tools/ 复制）
│   ├── documents/                 # 待分析的源文档（用户放入）
│   ├── policy-analyses/           # Phase 1 输出
│   ├── design-assessments/        # Phase 2 输出
│   ├── interview-materials/       # Phase 1.5 输出
│   ├── audit-programs/            # Phase 3 输出
│   ├── findings/                  # Phase 4 输出
│   ├── debates/                   # Phase 4.5 输出
│   └── reports/                   # Phase 5 输出
```

### 4.3 生成 current-audit.json（schema 1.1，含 audit_state）

```json
{
  "schema_version": "1.1",
  "audit_topic": "{topic}",
  "project_id": "AU_{topic}_{date}",
  "project_name": "{project_dir_name}",
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
    "audit_purpose": "",
    "report_type": "",
    "design_observations_consumed": false,
    "evidence_pool": [],
    "programs": {"initial_list": [], "current_priority": [], "completed": [], "pending": [], "deferred": [], "added": []},
    "findings": {"draft": [], "confirmed": [], "rejected": []},
    "signals": [], "uncertainties": [], "backlog": [], "scope_changes": [],
    "summary": {"last_updated": "", "programs": "", "findings": "", "signals": "", "evidence": "", "pending_decisions": ""},
    "audit_trail": [],
    "current_focus": ""
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

### 4.5 创建 constitution.md 和 tools/

- 将 `~/.claude/skills/internal-audit/constitution.md`（全局共享宪法）复制到项目 `internal-audit-workspace/constitution.md`。如全局宪法尚不存在，先生成初始版本再复制。
- 将 `~/.claude/skills/internal-audit/tools/*.md`（工具能力声明）复制到项目 `internal-audit-workspace/tools/`。
  ⚠️ 只复制以下 7 个能力声明文件，忽略全局 tools/ 中的其他文件：document-organizer.md、interview-designer.md、program-generator.md、execution-assistant.md、finding-debate.md、report-generator.md、validate-finding.md

### 4.6 注册到项目索引

项目创建完成后，自动执行注册命令将项目登记到 `audit-topics/projects-index.json`：

```bash
python _shared/scripts/queries.py register --path "{project_dir}" \
  --topic "{topic_name}" --period "{audit_period}"
```

注册信息用于跨项目数据查询、未来一键批量升级和历史项目统计。

⚠️ 注册失败不阻断创建流程。若失败，在 Step 5 输出末尾增加提示：
```
📌 跨项目索引注册失败（不影响当前项目使用）
   可稍后手动注册：
   python queries.py register --path <项目目录> --topic <主题> --period <期间>
```

---

## Step 5：确认输出

```
✅ 审计项目已创建

路径：{project_dir}
主题：{topic_name}
状态：phase_1_document_analysis

已创建：
✓ constitution.md（中央大脑运行宪法）
✓ tools/（7个工具能力声明）
✓ internal-audit-workspace/current-audit.json（含 audit_state）
✓ internal-audit-workspace/documents/
✓ internal-audit-workspace/policy-analyses/
✓ internal-audit-workspace/design-assessments/
✓ internal-audit-workspace/interview-materials/
✓ internal-audit-workspace/audit-programs/
✓ internal-audit-workspace/findings/
✓ internal-audit-workspace/debates/
✓ internal-audit-workspace/reports/
✓ CLAUDE.md

下一步：
1. 将制度文档放入 internal-audit-workspace/documents/
2. 输入"分析制度"开始

> 若注册失败，此处额外输出：
> 📌 跨项目索引注册失败（不影响当前项目使用）
>    可稍后手动注册：python queries.py register --path <项目目录> --topic <主题> --period <期间>
```

---

## 禁止事项

- ❌ 禁止跳过主题配置验证
- ❌ 禁止在主题目录不存在时自动创建（必须引导用户走 topic-wizard）
- ❌ 禁止覆盖已有项目而不警告
- ❌ 禁止自动生成 about-me.md 或 my-config.md（内容须用户手动填写）
- ❌ 禁止在 CLAUDE.md 中硬编码项目特有路径
- ❌ `project_name` 必须等于项目文件夹名称，禁止自由命名。例：文件夹 `AU_PL_260601_人力资源_武汉长源` → `project_name: "AU_PL_260601_人力资源_武汉长源"`
