#!/usr/bin/env python3
"""
queries.py — 审计数据查询工具

读取 findings/index.json + evaluator JSONL 历史，提供查询和分析能力。
在任何阶段都可调用，支持按风险/状态/关键词/年度/来源筛选 findings。
支持 --cross-project 跨项目查询（需 projects-index.json）。

[INPUT]:  findings/index.json + findings/F-YYYY-NNN.json + evaluator JSONL + projects-index.json
[OUTPUT]: 结构化查询结果（文本/JSON）
[POS]:    _shared/scripts 的通用查询工具，被 CLAUDE.md 注册为全局可用

用法：
    python queries.py register --path "D:\审计项目\2026-Q3" --topic 存货管理 --period 2026-Q3
    python queries.py register --list
    python queries.py register --remove P-2026-001

    python queries.py findings --risk high [--cross-project]
    python queries.py findings --keyword 废料 --year 2026 [--cross-project]
    python queries.py findings --status 待整改 [--cross-project]
    python queries.py findings --by-origin design [--cross-project]

    python queries.py trend --content-type audit_program
    python queries.py trend --days 90

    python queries.py compare --topic 存货管理 --from 2025 --to 2026 [--cross-project]

    python queries.py summary [--cross-project]

    python queries.py search "SAP 权限" [--cross-project]

    python queries.py analyses --topic 存货管理 --gaps
    python queries.py analyses --verbose

    python queries.py trace F-2026-001

    python queries.py decide D-003
    python queries.py decide --all
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


def get_policy_analyses_dir() -> Path:
    return find_workspace() / "policy-analyses"


def get_design_assessments_dir() -> Path:
    return find_workspace() / "design-assessments"


def get_audit_programs_dir() -> Path:
    return find_workspace() / "audit-programs"


def get_projects_index_path() -> Path:
    """Find projects-index.json from gold source (same dir as this script's repo)"""
    # queries.py lives at <gold>/_shared/scripts/queries.py
    script_dir = Path(__file__).resolve().parent
    gold_root = script_dir.parent.parent  # _shared/../.. = gold root
    return gold_root / "audit-topics" / "projects-index.json"


def load_projects_index() -> dict:
    """Load projects-index.json from gold source"""
    path = get_projects_index_path()
    if not path.exists():
        return {"projects": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"projects": []}


def save_projects_index(data: dict):
    """Save projects-index.json to gold source"""
    path = get_projects_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scan_project(path_str: str) -> dict:
    """Scan a project directory and return its stats"""
    pp = Path(path_str).resolve()
    ws = pp / "internal-audit-workspace"
    if not ws.exists():
        ws = pp  # maybe user gave path that IS the workspace parent or workspace itself
        if not (ws / "current-audit.json").exists():
            # try one level up
            ws = pp.parent / "internal-audit-workspace"

    info = {"path": str(pp), "findings_count": 0, "topic": "", "period": "", "phase": "unknown"}

    # Read current-audit.json
    audit_json = ws / "current-audit.json"
    if audit_json.exists():
        try:
            with open(audit_json, "r", encoding="utf-8-sig") as f:
                audit = json.load(f)
            info["topic"] = audit.get("audit_topic", "")
            info["phase"] = audit.get("status", "unknown")
            state = audit.get("audit_state", {})
            info["period"] = state.get("audit_period", audit.get("updated_at", ""))
        except Exception:
            pass

    # Count findings
    findings_dir = ws / "findings"
    if findings_dir.exists():
        fj = [f for f in findings_dir.glob("F-*.json")]
        info["findings_count"] = len(fj)

    return info


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


# ── 跨项目数据源 ───────────────────────────────────────

class CrossProjectSource:
    """Iterate over all registered projects as if they were one workspace."""

    def __init__(self, projects: list):
        self.projects = [p for p in projects if Path(p.get("path", "")).exists()]

    def all_findings(self):
        """Yield (project_info, finding_dict) for every finding across all projects."""
        for proj in self.projects:
            pp = Path(proj["path"])
            findings_dir = pp / "internal-audit-workspace" / "findings"
            # also try if path IS the workspace
            if not findings_dir.exists():
                findings_dir = pp / "findings"
            if not findings_dir.exists():
                continue
            for fpath in sorted(findings_dir.glob("F-*.json")):
                try:
                    with open(fpath, "r", encoding="utf-8-sig") as f:
                        finding = json.load(f)
                    yield proj, finding
                except Exception:
                    continue

    def all_indexes(self):
        """Yield (project_info, index_dict) for every project with an index."""
        for proj in self.projects:
            pp = Path(proj["path"])
            idx = pp / "internal-audit-workspace" / "findings" / "index.json"
            if not idx.exists():
                idx = pp / "findings" / "index.json"
            if not idx.exists():
                continue
            try:
                with open(idx, "r", encoding="utf-8") as f:
                    yield proj, json.load(f)
            except Exception:
                continue

    def all_analyses(self):
        """Yield (project_info, analysis_dict) for every policy analysis."""
        for proj in self.projects:
            pp = Path(proj["path"])
            analyses_dir = pp / "internal-audit-workspace" / "policy-analyses"
            if not analyses_dir.exists():
                continue
            for fpath in sorted(analyses_dir.glob("*.json")):
                try:
                    with open(fpath, "r", encoding="utf-8-sig") as f:
                        yield proj, json.load(f)
                except Exception:
                    continue


# ── 查询命令 ──────────────────────────────────────────

def cmd_findings(args):
    """查询 findings — 支持 --cross-project"""
    # ── Cross-project mode ──
    if getattr(args, "cross_project", False):
        idx = load_projects_index()
        cps = CrossProjectSource(idx.get("projects", []))
        results = []
        for proj, finding in cps.all_findings():
            fid = finding.get("finding_id", "")
            title = finding.get("finding_title", finding.get("title", ""))
            rc = finding.get("risk_classification", {})
            risk = rc.get("risk_level", finding.get("risk_level", "-"))
            # Risk filter
            if args.risk:
                risk_label = {"高": "高", "中": "中", "低": "低"}
                if risk_label.get(args.risk) != risk:
                    continue
            # Status filter
            if args.status:
                status = finding.get("finding_metadata", {}).get("status", finding.get("status", "-"))
                status_map = {"待整改": "待整改", "整改中": "整改中", "已整改": "已整改", "延期": "延期"}
                target_status = status_map.get(args.status, args.status)
                if status != target_status:
                    continue
            # Year filter
            if args.year:
                fyear = fid.split("-")[1] if fid.startswith("F-") and "-" in fid else ""
                if fyear and fyear != str(args.year):
                    continue
            # Origin filter
            if args.by_origin:
                origin = finding.get("finding_metadata", {}).get("origin", finding.get("origin", "-"))
                if origin != args.by_origin:
                    continue
            # Keyword filter (by index)
            if args.keyword:
                kw_ids = set()
                for pi in idx.get("projects", []):
                    pp = Path(pi["path"])
                    idx_path = pp / "internal-audit-workspace" / "findings" / "index.json"
                    if not idx_path.exists():
                        idx_path = pp / "findings" / "index.json"
                    if idx_path.exists():
                        try:
                            with open(idx_path, "r", encoding="utf-8") as f:
                                pidx = json.load(f)
                            kw_ids.update(pidx.get("by_keyword", {}).get(args.keyword, []))
                        except Exception:
                            pass
                if kw_ids and fid not in kw_ids:
                    continue

            topic = proj.get("topic", "")
            results.append((topic, finding))

        if not results:
            print("🔍 跨项目查询：无匹配的 finding")
            return

        print(f"🔍 跨项目查询：{len(results)} 个 finding（{len(idx.get('projects', []))} 个项目）\n")
        print(f"  {'编号':<18} {'项目':<12} {'标题':<40} {'风险':<6} {'状态':<8}")
        print("  " + "-" * 90)
        hc = 0
        for topic, finding in results:
            fid = finding.get("finding_id", "")
            title = finding.get("finding_title", finding.get("title", ""))[:38]
            rc = finding.get("risk_classification", {})
            risk = rc.get("risk_level", finding.get("risk_level", "-"))
            status = finding.get("finding_metadata", {}).get("status", finding.get("status", "-"))
            if risk == "高":
                hc += 1
            print(f"  {fid:<18} {topic:<12} {title:<40} {risk:<6} {status:<8}")
        print(f"\n  共 {len(results)} 个，高风险 {hc} 个")
        return

    # ── Single-project mode (original) ──
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
    """比较不同年度的 finding — 支持 --cross-project（按主题跨项目对比）"""
    # ── Cross-project mode ──
    if getattr(args, "cross_project", False):
        idx = load_projects_index()
        cps = CrossProjectSource(idx.get("projects", []))
        topic_filter = args.topic

        from_year = str(args.from_year)
        to_year = str(args.to_year)

        from_findings = []
        to_findings = []
        projects_used = set()

        for proj, finding in cps.all_findings():
            ptopic = proj.get("topic", "")
            if topic_filter and topic_filter not in ptopic:
                continue
            fid = finding.get("finding_id", "")
            fyear = fid.split("-")[1] if fid.startswith("F-") and "-" in fid else ""
            if fyear == from_year:
                from_findings.append((proj, finding))
            elif fyear == to_year:
                to_findings.append((proj, finding))

        print(f"📋  跨项目审计对比：{topic_filter}（{from_year} → {to_year}）\n")
        print(f"    {from_year} 年 finding 数: {len(from_findings)}（{len(set(p['id'] for p,_ in from_findings))} 个项目）")
        print(f"    {to_year} 年 finding 数: {len(to_findings)}（{len(set(p['id'] for p,_ in to_findings))} 个项目）")

        # Repeat detection: title similarity across years/projects
        repeated = []
        for proj1, f1 in from_findings:
            t1 = f1.get("finding_title", "")
            for proj2, f2 in to_findings:
                t2 = f2.get("finding_title", "")
                words1 = set(t1.replace("，", "").replace(" ", ""))
                words2 = set(t2.replace("，", "").replace(" ", ""))
                if words1 and words2 and len(words1 & words2) / max(len(words1 | words2), 1) > 0.3:
                    repeated.append((f1.get("finding_id", ""), f2.get("finding_id", ""), t1[:30], t2[:30]))

        if repeated:
            print(f"\n  🔁 可能跨年重复的问题（{len(repeated)} 项）：")
            for fid1, fid2, t1, t2 in repeated[:10]:
                print(f"    {fid1:<16} → {fid2:<16} | {t1[:40]}")
            if len(repeated) > 10:
                print(f"    ... 还有 {len(repeated)-10} 项")
        else:
            print(f"\n  ✅ 未检测到跨年重复问题")

        # New in to_year (not similar to anything in from_year)
        all_from_titles = set()
        for _, f1 in from_findings:
            all_from_titles.add(f1.get("finding_title", ""))
        truly_new = []
        for proj2, f2 in to_findings:
            t2 = f2.get("finding_title", "")
            is_new = True
            for t1 in all_from_titles:
                words1 = set(t1.replace("，", "").replace(" ", ""))
                words2 = set(t2.replace("，", "").replace(" ", ""))
                if words1 and words2 and len(words1 & words2) / max(len(words1 | words2), 1) > 0.3:
                    is_new = False
                    break
            if is_new:
                rc = f2.get("risk_classification", {})
                risk = rc.get("risk_level", f2.get("risk_level", "-"))
                truly_new.append((f2.get("finding_id", ""), t2[:50], risk))

        if truly_new:
            print(f"\n  🆕 {to_year} 年新增问题（非重复，{len(truly_new)} 项）：")
            for fid, title, risk in truly_new[:15]:
                print(f"    - [{risk}] {fid}: {title}")
            if len(truly_new) > 15:
                print(f"    ... 还有 {len(truly_new)-15} 项")
        return

    # ── Single-project mode ──
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
    """输出汇总统计 — 支持 --cross-project"""
    # ── Cross-project mode ──
    if getattr(args, "cross_project", False):
        idx = load_projects_index()
        cps = CrossProjectSource(idx.get("projects", []))
        projects = idx.get("projects", [])
        print(f"📊  跨项目汇总（{len(projects)} 个注册项目）\n")

        total_findings = 0
        risk_counts = {"高": 0, "中": 0, "低": 0}
        status_counts = defaultdict(int)
        by_topic = defaultdict(lambda: {"count": 0, "high": 0})
        all_ids = []

        for proj, finding in cps.all_findings():
            total_findings += 1
            rc = finding.get("risk_classification", {})
            risk = rc.get("risk_level", finding.get("risk_level", "-"))
            status = finding.get("finding_metadata", {}).get("status", finding.get("status", "-"))
            if risk in risk_counts:
                risk_counts[risk] += 1
            status_counts[status] += 1
            topic = proj.get("topic", "未分类")
            by_topic[topic]["count"] += 1
            if risk == "高":
                by_topic[topic]["high"] += 1
            all_ids.append(finding.get("finding_id", ""))

        print(f"  总 finding 数: {total_findings}")
        print(f"  风险分布: 高={risk_counts['高']} 中={risk_counts['中']} 低={risk_counts['低']}")
        if status_counts:
            print(f"  状态分布: {dict(status_counts)}")
        print(f"\n  {'主题':<14} {'finding数':<12} {'高风险':<8}")
        print("  " + "-" * 36)
        for topic, stats in sorted(by_topic.items()):
            print(f"  {topic:<14} {stats['count']:<12} {stats['high']:<8}")

        # Trend: list projects by findings count descending
        print(f"\n  {'项目':<20} {'主题':<14} {'finding数':<10} {'阶段':<20}")
        print("  " + "-" * 68)
        for proj in projects:
            pp = Path(proj["path"])
            info = scan_project(str(pp))
            print(f"  {proj.get('id','?'):<20} {info.get('topic',''):<14} {info.get('findings_count',0):<10} {info.get('phase',''):<20}")

        return

    # ── Single-project mode ──
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


# ── 全文搜索 ──────────────────────────────────────────────

def search_in_json(obj, term, path=""):
    """递归搜索 JSON 对象中所有包含 term 的字符串字段，返回 [(field_path, context)]"""
    matches = []
    if isinstance(obj, str):
        if term in obj:
            # 截取匹配周围的上下文
            idx = obj.index(term)
            start = max(0, idx - 30)
            end = min(len(obj), idx + len(term) + 30)
            context = obj[start:end]
            if start > 0:
                context = "..." + context
            if end < len(obj):
                context = context + "..."
            matches.append((path, context))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            matches.extend(search_in_json(v, term, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            matches.extend(search_in_json(v, term, f"{path}[{i}]"))
    return matches


def cmd_search(args):
    """全文搜索 finding 正文 — 支持 --cross-project"""
    # ── Cross-project mode ──
    if getattr(args, "cross_project", False):
        idx = load_projects_index()
        cps = CrossProjectSource(idx.get("projects", []))
        term = args.term
        all_matches = []
        for proj, finding in cps.all_findings():
            matches = search_in_json(finding, term)
            if matches:
                fid = finding.get("finding_id", "")
                title = finding.get("finding_title", finding.get("title", ""))
                rc = finding.get("risk_classification", {})
                risk = rc.get("risk_level", finding.get("risk_level", "-"))
                topic = proj.get("topic", "")
                all_matches.append({"project": topic, "finding_id": fid, "title": title, "risk": risk, "matches": matches})

        if not all_matches:
            print(f"🔍 跨项目搜索「{term}」: 无匹配")
            return
        print(f"🔍 跨项目搜索「{term}」: {len(all_matches)} 个 finding 匹配\n")
        for r in all_matches:
            print(f"  📌 [{r['project']}] {r['finding_id']} [{r['risk']}] {r['title'][:50]}")
            for field_path, context in r["matches"][:3]:
                print(f"     {field_path}: {context[:80]}")
            if len(r["matches"]) > 3:
                print(f"     ... 还有 {len(r['matches']) - 3} 个匹配")
            print()
        print(f"共 {len(all_matches)} 个 finding 匹配「{term}」")
        return

    # ── Single-project mode ──
    findings_dir = get_findings_dir()
    if not findings_dir.exists():
        print("📂 findings/ 目录不存在")
        return

    term = args.term
    files = sorted(findings_dir.glob("F-*.json"))
    if not files:
        print("📂 findings/ 中无 finding 文件")
        return

    results = []
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            continue

        matches = search_in_json(data, term)
        if matches:
            fid = data.get("finding_id", fpath.stem)
            title = data.get("finding_title", data.get("title", ""))
            rc = data.get("risk_classification", {})
            risk = rc.get("risk_level", data.get("risk_level", "-"))
            results.append({"file": fpath.name, "finding_id": fid, "title": title, "risk": risk, "matches": matches})

    if not results:
        print(f"🔍 未找到包含「{term}」的 finding")
        return

    print(f"🔍 全文搜索「{term}」: {len(results)} 个 finding 匹配\n")
    for r in results:
        print(f"  📌 {r['finding_id']} [{r['risk']}] {r['title'][:50]}")
        for field_path, context in r["matches"][:5]:  # 每个 finding 最多显示 5 个匹配
            print(f"     {field_path}: {context[:80]}")
        if len(r["matches"]) > 5:
            print(f"     ... 还有 {len(r['matches']) - 5} 个匹配")
        print()

    print(f"共 {len(results)} 个 finding 匹配「{term}」")


def cmd_analyses(args):
    """查询制度分析结果"""
    analyses_dir = get_policy_analyses_dir()
    if not analyses_dir.exists():
        print("📂 policy-analyses/ 目录不存在")
        return

    files = sorted(analyses_dir.glob("*.json"))
    if not files:
        print("📂 policy-analyses/ 中无分析结果")
        return

    topic_filter = args.topic
    total_cp = 0
    total_gaps = 0
    total_risks = 0

    print(f"📋  制度分析查询（{len(files)} 份分析结果）\n")

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"  ⚠️ {fpath.name}: JSON 格式错误，跳过")
            continue

        # 按主题筛选
        if topic_filter and topic_filter not in fpath.stem:
            continue

        cps = data.get("control_points", [])
        gaps = data.get("control_gaps", [])
        risks = data.get("risk_points", [])
        summary = data.get("summary", {})

        total_cp += len(cps)
        total_gaps += len(gaps)
        total_risks += len(risks)

        print(f"  📄 {fpath.stem}")
        print(f"     控制点: {len(cps)} | 控制缺口: {len(gaps)} | 风险点: {len(risks)}")

        # 显示缺口详情
        if gaps and (args.gaps or args.verbose):
            for g in gaps:
                if isinstance(g, dict):
                    title = g.get("title", g.get("name", ""))
                    status = g.get("verification_status", "-")
                    severity = g.get("severity", g.get("risk_level", "-"))
                    print(f"       缺口: {title[:40]} [{severity}] 状态:{status}")

        # 显示高风险点
        if risks and args.verbose:
            high_risks = [r for r in risks if isinstance(r, dict)
                          and r.get("severity", r.get("risk_level", "")) in ("高", "high")]
            if high_risks:
                for r in high_risks:
                    print(f"       🔴 高风险: {r.get('title', r.get('name', ''))[:40]}")
        print()

    print(f"汇总: 控制点 {total_cp} 个, 控制缺口 {total_gaps} 个, 风险点 {total_risks} 个")


def cmd_register(args):
    """注册/管理审计项目到 projects-index.json"""
    idx = load_projects_index()
    projects = idx.get("projects", [])

    # ── --list ──
    if args.list:
        if not projects:
            print("📋 项目注册表为空。\n")
            print("注册新项目: python queries.py register --path <项目目录> --topic <主题> --period <期间>")
            return
        print(f"📋 已注册项目（{len(projects)} 个）\n")
        print(f"  {'ID':<14} {'主题':<14} {'期间':<12} {'finding数':<10} {'阶段':<22} {'路径'}")
        print("  " + "-" * 110)
        for p in projects:
            pid = p.get("id", "?")
            topic = p.get("topic", "")
            period = p.get("period", "")
            fc = p.get("findings_count", 0)
            phase = p.get("status", "?")
            path = p.get("path", "")
            print(f"  {pid:<14} {topic:<14} {period:<12} {fc:<10} {phase:<22} {path}")
        return

    # ── --remove ──
    if args.remove:
        target = args.remove
        before = len(projects)
        projects = [p for p in projects if p.get("id") != target]
        after = len(projects)
        if before == after:
            print(f"❌ 未找到项目 {target}")
            return
        idx["projects"] = projects
        save_projects_index(idx)
        print(f"🗑️  已移除: {target}（剩余 {after} 个项目）")
        return

    # ── --path (register) ──
    if args.path:
        path = Path(args.path).resolve()
        if not path.exists():
            print(f"❌ 目录不存在: {path}")
            return

        info = scan_project(str(path))
        topic = args.topic or info.get("topic", "")
        period = args.period or info.get("period", "")

        if not topic:
            print("⚠️  未检测到审计主题，请用 --topic 指定")
            return

        # Auto-generate ID if not provided
        if args.id:
            pid = args.id
        else:
            # Generate P-YYYY-NNN style ID
            existing = [p.get("id", "") for p in projects if p.get("id", "").startswith("P-")]
            num = 1
            yyyy = datetime.now().strftime("%Y")
            while f"P-{yyyy}-{num:03d}" in existing:
                num += 1
            pid = f"P-{yyyy}-{num:03d}"

        # Check if already registered
        for p in projects:
            if p.get("path") == str(path):
                # Update existing
                p.update({
                    "id": pid,
                    "topic": topic,
                    "period": period,
                    "path": str(path),
                    "findings_count": info.get("findings_count", 0),
                    "status": info.get("phase", "unknown"),
                    "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                })
                save_projects_index(idx)
                print(f"🔄 已更新注册: {pid} ({topic})")
                return

        # New registration
        projects.append({
            "id": pid,
            "topic": topic,
            "period": period,
            "path": str(path),
            "registered_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "findings_count": info.get("findings_count", 0),
            "status": info.get("phase", "unknown"),
        })
        idx["projects"] = projects
        save_projects_index(idx)
        print(f"✅ 已注册: {pid}")
        print(f"   主题: {topic}")
        print(f"   期间: {period}")
        print(f"   Finding: {info.get('findings_count', 0)} 个")
        print(f"   阶段: {info.get('phase', 'unknown')}")
        print(f"   路径: {path}")
        return

    # ── No args ──
    print("用法:")
    print("  python queries.py register --list                          列出已注册项目")
    print("  python queries.py register --path <目录> --topic <主题>      注册新项目")
    print("  python queries.py register --remove <PROJECT_ID>             删除项目注册")


def cmd_decide(args):
    """查询决策追溯链"""
    import importlib.util
    # decisions_schema.py is in the same directory
    spec = importlib.util.spec_from_file_location(
        "decisions_schema",
        os.path.join(os.path.dirname(__file__), "decisions_schema.py")
    )
    ds = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ds)
    DECISION_POINTS = ds.DECISION_POINTS

    ws = find_workspace()
    findings_dir = ws / "findings"

    # ── --all：列出所有决策点定义 ──
    if args.all:
        print("📋  9 个关键决策点\n")
        print(f"  {'ID':<8} {'决策点':<16} {'阶段':<28} {'生产者':<32}")
        print("  " + "-" * 86)
        for key, dp in DECISION_POINTS.items():
            print(f"  {key:<8} {dp['label']:<16} {dp['phase']:<28} {dp['produced_by']:<32}")
        print()
        print("查询单个决策: python queries.py decide D-003")
        print("查看决策链:   python queries.py decide F-2026-005")
        return

    # ── 按阶段筛选 ──
    if args.phase:
        phase = args.phase
        matched = [(k, dp) for k, dp in DECISION_POINTS.items() if dp["phase"] == phase]
        if not matched:
            print(f"📭 阶段 {phase} 无已注册的决策点")
            return
        print(f"📋  {phase} 的决策点 ({len(matched)} 个)\n")
        for key, dp in matched:
            print(f"  {key}  {dp['label']}")
            print(f"     问题: {dp['question']}")
            print(f"     生产者: {dp['produced_by']}")
            print()
        return

    # ── 无参数：提示用法 ──
    if not args.id_or_finding:
        print("📋  决策追溯查询\n")
        print("用法:")
        print("  python queries.py decide D-003          查看单个决策点定义")
        print("  python queries.py decide F-2026-005     查看 finding 的决策链")
        print("  python queries.py decide --phase phase_3_execution  按阶段查看")
        print("  python queries.py decide --all          列出所有决策点")
        return

    target = args.id_or_finding

    # ── 决策 ID 方式（D-YYYY-NNN）──
    if target.startswith("D-"):
        dp = DECISION_POINTS.get(target)
        if not dp:
            print(f"❌ 未知决策点: {target}")
            print(f"   可用: {', '.join(DECISION_POINTS.keys())}")
            return
        print(f"🔗 {target} — {dp['label']}")
        print(f"   阶段: {dp['phase']}")
        print(f"   问题: {dp['question']}")
        print(f"   生产者: {dp['produced_by']}")
        print()

        # 尝试从现有数据中查找该决策的实际记录
        decision_records = _collect_decision_logs(ws, findings_dir)
        matches = [d for d in decision_records if d.get("decision_id") == target]
        if matches:
            for m in matches:
                print(f"   ✅ 已记录")
                print(f"      决策结果: {m.get('decision', '(未填写)')}")
                rationale = m.get('rationale', '')
                print(f"      理由: {rationale[:120]}")
                if len(rationale) > 120:
                    print(f"           ... (+{len(rationale)-120}字)")
                refs = m.get('context_refs', [])
                if refs:
                    print(f"      依据: {', '.join(refs[:5])}")
                parents = m.get('parent_decisions', [])
                if parents:
                    print(f"      上游决策: {', '.join(parents)}")
                ts = m.get('timestamp', '')
                if ts:
                    print(f"      时间: {ts}")
                print()
        else:
            print(f"   ⚠️  尚未记录（当前审计项目中未找到该决策的记录）")
            print()

    # ── Finding ID 方式（F-YYYY-NNN）──
    elif target.startswith("F-"):
        finding = load_finding(target)
        if not finding:
            print(f"❌ 未找到 {target}")
            return
        title = finding.get("finding_title", finding.get("title", ""))
        print(f"🔗 决策追溯: {target} — {title[:50]}\n")

        # 收集所有相关的决策记录
        decision_records = _collect_decision_logs(ws, findings_dir)

        # 查找该 finding 涉及的决策
        related = []
        for d in decision_records:
            refs = d.get("context_refs", [])
            if any(target in str(r) for r in refs):
                related.append(d)

        if not related:
            print("  ⚠️  未找到与该 finding 关联的决策记录")
            print("  （decision_log 可能尚未在对应阶段产物中填写）")
            print()
            return

        # 按决策 ID 排序展示链
        related.sort(key=lambda x: x.get("decision_id", ""))

        print(f"  {'决策点':<10} {'决策结果':<20} {'阶段':<28} {'理由摘要'}")
        print(f"  " + "-" * 90)
        for d in related:
            did = d.get("decision_id", "?")
            dp = DECISION_POINTS.get(did, {})
            label = dp.get("label", did)
            decision = d.get("decision", "?")[:18]
            phase = d.get("phase", dp.get("phase", "?"))
            rationale = d.get("rationale", "")[:50]
            print(f"  {label:<10} {decision:<20} {phase:<28} {rationale}")

        print()

        # 检查决策链完整性
        found_ids = set(d.get("decision_id") for d in related)
        print("  决策链完整性:")
        D_CHAIN = ["D-001", "D-002", "D-003", "D-004", "D-005", "D-006", "D-007", "D-008", "D-009"]
        for did in D_CHAIN:
            dp = DECISION_POINTS.get(did, {})
            label = dp.get("label", did)
            if did in found_ids:
                print(f"    ✅ {did} {label}")
            else:
                print(f"    ❌ {did} {label} — 缺失（{dp.get('phase', '未知阶段')}）")

        print()
    else:
        print(f"❌ 无法识别 ID 格式: {target}")
        print("   决策 ID 格式: D-YYYY-NNN（如 D-003）")
        print("   Finding ID 格式: F-YYYY-NNN（如 F-2026-005）")


def _collect_decision_logs(ws, findings_dir):
    """从 workspace 各级产物中收集 decision_log 记录"""
    records = []

    # 从 current-audit.json 的 audit_state.decision_log
    audit_path = ws / "current-audit.json"
    if audit_path.exists():
        try:
            with open(audit_path, "r", encoding="utf-8-sig") as f:
                audit = json.load(f)
            state = audit.get("audit_state", {})
            dl = state.get("decision_log", [])
            if isinstance(dl, list):
                records.extend(dl)
        except Exception:
            pass

    # 从 findings 中提取 decision_log 引用
    if findings_dir.exists():
        for fpath in findings_dir.glob("F-*.json"):
            try:
                with open(fpath, "r", encoding="utf-8-sig") as f:
                    finding = json.load(f)
            except Exception:
                continue
            # 有些 finding 可能在 decision_rationale 中记录了决策上下文
            dr = finding.get("decision_rationale", {})
            if dr:
                # 构造一个拟 decision_log entry
                records.append({
                    "decision_id": "D-007",
                    "decision_point": "risk_classification",
                    "phase": "phase_3_execution",
                    "decision": finding.get("risk_classification", {}).get("risk_level", ""),
                    "rationale": dr.get("risk_level", dr.get("key_judgment", "")),
                    "context_refs": [finding.get("finding_id", "")],
                    "timestamp": finding.get("audit_date", ""),
                })

    return records


def cmd_trace(args):
    """跨实体追溯：finding ↔ design observation ↔ control point"""
    finding_id = args.finding_id
    findings_dir = get_findings_dir()
    assessments_dir = get_design_assessments_dir()

    # 读取目标 finding
    finding = load_finding(finding_id)
    if not finding:
        print(f"❌ 未找到 {finding_id}")
        return

    title = finding.get("finding_title", finding.get("title", ""))
    origin = finding.get("finding_metadata", {}).get("origin", finding.get("origin", "-"))
    obs_id = finding.get("design_observation_id", "")
    related_ctrl = finding.get("related_control", "")
    related_procs = finding.get("related_procedures", [])

    print(f"🔗 追溯: {finding_id} — {title[:50]}\n")

    # 基本关联
    print(f"  来源: {origin}")
    if obs_id:
        print(f"  关联设计观察: {obs_id}")
    if related_ctrl:
        print(f"  关联控制点: {related_ctrl}")
    if related_procs:
        print(f"  关联审计程序: {', '.join(related_procs)}")

    # 追溯设计观察
    if obs_id and assessments_dir.exists():
        for fpath in assessments_dir.glob("*.json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                continue
            observations = data.get("design_observations", data.get("observations", []))
            for obs in observations:
                if isinstance(obs, dict) and obs.get("id") == obs_id:
                    obs_title = obs.get("title", "")
                    obs_source = obs.get("source", "")
                    obs_status = obs.get("status", "")
                    print(f"\n  📋 设计观察 {obs_id}:")
                    print(f"     标题: {obs_title[:60]}")
                    print(f"     来源: {obs_source}")
                    print(f"     状态: {obs_status}")
                    break

    # 反向追溯：哪些 finding 关联了同一个控制点
    if related_ctrl:
        related_findings = []
        for fpath in findings_dir.glob("F-*.json"):
            if fpath.name == f"{finding_id}.json":
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    other = json.load(f)
            except json.JSONDecodeError:
                continue
            if other.get("related_control") == related_ctrl:
                other_id = other.get("finding_id", fpath.stem)
                other_title = other.get("finding_title", other.get("title", ""))[:40]
                related_findings.append((other_id, other_title))
        if related_findings:
            print(f"\n  🔁 同一控制点 {related_ctrl} 的其他 finding:")
            for fid, ft in related_findings:
                print(f"     {fid}: {ft}")

    # 反向追溯：哪些 finding 来自同一个设计观察
    if obs_id:
        related_findings = []
        for fpath in findings_dir.glob("F-*.json"):
            if fpath.name == f"{finding_id}.json":
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    other = json.load(f)
            except json.JSONDecodeError:
                continue
            if other.get("design_observation_id") == obs_id:
                other_id = other.get("finding_id", fpath.stem)
                other_title = other.get("finding_title", other.get("title", ""))[:40]
                related_findings.append((other_id, other_title))
        if related_findings:
            print(f"\n  🔁 同一设计观察 {obs_id} 的其他 finding:")
            for fid, ft in related_findings:
                print(f"     {fid}: {ft}")


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
    p_findings.add_argument("--cross-project", action="store_true", help="跨项目查询（需 projects-index.json）")

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
    p_compare.add_argument("--cross-project", action="store_true", help="跨项目对比（按主题跨项目）")

    # summary
    p_summary = sub.add_parser("summary", help="汇总统计")
    p_summary.add_argument("--cross-project", action="store_true", help="跨项目汇总")

    # search
    p_search = sub.add_parser("search", help="全文搜索 finding 正文")
    p_search.add_argument("term", help="搜索关键词")
    p_search.add_argument("--cross-project", action="store_true", help="跨项目搜索")

    # analyses
    p_analyses = sub.add_parser("analyses", help="查询制度分析结果")
    p_analyses.add_argument("--topic", help="按主题筛选")
    p_analyses.add_argument("--gaps", action="store_true", help="显示缺口详情")
    p_analyses.add_argument("--verbose", action="store_true", help="显示高风险点详情")

    # trace
    p_trace = sub.add_parser("trace", help="跨实体追溯")
    p_trace.add_argument("finding_id", help="Finding ID (如 F-2026-001)")

    # decide
    p_decide = sub.add_parser("decide", help="查询决策追溯链")
    p_decide.add_argument("id_or_finding", nargs="?", help="决策ID (D-YYYY-NNN) 或 finding ID (F-YYYY-NNN)")
    p_decide.add_argument("--phase", help="按阶段筛选 (如 phase_3_execution)")
    p_decide.add_argument("--all", action="store_true", help="显示所有决策点")

    # register
    p_register = sub.add_parser("register", help="注册/管理审计项目")
    p_register.add_argument("--path", help="项目目录路径")
    p_register.add_argument("--id", help="项目 ID（如 P-2026-001），注册时可选，删除时必填")
    p_register.add_argument("--topic", help="审计主题（注册时填写）")
    p_register.add_argument("--period", help="审计期间（如 2026-Q3）")
    p_register.add_argument("--list", action="store_true", help="列出所有已注册项目")
    p_register.add_argument("--remove", metavar="PROJECT_ID", help="删除指定项目注册")

    args = parser.parse_args()

    commands = {
        "findings": cmd_findings,
        "trend": cmd_trend,
        "compare": cmd_compare,
        "summary": cmd_summary,
        "search": cmd_search,
        "analyses": cmd_analyses,
        "trace": cmd_trace,
        "decide": cmd_decide,
        "register": cmd_register,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
