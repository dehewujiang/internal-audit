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


def _cell_lines(text):
    return [x for x in (text or "").split("；") if x.strip()]


def print_table_card(path, table):
    """一张桌子：三格几条 + 抽屉状态 + 证据几条"""
    print(f"🗂️  桌子：{table.get('table', path.stem)}\n")
    for x in table.get("left", []):
        n = len(_cell_lines(x.get("text", "")))
        refs = len(x.get("ref_finding_ids", []))
        print(f"  {x.get('slot', '?')}: {n} 条（对单 {refs} 张）")
    print(f"  右边证据: {len(table.get('right', []))} 条")
    print(f"\n  抽屉:")
    for d in table.get("drawers", []):
        status = d.get("status") or "空"
        print(f"    {d.get('name', '?')}: {status}")
    print(f"\n  收料本子: {len(table.get('ingested', {}))} 条机器行")


def print_evidence_card(catalog):
    """证据柜：总数/已收/没主的槽点名"""
    items = catalog.get("items", [])
    filled = [it for it in items if it.get("file")]
    orphans = [it for it in items if not (it.get("source_programs") or [])]
    print(f"🗄️  证据柜：共 {len(items)} 槽，已收 {len(filled)} 槽\n")
    if orphans:
        print(f"  没主的槽（{len(orphans)} 个）:")
        for it in orphans:
            print(f"    {it.get('id', '?')}: {it.get('name', '')[:40]}")
    else:
        print("  个个槽都有主")


def print_status_card(audit):
    """状态账本：一句话看到哪了"""
    st = audit.get("audit_state", {})
    print(f"📍 状态：{audit.get('status', '未知阶段')}\n")
    print(f"  程序版本: {st.get('program_version', audit.get('program_version', '未记'))}")
    consumed = st.get("design_observations_consumed", "-")
    print(f"  问话消化完: {consumed}")
    wb = st.get("whistleblower_pending") or []
    print(f"  举报待办: {len(wb)} 条")
    progs = st.get("programs", {})
    print(f"  现场加菜: 新增 {len(progs.get('added', []))} 条、"
          f"停用 {len(progs.get('deferred', []))} 条")
    hist = st.get("sweep_history") or []
    if hist:
        last = hist[-1]
        print(f"  上次收料: {last.get('at', '?')} "
              f"(新增{last.get('added', 0)}条、挪格{last.get('moved', 0)}条)")
    else:
        print("  上次收料: 还没收过")


def print_lineage_card(b):
    """来龙去脉卡：八段一次看全"""
    print(f"🔗 来龙去脉：{b['finding_id']} — {b['title'][:50]}")
    print(f"  风险{b['risk']}｜状态{b['status']}｜来源{b['origin']}\n")
    print("  一、来路")
    if b["obs"]:
        print(f"    设计观察 {b['obs_id']}：{b['obs']['title'][:40]}")
        if b["obs"]["snippet"]:
            print(f"    原文一句话：{b['obs']['snippet']}")
    elif b["obs_id"]:
        print(f"    设计观察 {b['obs_id']}（纸还没落）")
    else:
        print("    直接执行发现，无设计观察号")
    print("  二、程序")
    if b["steps"]:
        for s in b["steps"]:
            print(f"    {s.get('step_id', '?')} [{s.get('track', '')}]："
                  f"{s.get('title', '')[:40]}")
            for n in s.get("_notes", []):
                print(f"      ⚠️ {n}")
    else:
        print("    没关联程序号")
    print("  三、证据")
    if b["evidence"]:
        for e in b["evidence"]:
            print(f"    {e['name'][:40]}｜{e['source']}给｜{e['when']}｜{e['grade']}级")
    if b["gap"]:
        print(f"    ⚠️ 还有缺口，先按三个方向问："
              f"{' / '.join(['业务未发生', '管理缺失未留痕', '证据被消除'])}")
    if not b["evidence"] and not b["gap"]:
        print("    无")
    print("  四、桌位")
    if b["slot"]:
        print(f"    摆在「{b['slot']}」" + ("，已对单✓" if b["linked"] else ""))
    else:
        print("    还没上桌")
    print("  五、控制点")
    if b["related_ctrl"]:
        print(f"    {b['related_ctrl']}", end="")
        if b["ctrl_detail"]:
            print(f"（{b['ctrl_detail'].get('source_file', '')}）")
        else:
            print("（制度分析里没找到）")
    else:
        print("    没关联控制点")
    print("  六、同源")
    for fid, ft in (b["same_ctrl"] + b["same_obs"]):
        print(f"    {fid}：{ft}")
    if not (b["same_ctrl"] + b["same_obs"]):
        print("    无")
    print("  七、决定")
    if b["decisions"]:
        for d in b["decisions"]:
            print(f"    {d.get('decision_id', '?')}：{d.get('decision', '')[:40]}")
    else:
        print("    还没记相关决定")


def print_brief_card(b):
    """沟通发言稿：四段一次念完"""
    print(f"🎙️ 沟通卡：{b['finding_id']} — {b['title'][:50]}\n")
    print("  一、从哪里来")
    if b["obs"]:
        print(f"    {b['obs']['title'][:40]}：{b['obs']['snippet']}")
    else:
        print(f"    来源{b['origin']}，{b['title'][:60]}")
    print("  二、执行了什么程序")
    if b["steps"]:
        for s in b["steps"]:
            print(f"    {s.get('step_id', '?')}：{s.get('title', '')[:40]}")
            for n in s.get("_notes", []):
                print(f"      ⚠️ {n}")
    else:
        print("    没关联程序号")
    print("  三、拿到什么证据")
    if b["evidence"]:
        for e in b["evidence"]:
            print(f"    {e['name'][:40]}｜{e['source']}给｜{e['when']}｜{e['grade']}级")
    if b["gap"]:
        print(f"    ⚠️ 还有缺口，先按三个方向问："
              f"{' / '.join(['业务未发生', '管理缺失未留痕', '证据被消除'])}")
    print("  四、得出什么发现")
    print(f"    依据：{b['criteria'][:60]}")
    print(f"    现状：{b['condition'][:60]}")
    print(f"    根因：{b['cause'][:60]}")
    print(f"    影响建议：{b['consequence'][:40]} / {b['recommendation'][:40]}")
