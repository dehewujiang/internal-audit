#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-relations.py — relations.json 口径配置校验器（勾稽 v1.0）

[INPUT]:  relations.json 文件路径（审计项目内 internal-audit-workspace/reconcile/relations.json）
[OUTPUT]: 校验报告（文本/JSON），exit 0=pass/warn / 2=block或文件错误；
          人话模式尾行追 SHEET 答卷（action=pass/warn/block）
[POS]:    _shared/scripts 的勾稽口径校验工具，check_reconcile.py 执行前调用；
          口径未声明、容差未定义、键未验唯一时阻止勾稽执行，避免口径不清的数字进底稿

校验范围（schema v1.0，本版只允许 type=detail_to_total）：
- 结构：JSON 可解析、顶层必填、relations 为数组、id 唯一
- 硬停（block）：type 越界、key_unique_checked 非 true、caliber 缺项、
  tolerance 缺项或 mode 非法、detail 缺项、total 写法二选一落空、filter.op 越界
- 警告（warn）：field_map 值不在词典内、file 在 _files/ 里找不到、
  relations 为空、disabled 跳过提示

[PROTOCOL]: 变更时更新此头部，然后检查同级 CLAUDE.md
"""

import sys
import json
import argparse
from pathlib import Path

REQUIRED_TOP = ["relations"]
REQUIRED_REL = ["id", "type", "title", "detail", "total",
                "caliber", "tolerance", "key_unique_checked", "status"]
REQUIRED_DETAIL = ["file", "sheet", "header_row", "key_col", "amount_col"]
REQUIRED_CALIBER = ["currency_unit", "tax", "date_range", "note"]
ALLOWED_TYPES = ["detail_to_total"]
ALLOWED_FILTER_OPS = ["eq", "ne", "in", "notnull"]
ALLOWED_TOL_MODES = ["absolute", "relative"]


def _script_dir():
    return Path(__file__).resolve().parent


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_dictionary():
    """词典在金源 _shared/reconcile/field_dictionary.json；找不到返回空（降级为不查）。"""
    p = _script_dir().parent / "reconcile" / "field_dictionary.json"
    try:
        return load_json(p).get("fields", {})
    except Exception:
        return {}


def check_structure(data):
    """[S] 顶层结构与单条必填字段（含 id 唯一）。"""
    issues = []
    for k in REQUIRED_TOP:
        if k not in data:
            issues.append(f"缺少顶层字段: {k}")
    if "relations" in data and not isinstance(data["relations"], list):
        issues.append("relations 必须是数组")
        return False, issues

    seen = set()
    for i, rel in enumerate(data.get("relations", [])):
        if not isinstance(rel, dict):
            issues.append(f"relations[{i}] 不是对象")
            continue
        for k in REQUIRED_REL:
            if k not in rel:
                issues.append(f"relations[{i}]({rel.get('id', '?')}) 缺少字段: {k}")
        rid = rel.get("id")
        if rid is not None:
            if rid in seen:
                issues.append(f"口径 id 重复: {rid}")
            seen.add(rid)
    return (not issues), issues


def check_hard_stops(data):
    """[H] 三个硬停 + 两道门（type/filter 越界）。disabled 的口径跳过（只查 id）。"""
    blocks = []
    for i, rel in enumerate(data.get("relations", [])):
        if not isinstance(rel, dict):
            continue
        rid = rel.get("id", f"relations[{i}]")
        if rel.get("status") == "disabled":
            continue

        # 门1：本版只允许 detail_to_total
        if "type" in rel and rel["type"] not in ALLOWED_TYPES:
            blocks.append(f"{rid}: type={rel['type']} 本版只支持 detail_to_total——配置退回")

        # 硬停①：键唯一必须已验
        if "key_unique_checked" in rel and rel["key_unique_checked"] is not True:
            blocks.append(f"{rid}: 明细键唯一未验——先跑 dedup 验唯一再勾稽")

        # 硬停②：口径四项全非空
        cal = rel.get("caliber")
        if isinstance(cal, dict):
            for k in REQUIRED_CALIBER:
                if not cal.get(k):
                    blocks.append(f"{rid}: 口径未声明（caliber.{k} 为空）——人先签字")
        elif "caliber" in rel:
            blocks.append(f"{rid}: caliber 必须是对象")

        # 硬停③：容差 mode+value 必备且合法
        tol = rel.get("tolerance")
        if isinstance(tol, dict):
            if tol.get("mode") not in ALLOWED_TOL_MODES:
                blocks.append(f"{rid}: 容差未定义（tolerance.mode 须为 absolute/relative）——人先拍数")
            if tol.get("value") is None:
                blocks.append(f"{rid}: 容差未定义（tolerance.value 缺失）——人先拍数")
        elif "tolerance" in rel:
            blocks.append(f"{rid}: tolerance 必须是对象")

        # detail 缺项
        det = rel.get("detail")
        if isinstance(det, dict):
            for k in REQUIRED_DETAIL:
                if k not in det or det[k] in (None, ""):
                    blocks.append(f"{rid}: detail.{k} 缺失——列定位不清不许跑")
            flt = det.get("filter")
            if flt is not None:
                if not isinstance(flt, dict):
                    blocks.append(f"{rid}: detail.filter 必须是对象")
                elif flt.get("op") not in ALLOWED_FILTER_OPS:
                    blocks.append(
                        f"{rid}: filter.op={flt.get('op')} 越界"
                        f"（只认 { '/'.join(ALLOWED_FILTER_OPS) }）——复杂条件走人工")
        elif "detail" in rel:
            blocks.append(f"{rid}: detail 必须是对象")

        # total：file 必备 + cell/row_filter 二选一
        tot = rel.get("total")
        if isinstance(tot, dict):
            if not tot.get("file"):
                blocks.append(f"{rid}: total.file 缺失——总数来源不清不许跑")
            if not tot.get("cell") and not tot.get("row_filter"):
                blocks.append(f"{rid}: total 须写 cell 或 row_filter 二选一——总数定位不清不许跑")
        elif "total" in rel:
            blocks.append(f"{rid}: total 必须是对象")
    return blocks


def check_warnings(data, dictionary, workspace=None):
    """[W] 非阻断警告：词典外字段、文件找不到、空表、disabled 提示。"""
    warns = []
    relations = data.get("relations", [])
    if isinstance(relations, list) and not relations:
        warns.append("relations 为空——没有可执行的勾稽口径")
    for rel in relations:
        if not isinstance(rel, dict):
            continue
        rid = rel.get("id", "?")
        if rel.get("status") == "disabled":
            warns.append(f"{rid} 已停用（disabled），跳过执行")
            continue
        fm = rel.get("field_map")
        if isinstance(fm, dict) and dictionary:
            for src, std in fm.items():
                if std not in dictionary:
                    warns.append(f"{rid}: field_map 值 '{std}' 不在词典内——先扩词典再跑")
        if workspace:
            ws = Path(workspace)
            for side in ("detail", "total"):
                f = (rel.get(side) or {}).get("file") if isinstance(rel.get(side), dict) else None
                if f and not (ws / f.lstrip("/")).is_file() and not Path(f).is_file():
                    warns.append(f"{rid}: {side}.file '{f}' 在工作区找不到——文件先入柜")
    return warns


def main():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure and sys.stdout.encoding != "utf-8":
        reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="勾稽口径 relations.json 校验器")
    parser.add_argument("path", help="relations.json 文件路径")
    parser.add_argument("--strict", action="store_true",
                        help="已废弃（block 一律 exit 2，无需加 strict；保留仅为兼容旧调用）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--workspace", default=None,
                        help="审计项目工作区目录（用于检查 file 是否存在，不传则跳过此项）")
    args = parser.parse_args()

    p = Path(args.path)
    if not p.is_file():
        print(f"[ERROR] 文件不存在: {p}", file=sys.stderr)
        sys.exit(2)
    try:
        data = load_json(p)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(2)

    ok_s, issues_s = check_structure(data)
    blocks_h = check_hard_stops(data) if ok_s else []
    dictionary = load_dictionary()
    warns = check_warnings(data, dictionary, args.workspace)
    blocks = issues_s + blocks_h
    action = "block" if blocks else ("warn" if warns else "pass")

    active = [r for r in data.get("relations", [])
              if isinstance(r, dict) and r.get("status") != "disabled"]

    if args.json:
        print(json.dumps({
            "action": action,
            "blocks": blocks,
            "warnings": warns,
            "total": len(active),
        }, ensure_ascii=False, indent=2))
    else:
        for i in blocks:
            print(f"[BLOCK] {i}")
        for w in warns:
            print(f"[WARN] {w}")
        print(f"action={action}（{len(blocks)} block / {len(warns)} warn / {len(active)} active）")
        print("SHEET:" + json.dumps({
            "tool": "validate-relations",
            "action": action,
            "message": f"勾稽口径 {len(active)} 个生效: 拦下 {len(blocks)}, 警告 {len(warns)}",
            "summary": {"total": len(active),
                        "passed": 1 if action == "pass" else 0,
                        "warned": 1 if action == "warn" else 0,
                        "blocked": 1 if action == "block" else 0},
            "details": [{"check": "structure_hardstops", "result": action,
                         "message": "; ".join(blocks + warns) or "通过"}],
            "crashed": False,
        }, ensure_ascii=False))

    if blocks:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # 未预期崩溃 → exit(2) 阻断。绝不能让崩溃的退出码(1)被闸机误判成"警告"而放行
        import traceback
        print("SHEET:" + json.dumps({
            "tool": "validate-relations",
            "action": "block",
            "message": "脚本崩溃，已转拦下",
            "summary": {"total": 0, "passed": 0, "warned": 0, "blocked": 1},
            "details": [],
            "crashed": True,
        }, ensure_ascii=False))
        traceback.print_exc()
        sys.exit(2)
