"""
评估历史存储 - JSONL 格式

[INPUT]: 被本技能的 record_evaluation.py / quality_gate.py 导入，提供评估记录的读写
[OUTPUT]: EVALUATION_DIR 常量；save_evaluation / load_evaluations / get_latest_evaluation 等存取函数
[POS]: internal-audit-evaluator 的数据层，与 quality_gate.py（阈值判定）互为读写两端，
       存储位置必须与 quality_gate.get_eval_dir() 保持一致（均随脚本位置解析到仓库根 data/evaluations）
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path


# 评估历史存储路径：随脚本位置解析到仓库根（开发仓 = 源仓库根；部署项目 = 项目根）。
# 禁止写死用户主目录下的外部快照路径——那是导致幽灵目录和读写分离的病根（见 memory/decisions.md）。
REPO_ROOT = Path(__file__).resolve().parent.parent
EVALUATION_DIR = REPO_ROOT / "data" / "evaluations"


def _ensure_dir():
    """确保存储目录存在"""
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)


def _get_file_path(date: Optional[datetime] = None) -> Path:
    """获取指定日期的存储文件路径"""
    _ensure_dir()
    date = date or datetime.now()
    filename = date.strftime("%Y-%m-%d") + ".jsonl"
    return EVALUATION_DIR / filename


def save_evaluation(report) -> str:
    """
    保存评估报告到 JSONL

    Args:
        report: EvalReport 对象

    Returns:
        str: 存储的文件路径
    """
    file_path = _get_file_path()

    # 将报告序列化为字典
    record = {
        "eval_id": report.eval_id,
        "content_type": report.content_type,
        "timestamp": report.timestamp,
        "overall_score": report.overall_score,
        "summary": report.summary,
        "dimensions": {
            name: {
                "score": dim.score,
                "issues": dim.issues,
                "suggestions": dim.suggestions,
                "confidence": dim.confidence,
                "failed": dim.failed
            }
            for name, dim in report.dimensions.items()
        },
        "critical_issues_count": len(report.critical_issues)
    }

    # 追加写入 JSONL
    with open(file_path, "a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")

    return str(file_path)


def load_evaluations(
    days: int = 30,
    content_type: Optional[str] = None,
    min_score: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    加载评估历史

    Args:
        days: 加载最近多少天
        content_type: 按内容类型过滤
        min_score: 按最低评分过滤

    Returns:
        List[Dict]: 评估记录列表
    """
    _ensure_dir()

    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 遍历日期范围内的文件
    current = start_date
    while current <= end_date:
        file_path = _get_file_path(current)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)

                        # 过滤条件
                        if content_type and record.get("content_type") != content_type:
                            continue
                        if min_score is not None and record.get("overall_score", 0) < min_score:
                            continue

                        results.append(record)
                    except json.JSONDecodeError:
                        continue
        current += timedelta(days=1)

    # 按时间排序
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results


def get_latest_evaluation(content_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取最新的评估记录"""
    evaluations = load_evaluations(days=7, content_type=content_type)
    return evaluations[0] if evaluations else None


def get_score_trend(days: int = 30) -> List[Dict[str, Any]]:
    """
    获取评分趋势

    Returns:
        [{date: str, avg_score: float, count: int}]
    """
    evaluations = load_evaluations(days=days)

    from collections import defaultdict
    by_date = defaultdict(list)

    for ev in evaluations:
        date = ev.get("timestamp", "")[:10]  # YYYY-MM-DD
        by_date[date].append(ev.get("overall_score", 0))

    result = []
    for date in sorted(by_date.keys()):
        scores = by_date[date]
        result.append({
            "date": date,
            "avg_score": round(sum(scores) / len(scores), 1),
            "count": len(scores)
        })

    return result


def export_to_csv(output_path: str, days: int = 90):
    """导出评估历史为 CSV"""
    import csv

    evaluations = load_evaluations(days=days)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["eval_id", "timestamp", "content_type", "overall_score", "summary"])

        for ev in evaluations:
            writer.writerow([
                ev.get("eval_id"),
                ev.get("timestamp"),
                ev.get("content_type"),
                ev.get("overall_score"),
                ev.get("summary", "")[:100]
            ])

    return output_path
