#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-program.py — 审计程序硬校验脚本

对审计程序文档执行确定性校验，不依赖 LLM 自觉遵循规则。
在 program-generator/SKILL.md Step 5 调用。

[INPUT]:  审计程序 Markdown 文件路径
[OUTPUT]: JSON 格式校验报告 + 退出码 (0=pass, 1=warn, 2=block)
[POS]:    _shared/scripts 的程序校验工具，被 program-generator/SKILL.md 引用
"""

import json
import os
import sys
import re
import argparse


# ── 校验项 ──────────────────────────────────────────────

def check_no_placeholder(text):
    """[S] 无占位符（_X_ 或 {{}}）"""
    # _X_ : 排除"无 _X_ 占位符"这类质量自检行（提及占位符但本身不是占位符）
    x_matches = [m for m in re.findall(r'_X_[^\n]*', text)
                 if not re.search(r'[无沒][\s\S]{0,20}_X_[\s\S]{0,20}(?:占位符|placeholder)', m, re.IGNORECASE)]
    # {{ }} : 要求括号内至少有一个非空白字符（排除 "{{ }}" 空壳和 "{{ }}" 这类自查文案）
    brace_matches = [m for m in re.findall(r'\{\{[^}\s][^}]*\}\}|\{\{[^}]*[^\s}]\}\}', text)
                     if not re.search(r'[无沒][\s\S]{0,30}\{\{', m, re.IGNORECASE)]
    issues = []
    if x_matches:
        issues.append(f"发现 {len(x_matches)} 处 _X_ 占位符: {x_matches[0][:60]}")
    if brace_matches:
        issues.append(f"发现 {len(brace_matches)} 处 {{}} 占位符: {brace_matches[0][:60]}")
    return len(issues) == 0, "; ".join(issues) if issues else None


def check_no_switch_criteria(text):
    """[Q] 量化标准不是开关型（是/否、有/无）"""
    # 在表格行中查找量化标准列
    switch_patterns = [
        r'\|\s*(是|否|有|无|存在|不存在|符合|不符合)\s*\|',
        r'\|\s*(yes|no|true|false)\s*\|',
    ]
    found = []
    for pat in switch_patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        found.extend(matches)
    if len(found) >= 3:
        return False, f"量化标准中发现 {len(found)} 处开关型判断（是/否/有/无），应使用可量化的判定标准"
    if found:
        return True, f"量化标准中发现 {len(found)} 处疑似开关型判断，建议确认"
    return True, None


def check_track_activation(text):
    """[T] 轨道激活标识清晰"""
    tracks = {"A": False, "B": False, "C": False, "D": False, "E": False, "F": False}
    for t in tracks:
        if re.search(rf'轨道\s*{t}[：:\s]|Track\s*{t}[：:\s]|## .*轨道\s*{t}', text):
            tracks[t] = True
    active = [t for t, v in tracks.items() if v]
    if not active:
        return False, "未找到任何轨道标识（A/B/C/D/E/F）"
    return True, f"激活轨道: {', '.join(active)}"


def check_company_facts(text):
    """[F] 引用了公司具体事实（非通用描述）"""
    # 检查是否引用了 about-me.md 中的公司特征
    company_markers = [
        r'21\s*亿', r'2000\s*人', r'紧固件', r'冲焊',
        r'SAP', r'MES', r'泛微', r'62\.24%',
        r'FLAN|Flan|flan',
        r'宁波', r'武汉', r'广东',
        r'大众', r'丰田', r'本田', r'比亚迪',
    ]
    found = [m for m in company_markers if re.search(m, text)]
    if len(found) < 2:
        return False, f"程序中仅引用了 {len(found)} 条公司具体事实（至少需要 2 条），可能使用了通用描述"
    return True, f"引用了 {len(found)} 条公司事实: {', '.join(found[:5])}"


def check_risk_coverage(text):
    """[R] 风险点有对应的测试程序（粗略检查）"""
    # 统计风险编号出现次数
    risk_ids = re.findall(r'[Rr]-\d{3}', text)
    test_ids = re.findall(r'[A-F]-\d{3}', text)
    unique_risks = set(risk_ids)
    unique_tests = set(test_ids)
    if not unique_risks:
        return True, "未发现风险编号（R-XXX 格式），可能使用了不同的编号体系"
    if not unique_tests:
        return False, f"发现了 {len(unique_risks)} 个风险点但无对应测试程序编号（A-XXX/B-XXX 格式）"
    return True, f"风险点 {len(unique_risks)} 个，测试程序 {len(unique_tests)} 个"


def check_decision_log(text):
    """[L] 决策理由记录——程序文本中应有 D-003/D-004/D-005 决策点的理由说明"""
    issues = []
    # 检查是否提到了审计目的选择的理由
    if not re.search(r'(审计目的|审计目标|audit\s*purpose).*(?:因为|原因|理由|基于|由于)', text, re.IGNORECASE):
        issues.append("D-003（审计目的选择）：未找到选择理由说明")
    # 检查是否提到了审计范围的理由
    scope_patterns = [r'审计范围.*(?:为什么|因为|原因|理由|不包括|未纳入|排除)',
                      r'(?:不包括|未纳入|排除).*(?:因为|原因|基于|理由)']
    if not any(re.search(p, text, re.IGNORECASE) for p in scope_patterns):
        issues.append("D-004（审计范围定义）：未找到范围边界理由说明")
    # 检查轨道激活理由
    if not re.search(r'(?:激活|启用|选择).*(?:轨道|track).*(?:因为|理由|原因|基于)', text, re.IGNORECASE):
        if re.search(r'(?:轨道|track)\s*[A-F]', text, re.IGNORECASE):
            # 有轨道标记但无理由
            issues.append("D-005（程序轨道激活）：有轨道选择但未说明为什么选这些轨道")

    if issues:
        return True, "; ".join(issues) + "（非阻断，建议补充）"
    return True, None


# ── 主校验 ──────────────────────────────────────────────

def validate_program(text, filename=""):
    """对审计程序文本执行全部校验"""
    checks = {}

    passed, msg = check_no_placeholder(text)
    checks["no_placeholder"] = {"passed": passed, "message": msg}

    passed, msg = check_no_switch_criteria(text)
    checks["no_switch_criteria"] = {"passed": passed, "message": msg}

    passed, msg = check_track_activation(text)
    checks["track_activation"] = {"passed": passed, "message": msg}

    passed, msg = check_company_facts(text)
    checks["company_facts"] = {"passed": passed, "message": msg}

    passed, msg = check_risk_coverage(text)
    checks["risk_coverage"] = {"passed": passed, "message": msg}

    passed, msg = check_decision_log(text)
    checks["decision_log"] = {"passed": passed, "message": msg}

    blockers = [k for k, v in checks.items() if not v["passed"]
                and k in ("no_placeholder", "track_activation")]
    warnings = [k for k, v in checks.items() if not v["passed"]
                and k not in ("no_placeholder", "track_activation")]

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
    # Windows 终端默认 GBK 编码，emoji（🔴⚠️✅）会触发 UnicodeEncodeError。
    # 在打印任何 emoji 之前先把 stdout 切到 UTF-8。
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="审计程序硬校验工具")
    parser.add_argument("path", help="审计程序 Markdown 文件路径（或目录）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--strict", action="store_true", help="block时exit 1而非exit 0")
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
        report = validate_program(text, filename=os.path.basename(fpath))
        results.append(report)
        if report["action"] == "block":
            has_blocker = True
        elif report["action"] == "warn":
            has_warn = True

        if not args.json:
            emoji = {"pass": "✅", "warn": "⚠️", "block": "🔴"}
            print(f"\n  {emoji[report['action']]} {os.path.basename(fpath)} — {report['action'].upper()}")
            for name, data in report["checks"].items():
                status = "✅" if data["passed"] else "🔴" if name in ("no_placeholder", "track_activation") else "⚠️"
                msg = data.get("message") or "通过"
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
                print(f"[BLOCK] {r['file']}: {', '.join(b['message'] for b in r['summary']['blockers'])}", file=sys.stderr)
        sys.exit(1)

    sys.exit(2 if has_blocker else 1 if has_warn else 0)


if __name__ == "__main__":
    main()
