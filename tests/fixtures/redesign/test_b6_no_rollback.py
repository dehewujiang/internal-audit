#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/phase_gate.py（rollback）+ ledger/ledger.py（rollback/add-task）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下回退消失（A4）的事前红测试。锁四件事：
          ① phase_gate rollback → exit 2 + 指引，status 不变、无新快照
          ② ledger rollback → exit 2 + 文件一字不动
          ③ 新线索只走 add-task 放行（含 S 编号）
          ④ 旧快照/照片文件本身不受影响（只增不减，不断链）
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
PHASE_GATE = REPO_ROOT / "_shared" / "scripts" / "phase_gate.py"
LEDGER = REPO_ROOT / "ledger"
SANDBOX = Path(tempfile.mkdtemp(prefix="b6ws_"))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def _run(script, *args, cwd=None):
    r = subprocess.run(
        [sys.executable, str(script)] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(cwd) if cwd else None)
    return r


def _project(name, status="phase_3_execution"):
    ws = SANDBOX / name
    (ws / "internal-audit-workspace").mkdir(parents=True)
    (ws / "internal-audit-workspace" / "current-audit.json").write_text(
        json.dumps({"status": status, "audit_state": {}}, ensure_ascii=False),
        encoding="utf-8")
    return ws


def _table(ws):
    t = ws / "internal-audit-workspace" / "audit-table" / "T.json"
    t.parent.mkdir(parents=True, exist_ok=True)
    r = _run(LEDGER / "ledger.py", "create", t, "--table", "B6")
    assert r.returncode == 0, r.stderr
    return t


print("== B6 回退消失（倒车改指引，往前走）==")

# --- ① phase_gate rollback → exit 2 + 指引，状态不动 ---
ws = _project("阶段回退")
r = _run(PHASE_GATE, "rollback", "--to", "phase_1_document_analysis",
         "--reason", "补制度", cwd=ws)
check("阶段回退 → exit 2 拒收", r.returncode == 2, f"退出码={r.returncode}")
out = r.stdout + r.stderr
check("拒收带插任务指引", "add-task" in out, out[:120])
data = json.loads((ws / "internal-audit-workspace" / "current-audit.json")
                  .read_text(encoding="utf-8-sig"))
check("status 一个字没动", data.get("status") == "phase_3_execution",
      f"status={data.get('status')}")
check("没拍新快照", not (ws / "internal-audit-workspace" / "snapshots").exists()
      or not list((ws / "internal-audit-workspace" / "snapshots").glob("snap_*.json")),
      "snapshots 有新增" if (ws / "internal-audit-workspace" / "snapshots").exists() else "无快照目录")

# --- ② ledger rollback → exit 2 + 文件不动 ---
t = _table(ws)
snap_d = t.parent / (t.stem + ".snaps")
snap_d.mkdir(exist_ok=True)
(t.with_suffix(".json")).write_bytes(t.read_bytes())
fake = snap_d / "snap_20260101000000000000.json"
fake.write_bytes(t.read_bytes())
before = t.read_bytes()
r = _run(LEDGER / "ledger.py", "rollback", t, "--to", fake.name)
check("桌子回头 → exit 2 拒收", r.returncode == 2, f"退出码={r.returncode}")
check("桌文件一字不动", t.read_bytes() == before)

# --- ③ 新线索只走 add-task（含 S 编号）---
r = _run(LEDGER / "ledger.py", "add-task", t, "--title", "访谈冒出新线索",
         "--room", "检查单", "--ref", "S-001")
check("S 编号立任务 → 放行", r.returncode == 0, f"退出码={r.returncode}")

# --- ④ 照片只增不减 ---
check("旧照片还在", fake.exists(), f"{fake.name} 丢了" if not fake.exists() else "")

print()
if failures:
    print(f"B6 红→绿：{len(failures)} 项未过 —— {failures}")
    sys.exit(1)
print("B6 全绿")
