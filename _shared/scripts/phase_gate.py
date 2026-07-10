#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phase_gate.py - phase state machine (turnstile model) + tool authorization gate

Deterministic phase transition checks and per-phase tool whitelist for audit projects.
Called by constitution.md phase management rules.

INPUT:  current-audit.json (status field) + workspace directory contents
OUTPUT: JSON phase status/transition/tool-check result + exit code (0=pass, 1=block, 2=error/prompt_update)
POS:    _shared/scripts phase management + tool authorization tool, referenced by constitution.md

Usage:
    python phase_gate.py status       # show current phase and exit conditions
    python phase_gate.py check        # check if advance is possible
    python phase_gate.py advance      # execute phase transition
    python phase_gate.py rollback --to phase_1_document_analysis --reason "补充制度分析"
    python phase_gate.py tool-check validate-finding.py           # check tool phase permission
    python phase_gate.py tool-check validate-finding.py --force   # override with audit_trail record
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

PHASES = [
    "phase_0_init",
    "phase_1_document_analysis",
    "phase_1_5_interview",
    "phase_2_program_generation",
    "phase_3_execution",
    "phase_4_report",
]

# ── Tool whitelist per phase ──────────────────────────────
# Each phase has ONE exclusive validate script + optional aux scripts.
# Globals (GLOBAL_TOOLS) and evaluators (EVALUATOR_TOOLS) are resolved at check time.

PHASE_TOOLS = {
    "phase_0_init":                    {"project_init.py"},
    "phase_1_document_analysis":       {"validate-policy-analysis.py", "pdf_ocr_extractor.py"},
    "phase_1_5_interview":            {"validate-interview.py"},
    "phase_2_program_generation":      {"validate-program.py"},
    "phase_3_execution":               {"validate-finding.py"},
    "phase_4_report":                  {"validate-report.py"},
}

GLOBAL_TOOLS = {
    "phase_gate.py",
    "queries.py",
    "validate-json.py",
    "audit_styles.py",
    "excel_core.py",
}

# Evaluator scripts — allowed from Phase 1 onward (no init-phase eval)
EVALUATOR_TOOLS = {
    "record_evaluation.py",
    "quality_gate.py",
}


def resolve_skills_dir(args) -> Path:
    """Resolve skills directory: CLI arg > env var > workspace.parent.parent inference."""
    if args is not None and getattr(args, "skills_dir", None):
        return Path(args.skills_dir)
    env_val = os.environ.get("INTERNAL_AUDIT_SKILLS_DIR")
    if env_val:
        return Path(env_val)
    ws = find_workspace()
    inferred = ws.parent.parent
    return inferred


def find_workspace() -> Path:
    """Find internal-audit-workspace/ from CWD upwards"""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        ws = parent / "internal-audit-workspace"
        if ws.exists():
            return ws
    return cwd / "internal-audit-workspace"


def load_audit() -> dict:
    """Load current-audit.json"""
    ws = find_workspace()
    audit_path = ws / "current-audit.json"
    if not audit_path.exists():
        print(json.dumps({"action": "error", "reason": f"找不到 {audit_path}"}, ensure_ascii=False))
        sys.exit(2)
    with open(audit_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_audit(data: dict, ws: Path):
    """Write back current-audit.json"""
    audit_path = ws / "current-audit.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def check_exit_conditions(ws: Path, current_phase: str, data: dict, args=None) -> list:
    """Check exit conditions for current phase. Returns list of issue dicts."""
    issues = []

    if current_phase == "phase_1_document_analysis":
        analyses = list((ws / "policy-analyses").glob("*.json")) if (ws / "policy-analyses").exists() else []
        if len(analyses) == 0:
            issues.append({"type": "block", "msg": "policy-analyses/ 无 JSON (需 >=1 份制度分析)"})
        if not data.get("audit_topic"):
            issues.append({"type": "block", "msg": "audit_topic 未设置"})

    elif current_phase == "phase_1_5_interview":
        state = data.get("audit_state", {})
        known = state.get("known_facts", {})
        audit_purpose = (
            state.get("audit_purpose")
            or known.get("audit_purpose")
            or data.get("audit_purpose")
        )
        if not audit_purpose:
            issues.append({"type": "block", "msg": "审计目的未选择。请返回 program-generator Step 1 完成目的选择。"})

        skills_dir = resolve_skills_dir(args)
        about_me = skills_dir / "audit-topics" / "about-me.md"
        if not about_me.exists():
            issues.append({"type": "block", "msg": "about-me.md 不存在。请先完成公司背景配置。"})

    elif current_phase == "phase_2_program_generation":
        progs = list((ws / "audit-programs").glob("*")) if (ws / "audit-programs").exists() else []
        if len(progs) == 0:
            issues.append({"type": "block", "msg": "audit-programs/ 无文件 (需 >=1 份审计程序)"})
        state = data.get("audit_state", {})
        known = state.get("known_facts", {})
        audit_purpose = (
            state.get("audit_purpose")
            or known.get("audit_purpose")
            or data.get("audit_purpose")
        )
        if not audit_purpose:
            if len(progs) > 0:
                issues.append({"type": "prompt_update", "msg": "audit_purpose 未设置"})
            else:
                issues.append({"type": "block", "msg": "audit_purpose 未设置"})

        if not data.get("audit_state", {}).get("design_observations_consumed", True):
            design_dir = ws / "design-assessments"
            if design_dir.exists():
                for f in design_dir.glob("*_设计观察.json"):
                    try:
                        content = json.loads(f.read_text(encoding="utf-8"))
                        clues = [obs for obs in content.get("design_observations", [])
                                 if obs.get("type") == "risk_clue" and obs.get("status") == "pending"]
                        if clues:
                            issues.append({"type": "prompt_update", "msg": f"{len(clues)}条访谈线索尚未纳入审计程序", "suggested_skill": "internal-audit-program-generator", "trigger": "interview"})
                    except Exception:
                        pass

        if data.get("audit_state", {}).get("whistleblower_pending"):
            issues.append({"type": "prompt_update", "msg": "举报材料尚未纳入审计程序", "suggested_skill": "internal-audit-program-generator", "trigger": "whistleblower"})

    elif current_phase == "phase_3_execution":
        if not data.get("audit_state", {}).get("report_type"):
            issues.append({"type": "block", "msg": "报告类型未选择。请返回 report-generator 选择报告类型（标准/专项/舞弊/跟踪）。"})
        findings_dir = ws / "findings"
        findings = [f for f in findings_dir.glob("F-*.json")] if findings_dir.exists() else []
        if len(findings) == 0:
            issues.append({"type": "block", "msg": "findings/ 无 F-*.json (需 >=1 个审计发现)"})

    elif current_phase == "phase_4_report":
        reports_dir = ws / "reports"
        reports = list(reports_dir.glob("*")) if reports_dir.exists() else []
        if len(reports) == 0:
            issues.append({"type": "block", "msg": "reports/ 无报告 (需 >=1 份审计报告)"})

    return issues


def check_tool_allowed(tool_name: str, phase: str) -> dict:
    """Check if a tool script is allowed in the given phase.

    Returns: {"allowed": bool, "reason": str (if blocked), "available": [...] }
    """
    # Strip path — only match basename
    base = os.path.basename(tool_name)

    # 1. Global tools — always allowed
    if base in GLOBAL_TOOLS:
        return {"allowed": True, "tool": base, "phase": phase}

    # 2. Phase-specific tools
    phase_set = PHASE_TOOLS.get(phase, set())

    # 3. Evaluator tools — Phase 1+ only
    if base in EVALUATOR_TOOLS:
        idx = PHASES.index(phase) if phase in PHASES else -1
        if idx >= 1:  # phase_1_document_analysis or later
            return {"allowed": True, "tool": base, "phase": phase}
        else:
            available = sorted(phase_set | GLOBAL_TOOLS)
            return {
                "allowed": False,
                "tool": base,
                "phase": phase,
                "reason": f"{base} 在 {phase} 不可用（评估工具从 Phase 1 开始可用）",
                "available": available,
            }

    # 4. Unknown tool — not in any whitelist
    all_known = set()
    for s in PHASE_TOOLS.values():
        all_known |= s
    all_known |= GLOBAL_TOOLS | EVALUATOR_TOOLS

    if base not in all_known:
        return {
            "allowed": False,
            "tool": base,
            "phase": phase,
            "reason": f"{base} 不在已知工具白名单中",
            "available": sorted(phase_set | GLOBAL_TOOLS),
        }

    # 5. Known tool but wrong phase
    if base in phase_set:
        return {"allowed": True, "tool": base, "phase": phase}

    available = sorted(phase_set | GLOBAL_TOOLS)
    return {
        "allowed": False,
        "tool": base,
        "phase": phase,
        "reason": f"{base} 在 {phase} 不可用",
        "available": available,
    }


def snapshot_audit_state(data: dict, ws: Path):
    """Save audit_state snapshot (keep last 20)"""
    snapshots_dir = ws / "snapshots"
    snapshots_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    phase = data.get("status", "unknown")
    snap_file = snapshots_dir / f"snap_{ts}_{phase}.json"
    with open(snap_file, "w", encoding="utf-8") as f:
        json.dump(data.get("audit_state", {}), f, ensure_ascii=False, indent=2)
    snaps = sorted(snapshots_dir.glob("snap_*.json"))
    for old in snaps[:-20]:
        old.unlink()
    return str(snap_file)


def append_audit_trail(data: dict, event_type: str, detail: str):
    """Append event to audit_trail"""
    state = data.setdefault("audit_state", {})
    trail = state.setdefault("audit_trail", [])
    trail.append({
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "detail": detail,
    })


# ── CLI commands ──────────────────────────────────────────


def cmd_tool_check(args):
    """Check whether a tool script is allowed in the current phase."""
    tool_name = args.tool_name
    ws = find_workspace()

    # Resolve phase: explicit arg > current-audit.json > fallback to phase_0_init
    if args.phase:
        phase = args.phase
    else:
        try:
            data = load_audit()
            phase = data.get("status", "phase_0_init")
        except SystemExit:
            # workspace doesn't exist yet — assume init phase
            phase = "phase_0_init"

    if phase not in PHASES:
        print(json.dumps({"action": "error", "reason": f"未知阶段: {phase}"}, ensure_ascii=False))
        sys.exit(2)

    result = check_tool_allowed(tool_name, phase)

    if result["allowed"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    # Not allowed — force overrides
    if getattr(args, "force", False):
        try:
            data = load_audit()
            snap_path = snapshot_audit_state(data, ws)
            append_audit_trail(data, "tool_force_override",
                               f"强制调用 {tool_name}（当前阶段 {phase} 不允许）")
            save_audit(data, ws)
            result["snapshot"] = snap_path
        except SystemExit:
            pass  # no workspace to snapshot — ok
        result["allowed"] = True
        result["forced"] = True
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1)


def cmd_status(args):
    """Show current phase status"""
    ws = find_workspace()
    data = load_audit()
    current = data.get("status", "unknown")
    idx = PHASES.index(current) if current in PHASES else -1

    result = {
        "current_phase": current,
        "phase_index": idx,
        "total_phases": len(PHASES),
    }

    if idx >= 0 and idx < len(PHASES) - 1:
        next_phase = PHASES[idx + 1]
        issues = check_exit_conditions(ws, current, data)
        blocks = [i for i in issues if i["type"] == "block"]
        result["next_phase"] = next_phase
        result["exit_ready"] = len(blocks) == 0
        result["exit_missing"] = [i["msg"] for i in issues]
    elif idx == len(PHASES) - 1:
        result["next_phase"] = None
        result["exit_ready"] = True
        result["exit_missing"] = []
    else:
        result["exit_ready"] = False
        result["exit_missing"] = [f"未知阶段: {current}"]

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["exit_ready"] else 1)


def cmd_check(args):
    """Check if advance to next phase is possible"""
    ws = find_workspace()
    data = load_audit()
    current = data.get("status", "unknown")

    if current not in PHASES:
        print(json.dumps({"action": "block", "reason": f"未知阶段: {current}"}, ensure_ascii=False))
        sys.exit(2)

    idx = PHASES.index(current)
    if idx >= len(PHASES) - 1:
        print(json.dumps({"action": "pass", "reason": "已是最终阶段", "phase": current}, ensure_ascii=False))
        sys.exit(0)

    issues = check_exit_conditions(ws, current, data, args)
    next_phase = PHASES[idx + 1]

    if any(i["type"] == "block" for i in issues):
        action = "block"
    elif any(i["type"] == "prompt_update" for i in issues):
        action = "prompt_program_update"
    else:
        action = "pass"

    if action == "pass":
        print(json.dumps({
            "action": "pass",
            "reason": f"可从 {current} 切换到 {next_phase}",
            "current": current,
            "next": next_phase,
        }, ensure_ascii=False, indent=2))
        sys.exit(0)
    elif action == "prompt_program_update":
        if getattr(args, "force", False):
            print(json.dumps({
                "action": "pass",
                "reason": f"--force 已指定, 强制通过 {current} -> {next_phase}",
                "current": current,
                "next": next_phase,
                "forced": True,
            }, ensure_ascii=False, indent=2))
            sys.exit(0)
        print(json.dumps({
            "action": "prompt_program_update",
            "reason": "存在未完成的提示更新, 建议处理后再前进",
            "current": current,
            "next": next_phase,
            "issues": issues,
        }, ensure_ascii=False, indent=2))
        sys.exit(2)
    else:
        print(json.dumps({
            "action": "block",
            "reason": f"退出条件未满足, 无法从 {current} 切换到 {next_phase}",
            "issues": issues,
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


def cmd_advance(args):
    """Execute phase transition (forward)"""
    ws = find_workspace()
    data = load_audit()
    current = data.get("status", "unknown")

    if current not in PHASES:
        print(json.dumps({"action": "error", "reason": f"未知阶段: {current}"}, ensure_ascii=False))
        sys.exit(2)

    idx = PHASES.index(current)
    if idx >= len(PHASES) - 1:
        print(json.dumps({"action": "pass", "reason": "已是最终阶段"}, ensure_ascii=False))
        sys.exit(0)

    issues = check_exit_conditions(ws, current, data, args)
    next_phase = PHASES[idx + 1]

    if any(i["type"] == "block" for i in issues):
        action = "block"
    elif any(i["type"] == "prompt_update" for i in issues):
        action = "prompt_program_update"
    else:
        action = "pass"

    if action == "block":
        print(json.dumps({
            "action": "block",
            "reason": "退出条件未满足, 无法前进",
            "issues": [i for i in issues if i["type"] == "block"],
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    elif action == "prompt_program_update":
        if getattr(args, "force", False):
            print(json.dumps({
                "action": "pass",
                "reason": f"--force 已指定, 强制前进 {current} -> {next_phase}",
                "current": current,
                "next": next_phase,
                "forced": True,
                "warnings": [i for i in issues if i["type"] == "prompt_update"],
            }, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({
                "action": "prompt_program_update",
                "reason": "存在未完成的提示更新, 建议处理后再前进",
                "current": current,
                "next": next_phase,
                "issues": issues,
            }, ensure_ascii=False, indent=2))
            sys.exit(2)

    snap_path = snapshot_audit_state(data, ws)
    data["status"] = next_phase
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    append_audit_trail(data, "phase_advance", f"{current} -> {next_phase}")
    save_audit(data, ws)

    print(json.dumps({
        "action": "advanced",
        "from": current,
        "to": next_phase,
        "snapshot": snap_path,
        "updated_at": data["updated_at"],
    }, ensure_ascii=False, indent=2))
    sys.exit(0)


def cmd_rollback(args):
    """Rollback to specified phase"""
    ws = find_workspace()
    data = load_audit()

    if not args.to:
        print(json.dumps({"action": "error", "reason": "必须指定 --to 参数"}, ensure_ascii=False))
        sys.exit(2)

    if args.to not in PHASES:
        print(json.dumps({"action": "error", "reason": f"无效阶段: {args.to}"}, ensure_ascii=False))
        sys.exit(2)

    current = data.get("status", "unknown")
    target_idx = PHASES.index(args.to)
    current_idx = PHASES.index(current) if current in PHASES else -1

    if target_idx >= current_idx:
        print(json.dumps({"action": "error", "reason": f"回退目标 {args.to} 不在当前阶段 {current} 之前"}, ensure_ascii=False))
        sys.exit(2)

    if not args.reason:
        print(json.dumps({"action": "error", "reason": "回退必须提供 --reason 说明原因"}, ensure_ascii=False))
        sys.exit(2)

    snap_path = snapshot_audit_state(data, ws)
    data["status"] = args.to
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    append_audit_trail(data, "phase_rollback", f"{current} -> {args.to}, 原因: {args.reason}")
    save_audit(data, ws)

    print(json.dumps({
        "action": "rolled_back",
        "from": current,
        "to": args.to,
        "reason": args.reason,
        "snapshot": snap_path,
    }, ensure_ascii=False, indent=2))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="阶段状态机 (地铁闸机模型)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="显示当前阶段和退出条件")

    p_check = sub.add_parser("check", help="检查能否进入下一阶段")
    p_check.add_argument("--skills-dir", default=None, help="技能目录路径 (默认: env INTERNAL_AUDIT_SKILLS_DIR 或 workspace.parent.parent)")
    p_check.add_argument("--force", action="store_true", help="强制通过 prompt_program_update 提示")

    p_advance = sub.add_parser("advance", help="执行阶段切换")
    p_advance.add_argument("--skills-dir", default=None, help="技能目录路径 (默认: env INTERNAL_AUDIT_SKILLS_DIR 或 workspace.parent.parent)")
    p_advance.add_argument("--force", action="store_true", help="强制通过 prompt_program_update 提示")

    rb = sub.add_parser("rollback", help="回退到指定阶段")
    rb.add_argument("--to", required=True, choices=PHASES, help="目标阶段")
    rb.add_argument("--reason", required=True, help="回退原因")

    p_tc = sub.add_parser("tool-check", help="检查工具在当前阶段是否可用")
    p_tc.add_argument("tool_name", help="脚本名称 (如 validate-finding.py)")
    p_tc.add_argument("--phase", default=None, choices=PHASES, help="强制指定阶段 (默认: 从 current-audit.json 读取)")
    p_tc.add_argument("--force", action="store_true", help="强制放行并记录 audit_trail")

    args = parser.parse_args()
    cmds = {"status": cmd_status, "check": cmd_check, "advance": cmd_advance,
            "rollback": cmd_rollback, "tool-check": cmd_tool_check}
    if args.command in cmds:
        cmds[args.command](args)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
