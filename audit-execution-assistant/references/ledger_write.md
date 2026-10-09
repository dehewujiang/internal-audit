# 上桌写结论与缺口记账（ledger_write）

> SKILL.md"输出格式"节中写桌子命令串的完整细节。正文只留顺序铁律，干活时读这里。

结论**只写桌子**，不再写入 `findings/F-YYYY-NNN.json`（旧格式已停写，2026-10 关双轨）。
结论的行文结构仍按 [finding_schema.md](./finding_schema.md) 组织（标题/状况/原因/影响/建议），只是落点从文件改成桌子行。

**上桌前必做**：
- 所有 evidence 条目标记 `reliability_grade`
- 高风险 finding 必须有 ≥1 个 A级或E级证据（上桌后由门卫复核）
- `storage_path` 从 evidence 目录读取时必填实际路径
- 分析过程（证据链、推理）写底稿：`working-papers/F-xxx.md`

**上桌后必做（最终门卫，不可跳过）**：
- 运行 `python ledger/check.py --workspace <项目根目录>` 查高风险硬度
- 红格无 A/E 级硬证据 → 当场补证据或降级，不许带着红格往下走
- 草稿期的 `validate-finding.py` 检查照旧（只查初稿内容质量，不变）

### index.json 停写说明

`findings/index.json` 已停写（2026-10 关双轨）：不生成、不更新、不扫描。
查询/报告/吵架一律读桌子。旧项目冻结归档，不迁移。

**写桌子**（桌子在 `internal-audit-workspace/audit-table/*.json`，建项目时已开好；找不到就停下报告，不要跳过——宪法#12）：
顺序铁律：**先贴证据，再上桌**——红格（怀疑偷骗）无 A/E 级硬证据会被写入口当场拒收（exit 2）：
- 证据 → `python ledger/ledger.py add-evidence <桌子.json> --file <文件名> --from <谁给的> --when <啥时候> --grade <A/B/C/D/E 照实标> --room 执行取证 --ref F-xxx`
- 非舞弊问题单 → `python ledger/ledger.py add-line <桌子.json> --slot 确定的毛病 --text <结论> --room 执行取证 --ref F-xxx --status 已确认`
- 舞弊问题单 → `python ledger/ledger.py add-line <桌子.json> --slot 怀疑偷骗 --text <结论> --room 执行取证 --ref F-xxx --status 已确认`（无 A/E 会被拒收；证据不够就降格写"说不清的信号"）
- 对单号 → `python ledger/ledger.py link-finding <桌子.json> --slot <格> --finding F-xxx`
- 结论从任务板来 → 先结任务再上桌（顺序：证据→结论→销任务）：
  查实 → `python ledger/ledger.py close-task <桌子.json> --id <T-xxx> --verdict 已结 --finding F-xxx`；
  查否 → `python ledger/ledger.py close-task <桌子.json> --id <T-xxx> --verdict 作废 --reason "<哪条证据推翻了>"`。
  已结不带单号会被拒收（防任务无声消失）；结论文本上桌仍走上面的 `add-line`。
- 分析过程（证据链、推理）写底稿：`working-papers/F-xxx.md`
- 收料已删除（A6），结论直写上桌。桌子是账本（记结论），底稿是备查（记过程）。
（`import` 只用于**老项目整桌搬家**，日常不用——桌子已存在时它按设计拒绝。）

**证据缺失必须记账（宪法#9）**：证据完整性校验不通过时，**禁止**停在"证据不足，等待补充"——
必须把"证据为什么不存在"本身当成一件要查的事，写进信号格，三个方向一个不能少：
```
python ledger/ledger.py add-gap <桌子.json> --finding F-xxx --missing "缺的是哪份证据"

**查与说**（用户说人话，不用记命令）：用户说"查F-xxx的来龙去脉" → 跑
`python _shared/scripts/queries.py lineage F-xxx`（八段一次看全）；用户说"跟对方谈F-xxx"或"沟通卡" →
跑 `python _shared/scripts/queries.py brief F-xxx`（四段发言稿一次念完）。
```
记下的每条缺口都带三种可能：业务未发生 / 管理缺失未留痕 / 证据被消除，执行时逐条追问。
