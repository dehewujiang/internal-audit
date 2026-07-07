# validate-policy-analysis

## 能力
- 对制度分析 JSON 执行确定性硬校验
- 检查项：schema 合规（必要数组存在）、schema_version 存在、控制点可追溯性、风险点结构完整性、控制缺口不是全部待确认
- 输出 block/warn/pass 三级判定
- 支持单文件和批量扫描

## 限制
- 只做结构检查，不评估分析质量
- 不做跨文件验证（由 document-organizer 负责）

## 输入
- policy-analyses/ 下的 .json 文件

## 输出
- 判定结果（block/warn/pass + 具体问题列表）

## 授权
level_0
