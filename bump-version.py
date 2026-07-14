#!/usr/bin/env python3
"""
bump-version.py — 自动更新 VERSION.json

用法：
    python bump-version.py                           # 自动 bump 版本号 + 时间戳
    python bump-version.py --add "script:queries.py:trace 支持三种 ID"   # 追加一条变更记录
    python bump-version.py --commit                  # bump + git commit VERSION.json

版本号规则：YYYY-MM-DD-N（当天第 N 个版本）

[INPUT]:  VERSION.json + git HEAD
[OUTPUT]: VERSION.json（更新 version/git_commit/updated_at/changes）
[POS]:    黄金源根目录的开发工具，不部署到审计项目
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Windows GBK 兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def get_version_path():
    """定位 VERSION.json（与脚本同目录）"""
    return Path(__file__).resolve().parent / "VERSION.json"


def get_short_hash():
    """获取当前 git HEAD 短哈希"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def bump_version(current_version: str, today: str) -> str:
    """计算下一个版本号。规则：YYYY-MM-DD-N"""
    parts = current_version.rsplit("-", 1)
    if len(parts) == 2 and parts[0] == today and parts[1].isdigit():
        return f"{today}-{int(parts[1]) + 1}"
    return f"{today}-1"


def main():
    version_path = get_version_path()
    if not version_path.exists():
        print(f"❌ VERSION.json 不存在: {version_path}")
        sys.exit(1)

    # 读取当前版本
    with open(version_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    old_version = data.get("version", "unknown")
    old_hash = data.get("git_commit", "unknown")

    # 计算新版本
    today = datetime.now().strftime("%Y-%m-%d")
    new_version = bump_version(old_version, today)
    new_hash = get_short_hash()
    new_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # 处理 --add 参数（追加变更记录）
    changes = data.get("changes", [])
    if "--add" in sys.argv:
        idx = sys.argv.index("--add")
        if idx + 1 < len(sys.argv):
            entry = sys.argv[idx + 1]
            parts = entry.split(":", 2)
            if len(parts) == 3:
                changes.append({
                    "type": parts[0],
                    "file": parts[1],
                    "summary": parts[2],
                })
            else:
                print(f"⚠️  --add 格式应为 type:file:summary，收到: {entry}")
                sys.exit(1)

    # 更新
    data["version"] = new_version
    data["git_commit"] = new_hash
    data["updated_at"] = new_time
    data["changes"] = changes

    with open(version_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ VERSION.json: {old_version} ({old_hash}) → {new_version} ({new_hash})")

    # --commit 模式：自动提交
    if "--commit" in sys.argv:
        result = subprocess.run(
            ["git", "add", "VERSION.json"],
            capture_output=True, text=True
        )
        result = subprocess.run(
            ["git", "commit", "-m", f"chore: bump VERSION.json to {new_version}"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ 已提交: {result.stdout.strip().split(chr(10))[-1]}")
        else:
            print(f"❌ 提交失败: {result.stderr}")
            sys.exit(1)


if __name__ == "__main__":
    main()
