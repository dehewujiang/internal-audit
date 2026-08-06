#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-index.py — findings/index.json 结构校验器（R06）

[INPUT]:  findings 目录路径（内含 index.json）或 index.json 文件路径
[OUTPUT]: 校验报告（文本/JSON），exit 0=pass / 1=block / 2=文件错误
[POS]:    _shared/scripts 的 finding 索引校验工具，被 internal-audit-report-generator/
          SKILL.md 读取 index 前调用；index 漂移会导致报告汇总统计出错

校验范围（schema v1.1.0，见 audit-execution-assistant/references/index_schema.md）：
- 结构：JSON 可解析、必填字段（schema_version/version/total_findings/by_year/
  by_risk/by_status/by_category/by_origin/by_keyword）
- 交叉：index 汇总条目 vs findings/ 目录实际 F-*.json 文件（排除 index.json 本身）
  - 目录有 index 无 → 遗漏（生成 finding 后忘了更新 index）
  - index 有目录无 → 幽灵条目（finding 被删但 index 未清）
- 闭合：index 中每个 finding_id 与对应 JSON 文件内 finding_id 一致
- 计数：total_findings 与 index 实际条目数一致

[PROTOCOL]: 变更时更新此头部，然后检查同级 CLAUDE.md
"""

import sys
import json
import argparse
from pathlib import Path

REQUIRED_TOP = ["schema_version", "version", "total_findings",
                "by_year", "by_risk", "by_status", "by_category", "by_origin", "by_keyword"]


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def collect_index_ids(data):
    """从所有 by_* 分组收集 finding_id 集合（by_keyword 的 value 也是 id 列表）。"""
    ids = set()

    def walk(v):
        if isinstance(v, list):
            for x in v:
                if isinstance(x, str):
                    ids.add(x)
                else:
                    walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    for k, v in data.items():
        if isinstance(k, str) and k.startswith("by_"):
            walk(v)
    return ids


def check_structure(data):
    """[S] 必填字段"""
    missing = [k for k in REQUIRED_TOP if k not in data]
    return (not missing), [f"缺少必填字段: {', '.join(missing)}"] if missing else []


def cross_check(data, findings_dir):
    """[X] index 与目录交叉比对"""
    issues = []
    files = sorted(findings_dir.glob("F-*.json"))
    dir_ids = {p.stem for p in files}
    index_ids = collect_index_ids(data)

    missing = sorted(dir_ids - index_ids)
    ghost = sorted(index_ids - dir_ids)
    if missing:
        issues.append(f"目录有但 index 遗漏（{len(missing)} 个）: {', '.join(missing[:10])}")
    if ghost:
        issues.append(f"index 有但目录缺失——幽灵条目（{len(ghost)} 个）: {', '.join(ghost[:10])}")

    # 闭合：文件内 finding_id 与文件名一致
    mismatch = []
    for p in files:
        try:
            fdata = load_json(p)
        except (json.JSONDecodeError, OSError):
            mismatch.append(f"{p.name}: 无法解析")
            continue
        fid = fdata.get("finding_id")
        if fid and fid != p.stem:
            mismatch.append(f"{p.name}: 文件内 finding_id={fid} 与文件名不一致")
    if mismatch:
        issues.append(f"闭合检查（{len(mismatch)} 个）: {', '.join(mismatch[:5])}")

    total = data.get("total_findings")
    if total is not None and total != len(index_ids):
        issues.append(f"total_findings({total}) 与 index 实际条目数({len(index_ids)}) 不一致")
    return (not issues), issues


def main():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure and sys.stdout.encoding != "utf-8":
        reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="findings/index.json 结构校验器")
    parser.add_argument("path", help="findings 目录路径（含 index.json）或 index.json 文件路径")
    parser.add_argument("--strict", action="store_true", help="block 时 exit 1（默认 exit 0）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    p = Path(args.path)
    if p.is_dir():
        index_path = p / "index.json"
        findings_dir = p
    else:
        index_path = p
        findings_dir = p.parent
    if not index_path.is_file():
        existing = list(findings_dir.glob("F-*.json"))
        if not existing:
            print("无 finding 文件，index 校验跳过（exit 0）")
            sys.exit(0)
        print(f"[ERROR] index.json 不存在但存在 {len(existing)} 个 finding 文件——"
              "违反 index 强制更新规则", file=sys.stderr)
        sys.exit(2)

    try:
        data = load_json(index_path)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(2)

    blocks = []
    ok_s, issues_s = check_structure(data)
    blocks += issues_s
    ok_x, issues_x = cross_check(data, findings_dir)
    blocks += issues_x
    action = "block" if blocks else "pass"

    if args.json:
        print(json.dumps({
            "action": action,
            "blocks": blocks,
            "total_in_index": len(collect_index_ids(data)),
            "files_in_dir": len(list(findings_dir.glob("F-*.json"))),
        }, ensure_ascii=False, indent=2))
    else:
        for i in blocks:
            print(f"[BLOCK] {i}")
        print(f"action={action}（{len(blocks)} block）")

    if blocks:
        sys.exit(1 if args.strict else 0)
    sys.exit(0)


if __name__ == "__main__":
    main()
