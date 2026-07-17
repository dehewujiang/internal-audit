#!/usr/bin/env python3
"""
quality_gate.py — 质量门工具

读取评估结果，对比配置阈值，输出通过/重生成指令。
在每个 Skill 的 Step 5 末尾，记录评估结果后调用。

用法：
    # 按 eval-id 检查
    python quality_gate.py --eval-id EVAL-TEST-001
    
    # 直接传入检查结果
    python quality_gate.py --input result.json
    
    # 自定义阈值
    python quality_gate.py --eval-id EVAL-xxx --threshold 6.0

输出格式：
    {"action": "pass|warn|regenerate", "reason": "...", "score": 8.0}
"""
import json
import sys
import os
import argparse
import re
from datetime import datetime


# ── 路径 ──────────────────────────────────────────────

def get_my_config_path() -> str:
    """查找 my-config.md"""
    candidates = [
        os.path.expanduser("~/.claude/skills/internal-audit/audit-topics/my-config.md"),
        os.path.join(os.getcwd(), "internal-audit-workspace", "..", "..", "my-config.md"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


def get_eval_dir() -> str:
    return os.path.expanduser("~/.claude/skills/internal-audit/data/evaluations")


# ── 阈值读取 ──────────────────────────────────────────

DEFAULT_THRESHOLDS = {
    "program_quality": 5.0,
    "context_validation": 5.0,
    "evidence_rating": 5.0,
    "report_compliance": 6.0,
    "executability": 5.0,
    "risk_matrix": 5.0,
    "coverage_detector": 5.0,
    "trend_analyzer": 5.0,
    "benchmark": 5.0,
    "confidence": 5.0,
    # 综合
    "overall": 5.0,
    "critical_issues": 0,  # 允许的关键问题数
}


def parse_my_config():
    """从 my-config.md 解析阈值配置"""
    config_path = get_my_config_path()
    if not os.path.exists(config_path):
        return DEFAULT_THRESHOLDS.copy()
    
    thresholds = DEFAULT_THRESHOLDS.copy()
    
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 解析阈值配置块
    # 期望格式：
    # ### 质量阈值设置
    # - 程序质量最低分: 5.0
    # - 证据强度最低分: 5.0
    # - 报告合规最低分: 6.0
    
    section_match = re.search(r'###\s*质量阈值设置\s*(.*?)(?=\n###|\Z)', content, re.DOTALL)
    if not section_match:
        return thresholds
    
    section = section_match.group(1)
    
    mappings = {
        "程序质量": "program_quality",
        "情境分析": "context_validation",
        "证据强度": "evidence_rating",
        "报告合规": "report_compliance",
        "执行可行性": "executability",
        "风险评估": "risk_matrix",
        "覆盖检测": "coverage_detector",
        "历史趋势": "trend_analyzer",
        "同行对标": "benchmark",
        "置信度": "confidence",
        "综合": "overall",
    }
    
    for cn_name, en_name in mappings.items():
        pattern = rf'{cn_name}[^\d]*?([\d.]+)'
        match = re.search(pattern, section)
        if match:
            thresholds[en_name] = float(match.group(1))
    
    return thresholds


# ── 评估数据读取 ──────────────────────────────────────

def load_evaluation(eval_id: str) -> dict:
    """从 JSONL 按 eval_id 查找评估记录"""
    eval_dir = get_eval_dir()
    if not os.path.exists(eval_dir):
        return {}
    
    for fname in os.listdir(eval_dir):
        if fname.endswith(".jsonl"):
            fpath = os.path.join(eval_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("eval_id") == eval_id:
                            return record
                    except json.JSONDecodeError:
                        continue
    return {}


def load_from_input(input_path: str) -> dict:
    """从 JSON 文件读取评估结果"""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 判定逻辑 ──────────────────────────────────────────

def evaluate(record: dict, thresholds: dict, custom_threshold: float = None) -> dict:
    """
    评估并输出行动指令
    
    返回:
        {"action": "pass"|"warn"|"regenerate", "reason": "...", "score": float}
    """
    
    overall_score = record.get("overall_score", 0.0)
    dimensions = record.get("dimensions", {})
    critical_count = record.get("critical_issues_count", 0)
    
    overall_threshold = custom_threshold if custom_threshold is not None else thresholds.get("overall", 5.0)
    max_critical = thresholds.get("critical_issues", 0)
    
    # 检查1：综合评分
    if overall_score < overall_threshold:
        return {
            "action": "regenerate",
            "reason": f"综合评分 {overall_score} 低于阈值 {overall_threshold}",
            "score": overall_score,
            "detail": {
                "overall_score": overall_score,
                "threshold": overall_threshold,
                "critical_issues": critical_count,
                "max_critical": max_critical,
            }
        }
    
    # 检查2：关键问题数
    if critical_count > max_critical:
        return {
            "action": "regenerate",
            "reason": f"关键问题数 {critical_count} 超过上限 {max_critical}",
            "score": overall_score,
            "detail": {
                "overall_score": overall_score,
                "threshold": overall_threshold,
                "critical_issues": critical_count,
                "max_critical": max_critical,
            }
        }
    
    # 检查3：各维度
    low_dimensions = []
    for dim_name, dim_data in dimensions.items():
        dim_score = dim_data.get("score", 10) if isinstance(dim_data, dict) else getattr(dim_data, "score", 10)
        # 尝试匹配维度阈值
        dim_threshold = thresholds.get(dim_name, overall_threshold)
        if isinstance(dim_score, (int, float)) and dim_score < dim_threshold:
            low_dimensions.append(f"{dim_name}={dim_score}(<{dim_threshold})")
    
    if low_dimensions:
        if len(low_dimensions) >= 2:
            return {
                "action": "regenerate",
                "reason": f"多个维度低于阈值: {'; '.join(low_dimensions)}",
                "score": overall_score,
            }
        else:
            return {
                "action": "warn",
                "reason": f"维度评分偏低: {'; '.join(low_dimensions)}",
                "score": overall_score,
            }
    
    return {
        "action": "pass",
        "reason": "所有检查通过",
        "score": overall_score,
    }


# ── 主入口 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="质量门工具")
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--eval-id", help="评估 ID（从 JSONL 历史查找）")
    input_group.add_argument("--input", help="评估结果 JSON 文件路径")
    
    parser.add_argument("--threshold", type=float, help="覆盖默认阈值")
    parser.add_argument("--verbose", action="store_true", help="输出详细信息")
    
    args = parser.parse_args()
    
    # 读取评估数据
    if args.eval_id:
        record = load_evaluation(args.eval_id)
        if not record:
            print(json.dumps({
                "action": "error",
                "reason": f"未找到评估记录: {args.eval_id}",
                "score": 0,
            }, ensure_ascii=False))
            sys.exit(1)
    else:
        record = load_from_input(args.input)
    
    # 读取阈值
    thresholds = parse_my_config()
    
    # 执行判定
    result = evaluate(record, thresholds, custom_threshold=args.threshold)
    
    # 输出
    if args.verbose:
        result["thresholds"] = thresholds
        result["overall_score"] = record.get("overall_score", 0)
        result["checks_count"] = len(record.get("dimensions", {}))
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 退出码
    if result["action"] == "regenerate":
        sys.exit(2)
    elif result["action"] == "warn":
        sys.exit(1)


if __name__ == "__main__":
    main()
