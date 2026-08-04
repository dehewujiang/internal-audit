---
slug: model-config-2026-08
status: drafting
intent: clear
review_required: false
pending-action: write .omo/plans/model-config-2026-08.md
approach: 基于 opencode-go 订阅配额表（10 美金/月 = 月度 $60 用量）重新评估并配置全部模型；原则：高频主力用最便宜、编码用 k2.7-code、多模态/长上下文用 m3、K3 降级为最后 fallback
---

# Draft: model-config-2026-08

## Components (topology ledger)

| id | 组件 | 预期结果 | 状态 | 证据路径 |
|----|------|---------|------|---------|
| C1 | C:\Users\Administrator\.omo\omo.jsonc | 模型配置按配额表优化 | active | C:\Users\Administrator\.omo\omo.jsonc |
| C2 | D:\Nut\00_my_digital\12_AGI\memory\opencode_config_copy\omo.jsonc | 同步副本 | active | D:\Nut\00_my_digital\12_AGI\memory\opencode_config_copy\omo.jsonc |
| C3 | 备份 | omo.jsonc.backup-2026-08-04 | active | C:\Users\Administrator\.omo\ |

## Open assumptions (announced defaults)

| 假设 | 采用的默认值 | 理由 | 可逆? |
|------|------------|------|-------|
| 配额按美元价值计 | 5小时$12/周$30/月$60，贵模型烧钱快 | opencode.ai/docs/go 官方 | 是 |
| 主模型=高频消费点 | 高频 agent 用最便宜模型 | 10美金是硬限制，主模型决定配额消耗速度 | 是 |
| K3 不做主模型 | oracle/deep/ultrabrain 主模型换掉 K3 | K3 输出 $15/1M 是 glm-5.2 的 3.4 倍，月仅 ~490 请求 | 是 |
| 禁用+不可用模型 | qwen3.7-max/plus/qwen3.6-plus/mimo-v2.5/v2.5-pro 禁用；grok-4.5/gpt-5.6-luna 国内不可用 | 用户约束 | 是 |
| k2.7-code 优于 k2.6 | 编码类备用链 k2.6→k2.7-code | 同价 $0.95/$4.00，配额更多（6750 vs 5750），编码更强 | 是 |
| m3 优于 m2.7 | m2.7→m3 | 同价 $0.30/$1.20，m3 有 1M ctx+多模态 | 是 |

## Findings (cited - path:lines)

1. **订阅配额（官方文档）**：opencode.ai/docs/go — $10/月（首月$5），限额 5小时$12/周$30/月$60 美元价值；不同模型请求数差异巨大（deepseek-v4-flash 月 158K vs kimi-k3 月 490）
2. **完整模型清单 24 个**：`.omo/evidence/model-config-2026-08/opencode-go-models.txt`（后台解析自 C:\Users\Administrator\.cache\opencode\models.json）
3. **价格对比**（每 1M token，输入/输出）：deepseek-v4-flash $0.14/$0.28（最便宜）、minimax-m3/m2.7 $0.30/$1.20、qwen3.5-plus $0.20/$1.20、hy3 $0.14/$0.58、kimi-k2.7-code/k2.6 $0.95/$4.00、glm-5.2 $1.40/$4.40、kimi-k3 $3.00/$15.00（最贵）、grok-4.5 $2.00/$6.00
4. **fallback 调用机制（源码）**：dist/index.js:119593-119610 `findNextAvailableFallback` 按数组顺序遍历；:25098-25124 错误分类（ratelimit/modelunavailable/429/503 触发 fallback；quota_exceeded 经 provider-exhaustion 策略仍可 fallback）；:25420-25471 quota_exceeded 归类为可重试
5. **当前配置**：K3 是 oracle/deep/ultrabrain 主模型（最贵模型做高频主模型=预算风险）；k2.7-code 和 m3 只配给了视觉类（浪费）；k2.6/m2.7 占着编码/检索备用链（有更好的替代）
6. **K3 配额风险**：月仅 ~490 请求（官方估算），oracle/deep/ultrabrain 任一高频使用都会快速触发限额

## Decisions (with rationale)

1. **主模型分层**：
   - 高频主力（atlas/sisyphus/sisyphus-junior/explore/hephaestus/librarian/quick/unspecified-low）：deepseek-v4-flash（$0.14/$0.28 最便宜，1M ctx）——保持现状 ✅
   - 次主力（deep/ultrabrain）：minimax-m3（$0.30/$1.20，1M ctx+多模态，月16K请求）替代 kimi-k3
   - 中频（oracle）：minimax-m3 或 glm-5.2——**待用户选**（m3 性价比 vs glm-5.2 能力）
   - 轻任务（writing）：deepseek-v4-flash 替代 glm-5.2（轻任务省钱）
   - 视觉/多模态（multimodal-looker/visual-engineering）：minimax-m3 主 + k2.7-code 备用——保持现状 ✅
2. **备用链统一升级**：
   - 所有出现 kimi-k2.6 的备用链 → kimi-k2.7-code（同价更强）
   - 所有出现 minimax-m2.7 的备用链 → minimax-m3（同价更强）
   - kimi-k3 保留在 oracle/deep/ultrabrain 备用链**最后一位**（作为"核武器"兜底，平时不触发）
3. **保留 glm-5.2**：作为中高能力通用模型留在备用链（1M ctx 优势）
4. **备份先行**：修改前备份

## Scope IN

1. 备份 omo.jsonc
2. 修改 C:\Users\Administrator\.omo\omo.jsonc（agents + categories 的 model/fallback_models）
3. 同步 memory 副本
4. 验证 JSON 语法
5. 告知重启生效

## Scope OUT (Must NOT have)

1. 不改 opencode.json（blacklist 已正确）
2. 不启用禁用模型（qwen3.7*/qwen3.6-plus/mimo-v2.5*）
3. 不配置国内不可用模型（grok-4.5/gpt-5.6-luna）
4. 不新增/删除 agent 或 category
5. 不改 maxTokens 等其他字段

## Open questions

已解决（用户确认修正版方案）：
1. oracle 主模型 → **minimax-m3**（性价比，glm-5.2 退到备用链）
2. kimi-k3 → **保留在重型角色备用链最后一位**（核武器兜底）
3. categories 段与 agents 段**都要改**（两条派发通道：task(category=) 走 categories；主会话/子代理走 agents）

## Approval gate
status: approved
<!-- 用户 2026-08-04 确认修正版方案：双通道配置、m3 做主模型、k3 核武器、writing 降档 -->
