# Prompt 回归测试指南

## 何时使用

当以下任一文件被修改后，应执行回归测试：
- `audit-execution-assistant/SKILL.md`
- `audit-execution-assistant/references/intuition_engine.md`
- `audit-execution-assistant/references/evidence_standards.md`
- `audit-execution-assistant/references/root_cause_framework.md`
- `internal-audit-program-generator/SKILL.md`
- `internal-audit-program-generator/references/*`（知识库）

## 测试步骤

### 1. 对比快照（自动闸机）

pre-commit hook 已自动检测"源文件变更但快照未同步"（R08）：
```bash
python tests/prompt_snapshots/compare-snapshots.py --files <变更文件列表>
```
- 源+快照同改 → 有意变更，通过
- 源改快照未改 → 拦截，提示同步快照或回滚源文件
- 跳过检查：`SKIP_SNAP_CHECK=1 git commit ...`

### 2. 判定变更意图

- 差异为有意修改 → 更新快照文件，在提交信息中说明原因
- 差异为意外漂移 → 回滚到快照版本
- 不确定 → 在隔离的测试项目中用旧版和新版分别生成同一个 finding，对比结果

### 3. 关键检查点

| 检查项 | 期望行为 |
|--------|---------|
| CCEER 五要素 | Finding 必须包含全部五个要素，缺一不可（含 consequence） |
| 证据等级 | 高风险 finding 必须有 A 或 E 级证据（B 级截图不可独立支撑） |
| 根因深度 | 至少追溯到层次1（控制环境）或层次2（控制设计）；EXEC-01 需终止条件标注 |
| 法律定性 | 不得出现"构成舞弊"等法律结论 |
| 对抗验证 | 轨道B 必须执行红蓝队对抗，且输出 30%/50% 定量判定 |

---

## R09 人工抽查清单（短期纪律，LLM 输出本质非确定性，自动化断言不适用）

### 触发抽查的改动规模（满足任一即抽）

- [ ] schema 升级（finding / catalog / index / program_ir 任一）
- [ ] SKILL.md 重写（结构或关键步骤变更）
- [ ] references 目录大改（知识库/框架文件）
- [ ] 引入新脚本或重写既有校验脚本
- [ ] 快照批量重写（R03 类）

### 抽查动作

1. 取一份已完成项目的真实输入（policy-analyses + DRL + about-me/my-config）
2. 重新跑一次完整流程（program-generator → execution-assistant）
3. 对比新旧输出的：
   - finding 数量与风险等级分布
   - 程序覆盖率（validate-program.py --ir 输出）
   - 证据等级标注完整率
4. 差异评级：
   - GREEN：无实质差异
   - YELLOW：结构一致但措辞不同（可接受）
   - RED：关键字段缺失或结论反转（必须修复）

### 提交标注规范

抽查完成后，在 commit message 中标注：`已人工回归: [抽查项目名] [评级]`

示例：`fix: XX 调整` → `fix: XX 调整 已人工回归: 武汉长源-人力资源 GREEN`

### 标准用例积累（中期，排期）

从已完成的真实审计项目提取 5-10 份有定论的输入输出对，存入 `tests/fixtures/regression/`，每份含 `input/` + `expected_output/` + `README.md`。

**已积累（首批 1 份 P1→P2 回归对，后续待补至 5-10 份）**：`tests/fixtures/regression/p2026-001-hr/`——提取自 P-2026-001（武汉长源，已脱敏为"公司A"），含 policy-analyses（考勤管理规定 A5）+ audit-programs（审计程序 v3.0）真实输入各 1 份，expected_output 记录 `validate-policy-analysis.py`（exit 2）与 `validate-program.py --ir --strict`（exit 1）的基准结果；findings 回归对待项目完成 P3 后补充。后续积累方向：其他真实项目（P-2026-002 等）完成后的 P1→P2 对，以及本项目 P3 findings 产出的 P3→P4 对。

---

## 自动回归与影响卡片（R09 自动化，pre-commit 两层检查）

pre-commit hook 在提交时对暂存区做两层自动检测（需先安装新版 hook 才生效，见下方「部署注意」）：

### ① SKILL.md / references/ 变更 → 影响卡片 + 快照闸机拦截

暂存区命中 `SKILL.md` 或 `references/` 文件时，hook 做两层处理：

**影响卡片（只提示，不拦截）**：

- **列出变更文件**
- **阶段映射**（硬编码表）：
  - document-organizer → Phase1 制度分析
  - audit-interview-designer → Phase1.5 访谈
  - internal-audit-program-generator → Phase2 程序生成
  - audit-execution-assistant → Phase3 执行取证
  - audit-finding-debate → Phase3.5 发现辩论
  - internal-audit-report-generator → Phase4 报告
  - internal-audit-evaluator → 全阶段质量评估
  - references/ → 所属 skill 对应阶段
- **提醒行**：`⚠️ 此变更未经 LLM 回归验证，建议按 R09 清单人工抽查后 commit 标注: 已人工回归: [项目] [评级]`
- **引导行**：
  - `⚠️ 若此变更为无意改动（你没要求改 SKILL），请回滚：git checkout -- <文件>`
  - `⚠️ 若为有意变更：快照闸机要求同步快照（源文件+快照同改）方可提交；同步方法见上文「对比快照」一节`

**快照闸机（R08，拦截）**：影响卡片本身只提示不拦截（SKILL 语义变更无法用确定性断言覆盖，交给人工 R09 清单）；但 `compare-snapshots` 在"源文件变更而快照未同步"时**拦截 commit（exit 1）**——这是防"未授权改动悄悄入库"的第一道闸。提交前必须二选一：

- **有意变更** → 同步快照（源文件 + 快照同改），提交信息中说明原因
- **无意变更** → 回滚源文件（`git checkout -- <文件>`）

### ② 脚本/schema/测试基础设施变更 → 确定性回归（RED 拦截）

暂存区命中 `_shared/scripts/*.py`、`tests/fixtures/`、`tests/prompt_snapshots/` 时，hook 自动运行：

```bash
python tests/prompt_snapshots/regression-check.py
```

- 扫描 `tests/fixtures/regression/*/expected_output/*.txt`，按文件名前缀映射校验脚本（`validate-policy-analysis` → `validate-policy-analysis.py`；`validate-program` → `validate-program.py --ir --strict`），从 `## exit code` 段解析基线退出码
- 重跑校验脚本对比 exit code：一致 → GREEN；不一致 → RED（脚本行为变化 = 兼容性风险）
- 全 GREEN → 放行；有 RED → **拦截 commit**，提示「回归基线破坏」

拦截时建议：修正脚本兼容性；或确认为有意变更后更新 `expected_output/` 基线并在 commit message 注明；或临时 `SKIP_REGRESSION_CHECK=1 git commit ...`（不推荐）。

### 跳过开关

| 开关 | 作用 |
|:-----|:-----|
| `SKIP_SNAP_CHECK=1` | 跳过快照一致性检查（R08，compare-snapshots） |
| `SKIP_REGRESSION_CHECK=1` | 跳过自动回归（②），独立于 SKIP_SNAP_CHECK |

### 部署注意

已部署项目（`.git/hooks/pre-commit` 为旧版，仅含快照检查）需重新安装新版 hook 才生效：

```bash
cp tests/prompt_snapshots/pre-commit.hook .git/hooks/pre-commit
```

手动运行回归：`python tests/prompt_snapshots/regression-check.py [--fixtures-dir <路径>] [--json]`
