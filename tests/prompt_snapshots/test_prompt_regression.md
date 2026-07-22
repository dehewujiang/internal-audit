# Prompt 回归测试指南

## 何时使用

当以下任一文件被修改后，应执行回归测试：
- `audit-execution-assistant/SKILL.md`
- `audit-execution-assistant/references/intuition_engine.md`
- `audit-execution-assistant/references/evidence_standards.md`
- `internal-audit-program-generator/SKILL.md`

## 测试步骤

### 1. 对比快照
```bash
# 对比当前 prompt 与快照的差异
diff -u tests/prompt_snapshots/<name>.snap <(提取当前版本的对应prompt段落)
```

### 2. 判定变更意图
- 差异为有意修改 → 更新快照文件，在提交信息中说明原因
- 差异为意外漂移 → 回滚到快照版本
- 不确定 → 在隔离的测试项目中用旧版和新版分别生成同一个 finding，对比结果

### 3. 关键检查点

| 检查项 | 期望行为 |
|--------|---------|
| CCEER 五要素 | Finding 必须包含全部五个要素，缺一不可 |
| 证据等级 | 高风险 finding 必须有 A 或 E 级证据 |
| 停表词 | 不得出现"操作人员疏忽"等 27 个停表词 |
| 根因深度 | 至少追溯到 COSO 第 2 层 |
| 法律定性 | 不得出现"构成舞弊"等法律结论 |
| 对抗验证 | 轨道B 必须执行红蓝队对抗 |
