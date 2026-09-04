#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_table.py — 报告前查桌子（丢东西就拦下，大模型绕不过去）

[INPUT]:  ledger JSON + 老项目根目录（读 findings/ 和 index.json，只读不写）
[OUTPUT]: 中文核对报告 + 退出码（0=放行, 2=拦下）
[POS]:    ledger/ 的报告前闸机，给 report-generator Step 2b 跑的；
          日常门卫（check.py）只提醒，这把是报告签字前的最后一道，红格没对单号也拦。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

拦的三件事（都是"会丢东西"，不管顺序和格式）：
  1. 单缺位：问题单在桌上没位子 → 写报告会漏
  2. 鬼号：桌上单号在目录里不存在 → 写报告会编
  3. 红格没对单号：怀疑没主 → 报告不敢发

用法:
    python ledger/audit_table.py --table 桌子.json --workspace D:\某个审计项目
"""

import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="报告前查桌子")
    ap.add_argument("--table", required=True)
    ap.add_argument("--workspace", required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.table).read_text(encoding="utf-8-sig"))
    fdir = Path(args.workspace) / "internal-audit-workspace" / "findings"
    files = {p.stem for p in fdir.glob("F-*.json")} if fdir.exists() else set()
    refs = set(sum([x.get("ref_finding_ids", []) for x in data.get("left", [])], []))
    blocks = []
    for fid in sorted(files - refs):
        blocks.append(f"单缺位：{fid}在桌上没位子，先搬（ledger.py import）")
    for fid in sorted(refs - files):
        blocks.append(f"鬼号：桌上{fid}在目录里不存在，先对单号（ledger.py link-finding）")
    left = {x.get("slot"): x for x in data.get("left", [])}
    red = left.get("怀疑偷骗", {}) or {}
    if red.get("text") and not red.get("ref_finding_ids"):
        blocks.append("红格有怀疑但没对单号，先对上再发报告")
    if blocks:
        print("拦下（报告先别发）：")
        for b in blocks:
            print(f"  - {b}")
        return 2
    print(f"放行：{len(files)}张单全在桌上有位，无鬼号")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
