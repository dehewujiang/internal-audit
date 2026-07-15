#!/usr/bin/env python3
"""
[INPUT]:  internal-audit-workspace/documents/ + policy-analyses/_analysis_manifest.json
[OUTPUT]: diff/mark/status — manifest 管理（新增/变更文件检测、标记已分析、查看进度）
[POS]:    _shared/scripts 的工具层，供 incremental_analysis_gate.py 和 document-organizer 调用
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── 常量 ──────────────────────────────────────────────

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".doc", ".txt"}
EXCLUDE_PATTERNS = ["_ocr", "_待办核对"]  # OCR 中间文件不是制度原文
MANIFEST_FILENAME = "_analysis_manifest.json"
HASH_BLOCK_SIZE = 65536  # 64KB blocks for streaming hash


# ── 路径 ──────────────────────────────────────────────

def find_workspace() -> Path:
    """从 CWD 向上查找 internal-audit-workspace/"""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        ws = parent / "internal-audit-workspace"
        if ws.exists():
            return ws
    raise FileNotFoundError("未找到 internal-audit-workspace/ 目录")


def get_documents_dir(workspace: Path) -> Path:
    return workspace / "documents"


def get_policy_analyses_dir(workspace: Path) -> Path:
    return workspace / "policy-analyses"


def get_manifest_path(workspace: Path) -> Path:
    return get_policy_analyses_dir(workspace) / MANIFEST_FILENAME


# ── 文件扫描 ───────────────────────────────────────────

def scan_documents(workspace: Path) -> list[Path]:
    """扫描 documents/ 下所有支持格式文件，按文件名排序"""
    docs_dir = get_documents_dir(workspace)
    if not docs_dir.exists():
        return []
    files = []
    for fpath in sorted(docs_dir.iterdir()):
        if not fpath.is_file():
            continue
        if fpath.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        # 排除 OCR 中间文件（_ocr.txt, _ocr_待办核对.md 等）
        name = fpath.name
        if any(pat in name for pat in EXCLUDE_PATTERNS):
            continue
        files.append(fpath)
    return files


def compute_hash(fpath: Path) -> str:
    """流式计算 SHA256 哈希"""
    sha = hashlib.sha256()
    with open(fpath, "rb") as f:
        while True:
            chunk = f.read(HASH_BLOCK_SIZE)
            if not chunk:
                break
            sha.update(chunk)
    return f"sha256:{sha.hexdigest()[:16]}"


# ── manifest 读写 ──────────────────────────────────────

def load_manifest(workspace: Path) -> Optional[dict]:
    """读取 manifest，不存在返回 None，损坏返回 None + stderr 警告"""
    mpath = get_manifest_path(workspace)
    if not mpath.exists():
        return None
    try:
        with open(mpath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"[WARN] manifest 文件损坏: {mpath} — {e}", file=sys.stderr)
        return None


def save_manifest(workspace: Path, manifest: dict) -> None:
    mpath = get_manifest_path(workspace)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def create_manifest(project_id: str = "") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "1.0",
        "project_id": project_id,
        "created_at": now,
        "updated_at": now,
        "files": [],
    }


def find_entry(manifest: dict, file_name: str) -> Optional[dict]:
    for entry in manifest.get("files", []):
        if entry.get("file_name") == file_name:
            return entry
    return None


# ── diff 命令 ──────────────────────────────────────────

def cmd_diff(workspace: Path) -> int:
    manifest = load_manifest(workspace)
    if manifest is None:
        manifest = create_manifest()

    doc_files = scan_documents(workspace)
    if not doc_files:
        print(json.dumps({
            "summary": {"total_files": 0, "new": 0, "changed": 0, "unchanged": 0, "deleted": 0},
            "new_files": [],
            "changed_files": [],
            "unchanged_files": [],
            "deleted_files": [],
        }, ensure_ascii=False, indent=2))
        return 0

    # 建立 manifest 中的文件名 → entry 映射
    manifest_map = {e["file_name"]: e for e in manifest.get("files", [])}
    doc_names = {f.name for f in doc_files}

    new_files = []
    changed_files = []
    unchanged_files = []

    for fpath in doc_files:
        entry = manifest_map.get(fpath.name)
        if entry is None:
            new_files.append(fpath.name)
            continue
        current_hash = compute_hash(fpath)
        if current_hash != entry.get("file_hash"):
            changed_files.append(fpath.name)
        else:
            unchanged_files.append(fpath.name)

    # 在 manifest 中但文件已不在 documents/ 中
    deleted_files = [name for name in manifest_map if name not in doc_names]

    result = {
        "summary": {
            "total_files": len(doc_files),
            "new": len(new_files),
            "changed": len(changed_files),
            "unchanged": len(unchanged_files),
            "deleted": len(deleted_files),
        },
        "new_files": new_files,
        "changed_files": changed_files,
        "unchanged_files": unchanged_files,
        "deleted_files": deleted_files,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ── mark 命令 ──────────────────────────────────────────

def cmd_mark(workspace: Path, file_name: str, output_json: str) -> int:
    # 首先确认 output JSON 确实存在
    analyses_dir = get_policy_analyses_dir(workspace)
    output_path = analyses_dir / output_json
    if not output_path.exists():
        print(
            f"[ERROR] 产出 JSON 不存在: {output_path}，拒绝标记",
            file=sys.stderr,
        )
        return 1

    manifest = load_manifest(workspace)
    if manifest is None:
        manifest = create_manifest()

    # 计算哈希（如果 documents/ 中有对应文件）
    doc_dir = get_documents_dir(workspace)
    doc_path = doc_dir / file_name
    file_hash = compute_hash(doc_path) if doc_path.exists() else ""

    now = datetime.now(timezone.utc).isoformat()

    new_entry = {
        "file_name": file_name,
        "file_hash": file_hash,
        "status": "analyzed",
        "analyzed_at": now,
        "output_json": output_json,
    }

    # 如果已有旧记录，保留到 previous_analyses
    existing = find_entry(manifest, file_name)
    if existing:
        previous = existing.get("previous_analyses", [])
        # 去掉 current 字段，保留为历史记录
        history = {
            "analyzed_at": existing.get("analyzed_at"),
            "output_json": existing.get("output_json"),
            "file_hash": existing.get("file_hash"),
        }
        previous.append(history)
        new_entry["previous_analyses"] = previous

    # 替换或追加
    files = manifest.get("files", [])
    files = [e for e in files if e.get("file_name") != file_name]
    files.append(new_entry)
    manifest["files"] = files
    manifest["updated_at"] = now

    save_manifest(workspace, manifest)
    print(json.dumps({"status": "ok", "file": file_name, "output_json": output_json}, ensure_ascii=False))
    return 0


# ── status 命令 ────────────────────────────────────────

def cmd_status(workspace: Path) -> int:
    manifest = load_manifest(workspace)
    if manifest is None:
        print(json.dumps({
            "status": "not_started",
            "message": "尚未开始制度分析（manifest 不存在）",
        }, ensure_ascii=False, indent=2))
        return 0

    analyzed = [e for e in manifest.get("files", []) if e.get("status") == "analyzed"]
    result = {
        "status": "in_progress",
        "total_analyzed": len(analyzed),
        "last_updated": manifest.get("updated_at"),
        "files": [
            {
                "file_name": e["file_name"],
                "status": e.get("status"),
                "analyzed_at": e.get("analyzed_at"),
                "output_json": e.get("output_json"),
            }
            for e in manifest.get("files", [])
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ── 入口 ───────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="制度分析清单管理 — diff/mark/status"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_diff = sub.add_parser("diff", help="对比 documents/ 和 manifest，输出新增/变更/未变")
    p_diff.add_argument("--workspace", type=Path, help="工作区路径（默认自动查找）")

    p_mark = sub.add_parser("mark", help="标记文件为已分析")
    p_mark.add_argument("--workspace", type=Path, help="工作区路径（默认自动查找）")
    p_mark.add_argument("--file", required=True, help="文件名")
    p_mark.add_argument("--output-json", required=True, help="分析产出 JSON 文件名")

    p_status = sub.add_parser("status", help="查看分析进度")
    p_status.add_argument("--workspace", type=Path, help="工作区路径（默认自动查找）")

    args = parser.parse_args()

    workspace: Path = args.workspace if args.workspace else find_workspace()

    if args.command == "diff":
        sys.exit(cmd_diff(workspace))
    elif args.command == "mark":
        sys.exit(cmd_mark(workspace, args.file, args.output_json))
    elif args.command == "status":
        sys.exit(cmd_status(workspace))


if __name__ == "__main__":
    main()
