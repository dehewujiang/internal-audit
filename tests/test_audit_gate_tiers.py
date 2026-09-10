#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 tests/fixtures/gate_tiers/ 的夹具（program_warn/program_block/bad_utf8/interview_bad）、
         _shared/scripts/ 下的 validate-program.py / validate-interview.py / audit_gate.py
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]: tests/ 下的专项测试。回归基线 regression-check.py 只覆盖"阻断"场景，
       本脚本专门覆盖闸机新增的"警告放行 / 阻断拦下 / 崩溃兜底"三档语义
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

背景：audit_gate.py 曾把"非 0 退出码"一律判失败，导致校验脚本的"警告"(exit 1)
与"阻断"(exit 2) 在闸机眼里没有区别，"只提醒不拦"这一档位形同不存在。
本测试锁死修复后的行为——三条断言缺一不可，且每条都能被"撤销改动"验红。
"""

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "_shared" / "scripts"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "gate_tiers"

# 隔离的工作目录：避免测试运行时找到真实项目的 current-audit.json 而写入审计轨迹
SANDBOX = tempfile.mkdtemp(prefix="gate_tiers_")

failures = []


def _run(cmd):
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=SANDBOX,
    )


def run_script(script, *args):
    return _run([sys.executable, str(SCRIPTS / script)] + [str(a) for a in args])


def run_gate(action, fixture):
    return _run([
        sys.executable, str(SCRIPTS / "audit_gate.py"), "postcheck",
        "--action", action, "--file", str(FIXTURES / fixture),
    ])


def make_bad_xlsx():
    """现场生成一份不合格的访谈 Excel（列数不足）。

    不往版本库塞二进制夹具——仓库 .gitignore 含 *.xlsx 规则。
    返回 None 表示环境缺 openpyxl（validate-interview.py 本身也依赖它）。
    """
    try:
        import openpyxl
    except ImportError:
        return None
    path = Path(SANDBOX) / "interview_bad.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "X"
    ws.append(["a", "b"])
    wb.save(path)
    return path


def check(label, actual, expected):
    if actual == expected:
        print(f"  ✅ {label}: {actual}")
    else:
        print(f"  ❌ {label}: 实际 {actual}，期望 {expected}")
        failures.append(label)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("\n[一] 校验脚本退出码三档")
    check("程序·警告场景 → 退出码",
          run_script("validate-program.py", FIXTURES / "program_warn.md").returncode, 1)
    check("程序·阻断场景 → 退出码",
          run_script("validate-program.py", FIXTURES / "program_block.md").returncode, 2)
    check("程序·脚本崩溃（非 UTF-8）→ 退出码应为阻断而非警告",
          run_script("validate-program.py", FIXTURES / "bad_utf8.md").returncode, 2)
    bad_xlsx = make_bad_xlsx()
    if bad_xlsx is None:
        print("  ⚠️ 跳过访谈断言：环境未安装 openpyxl")
    else:
        check("访谈·校验失败 + --strict → 退出码",
              run_script("validate-interview.py", bad_xlsx, "--strict").returncode, 2)

    print("\n[二] 闸机三档（警告放行 / 阻断拦下）")
    warn_run = run_gate("generate_program", "program_warn.md")
    check("闸机·警告场景 → 退出码（0=放行）", warn_run.returncode, 0)
    check("闸机·警告场景 → 确实打印了警告", "⚠️" in warn_run.stdout, True)

    block_run = run_gate("generate_program", "program_block.md")
    check("闸机·阻断场景 → 退出码（1=拦下）", block_run.returncode, 1)
    check("闸机·阻断场景 → 确实打印了拦截", "❌" in block_run.stdout, True)

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
