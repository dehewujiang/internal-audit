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
    python phase_gate.py rollback     # 已取消：只拒收并指引插任务往前走
    python phase_gate.py tool-check validate-finding.py           # check tool phase permission
    python phase_gate.py tool-check validate-finding.py --force   # override with audit_trail record
    python phase_gate.py checklist --workspace D:\某个审计项目  # 打勾纸：六句话看板，只看不拦（新桌子）
    python phase_gate.py log-decision --scene 风险定级 --decision 高 --basis "回款超账期且无对账"
    python phase_gate.py log-program-change --type added --id X-001 --reason "发现新风险"
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

# ── next 命令：本阶段能干什么（人话看板，只报不拦） ──
PHASE_CN = {
    "phase_0_init": ("定主题", [
        "告诉 AI 你要审计什么主题（主题向导帮你登记）",
        "建工作区：python _shared/scripts/project_init.py",
    ]),
    "phase_1_document_analysis": ("看制度", [
        "把制度文件（Word/PDF/扫描件）放进 documents/ 文件夹",
        "跑制度分析（document-organizer），输出控制点+风险点",
        "查制度完整性：python _shared/scripts/check_mandatory_coverage.py --topic <主题>",
    ]),
    "phase_1_5_interview": ("问话", [
        "告诉 AI 你想访谈谁（岗位+姓名）",
        "拿访谈提纲去问，把记录拿回来回填",
        "有新线索时说“更新审计程序”（增量补充，不推翻）",
    ]),
    "phase_2_program_generation": ("列检查单", [
        "生成审计程序（program-generator，一次给全 6 轨道）",
        "红队攻击在 Step 4.6 自动跑，不用你动手",
        "自检：python _shared/scripts/validate-program.py <程序文件>",
    ]),
    "phase_3_execution": ("现场取证", [
        "按审计程序去现场收集证据",
        "先贴证据再上桌：add-evidence --grade 照实标（A-E）→ add-line 上桌",
        "自查门卫：python ledger/check.py <桌子.json> --workspace <项目根>",
    ]),
    "phase_4_report": ("写报告", [
        "先选报告类型（标准/专项/舞弊/跟踪）",
        "汇总 finding 生成报告（report-generator）",
        "报告前过桌子闸机：python ledger/audit_table.py --table <桌子.json>",
    ]),
}


def _policy_rows(ws: Path) -> int:
    """桌上看制度的行数（C1·S3 门限）。读不出 → 0（看板不崩）。"""
    ddir = ws / "audit-table"
    if not ddir.exists():
        return 0
    n = 0
    for p in sorted(ddir.glob("*.json")):
        try:
            t = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        for x in t.get("left", []):
            text = str(x.get("text") or "")
            src = x.get("source") or {}
            if "[CG-" in text or src.get("room") == "看制度":
                n += 1
    return n


def _table_rows(ws: Path) -> int:
    """桌上 left[] 事实行数。读不出 → 0（看板不崩）。"""
    ddir = ws / "audit-table"
    if not ddir.exists():
        return 0
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from query_data_sources import load_table_findings as _ltf
        return len(_ltf(ws))
    except Exception:
        return 0


def _count_files(ws: Path, *parts: str, pattern: str = "*") -> int:
    d = ws.joinpath(*parts)
    if not d.exists():
        return 0
    try:
        return sum(1 for p in d.glob(pattern) if p.is_file())
    except Exception:
        return 0


def _evidence_progress(ws: Path) -> tuple:
    """证据柜（已收槽，总槽）。读不出 → (0, 0)。"""
    p = ws / "evidence" / "_evidence_catalog.json"
    try:
        items = json.loads(p.read_text(encoding="utf-8-sig")).get("items", [])
    except Exception:
        return 0, 0
    return sum(1 for it in items if isinstance(it, dict) and it.get("file")), len(items)


def cmd_next(args) -> None:
    """下一步：现在能干什么、还缺什么、能用什么工具。人话看板，只报不拦，永远 exit 0。"""
    ws = find_workspace()
    audit_path = ws / "current-audit.json"
    if not audit_path.exists():
        print("还没建账：在项目文件夹里说“开始新审计项目”，先定主题。")
        print("能用工具：project_init.py")
        sys.exit(0)
    try:
        data = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    except Exception:
        print(f"账本读不出来（{audit_path}），先修好它再看下一步。")
        sys.exit(0)
    current = data.get("status", "unknown")

    if current not in PHASES:
        print(f"你在：未知阶段（{current}）")
        print("能干：看看 current-audit.json 的 status 是不是写错了，对着六阶段改：")
        print("  初始化 → 看制度 → 问话 → 列检查单 → 现场取证 → 写报告")
        sys.exit(0)

    idx = PHASES.index(current)
    cname, actions = PHASE_CN[current]

    n_policy = _count_files(ws, "policy-analyses", pattern="*.json")
    n_prog = _count_files(ws, "audit-programs")
    n_report = _count_files(ws, "reports")
    rows = _table_rows(ws)
    ev_got, ev_all = _evidence_progress(ws)

    done = []
    n_table_policy = _policy_rows(ws)
    if n_table_policy:
        done.append(f"制度分析桌上 {n_table_policy} 行")
    elif n_policy:
        done.append(f"制度分析 {n_policy} 份（旧 JSON，未上桌）")
    if n_prog:
        done.append(f"审计程序 {n_prog} 份")
    if rows:
        done.append(f"桌上有 {rows} 行")
    if ev_all:
        done.append(f"证据柜 {ev_all} 槽已收 {ev_got}")
    if n_report:
        done.append(f"报告 {n_report} 份")

    print(f"你在：{cname}（第 {idx + 1} 步，共 {len(PHASES)} 步）")
    print(f"已干完：{' / '.join(done) if done else '刚起步，先干第一件事'}")
    print("现在能干：")
    for i, a in enumerate(actions, 1):
        print(f"  {i}）{a}")
    try:
        issues = check_exit_conditions(ws, current, data, args)
    except Exception:
        issues = []
    if issues:
        print("还缺什么：")
        for i in issues:
            print(f"  · {i.get('msg', i)}")
    else:
        print("还缺什么：不缺，直跑 check，能进跑 advance")
    tools = sorted(PHASE_TOOLS.get(current, set()) | {"phase_gate.py", "queries.py"})
    print(f"能用工具：{' / '.join(tools)}")
    print("下一步：缺口补齐跑 check，能进下一阶段跑 advance")
    sys.exit(0)

# ── Tool whitelist per phase ──────────────────────────────
# Each phase has ONE exclusive validate script + optional aux scripts.
# Globals (GLOBAL_TOOLS) and evaluators (EVALUATOR_TOOLS) are resolved at check time.

PHASE_TOOLS = {
    "phase_0_init":                    {"project_init.py"},
    "phase_1_document_analysis":       {"validate-policy-analysis.py", "pdf_ocr_extractor.py"},
    "phase_1_5_interview":            {"validate-interview.py"},
    "phase_2_program_generation":      {"validate-program.py"},
    "phase_3_execution":               {"validate-finding.py", "data_executor.py", "data_health_check.py"},
    "phase_4_report":                  {"validate-report.py"},
}

GLOBAL_TOOLS = {
    "phase_gate.py",
    "queries.py",
    "validate-json.py",
    "audit_styles.py",
    "excel_core.py",
    "decisions_schema.py",
    "data_executor.py",
    "audit_gate.py",
    # 数据体检室（入桌前体检: Excel结构/加密/版本混乱/图片OCR待确认）
    "data_health_check.py",
    # 新桌子 ledger/ 零件（tool-check 只比 basename，见 cmd_check_tool）：
    # ledger.py=往桌上写, check.py=日常门卫, checklist.py=打勾纸,
    # audit_table.py=报告前闸机, export.py=总览表格
    "ledger.py",
    "check.py",
    "checklist.py",
    "audit_table.py",
    "export.py",
}

# Evaluator scripts — allowed from Phase 1 onward (no init-phase eval)
EVALUATOR_TOOLS = {
    "record_evaluation.py",
    "quality_gate.py",
}


def resolve_skills_dir(args) -> Path:
    """Resolve skills directory: CLI arg > env var > workspace.parent inference."""
    if args is not None and getattr(args, "skills_dir", None):
        return Path(args.skills_dir)
    env_val = os.environ.get("INTERNAL_AUDIT_SKILLS_DIR")
    if env_val:
        return Path(env_val)
    ws = find_workspace()
    inferred = ws.parent
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
    """Write back current-audit.json（原子落账：先写临时再改名，断电不留半条）。"""
    import os
    audit_path = ws / "current-audit.json"
    tmp = ws / "current-audit.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, audit_path)


def check_exit_conditions(ws: Path, current_phase: str, data: dict, args=None) -> list:
    """Check exit conditions for current phase. Returns list of issue dicts."""
    issues = []

    if current_phase == "phase_1_document_analysis":
        # C1·S3 门限：先看桌上有无看制度的行；空桌但有旧 JSON（过渡期）也放行；
        # 两边都空才拦
        if _policy_rows(ws) == 0:
            analyses = list((ws / "policy-analyses").glob("*.json")) if (ws / "policy-analyses").exists() else []
            if len(analyses) == 0:
                issues.append({"type": "block", "msg": "桌上无看制度的结论行（需 document-organizer 先上桌），policy-analyses/ 也无 JSON"})
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

        issues.extend(check_consumed_consistency(data, ws))

    elif current_phase == "phase_3_execution":
        if not data.get("audit_state", {}).get("report_type"):
            issues.append({"type": "block", "msg": "报告类型未选择。请返回 report-generator 选择报告类型（标准/专项/舞弊/跟踪）。"})
        findings_dir = ws / "findings"
        findings = [f for f in findings_dir.glob("F-*.json")] if findings_dir.exists() else []
        table_rows = _table_rows(ws)
        if len(findings) == 0 and table_rows == 0:
            issues.append({"type": "block", "msg": "无审计发现（findings/ 无 F-*.json 且桌子 left[] 为空，需 >=1 条）"})

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


def _obs_covered_by_s(obs: dict, stext: str) -> bool:
    """一条待处理线索在 S 补充文字里找得到号（编号命中，或标题前 6 字命中）→ 对上号了。"""
    oid = str(obs.get("id") or "").strip().upper()
    if oid and oid in stext:
        return True
    title = str(obs.get("title") or "").strip()
    if len(title) >= 6 and title[:6].upper() in stext:
        return True
    return False


def check_consumed_consistency(data: dict, iw: Path) -> list:
    """消化对号保险：账本标了"已消化"，就得在 S 补充里找得到每条待处理线索的号。
    对不上 → prompt_update（先对号再标；--force 可过）。解析器坏了/没文件 → 空
    （门卫不因自己看不清而拦路）。iw = internal-audit-workspace 目录。"""
    if data.get("audit_state", {}).get("design_observations_consumed") is not True:
        return []
    try:
        from program_ir_parser import build_ir
    except Exception:
        return []
    pending = []
    ddir = iw / "design-assessments"
    if ddir.is_dir():
        for f in sorted(ddir.glob("*.json")):
            try:
                content = json.loads(f.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            for o in content.get("design_observations") or []:
                if isinstance(o, dict) and o.get("type") == "risk_clue" and o.get("status") == "pending":
                    pending.append(o)
    if not pending:
        return []
    stext = ""
    pdir = iw / "audit-programs"
    if pdir.is_dir():
        for md in sorted(pdir.glob("*.md")):
            try:
                ir = build_ir(md)
            except Exception:
                continue
            for s in ir.get("steps", []) or []:
                if s.get("track") == "S" and not s.get("is_deleted"):
                    stext += " " + " ".join(str(s.get(k) or "")
                                            for k in ("step_id", "title", "procedure", "clue_basis")).upper()
    missing = [o for o in pending if not _obs_covered_by_s(o, stext)]
    if not missing:
        return []
    ids = "、".join(str(o.get("id") or "?") for o in missing[:10])
    return [{"type": "prompt_update",
             "msg": f"{len(missing)}条待处理线索在S补充中找不到对应，先对号再标消化（{ids}）",
             "suggested_skill": "internal-audit-program-generator",
             "trigger": "interview"}]


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


def cmd_checklist(args):
    """打勾纸（只看不拦）：转调 ledger/checklist.py，旧闸机命令一个不动。"""
    import subprocess
    gold = Path(__file__).resolve().parent.parent.parent
    script = gold / "ledger" / "checklist.py"
    if not script.exists():
        print("打勾纸零件缺失：ledger/checklist.py，用旧闸机 status/check")
        sys.exit(2)
    r = subprocess.run([sys.executable, str(script), "--workspace", args.workspace])
    sys.exit(0)  # 纸不拦路，透传只看不看码


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

    # Not allowed — force overrides (拍照已取消A5：只记流水，不存快照)
    if getattr(args, "force", False):
        try:
            data = load_audit()
            append_audit_trail(data, "tool_force_override",
                               f"强制调用 {tool_name}（当前阶段 {phase} 不允许）")
            save_audit(data, ws)
        except SystemExit:
            pass  # no workspace — ok
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

    data["status"] = next_phase
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    append_audit_trail(data, "phase_advance", f"{current} -> {next_phase}")
    save_audit(data, ws)

    print(json.dumps({
        "action": "advanced",
        "from": current,
        "to": next_phase,
        "updated_at": data["updated_at"],
    }, ensure_ascii=False, indent=2))
    sys.exit(0)


def cmd_rollback(args):
    """回退已取消（A4）：状态只朝前走，不倒车。

    新线索 → ledger.py add-task 插任务往前走；
    结论有误 → 标作废另起行。本命令一个字不写，直接拒收。
    """
    print(json.dumps({
        "action": "refused",
        "reason": "回退已取消：状态只朝前走。新线索请用 ledger.py add-task 插任务往前走；"
                  "结论有误请标作废另起行（close-task --verdict 作废）",
    }, ensure_ascii=False, indent=2))
    sys.exit(2)


def cmd_log_program_change(args):
    """现场改程序记账：新增进 added、停用进 deferred（并从 pending 摘掉）、替代只记历史。
    只记流水（大事记+更新历史），不拍照。缺的格子就地补（老账本不作废）。"""
    ws = find_workspace()
    data = load_audit()
    st = data.setdefault("audit_state", {})
    progs = st.setdefault("programs", {})
    pid, ptype = args.id, args.type
    if ptype == "added":
        lst = progs.setdefault("added", [])
        if pid not in lst:
            lst.append(pid)
    elif ptype == "deferred":
        lst = progs.setdefault("deferred", [])
        if pid not in lst:
            lst.append(pid)
        pend = progs.get("pending") or []
        if pid in pend:
            pend.remove(pid)
            progs["pending"] = pend
    hist = st.setdefault("program_update_history", [])
    hist.append({"date": datetime.now().strftime("%Y-%m-%d"),
                 "id": pid, "type": ptype, "reason": args.reason})
    append_audit_trail(data, "program_change", f"{pid} {ptype}：{args.reason}")
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    save_audit(data, ws)
    print(json.dumps({
        "action": "program_change_logged",
        "id": pid,
        "type": ptype,
    }, ensure_ascii=False, indent=2))
    sys.exit(0)


def cmd_log_decision(args):
    """记录审计决策到 audit_trail（decision 事件）"""
    ws = find_workspace()
    data = load_audit()
    detail = f"{args.scene}:{args.decision}:{args.basis}"
    append_audit_trail(data, "decision", detail)
    save_audit(data, ws)
    print(json.dumps({
        "action": "decision_logged",
        "event_type": "decision",
        "detail": detail,
    }, ensure_ascii=False, indent=2))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="阶段状态机 (地铁闸机模型)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="显示当前阶段和退出条件")

    p_check = sub.add_parser("check", help="检查能否进入下一阶段")
    p_check.add_argument("--skills-dir", default=None, help="技能目录路径 (默认: env INTERNAL_AUDIT_SKILLS_DIR 或 workspace.parent)")
    p_check.add_argument("--force", action="store_true", help="强制通过 prompt_program_update 提示")

    sub.add_parser("next", help="下一步：现在能干什么、还缺什么（人话看板，只报不拦）")

    p_advance = sub.add_parser("advance", help="执行阶段切换")
    p_advance.add_argument("--skills-dir", default=None, help="技能目录路径 (默认: env INTERNAL_AUDIT_SKILLS_DIR 或 workspace.parent)")
    p_advance.add_argument("--force", action="store_true", help="强制通过 prompt_program_update 提示")

    rb = sub.add_parser("rollback", help="已取消：回退改插任务往前走（本命令只拒收）")
    rb.add_argument("--to", required=False, default=None, help="已废弃，保留只为兼容旧调用")
    rb.add_argument("--reason", required=False, default=None, help="已废弃，保留只为兼容旧调用")

    p_tc = sub.add_parser("tool-check", help="检查工具在当前阶段是否可用")
    p_tc.add_argument("tool_name", help="脚本名称 (如 validate-finding.py)")
    p_tc.add_argument("--phase", default=None, choices=PHASES, help="强制指定阶段 (默认: 从 current-audit.json 读取)")
    p_tc.add_argument("--force", action="store_true", help="强制放行并记录 audit_trail")

    p_log = sub.add_parser("log-decision", help="记录审计决策到 audit_trail (decision 事件)")
    p_log.add_argument("--scene", required=True, help="决策场景 (程序选择/风险定级/线索排除)")
    p_log.add_argument("--decision", required=True, help="决策内容")
    p_log.add_argument("--basis", required=True, help="决策依据")

    p_pc = sub.add_parser("log-program-change", help="现场改程序记账 (added/deferred + 更新历史 + 大事记)")
    p_pc.add_argument("--type", required=True, choices=["added", "deferred", "substituted"],
                      help="新增 / 停用(盖章保留原行) / 替代换方法")
    p_pc.add_argument("--id", required=True, help="程序编号 (如 X-001/A-003)")
    p_pc.add_argument("--reason", required=True, help="变更原因")

    p_cl = sub.add_parser("checklist", help="打勾纸：六句话看板，只看不拦（新桌子）")
    p_cl.add_argument("--workspace", required=True, help="老项目根目录（内含 internal-audit-workspace/）")

    args = parser.parse_args()
    cmds = {"status": cmd_status, "check": cmd_check, "advance": cmd_advance,
            "rollback": cmd_rollback, "tool-check": cmd_tool_check,
            "log-decision": cmd_log_decision, "log-program-change": cmd_log_program_change,
            "checklist": cmd_checklist, "next": cmd_next}
    if args.command in cmds:
        cmds[args.command](args)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
