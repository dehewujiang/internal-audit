# 经验教训

## 2026-08-06：三则教训（全量坏路径修复 + 阶段一/二/三整改批次）

### 教训1：验收记录的"已验证"可能是假阳性
- **发生了什么**：8-05 的 session 记录写着"grep 验证源仓库无 ~/.claude/skills/internal-audit 残留"，实际 8-06 全量排查发现 **44 处残留、12 个文件**（修复只覆盖了 execution-assistant 4 处）。
- **根因**：验证动作可能只覆盖了部分范围（或 grep 模式写漏），但记录写成了全局结论。
- **硬规则**：memory 中写"已验证/无残留/全部通过"必须附**可复查的证据**（命令输出、文件清单）；验证结论的范围要写清楚（"execution-assistant 4 处已修"≠"全仓库无残留"）。

### 教训2：文档与代码的字段名多次不一致——文档治理是持续负债
- **发生了什么**：① 整改方案 R05 写槽位字段 `slot_id/matched_fields`，代码实际是 `id/file/source_programs`；② VERSION.json 记录 constitution 有 13/14 条，文件实际只有 10 条（11-14 被误删）；③ 5 份 prompt 快照与源文件 4 处实质漂移（根因分层顺序错、中风险执行范围错、"27 个停表词"无源）。
- **根因**：文档是"写时快照"，代码/文件持续演进后文档不会自己跟上。
- **硬规则**：① 写校验脚本前先读**代码实际 schema**（以实测为准，不信任描述性文档）；② 用 pre-commit hook + validate 脚本把"文档-代码一致性"变成机器检查（R08 快照对比、R05/R06 校验器）；③ 核心规则文件（constitution）的删除必须留记录。

### 教训3：宪法级文件可能被"顺手改动"误删
- **发生了什么**：commit 20ad90b 本意是改 evidence 目录说明，却连带删除了 constitution 第 11-14 条硬约束和两大章节，commit message 和 VERSION.json 均无删除记录。
- **根因**：大型编辑时选区错误 + 无独立删除记录机制。
- **硬规则**：constitution 级文件修改必须 `git diff` 审查后再提交；权威文本双份保存（CLAUDE-project.md 保留 14 条，救回了误删内容）。

## 2026-08-05：SKILL.md 脚本路径写死 ~/.claude 绝对路径——部署后文档指向与运行环境不符

- **发生了什么**：audit-execution-assistant/SKILL.md 中 4 处脚本路径写为 `python ~/.claude/skills/internal-audit/_shared/scripts/validate-finding.py`（开发环境绝对路径）。审计项目部署时脚本实际在项目本地 `_shared/scripts/`。审计执行时 LLM 按文档去 `~/.claude` 找脚本——该目录是 7 月 6 日创建的旧快照，里面的 validate-finding.py 是初版（旧 schema），校验行为与源仓库最新版不一致。8 月 5 日清理旧快照后路径彻底失效，已修复为相对路径并重新部署。
- **根因**：把开发环境绝对路径（~/.claude）硬编码进运行文档。文档引导的环境与实际运行环境不一致——源仓库开发时 junction 能看到，部署到审计项目后"文档指东、实际在西"。
- **教训**：SKILL.md 及一切技能文档中的脚本路径必须用**相对路径**（如 `_shared/scripts/validate-finding.py`、`internal-audit-evaluator/SKILL.md`），禁止写 `~/.claude` 等绝对路径。审计项目运行时文档指向的路径必须与部署结构（项目本地 _shared/、.claude/skills/）一致。
- **硬规则**：写 SKILL.md 时，凡引用脚本/技能文件，一律用相对路径；写完用 grep 检查全文无 `~/.claude`、`/home/` 等绝对路径残留。

## 2026-08-04：探索阶段抽样验证导致计划假设被推翻

- **发生了什么**：执行「证据 v2.0 集中存储工作流修复」计划时，探索阶段只抽样验证了 2 个目录（A1.1 和 `_files.old`）就假设"74 个程序目录全空"，计划据此设计"全删"。执行清理时按保护规则全量核对，发现 B1.1（20 文件）和 L1.1（40 文件）含 60 个真实证据文件——计划假设被推翻，靠执行时的保护规则（finding 引用的证据不删）兜住了，未造成数据丢失。
- **根因**：探索阶段用"抽样推断全量"代替"全量验证"。涉及删除的操作，抽样验证的样本不能代表总体——空目录占比高不代表没有非空目录。
- **教训**：
  - **硬规则：涉及删除的操作，探索时必须全量验证，不能抽样推断。** 抽样只适用于"只读分析"场景，不适用于"破坏性操作"的前置确认。
  - 呼应 2026-07-29 的 R04 教训：诊断"缺什么"之前必须先确认"有什么"；同理，删"什么"之前必须先确认"有什么"。
- **触发自查**：计划里出现"全部删除/全部清空"类操作时，立刻自问——我验证了多少个样本？样本数 = 总体数吗？如果不是，必须全量验证再动手。

## 2026-08-04：bump-version.py --commit 只 add VERSION.json

- **发生了什么**：本次想用一个 commit 同时包含 VERSION.json + SKILL.md + create_evidence_dirs.py 三文件，但 `bump-version.py --commit` 只 add VERSION.json，commit 消息是 `chore: bump...`（无业务关键词）。如果直接用它，代码改动会进不了同一个 commit，或 commit 消息不含业务关键词。
- **根因**：`bump-version.py --commit` 的设计假设是"纯版本号 bump 单独成 commit"，没考虑"bump + 代码改动合并 commit"的场景。
- **教训**：
  - `bump-version.py --commit` 只适用于纯版本号 bump 场景。
  - 想把代码改动和版本号放一个 commit（含业务关键词消息）时，正确流程是：先 `bump-version.py`（不带 --commit）更新 VERSION.json → 手动 `git add` 目标文件 → 手动 `git commit -m "业务关键词消息"`。
- **触发自查**：看到 `bump-version.py --commit` 时，自问——这个 commit 里除了 VERSION.json 还要不要带别的文件？要带 → 别用 --commit。

## 2026-07-29：decisions.md 被 Write 覆盖——丢失 19 条 ADR

- **发生了什么**：收工写入 `decisions.md` 时用了 `Write`（全量覆盖）而非 `Edit`（追加），写入内容只有新增的 ADR-020，导致 ADR-001~019 全部丢失。用户发现后从 git 恢复。
- **根因**：`Write` vs `Edit` 在使用习惯上无区分——收工时同时改 5 个文件，全部用了 `Write`。但 `decisions.md` 和 `feedback.md` 是追加型文件，`session.md` 是覆盖型文件，这两种文件的写入模式不同，混用会出事故。
- **教训**：
  - **硬规则：对 decisions.md 和 feedback.md，永远只用 Edit 追加，绝不用 Write 覆盖。**
  - 这两个文件是项目的历史记录，清空 = 历史断裂，比单次 session 记录丢失更严重。
- **触发自查**：收工时如果用了 `Write` 写入 decisions.md 或 feedback.md → 立刻停下，检查是否丢了已有内容。

## 2026-07-29：memory 文件未引用关键文档路径

- **发生了什么**：TODO.md、session.md、project.md 都提到了"风险整改方案"，但都没写文件路径 `风险整改方案_2026-07-29.md`。明天启动时只能知道"有份方案"，找不到文件在哪。
- **教训**：memory 文件里提到任何项目内的关键文档时，必须带可定位的路径（相对项目根目录），不能只写主题描述。
- **硬规则**：收工审核时自检——TODO.md 中每个待办项如果有对应文档，必须注明文件路径。

## 2026-07-29：整改方案诊断偏差——R04 没发现已有 Infrastructure

- **发生了什么**：整改方案声称 R04 "validate-program.py 只查格式不查覆盖"，但实际 `check_risk_coverage()` 和 `check_ir_coverage_rate()` 两个函数都存在，`program_ir_parser.py` 已能将 MD 解析为结构化 ProgramIR。基础设施已就绪，缺的是工作流接入。
- **根因**：整改方案作者（可能是 LLM）没读 `validate-program.py` 的 `--ir` 模式和 `program_ir_parser.py`，只看到了表面的 `check_risk_coverage()` 正则粗扫，就下了"只查格式"的结论。
- **教训**：诊断"缺什么"之前，必须先确认"有什么"。读代码不能只读函数名和注释——要读参数、读 CLI 入口、读调用链。`--ir` 模式在 argparse 中定义（第 374 行），如果没看到就漏了整个结构化校验体系。
- **下次类似情况**：遇到"缺 XX 检查"的诊断时，先 grep 整个代码库搜相关关键词，确认真的没有，再写方案。

## 2026-07-26：部署流程脱节 — 跳过了 update-project.ps1

- **发生了什么**：证据架构改造完成后，部署到已有项目时只跑了 `create_evidence_dirs.py`（创建目录和 catalog），跳过了 `update-project.ps1`（同步 `_shared/`、`tools/` 和 VERSION.lock）。用户发现 VERSION.lock 日期还是 7月22日。
- **根因**：PowerShell 工具在当前会话中输出静默（`echo "hello"` 也无输出），`update-project.ps1` 静默失败。我没有明确告知用户这个环境问题，而是用 Python 手改了 VERSION.lock 绕过去——结果是版本号对了但文件没同步。
- **教训**：部署到已有项目的正确流程是 `update-project.ps1` → `create_evidence_dirs.py`。工具故障不能成为跳过关键步骤的借口——应该告知用户并等待其手动操作。

## 2026-07-26：PowerShell 输出静默

- **发生环境**：当前 WorkBuddy 会话中，PowerShell 工具所有输出方式均返回空白，exit code 始终为 0。
- **影响**：`update-project.ps1`、`setup-project.ps1` 等依赖 PowerShell 的部署脚本无法使用。
- **根因**：[推测] 当前会话的 PowerShell 宿主配置问题，非脚本本身问题。之前会话中可正常运行。
- **教训**：涉及 PowerShell 脚本的任务在当前环境需改用 Python + Bash 手动完成等价操作。

## 2026-07-26：commit 前忘记跑 bump-version.py（第三次违反）

- **硬规则**：
  1. **任何涉及代码/skill/脚本的 commit 之前，必须先跑 `python _shared/scripts/bump-version.py`。**
  2. 追加变更记录：`python _shared/scripts/bump-version.py --add "type:file:summary"`
  3. 一步到位：`python _shared/scripts/bump-version.py --add "type:file:summary" --commit`
  4. 纯文档/记忆更新不需要 bump VERSION.json。

## 2026-07-13：验证循环复发——硬停止规则

- **硬规则（禁令，非建议）**：
  1. **同一个 Bash 命令在一个响应中只跑一次。**
  2. **验证 = 执行一次命令 + 确认输出符合预期。** 两者都完成后，验证结束。不存在"再看看"。
  3. **汇报 = 停止。** 汇报完就停，不额外验证。
  4. **成功 = 停止。** 操作成功不触发额外检查。
  5. **用户确认才是二次验证的触发条件。**

## 2026-07-10：验证循环——成功信号不产生停止信号

- **根因**：`Bash` 返回成功时，成功不提供停止信号。失败会停，成功反而不会。我把"验证通过"读成"还需要再验证一轮"。
- **硬规则**：同一个 Bash 调用在一个响应中只跑一次。如果用户说"再确认一下"才是再次验证的触发条件。

## 2026-07-06：Memory 位置错误
- **教训**：当两条同类型指令指向不同目标时，必须先停下来对账。

## 2026-07-06：Windows junction 创建
- **cmd //c 'mklink /J ...'** 是正确语法
