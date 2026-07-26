#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_evidence_dirs.py — 从审计程序 Markdown 自动创建证据目录和证据清单

[INPUT]:  审计程序 Markdown 文件 + current-audit.json（读取 project_name）
[OUTPUT]: evidence/{project_name}/ 目录树（含 _files/ 集中存储 + _evidence_catalog.json）
[POS]:    _shared/scripts 的工具脚本，被 program-generator SKILL.md Step 4 调用
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

解析审计程序的 Markdown 文档，提取所有程序的编号、名称和取证方式，
在 evidence/ 下创建完整目录结构和证据清单（catalog）。

v2.0 新增：
  - 集中存储目录 _files/（证据只放一份，多个程序共享）
  - 证据清单 _evidence_catalog.json（从"取证方式"列自动提取槽位）

用法：
    python create_evidence_dirs.py --program-md audit-programs/xxx.md
    python create_evidence_dirs.py --program-md audit-programs/xxx.md --workspace internal-audit-workspace/
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
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


def _find_risk_name(parts: list, code_idx: int, headers: list) -> str:
    """根据表头关键词匹配找到 risk name，带三级降级策略。

    优先匹配表头中含"风险名称"或"风险"（但不含"编号"）的列，
    降级到位置偏移，再降到相邻列，最终返回"未命名"。
    """
    # 策略 A：扫描表头找到含"风险名称"的列
    for i, hdr in enumerate(headers):
        if i < len(parts) and isinstance(hdr, str) and "风险名称" in hdr:
            val = parts[i]
            if val:
                return val

    # 策略 B：扫描表头找到以"风险"开头但不含"编号"的列
    for i, hdr in enumerate(headers):
        if i < len(parts) and isinstance(hdr, str) and hdr.startswith("风险") and "编号" not in hdr:
            val = parts[i]
            if val:
                return val

    # 策略 C：降级到位置偏移 code_idx - 2（历史兼容）
    if code_idx >= 2:
        val = parts[code_idx - 2]
        if val:
            return val

    # 策略 D：降级到相邻位置 code_idx + 1
    if code_idx + 1 < len(parts):
        val = parts[code_idx + 1]
        if val:
            return val

    return "未命名"


def _parse_table_rows(text: str) -> list:
    """从 Markdown 文本中提取程序编号和风险名称。

    v3.0：先提取表头行（分隔符前行），再用 _find_risk_name() 按表头关键词
    匹配 risk name 列，支持不同轨道（A/B/C/D/E/F）列结构差异。
    回退到位置偏移（code_idx - 2 → code_idx + 1 → "未命名"）。

    返回 [(编号, 风险名称), ...] 列表。
    """
    results = []
    code_pattern = re.compile(r'^([A-H]\d+(?:\.\d+)?)$')

    lines = text.strip().split('\n')
    seen = set()
    headers = []  # 当前表格的表头

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 跳过非表格行
        if not stripped.startswith('|') or not stripped.endswith('|'):
            continue

        parts = [p.strip() for p in stripped[1:-1].split('|')]

        # 跳过分隔行（全是 --- 或 :---），并提取前一行作为表头
        if all(re.match(r'^[-:]+$', p) or p == '' for p in parts):
            if i > 0:
                prev = lines[i - 1].strip()
                if prev.startswith('|') and prev.endswith('|'):
                    headers = [p.strip() for p in prev[1:-1].split('|')]
            continue

        # 数据行：扫描整行找程序编号列（不假设位置）
        code = None
        code_idx = -1
        for j, p in enumerate(parts):
            if code_pattern.match(p):
                code = p
                code_idx = j
                break

        if not code or code in seen:
            continue
        seen.add(code)

        risk_name = _find_risk_name(parts, code_idx, headers)
        results.append((code, risk_name))

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


# ── 证据目录清单生成 ───────────────────────────────────

def _normalize_evidence_name(raw: str) -> str:
    """标准化证据名称，用于去重比对。
    去掉括号注释、多余空格、统一顿号逗号。
    """
    cleaned = re.sub(r'[（(][^)）]*[)）]', '', raw)
    cleaned = re.sub(r'\s+', '', cleaned)
    cleaned = cleaned.replace('、', ',').replace('；', ',')
    return cleaned.strip(',')


def _parse_evidence_rows(section_text: str, track_id: str) -> list:
    """从单个轨道的 Markdown 表格中提取程序编号和取证方式。
    返回 [{code, track, items[]}, ...]
    """
    results = []
    code_pattern = re.compile(r'^([A-H]\d+(?:\.\d+)?)$')

    lines = section_text.strip().split('\n')
    evidence_col = -1
    code_col = -1
    headers = []
    seen = set()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith('|') or not stripped.endswith('|'):
            continue

        parts = [p.strip() for p in stripped[1:-1].split('|')]

        # 分隔行：提取前一行作为表头
        if all(re.match(r'^[-:]+$', p) or p == '' for p in parts):
            if i > 0:
                prev = lines[i - 1].strip()
                if prev.startswith('|') and prev.endswith('|'):
                    headers = [p.strip() for p in prev[1:-1].split('|')]
                    for j, h in enumerate(headers):
                        if h == '取证方式':
                            evidence_col = j
                        if h in ('程序编号', '编号'):
                            code_col = j
            continue

        if evidence_col < 0:
            continue

        # 找程序编号
        code = None
        if code_col >= 0 and code_col < len(parts):
            code = parts[code_col]
        if not code or not code_pattern.match(code):
            for j, p in enumerate(parts):
                if code_pattern.match(p):
                    code = p
                    break
        if not code or code in seen:
            continue
        seen.add(code)

        # 提取证据项
        if evidence_col < len(parts):
            raw = parts[evidence_col]
            items = [it.strip() for it in re.split(r'[、,;；\n]', raw) if it.strip()]
            results.append({
                'code': code,
                'track': track_id,
                'items': items,
            })

    return results


def _merge_evidence_slots(raw_slots: list) -> list:
    """合并同名证据：不同程序引用同一证据时合并到同一槽位。"""
    merged = {}
    for slot in raw_slots:
        for item in slot['items']:
            norm = _normalize_evidence_name(item)
            if not norm:
                continue
            if norm not in merged:
                merged[norm] = {
                    'name': item,
                    'tracks': set(),
                    'programs': [],
                }
            merged[norm]['tracks'].add(slot['track'])
            if slot['code'] not in merged[norm]['programs']:
                merged[norm]['programs'].append(slot['code'])

    result = []
    for i, (_, data) in enumerate(sorted(merged.items()), 1):
        result.append({
            'id': f'EVD-{i:03d}',
            'name': data['name'],
            'source_track': ','.join(sorted(data['tracks'])),
            'source_programs': sorted(data['programs']),
            'file': None,
            'collected_at': None,
        })
    return result


def _extract_evidence_slots_from_content(content: str) -> list:
    """从审计程序 Markdown 全文提取所有轨道的证据槽位。
    返回 [{code, track, items[]}, ...]
    """
    sections = {}
    for track_id in ('A', 'B', 'C', 'D', 'E', 'F'):
        pattern = rf'<!--\s*track\s+{track_id}\s*-->(.*?)<!--\s*end\s*track\s+{track_id}\s*-->'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            sections[track_id] = match.group(1).strip()

    if not sections:
        sections = _fallback_by_headings(content)

    all_slots = []
    for track_id in sorted(sections.keys()):
        all_slots.extend(_parse_evidence_rows(sections[track_id], track_id))
    return all_slots


def generate_evidence_catalog(md_path: str, evidence_root: Path,
                               project_name: str) -> dict:
    """从审计程序 Markdown 生成 evidence catalog JSON 文件。
    覆盖写入 evidence_root/_evidence_catalog.json。
    返回 catalog dict，无证据列时返回 None。
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    raw_slots = _extract_evidence_slots_from_content(content)
    if not raw_slots:
        return None

    merged = _merge_evidence_slots(raw_slots)
    now = datetime.now().strftime('%Y-%m-%d')

    catalog = {
        'project': project_name,
        'created_at': now,
        'updated_at': now,
        'total_slots': len(merged),
        'filled_slots': 0,
        'items': merged,
    }

    catalog_path = evidence_root / '_evidence_catalog.json'
    evidence_root.mkdir(parents=True, exist_ok=True)
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    return catalog


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
    """创建证据目录（含 _files/ 集中存储目录）。返回 {"created": N, "existed": M}"""
    # 集中存储目录
    files_dir = evidence_root / '_files'
    files_dir.mkdir(parents=True, exist_ok=True)

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
    evidence_root = ws / "evidence"

    programs = parse_programs_from_md(str(md_path))
    if not programs:
        print(f"⚠️  未从 {md_path.name} 中提取到任何审计程序")
        sys.exit(0)

    stats = create_evidence_dirs(programs, evidence_root)
    print(f"✅ 已创建 {stats['created']} 个证据目录（{stats['existed']} 个已存在）")
    print(f"   📁 {evidence_root}/")
    print(f"   📁 {evidence_root}/_files/  （集中存储，证据只放一份）")
    print(f"   📋 共 {len(programs)} 个程序 → {len(programs)} 个目录")

    # 生成证据清单
    catalog = generate_evidence_catalog(str(md_path), evidence_root, project_name)
    if catalog:
        print(f"   📋 证据清单: {catalog.get('total_slots', 0)} 个槽位")
        print(f"   📄 {evidence_root}/_evidence_catalog.json")
    else:
        print(f"   ⚠️  程序文件中未找到'取证方式'列，跳过证据清单生成")


if __name__ == "__main__":
    main()
