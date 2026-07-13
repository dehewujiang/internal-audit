#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-report.py — 审计报告硬校验脚本

对报告生成器输出的 Markdown 报告执行确定性校验。
在 report-generator/SKILL.md Step 3 调用。

[INPUT]:  审计报告 Markdown 文件路径
[OUTPUT]: JSON 格式校验报告 + 退出码 (0=pass, 1=warn, 2=block)
[POS]:    _shared/scripts 的报告校验工具，被 report-generator/SKILL.md 引用
"""

import json
import os
import sys
import re
import argparse


# ── 校验项 ──────────────────────────────────────────────

def check_no_unreplaced_placeholders(text):
    """[P] 无未替换的占位符"""
    patterns = {
        "double_brace": re.findall(r'\{\{[^}]+\}\}', text),
        "blank_square": re.findall(r'\[\s+\]', text),
        "underscore_x": re.findall(r'_X_\w*', text),
        "blank_line": re.findall(r'_{3,}', text),
    }
    issues = []
    for name, matches in patterns.items():
        if matches:
            issues.append(f"{name}: {len(matches)} 处（如 {matches[0][:40]}）")
    return len(issues) == 0, "; ".join(issues) if issues else None


def check_conclusion_completeness(text):
    """[C] 综合结论四要素完整性"""
    # 检查报告中是否存在结论相关的结构
    elements = {
        "总体判断": bool(re.search(r'整体有效|部分有效|无效|总体判断', text)),
        "系统性风险评级": bool(re.search(r'系统性|孤立|风险评级', text)),
        "TOP3排序": bool(re.search(r'TOP\s*3|核心问题排序|问题排序', text)),
        "历史对比": bool(re.search(r'新发现|重复发现|已整改|未整改|历史对比|上期审计', text)),
    }
    missing = [k for k, v in elements.items() if not v]
    if len(missing) >= 3:
        return False, f"综合结论缺失 {len(missing)}/4 要素: {', '.join(missing)}"
    if missing:
        return True, f"综合结论缺失 {len(missing)}/4 要素: {', '.join(missing)}（非阻断，建议补充）"
    return True, "综合结论四要素完整"


def check_date_format(text):
    """[D] 日期格式——无空白日期"""
    blank_dates = re.findall(r'\d{4}年\s+\d{1,2}月\s+\d{1,2}日|\[\s*\]月|\[\s*\]日', text)
    if blank_dates:
        return False, f"发现 {len(blank_dates)} 处空白日期: {blank_dates[0][:30]}"
    return True, None


def check_has_findings_summary(text):
    """[F] 报告包含发现汇总"""
    has_summary = bool(re.search(r'发现汇总|finding.*汇总|审计发现.*统计|F-\d{4}-\d{3}', text))
    if not has_summary:
        return False, "报告中未找到发现汇总或 finding 引用"
    return True, None


def check_risk_distribution_consistency(text):
    """[R] 风险分布与总体判断一致性（粗略检查）"""
    # 统计高风险数量
    high_risk_count = len(re.findall(r'高风险|risk_level.*高|🔴', text))
    # 检查总体判断
    is_effective = bool(re.search(r'整体有效', text))
    if high_risk_count >= 3 and is_effective:
        return False, f"发现 {high_risk_count} 处高风险标记，但总体判断为「整体有效」——存在矛盾"
    return True, f"高风险标记 {high_risk_count} 处，总体判断一致性检查通过"


def check_conclusion_rationale(text):
    """[L] 决策理由记录——报告结论应有理由说明（D-008/D-009）"""
    issues = []
    # D-008：纳入报告判断——finding是否纳入报告
    if not re.search(r'(?:纳入|排出|筛选).*(?:finding|发现|问题)', text, re.IGNORECASE) and not re.search(r'(?:finding|审计发现|selected_findings)', text, re.IGNORECASE):
        issues.append("D-008（纳入报告判断）：未找到 finding 筛选/纳入说明")
    # D-009：报告结论理由
    has_conclusion = re.search(r'(?:审计结论|审计意见|综合结论|整体评价)', text)
    if has_conclusion:
        # 找到了结论段，检查是否有理由
        conclusion_start = has_conclusion.start()
        around = text[conclusion_start:conclusion_start+500]
        if not re.search(r'(?:因为|原因|理由|基于|根据|依据)', around):
            issues.append("D-009（报告结论）：结论段缺少理由/依据说明")
    else:
        issues.append("D-009（报告结论）：未找到审计结论段")

    if issues:
        return True, "; ".join(issues) + "（非阻断，建议补充）"
    return True, None


# ── 主校验 ──────────────────────────────────────────────

def validate_report(text, filename=""):
    """对审计报告文本执行全部校验"""
    checks = {}

    passed, msg = check_no_unreplaced_placeholders(text)
    checks["no_placeholders"] = {"passed": passed, "message": msg}

    passed, msg = check_conclusion_completeness(text)
    checks["conclusion_completeness"] = {"passed": passed, "message": msg}

    passed, msg = check_date_format(text)
    checks["date_format"] = {"passed": passed, "message": msg}

    passed, msg = check_has_findings_summary(text)
    checks["findings_summary"] = {"passed": passed, "message": msg}

    passed, msg = check_risk_distribution_consistency(text)
    checks["risk_consistency"] = {"passed": passed, "message": msg}

    passed, msg = check_conclusion_rationale(text)
    checks["conclusion_rationale"] = {"passed": passed, "message": msg}

    blockers = [k for k, v in checks.items() if not v["passed"]
                and k in ("no_placeholders", "date_format")]
    warnings = [k for k, v in checks.items() if not v["passed"]
                and k not in ("no_placeholders", "date_format")]

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
    # Windows GBK → UTF-8（emoji 兼容）
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="审计报告硬校验工具")
    parser.add_argument("path", help="报告 Markdown 文件路径（或目录）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--strict", action="store_true", help="严格模式：存在阻断时打印到 stderr 并 exit(1)")
    args = parser.parse_args()

    files = []
    target = args.path
    if os.path.isdir(target):
        for root, _, fnames in os.walk(target):
            for fn in sorted(fnames):
                if fn.endswith(".md"):
                    files.append(os.path.join(root, fn))
    elif os.path.isfile(target):
        files.append(target)
    else:
        print(f"[ERROR] 路径不存在: {target}")
        sys.exit(2)

    if not files:
        print("[ERROR] 未找到 .md 文件")
        sys.exit(2)

    results = []
    has_blocker = False
    has_warn = False

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()
        report = validate_report(text, filename=os.path.basename(fpath))
        results.append(report)
        if report["action"] == "block":
            has_blocker = True
        elif report["action"] == "warn":
            has_warn = True

        if not args.json:
            emoji = {"pass": "✅", "warn": "⚠️", "block": "🔴"}
            print(f"\n  {emoji[report['action']]} {os.path.basename(fpath)} — {report['action'].upper()}")
            for name, d in report["checks"].items():
                status = "✅" if d["passed"] else "🔴" if name in ("no_placeholders", "date_format") else "⚠️"
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

    if args.strict and has_blocker:
        for r in results:
            if r["action"] == "block":
                block_msgs = [b["message"] for b in r["summary"]["blockers"]]
                print(f"[BLOCK] {r['file']}: {', '.join(block_msgs)}", file=sys.stderr)
        sys.exit(1)

    sys.exit(2 if has_blocker else 1 if has_warn else 0)


if __name__ == "__main__":
    main()
