---
slug: evidence-single-copy
status: awaiting-approval
intent: clear
review_required: false
pending-action: write .omo/plans/evidence-single-copy.md
approach: 修复证据 v2.0 集中存储的四个工作流断点，使"文件只放一份、多程序引用"真正生效；取消程序目录，全部集中到 _files/；广东长华程序 v1.0→v3.0 升级以启用 catalog
---

# Draft: evidence-single-copy

## Components (topology ledger)
<!-- id | outcome (one line) | status: active|deferred | evidence path -->

| id | 组件 | 预期结果 | 状态 | 证据路径 |
|----|------|---------|------|---------|
| C1 | audit-execution-assistant/SKILL.md | 消除自相矛盾：界面示例改为 _files/ 路径；catalog 检查成为 Step 1 默认动作 | active | audit-execution-assistant/SKILL.md:115-171 |
| C2 | create_evidence_dirs.py | 不再创建程序目录，只建 _files/ + catalog | active | _shared/scripts/create_evidence_dirs.py:384-400 |
| C3 | evidence_catalog.py | scan 只扫 _files/（无需改）；match/status 保持 | active | _shared/scripts/evidence_catalog.py:47-83 |
| C4 | 广东长华程序 v1.0→v3.0 | 补"取证方式"列，catalog 可生成 | **deferred（用户搁置）** | D:\01_CH\01_Doing\AU_PL_260601_人力资源_广东长华\internal-audit-workspace\audit-programs\人力资源管理_审计程序_v1.0.md |
| C5 | 武汉长源证据目录清理 | _files.old/ 改名 _files/，74 个空程序目录移除 | active | D:\01_CH\01_Doing\AU_PL_260601_人力资源_武汉长源\internal-audit-workspace\evidence\ |
| C6 | 部署更新 | update-project.ps1 同步到两个在审项目 | active | update-project.ps1 |
| C7 | VERSION.json 升级 | bump-version.py 记录变更 | active | VERSION.json |

## Open assumptions (announced defaults)
<!-- assumption | adopted default | rationale | reversible? -->

| 假设 | 采用的默认值 | 理由 | 可逆? |
|------|------------|------|-------|
| 程序目录内无用户数据 | 武汉长源 74 个程序目录均为空（已验证 A1.1 空、_files.old 空），可直接删除 | 探索确认目录为空 | 是（删除前确认） |
| 武汉长源执行进度 | findings/ 仅有 1 个待核实异常（B1.1），证据收集未实质开始，改动不破坏已有工作 | catalog 填充 0、目录空 | 是 |
| 广东长华升级方式 | 用 program-generator 增量模式补取证方式列（ADR-006 已有机制） | 避免推倒重来 | 是 |
| v2.0 方案延续 | 修断点而非换方案（硬链接/符号链接在网盘 D:\Nut 下不可靠） | 探索证明 v2.0 逻辑正确 | 是 |

## Findings (cited - path:lines)

1. SKILL.md 内部矛盾：第 115-127 行规定"证据只放 _files/ 一份"，第 156 行界面示例仍写"evidence/{project_name}/{程序编号}_{程序关键词}/"引导放程序目录（源仓库与武汉长源部署版完全一致）
2. catalog 匹配是条件触发：Step 0.1 仅当用户说"帮我匹配证据"时执行，Step 1 正常流程不查 catalog（audit-execution-assistant/SKILL.md:228-266）
3. scan_files 只扫 _files/：程序目录中的文件对 catalog 不可见（_shared/scripts/evidence_catalog.py:51）
4. 路径不一致：SKILL.md 写 evidence/{project_name}/_files/（带中间层），代码创建 evidence/_files/（无中间层）（create_evidence_dirs.py:387 vs SKILL.md:118）
5. 武汉长源 catalog 生成成功但从未使用：162 槽位，filled_slots=0，created 2026-07-26（evidence/_evidence_catalog.json.old）；_files.old 为空
6. v2.0 合并逻辑正确：EVD-003「Excel工资表」source_programs=["A10.1","A5.1","B10.1","B5.1","C12.1"]，同一证据被 5 程序引用的场景已正确处理
7. 广东长华程序 v1.0 无取证方式列：表头为 风险编号/风险名称/风险描述/系统业务要素/可能表现/来源标注（v1.0.md:48），create_evidence_dirs.py:453 "未找到'取证方式'列，跳过证据清单生成"
8. TODO.md 已有待办：广东长华程序 v1.0→v3.0（**用户批准时搁置，不纳入本次执行**）；部署后完整证据匹配端到端测试
9. R05 待办：validate-catalog.py 不存在（_shared/scripts 23 个 py 文件清单）

## Decisions (with rationale)

1. **取消程序目录，全部集中 _files/**（用户拍板）：消除"复制"可能性的唯一物理保证。catalog 的 source_programs 已记录引用关系，查状态用 evidence_catalog.py status。
2. **修 v2.0 而非换方案**：v2.0 合并逻辑经武汉长源 catalog 验证正确；硬链接/符号链接在网盘目录（D:\Nut）下同步不可靠，不采用。
3. **catalog 检查默认化**：Step 1 执行每个程序前默认展示该程序证据状态（来自 catalog），替代"用户说帮我匹配才查"。
4. **广东长华升级纳入本次计划**：它是 v2.0 生效的前提（无取证方式列→无 catalog）。
5. **范围包含部署与版本**：改动后必须 update-project.ps1 同步两个在审项目 + bump-version.py（feedback.md 硬规则）。

## Scope IN

1. audit-execution-assistant/SKILL.md：修正路径矛盾（第 156 行界面示例改 _files/、去 {project_name} 中间层）、Step 1 增加默认 catalog 状态展示、Step 0.1 从条件触发改为 Step 1 内置步骤
2. create_evidence_dirs.py：取消程序目录创建（create_evidence_dirs 函数），只建 _files/ + 生成 catalog；CLI 输出同步
3. 武汉长源现场修复：_files.old → _files，删除 74 个空程序目录（执行前确认全空），catalog 重新生成
4. 部署：update-project.ps1 同步两个在审项目（含 .claude/skills/audit-execution-assistant、_shared/）
5. VERSION.json：bump-version.py 记录（feedback.md 硬规则）
6. 端到端验证：在武汉长源跑一次完整证据匹配流程（scan→match→status→update）

## Scope OUT (Must NOT have)

1. **广东长华程序 v1.0→v3.0 升级：用户批准时明确搁置，本次不执行**（C4 deferred；广东长华的 SKILL.md/脚本部署照做，程序文档升级另行安排）
2. 不新建 validate-catalog.py（R05 属 2026-07-29 整改方案的独立事项，不在本计划）
3. 不处理 9 项风险整改（R01-R09 待用户另行确认启动）
4. 不动 findings/index.json 既有数据（武汉长源 1 个待核实异常保留）
5. 不实现硬链接/符号链接/快捷方式方案（网盘环境下不可靠）
6. 不修改 evidence_catalog.py 的扫描/匹配逻辑（v2.0 逻辑已验证正确）
7. 不动"人力资源（总）"老项目（用户此前只授权执行第一项）
8. 不新增证据等级规则（R01 独立事项）

## Open questions

无（用户已拍板：取消程序目录、全部集中）

## Approval gate
status: awaiting-approval
<!-- 探索已穷尽、未知已答：SKILL.md 矛盾点、catalog 未用原因、广东长华程序列结构、目录内容均已验证。等待用户明确批准后写 .omo/plans/evidence-single-copy.md。 -->
