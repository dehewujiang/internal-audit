# 技术上下文
更新时间：2026-07-22

## 核心模块关系

```
internal-audit/
├── CLAUDE.md                 ← 开发版（含 architecture gotchas, rules loading）
├── CLAUDE-project.md         ← 运行版（精简，setup-project.ps1 拷贝为审计项目 CLAUDE.md）
├── constitution.md           ← 10 条全局硬约束
├── setup-project.ps1         ← 一键部署：扫描 .claude/skills/ 自动发现技能
├── update-project.ps1        ← 增量升级：逐技能合并而非整目录覆盖
├── .claude/
│   ├── skills/               ← 12 个技能（2 geb-* + 10 个审计 junction）
│   ├── settings.json         ← extraRules 配置
│   └── rules/                ← junction → D:\Nut\00_my_digital\12_AGI\rules\
├── _shared/scripts/          ← 核心脚本（phase_gate + 5 validate-* + queries + data_executor + audit_gate + check_mandatory_coverage + project_init）
├── tools/                    ← pdf_ocr_extractor.py（PaddleOCR）+ 13 个能力声明
├── audit-topics/             ← 审计主题模板（人力资源管理、存货管理）
├── tests/prompt_snapshots/   ← 5 个 prompt 快照 + 回归测试指南
├── [10 个 skill 目录]/        ← 各含 SKILL.md + references/
└── memory/                   ← 项目记忆（本目录）
```

## 技能注册架构（2026-07-14 修复）

- **唯一来源**：`.claude/skills/` — 仓库根目录的 10 个审计技能通过 junction 映射于此
- **部署一致性**：setup 和 update 都从 `.claude/skills/` 读取技能列表
- **setup**：扫描 `.claude/skills/` 自动发现 → deployment
- **update stable**：逐技能合并而非整目录覆盖（不再丢失审计技能）

## 三重闸机体系（2026-07-22 扩展到四层）

```
流程闸机:  phase_gate check/advance          → exit 0/1/2（阶段转换）
质量闸机:  validate-*.py                      → exit 0/1（产物校验）
授权闸机:  phase_gate tool-check <script>     → exit 0/1（工具分域）
调度闸机:  audit_gate precheck/postcheck       → exit 0/1（LLM 推理前后硬闸机）
```

## 10 个 Skill 流水线（+ 2 evaluators + 1 新脚本）

```
project-init / topic-wizard  (Phase 0)
document-organizer           (Phase 1 → policy-analyses/ + design-assessments/)
audit-interview-designer     (Phase 1.5 → interview-materials/)
program-generator            (Phase 2-3 → audit-programs/)
execution-assistant          (Phase 3 → findings/)    ← 新增 data_executor.py 集成
finding-debate               (Phase 3.5, 可选)
report-generator             (Phase 4 → reports/)
evaluator (*): quality_gate + record_evaluation
program-quality-evaluator: 四层评估
check_mandatory_coverage.py: constitution #10 制度完整性检查（新增）
```

## 新架构组件（2026-07-22 新增）

| 组件 | 文件 | 功能 |
|------|------|------|
| 数据执行引擎 | `_shared/scripts/data_executor.py` | LLM 生成的 pandas 代码沙箱执行，8 个预制分析工具 |
| 调度闸机 | `_shared/scripts/audit_gate.py` | LLM 推理前后硬闸机（precheck/postcheck/status） |
| mandatory 检查 | `_shared/scripts/check_mandatory_coverage.py` | constitution #10 制度完整性检查 |
| Prompt 快照 | `tests/prompt_snapshots/` | 5 关键 prompt 版本快照 + 回归测试指南 |
| OCR 升级 | `tools/pdf_ocr_extractor.py` | EasyOCR → PaddleOCR（中文识别率 50-60% → 75-85%） |

## 关键技术约束
- 状态传递：全部通过文件系统，不通过内存
- 工具分域：每个 Python 脚本调用前必须过 phase_gate tool-check
- finding schema：已从旧 schema（finding_title/finding_metadata/risk_classification）统一到 schema 1.2.0（title/risk_level/origin/evidence[]）。validate-finding.py 已同步
- 证据等级：A-E 五级，高风险 finding 必须 A 或 E
- 部署：setup-project.ps1 一键初始化审计项目
- data_executor 安全：import 白名单（仅 pandas/numpy）+ threading.Timer 跨平台超时

## 当前活跃风险（2026-07-22）
1. ✅ ~~schedule 校验与 data 脱节~~ — P0-5 已修复，validate-finding.py 重写
2. ✅ ~~constitution #10 无执行代码~~ — check_mandatory_coverage.py 已实现
3. ✅ ~~新模块未入白名单~~ — data_executor/audit_gate 已加入 GLOBAL_TOOLS
4. ✅ ~~社保判定标准错误~~ — F3.2 已修正为社平工资 60%
5. ✅ ~~项目自动注册缺失~~ — project-init Step 4.6 已实现
6. 🟡 存货管理 topic.json 仍缺 reference_framework — 已补（2026-07-22）
7. 🟡 PaddleOCR 安装中 — 后台下载中

## 已部署项目
| ID | 项目 | 主题 | 阶段 |
|:---:|------|------|------|
| P-2026-001 | 武汉长源 | 人力资源管理 | phase_3_execution |
| P-2026-002 | 广东长华 | 人力资源管理 | phase_2_program_generation |

## 用户长期目标
Flan 从"操作员"变成"审核员"——系统自己管流程，他只做关键决策。
