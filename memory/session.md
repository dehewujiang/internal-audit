# 最近一次工作记录

## 完成了什么
本次 session（2026-08-04）完成了「证据 v2.0 集中存储工作流修复」计划（`.omo/plans/evidence-single-copy.md`）。

### 计划执行
1. 检查 5 个已部署审计项目，升级武汉长源到最新版（2026-07-21-2）
2. 修复 `audit-execution-assistant/SKILL.md` 证据路径矛盾——规则层（evidence/{project_name}/{程序编号}_{程序关键词}/）与界面示例层（evidence/_files/）打架，统一为 `evidence/_files/`；catalog 检查从"用户说帮我匹配才触发"改为 Step 1 默认动作
3. 修改 `_shared/scripts/create_evidence_dirs.py`：取消按程序建目录（原来一次建 74 个空目录），只建 `evidence/_files/` + `_evidence_catalog.json`；CLI 输出同步
4. bump VERSION.json `2026-07-26-3 → 2026-08-04-1`，commit `b4a0611` `fix(evidence): 证据 v2.0 集中存储工作流修复`（只含 3 文件：VERSION.json、SKILL.md、create_evidence_dirs.py）
5. 部署到武汉长源 + 广东长华（`update-project.ps1`，两项目 VERSION.lock = 2026-08-04-1，SKILL.md 与脚本逐字节一致）
6. 端到端验证：武汉长源重新生成 `_evidence_catalog.json`（162 槽位），scan→match→status→update 闭环跑通（filled 0→1→还原 0）
7. 武汉长源现场清理：`evidence/_files.old` → `_files`（改名）；删除 70 个确认空程序目录；**B1.1（20 文件）和 L1.1（40 文件）含真实证据按保护规则保留**（B1.1 的文件被 `findings/B1.1_考勤数据手工传递篡改_待核实异常.json` 的 evidence.files 硬编码引用，删除=销毁证据）
8. 最终验证波 F1-F4 全部 APPROVE（计划合规/代码质量/真机实测/范围保真）

## 为什么这样做
证据 v2.0 架构（2026-07-26 部署）虽然把存储集中到 `_files/`，但 SKILL.md 的规则层还在教 LLM 按程序建子目录，`create_evidence_dirs.py` 也在一次建 74 个空目录——规则和实现互相矛盾，集中存储名存实亡。本次修复让规则层、脚本层、界面示例层三方对齐到同一套路径约定。

## 遇到问题
- 探索阶段只抽样验证了 2 个目录（A1.1 和 `_files.old`）就假设"74 个目录全空"，实际 B1.1/L1.1 有 60 个真实证据文件——计划假设被推翻，靠执行时的保护规则（finding 引用的证据不删）兜住了。详见 `feedback.md` 2026-08-04 教训。
- `bump-version.py --commit` 只 add VERSION.json（commit 消息是 `chore: bump...`），想把代码改动一起 commit 需要手动 add 目标文件。本次用"先 bump 后手动 add 三文件再 commit"满足"一个 commit 含三文件+业务关键词"。

## 未完成事项
- 广东长华程序 v1.0→v3.0 升级仍待办（用户搁置，缺"取证方式"列无法生成 catalog）
- B1.1/L1.1 目录 60 个证据文件是否迁入 `_files/` 及同步更新 finding 引用路径——待用户决策（可选）

## 下一步建议
1. 用户决策 B1.1/L1.1 证据文件迁移问题（迁入 `_files/` 并更新 finding 引用，或维持现状）
2. 广东长华程序升级排期（需先补"取证方式"列）
3. 回到 9 项风险整改（`风险整改方案_2026-07-29.md`）阶段一：R01→R02→R03