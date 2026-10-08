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
     （记在 ingested 里），所以同一条反复收不会变两行，状态变了只从这格挪到那格；
     盖了"作废"章的行下架（只动本子里的机器行，原纸不动）；收完回写账本
     （sweep_history + 大事记，只追加）

用法:
    python ledger.py create 桌子.json --table "冲压车间废料多了"
    python ledger.py set-slot 桌子.json --slot 确定的毛病 --text "领料没签字"
    python ledger.py add-evidence 桌子.json --file "领料单7张" --from 班长 --when 审计当天
    python ledger.py sweep 桌子.json --workspace D:\某个审计项目
    python ledger.py add-gap 桌子.json --finding F-2026-003 --missing "绩效评分原始记录"
    python ledger.py add-task 桌子.json --title "钢筋回扣疑似内外勾结" --room 检查单 --ref R-010
    python ledger.py close-task 桌子.json --id T-001 --verdict 已结 --finding F-2026-010
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


def _refuse(code_msg: str) -> None:
    """写入口拒收：话说在 stdout（LLM 和人都看得见），码用 2（拦下）。"""
    print(code_msg)
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
    save(path, blank_table(args.table))
    print(f"开好桌子：{args.table}")


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


def _audit_state(ws: Path) -> dict:
    """current-audit.json 的 audit_state。标准位置在 internal-audit-workspace/ 里
    （project-init 建的就在那）；老项目放在项目根的也认。两处都没有 → 空。"""
    for p in (ws / "internal-audit-workspace" / "current-audit.json",
              ws / "current-audit.json"):
        if p.exists():
            return _read_json(p).get("audit_state") or {}
    return {}


def _looks_fraud(item: dict) -> bool:
    """是不是舞弊嫌疑。先看明确写的分类，没写才看字眼——宁可多进红格，不可漏（宪法#2）。"""
    if "舞弊" in f"{item.get('category', '')}{item.get('type', '')}{item.get('kind', '')}":
        return True
    blob = " ".join(str(item.get(k, "")) for k in
                    ("summary", "detail", "content", "title", "description"))
    return any(w in blob for w in FRAUD_WORDS)


def scan_policy(ws: Path) -> list:
    """看制度查出来的三样：控制缺口（CG）、风险点（RP）、制度冲突（CF）。"""
    GRADE = {"high": "高", "medium": "中", "low": "低"}
    out = []
    d = ws / "internal-audit-workspace" / "policy-analyses"
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        a = _read_json(p)
        doc = str(a.get("doc_name") or p.stem)
        for g in a.get("control_gaps") or []:
            # 编号字段两个名字都认：文档声明 id，真实批量产出用 gap_id——2026-09-14 广东长华实撞
            gid = str(g.get("id") or g.get("gap_id") or "").strip()
            slot = _route_gap(str(g.get("verification_status") or ""))
            if not gid or not slot:
                continue
            what = g.get("expected_control") or g.get("description") or g.get("actual") or ""
            out.append({"id": f"{p.name}:{gid}", "slot": slot,
                        "text": f"{gid} 控制缺口（{doc}）：{_short(str(what), 60)}"
                                f"（{g.get('verification_status')}）"})
        for r in a.get("risk_points") or []:
            rid = str(r.get("risk_id") or r.get("rp_id") or r.get("id") or "").strip()
            if not rid:
                continue
            sev = str(r.get("severity") or r.get("risk_level") or "未标")
            sev = GRADE.get(sev.lower(), sev)
            desc = r.get("risk_description") or r.get("description") or ""
            out.append({"id": f"{p.name}:{rid}", "slot": LEFT_SLOTS[2],
                        "text": f"{rid} 风险点（{sev}，{doc}）：{_short(str(desc), 60)}"})
        for c in a.get("conflicts") or []:
            cid = str(c.get("id") or c.get("conflict_id") or "").strip()
            if not cid:
                continue
            # 冲突没有"状态字段"——两份制度对不上，本身就是读出来的事实，不是待验的猜想
            out.append({"id": f"{p.name}:{cid}", "slot": LEFT_SLOTS[0],
                        "text": f"{cid} 制度冲突（{doc}）：{_short(str(c.get('description') or ''), 60)}"})
    return out


def scan_design(ws: Path) -> list:
    """设计观察（待现场验证的假设）。JSON 优先，没有 JSON 才读 DA-*.md——
    两份是同一批东西的两种写法，都读会让一件事在桌上占两行。
    current-audit.json 标了 design_observations_consumed=true（观察已消化进审计程序），
    就不再挂回桌面——消化了的东西再上桌，会把已经变成问题单的事摆两行。"""
    out = []
    d = ws / "internal-audit-workspace" / "design-assessments"
    if not d.is_dir():
        return out
    if _audit_state(ws).get("design_observations_consumed") is True:
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
    st = _audit_state(ws)
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


def _known_anchors(ws: Path) -> set:
    """制度分析／设计观察里已有的编号集合——判断程序文件里的风险"有没有户口"用。
    编号是去重的唯一凭据：找得到＝同一件事已经在桌上，找不到＝推演出的新假设。"""
    ids = set()
    for p in (ws / "internal-audit-workspace" / "policy-analyses").glob("*.json"):
        a = _read_json(p)
        for g in a.get("control_gaps") or []:
            ids.add(str(g.get("gap_id") or g.get("id") or "").strip().upper())
        for r in a.get("risk_points") or []:
            ids.add(str(r.get("rp_id") or r.get("risk_id") or r.get("id") or "").strip().upper())
        for c in a.get("conflicts") or []:
            ids.add(str(c.get("conflict_id") or c.get("id") or "").strip().upper())
    for p in (ws / "internal-audit-workspace" / "design-assessments").glob("*.json"):
        for o in _read_json(p).get("design_observations") or []:
            ids.add(str(o.get("id") or "").strip().upper())
    ids.discard("")
    return ids


def _load_ir_parser():
    """审计程序的解析器在 _shared/scripts/program_ir_parser.py（validate-program 也在用）。
    借它的现成解析，不另写一套 markdown 解析——两处共用，修一处两处受益。"""
    shared = Path(__file__).resolve().parent.parent / "_shared" / "scripts"
    if str(shared) not in sys.path:
        sys.path.insert(0, str(shared))
    try:
        import program_ir_parser
        return program_ir_parser
    except Exception as e:
        raise SystemExit(f"审计程序解析器用不了（{shared / 'program_ir_parser.py'}）：{e}")


def scan_programs(ws: Path) -> list:
    """审计程序 2.1 风险清单：推演出的假设上桌（信号格）。

    制度类的条目与制度分析同源——**有户口的就不上**，不然同一件事在桌上摆两行。
    户口＝来源标注里的 CG/RP/CF/D 编号在制度分析里找得到；找不到（或压根没有编号）
    的按推演处理照上，宁可多几行可删的，不可漏收。
    程序本体（65 条测试指令）是"要做的事"，不在这里收——归抽屉·检查表。
    """
    d = ws / "internal-audit-workspace" / "audit-programs"
    mds = sorted(d.glob("*.md")) if d.is_dir() else []
    if not mds:
        return []
    parser = _load_ir_parser()
    known = _known_anchors(ws)
    out = []
    for p in mds:
        for r in parser.build_ir(p).get("risk_register") or []:
            rid = str(r.get("risk_id") or "").strip()
            if not rid:
                continue
            if r.get("is_deleted"):
                continue  # 作废行不上桌（原行在程序文件里留着，只是不收）
            if known & {str(a).strip().upper() for a in r.get("fact_anchors") or []}:
                continue
            label = str(r.get("raw_id") or rid).strip()
            kind = _short(str(r.get("type") or "推演"), 8)
            out.append({"id": f"{p.name}:{rid}", "slot": LEFT_SLOTS[2],
                        "text": f"{label} 推演风险（{kind}）：{_short(str(r.get('title') or ''), 60)}"})
    return out


def scan_deleted_program_risks(ws: Path) -> set:
    """程序文件里盖了"作废"章的风险编号集合（ingested 键格式"文件名:编号"）。
    只认明确的章，不认"没了"——改名/搬文件造成的对不上，不在这里下架。"""
    d = ws / "internal-audit-workspace" / "audit-programs"
    mds = sorted(d.glob("*.md")) if d.is_dir() else []
    if not mds:
        return set()
    try:
        parser = _load_ir_parser()
    except SystemExit:
        return set()
    dead = set()
    for p in mds:
        try:
            risks = parser.build_ir(p).get("risk_register") or []
        except Exception:
            continue
        for r in risks:
            if r.get("is_deleted") and str(r.get("risk_id") or "").strip():
                dead.add(f"{p.name}:{str(r.get('risk_id')).strip()}")
    return dead


def prune_deleted(table: dict, dead_ids: set) -> int:
    """下架作废行：只动收料本子里记过的机器行，人写的字不动。
    原纸（程序文件）一个字节不动，留痕不受影响。"""
    book = table.get("ingested", {})
    n = 0
    for key in [k for k in book if k in dead_ids]:
        old = book.pop(key)
        if old.get("slot") in LEFT_SLOTS and old.get("text"):
            _drop_line(table, old["slot"], old["text"], "")
        n += 1
    return n


def _writeback_sweep(ws: Path, added: int, moved: int, nevd: int, pruned: int) -> bool:
    """收料回写账本：记"啥时候收、收几条"，大事记加一行。只追加不改旧数。
    没账本（老项目/纯桌子）就跳过，不崩。"""
    audit = None
    for p in (ws / "internal-audit-workspace" / "current-audit.json",
              ws / "current-audit.json"):
        if p.exists():
            audit = p
            break
    if audit is None:
        return False
    try:
        data = json.loads(audit.read_text(encoding="utf-8-sig"))
    except Exception:
        return False
    from datetime import datetime
    st = data.setdefault("audit_state", {})
    hist = st.setdefault("sweep_history", [])
    hist.append({
        "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "added": added, "moved": moved, "evidence": nevd, "pruned": pruned,
    })
    trail = st.setdefault("audit_trail", [])
    trail.append({
        "timestamp": datetime.now().isoformat(),
        "event_type": "sweep",
        "detail": f"收料：新增{added}条、挪格{moved}条、补证据{nevd}条、下架作废{pruned}条",
    })
    audit.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def scan_workspace(ws: Path) -> tuple:
    """扫遍所有房间，收成两摞：要上桌的条目、要贴的证据。只看不改。"""
    items, rows = scan_findings(ws)
    return (items + scan_policy(ws) + scan_design(ws) + scan_state(ws)
            + scan_programs(ws)), rows


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
        if not args.finding:
            pruned = prune_deleted(trial, scan_deleted_program_risks(ws))
            if pruned:
                print(f"  - 会下架作废 {pruned} 条（原纸留着，只是不摆了）")
        return
    added, moved = apply_items(data, items)
    nevd = apply_evidence(data, rows)
    pruned = 0
    if not args.finding:
        pruned = prune_deleted(data, scan_deleted_program_risks(ws))
    if not (added or moved or nevd or pruned):
        print("收料：桌上已是最新，没有新的")
        return
    save(path, data)
    _writeback_sweep(ws, added, moved, nevd, pruned)
    print(f"收料：新增 {added} 条、挪格 {moved} 条、补证据 {nevd} 条")
    if pruned:
        print(f"下架作废：{pruned} 条（原纸留着，只是不摆了）")


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
    缺一个就不让立。有户口的（--known-anchor 对上 --ref）不上新任务——
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
    if args.known_anchor and str(args.known_anchor).strip().upper() == str(args.ref).strip().upper():
        print(f"跳过：{args.ref} 户口已有，只挂引用不占新行（本次一个字没写）")
        return
    for t in tasks:
        if t.get("status") == "待查" and str(t.get("source", {}).get("ref", "")).upper() == str(args.ref).strip().upper():
            _refuse(f"拒收：{args.ref} 已有待查任务 {t.get('id')}，先查完再立新的（本次一个字没写）")
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
    save(path, data)
    print(f"立好任务：{tid} {args.title}（待查）")


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
            _refuse(f"拒收：{args.id} 结了就得有去向（--finding 单号或 --fact 结论），否则等于无声消失（本次一个字没写）")
        if args.finding:
            task.setdefault("ref_finding_ids", []).append(args.finding)
    else:
        if not (args.reason or "").strip():
            raise SystemExit("作废必须说清理由（--reason）")
        task["close_reason"] = args.reason
    task["status"] = args.verdict
    task["closed_at"] = _now()
    save(path, data)
    print(f"结好任务：{args.id} → {args.verdict}")


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
    save(path, data)
    print(f"贴好证据：{args.file_}" + (f"（{grade}级）" if grade else ""))


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
            f"证据不够就降格写“说不清的信号”。本次一个字没写）")
    src = _build_source(args)
    for x in data["left"]:
        if x["slot"] == args.slot:
            x["text"] = f"{x['text']}；{args.text}" if x["text"] else args.text
            if src:
                x["source"] = src
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
    open_tasks = [t for t in data.get("tasks", []) if t.get("status") == "待查"]
    print(f"  任务板：{len(open_tasks)}条待查")
    for t in open_tasks:
        print(f"    - {t['id']} {t.get('title', '')}（{(t.get('source') or {}).get('ref', '')}）")


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

    c = sub.add_parser("add-task", help="立任务：新假设先落任务板（待查）")
    c.add_argument("file")
    c.add_argument("--title", required=True, help="假设一句话")
    c.add_argument("--room", required=True, help="谁立的（如 检查单）")
    c.add_argument("--ref", required=True, help="立任务的编号（如 R-010）")
    c.add_argument("--known-anchor", default=None, help="户口编号：对上 ref 则只挂引用不占新行")
    c.set_defaults(fn=cmd_add_task)

    c = sub.add_parser("close-task", help="结任务：已结须带结论去向，作废须带理由")
    c.add_argument("file")
    c.add_argument("--id", required=True, help="任务编号（如 T-001）")
    c.add_argument("--verdict", required=True, choices=["已结", "作废"])
    c.add_argument("--finding", default=None, help="结论去向：问题单号")
    c.add_argument("--fact", default=None, help="结论去向：结论文本（转事实行走 add-line）")
    c.add_argument("--reason", default=None, help="作废理由")
    c.set_defaults(fn=cmd_close_task)

    c = sub.add_parser("import", help="老账搬家：抄进新桌子")
    c.add_argument("file")
    c.add_argument("--workspace", required=True)
    c.add_argument("--table", required=True)
    c.add_argument("--finding", default=None)
    c.set_defaults(fn=cmd_import)

    c = sub.add_parser("snaps", help="看照片")
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
