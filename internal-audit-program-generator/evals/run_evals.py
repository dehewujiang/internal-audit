#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_evals.py — 审计程序生成器 eval case 运行器

读取 program-generator 的输出（Markdown 审计程序），对照 eval case 的 expected 条件，
执行确定性检查（字符串匹配、正则），不使用 LLM-as-judge。

[INPUT]:  evals/case-*.json + 审计程序 .md 文件
[OUTPUT]: 每个 case 的 ✅/❌ 汇总 + 退出码 (0=全部通过, 1=有失败)
[POS]:    internal-audit-program-generator/evals/ 的运行脚本
"""

import json
import os
import sys
import re
import glob


def load_cases(evals_dir: str) -> list:
    """加载所有 eval case"""
    cases = []
    for fpath in sorted(glob.glob(os.path.join(evals_dir, "case-*.json"))):
        with open(fpath, "r", encoding="utf-8") as f:
            cases.append(json.load(f))
    return cases


def load_program(program_path: str) -> str:
    """读取审计程序 Markdown"""
    with open(program_path, "r", encoding="utf-8") as f:
        return f.read()


def check_activated_tracks(text: str, expected_tracks: list) -> tuple:
    """检查激活的轨道"""
    found_tracks = []
    for t in ["A", "B", "C", "D", "E", "F"]:
        if re.search(rf'轨道\s*{t}[：:\s]|Track\s*{t}[：:\s]|## .*轨道\s*{t}|测试程序.*轨道\s*{t}', text):
            found_tracks.append(t)
    expected_set = set(expected_tracks)
    found_set = set(found_tracks)
    missing = expected_set - found_set
    if missing:
        return False, f"缺少轨道: {', '.join(sorted(missing))}（期望: {', '.join(expected_tracks)}，实际: {', '.join(found_tracks)}）"
    return True, f"轨道匹配: {', '.join(found_tracks)}"


def check_must_have(text: str, must_have: list) -> tuple:
    """检查必须包含的内容"""
    missing = []
    for keyword in must_have:
        if keyword not in text:
            missing.append(keyword)
    if missing:
        return False, f"缺少必要内容: {', '.join(missing)}"
    return True, None


def check_must_not_have(text: str, must_not_have: list) -> tuple:
    """检查不能包含的内容"""
    found = []
    for keyword in must_not_have:
        if keyword in text:
            found.append(keyword)
    if found:
        return False, f"包含不应有的内容: {', '.join(found)}"
    return True, None


def check_company_facts(text: str, facts: list, min_count: int) -> tuple:
    """检查公司事实引用"""
    found = [f for f in facts if f in text]
    if len(found) < min_count:
        return False, f"公司事实引用不足: {len(found)}/{min_count}（期望至少 {min_count} 条，找到: {', '.join(found)}）"
    return True, f"公司事实引用: {len(found)} 条"


def run_case(case: dict, program_text: str) -> dict:
    """运行单个 eval case"""
    expected = case.get("expected", {})
    results = {}

    # 检查激活轨道
    if "activated_tracks" in expected:
        ok, msg = check_activated_tracks(program_text, expected["activated_tracks"])
        results["activated_tracks"] = {"passed": ok, "message": msg}

    # 检查必须包含
    if "must_have" in expected:
        ok, msg = check_must_have(program_text, expected["must_have"])
        results["must_have"] = {"passed": ok, "message": msg}

    # 检查不能包含
    if "must_not_have" in expected:
        ok, msg = check_must_not_have(program_text, expected["must_not_have"])
        results["must_not_have"] = {"passed": ok, "message": msg}

    # 检查公司事实
    if "company_facts_required" in expected:
        ok, msg = check_company_facts(
            program_text,
            expected["company_facts_required"],
            expected.get("min_company_fact_count", 1)
        )
        results["company_facts"] = {"passed": ok, "message": msg}

    # 检查缺口覆盖
    if "gap_coverage_required" in expected:
        missing = [g for g in expected["gap_coverage_required"] if g not in program_text]
        if missing:
            results["gap_coverage"] = {"passed": False, "message": f"未覆盖缺口: {', '.join(missing)}"}
        else:
            results["gap_coverage"] = {"passed": True, "message": "全部缺口已覆盖"}

    all_passed = all(r["passed"] for r in results.values())
    return {
        "case": case["name"],
        "passed": all_passed,
        "checks": results,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="审计程序 eval case 运行器")
    parser.add_argument("program", help="审计程序 .md 文件路径")
    parser.add_argument("--evals-dir", default=os.path.dirname(os.path.abspath(__file__)),
                        help="evals 目录路径（默认：脚本所在目录）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    cases = load_cases(args.evals_dir)
    if not cases:
        print("[ERROR] 未找到 eval case 文件")
        sys.exit(2)

    program_text = load_program(args.program)
    results = []
    has_failure = False

    for case in cases:
        result = run_case(case, program_text)
        results.append(result)
        if not result["passed"]:
            has_failure = True

    if not args.json:
        for r in results:
            emoji = "✅" if r["passed"] else "❌"
            print(f"\n  {emoji} {r['case']}")
            for name, check in r["checks"].items():
                status = "✅" if check["passed"] else "❌"
                msg = check.get("message", "")
                print(f"    {status} [{name}] {msg[:80]}")

        passed = sum(1 for r in results if r["passed"])
        print(f"\n{'='*60}")
        print(f"  共计 {len(results)} 个 case: ✅ {passed}  ❌ {len(results)-passed}")
        print(f"{'='*60}\n")
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    sys.exit(1 if has_failure else 0)


if __name__ == "__main__":
    main()
