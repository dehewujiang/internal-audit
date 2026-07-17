# -*- coding: utf-8 -*-
"""
审计报告生成器
==============
基于 findings JSON + 报告模板配置，生成审计报告 Excel。

用法:
python internal-audit-report-generator/script/report_generator.py \
    internal-audit-workspace/findings/存货管理_findings.json \
    internal-audit-workspace/reports/存货管理_审计报告.xlsx \
    [--template summary|full]

"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# 引用共享库
def find_project_root():
    p = Path(__file__).resolve().parent
    for _ in range(10):
        if (p / '_shared' / 'scripts').is_dir():
            return p
        p = p.parent
    raise FileNotFoundError("Cannot locate project root with _shared/scripts/")

sys.path.insert(0, str(find_project_root() / '_shared' / 'scripts'))
from excel_core import ExcelCore
from audit_styles import FILLS, COLORS
from openpyxl.styles import Font, PatternFill


def load_config(config_dir: Path) -> Dict:
    """加载报告模板配置"""
    with open(config_dir / 'report_templates.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_findings(input_path: str) -> Tuple[List[Dict], Dict]:
    """解析 findings JSON 文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    findings = data.get('findings', [])
    summary = {
        'total': len(findings),
        'high': sum(1 for f in findings if f.get('severity') == '高' or f.get('风险等级') == '高'),
        'medium': sum(1 for f in findings if f.get('severity') == '中' or f.get('风险等级') == '中'),
        'low': sum(1 for f in findings if f.get('severity') == '低' or f.get('风险等级') == '低'),
        'audit_topic': data.get('audit_topic', '未知主题'),
        'report_date': datetime.now().strftime('%Y-%m-%d')
    }

    return findings, summary


def format_currency(value) -> str:
    """格式化金额"""
    try:
        num = float(value)
        return f"{num:,.2f}"
    except:
        return str(value)


def render_finding_row(finding: Dict, index: int) -> List:
    """将单个 finding 转换为行数据"""
    return [
        index,
        finding.get('id', finding.get('finding_id', '')),
        finding.get('category', finding.get('模块', '未分类')),
        finding.get('description', finding.get('发现描述', '')),
        finding.get('severity', finding.get('风险等级', '中')),
        format_currency(finding.get('amount', finding.get('影响金额', 0))),
        finding.get('reference', finding.get('审计依据', '')),
        finding.get('recommendation', finding.get('整改建议', '')),
        finding.get('responsible', finding.get('整改责任人', '')),
        finding.get('deadline', finding.get('整改期限', '')),
        finding.get('progress', finding.get('整改进度', '未开始')),
        finding.get('notes', finding.get('备注', ''))
    ]


def calculate_score_card(findings: List[Dict], config: Dict) -> List[List]:
    """计算评分卡"""
    dimensions = config.get('sheets', {}).get('score_card', {}).get('dimensions', [])
    rows = []

    # 按维度统计
    dimension_scores = {}
    for dim in dimensions:
        dim_findings = [f for f in findings if dim in f.get('category', '')]
        high_count = sum(1 for f in dim_findings if f.get('severity') == '高')
        medium_count = sum(1 for f in dim_findings if f.get('severity') == '中')

        # 扣分逻辑：高=-3分，中=-1.5分
        penalty = high_count * 3 + medium_count * 1.5
        score = max(0, 10 - penalty)

        dimension_scores[dim] = {
            'score': score,
            'evidence': f"发现{len(dim_findings)}项问题（高{high_count}项，中{medium_count}项）" if dim_findings else "未发现问题",
            'improvement': "需建立/完善控制" if high_count > 0 else "保持监控"
        }

    weights = [20, 15, 15, 15, 10, 10, 10, 5]  # 默认权重

    for idx, dim in enumerate(dimensions):
        s = dimension_scores.get(dim, {'score': 10, 'evidence': '未评估', 'improvement': 'N/A'})
        weight = weights[idx] if idx < len(weights) else 10
        rows.append([
            dim,
            weight,
            s['score'],
            round(s['score'] * weight / 100, 2),
            s['evidence'],
            s['improvement']
        ])

    return rows


def generate_report_xlsx(
    input_json: str,
    output_xlsx: str,
    config_dir: Optional[str] = None,
    template_type: str = 'full'
) -> str:
    """生成审计报告 Excel"""

    cfg_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / 'config'
    templates = load_config(cfg_dir)
    findings, summary = parse_findings(input_json)

    print(f"载入 {summary['total']} 个发现，高/中/低: {summary['high']}/{summary['medium']}/{summary['low']}")

    core = ExcelCore(output_xlsx)

    # Sheet 1: 发现汇总
    if template_type in ['full', 'summary']:
        cfg = templates.get('sheets', {}).get('findings_summary', {})
        headers = [c['name'] for c in cfg.get('columns', [])]
        col_widths = [c['width'] for c in cfg.get('columns', [])]

        rows = [render_finding_row(f, i+1) for i, f in enumerate(findings)]

        ws = core.add_worksheet(
            title=cfg.get('name', '审计发现汇总'),
            headers=headers,
            rows=rows,
            col_widths=col_widths,
            default_height=50,
            freeze_header=True,
            alt_row_colors=True,
        )

        # 应用风险等级条件格式
        severity_col = 5  # 假设风险等级在第5列
        for row_idx, row_data in enumerate(rows, 2):
            severity = str(row_data[4] if len(row_data) > 4 else '')
            if '高' in severity:
                for col_idx in range(1, len(headers)+1):
                    ws.cell(row=row_idx, column=col_idx).fill = FILLS.warning

    # Sheet 2: 审计评分
    if template_type in ['full']:
        cfg = templates.get('sheets', {}).get('score_card', {})
        headers = [c['name'] for c in cfg.get('columns', [])]
        col_widths = [c['width'] for c in cfg.get('columns', [])]

        score_data = calculate_score_card(findings, templates)

        core.add_worksheet(
            title=cfg.get('name', '审计评分表'),
            headers=headers,
            rows=score_data,
            col_widths=col_widths,
            default_height=40,
            freeze_header=True,
            alt_row_colors=True,
        )

    # Sheet 3: 管理层反馈模板
    cfg_resp = templates.get('sheets', {}).get('management_response', {})
    headers_resp = [c['name'] for c in cfg_resp.get('columns', [])]
    col_widths_resp = [c['width'] for c in cfg_resp.get('columns', [])]

    # 预填充发现编号
    response_data = [[f.get('id', f.get('finding_id', '')), '', '', '', '', ''] for f in findings]

    core.add_worksheet(
        title=cfg_resp.get('name', '管理层反馈'),
        headers=headers_resp,
        rows=response_data,
        col_widths=col_widths_resp,
        default_height=50,
        freeze_header=True,
        alt_row_colors=True,
    )

    return core.save()


def main():
    parser = argparse.ArgumentParser(description='生成审计报告 Excel')
    parser.add_argument('input_json', help='输入的 findings JSON 文件')
    parser.add_argument('output_xlsx', help='输出 Excel 文件')
    parser.add_argument('--config', '-c', help='配置目录')
    parser.add_argument('--template', '-t', choices=['full', 'summary'], default='full',
                        help='报告模板类型')

    args = parser.parse_args()

    output_path = generate_report_xlsx(
        args.input_json,
        args.output_xlsx,
        config_dir=args.config,
        template_type=args.template
    )

    print(f'已生成：{output_path}')


if __name__ == '__main__':
    main()
