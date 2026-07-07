# validate-program

## 能力
- 对审计程序 Markdown 文件执行确定性硬校验
- 检查项：无占位符（_X_ / {{}}）、量化标准非开关型、轨道激活标识、公司事实引用、风险-程序覆盖
- 输出 block/warn/pass 三级判定
- 支持单文件和批量扫描

## 限制
- 只做格式和结构检查，不评估程序质量（由 program-quality-evaluator 负责）
- 不做语义判断（"这个风险描述是否合理"）

## 输入
- audit-programs/ 下的 .md 文件

## 输出
- 判定结果（block/warn/pass + 具体问题列表）

## 授权
level_0
