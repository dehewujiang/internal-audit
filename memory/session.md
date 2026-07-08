# 最近一次工作记录

## 完成了什么
本次 session 实施了 **控制流闸机加固**（audit-control-flow-hardening），P0+P1 全覆盖，6 次提交，20 个文件。

**前置修复（Wave 0）**：
- phase_gate.py --skills-dir CLI + audit_purpose 三层回退迁移（已存在，无需改）
- validate-finding.py FIND- 前缀修正（已修过，无需改）
- constitution.md 新增 prompt_program_update 闸机规则

**基础层（Wave 1）**：
- phase_gate.py 重构：check_exit_conditions 返回 issues list，新增 4 个检查（audit_purpose/about-me/访谈线索/举报/report_type）
- 当前 audit.json schema 扩展：6 个新字段
- validate-finding/validate-report/validate-program 三个脚本加入 --strict 写入前阻断

**功能层（Wave 2）**：
- program-generator：增量更新模式（读 design-assessments，生成 v1.1 补充章节）
- project_init.py：硬安全检查（覆盖检测 + 配置检测）
- execution-assistant：未消费线索提醒 + MANDATORY_OUTPUT 标记
- finding-debate：MANDATORY_GATE 标记
- report-generator：强制 queries.py 列出 findings
- validate-policy-analysis：OCR 检测
- document-organizer：verification 状态机规则
- interview-designer：回写时设置 design_observations_consumed

**交付层（Wave 3）**：
- 4 个原子提交 + 1 个 boulder 清理提交
- memory 文件全面更新

## 为什么这样做
系统审计发现全系统 28 个用户提示点中有 11 个依赖 LLM 自觉执行，遗忘即灾难。用代码闸机（phase_gate.py exit code、validate --strict exit 1、project_init.py exit 1）替代 LLM 记忆。

## 遇到什么问题
- API 层限流：minimax-m3 429、glm-5.2 连接超时、gpt-5.4-mini 和 claude-opus-4-7 不可用。切到 deepseek 模型后恢复。
- Boulder 触发循环：方案使用 `#### T0.1` 标题格式而非 `- [ ]` checkbox，导致 boulder 找不到已完成任务反复触发。最终删除 boulder.json 解决。
- T0.1/T0.2 和 T0.3 实际已预先存在——原方案引用的 bug 已在此前修复。
- validate-policy-analysis OCR 检查依赖上游填充 total_controls/analyzed_controls 字段（当前可能不产出），闸可能不触发。

## 下一步建议
- 跑一次端到端测试：完整走一遍 Phase 1→5，验证闸机在真实场景下正确触发
- 确认 document-organizer 输出是否包含 total_controls/analyzed_controls（否则 OCR 闸永远不触发）
- 考虑为 finding-debate 补 Step 5 + validate-finding.py 引用
