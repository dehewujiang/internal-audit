# index.json Schema

> **使用说明**：每次生成或修改 finding 后，必须同步更新 `internal-audit-workspace/findings/index.json`。如果不存在则新建。

## 硬规则

- ❌ 禁止生成 finding 但不更新 index.json
- ❌ 禁止手动编辑 index.json 与实际 finding 不一致
- ❌ 禁止跳过 index.json 的生成

**自动扫描规则**：每次更新前，扫描 `internal-audit-workspace/findings/` 下所有 JSON 文件，确保 index.json 与实际情况一致。

## 完整格式（schema v1.1.0）

```json
{
  "schema_version": "1.1.0",
  "version": "1.0",
  "total_findings": 1,
  "by_year": {
    "2026": { "count": 1, "ids": ["F-2026-001"] }
  },
  "by_program": {
    "存货管理审计": ["F-2026-001"]
  },
  "by_risk": {
    "高": [],
    "中": ["F-2026-001"],
    "低": []
  },
  "by_status": {
    "待整改": ["F-2026-001"],
    "整改中": [],
    "已整改": [],
    "延期": []
  },
  "by_category": {
    "内控缺陷": ["F-2026-001"],
    "舞弊风险": [],
    "合规问题": [],
    "效率问题": []
  },
  "by_origin": {
    "design": [],
    "execution": ["F-2026-001"]
  },
  "by_keyword": {
    "审批": ["F-2026-001"]
  },
  "by_related_control": {
    "CP-001": ["F-2026-001"]
  }
}
```
