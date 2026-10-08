#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/query_data_sources.py（SingleProjectSource /
          CrossProjectSource / load_table_findings / load_index / load_finding）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下第一步（关双轨）的事前红测试。锁三件事：
          ① 查询只认桌子（findings/*.json 旧格式不再被读）
          ② 桌子兼容字段全保留（风险/状态/搜索都能按原口径过滤）
          ③ 跨项目查询也只扫各项目的桌子
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md
"""

import json
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # tests/fixtures/redesign/xxx.py -> repo
SHARED = REPO_ROOT / "_shared" / "scripts"
FIXTURE = Path(__file__).resolve().parent / "b1_ws" / "internal-audit-workspace"
sys.path.insert(0, str(SHARED))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


# 场景：沙箱里 findings/F-2026-001.json（旧格式，高风险"待整改"）和
# 桌子 left[]（怀疑偷骗=高风险）各有一条。关双轨后：
#   - 单项目查询"高"风险 → 只出桌子的 1 条（旧 finding 不再计入）
#   - 全文搜索 → 只搜桌子的 1 条（旧 finding 文件不读）
#   - 兼容字段（risk_level/status/origin）仍能过滤桌子行

import os

# 走 CLI 子进程（与 CI 同口径）：queries.py 同目录 import query_commands，
# 但直接 import 需要先把 SHARED 加进 sys.path（文件头已做）
import subprocess

os.chdir(FIXTURE.parent)  # b1_ws/ —— queries.py 的 find_workspace 从 cwd 向上找

def run_q(*args):
    r = subprocess.run(
        [sys.executable, str(SHARED / "queries.py")] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(FIXTURE.parent))
    return r.returncode, r.stdout + r.stderr

# 跑 CLI 时把 SHARED 目录本身作为脚本所在目录（Python 自动加 sys.path[0]）
import importlib
sys.path.insert(0, str(SHARED))
qds = importlib.import_module("query_data_sources")
qds.find_workspace = lambda: FIXTURE  # 免去向上搜索，直指 fixture

print("== B1 查询只认桌子（关双轨）==")

# --- ① 单项目查询：旧 findings/ 不再进结果 ---
res = qds.SingleProjectSource().query_findings(risk="高")
old_ids = [r for r in res if r.get("finding_id") == "F-2026-001" and r.get("origin") == "execution"]
table_ids = [r for r in res if r.get("_from_table")]
check("查'高'风险：旧 finding（findings/F-*.json）不再进结果", len(old_ids) == 0,
      f"结果 {len(res)} 条，其中旧格式 {len(old_ids)} 条、桌子 {len(table_ids)} 条")
check("查'高'风险：桌子的'怀疑偷骗'行照常进结果", len(table_ids) == 1)

# --- ② 全文搜索：只搜桌子 ---
# "地磅"只在桌子行里，"称重/无签字"只在旧 finding 里
res = qds.SingleProjectSource().search("地磅")
check("搜索'地磅'：只命中桌子行",
      len(res) == 1 and res[0].get("finding_id", "").startswith("T-"),
      f"命中 {len(res)} 条")

# 搜索一个只存在于旧 finding 的词——关双轨后应 0 命中
res2 = qds.SingleProjectSource().search("无签字")
check("搜索只存在于旧 finding 的词：0 命中", len(res2) == 0, f"命中 {len(res2)} 条")

# --- ③ 兼容字段保留：风险/状态过滤仍生效 ---
res3 = qds.SingleProjectSource().query_findings(risk="高", status="已确认")
check("桌子行带 status='已确认' 可过滤", len(res3) == 1)

print()
print(f"汇总: {'全过' if not failures else str(len(failures)) + ' 条失败'}")
if failures:
    for f in failures:
        print(f"  ❌ {f}")
    sys.exit(1)
sys.exit(0)
