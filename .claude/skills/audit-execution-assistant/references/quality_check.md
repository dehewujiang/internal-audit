# 质量评估

> 在全部程序执行完成后、输出执行摘要前自动执行。
> 执行前确保已定位 evaluator 中 **finding** 的检查清单。

## 5.0 确定性校验（validate-finding.py 批量扫描）

在 LLM 执行格式/推理检查之前，先运行确定性脚本扫描全部 finding：

```bash
python _shared/scripts/validate-finding.py --findings-dir findings/ --json
```

**读取输出后**：

| validate-finding 结果 | 处理方式 |
|---------------------|---------|
| 存在任意 block | 阻断输出执行摘要，列出 block 项要求用户修正后重跑 |
| 只有 warn（无 block） | 记录所有 warnings，在质量判定中将这些 warn 视为 ❌ |
| 全部 pass | 进入下一步 |

**validate-finding 的输出必须与 LLM 推理回溯共同决定最终判定**。

## 5.1 格式检查

| 检查项 | 执行方式 | 自动修正？ |
|--------|---------|:---------:|
| JSON schema 合规 | 检查每个 finding 输出的必填字段：(finding_id, origin, title, criteria, condition, cause, recommendation, evidence) | ⚠️ 缺字段通知用户 |
| 证据等级完整性 | 检查所有 evidence 条目是否有 reliability_grade 字段 | ⚠️ 通知用户补标 |

## 5.2 推理检查：发现质量回溯

对本次审计全部 finding 中 risk_level="高" 的每个条目，逐一执行以下回溯检查：

```
高 → 检查全部高风险 finding
中/低 → 检查 risk_level 最高的 1 个
```

**对每个回溯的 finding：**

```
① 【证据等级充分性】高风险finding是否有 ≥1 个 A级或E级证据支撑？
   → 列出所有 evidence 的等级

② 【根因分析深度】cause 字段是否到达控制设计层或控制环境层？
   → 检查是否停在"操作人员未遵守""员工疏忽"等表面原因

③ 【CCEER 五要素完整性】Criteria/Condition/Cause/Effect/Recommendation 是否全部存在且非空？

④ 【建议可执行性】recommendation 是否有具体措施 + 整改责任人 + 完成期限？
   → 三条缺一不可
```

**输出格式**：

```
发现质量回溯 F-XXX：[标题]
├─ ✅/❌ 证据等级充分：[等级列表] 来源：[evidence条目]
├─ ✅/❌ 根因分析深度：[到达层]（若停在表面，标注）
├─ ✅/❌ CCEER完整：[各要素状态]
└─ ✅/❌ 建议可执行：[措施/责任人/期限状态]
```

## 5.3 质量判定

| 条件 | 判定 | 行动 |
|:----:|------|------|
| 全部检查通过 + validate-finding action=pass | ✅ 正常输出 | 输出执行摘要 |
| 仅格式检查 ❌（validate-finding 无 block） | ⚠️ 修正后输出 | 补标后输出 |
| validate-finding action=warn（任意一项） | ⚠️ 质量警告 | 输出时在摘要中列出 warnings 并提示用户审查 |
| 任意高风险finding的证据等级 ❌ | 🔴 质量待审 | 输出时在摘要中标记，提示用户补充证据 |
| 任意根因分析 ❌ 或 validate-finding 有 block | 🔴 阻断输出 | 逐项修正后重跑 validate-finding 直到 action=pass |

## 5.4 结果存储与质量门

```bash
# 1. validate-finding 结果（确定性校验）
python _shared/scripts/validate-finding.py \
    --findings-dir findings/ --json > /tmp/validate_result.json

# 2. LLM 质量回溯结果（推理校验）  
echo '{json格式检查结果}' > /tmp/eval_result.json

# 3. 合并写入评估历史
python .claude/skills/internal-audit-evaluator/record_evaluation.py \
    --input /tmp/eval_result.json

# 4. 质量门判定
python .claude/skills/internal-audit-evaluator/quality_gate.py \
    --input /tmp/eval_result.json
```

**Step 5 完整执行顺序**：
```
5.0 validate-finding 批量扫描（确定性）  → block则中断
5.1 格式检查（LLM）                       → ⚠️自动修正
5.2 推理检查：发现质量回溯（LLM）           → 🔴标记
5.3 质量判定（合并 deterministic + LLM）  → 输出/阻断/警告
5.4 结果存储 + 质量门                    → 写入 JSONL 历史
```
