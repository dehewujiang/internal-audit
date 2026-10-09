#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate-policy-analysis.py — 制度分析 JSON 硬校验脚本

对 document-organizer 输出的制度分析 JSON 执行确定性校验。
在 document-organizer/SKILL.md Step 5 调用。

[INPUT]:  policy-analyses/ 下的 JSON 文件路径（可选 --workspace 指定审计工作区，用于原文抽查）
[OUTPUT]: JSON 格式校验报告 + 退出码 (0=pass, 1=warn, 2=block)；原文抽查走独立字段，不参与退出码
[POS]:    _shared/scripts 的制度分析校验工具，被 document-organizer/SKILL.md 引用
"""

import json
import os
import re
import sys
import html
import zipfile
import argparse
from pathlib import Path


# ── 校验项 ──────────────────────────────────────────────

def check_schema(data):
    """[S] JSON schema 合规——必要数组存在且非空"""
    required_arrays = ["control_points", "risk_points"]
    missing = []
    empty = []
    for key in required_arrays:
        if key not in data:
            missing.append(key)
        elif not isinstance(data[key], list):
            missing.append(f"{key}（类型错误，应为数组）")
        elif len(data[key]) == 0:
            empty.append(key)
    issues = []
    if missing:
        issues.append(f"缺少必要字段: {', '.join(missing)}")
    if empty:
        issues.append(f"空数组: {', '.join(empty)}")
    return len(missing) == 0, "; ".join(issues) if issues else None


def check_ocr_completeness(data, filename=""):
    """[O] OCR 完整性——total_controls>0 但 analyzed_controls==0 说明 PDF 未 OCR"""
    total = data.get("total_controls", 0)
    analyzed = data.get("analyzed_controls", 0)
    if not isinstance(total, int) or not isinstance(analyzed, int):
        return True, "total_controls/analyzed_controls 非数字，跳过"
    if total > 0 and analyzed == 0:
        return False, (f"total_controls={total} 但 analyzed_controls=0"
                       "，疑似 PDF 未 OCR，请先运行 OCR 工具后重新分析")
    return True, None


def check_schema_version(data):
    """[V] schema_version 存在"""
    sv = data.get("schema_version")
    if not sv:
        return False, "缺少 schema_version 字段"
    return True, f"schema_version: {sv}"


def check_document_version(data):
    """[V] 制度版本与效力日期——warn 级（存量 JSON 可能缺失，不阻断；新输出必须包含）"""
    di = data.get("document_info")
    if not isinstance(di, dict):
        return False, "缺少 document_info（制度版本信息缺失，新输出必须包含）"
    missing = []
    if not di.get("version"):
        missing.append("version（版本号）")
    if not di.get("effective_date"):
        missing.append("effective_date（生效日期）")
    if missing:
        return False, f"document_info 缺少: {', '.join(missing)}——制度版本缺失会导致废止制度污染风险识别"
    return True, f"document_info.version={di['version']}, effective_date={di['effective_date']}"


def check_control_points_traceability(data):
    """[T] 控制点可追溯——每个控制点指向原文条款"""
    points = data.get("control_points", [])
    if not points:
        return True, "无控制点，跳过"
    no_source = []
    for i, cp in enumerate(points):
        if not isinstance(cp, dict):
            continue
        has_source = any(cp.get(f) for f in ("source_section", "source_doc", "source_clause", "原文出处"))
        if not has_source:
            title = cp.get("title", cp.get("name", f"#{i+1}"))
            no_source.append(str(title)[:40])
    if len(no_source) > len(points) * 0.3:
        return False, f"{len(no_source)}/{len(points)} 个控制点缺少原文出处: {', '.join(no_source[:3])}"
    if no_source:
        return True, f"{len(no_source)} 个控制点缺少出处（未超阈值，非阻断）"
    return True, None


def check_risk_points_structure(data):
    """[R] 风险点有描述和风险等级"""
    points = data.get("risk_points", [])
    if not points:
        return True, "无风险点，跳过"
    issues = []
    for i, rp in enumerate(points):
        if not isinstance(rp, dict):
            continue
        has_desc = any(rp.get(f) for f in ("description", "title", "name"))
        has_level = any(rp.get(f) for f in ("severity", "risk_level", "level"))
        label = rp.get("title", rp.get("name", f"#{i+1}"))
        if not has_desc:
            issues.append(f"风险点 {label}: 缺少描述")
        if not has_level:
            issues.append(f"风险点 {label}: 缺少风险等级")
    if len(issues) > 3:
        return False, f"{len(issues)} 个问题（仅显示前3）: {'; '.join(issues[:3])}"
    if issues:
        return True, "; ".join(issues)
    return True, None


def check_control_gaps_not_all_pending(data):
    """[G] 控制缺口不是全部标记为待确认"""
    gaps = data.get("control_gaps", [])
    if not gaps:
        return True, "无控制缺口，跳过"
    pending = sum(1 for g in gaps if isinstance(g, dict)
                  and g.get("verification_status", "").startswith("待"))
    if pending == len(gaps):
        return False, f"全部 {len(gaps)} 个控制缺口都标记为「待确认」，至少应有部分已确认"
    return True, f"{len(gaps)} 个缺口，{pending} 个待确认，{len(gaps)-pending} 个已确认"


def check_decision_log(data):
    """[L] 决策理由记录——检查 decision_log 字段（可选字段，不阻断）"""
    dl = data.get("decision_log")
    if not dl:
        return True, "decision_log 未提供（policy-analyses 正常产出的可选字段，不阻断）"
    if not isinstance(dl, list):
        return True, "decision_log 类型异常（不阻断）"
    if len(dl) == 0:
        return True, "decision_log 为空数组（未记录决策，不阻断）"

    found_ids = set()
    for entry in dl:
        if isinstance(entry, dict):
            did = entry.get("decision_id", "")
            if did:
                found_ids.add(did)

    issues = []
    if "D-001" not in found_ids:
        issues.append("缺少 D-001（制度关注重点）")
    if "D-002" not in found_ids:
        issues.append("缺少 D-002（设计观察升级判断）")

    if issues:
        # Check if rationale is filled
        for entry in dl:
            if isinstance(entry, dict) and entry.get("decision_id") in ("D-001", "D-002"):
                rationale = entry.get("rationale", "")
                if rationale and len(rationale.strip()) >= 10:
                    # Remove from issues if it has a real rationale
                    if entry["decision_id"] in found_ids:
                        for i, iss in enumerate(issues):
                            if entry["decision_id"] in iss:
                                issues[i] = None
                        issues = [i for i in issues if i is not None]
        if issues:
            return True, "; ".join(issues) + "（非阻断，建议补充）"

    # Check rationale depth
    short_rationales = []
    for entry in dl:
        if isinstance(entry, dict) and entry.get("decision_id") in ("D-001", "D-002"):
            rationale = entry.get("rationale", "")
            if len(rationale.strip()) < 20:
                short_rationales.append(f"{entry.get('decision_id')} 理由偏短({len(rationale.strip())}字)")

    if short_rationales:
        return True, "; ".join(short_rationales) + "（非阻断）"

    return True, f"已记录 {len(found_ids)} 个决策点: {', '.join(sorted(found_ids))}"


# ── 原文抽查（独立通道：只报告，不参与退出码） ──────────
#
# 背景：本脚本此前只读 AI 输出的 JSON——check_ocr_completeness 比的是 AI 自报的
# 两个数字，check_control_points_traceability 只查出处字段非空，都不看原文。
# 本节改为打开制度原件，核对控制点引用的条款号是否真实存在。
#
# 为何走独立通道：audit_gate.py 判定校验是否通过时只看退出码是否为 0，
# warn(exit 1) 与 block(exit 2) 在它眼里没有区别。若把新检查计入 action，
# 存量项目（控制点普遍无 source 字段）会被当场拦下。故结果单列字段。

# 条款号：兼容阿拉伯数字（第3条/第3.2条）与中文数字（第三条/第十二条），比对前统一归一化
CLAUSE_RE = re.compile(r'第\s*([0-9]+(?:\.[0-9]+)*|[零一二三四五六七八九十]+)\s*条')
SOURCE_EXTS = (".txt", ".md", ".docx")
_CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
           "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def clause_key(raw):
    """条款号归一化：中文数字 → 阿拉伯数字，其余原样返回（第3.2条 保持不变）"""
    raw = raw.strip()
    if not re.fullmatch(r'[零一二三四五六七八九十]+', raw):
        return raw
    if raw == "十":
        return "10"
    if "十" in raw:
        tens, _, ones = raw.partition("十")
        t = _CN_NUM.get(tens, 1) if tens else 1
        o = _CN_NUM.get(ones, 0) if ones else 0
        return str(t * 10 + o)
    digits = [_CN_NUM.get(ch) for ch in raw]
    return "".join(str(d) for d in digits) if all(d is not None for d in digits) else raw


def find_workspace(start=None):
    """从 start（默认 CWD）向上查找 internal-audit-workspace/，找不到返回 None"""
    cur = Path(start).resolve() if start else Path.cwd()
    for parent in [cur, *cur.parents]:
        ws = parent / "internal-audit-workspace"
        if ws.is_dir():
            return ws
    return None


def read_docx_text(path):
    """用标准库抽取 docx 正文文字（零依赖；失败返回 None）"""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception:
        return None
    xml = xml.replace("</w:p>", "\n")
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def locate_source_text(data, ws):
    """按 doc_name 在 documents/ 定位制度原文，返回 (text, source_name, note)"""
    if ws is None:
        return None, "", "未定位到 internal-audit-workspace，跳过原文抽查"
    docs_dir = ws / "documents"
    if not docs_dir.is_dir():
        return None, "", "工作区无 documents/ 目录，跳过原文抽查"

    name = str(data.get("doc_name") or "").strip()
    if not name:
        return None, "", "JSON 缺 doc_name，无法定位原文"

    stem = Path(name).stem
    candidates = [docs_dir / f"{stem}_ocr.txt"]
    candidates += [docs_dir / f"{stem}{e}" for e in SOURCE_EXTS]
    # 模糊兜底：文件名包含 doc_name 的（如「NPM003 考勤管理规定 A5.docx」）
    for p in sorted(docs_dir.iterdir()):
        if p.is_file() and p not in candidates and stem in p.stem:
            candidates.append(p)

    for p in candidates:
        if not p.is_file():
            continue
        if p.suffix == ".docx":
            text = read_docx_text(p)
            if text:
                return text, p.name, None
            continue
        try:
            return p.read_text(encoding="utf-8", errors="ignore"), p.name, None
        except Exception:
            continue
    return None, "", f"documents/ 下未找到与「{name}」对应的原文或 _ocr.txt（PDF 原件需先跑 OCR）"


def check_source_reconciliation(data, source_text, source_name, note):
    """原文抽查：核对控制点引用的条款号是否真在原文里。结果单列，不参与 action。"""
    if source_text is None:
        return {"status": "skipped", "reason": note}

    src_clauses = {clause_key(m) for m in CLAUSE_RE.findall(source_text)}
    points = data.get("control_points", []) or []
    cited_ok, cited_missing, without_source, non_clause = [], [], [], []
    for i, cp in enumerate(points):
        if not isinstance(cp, dict):
            continue
        label = str(cp.get("control_id") or cp.get("title") or f"#{i+1}")
        raw = ""
        for f in ("source", "source_section", "source_clause", "原文出处"):
            if cp.get(f):
                raw = str(cp[f])
                break
        if not raw:
            without_source.append(label)
            continue
        ids = CLAUSE_RE.findall(raw)
        if not ids:
            non_clause.append(label)
            continue
        for cid in ids:
            ck = clause_key(cid)
            (cited_ok if ck in src_clauses else cited_missing).append(f"{label}→第{cid}条")

    return {
        "status": "checked",
        "source_file": source_name,
        "source_clauses": len(src_clauses),
        "control_points": len(points),
        "cited_ok": cited_ok,
        "cited_missing": cited_missing,
        "without_source": without_source,
        "non_clause_source": non_clause,
    }


# ── 主校验 ──────────────────────────────────────────────

def validate_policy_analysis(data, filename="", source_text=None, source_name="", source_note=""):
    """对制度分析 JSON 执行全部校验"""
    checks = {}

    passed, msg = check_schema(data)
    checks["schema"] = {"passed": passed, "message": msg}

    passed, msg = check_ocr_completeness(data, filename)
    checks["ocr_completeness"] = {"passed": passed, "message": msg}

    passed, msg = check_schema_version(data)
    checks["schema_version"] = {"passed": passed, "message": msg}

    passed, msg = check_document_version(data)
    checks["document_version"] = {"passed": passed, "message": msg}

    passed, msg = check_control_points_traceability(data)
    checks["traceability"] = {"passed": passed, "message": msg}

    passed, msg = check_risk_points_structure(data)
    checks["risk_points_structure"] = {"passed": passed, "message": msg}

    passed, msg = check_control_gaps_not_all_pending(data)
    checks["gaps_resolution"] = {"passed": passed, "message": msg}

    passed, msg = check_decision_log(data)
    checks["decision_log"] = {"passed": passed, "message": msg}

    blockers = [k for k, v in checks.items() if not v["passed"]
                and k in ("schema", "schema_version", "ocr_completeness")]
    warnings = [k for k, v in checks.items() if not v["passed"]
                and k not in ("schema", "schema_version", "ocr_completeness")]

    action = "block" if blockers else ("warn" if warnings else "pass")

    return {
        "file": filename,
        "action": action,
        "checks": checks,
        # 原文抽查：独立通道，不参与 action/退出码（见本文件「原文抽查」节说明）
        "source_reconciliation": check_source_reconciliation(
            data, source_text, source_name, source_note),
        "summary": {
            "total": len(checks),
            "passed": sum(1 for v in checks.values() if v["passed"]),
            "blockers": [{"check": k, "message": checks[k]["message"]} for k in blockers],
            "warnings": [{"check": k, "message": checks[k]["message"]} for k in warnings],
        }
    }


# ── CLI ──────────────────────────────────────────────────

def main():
    # Windows GBK → UTF-8（emoji 兼容）
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure and sys.stdout.encoding != 'utf-8':
        reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="制度分析 JSON 硬校验工具")
    parser.add_argument("path", help="JSON 文件路径（或目录）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--workspace", help="审计工作区路径（缺省从 CWD 向上查找 internal-audit-workspace/）")
    args = parser.parse_args()
    ws = Path(args.workspace).expanduser() if args.workspace else find_workspace()

    files = []
    target = args.path
    if os.path.isdir(target):
        for root, _, fnames in os.walk(target):
            for fn in sorted(fnames):
                if fn.endswith(".json"):
                    files.append(os.path.join(root, fn))
    elif os.path.isfile(target):
        files.append(target)
    else:
        print(f"[ERROR] 路径不存在: {target}")
        sys.exit(2)

    if not files:
        print("[ERROR] 未找到 .json 文件")
        sys.exit(2)

    results = []
    has_blocker = False
    has_warn = False

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  🔴 [JSON格式错误] {os.path.basename(fpath)}: {e}")
            has_blocker = True
            continue

        src_text, src_name, src_note = locate_source_text(data, ws)
        report = validate_policy_analysis(
            data, filename=os.path.basename(fpath),
            source_text=src_text, source_name=src_name, source_note=src_note)
        results.append(report)
        if report["action"] == "block":
            has_blocker = True
        elif report["action"] == "warn":
            has_warn = True

        if not args.json:
            emoji = {"pass": "✅", "warn": "⚠️", "block": "🔴"}
            print(f"\n  {emoji[report['action']]} {os.path.basename(fpath)} — {report['action'].upper()}")
            for name, d in report["checks"].items():
                status = "✅" if d["passed"] else "🔴" if name in ("schema", "schema_version", "ocr_completeness") else "⚠️"
                msg = d.get("message") or "通过"
                print(f"    {status} [{name}] {msg[:100]}")
            rec = report.get("source_reconciliation", {})
            if rec.get("status") == "checked":
                miss = rec.get("cited_missing", [])
                mark = "🔴" if miss else "✅"
                print(f"    {mark} [原文抽查] 原文条款 {rec['source_clauses']} 个；控制点 {rec['control_points']} 个；"
                      f"条款引用 {len(rec['cited_ok'])} 条命中、{len(miss)} 条未在原文找到")
                for m in miss[:5]:
                    print(f"        └ 原文中不存在: {m}")
            else:
                print(f"    ℹ️ [原文抽查] {rec.get('reason', '跳过')}（独立通道，不影响校验结论）")

    if not args.json:
        passed = sum(1 for r in results if r["action"] == "pass")
        warned = sum(1 for r in results if r["action"] == "warn")
        blocked = sum(1 for r in results if r["action"] == "block")
        print(f"\n{'='*60}")
        print(f"  共计 {len(results)} 个文件: ✅ {passed}  ⚠️  {warned}  🔴 {blocked}")
        print(f"{'='*60}\n")
        # 结构化答卷（B1）：人话模式尾行追 SHEET；--json 保持纯 JSON
        # （test_source_reconciliation 全量解析 stdout；B2 闸机改读人话尾行）。
        verdict = "block" if has_blocker else "warn" if has_warn else "pass"
        print("SHEET:" + json.dumps({
            "tool": "validate-policy-analysis",
            "action": verdict,
            "message": f"{len(results)} 个文件: 过了 {passed}, 警告 {warned}, 拦下 {blocked}",
            "summary": {"total": len(results), "passed": passed,
                        "warned": warned, "blocked": blocked},
            "details": results,
            "crashed": False,
        }, ensure_ascii=False))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    sys.exit(2 if has_blocker else 1 if has_warn else 0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # 未预期崩溃 → exit(2) 阻断。绝不能让崩溃的退出码(1)被闸机误判成"警告"而放行
        import traceback
        print("SHEET:" + json.dumps({
            "tool": "validate-policy-analysis",
            "action": "block",
            "message": "脚本崩溃，已转拦下",
            "summary": {"total": 0, "passed": 0, "warned": 0, "blocked": 1},
            "details": [],
            "crashed": True,
        }, ensure_ascii=False))
        traceback.print_exc()
        sys.exit(2)
