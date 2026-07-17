#!/usr/bin/env python3
"""
record_evaluation.py — 评估结果回写工具

从命令行接收 JSON 格式的评估结果，写入 storage.py 的 JSONL 历史库。
在每个 Skill 的 Step 5 末尾调用。

用法：
    python record_evaluation.py --input result.json
    python record_evaluation.py --eval-id EVAL-xxx --content-type audit_program --judgment pass \
        --check '{"name":"模板完整性","result":"pass","detail":"无占位符"}' \
        --check '{"name":"推理链回溯","result":"fail","detail":"事实锚定❌"}'
"""
import json
import sys
import os
import argparse
from datetime import datetime

# 确保能导入同目录的 storage.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from storage import save_evaluation


class EvalReportStub:
    """storage.save_evaluation() 需要的报告对象结构体"""
    def __init__(self, eval_id, content_type, timestamp, overall_score,
                 dimensions, critical_issues, summary):
        self.eval_id = eval_id
        self.content_type = content_type
        self.timestamp = timestamp
        self.overall_score = overall_score
        self.dimensions = dimensions
        self.critical_issues = critical_issues
        self.summary = summary


def parse_args():
    parser = argparse.ArgumentParser(description="评估结果回写工具")
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", help="评估结果 JSON 文件路径")
    input_group.add_argument("--stdin", action="store_true", help="从 stdin 读取 JSON")
    
    parser.add_argument("--eval-id", help="评估 ID（不指定则自动生成）")
    parser.add_argument("--content-type", default="audit_program",
                        choices=["audit_program", "finding", "audit_report",
                                 "policy_analysis", "interview"])
    parser.add_argument("--judgment", default="pass",
                        choices=["pass", "warn", "fail"],
                        help="总体判定")
    parser.add_argument("--content-id", default="",
                        help="被评估内容的标识（如文件名）")
    
    return parser.parse_args()


def read_json(args):
    """读取评估结果 JSON"""
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            return json.load(f)
    elif args.stdin:
        return json.load(sys.stdin)
    return {}


def build_report(data, args):
    """从输入数据构建 storage.py 所需的报告对象"""
    eval_id = args.eval_id or data.get("eval_id") or f"EVAL-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    content_type = data.get("content_type", args.content_type or "audit_program")
    timestamp = data.get("timestamp", datetime.now().isoformat())
    overall_judgment = data.get("overall_judgment", args.judgment)
    content_id = data.get("content_id", args.content_id or "")
    checks = data.get("checks", data.get("check_results", []))
    
    if not checks:
        print("⚠️  警告：检查项为空（checks=[]），仍会记录，但建议补充检查项")
    
    # 计算总分（按检查项的 pass 比例）
    total = len(checks)
    passed = sum(1 for c in checks if c.get("result") == "pass")
    overall_score = round((passed / total) * 10, 1) if total > 0 else 0.0
    
    # 将 checks 转换为 dimensions 格式
    dimensions = {}
    issues = []
    suggestions = []
    
    for check in checks:
        name = check.get("name", "未知检查")
        result = check.get("result", "fail")
        detail = check.get("detail", "")
        
        # 每个 check 作为一个"维度"
        dim_score = 10.0 if result == "pass" else (5.0 if result == "warn" else 0.0)
        dim_issues = []
        dim_suggestions = []
        
        if result != "pass":
            dim_issues.append({
                "type": "check_failed",
                "severity": "high" if result == "fail" else "medium",
                "message": detail or f"{name} 未通过"
            })
        
        class DimStub:
            pass
        
        dim = DimStub()
        dim.score = dim_score
        dim.issues = dim_issues
        dim.suggestions = dim_suggestions
        dim.confidence = 0.85
        dim.failed = (result == "fail")
        
        dimensions[name] = dim
        
        if dim_issues:
            issues.extend(dim_issues)
    
    # 生成摘要
    if overall_judgment == "pass":
        summary = "所有检查项通过，内容质量合格。"
    elif overall_judgment == "warn":
        summary = f"存在 {total - passed}/{total} 项检查未通过，建议审查后使用。"
    else:
        summary = f"存在 {total - passed}/{total} 项检查未通过，建议重新生成。"
    
    # 记录 content_id 到 summary 中以便查询
    if content_id:
        summary = f"[{content_id}] {summary}"
    
    critical_count = len([c for c in checks if c.get("result") == "fail"])
    critical_issues = issues[:critical_count] if issues else []
    
    return EvalReportStub(
        eval_id=eval_id,
        content_type=content_type,
        timestamp=timestamp,
        overall_score=overall_score,
        dimensions=dimensions,
        critical_issues=critical_issues,
        summary=summary
    )


def main():
    args = parse_args()
    data = read_json(args) if not getattr(args, 'stdin', None) else read_json(args)
    
    report = build_report(data, args)
    
    try:
        file_path = save_evaluation(report)
        print(f"✅  已记录评估 [{report.eval_id}]")
        print(f"    内容类型: {report.content_type}")
        print(f"    总体判定: {args.judgment}")
        print(f"    综合评分: {report.overall_score}/10")
        print(f"    存储路径: {file_path}")
    except Exception as e:
        print(f"❌  存储失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
