#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 ledger/ledger.py（--json）+ ledger/check.py（--json）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下答卷收尾（A6a）的事前红测试。锁三件事：
          ① --json 时追一条 SHEET 答卷行（tool/action/message 键齐全）
          ② 人话 verdict 与答卷 action 一致（拦下↔exit 2）
          ③ 不加 --json 时输出与改前一致（一个字不少，不动码）
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
SANDBOX = Path(tempfile.mkdtemp(prefix="b8ws_"))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def _run(script, *args):
    return subprocess.run(
        [sys.executable, str(LEDGER / script)] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8")


def _sheet(out):
    for line in out.splitlines():
        if line.startswith("SHEET:"):
            try:
                return json.loads(line[len("SHEET:"):])
            except Exception:
                return None
    return None


def _fresh(name):
    t = SANDBOX / name
    r = _run("ledger.py", "create", t, "--table", "B8")
    assert r.returncode == 0, r.stderr
    return t


print("== B8 答卷收尾（人话照旧，答卷可读，码不动）==")

# --- ① 成功行带答卷 ---
t = _fresh("答卷桌.json")
r = _run("ledger.py", "--json", "add-task", t, "--title", "假设一",
         "--room", "检查单", "--ref", "R-010")
s = _sheet(r.stdout)
check("成功有 SHEET 行", s is not None, r.stdout[:120])
check("答卷键齐全", bool(s) and {"tool", "action", "message"} <= set(s.keys()),
      str(s)[:160] if s else "")
check("成功 verdict 一致", bool(s) and s["action"] == "pass" and r.returncode == 0,
      f"action={s.get('action') if s else None} exit={r.returncode}")

# --- ② 拒收行带答卷且 verdict 一致 ---
r = _run("ledger.py", "--json", "add-line", t, "--slot", "怀疑偷骗",
         "--text", "疑似舞弊", "--room", "执行取证", "--ref", "F-1",
         "--status", "已确认")
s = _sheet(r.stdout)
check("拒收有 SHEET 行", s is not None)
check("拦下 verdict 一致", bool(s) and s["action"] == "block" and r.returncode == 2,
      f"action={s.get('action') if s else None} exit={r.returncode}")

# --- ③ 不加 --json 与改前一致 ---
r = _run("ledger.py", "add-task", t, "--title", "假设二",
         "--room", "检查单", "--ref", "R-011")
check("默认无人话之外行", "SHEET:" not in r.stdout and "立好任务" in r.stdout,
      r.stdout[:120])

print()
if failures:
    print(f"B8 红→绿：{len(failures)} 项未过 —— {failures}")
    sys.exit(1)
print("B8 全绿")
