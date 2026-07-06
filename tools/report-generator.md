# report-generator

## 能力
- 读取 findings/ 中的所有审计发现并按风险级别和 origin 分类
- 选择适用的报告模板并填充变量
- 生成结构化审计报告（含综合结论四要素）
- 支持常规报告、专项报告、舞弊调查报告、整改跟踪报告
- 输出为 Markdown（可导出 DOCX/PDF）

## 限制
- 必须已有 finding 才能生成报告
- 不能生成无审计依据的发现
- 输出前必须完成质量评估

## 输入
- findings/: 审计发现文件
- design-assessments/: 设计观察（作为背景，不作为结论）
- about-me.md: 公司背景

## 输出
- reports/审计报告_{主题}_{YYYYMMDD}.md

## 授权
level_0
