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

# 引用共享库
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '_shared' / 'scripts'))
from excel_core import ExcelCore


# ── 章节标题 → 轨道映射 ──────────────────────────────────

# 已废弃：旧格式 ## 三/四/五/六/七/八，写作时参考但不再维护
# 新版统一使用 <!-- track X --> 注释标记，降级路径见 _fallback_by_headings()


def load_config(config_path: str) -> Dict:
    """加载轨道配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _fallback_by_headings(content: str) -> Dict[str, str]:
    """降级路径：按 Markdown 章节标题划分轨道内容。

    匹配形如 `## 三、测试程序（轨道A：...）` 的标题行，
    切出标题到下一个同级 ## 标题之间的内容，映射到对应轨道。
    章节编号与轨道的对应关系：
      三 → A, 四 → B, 五 → C, 六 → E, 七 → F, 八 → D
    （注意：六=E、七=F —— 模板中六是效率、七是合规，八是边界）
    """
    SECTION_TO_TRACK = {
        '三': 'A', '四': 'B', '五': 'C',
        '六': 'E', '七': 'F', '八': 'D',
    }

    # 找所有 ## 开头但不是 ## 的标题行（即二级标题）
    headings = list(re.finditer(r'^##\s+(.+?)(?:\[.+?\])?\s*$', content, re.MULTILINE))
    result = {}

    for i, m in enumerate(headings):
        title = m.group(1).strip()
        # 提取中文数字编号（如"三、"）
        num_match = re.match(r'([一二三四五六七八九十]+)[、．.]', title)
        if not num_match:
            continue
        section_num = num_match.group(1)
        track_id = SECTION_TO_TRACK.get(section_num)
        if not track_id:
            continue

        # 切出本标题到下一个 ## 标题之间的内容
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        track_content = content[start:end].strip()
        if track_content:
            result[track_id] = track_content

    return result


def parse_markdown_sections(md_path: str) -> Dict[str, List[str]]:
    """
    解析 Markdown 文件，提取各轨道测试程序。

    两级策略（先精确后降级）：
    1. 优先用 <!-- track A --> ... <!-- end track A --> 注释标记
    2. 没有注释标记时，降级为按章节标题（## 三、测试程序（轨道A）…）切分
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


def parse_test_procedures(track_content: str) -> List[List]:
    """
    解析测试程序 Markdown 内容，转换为表格行

    支持格式：
    | 风险编号 | 风险名称 | 测试程序 | 取数来源 |
    |----------|----------|----------|----------|
    | CP-001   | ...      | ...      | ...      |
    """
    rows = []
    lines = track_content.split('\n')

    for line in lines:
        line = line.strip()
        # 跳过空行和表头
        if not line or line.startswith('| 序号') or line.startswith('|---|---'):
            continue

        # 解析 Markdown 表格行
        if line.startswith('|') and line.endswith('|'):
            parts = [p.strip() for p in line[1:-1].split('|')]
            if len(parts) >= 5:  # 序号、风险编号、风险名称、来源标注、测试程序
                # 补齐到配置的列数
                while len(parts) < 11:
                    parts.append('')
                rows.append(parts[:11])

    # 如果没有解析到数据，尝试按文本段落解析
    if not rows:
        paragraphs = [p.strip() for p in track_content.split('\n\n') if p.strip()]
        for idx, para in enumerate(paragraphs, 1):
            # 简单解析：假设每段是一个测试程序
            rows.append([str(idx), '', '', '', para, '', '', '', '', '', ''])

    return rows


def filter_activated_tracks(
    tracks_data: Dict[str, List],
    track_activation: Dict[str, bool],
    track_config: Dict
) -> List[Tuple[str, str, Dict, List]]:
    """
    筛选激活的轨道，返回 (轨道ID, Sheet名称, 配置, 数据) 列表
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
        data = tracks_data.get(track_key, [])

        if is_activated and data:
            track_cfg = track_config['tracks'].get(track_id, {})
            sheet_name = track_cfg.get('sheet_name', f'轨道{track_id}')
            result.append((track_id, sheet_name, track_cfg, data))
            activated_count += 1

    # 如果没有激活的轨道，返回提示
    if activated_count == 0:
        result.append((
            'NONE',
            '无数据',
            {'columns': [{'name': '提示', 'width': 80}],
             'default_row_height': 30},
            [['未找到任何激活轨道的审计程序数据。请检查 Markdown 格式。']]
        ))

    return result


def build_rows_for_track(data: List[List], track_cfg: Dict) -> List[List]:
    """
    标准化数据行，确保列数与配置一致
    """
    expected_cols = len(track_cfg.get('columns', []))
    rows = []

    for idx, row_data in enumerate(data, 1):
        # 插入序号
        if len(row_data) > 0 and row_data[0] != str(idx):
            row_data = [str(idx)] + row_data

        # 补齐或截断列数
        while len(row_data) < expected_cols:
            row_data.append('')
        rows.append(row_data[:expected_cols])

    return rows


def generate_audit_program_xlsx(
    markdown_path: str,
    output_xlsx: str,
    tracks: Optional[str] = None,
    config_path: Optional[str] = None
) -> str:
    """
    生成审计程序 Excel

    Args:
        markdown_path: Markdown 文件路径
        output_xlsx: 输出 Excel 路径
        tracks: 激活的轨道，如 "A,B,C,E"
        config_path: 配置文件路径

    Returns:
        输出文件路径
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
        # 只激活指定的轨道
        activated = set(tracks.upper().split(','))
        track_activation = {t: t in activated for t in track_activation}

    # 过滤激活轨道
    activated_tracks = filter_activated_tracks(tracks_data, track_activation, track_config)

    # 创建 Excel
    core = ExcelCore(output_xlsx)

    for track_id, sheet_name, cfg, data in activated_tracks:
        # 构建列配置
        cols = cfg.get('columns', [])
        headers = [c['name'] for c in cols]
        col_widths = [c['width'] for c in cols]
        default_height = cfg.get('default_row_height', 50)

        # 标准化数据行
        rows = build_rows_for_track(data, cfg)

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
