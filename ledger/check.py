#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check.py — 门卫只读桌子（读线零件，不管"写"和"拍照"）

[INPUT]:  ledger JSON 文件（ledger.schema.json v1.0）
[OUTPUT]: 中文检查报告 + 退出码（0=放行, 1=提醒, 2=拦下）
[POS]:    ledger/ 的读线零件，是 validate-finding.py 等门口零件的接班人；
          以前翻6个房间，现在只读这一张桌子。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

门卫5件事（只看大事）：
  1. 左边三格都有字（桌子没写完不放行）
  2. 红格有字必须对上问题单号（没对上只提醒，不拦路）
  3. 右边每条证据有谁给的、啥时候给的（防手改坏账）
  4. 抽屉三张表都在（少了只提醒）
  5. 加 --workspace 才查：红格对上的高风险单子，必须有A/E级硬证据
     （旧规矩：高风险靠截图和口说立不住），没有就拦下

用法:
    python check.py 桌子.json
    python check.py 桌子.json --workspace D:\某个审计项目
"""

import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.0"
LEFT_SLOTS = ["确定的毛病", "怀疑偷骗", "说不清的信号"]


HARD_GRADES = {"A", "E"}


def _grades_of(finding: dict) -> set:
    """这张单子的证据硬度有哪些等级。"""
    return {str(e.get("reliability_grade", "")).upper() for e in finding.get("evidence", []) or []}


def check_grades(data: dict, workspace: Path, blocks: list) -> None:
    """第5件事：红格对上的高风险单子，没硬证据就拦下（旧宪法第3条）。"""
    findings_dir = workspace / "internal-audit-workspace" / "findings"
    left = {x.get("slot"): x for x in data.get("left", [])}
    for fid in (left.get("怀疑偷骗", {}) or {}).get("ref_finding_ids", []):
        p = findings_dir / f"{fid}.json"
        if not p.exists():
            blocks.append(f"红格对上的单子找不到：{fid}")
            continue
        f = json.loads(p.read_text(encoding="utf-8-sig"))
        if str(f.get("risk_level", "")) != "高":
            continue
        grades = _grades_of(f)
        if not (grades & HARD_GRADES):
            blocks.append(f"{fid}是高风险但没有A/E级硬证据（只有{','.join(sorted(grades)) or '无等级'}）")


def main() -> int:
    ap = argparse.ArgumentParser(description="门卫只读桌子")
    ap.add_argument("file")
    ap.add_argument("--workspace", default=None, help="老项目根目录，加了才查第5件事")
    args = ap.parse_args()
    path = Path(args.file)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    blocks, warns = [], []

    if data.get("schema_version") != SCHEMA_VERSION:
        blocks.append(f"桌子版本不对：{data.get('schema_version')}")
    left = {x.get("slot"): x for x in data.get("left", [])}
    for s in LEFT_SLOTS:
        if not (left.get(s) or {}).get("text"):
            blocks.append(f"左边格子没写完：{s}")
    red = left.get("怀疑偷骗", {})
    if red.get("text") and not red.get("ref_finding_ids"):
        warns.append("红格有怀疑但还没对上问题单号，记得补")
    for e in data.get("right", []):
        if not e.get("from") or not e.get("when"):
            blocks.append(f"证据缺来源：{e.get('file')}")
    if data.get("drawers") != ["问话表", "检查表", "报告表"]:
        warns.append("抽屉的表不全")
    if args.workspace:
        check_grades(data, Path(args.workspace), blocks)

    if blocks:
        print("拦下：")
        for b in blocks:
            print(f"  - {b}")
        return 2
    if warns:
        print("放行（有提醒）：")
        for w in warns:
            print(f"  - {w}")
        return 1
    print("放行：全对")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
