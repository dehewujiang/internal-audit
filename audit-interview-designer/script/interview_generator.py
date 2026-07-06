# -*- coding: utf-8 -*-
"""
访谈问卷生成器
==============
基于设计观察 JSON + 问题模板配置，生成访谈问卷 Excel。

用法:
python audit-interview-designer/script/interview_generator.py \
    internal-audit-workspace/design-assessments/存货管理_设计观察.json \
    internal-audit-workspace/interview-materials/存货管理_访谈问卷.xlsx \
    [--filter-high-risk]
"""

import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# 引用共享库
sys.path.insert(0, str(Path(__file__).parent.parent.parent / '_shared' / 'scripts'))
from excel_core import ExcelCore
from audit_styles import FILLS, COLORS
from openpyxl.styles import Font, PatternFill


def load_config(config_dir: Path) -> Tuple[Dict, Dict]:
    """加载配置"""
    with open(config_dir / 'question_bank.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
    with open(config_dir / 'module_mapping.json', 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    return questions, mappings


def map_module(title: str, desc: str, mapping_cfg: Dict, obs_type: str) -> str:
    """根据关键词推断模块"""
    text = f"{title} {desc}".lower()
    type_cfg = mapping_cfg.get('mappings', {}).get(obs_type, {})
    for keyword, module in type_cfg.get('keyword_mapping', {}).items():
        if keyword in text:
            return module
    return type_cfg.get('default_module', '未分类')


def render(template: str, data: Dict) -> str:
    """安全格式化模板"""
    pattern = re.compile(r'\{(\w+)\}')
    result = template
    for match in pattern.finditer(template):
        key = match.group(1)
        val = data.get(key, f'[{key}]')
        result = result.replace(f'{{{key}}}', str(val))
    return result


def generate_interview_xlsx(input_json: str, output_xlsx: str, config_dir: Optional[str] = None, filter_high_risk: bool = False) -> str:
    """生成访谈问卷"""
    cfg_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / 'config'
    templates, mappings = load_config(cfg_dir)

    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    observations = data.get('design_observations', [])
    if filter_high_risk:
        observations = [o for o in observations if o.get('severity') == '高']

    print(f"载入 {len(observations)} 个设计观察")

    # 生成问题
    questions = []
    drl = []
    seen_docs = set()

    for obs in observations:
        obs_type = obs.get('type', 'risk_point')
        severity = obs.get('severity', 'medium')

        tmpl = templates.get('templates', {}).get(obs_type, {}).get(severity, {})
        if not tmpl:
            tmpl = templates.get('templates', {}).get('risk_point', {}).get('medium', {})

        # 渲染问题
        render_data = {
            'title': obs.get('title', ''),
            'source_doc': obs.get('source_doc', ''),
            'description': obs.get('description', ''),
            'expected': obs.get('expected_control', ''),
            'design_issue': obs.get('design_issue', ''),
            'doc_a_name': obs.get('doc_a', {}).get('name', ''),
            'doc_b_name': obs.get('doc_b', {}).get('name', ''),
            'doc_a_rule': obs.get('doc_a', {}).get('rule', ''),
            'doc_b_rule': obs.get('doc_b', {}).get('rule', ''),
        }

        module = map_module(obs.get('title', ''), obs.get('description', ''), mappings, obs_type)
        suffix = mappings.get('module_suffix', {}).get(severity, '')

        questions.append([
            f"{module} {suffix}".strip(),
            obs.get('id', ''),
            render(tmpl.get('question', ''), render_data),
            render(tmpl.get('probe_hints', ''), render_data),
            f"《{obs.get('source_doc', '未知')}》{obs.get('source_section', '')}",
            '', '',  # 访谈记录、证据索引
            obs.get('id', '') if severity == '高' else ''
        ])

        # DRL
        doc_key = obs.get('source_doc', '')
        if doc_key and doc_key not in seen_docs:
            seen_docs.add(doc_key)
            drl.append([len(drl)+1, f"《{doc_key}》及相关记录", "纸质/电子", obs.get('source_doc', ''), "否/是", f"用于验证{obs['id']}"])

    # 红旗提示
    red_flags = [['高风险', '无法提供书面证据', '追问替代取证方式']]

    # 创建 Excel
    core = ExcelCore(output_xlsx)

    # Sheet 1
    core.add_worksheet("访谈问卷", ["模块", "序号", "问题", "追问提示", "制度依据", "访谈记录", "证据索引", "风险标记"],
                       questions, [20, 10, 45, 30, 20, 30, 15, 10], default_height=60)

    # Sheet 2
    if drl:
        core.add_worksheet("资料需求清单", ["序号", "资料名称", "格式", "责任部门", "是否获取", "备注"],
                           drl, [8, 35, 12, 15, 12, 30], default_height=30)

    # Sheet 3
    core.add_worksheet("访谈指南", ["场景", "红旗信号", "应对策略"],
                       red_flags, [15, 45, 45], default_height=60, alt_row_colors=False)

    return core.save()


def main():
    parser = argparse.ArgumentParser(description='生成访谈问卷 Excel')
    parser.add_argument('input_json', help='设计观察 JSON')
    parser.add_argument('output_xlsx', help='输出 Excel')
    parser.add_argument('--config', '-c', help='配置目录')
    parser.add_argument('--filter-high-risk', action='store_true', help='仅高风险')
    args = parser.parse_args()

    print(generate_interview_xlsx(args.input_json, args.output_xlsx, args.config, args.filter_high_risk))


if __name__ == '__main__':
    main()
