# Prompt 版本快照

每次修改 SKILL.md 中关键推理指令后，更新对应快照文件。快照用于：
- 检视 prompt 是否发生意外漂移
- 回归测试时对比旧版和新版的行为差异

## 快照文件清单

| 文件名 | 来源 | 描述 |
|--------|------|------|
| `cceer_chain.snap` | audit-execution-assistant/SKILL.md Step 3 | CCEER 五要素推理链 |
| `intuition_engine.snap` | audit-execution-assistant/references/intuition_engine.md | 星座检测/反直觉红旗/时间维度 |
| `root_cause_challenge.snap` | audit-execution-assistant/SKILL.md Step 根因质证 | 根因分析与替代解释检查 |
| `evidence_grading.snap` | audit-execution-assistant/references/evidence_standards.md | A-E 五级证据等级标准 |
| `adversarial_validation.snap` | internal-audit-program-generator/SKILL.md 轨道B | 对抗验证红蓝队规则 |

## 更新频率

- 每次修改相关 SKILL.md 或 references 文件后
- 至少每月检查一次快照与实际 prompt 的一致性

## 自动检测（R08）

pre-commit hook 自动检测"源文件变更但快照未同步"（区分有意变更 vs 无意漂移）：

```bash
# 安装（一次性）
cp tests/prompt_snapshots/pre-commit.hook .git/hooks/pre-commit

# 跳过检查
SKIP_SNAP_CHECK=1 git commit ...
```

手动运行：`python tests/prompt_snapshots/compare-snapshots.py --files <变更文件列表>`
