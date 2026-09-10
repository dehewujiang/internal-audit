# 内部审计共享配置

本文件为内部审计平台的共享运行配置。所有基于此框架的审计项目共用此文件。
项目级 CLAUDE.md 只包含项目特有配置。

## 工具清单

以下工具注册在中央大脑调度范围内：

| 工具名 | 能力 | 授权级别 | 能力声明位置 |
|--------|------|---------|-------------|
| document-organizer | 分析制度文件，提取控制点和风险点 | level_0 | `skills/internal-audit/document-organizer/SKILL.md` |
| audit-interview-designer | 基于设计观察生成访谈问卷并回填结果 | level_0 | `skills/internal-audit/audit-interview-designer/SKILL.md` |
| program-generator | 基于审计目的和风险生成审计程序 | level_0 | `skills/internal-audit/internal-audit-program-generator/SKILL.md` |
| execution-assistant | 执行程序、分析证据、生成 finding | level_0 | `skills/internal-audit/audit-execution-assistant/SKILL.md` |
| finding-debate | 对 finding 进行业务审视和攻防演练 | level_1 | `skills/internal-audit/audit-finding-debate/SKILL.md` |
| report-generator | 汇总 finding 生成结构化审计报告 | level_0 | `skills/internal-audit/internal-audit-report-generator/SKILL.md` |
| validate-finding | finding 格式+根因+证据等级校验 | level_0 | `skills/internal-audit/_shared/scripts/validate-finding.py` |
| data-executor | LLM 生成的 pandas 代码沙箱执行（大文件分析） | level_0 | `skills/internal-audit/_shared/scripts/data_executor.py` |
| audit-gate | LLM 推理前后的硬闸机（precheck/postcheck） | level_0 | `skills/internal-audit/_shared/scripts/audit_gate.py` |
| mandatory-check | constitution #10 制度完整性检查 | level_0 | `skills/internal-audit/_shared/scripts/check_mandatory_coverage.py` |
| evidence-catalog | 证据清单管理（生成槽位/扫描文件/匹配建议/状态汇总） | level_0 | `skills/internal-audit/_shared/scripts/evidence_catalog.py` |
| validate-catalog | 证据清单结构校验（槽位必填/唯一性/计数一致性，R05） | level_0 | `skills/internal-audit/_shared/scripts/validate-catalog.py` |
| validate-index | finding 索引交叉校验（目录vs索引遗漏/幽灵/闭合，R06） | level_0 | `skills/internal-audit/_shared/scripts/validate-index.py` |
| ledger-keeper | 新桌子管家：开桌/写格/贴证据/对单号/老账搬家（只管写） | level_0 | `skills/internal-audit/ledger/ledger.py` |
| ledger-gate | 新桌子日常门卫：只读桌子查大事+高风险硬度 | level_0 | `skills/internal-audit/ledger/check.py` |
| ledger-checklist | 新桌子打勾纸：六句话看板，只看不拦 | level_0 | `skills/internal-audit/ledger/checklist.py` |
| ledger-audit | 报告前桌子闸机：单缺位/鬼号/红格无单号拦下 | level_0 | `skills/internal-audit/ledger/audit_table.py` |
| ledger-export | 桌子总览表格：左边/证据/抽屉三页（签字存档） | level_0 | `skills/internal-audit/ledger/export.py` |

## 关键文件

- `audit-topics/about-me.md` — 公司背景
- `audit-topics/my-config.md` — 系统配置
- `constitution.md` — 中央大脑运行宪法（项目目录中的 constitution.md 指向此全局定义或为副本）
- `internal-audit-workspace/evidence/_evidence_catalog.json` — 证据清单（v2.0 集中存储，记录证据-程序映射和收集状态）
- `internal-audit-workspace/evidence/_files/` — 共享证据集中存放目录（v2.0）

## 全局工作规则

- 所有输出写入 `internal-audit-workspace/` 对应目录
- JSON 文件必须包含 `schema_version` 字段
- 生成 finding 前必须通过证据完整性校验
- 涉及舞弊的 finding 必须标记为高风险
- 写入 JSON 后立即运行 `validate-json.py` 验证
