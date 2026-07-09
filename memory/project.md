# internal-audit 项目

## 项目是什么
AI 驱动的内部审计辅助流水线，帮 Flan（汽车零部件企业审计经理）覆盖从制度分析到报告生成的全过程。

## 当前状态
✅ **控制流闸机加固完成（2026-07-08）**。phase_gate 新增 7 个检查条件 + prompt_program_update action，全部 5 个 validate 脚本接入 --strict 写入前阻断，project_init.py 硬安全检查，program-generator 支持增量更新模式。全系统 16 项 P0+P1 改动全部就位。

## 已完成功能
- 8 个 skill 各自可以独立运作（document-organizer、interview-designer、program-generator、execution-assistant、finding-debate、report-generator、project-init、topic-wizard）
- evaluator 质量评估框架（各 skill Step 5 引用）
- 母仓库 rules/ 通过 junction 链接到本项目 `.claude/rules/`
- Memory 系统就绪
- **phase_gate**: 阶段状态机 + 7 新检查（audit_purpose/about-me/report_type/findings/访谈线索/举报/OCR）
- **5 个 validate 脚本** + --strict 写入前阻断
- **project_init.py**: 覆盖检测 + 配置检测
- **program-generator 增量更新**: 访谈回写/举报材料 → 程序 v1.1+ 补充章节
- **queries.py**: 独立查询工具
- **program-quality-evaluator**: 四层评估体系
- **RP/CF 编号跨引用**: 来源标注支持全部四类 ID
- **constitution.md**: 闸机规则新增 prompt_program_update 处理条款
- **3 个 SKILL.md**: MANDATORY_OUTPUT/GATE 强制标记
- **report-generator 重构**: 强制 queries.py 列出 findings
- **document-organizer**: OCR 检测 + verification 状态机
- **interview-designer**: 回写时设置 design_observations_consumed flag
- **document-organizer 行业基准表重写（2026-07-09）**：15域控制维度清单 + 两遍法分析模式

## 正在开发
- （无）

## 已知缺口（非阻塞）
| 缺口 | 说明 |
|------|------|
| finding-debate 缺 Step 5 | 已有 MANDATORY_GATE 标记，但无 validate 引用 |
| interview-designer 缺校验脚本 | 无对应的 validate-interview.py |

## 最大风险
🟢 无阻塞级风险。主要风险已通过闸机加固消除。剩余为 SKILL.md 软提示的 LLM 遵从性问题（非代码级）。

## 下一步
1. 跑一次端到端测试验证两遍法的实际效果

## 系统结构
- 核心仓库：`D:\Nut\00_my_digital\12_AGI\skills\internal-audit\`
- 规则来源：`.claude/rules/` → 通过 junction 链接 `D:\Nut\00_my_digital\12_AGI\rules\`
- 公司背景：`audit-topics/about-me.md` + `audit-topics/my-config.md`
- 工具脚本：`_shared/scripts/`（validate-finding.py, validate-program.py, validate-policy-analysis.py, validate-report.py, phase_gate.py, queries.py）
- 程序质量评估：`program-quality-evaluator/SKILL.md`
- 审计项目：每个审计主题独立目录，输出到 `internal-audit-workspace/`

## 相关决策
见 decisions.md
