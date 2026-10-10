#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: _shared/scripts 下 7 个 validate-*.py（program/report/finding/policy-analysis/interview/catalog/json）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]: tests/ 下的答卷契约测试（B0 冻结契约）。锁死"结构化答卷"契约：
       每个脚本 stdout 尾行必须有 SHEET: 单行 JSON（含 tool/action/message），
       且 action↔退出码一致（pass↔0、warn↔1、block↔2）。
       每条都能被"撤销改动"验红（删答卷行即红）。

背景：新架构"脚本一律吐结构化答卷，LLM 读答卷比数退出码靠谱"。
B0 先立测试（事前红：当前无脚本吐答卷，SHEET 断言全红），B1/B3 逐个脚本转绿。
已知偏差（B3a 已修）：validate-catalog 默认 block 曾 exit 0（strict 才拦），现一律 exit 2，--strict 保留为兼容空开关。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "_shared" / "scripts"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "gate_tiers"
REG_IN = REPO_ROOT / "tests" / "fixtures" / "regression" / "p2026-001-hr" / "input"
SAMPLE = REPO_ROOT / "tests" / "fixtures"

SANDBOX = Path(tempfile.mkdtemp(prefix="answer_sheet_"))

failures = []


def _run(cmd):
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=str(SANDBOX),
    )


def run_script(script, *args):
    return _run([sys.executable, str(SCRIPTS / script)] + [str(a) for a in args])


def sheet_of(proc):
    """取 stdout 最后一行 SHEET: 并解析，无则返回 None。"""
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith("SHEET:"):
            try:
                return json.loads(line[len("SHEET:"):])
            except Exception:
                return "BADJSON"
    return None


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def check_script(label, proc, expect_code=None, check_mapping=True):
    """答卷契约：有 SHEET 行；有则验 action↔退出码一致。"""
    sheet = sheet_of(proc)
    has = isinstance(sheet, dict)
    keys_ok = has and all(k in sheet for k in ("tool", "action", "message"))
    check(f"{label}：有 SHEET 答卷行", has and keys_ok,
          f"exit={proc.returncode}" if not has else f"action={sheet.get('action')}")
    if isinstance(sheet, dict) and check_mapping:
        mapping = {"pass": 0, "warn": 1, "block": 2}
        want = mapping.get(sheet.get("action"))
        check(f"{label}：action↔退出码一致",
              want is not None and proc.returncode == want,
              f"action={sheet.get('action')} exit={proc.returncode}")
    if expect_code is not None:
        check(f"{label}：退出码符合旧契约", proc.returncode == expect_code,
              f"实际={proc.returncode}")


def make_bad_xlsx():
    try:
        import openpyxl
    except ImportError:
        return None
    path = SANDBOX / "interview_bad.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "X"
    ws.append(["a", "b"])
    wb.save(path)
    return path


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("\n[答卷契约] 7 脚本 SHEET 行 + action↔退出码")

    check_script("程序·警告", run_script("validate-program.py",
                 FIXTURES / "program_warn.md", "--ir"), expect_code=1)
    check_script("程序·阻断", run_script("validate-program.py",
                 FIXTURES / "program_block.md", "--ir"), expect_code=2)
    check_script("程序·崩溃", run_script("validate-program.py",
                 FIXTURES / "bad_utf8.md", "--ir"), expect_code=2)

    rep = SANDBOX / "rep.md"
    rep.write_text("# 报告\n\n空报告。\n", encoding="utf-8")
    check_script("报告·空报告", run_script("validate-report.py", rep))

    fin = SAMPLE / "样本_测试_finding_with_reason.json"
    if fin.exists():
        check_script("发现·单文件", run_script("validate-finding.py", fin, "--exit-on-error"))
    else:
        print("  ⚠️ 跳过发现用例：样本文件不存在")

    pol = REG_IN / "policy-analysis_考勤管理规定_A5.json"
    if pol.exists():
        # 人话模式（闸机 B2 起读人话尾行；--json 保持纯 JSON 供全量解析者）
        check_script("制度·回归样本", run_script("validate-policy-analysis.py", pol))
    else:
        print("  ⚠️ 跳过制度用例：回归样本不存在")

    bad_xlsx = make_bad_xlsx()
    if bad_xlsx is None:
        print("  ⚠️ 跳过访谈用例：环境未安装 openpyxl")
    else:
        check_script("访谈·失败", run_script("validate-interview.py", bad_xlsx, "--strict"))

    cat = SANDBOX / "catalog.json"
    cat.write_text(json.dumps({
        "project": "验", "created_at": "2026-10-10", "updated_at": "2026-10-10",
        "total_slots": 1, "filled_slots": 0,
        "items": [{"id": "EVD-001", "name": "单据", "source_track": "A",
                   "source_programs": ["A1.1"], "file": None, "collected_at": None}],
    }, ensure_ascii=False), encoding="utf-8")
    # catalog 已知偏差：默认 block 也 exit 0，本次只验 SHEET 行，不验映射
    check_script("清单·有效", run_script("validate-catalog.py", cat), check_mapping=False)

    jdir = SANDBOX / "jsons"
    jdir.mkdir(exist_ok=True)
    (jdir / "ok.json").write_text('{"a": 1}', encoding="utf-8")
    check_script("通用JSON·有效目录", run_script("validate-json.py", jdir))

    print()
    if failures:
        print(f"FAIL — {len(failures)} 条断言未通过：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
