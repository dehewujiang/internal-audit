#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export.py — 桌子总览表格（签字存档用的那张皮）

[INPUT]:  ledger JSON 文件（ledger.schema.json v1.2）[[ --workspace 项目根目录]]
[OUTPUT]: 总览 Excel（三页：左边三格 / 右边证据 / 抽屉打勾；带 --workspace
          时多一页"作废一览"：程序文件里盖了章的行，签字时看得见但不计数）；
          退出码 0=成功, 2=失败或崩溃
[POS]:    ledger/ 的表格零件，复用 _shared/scripts 的打印机芯（excel_core），
          是以前三张表之外的第四张，只管排版，不管结论对错。
          抽屉页两种格式都认：老桌子（1.0）的纯名字、新桌子的 {name,path,status}。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

用法:
    python ledger/export.py 桌子.json 总览.xlsx [--workspace D:\某个审计项目]
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


def drawer_row(d) -> list:
    """一行抽屉。老桌子（1.0）的抽屉是纯名字，新桌子是 {name, path, status}——两种都认，
    否则导一张老桌子会直接抛异常（看着像"工具坏了"，实际只是版本不同）。"""
    if isinstance(d, dict):
        return [d.get("name", ""), d.get("path", ""), d.get("status", "")]
    return [str(d), "", ""]


def deleted_rows(ws: Path) -> list:
    """作废一览：程序文件里盖了章的行（编号/标题/原因）。只管排版，不管结论。
    解析器坏了/没程序文件 → 空（导出不因看不清而崩）。"""
    d = ws / "internal-audit-workspace" / "audit-programs"
    mds = sorted(d.glob("*.md")) if d.is_dir() else []
    if not mds:
        return []
    try:
        sys.path.insert(0, str(_SHARED))
        import program_ir_parser as parser
    except Exception:
        return []
    rows = []
    for p in mds:
        try:
            ir = parser.build_ir(p)
        except Exception:
            continue
        for r in ir.get("risk_register", []) or []:
            if r.get("is_deleted"):
                rows.append([r.get("raw_id", ""), r.get("title", "")[:40],
                             "风险", "作废（原纸留痕，不计数）"])
        for s in ir.get("steps", []) or []:
            if s.get("is_deleted"):
                rows.append([s.get("step_id", ""), s.get("title", "")[:40],
                             f"程序{s.get('track', '')}", "作废（原纸留痕，不计数）"])
    return rows


def main() -> None:
    if len(sys.argv) not in (3, 5):
        print("用法: python ledger/export.py 桌子.json 总览.xlsx [--workspace 项目根目录]")
        raise SystemExit(2)
    ws = None
    if len(sys.argv) == 5:
        if sys.argv[3] != "--workspace":
            print("用法: python ledger/export.py 桌子.json 总览.xlsx [--workspace 项目根目录]")
            raise SystemExit(2)
        ws = Path(sys.argv[4])
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
        ["事项", "在哪", "什么状态"],
        [drawer_row(d) for d in data.get("drawers", [])]
        + [[c, "打勾纸", ""] for c in data.get("checklist", [])],
        col_widths=[24, 60, 14],
    )
    if ws is not None:
        core.add_worksheet(
            "作废一览",
            ["编号", "标题", "种类", "说明"],
            deleted_rows(ws),
            col_widths=[14, 50, 12, 30],
        )
    core.save()
    print(f"总览表格：{sys.argv[2]}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # 未预期崩溃 → exit(2)。导出失败必须能和"正常出表"区分开
        import traceback
        traceback.print_exc()
        sys.exit(2)
