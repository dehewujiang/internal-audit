# 原文抽查 fixture（正反例）

供 `tests/test_source_reconciliation.py` 使用，验证 `validate-policy-analysis.py`
的「原文抽查」能真的报警、且不误报。

## 结构

```
workspace/                              ← 模拟 internal-audit-workspace/
├── documents/考勤管理规定_ocr.txt        ← 制度原文（条款用中文数字：第一条…第五条）
└── policy-analyses/
    ├── bad.json                        ← 反例：CP-003 引用「第99条」，原文中不存在
    └── good.json                       ← 正例：三个控制点引用的条款都在原文中
```

## 为什么单独测

原文抽查走**独立通道**（结果单列 `source_reconciliation` 字段，不参与 `action`/退出码），
而 `tests/prompt_snapshots/regression-check.py` 只比对退出码——独立通道天然覆盖不到。
所以本 fixture 由专项脚本断言，而非走回归基线。

## 顺带覆盖的场景

原文用中文数字（`第二条`）、JSON 用阿拉伯数字（`第2条`）——由 `clause_key()` 归一化后比对。
