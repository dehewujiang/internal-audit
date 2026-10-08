#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ledger.py — 新桌子的管家（只管"往桌上写"，不管"查"和"拍照"）

[INPUT]:  ledger JSON 文件（见 ledger.schema.json v1.2）+ 老项目根目录（收料时读）
[OUTPUT]: 更新后的 ledger JSON + 命令行回显；退出码 0=成功, 1=明确拒绝(消息), 2=崩溃兜底
[POS]:    ledger/ 的写线零件，是 evidence_catalog.py（证据柜管家）的兄弟；
          查线（门卫读桌子）和拍照线（写前拍照）以后再接，这里只留好线头。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

规矩（写死的，不靠自觉）：
  1. 左边三格固定，只能写不能加格、不能改名
  2. 右边每条证据必须写"谁给的、啥时候给的"，缺一个就不让贴
  3. 每次只改桌上的一处，不碰其他格
  4. 直接写桌：各房间结论直写上桌，不再经收料中转；
     新假设先落任务板（待查），查实转事实行（A6 收料/搬家已删除）

用法:
    python ledger.py create 桌子.json --table "冲压车间废料多了"
    python ledger.py set-slot 桌子.json --slot 确定的毛病 --text "领料没签字"
    python ledger.py add-evidence 桌子.json --file "领料单7张" --from 班长 --when 审计当天
    python ledger.py add-gap 桌子.json --finding F-2026-003 --missing "绩效评分原始记录"
    python ledger.py add-task 桌子.json --title "钢筋回扣疑似内外勾结" --room 检查单 --ref R-010
    python ledger.py close-task 桌子.json --id T-001 --verdict 已结 --finding F-2026-010
    python ledger.py show 桌子.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.3"
LEFT_SLOTS = ["确定的毛病", "怀疑偷骗", "说不清的信号"]
TASK_STATUSES = ["待查", "已结", "作废"]
DRAWER_NAMES = ["问话表", "检查表", "报告表"]
CHECKLIST = ["证据够了吗", "制度看全了吗", "红格看了吗"]

# 落格规则（ledger.schema.json 的「落格规则」就是这一条，改这里要同步改那里）：
#   来源自带的状态字段 → 格；跨文件覆盖＝别的制度里有，不算缺失，不上桌；
#   涉及舞弊 → 红格；没状态字段、或状态说不清的 → 信号格
FRAUD_WORDS = ("舞弊", "贪", "侵占", "回扣", "受贿", "私分", "挪用", "串通", "虚假报")

# 写入口硬度门：红格（怀疑偷骗）只认 A/E 级硬证据（宪法#3）
HARD_GRADES = {"A", "E"}
RED_SLOT = "怀疑偷骗"


def _hard_grades(data: dict, ref: str) -> set:
    """桌上已有的硬证据等级。有单号只认对上号的；空单号查全桌。"""
    grades = set()
    for e in data.get("right", []):
        g = str(e.get("grade", "")).upper()
        if g not in HARD_GRADES:
            continue
        if ref:
            if ((e.get("source") or {}).get("ref") or "") == ref:
                grades.add(g)
        else:
            grades.add(g)
    return grades


def _sheet_line(args, action: str, message: str, tool: str = "ledger") -> None:
    """答卷行（A6）：--json 才追一行 SHEET，人话原样不动，退出码不动。"""
    if getattr(args, "json", False):
        print("SHEET:" + json.dumps({"tool": tool, "action": action,
                                     "message": message}, ensure_ascii=False))


def _say(args, action: str, human: str) -> None:
    """成功行：人话照打，--json 再追答卷。"""
    print(human)
    _sheet_line(args, action, human)


def _refuse(code_msg: str, args=None) -> None:
    """写入口拒收：话说在 stdout（LLM 和人都看得见），码用 2（拦下）。
    --json 时追答卷 action=block。"""
    print(code_msg)
    _sheet_line(args, "block", code_msg)
    raise SystemExit(2)


def blank_table(name: str) -> dict:
    """空桌子：三格占好，证据为空，抽屉三个入口空着等填，收料本子空着，任务板空着。"""
    return {
        "schema_version": SCHEMA_VERSION,
        "table": name,
        "left": [
            {"slot": s, "red": (s == "怀疑偷骗"), "text": "", "ref_finding_ids": []}
            for s in LEFT_SLOTS
        ],
        "right": [],
        "drawers": [{"name": n, "path": "", "status": ""} for n in DRAWER_NAMES],
        "checklist": list(CHECKLIST),
        "ingested": {},
        "tasks": [],
    }


def load(path: Path) -> dict:
    """读桌子，格子不对就报错（桌子坏了不能往上写）。

    老桌子就地升级，不作废：
      1.0 的抽屉只记了三个表名 → 1.1 起每张还记"在哪、什么状态"
      1.1 没有 ingested      → 1.2 起记"哪几条是机器收上来的"，收料才不会重复
      1.2 没有 tasks         → 1.3 起账上多一块任务板（一条假设一个任务）
    硬拒绝会把"版本号变了"升级成"以前的桌子全打不开"。
    """
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    ver = data.get("schema_version")
    if ver != SCHEMA_VERSION:
        if ver not in ("1.0", "1.1", "1.2"):
            raise SystemExit(f"桌子版本不对：{ver}，要 {SCHEMA_VERSION}")
        if ver == "1.0":
            data["drawers"] = [
                d if isinstance(d, dict) else {"name": d, "path": "", "status": ""}
                for d in data.get("drawers", [])
            ]
        data.setdefault("ingested", {})
        data.setdefault("tasks", [])
        data["schema_version"] = SCHEMA_VERSION
    names = [x.get("slot") for x in data.get("left", [])]
    if names != LEFT_SLOTS:
        raise SystemExit(f"左边三格坏了：{names}")
    return data


def snaps_dir(path: Path) -> Path:
    """照片夹：跟桌子同名同目录，后缀 .snaps。"""
    d = path.parent / (path.stem + ".snaps")
    d.mkdir(exist_ok=True)
    return d


def history_path(path: Path) -> Path:
    """流水文件：跟桌子同名同目录，后缀 .history.jsonl，只增不减。"""
    return path.parent / (path.stem + ".history.jsonl")


def save(path: Path, data: dict, op: str = "") -> None:
    """写桌子：先写临时文件再改名（断电不留半条），再追记流水一行。

    旧照片（.snaps）只读保留，取证用，不再新增——A5 起流水代替拍照。
    """
    from datetime import datetime
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, indent=2)
    tmp = path.parent / (path.stem + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, path)
    row = {"at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "op": op or "落盘",
           "table": data.get("table", "")}
    with history_path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def cmd_snaps(args) -> None:
    """看照片：有几张、啥时候拍的。"""
    d = snaps_dir(Path(args.file))
    snaps = sorted(d.glob("snap_*.json")) if d.exists() else []
    print(f"照片{len(snaps)}张")
    for s in snaps:
        print(f"  - {s.name}")


def cmd_rollback(args) -> None:
    """回头已取消（A4）：账只增不减，不盖文件。

    照片（.snaps）保留只增不减，紧急恢复走用户手动拷文件。
    日常改道：新线索 add-task 插任务，结论有误 close-task 标作废另起行。
    本次一个字不写，直接拒收。
    """
    _refuse(
        "拒收：回头已取消，账只增不减（本次一个字没写）\n"
        "（新线索 add-task 插任务往前走；结论有误 close-task --verdict 作废 + 理由；"
        "紧急恢复请手动拷 .snaps 照片文件）")


def cmd_create(args) -> None:
    path = Path(args.file)
    if path.exists():
        raise SystemExit(f"桌子已存在：{path}，换个名再开")
    save(path, blank_table(args.table), op="开桌")
    _say(args, "pass", f"开好桌子：{args.table}")


def _build_source(args) -> dict | None:
    """造来源标记：--room 传了才记，没传不加字段（兼容老命令）。"""
    room = getattr(args, "room", None)
    if not room:
        return None
    src = {"room": room}
    if getattr(args, "ref", None):
        src["ref"] = args.ref
    if getattr(args, "status", None):
        src["status"] = args.status
    return src


def cmd_set_slot(args) -> None:
    """小李写左边：一次只写一格，格名必须对。"""
    if args.slot not in LEFT_SLOTS:
        raise SystemExit(f"没这格：{args.slot}，只能是 {LEFT_SLOTS}")
    path = Path(args.file)
    data = load(path)
    src = _build_source(args)
    for x in data["left"]:
        if x["slot"] == args.slot:
            x["text"] = args.text
            if src:
                x["source"] = src
    save(path, data, op="改字")
    _say(args, "pass", f"写好：{args.slot}")
def _slot_cell(table: dict, name: str) -> dict:
    for x in table["left"]:
        if x["slot"] == name:
            return x
    raise SystemExit(f"没这格：{name}")


def _append_line(table: dict, slot: str, text: str) -> None:
    cell = _slot_cell(table, slot)
    cell["text"] = f"{cell['text']}；{text}" if cell["text"] else text
def cmd_add_gap(args) -> None:
    """证据缺失不是终点：宪法#9 要求把"证据为什么不存在"本身当成一件要查的事。

    一条缺口必须写清缺的是什么，并记三个可能方向——停在"证据不足，等待补充"是违规。
    """
    if not args.missing.strip():
        raise SystemExit("要说清缺的是什么证据（--missing）")
    path = Path(args.file)
    data = load(path)
    _append_line(data, LEFT_SLOTS[2],
                 f"{args.finding} 证据缺失：{args.missing}"
                 f"（三种可能：业务未发生 / 管理缺失未留痕 / 证据被消除，须分别追问）")
    save(path, data, op="记缺口")
    _say(args, "pass", f"已记缺口：{args.finding} 缺「{args.missing}」→ 三种可能都要问")


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _next_task_id(data: dict) -> str:
    """任务编号 T-001 起，已有关的不重用（作废的也占号）。"""
    n = 0
    for t in data.get("tasks", []):
        try:
            n = max(n, int(str(t.get("id", "T-0")).split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"T-{n + 1:03d}"


def cmd_add_task(args) -> None:
    """立任务：新假设先落任务板（待查），查实了才转事实行。

    写入口只认三件事：说什么假设(--title)、谁立的(--room)、凭什么编号(--ref)，
    缺一个就不让立。有户口的（--known-anchor 给出户口编号）不上新任务——
    户口已有，SKILL 只挂引用（桌上已有行），本次一个字不写，exit 0。
    任务是假设不是结论，红格 A/E 门不管任务。
    """
    if not args.title.strip():
        raise SystemExit("要说清是什么假设（--title）")
    if not args.room or not args.ref:
        raise SystemExit("任务必须写清谁立的(--room)、凭什么编号(--ref)")
    path = Path(args.file)
    data = load(path)
    tasks = data.setdefault("tasks", [])
    if (args.known_anchor or "").strip():
        _say(args, "pass", f"跳过：{args.ref} 户口已有（{args.known_anchor}），只挂引用不占新行（本次一个字没写）")
        return
    for t in tasks:
        if t.get("status") == "待查" and str(t.get("source", {}).get("ref", "")).upper() == str(args.ref).strip().upper():
            _refuse(f"拒收：{args.ref} 已有待查任务 {t.get('id')}，先查完再立新的（本次一个字没写）", args)
    tid = _next_task_id(data)
    tasks.append({
        "id": tid,
        "title": args.title,
        "status": "待查",
        "source": {"room": args.room, "ref": args.ref},
        "fact_anchors": [],
        "ref_finding_ids": [],
        "created_at": _now(),
        "closed_at": "",
    })
    save(path, data, op="立任务")
    _say(args, "pass", f"立好任务：{tid} {args.title}（待查）")


def cmd_close_task(args) -> None:
    """结任务：查实转事实行走 add-line（来源 ref 指回任务 id），这里只销任务的账。

    已结必须带结论去向（--finding 单号或 --fact 结论文本其一），不带就 exit 2——
    任务不能无声消失。作废必须带理由（--reason）。
    """
    if args.verdict not in ("已结", "作废"):
        raise SystemExit("结任务只能是 已结/作废")
    path = Path(args.file)
    data = load(path)
    task = next((t for t in data.get("tasks", []) if t.get("id") == args.id), None)
    if task is None:
        raise SystemExit(f"没这个任务：{args.id}")
    if task.get("status") != "待查":
        raise SystemExit(f"任务 {args.id} 已是{task.get('status')}，不能再结")
    if args.verdict == "已结":
        if not (args.finding or (args.fact or "").strip()):
            _refuse(f"拒收：{args.id} 结了就得有去向（--finding 单号或 --fact 结论），否则等于无声消失（本次一个字没写）", args)
        if args.finding:
            task.setdefault("ref_finding_ids", []).append(args.finding)
    else:
        if not (args.reason or "").strip():
            raise SystemExit("作废必须说清理由（--reason）")
        task["close_reason"] = args.reason
    task["status"] = args.verdict
    task["closed_at"] = _now()
    save(path, data, op="结任务")
    _say(args, "pass", f"结好任务：{args.id} → {args.verdict}")


def cmd_add_evidence(args) -> None:
    """小王贴右边：谁给的、啥时候给的，缺一个不让贴。等级照实标（A-E），红格认 A/E。"""
    if not args.from_ or not args.when:
        raise SystemExit("证据必须写清谁给的(--from)、啥时候给的(--when)")
    grade = (args.grade or "").upper()
    if grade and grade not in ("A", "B", "C", "D", "E"):
        raise SystemExit(f"等级只能是 A/B/C/D/E，收到：{args.grade}")
    path = Path(args.file)
    data = load(path)
    src = _build_source(args)
    row = {
        "slot_id": args.slot_id,
        "file": args.file_,
        "from": args.from_,
        "when": args.when,
        "grade": grade,
    }
    if src:
        row["source"] = src
    data["right"].append(row)
    save(path, data, op="贴证据")
    _say(args, "pass", f"贴好证据：{args.file_}" + (f"（{grade}级）" if grade else ""))


def cmd_add_line(args) -> None:
    """添字：往格子里追加一句，不盖旧字（多家写同一格用这个）。

    写入口硬度门（只拦新增红格）：怀疑偷骗格上桌时，桌上必须已有 A/E 级硬证据，
    否则 exit 2 拒收（本次一个字不写）。改字（set-slot）不管，事后门卫照扫。
    """
    if args.slot not in LEFT_SLOTS:
        raise SystemExit(f"没这格：{args.slot}，只能是 {LEFT_SLOTS}")
    path = Path(args.file)
    data = load(path)
    if args.slot == RED_SLOT and not _hard_grades(data, args.ref or ""):
        _refuse(
            f"拒收：{RED_SLOT}是高风险区，先贴 A/E 级硬证据再上桌\n"
            f"（add-evidence --grade A/E --ref {args.ref or '单号'} → 再 add-line；"
            f"证据不够就降格写“说不清的信号”。本次一个字没写）", args)
    src = _build_source(args)
    for x in data["left"]:
        if x["slot"] == args.slot:
            x["text"] = f"{x['text']}；{args.text}" if x["text"] else args.text
            if src:
                x["source"] = src
    save(path, data, op="添字")
    _say(args, "pass", f"添好：{args.slot}")


def cmd_link(args) -> None:
    """小张对单号：红格的怀疑对上问题单号，一次对一个。"""
    if args.slot not in LEFT_SLOTS:
        raise SystemExit(f"没这格：{args.slot}，只能是 {LEFT_SLOTS}")
    path = Path(args.file)
    data = load(path)
    for x in data["left"]:
        if x["slot"] == args.slot and args.finding not in x["ref_finding_ids"]:
            x["ref_finding_ids"].append(args.finding)
    save(path, data, op="对单号")
    _say(args, "pass", f"对好：{args.slot} ↔ {args.finding}")


def cmd_set_drawer(args) -> None:
    """抽屉填入口：三张表分别在哪、做到哪一步了。只动指定的那张。"""
    path = Path(args.file)
    data = load(path)
    for d in data["drawers"]:
        if d["name"] == args.name:
            if args.path is not None:
                d["path"] = args.path
            if args.status is not None:
                d["status"] = args.status
    save(path, data, op="填抽屉")
    _say(args, "pass", f"抽屉填好：{args.name}")


def cmd_show(args) -> None:
    data = load(Path(args.file))
    print(f"桌子：{data['table']}")
    for x in data["left"]:
        mark = "【红】" if x["red"] else ""
        print(f"  左{mark}{x['slot']}：{x['text'] or '（空）'}")
    print(f"  右：{len(data['right'])}条证据")
    for e in data["right"]:
        print(f"    - {e['file']}（{e['from']}，{e['when']}）")
    print("  抽屉：")
    for d in data["drawers"]:
        state = f"（{d['status']}）" if d["status"] else ""
        print(f"    - {d['name']}：{d['path'] or '（还没填入口）'}{state}")
    open_tasks = [t for t in data.get("tasks", []) if t.get("status") == "待查"]
    print(f"  任务板：{len(open_tasks)}条待查")
    for t in open_tasks:
        print(f"    - {t['id']} {t.get('title', '')}（{(t.get('source') or {}).get('ref', '')}）")


def main() -> None:
    p = argparse.ArgumentParser(description="新桌子管家：只管往桌上写")
    p.add_argument("--json", action="store_true",
                   help="成功/拒收行后追 SHEET 答卷行（人话不动，退出码不动）")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="开一张空桌子")
    c.add_argument("file")
    c.add_argument("--table", required=True)
    c.set_defaults(fn=cmd_create)

    c = sub.add_parser("set-slot", help="写左边一格")
    c.add_argument("file")
    c.add_argument("--slot", required=True, choices=LEFT_SLOTS)
    c.add_argument("--text", required=True)
    c.add_argument("--room", default=None, help="来源房间（看制度/问话/执行取证/吵架/信号池）")
    c.add_argument("--ref", default=None, help="来源编号（如 CF-001、DA-001、F-2026-004）")
    c.add_argument("--status", default=None, help="来源状态")
    c.set_defaults(fn=cmd_set_slot)

    c = sub.add_parser("add-evidence", help="右边贴一条证据")
    c.add_argument("file")
    c.add_argument("--file", dest="file_", required=True)
    c.add_argument("--from", dest="from_", required=True)
    c.add_argument("--when", required=True)
    c.add_argument("--slot-id", default=None)
    c.add_argument("--room", default=None, help="来源房间")
    c.add_argument("--ref", default=None, help="来源编号")
    c.add_argument("--grade", default=None, help="证据等级 A/B/C/D/E（红格只认 A/E）")
    c.set_defaults(fn=cmd_add_evidence)

    c = sub.add_parser("add-line", help="往格子里追加一句")
    c.add_argument("file")
    c.add_argument("--slot", required=True, choices=LEFT_SLOTS)
    c.add_argument("--text", required=True)
    c.add_argument("--room", default=None, help="来源房间（看制度/问话/执行取证/吵架/信号池）")
    c.add_argument("--ref", default=None, help="来源编号（如 CF-001、DA-001、F-2026-004）")
    c.add_argument("--status", default=None, help="来源状态")
    c.set_defaults(fn=cmd_add_line)

    c = sub.add_parser("link-finding", help="左边一格对上问题单号")
    c.add_argument("file")
    c.add_argument("--slot", required=True, choices=LEFT_SLOTS)
    c.add_argument("--finding", required=True)
    c.set_defaults(fn=cmd_link)

    c = sub.add_parser("set-drawer", help="抽屉填入口：三张表在哪、什么状态")
    c.add_argument("file")
    c.add_argument("--name", required=True, choices=DRAWER_NAMES)
    c.add_argument("--path", default=None)
    c.add_argument("--status", default=None)
    c.set_defaults(fn=cmd_set_drawer)

    c = sub.add_parser("add-gap", help="记一条证据缺失（宪法#9：缺失即信号）")
    c.add_argument("file")
    c.add_argument("--finding", required=True)
    c.add_argument("--missing", required=True, help="缺的是哪份证据")
    c.set_defaults(fn=cmd_add_gap)

    c = sub.add_parser("add-task", help="立任务：新假设先落任务板（待查）")
    c.add_argument("file")
    c.add_argument("--title", required=True, help="假设一句话")
    c.add_argument("--room", required=True, help="谁立的（如 检查单）")
    c.add_argument("--ref", required=True, help="立任务的编号（如 R-010）")
    c.add_argument("--known-anchor", default=None, help="户口编号：给了就不占新行，只挂引用")
    c.set_defaults(fn=cmd_add_task)

    c = sub.add_parser("close-task", help="结任务：已结须带结论去向，作废须带理由")
    c.add_argument("file")
    c.add_argument("--id", required=True, help="任务编号（如 T-001）")
    c.add_argument("--verdict", required=True, choices=["已结", "作废"])
    c.add_argument("--finding", default=None, help="结论去向：问题单号")
    c.add_argument("--fact", default=None, help="结论去向：结论文本（转事实行走 add-line）")
    c.add_argument("--reason", default=None, help="作废理由")
    c.set_defaults(fn=cmd_close_task)

    c = sub.add_parser("snaps", help="看照片（只读旧存档）")
    c.add_argument("file")
    c.set_defaults(fn=cmd_snaps)

    c = sub.add_parser("rollback", help="已取消：只拒收并指引（加--to 也照拒）")
    c.add_argument("file")
    c.add_argument("--to", required=False, default=None)
    c.set_defaults(fn=cmd_rollback)

    c = sub.add_parser("show", help="看桌子现状")
    c.add_argument("file")
    c.set_defaults(fn=cmd_show)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # 未预期崩溃 → exit(2)。绝不能让崩溃的退出码(1)与"明确拒绝"混作一谈
        import traceback
        traceback.print_exc()
        sys.exit(2)
