#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phase_gate.py - phase state machine (turnstile model)

Deterministic phase transition checks for audit projects.
Called by constitution.md phase management rules.

INPUT:  current-audit.json (status field) + workspace directory contents
OUTPUT: JSON phase status/transition result + exit code (0=pass, 1=block, 2=error)
POS:    _shared/scripts phase management tool, referenced by constitution.md

Usage:
    python phase_gate.py status       # show current phase and exit conditions
    python phase_gate.py check        # check if advance is possible
    python phase_gate.py advance      # execute phase transition
    python phase_gate.py rollback --to phase_1_document_analysis --reason "补充制度分析"
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


def check_exit_conditions(ws: Path, current_phase: str, data: dict) -> dict:
    """Check exit conditions for current phase. Returns {ready: bool, missing: []}"""
    missing = []

    if current_phase == "phase_1_document_analysis":
        analyses = list((ws / "policy-analyses").glob("*.json")) if (ws / "policy-analyses").exists() else []
        if len(analyses) == 0:
            missing.append("policy-analyses/ 无 JSON (需 >=1 份制度分析)")
        if not data.get("audit_topic"):
            missing.append("audit_topic 未设置")

    elif current_phase == "phase_1_5_interview":
        pass  # human decision point, no auto condition

    elif current_phase == "phase_2_program_generation":
        progs = list((ws / "audit-programs").glob("*")) if (ws / "audit-programs").exists() else []
        if len(progs) == 0:
            missing.append("audit-programs/ 无文件 (需 >=1 份审计程序)")
        state = data.get("audit_state", {})
        known = state.get("known_facts", {})
        if not known.get("audit_purpose") and not data.get("audit_purpose"):
            missing.append("audit_purpose 未设置")

    elif current_phase == "phase_3_execution":
        findings_dir = ws / "findings"
        findings = [f for f in findings_dir.glob("F-*.json")] if findings_dir.exists() else []
        if len(findings) == 0:
            missing.append("findings/ 无 F-*.json (需 >=1 个审计发现)")

    elif current_phase == "phase_4_report":
        reports_dir = ws / "reports"
        reports = list(reports_dir.glob("*")) if reports_dir.exists() else []
        if len(reports) == 0:
            missing.append("reports/ 无报告 (需 >=1 份审计报告)")

    return {"ready": len(missing) == 0, "missing": missing}


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
        gate = check_exit_conditions(ws, current, data)
        result["next_phase"] = next_phase
        result["exit_ready"] = gate["ready"]
        result["exit_missing"] = gate["missing"]
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

    gate = check_exit_conditions(ws, current, data)
    next_phase = PHASES[idx + 1]

    if gate["ready"]:
        print(json.dumps({
            "action": "pass",
            "reason": f"可从 {current} 切换到 {next_phase}",
            "current": current,
            "next": next_phase,
        }, ensure_ascii=False, indent=2))
        sys.exit(0)
    else:
        print(json.dumps({
            "action": "block",
            "reason": f"退出条件未满足, 无法从 {current} 切换到 {next_phase}",
            "missing": gate["missing"],
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

    gate = check_exit_conditions(ws, current, data)
    next_phase = PHASES[idx + 1]

    if not gate["ready"]:
        print(json.dumps({
            "action": "block",
            "reason": "退出条件未满足, 无法前进",
            "missing": gate["missing"],
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

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
    sub.add_parser("check", help="检查能否进入下一阶段")
    sub.add_parser("advance", help="执行阶段切换")

    rb = sub.add_parser("rollback", help="回退到指定阶段")
    rb.add_argument("--to", required=True, choices=PHASES, help="目标阶段")
    rb.add_argument("--reason", required=True, help="回退原因")

    args = parser.parse_args()
    cmds = {"status": cmd_status, "check": cmd_check, "advance": cmd_advance, "rollback": cmd_rollback}
    if args.command in cmds:
        cmds[args.command](args)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
