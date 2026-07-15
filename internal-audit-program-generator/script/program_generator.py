# -*- coding: utf-8 -*-
"""
审计程序生成器 v2.0
==================
基于 Markdown 审计程序 + JSON 配置，生成多轨道审计程序表 Excel。

v2.0 变更：
- 按三层列结构（risk/design/execution）导出
- MD输出①②层，Excel输出全三层（③层留空现场填）
- 保留子表标题（### A1.xxx）作为Excel分隔行
- 识别非程序表（如效率损失估算表）并跳过
- 去除硬编码11列，按JSON动态读取列数

用法:
python internal-audit-program-generator/script/program_generator.py \
    ../audit-programs/存货管理审计程序.md \
    ../audit-programs/存货管理审计程序.xlsx \
    --tracks A,B,C,E
"""

import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 引用共享库
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '_shared' / 'scripts'))
from excel_core import ExcelCore


# ── 章节标题 → 轨道映射 ──────────────────────────────────

SECTION_TO_TRACK = {
    '三': 'A', '四': 'B', '五': 'C',
    '六': 'E', '七': 'F', '八': 'D',
}


def load_config(config_path: str) -> Dict:
    """加载轨道配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _fallback_by_headings(content: str) -> Dict[str, str]:
    """降级路径：按 Markdown 章节标题划分轨道内容。"""
    headings = list(re.finditer(r'^##\s+(.+?)(?:\[.+?\])?\s*$', content, re.MULTILINE))
    result = {}

    for i, m in enumerate(headings):
        title = m.group(1).strip()
        num_match = re.match(r'([一二三四五六七八九十]+)[、．.]', title)
        if not num_match:
            continue
        section_num = num_match.group(1)
        track_id = SECTION_TO_TRACK.get(section_num)
        if not track_id:
            continue

        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        track_content = content[start:end].strip()
        if track_content:
            result[track_id] = track_content

    return result


def parse_markdown_sections(md_path: str) -> Dict[str, list]:
    """
    解析 Markdown 文件，提取各轨道测试程序。

    两级策略（先精确后降级）：
    1. 优先用 <!-- track A --> ... <!-- end track A --> 注释标记
    2. 没有注释标记时，降级为按章节标题切分
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tracks_data = {
        'control_tests': [],      # 轨道 A
        'fraud_tests': [],        # 轨道 B
        'system_tests': [],       # 轨道 C
        'boundary_tests': [],     # 轨道 D
        'efficiency_tests': [],   # 轨道 E
        'compliance_tests': [],   # 轨道 F
    }

    track_mapping = {
        'A': 'control_tests',
        'B': 'fraud_tests',
        'C': 'system_tests',
        'D': 'boundary_tests',
        'E': 'efficiency_tests',
        'F': 'compliance_tests',
    }

    # 第一级：注释标记
    has_comments = False
    for track_id, track_key in track_mapping.items():
        pattern = rf'<!--\s*track\s+{track_id}\s*-->(.*?)<!--\s*end\s*track\s+{track_id}\s*-->'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            has_comments = True
            track_content = match.group(1).strip()
            tracks_data[track_key] = parse_test_procedures(track_content)

    if has_comments:
        return tracks_data

    # 第二级：降级到章节标题
    sections = _fallback_by_headings(content)
    if sections:
        for track_id, track_content in sections.items():
            track_key = track_mapping[track_id]
            tracks_data[track_key] = parse_test_procedures(track_content)

    return tracks_data


def parse_test_procedures(track_content: str) -> List[dict]:
    """
    v2.0：解析测试程序 Markdown 内容，返回结构化行列表。

    返回 [{"type": "subtitle", "text": "..."}, {"type": "data", "row": [...]}, ...]
    - subtitle: 子表标题（### A1.xxx），导出时作为Excel分隔行
    - data: 表格数据行（按实际列数，不补不截）
    - 非程序表（表头不含"程序编号"，如效率损失估算表）自动跳过
    """
    result = []
    lines = track_content.split('\n')
    ALIGN_SEP = re.compile(r'^\|[:\-\s]+\|')
    HEADER_MARKER = '程序编号'

    # 第一遍：标记表头行 + 识别非程序表范围
    header_indices = set()
    skip_ranges = []  # 非程序表的行范围 (start, end)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if ALIGN_SEP.match(stripped) and i > 0:
            prev = lines[i - 1].strip()
            if prev.startswith('|') and prev.endswith('|'):
                if HEADER_MARKER not in prev:
                    # 非程序表（如效率损失估算表），标记跳过范围
                    start = i - 1
                    end = i
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith('|'):
                            end = j
                        else:
                            break
                    skip_ranges.append((start, end))
                else:
                    # 程序表表头
                    if not re.match(r'^\|\s*[A-H]?\d+(?:\.\d+)?\s*\|', prev):
                        header_indices.add(i - 1)

    def in_skip_range(idx):
        return any(s <= idx <= e for s, e in skip_ranges)

    # 第二遍：提取子表标题和数据行
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or in_skip_range(i):
            continue

        # 子表标题（### A1.xxx）
        if stripped.startswith('###'):
            title_text = stripped.lstrip('#').strip()
            if title_text:
                result.append({"type": "subtitle", "text": title_text})
            continue

        if ALIGN_SEP.match(stripped) or i in header_indices:
            continue

        if stripped.startswith('|') and stripped.endswith('|'):
            parts = [p.strip() for p in stripped[1:-1].split('|')]
            if len(parts) >= 3:
                result.append({"type": "data", "row": parts})

    # 兜底：无数据行时尝试文本段落解析
    if not any(item["type"] == "data" for item in result):
        paragraphs = [p.strip() for p in track_content.split('\n\n') if p.strip()]
        for idx, para in enumerate(paragraphs, 1):
            result.append({"type": "data", "row": [str(idx), '', '', '', para, '', '', '']})

    return result


def filter_activated_tracks(
    tracks_data: Dict[str, list],
    track_activation: Dict[str, bool],
    track_config: Dict
) -> List[Tuple[str, str, Dict, list]]:
    """筛选激活的轨道，返回 (轨道ID, Sheet名称, 配置, 数据) 列表"""
    track_mapping = {
        'A': 'control_tests',
        'B': 'fraud_tests',
        'C': 'system_tests',
        'D': 'boundary_tests',
        'E': 'efficiency_tests',
        'F': 'compliance_tests',
    }

    result = []
    activated_count = 0

    for track_id, track_key in track_mapping.items():
        is_activated = track_activation.get(track_id, True)
        data = tracks_data.get(track_key, [])

        if is_activated and data:
            track_cfg = track_config['tracks'].get(track_id, {})
            sheet_name = track_cfg.get('sheet_name', f'轨道{track_id}')
            result.append((track_id, sheet_name, track_cfg, data))
            activated_count += 1

    if activated_count == 0:
        result.append((
            'NONE',
            '无数据',
            {'columns': [{'name': '提示', 'width': 80}],
             'default_row_height': 30},
            [{"type": "data", "row": ['未找到任何激活轨道的审计程序数据。请检查 Markdown 格式。']}]
        ))

    return result


def build_excel_rows(data: List[dict], track_cfg: Dict) -> List[List]:
    """
    v2.0：将解析结果转为 Excel 行（List[List]，兼容 excel_core）。

    - subtitle 行：第一列填标题文本，其余列空（作为视觉分隔）
    - data 行：取 risk+design 层列数据 + execution 层补空
    """
    all_cols = track_cfg.get('columns', [])
    expected_cols = len(all_cols)

    # 分离 execution 层和 risk+design 层
    risk_design_count = sum(1 for c in all_cols if c.get('layer') != 'execution')
    execution_count = sum(1 for c in all_cols if c.get('layer') == 'execution')

    result = []
    for item in data:
        if item["type"] == "subtitle":
            # 子表标题行：第一列填标题，其余空
            row = [item["text"]] + [''] * (expected_cols - 1)
            result.append(row)
        elif item["type"] == "data":
            # 数据行：取 risk+design 层列，补 execution 层空列
            row = item["row"][:risk_design_count]
            while len(row) < risk_design_count:
                row.append('')
            row.extend([''] * execution_count)
            result.append(row[:expected_cols])

    return result


def generate_audit_program_xlsx(
    markdown_path: str,
    output_xlsx: str,
    tracks: Optional[str] = None,
    config_path: Optional[str] = None
) -> str:
    """
    生成审计程序 Excel（v2.0 三层列结构）

    MD输出①②层（risk+design），Excel输出全三层（risk+design+execution，③层留空）
    """
    # 加载配置
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config' / 'program_templates.json'
    track_config = load_config(config_path)

    # 解析 Markdown
    tracks_data = parse_markdown_sections(markdown_path)

    # 设置激活状态
    track_activation = {t: True for t in track_config['tracks'].keys()}
    if tracks:
        activated = set(tracks.upper().split(','))
        track_activation = {t: t in activated for t in track_activation}

    # 过滤激活轨道
    activated_tracks = filter_activated_tracks(tracks_data, track_activation, track_config)

    # 创建 Excel
    core = ExcelCore(output_xlsx)

    for track_id, sheet_name, cfg, data in activated_tracks:
        # 构建列配置（全三层：risk+design+execution）
        cols = cfg.get('columns', [])
        headers = [c['name'] for c in cols]
        col_widths = [c['width'] for c in cols]
        default_height = cfg.get('default_row_height', 50)

        # 构建数据行（含子表标题分隔 + execution层空列）
        rows = build_excel_rows(data, cfg)

        # 创建 Sheet
        core.add_worksheet(
            title=sheet_name,
            headers=headers,
            rows=rows,
            col_widths=col_widths,
            default_height=default_height,
            freeze_header=True,
            alt_row_colors=True,
        )

    # 保存
    return core.save()


def main():
    parser = argparse.ArgumentParser(description='生成审计程序 Excel（v2.0 三层列结构）')
    parser.add_argument('markdown', help='输入 Markdown 文件')
    parser.add_argument('output', help='输出 Excel 文件')
    parser.add_argument('--tracks', '-t', help='激活的轨道，如 "A,B,C"')
    parser.add_argument('--config', '-c', help='配置文件路径')

    args = parser.parse_args()

    output_path = generate_audit_program_xlsx(
        args.markdown,
        args.output,
        tracks=args.tracks,
        config_path=args.config
    )

    print(f'已生成：{output_path}')


if __name__ == '__main__':
    main()
