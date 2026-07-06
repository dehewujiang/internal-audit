# 分析示例

## 示例1：分析采购管理制度

**用户输入**：
> 帮我分析这份采购管理制度，提取控制点并输出程序基线

**Skill执行**：
1. 读取文档，识别为"管理制度-采购管理"
2. 提取控制点：
   - 审批权限控制：5万元以上需总经理审批
   - 职责分离控制：采购与验收分离
   - 定期检查控制：每季度评估供应商
   - 文档记录控制：采购台账完整记录
3. 识别风险点：
   - 权限集中：采购员兼验收
   - 监督盲区：废料处置无监督
4. 生成baseline_audit_program
5. 输出Markdown + JSON

**输出**：
- `internal-audit-workspace/policy-analyses/采购管理制度分析报告.md`
- `internal-audit-workspace/policy-analyses/采购管理制度分析报告.json`

---

## 示例2：批量分析内控手册

**用户输入**：
> 分析 internal-audit-workspace/documents/ 文件夹中的所有制度文件

**Skill执行**：
1. 扫描文件夹，识别所有制度文档
2. 建立"业务领域-文件"映射表
3. 逐一分析每个文档
4. 跨文件交叉验证
5. 汇总控制点清单
6. 识别系统性风险
7. 输出控制点清单和风险点清单（JSON+Markdown）

**输出**：
- `internal-audit-workspace/policy-analyses/综合制度分析报告.md`
- `internal-audit-workspace/policy-analyses/综合制度分析报告.json`
