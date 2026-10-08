#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 ledger/ledger.py（add-line/add-evidence/set-slot/link-finding/create）
          + ledger/check.py（--workspace 硬度两档）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下第二步（写入口收权）的事前红测试。锁四件事：
          ① 红格新增无 A/E → exit 2 拒收（C 级不够硬也拒）
          ② 先贴 A/E 再写 → 放行；非红格/改字不受影响
          ③ 门卫 check.py 两档改读桌子（舞弊拦死/非舞弊提醒）
          ④ 拒收时桌子没写坏（一句没进）
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
SANDBOX = Path(tempfile.mkdtemp(prefix="b2ws_"))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def _run(script, *args):
    r = subprocess.run(
        [sys.executable, str(LEDGER / script)] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8")
    return r


def _fresh(name):
    t = SANDBOX / name
    r = _run("ledger.py", "create", t, "--table", "B2 写入口")
    assert r.returncode == 0, r.stderr
    return t


def _red_text(t):
    data = json.loads(t.read_text(encoding="utf-8-sig"))
    for x in data.get("left", []):
        if x.get("slot") == "怀疑偷骗":
            return x.get("text", "")
    return ""


print("== B2 写入口收权（红格无 A/E 拒收）==")

# --- ① 红格新增：右边空 → exit 2 拒收，桌子没写坏 ---
t = _fresh("无证据桌.json")
r = _run("ledger.py", "add-line", t, "--slot", "怀疑偷骗",
         "--text", "地磅夜班少2吨疑似被卖", "--room", "执行取证",
         "--ref", "F-2026-001", "--status", "已确认")
check("红格无证据新增 → exit 2 拒收", r.returncode == 2,
      f"退出码={r.returncode} {r.stdout.strip()[:60]}")
check("拒收理由提到硬证据/A/E", "A" in r.stdout and "E" in r.stdout,
      r.stdout.strip()[:80])
check("拒收后红格一句没进", _red_text(t) == "")

# --- ② C 级不够硬 → 照样拒收 ---
t = _fresh("C级桌.json")
_run("ledger.py", "add-evidence", t, "--file", "称重单3张", "--from", "地磅员",
     "--when", "2026-10-08", "--grade", "C", "--room", "执行取证", "--ref", "F-2026-001")
r = _run("ledger.py", "add-line", t, "--slot", "怀疑偷骗",
         "--text", "地磅夜班少2吨疑似被卖", "--room", "执行取证",
         "--ref", "F-2026-001", "--status", "已确认")
check("只有 C 级证据 → 仍 exit 2", r.returncode == 2, f"退出码={r.returncode}")

# --- ③ 先贴 A 再写 → 放行 ---
t = _fresh("A级桌.json")
_run("ledger.py", "add-evidence", t, "--file", "地磅系统导出", "--from", "系统",
     "--when", "2026-10-08", "--grade", "A", "--room", "执行取证", "--ref", "F-2026-001")
r = _run("ledger.py", "add-line", t, "--slot", "怀疑偷骗",
         "--text", "地磅夜班少2吨疑似被卖", "--room", "执行取证",
         "--ref", "F-2026-001", "--status", "已确认")
check("有 A 级证据 → exit 0 放行", r.returncode == 0, f"退出码={r.returncode}")
check("放行后红格有字", "少2吨" in _red_text(t))

# --- ④ E 级同样是硬证据 ---
t = _fresh("E级桌.json")
_run("ledger.py", "add-evidence", t, "--file", "第三方称重报告", "--from", "计量所",
     "--when", "2026-10-08", "--grade", "E")
r = _run("ledger.py", "add-line", t, "--slot", "怀疑偷骗", "--text", "少2吨疑似被卖")
check("E 级证据（无单号查全桌）→ 放行", r.returncode == 0, f"退出码={r.returncode}")

# --- ⑤ 非红格不受影响 ---
t = _fresh("非红桌.json")
r = _run("ledger.py", "add-line", t, "--slot", "确定的毛病", "--text", "领料没签字")
check("确定的毛病无证据 → exit 0", r.returncode == 0, f"退出码={r.returncode}")

# --- ⑥ set-slot 改字不管（①a）---
t = _fresh("改字桌.json")
r = _run("ledger.py", "set-slot", t, "--slot", "怀疑偷骗", "--text", "改个措辞")
check("set-slot 改红格无证据 → exit 0（只拦新增）", r.returncode == 0,
      f"退出码={r.returncode}")

# --- ⑦ 门卫 check.py 两档改读桌子 ---
def _full_table(name, red_text, grade):
    t = _fresh(name)
    _run("ledger.py", "add-line", t, "--slot", "确定的毛病", "--text", "领料没签字")
    _run("ledger.py", "add-line", t, "--slot", "说不清的信号", "--text", "丢3张单子待查")
    _run("ledger.py", "add-evidence", t, "--file", "称重单", "--from", "地磅员",
         "--when", "2026-10-08", "--grade", grade, "--room", "执行取证", "--ref", "F-2026-001")
    # 红格行用 set-slot 摆进去（只拦新增不拦改字，摆门卫夹具正好走这条路）
    _run("ledger.py", "set-slot", t, "--slot", "怀疑偷骗", "--text", red_text,
         "--room", "执行取证", "--ref", "F-2026-001", "--status", "已确认")
    _run("ledger.py", "link-finding", t, "--slot", "怀疑偷骗", "--finding", "F-2026-001")
    return t


ws = SANDBOX / "check_ws"
ws.mkdir(exist_ok=True)

t = _full_table("门卫舞弊桌.json", "夜班少2吨疑似舞弊卖出", "C")
r = _run("check.py", t, "--workspace", ws)
check("门卫：红格舞弊字眼+只有C → exit 2 拦死", r.returncode == 2,
      f"退出码={r.returncode}")
check("拦死理由点名硬证据", "硬证据" in r.stdout, r.stdout.strip()[:80])

t = _full_table("门卫非舞弊桌.json", "夜班少2吨原因待查", "C")
r = _run("check.py", t, "--workspace", ws)
check("门卫：红格无舞弊字眼+只有C → exit 1 提醒", r.returncode == 1,
      f"退出码={r.returncode}")

t = _full_table("门卫有A桌.json", "夜班少2吨疑似舞弊卖出", "A")
r = _run("check.py", t, "--workspace", ws)
check("门卫：红格有A → exit 0 放行", r.returncode == 0, f"退出码={r.returncode}")

print()
print(f"汇总: {'全过' if not failures else str(len(failures)) + ' 条失败'}")
if failures:
    for f in failures:
        print(f"  ❌ {f}")
    sys.exit(1)
sys.exit(0)
