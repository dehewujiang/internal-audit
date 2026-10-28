# 最近一次工作记录

## 完成了什么
本次 session（2026-10-28 下半场）：**存货项目同步 + 覆盖惊魂 + 恢复**。

### 清单
1. 确认要同步：项目 skill 是复印件（10-27 部署时拷的），金源改了三个 skill，必须跑增量升级；升级不碰 `audit-topics/`、`memory/`、工作区，但其余目录是整目录重拷。
2. 先涨版本号（`2a12075` → 2026-10-28-1），再升级：7 upgraded / 0 failed，备份 `.backup/20261028-112909`。
3. 用户叫停质问：昨天试点四件改在项目上，会不会被盖？核对发现盖掉 2 件——`tools/make_chart.py` 被删、`settings.json` 的 hooks + permissions 被清空；另 2 件没事（三问基线系在 `audit-topics/`、钩子脚本在升级清单外）。
4. 用户拍恢复：SHA256 确认金源 `settings.json` 与项目现行一致后，旧 `settings.json` 整体拷回 + `make_chart.py` 拷回 + 方案文件拷进项目 `audit-topics/存货管理/`；逐项验证通过。
5. 项目现为 2026-10-28-1，试点四件 + 反写规则齐，可直接测。项目侧 `memory/pilot.md` 已补同步记录。

### 验证（机器证据）
- `Get-FileHash` 金源 vs 现行 `settings.json` 一致，才敢整体还原。
- 恢复后：settings 键为 hooks,permissions；`make_chart.py`、方案文件存在；项目 skill 含 Step 6 与"口说待验"（grep 确认）。
- 三问基线（`efficiency_baseline.md` + my-config 暂定值）升级前后一直在。

### 关键决策（用户拍板）
- 先恢复再继续：恢复动作经用户明确批准（"好，恢复吧"）。
- 根因：升级前没查项目本地独有文件；以后升级前先查（已记 feedback 硬规则）。

## 遇到问题
- 首跑升级报 "Already up to date"：`VERSION.json` 没涨就没有 diff 可升。以后 skill 改完先 bump 再升（金源侧已补 `2a12075`）。
- JSON 是单行文件，行级 diff 看不出东西，要 `ConvertFrom-Json` 按键比。

## 未完成事项
- **待真跑验收（不是完成）**：①制度分析后【制度摘】草稿 ②访谈回填当下【口说待验】三选一 ③手改处不覆盖。等用户跑存货项目时验。
- R09 再增一项：本次三 skill 改动 + 本次升级恢复，待真人抽查。
