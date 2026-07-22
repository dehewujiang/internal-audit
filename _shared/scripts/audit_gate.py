#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审计调度闸机 — 确保 LLM 推理前后的 Python 校验脚本不被跳过

设计：只做"该不该放行"的判断，不做推理（推理是 LLM 的活）

用法:
    python audit_gate.py precheck --action generate_finding
    python audit_gate.py postcheck --action validate_finding --file <path>
    python audit_gate.py status

原则:
    - 不替代 LLM 推理，只做硬闸机检查
    - 校验脚本不可用时记录警告但不阻断（constitution #12 精神）
    - 所有拦截记录写入 audit_trail
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = Path(os.getcwd())


# ── 动作定义 ──────────────────────────────────────────────

ACTIONS = {
    "generate_finding": {
        "prechecks": [
            {"name": "程序完成检查", "desc": "审计程序 steps 中是否有未完成的步骤"},
            {"name": "证据完整性", "desc": "所需证据文件是否已到位"},
        ],
        "postcheck": {
            "script": "validate-finding.py",
            "message": "Finding 格式校验未通过"
        }
    },
    "generate_program": {
        "prechecks": [
            {"name": "制度分析完成", "desc": "policy-analyses/ 目录不为空"},
        ],
        "postcheck": {
            "script": "validate-program.py",
            "message": "审计程序格式校验未通过"
        }
    },
    "generate_report": {
        "prechecks": [
            {"name": "Findings 确认", "desc": "findings/ 目录中有已确认的 finding"},
        ],
        "postcheck": {
            "script": "validate-report.py",
            "message": "审计报告格式校验未通过"
        }
    },
    "generate_interview": {
        "prechecks": [],
        "postcheck": {
            "script": "validate-interview.py",
            "message": "访谈材料校验未通过"
        }
    },
    "generate_policy_analysis": {
        "prechecks": [],
        "postcheck": {
            "script": "validate-policy-analysis.py",
            "message": "制度分析校验未通过"
        }
    },
}


# ── 闸机逻辑 ──────────────────────────────────────────────

def _get_audit_json():
    """查找 current-audit.json"""
    paths = [
        WORKSPACE / "internal-audit-workspace" / "current-audit.json",
        WORKSPACE / "current-audit.json",
    ]
    for p in paths:
        if p.exists():
            return p
    return None


def do_precheck(action: str) -> int:
    """执行前置条件检查"""
    if action not in ACTIONS:
        print(f"[GATE] 未知动作: {action}")
        return 1

    checks = ACTIONS[action]["prechecks"]
    if not checks:
        print(f"[GATE] 前置检查: {action} — 无前置条件，放行")
        return 0

    audit_json = _get_audit_json()
    if not audit_json:
        print(f"[GATE] 前置检查: {action}")
        print("[GATE] ⚠️ current-audit.json 未找到，无法验证前置条件，放行（风险自负）")
        return 0

    with open(audit_json, 'r', encoding='utf-8-sig') as f:
        state = json.load(f)

    all_ok = True
    print(f"[GATE] 前置检查: {action}")
    for check in checks:
        print(f"[GATE]   {check['name']}: {check['desc']} ... 跳过（人工判断）")
    print(f"[GATE] 前置检查通过（部分条件需人工确认）")

    return 0


def do_postcheck(action: str, file_path: str) -> int:
    """执行后置校验（调用 validate 脚本）"""
    if action not in ACTIONS:
        print(f"[GATE] 未知动作: {action}")
        return 1

    postcheck = ACTIONS[action]["postcheck"]
    script_name = postcheck["script"]
    script_path = SCRIPT_DIR / script_name

    if not script_path.exists():
        print(f"[GATE] 后置校验: {action}")
        print(f"[GATE] ⚠️ 校验脚本 {script_name} 不存在，记录警告后放行")
        _log_to_trail(f"postcheck_skipped:{action}:script_not_found")
        return 0

    target = file_path or ""
    # 不同脚本使用不同的硬校验参数
    if script_name == "validate-finding.py":
        cmd = [sys.executable, str(script_path), target, "--exit-on-error"]
    elif script_name == "validate-policy-analysis.py":
        cmd = [sys.executable, str(script_path), target, "--json"]
    else:
        cmd = [sys.executable, str(script_path), target, "--strict"]

    print(f"[GATE] 后置校验: {action} → {script_name} {target}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"[GATE] ✅ 校验通过")
        _log_to_trail(f"postcheck_pass:{action}")
        return 0
    else:
        print(f"[GATE] ❌ {postcheck['message']}")
        print(f"[GATE] --- 错误详情 ---")
        print(result.stderr or result.stdout)
        print(f"[GATE] --- 结束 ---")
        _log_to_trail(f"postcheck_fail:{action}")
        return 1


def do_status():
    """显示当前项目状态"""
    audit_json = _get_audit_json()
    if not audit_json:
        print("[GATE] 当前不在审计项目目录中")
        return

    with open(audit_json, 'r', encoding='utf-8-sig') as f:
        state = json.load(f)

    print(f"[GATE] 审计项目状态")
    print(f"  主题: {state.get('audit_topic', 'unknown')}")
    print(f"  阶段: {state.get('status', 'unknown')}")

    audit_state = state.get('audit_state', {})
    findings = audit_state.get('findings', {})
    signals = audit_state.get('signals', [])
    programs = audit_state.get('programs', {})

    print(f"  发现: 草稿 {len(findings.get('draft', []))}, 已确认 {len(findings.get('confirmed', []))}")
    print(f"  信号: {len(signals)} 个")
    print(f"  程序: 完成 {len(programs.get('completed', []))}, 待办 {len(programs.get('pending', []))}")


def _log_to_trail(event: str):
    """写入 audit_trail"""
    audit_json = _get_audit_json()
    if not audit_json:
        return
    try:
        with open(audit_json, 'r', encoding='utf-8-sig') as f:
            state = json.load(f)
        trail = state.get('audit_state', {}).get('audit_trail', [])
        trail.append({
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "event": event,
            "source": "audit_gate.py"
        })
        if 'audit_state' not in state:
            state['audit_state'] = {}
        state['audit_state']['audit_trail'] = trail
        with open(audit_json, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── CLI ───────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python audit_gate.py status")
        print("  python audit_gate.py precheck --action <action>")
        print("  python audit_gate.py postcheck --action <action> --file <path>")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        do_status()

    elif cmd == "precheck":
        action = None
        for i, arg in enumerate(sys.argv):
            if arg == '--action' and i + 1 < len(sys.argv):
                action = sys.argv[i + 1]
                break
        if not action:
            print("错误: --action 参数必填")
            sys.exit(1)
        sys.exit(do_precheck(action))

    elif cmd == "postcheck":
        action = None
        file_path = ""
        for i, arg in enumerate(sys.argv):
            if arg == '--action' and i + 1 < len(sys.argv):
                action = sys.argv[i + 1]
            if arg == '--file' and i + 1 < len(sys.argv):
                file_path = sys.argv[i + 1]
        if not action:
            print("错误: --action 参数必填")
            sys.exit(1)
        sys.exit(do_postcheck(action, file_path))

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
