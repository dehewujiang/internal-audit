# [INPUT]: --workspace, --skills-dir, --force (optional)
# [OUTPUT]: exit 0 on pass, exit 1 on block
# [POS]: 审计项目初始化安全检查，在 mkdir/写文件之前调用
import argparse
import sys
from pathlib import Path


def check_workspace_overwrite(workspace_path: Path, force: bool) -> bool:
    audit_json = workspace_path / "current-audit.json"
    if audit_json.exists():
        if force:
            print(
                f"[WARN] {audit_json} 已存在，--force 模式下继续",
                file=sys.stderr,
            )
            return True
        print(
            f"[ERROR] {audit_json} 已存在，工作区非空。使用 --force 强制覆盖",
            file=sys.stderr,
        )
        return False
    return True


def check_config_files(skills_dir: Path) -> bool:
    ok = True
    for filename in ("about-me.md", "my-config.md"):
        target = skills_dir / "audit-topics" / filename
        if not target.exists():
            print(f"[ERROR] 配置文件缺失: {target}", file=sys.stderr)
            ok = False
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="审计项目初始化安全检查")
    parser.add_argument(
        "--workspace", required=True, type=Path, help="工作区目录路径"
    )
    parser.add_argument(
        "--skills-dir", required=True, type=Path, help="skills 目录路径"
    )
    parser.add_argument(
        "--force", action="store_true", help="强制覆盖已有工作区"
    )
    args = parser.parse_args()

    workspace: Path = args.workspace
    skills_dir: Path = args.skills_dir

    if not check_workspace_overwrite(workspace, args.force):
        sys.exit(1)

    if not check_config_files(skills_dir):
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
