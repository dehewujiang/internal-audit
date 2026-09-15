#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/queries.py + query_commands.py +
          query_data_sources.py + query_display.py
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下的专项测试，锁死第三拨（查询接线）四件事：
          认新索引（S/X/-C，老索引当备胎）/ 桌子能查 / 证据槽能查 /
          状态能查 / 搜东西可扩大。每条都能被"撤销改动"验红。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED = REPO_ROOT / "_shared" / "scripts"
SANDBOX = Path(tempfile.mkdtemp(prefix="batch3_"))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


IR_STEPS = [
    {"step_id": "A1.1", "track": "A", "title": "夜班称重跟访",
     "procedure": "连续三天夜班跟访称重", "risk_ref": "R-1", "risk_refs": ["R-1"],
     "related_controls": [], "related_design_observations": [],
     "data_source": "称重单", "test_method": "控制有效性测试"},
    {"step_id": "S01", "track": "S", "title": "夜班称重突击复核",
     "procedure": "突击抽查夜班称重记录签字", "risk_ref": "R-1", "risk_refs": ["R-1"],
     "related_controls": [], "related_design_observations": ["D-001"],
     "data_source": "称重单", "test_method": "增量补充测试"},
    {"step_id": "X-001", "track": "C", "title": "废料报价单签字检查",
     "procedure": "抽查报价单是否有两人签字", "risk_ref": "", "risk_refs": [],
     "related_controls": [], "related_design_observations": [],
     "data_source": "报价单", "test_method": "系统/公司类实质性测试"},
    {"step_id": "A7.2-C", "track": "A", "title": "薪资计算复核（修正）",
     "procedure": "复核修正后的薪资表", "risk_ref": "", "risk_refs": [],
     "is_errata": True, "corrects": "A7.2",
     "related_controls": [], "related_design_observations": [],
     "data_source": "薪资表", "test_method": "控制有效性测试"},
]


def _ws():
    ws = Path(tempfile.mkdtemp(prefix="b3ws_", dir=str(SANDBOX)))
    iw = ws / "internal-audit-workspace"
    (iw / "findings").mkdir(parents=True)
    (iw / "findings" / "index.json").write_text(json.dumps({
        "schema_version": "1.1.0", "version": "v1", "total_findings": 1,
        "by_year": {"2026": {"count": 1, "ids": ["F-2026-001"]}},
        "by_risk": {"高": ["F-2026-001"]}, "by_status": {"待整改": ["F-2026-001"]},
        "by_origin": {"design": ["F-2026-001"], "execution": []},
        "by_category": {}, "by_keyword": {}}, ensure_ascii=False), encoding="utf-8")
    (iw / "findings" / "F-2026-001.json").write_text(json.dumps({
        "finding_id": "F-2026-001", "finding_title": "夜班称重单人无复核",
        "title": "夜班称重单人无复核"}, ensure_ascii=False), encoding="utf-8")
    (iw / "audit-programs").mkdir(exist_ok=True)
    (iw / "audit-programs" / "废料_program_index.json").write_text(
        json.dumps({"steps": [IR_STEPS[0]]}, ensure_ascii=False), encoding="utf-8")
    (iw / "program_ir.json").write_text(
        json.dumps({"schema_version": "2.0.0", "steps": IR_STEPS,
                    "risk_register": []}, ensure_ascii=False), encoding="utf-8")
    (iw / "audit-table").mkdir(exist_ok=True)
    (iw / "audit-table" / "废料.json").write_text(json.dumps({
        "schema_version": "1.2", "table": "废料",
        "left": [
            {"slot": "确定的毛病", "red": False, "text": "F-2026-001 夜班称重",
             "ref_finding_ids": ["F-2026-001"]},
            {"slot": "怀疑偷骗", "red": True, "text": "", "ref_finding_ids": []},
            {"slot": "说不清的信号", "red": False, "text": "R01 推演风险",
             "ref_finding_ids": []}],
        "right": [{"slot_id": None, "file": "称重单7张", "from": "班长", "when": "审计当天"}],
        "drawers": [{"name": "问话表", "path": "interview-materials/问卷.xlsx", "status": "已收回"},
                    {"name": "检查表", "path": "", "status": ""},
                    {"name": "报告表", "path": "", "status": ""}],
        "checklist": [], "ingested": {"a": 1}}, ensure_ascii=False), encoding="utf-8")
    (iw / "evidence").mkdir(exist_ok=True)
    (iw / "evidence" / "_evidence_catalog.json").write_text(json.dumps({
        "project": "废料", "total_slots": 2, "filled_slots": 1, "items": [
            {"id": "EVD-001", "name": "称重单", "source_track": "A",
             "source_programs": ["A1.1"], "file": "_files/称重单7张.pdf",
             "collected_at": "2026-09-15"},
            {"id": "EVD-002", "name": "没主的槽", "source_track": "",
             "source_programs": [], "file": None, "collected_at": None}]},
        ensure_ascii=False), encoding="utf-8")
    (iw / "current-audit.json").write_text(json.dumps({
        "schema_version": "1.1", "audit_topic": "废料", "status": "phase_3_execution",
        "audit_state": {"design_observations_consumed": True,
                        "program_version": "v1.1",
                        "sweep_history": [{"at": "2026-09-15 10:00", "added": 2,
                                           "moved": 0, "evidence": 1, "pruned": 0}]}},
        ensure_ascii=False), encoding="utf-8")
    return ws


def _q(ws, *args):
    return subprocess.run(
        [sys.executable, str(SHARED / "queries.py")] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ws)


# ══════════════════════════════════════════════════════════════
def test_trace_new_index():
    print("\n[1] 追溯认新索引（S/X/-C）")
    ws = _ws()
    r = _q(ws, "trace", "S01")
    check("S01 查得到", r.returncode == 0 and "审计程序步骤: S01" in r.stdout, r.stdout.strip()[:120])
    r = _q(ws, "trace", "X-001")
    check("X-001 查得到", r.returncode == 0 and "审计程序步骤: X-001" in r.stdout, r.stdout.strip()[:120])
    r = _q(ws, "trace", "A7.2-C")
    check("-C 查得到", r.returncode == 0 and "审计程序步骤: A7.2-C" in r.stdout, r.stdout.strip()[:120])


def test_trace_old_fallback():
    print("\n[2] 老索引当备胎（没 program_ir.json 也能查）")
    ws = _ws()
    (ws / "internal-audit-workspace" / "program_ir.json").unlink()
    r = _q(ws, "trace", "A1.1")
    check("老索引 A1.1 查得到", r.returncode == 0 and "审计程序步骤: A1.1" in r.stdout,
          r.stdout.strip()[:120])


def test_table_query():
    print("\n[3] 桌子能查")
    ws = _ws()
    r = _q(ws, "table")
    check("exit 0", r.returncode == 0, (r.stdout + r.stderr)[:200])
    check("三格数对得上", "确定的毛病" in r.stdout and "说不清的信号" in r.stdout)
    check("抽屉状态看得见", "问话表" in r.stdout and "已收回" in r.stdout)


def test_evidence_query():
    print("\n[4] 证据槽能查")
    ws = _ws()
    r = _q(ws, "evidence")
    check("exit 0", r.returncode == 0, (r.stdout + r.stderr)[:200])
    check("没主的槽被点名", "EVD-002" in r.stdout, r.stdout.strip()[:200])


def test_status_query():
    print("\n[5] 状态能查")
    ws = _ws()
    r = _q(ws, "status")
    check("exit 0", r.returncode == 0, (r.stdout + r.stderr)[:200])
    check("阶段+v1.1+消化+上次收料都在",
          all(k in r.stdout for k in ("phase_3_execution", "v1.1", "2026-09-15 10:00")),
          r.stdout.strip()[:200])


def test_search_scope():
    print("\n[6] 搜东西可扩大")
    ws = _ws()
    r = _q(ws, "search", "突击抽查夜班称重记录签字")
    check("默认只搜问题单（程序里的词搜不到）", "无匹配" in r.stdout, r.stdout.strip()[:120])
    r = _q(ws, "search", "突击抽查夜班称重记录签字", "--in", "all")
    check("--in all 连程序一起搜", "S01" in r.stdout, r.stdout.strip()[:200])


def test_summary_includes_table():
    print("\n[7] 汇总带上桌上数")
    ws = _ws()
    r = _q(ws, "summary")
    check("汇总里有桌上数", "桌上" in r.stdout, r.stdout.strip()[:200])


if __name__ == "__main__":
    test_trace_new_index()
    test_trace_old_fallback()
    test_table_query()
    test_evidence_query()
    test_status_query()
    test_search_scope()
    test_summary_includes_table()
    print(f"\n{'全过' if not failures else f'失败 {len(failures)} 项: {failures}'}")
    sys.exit(1 if failures else 0)
