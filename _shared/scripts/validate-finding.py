#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-finding.py — Finding 质量硬校验脚本

对每个 finding JSON 执行确定性校验，不依赖 LLM 自觉遵循 schema。
在 SKILL.md Step 3b-3 (生成阶段) 和 Step 5 (质量回溯) 调用。

校验项:
  [S] schema_compliance    必要字段完整性（finding_id, origin, title 等）
  [R] root_cause_existence 根因分析存在性（cause + cause_category 或 root_cause_analysis）
  [D] root_cause_depth     根因深度（高风险严禁停在"操作人员未遵守"）
  [C] cceer_completeness   CCEER 五要素完整性
  [E] evidence_grade       证据等级校验 (reliability_grade)
  [I] intuition_engine     直觉引擎完整性（高风险必须）
  [G] cause_evidence_gap   根因与证据等级匹配校验

用法:
    # 校验单个 finding
    python validate-finding.py findings/FIND-001.json

    # 批量校验目录下所有 finding
    python validate-finding.py --findings-dir findings/
    python validate-finding.py --findings-dir findings/ --exit-on-error

    # 从 index.json 读取列表
    python validate-finding.py --index findings/index.json

输出:
    JSON 格式校验报告 + 退出码 (0=全部通过, 1=警告, 2=阻断)
"""

import json
import os
import sys
import re
import argparse
from datetime import datetime


# ── 停表词 ─────────────────────────────────────────────
# 这些词如果出现在根因分析中且无深层追溯，意味着分析停在表层
STOP_WORDS = [
    "操作人员疏忽",
    "操作人员未按规定",
    "操作人员未遵守",
    "操作人员忘记",
    "操作人员大意",
    "操作人员不认真",
    "操作人员态度",
    "个别人员未按规定",
    "个别员工疏忽",
    "一时疏忽",
    "不小心",
    "忘记执行",
    "工作不认真",
    "态度不端正",
    "偶发事件",
    "偶发情况",
    "未严格遵守制度",
    "执行人员未注意",
]

# 深层追溯关键词——如果根因文本中含这些词，说明追到了设计/环境层
ESCALATION_KEYWORDS = [
    "根本原因是",
    "根因是",
    "追溯至",
    "制度设计",
    "系统设计",
    "系统未设置",
    "系统缺少",
    "系统功能缺失",
    "职责设计",
    "职责未分离",
    "职责分离",
    "控制设计",
    "控制环境",
    "管理层",
    "KPI",
    "激励机制",
    "资源不足",
    "培训机制缺失",
    "缺乏培训",
    "流程设计",
    "审批权限设计",
    "治理结构",
    "企业文化",
    "管理层态度",
    "缺编",
    "人员编制",
]

def normalize_level(level):
    """统一风险等级写法"""
    if not level:
        return None
    level = level.strip()
    if level in ("高", "high", "High", "HIGH"):
        return "高"
    if level in ("中", "medium", "Medium", "MEDIUM"):
        return "中"
    if level in ("低", "low", "Low", "LOW"):
        return "低"
    return level


# ── 读取函数 ───────────────────────────────────────────

def load_finding(path):
    """加载并解析 finding JSON，支持 UTF-8 BOM"""
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


# ── 校验器 ─────────────────────────────────────────────

def check_schema_compliance(data):
    """[S] 必要字段完整性"""
    required = ["finding_id", "finding_title", "finding_metadata", "risk_classification"]
    missing = [k for k in required if k not in data]
    if missing:
        return False, f"缺少必要字段: {', '.join(missing)}"

    # 子结构检查
    fm = data.get("finding_metadata", {})
    rc = data.get("risk_classification", {})

    meta_required = ["origin", "status", "verification_status"]
    risk_required = ["risk_level"]

    meta_missing = [k for k in meta_required if k not in fm]
    risk_missing = [k for k in risk_required if k not in rc]

    issues = []
    if meta_missing:
        issues.append(f"finding_metadata 缺少: {', '.join(meta_missing)}")
    if risk_missing:
        issues.append(f"risk_classification 缺少: {', '.join(risk_missing)}")

    if issues:
        return False, "; ".join(issues)
    return True, None


def check_root_cause_existence(data):
    """[R] 根因分析存在性 - 支持新旧两套 schema"""
    has_cause = "cause" in data
    has_cause_cat = "cause_category" in data
    has_rca = "root_cause_analysis" in data

    if has_cause and has_cause_cat:
        return True, "new_schema"  # 新 schema，通过
    if has_rca:
        rca = data["root_cause_analysis"]
        sub_fields = [k for k in ("system_level", "process_level", "management_level", "design_level") if rca.get(k)]
        if sub_fields:
            return True, "legacy"  # 旧 schema，通过但标记
        return False, "root_cause_analysis 字段存在但内容为空"
    if has_cause and not has_cause_cat:
        return False, "存在 cause 字段但缺少 cause_category 标签"
    if has_cause_cat and not has_cause:
        return False, "存在 cause_category 标签但缺少 cause 字段"

    return False, "既无 cause+cause_category（新schema）也无 root_cause_analysis（旧schema）"


def check_root_cause_depth(data, risk_level):
    """[D] 根因深度校验——严禁停表

    检查策略：
      1. 新 schema：检查 cause 字段是否含停表词 + 无深层追溯关键词
      2. 旧 schema：检查 root_cause_analysis 三层是否覆盖到设计/环境层
      3. 低风险 finding 跳过深度检查（形式合规问题允许停在 EXEC-01）
    """
    if risk_level == "低":
        return True, None

    issues = []

    # ── 检查 cause 字段（新 schema） ──
    cause = data.get("cause", "")
    if cause:
        if any(w in cause for w in STOP_WORDS):
            if not any(kw in cause for kw in ESCALATION_KEYWORDS):
                issues.append(f"cause 字段含停表词但未追溯至设计/环境层")
        # 检查长度（非常短的 cause 可能太浅）
        if len(cause.strip()) < 40 and risk_level == "高":
            issues.append(f"cause 字段过短（{len(cause.strip())}字），高风险发现应给出更完整的根因追溯")

    # ── 检查 root_cause_analysis（旧 schema） ──
    rca = data.get("root_cause_analysis", {})
    if rca:
        # 二层/管理层级有内容 → 到达设计/环境层
        has_design_level = bool(rca.get("system_level") or rca.get("design_level"))
        has_env_level = bool(rca.get("management_level"))
        has_process_level = bool(rca.get("process_level"))

        if risk_level == "高":
            if not has_design_level and not has_env_level:
                if has_process_level:
                    process_text = rca.get("process_level", "")
                    if any(w in process_text for w in STOP_WORDS):
                        issues.append(f"root_cause_analysis 停在控制执行层（process_level），含停表词")
                    elif len(process_text) < 30:
                        issues.append(f"root_cause_analysis 停在控制执行层（process_level），分析过浅")
                else:
                    issues.append(f"root_cause_analysis 三层均为空")
            # 检查 management_level 是否为真深层（不只是一个标题）
            if has_env_level:
                mgmt_text = rca.get("management_level", "")
                if mgmt_text and len(mgmt_text.strip()) < 10:
                    issues.append(f"management_level 内容过短（{len(mgmt_text.strip())}字），可能是占位符")

    # ── 完全没有任何根因分析 ──
    if not cause and not rca:
        issues.append(f"完全缺少根因分析")

    if issues:
        return False, "; ".join(issues)
    return True, None


def check_cceer_completeness(data):
    """[C] CCEER 五要素完整性

    Criteria  → 制度/法规引用（finding_description 或 criteria 字段）
    Condition → 实际情况（finding_description.current_state）
    Cause     → 根因分析
    Effect    → 影响（impact_and_risk）
    Recommendation → 建议（recommendations）
    """
    issues = []

    # Criteria: 检查是否有制度引用
    fd = data.get("finding_description", {})
    criteria_sources = []
    # 从 finding_description 中找
    if isinstance(fd, dict):
        for v in fd.values():
            if isinstance(v, str) and re.search(r'[A-Z]{3,4}-?\d{2,4}', v):
                criteria_sources.append(v[:60])
    # 从 cross_references 找
    cr = data.get("cross_references", {})
    docs = cr.get("documents", []) if isinstance(cr, dict) else []
    if docs:
        criteria_sources.extend(docs)

    if not criteria_sources:
        issues.append("Criteria（审计依据）: 未找到制度/法规引用")

    # Condition: finding_description.current_state
    condition_text = ""
    if isinstance(fd, dict):
        condition_text = fd.get("current_state", "")
    if not condition_text:
        issues.append("Condition（实际情况）: 缺少 finding_description.current_state")

    # Cause
    has_cause = "cause" in data
    has_rca = "root_cause_analysis" in data
    if not has_cause and not has_rca:
        issues.append("Cause（根因）: 既无 cause 也无 root_cause_analysis")

    # Effect: impact_and_risk
    ir = data.get("impact_and_risk", {})
    if not ir or (isinstance(ir, dict) and not any(ir.values())):
        issues.append("Effect（影响）: impact_and_risk 为空或缺失")

    # Recommendation
    recs = data.get("recommendations", [])
    if not recs:
        issues.append("Recommendation（建议）: recommendations 为空")
    elif isinstance(recs, list):
        # 检查建议是否有具体内容
        empty_recs = sum(1 for r in recs if not isinstance(r, dict) or not r.get("description"))
        if empty_recs > 0:
            issues.append(f"recommendations 中有 {empty_recs} 条缺少 description")

    if issues:
        return False, "; ".join(issues)
    return True, None


def check_evidence_grade(data):
    """[E] 证据等级校验

    检查每个 evidence 条目是否有 reliability_grade 字段。
    高风险 finding 必须有 ≥1 个 A 级或 E 级证据。
    """
    issues = []
    rc = data.get("risk_classification", {})
    risk_level = normalize_level(rc.get("risk_level"))

    evidence = data.get("evidence", {})
    if not evidence:
        return True, f"无 evidence 字段，跳过校验（非阻断）"

    all_items = []

    # 支持两种 evidence 结构
    if isinstance(evidence, dict):
        # 旧结构: {"primary_evidence": [...], "supporting_evidence": [...]}
        for key in ("primary_evidence", "supporting_evidence"):
            items = evidence.get(key, [])
            if items and isinstance(items, list):
                all_items.extend(items)
    elif isinstance(evidence, list):
        # 新结构: [...] 直接是数组
        all_items = evidence

    if not all_items:
        return True, None

    has_grade_problem = False
    grades_found = set()

    for i, item in enumerate(all_items):
        if not isinstance(item, dict):
            continue
        # 检查 reliability_grade（新标准）
        grade = item.get("reliability_grade")
        if grade:
            grades_found.add(grade.upper())
        else:
            # 回退检查 verification_status
            vs = item.get("verification_status", "")
            if vs in ("已获取", "已核实", "已确认"):
                # 这些旧字段不足以作为 evidence 等级
                pass
            has_grade_problem = True
            issues.append(f"evidence[{i}] 缺少 reliability_grade（必填字段）")

    # 高风险必须有 A 或 E 级证据
    if risk_level == "高" and grades_found:
        if not ("A" in grades_found or "E" in grades_found):
            issues.append(f"高风险 finding 但最高证据等级为 {grades_found}，缺少 A级或E级证据")

    if has_grade_problem:
        return False, "; ".join(issues)

    return True, None


def check_intuition_engine(data):
    """[I] 直觉引擎完整性

    高风险 finding 必须有 intuition_analysis 字段。
    中风险可选。
    """
    rc = data.get("risk_classification", {})
    risk_level = normalize_level(rc.get("risk_level"))

    if risk_level != "高":
        return True, None

    intuition = data.get("intuition_analysis", None)
    if not intuition:
        return False, "高风险 finding 缺少 intuition_analysis 字段"

    # 检查子模块
    if isinstance(intuition, dict):
        modules = ["constellation_detected", "counter_intuitive_flags", "temporal_patterns", "second_order_thinking"]
        missing_modules = [m for m in modules if m not in intuition or not intuition[m]]
        if missing_modules:
            return True, f"intuition_analysis 缺少模块: {', '.join(missing_modules)}（非阻断）"

    return True, None


def check_cause_evidence_gap(data):
    """[G] 根因与证据等级匹配校验

    高风险 finding + 所有 evidence 均为 C/D 级 → 标记"证据等级偏低，根因结论可信度有限"
    """
    rc = data.get("risk_classification", {})
    risk_level = normalize_level(rc.get("risk_level"))
    if risk_level != "高":
        return True, None

    evidence = data.get("evidence", {})
    if not evidence:
        return True, None

    all_items = []
    if isinstance(evidence, dict):
        for key in ("primary_evidence", "supporting_evidence"):
            items = evidence.get(key, [])
            if items and isinstance(items, list):
                all_items.extend(items)
    elif isinstance(evidence, list):
        all_items = evidence

    if not all_items:
        return True, None

    # 检查是否有 A/E 级证据
    has_high_grade = False
    max_grade = "D"
    grade_order = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 5}

    for item in all_items:
        if not isinstance(item, dict):
            continue
        g = item.get("reliability_grade", "").upper() if item.get("reliability_grade") else ""
        if g in grade_order:
            if grade_order[g] > grade_order.get(max_grade, 0):
                max_grade = g
            if g in ("A", "E"):
                has_high_grade = True

    if not has_high_grade:
        return False, f"高风险 finding 无 A/E 级证据支撑（最高证据等级: {max_grade}），根因分析可靠存疑"

    return True, None


def check_decision_rationale(data, risk_level):
    """[L] 决策理由记录——高风险 finding 必须记录关键判断理由

    检查 decision_rationale 字段是否存在且关键子字段已填写。
    高风险 finding 的 risk_level 和 evidence_grade_summary 为必填。
    """
    rationale = data.get("decision_rationale")
    if not rationale:
        if risk_level == "高":
            return False, "高风险 finding 缺少 decision_rationale 字段（必须记录关键判断理由）"
        return True, "无 decision_rationale（非阻断，建议补充）"

    if not isinstance(rationale, dict):
        return False, "decision_rationale 应为对象类型"

    issues = []

    # 高风险必填字段
    if risk_level == "高":
        for field in ("risk_level", "evidence_grade_summary"):
            val = rationale.get(field, "")
            if not val or len(str(val).strip()) < 10:
                issues.append(f"decision_rationale.{field} 过短或缺失（高风险必填）")

    # 所有 finding 建议填写的字段
    for field in ("category", "cause_category", "key_judgment"):
        val = rationale.get(field, "")
        if not val or len(str(val).strip()) < 10:
            issues.append(f"decision_rationale.{field} 过短或缺失")

    if issues:
        has_blocker = any("高风险必填" in i for i in issues)
        if has_blocker:
            return False, "; ".join(issues)
        return True, "; ".join(issues) + "（非阻断，建议补充）"

    return True, None


# ── 主校验 ─────────────────────────────────────────────

def validate_finding(data, exit_on_error=False):
    """对单个 finding 执行全部校验，返回校验报告"""
    rc = data.get("risk_classification", {})
    risk_level = normalize_level(rc.get("risk_level"))
    finding_id = data.get("finding_id", "UNKNOWN")
    finding_title = data.get("finding_title", "")

    checks = {}

    # [S] Schema 合规
    passed, msg = check_schema_compliance(data)
    checks["schema_compliance"] = {"passed": passed, "message": msg}

    # [R] 根因存在性
    passed, rca_msg = check_root_cause_existence(data)
    checks["root_cause_existence"] = {
        "passed": passed,
        "message": "通过" if passed else rca_msg,
        "schema_type": rca_msg if passed else "unknown"
    }

    # [D] 根因深度
    passed, depth_msg = check_root_cause_depth(data, risk_level)
    checks["root_cause_depth"] = {"passed": passed, "message": depth_msg}

    # [C] CCEER 完整性
    passed, cceer_msg = check_cceer_completeness(data)
    checks["cceer_completeness"] = {"passed": passed, "message": cceer_msg}

    # [E] 证据等级
    passed, ev_msg = check_evidence_grade(data)
    checks["evidence_grade"] = {"passed": passed, "message": ev_msg}

    # [I] 直觉引擎
    passed, int_msg = check_intuition_engine(data)
    checks["intuition_engine"] = {"passed": passed, "message": int_msg}

    # [G] 根因与证据等级匹配
    passed, gap_msg = check_cause_evidence_gap(data)
    checks["cause_evidence_gap"] = {"passed": passed, "message": gap_msg}

    # [L] 决策理由记录
    passed, rationale_msg = check_decision_rationale(data, risk_level)
    checks["decision_rationale"] = {"passed": passed, "message": rationale_msg}

    # ── 判定 ──
    blockers = [k for k, v in checks.items() if not v["passed"] and k in (
        "schema_compliance",
        "root_cause_existence",
    )]
    warnings = [k for k, v in checks.items() if not v["passed"] and k not in (
        "schema_compliance",
        "root_cause_existence",
    )]

    if blockers:
        action = "block"
    elif warnings:
        action = "warn"
    else:
        action = "pass"

    report = {
        "finding_id": finding_id,
        "finding_title": finding_title[:60],
        "risk_level": risk_level,
        "action": action,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "passed": sum(1 for v in checks.values() if v["passed"]),
            "blockers": [{"check": k, "message": checks[k]["message"]} for k in blockers],
            "warnings": [{"check": k, "message": checks[k]["message"]} for k in warnings],
        }
    }

    return report


# ── CLI ─────────────────────────────────────────────────

def print_report(report, verbose=False):
    """输出人类可读报告"""
    fid = report["finding_id"]
    title = report["finding_title"]
    risk = report["risk_level"]
    action = report["action"]

    emoji = {"pass": "✅", "warn": "⚠️", "block": "🔴"}
    action_label = {"pass": "全部通过", "warn": "警告（建议审查）", "block": "阻断（必须修正）"}

    print()
    print(f"  {emoji.get(action, '❓')} {fid} [{risk}] {title}")
    print(f"  判定: {action_label.get(action, '未知')}")

    for check_name, check_data in report["checks"].items():
        status = "✅" if check_data["passed"] else "⚠️" if check_name not in ("schema_compliance", "root_cause_existence") else "🔴"
        msg = check_data.get("message") or "通过"
        label = {
            "schema_compliance": "Schema合规",
            "root_cause_existence": "根因存在性",
            "root_cause_depth": "根因深度",
            "cceer_completeness": "CCEER完整性",
            "evidence_grade": "证据等级",
            "intuition_engine": "直觉引擎",
            "cause_evidence_gap": "根因-证据匹配",
            "decision_rationale": "决策理由",
        }.get(check_name, check_name)
        print(f"    {status} [{label}] {msg[:120]}")

    if verbose:
        print(f"  raw -> {json.dumps(report, ensure_ascii=False)[:300]}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Finding 质量硬校验工具")
    parser.add_argument("path", nargs="?", help="单个 finding JSON 文件路径")
    parser.add_argument("--findings-dir", help="批量校验目录下所有 FIND-*.json")
    parser.add_argument("--index", help="从 index.json 读取 finding 列表")
    parser.add_argument("--exit-on-error", action="store_true", help="发现阻断时立即退出")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--verbose", action="store_true", help="详细信息")
    parser.add_argument("--strict", action="store_true", help="严格模式：存在阻断时打印到 stderr 并 exit(1)")

    args = parser.parse_args()

    # ── 收集文件 ──
    files = []

    if args.path:
        if args.path.endswith(".json"):
            files.append(args.path)
        else:
            print(f"[ERROR] 文件必须是 .json: {args.path}")
            sys.exit(2)

    if args.findings_dir:
        dir_path = args.findings_dir
        if not os.path.isdir(dir_path):
            print(f"[ERROR] 目录不存在: {dir_path}")
            sys.exit(2)
        for root, dirs, fnames in os.walk(dir_path):
            for fn in sorted(fnames):
                if fn.startswith("F-") and fn.endswith(".json"):
                    files.append(os.path.join(root, fn))

    if args.index:
        if not os.path.exists(args.index):
            print(f"[ERROR] index.json 不存在: {args.index}")
            sys.exit(2)
        with open(args.index, "r", encoding="utf-8-sig") as f:
            index = json.load(f)
        base_dir = os.path.dirname(args.index)
        for year_data in index.get("by_year", {}).values():
            for fid in year_data.get("ids", []):
                # 查找对应的 json 文件
                for root, dirs, fnames in os.walk(base_dir):
                    for fn in fnames:
                        if fn.startswith(f"{fid}_") and fn.endswith(".json"):
                            files.append(os.path.join(root, fn))

    if not files:
        print("[ERROR] 未指定任何 finding 文件。使用 --path, --findings-dir 或 --index")
        sys.exit(2)

    # ── 执行校验 ──
    results = []
    has_blocker = False

    for fpath in sorted(set(files)):
        try:
            data = load_finding(fpath)
            report = validate_finding(data)
            report["file"] = fpath
            results.append(report)
            if report["action"] == "block":
                has_blocker = True
            if not args.json:
                print_report(report, verbose=args.verbose)
        except json.JSONDecodeError as e:
            print(f"  🔴 [JSON格式错误] {fpath}: {e}")
            if args.exit_on_error:
                sys.exit(2)
        except Exception as e:
            print(f"  🔴 [读取失败] {fpath}: {e}")
            if args.exit_on_error:
                sys.exit(2)

    # ── 汇总 ──
    if not args.json:
        passed = sum(1 for r in results if r["action"] == "pass")
        warned = sum(1 for r in results if r["action"] == "warn")
        blocked = sum(1 for r in results if r["action"] == "block")
        print(f"\n{'='*60}")
        print(f"  共计 {len(results)} 个 finding: ✅ {passed}  ⚠️  {warned}  🔴 {blocked}")
        print(f"{'='*60}\n")

        if has_blocker and args.exit_on_error:
            sys.exit(2)

    else:
        print(json.dumps({
            "findings": results,
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r["action"] == "pass"),
                "warned": sum(1 for r in results if r["action"] == "warn"),
                "blocked": sum(1 for r in results if r["action"] == "block"),
            }
        }, ensure_ascii=False, indent=2))

    if args.strict and has_blocker:
        for r in results:
            if r["action"] == "block":
                print(f"[BLOCK] {r['finding_id']}: {', '.join(b['message'] for b in r['summary']['blockers'])}", file=sys.stderr)
        sys.exit(1)

    sys.exit(2 if has_blocker else 1 if any(r["action"] == "warn" for r in results) else 0)


if __name__ == "__main__":
    main()
