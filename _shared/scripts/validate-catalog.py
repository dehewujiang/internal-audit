#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-catalog.py — _evidence_catalog.json 结构校验器（R05）

[INPUT]:  _evidence_catalog.json 文件路径
[OUTPUT]: 校验报告（文本/JSON），exit 0=pass / 1=block / 2=文件错误
[POS]:    _shared/scripts 的证据清单校验工具，被 audit-execution-assistant/SKILL.md
          Step 1 引用（读取 catalog 前调用）；损坏时阻止执行阶段误判证据状态

校验范围（基于 v2.0 实际 schema，字段名以 evidence_catalog.py / create_evidence_dirs.py
生成的真实 catalog 为准——顶层 project/items/total_slots/filled_slots，槽位
id/name/source_track/source_programs/file/collected_at）：
- 结构：JSON 可解析、顶层必填、items 为数组
- 槽位：id 非空且唯一、name 非空、source_track 非空、source_programs 为数组、
  file 为 null 或字符串
- 计数：total_slots 与 len(items) 一致、filled_slots 与 file 非空槽位数一致
  （不一致 = catalog 被手工编辑过或生成逻辑异常）
- 警告：source_programs 为空的槽位（无程序引用的孤儿槽位）

[PROTOCOL]: 变更时更新此头部，然后检查同级 CLAUDE.md
"""

import sys
import json
import argparse
from pathlib import Path

REQUIRED_TOP = ["project", "items"]
REQUIRED_SLOT = ["id", "name", "source_track", "source_programs", "file"]


def load_catalog(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def check_structure(data):
    """[S] 顶层结构与槽位必填字段"""
    issues = []
    for k in REQUIRED_TOP:
        if k not in data:
            issues.append(f"缺少顶层字段: {k}")
    if "items" in data and not isinstance(data["items"], list):
        issues.append("items 必须是数组")
        return False, issues

    items = data.get("items", [])
    seen = set()
    for i, slot in enumerate(items):
        if not isinstance(slot, dict):
            issues.append(f"items[{i}] 不是对象")
            continue
        for k in REQUIRED_SLOT:
            if k not in slot:
                issues.append(f"items[{i}] 缺少字段: {k}")
        sid = slot.get("id")
        if sid is not None:
            if sid in seen:
                issues.append(f"槽位 id 重复: {sid}")
            seen.add(sid)
        sp = slot.get("source_programs")
        if sp is not None and not isinstance(sp, list):
            issues.append(f"items[{i}] source_programs 必须是数组")
        f = slot.get("file")
        if f is not None and not isinstance(f, str):
            issues.append(f"items[{i}] file 必须是 null 或字符串")
    return (not issues), issues


def check_counts(data):
    """[C] 计数一致性（total_slots / filled_slots）"""
    issues = []
    items = data.get("items", [])
    if not isinstance(items, list):
        return False, issues
    if "total_slots" in data and data["total_slots"] != len(items):
        issues.append(
            f"total_slots({data['total_slots']}) 与 items 实际数量({len(items)}) 不一致"
            "——catalog 可能被手工编辑过")
    filled = sum(1 for s in items if isinstance(s, dict) and s.get("file"))
    if "filled_slots" in data and data["filled_slots"] != filled:
        issues.append(
            f"filled_slots({data['filled_slots']}) 与实际已匹配槽位数({filled}) 不一致")
    return (not issues), issues


def check_warnings(data):
    """[W] 非阻断警告"""
    warns = []
    items = data.get("items", [])
    for i, slot in enumerate(items):
        if isinstance(slot, dict) and not slot.get("source_programs"):
            warns.append(f"items[{i}]({slot.get('id', '?')}) source_programs 为空——无程序引用")
    return warns


def main():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure and sys.stdout.encoding != "utf-8":
        reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="证据清单 _evidence_catalog.json 结构校验器")
    parser.add_argument("path", help="catalog JSON 文件路径")
    parser.add_argument("--strict", action="store_true", help="block 时 exit 1（默认 exit 0）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    p = Path(args.path)
    if not p.is_file():
        print(f"[ERROR] 文件不存在: {p}", file=sys.stderr)
        sys.exit(2)
    try:
        data = load_catalog(p)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(2)

    ok_s, issues_s = check_structure(data)
    ok_c, issues_c = check_counts(data)
    warns = check_warnings(data)
    blocks = issues_s + issues_c
    action = "block" if blocks else ("warn" if warns else "pass")

    if args.json:
        print(json.dumps({
            "action": action,
            "blocks": blocks,
            "warnings": warns,
            "total_slots": len(data.get("items", [])) if isinstance(data.get("items"), list) else -1,
        }, ensure_ascii=False, indent=2))
    else:
        for i in blocks:
            print(f"[BLOCK] {i}")
        for w in warns:
            print(f"[WARN] {w}")
        print(f"action={action}（{len(blocks)} block / {len(warns)} warn）")

    if blocks:
        sys.exit(1 if args.strict else 0)
    sys.exit(0)


if __name__ == "__main__":
    main()
