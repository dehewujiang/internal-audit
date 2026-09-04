#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export.py — 桌子总览表格（签字存档用的那张皮）

[INPUT]:  ledger JSON 文件（ledger.schema.json v1.0）
[OUTPUT]: 总览 Excel（三页：左边三格 / 右边证据 / 抽屉打勾）
[POS]:    ledger/ 的表格零件，复用 _shared/scripts 的打印机芯（excel_core），
          是以前三张表之外的第四张，只管排版，不管结论对错。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

用法:
    python ledger/export.py 桌子.json 总览.xlsx
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_SHARED = Path(__file__).resolve().parent.parent / "_shared" / "scripts"
sys.path.insert(0, str(_SHARED))

from excel_core import ExcelCore


def main() -> None:
    if len(sys.argv) != 3:
        print("用法: python ledger/export.py 桌子.json 总览.xlsx")
        raise SystemExit(2)
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    left = data.get("left", [])
    core = ExcelCore(sys.argv[2])
    core.add_worksheet(
        "左边三格",
        ["格子", "标红", "内容", "对单号"],
        [[x.get("slot", ""), "是" if x.get("red") else "否",
          x.get("text", ""), "、".join(x.get("ref_finding_ids", []))] for x in left],
        col_widths=[14, 8, 80, 20],
    )
    core.add_worksheet(
        "右边证据",
        ["文件", "谁给的", "啥时候", "槽位号"],
        [[e.get("file", ""), e.get("from", ""), e.get("when", ""),
          e.get("slot_id") or ""] for e in data.get("right", [])],
        col_widths=[50, 24, 14, 12],
    )
    core.add_worksheet(
        "抽屉打勾",
        ["事项", "在哪"],
        [[t, "抽屉"] for t in data.get("drawers", [])]
        + [[c, "打勾纸"] for c in data.get("checklist", [])],
        col_widths=[24, 10],
    )
    core.save()
    print(f"总览表格：{sys.argv[2]}")


if __name__ == "__main__":
    main()
