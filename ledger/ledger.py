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


def snaps_dir(path: Path) -> Path:
    """照片夹：跟桌子同名同目录，后缀 .snaps。"""
    d = path.parent / (path.stem + ".snaps")
    d.mkdir(exist_ok=True)
    return d


def snapshot(path: Path) -> None:
    """写之前拍一张，只留20张，多了扔最早的。开新桌不拍（没旧可回）。"""
    if not path.exists():
        return
    from datetime import datetime
    d = snaps_dir(path)
    (d / f"snap_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.json").write_bytes(path.read_bytes())
    snaps = sorted(d.glob("snap_*.json"))
    for old in snaps[:-20]:
        old.unlink()


def save(path: Path, data: dict) -> None:
    """写桌子：先拍照再写。"""
    snapshot(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_snaps(args) -> None:
    """看照片：有几张、啥时候拍的。"""
    d = snaps_dir(Path(args.file))
    snaps = sorted(d.glob("snap_*.json")) if d.exists() else []
    print(f"照片{len(snaps)}张")
    for s in snaps:
        print(f"  - {s.name}")


def cmd_rollback(args) -> None:
    """回头：整张桌子回到某张照片（回之前先给现在拍一张，不丢）。"""
    path = Path(args.file)
    snap = snaps_dir(path) / args.to
    if not snap.exists():
        raise SystemExit(f"没这张照片：{args.to}")
    data = load(path)
    save(path, data)  # 先给现在拍照
    path.write_bytes(snap.read_bytes())
    print(f"回到：{args.to}")


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


def _read_json(p: Path) -> dict:
    """读老账本，坏了就报错（不猜）。"""
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _is_fraud(f: dict) -> bool:
    return "舞弊" in str(f.get("category", ""))


def _short(title: str, n: int = 40) -> str:
    return title if len(title) <= n else title[:n] + "…"


def cmd_import(args) -> None:
    """老账搬家：只读老项目，原样抄进新桌子，老账一个字不动。

    抄写规矩：
      确定的毛病 ← 非舞弊类问题单的标题（校验已过，立得住的）
      怀疑偷骗   ← 舞弊类/高风险问题单的标题，自动对上单号
      说不清的信号 ← 待补充问题单 + DA观察（待现场验证）+ 证据不足的缺口
      右边证据   ← 问题单里的证据条（名/来源/日期原样抄，slot_id空着，
                   老项目没用证据柜所以没有槽位号）
    """
    ws = Path(args.workspace)
    findings_dir = ws / "internal-audit-workspace" / "findings"
    da_dir = ws / "internal-audit-workspace" / "design-assessments"
    paths = []
    if args.finding:
        paths = [findings_dir / f"{args.finding}.json"]
    else:
        paths = sorted(findings_dir.glob("F-*.json"))
    sure, red, signals, red_refs, sure_refs = [], [], [], [], []
    right = []
    for p in paths:
        if not p.exists():
            raise SystemExit(f"老账里没这张单：{p.name}")
        f = _read_json(p)
        fid = f.get("finding_id", p.stem)
        line = f"{fid} {_short(str(f.get('title', '')))}"
        if _is_fraud(f):
            red.append(line)
            red_refs.append(fid)
        elif str(f.get("status", "")) == "待补充":
            signals.append(f"{line}（待补充）")
        else:
            sure.append(line)
            sure_refs.append(fid)
        for e in f.get("evidence", []) or []:
            right.append({
                "slot_id": None,
                "file": f"{fid}：{e.get('name', '未命名')}",
                "from": e.get("source") or "未注明",
                "when": e.get("obtained_date") or "未注明",
            })
        for u in ((f.get("audit_team_notes") or {}).get("key_uncertainties") or []):
            signals.append(f"{fid}待查：{_short(str(u))}")
    if da_dir.exists() and not args.finding:
        for md in sorted(da_dir.glob("DA-*.md")):
            head = md.read_text(encoding="utf-8-sig").splitlines()
            title = head[0].lstrip("# ").strip() if head else md.stem
            signals.append(f"{title}（待现场验证）")
    table = blank_table(args.table)
    table["left"][0]["text"] = "；".join(sure)
    table["left"][0]["ref_finding_ids"] = sure_refs
    table["left"][1]["text"] = "；".join(red)
    table["left"][1]["ref_finding_ids"] = red_refs
    table["left"][2]["text"] = "；".join(signals)
    table["right"] = right
    out = Path(args.file)
    if out.exists():
        raise SystemExit(f"桌子已存在：{out}，换个名再搬")
    save(out, table)
    print(f"搬好：{len(sure)}确定/{len(red)}怀疑/{len(signals)}信号/{len(right)}证据 ← {ws.name}")
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

    c = sub.add_parser("import", help="老账搬家：抄进新桌子")
    c.add_argument("file")
    c.add_argument("--workspace", required=True)
    c.add_argument("--table", required=True)
    c.add_argument("--finding", default=None)
    c.set_defaults(fn=cmd_import)

    c = sub.add_parser("snaps", help="看照片")
    c.add_argument("file")
    c.set_defaults(fn=cmd_snaps)

    c = sub.add_parser("rollback", help="回到某张照片")
    c.add_argument("file")
    c.add_argument("--to", required=True)
    c.set_defaults(fn=cmd_rollback)

    c = sub.add_parser("show", help="看桌子现状")
    c.add_argument("file")
    c.set_defaults(fn=cmd_show)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
