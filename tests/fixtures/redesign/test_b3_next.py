#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/phase_gate.py（next 子命令）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下第三步（下一步命令）的事前红测试。锁四件事：
          ① 输出有"能干/还缺/工具"三段
          ② 缺口指到具体动作（空阶段点名制度分析）
          ③ 有桌子行时指到上桌+门卫
          ④ 只报不拦——缺口再大 exit 0；未知阶段也不拦
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
GATE = REPO_ROOT / "_shared" / "scripts" / "phase_gate.py"
SANDBOX = Path(tempfile.mkdtemp(prefix="b3ws_"))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def _proj(name, status, files=None):
    proj = SANDBOX / name
    iw = proj / "internal-audit-workspace"
    iw.mkdir(parents=True, exist_ok=True)
    (iw / "current-audit.json").write_text(json.dumps({
        "schema_version": "1.0", "status": status,
        "audit_topic": "写入口测试", "audit_state": {},
    }, ensure_ascii=False), encoding="utf-8")
    for f in (files or []):
        p = iw / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    return proj


def _next(proj):
    r = subprocess.run(
        [sys.executable, str(GATE), "next"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(proj))
    return r.returncode, r.stdout + r.stderr


print("== B3 下一步命令（代码算路）==")

# --- ① 空 phase_1：三段都有，缺口点名制度分析 ---
code, out = _next(_proj("空制度", "phase_1_document_analysis"))
check("三段齐（能干/还缺/工具）",
      "能干" in out and "缺" in out and "工具" in out, out.strip()[:100])
check("缺口点名制度分析", "制度分析" in out or "policy-analyses" in out,
      out.strip()[:100])

# --- ② phase_3 有桌子行：指到上桌+门卫 ---
code3, out3 = _next(_proj("执行中", "phase_3_execution", [
    "audit-table/废料.json",
    "audit-programs/程序.md",
]))
check("执行阶段指到上桌", "上桌" in out3 or "add-line" in out3, out3.strip()[:100])
check("执行阶段指到门卫自查", "门卫" in out3 or "check.py" in out3,
      out3.strip()[:100])

# --- ③ 只报不拦 ---
check("缺口再大 exit 0", code == 0, f"退出码={code}")

# --- ④ 未知阶段也不拦 ---
code4, out4 = _next(_proj("未知", "phase_9_不存在"))
check("未知阶段 exit 0", code4 == 0, f"退出码={code4}")
check("未知阶段说人话", "未知" in out4, out4.strip()[:80])

print()
print(f"汇总: {'全过' if not failures else str(len(failures)) + ' 条失败'}")
if failures:
    for f in failures:
        print(f"  ❌ {f}")
    sys.exit(1)
sys.exit(0)
