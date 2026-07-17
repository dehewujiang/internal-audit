#!/usr/bin/env python3
"""
queries.py — 审计数据查询工具

读取 findings/index.json + evaluator JSONL 历史，提供查询和分析能力。

用法：
    python queries.py findings --risk high
    python queries.py findings --keyword 废料 --year 2026
    python queries.py findings --status 待整改
    python queries.py findings --by-origin design
    
    python queries.py trend --content-type audit_program
    python queries.py trend --days 90
    
    python queries.py compare --topic 存货管理 --from 2025 --to 2026
    
    python queries.py summary
"""
import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


# ── 路径解析 ──────────────────────────────────────────

def find_workspace() -> Path:
    """从 CWD 向上查找 internal-audit-workspace/"""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        ws = parent / "internal-audit-workspace"
        if ws.exists():
            return ws
    return cwd / "internal-audit-workspace"


def get_index_path() -> Path:
    return find_workspace() / "findings" / "index.json"


def get_findings_dir() -> Path:
    return find_workspace() / "findings"


def get_eval_dir() -> Path:
    return Path.home() / ".claude" / "skills" / "internal-audit" / "data" / "evaluations"


# ── 数据读取 ──────────────────────────────────────────

def load_index() -> dict:
    """读取 findings/index.json"""
    path = get_index_path()
    if not path.exists():
        print("📂 未找到 index.json（可能尚未生成任何 finding，或不在审计项目目录中）")
        print(f"   期望路径: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_finding(finding_id: str) -> dict:
    """读取单个 finding JSON"""
    base = get_findings_dir()
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".json") and f != "index.json":
                if finding_id in f:
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fh:
                        return json.load(fh)
    return {}


def load_evaluations(days: int = 30, content_type: str = None) -> list:
    """从 JSONL 历史加载评估记录"""
    eval_dir = get_eval_dir()
    if not eval_dir.exists():
        return []
    
    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    current = start_date
    while current <= end_date:
        file_path = eval_dir / (current.strftime("%Y-%m-%d") + ".jsonl")
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if content_type and record.get("content_type") != content_type:
                            continue
                        results.append(record)
                    except json.JSONDecodeError:
                        continue
        current += timedelta(days=1)
    
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results


# ── 查询命令 ──────────────────────────────────────────

def cmd_findings(args):
    """查询 findings"""
    index = load_index()
    if not index:
        return
    
    total = index.get("total_findings", 0)
    print(f"📊  共 {total} 个 finding\n")
    
    # 筛选
    matched_ids = set()
    
    if args.risk:
        risk_ids = index.get("by_risk", {}).get(args.risk, [])
        matched_ids.update(risk_ids)
        print(f"风险等级 [{args.risk}]：{len(risk_ids)} 个")
    
    if args.status:
        status_ids = index.get("by_status", {}).get(args.status, [])
        matched_ids.update(status_ids) if not matched_ids else matched_ids.intersection_update(status_ids)
        print(f"状态 [{args.status}]：{len(status_ids)} 个")
    
    if args.keyword:
        kw_ids = index.get("by_keyword", {}).get(args.keyword, [])
        matched_ids.update(kw_ids) if not matched_ids else matched_ids.intersection_update(kw_ids)
        print(f"关键词 [{args.keyword}]：{len(kw_ids)} 个")
    
    if args.by_origin:
        origin_ids = index.get("by_origin", {}).get(args.by_origin, [])
        matched_ids.update(origin_ids) if not matched_ids else matched_ids.intersection_update(origin_ids)
        print(f"来源 [{args.by_origin}]：{len(origin_ids)} 个")
    
    if args.year:
        year_ids = index.get("by_year", {}).get(str(args.year), {}).get("ids", [])
        matched_ids.update(year_ids) if not matched_ids else matched_ids.intersection_update(year_ids)
        print(f"年度 [{args.year}]：{len(year_ids)} 个")
    
    # 默认：没有筛选条件时列出全部
    if not matched_ids:
        for year_data in index.get("by_year", {}).values():
            matched_ids.update(year_data.get("ids", []))
    
    # 输出
    matched_list = sorted(matched_ids)
    if not matched_list:
        print("\n没有匹配的 finding")
        return
    
    print(f"\n{'编号':<20} {'标题':<40} {'风险':<6} {'状态':<8} {'来源':<10}")
    print("-" * 90)
    
    hight_count = 0
    for fid in matched_list:
        finding = load_finding(fid)
        if not finding:
            print(f"{fid:<20} {'[未找到文件]':<40}")
            continue
        
        title = finding.get("finding_title", "")[:38]
        rc = finding.get("risk_classification", {})
        risk = rc.get("risk_level", "-")
        status = finding.get("finding_metadata", {}).get("status", "-")
        origin = finding.get("finding_metadata", {}).get("origin", "-")
        
        if risk == "高":
            hight_count += 1
        
        print(f"{fid:<20} {title:<40} {risk:<6} {status:<8} {origin:<10}")
    
    print(f"\n共 {len(matched_list)} 个 finding，其中高风险 {hight_count} 个")
    
    # 统计状态分布
    if matched_list:
        status_dist = defaultdict(int)
        for fid in matched_list:
            finding = load_finding(fid)
            if finding:
                s = finding.get("finding_metadata", {}).get("status", "未知")
                status_dist[s] += 1
        if status_dist:
            print("状态分布：", ", ".join(f"{k}={v}" for k, v in sorted(status_dist.items())))


def cmd_trend(args):
    """展示评估趋势"""
    evals = load_evaluations(days=args.days, content_type=args.content_type)
    
    if not evals:
        print("📭  评估历史为空。请先执行一次含 Step 5 的审计流程。")
        return
    
    print(f"📈  评估趋势（最近 {args.days} 天）\n")
    print(f"    总记录数: {len(evals)}")
    
    if args.content_type:
        print(f"    内容类型: {args.content_type}")
    
    # 按日期聚合
    by_date = defaultdict(list)
    for ev in evals:
        date = ev.get("timestamp", "")[:10]
        by_date[date].append(ev.get("overall_score", 0))
    
    print(f"\n    {'日期':<14} {'平均分':<8} {'数量':<6} {'趋势'}")
    print("    " + "-" * 40)
    
    scores = []
    for date in sorted(by_date.keys()):
        daily_scores = by_date[date]
        avg = sum(daily_scores) / len(daily_scores)
        scores.append(avg)
        bar = "█" * int(avg) + "░" * (10 - int(avg))
        print(f"    {date:<14} {avg:<8.1f} {len(daily_scores):<6} {bar}")
    
    if scores:
        overall_avg = sum(scores) / len(scores)
        print(f"\n    平均分: {overall_avg:.1f}/10")
        if len(scores) > 1:
            trend = scores[-1] - scores[0]
            trend_str = f"上升 {trend:.1f} 分" if trend > 0 else f"下降 {abs(trend):.1f} 分" if trend < 0 else "持平"
            print(f"    趋势: {trend_str}")
    
    # 显示最近的判定分布
    judgment_dist = defaultdict(int)
    for ev in evals:
        summary = ev.get("summary", "")
        if "不合格" in summary or "重新生成" in summary:
            judgment_dist["fail"] += 1
        elif "建议审查" in summary:
            judgment_dist["warn"] += 1
        else:
            judgment_dist["pass"] += 1
    
    if judgment_dist:
        print(f"\n    判定分布: ✅ pass={judgment_dist['pass']}  ⚠️ warn={judgment_dist['warn']}  🔴 fail={judgment_dist['fail']}")


def cmd_compare(args):
    """比较不同年度的 finding"""
    index = load_index()
    if not index:
        return
    
    from_year = str(args.from_year)
    to_year = str(args.to_year)
    
    from_data = index.get("by_year", {}).get(from_year, {})
    to_data = index.get("by_year", {}).get(to_year, {})
    
    from_ids = set(from_data.get("ids", []))
    to_ids = set(to_data.get("ids", []))
    
    print(f"📋  审计对比：{args.topic}（{from_year} → {to_year}）\n")
    print(f"    {from_year} 年 finding 数: {len(from_ids)}")
    print(f"    {to_year} 年 finding 数: {len(to_ids)}")
    
    # 重复发现：标题相似
    new_in_to = to_ids - from_ids
    
    # 尝试通过标题判断重复
    repeated = []
    for fid in from_ids:
        f1 = load_finding(fid)
        if not f1:
            continue
        t1 = f1.get("finding_title", "")
        # 找 to_year 中标题相似的
        for fid2 in to_ids:
            f2 = load_finding(fid2)
            if f2:
                t2 = f2.get("finding_title", "")
                # 简单相似度：共享关键词比例
                words1 = set(t1.replace("，", "").replace(" ", ""))
                words2 = set(t2.replace("，", "").replace(" ", ""))
                if len(words1 & words2) / max(len(words1 | words2), 1) > 0.3:
                    repeated.append((fid, fid2, t1[:30], t2[:30]))
    
    if repeated:
        print(f"\n  🔁 可能重复的问题（{len(repeated)} 项）：")
        print(f"    {'去年 ID':<16} {'今年 ID':<16} {'去年标题':<32} {'今年标题':<32}")
        print("    " + "-" * 96)
        for fid1, fid2, t1, t2 in repeated:
            f2 = load_finding(fid2)
            status = f2.get("finding_metadata", {}).get("status", "") if f2 else ""
            print(f"    {fid1:<16} {fid2:<16} {t1:<32} {t2:<32}")
            print(f"    {'':>32} 状态: {status}")
    else:
        print(f"\n  ✅ 未检测到重复问题（或标题差异大，建议人工核对）")
    
    # 今年新增（非重复）
    truly_new = new_in_to - {r[1] for r in repeated}
    if truly_new:
        print(f"\n  🆕 今年新增问题（{len(truly_new)} 项）：")
        for fid in sorted(truly_new):
            finding = load_finding(fid)
            title = finding.get("finding_title", "")[:50] if finding else "[未加载]"
            print(f"    - {fid}: {title}")


def cmd_summary(args):
    """输出汇总统计"""
    index = load_index()
    if not index:
        return
    
    total = index.get("total_findings", 0)
    print(f"📊  Finding 汇总\n")
    print(f"    总数: {total}")
    
    by_risk = index.get("by_risk", {})
    print(f"    风险分布: 高={by_risk.get('高', 0)} 中={by_risk.get('中', 0)} 低={by_risk.get('低', 0)}")
    
    by_status = index.get("by_status", {})
    print(f"    状态分布: ", ", ".join(f"{k}={len(v)}" for k,v in by_status.items() if v))
    
    by_origin = index.get("by_origin", {})
    print(f"    来源分布: design={len(by_origin.get('design', []))} execution={len(by_origin.get('execution', []))}")
    
    by_year = index.get("by_year", {})
    print(f"    年度分布: ", ", ".join(f"{y}={d['count']}" for y,d in sorted(by_year.items())))
    
    # evaluator 历史
    evals = load_evaluations(days=90)
    if evals:
        avg = sum(e.get("overall_score", 0) for e in evals) / len(evals)
        print(f"\n    📈 评估历史（90天）: {len(evals)} 条记录，平均分 {avg:.1f}/10")


# ── 主入口 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="审计数据查询工具")
    sub = parser.add_subparsers(dest="command", required=True)
    
    # findings
    p_findings = sub.add_parser("findings", help="查找 finding")
    p_findings.add_argument("--risk", choices=["高", "中", "低"], help="按风险等级筛选")
    p_findings.add_argument("--status", choices=["待整改", "整改中", "已整改", "延期", "draft"], help="按状态筛选")
    p_findings.add_argument("--keyword", help="按关键词筛选")
    p_findings.add_argument("--year", type=int, help="按年度筛选")
    p_findings.add_argument("--by-origin", choices=["design", "execution"], help="按来源筛选")
    
    # trend
    p_trend = sub.add_parser("trend", help="评估趋势")
    p_trend.add_argument("--days", type=int, default=30, help="天数范围（默认 30）")
    p_trend.add_argument("--content-type", choices=["audit_program", "finding", "audit_report",
                                                     "policy_analysis", "interview"],
                        help="按内容类型筛选")
    
    # compare
    p_compare = sub.add_parser("compare", help="跨年对比")
    p_compare.add_argument("--topic", default="存货管理", help="审计主题")
    p_compare.add_argument("--from-year", type=int, required=True, help="起始年度")
    p_compare.add_argument("--to-year", type=int, required=True, help="对比年度")
    
    # summary
    sub.add_parser("summary", help="汇总统计")
    
    args = parser.parse_args()
    
    commands = {
        "findings": cmd_findings,
        "trend": cmd_trend,
        "compare": cmd_compare,
        "summary": cmd_summary,
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()
