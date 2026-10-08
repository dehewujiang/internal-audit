#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 ledger/ledger.py（add-task/close-task/create/add-line）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下任务板（A1+A2）的事前红测试。锁五件事：
          ① 无来源建任务 → 拒收（缺 room/ref 其一即拦）
          ② 同一 ref 已有待查任务 → 拒收（占位即户口，防重复）
          ③ close-task 已结不带结论去向 → 拒收（防任务无声消失）
          ④ 老桌无 tasks 字段 → 读写自动升级，不作废
          ⑤ 有户口风险只挂引用不建任务（户口命中即跳过）
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
SANDBOX = Path(tempfile.mkdtemp(prefix="b4ws_"))

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
    r = _run("ledger.py", "create", t, "--table", "B4 任务板")
    assert r.returncode == 0, r.stderr
    return t


def _tasks(t):
    return json.loads(t.read_text(encoding="utf-8-sig")).get("tasks", None)


print("== B4 任务板（新假设落任务，查实转事实）==")

# --- ① 无来源建任务 → 拒收 ---
t = _fresh("无来源桌.json")
r = _run("ledger.py", "add-task", t, "--title", "钢筋回扣疑似内外勾结")
check("无来源建任务 → 非 0 拒收", r.returncode != 0,
      f"退出码={r.returncode}")
check("拒收后 tasks 一条没进", _tasks(t) == [] or _tasks(t) is None,
      f"tasks={_tasks(t)}")

# --- ② 同一 ref 重复建 → 拒收 ---
t = _fresh("重复桌.json")
r1 = _run("ledger.py", "add-task", t, "--title", "钢筋回扣疑似内外勾结",
          "--room", "检查单", "--ref", "R-010")
check("首建 R-010 放行", r1.returncode == 0, f"退出码={r1.returncode}")
r2 = _run("ledger.py", "add-task", t, "--title", "钢筋回扣另一说法",
          "--room", "检查单", "--ref", "R-010")
check("重复 ref 建任务 → 非 0 拒收", r2.returncode != 0,
      f"退出码={r2.returncode}")
check("重复后仍只有一条", isinstance(_tasks(t), list) and len(_tasks(t)) == 1,
      f"tasks={_tasks(t)}")

# --- ③ 已结不带结论去向 → 拒收 ---
t = _fresh("无声消失桌.json")
_run("ledger.py", "add-task", t, "--title", "窝工费虚增",
     "--room", "检查单", "--ref", "R-011")
tid = _tasks(t)[0]["id"]
r = _run("ledger.py", "close-task", t, "--id", tid, "--verdict", "已结")
check("已结不带结论去向 → 非 0 拒收", r.returncode != 0,
      f"退出码={r.returncode}")
check("拒收后任务仍是待查", _tasks(t)[0]["status"] == "待查",
      f"status={_tasks(t)[0]['status']}")

# --- ③b 已结带 finding → 放行且状态翻转 ---
r = _run("ledger.py", "close-task", t, "--id", tid, "--verdict", "已结",
         "--finding", "F-2026-010")
check("已结带单号 → 放行", r.returncode == 0, f"退出码={r.returncode}")
check("任务状态变已结", _tasks(t)[0]["status"] == "已结",
      f"status={_tasks(t)[0]['status']}")

# --- ④ 老桌无 tasks 字段 → 自动升级 ---
t = _fresh("老桌.json")
data = json.loads(t.read_text(encoding="utf-8-sig"))
del data["tasks"]
data["schema_version"] = "1.2"
t.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
r = _run("ledger.py", "add-task", t, "--title", "转包挂靠",
         "--room", "检查单", "--ref", "R-013")
check("老桌写任务 → 放行且自动升级", r.returncode == 0,
      f"退出码={r.returncode}")
check("升级后 tasks 是一条", isinstance(_tasks(t), list) and len(_tasks(t)) == 1)

# --- ⑤ 有户口只挂引用（约定：add-task 遇户口 ref 拒绝建任务） ---
t = _fresh("户口桌.json")
r = _run("ledger.py", "add-task", t, "--title", "变更签证随意加钱",
         "--room", "检查单", "--ref", "CG-01",
         "--known-anchor", "CG-01")
check("户口命中 → 不建任务（拒收或跳过）", r.returncode != 0 or _tasks(t) == [],
      f"退出码={r.returncode} tasks={_tasks(t)}")

print()
if failures:
    print(f"B4 红→绿：{len(failures)} 项未过 —— {failures}")
    sys.exit(1)
print("B4 全绿")
