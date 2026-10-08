#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/program_ir_parser.py、validate-program.py、
          ledger/ledger.py、create_evidence_dirs.py、phase_gate.py
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下的专项测试，锁死第二拨（账本回写+三修）五件事：
          作废标记识别 / 任务作废（A6 收料删除后改道）/ 落盘记流水 /
          证据柜合流保纸条 / 程序变更记账 / 消化对号保险。
          每条都能被"撤销改动"验红。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md
"""

import importlib.util
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
LEDGER = REPO_ROOT / "ledger"
SANDBOX = Path(tempfile.mkdtemp(prefix="batch2_"))

failures = []


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(SHARED))
import program_ir_parser  # noqa: E402


MD_TMPL = """# 废料管理审计程序

### 2.1 风险识别清单

| 风险编号 | 风险名称 | 风险描述 | 来源标注 |
|----------|----------|----------|----------|
| R01 | 夜班单人称重 | 夜班称重单人操作无复核 | 【推演】 |
| R02 | 地磅年久失修 | 【已删除-原因：地磅已换新】 | 【推演】 |

<!-- track A -->
| 程序编号 | 风险编号 | 测试程序 | 取证方式 | 抽样方法 | 判定标准 |
|----------|----------|----------|----------|----------|----------|
| A1.1 | R01 | 夜班称重跟访 | 称重单 | 最近30天抽20笔 | 无签字笔数=0 |
| A1.2 | R02 | 地磅精度测试【已删除-原因：地磅已换新】 | 地磅检定证书 |  |  |
<!-- end track A -->
"""


def _ws_with_program(md_text, with_audit=True):
    ws = Path(tempfile.mkdtemp(prefix="b2ws_", dir=str(SANDBOX)))
    iw = ws / "internal-audit-workspace"
    (iw / "audit-programs").mkdir(parents=True)
    (iw / "audit-programs" / "废料管理审计程序_v1.0.md").write_text(md_text, encoding="utf-8")
    (iw / "findings").mkdir(exist_ok=True)
    (iw / "design-assessments").mkdir(exist_ok=True)
    (iw / "evidence").mkdir(exist_ok=True)
    if with_audit:
        (iw / "current-audit.json").write_text(json.dumps({
            "schema_version": "1.1", "status": "phase_2_program_generation",
            "audit_state": {"audit_purpose": "内控", "design_observations_consumed": False,
                            "programs": {"added": [], "deferred": []}}},
            ensure_ascii=False), encoding="utf-8")
    return ws


# ══════════════════════════════════════════════════════════════
# 1. 解析器认出"作废"章，覆盖度不算作废行
# ══════════════════════════════════════════════════════════════
def test_parser_deleted_flag():
    print("\n[1] 解析器：作废行打标，覆盖度排除")
    ws = _ws_with_program(MD_TMPL, with_audit=False)
    ir = program_ir_parser.build_ir(ws / "internal-audit-workspace" / "audit-programs" / "废料管理审计程序_v1.0.md")
    by_id = {s["step_id"]: s for s in ir["steps"]}
    check("A1.2 打上作废标", by_id.get("A1.2", {}).get("is_deleted") is True)
    check("A1.1 没误伤", by_id.get("A1.1", {}).get("is_deleted") is not True)
    check("覆盖率=100%（R02 作废不计分母，A1.2 不算覆盖）",
          ir["coverage"]["coverage_rate"] == 1.0, f"实际={ir['coverage']['coverage_rate']}")
    check("未覆盖清单为空", ir["coverage"]["uncovered_risks"] == [],
          f"实际={ir['coverage']['uncovered_risks']}")


# ══════════════════════════════════════════════════════════════
# 2. 校验器跳过作废行（判定标准/数据来源不拦死人）
# ══════════════════════════════════════════════════════════════
def test_validate_skips_deleted():
    print("\n[2] 校验器：作废行不参与判定标准/数据来源检查")
    vp = _load("validate_program_b2", SHARED / "validate-program.py")
    ws = _ws_with_program(MD_TMPL, with_audit=False)
    ir = program_ir_parser.build_ir(ws / "internal-audit-workspace" / "audit-programs" / "废料管理审计程序_v1.0.md")
    ok_c, msg_c = vp.check_ir_criterion(ir)
    ok_d, msg_d = vp.check_ir_data_source(ir)
    check("判定标准放行（A1.2 空标准不算）", ok_c, msg_c)
    check("数据来源放行（A1.2 空来源不算）", ok_d, msg_d)


# ══════════════════════════════════════════════════════════════
# 3. 作废走任务（任务作废，人写的字不动）
# ══════════════════════════════════════════════════════════════
def test_sweep_prunes_deleted():
    print("[3] 作废走任务：任务作废，人写的字不动")
    ws = _ws_with_program(MD_TMPL)
    t = ws / "桌子.json"

    def run(*a):
        return subprocess.run([sys.executable, str(LEDGER / "ledger.py")] + [str(x) for x in a],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    run("create", t, "--table", "废料")
    run("add-task", t, "--title", "地磅年久失修", "--room", "检查单", "--ref", "R-002")
    run("add-line", t, "--slot", "说不清的信号", "--text", "人工补一句")
    before = json.loads(t.read_text(encoding="utf-8-sig"))
    check("先摆上桌：R-002 在任务板",
          any("R-002" in str(x.get("source", {}).get("ref", "")) for x in before["tasks"]),
          "预置条件")
    # 程序里盖作废章 → 任务作废
    r = run("close-task", t, "--id", "T-001", "--verdict", "作废", "--reason", "地磅已换新")
    after = json.loads(t.read_text(encoding="utf-8-sig"))
    check("作废成功", r.returncode == 0, r.stdout.strip()[:80])
    check("任务状态变作废", after["tasks"][0]["status"] == "作废")
    check("人工那句还在", any("人工补一句" in x.get("text", "") for x in after["left"]))

def test_sweep_writeback():
    print("[4] 落盘记流水")
    ws = _ws_with_program(MD_TMPL)
    t = ws / "桌子.json"

    def run(*a):
        return subprocess.run([sys.executable, str(LEDGER / "ledger.py")] + [str(x) for x in a],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    run("create", t, "--table", "废料")
    r = run("add-task", t, "--title", "假设", "--room", "检查单", "--ref", "R-010")
    h = t.parent / (t.stem + ".history.jsonl")
    rows = h.read_text(encoding="utf-8").splitlines() if h.exists() else []
    check("流水记两笔（开桌+立任务）", len(rows) == 2, r.stdout.strip()[:80])
    check("行行合法 JSON 且带 op",
          all(__import__("json").loads(x).get("op") for x in rows))

def test_catalog_merge():
    print("\n[5] 证据柜：合流旧纸条 + 作废的不占槽")
    ced = _load("create_evidence_dirs_b2", SHARED / "create_evidence_dirs.py")
    d = Path(tempfile.mkdtemp(prefix="b2ev_", dir=str(SANDBOX)))
    md = d / "prog.md"
    md.write_text(MD_TMPL, encoding="utf-8")
    root = d / "evidence"
    ced.generate_evidence_catalog(str(md), root, "废料")
    cat1 = json.loads((root / "_evidence_catalog.json").read_text(encoding="utf-8"))
    check("首建 1 槽（A1.2 作废不占槽，只剩称重单）", cat1["total_slots"] == 1, f"实际={cat1['total_slots']}")
    # 贴纸条后重做
    cat1["items"][0]["file"] = "_files/称重单7张.pdf"
    cat1["items"][0]["collected_at"] = "2026-09-15"
    (root / "_evidence_catalog.json").write_text(json.dumps(cat1, ensure_ascii=False), encoding="utf-8")
    ced.generate_evidence_catalog(str(md), root, "废料")
    cat2 = json.loads((root / "_evidence_catalog.json").read_text(encoding="utf-8"))
    kept = [it for it in cat2["items"] if it["file"]]
    check("旧纸条还在", len(kept) == 1 and kept[0]["file"] == "_files/称重单7张.pdf")
    check("已填数重算对", cat2["filled_slots"] == 1, f"实际={cat2['filled_slots']}")
    dead = [it for it in cat2["items"]
            if any("A1.2" in p for p in it.get("source_programs", []))]
    check("作废的 A1.2 不占槽", dead == [])


# ══════════════════════════════════════════════════════════════
# 6. 程序变更记账（log-program-change）
# ══════════════════════════════════════════════════════════════
def test_log_program_change():
    print("\n[6] 程序变更记账")
    ws = _ws_with_program(MD_TMPL)
    r = subprocess.run(
        [sys.executable, str(SHARED / "phase_gate.py"), "log-program-change",
         "--type", "added", "--id", "X-001", "--reason", "发现新风险"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ws)
    check("命令 exit 0", r.returncode == 0, (r.stdout + r.stderr)[:200])
    audit = json.loads((ws / "internal-audit-workspace" / "current-audit.json").read_text(encoding="utf-8-sig"))
    st = audit["audit_state"]
    check("added 进 X-001", "X-001" in st.get("programs", {}).get("added", []))
    check("更新历史记一笔", any(h.get("id") == "X-001" for h in st.get("program_update_history", [])))
    check("大事记记一笔", any(e.get("event_type") == "program_change" for e in st.get("audit_trail", [])))
    check("不拍新快照（A5 拍照取消）", not (ws / "internal-audit-workspace" / "snapshots").exists())


# ══════════════════════════════════════════════════════════════
# 7. 消化对号保险（标消化前先对号）
# ══════════════════════════════════════════════════════════════
def test_consumed_consistency():
    print("\n[7] 消化对号保险")
    pg = _load("phase_gate_b2", SHARED / "phase_gate.py")
    ws = _ws_with_program(MD_TMPL)
    (ws / "internal-audit-workspace" / "design-assessments" / "废料_设计观察.json").write_text(
        json.dumps({"design_observations": [
            {"id": "D-001", "title": "夜班单人称重无人复核", "type": "risk_clue", "status": "pending"}]},
            ensure_ascii=False), encoding="utf-8")
    data = {"status": "phase_2_program_generation",
            "audit_state": {"design_observations_consumed": True}}
    issues = pg.check_consumed_consistency(data, ws / "internal-audit-workspace")
    check("对不上号就报警", any("对号" in i.get("msg", "") for i in issues),
          f"实际={issues}")


if __name__ == "__main__":
    test_parser_deleted_flag()
    test_validate_skips_deleted()
    test_sweep_prunes_deleted()
    test_sweep_writeback()
    test_catalog_merge()
    test_log_program_change()
    test_consumed_consistency()
    print(f"\n{'全过' if not failures else f'失败 {len(failures)} 项: {failures}'}")
    sys.exit(1 if failures else 0)
