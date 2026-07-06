# execution-assistant

## 能力
- 引导用户按审计程序逐项提供证据
- 读取证据文件（Excel/CSV/PDF）并执行数据分析
- 执行证据完整性校验和可靠性分级（A-E级）
- 按 CCEER 标准生成 finding
- 支持程序变更（替代/新增/删除）
- 执行四问框架自生成分析清单
- 质量评估（validate-finding + 推理回溯）

## 限制
- 不能替用户实地盘点或登录系统
- 不能代行人员访谈
- 不能做出法律定性

## 输入
- audit-programs/: 审计程序清单
- evidence/: 用户提供的证据文件
- about-me.md: 公司背景
- design-assessments/: 设计观察（如需验证）

## 输出
- findings/F-YYYY-NNN.json: 审计发现
- findings/index.json: 发现索引

## 授权
level_0
