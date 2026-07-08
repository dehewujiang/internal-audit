#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-policy-analysis.py — 制度分析 JSON 硬校验脚本

对 document-organizer 输出的制度分析 JSON 执行确定性校验。
在 document-organizer/SKILL.md Step 5 调用。

[INPUT]:  policy-analyses/ 下的 JSON 文件路径
[OUTPUT]: JSON 格式校验报告 + 退出码 (0=pass, 1=warn, 2=block)
[POS]:    _shared/scripts 的制度分析校验工具，被 document-organizer/SKILL.md 引用
"""

import json
import os
import sys
import argparse


# ── 校验项 ──────────────────────────────────────────────

def check_schema(data):
    """[S] JSON schema 合规——必要数组存在且非空"""
    required_arrays = ["control_points", "risk_points"]
    missing = []
    empty = []
    for key in required_arrays:
        if key not in data:
            missing.append(key)
        elif not isinstance(data[key], list):
            missing.append(f"{key}（类型错误，应为数组）")
        elif len(data[key]) == 0:
            empty.append(key)
    issues = []
    if missing:
        issues.append(f"缺少必要字段: {', '.join(missing)}")
    if empty:
        issues.append(f"空数组: {', '.join(empty)}")
    return len(missing) == 0, "; ".join(issues) if issues else None


def check_ocr_completeness(data, filename=""):
    """[O] OCR 完整性——total_controls>0 但 analyzed_controls==0 说明 PDF 未 OCR"""
    total = data.get("total_controls", 0)
    analyzed = data.get("analyzed_controls", 0)
    if not isinstance(total, int) or not isinstance(analyzed, int):
        return True, "total_controls/analyzed_controls 非数字，跳过"
    if total > 0 and analyzed == 0:
        return False, (f"total_controls={total} 但 analyzed_controls=0"
                       "，疑似 PDF 未 OCR，请先运行 OCR 工具后重新分析")
    return True, None


def check_schema_version(data):
    """[V] schema_version 存在"""
    sv = data.get("schema_version")
    if not sv:
        return False, "缺少 schema_version 字段"
    return True, f"schema_version: {sv}"


def check_control_points_traceability(data):
    """[T] 控制点可追溯——每个控制点指向原文条款"""
    points = data.get("control_points", [])
    if not points:
        return True, "无控制点，跳过"
    no_source = []
    for i, cp in enumerate(points):
        if not isinstance(cp, dict):
            continue
        has_source = any(cp.get(f) for f in ("source_section", "source_doc", "source_clause", "原文出处"))
        if not has_source:
            title = cp.get("title", cp.get("name", f"#{i+1}"))
            no_source.append(str(title)[:40])
    if len(no_source) > len(points) * 0.3:
        return False, f"{len(no_source)}/{len(points)} 个控制点缺少原文出处: {', '.join(no_source[:3])}"
    if no_source:
        return True, f"{len(no_source)} 个控制点缺少出处（未超阈值，非阻断）"
    return True, None


def check_risk_points_structure(data):
    """[R] 风险点有描述和风险等级"""
    points = data.get("risk_points", [])
    if not points:
        return True, "无风险点，跳过"
    issues = []
    for i, rp in enumerate(points):
        if not isinstance(rp, dict):
            continue
        has_desc = any(rp.get(f) for f in ("description", "title", "name"))
        has_level = any(rp.get(f) for f in ("severity", "risk_level", "level"))
        label = rp.get("title", rp.get("name", f"#{i+1}"))
        if not has_desc:
            issues.append(f"风险点 {label}: 缺少描述")
        if not has_level:
            issues.append(f"风险点 {label}: 缺少风险等级")
    if len(issues) > 3:
        return False, f"{len(issues)} 个问题（仅显示前3）: {'; '.join(issues[:3])}"
    if issues:
        return True, "; ".join(issues)
    return True, None


def check_control_gaps_not_all_pending(data):
    """[G] 控制缺口不是全部标记为待确认"""
    gaps = data.get("control_gaps", [])
    if not gaps:
        return True, "无控制缺口，跳过"
    pending = sum(1 for g in gaps if isinstance(g, dict)
                  and g.get("verification_status", "").startswith("待"))
    if pending == len(gaps):
        return False, f"全部 {len(gaps)} 个控制缺口都标记为「待确认」，至少应有部分已确认"
    return True, f"{len(gaps)} 个缺口，{pending} 个待确认，{len(gaps)-pending} 个已确认"


# ── 主校验 ──────────────────────────────────────────────

def validate_policy_analysis(data, filename=""):
    """对制度分析 JSON 执行全部校验"""
    checks = {}

    passed, msg = check_schema(data)
    checks["schema"] = {"passed": passed, "message": msg}

    passed, msg = check_ocr_completeness(data, filename)
    checks["ocr_completeness"] = {"passed": passed, "message": msg}

    passed, msg = check_schema_version(data)
    checks["schema_version"] = {"passed": passed, "message": msg}

    passed, msg = check_control_points_traceability(data)
    checks["traceability"] = {"passed": passed, "message": msg}

    passed, msg = check_risk_points_structure(data)
    checks["risk_points_structure"] = {"passed": passed, "message": msg}

    passed, msg = check_control_gaps_not_all_pending(data)
    checks["gaps_resolution"] = {"passed": passed, "message": msg}

    blockers = [k for k, v in checks.items() if not v["passed"]
                and k in ("schema", "schema_version", "ocr_completeness")]
    warnings = [k for k, v in checks.items() if not v["passed"]
                and k not in ("schema", "schema_version", "ocr_completeness")]

    action = "block" if blockers else ("warn" if warnings else "pass")

    return {
        "file": filename,
        "action": action,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "passed": sum(1 for v in checks.values() if v["passed"]),
            "blockers": [{"check": k, "message": checks[k]["message"]} for k in blockers],
            "warnings": [{"check": k, "message": checks[k]["message"]} for k in warnings],
        }
    }


# ── CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="制度分析 JSON 硬校验工具")
    parser.add_argument("path", help="JSON 文件路径（或目录）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    files = []
    target = args.path
    if os.path.isdir(target):
        for root, _, fnames in os.walk(target):
            for fn in sorted(fnames):
                if fn.endswith(".json"):
                    files.append(os.path.join(root, fn))
    elif os.path.isfile(target):
        files.append(target)
    else:
        print(f"[ERROR] 路径不存在: {target}")
        sys.exit(2)

    if not files:
        print("[ERROR] 未找到 .json 文件")
        sys.exit(2)

    results = []
    has_blocker = False
    has_warn = False

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  🔴 [JSON格式错误] {os.path.basename(fpath)}: {e}")
            has_blocker = True
            continue

        report = validate_policy_analysis(data, filename=os.path.basename(fpath))
        results.append(report)
        if report["action"] == "block":
            has_blocker = True
        elif report["action"] == "warn":
            has_warn = True

        if not args.json:
            emoji = {"pass": "✅", "warn": "⚠️", "block": "🔴"}
            print(f"\n  {emoji[report['action']]} {os.path.basename(fpath)} — {report['action'].upper()}")
            for name, d in report["checks"].items():
                status = "✅" if d["passed"] else "🔴" if name in ("schema", "schema_version", "ocr_completeness") else "⚠️"
                msg = d.get("message") or "通过"
                print(f"    {status} [{name}] {msg[:100]}")

    if not args.json:
        passed = sum(1 for r in results if r["action"] == "pass")
        warned = sum(1 for r in results if r["action"] == "warn")
        blocked = sum(1 for r in results if r["action"] == "block")
        print(f"\n{'='*60}")
        print(f"  共计 {len(results)} 个文件: ✅ {passed}  ⚠️  {warned}  🔴 {blocked}")
        print(f"{'='*60}\n")
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    sys.exit(2 if has_blocker else 1 if has_warn else 0)


if __name__ == "__main__":
    main()
