#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 ledger/ledger.py（save 经各写命令）+ _shared/scripts/phase_gate.py（advance）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下快照换历史表（A5）的事前红测试。锁四件事：
          ① 落盘一次历史多一行（合法 JSON 行，带 op）
          ② 21 次写入历史 21 行，且无 .snaps 新目录
          ③ advance 不建 snapshots/，但 audit_trail 有事件
          ④ 连写后桌子永远是合法 JSON 且无 .tmp 残留（原子性）
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
LEDGER = REPO_ROOT / "ledger"
PHASE_GATE = REPO_ROOT / "_shared" / "scripts" / "phase_gate.py"
SANDBOX = Path(tempfile.mkdtemp(prefix="b7ws_"))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def _run(script, *args, cwd=None):
    return subprocess.run(
        [sys.executable, str(script)] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(cwd) if cwd else None)


def _history(t):
    h = t.parent / (t.stem + ".history.jsonl")
    if not h.exists():
        return None
    return [json.loads(line) for line in
            h.read_text(encoding="utf-8").splitlines() if line.strip()]


print("== B7 快照换历史表（只增不减，原子落账）==")

# --- ① 落盘一次历史多一行 ---
ws = SANDBOX / "历史"
iw = ws / "internal-audit-workspace"
(iw / "audit-table").mkdir(parents=True)
t = iw / "audit-table" / "T.json"
r = _run(LEDGER / "ledger.py", "create", t, "--table", "B7")
assert r.returncode == 0, r.stderr
r = _run(LEDGER / "ledger.py", "add-task", t, "--title", "假设一",
         "--room", "检查单", "--ref", "R-010")
rows = _history(t)
check("写一次历史多一行", rows is not None and len(rows) == 2,
      f"行数={len(rows) if rows is not None else '无文件'}")
check("历史行是合法 JSON 且带 op",
      bool(rows) and all(isinstance(x, dict) and x.get("op") for x in rows),
      str(rows[-1])[:120] if rows else "")

# --- ② 21 次写入历史 21+2 行，无 .snaps 新目录 ---
for i in range(21):
    _run(LEDGER / "ledger.py", "add-line", t, "--slot", "说不清的信号",
         "--text", f"第{i}次")
rows = _history(t)
check("21 次写入历史对上数", rows is not None and len(rows) == 2 + 21,
      f"行数={len(rows) if rows is not None else '无文件'}")
check("无 .snaps 新目录", not (t.parent / (t.stem + ".snaps")).exists())

# --- ③ advance 不建 snapshots，但 audit_trail 有事件 ---
ws2 = SANDBOX / "阶段"
iw2 = ws2 / "internal-audit-workspace"
(iw2 / "audit-programs").mkdir(parents=True)
(iw2 / "audit-programs" / "P.md").write_text("# 程序", encoding="utf-8")
(iw2 / "current-audit.json").write_text(json.dumps(
    {"status": "phase_2_program_generation", "audit_topic": "T",
     "audit_purpose": "查", "audit_state": {"audit_purpose": "查"}},
    ensure_ascii=False), encoding="utf-8")
r = _run(PHASE_GATE, "advance", cwd=ws2)
check("advance 照常放行", r.returncode == 0, f"退出码={r.returncode} {r.stdout[:100]}")
check("没建 snapshots 目录", not (iw2 / "snapshots").exists())
trail = json.loads((iw2 / "current-audit.json").read_text(encoding="utf-8-sig")) \
    .get("audit_state", {}).get("audit_trail", [])
check("audit_trail 有前进事件",
      any(x.get("event_type") == "phase_advance" for x in trail),
      f"事件数={len(trail)}")

# --- ④ 原子性：合法 JSON + 无残留 ---
try:
    json.loads(t.read_text(encoding="utf-8-sig"))
    valid = True
except Exception:
    valid = False
check("连写后桌子是合法 JSON", valid)
leftovers = list(t.parent.glob("*.tmp")) + list(iw2.glob("*.tmp"))
check("无 .tmp 残留", leftovers == [], str(leftovers))

print()
if failures:
    print(f"B7 红→绿：{len(failures)} 项未过 —— {failures}")
    sys.exit(1)
print("B7 全绿")
