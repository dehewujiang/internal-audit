#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
explore_paper.py — 探索底稿工具（建骨架 + 自检）

[INPUT]:  new  : 底稿编号/标题/源文件路径/输出目录
          check: 底稿目录（内含 底稿.json）
[OUTPUT]: new  : 底稿.md + 底稿.json 骨架（源文件 size/sha256 自动写入）
          check: 校验报告（文本/JSON），exit 0=pass/warn / 2=block；
                 人话模式尾行追 SHEET 答卷
[POS]:    _shared/scripts 的探索底稿工具，探索车道产物入口；
          把"事实必须能指到依据、线索必须写下一步证据"变成机器检查，
          避免探索结果只留在对话里、复核时无法追溯
[PROTOCOL]: 变更时更新此头部，然后检查同级 CLAUDE.md
拆分候选：本文件已超 300 行，下次改动前评估把“建骨架”与“自检”分文件。
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

SCHEMA_VERSION = "0.1-prototype"
GRADES = ("A", "B", "C", "D", "E")
REQUIRED_TOP = ["working_paper_id", "title", "sources", "facts", "leads", "conclusion"]
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _reconfigure_stdout():
    fn = getattr(sys.stdout, "reconfigure", None)
    if fn and sys.stdout.encoding != "utf-8":
        fn(encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _skeleton(args):
    sources = []
    for raw in args.source:
        p = Path(raw)
        if not p.is_file():
            raise FileNotFoundError(f"源文件不存在: {raw}")
        digest = sha256_file(p)
        sources.append({
            "role": "",
            "file": raw,
            "size_bytes": p.stat().st_size,
            "sha256": digest,
            "sha256_12": digest[:12],
            "origin": "",
            "grade": None,
            "note": "",
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "working_paper_id": args.id,
        "type": "exploratory_data_analysis",
        "status": "draft",
        "environment": "development",
        "title": args.title,
        "notice": "本底稿为线索阶段产物，不构成审计结论。",
        "meta": {
            "subject": "",
            "audit_period": "",
            "data_period": "",
            "prepared_by": "AI 助手",
            "prepared_at": date.today().isoformat(),
            "reviewed_by": None,
            "reviewed_at": None,
            "evidence_grade": "",
        },
        "objective": list(args.objective or []),
        "sources": sources,
        "profile": {},
        "cross_check": {},
        "procedures": [],
        "facts": [],
        "leads": [],
        "excluded_leads": [],
        "limitations": [],
        "conclusion": {
            "type": "data_usability_only",
            "audit_conclusion": False,
            "usable_for": [],
            "not_usable_for": [],
            "preconditions": [],
        },
        "next_steps": [],
        "attachments": [],
    }


def _render_md(paper):
    lines = [
        f"# 探索底稿 {paper['working_paper_id']}",
        "",
        "**底稿性质**：探索性数据分析（线索阶段）",
        "**用途**：开发环境/审计项目底稿",
        "**状态**：草稿",
        "**本底稿不构成审计结论。**",
        "",
        "---",
        "",
        "## 底稿头",
        "",
        "| 项目 | 内容 |",
        "|---|---|",
        f"| 底稿编号 | {paper['working_paper_id']} |",
        f"| 标题 | {paper['title']} |",
        f"| 编制日期 | {paper['meta']['prepared_at']} |",
        "| 复核人 | 待定 |",
        "| 复核日期 | 待定 |",
        "",
        "## 0. 三句话看懂",
        "",
        "（待填）",
        "",
        "## 1. 审计目标",
        "",
    ]
    if paper["objective"]:
        for i, obj in enumerate(paper["objective"], 1):
            lines.append(f"{i}. {obj}")
    else:
        lines.append("（待填）")

    lines += ["", "## 2. 数据来源", "", "| 文件 | 大小 | sha256（前12位） | 来源 | 等级 |", "|---|---:|---|---|:---:|"]
    for s in paper["sources"]:
        lines.append(f"| `{s['file']}` | {s['size_bytes']} B | `{s['sha256_12']}` | {s['origin'] or '待补'} | {s['grade'] or '待定'} |")

    lines += [
        "",
        "## 3. 执行的程序",
        "",
        "（待填：每条程序对应代码与结果文件）",
        "",
        "## 4. 已确认的事实",
        "",
        "（待填：每条事实必须写 `basis`，指向可复算的结果文件）",
        "",
        "## 5. 线索清单",
        "",
        "（待填：每条线索必须写 `evidence_needed`，说明下一步要什么证据）",
        "",
        "## 6. 限制与不确定性",
        "",
        "（待填）",
        "",
        "## 7. 数据可用性结论",
        "",
        "（待填：只写数据能不能用，不写审计结论）",
        "",
        "## 8. 下一步",
        "",
        "（待填）",
        "",
        "## 9. 附件",
        "",
        "（待填：代码、结果、画像）",
        "",
        "## 10. 复核栏",
        "",
        "| 项 | 内容 |",
        "|---|---|",
        "| 复核人 | |",
        "| 复核日期 | |",
        "| 复核意见 | ☐ 同意作为线索底稿 ☐ 需补充证据 ☐ 需重做 |",
        "| 复核签名 | |",
        "",
        "---",
        "",
        "*所有数字应能用附件代码复算；线索未经原始凭证验证，不得直接作为审计发现。*",
        "",
    ]
    return "\n".join(lines)


def cmd_new(args):
    out = Path(args.out)
    json_path = out / "底稿.json"
    md_path = out / "底稿.md"
    if not args.force and (json_path.exists() or md_path.exists()):
        print(f"[BLOCK] 输出目录已有底稿文件，拒绝覆盖: {out}（确需覆盖加 --force）")
        return 2
    try:
        paper = _skeleton(args)
    except FileNotFoundError as e:
        print(f"[BLOCK] {e}")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(paper, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_md(paper), encoding="utf-8")
    print(f"[OK] 底稿骨架: {json_path}")
    print(f"[OK] 人话底稿: {md_path}")
    print(f"源文件 {len(paper['sources'])} 个，sha256 已写入")
    print("SHEET:" + json.dumps({
        "tool": "explore-paper", "action": "pass",
        "message": f"骨架已生成：{paper['working_paper_id']}",
        "summary": {"total": 1, "passed": 1, "warned": 0, "blocked": 0},
        "details": [], "crashed": False,
    }, ensure_ascii=False))
    return 0


def _load(paper_dir: Path):
    p = paper_dir / "底稿.json"
    if not p.is_file():
        raise FileNotFoundError(f"找不到 {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def check_paper(paper_dir: Path):
    """返回 (blocks, warns)。纯函数，便于测试。"""
    blocks, warns = [], []
    try:
        paper = _load(paper_dir)
    except FileNotFoundError as e:
        return [str(e)], []
    except json.JSONDecodeError as e:
        return [f"底稿.json 解析失败: {e}"], []

    for k in REQUIRED_TOP:
        if k not in paper:
            blocks.append(f"缺少顶层字段: {k}")
    if blocks:
        return blocks, warns

    if not (paper_dir / "底稿.md").is_file():
        warns.append("底稿.md 缺失（人话版未生成）")

    sources = paper.get("sources") or []
    if not isinstance(sources, list) or not sources:
        blocks.append("sources 为空——至少登记一个源文件")
    else:
        for i, s in enumerate(sources):
            name = s.get("file") or f"sources[{i}]"
            if not s.get("file"):
                blocks.append(f"sources[{i}] 缺少 file")
            if not HEX64.match(str(s.get("sha256", ""))):
                blocks.append(f"{name}: sha256 缺失或不是64位小写十六进制")
            if s.get("grade") not in GRADES:
                warns.append(f"{name}: 证据等级未标（A/B/C/D/E）")
            f = Path(s.get("file", ""))
            if not f.is_file() and not (paper_dir / f).is_file():
                warns.append(f"{name}: 源文件在当前路径下找不到")

    facts = paper.get("facts") or []
    fact_ids = set()
    if not facts:
        warns.append("facts 为空——还没有可复算的事实")
    for i, f in enumerate(facts):
        fid = f.get("id") or f"facts[{i}]"
        if not f.get("id"):
            blocks.append(f"facts[{i}] 缺少 id")
        if not f.get("statement"):
            blocks.append(f"{fid}: 缺少 statement")
        if fid in fact_ids:
            blocks.append(f"事实 id 重复: {fid}")
        fact_ids.add(fid)
        basis = f.get("basis") or []
        if not basis:
            blocks.append(f"{fid}: 缺少依据（basis）——事实必须能指到可复算的结果文件")
            continue
        for b in basis:
            if not (paper_dir / b).is_file():
                blocks.append(f"{fid}: 依据文件不存在: {b}")

    leads = paper.get("leads") or []
    lead_ids = set()
    if not leads:
        warns.append("leads 为空——还没有线索")
    for i, l in enumerate(leads):
        lid = l.get("id") or f"leads[{i}]"
        if not l.get("id"):
            blocks.append(f"leads[{i}] 缺少 id")
        if lid in lead_ids:
            blocks.append(f"线索 id 重复: {lid}")
        lead_ids.add(lid)
        if not l.get("title"):
            blocks.append(f"{lid}: 缺少 title")
        if not (l.get("evidence_needed") or []):
            blocks.append(f"{lid}: 缺少下一步证据（evidence_needed）")
        if not l.get("status"):
            warns.append(f"{lid}: 状态未填")
        for ref in (l.get("basis") or []):
            if ref not in fact_ids:
                blocks.append(f"{lid}: 依据 {ref} 不是已登记的事实 id")

    conclusion = paper.get("conclusion")
    if not isinstance(conclusion, dict):
        blocks.append("conclusion 必须是对象")
    elif not isinstance(conclusion.get("audit_conclusion"), bool):
        blocks.append("conclusion.audit_conclusion 必须是 true/false")

    return blocks, warns


def cmd_check(args):
    paper_dir = Path(args.dir)
    blocks, warns = check_paper(paper_dir)
    action = "block" if blocks else ("warn" if warns else "pass")
    if args.json:
        print(json.dumps({"action": action, "blocks": blocks, "warnings": warns},
                         ensure_ascii=False, indent=2))
    else:
        for b in blocks:
            print(f"[BLOCK] {b}")
        for w in warns:
            print(f"[WARN] {w}")
        print(f"action={action}（{len(blocks)} block / {len(warns)} warn）")
        print("SHEET:" + json.dumps({
            "tool": "explore-paper", "action": action,
            "message": f"探索底稿检查: 拦下 {len(blocks)}, 警告 {len(warns)}",
            "summary": {"total": 1, "passed": 1 if action == "pass" else 0,
                        "warned": 1 if action == "warn" else 0,
                        "blocked": 1 if action == "block" else 0},
            "details": [{"check": "explore-paper", "result": action,
                         "message": "; ".join(blocks + warns) or "通过"}],
            "crashed": False,
        }, ensure_ascii=False))
    return 2 if blocks else 0


def main():
    _reconfigure_stdout()
    parser = argparse.ArgumentParser(description="探索底稿工具：建骨架 / 自检")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="生成底稿骨架")
    p_new.add_argument("--id", required=True, help="底稿编号，如 EWP-2026-001")
    p_new.add_argument("--title", required=True)
    p_new.add_argument("--source", action="append", required=True, help="源文件路径，可多次")
    p_new.add_argument("--objective", action="append", help="审计目标，可多次")
    p_new.add_argument("--out", required=True, help="输出目录")
    p_new.add_argument("--force", action="store_true", help="允许覆盖已有底稿")
    p_new.set_defaults(fn=cmd_new)

    p_check = sub.add_parser("check", help="自检底稿")
    p_check.add_argument("dir", help="底稿目录")
    p_check.add_argument("--json", action="store_true")
    p_check.set_defaults(fn=cmd_check)

    args = parser.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        print("SHEET:" + json.dumps({
            "tool": "explore-paper", "action": "block",
            "message": "脚本崩溃，已转拦下",
            "summary": {"total": 0, "passed": 0, "warned": 0, "blocked": 1},
            "details": [], "crashed": True,
        }, ensure_ascii=False))
        traceback.print_exc()
        sys.exit(2)
