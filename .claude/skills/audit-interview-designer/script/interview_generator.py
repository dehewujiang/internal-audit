# -*- coding: utf-8 -*-
"""
访谈问卷生成器 v2.0
=================
双模式：新格式（interview_content.json）直读写入 + 旧格式（design_observations.json）模板兼容。

新模式（推荐）— 内容由 LLM 推理生成，本脚本仅做 Excel 排版:
  {
    "questions": [{module, id, question, probe_hints, policy_ref, risk_flag}, ...],
    "drl": [{name, format, dept, acquired, note}, ...],
    "interview_guide": [{scenario, red_flag, strategy}, ...]
  }

旧模式（兼容）— 模板渲染，severity 已支持中英文:
  {
    "design_observations": [{id, type, severity, title, ...}, ...]
  }

用法:
  python interview_generator.py input.json output.xlsx [--filter-high-risk]
"""

import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

# ── severity 规范化 ─────────────────────────────────────
# 输入数据可能用中文或英文，统一转为中文（模板 key 已改为中文）
SEVERITY_MAP = {
    "高": "高", "中": "中", "低": "低",
    "high": "高", "medium": "中", "low": "低",
    "High": "高", "Medium": "中", "Low": "低",
}

def normalize_severity(raw: str) -> str:
    """统一 severity 为中文"""
    if not raw:
        return "中"
    return SEVERITY_MAP.get(str(raw).strip(), "中")


# ── 配置加载 ────────────────────────────────────────────

def load_config(config_dir: Path) -> Tuple[Dict, Dict]:
    """加载模板和映射配置"""
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
    """安全格式化模板：替换 {key} 为 data[key]"""
    pattern = re.compile(r'\{(\w+)\}')
    result = template
    for match in pattern.finditer(template):
        key = match.group(1)
        val = data.get(key, f'[{key}]')
        result = result.replace(f'{{{key}}}', str(val))
    return result


# ── 新模式：从 interview_content.json 直接读 ──────────────

def _build_from_content(data: Dict) -> Tuple[List[List], List[List], List[List]]:
    """
    新模式入口：输入含 "questions" 键 → 直接读字段写入。
    LLM 已在生成阶段完成所有的推理工作。
    """
    questions_raw = data.get('questions', [])
    drl_raw = data.get('drl', [])
    guide_raw = data.get('interview_guide', [])

    questions = []
    for q in questions_raw:
        questions.append([
            q.get('module', '未分类'),
            q.get('id', ''),
            q.get('question', ''),
            q.get('probe_hints', ''),
            q.get('policy_ref', ''),
            q.get('interview_record', ''),
            q.get('evidence_index', ''),
            q.get('risk_flag', ''),
        ])

    drl = []
    for d in drl_raw:
        drl.append([
            d.get('seq', len(drl) + 1),
            d.get('name', ''),
            d.get('format', '纸质/电子'),
            d.get('dept', ''),
            d.get('acquired', '否'),
            d.get('note', ''),
        ])

    interview_guide = []
    for g in guide_raw:
        interview_guide.append([
            g.get('scenario', ''),
            g.get('red_flag', ''),
            g.get('strategy', ''),
        ])

    return questions, drl, interview_guide


# ── 旧模式：从 design_observations 模板渲染 ─────────────────

def _build_from_observations(
    observations: List[Dict],
    templates: Dict,
    mappings: Dict,
) -> Tuple[List[List], List[List], List[List]]:
    """
    旧模式兼容入口：输入含 "design_observations" 键 → 模板渲染。
    severity 已通过 normalize_severity() 对齐到中文模板 key。
    """
    questions = []
    drl = []
    seen_docs = set()

    for obs in observations:
        obs_type = obs.get('type', 'risk_point')
        severity = normalize_severity(obs.get('severity', '中'))

        # 模板查找：先按 (type, severity) 精确匹配，失败回退到 risk_point.中
        tmpl = templates.get('templates', {}).get(obs_type, {}).get(severity, {})
        if not tmpl:
            tmpl = templates.get('templates', {}).get('risk_point', {}).get('中', {})

        # 渲染数据 — 模板中可用 {title} {source_doc} {description} {expected} {design_issue} 等
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
            '', '',  # 访谈记录、证据索引 — 留空供用户填写
            obs.get('id', '') if severity == '高' else ''
        ])

        # DRL：按 source_doc 去重
        doc_key = obs.get('source_doc', '')
        if doc_key and doc_key not in seen_docs:
            seen_docs.add(doc_key)
            drl.append([
                len(drl) + 1,
                f"《{doc_key}》及相关记录",
                "纸质/电子",
                obs.get('source_doc', ''),
                "否/是",
                f"用于验证{obs['id']}"
            ])

    # 访谈指南：旧模式只给一个通用策略（建议尽快迁移到新模式以获取场景化指南）
    interview_guide = [
        ['高风险', '无法提供书面证据', '追问替代取证方式（如系统截图、邮件记录、工作台账）'],
        ['中风险', '受访者描述模糊', '追问具体实例：最近一次发生是什么时候？涉及哪些人员？'],
        ['低风险', '受访者认为"没问题"', '追问例外情况：有没有哪次操作没按流程走的？'],
    ]

    return questions, drl, interview_guide


# ── 主入口 ──────────────────────────────────────────────

def generate_interview_xlsx(
    input_json: str,
    output_xlsx: str,
    config_dir: Optional[str] = None,
    filter_high_risk: bool = False
) -> str:
    """生成访谈问卷 Excel — 自动检测新旧格式"""
    cfg_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / 'config'
    templates, mappings = load_config(cfg_dir)

    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # ── 格式检测 ──
    if 'questions' in data:
        # 新模式：LLM 已生成完整内容
        print("检测到新格式 (interview_content.json)，直接读取内容")
        questions, drl, interview_guide = _build_from_content(data)
    elif 'design_observations' in data:
        # 旧模式：模板渲染（兼容）
        observations = data.get('design_observations', [])
        if filter_high_risk:
            observations = [o for o in observations if normalize_severity(o.get('severity')) == '高']
        print(f"检测到旧格式 (design_observations)，模板渲染 {len(observations)} 个观察")
        questions, drl, interview_guide = _build_from_observations(observations, templates, mappings)
    else:
        raise ValueError(
            "输入 JSON 缺少 'questions' 或 'design_observations' 键。\n"
            "请确认输入文件格式：新格式需含 questions/drl/interview_guide，旧格式需含 design_observations。"
        )

    # ── 写入 Excel ──
    core = ExcelCore(output_xlsx)

    # Sheet 1: 访谈问卷
    core.add_worksheet(
        "访谈问卷",
        ["模块", "序号", "问题", "追问提示", "制度依据", "访谈记录", "证据索引", "风险标记"],
        questions,
        [20, 10, 45, 30, 20, 30, 15, 10],
        default_height=60
    )

    # Sheet 2: 资料需求清单
    if drl:
        core.add_worksheet(
            "资料需求清单",
            ["序号", "资料名称", "格式", "责任部门", "是否获取", "备注"],
            drl,
            [8, 35, 12, 15, 12, 30],
            default_height=30
        )

    # Sheet 3: 访谈指南
    if interview_guide:
        core.add_worksheet(
            "访谈指南",
            ["场景", "红旗信号", "应对策略"],
            interview_guide,
            [15, 45, 45],
            default_height=60,
            alt_row_colors=False
        )

    return core.save()


def main():
    parser = argparse.ArgumentParser(description='生成访谈问卷 Excel (v2.0 — 支持新旧双格式)')
    parser.add_argument('input_json', help='输入 JSON（新: interview_content.json / 旧: design_observations.json）')
    parser.add_argument('output_xlsx', help='输出 Excel 路径')
    parser.add_argument('--config', '-c', help='配置目录（默认自动查找）')
    parser.add_argument('--filter-high-risk', action='store_true', help='仅生成高风险题目（仅旧模式有效）')
    args = parser.parse_args()

    print(generate_interview_xlsx(args.input_json, args.output_xlsx, args.config, args.filter_high_risk))


if __name__ == '__main__':
    main()
