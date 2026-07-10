#!/usr/bin/env python3
"""
queries.py — 审计数据查询工具

读取 findings/index.json + evaluator JSONL 历史，提供查询和分析能力。
在任何阶段都可调用，支持按风险/状态/关键词/年度/来源筛选 findings。
支持 --cross-project 跨项目查询（需 projects-index.json）。

[INPUT]:  findings/index.json + findings/F-*.json + evaluator JSONL + projects-index.json
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
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# 数据源层 — "数据从哪来"与"怎么查/怎么显示"分离
from query_data_sources import (
    create_data_source, load_finding, load_evaluations,
    find_workspace, get_findings_dir, get_design_assessments_dir,
    get_policy_analyses_dir, load_projects_index, save_projects_index, scan_project,
    search_in_json,
)


# ── 公共格式化函数 ──────────────────────────────────────

def _print_findings_table(findings, source):
    """格式化输出 findings 表格 — 被 findings/summary 等命令共用"""
    if not findings:
        print(f"🔍 {source.name}：无匹配的 finding")
        return

    if source.is_cross_project:
        print(f"🔍 {source.name}：{len(findings)} 个 finding\n")
        print(f"  {'编号':<18} {'项目':<12} {'标题':<40} {'风险':<6} {'状态':<8}")
        print("  " + "-" * 90)
        high_count = 0
        for finding in findings:
            fid = finding.get("finding_id", "")
            title = finding.get("finding_title", finding.get("title", ""))[:38]
            rc = finding.get("risk_classification", {})
            risk = rc.get("risk_level", finding.get("risk_level", "-"))
            status = finding.get("finding_metadata", {}).get("status", finding.get("status", "-"))
            project = finding.get("_project", "")
            if risk == "高":
                high_count += 1
            print(f"  {fid:<18} {project:<12} {title:<40} {risk:<6} {status:<8}")
        print(f"\n  共 {len(findings)} 个，高风险 {high_count} 个")
    else:
        print(f"\n{'编号':<20} {'标题':<40} {'风险':<6} {'状态':<8} {'来源':<10}")
        print("-" * 90)

        high_count = 0
        status_dist = defaultdict(int)
        for finding in findings:
            fid = finding.get("finding_id", "")
            title = finding.get("finding_title", finding.get("title", ""))[:38]
            rc = finding.get("risk_classification", {})
            risk = rc.get("risk_level", "-")
            status = finding.get("finding_metadata", {}).get("status", "-")
            origin = finding.get("finding_metadata", {}).get("origin", "-")

            if risk == "高":
                high_count += 1
            status_dist[status] += 1

            print(f"{fid:<20} {title:<40} {risk:<6} {status:<8} {origin:<10}")

        print(f"\n共 {len(findings)} 个 finding，其中高风险 {high_count} 个")
        if status_dist:
            print("状态分布：", ", ".join(f"{k}={v}" for k, v in sorted(status_dist.items())))


# ── 查询命令 ──────────────────────────────────────────

def cmd_findings(args):
    """查找 findings"""
    source = create_data_source(args)
    findings = source.query_findings(
        risk=args.risk, status=args.status,
        keyword=args.keyword, year=args.year,
        by_origin=args.by_origin,
    )
    _print_findings_table(findings, source)


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
    from_year = args.from_year
    to_year = args.to_year
    source = create_data_source(args)

    print(f"📋  {source.name}审计对比：{args.topic}（{from_year} → {to_year}）\n")

    data = source.compare_years(args.topic, from_year, to_year)
    if data is None:
        print("  无数据可比较")
        return

    print(f"    {from_year} 年 finding 数: {data['from_count']}")
    print(f"    {to_year} 年 finding 数: {data['to_count']}")

    repeated = data.get("repeated", [])
    if repeated:
        print(f"\n  🔁 可能重复的问题（{len(repeated)} 项）：")
        if source.is_cross_project:
            for fid1, fid2, t1, t2 in repeated[:10]:
                print(f"    {fid1:<16} → {fid2:<16} | {t1[:40]}")
            if len(repeated) > 10:
                print(f"    ... 还有 {len(repeated) - 10} 项")
        else:
            print(f"    {'去年 ID':<16} {'今年 ID':<16} {'去年标题':<32} {'今年标题':<32}")
            print("    " + "-" * 96)
            for fid1, fid2, t1, t2 in repeated:
                f2 = load_finding(fid2)
                status = f2.get("finding_metadata", {}).get("status", "") if f2 else ""
                print(f"    {fid1:<16} {fid2:<16} {t1:<32} {t2:<32}\n    {'':>32} 状态: {status}")
    else:
        print(f"\n  ✅ 未检测到重复问题（或标题差异大，建议人工核对）")

    truly_new = data.get("new", [])
    if truly_new:
        print(f"\n  🆕 {to_year} 年新增问题（非重复，{len(truly_new)} 项）：")
        for item in truly_new[:15]:
            fid, title, risk = item
            print(f"    - [{risk}] {fid}: {title}")
        if len(truly_new) > 15:
            print(f"    ... 还有 {len(truly_new) - 15} 项")


def cmd_summary(args):
    """汇总统计"""
    source = create_data_source(args)
    data = source.summary()

    if data is None:
        print("📂 暂无数据")
        return

    if source.is_cross_project:
        print(f"📊  {source.name}\n")
        print(f"  总 finding 数: {data['total']}")
        rc = data.get("risk_counts", {})
        print(f"  风险分布: 高={rc.get('高', 0)} 中={rc.get('中', 0)} 低={rc.get('低', 0)}")
        if data.get("status_counts"):
            print(f"  状态分布: {data['status_counts']}")
        by_topic = data.get("by_topic", {})
        if by_topic:
            print(f"\n  {'主题':<14} {'finding数':<12} {'高风险':<8}")
            print("  " + "-" * 36)
            for topic, stats in sorted(by_topic.items()):
                print(f"  {topic:<14} {stats['count']:<12} {stats['high']:<8}")

        # Per-project listing
        idx = load_projects_index()
        projects = idx.get("projects", [])
        print(f"\n  {'项目':<20} {'主题':<14} {'finding数':<10} {'阶段':<20}")
        print("  " + "-" * 68)
        for proj in projects:
            pp = Path(proj["path"])
            info = scan_project(str(pp))
            print(f"  {proj.get('id','?'):<20} {info.get('topic',''):<14} {info.get('findings_count',0):<10} {info.get('phase',''):<20}")
    else:
        print(f"📊  Finding 汇总\n")
        print(f"    总数: {data['total']}")
        print(f"    风险分布: 高={data['by_risk'].get('高',0)} 中={data['by_risk'].get('中',0)} 低={data['by_risk'].get('低',0)}")
        print(f"    状态分布: ", ", ".join(f"{k}={v}" for k, v in data['by_status'].items()))
        print(f"    来源分布: design={data['by_origin'].get('design',0)} execution={data['by_origin'].get('execution',0)}")
        print(f"    年度分布: ", ", ".join(f"{y}={c}" for y, c in data['by_year'].items()))

        if data.get("eval_avg") is not None:
            print(f"\n    📈 评估历史（90天）: {data['eval_count']} 条记录，平均分 {data['eval_avg']:.1f}/10")


def cmd_search(args):
    """全文搜索 finding 正文"""
    source = create_data_source(args)
    term = args.term
    results = source.search(term)

    if not results:
        print(f"🔍 {source.name}搜索「{term}」: 无匹配")
        return

    print(f"🔍 {source.name}搜索「{term}」: {len(results)} 个 finding 匹配\n")
    for r in results:
        project_tag = f" [{r.get('_project', '')}]" if source.is_cross_project else ""
        print(f"  📌{project_tag} {r['finding_id']} [{r['risk']}] {r['title'][:50]}")
        max_per_finding = 3 if source.is_cross_project else 5
        for field_path, context in r["matches"][:max_per_finding]:
            print(f"     {field_path}: {context[:80]}")
        if len(r["matches"]) > max_per_finding:
            print(f"     ... 还有 {len(r['matches']) - max_per_finding} 个匹配")
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

        if gaps and (args.gaps or args.verbose):
            for g in gaps:
                if isinstance(g, dict):
                    title = g.get("title", g.get("name", ""))
                    status = g.get("verification_status", "-")
                    severity = g.get("severity", g.get("risk_level", "-"))
                    print(f"       缺口: {title[:40]} [{severity}] 状态:{status}")

        if risks and args.verbose:
            high_risks = [r for r in risks if isinstance(r, dict)
                          and r.get("severity", r.get("risk_level", "")) in ("高", "high")]
            if high_risks:
                for r in high_risks:
                    print(f"       🔴 高风险: {r.get('title', r.get('name', ''))[:40]}")
        print()

    print(f"汇总: 控制点 {total_cp} 个, 控制缺口 {total_gaps} 个, 风险点 {total_risks} 个")


def cmd_register(args):
    """注册/管理审计项目"""
    idx = load_projects_index()
    projects = idx.get("projects", [])

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
            existing = [p.get("id", "") for p in projects if p.get("id", "").startswith("P-")]
            num = 1
            yyyy = datetime.now().strftime("%Y")
            while f"P-{yyyy}-{num:03d}" in existing:
                num += 1
            pid = f"P-{yyyy}-{num:03d}"

        # Update existing or create new
        for p in projects:
            if p.get("path") == str(path):
                p.update({
                    "id": pid, "topic": topic, "period": period,
                    "path": str(path),
                    "findings_count": info.get("findings_count", 0),
                    "status": info.get("phase", "unknown"),
                    "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                })
                save_projects_index(idx)
                print(f"🔄 已更新注册: {pid} ({topic})")
                return

        projects.append({
            "id": pid, "topic": topic, "period": period,
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

    print("用法:")
    print("  python queries.py register --list                          列出已注册项目")
    print("  python queries.py register --path <目录> --topic <主题>      注册新项目")
    print("  python queries.py register --remove <PROJECT_ID>             删除项目注册")


# ── 决策追溯 ──────────────────────────────────────────

def _load_decisions_schema():
    """动态加载 decisions_schema.py"""
    spec = importlib.util.spec_from_file_location(
        "decisions_schema",
        os.path.join(os.path.dirname(__file__), "decisions_schema.py")
    )
    ds = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ds)
    return ds.DECISION_POINTS


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
            dr = finding.get("decision_rationale", {})
            if dr:
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


def _print_decision_detail(dp, target, ws, findings_dir):
    """Print detail for a single decision point"""
    print(f"🔗 {target} — {dp['label']}")
    print(f"   阶段: {dp['phase']}")
    print(f"   问题: {dp['question']}")
    print(f"   生产者: {dp['produced_by']}")
    print()

    decision_records = _collect_decision_logs(ws, findings_dir)
    matches = [d for d in decision_records if d.get("decision_id") == target]
    if matches:
        for m in matches:
            print(f"   ✅ 已记录")
            print(f"      决策结果: {m.get('decision', '(未填写)')}")
            rationale = m.get('rationale', '')
            print(f"      理由: {rationale[:120]}")
            if len(rationale) > 120:
                print(f"           ... (+{len(rationale) - 120}字)")
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


def cmd_decide(args):
    """查询决策追溯链"""
    DECISION_POINTS = _load_decisions_schema()
    ws = find_workspace()
    findings_dir = ws / "findings"

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

    if not args.id_or_finding:
        print("📋  决策追溯查询\n")
        print("用法:")
        print("  python queries.py decide D-003          查看单个决策点定义")
        print("  python queries.py decide F-2026-005     查看 finding 的决策链")
        print("  python queries.py decide --phase phase_3_execution  按阶段查看")
        print("  python queries.py decide --all          列出所有决策点")
        return

    target = args.id_or_finding

    # 决策 ID 方式（D-YYYY-NNN）
    if target.startswith("D-"):
        dp = DECISION_POINTS.get(target)
        if not dp:
            print(f"❌ 未知决策点: {target}")
            print(f"   可用: {', '.join(DECISION_POINTS.keys())}")
            return
        _print_decision_detail(dp, target, ws, findings_dir)

    # Finding ID 方式（F-YYYY-NNN）
    elif target.startswith("F-"):
        finding = load_finding(target)
        if not finding:
            print(f"❌ 未找到 {target}")
            return
        title = finding.get("finding_title", finding.get("title", ""))
        print(f"🔗 决策追溯: {target} — {title[:50]}\n")

        decision_records = _collect_decision_logs(ws, findings_dir)

        related = [d for d in decision_records if any(target in str(r) for r in d.get("context_refs", []))]

        if not related:
            print("  ⚠️  未找到与该 finding 关联的决策记录")
            print("  （decision_log 可能尚未在对应阶段产物中填写）")
            print()
            return

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

        # 决策链完整性检查
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


def cmd_trace(args):
    """跨实体追溯：finding ↔ design observation ↔ control point"""
    finding_id = args.finding_id
    findings_dir = get_findings_dir()
    assessments_dir = get_design_assessments_dir()

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

    # 反向追溯：同一控制点的其他 finding
    if related_ctrl:
        related_findings = _find_related_findings(findings_dir, finding_id,
                                                   lambda other: other.get("related_control") == related_ctrl)
        if related_findings:
            print(f"\n  🔁 同一控制点 {related_ctrl} 的其他 finding:")
            for fid, ft in related_findings:
                print(f"     {fid}: {ft}")

    # 反向追溯：同一设计观察的其他 finding
    if obs_id:
        related_findings = _find_related_findings(findings_dir, finding_id,
                                                   lambda other: other.get("design_observation_id") == obs_id)
        if related_findings:
            print(f"\n  🔁 同一设计观察 {obs_id} 的其他 finding:")
            for fid, ft in related_findings:
                print(f"     {fid}: {ft}")


def _find_related_findings(findings_dir, exclude_id, predicate):
    """Find findings matching predicate, excluding the given ID. Returns [(id, title)] list."""
    related = []
    for fpath in findings_dir.glob("F-*.json"):
        if fpath.name == f"{exclude_id}.json":
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                other = json.load(f)
        except json.JSONDecodeError:
            continue
        if predicate(other):
            other_id = other.get("finding_id", fpath.stem)
            other_title = other.get("finding_title", other.get("title", ""))[:40]
            related.append((other_id, other_title))
    return related


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
