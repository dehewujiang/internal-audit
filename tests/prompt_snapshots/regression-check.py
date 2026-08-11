#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regression-check.py — 回归基线检查（R09 自动化部分）

[INPUT]:  tests/fixtures/regression/<case>/expected_output/*.txt（基线）+ input/（用例输入）
[OUTPUT]: 每用例 GREEN/RED/SKIP 判定 + 汇总；exit 0=无 RED / 1=有 RED
[POS]:    tests/prompt_snapshots 的开发工具，被 .git/hooks/pre-commit 调用

判定：对每个 expected_output/<前缀>.txt，按文件名前缀映射校验脚本与输入文件，
重跑脚本对比 exit code 与基线。exit 一致 → GREEN；不一致 → RED
（脚本行为变化 = 兼容性风险）。全 GREEN 放行，有 RED 拦截 commit。

基线解析规则：读取 expected_output 中 `## exit code` 标题后的第一行，
提取首个整数（兼容 `2（BLOCK）`、`1 (BLOCK)`、`0` 等写法）。

[PROTOCOL]: 新增校验脚本用例时，在 CASE_SCRIPTS 注册前缀映射
             （脚本相对仓库根路径 + 额外参数 + 输入文件匹配 glob 列表）。
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# 仓库根 = 本脚本所在目录（tests/prompt_snapshots/）的上三级
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# expected_output 文件名前缀 → (校验脚本相对仓库根路径, 额外参数, 输入匹配 glob 列表)
# 输入匹配：按 glob 列表顺序取 input/ 下第一个命中的文件（前缀优先，退化到扩展名）。
CASE_SCRIPTS = {
    "validate-policy-analysis": (
        "_shared/scripts/validate-policy-analysis.py",
        [],
        ["*policy-analysis*.json", "*.json"],
    ),
    "validate-program": (
        "_shared/scripts/validate-program.py",
        ["--ir", "--strict"],
        ["*audit-program*.md", "*.md"],
    ),
}

EXIT_SECTION_RE = re.compile(r"##\s*exit\s*code", re.IGNORECASE)
EXIT_NUM_RE = re.compile(r"(\d+)")


def parse_baseline_exit(text):
    """从基线 txt 解析 exit code：`## exit code` 标题后第一行的首个整数。"""
    m = EXIT_SECTION_RE.search(text)
    if not m:
        return None
    rest = text[m.end():]
    lines = [ln.strip() for ln in rest.splitlines() if ln.strip()]
    if not lines:
        return None
    m2 = EXIT_NUM_RE.search(lines[0])
    return int(m2.group(1)) if m2 else None


def find_input_file(input_dir, patterns):
    """按 glob 列表顺序返回 input/ 下第一个命中文件；无命中返回 None。"""
    for pat in patterns:
        matches = sorted(input_dir.glob(pat))
        if matches:
            return matches[0]
    return None


def run_case(fixtures_dir, case_dir, expected_txt):
    """运行单个用例，返回 (status, detail)；status ∈ GREEN / RED / SKIP。"""
    prefix = expected_txt.stem
    spec = CASE_SCRIPTS.get(prefix)
    if spec is None:
        return "SKIP", f"未知校验脚本前缀 {prefix!r}（未在 CASE_SCRIPTS 注册）"

    script = REPO_ROOT / spec[0]
    if not script.exists():
        return "SKIP", f"校验脚本不存在: {spec[0]}"

    input_dir = case_dir / "input"
    if not input_dir.is_dir():
        return "SKIP", "input/ 目录缺失"

    inp = find_input_file(input_dir, spec[2])
    if inp is None:
        return "SKIP", f"input/ 下未找到匹配输入文件（glob: {spec[2]}）"

    base_text = expected_txt.read_text(encoding="utf-8", errors="replace")
    baseline = parse_baseline_exit(base_text)
    if baseline is None:
        return "SKIP", f"基线 txt 无法解析 exit code: {expected_txt.name}"

    cmd = [sys.executable, str(script), str(inp)] + list(spec[1])
    proc = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    actual = proc.returncode
    if actual == baseline:
        return "GREEN", f"exit {actual} == 基线 {baseline}"
    return "RED", f"exit {actual} != 基线 {baseline}（脚本行为变化 = 兼容性风险）"


def main():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure and sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="回归基线检查（pre-commit hook 用，对比 tests/fixtures/regression/ 基线）")
    parser.add_argument(
        "--fixtures-dir", default="tests/fixtures/regression",
        help="回归用例根目录（相对仓库根，默认 tests/fixtures/regression）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    args = parser.parse_args()

    fixtures_dir = REPO_ROOT / args.fixtures_dir
    if not fixtures_dir.is_dir():
        print(f"[regression-check] ❌ fixtures 目录不存在: {fixtures_dir}")
        sys.exit(1)

    cases = []  # 每项: {case, expected, status, detail}
    for case_dir in sorted(fixtures_dir.iterdir()):
        if not case_dir.is_dir():
            continue
        expected_dir = case_dir / "expected_output"
        if not expected_dir.is_dir():
            continue
        for txt in sorted(expected_dir.glob("*.txt")):
            status, detail = run_case(fixtures_dir, case_dir, txt)
            cases.append({
                "case": case_dir.name,
                "expected": txt.name,
                "status": status,
                "detail": detail,
            })

    green = sum(1 for c in cases if c["status"] == "GREEN")
    red = sum(1 for c in cases if c["status"] == "RED")
    skip = sum(1 for c in cases if c["status"] == "SKIP")

    if args.json:
        print(json.dumps({
            "fixtures_dir": str(fixtures_dir),
            "cases": cases,
            "summary": {"green": green, "red": red, "skip": skip},
            "exit_code": 1 if red else 0,
        }, ensure_ascii=False, indent=2))
    else:
        for c in cases:
            print(f"[{c['status']}] {c['case']}/{c['expected']}: {c['detail']}")
        print(f"汇总: GREEN={green} RED={red} SKIP={skip}")
        if red:
            print("回归基线检查失败（RED）——SKILL/脚本变更使既有回归用例退出码变化")
            sys.exit(1)
        print("回归基线检查通过")
    sys.exit(0)


if __name__ == "__main__":
    main()
