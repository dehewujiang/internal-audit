#!/usr/bin/env python3
"""
query_commands.py — 查询命令实现

将"怎么查"从"怎么路由"中分离。每个 cmd_* 函数对应一个 CLI 子命令。

[INPUT]:  argparse args + data sources
[OUTPUT]: 结构化查询结果（通过 query_display 格式化）
[POS]:    _shared/scripts 的命令层，被 queries.py CLI 入口调用
"""
import json
import os
import re
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from query_data_sources import (
    create_data_source, load_finding, load_evaluations,
    find_workspace, get_findings_dir, get_design_assessments_dir,
    get_policy_analyses_dir, get_audit_programs_dir, load_program_index,
    load_projects_index, save_projects_index, scan_project,
    search_in_json,
)
from query_display import (
    print_findings_table, print_decision_detail,
    print_control_point_details, print_program_steps_for_procedures,
    print_peer_steps, print_errata_list,
)


# ── 查询命令 ──────────────────────────────────────────

def cmd_findings(args):
    """查找 findings"""
    source = create_data_source(args)
    findings = source.query_findings(
        risk=args.risk, status=args.status,
        keyword=args.keyword, year=args.year,
        by_origin=args.by_origin,
    )
    print_findings_table(findings, source)


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

        idx = load_projects_index()
        projects = idx.get("projects", [])
        print(f"\n  {'项目':<20} {'主题':<14} {'finding数':<10} {'阶段':<22}")
        print("  " + "-" * 68)
        for proj in projects:
            pp = Path(proj["path"])
            info = scan_project(str(pp))
            print(f"  {proj.get('id','?'):<20} {info.get('topic',''):<14} {info.get('findings_count',0):<10} {info.get('phase',''):<22}")
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

        if args.id:
            pid = args.id
        else:
            existing = [p.get("id", "") for p in projects if p.get("id", "").startswith("P-")]
            num = 1
            yyyy = datetime.now().strftime("%Y")
            while f"P-{yyyy}-{num:03d}" in existing:
                num += 1
            pid = f"P-{yyyy}-{num:03d}"

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

    if target.startswith("D-"):
        dp = DECISION_POINTS.get(target)
        if not dp:
            print(f"❌ 未知决策点: {target}")
            print(f"   可用: {', '.join(DECISION_POINTS.keys())}")
            return
        decision_records = _collect_decision_logs(ws, findings_dir)
        print_decision_detail(dp, target, ws, findings_dir, decision_records)

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


# ── 实体追溯 ──────────────────────────────────────────

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


def _load_all_control_points():
    """一次性加载所有制度分析中的控制点"""
    analyses_dir = get_policy_analyses_dir()
    all_cps = {}
    if analyses_dir.exists():
        for fpath in analyses_dir.glob("*.json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                continue
            for cp in data.get("control_points", []):
                if isinstance(cp, dict) and cp.get("id"):
                    all_cps[cp["id"]] = cp
    return all_cps


def cmd_trace(args):
    """跨实体追溯：finding ↔ design observation ↔ control point ↔ 审计程序步骤"""
    target = args.target

    if target.startswith("F-"):
        _trace_finding(target)
    elif target.startswith("CP-") or target.startswith("RK-"):
        _trace_control_point(target)
    else:
        _trace_program_step(target)


def _trace_finding(finding_id):
    """Finding 追溯链"""
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
                    print(f"\n  📋 设计观察 {obs_id}:")
                    print(f"     标题: {obs.get('title', '')[:60]}")
                    print(f"     来源: {obs.get('source', '')}")
                    print(f"     状态: {obs.get('status', '')}")
                    break

    if related_procs:
        index = load_program_index()
        steps = index.get("steps", [])
        matched = []
        for proc_ref in related_procs:
            ref_upper = proc_ref.upper().strip()
            for step in steps:
                sid = step.get("step_id", "").upper()
                title_s = step.get("title", "").upper()
                if ref_upper in sid or ref_upper in title_s:
                    matched.append(step)
        print_program_steps_for_procedures(matched)

    if related_ctrl:
        related_findings = _find_related_findings(findings_dir, finding_id,
                                                   lambda other: other.get("related_control") == related_ctrl)
        if related_findings:
            print(f"\n  🔁 同一控制点 {related_ctrl} 的其他 finding:")
            for fid, ft in related_findings:
                print(f"     {fid}: {ft}")

    if obs_id:
        related_findings = _find_related_findings(findings_dir, finding_id,
                                                   lambda other: other.get("design_observation_id") == obs_id)
        if related_findings:
            print(f"\n  🔁 同一设计观察 {obs_id} 的其他 finding:")
            for fid, ft in related_findings:
                print(f"     {fid}: {ft}")


def _trace_program_step(step_id):
    """审计程序步骤追溯"""
    index = load_program_index()
    steps = index.get("steps", [])

    if not steps:
        print("📋 未找到审计程序索引文件。")
        print("   审计程序索引（program_index.json）由 program-generator 在 Step 4 输出时生成。")
        print("   如果审计程序已生成但没有索引，请重新运行 program-generator。")
        return

    normalized = step_id.replace("-", "").replace(".", "").upper()
    matched = None
    for step in steps:
        sid = step.get("step_id", "").replace("-", "").replace(".", "").upper()
        if sid == normalized:
            matched = step
            break

    if not matched:
        prefix_matches = [s for s in steps if s.get("step_id", "").upper().startswith(step_id.upper())]
        if len(prefix_matches) == 1:
            matched = prefix_matches[0]
        elif len(prefix_matches) > 1:
            print(f"🔍 步骤 ID「{step_id}」匹配到 {len(prefix_matches)} 个结果：")
            for s in prefix_matches:
                print(f"   {s.get('step_id', '?')}: {s.get('title', '')[:50]}")
            print(f"\n请使用更精确的 ID。")
            return

    if not matched:
        print(f"❌ 未找到审计程序步骤「{step_id}」")
        available = [s.get("step_id", "") for s in steps[:10]]
        if available:
            print(f"   可用步骤: {', '.join(available)}{'...' if len(steps) > 10 else ''}")
        return

    sid = matched.get("step_id", "")
    title = matched.get("title", "")
    track = matched.get("track", "")
    risk_ref = matched.get("risk_ref", "")
    controls = matched.get("related_controls", [])
    observations = matched.get("related_design_observations", [])
    data_source = matched.get("data_source", "")
    test_method = matched.get("test_method", "")

    print(f"🔗 审计程序步骤: {sid} — {title}\n")
    print(f"  轨道: {track}")
    if risk_ref:
        print(f"  风险编号: {risk_ref}")
    if test_method:
        print(f"  测试方法: {test_method}")
    if data_source:
        print(f"  数据来源: {data_source}")

    if controls:
        print(f"\n  📎 关联控制点 ({len(controls)} 个):")
        all_cps = _load_all_control_points()
        print_control_point_details(controls, all_cps)

    if observations:
        print(f"\n  📋 关联设计观察: {', '.join(observations)}")

    if controls:
        print_peer_steps(sid, controls, steps)


def _trace_control_point(cp_id):
    """控制点追溯"""
    print(f"🔗 控制点追溯: {cp_id}\n")

    all_cps = _load_all_control_points()
    found_cp = all_cps.get(cp_id)

    if found_cp:
        print(f"  制度来源: {found_cp.get('source_file', '')} — {found_cp.get('source', '')}")
        print(f"  控制类型: {found_cp.get('type', '')}")
        print(f"  风险等级: {found_cp.get('risk_level', '')}")
        req = found_cp.get("requirement", "")
        if req:
            print(f"  制度要求: {req[:100]}")
    else:
        print(f"  ⚠️  未在制度分析中找到 {cp_id}")

    index = load_program_index()
    steps = index.get("steps", [])
    related_steps = [s for s in steps if cp_id in s.get("related_controls", [])]
    if related_steps:
        print(f"\n  📎 引用该控制点的审计程序步骤 ({len(related_steps)} 个):")
        for s in related_steps:
            print(f"     {s.get('step_id', '?')} [{s.get('track', '')}]: {s.get('title', '')[:50]}")
    else:
        print(f"\n  📎 审计程序索引中无引用该控制点的步骤")

    findings_dir = get_findings_dir()
    if findings_dir.exists():
        related_findings = _find_related_findings(findings_dir, "",
                                                   lambda other: other.get("related_control") == cp_id)
        if related_findings:
            print(f"\n  📌 关联 findings ({len(related_findings)} 个):")
            for fid, ft in related_findings:
                print(f"     {fid}: {ft}")


# ── 勘误查询 ──────────────────────────────────────────

def cmd_errata(args):
    """查询审计程序勘误记录

    从三个来源收集勘误信息：
    1. 审计程序 Markdown 中的勘误注记（⚠️ 勘误）
    2. program_index.json 中的 errata 标记
    3. decision_log 中的程序勘误决策
    """
    ws = find_workspace()
    programs_dir = get_audit_programs_dir()
    findings_dir = ws / "findings"

    errata_items = []

    # 来源 1：program_index.json 中的 errata 标记
    index = load_program_index()
    for step in index.get("steps", []):
        if step.get("errata"):
            errata_items.append({
                "step_id": step.get("step_id", "?"),
                "correction": step.get("corrects", "-") + " → " + step.get("step_id", "?") if step.get("corrects") else "-",
                "reason": step.get("errata_reason", ""),
                "date": step.get("errata_date", "-"),
                "source": "program_index",
            })

    # 来源 2：decision_log 中的程序勘误
    DECISION_POINTS = _load_decisions_schema()
    decision_records = _collect_decision_logs(ws, findings_dir)
    for d in decision_records:
        if d.get("decision_id", "").startswith("D-") and "勘误" in d.get("decision_point", ""):
            errata_items.append({
                "step_id": d.get("context_refs", ["?"])[0] if d.get("context_refs") else "?",
                "correction": d.get("decision", ""),
                "reason": d.get("rationale", ""),
                "date": d.get("timestamp", "-")[:10],
                "source": "decision_log",
            })

    # 来源 3：审计程序 Markdown 中的勘误注记
    if programs_dir.exists():
        errata_pattern = re.compile(r"⚠️\s*勘误.*?：(.+?)(?:\n|$)")
        step_pattern = re.compile(r"\|\s*([A-F][\d.]+(?:-C)?)\s*\|")
        for md_path in sorted(programs_dir.glob("*.md")):
            try:
                content = md_path.read_text(encoding="utf-8")
            except Exception:
                continue
            for match in errata_pattern.finditer(content):
                reason = match.group(1).strip()
                # 尝试从勘误行前的表格行找到步骤 ID
                pos = match.start()
                preceding = content[max(0, pos - 500):pos]
                step_matches = step_pattern.findall(preceding)
                step_id = step_matches[-1] if step_matches else "?"
                # 检查是否已在 program_index 中记录（去重）
                already_indexed = any(
                    e.get("source") == "program_index" and e.get("reason", "")[:20] == reason[:20]
                    for e in errata_items
                )
                if not already_indexed:
                    errata_items.append({
                        "step_id": step_id,
                        "correction": "-",
                        "reason": reason,
                        "date": "-",
                        "source": "markdown",
                    })

    # 去重（按 step_id + reason 前 20 字）
    seen = set()
    deduped = []
    for item in errata_items:
        key = (item.get("step_id", ""), item.get("reason", "")[:20])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    print_errata_list(deduped)
