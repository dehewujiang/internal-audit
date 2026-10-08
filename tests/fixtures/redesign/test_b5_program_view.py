#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/validate-program.py（--ir --json --workspace）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下程序视图化（A3）的事前红测试。锁四件事：
          ① 孤儿风险（无任务、无户口）→ ir_ledger_reconcile block
          ② 全员有任务或户口 → pass
          ③ S 增量无对应任务 → block
          ④ 不传 --workspace（旧版程序）→ 跳过不误拦
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
VALIDATE = REPO_ROOT / "_shared" / "scripts" / "validate-program.py"
SANDBOX = Path(tempfile.mkdtemp(prefix="b5ws_"))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def _ws(name, tasks=(), left_refs=(), gaps=()):
    """搭一个最小项目：桌子（任务+左边行）+ 制度分析（缺口编号）。"""
    ws = SANDBOX / name
    (ws / "internal-audit-workspace" / "audit-table").mkdir(parents=True)
    (ws / "internal-audit-workspace" / "policy-analyses").mkdir(parents=True)
    table = {
        "schema_version": "1.3",
        "table": name,
        "left": [{"slot": "说不清的信号", "red": False, "text": f"{r} 风险点",
                  "ref_finding_ids": [], "source": {"room": "看制度", "ref": r}}
                 for r in left_refs],
        "right": [],
        "drawers": [],
        "checklist": [],
        "ingested": {},
        "tasks": [{"id": f"T-{i + 1:03d}", "title": t, "status": "待查",
                   "source": {"room": "检查单", "ref": t},
                   "fact_anchors": [], "ref_finding_ids": [],
                   "created_at": "", "closed_at": ""} for i, t in enumerate(tasks)],
    }
    (ws / "internal-audit-workspace" / "audit-table" / "T.json").write_text(
        json.dumps(table, ensure_ascii=False), encoding="utf-8")
    pa = {"control_gaps": [{"gap_id": g} for g in gaps],
          "risk_points": [], "conflicts": []}
    (ws / "internal-audit-workspace" / "policy-analyses" / "a.json").write_text(
        json.dumps(pa, ensure_ascii=False), encoding="utf-8")
    return ws


def _md(ws, name, rows):
    """写一份带风险识别清单的程序文档。rows: (编号, 名称, 描述, 来源标注)。"""
    lines = ["# 测试审计程序", "### 2.1 风险识别清单",
             "| 风险编号 | 风险名称 | 风险描述 | 来源标注 |",
             "|---|---|---|---|"]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    p = ws / f"{name}.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def _reconcile(md, ws=None):
    cmd = [sys.executable, str(VALIDATE), str(md), "--ir", "--json"]
    if ws is not None:
        cmd += ["--workspace", str(ws)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        reports = json.loads(r.stdout)
        checks = reports[0]["checks"]
    except Exception as e:
        return None, f"输出非 JSON（{e}）：{r.stdout[:120]}|{r.stderr[:120]}"
    return checks.get("ir_ledger_reconcile"), r.returncode


print("== B5 程序视图化（风险清单与账对账）==")

# --- ① 孤儿风险 → block ---
ws = _ws("孤儿", tasks=["R-010"], left_refs=["D-001"], gaps=["CG-01"])
md = _md(ws, "孤儿程序", [
    ("R10", "钢筋回扣", "内外勾结", "【经验类】"),
    ("R99", "凭空风险", "无来源", "【经验类】"),
])
c, info = _reconcile(md, ws)
check("对账项存在", c is not None, str(info)[:80] if c is None else "")
check("孤儿 R-99 → block", bool(c) and not c["passed"] and "R-99" in c["message"],
      str(c)[:160] if c else info)

# --- ② 全员有任务或户口 → pass ---
md = _md(ws, "干净程序", [
    ("R10", "钢筋回扣", "内外勾结", "【经验类】"),
    ("R01", "变更签证", "随意加钱", "【制度类】CG-01"),
])
c, info = _reconcile(md, ws)
check("任务+户口全覆盖 → pass", bool(c) and c["passed"],
      str(c)[:160] if c else info)

# --- ③ S 增量无对应任务 → block ---
md = _md(ws, "增量程序", [("S01", "新增假设", "访谈冒出来的", "【访谈类】")])
c, info = _reconcile(md, ws)
check("无任务 S01 → block", bool(c) and not c["passed"] and "S01" in c["message"],
      str(c)[:160] if c else info)

# --- ④ 不传 --workspace → 跳过不误拦 ---
ws2 = _ws("旧版", tasks=[], left_refs=[], gaps=[])
md2 = _md(ws2, "旧版程序", [("R99", "凭空风险", "无来源", "【经验类】")])
c, info = _reconcile(md2, None)
check("无账可对 → pass 跳过", bool(c) and c["passed"],
      str(c)[:160] if c else info)

print()
if failures:
    print(f"B5 红→绿：{len(failures)} 项未过 —— {failures}")
    sys.exit(1)
print("B5 全绿")
