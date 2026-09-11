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
  4. 收料（sweep）只添不盖：人写的字一个字不动；机器只认自己上次写的那几条
     （记在 ingested 里），所以同一条反复收不会变两行，状态变了只从这格挪到那格

用法:
    python ledger.py create 桌子.json --table "冲压车间废料多了"
    python ledger.py set-slot 桌子.json --slot 确定的毛病 --text "领料没签字"
    python ledger.py add-evidence 桌子.json --file "领料单7张" --from 班长 --when 审计当天
    python ledger.py sweep 桌子.json --workspace D:\某个审计项目
    python ledger.py add-gap 桌子.json --finding F-2026-003 --missing "绩效评分原始记录"
    python ledger.py show 桌子.json
"""

import argparse
import copy
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.2"
LEFT_SLOTS = ["确定的毛病", "怀疑偷骗", "说不清的信号"]
DRAWER_NAMES = ["问话表", "检查表", "报告表"]
CHECKLIST = ["证据够了吗", "制度看全了吗", "红格看了吗"]

# 落格规则（ledger.schema.json 的「落格规则」就是这一条，改这里要同步改那里）：
#   来源自带的状态字段 → 格；跨文件覆盖＝别的制度里有，不算缺失，不上桌；
#   涉及舞弊 → 红格；没状态字段、或状态说不清的 → 信号格
FRAUD_WORDS = ("舞弊", "贪", "侵占", "回扣", "受贿", "私分", "挪用", "串通", "虚假报")


def blank_table(name: str) -> dict:
    """空桌子：三格占好，证据为空，抽屉三个入口空着等填，收料本子空着。"""
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
    }


def load(path: Path) -> dict:
    """读桌子，格子不对就报错（桌子坏了不能往上写）。

    老桌子就地升级，不作废：
      1.0 的抽屉只记了三个表名 → 1.1 起每张还记"在哪、什么状态"
      1.1 没有 ingested      → 1.2 起记"哪几条是机器收上来的"，收料才不会重复
    硬拒绝会把"版本号变了"升级成"以前的桌子全打不开"。
    """
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    ver = data.get("schema_version")
    if ver != SCHEMA_VERSION:
        if ver not in ("1.0", "1.1"):
            raise SystemExit(f"桌子版本不对：{ver}，要 {SCHEMA_VERSION}")
        if ver == "1.0":
            data["drawers"] = [
                d if isinstance(d, dict) else {"name": d, "path": "", "status": ""}
                for d in data.get("drawers", [])
            ]
        data.setdefault("ingested", {})
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
    """写桌子：先拍照再写。父目录没建就顺手建上——
    建项目时开第一张桌走的就是这条路，那时 audit-table/ 还不存在。"""
    path.parent.mkdir(parents=True, exist_ok=True)
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
    target = snap.read_bytes()  # 先把目标读进内存：save() 拍照时会淘汰最早一张，
                                # 而"回到最早那张"时目标正是被淘汰的那张
    data = load(path)
    save(path, data)  # 再给现在拍照
    path.write_bytes(target)
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


def _lines_of(text: str) -> list:
    """格子里的一行行话（用"；"隔开）。"""
    return [x for x in (text or "").split("；") if x.strip()]


# ══════════════════════════════════════════════════════════════
# 收料：把各房间查出来的东西，按「落格规则」搬上桌
# （只读老账，一个字节不改；落格规则见 ledger.schema.json）
# ══════════════════════════════════════════════════════════════
def check_workspace(ws: Path) -> None:
    """项目路径不对就别往下走——否则收出一张空桌，看着成功、其实什么都没收。"""
    if not (ws / "internal-audit-workspace").is_dir():
        raise SystemExit(f"项目路径不对：找不到 {ws / 'internal-audit-workspace'}"
                         f"——检查 --workspace 是否指向项目根目录")


def _route_gap(status: str) -> str:
    """控制缺口去哪个格。跨文件覆盖＝别的制度里有，不算缺失，返回空串＝不上桌。"""
    if status == "跨文件覆盖":
        return ""
    return LEFT_SLOTS[0] if status == "已确认" else LEFT_SLOTS[2]


def _looks_fraud(item: dict) -> bool:
    """是不是舞弊嫌疑。先看明确写的分类，没写才看字眼——宁可多进红格，不可漏（宪法#2）。"""
    if "舞弊" in f"{item.get('category', '')}{item.get('type', '')}{item.get('kind', '')}":
        return True
    blob = " ".join(str(item.get(k, "")) for k in
                    ("summary", "detail", "content", "title", "description"))
    return any(w in blob for w in FRAUD_WORDS)


def scan_policy(ws: Path) -> list:
    """看制度查出来的三样：控制缺口（CG）、风险点（RP）、制度冲突（CF）。"""
    out = []
    d = ws / "internal-audit-workspace" / "policy-analyses"
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        a = _read_json(p)
        doc = str(a.get("doc_name") or p.stem)
        for g in a.get("control_gaps") or []:
            gid = str(g.get("id") or "").strip()
            slot = _route_gap(str(g.get("verification_status") or ""))
            if not gid or not slot:
                continue
            what = g.get("expected_control") or g.get("description") or g.get("actual") or ""
            out.append({"id": f"{p.name}:{gid}", "slot": slot,
                        "text": f"{gid} 控制缺口（{doc}）：{_short(str(what), 60)}"
                                f"（{g.get('verification_status')}）"})
        for r in a.get("risk_points") or []:
            rid = str(r.get("risk_id") or r.get("id") or "").strip()
            if not rid:
                continue
            sev = str(r.get("severity") or r.get("risk_level") or "未标")
            desc = r.get("risk_description") or r.get("description") or ""
            out.append({"id": f"{p.name}:{rid}", "slot": LEFT_SLOTS[2],
                        "text": f"{rid} 风险点（{sev}，{doc}）：{_short(str(desc), 60)}"})
        for c in a.get("conflicts") or []:
            cid = str(c.get("id") or "").strip()
            if not cid:
                continue
            # 冲突没有"状态字段"——两份制度对不上，本身就是读出来的事实，不是待验的猜想
            out.append({"id": f"{p.name}:{cid}", "slot": LEFT_SLOTS[0],
                        "text": f"{cid} 制度冲突（{doc}）：{_short(str(c.get('description') or ''), 60)}"})
    return out


def scan_design(ws: Path) -> list:
    """设计观察（待现场验证的假设）。JSON 优先，没有 JSON 才读 DA-*.md——
    两份是同一批东西的两种写法，都读会让一件事在桌上占两行。"""
    out = []
    d = ws / "internal-audit-workspace" / "design-assessments"
    if not d.is_dir():
        return out
    jsons = sorted(d.glob("*.json"))
    if jsons:
        for p in jsons:
            for o in _read_json(p).get("design_observations") or []:
                oid = str(o.get("id") or "").strip()
                # 只有 pending 是"还没验证的假设"；verified 已变成问题单自己上桌，rejected 不成立
                if not oid or str(o.get("status") or "") != "pending":
                    continue
                tag = "访谈" if o.get("source") == "interview" else "看制度"
                what = o.get("title") or o.get("description") or ""
                out.append({"id": f"{p.name}:{oid}", "slot": LEFT_SLOTS[2],
                            "text": f"{oid} {_short(str(what), 60)}（{tag}，待现场验证）"})
        return out
    for md in sorted(d.glob("DA-*.md")):
        head = md.read_text(encoding="utf-8-sig").splitlines()
        title = head[0].lstrip("# ").strip() if head else md.stem
        out.append({"id": md.name, "slot": LEFT_SLOTS[2], "text": f"{title}（待现场验证）"})
    return out


def scan_state(ws: Path) -> list:
    """信号池（宪法#10 制度空白）＋ 举报线索——两样都住在 current-audit.json 里。"""
    out = []
    p = ws / "current-audit.json"
    if not p.exists():
        return out
    st = _read_json(p).get("audit_state") or {}
    for s in st.get("signals") or []:
        if not isinstance(s, dict):
            continue
        name = s.get("module") or s.get("type") or "信号"
        out.append({"id": f"current-audit.json:MB-{name}", "slot": LEFT_SLOTS[2],
                    "text": f"制度空白：{_short(str(s.get('detail') or name), 60)}"})
    for i, w in enumerate(st.get("whistleblower_pending") or [], 1):
        if not isinstance(w, dict):
            w = {"summary": str(w)}
        wid = str(w.get("id") or f"WB-{i:03d}")
        what = w.get("summary") or w.get("detail") or w.get("content") or w.get("title") or ""
        out.append({"id": f"current-audit.json:{wid}",
                    "slot": LEFT_SLOTS[1] if _looks_fraud(w) else LEFT_SLOTS[2],
                    "text": f"{wid} 举报线索：{_short(str(what), 60)}"})
    return out


def scan_findings(ws: Path, only: str = None) -> tuple:
    """问题单（F-）＋待查项。返回（要上桌的条目, 要贴的证据）。"""
    fdir = ws / "internal-audit-workspace" / "findings"
    paths = [fdir / f"{only}.json"] if only else sorted(fdir.glob("F-*.json"))
    if only and not paths[0].exists():
        raise SystemExit(f"老账里没这张单：{paths[0].name}")
    items, rows = [], []
    for p in paths:
        f = _read_json(p)
        fid = str(f.get("finding_id") or p.stem)
        line = f"{fid} {_short(str(f.get('title', '')))}"
        if _is_fraud(f):
            items.append({"id": f"F:{fid}", "slot": LEFT_SLOTS[1], "text": line, "ref": fid})
        elif str(f.get("status", "")) == "待补充":
            items.append({"id": f"F:{fid}", "slot": LEFT_SLOTS[2], "text": f"{line}（待补充）"})
        else:
            items.append({"id": f"F:{fid}", "slot": LEFT_SLOTS[0], "text": line, "ref": fid})
        for e in f.get("evidence") or []:
            rows.append({
                "slot_id": None,
                "file": f"{fid}：{e.get('name', '未命名')}",
                "from": e.get("source") or "未注明",
                "when": e.get("obtained_date") or "未注明",
            })
        for j, u in enumerate((f.get("audit_team_notes") or {}).get("key_uncertainties") or []):
            items.append({"id": f"F:{fid}:待查{j}", "slot": LEFT_SLOTS[2],
                          "text": f"{fid}待查：{_short(str(u))}"})
    return items, rows


def scan_workspace(ws: Path) -> tuple:
    """扫遍所有房间，收成两摞：要上桌的条目、要贴的证据。只看不改。"""
    items, rows = scan_findings(ws)
    return items + scan_policy(ws) + scan_design(ws) + scan_state(ws), rows


def _slot_cell(table: dict, name: str) -> dict:
    for x in table["left"]:
        if x["slot"] == name:
            return x
    raise SystemExit(f"没这格：{name}")


def _append_line(table: dict, slot: str, text: str) -> None:
    cell = _slot_cell(table, slot)
    cell["text"] = f"{cell['text']}；{text}" if cell["text"] else text


def _drop_line(table: dict, slot: str, text: str, ref: str = "") -> None:
    cell = _slot_cell(table, slot)
    cell["text"] = "；".join(x for x in _lines_of(cell["text"]) if x != text)
    if ref and ref in cell["ref_finding_ids"]:
        cell["ref_finding_ids"].remove(ref)


def apply_items(table: dict, items: list) -> tuple:
    """把收来的条目并进桌子：新的追加、状态变了的挪格、没变的跳过。
    返回（新增条数, 挪格条数）。只碰机器自己上次写的行，人写的字不动。"""
    book = table.setdefault("ingested", {})
    added = moved = 0
    for it in items:
        old = book.get(it["id"])
        if old and old.get("slot") == it["slot"] and old.get("text") == it["text"]:
            continue
        ref = it.get("ref") or ""
        if old:
            # 状态变了（"待确认"补全文件后变"已确认"）：先从旧格撤下来再进新格，
            # 不然同一件事会在两个格子里各挂一条
            _drop_line(table, old["slot"], old["text"], ref)
            moved += 1
        else:
            added += 1
        _append_line(table, it["slot"], it["text"])
        cell = _slot_cell(table, it["slot"])
        if ref and ref not in cell["ref_finding_ids"]:
            cell["ref_finding_ids"].append(ref)
        book[it["id"]] = {"slot": it["slot"], "text": it["text"]}
    return added, moved


def apply_evidence(table: dict, rows: list) -> int:
    """贴证据：同一份（名、谁给的、啥时候）已在右边就不重复贴。"""
    have = {(e.get("file"), e.get("from"), e.get("when")) for e in table["right"]}
    n = 0
    for e in rows:
        k = (e.get("file"), e.get("from"), e.get("when"))
        if k in have:
            continue
        table["right"].append(e)
        have.add(k)
        n += 1
    return n


def cmd_import(args) -> None:
    """老账搬家：只读老项目，原样抄进新桌子，老账一个字不动。

    搬的是各房间已经落纸的东西：问题单＋待查项、看制度的控制缺口/风险点/冲突、
    设计观察、信号池的制度空白、举报线索。搬过的记进 ingested，以后 sweep 不会重复搬。
    """
    ws = Path(args.workspace)
    check_workspace(ws)
    out = Path(args.file)
    if out.exists():
        raise SystemExit(f"桌子已存在：{out}，换个名再搬（日常补漏用 sweep）")
    items, rows = scan_workspace(ws)
    if args.finding:
        items, rows = scan_findings(ws, args.finding)
    table = blank_table(args.table)
    added, _ = apply_items(table, items)
    nevd = apply_evidence(table, rows)
    save(out, table)
    counts = "／".join(f"{x['slot']}{len(_lines_of(x['text']))}"
                      for x in table["left"])
    print(f"搬好：{added}条上桌（{counts}）／ 证据{nevd}条 ← {ws.name}")


def cmd_sweep(args) -> None:
    """收料：把各房间查出来的东西，按「落格规则」搬上桌。

    只添不盖——人写的字一个字不动。机器只认自己上次写的那几条（记在 ingested），
    所以反复收不会变两行；状态变了也只是从这格挪到那格。加 --dry-run 只看不写。
    """
    ws = Path(args.workspace)
    check_workspace(ws)
    path = Path(args.file)
    data = load(path)
    items, rows = (scan_findings(ws, args.finding) if args.finding
                   else scan_workspace(ws))
    if args.dry_run:
        trial = copy.deepcopy(data)
        added, moved = apply_items(trial, items)
        nevd = apply_evidence(trial, rows)
        print(f"[试算] 会新增 {added} 条、挪格 {moved} 条、补证据 {nevd} 条（一个字没写）")
        for k, v in trial["ingested"].items():
            if k not in data.get("ingested", {}):
                print(f"  + {v['slot']}｜{_short(v['text'], 70)}")
        return
    added, moved = apply_items(data, items)
    nevd = apply_evidence(data, rows)
    if not (added or moved or nevd):
        print("收料：桌上已是最新，没有新的")
        return
    save(path, data)
    print(f"收料：新增 {added} 条、挪格 {moved} 条、补证据 {nevd} 条")


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
    save(path, data)
    print(f"已记缺口：{args.finding} 缺「{args.missing}」→ 三种可能都要问")
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


def cmd_add_line(args) -> None:
    """添字：往格子里追加一句，不盖旧字（多家写同一格用这个）。"""
    if args.slot not in LEFT_SLOTS:
        raise SystemExit(f"没这格：{args.slot}，只能是 {LEFT_SLOTS}")
    path = Path(args.file)
    data = load(path)
    for x in data["left"]:
        if x["slot"] == args.slot:
            x["text"] = f"{x['text']}；{args.text}" if x["text"] else args.text
    save(path, data)
    print(f"添好：{args.slot}")


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
    save(path, data)
    print(f"抽屉填好：{args.name}")


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

    c = sub.add_parser("add-line", help="往格子里追加一句")
    c.add_argument("file")
    c.add_argument("--slot", required=True, choices=LEFT_SLOTS)
    c.add_argument("--text", required=True)
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

    c = sub.add_parser("sweep", help="收料：把各房间查出来的东西搬上桌")
    c.add_argument("file")
    c.add_argument("--workspace", required=True)
    c.add_argument("--finding", default=None, help="只收这一张单（刚执行完一张时用）")
    c.add_argument("--dry-run", action="store_true", help="只看会加什么，一个字不写")
    c.set_defaults(fn=cmd_sweep)

    c = sub.add_parser("add-gap", help="记一条证据缺失（宪法#9：缺失即信号）")
    c.add_argument("file")
    c.add_argument("--finding", required=True)
    c.add_argument("--missing", required=True, help="缺的是哪份证据")
    c.set_defaults(fn=cmd_add_gap)

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
    try:
        sys.exit(main())
    except Exception:
        # 未预期崩溃 → exit(2)。绝不能让崩溃的退出码(1)与"明确拒绝"混作一谈
        import traceback
        traceback.print_exc()
        sys.exit(2)
