#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
program_ir_parser.py — 审计程序 Markdown → ProgramIR 结构化中间表示解析器

把审计程序 Markdown 解析成结构化 ProgramIR JSON，供 validate-program.py --ir 做
确定性校验（覆盖度/判定标准量化/数据来源比例），并替代此前由 LLM 手写的
program_index.json（ProgramIR 是其超集，steps[] 字段名严格兼容）。

设计要点：
- 复用 program_generator.SECTION_TO_TRACK（非字母序：六→E 七→F 八→D），避免两套映射漂移
- header-aware 表格解析：按 MD 表头实际列名映射命名字段，不依赖固定列序
- 风险编号归一化：R01 / R-001 / R1 → R-1（LLM 继续输出 R01，AI 零感知）
- 增量章节十/十一（S 编号）在 <!-- track --> 之外，单独扫描并计入覆盖度
- -C 勘误后缀识别：A7.2-C 标记 is_errata，corrects=A7.2，覆盖度不重复计数

[INPUT]:  审计程序 Markdown 文件路径
[OUTPUT]: ProgramIR JSON（--out 写文件，否则 stdout）+ 退出码 0/1
[POS]:    _shared/scripts 的程序结构化工具，被 validate-program.py --ir 与
          internal-audit-program-generator/SKILL.md Step 4.X+2 引用
"""

import sys
import json
import re
import argparse
from pathlib import Path
from datetime import date

# 复用 program_generator 的章节→轨道映射（非字母序），避免漂移
_PG_DIR = Path(__file__).parent.parent.parent / 'internal-audit-program-generator'
sys.path.insert(0, str(_PG_DIR / 'script'))
try:
    from program_generator import SECTION_TO_TRACK  # noqa: F401
except Exception:  # 兜底：万一 program_generator 不可 import，退化为本文件内置映射
    SECTION_TO_TRACK = {'三': 'A', '四': 'B', '五': 'C', '六': 'E', '七': 'F', '八': 'D'}

CONFIG_PATH = _PG_DIR / 'config' / 'program_templates.json'

ALIGN_SEP_RE = re.compile(r'^\|[:\-\s|]+\|?\s*$')


# ── 编号归一化 ──────────────────────────────────────────

RISK_ID_RE = re.compile(r'^R[K]?[-]?(\d+)$', re.IGNORECASE)


def normalize_risk_id(raw):
    """R01 / R-001 / R1 / r01 → R-1。无法识别的返回原值大写。"""
    if not raw:
        return ''
    raw = raw.strip()
    m = RISK_ID_RE.match(raw)
    if m:
        return f"R-{int(m.group(1))}"
    return raw.upper()


def parse_risk_ids(cell):
    """风险编号列可能多值（R01/R03），split 后归一化去重。"""
    if not cell:
        return []
    parts = re.split(r'[/／,，、\s]+', cell.strip())
    ids = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        nid = normalize_risk_id(p)
        if nid and nid not in ids:
            ids.append(nid)
    return ids


ANCHOR_RE = re.compile(r'\b(?:CP|CG|RP|CF|D)-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', re.IGNORECASE)


def extract_anchors(cell):
    """从来源标注列提取 CP-/CG-/RP-/CF-/D- 编号。"""
    if not cell:
        return []
    return list(dict.fromkeys(m.group(0).upper() for m in ANCHOR_RE.finditer(cell)))


def parse_step_id(raw):
    """识别 -C 勘误后缀。返回 (step_id, is_errata, corrects)。"""
    if not raw:
        return '', False, ''
    raw = raw.strip()
    m = re.match(r'^(.*?)-C$', raw, re.IGNORECASE)
    if m:
        base = m.group(1).strip()
        return raw, True, base
    return raw, False, ''


# ── 通用 Markdown 表格解析 ──────────────────────────────

def parse_md_tables(content):
    """解析内容块内所有 Markdown 表格。

    返回 [{"header": [列名...], "rows": [[单元格...], ...]}, ...]
    只返回有表头 + 对齐分隔行的合法表格。
    """
    tables = []
    lines = content.split('\n')
    i = 0
    while i < len(lines) - 1:
        line = lines[i].strip()
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
        if line.startswith('|') and ALIGN_SEP_RE.match(next_line):
            header = [c.strip() for c in line.strip('|').split('|')]
            rows = []
            j = i + 2
            while j < len(lines):
                r = lines[j].strip()
                if not r.startswith('|'):
                    break
                cells = [c.strip() for c in r.strip('|').split('|')]
                rows.append(cells)
                j += 1
            tables.append({"header": header, "rows": rows})
            i = j
        else:
            i += 1
    return tables


def _is_program_table(header):
    """程序表判定：表头含'程序编号'或'补充编号'（排除效率损失估算表等）。"""
    joined = ''.join(header)
    return '程序编号' in joined or '补充编号' in joined


def _is_risk_register_table(header):
    """风险清单表判定：表头含'风险编号'且含'风险描述'（程序表有风险编号但无风险描述）。"""
    joined = ''.join(header)
    return '风险编号' in joined and '风险描述' in joined


# ── 章节切分 ────────────────────────────────────────────

def split_track_sections(content):
    """返回 {track_id: 该轨道内容}。

    两级策略：优先 <!-- track X --> 注释；无则按 SECTION_TO_TRACK 章节标题切分。
    """
    sections = {}
    has_comments = False
    for track_id in ['A', 'B', 'C', 'D', 'E', 'F']:
        pat = rf'<!--\s*track\s+{track_id}\s*-->(.*?)<!--\s*end\s*track\s+{track_id}\s*-->'
        m = re.search(pat, content, re.DOTALL | re.IGNORECASE)
        if m:
            has_comments = True
            sections[track_id] = m.group(1).strip()

    if has_comments:
        return sections

    # 降级：按 ## 章节标题 + SECTION_TO_TRACK
    headings = list(re.finditer(r'^##\s+(.+?)(?:\[.+?\])?\s*$', content, re.MULTILINE))
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
        block = content[start:end].strip()
        if block:
            sections[track_id] = block
    return sections


def extract_chapter(content, chapter_num):
    """提取 `## 十、...` 等章节正文（到下一个 ## 结束）。chapter_num 为中文数字。"""
    pat = rf'^##\s*{chapter_num}[、．.][^\n]*\n(.*?)(?=^##\s|\Z)'
    m = re.search(pat, content, re.DOTALL | re.MULTILINE)
    return m.group(1).strip() if m else ''


def find_risk_register_section(content):
    """风险识别清单可能在 2.1 或 2.2（文档不一致），按 ### 标题关键词定位。"""
    pat = r'^###\s*[0-9.]*\s*风险识别清单[^\n]*\n(.*?)(?=^###\s|\Z)'
    m = re.search(pat, content, re.DOTALL | re.MULTILINE)
    return m.group(1).strip() if m else ''


# ── 字段映射 ────────────────────────────────────────────

def _cell_at(row, idx):
    return row[idx] if 0 <= idx < len(row) else ''


def _find_col(header, *keywords):
    """在表头里找含任一关键词的列下标，找不到返回 -1。"""
    for i, name in enumerate(header):
        for kw in keywords:
            if kw in name:
                return i
    return -1


def map_row_to_step(header, row, track_id):
    """把一行单元格映射成结构化 step 字典。"""
    c_risk = _find_col(header, '风险编号')
    c_title = _find_col(header, '风险名称')
    c_src = _find_col(header, '来源标注')
    c_step = _find_col(header, '程序编号', '补充编号')
    c_proc = _find_col(header, '测试程序')
    c_sample = _find_col(header, '抽样方法')
    c_data = _find_col(header, '取证方式')
    c_crit = _find_col(header, '判定标准')
    c_bound = _find_col(header, '为什么这家公司更需要关注')
    c_clue = _find_col(header, '线索依据', '举报线索摘要')

    raw_risk_cell = _cell_at(row, c_risk)
    risk_refs = parse_risk_ids(raw_risk_cell)
    source_tag = _cell_at(row, c_src)
    anchors = extract_anchors(source_tag)
    related_controls = [a for a in anchors if a.startswith(('CP-', 'CG-'))]
    related_design_obs = [a for a in anchors if a.startswith('D-')]

    raw_step = _cell_at(row, c_step)
    step_id, is_errata, corrects = parse_step_id(raw_step)

    procedure = _cell_at(row, c_proc).replace('<br>', '\n').replace('<br/>', '\n').strip()

    return {
        "step_id": step_id,
        "track": track_id,
        "risk_ref": risk_refs[0] if risk_refs else "",   # 兼容现有单值字段
        "risk_refs": risk_refs,                            # 数组，覆盖度用
        "raw_risk_ids": [raw_risk_cell.strip()] if raw_risk_cell.strip() else [],
        "title": _cell_at(row, c_title),
        "source_tag": source_tag,
        "related_controls": related_controls,
        "related_design_observations": related_design_obs,
        "procedure": procedure,
        "sampling": _cell_at(row, c_sample),
        "data_source": _cell_at(row, c_data),
        "tool": "",                                        # 工具明确性留 LLM 判断
        "criterion": _cell_at(row, c_crit),
        "test_method": _test_method_of(track_id),
        "boundary_reason": _cell_at(row, c_bound),
        "clue_basis": _cell_at(row, c_clue),
        "is_errata": is_errata,
        "corrects": corrects,
    }


def _test_method_of(track_id):
    return {
        'A': '控制有效性测试',
        'B': '舞弊实质性测试',
        'C': '系统/公司类实质性测试',
        'D': '边界探测',
        'E': '运营效率专项',
        'F': '合规专项',
        'S': '增量补充测试',
    }.get(track_id, '')


def map_row_to_risk(header, row):
    """风险清单表一行 → risk_register 条目。"""
    c_id = _find_col(header, '风险编号')
    c_name = _find_col(header, '风险名称')
    c_desc = _find_col(header, '风险描述')
    c_src = _find_col(header, '来源标注')
    raw_id = _cell_at(row, c_id)
    source_tag = _cell_at(row, c_src)
    # 类型从来源标注的【...】标签提取
    type_m = re.search(r'【([^】]+?)】', source_tag)
    rtype = type_m.group(1).strip() if type_m else ''
    return {
        "risk_id": normalize_risk_id(raw_id),
        "raw_id": raw_id.strip(),
        "type": rtype,
        "title": _cell_at(row, c_name),
        "desc": _cell_at(row, c_desc),
        "source_tag": source_tag,
        "fact_anchors": extract_anchors(source_tag),
    }


# ── 元信息提取 ──────────────────────────────────────────

def extract_audit_topic(content):
    m = re.search(r'^#\s*(.+?)审计程序', content, re.MULTILINE)
    return m.group(1).strip() if m else ''


def extract_program_version(md_path):
    m = re.search(r'_v([\d.]+)\.md$', md_path.name)
    return f"v{m.group(1)}" if m else 'v1.0'


def parse_decision_log(content):
    """best-effort 从第十章提取 D-003/D-004/D-005 的 result/rationale。"""
    chapter = extract_chapter(content, '十')
    # 第十章可能是"审计程序决策理由"或"数据来源"——按 D-00X 标题定位
    if 'D-00' not in chapter:
        # 退而在全文找
        chapter = content
    dl = {}
    for did in ['D-003', 'D-004', 'D-005']:
        pat = rf'###\s*{did}[^\n]*\n(.*?)(?=\n###\s*D-\d|\n##\s|\Z)'
        m = re.search(pat, chapter, re.DOTALL)
        if not m:
            continue
        block = m.group(1)
        entry = {}
        r = re.search(r'决策结果[：:]\s*(.+)', block)
        if r:
            entry['result'] = r.group(1).strip()
        r = re.search(r'(?:选择理由|范围边界理由|激活理由|理由)[：:]\s*(.+)', block)
        if r:
            entry['rationale'] = r.group(1).strip()
        if entry:
            dl[did] = entry
    return dl


# ── 主编排 ──────────────────────────────────────────────

def build_ir(md_path):
    """解析审计程序 MD，返回 ProgramIR dict。"""
    md_path = Path(md_path)
    content = md_path.read_text(encoding='utf-8')

    # 风险清单
    risk_register = []
    rr_section = find_risk_register_section(content)
    if rr_section:
        for tbl in parse_md_tables(rr_section):
            if _is_risk_register_table(tbl['header']):
                for row in tbl['rows']:
                    if len(row) >= 3 and any(c.strip() for c in row):
                        risk_register.append(map_row_to_risk(tbl['header'], row))
                break
    # 去重（按 risk_id）
    seen = set()
    deduped = []
    for r in risk_register:
        if r['risk_id'] and r['risk_id'] not in seen:
            seen.add(r['risk_id'])
            deduped.append(r)
    risk_register = deduped

    # 各轨道程序步骤
    steps = []
    track_sections = split_track_sections(content)
    activated_tracks = []
    for track_id in ['A', 'B', 'C', 'D', 'E', 'F']:
        block = track_sections.get(track_id, '')
        if not block:
            continue
        for tbl in parse_md_tables(block):
            if not _is_program_table(tbl['header']):
                continue
            for row in tbl['rows']:
                if len(row) < 3 or not any(c.strip() for c in row):
                    continue
                step = map_row_to_step(tbl['header'], row, track_id)
                if step['step_id']:
                    steps.append(step)
                    if track_id not in activated_tracks:
                        activated_tracks.append(track_id)

    # 增量章节十/十一（S 编号，在 track 注释外）
    for chapter_num in ['十', '十一']:
        block = extract_chapter(content, chapter_num)
        if not block:
            continue
        for tbl in parse_md_tables(block):
            if not _is_program_table(tbl['header']):
                continue
            for row in tbl['rows']:
                if len(row) < 3 or not any(c.strip() for c in row):
                    continue
                step = map_row_to_step(tbl['header'], row, 'S')
                if step['step_id']:
                    steps.append(step)
        if 'S' not in activated_tracks and any(s['track'] == 'S' for s in steps):
            activated_tracks.append('S')

    # 覆盖度（校验器计算，但解析器也填一份方便直接用）
    register_ids = {r['risk_id'] for r in risk_register if r['risk_id']}
    covered = set()
    for s in steps:
        covered.update(s['risk_refs'])
    uncovered = register_ids - covered
    coverage_rate = (len(register_ids - uncovered) / len(register_ids)) if register_ids else 1.0

    ir = {
        "schema_version": "2.0.0",
        "audit_topic": extract_audit_topic(content),
        "generated_date": date.today().isoformat(),
        "program_version": extract_program_version(md_path),
        "program_md_file": md_path.name,
        "audit_purpose": [],
        "trigger_reason": "",
        "activated_tracks": activated_tracks,
        "decision_log": parse_decision_log(content),
        "risk_register": risk_register,
        "steps": steps,
        "coverage": {
            "covered_risks": sorted(covered),
            "uncovered_risks": [{"risk_id": rid, "reason": ""} for rid in sorted(uncovered)],
            "coverage_rate": round(coverage_rate, 4),
        },
        "stats": {
            "risk_count": len(risk_register),
            "step_count": len(steps),
            "tracks_with_steps": activated_tracks,
        },
    }
    return ir


# ── CLI ─────────────────────────────────────────────────

def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description='审计程序 MD → ProgramIR 结构化解析器')
    parser.add_argument('md_path', help='审计程序 Markdown 文件路径')
    parser.add_argument('--out', '-o', help='输出 JSON 文件路径（默认 stdout）', default='')
    args = parser.parse_args()

    md_path = Path(args.md_path)
    if not md_path.is_file():
        print(f"[ERROR] 文件不存在: {args.md_path}", file=sys.stderr)
        sys.exit(2)

    try:
        ir = build_ir(md_path)
    except Exception as e:
        print(f"[ERROR] 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    out = json.dumps(ir, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(out, encoding='utf-8')
        print(f"已生成: {args.out}（风险 {ir['stats']['risk_count']} 个，"
              f"步骤 {ir['stats']['step_count']} 个，"
              f"覆盖率 {ir['coverage']['coverage_rate']*100:.0f}%）")
    else:
        print(out)


if __name__ == '__main__':
    main()
