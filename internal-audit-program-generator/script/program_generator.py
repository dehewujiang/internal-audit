# -*- coding: utf-8 -*-
"""
审计程序生成器
==============
基于 Markdown 审计程序 + JSON 配置，生成多轨道审计程序表 Excel。

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


def find_project_root():
    """向上查找包含 _shared/scripts/ 的项目根目录"""
    p = Path(__file__).resolve().parent
    for _ in range(10):
        if (p / '_shared' / 'scripts').is_dir():
            return p
        p = p.parent
    raise FileNotFoundError("Cannot locate project root with _shared/scripts/")


sys.path.insert(0, str(find_project_root() / '_shared' / 'scripts'))
from excel_core import ExcelCore


def load_config(config_path: str) -> Dict:
    """加载轨道配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_track_tables(track_content: str) -> List[Tuple[List[str], List[List[str]]]]:
    """
    解析轨道内容中的所有 Markdown 表格，表头从 MD 表格中直接读取。

    识别逻辑：
    1. 扫描表格分隔行（|--- 模式，regex: ^\\|[\\:\\-\\s|]+\\|?\\s*$）
    2. 分隔行上面一行 = 表头
    3. 分隔行下面每一行 = 数据行，直到遇到空行 / ### 标题 / 下一个分隔行

    Returns:
        [(表头: [列名...], 数据行: [[值...]...]), ...]  每个表格一个元组
    """
    lines = track_content.split('\n')
    tables = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        # 检测表格分隔行，如 |---|:---:|---:|---|
        if re.match(r'^\|[:\-\s|]+\|?\s*$', line) and i > 0:
            # 上一行是表头
            header_line = lines[i - 1].strip()
            header = [h.strip() for h in header_line.strip('|').split('|')]

            # 收集数据行，直到终止条件
            data_rows = []
            j = i + 1
            while j < len(lines):
                data_line = lines[j].strip()
                if not data_line:
                    break
                if data_line.startswith('###'):
                    break
                if re.match(r'^\|[:\-\s|]+\|?\s*$', data_line):
                    break
                if data_line.startswith('|') and data_line.endswith('|'):
                    parts = [p.strip() for p in data_line[1:-1].split('|')]
                    data_rows.append(parts)
                j += 1

            if header and any(h for h in header):
                tables.append((header, data_rows))
            i = j
        else:
            i += 1

    return tables


def parse_markdown_sections(md_path: str) -> Dict[str, str]:
    """
    解析 Markdown 文件，提取各轨道原始内容。

    主路径：<!-- track X --> ... <!-- end track X -->
    回退路径：### 轨道 X 标题（仅在主路径未找到任何轨道时启用）
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tracks_data = {
        'control_tests': '',      # 轨道 A
        'fraud_tests': '',        # 轨道 B
        'system_tests': '',       # 轨道 C
        'boundary_tests': '',     # 轨道 D
        'efficiency_tests': '',   # 轨道 E
        'compliance_tests': '',   # 轨道 F
    }

    track_mapping = {
        'A': 'control_tests',
        'B': 'fraud_tests',
        'C': 'system_tests',
        'D': 'boundary_tests',
        'E': 'efficiency_tests',
        'F': 'compliance_tests',
    }

    # 主路径：按 <!-- track X --> ... <!-- end track X --> 提取
    for track_id, track_key in track_mapping.items():
        pattern = rf'<!--\s*track\s+{track_id}\s*-->(.*?)<!--\s*end\s*track\s+{track_id}\s*-->'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            tracks_data[track_key] = match.group(1).strip()

    # 回退路径：未找到任何 track 标记时，按 ### 轨道 X 标题拆分
    if not any(tracks_data.values()):
        for track_id, track_key in track_mapping.items():
            pattern = rf'###\s*轨道\s*{track_id}[^\n]*\n(.*?)(?=###\s*轨道\s*[A-F]|\Z)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                tracks_data[track_key] = match.group(1).strip()

    return tracks_data


def filter_activated_tracks(
    tracks_data: Dict[str, str],
    track_activation: Dict[str, bool],
    track_config: Dict
) -> List[Tuple[str, str, Dict, str]]:
    """
    筛选激活的轨道。

    Returns:
        [(轨道ID, Sheet名称, 轨道配置, 原始内容), ...]
    """
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
        content = tracks_data.get(track_key, '')

        if is_activated and content:
            track_cfg = track_config['tracks'].get(track_id, {})
            sheet_name = track_cfg.get('sheet_name', f'轨道{track_id}')
            result.append((track_id, sheet_name, track_cfg, content))
            activated_count += 1

    if activated_count == 0:
        result.append((
            'NONE',
            '无数据',
            {'default_row_height': 30},
            '未找到任何激活轨道的审计程序数据。请检查 Markdown 格式。'
        ))

    return result


def generate_audit_program_xlsx(
    markdown_path: str,
    output_xlsx: str,
    tracks: Optional[str] = None,
    config_path: Optional[str] = None
) -> str:
    """
    生成审计程序 Excel。
    列名从 Markdown 表格头部读取，config 仅用于样式（列宽、行高、Sheet 名）。

    Args:
        markdown_path: Markdown 文件路径
        output_xlsx: 输出 Excel 路径
        tracks: 激活的轨道，如 "A,B,C,E"
        config_path: 配置文件路径

    Returns:
        输出文件路径
    """
    # 加载配置（仅用于样式和轨道元信息）
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config' / 'program_templates.json'
    track_config = load_config(config_path)

    # 解析 Markdown → 各轨道原始内容
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

    for track_id, sheet_name, cfg, content in activated_tracks:
        if track_id == 'NONE':
            # 无数据提示
            ws_rows = [[content]]
            col_widths = [80]
            default_height = cfg.get('default_row_height', 30)
        else:
            # 解析轨道内容中的所有表格（列名来自 MD 表头）
            tables = parse_track_tables(content)

            # 串联所有表格：表头行 + 数据行 + 空行分隔
            ws_rows = []
            max_cols = 0
            for header, data_rows in tables:
                if not header:
                    continue
                ws_rows.append(header)
                max_cols = max(max_cols, len(header))
                for row in data_rows:
                    ws_rows.append(row)
                    max_cols = max(max_cols, len(row))
                ws_rows.append([])  # 表格间空行分隔

            # 移除末尾空白分隔行
            if ws_rows and not ws_rows[-1]:
                ws_rows.pop()

            # 列宽：从 JSON 配置读取，不足列补默认值 20
            col_widths_cfg = [c['width'] for c in cfg.get('columns', [])]
            while len(col_widths_cfg) < max_cols:
                col_widths_cfg.append(20)
            col_widths = col_widths_cfg[:max_cols] if max_cols else col_widths_cfg

            default_height = cfg.get('default_row_height', 50)

        # 创建 Sheet（表头已作为数据行写入，故传空列表）
        core.add_worksheet(
            title=sheet_name,
            headers=[],
            rows=ws_rows,
            col_widths=col_widths,
            default_height=default_height,
            freeze_header=True,
            alt_row_colors=True,
        )

    return core.save()


def main():
    parser = argparse.ArgumentParser(description='生成审计程序 Excel')
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
