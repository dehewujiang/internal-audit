#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
progress_report.py — 风险进度表（一页纸看到每条风险走到哪了）

[INPUT]:  项目根目录（读 audit-programs/*.md + findings/F-*.json +
          audit-table/*.json + evidence/_evidence_catalog.json）
[OUTPUT]: 进度表 Excel（风险进度一页：编号/名称/哪来的/查到哪步/
          问题单/谁手里/啥状态/证据/桌位）；退出码 0=成功, 2=失败
[POS]:    report-generator/script 的对外汇报零件，复用 _shared 的解析器
          与打印机芯；只管排版，不管结论对错。作废行照列（标"作废"），不计数。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

用法:
    python progress_report.py --workspace D:\某个审计项目 --out 进度表.xlsx
"""

import argparse
import json
import sys
from pathlib import Path


def find_shared():
    p = Path(__file__).resolve().parent
    for _ in range(10):
        if (p / '_shared' / 'scripts').is_dir():
            return p / '_shared' / 'scripts'
        p = p.parent
    raise FileNotFoundError("Cannot locate _shared/scripts/")


sys.path.insert(0, str(find_shared()))
from excel_core import ExcelCore  # noqa: E402
import program_ir_parser as parser  # noqa: E402


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def build_rows(iw: Path) -> list:
    """每条风险一行。缺纸就空着，不崩。"""
    risks, steps = [], []
    for md in sorted((iw / "audit-programs").glob("*.md")) if (iw / "audit-programs").is_dir() else []:
        try:
            ir = parser.build_ir(md)
        except Exception:
            continue
        risks.extend(ir.get("risk_register", []) or [])
        steps.extend(ir.get("steps", []) or [])

    findings = {}
    for fp in sorted((iw / "findings").glob("F-*.json")) if (iw / "findings").is_dir() else []:
        f = _read_json(fp)
        fid = f.get("finding_id") or fp.stem
        findings[fid] = f

    tables = []
    for tp in sorted((iw / "audit-table").glob("*.json")) if (iw / "audit-table").is_dir() else []:
        tables.append(_read_json(tp))

    catalog = _read_json(iw / "evidence" / "_evidence_catalog.json")
    slot_filled = {}
    for it in catalog.get("items", []) or []:
        if it.get("file"):
            for code in it.get("source_programs", []) or []:
                slot_filled[code] = True

    def table_slot(fid, rid):
        for t in tables:
            for x in t.get("left", []) or []:
                if fid and fid in (x.get("ref_finding_ids") or []):
                    return x.get("slot", "") + "（已对单）"
        for t in tables:
            for x in t.get("left", []) or []:
                if rid and rid in (x.get("text") or ""):
                    return x.get("slot", "")
        return "未上桌"

    rows = []
    for r in risks:
        rid = r.get("raw_id", "") or r.get("risk_id", "")
        if r.get("is_deleted"):
            rows.append([rid, (r.get("title", "") or "")[:40], r.get("type") or "推演",
                         "作废（原纸留痕）", "-", "-", "作废不计数", "-",
                         table_slot("", rid) if table_slot("", rid) != "未上桌" else "已下桌"])
            continue
        covering = [s for s in steps
                    if not s.get("is_deleted")
                    and r.get("risk_id") in (s.get("risk_refs") or [])]
        procs = "、".join(s.get("step_id", "") for s in covering) or "-"
        hit = [fid for fid, f in findings.items()
               if set(f.get("related_procedures", []) or [])
               & {s.get("step_id", "") for s in covering}]
        fid = hit[0] if hit else ""
        f = findings.get(fid, {})
        who = f.get("responsible", "-") or "-"
        status = f.get("status", "未立单") or "未立单"
        ev = f.get("evidence", []) or []
        if ev:
            ev_txt = f"单上有{len(ev)}份"
        elif any(slot_filled.get(s.get("step_id", "")) for s in covering):
            ev_txt = "柜里有"
        else:
            ev_txt = "缺"
        rows.append([rid, (r.get("title", "") or "")[:40], r.get("type") or "推演",
                     procs, fid or "-", who, status, ev_txt, table_slot(fid, rid)])
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="风险进度表（一页纸看到每条风险走到哪了）")
    ap.add_argument("--workspace", required=True, help="项目根目录")
    ap.add_argument("--out", required=True, help="输出 Excel 文件")
    args = ap.parse_args()

    iw = Path(args.workspace) / "internal-audit-workspace"
    rows = build_rows(iw)
    core = ExcelCore(args.out)
    core.add_worksheet(
        "风险进度",
        ["风险编号", "风险名称", "哪来的", "查到哪步", "问题单",
         "谁手里", "啥状态", "证据", "桌位"],
        rows,
        col_widths=[12, 30, 12, 24, 14, 14, 12, 12, 18],
        default_height=40,
        freeze_header=True,
        alt_row_colors=True,
    )
    core.save()
    print(f"进度表：{args.out}（{len(rows)} 条风险）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
