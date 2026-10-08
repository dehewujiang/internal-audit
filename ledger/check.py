#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check.py — 门卫只读桌子（读线零件，不管"写"和"拍照"）

[INPUT]:  ledger JSON 文件（ledger.schema.json v1.2）+ 项目根目录（--workspace，只读抽屉路径与 current-audit.json 信号池；硬度只认桌子右边 grade）
[OUTPUT]: 中文检查报告 + 退出码（0=放行, 1=提醒, 2=拦下；未预期崩溃同样落 2）
[POS]:    ledger/ 的读线零件，是 validate-finding.py 等门口零件的接班人；
          以前翻6个房间，现在只读这一张桌子。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

门卫6件事（只看大事）：
  1. 左边三格都有字（桌子没写完不放行）
  2. 红格有字必须对上问题单号（没对上只提醒，不拦路）
  3. 右边每条证据有谁给的、啥时候给的（防手改坏账）
  4. 抽屉三张表都在；填了入口的，指到的表要真存在（找不到只提醒）
  5. 加 --workspace 才查：红格行都要有 A/E 级硬证据（只认桌子右边 grade）——
     文字含舞弊字眼没有就拦下，其余红格行只提醒（宪法#2/#3）
  6. 加 --workspace 才查：信号池（current-audit.json）里的东西必须都上桌——
     池子只写不读就是黑洞，宪法#10 的制度空白就住在里面

用法:
    python check.py 桌子.json
    python check.py 桌子.json --workspace D:\某个审计项目
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ledger import FRAUD_WORDS

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.3"
KNOWN_VERSIONS = ("1.0", "1.1", "1.2", "1.3")
LEFT_SLOTS = ["确定的毛病", "怀疑偷骗", "说不清的信号"]
DRAWERS = ["问话表", "检查表", "报告表"]


HARD_GRADES = {"A", "E"}


def check_grades(data: dict, blocks: list, warns: list) -> None:
    """第5件事：红格行都要有硬证据（宪法#3：A 级或 E 级）。

    只认桌子：右边证据的 grade 按 source.ref 对左行 ref_finding_ids；
    无单号证据算全桌通用（与写入口同口径）。无 grade 视为无硬证据。

    分两档（语义与旧版一致）：
      红格文字含舞弊字眼 + 缺硬证据 → 拦下（宪法#2 红线不动）
      红格其余行缺硬证据 → 只提醒
    非红格行无风险信息，不查（风险只在红格语义里）。
    """
    hard_by_ref = {}
    hard_free = set()
    for e in data.get("right", []):
        g = str(e.get("grade", "")).upper()
        if g not in HARD_GRADES:
            continue
        ref = ((e.get("source") or {}).get("ref") or "")
        if ref:
            hard_by_ref.setdefault(ref, set()).add(g)
        else:
            hard_free.add(g)
    for x in data.get("left", []):
        if x.get("slot") != "怀疑偷骗":
            continue
        text = (x.get("text") or "").strip()
        if not text:
            continue
        refs = x.get("ref_finding_ids") or []
        grades = set(hard_free)
        for r in refs:
            grades |= hard_by_ref.get(r, set())
        if grades & HARD_GRADES:
            continue
        label = refs[0] if refs else (text[:30] + "…")
        msg = f"红格「{label}」是高风险但没有A/E级硬证据"
        if any(w in text for w in FRAUD_WORDS):
            blocks.append(msg)
        else:
            warns.append(msg + "——宪法#3 要求 A/E，建议补硬证据或降格")


def check_pool(workspace: Path, data: dict, warns: list) -> None:
    """第6件事：信号池里的东西必须都上桌。

    宪法#10 的制度空白是写进 current-audit.json 的 audit_state.signals 的。这个池子
    以前只有人往里写、没有任何东西读它——写进去就沉底，等于黑洞。桌子读它：池里有、
    桌上没影，就是还没收料。这里按名字找，不按内部编号找——编号是桌子的家事，
    门卫不该跟着一起变。
    """
    p = workspace / "current-audit.json"
    if not p.exists():
        return
    try:
        state = json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        warns.append("current-audit.json 读不出来，信号池这次没核")
        return
    blob = "；".join(str(x.get("text", "")) for x in data.get("left", []))
    for s in (state.get("audit_state") or {}).get("signals") or []:
        if not isinstance(s, dict):
            continue
        name = str(s.get("module") or s.get("type") or "信号")
        if name not in blob:
            warns.append(f"信号池里的「{s.get('type', '信号')}：{name}」还没上桌"
                         f"（跑 ledger.py sweep）")


def main() -> int:
    ap = argparse.ArgumentParser(description="门卫只读桌子")
    ap.add_argument("file")
    ap.add_argument("--workspace", default=None, help="项目根目录，加了才查第5、6件事")
    args = ap.parse_args()
    path = Path(args.file)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    blocks, warns = [], []

    ver = data.get("schema_version")
    if ver not in KNOWN_VERSIONS:
        blocks.append(f"桌子版本不认：{ver}（本工具认 {KNOWN_VERSIONS}）")
    elif ver != SCHEMA_VERSION:
        # 老桌子照样读得动，拦下报告没道理——提醒一句，写一次就升上来
        warns.append(f"桌子是老版本 {ver}，随便跑一次写入命令就自动升到 {SCHEMA_VERSION}")
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
    names = [d.get("name") if isinstance(d, dict) else d for d in data.get("drawers", [])]
    if names != DRAWERS:
        warns.append("抽屉的表不全")
    for t in data.get("tasks", []):
        if t.get("status") == "待查":
            warns.append(f"任务板还有待查：{t.get('id')} {t.get('title', '')}，查完记得结任务")
    if args.workspace:
        ws = Path(args.workspace)
        for d in data.get("drawers", []):
            p = d.get("path") if isinstance(d, dict) else None
            # 没填路径 = 这张表还没生出来（早期阶段正常）；填了却找不到 = 真丢了
            if p and not (ws / p).exists() and not Path(p).exists():
                warns.append(f"抽屉里的「{d['name']}」指到的表找不到：{p}")
        check_grades(data, blocks, warns)
        check_pool(ws, data, warns)

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
    try:
        sys.exit(main())
    except Exception:
        # 未预期崩溃 → exit(2)。绝不能让崩溃的退出码(1)与"放行（有提醒）"撞车
        import traceback
        traceback.print_exc()
        sys.exit(2)
