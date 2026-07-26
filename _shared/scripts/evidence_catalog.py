#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evidence_catalog.py — 证据清单管理工具

[INPUT]:  证据清单 JSON + _files/ 目录中的文件
[OUTPUT]: 文件扫描结果 / 匹配建议 / 更新后的清单
[POS]:    _shared/scripts 的工具脚本，供 audit-execution-assistant Phase 3 调用
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

功能：
  1. load/save — 读取和保存证据清单
  2. scan_files — 扫描 _files/ 获取文件结构指纹
  3. suggest_matches — 基于关键词匹配生成槽位→文件的匹配建议
  4. update_slot — 更新槽位的文件路径

用法：
    python evidence_catalog.py scan <workspace>     — 扫描文件并输出 JSON
    python evidence_catalog.py match <workspace>    — 匹配文件到槽位
    python evidence_catalog.py status <workspace>   — 查看收集进度
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


# ── 文件扫描 ──────────────────────────────────────────

def _read_excel_headers(filepath: str, sample_rows: int = 5) -> list:
    """读取 Excel/CSV 的前几行列名。返回列名列表，失败返回空列表。"""
    try:
        import pandas as pd
        ext = Path(filepath).suffix.lower()
        if ext == '.csv':
            df = pd.read_csv(filepath, nrows=sample_rows, encoding='utf-8-sig')
        else:
            df = pd.read_excel(filepath, nrows=sample_rows)
        return [str(c).strip() for c in df.columns.tolist()]
    except Exception:
        return []


def scan_files(evidence_root: Path) -> list:
    """扫描 _files/ 目录下所有文件，返回文件信息列表。
    每项包��：name, path, ext, size_bytes, headers (Excel/CSV), rows (Excel/CSV行数)
    """
    files_dir = evidence_root / '_files'
    if not files_dir.exists():
        return []

    results = []
    for f in files_dir.iterdir():
        if not f.is_file() or f.name.startswith('.'):
            continue

        info = {
            'name': f.name,
            'path': str(f.relative_to(evidence_root.parent)),
            'ext': f.suffix.lower(),
            'size_bytes': f.stat().st_size,
            'headers': [],
            'rows': 0,
        }

        if info['ext'] in ('.xlsx', '.xls', '.csv'):
            try:
                import pandas as pd
                ext = info['ext']
                if ext == '.csv':
                    df = pd.read_csv(str(f), nrows=500, encoding='utf-8-sig')
                else:
                    df = pd.read_excel(str(f), nrows=500)
                info['headers'] = [str(c).strip() for c in df.columns.tolist()]
                info['rows'] = len(df)
            except Exception:
                pass

        results.append(info)
    return results


# ── 关键词匹配 ────────────────────────────────────────

def _tokenize(text: str) -> set:
    """将文本切分为关键词集合。"""
    if not text:
        return set()
    # 按常见分隔符切分，保留2字及以上的中文词
    tokens = set()
    for sep in ['、', ',', '，', '；', ';', '\n', '  ']:
        text = text.replace(sep, ' ')
    for word in text.split():
        word = word.strip()
        if len(word) >= 2:
            tokens.add(word)
    return tokens


def _score_slot_file(slot: dict, file_info: dict) -> tuple:
    """计算槽位与文件的匹配度。返回 (分数, 匹配理由列表)。
    匹配策略：
      - 文件名含证据名称关键词 → +3 分/词
      - 文件列名含证据名称关键词 → +2 分/词
      - 文件名/扩展名与槽位描述一致 → +1 分
    """
    score = 0
    reasons = []

    slot_tokens = _tokenize(slot.get('name', ''))
    file_name_tokens = _tokenize(Path(file_info['name']).stem)

    # 文件名匹配
    common = slot_tokens & file_name_tokens
    if common:
        score += len(common) * 3
        reasons.append(f'文件名匹配: {",".join(common)}')

    # 列名匹配
    header_tokens = set()
    for h in file_info.get('headers', []):
        header_tokens |= _tokenize(h)
    header_match = slot_tokens & header_tokens
    if header_match:
        score += len(header_match) * 2
        reasons.append(f'列名匹配: {",".join(header_match)}')

    # 格式描述匹配
    ext = file_info.get('ext', '')
    if ext in ('.xlsx', '.xls', '.csv') and any(
        kw in slot.get('name', '') for kw in ['表', '清单', '台账', '记录']
    ):
        score += 1
        reasons.append('格式匹配(表格类)')

    return score, reasons


def suggest_matches(catalog: dict, files: list,
                     min_score: int = 1) -> dict:
    """为 catalog 中 file: null 的槽位匹配文件。
    返回 {'matched': [], 'missing': [], 'unmatched_files': []}
    """
    unmatched_slots = [s for s in catalog.get('items', []) if s.get('file') is None]
    matched_slots = [s for s in catalog.get('items', []) if s.get('file') is not None]
    unmatched_files = list(files)

    matches = []

    for slot in unmatched_slots:
        best_score = 0
        best_file = None
        best_reasons = []

        for f in unmatched_files:
            score, reasons = _score_slot_file(slot, f)
            if score > best_score:
                best_score = score
                best_file = f
                best_reasons = reasons

        if best_score >= min_score and best_file:
            matches.append({
                'slot_id': slot['id'],
                'slot_name': slot['name'],
                'matched_file': best_file['name'],
                'score': best_score,
                'reasons': best_reasons,
                'source_programs': slot.get('source_programs', []),
            })
            unmatched_files.remove(best_file)
        else:
            matches.append({
                'slot_id': slot['id'],
                'slot_name': slot['name'],
                'matched_file': None,
                'score': 0,
                'reasons': [],
                'source_programs': slot.get('source_programs', []),
            })

    return {
        'matched': [m for m in matches if m['matched_file']],
        'missing': [m for m in matches if not m['matched_file']],
        'unmatched_files': [f['name'] for f in unmatched_files],
        'previously_matched': len(matched_slots),
    }


def status_summary(catalog: dict, files: list) -> dict:
    """生成证据收集状态摘要。"""
    total = catalog.get('total_slots', 0)
    filled = sum(1 for s in catalog.get('items', []) if s.get('file'))
    return {
        'project': catalog.get('project', ''),
        'total_slots': total,
        'filled_slots': filled,
        'missing_slots': total - filled,
        'files_in_dir': len(files),
    }


# ── 清单读写 ──────────────────────────────────────────

def load_catalog(workspace: Path) -> dict:
    """读取证据清单。路径: <workspace>/evidence/_evidence_catalog.json"""
    evidence_root = workspace / 'evidence'
    catalog_path = evidence_root / '_evidence_catalog.json'
    if not catalog_path.exists():
        return {}
    with open(catalog_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_catalog(workspace: Path, catalog: dict) -> None:
    """保存证据清单。"""
    evidence_root = workspace / 'evidence'
    catalog_path = evidence_root / '_evidence_catalog.json'
    catalog['updated_at'] = datetime.now().strftime('%Y-%m-%d')
    # 重算统计
    total = len(catalog.get('items', []))
    filled = sum(1 for s in catalog.get('items', []) if s.get('file'))
    catalog['total_slots'] = total
    catalog['filled_slots'] = filled
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)


def update_slot(workspace: Path, slot_id: str, file_path: str) -> bool:
    """更新槽位的文件路径。成功返回 True。"""
    catalog = load_catalog(workspace)
    if not catalog:
        return False

    for item in catalog.get('items', []):
        if item.get('id') == slot_id:
            item['file'] = file_path
            item['collected_at'] = datetime.now().strftime('%Y-%m-%d')
            save_catalog(workspace, catalog)
            return True
    return False


# ── CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='证据清单管理工具')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('scan', help='扫描 _files/ 目录中的文件').add_argument(
        'workspace', type=str, help='workspace 目录路径')

    sub.add_parser('match', help='匹配文件到证据槽位').add_argument(
        'workspace', type=str, help='workspace 目录路径')

    sub.add_parser('status', help='查看证据收集进度').add_argument(
        'workspace', type=str, help='workspace 目录路径')

    p_update = sub.add_parser('update', help='更新槽位文件路径')
    p_update.add_argument('workspace', type=str)
    p_update.add_argument('--slot', required=True, type=str, help='槽位 ID')
    p_update.add_argument('--file', required=True, type=str, help='文件路径')

    args = parser.parse_args()
    ws = Path(args.workspace)

    if args.command == 'scan':
        files = scan_files(ws / 'evidence')
        print(json.dumps(files, ensure_ascii=False, indent=2))

    elif args.command == 'match':
        catalog = load_catalog(ws)
        if not catalog:
            print(json.dumps({'error': '证据清单不存在'}, ensure_ascii=False))
            sys.exit(1)
        files = scan_files(ws / 'evidence')
        result = suggest_matches(catalog, files)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == 'status':
        catalog = load_catalog(ws)
        files = scan_files(ws / 'evidence')
        status = status_summary(catalog, files)
        print(json.dumps(status, ensure_ascii=False, indent=2))

    elif args.command == 'update':
        ok = update_slot(ws, args.slot, args.file)
        print(json.dumps({'success': ok}, ensure_ascii=False))


if __name__ == '__main__':
    main()
