#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_source_reconciliation.py — 原文抽查会响性测试

[INPUT]:  tests/fixtures/source_reconciliation/workspace/（documents/ + policy-analyses/ 正反例）
[OUTPUT]: 断言结果 + exit 0=全通过 / 1=有失败
[POS]:    tests 的专项测试。补 regression-check.py 的盲区——原文抽查走独立通道、
          不改退出码，exit-code 基线比对天然覆盖不到，只能靠本脚本断言。
[PROTOCOL]: 改动 validate-policy-analysis.py 的原文抽查处时，同步核对本测试的正反例。
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "_shared/scripts/validate-policy-analysis.py"
WS = REPO_ROOT / "tests" / "fixtures" / "source_reconciliation" / "workspace"


def run_case(name):
    """跑单个 JSON，取回 source_reconciliation 结果"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(WS / "policy-analyses" / name),
         "--json", "--workspace", str(WS)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(proc.stdout)[0]["source_reconciliation"]


def main():
    failures = []

    bad = run_case("bad.json")
    if bad.get("status") != "checked":
        failures.append(f"反例未被检查（status={bad.get('status')}）")
    elif not bad.get("cited_missing"):
        failures.append("反例应报「引用了原文不存在的条款」，实际未报")

    good = run_case("good.json")
    if good.get("status") != "checked":
        failures.append(f"正例未被检查（status={good.get('status')}）")
    elif good.get("cited_missing"):
        failures.append(f"正例不应报警，实际报了: {good['cited_missing']}")

    if failures:
        for f in failures:
            print(f"🔴 {f}")
        print(f"\nFAIL — {len(failures)} 项断言未通过")
        sys.exit(1)

    print(f"✅ 反例报警正确: {bad['cited_missing']}")
    print(f"✅ 正例无误报: {len(good['cited_ok'])} 条条款引用全部命中")
    print("\nPASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
