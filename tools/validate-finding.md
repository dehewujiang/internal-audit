# validate-finding

## 能力
- 对 finding JSON 执行确定性硬校验
- 检查项：schema合规性、根因分析存在性、根因深度（高风险禁止停在表面）、CCEER五要素完整性、证据等级、直觉引擎完整性、根因与证据等级匹配
- 输出 block/warn/pass 三级判定
- 支持单个 finding 和批量扫描

## 限制
- 只能校验已生成的 finding JSON，不能修改
- 没有审计推理能力，只做确定性检查

## 输入
- findings/F-YYYY-NNN.json: 单个发现
- 或 findings/ 目录: 批量扫描

## 输出
- 判定结果（block/warn/pass + 具体问题列表）

## 授权
level_0
