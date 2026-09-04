#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ledger.py — 新桌子的管家（只管"往桌上写"，不管"查"和"拍照"）

[INPUT]:  ledger JSON 文件（见 ledger.schema.json v1.0）
[OUTPUT]: 更新后的 ledger JSON + 命令行回显
[POS]:    ledger/ 的写线零件，是 evidence_catalog.py（证据柜管家）的兄弟；
          查线（门卫读桌子）和拍照线（写前拍照）以后再接，这里只留好线头。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

规矩（写死的，不靠自觉）：
  1. 左边三格固定，只能写不能加格、不能改名
  2. 右边每条证据必须写"谁给的、啥时候给的"，缺一个就不让贴
  3. 每次只改桌上的一处，不碰其他格

用法:
    python ledger.py create 桌子.json --table "冲压车间废料多了"
    python ledger.py set-slot 桌子.json --slot 确定的毛病 --text "领料没签字"
    python ledger.py add-evidence 桌子.json --file "领料单7张" --from 班长 --when 审计当天
    python ledger.py show 桌子.json
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
DRAWERS = ["问话表", "检查表", "报告表"]
CHECKLIST = ["证据够了吗", "制度看全了吗", "红格看了吗"]


def blank_table(name: str) -> dict:
    """空桌子：三格占好，证据为空。"""
    return {
        "schema_version": SCHEMA_VERSION,
        "table": name,
        "left": [
            {"slot": s, "red": (s == "怀疑偷骗"), "text": "", "ref_finding_ids": []}
            for s in LEFT_SLOTS
        ],
        "right": [],
        "drawers": list(DRAWERS),
        "checklist": list(CHECKLIST),
    }


def load(path: Path) -> dict:
    """读桌子，格子不对就报错（桌子坏了不能往上写）。"""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"桌子版本不对：{data.get('schema_version')}，要 {SCHEMA_VERSION}")
    names = [x.get("slot") for x in data.get("left", [])]
    if names != LEFT_SLOTS:
        raise SystemExit(f"左边三格坏了：{names}")
    return data


def save(path: Path, data: dict) -> None:
    """写桌子。拍照线以后接在这里（写之前先拍一张）。"""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_create(args) -> None:
    path = Path(args.file)
    if path.exists():
        raise SystemExit(f"桌子已存在：{path}，换个名再开")
    save(path, blank_table(args.table))
    print(f"开好桌子：{args.table}")


def cmd_set_slot(args) -> None:
    """小李写左边：一次只写一格，格名必须对。"""
    if args.slot not in LEFT_SLOTS:
        raise SystemExit(f"没这格：{args.slot}，只能是 {LEFT_SLOTS}")
    path = Path(args.file)
    data = load(path)
    for x in data["left"]:
        if x["slot"] == args.slot:
            x["text"] = args.text
    save(path, data)
    print(f"写好：{args.slot}")


def cmd_add_evidence(args) -> None:
    """小王贴右边：谁给的、啥时候给的，缺一个不让贴。"""
    if not args.from_ or not args.when:
        raise SystemExit("证据必须写清谁给的(--from)、啥时候给的(--when)")
    path = Path(args.file)
    data = load(path)
    data["right"].append({
        "slot_id": args.slot_id,
        "file": args.file_,
        "from": args.from_,
        "when": args.when,
    })
    save(path, data)
    print(f"贴好证据：{args.file_}")


def cmd_link(args) -> None:
    """小张对单号：红格的怀疑对上问题单号，一次对一个。"""
    if args.slot not in LEFT_SLOTS:
        raise SystemExit(f"没这格：{args.slot}，只能是 {LEFT_SLOTS}")
    path = Path(args.file)
    data = load(path)
    for x in data["left"]:
        if x["slot"] == args.slot and args.finding not in x["ref_finding_ids"]:
            x["ref_finding_ids"].append(args.finding)
    save(path, data)
    print(f"对好：{args.slot} ↔ {args.finding}")


def cmd_show(args) -> None:
    data = load(Path(args.file))
    print(f"桌子：{data['table']}")
    for x in data["left"]:
        mark = "【红】" if x["red"] else ""
        print(f"  左{mark}{x['slot']}：{x['text'] or '（空）'}")
    print(f"  右：{len(data['right'])}条证据")
    for e in data["right"]:
        print(f"    - {e['file']}（{e['from']}，{e['when']}）")


def main() -> None:
    p = argparse.ArgumentParser(description="新桌子管家：只管往桌上写")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="开一张空桌子")
    c.add_argument("file")
    c.add_argument("--table", required=True)
    c.set_defaults(fn=cmd_create)

    c = sub.add_parser("set-slot", help="写左边一格")
    c.add_argument("file")
    c.add_argument("--slot", required=True, choices=LEFT_SLOTS)
    c.add_argument("--text", required=True)
    c.set_defaults(fn=cmd_set_slot)

    c = sub.add_parser("add-evidence", help="右边贴一条证据")
    c.add_argument("file")
    c.add_argument("--file", dest="file_", required=True)
    c.add_argument("--from", dest="from_", required=True)
    c.add_argument("--when", required=True)
    c.add_argument("--slot-id", default=None)
    c.set_defaults(fn=cmd_add_evidence)

    c = sub.add_parser("link-finding", help="左边一格对上问题单号")
    c.add_argument("file")
    c.add_argument("--slot", required=True, choices=LEFT_SLOTS)
    c.add_argument("--finding", required=True)
    c.set_defaults(fn=cmd_link)

    c = sub.add_parser("show", help="看桌子现状")
    c.add_argument("file")
    c.set_defaults(fn=cmd_show)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
