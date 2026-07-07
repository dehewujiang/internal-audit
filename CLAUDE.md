# 内部审计共享配置

本文件为内部审计平台的共享运行配置。所有基于此框架的审计项目共用此文件。
项目级 CLAUDE.md 只包含项目特有配置。

## 工具清单

以下工具注册在中央大脑调度范围内：

| 工具名 | 能力 | 授权级别 | 能力声明位置 | 适用阶段 |
|--------|------|---------|-------------|---------|
| document-organizer | 分析制度文件，提取控制点和风险点 | level_0 | `skills/internal-audit/document-organizer/SKILL.md` | Phase 1 |
| audit-interview-designer | 基于设计观察生成访谈问卷并回填结果 | level_0 | `skills/internal-audit/audit-interview-designer/SKILL.md` | Phase 1-4 |
| program-generator | 基于审计目的和风险生成审计程序 | level_0 | `skills/internal-audit/internal-audit-program-generator/SKILL.md` | Phase 2-3 |
| execution-assistant | 执行程序、分析证据、生成 finding | level_0 | `skills/internal-audit/audit-execution-assistant/SKILL.md` | Phase 4-5 |
| finding-debate | 对 finding 进行业务审视和攻防演练 | level_1 | `skills/internal-audit/audit-finding-debate/SKILL.md` | Phase 4-5 |
| report-generator | 汇总 finding 生成结构化审计报告 | level_0 | `skills/internal-audit/internal-audit-report-generator/SKILL.md` | Phase 5 |
| queries | 审计数据查询（findings 筛选/统计/趋势/对比） | level_0 | `skills/internal-audit/_shared/scripts/queries.py` | 全阶段 |
| program-quality-evaluator | 独立评估审计程序实质质量（覆盖度/检测力/可执行性） | level_0 | `skills/internal-audit/program-quality-evaluator/SKILL.md` | Phase 2-3 |
| validate-finding | 对 finding 做确定性质量校验 | level_0 | `skills/internal-audit/_shared/scripts/validate-finding.py` | Phase 4-5 |
| validate-program | 对审计程序做格式/结构硬校验 | level_0 | `skills/internal-audit/_shared/scripts/validate-program.py` | Phase 2-3 |
| validate-policy-analysis | 对制度分析 JSON 做结构硬校验 | level_0 | `skills/internal-audit/_shared/scripts/validate-policy-analysis.py` | Phase 1 |
| validate-report | 对审计报告做格式/结构硬校验 | level_0 | `skills/internal-audit/_shared/scripts/validate-report.py` | Phase 5 |
| phase_gate | 阶段状态机：检查退出条件、执行前进/回退 | level_0 | `skills/internal-audit/_shared/scripts/phase_gate.py` | 全阶段 |

## 阶段流转（地铁闸机）

**阶段顺序**：`phase_0_init → phase_1 → phase_1_5 → phase_2 → phase_3 → phase_4`

**进入下一阶段前**：运行 `python phase_gate.py check`，action=pass 才前进，action=block 列出缺失项等用户决定。

**回退**：必须用户确认，运行 `python phase_gate.py rollback --to <phase> --reason "<原因>"`。

**工具分域规则**（constitution.md 详细说明）：
| 工具 | Phase 1 | Phase 1.5 | Phase 2-3 | Phase 4 | Phase 5 |
|------|:--:|:--:|:--:|:--:|:--:|
| document-organizer | ✅ | ✅ | ❌ | ❌ | ❌ |
| interview-designer | ✅ | ✅ | ✅ | ✅ | ❌ |
| program-generator | ❌ | ❌ | ✅ | ❌ | ❌ |
| execution-assistant | ❌ | ❌ | ❌ | ✅ | ✅ |
| finding-debate | ❌ | ❌ | ❌ | ✅ | ✅ |
| report-generator | ❌ | ❌ | ❌ | ❌ | ✅ |
| phase_gate | ✅ | ✅ | ✅ | ✅ | ✅ |
| evaluator/queries | ✅ | ✅ | ✅ | ✅ | ✅ |

## 关键文件

- `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/about-me.md` — 公司背景
- `D:/Nut/00_my_digital/12_AGI/skills/internal-audit/audit-topics/my-config.md` — 系统配置
- `constitution.md` — 中央大脑运行宪法（项目目录中的 constitution.md 指向此全局定义或为副本）

## 全局工作规则

- 所有输出写入 `internal-audit-workspace/` 对应目录
- JSON 文件必须包含 `schema_version` 字段
- 生成 finding 前必须通过证据完整性校验
- 涉及舞弊的 finding 必须标记为高风险
- 写入 JSON 后立即运行 `validate-json.py` 验证

## 全局编码与文档规则

本项目的 `.claude/rules/` 通过目录链接（junction）指向 `D:/Nut/00_my_digital/12_AGI/rules/`，与母仓库共享同一套规则。规则按路径自动加载：

| 规则文件 | 触发路径 | 核心约束 |
|---------|---------|---------|
| `coding-safety.md` | `**/*.{py,js,ts,go,html,css}` | 删文件要确认、改前评估影响、改后必须验证 |
| `good-taste.md` | 同上 | 消除分支、函数短小（≤30行）、数据结构优先 |
| `geb-l3.md` | 同上 | 文件头部 INPUT/OUTPUT/POS 注释契约 |
| `compat.md` | `**/api/**`, `**/interface/**`, `**/public/**` | 公开接口不可破坏 |
| `project-doctrine.md` | 全局（通过 settings.json 注入） | GEB 分形文档协议，代码=文档 |
| `memory_rules.md` | 全局（通过 settings.json 注入） | 记忆系统三筛法、启动/结束协议 |

**对 internal-audit 项目的特殊说明**：

- 本项目的 SKILL.md 是给 LLM 看的 prompt，不是传统代码——`good-taste.md` 的"函数≤30行"不适用于 SKILL.md 文件
- `_shared/scripts/*.py` 走全部编码规则（安全、品味、L3 头部）
- `compat.md` 保护 `_shared/scripts/` 中的公开脚本接口
- 新增 Python 脚本时必须添加 L3 头部
