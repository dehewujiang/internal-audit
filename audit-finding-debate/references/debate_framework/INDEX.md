# 辩论框架索引

## 模式选择

| 模式 | 加载文件 | 说明 |
|------|---------|------|
| **模式A：专家评估** | `evaluation_10dim.md` | 对finding进行10维度业务现实性检验，输出评分和改进建议 |
| **模式B：攻防演练** | `difficulty_levels.md` | 按选定难度进行角色对抗演练，角色通过 `debate_roles/INDEX.md` 选择 |
| **模式C：完整流程** | `evaluation_10dim.md` + `difficulty_levels.md` | 先评估，再演练 |

## 使用规则

- 评估（模式A）时，LLM 基于 10 维度框架对 finding 逐项打分，不需要额外加载任何文件
- 演练（模式B）时，LLM 根据 difficulty_levels.md 中对应难度的 AI 行为特征生成角色回应，不需要加载对话规则或反驳策略文件——这些由 LLM 根据当前 finding 内容和被审计方特征动态生成
- 完整流程（模式C）时，先评估再演练，评估结果作为演练的输入
