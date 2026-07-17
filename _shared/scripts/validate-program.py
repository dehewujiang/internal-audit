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
from pathlib import Path


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
    """[R] 风险点有对应的测试程序（粗略检查）

    注：本检查为正则粗扫，结构化覆盖度请用 --ir 模式（check_ir_coverage_rate）。
    风险编号兼容 R01 / R-001；程序编号兼容 A1.1 / B2.3-C。
    """
    # 统计风险编号出现次数
    risk_ids = re.findall(r'[Rr]-?\d+', text)
    test_ids = re.findall(r'[A-F]\d+(?:\.\d+)?(?:-C)?', text)
    unique_risks = set(risk_ids)
    unique_tests = set(test_ids)
    if not unique_risks:
        return True, "未发现风险编号（R01/R-001 格式），可能使用了不同的编号体系"
    if not unique_tests:
        return False, f"发现了 {len(unique_risks)} 个风险点但无对应测试程序编号（A1.1/B2.3 格式）"
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


def check_column_consistency(text, config_path=None):
    """[C] 表格结构合法性校验——验证MD各轨道表格列数一致性

    v3.0 重写：不再与 program_templates.json 比对列名/列数。
    只校验表格结构的合法性：
    - 每个轨道至少有一个表格
    - 每个表格的数据行与表头列数一致
    """
    issues = []
    SECTION_TO_TRACK = {'三': 'A', '四': 'B', '五': 'C', '六': 'E', '七': 'F', '八': 'D'}

    headings = list(re.finditer(r'^##\s+(.+?)(?:\[.+?\])?\s*$', text, re.MULTILINE))
    ALIGN_SEP = re.compile(r'^\|[:\-\s|]+\|?\s*$')

    for i, m in enumerate(headings):
        title = m.group(1).strip()
        num_match = re.match(r'([一二三四五六七八九十]+)[、．.]', title)
        if not num_match:
            continue
        track_id = SECTION_TO_TRACK.get(num_match.group(1))
        if not track_id:
            continue

        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        track_content = text[start:end]
        track_lines = track_content.split('\n')
        table_count = 0

        j = 0
        while j < len(track_lines):
            stripped = track_lines[j].strip()
            if ALIGN_SEP.match(stripped) and j > 0:
                header_line = track_lines[j - 1].strip()
                if not (header_line.startswith('|') and header_line.endswith('|')):
                    j += 1
                    continue

                header_cols = [c.strip() for c in header_line[1:-1].split('|')]
                header_count = len(header_cols)
                table_count += 1

                # 验证数据行（从分隔行下一行到下一个分隔行或非表格行）
                k = j + 1
                row_num = 1
                while k < len(track_lines):
                    data_line = track_lines[k].strip()
                    if ALIGN_SEP.match(data_line):
                        break
                    if not data_line.startswith('|') or not data_line.endswith('|'):
                        if data_line == '' or not data_line.startswith('|'):
                            break
                        k += 1
                        continue

                    data_cols = [c.strip() for c in data_line[1:-1].split('|')]
                    if len(data_cols) != header_count:
                        issues.append(
                            f"轨道{track_id} 表格行{row_num}列数不一致："
                            f"表头有{header_count}列，数据行有{len(data_cols)}列"
                        )
                    row_num += 1
                    k += 1

                j = k
                continue
            j += 1

        if table_count == 0:
            issues.append(f"轨道{track_id} 未找到任何表格")

    return len(issues) == 0, "; ".join(issues) if issues else None


# ── IR 结构化校验（--ir 模式）──────────────────────────

# block 级检查（失败即阻断）。文本检查 + IR 检查统一在此声明。
BLOCKER_KEYS = {
    "no_placeholder", "track_activation", "column_consistency",
    "ir_coverage_rate", "ir_criterion", "ir_data_source",
}

SWITCH_WORDS = {'是', '否', '有', '无', '存在', '不存在', '符合', '不符合',
                'yes', 'no', 'true', 'false'}
FUZZY_WORDS = ['较大', '过多', '不足', '一般', '偏高', '偏低', '显著', '基本']


def check_ir_coverage_rate(ir):
    """[IR] 覆盖度：风险清单 − 程序覆盖，覆盖率 < 80% → block"""
    register_ids = {r['risk_id'] for r in ir.get('risk_register', []) if r['risk_id']}
    if not register_ids:
        return True, "未抽到风险清单，覆盖度检查跳过（请确认 2.1/2.2 风险识别清单表存在）"
    rate = ir['coverage']['coverage_rate']
    if rate < 0.8:
        unc = [u['risk_id'] for u in ir['coverage']['uncovered_risks']]
        return False, f"覆盖率 {rate*100:.0f}% < 80%（未覆盖：{', '.join(unc[:10])}）"
    return True, f"覆盖率 {rate*100:.0f}%（{len(register_ids)} 个风险）"


def check_ir_coverage_uncovered(ir):
    """[IR] 有未覆盖风险但无理由 → warn（非阻断）"""
    no_reason = [u['risk_id'] for u in ir['coverage']['uncovered_risks']
                 if not u.get('reason', '').strip()]
    if no_reason:
        return False, f"{len(no_reason)} 个风险未覆盖且无理由：{', '.join(no_reason[:10])}（建议补充理由或加程序）"
    return True, None


def check_ir_criterion(ir):
    """[IR] 判定标准量化：纯开关词 / 模糊词 / 空 → block"""
    bad = []
    for s in ir['steps']:
        c = (s.get('criterion') or '').strip()
        sid = s.get('step_id', '?')
        if not c:
            bad.append(f"{sid}:判定标准为空")
            continue
        if c.lower() in SWITCH_WORDS:
            bad.append(f"{sid}:开关型('{c}')")
            continue
        if any(w in c for w in FUZZY_WORDS):
            bad.append(f"{sid}:含模糊词('{c[:24]}')")
    if bad:
        return False, f"{len(bad)} 个程序判定标准不达标：{'; '.join(bad[:5])}"
    return True, None


def check_ir_data_source(ir):
    """[IR] 数据来源比例：空 data_source 步骤 > 30% → block"""
    steps = ir['steps']
    if not steps:
        return True, "无步骤，跳过"
    empty = [s['step_id'] for s in steps if not (s.get('data_source') or '').strip()]
    ratio = len(empty) / len(steps)
    if ratio > 0.3:
        return False, f"{len(empty)}/{len(steps)} ({ratio*100:.0f}%) 步骤无数据来源 > 30%"
    return True, f"{len(empty)}/{len(steps)} 步骤无数据来源"


def check_ir_sampling(ir):
    """[IR] 轨道A 抽样方法缺失 → warn（非阻断）"""
    missing = [s['step_id'] for s in ir['steps']
               if s.get('track') == 'A' and not (s.get('sampling') or '').strip()]
    if missing:
        return False, f"{len(missing)} 个轨道A步骤缺抽样方法：{', '.join(missing[:10])}"
    return True, None


def check_ir_decision_rationale(ir):
    """[IR] 决策理由字数：D-003≥30、D-004/D-005≥20 → warn（非阻断）"""
    dl = ir.get('decision_log', {})
    issues = []
    for did, minn in [('D-003', 30), ('D-004', 20), ('D-005', 20)]:
        r = (dl.get(did, {}) or {}).get('rationale', '').strip()
        if not r:
            issues.append(f"{did}缺理由")
        elif len(r) < minn:
            issues.append(f"{did}理由{len(r)}字<{minn}")
    if issues:
        return False, "; ".join(issues) + "（非阻断，建议补充）"
    return True, None


def run_ir_checks(ir):
    """对 ProgramIR 执行全部 IR 结构化检查，返回 {check_name: {passed, message}}。"""
    checks = {}
    for name, fn in [
        ("ir_coverage_rate", check_ir_coverage_rate),
        ("ir_coverage_uncovered", check_ir_coverage_uncovered),
        ("ir_criterion", check_ir_criterion),
        ("ir_data_source", check_ir_data_source),
        ("ir_sampling", check_ir_sampling),
        ("ir_decision_rationale", check_ir_decision_rationale),
    ]:
        try:
            passed, msg = fn(ir)
        except Exception as e:
            passed, msg = False, f"检查异常: {e}"
        checks[name] = {"passed": passed, "message": msg}
    return checks


# ── 主校验 ──────────────────────────────────────────────

def validate_program(text, filename="", ir=None):
    """对审计程序文本执行全部校验。ir 非 None 时追加 IR 结构化检查。"""
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

    passed, msg = check_column_consistency(text)
    checks["column_consistency"] = {"passed": passed, "message": msg}

    # IR 结构化检查（仅 --ir 模式）
    ir_error = None
    if ir is not None:
        if isinstance(ir, dict) and ir.get("_parse_error"):
            ir_error = ir.get("_parse_error")
            checks["ir_parse"] = {"passed": False,
                                  "message": f"ProgramIR 解析失败，IR 检查跳过：{ir_error}"}
        else:
            checks.update(run_ir_checks(ir))

    blockers = [k for k, v in checks.items() if not v["passed"] and k in BLOCKER_KEYS]
    warnings = [k for k, v in checks.items() if not v["passed"] and k not in BLOCKER_KEYS]

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
    parser.add_argument("--ir", action="store_true",
                        help="追加 ProgramIR 结构化校验（覆盖度/判定标准量化/数据来源比例等）")
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

    # --ir 模式：懒加载解析器（避免非 ir 模式依赖 program_generator）
    build_ir = None
    if args.ir:
        try:
            from program_ir_parser import build_ir as _build_ir
            build_ir = _build_ir
        except Exception as e:
            print(f"[ERROR] 无法加载 program_ir_parser: {e}", file=sys.stderr)
            sys.exit(2)

    results = []
    has_blocker = False
    has_warn = False

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()
        ir = None
        if args.ir and build_ir:
            try:
                ir = build_ir(Path(fpath))
            except Exception as e:
                ir = {"_parse_error": str(e)}
        report = validate_program(text, filename=os.path.basename(fpath), ir=ir)
        results.append(report)
        if report["action"] == "block":
            has_blocker = True
        elif report["action"] == "warn":
            has_warn = True

        if not args.json:
            emoji = {"pass": "✅", "warn": "⚠️", "block": "🔴"}
            print(f"\n  {emoji[report['action']]} {os.path.basename(fpath)} — {report['action'].upper()}")
            for name, data in report["checks"].items():
                if data["passed"]:
                    status = "✅"
                elif name in BLOCKER_KEYS:
                    status = "🔴"
                else:
                    status = "⚠️"
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
