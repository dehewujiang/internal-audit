#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/queries.py + query_commands.py + query_display.py
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下的专项测试，锁死第四拨（追溯+沟通卡）三件事：
          来龙去脉一次拼全 / -C顶替与缺口提示 / 发言稿四段。
          每条都能被"撤销改动"验红。
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
SANDBOX = Path(tempfile.mkdtemp(prefix="batch4_"))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


FINDING_FULL = {
    "schema_version": "1.2.0", "finding_id": "F-2026-005", "origin": "design",
    "risk_level": "高", "title": "夜班称重单人无复核", "status": "待整改",
    "criteria": "《称重制度》第5条：双人复核签字",
    "condition": "抽20笔，7笔无复核签字",
    "cause": "排班缺双人复核岗",
    "consequence": "废料可能流失",
    "recommendation": "加双人签字",
    "design_observation_id": "D-001",
    "related_control": "CP-012",
    "related_procedures": ["A7.2", "S01"],
    "evidence": [{"name": "称重单7张", "source": "班长", "obtained_date": "审计当天",
                  "reliability_grade": "A"}],
}

FINDING_GAP = {
    "schema_version": "1.2.0", "finding_id": "F-2026-006", "origin": "execution",
    "risk_level": "中", "title": "报价单缺签字", "status": "待补充",
    "criteria": "《报价制度》第3条", "condition": "抽10笔，3笔缺签字",
    "cause": "待查", "consequence": "待定", "recommendation": "补签字",
    "related_control": "", "related_procedures": ["X-001"], "evidence": [],
}


def _ws():
    ws = Path(tempfile.mkdtemp(prefix="b4ws_", dir=str(SANDBOX)))
    iw = ws / "internal-audit-workspace"
    (iw / "findings").mkdir(parents=True)
    (iw / "findings" / "index.json").write_text(json.dumps({
        "schema_version": "1.1.0", "version": "v1", "total_findings": 2,
        "by_year": {"2026": {"count": 2, "ids": ["F-2026-005", "F-2026-006"]}},
        "by_risk": {"高": ["F-2026-005"], "中": ["F-2026-006"]},
        "by_status": {"待整改": ["F-2026-005"], "待补充": ["F-2026-006"]},
        "by_origin": {"design": ["F-2026-005"], "execution": ["F-2026-006"]},
        "by_category": {}, "by_keyword": {}}, ensure_ascii=False), encoding="utf-8")
    (iw / "findings" / "F-2026-005.json").write_text(
        json.dumps(FINDING_FULL, ensure_ascii=False), encoding="utf-8")
    (iw / "findings" / "F-2026-006.json").write_text(
        json.dumps(FINDING_GAP, ensure_ascii=False), encoding="utf-8")
    (iw / "design-assessments").mkdir(exist_ok=True)
    (iw / "design-assessments" / "废料_设计观察.json").write_text(json.dumps({
        "design_observations": [{"id": "D-001", "title": "夜班单人称重",
                                 "description": "班长说夜班称重就一个人，还不签字",
                                 "source": "interview", "status": "pending"}]},
        ensure_ascii=False), encoding="utf-8")
    (iw / "policy-analyses").mkdir(exist_ok=True)
    (iw / "policy-analyses" / "a.json").write_text(json.dumps({
        "control_points": [{"id": "CP-012", "source_file": "称重制度",
                            "source": "第5条", "type": "复核",
                            "risk_level": "高", "requirement": "双人复核签字"}]},
        ensure_ascii=False), encoding="utf-8")
    (iw / "audit-programs").mkdir(exist_ok=True)
    (iw / "program_ir.json").write_text(json.dumps({
        "schema_version": "2.0.0",
        "steps": [
            {"step_id": "A7.2", "track": "A", "title": "夜班称重跟访",
             "procedure": "跟访三天", "risk_refs": [], "related_controls": ["CP-012"],
             "related_design_observations": [], "data_source": "称重单",
             "test_method": "控制有效性测试"},
            {"step_id": "A7.2-C", "track": "A", "title": "夜班称重跟访（修正）",
             "procedure": "跟访一周", "risk_refs": [], "is_errata": True,
             "corrects": "A7.2", "related_controls": ["CP-012"],
             "related_design_observations": [], "data_source": "称重单",
             "test_method": "控制有效性测试"},
            {"step_id": "S01", "track": "S", "title": "夜班突击复核",
             "procedure": "突击抽查签字", "risk_refs": [],
             "related_controls": [], "related_design_observations": ["D-001"],
             "data_source": "称重单", "test_method": "增量补充测试"}],
        "risk_register": []}, ensure_ascii=False), encoding="utf-8")
    (iw / "audit-table").mkdir(exist_ok=True)
    (iw / "audit-table" / "废料.json").write_text(json.dumps({
        "schema_version": "1.2", "table": "废料",
        "left": [{"slot": "确定的毛病", "red": False,
                  "text": "F-2026-005 夜班称重单人无复核",
                  "ref_finding_ids": ["F-2026-005"]},
                 {"slot": "怀疑偷骗", "red": True, "text": "", "ref_finding_ids": []},
                 {"slot": "说不清的信号", "red": False, "text": "", "ref_finding_ids": []}],
        "right": [], "drawers": [], "checklist": [], "ingested": {}},
        ensure_ascii=False), encoding="utf-8")
    return ws


def _q(ws, *args):
    return subprocess.run(
        [sys.executable, str(SHARED / "queries.py")] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ws)


# ══════════════════════════════════════════════════════════════
def test_lineage_full():
    print("\n[1] 来龙去脉一次拼全")
    ws = _ws()
    r = _q(ws, "lineage", "F-2026-005")
    check("exit 0", r.returncode == 0, (r.stdout + r.stderr)[:200])
    for key in ("来路", "程序", "证据", "桌位", "控制点", "同源", "决定"):
        check(f"有[{key}]段", key in r.stdout, r.stdout.strip()[:150])


def test_lineage_hints():
    print("\n[2] 顶替提示 + 证据明细 + 桌位 + 原文")
    ws = _ws()
    r = _q(ws, "lineage", "F-2026-005")
    check("-C 顶替提示", "A7.2-C" in r.stdout and "顶替" in r.stdout)
    check("证据写清文件/谁给/啥时候/等级",
          all(k in r.stdout for k in ("称重单7张", "班长", "审计当天", "A级")),
          r.stdout.strip()[:200])
    check("桌位+对单", "确定的毛病" in r.stdout and "对单" in r.stdout)
    check("问话原文一句话", "就一个人" in r.stdout)


def test_brief_gap():
    print("\n[3] 发言稿四段 + 缺口三方向")
    ws = _ws()
    r = _q(ws, "brief", "F-2026-006")
    check("exit 0", r.returncode == 0, (r.stdout + r.stderr)[:200])
    for key in ("从哪里来", "执行了什么程序", "拿到什么证据", "得出什么发现"):
        check(f"有[{key}]段", key in r.stdout)
    check("缺口三方向",
          all(k in r.stdout for k in ("业务未发生", "管理缺失未留痕", "证据被消除")))


def test_lineage_missing():
    print("\n[4] 查无此单不断腿")
    ws = _ws()
    r = _q(ws, "lineage", "F-2099-999")
    check("exit 0 且提示未找到", r.returncode == 0 and "未找到" in r.stdout,
          (r.stdout + r.stderr)[:150])


if __name__ == "__main__":
    test_lineage_full()
    test_lineage_hints()
    test_brief_gap()
    test_lineage_missing()
    print(f"\n{'全过' if not failures else f'失败 {len(failures)} 项: {failures}'}")
    sys.exit(1 if failures else 0)
