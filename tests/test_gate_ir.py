#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/ 下的 validate-program.py / audit_gate.py
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]: tests/ 下的专项测试。覆盖"闸机接 --ir"的两个副作用修复——
       ① ir_parse 解析失败应阻断（原先只算 warn 会误放）
       ② program_ir_parser 导入失败应警告放行（原先 exit 2 会误拦）
       ③ 闸机 generate_program 须传 --ir 给 validate-program.py
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

背景：audit_gate.py 调用 validate-program.py 时从不传 --ir，导致覆盖率/判定标准/
数据来源三类阻断从未生效。直接加 --ir 会引入两个副作用，本测试锁死修复后的行为。
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "_shared" / "scripts"

failures = []


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(label, actual, expected):
    if actual == expected:
        print(f"  ✅ {label}: {actual}")
    else:
        print(f"  ❌ {label}: 实际 {actual}，期望 {expected}")
        failures.append(label)


# 一份能通过全部文本阻断项的最小程序（含轨道标识 + 合规表格 + 公司事实）
GOOD_PROGRAM = (
    "# 测试程序\n\n"
    "公司：武汉长源，紧固件制造，SAP 系统。\n\n"
    "## 三、轨道A：文档检查\n\n"
    "| 程序编号 | 测试目的 | 判定标准 | 取证方式 | 数据来源 | 抽样方法 |\n"
    "|---------|---------|---------|---------|---------|---------|\n"
    "| A1.1 | 测试 | 系统导出数据完整率100% | 系统导出 | SAP | 全查 |\n"
)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    vp = load_module("validate_program", SCRIPTS / "validate-program.py")
    ag = load_module("audit_gate", SCRIPTS / "audit_gate.py")

    # ── [一] ir_parse 解析失败 → 应阻断（block），不是警告（warn） ──
    print("\n[一] ir_parse 解析失败应阻断")
    # 先用好文本 + 无 ir 验证基线：不触发 block
    baseline = vp.validate_program(GOOD_PROGRAM, filename="ok.md", ir=None)
    check("基线（无 ir）→ action 不是 block", baseline["action"] != "block", True)
    # 再注入 _parse_error：修复后应变为 block
    ir = {"_parse_error": "模拟解析失败"}
    result = vp.validate_program(GOOD_PROGRAM, filename="test.md", ir=ir)
    check("ir_parse 失败 → action", result["action"], "block")

    # ── [二] 闸机 generate_program 须传 --ir ──
    print("\n[二] 闸机传 --ir 给 validate-program.py")
    postcheck = ag.ACTIONS["generate_program"]["postcheck"]
    args = postcheck.get("args", [])
    check("generate_program args 包含 --ir", "--ir" in args, True)

    # ── [三] program_ir_parser 导入失败 → 应警告放行（exit 0/1），不是阻断（exit 2） ──
    print("\n[三] 导入失败应警告放行")
    with tempfile.TemporaryDirectory(prefix="gate_ir_") as tmpdir:
        # 在临时目录放坏的 program_ir_parser.py + 一份好程序
        bad_parser = Path(tmpdir) / "program_ir_parser.py"
        bad_parser.write_text("raise ImportError('模拟导入失败')\n", encoding="utf-8")
        prog = Path(tmpdir) / "prog.md"
        prog.write_text(GOOD_PROGRAM, encoding="utf-8")

        # 把 validate-program.py 拷进临时目录运行——脚本目录即 tmpdir，
        # import program_ir_parser 会命中坏模块（而非 _shared/scripts/ 的真模块）
        script_copy = Path(tmpdir) / "validate-program.py"
        shutil.copy2(SCRIPTS / "validate-program.py", script_copy)

        r = subprocess.run(
            [sys.executable, str(script_copy), str(prog), "--ir"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=tmpdir,
            env={**os.environ, "PYTHONPATH": tmpdir},
        )
        check("导入失败 → 退出码（0/1=放行，2=阻断）", r.returncode in (0, 1), True)

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
