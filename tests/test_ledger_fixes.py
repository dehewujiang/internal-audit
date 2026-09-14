#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 ledger/ 下的 ledger.py / check.py / audit_table.py
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]:    tests/ 下的专项测试，锁死新桌子 A 批三处修复。回归基线 regression-check.py 不覆盖 ledger，
          本脚本补上"后悔药边界 / 崩溃兜底 / 搬老账路径校验"三条
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

背景（2026-09-11 验货实测）：
  1. 照片攒满 20 张后回滚到最早那张会崩——cmd_rollback 先 save()（内含淘汰）再读目标，
     目标已被自己淘汰掉 → FileNotFoundError
  2. 五个零件无崩溃兜底，异常时 Python 返回 1，与 check.py 的"放行（有提醒）"语义撞车：
     工具坏了看起来和"放行"一样
  3. cmd_import 不检查项目路径，路径写错时静默搬出一张空桌子（打印 0 确定，但不报错）

三条断言缺一不可，且每条都能被"撤销改动"验红。
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows 控制台默认 GBK，直出 ✅/❌ 会抛 UnicodeEncodeError 把测试打断（表现为"测试崩了"，
# 而不是"测试失败了"）——强制 stdout 走 UTF-8，让断言结果无论如何都打得出来
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER = REPO_ROOT / "ledger"

# 隔离沙箱：不碰任何真实项目
SANDBOX = Path(tempfile.mkdtemp(prefix="ledger_fixes_"))

failures = []


def _run(script, *args):
    return subprocess.run(
        [sys.executable, str(LEDGER / script)] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=SANDBOX,
    )


def check(label, ok, detail=""):
    print(f"  {'✅' if ok else '❌'} {label}" + (f" —— {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def table_text(path: Path) -> str:
    return json.dumps(json.loads(path.read_text(encoding="utf-8-sig")),
                      ensure_ascii=False, sort_keys=True)


# ══════════════════════════════════════════════════════════════
# 断言 1：后悔药在照片攒满 20 张时，回到最早那张不能崩，且整件事可逆
# ══════════════════════════════════════════════════════════════
def test_rollback_full():
    print("\n[1] 后悔药边界：照片攒满 20 张后回滚到最早那张")
    t = SANDBOX / "回滚测试.json"
    _run("ledger.py", "create", t, "--table", "回滚测试")
    for i in range(1, 22):                       # 21 次写入 → 照片封顶 20 张
        _run("ledger.py", "add-line", t, "--slot", "说不清的信号", "--text", f"第{i}次")

    snaps_dir = SANDBOX / "回滚测试.snaps"
    snaps = sorted(snaps_dir.glob("snap_*.json"))
    check("照片按上限留 20 张", len(snaps) == 20, f"实际 {len(snaps)} 张")

    earliest = snaps[0]
    earliest_content = table_text(earliest)
    before_rollback = table_text(t)

    r = _run("ledger.py", "rollback", t, "--to", earliest.name)
    check("回滚到最早那张不崩（退出码 0）", r.returncode == 0,
          f"退出码={r.returncode}" + (f" | {r.stderr.strip().splitlines()[-1]}" if r.stderr.strip() else ""))
    check("真的回到了最早那张的内容", table_text(t) == earliest_content)

    # 守恒：回滚是一次可逆操作——回滚前的状态必须还能找回来
    after = {table_text(p) for p in snaps_dir.glob("snap_*.json")}
    check("回滚前的状态仍可恢复（无不可逆丢失）", before_rollback in after)


# ══════════════════════════════════════════════════════════════
# 断言 2：工具自己坏掉时，必须报错退出，不能和"放行/有提醒"撞码
# ══════════════════════════════════════════════════════════════
def test_crash_guard():
    print("\n[2] 崩溃兜底：工具坏掉 ≠ 放行")
    missing = SANDBOX / "没有这张桌子.json"
    r = _run("check.py", missing)
    check("门卫：桌子文件不存在 → 退出码 2（不是 1）", r.returncode == 2,
          f"退出码={r.returncode}")

    broken = SANDBOX / "坏桌子.json"
    broken.write_text("{ 这不是合法表格", encoding="utf-8")
    r = _run("check.py", broken)
    check("门卫：桌子内容损坏 → 退出码 2", r.returncode == 2, f"退出码={r.returncode}")

    r = _run("audit_table.py", "--table", broken, "--workspace", SANDBOX)
    check("报告闸机：桌子内容损坏 → 退出码 2", r.returncode == 2, f"退出码={r.returncode}")


# ══════════════════════════════════════════════════════════════
# 断言 3：搬老账时项目路径写错，必须报错，不能静默搬出空桌子
# ══════════════════════════════════════════════════════════════
def test_import_bad_workspace():
    print("\n[3] 搬老账路径校验")
    out = SANDBOX / "空搬.json"
    r = _run("ledger.py", "import", out,
             "--workspace", SANDBOX / "压根不存在的项目", "--table", "空搬")
    check("路径不存在 → 非 0 退出", r.returncode != 0, f"退出码={r.returncode}")
    check("路径不存在 → 不产出桌子文件", not out.exists())


# ══════════════════════════════════════════════════════════════
# 断言 4（B1）：高风险硬证据——舞弊拦死，非舞弊只提醒
# ══════════════════════════════════════════════════════════════
def _make_workspace(name, category, grades):
    """造一个只含一张高风险单子的假项目。"""
    ws = SANDBOX / name
    fdir = ws / "internal-audit-workspace" / "findings"
    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / "F-B1.json").write_text(json.dumps({
        "schema_version": "2.0", "finding_id": "F-B1", "title": "高风险测试单",
        "category": category, "risk_level": "高", "status": "已确认",
        "evidence": [{"name": "记录", "source": "口头", "obtained_date": "2026-08-10",
                      "reliability_grade": g} for g in grades],
    }, ensure_ascii=False), encoding="utf-8")
    return ws


def _make_table(name, slot, refs):
    """造一张三格都填满、并把 refs 对到指定格子的桌子。"""
    t = SANDBOX / name
    _run("ledger.py", "create", t, "--table", "B1 测试")
    for s in ("确定的毛病", "怀疑偷骗", "说不清的信号"):
        _run("ledger.py", "add-line", t, "--slot", s, "--text", "占位")
    for fid in refs:
        _run("ledger.py", "link-finding", t, "--slot", slot, "--finding", fid)
    return t


def test_high_risk_grades():
    print("\n[4] 高风险硬证据：舞弊拦死，非舞弊只提醒")
    # 非舞弊高风险 + 只有 C：对在"确定的毛病"格 → 只提醒，不卡报告
    ws = _make_workspace("项目非舞弊", "合规问题", ["C"])
    r = _run("check.py", _make_table("非舞弊桌.json", "确定的毛病", ["F-B1"]), "--workspace", ws)
    check("非舞弊高风险缺硬证据 → 只提醒（退出码 1）", r.returncode == 1, f"退出码={r.returncode}")
    check("提醒里点名了这张单子和'硬证据'", "F-B1" in r.stdout and "硬证据" in r.stdout)

    # 舞弊高风险 + 只有 C：对在红格 → 拦下
    ws2 = _make_workspace("项目舞弊", "舞弊风险", ["C"])
    r = _run("check.py", _make_table("舞弊桌.json", "怀疑偷骗", ["F-B1"]), "--workspace", ws2)
    check("舞弊高风险缺硬证据 → 拦下（退出码 2）", r.returncode == 2, f"退出码={r.returncode}")
    check("拦下理由点名了这张单子", "F-B1" in r.stdout)

    # 舞弊高风险 + 有 A 级 → 放行
    ws3 = _make_workspace("项目有硬证据", "舞弊风险", ["A", "C"])
    r = _run("check.py", _make_table("有硬证据桌.json", "怀疑偷骗", ["F-B1"]), "--workspace", ws3)
    check("高风险有 A 级证据 → 放行（退出码 0）", r.returncode == 0, f"退出码={r.returncode}")


# ══════════════════════════════════════════════════════════════
# 断言 5（B3）：抽屉是三张表的入口（在哪、什么状态），不再是三个死名字
# ══════════════════════════════════════════════════════════════
def test_drawers():
    print("\n[5] 抽屉：从死名字改成真入口")
    ws = _make_workspace("抽屉项目", "舞弊风险", ["A"])
    (ws / "internal-audit-workspace" / "audit-programs").mkdir(parents=True, exist_ok=True)
    (ws / "internal-audit-workspace" / "audit-programs" / "程序_v1.md").write_text("x", encoding="utf-8")

    t = _make_table("抽屉桌.json", "怀疑偷骗", ["F-B1"])
    data = json.loads(t.read_text(encoding="utf-8-sig"))
    names = [d.get("name") if isinstance(d, dict) else d for d in data.get("drawers", [])]
    check("抽屉仍是三张表", names == ["问话表", "检查表", "报告表"], f"实际 {names}")
    check("每张表带 name/path/status 三个槽",
          all(isinstance(d, dict) and {"name", "path", "status"} <= set(d) for d in data["drawers"]))

    rel = "internal-audit-workspace/audit-programs/程序_v1.md"
    r = _run("ledger.py", "set-drawer", t, "--name", "检查表", "--path", rel, "--status", "已执行")
    check("set-drawer 能填入口", r.returncode == 0, f"退出码={r.returncode}")
    data = json.loads(t.read_text(encoding="utf-8-sig"))
    drawer = next((d for d in data["drawers"]
                   if isinstance(d, dict) and d.get("name") == "检查表"), {})
    check("路径与状态写进去了",
          drawer.get("path") == rel and drawer.get("status") == "已执行",
          f"{drawer.get('path')} / {drawer.get('status')}")

    r = _run("check.py", t, "--workspace", ws)
    check("门卫：指到的表在 → 不因抽屉报警（退出码 0）", r.returncode == 0, f"退出码={r.returncode}")

    _run("ledger.py", "set-drawer", t, "--name", "问话表",
         "--path", "internal-audit-workspace/没有这份.md", "--status", "已收回")
    r = _run("check.py", t, "--workspace", ws)
    check("门卫：指到的表找不到 → 提醒（退出码 1）", r.returncode == 1, f"退出码={r.returncode}")

    out = SANDBOX / "抽屉总览.xlsx"
    r = _run("export.py", t, out)
    check("总览表能导出", r.returncode == 0 and out.exists(), f"退出码={r.returncode}")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(out)
        cells = [str(c.value) for row in wb["抽屉打勾"].iter_rows() for c in row]
        check("抽屉页带出位置与状态", rel in cells and "已执行" in cells)
    except ImportError:
        check("抽屉页带出位置与状态", False, "openpyxl 不可用，跳过")


# ══════════════════════════════════════════════════════════════
# 断言 5b（B3 连带）：老桌子（抽屉还是三个纯名字）不能被新版本锁死
# ══════════════════════════════════════════════════════════════
def test_legacy_table():
    print("\n[5b] 老桌子兼容：抽屉只写了三个名字的老桌子仍能读、能写、能导")
    t = SANDBOX / "老桌.json"
    legacy = {
        "schema_version": "1.0",
        "table": "老桌",
        "left": [{"slot": s, "red": (s == "怀疑偷骗"), "text": "", "ref_finding_ids": []}
                 for s in ("确定的毛病", "怀疑偷骗", "说不清的信号")],
        "right": [],
        "drawers": ["问话表", "检查表", "报告表"],
        "checklist": ["证据够了吗", "制度看全了吗", "红格看了吗"],
    }
    t.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")

    r = _run("ledger.py", "show", t)
    check("老桌读得开（退出码 0）", r.returncode == 0, f"退出码={r.returncode} {r.stdout.strip()[:60]}")

    r = _run("ledger.py", "set-slot", t, "--slot", "确定的毛病", "--text", "领料没签字")
    check("老桌写得进（退出码 0）", r.returncode == 0, f"退出码={r.returncode}")
    after = json.loads(t.read_text(encoding="utf-8-sig"))
    newest = json.loads((REPO_ROOT / "ledger" / "ledger.schema.json")
                        .read_text(encoding="utf-8-sig"))["schema_version"]
    check("写过之后升到当前版本", after.get("schema_version") == newest,
          f"{after.get('schema_version')} vs 最新 {newest}")
    drawers = after.get("drawers", [])
    check("抽屉补成入口（仍是三张、带 path/status）",
          [d.get("name") if isinstance(d, dict) else d for d in drawers]
          == ["问话表", "检查表", "报告表"]
          and all(isinstance(d, dict) and {"path", "status"} <= set(d) for d in drawers))
    check("原来写好的格子没丢", after["left"][0]["text"] == "领料没签字")

    t.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
    out = SANDBOX / "老桌总览.xlsx"
    r = _run("export.py", t, out)
    check("老桌导得出总览（退出码 0）", r.returncode == 0 and out.exists(), f"退出码={r.returncode}")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(out)
        cells = [str(c.value) for row in wb["抽屉打勾"].iter_rows() for c in row]
        check("老桌的抽屉页带出三个表名", "问话表" in cells and "检查表" in cells and "报告表" in cells)
    except ImportError:
        pass


# ══════════════════════════════════════════════════════════════
# 断言 7（C2）：收料——各房间查出来的东西，按自带状态自动落格
# ══════════════════════════════════════════════════════════════
def _make_source_project(name):
    """造一个有全部来源的假项目：看制度、设计观察、信号池、举报、问题单。"""
    ws = SANDBOX / name
    wsx = ws / "internal-audit-workspace"
    for sub in ("policy-analyses", "design-assessments", "findings"):
        (wsx / sub).mkdir(parents=True, exist_ok=True)

    (wsx / "policy-analyses" / "废料制度_分析.json").write_text(json.dumps({
        "schema_version": "1.0.0", "doc_name": "废料管理制度",
        "control_gaps": [
            {"id": "CG-001", "expected_control": "过磅双人复核", "verification_status": "已确认"},
            {"id": "CG-002", "expected_control": "废料出厂月度对账", "verification_status": "待确认"},
            {"id": "CG-003", "expected_control": "废料台账登记", "verification_status": "跨文件覆盖"},
        ],
        "risk_points": [{"risk_id": "RK-001", "risk_description": "单人值守无监督",
                         "risk_level": "高"}],
        "conflicts": [{"id": "CF-001", "description": "过磅签字要求与门卫记录条款打架"}],
    }, ensure_ascii=False), encoding="utf-8")

    (wsx / "design-assessments" / "废料_设计观察.json").write_text(json.dumps({
        "schema_version": "1.0.0",
        "design_observations": [
            {"id": "D-001", "title": "过磅房单人值守", "status": "pending",
             "source": "document-organizer"},
            {"id": "D-002", "title": "已升级成单子的观察", "status": "verified",
             "source": "interview"},
            {"id": "D-003", "title": "经核实不成立", "status": "rejected", "source": "interview"},
        ],
    }, ensure_ascii=False), encoding="utf-8")

    (ws / "current-audit.json").write_text(json.dumps({
        "audit_state": {
            "signals": [{"source": "constitution_#10", "type": "制度空白",
                         "module": "废料处置", "risk": "高",
                         "detail": "审计主题'废料管理'缺少 mandatory 模块'废料处置'的制度文档"}],
            "whistleblower_pending": [
                {"id": "WB-001", "summary": "举报采购员收受回扣"},
                {"id": "WB-002", "summary": "加班费算法看不懂"},
            ],
        },
    }, ensure_ascii=False), encoding="utf-8")

    (wsx / "findings" / "F-2026-001.json").write_text(json.dumps({
        "finding_id": "F-2026-001", "title": "领料单没签字", "category": "内控缺陷",
        "risk_level": "高", "status": "待整改",
        "evidence": [{"name": "领料单", "source": "班长", "obtained_date": "2026-08-10",
                      "reliability_grade": "A"}],
    }, ensure_ascii=False), encoding="utf-8")
    (wsx / "findings" / "F-2026-002.json").write_text(json.dumps({
        "finding_id": "F-2026-002", "title": "废料少了2吨", "category": "舞弊风险",
        "risk_level": "高", "status": "待整改",
        "evidence": [{"name": "地磅记录", "source": "系统导出", "obtained_date": "2026-08-10",
                      "reliability_grade": "A"}],
    }, ensure_ascii=False), encoding="utf-8")
    return ws


def test_sweep_routing():
    print("\n[7] 收料：各房间的东西按自带状态自动落格")
    ws = _make_source_project("收料项目")

    by_import = SANDBOX / "整搬桌.json"
    r = _run("ledger.py", "import", by_import, "--workspace", ws, "--table", "废料管理")
    check("整搬能跑（退出码 0）", r.returncode == 0, f"退出码={r.returncode}")

    by_sweep = SANDBOX / "收料桌.json"
    _run("ledger.py", "create", by_sweep, "--table", "废料管理")
    r = _run("ledger.py", "sweep", by_sweep, "--workspace", ws)
    check("收料能跑（退出码 0）", r.returncode == 0, f"退出码={r.returncode}")

    d = json.loads(by_sweep.read_text(encoding="utf-8-sig"))
    cells = {x["slot"]: x["text"] for x in d["left"]}
    sure, red, sig = cells["确定的毛病"], cells["怀疑偷骗"], cells["说不清的信号"]
    everything = sure + red + sig

    check("控制缺口·已确认 → 确定的毛病", "CG-001" in sure)
    check("控制缺口·待确认 → 说不清的信号", "CG-002" in sig)
    check("控制缺口·跨文件覆盖 → 不上桌", "CG-003" not in everything)
    check("制度冲突 → 确定的毛病", "CF-001" in sure)
    check("风险点 → 说不清的信号", "RK-001" in sig)
    check("设计观察·pending → 说不清的信号", "D-001" in sig)
    check("设计观察·verified/rejected → 不上桌",
          "D-002" not in everything and "D-003" not in everything)
    check("宪法#10 制度空白 → 说不清的信号", "制度空白" in sig and "废料处置" in sig)
    check("涉舞弊举报 → 红格", "WB-001" in red)
    check("不涉舞弊举报 → 说不清的信号", "WB-002" in sig)
    check("非舞弊问题单 → 确定的毛病＋自动对单号",
          "F-2026-001" in sure and "F-2026-001" in d["left"][0]["ref_finding_ids"])
    check("舞弊问题单 → 红格＋自动对单号",
          "F-2026-002" in red and "F-2026-002" in d["left"][1]["ref_finding_ids"])
    check("右边贴上问题单的证据", any("领料单" in e.get("file", "") for e in d["right"]))

    check("整搬与收料结果一致",
          table_text(by_import) == table_text(by_sweep))

    # 只收一张单：不动别的
    one = SANDBOX / "单张桌.json"
    _run("ledger.py", "create", one, "--table", "单张")
    _run("ledger.py", "sweep", one, "--workspace", ws, "--finding", "F-2026-002")
    d1 = json.loads(one.read_text(encoding="utf-8-sig"))
    t1 = "；".join(x["text"] for x in d1["left"])
    check("--finding 只收那一张单", "F-2026-002" in t1 and "F-2026-001" not in t1)

    # 建项目时开第一张桌：那时 audit-table/ 目录还不存在，也得能开出来
    fresh = SANDBOX / "新项目" / "internal-audit-workspace" / "audit-table"
    r = _run("ledger.py", "create", fresh / "存货.json", "--table", "存货管理")
    check("目录还没建也能开出第一张桌（退出码 0）",
          r.returncode == 0 and (fresh / "存货.json").exists(), f"退出码={r.returncode}")


# ══════════════════════════════════════════════════════════════
# 断言 8（C2）：收料只添不盖——反复收不重复，状态变了只挪格
# ══════════════════════════════════════════════════════════════
def test_real_fieldnames():
    print("\n[8b] 真实产物字段名兜底：广东长华撞出来的两条")
    ws = SANDBOX / "真实字段项目"
    wsx = ws / "internal-audit-workspace"
    for sub in ("policy-analyses", "design-assessments"):
        (wsx / sub).mkdir(parents=True, exist_ok=True)

    # ① 字段名兜底：真实 document-organizer 产出用 gap_id/rp_id/conflict_id，
    #    沙箱测试当初照抄代码字段名（id/risk_id），等于自己考自己——2026-09-14 实撞
    (wsx / "policy-analyses" / "HR_分析.json").write_text(json.dumps({
        "schema_version": "1.0",
        "analysis_date": "2026-07-17", "company": "某公司", "audit_topic": "人力资源",
        "documents_analyzed": [{"file": "a.md", "title": "考勤管理制度"}],
        "control_gaps": [
            {"gap_id": "CG-HR-001", "document": "考勤制度", "verification_status": "已确认",
             "description": "考勤数据→薪资计算缺少签收确认机制"},
            {"gap_id": "CG-HR-002", "document": "考勤制度", "verification_status": "待确认",
             "description": "调休假制度合规性待核实"},
        ],
        "risk_points": [
            {"rp_id": "RP-HR-001", "document": "考勤制度", "risk_level": "high",
             "description": "综合管理科五权合一"},
        ],
        "conflicts": [
            {"conflict_id": "CF-HR-001", "documents": "两份制度",
             "description": "全勤奖条款打架"},
        ],
    }, ensure_ascii=False), encoding="utf-8")

    # ② 已消化的设计观察不再挂回桌面：current-audit.json 标了 consumed
    (wsx / "design-assessments" / "HR_观察.json").write_text(json.dumps({
        "schema_version": "1.0.0",
        "design_observations": [
            {"id": "D-001", "title": "产假天数低于法定", "status": "pending",
             "source": "document-organizer"},
            {"id": "D-002", "title": "已消化的观察", "status": "verified",
             "source": "interview"},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    (wsx / "current-audit.json").write_text(json.dumps({
        "audit_state": {"design_observations_consumed": True},
    }, ensure_ascii=False), encoding="utf-8")

    t = SANDBOX / "真实字段桌.json"
    _run("ledger.py", "create", t, "--table", "人力资源")
    r = _run("ledger.py", "sweep", t, "--workspace", ws)
    check("真实字段项目收料能跑（退出码 0）", r.returncode == 0, f"退出码={r.returncode}")
    d = json.loads(t.read_text(encoding="utf-8-sig"))
    cells = {x["slot"]: x["text"] for x in d["left"]}
    sure, sig = cells["确定的毛病"], cells["说不清的信号"]

    # ① 列名兜底
    check("gap_id 编号也能上桌（已确认→确定格）", "CG-HR-001" in sure)
    check("gap_id 待确认→信号格", "CG-HR-002" in sig)
    check("rp_id 风险点→信号格", "RP-HR-001" in sig)
    check("conflict_id 冲突→确定格", "CF-HR-001" in sure)
    check("风险点等级 high 译成中文", "高" in sig)

    # ② 消化口径
    check("已消化（consumed）→ 设计观察一律不上桌", "D-001" not in sig and "D-002" not in sig)


def test_program_risks():
    print("\n[8c] 程序风险清单：推演的上桌，制度类的有户口就不上（去重）")
    ws = SANDBOX / "程序风险项目"
    wsx = ws / "internal-audit-workspace"
    for sub in ("policy-analyses", "audit-programs"):
        (wsx / sub).mkdir(parents=True, exist_ok=True)

    # 制度分析里已有一条控制缺口（这就是"户口"）
    (wsx / "policy-analyses" / "废料_分析.json").write_text(json.dumps({
        "schema_version": "1.0.0",
        "control_gaps": [{"gap_id": "CG-001", "description": "过磅无复核",
                          "verification_status": "已确认"}],
    }, ensure_ascii=False), encoding="utf-8")

    # 程序文件的风险清单：两条纯推演 + 三条制度类（户口命中/户口查无/衍生）
    (wsx / "audit-programs" / "废料审计程序_v1.0.md").write_text("""# 废料审计程序

## 二、情境分析

### 2.1 风险识别清单

| 风险编号 | 风险名称 | 风险描述 | 来源标注 |
|------|------|------|------|
| R01 | 单人值守偷卖废料 | 值班员独自过磅，无人复核 | 【经验类】 |
| R02 | 地磅数据被改 | 地磅软件无操作日志 | 【系统类-推演】 |
| R19 | 过磅无复核 | 与制度分析同一件事 | 【制度类-设计缺陷：CG-001（废料管理制度）】 |
| R20 | 台账未登记 | 指向一条制度分析里根本没有的缺口 | 【制度类-设计缺陷：CG-999（废料管理制度）】 |
| R21 | 值班交接无留痕 | 由已有缺口衍生出的新问题 | 【制度类-设计缺陷：CG-001衍生（废料管理制度）】 |

## 三、测试程序（轨道A：控制有效性测试）

<!-- track A -->
| 风险编号 | 风险名称 | 控制有效性测试程序 | 取数来源 |
|------|------|------|------|
| R01 | 单人值守偷卖废料 | 现场观察过磅流程 | 现场 |
""", encoding="utf-8")

    t = SANDBOX / "程序风险桌.json"
    _run("ledger.py", "create", t, "--table", "废料管理")
    r = _run("ledger.py", "sweep", t, "--workspace", ws)
    check("带程序文件的项目收料能跑（退出码 0）", r.returncode == 0, f"退出码={r.returncode}")
    d = json.loads(t.read_text(encoding="utf-8-sig"))
    cells = {x["slot"]: x["text"] for x in d["left"]}
    sig = cells["说不清的信号"]
    everything = cells["确定的毛病"] + cells["怀疑偷骗"] + sig

    check("推演风险（经验类）→ 上桌，落信号格", "R01" in sig)
    check("推演风险（系统类）→ 上桌，落信号格", "R02" in sig)
    check("制度类·户口命中 → 不上桌（制度分析已收）", "R19" not in everything)
    check("制度类·户口查无 → 仍上桌（宁可多收不可漏）", "R20" in sig)
    check("制度类·衍生款 → 严处理，不上桌", "R21" not in everything)
    check("被跳过的衍生条正文也没漏进桌上", "值班交接" not in everything)

    # 守恒：程序风险净上桌 = 推演 2 条 + 户口查无 1 条 = 3（不是 0，也不是 5）
    risk_lines = [l for x in d["left"] for l in x["text"].split("；")
                  if l.startswith(("R01", "R02", "R19", "R20", "R21"))]
    check("守恒：只有 3 条程序风险上桌（2 推演 + 1 户口查无）",
          len(risk_lines) == 3, f"实际 {len(risk_lines)}：{risk_lines}")

    # 反复收不重复（R 条目也走 ingested 记账）
    before = table_text(t)
    _run("ledger.py", "sweep", t, "--workspace", ws)
    check("再收一次 → 一个字没变", table_text(t) == before)


def test_sweep_idempotent():
    print("\n[8] 收料：反复收不重复；状态变了只挪格不两挂")
    ws = _make_source_project("幂等项目")
    t = SANDBOX / "幂等桌.json"
    _run("ledger.py", "create", t, "--table", "幂等")
    _run("ledger.py", "sweep", t, "--workspace", ws)
    before = table_text(t)

    r = _run("ledger.py", "sweep", t, "--workspace", ws)
    check("第二次收料 → 一个字没变", table_text(t) == before, r.stdout.strip()[:40])

    _run("ledger.py", "add-line", t, "--slot", "说不清的信号", "--text", "人工补一句")
    _run("ledger.py", "sweep", t, "--workspace", ws)
    d = json.loads(t.read_text(encoding="utf-8-sig"))
    sig = next(x for x in d["left"] if x["slot"] == "说不清的信号")["text"]
    check("人写的字收料碰不掉", "人工补一句" in sig)

    p = ws / "internal-audit-workspace" / "policy-analyses" / "废料制度_分析.json"
    a = json.loads(p.read_text(encoding="utf-8-sig"))
    for g in a["control_gaps"]:
        if g["id"] == "CG-002":
            g["verification_status"] = "已确认"
    p.write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
    _run("ledger.py", "sweep", t, "--workspace", ws)
    d = json.loads(t.read_text(encoding="utf-8-sig"))
    cells = {x["slot"]: x["text"] for x in d["left"]}
    check("状态变了 → 挪到确定的毛病", "CG-002" in cells["确定的毛病"])
    check("状态变了 → 信号格里不留旧行", "CG-002" not in cells["说不清的信号"])

    before_dry = table_text(t)
    r = _run("ledger.py", "sweep", t, "--workspace", ws, "--dry-run")
    check("--dry-run 只看不写", table_text(t) == before_dry and "试算" in r.stdout)


# ══════════════════════════════════════════════════════════════
# 断言 9（C3）：信号池不再是黑洞——池里有、桌上没有，门卫要点名
# ══════════════════════════════════════════════════════════════
def test_pool_consumed():
    print("\n[9] 信号池被真正消费：池里有、桌上没有 → 门卫点名")
    ws = _make_source_project("信号池项目")
    t = SANDBOX / "池桌.json"
    _run("ledger.py", "create", t, "--table", "池")
    for s in ("确定的毛病", "怀疑偷骗", "说不清的信号"):
        _run("ledger.py", "add-line", t, "--slot", s, "--text", "占位")

    r = _run("check.py", t, "--workspace", ws)
    check("没收料 → 门卫点名信号池", "信号池" in r.stdout, f"退出码={r.returncode}")

    _run("ledger.py", "sweep", t, "--workspace", ws)
    r = _run("check.py", t, "--workspace", ws)
    check("收料后 → 不再提信号池", "信号池" not in r.stdout, f"退出码={r.returncode}")


# ══════════════════════════════════════════════════════════════
# 断言 10（C4）：证据缺失即信号（宪法#9）——三个方向缺一不可
# ══════════════════════════════════════════════════════════════
def test_add_gap():
    print("\n[10] 证据缺失即信号（宪法#9）")
    t = SANDBOX / "缺口桌.json"
    _run("ledger.py", "create", t, "--table", "缺口")
    r = _run("ledger.py", "add-gap", t, "--finding", "F-2026-003",
             "--missing", "绩效评分原始记录")
    check("add-gap 能记（退出码 0）", r.returncode == 0, f"退出码={r.returncode}")
    d = json.loads(t.read_text(encoding="utf-8-sig"))
    sig = next(x for x in d["left"] if x["slot"] == "说不清的信号")["text"]
    check("三个可能方向都写进去了",
          all(k in sig for k in ("业务未发生", "管理缺失", "证据被消除")))
    check("点名了哪张单、缺什么",
          "F-2026-003" in sig and "绩效评分原始记录" in sig)

    r = _run("ledger.py", "add-gap", t, "--finding", "F-2026-003", "--missing", "   ")
    check("没写缺什么 → 明确拒绝（退出码 1）", r.returncode == 1, f"退出码={r.returncode}")


# ══════════════════════════════════════════════════════════════
# 断言 6（B2/B5/B6）：流程文档——桌子必在，不再"没有就跳过"
# ══════════════════════════════════════════════════════════════
def test_skill_docs():
    print("\n[6] 流程文档：桌子必在，不再'没有就跳过'")
    write_docs = [
        "document-organizer/SKILL.md",
        "audit-interview-designer/SKILL.md",
        "audit-execution-assistant/SKILL.md",
        "audit-finding-debate/SKILL.md",
        "internal-audit-report-generator/SKILL.md",
    ]
    for d in write_docs:
        text = (REPO_ROOT / d).read_text(encoding="utf-8")
        check(f"{d.split('/')[0]}：不再有'没有就跳过'", "没有就跳过" not in text)

    init = (REPO_ROOT / "project-init/SKILL.md").read_text(encoding="utf-8")
    check("建项目技能：会开桌子", "ledger.py create" in init)
    check("建项目技能：桌子落地在 audit-table/", "audit-table" in init)

    # C1/C2/C4：收料和缺口要走命令，写桌子的技能必须提
    for d in ("document-organizer/SKILL.md", "audit-interview-designer/SKILL.md",
              "audit-execution-assistant/SKILL.md",
              "internal-audit-report-generator/SKILL.md"):
        check(f"{d.split('/')[0]}：用 sweep 收料",
              "ledger.py sweep" in (REPO_ROOT / d).read_text(encoding="utf-8"))
    check("执行技能：证据缺失走 add-gap",
          "add-gap" in (REPO_ROOT / "audit-execution-assistant/SKILL.md")
          .read_text(encoding="utf-8"))

    # B4：三张表的产出方要填抽屉入口
    for d in ("audit-interview-designer/SKILL.md",
              "internal-audit-program-generator/SKILL.md",
              "internal-audit-report-generator/SKILL.md"):
        check(f"{d.split('/')[0]}：产出后填抽屉入口",
              "set-drawer" in (REPO_ROOT / d).read_text(encoding="utf-8"))

    # 洞察要有户口：对抗验证补充建议不能只留程序文件尾部
    gen = (REPO_ROOT / "internal-audit-program-generator/SKILL.md").read_text(encoding="utf-8")
    check("程序生成：对抗验证补充建议须立设计观察户口",
          "立户口" in gen and "design-assessments/" in gen)
    check("程序生成：制度类风险沿用原编号（防重复）", "沿用原编号" in gen)


def main():
    print(f"沙箱：{SANDBOX}")
    test_rollback_full()
    test_crash_guard()
    test_import_bad_workspace()
    test_high_risk_grades()
    test_drawers()
    test_legacy_table()
    test_sweep_routing()
    test_real_fieldnames()
    test_program_risks()
    test_sweep_idempotent()
    test_pool_consumed()
    test_add_gap()
    test_skill_docs()
    print()
    if failures:
        print(f"❌ 失败 {len(failures)} 条：")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("✅ 全过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
