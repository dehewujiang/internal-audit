#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
decisions_schema.py — 决策追溯数据结构定义

纯数据结构，无业务逻辑。供各 Skill 在生成输出时引用，
供 validate 脚本校验 decision_log 字段，供 queries.py decide 查询。

[INPUT]:  无外部依赖
[OUTPUT]: DECISION_POINTS 枚举 + DECISION_LOG_TEMPLATE 模板 + validate_decision_log() 校验函数
[POS]:    _shared/scripts 的共享数据结构，被 validate-* 和 queries.py 引用
"""

# ── 9 个决策点枚举 ──────────────────────────────────────
# 按审计决策链顺序排列（审计目的 → 报告结论）

DECISION_POINTS = {
    "D-001": {
        "id": "policy_focus",
        "label": "制度关注重点",
        "phase": "phase_1_document_analysis",
        "question": "为什么重点看这些控制点而不是其他？",
        "produced_by": "document-organizer",
    },
    "D-002": {
        "id": "design_observation_escalation",
        "label": "设计观察升级判断",
        "phase": "phase_1_document_analysis",
        "question": "为什么这些纸面问题需要去现场验证？",
        "produced_by": "document-organizer",
    },
    "D-003": {
        "id": "audit_purpose",
        "label": "审计目的选择",
        "phase": "phase_2_program_generation",
        "question": "为什么是舞弊调查而不是内控评估？",
        "produced_by": "internal-audit-program-generator",
    },
    "D-004": {
        "id": "audit_scope",
        "label": "审计范围定义",
        "phase": "phase_2_program_generation",
        "question": "为什么只看废料处置不看采购入库？",
        "produced_by": "internal-audit-program-generator",
    },
    "D-005": {
        "id": "track_activation",
        "label": "程序轨道激活",
        "phase": "phase_2_program_generation",
        "question": "为什么激活轨道 B+E 而不是 A+F？",
        "produced_by": "internal-audit-program-generator",
    },
    "D-006": {
        "id": "evidence_sufficiency",
        "label": "证据充分性判断",
        "phase": "phase_3_execution",
        "question": "这些证据为什么足够支撑这个结论？",
        "produced_by": "audit-execution-assistant",
    },
    "D-007": {
        "id": "risk_classification",
        "label": "风险定级",
        "phase": "phase_3_execution",
        "question": "为什么定高/中/低而不是其他级别？",
        "produced_by": "audit-execution-assistant",
    },
    "D-008": {
        "id": "finding_inclusion",
        "label": "纳入报告判断",
        "phase": "phase_4_report",
        "question": "这个 finding 为什么写进（或不写进）正式报告？",
        "produced_by": "internal-audit-report-generator",
    },
    "D-009": {
        "id": "report_conclusion",
        "label": "报告结论",
        "phase": "phase_4_report",
        "question": "为什么出保留意见/无保留意见/否定意见？",
        "produced_by": "internal-audit-report-generator",
    },
}

# ── 决策记录模板 ─────────────────────────────────────────

DECISION_LOG_TEMPLATE = {
    "decision_id": "",           # D-YYYY-NNN（与 DECISION_POINTS key 对应）
    "decision_point": "",        # decision_points 中的 id 值（如 "audit_purpose"）
    "phase": "",                 # 所属阶段
    "decision": "",              # 决策结果（如 "fraud_investigation"）
    "rationale": "",             # 判断理由（核心字段，≥30 字）
    "alternatives_considered": [ # 考虑过但未选的替代方案
        # {"option": "内控评估", "rejected_reason": "举报线索指向舞弊而非控制失效"}
    ],
    "context_refs": [],          # 依赖的证据/数据（文件路径）
    "parent_decisions": [],      # 上游决策 ID（如 ["D-003"]）
    "reversible": True,          # 新证据出现时能否推翻
    "timestamp": "",             # ISO 8601
}

# ── 必填字段（按风险分级）─────────────────────────────────

# 高风险决策点：无论 finding 风险等级，都必须填写完整的 rationale
HIGH_STAKES_POINTS = {"D-003", "D-007", "D-009"}

# 中风险决策点：rationale ≥ 20 字
MEDIUM_STAKES_POINTS = {"D-002", "D-004", "D-005", "D-006", "D-008"}

# 低风险决策点：rationale 非空即可
LOW_STAKES_POINTS = {"D-001"}


# ── 校验函数 ─────────────────────────────────────────────

def validate_decision_log(decision_log: list, phase: str = None) -> dict:
    """校验 decision_log 数组的完整性和深度。

    Args:
        decision_log: 决策记录列表
        phase: 可选，只校验该阶段的决策点

    Returns:
        {"passed": bool, "issues": [str], "warnings": [str]}
    """
    issues = []
    warnings = []

    if not decision_log:
        return {"passed": False, "issues": ["decision_log 数组为空"], "warnings": []}

    if not isinstance(decision_log, list):
        return {"passed": False, "issues": ["decision_log 应为数组类型"], "warnings": []}

    # 按 phase 筛选要检查的决策点
    expected_points = {}
    for key, dp in DECISION_POINTS.items():
        if phase and dp["phase"] != phase:
            continue
        expected_points[key] = dp

    # 检查覆盖
    found_ids = set()
    for entry in decision_log:
        if not isinstance(entry, dict):
            issues.append("decision_log 中有非对象元素")
            continue

        did = entry.get("decision_id", "")
        if not did:
            issues.append("decision_log 中有条目缺少 decision_id")
            continue

        found_ids.add(did)

        # 检查核心字段
        rationale = entry.get("rationale", "")
        if not rationale:
            if did in HIGH_STAKES_POINTS:
                issues.append(f"{did}: rationale 为空（高风险决策点必填）")
            elif did in MEDIUM_STAKES_POINTS:
                issues.append(f"{did}: rationale 为空（中风险决策点必填）")
            else:
                warnings.append(f"{did}: rationale 为空（建议填写）")
        else:
            # 检查理由深度
            rlen = len(rationale.strip())
            if did in HIGH_STAKES_POINTS and rlen < 30:
                issues.append(f"{did}: rationale 过短（{rlen}字），高风险决策点需 ≥30 字")
            elif did in MEDIUM_STAKES_POINTS and rlen < 20:
                warnings.append(f"{did}: rationale 偏短（{rlen}字），建议 ≥20 字")
            elif rlen < 10:
                warnings.append(f"{did}: rationale 过短（{rlen}字）")

        # 检查 decision 字段
        if not entry.get("decision"):
            warnings.append(f"{did}: decision 字段为空（建议填写决策结果）")

        # 检查 context_refs — 高风险决策点建议有引用
        if did in HIGH_STAKES_POINTS:
            refs = entry.get("context_refs", [])
            if not refs:
                warnings.append(f"{did}: context_refs 为空（高风险决策点建议注明证据依据）")

        # 检查 timestamp
        if not entry.get("timestamp"):
            warnings.append(f"{did}: timestamp 为空")

    # 检查是否遗漏了本阶段该有的决策点
    if phase:
        missing = set(expected_points.keys()) - found_ids
        for m in sorted(missing):
            dp = expected_points[m]
            if m in HIGH_STAKES_POINTS:
                issues.append(f"缺少高风险决策点 {m}（{dp['label']}）")
            elif m in MEDIUM_STAKES_POINTS:
                issues.append(f"缺少中风险决策点 {m}（{dp['label']}）")
            else:
                warnings.append(f"缺少决策点 {m}（{dp['label']}）")

    # 判定
    if any("高风险" in i or "缺少高风险" in i for i in issues):
        passed = False
    else:
        # 有 issue 但不是高风险 → 看 severity
        passed = len([i for i in issues if "高风险" not in i]) == 0

    return {
        "passed": passed,
        "issues": issues,
        "warnings": warnings,
        "covered": sorted(found_ids),
        "expected": sorted(expected_points.keys()),
    }


# ── CLI 入口（供独立验证用）─────────────────────────────────

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("用法: python decisions_schema.py <decision_log.json> [--phase phase_3_execution]")
        print("      校验 decision_log JSON 文件的完整性和深度")
        print()
        print("可用的决策点:")
        for key, dp in DECISION_POINTS.items():
            print(f"  {key}  {dp['label']}（{dp['phase']}）— {dp['produced_by']}")
        sys.exit(0)

    path = sys.argv[1]
    phase_filter = None
    if "--phase" in sys.argv:
        idx = sys.argv.index("--phase")
        phase_filter = sys.argv[idx + 1]

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        print(json.dumps({"passed": False, "issues": [f"文件读取失败: {e}"], "warnings": []},
                         ensure_ascii=False, indent=2))
        sys.exit(1)

    # 支持两种输入：直接是数组，或者是包含 decision_log 字段的对象
    if isinstance(data, list):
        decision_log = data
    elif isinstance(data, dict):
        decision_log = data.get("decision_log", [])
    else:
        print(json.dumps({"passed": False, "issues": ["输入应为 JSON 数组或包含 decision_log 字段的对象"],
                          "warnings": []}, ensure_ascii=False, indent=2))
        sys.exit(1)

    result = validate_decision_log(decision_log, phase=phase_filter)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["passed"] else 1)
