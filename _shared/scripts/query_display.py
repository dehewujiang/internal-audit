#!/usr/bin/env python3
"""
query_display.py — 查询结果显示格式化

将"数据长什么样"从"怎么查"中分离。纯显示逻辑，不含数据访问。

[INPUT]:  结构化数据（list/dict）
[OUTPUT]: 格式化文本输出到 stdout
[POS]:    _shared/scripts 的显示层，被 query_commands.py 调用
"""
from collections import defaultdict


def print_findings_table(findings, source):
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


def print_decision_detail(dp, target, ws, findings_dir, decision_records):
    """Print detail for a single decision point"""
    print(f"🔗 {target} — {dp['label']}")
    print(f"   阶段: {dp['phase']}")
    print(f"   问题: {dp['question']}")
    print(f"   生产者: {dp['produced_by']}")
    print()

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


def print_control_point_details(control_ids, all_cps):
    """打印控制点详情"""
    for cid in control_ids:
        cp = all_cps.get(cid)
        if cp:
            source = cp.get("source", "")
            source_file = cp.get("source_file", "")
            requirement = cp.get("requirement", "")
            print(f"     {cid}: {source_file} — {source}")
            if requirement:
                print(f"       制度要求: {requirement[:80]}")
        else:
            print(f"     {cid}: (未在制度分析中找到)")


def print_program_steps_for_procedures(matched_steps):
    """打印匹配的审计程序步骤"""
    if not matched_steps:
        return
    print(f"\n  📎 审计程序步骤详情 ({len(matched_steps)} 个):")
    for s in matched_steps:
        sid = s.get("step_id", "?")
        title = s.get("title", "")[:50]
        track = s.get("track", "")
        controls = s.get("related_controls", [])
        print(f"     {sid} [{track}]: {title}")
        if controls:
            print(f"       关联控制点: {', '.join(controls)}")


def print_peer_steps(exclude_step_id, control_ids, all_steps):
    """打印同一控制点的其他审计程序步骤"""
    peers = []
    for s in all_steps:
        sid = s.get("step_id", "")
        if sid == exclude_step_id:
            continue
        s_controls = set(s.get("related_controls", []))
        if s_controls & set(control_ids):
            peers.append(s)

    if peers:
        print(f"\n  🔁 同一控制点的其他审计程序步骤:")
        for s in peers:
            sid = s.get("step_id", "?")
            title = s.get("title", "")[:50]
            track = s.get("track", "")
            print(f"     {sid} [{track}]: {title}")


def print_errata_list(errata_items):
    """格式化输出勘误记录列表"""
    if not errata_items:
        print("📋 无勘误记录")
        return

    print(f"📋 勘误记录（{len(errata_items)} 条）\n")
    print(f"  {'步骤':<12} {'修正步骤':<12} {'原因':<50} {'日期':<12} {'来源':<10}")
    print("  " + "-" * 100)

    for item in errata_items:
        step_id = item.get("step_id", "?")
        correction = item.get("correction", "-")
        reason = item.get("reason", "")[:48]
        date = item.get("date", "-")
        source = item.get("source", "-")
        print(f"  {step_id:<12} {correction:<12} {reason:<50} {date:<12} {source:<10}")
