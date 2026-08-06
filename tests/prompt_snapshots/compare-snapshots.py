#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare-snapshots.py — Prompt 快照漂移检测（R08）

[INPUT]:  当前 git 暂存区（git diff --cached --name-only）；或 --files 手动传入
[OUTPUT]: 漂移警告，exit 0=通过 / 1=拦截
[POS]:    tests/prompt_snapshots 的开发工具，被 .git/hooks/pre-commit 调用

判定逻辑（区分"有意变更 vs 无意漂移"）：
- 源文件和对应快照【同时】被修改 → 有意变更 → 通过
- 源文件被修改但快照【未】修改 → 可能漂移 → 警告 + 拦截（可 SKIP_SNAP_CHECK=1 跳过）
- 仅快照被修改 → 允许（快照单独更新）

映射关系（源文件 → 依赖它的快照列表；注意 .claude/skills/ junction 镜像路径会归一化）：
[PROTOCOL]: 变更此映射时同步更新 README.md 快照清单
"""

import os
import sys
import subprocess
import argparse

# 源文件 → 快照列表（junction 镜像路径自动归一化）
SOURCE_TO_SNAPS = {
    "audit-execution-assistant/SKILL.md": [
        "tests/prompt_snapshots/cceer_chain.snap",
        "tests/prompt_snapshots/root_cause_challenge.snap",
    ],
    "audit-execution-assistant/references/evidence_standards.md": [
        "tests/prompt_snapshots/evidence_grading.snap",
    ],
    "audit-execution-assistant/references/intuition_engine.md": [
        "tests/prompt_snapshots/intuition_engine.snap",
    ],
    "internal-audit-program-generator/SKILL.md": [
        "tests/prompt_snapshots/adversarial_validation.snap",
    ],
}


def normalize(path):
    """归一化路径：反斜杠转正斜杠；去掉 .claude/skills/ junction 镜像前缀。"""
    p = path.replace("\\", "/")
    if p.startswith(".claude/skills/"):
        return p[len(".claude/skills/"):]
    return p


def get_changed_files():
    """读取 git 暂存区（cached）变更文件列表。"""
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        return {normalize(f) for f in out.stdout.splitlines() if f.strip()}
    except subprocess.CalledProcessError:
        return set()


def check(changed):
    issues = []
    for src, snaps in SOURCE_TO_SNAPS.items():
        if src in changed:
            missing = [s for s in snaps if s not in changed]
            if missing:
                issues.append(
                    f"[SNAP] 源文件 {src} 已修改，但快照未同步: {', '.join(missing)}")
                issues.append("       如为有意变更请同步更新快照；如为无意漂移请回滚源文件。")
    return issues


def main():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure and sys.stdout.encoding != "utf-8":
        reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Prompt 快照漂移检测（pre-commit hook 用）")
    parser.add_argument("--files", help="手动传入变更文件列表（逗号分隔，测试/CI 用；默认读 git 暂存区）")
    parser.add_argument("--no-exit", action="store_true", help="始终 exit 0（仅展示警告，CI 报告用）")
    args = parser.parse_args()

    if args.files:
        changed = {normalize(f.strip()) for f in args.files.split(",") if f.strip()}
    else:
        changed = get_changed_files()

    issues = check(changed)
    if issues:
        for i in issues:
            print(i)
        print("跳过本次检查: 环境变量 SKIP_SNAP_CHECK=1")
        if args.no_exit:
            sys.exit(0)
        sys.exit(1)
    print("快照一致性检查通过")
    sys.exit(0)


if __name__ == "__main__":
    main()
