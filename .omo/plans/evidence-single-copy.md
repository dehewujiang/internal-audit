---
slug: evidence-single-copy
status: ready
intent: clear
review_required: false
plan_sha256: null
---

# evidence-single-copy - Work Plan

## TL;DR (For humans)

**What you'll get:** 修复"证据重复复制"问题——以后每个证据文件只放 `_files/` 一个公共文件夹，哪些审计程序引用它由证据清单（`_evidence_catalog.json`）自动记录。取消按程序建 74 个空文件夹的做法。武汉长源现场清理，两个在审项目同步新版说明和脚本。

**Why this approach:** 系统在 7 月 26 日已设计好"集中存储"功能且核心逻辑经武汉长源证据清单验证正确（一份 Excel工资表被 5 个程序引用的场景已正确处理），只是使用说明自相矛盾、操作流程没接通，导致从未真正用起来。修断点比换方案可靠。

**What it will NOT do:** 不升级广东长华的程序文档（你已明确搁置）；不处理 9 项风险整改；不动已有审计数据；不用链接文件方案（网盘下不可靠）。

**Effort:** Short
**Risk:** Low - 改动集中在 1 个说明文件 + 1 个脚本 + 项目现场清理，全部目录已验证为空

**Decisions to sanity-check:** 广东长华程序升级（C4）按用户指示搁置；证据目录全部集中到 `_files/`（用户已拍板）。

Your next move: 用 `/start-work` 启动执行。详细执行步骤见下。

---

> TL;DR (machine): Short effort, Low risk. Fix v2.0 evidence single-copy workflow: SKILL.md contradiction, create_evidence_dirs dirs, Wuhan site cleanup, deploy to 2 projects, bump VERSION, e2e verify.

## Scope

### Must have

1. `audit-execution-assistant/SKILL.md`（源仓库根目录）路径矛盾修正 + catalog 检查默认化
2. `_shared/scripts/create_evidence_dirs.py` 取消程序目录创建，只建 `_files/` + catalog
3. 武汉长源现场：`_files.old` → `_files`，删除 74 个空程序目录（逐目录验证为空后删）
4. 部署：`update-project.ps1` 同步武汉长源、广东长华（SKILL.md + create_evidence_dirs.py）
5. `VERSION.json`：`bump-version.py` 记录变更并 commit（feedback.md 硬规则）
6. 端到端验证：武汉长源完整跑一遍 生成catalog → scan → match → status → update

### Must NOT have (guardrails, anti-slop, scope boundaries)

1. **广东长华程序 v1.0→v3.0 升级：用户批准时明确搁置，本次不执行**（C4 deferred）
2. 不新建 validate-catalog.py（R05 属 2026-07-29 整改方案，另行安排）
3. 不处理 9 项风险整改（R01-R09）
4. 不动 findings/ 既有数据（武汉长源 1 个待核实异常保留）
5. 不实现硬链接/符号链接/快捷方式方案
6. 不修改 evidence_catalog.py 的扫描/匹配逻辑
7. 不动"人力资源（总）"老项目
8. 不新增证据等级规则
9. 不删除任何**非空**目录——发现任一程序目录内有文件，立即停止并报告

## Verification strategy

> Zero human intervention - all verification is agent-executed.

- Test decision: tests-after（脚本改动小，用现有 fixtures 实测）+ 命令级验收
- 复用现有测试夹具：`tests/fixtures/` 下的合成审计程序 MD（TODO.md 记录 2026-07-14 曾用于 --ir 端到端验证）
- Evidence: `.omo/evidence/evidence-single-copy/task-<N>.txt`（执行者自建目录，记录每条验收命令的输出）

## Execution strategy

### Parallel execution waves

- **Wave 1（3 任务并行）**: Todo 1（SKILL.md）、Todo 2（脚本）、Todo 3（武汉长源现场清理）
- **Wave 2（1 任务）**: Todo 4（bump+commit）——必须先于部署，让 VERSION.json 记录本次变更
- **Wave 3（2 任务并行）**: Todo 5（部署，依赖 4）、Todo 6（端到端验证，依赖 3+5）

> 顺序依据：update-project.ps1 对比"项目 VERSION.lock vs 源仓库 VERSION.json"决定是否复制。先 bump 再部署，项目锁定的版本号与实际复制的内容一致；先部署后 bump 会导致锁定版本 ≠ 实际内容，追溯链失真。

### Dependency matrix

| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1. SKILL.md 修正 | — | 4 | 2, 3 |
| 2. 脚本修改 | — | 4, 6 | 1, 3 |
| 3. 武汉长源现场清理 | — | 6 | 1, 2 |
| 4. bump+commit | 1, 2 | 5 | — |
| 5. 部署同步 | 4 | 6 | — |
| 6. 端到端验证 | 3, 5 | — | — |

## Todos

- [x] 1. audit-execution-assistant/SKILL.md：消除证据路径矛盾，catalog 检查默认化
  What to do / Must NOT do:
  - 文件：`D:\Nut\00_my_digital\12_AGI\skills\internal-audit\audit-execution-assistant\SKILL.md`（源仓库根目录，**不要改**部署项目的副本，由 Todo 4 部署过去）
  - 第 115-127 行（Step 1 证据存放路径规则 v2.0）：
    - 目录树示例改为 `evidence/_files/`（去掉 `{project_name}/` 中间层，与代码一致）
    - 删除 `{程序编号}_{程序关键词}/` 行（不再有程序目录）
  - 第 156 行（Step 1 界面示例"证据存放路径"）：`evidence/{project_name}/{程序编号}_{程序关键词}/` → `evidence/_files/`
  - 第 228-266 行（Step 0.1 证据匹配）：将"当用户说'帮我匹配证据'时"的条件触发，改为 Step 1 执行每个程序前**默认**展示该程序证据收集状态（读 catalog 的 source_programs 定位当前程序槽位），证据到达后默认跑 `evidence_catalog.py match` + 展示状态表
  - 第 121 行及全文：不得残留 `{程序编号}_{程序关键词}` 或 `evidence/{project_name}` 字样
  - 不得改动 Step 2 以后的证据分析/等级规则等无关内容
  Parallelization: Wave 1 | Blocked by: — | Blocks: 4
  References:
  - 矛盾点：`audit-execution-assistant/SKILL.md:115-127`（规则）vs `:156`（界面示例）
  - 代码实际路径：`_shared/scripts/create_evidence_dirs.py:387`（`evidence_root / '_files'`，无中间层）
  - 部署版与源仓库一致性已验证（grep 输出两文件 16 处匹配完全相同）
  Acceptance criteria (agent-executable):
  - `grep -n "{程序编号}_{程序关键词}" <SKILL.md>` 无匹配
  - `grep -n "evidence/{project_name}" <SKILL.md>` 无匹配
  - `grep -n "evidence/_files" <SKILL.md>` ≥3 处匹配
  - Step 1 段落包含"默认检查 catalog"描述
  QA scenarios (name the exact tool + invocation): happy: 上述 grep 全过；failure: 任一 grep 有残留 → 修正后重跑。Evidence `.omo/evidence/evidence-single-copy/task-1.txt`
  Commit: N（与 Todo 2 合并 commit，见 Todo 5）

- [x] 2. _shared/scripts/create_evidence_dirs.py：取消程序目录创建
  What to do / Must NOT do:
  - 文件：`D:\Nut\00_my_digital\12_AGI\skills\internal-audit\_shared\scripts\create_evidence_dirs.py`
  - 修改 `create_evidence_dirs()`（第 384-400 行）：删除按程序编号循环 `mkdir` 程序目录的代码，只保留 `_files/` 目录创建（`files_dir.mkdir(parents=True, exist_ok=True)`）
  - 函数返回 dict 保持 `{"created": N, "existed": M}` 语义：`created` 改为 `_files/` 创建计数（0/1），不再对程序计数
  - `main()` CLI（第 402 行起）输出同步：不再打印"共 N 个程序 → N 个目录"，改为打印"证据集中目录 _files/ 就绪 + catalog 槽位数"
  - `generate_evidence_catalog()`（第 335 行）**不得改动**——catalog 生成逻辑已正确
  - `parse_programs_from_md()` 等解析函数**不得改动**——ProgramIR 复用
  - 不得顺手重构其他函数
  Parallelization: Wave 1 | Blocked by: — | Blocks: 4, 6
  References:
  - 函数现状：`_shared/scripts/create_evidence_dirs.py:384-400`
  - CLI：同文件 `main()`（~402-460 行），第 453 行有"未找到取证方式列"提示
  - 测试夹具：`tests/fixtures/`（合成审计程序 MD，2026-07-14 端到端验证用过）
  Acceptance criteria (agent-executable):
  - `python -m py_compile _shared/scripts/create_evidence_dirs.py` 退出 0
  - 用 tests/fixtures 的合成 MD 运行：`python _shared/scripts/create_evidence_dirs.py --program-md tests/fixtures/<fixture>.md --workspace <temp_ws>` → 输出目录中**只有** `evidence/_files/`，无 `evidence/<编号>_*` 目录
  QA scenarios: happy: 上述命令产物只有 _files/；failure: 若仍有程序目录产生 → 检查循环删除是否彻底。Evidence `.omo/evidence/evidence-single-copy/task-2.txt`
  Commit: N（与 Todo 1 合并 commit，见 Todo 5）

- [x] 3. 武汉长源现场：_files.old 正名 + 删除空程序目录（完成：改名 ✅ + 删除 70 个确认空目录 ✅；B1.1/L1.1 含真实证据且 B1.1 被 finding 引用，按保护规则永久保留——删除=销毁证据，非阻塞项）
  What to do / Must NOT do:
  - 目录：`D:\01_CH\01_Doing\AU_PL_260601_人力资源_武汉长源\internal-audit-workspace\evidence\`
  - 改名：`_files.old` → `_files`（Windows: `Rename-Item` 或 `Move-Item`；若目标已存在则先处理）
  - 删除程序目录：遍历 `evidence/` 下所有匹配 `[A-H]\d+(\.\d+)?_*` 模式的目录（74 个，含 `B1.1 考勤数据手工传递篡改/`、`L1.1 小时工效率/` 等空格命名变体）：
    - **逐一验证目录为空**（无任何文件和子目录，含隐藏文件）
    - 全部为空 → 逐个删除
    - **任一非空 → 立即停止删除操作，记录该目录名并向用户报告，剩余目录保持原样**
  - `_evidence_catalog.json.old` 保留不动（Todo 6 会用新脚本重新生成 catalog 覆盖）
  - 不得删除 `findings/`、`audit-programs/` 等 evidence 之外的任何东西
  - 不得改动 findings/B1.1_考勤数据手工传递篡改_待核实异常.json
  Parallelization: Wave 1 | Blocked by: — | Blocks: 6
  References:
  - 目录现状（已读取验证）：`evidence/` 74 个程序目录 + `_files.old/`（空）+ `_evidence_catalog.json.old`（162 槽位）
  - 抽样已验证：`evidence/A1.1_考勤数据手工传递篡改/` 为空、`evidence/_files.old/` 为空
  Acceptance criteria (agent-executable):
  - `evidence/` 下 `Get-ChildItem -Directory | Where-Object { $_.Name -match '^[A-H]\d' }` 返回 0 个
  - `evidence/_files` 存在且为空目录
  QA scenarios: happy: 74 目录全删、_files 就位；failure: 任一目录非空 → 停止并报告（验收失败，不强行删除）。Evidence `.omo/evidence/evidence-single-copy/task-3.txt`
  Commit: N（项目现场操作，不属源仓库）

- [x] 4. VERSION.json 记录 + 合并 commit（先于部署）
  What to do / Must NOT do:
  - 在源仓库根目录运行：`python _shared/scripts/bump-version.py --add "fix:create_evidence_dirs.py,SKILL.md:证据 v2.0 集中存储工作流修复（取消程序目录、SKILL.md 路径矛盾修正、catalog 检查默认化）" --commit`
  - commit 消息遵循仓库风格（参考 `git log --oneline -5`）
  - 只暂存本次改动的两个文件：`audit-execution-assistant/SKILL.md`、`_shared/scripts/create_evidence_dirs.py`（+ bump-version.py 自动改的 VERSION.json）
  - **不得**捆绑其他无关文件（如 memory 更新、.omo 文件）
  - 纯文档/记忆文件不需要 bump（本次不是）
  - **必须先于 Todo 5（部署）完成**——部署脚本靠 VERSION.json 的新版本号驱动差异检测
  Parallelization: Wave 2 | Blocked by: 1, 2 | Blocks: 5
  References:
  - feedback.md 硬规则：commit 前必须先跑 bump-version.py（2026-07-26 第三次违反记录）
  - bump-version.py 用法：`--add "type:file:summary" --commit` 一步到位
  - update-project.ps1 版本对比机制：读取项目 VERSION.lock.json 的 locked_version 对比源仓库 VERSION.json 的 version
  Acceptance criteria (agent-executable):
  - `git log --oneline -1` 显示新 commit，消息含证据/集中存储关键词
  - `git status` 无未暂存的本次改动文件
  - VERSION.json `version` 已递增、`changes` 含本次记录
  QA scenarios: happy: commit 成功且 VERSION 递增；failure: commit 被拒/漏文件 → 检查暂存区。Evidence `.omo/evidence/evidence-single-copy/task-4.txt`
  Commit: Y | fix(evidence): 证据 v2.0 集中存储工作流修复

- [x] 5. 部署同步：update-project.ps1 更新两个在审项目（bump 完成后）
  What to do / Must NOT do:
  - 在源仓库目录运行：`powershell -File update-project.ps1 -ProjectDir "D:\01_CH\01_Doing\AU_PL_260601_人力资源_武汉长源" -Force`
  - 再运行同命令（广东长华）：`... -ProjectDir "D:\01_CH\01_Doing\AU_PL_260601_人力资源_广东长华" -Force`
  - 确认输出显示新版本号（应为 Todo 4 bump 后的版本，如 2026-07-21-3）且 `.claude/skills/audit-execution-assistant` 和 `_shared` upgraded
  - **必须先于 Todo 6（端到端验证）完成**——验证要用部署后的新脚本
  - 不得执行 setup-project.ps1（会重建目录结构）
  - 不得跳过任一项目（两个都要部署）
  - 若部署输出异常（如 PowerShell 静默），按 feedback.md 2026-07-26 教训：告知用户，不得手改 VERSION.lock 绕过
  Parallelization: Wave 3 | Blocked by: 4 | Blocks: 6
  References:
  - 脚本：`update-project.ps1`（`-Force` 跳过确认、保留备份）
  - feedback.md 2026-07-26 教训：部署正确流程是 update-project.ps1，工具静默失败不能用手改 VERSION.lock 绕过
  Acceptance criteria (agent-executable):
  - 两个项目的 `VERSION.lock.json` `locked_version` == 源仓库 `VERSION.json` `version`（Todo 4 bump 后的新版本号）
  - 两项目 `.claude/skills/audit-execution-assistant/SKILL.md` 与源仓库文件逐字节一致（`fc.exe /b` 或 `Compare-Object (Get-Content ...)`）
  - 两项目 `_shared/scripts/create_evidence_dirs.py` 与源仓库一致
  QA scenarios: happy: 版本一致 + 文件一致；failure: 任一项目版本不匹配 → 重跑 update-project.ps1 直到一致。Evidence `.omo/evidence/evidence-single-copy/task-5.txt`
  Commit: N（部署是复制操作）

- [x] 6. 端到端验证：武汉长源完整证据流程
  What to do / Must NOT do:
  - 前置：Todo 3（现场清理）+ Todo 5（部署）必须已完成——本步骤使用**部署后**的新脚本
  - 在武汉长源 workspace 运行（用新部署的脚本）：
    - `python _shared/scripts/create_evidence_dirs.py --program-md internal-audit-workspace/audit-programs/人力资源管理_审计程序_v3.0.md --workspace internal-audit-workspace` → 确认生成 `_evidence_catalog.json`（约 162 槽位）且**不再创建程序目录**
    - `python _shared/scripts/evidence_catalog.py status internal-audit-workspace` → 输出 total_slots ≈ 162、filled_slots = 0
    - `python _shared/scripts/evidence_catalog.py scan internal-audit-workspace` → 输出文件列表（_files/ 目前为空则返回 []，正常）
    - 放一个模拟文件：`Copy-Item tests/fixtures/<某合成表.xlsx> internal-audit-workspace/evidence/_files/模拟证据.xlsx`（或新建一个空 txt）→ 再跑 `scan` + `match` → 确认建议匹配输出
    - `python _shared/scripts/evidence_catalog.py update internal-audit-workspace --slot EVD-<某id> --file <相对路径>` → 确认 success:true
    - 再跑 `status` → filled_slots 变为 ≥1
  - 验证完成后：删除模拟文件，`update` 回空（或保留一个真实证据由用户决定——默认删除模拟文件保持现场干净）
  - 不得在真实项目里跑 data_executor 或任何写操作之外的脚本
  - 不得修改 catalog 槽位内容本身（只做 update 填充验证）
  Parallelization: Wave 3 | Blocked by: 3, 5 | Blocks: —
  References:
  - 脚本用法：`_shared/scripts/evidence_catalog.py` 头部注释（scan/match/status/update 四命令）
  - 武汉长源程序：`internal-audit-workspace/audit-programs/人力资源管理_审计程序_v3.0.md`
  - 旧 catalog 参照：`evidence/_evidence_catalog.json.old`（162 槽位，EVD-003 Excel工资表 5 程序引用）
  Acceptance criteria (agent-executable):
  - catalog 重新生成成功（JSON 合法、total_slots ≥ 150）
  - 生成过程未创建任何 `evidence/<编号>_*` 目录
  - status → update → status 闭环：filled_slots 从 0 变 ≥1（验证后还原为 0）
  QA scenarios: happy: 全流程输出符合预期；failure: match 无建议或 update 失败 → 检查路径相对基准（scan_files 用 `relative_to(evidence_root.parent)`）。Evidence `.omo/evidence/evidence-single-copy/task-6.txt`
  Commit: N

## Final verification wave

> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.

- [x] F1. Plan compliance audit
- [x] F2. Code quality review
- [x] F3. Real manual QA
- [x] F4. Scope fidelity

## Commit strategy

- 源仓库代码改动（Todo 1 + Todo 2）合并为**一个 commit**：`fix(evidence): 证据 v2.0 集中存储工作流修复`
- commit 前必须 `bump-version.py --add ... --commit`（feedback.md 硬规则）
- 项目现场操作（Todo 3/4/6）不 commit——它们是部署项目内的文件操作
- 不 push、不 amend、不改写历史

## Success criteria

1. SKILL.md 全文无"程序编号_程序关键词"目录引导，无 `evidence/{project_name}` 路径
2. create_evidence_dirs.py 运行后只产生 `evidence/_files/` + `_evidence_catalog.json`
3. 武汉长源 `evidence/` 下无任何程序目录残留，`_files/` 就位
4. 两个在审项目 SKILL.md 与脚本与源仓库一致，VERSION.lock 匹配
5. VERSION.json 已记录本次变更并有对应 commit
6. 端到端：武汉长源 catalog 生成 → status → update 闭环跑通（filled 0→1→还原 0）
7. 广东长华程序文档保持 v1.0 原样（用户搁置项，未被动过）
