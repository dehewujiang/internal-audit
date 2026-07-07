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
```

## 授权
level_0（全阶段可用）
