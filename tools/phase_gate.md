# phase_gate

## 能力
- 管理审计项目阶段流转（地铁闸机模型）
- 显示当前阶段状态和退出条件
- 检查能否进入下一阶段
- 执行阶段前进（满足退出条件后自动切换）
- 执行阶段回退（需用户指定目标阶段和原因）
- 每次切换前自动备份 audit_state 快照（最近 20 份）
- 记录 audit_trail（前进/回退事件）

## 阶段定义
phase_0_init → phase_1_document_analysis → phase_1_5_interview → phase_2_program_generation → phase_3_execution → phase_4_report

## 退出条件（自动检查）
- Phase 1 → 1.5: policy-analyses/ 存在 ≥1 个 JSON + audit_topic 已设置
- Phase 1.5 → 2: 用户确认（人工决策点，无自动条件）
- Phase 2 → 3: audit-programs/ 存在 ≥1 个文件 + audit_purpose 已确认
- Phase 3 → 4: findings/ 存在 ≥1 个 F-*.json
- Phase 4 → end: reports/ 存在 ≥1 个文件

## 限制
- 不参与审计业务判断，只管阶段流转
- 回退必须由用户确认，AI 不得自行回退
- 退出条件检查是确定性的（文件存在性），不做内容质量判断

## 输入
- current-audit.json（status 字段）
- workspace 各目录的内容

## 输出
- JSON 格式的状态/转换结果
- 退出码：0=通过/成功，1=阻塞，2=错误

## 用法
```bash
python phase_gate.py status       # 显示当前状态
python phase_gate.py check        # 检查能否前进
python phase_gate.py advance      # 执行前进
python phase_gate.py rollback --to phase_1_document_analysis --reason "补充制度分析"
python phase_gate.py tool-check <script_name>                 # exit 0 = 放行，exit 1 = 拦截
python phase_gate.py tool-check <script_name> --force         # 跨阶段回退时用户确认后临时开放（记录 audit_trail）
python phase_gate.py checklist --workspace <项目根目录>      # 打勾纸：六句话看板，只看不拦（新桌子，转调 ledger/checklist.py）
```

## 阶段流转语义（与宪法「阶段流转规则」一致）

**前进规则**：每次准备进入下一阶段前，先运行 `check`，按 action 处理：

| action | exit code | 含义 | 处理 |
|--------|:---------:|------|------|
| `pass` | 0 | 前进 OK | 运行 `advance` |
| `block` | 1 | 退出条件未满足 | 列出缺失项，等用户决定 |
| `prompt_program_update` | 2 | 程序未覆盖所有风险线索 | 先执行 program-generator 增量更新模式（SKILL.md Step 0.5）补齐，补齐后重新运行 `check` |

- `--force` 可将 `prompt_program_update` 降级为 warning（放行但提示）；**不可降级 block**
- 被拦截（exit 1）时 AI 不得自行跳过，必须修复缺失项或等待用户决定

**回退规则**：
- 回退必须用户确认（用户说"回退到 Phase 1 补分析"），AI 不得自行回退
- 运行 `rollback --to <phase> --reason "<原因>"`，原因必填，写入 audit_trail

**闸机与自由区**：
- 闸机（`check`）= 确定性的代码检查，AI 不能改
- 闸机之间（每个 phase 内部）= AI 的自由决策空间（选什么方法、生成什么内容）
- AI 不能跳闸机、不能绕闸机、不能自己把闸机搬开

**工具分域**：每个阶段只暴露该阶段需要的工具脚本，详见 CLAUDE.md 的「Tool domain table」章节。执行任何 Python 脚本前，必须先跑 `tool-check <脚本名>` 确认当前阶段可用。跨阶段回退时，用户确认后使用 `--force` 临时开放。

## 授权
level_0（全阶段可用）
