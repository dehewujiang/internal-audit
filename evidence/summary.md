# 本次交付（2026-10-20）：勾稽口径卡 schema v1.0 + 校验器

1. 新增 `validate-relations.py`：口径缺项/容差未定/键未验唯一/type 越界/filter 越界一律拦下（exit 2），词典外字段只警告。
2. 新增 `field_dictionary.json`（6 词，含拍板的 currency_unit/tax）+ `relations.example.json` 模板；口径卡放项目 `reconcile/` 下，升级不覆盖，无需改部署脚本。
3. OPS.md 已同步三处：常见情况、速查表、近期更新。验证 GREEN 9/9，见 run.json。

验收：`python _shared/scripts/validate-relations.py _shared/reconcile/relations.example.json` 应出 action=pass。
