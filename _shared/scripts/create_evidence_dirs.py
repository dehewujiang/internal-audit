#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_evidence_dirs.py — 从审计程序 Markdown 自动创建证据存放目录

解析审计程序的 Markdown 文档，提取所有程序的编号和名称，
在 evidence/ 下预先创建 `{project_name}/{程序编号}_{程序关键词}/` 目录结构，
免去审计员手动建 65 个文件夹的麻烦。

[INPUT]:  审计程序 Markdown 文件 + current-audit.json（读取 project_name）
[OUTPUT]: evidence/{project_name}/{编号}_{关键词}/ 目录树，打印创建统计
[POS]:    _shared/scripts 的工具脚本，被 program-generator SKILL.md Step 4 调用

用法：
    python create_evidence_dirs.py --program-md audit-programs/xxx.md
    python create_evidence_dirs.py --program-md audit-programs/xxx.md --workspace internal-audit-workspace/
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ── 安全文件名 ──────────────────────────────────────────

def safe_dirname(raw: str, max_len: int = 50) -> str:
    """将程序描述转为安全的目录名：去非法字符、去首尾空白、截断。"""
    # Windows 非法字符: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/:*?"<>|]', '', raw)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip()
    return cleaned


# ── 标��解析 ──────────────────────────────────────────

def _extract_title(description: str) -> str:
    """从程序描述中提纯标题。
    优先取 `——` 前面的部分，其次取 `——` 后面到描述结尾的部分，
    最后兜底取前 30 字。
    """
    desc = description.strip()
    if not desc:
        return "未命名程序"
    if '——' in desc:
        before = desc.split('——')[0].strip()
        if before and len(before) >= 2:
            return before
    # 兜底：取前 30 字
    return desc[:30].rstrip()


def _parse_table_rows(text: str) -> list:
    """从 Markdown 文本中提取符合 `| 编号 | 描述 | ...` 格式的表格行。
    返回 [(编号, 标题), ...] 列表。
    """
    results = []
    # 匹配以程序编号开头的表格行（A-H + 数字，或纯数字编号）
    pattern = re.compile(
        r'^\|\s*([A-H]?\d+(?:\.\d+)?)\s*\|\s*(.+?)\s*\|',
        re.MULTILINE
    )
    seen = set()
    for m in pattern.finditer(text):
        code = m.group(1).strip()
        desc = m.group(2).strip()
        # 跳过表头行（编号列是 --- 或 序号 等）
        if re.match(r'^[-:]+$', code) or code in ('序号', '编号'):
            continue
        if code in seen:
            continue
        seen.add(code)
        title = _extract_title(desc)
        results.append((code, title))
    return results


# ── 两级降级解析（复用 program_generator.py 的逻辑） ─────

def _fallback_by_headings(content: str) -> dict:
    """降级路径：按 Markdown 章节标题划分各轨道内容。
    章节编号与轨道的对应关系：三→A, 四→B, 五→C, 六→E, 七→F, 八→D
    """
    SECTION_TO_TRACK = {
        '三': 'A', '四': 'B', '五': 'C',
        '六': 'E', '七': 'F', '八': 'D',
    }
    headings = list(re.finditer(r'^##\s+(.+?)(?:\[.+?\])?\s*$', content, re.MULTILINE))
    result = {}
    for i, m in enumerate(headings):
        title = m.group(1).strip()
        num_match = re.match(r'([一二三四五六七八九十]+)[、．.]', title)
        if not num_match:
            continue
        track_id = SECTION_TO_TRACK.get(num_match.group(1))
        if not track_id:
            continue
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        result[track_id] = content[start:end].strip()
    return result


def parse_programs_from_md(md_path: str) -> list:
    """从 Markdown 文件中提取所有程序的 (编号, 标题) 列表。

    两级策略：
    1. 优先解析 <!-- track X --> 注释标记内的表格
    2. 降级为按章节标题切分后解析表格
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 第一级：注释标记
    sections = {}
    for track_id in ('A', 'B', 'C', 'D', 'E', 'F'):
        pattern = rf'<!--\s*track\s+{track_id}\s*-->(.*?)<!--\s*end\s*track\s+{track_id}\s*-->'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            sections[track_id] = match.group(1).strip()

    if sections:
        all_programs = []
        for track_id in sorted(sections.keys()):
            all_programs.extend(_parse_table_rows(sections[track_id]))
        return all_programs

    # 第二级：章节标题降级
    sections = _fallback_by_headings(content)
    if sections:
        all_programs = []
        for track_id in sorted(sections.keys()):
            all_programs.extend(_parse_table_rows(sections[track_id]))
        return all_programs

    return []


# ── 目录创建 ──────────────────────────────────────────

def load_project_name(workspace: Path) -> str:
    """从 current-audit.json 读取 project_name"""
    audit_json = workspace / "current-audit.json"
    if audit_json.exists():
        try:
            with open(audit_json, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            return data.get("project_name", "")
        except Exception:
            pass
    # 兜底：用 workspace 父目录名
    return workspace.parent.name


def create_evidence_dirs(programs: list, evidence_root: Path) -> dict:
    """创建证据目录。返回 {"created": N, "existed": M}"""
    created = 0
    existed = 0
    for code, title in programs:
        dirname = f"{code}_{safe_dirname(title)}"
        target = evidence_root / dirname
        if target.exists():
            existed += 1
        else:
            target.mkdir(parents=True)
            created += 1
    return {"created": created, "existed": existed}


# ── CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="从审计程序 Markdown 自动创建证据目录")
    parser.add_argument(
        "--program-md", required=True, type=str,
        help="审计程序 Markdown 文件路径"
    )
    parser.add_argument(
        "--workspace", type=str, default=None,
        help="workspace 目录路径（默认：从 --program-md 所在目录推断）"
    )
    args = parser.parse_args()

    md_path = Path(args.program_md)
    if not md_path.exists():
        print(f"[ERROR] 文件不存在: {md_path}", file=sys.stderr)
        sys.exit(1)

    # 推断 workspace
    if args.workspace:
        ws = Path(args.workspace)
    else:
        # program-md 通常在 internal-audit-workspace/audit-programs/xxx.md
        md_parent = md_path.resolve().parent
        if md_parent.name == "audit-programs":
            ws = md_parent.parent  # 往上一级 = internal-audit-workspace/
        else:
            ws = md_parent  # 兜底

    project_name = load_project_name(ws)
    evidence_root = ws / "evidence" / safe_dirname(project_name, max_len=80)

    programs = parse_programs_from_md(str(md_path))
    if not programs:
        print(f"⚠️  未从 {md_path.name} 中提取到任何审计程序")
        sys.exit(0)

    stats = create_evidence_dirs(programs, evidence_root)
    print(f"✅ 已创建 {stats['created']} 个证据目录（{stats['existed']} 个已存在）")
    print(f"   📁 {evidence_root}/")
    print(f"   📋 共 {len(programs)} 个程序 → {len(programs)} 个目录")


if __name__ == "__main__":
    main()
