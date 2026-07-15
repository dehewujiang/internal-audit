#!/usr/bin/env python3
"""
[INPUT]:  analysis_manifest.py diff 输出 + policy-analyses/*.json
[OUTPUT]: check/verify/finalize — 增量分析三阶段闸机（exit code 决定LLM能否继续）
[POS]:    _shared/scripts 的闸机层，和 phase_gate.py 同级——代码管边界，LLM管分析
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_SCRIPT = SCRIPT_DIR / "analysis_manifest.py"
VALIDATE_SCRIPT = SCRIPT_DIR / "validate-policy-analysis.py"


def find_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        ws = parent / "internal-audit-workspace"
        if ws.exists():
            return ws
    raise FileNotFoundError("未找到 internal-audit-workspace/ 目录")


def get_policy_analyses_dir(workspace: Path) -> Path:
    return workspace / "policy-analyses"


def get_manifest_path(workspace: Path) -> Path:
    return get_policy_analyses_dir(workspace) / "_analysis_manifest.json"


# ── 内部工具 ──────────────────────────────────────────

def run_manifest_cmd(args: list[str]) -> dict:
    """调用 analysis_manifest.py 并解析 JSON 输出"""
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)] + args,
        capture_output=True, text=True, encoding="utf-8",
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"[ERROR] analysis_manifest.py 输出解析失败: {result.stdout[:200]}", file=sys.stderr)
        sys.exit(2)


def run_validate(json_path: Path) -> tuple[bool, str]:
    """调用 validate-policy-analysis.py 校验单个 JSON"""
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(json_path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode == 0, result.stdout.strip()


# ── 闸机 1: check — 决定分析模式 ──────────────────────

def cmd_check(workspace: Path) -> int:
    diff = run_manifest_cmd(["diff", "--workspace", str(workspace)])
    summary = diff.get("summary", {})
    new_files = diff.get("new_files", [])
    changed_files = diff.get("changed_files", [])
    unchanged_files = diff.get("unchanged_files", [])

    # 检查 manifest 是否存在（首次全量 vs 增量）
    manifest = _load_manifest_silent(workspace)
    is_first_run = manifest is None

    new_and_changed = new_files + changed_files
    total = summary.get("total_files", 0)

    if total == 0:
        result = {
            "mode": "no_change",
            "message": "documents/ 目录为空，无可分析文件",
            "new_files": [],
            "unchanged_files": [],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # 首次运行：全部文件 = full 模式
    if is_first_run:
        result = {
            "mode": "full",
            "total_files": total,
            "message": f"首次分析：manifest 不存在，请对所有 {total} 个文件执行完整的批量分析。分析完成后使用 analysis_manifest.py mark 逐文件标记。",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not new_and_changed:
        # 检查是否有 manifest 记录存在但 output_json 缺失的情况
        missing_outputs = _check_missing_outputs(workspace, diff)
        if missing_outputs:
            result = {
                "mode": "repair",
                "message": f"所有文件标记为已分析，但 {len(missing_outputs)} 个产出 JSON 缺失。建议重新分析以下文件。",
                "new_files": missing_outputs,
                "unchanged_files": [f for f in unchanged_files if f not in missing_outputs],
                "missing_outputs": missing_outputs,
            }
        else:
            result = {
                "mode": "no_change",
                "message": "所有文件已分析完成，无新增或变更文件",
                "new_files": [],
                "unchanged_files": unchanged_files,
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # 增量模式
    result = {
        "mode": "incremental",
        "total_files": total,
        "new_files": new_and_changed,
        "unchanged_files": unchanged_files,
        "message": (
            f"增量模式：请只分析 new_files 中的 {len(new_and_changed)} 个文件。"
            f"unchanged_files ({len(unchanged_files)} 个) 仅用于交叉验证阶段（只读 JSON，禁止重读原文）。"
            "完成后执行 verify 闸机。"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _load_manifest_silent(workspace: Path):
    """读取 manifest，不存在返回 None（不输出警告）"""
    mpath = get_manifest_path(workspace)
    if not mpath.exists():
        return None
    try:
        with open(mpath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def _check_missing_outputs(workspace: Path, diff: dict) -> list[str]:
    """检查 manifest 中有记录但 output_json 文件不存在的情况"""
    manifest = json.loads(
        subprocess.run(
            [sys.executable, str(MANIFEST_SCRIPT), "status", "--workspace", str(workspace)],
            capture_output=True, text=True, encoding="utf-8",
        ).stdout
    )
    analyses_dir = get_policy_analyses_dir(workspace)
    missing = []
    for f in manifest.get("files", []):
        output = f.get("output_json", "")
        if output and not (analyses_dir / output).exists():
            missing.append(f["file_name"])
    return missing


# ── 闸机 2: verify — 校验 LLM 产出 ────────────────────

def cmd_verify(workspace: Path, new_files_str: str) -> int:
    new_files = [f.strip() for f in new_files_str.split(",") if f.strip()]
    if not new_files:
        print("[ERROR] --new-files 参数为空", file=sys.stderr)
        return 1

    analyses_dir = get_policy_analyses_dir(workspace)

    verified = []
    missing = []
    failed_validation = []

    for file_name in new_files:
        # 推导 JSON 文件名：{文件名去扩展名}分析报告.json
        stem = Path(file_name).stem
        json_name = f"{stem}分析报告.json"
        json_path = analyses_dir / json_name

        if not json_path.exists():
            # 也尝试其他可能的命名模式
            candidates = sorted(analyses_dir.glob(f"*{stem}*.json"))
            candidates = [c for c in candidates if not c.name.startswith("_")]
            if candidates:
                json_path = candidates[0]
                json_name = json_path.name
            else:
                missing.append(file_name)
                continue

        # 运行 validate
        passed, msg = run_validate(json_path)
        if not passed:
            failed_validation.append({"file": file_name, "json": json_name, "error": msg[:200]})
        else:
            verified.append({"file": file_name, "json": json_name})

    if missing or failed_validation:
        result = {
            "status": "fail",
            "verified": [v["json"] for v in verified],
            "missing": missing,
            "failed_validation": failed_validation,
            "message": (
                f"闸机未通过：{len(missing)} 个产出缺失，{len(failed_validation)} 个校验失败。"
                "请修正后重新运行 verify。"
            ),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = {
        "status": "pass",
        "verified": [v["json"] for v in verified],
        "missing": [],
        "failed_validation": [],
        "message": f"全部 {len(verified)} 个产出通过闸机校验。可以执行 finalize。",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ── 闸机 3: finalize — 收尾 ────────────────────────────

def cmd_finalize(workspace: Path, new_files_str: str) -> int:
    new_files = [f.strip() for f in new_files_str.split(",") if f.strip()]
    if not new_files:
        print("[ERROR] --new-files 参数为空", file=sys.stderr)
        return 1

    # 先跑 verify（确保状态未被修改）
    verify_code = cmd_verify(workspace, new_files_str)
    if verify_code != 0:
        print("[ERROR] verify 未通过，拒绝 finalize", file=sys.stderr)
        return 1

    # 逐文件 mark
    analyses_dir = get_policy_analyses_dir(workspace)
    all_ok = True
    for file_name in new_files:
        stem = Path(file_name).stem
        json_name = f"{stem}分析报告.json"
        json_path = analyses_dir / json_name
        if not json_path.exists():
            candidates = sorted(analyses_dir.glob(f"*{stem}*.json"))
            candidates = [c for c in candidates if not c.name.startswith("_")]
            json_name = candidates[0].name if candidates else json_name

        result = subprocess.run(
            [
                sys.executable, str(MANIFEST_SCRIPT), "mark",
                "--workspace", str(workspace),
                "--file", file_name,
                "--output-json", json_name,
            ],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"[ERROR] mark 失败: {file_name} — {result.stderr}", file=sys.stderr)
            all_ok = False

    if not all_ok:
        return 1

    # 检查是否需要交叉验证
    manifest = run_manifest_cmd(["status", "--workspace", str(workspace)])
    analyzed_count = manifest.get("total_analyzed", 0)
    diff = run_manifest_cmd(["diff", "--workspace", str(workspace)])
    total = diff.get("summary", {}).get("total_files", 0)

    cross_validation_needed = analyzed_count != total

    result = {
        "status": "ok",
        "files_marked": len(new_files),
        "total_analyzed": analyzed_count,
        "total_documents": total,
        "cross_validation_needed": cross_validation_needed,
        "message": (
            f"已标记 {len(new_files)} 个文件。"
            + (f"⚠️  注意：manifest 记录 {analyzed_count} 个已分析文件，但 documents/ 有 {total} 个文件。"
               "请执行全量交叉验证（只读 JSON，不重读原文）。"
               if cross_validation_needed
               else "manifest 与 documents/ 一致。")
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ── 入口 ───────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="增量分析闸机 — check/verify/finalize"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="闸机1：分析前检测，决定增量/全量模式")
    p_check.add_argument("--workspace", type=Path, help="工作区路径（默认自动查找）")

    p_verify = sub.add_parser("verify", help="闸机2：校验 LLM 的 JSON 产出是否存在并通过 validate")
    p_verify.add_argument("--workspace", type=Path, help="工作区路径（默认自动查找）")
    p_verify.add_argument("--new-files", required=True, help="新分析的文件名，逗号分隔")

    p_finalize = sub.add_parser("finalize", help="闸机3：标记完成 + 交叉验证提醒")
    p_finalize.add_argument("--workspace", type=Path, help="工作区路径（默认自动查找）")
    p_finalize.add_argument("--new-files", required=True, help="新分析的文件名，逗号分隔")

    args = parser.parse_args()

    workspace: Path = args.workspace if args.workspace else find_workspace()

    if args.command == "check":
        sys.exit(cmd_check(workspace))
    elif args.command == "verify":
        sys.exit(cmd_verify(workspace, args.new_files))
    elif args.command == "finalize":
        sys.exit(cmd_finalize(workspace, args.new_files))


if __name__ == "__main__":
    main()
