---
slug: model-config-2026-08
status: ready
intent: clear
review_required: false
plan_sha256: null
---

# model-config-2026-08 - Work Plan

## TL;DR (For humans)

**What you'll get:** 按 opencode-go 订阅真实配额（10 美金/月 = $60 用量）重新分配全部模型，并修正配置机制缺陷。

**Why this approach:** 三个硬事实驱动：(1) deepseek-v4-flash 0731 正式版已追平 glm-5.2（独立测 79 vs 81，差 2 分），价格却是 1/10——高频角色全用 flash 最划算；(2) 订阅按美元计配额，k3（$15/百万输出）月仅 ~490 次额度，只能给低频高价值角色；(3) omo.jsonc 有 agents（子代理/主会话通道）和 categories（task(category=) 通道）两段配置，必须双段同改才生效。

**What it will NOT do:** 不改 opencode.json、不启用禁用模型（qwen3.7*/mimo*）、不配国内不可用模型（grok/gpt-5.6-luna）、不新增删除 agent、不改 maxTokens。

**Effort:** Short
**Risk:** Low - 纯配置修改，改前备份可回滚；重启 opencode 生效

**Decisions to sanity-check:** 高频+中频纯文本角色（atlas/sisyphus*/explore/quick/unspecified-low/writing/deep/unspecified-high）主=deepseek-flash、备用仅 [m3, k2.7-code]（永不碰 k3/glm-5.2）；ultrabrain 主=k3；oracle/metis/momus/prometheus/artistry 主=glm-5.2；视觉=m3（多模态必需）；agents+categories 双段同改。

Your next move: 用 `/start-work` 启动执行。

---

> TL;DR (machine): Short effort, Low risk. Rebalance all agent/category model configs per opencode-go quota table + V4-Flash-0731 benchmark; high-freq roles use flash with cheap-only fallbacks (never k3/glm-5.2); strong models only on low-freq high-value roles; fix dual-channel config (agents + categories).

## Scope

### Must have

1. 备份 `C:\Users\Administrator\.omo\omo.jsonc` → `omo.jsonc.backup-2026-08-04`
2. 修改 `C:\Users\Administrator\.omo\omo.jsonc` 的 `[opencode].agents` 段（11 个 agent）
3. 修改同文件 `[opencode].categories` 段（8 个 category）
4. 同步 `D:\Nut\00_my_digital\12_AGI\memory\opencode_config_copy\omo.jsonc`
5. 验证 JSON 语法有效
6. 告知用户重启 opencode 生效

### Must NOT have (guardrails, anti-slop, scope boundaries)

1. 不改 `C:\Users\Administrator\.config\opencode\opencode.json`
2. 不启用禁用模型：qwen3.7-max / qwen3.7-plus / qwen3.6-plus / mimo-v2.5 / mimo-v2.5-pro
3. 不配置国内不可用：grok-4.5 / gpt-5.6-luna
4. 不新增/删除任何 agent 或 category 键
5. 不改 `defaults.maxTokens`、`disabled`、`_migrations` 等其他字段
6. **高频角色的 fallback_models 不得包含 kimi-k3 或 glm-5.2**（用户硬性要求）
7. 不 push、不涉及 git

## Verification strategy

> Zero human intervention - all verification is agent-executed.

- Test decision: none（纯 JSON 配置）+ 语法校验 + 文件一致性对比 + 规则断言（grep 校验高频角色备用链）
- Evidence: `.omo/evidence/model-config-2026-08/task-<N>.txt`

## Execution strategy

### Parallel execution waves

- **Wave 1（1 任务）**: Todo 1（备份）
- **Wave 2（1 任务）**: Todo 2（修改 omo.jsonc 双段）
- **Wave 3（2 任务并行）**: Todo 3（同步副本）、Todo 4（验证）

### Dependency matrix

| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1. 备份 | — | 2 | — |
| 2. 修改 omo.jsonc | 1 | 3, 4 | — |
| 3. 同步副本 | 2 | — | 4 |
| 4. 验证 | 2 | — | 3 |

## Todos

- [x] 1. 备份 omo.jsonc
  What to do / Must NOT do:
  - 复制 `C:\Users\Administrator\.omo\omo.jsonc` → `C:\Users\Administrator\.omo\omo.jsonc.backup-2026-08-04`（若已存在则覆盖）
  - 备份后确认文件存在且与原件字节一致
  Parallelization: Wave 1 | Blocked by: — | Blocks: 2
  References: `C:\Users\Administrator\.omo\omo.jsonc`（173 行）
  Acceptance criteria (agent-executable): `Test-Path "C:\Users\Administrator\.omo\omo.jsonc.backup-2026-08-04"` 为 True
  QA scenarios: happy: 备份存在；failure: 备份失败 → 报告停止。Evidence `.omo/evidence/model-config-2026-08/task-1.txt`
  Commit: N

- [x] 2. 修改 omo.jsonc 的 agents + categories 双段
  What to do / Must NOT do:
  - 文件：`C:\Users\Administrator\.omo\omo.jsonc`（保留 `$schema`、`_migrations`、`defaults` 不变）
  - **agents 段**（11 个，只改 model/fallback_models）：
    | agent | model | fallback_models |
    |:--|:--|:--|
    | atlas | opencode-go/deepseek-v4-flash | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
    | explore | opencode-go/deepseek-v4-flash | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
    | hephaestus | opencode-go/deepseek-v4-flash | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
    | librarian | opencode-go/deepseek-v4-flash | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
    | metis | opencode-go/glm-5.2 | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code, opencode-go/deepseek-v4-flash] |
    | momus | opencode-go/glm-5.2 | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code, opencode-go/deepseek-v4-flash] |
    | multimodal-looker | opencode-go/minimax-m3 | [opencode-go/kimi-k2.7-code]（去掉 kimi-k2.6） |
    | oracle | opencode-go/glm-5.2 | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code, opencode-go/kimi-k3] |
    | prometheus | opencode-go/glm-5.2 | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code, opencode-go/deepseek-v4-flash] |
    | sisyphus | opencode-go/deepseek-v4-flash | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
    | sisyphus-junior | opencode-go/deepseek-v4-flash | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
  - **categories 段**（8 个，只改 model/fallback_models）：
    | category | model | fallback_models |
    |:--|:--|:--|
    | artistry | opencode-go/glm-5.2 | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code, opencode-go/deepseek-v4-flash] |
    | deep | opencode-go/deepseek-v4-flash | [opencode-go/kimi-k2.7-code, opencode-go/minimax-m3] |
    | quick | opencode-go/deepseek-v4-flash | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
    | ultrabrain | opencode-go/kimi-k3 | [opencode-go/glm-5.2, opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
    | unspecified-high | opencode-go/deepseek-v4-flash | [opencode-go/kimi-k2.7-code, opencode-go/minimax-m3] |
    | unspecified-low | opencode-go/deepseek-v4-flash | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
    | visual-engineering | opencode-go/minimax-m3 | [opencode-go/kimi-k2.7-code]（去掉 kimi-k2.6） |
    | writing | opencode-go/deepseek-v4-flash | [opencode-go/minimax-m3, opencode-go/kimi-k2.7-code] |
  - **硬性规则（用户要求）**：以下 8 个高频角色的 fallback_models **不得**含 kimi-k3 或 glm-5.2：atlas、explore、hephaestus、librarian、sisyphus、sisyphus-junior（agents 段）+ quick、unspecified-low、writing（categories 段）
  - 注意：`defaults.maxTokens: 16384` 保留；multimodal-looker 的 `disabled: false`、visual-engineering 的 `maxTokens: 16384` 保留
  - **不得**出现禁用/不可用模型名
  Parallelization: Wave 2 | Blocked by: 1 | Blocks: 3, 4
  References:
  - 当前配置：`C:\Users\Administrator\.omo\omo.jsonc`
  - 调用机制（源码）：`dist/index.js:128755-128806`（resolveModelAndFallbackChain）；`:119520-119542`（getRawFallbackModelsForSession）；`dist/cli-node/index.js:26056-26168`（内置 CATEGORY_MODEL_REQUIREMENTS）
  - 性能数据：DeepSeek V4-Flash-0731 官方 9 项 agent benchmark（Terminal-Bench 82.7、DeepSWE 54.4、NL2Repo 54.2）+ 独立复测（AA 智能指数 50 vs GLM-5.2 51、TB 79 vs 81）
  - 配额/价格：opencode.ai/docs/go（$10/月=月$60 用量；flash $0.14/$0.28 月15.8万；m3 $0.30/$1.20 月1.6万；k2.7-code $0.95/$4.00 月6750；glm-5.2 $1.40/$4.40 月4300；k3 $3.00/$15.00 月490）
  Acceptance criteria (agent-executable):
  - Python 去注释后 `json.load` 成功
  - 每个 agent/category 的 model 与 fallback_models 与上表完全一致
  - grep 确认 8 个高频角色 fallback 无 `kimi-k3`、`glm-5.2`
  - grep 确认全文无 `kimi-k2.6`、`minimax-m2.7` 残留（除 _migrations）
  - grep 确认无 `qwen3.7`、`mimo-v2.5`、`grok-4.5`、`gpt-5.6-luna`
  QA scenarios: happy: JSON 有效 + 规则断言全过；failure: 任一不通过 → 对照备份修正。Evidence `.omo/evidence/model-config-2026-08/task-2.txt`
  Commit: N

- [x] 3. 同步 memory 副本
  What to do / Must NOT do:
  - 修改后的 `C:\Users\Administrator\.omo\omo.jsonc` 完整复制到 `D:\Nut\00_my_digital\12_AGI\memory\opencode_config_copy\omo.jsonc`（覆盖）
  - 确认两文件逐字节一致
  Parallelization: Wave 3 | Blocked by: 2 | Blocks: —
  References: `D:\Nut\00_my_digital\12_AGI\memory\opencode_config_copy\omo.jsonc`
  Acceptance criteria (agent-executable): `fc.exe /b` 无差异
  QA scenarios: happy: 一致；failure: 重复制。Evidence `.omo/evidence/model-config-2026-08/task-3.txt`
  Commit: N

- [x] 4. 验证语法与规则
  What to do / Must NOT do:
  - Python 去注释后 json.load 校验
  - 列出 agents（11 键）+ categories（8 键）齐全
  - 逐条核对 model/fallback_models（对照 Todo 2 表格）
  - **规则断言**：8 个高频角色（atlas/explore/hephaestus/librarian/sisyphus/sisyphus-junior/quick/unspecified-low/writing）fallback_models 不含 kimi-k3、glm-5.2
  - 确认 `_migrations` 原样保留
  - 确认 opencode.json 未动
  Parallelization: Wave 3 | Blocked by: 2 | Blocks: —
  References: Todo 2 表格为唯一事实源
  Acceptance criteria (agent-executable): 全部通过
  QA scenarios: happy: 全过；failure: 修复重验。Evidence `.omo/evidence/model-config-2026-08/task-4.txt`
  Commit: N

## Final verification wave

> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.

- [x] F1. Plan compliance audit
- [x] F2. Config correctness review（逐条核对模型名/配额/规则）
- [x] F3. Real manual QA（读取生效配置 + 模拟解析 + 规则断言重跑）
- [x] F4. Scope fidelity（未越界：opencode.json/禁用/不可用模型/高频备用链规则）

## Commit strategy

- 全局配置文件不在项目 git 仓库内，不做 git 操作
- 项目内 memory 副本若被 git 跟踪可单独提交（可选，等用户指示）
- 不 push、不 amend

## Success criteria

1. omo.jsonc 语法有效，agents 11 键 + categories 8 键齐全
2. 高频角色（atlas/sisyphus*/explore/hephaestus/librarian/quick/unspecified-low/writing）主=deepseek-flash，备用仅 [m3, k2.7-code]，**绝无 k3/glm-5.2**
3. **deep/unspecified-high 主=flash**（纯文本任务，flash 0731 全面不输 m3 且更便宜——用户指正）；视觉=m3 主 + k2.7-code 备
4. ultrabrain 主=k3；oracle/metis/momus/prometheus/artistry 主=glm-5.2（低频高价值角色）
5. 无 kimi-k2.6 / minimax-m2.7 残留；无禁用/不可用模型
6. memory 副本与生效配置一致
7. 用户重启 opencode 后生效
