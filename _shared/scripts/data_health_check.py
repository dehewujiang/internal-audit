#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据体检室 — 证据入桌前先体检，只看不改

用法:
    # 体检单个文件
    python data_health_check.py file <path>

    # 体检整个目录（递归，含子目录）
    python data_health_check.py dir <path>

    # 输出 JSON（供程序消费 / 写入证据清单备注）
    python data_health_check.py file <path> --json

设计原则（对齐 ADR-028 加法不减法）:
    - 只读文件内容，不修改任何数据
    - 每份证据给出分诊结论: pass(直接分析) / fix(需小处理，附步骤) / manual(必须人工干预)
    - 真实格式以魔数为准，不信扩展名（工资表 .xlsx 实为加密 OLE2 的教训）
"""

import sys
import os
import json
from pathlib import Path


# ── 魔数识别：文件真实格式 ───────────────────────────────

MAGIC_ZIP = b'PK\x03\x04'          # 新版 xlsx/docx/pptx (OOXML)
MAGIC_OLE2 = b'\xd0\xcf\x11\xe0'   # 旧版 xls 或加密的 OOXML


def detect_real_format(path: Path) -> dict:
    """读文件头 8 字节判断真实格式。返回 {magic_name, needs_password, comment}"""
    try:
        head = open(path, 'rb').read(8)
    except OSError as e:
        return {"magic_name": "unreadable", "needs_password": None, "error": str(e)}

    if head[:4] == MAGIC_ZIP:
        return {"magic_name": "zip_ooxml", "needs_password": False, "error": None}
    if head[:4] == MAGIC_OLE2:
        # OLE2 需进一步区分：加密 OOXML 还是普通旧版 xls
        try:
            ole_probe = _ole2_probe(path)
        except Exception as e:
            ole_probe = {"error": str(e)}
        if ole_probe.get("encrypted"):
            return {"magic_name": "ole2_encrypted", "needs_password": True,
                    "error": "文件已加密（含 EncryptedPackage）。需要密码，或请对方去掉密码/保护后重发"}
        return {"magic_name": "ole2_xls", "needs_password": False, "error": None}
    if head.startswith(b'%PDF'):
        return {"magic_name": "pdf", "needs_password": False, "error": None}
    if head[:3] == b'\xff\xd8\xff':
        return {"magic_name": "jpeg", "needs_password": False, "error": None}
    if head[:8] == b'\x89PNG\r\n\x1a\n':
        return {"magic_name": "png", "needs_password": False, "error": None}
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return {"magic_name": "webp", "needs_password": False, "error": None}
    if head[:2] == b'BM':
        return {"magic_name": "bmp", "needs_password": False, "error": None}
    return {"magic_name": "unknown", "needs_password": False, "error": None}


def _ole2_probe(path: Path) -> dict:
    """OLE2 复合文档探测：区分加密 OOXML 与旧版 xls。纯字节解析，零依赖。"""
    data = open(path, 'rb').read(2 * 1024 * 1024)  # 前 2MB 足够看到目录流名
    # OLE2 目录流名以 UTF-16LE 存储，纯 ASCII 字节序列匹配不到（实测踩坑）
    has_encrypted = (b'E\x00n\x00c\x00r\x00y\x00p\x00t\x00e\x00d\x00P\x00a\x00c\x00k\x00a\x00g\x00e\x00' in data
                     or b'EncryptedPackage' in data)
    has_enc_transform = (b'S\x00t\x00r\x00o\x00n\x00g\x00E\x00n\x00c\x00r\x00y\x00p\x00t\x00i\x00o\x00n\x00D\x00a\x00t\x00a\x00S\x00p\x00a\x00c\x00e\x00' in data
                         or b'StrongEncryptionDataSpace' in data
                         or b'E\x00n\x00c\x00r\x00y\x00p\x00t\x00i\x00o\x00n\x00I\x00n\x00f\x00o\x00' in data
                         or b'EncryptionInfo' in data)
    return {"encrypted": has_encrypted and has_enc_transform}


# ── Excel 体检 ──────────────────────────────────────────

def check_excel(path: Path, real_format: dict) -> dict:
    """Excel/.csv 体检。返回结构化报告。"""
    report = {"file": str(path), "category": "spreadsheet", "issues": [],
              "triage": "pass", "sheets": []}

    if real_format["magic_name"] == "ole2_encrypted":
        report["triage"] = "manual"
        report["issues"].append(
            "CRITICAL: 文件加密。任何程序都读不出内容——需要密码，或请对方去掉保护后重发")
        return report
    if real_format["magic_name"] == "ole2_xls":
        report["issues"].append(
            "FORMAT: 扩展名与真实格式不符（实际是旧版 xls 格式）。读取引擎可能与按扩展名推断的预期不一致")
        report["triage"] = "fix"

    import pandas as pd
    xl = None
    try:
        xl = pd.ExcelFile(path)
    except Exception as e:
        report["triage"] = "manual"
        report["issues"].append(f"CRITICAL: 无法打开: {e}")
        return report

    for sheet_name in xl.sheet_names:
        sheet_report = _check_single_sheet(path, sheet_name)
        report["sheets"].append(sheet_report)
        for issue in sheet_report["issues"]:
            report["issues"].append(f"[{sheet_name}] {issue}")

    # 汇总分诊
    sheet_triages = [s["triage"] for s in report["sheets"]]
    if "manual" in sheet_triages:
        report["triage"] = "manual"
    elif "fix" in sheet_triages or report["triage"] == "fix":
        report["triage"] = "fix"

    # 多版本提示：文件名含 副本/v2/v3/日期戳 等版本痕迹
    name_l = path.stem.lower()
    version_hints = [h for h in ('副本', 'copy', 'v1', 'v2', 'v3', 'v4', 'final', '最终')
                     if h in name_l]
    if version_hints:
        report["issues"].append(
            f"VERSION: 文件名含版本痕迹 {version_hints}——同目录可能存在多个版本，无法从文件名判断哪份是最终版。请人工确认以哪份为准")
        if report["triage"] == "pass":
            report["triage"] = "fix"
    return report


def _check_single_sheet(path: Path, sheet_name: str) -> dict:
    """单张表体检：真假表头 / 前置空行 / 列格式混杂。"""
    import pandas as pd
    sr = {"sheet": sheet_name, "triage": "pass", "issues": [],
          "header_row": 0, "columns": [], "suggest_read": None}
    try:
        raw = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=30)
    except Exception as e:
        sr["triage"] = "manual"
        sr["issues"].append(f"读取失败: {e}")
        return sr

    header_row = _find_header_row(raw)
    sr["header_row"] = header_row
    if header_row > 0:
        sr["issues"].append(
            f"表头不在第一行（第 {header_row+1} 行才有列名，前面是标题/说明/空行）。"
            f"直接 read 顶行会把标题当列名——建议 header={header_row}")
        sr["triage"] = "fix"
        sr["suggest_read"] = {"header": header_row}

    # 全空行检测
    empty_rows = int(raw.isna().reindex(raw.columns, axis=1).reindex().sum(axis=1).apply(
        lambda x: raw.loc[x.name] if False else 0).sum()) if False else _count_empty_rows(raw)
    if empty_rows > 0:
        sr["issues"].append(f"前 30 行中含 {empty_rows} 行全空（数据区中间隔断行，分析时会断开）")
        if sr["triage"] == "pass":
            sr["triage"] = "fix"

    # 列格式混杂：同一列里既有数字又有文本
    if header_row < len(raw):
        body = raw.iloc[header_row:]
        mixed_cols = _mixed_type_cols(body)
        if mixed_cols:
            sr["issues"].append(
                f"列格式混杂: {mixed_cols[:10]}（同一列既有文本又有数字，多为日期/编号格式不统一——"
                f"分析前需先统一格式，否则比较/汇总必错）")
            sr["triage"] = "fix"

    cols = raw.iloc[header_row] if header_row < len(raw) else []
    sr["columns"] = [str(c) for c in cols.tolist()] if hasattr(cols, 'tolist') else []
    if not any(str(c).strip() for c in sr["columns"]):
        sr["issues"].append("表头层全空——这是图片或管控过的表，需人工阅读")
        sr["triage"] = "manual"
    return sr


def _find_header_row(raw) -> int:
    """猜表头行：一行里'字符串列占比高+无全空单元格'的行更像表头。简化启发式。"""
    for i in range(min(10, len(raw))):
        row = raw.iloc[i]
        vals = row.dropna()
        if len(vals) < 2:
            continue  # 空行或单格标题行
        strs = sum(1 for v in vals if isinstance(v, str) and v.strip())
        if strs >= max(2, int(len(vals) * 0.7)):
            return i
    return 0  # 猜不出，默认第 0 行


def _count_empty_rows(raw) -> int:
    import pandas as pd
    empty = raw.replace('', pd.NA).isna().all(axis=1)
    return int(empty.sum())


def _mixed_type_cols(body) -> list:
    """体 :TEXT 里同一列既有 str 又有 numeric。"""
    mixed = []
    for col in body.columns:
        series = body[col].dropna()
        if len(series) < 3:
            continue
        has_str = sum(1 for v in series if isinstance(v, str) and v.strip())
        has_num = sum(1 for v in series if isinstance(v, (int, float)))
        if has_str >= 1 and has_num >= 1:
            mixed.append(str(col))
    return mixed


# ── 图片体检（只归类，OCR 由调用方按需走 tools/pdf_ocr_extractor）──

def check_image(path: Path, real_format: dict) -> dict:
    report = {"file": str(path), "category": "image", "issues": [],
              "triage": "fix", "ocr_pending": True}
    size_kb = path.stat().st_size / 1024
    report["issues"].append(
        f"图片证据: 内容需 OCR 提取或人工阅读后才能成为可分析数据。"
        f"建议走人工确认页流程（OCR 结果待你核对确认后才用于分析）")
    if size_kb > 8 * 1024:
        report["issues"].append(
            f"大图警告: {size_kb/1024:.0f}MB——可能是拍照整页/多页文档拼接，OCR 或人工阅读成本高，"
            f"建议先让提供方给出关键数据的文本摘录")
    return report


# ── PDF / pptx / 其他 ─────────────────────────────────────

def check_pdf(path: Path, real_format: dict) -> dict:
    report = {"file": str(path), "category": "pdf", "issues": [], "triage": "fix"}
    size_mb = path.stat().st_size / (1024 * 1024)
    report["issues"].append(
        f"PDF 证据: {size_mb:.0f}MB。 systematic 内容（表格/数字）需先提取文本/表格，"
        f"扫描件质量差时需 OCR 或人工阅读")
    if size_mb > 20:
        report["issues"].append(
            "大文件警告: 超 20MB 的 PDF 多为整卷扫描档案——直接分页提取效率低且易漏页，"
            "建议先人工翻看确定关键页范围，再针对性提取")
        report["triage"] = "manual"
    return report


def check_other(path: Path, real_format: dict) -> dict:
    return {"file": str(path), "category": real_format["magic_name"],
            "issues": ["非表格/图片/PDF 类型，本体检室不判内容，请人工确认"],
            "triage": "manual"}


# ── 图片 OCR 深检（带置信度，产出待人工确认清单）──────────

def ocr_check(path: Path, min_conf: float = 0.85) -> dict:
    """
    图片证据 OCR 深检：提取文字并按置信度分级。

    引擎：PaddleOCR（系统正式引擎，tools/pdf_ocr_extractor.py 同款），
    Windows 需 enable_mkldnn=False 绕过 PaddlePaddle 3.3.x oneDNN 回归 bug（f2b154a）。

    实测校准（2026-09-10，广东长华真实图片）：PaddleOCR 数字/日期识别置信度
    普遍 0.98+，斜杠/字母完整——低置信（<min_conf）条目才需人工逐条核对，
    高置信条目默认采信、抽查即可。

    返回 {"file", "items": [{text, conf, trust}], "summary"}
    trust: high(≥min_conf 默认采信) / low(<min_conf 必须人工核对)
    """
    report = {"file": str(path), "items": [], "engine": "paddleocr", "summary": {},
              "triage": "manual",
              "issues": ["OCR 结果为候选文本：低置信条目须逐条人工核对原图后才能使用；"
                         "高置信条目默认采信，抽查明细由用户决定"]}
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        report["issues"].append(
            "PaddleOCR 未安装（pip install paddlepaddle paddleocr）。"
            "体检查不出内容，请安装后重跑")
        return report
    try:
        ocr = PaddleOCR(use_doc_orientation_classify=False, use_doc_unwarping=False,
                        use_textline_orientation=False, enable_mkldnn=False)
        results = ocr.predict(str(path))
    except Exception as e:
        report["issues"].append(f"OCR 引擎失败: {e}")
        return report

    items = []
    for r in results:
        for text, conf in zip(r["rec_texts"], r["rec_scores"]):
            items.append({"text": text, "conf": round(float(conf), 2),
                          "trust": "high" if conf >= min_conf else "low"})
    n_low = sum(1 for i in items if i["trust"] == "low")
    has_numbers = sum(1 for i in items if any(c.isdigit() for c in i["text"]))
    report["items"] = items
    report["summary"] = {"total": len(items), "low_conf": n_low,
                         "numeric_texts": has_numbers,
                         "low_conf_rate": round(n_low / max(len(items), 1), 2)}
    if n_low:
        report["issues"].append(
            f"{n_low}/{len(items)} 条识别置信度低于 {min_conf}（低置信率 {report['summary']['low_conf_rate']}）"
            f"——低置信条目已在下方标 low，逐条人工核对原图")
    if has_numbers:
        report["issues"].append(
            f"含 {has_numbers} 条数字类文字——用于计数/汇总前建议抽查原图")
    return report


# ── 总入口 ──────────────────────────────────────────────

CHECKERS = {"spreadsheet_checkers": ("ole2_encrypted", "ole2_xls", "zip_ooxml")}


def check_file(path: Path) -> dict:
    real_format = detect_real_format(path)
    magic = real_format["magic_name"]
    ext = path.suffix.lower().lstrip('.')
    comment = {"magic": magic, "needs_password": real_format.get("needs_password")}
    if real_format.get("error"):
        comment["error"] = real_format["error"]

    try:
        if magic == "ole2_encrypted":
            result = check_excel(path, real_format)
        elif magic in ("zip_ooxml", "ole2_xls") and ext not in ('.pptx', '.docx'):
            # doc/ppt 等 OOXML 族非表格文件交给 other；扩展名为表格类也进 excel 体检
            result = check_excel(path, real_format)
        elif magic in ('jpeg', 'png', 'webp', 'bmp') or ext in ('.jpg', '.jpeg', '.png', '.bmp', '.webp'):
            result = check_image(path, real_format)
        elif magic == 'pdf' or ext == '.pdf':
            result = check_pdf(path, real_format)
        else:
            result = check_other(path, real_format)
    except Exception as e:
        result = {"file": str(path), "triage": "manual",
                  "issues": [f"体检器自身异常（请报告此 bug）: {e}"]}
    result["type_comment"] = comment
    return result


def check_dir(base: Path) -> list:
    exts = {'xlsx', 'xls', 'csv', 'jpg', 'jpeg', 'png', 'bmp', 'webp', 'pdf'}
    all_files = sorted(p for p in base.rglob('*') if p.suffix.lower().lstrip('.') in exts)
    return [check_file(p) for p in all_files]


# ── CLI 展示 ─────────────────────────────────────────────

TRIAGE_BADGE = {"pass": "🟢 可直接分析", "fix": "🟡 需小处理", "manual": "🔴 必须人工干预"}


def _show_ocr(r):
    """OCR 待确认清单展示：低置信在前（优先核对）。"""
    print(f"\n📸 OCR 待人工确认  {Path(r['file']).name}")
    for issue in r["issues"]:
        print(f"   ⚠ {issue}")
    items = sorted(r["items"], key=lambda x: (x["trust"] != 'low', -x["conf"]))
    for it in items:
        mark = "🔴low" if it["trust"] == "low" else "  高"
        print(f"   [{mark} {it['conf']}] {it['text']}")
    s = r["summary"]
    print(f"   ── 共 {s['total']} 条: 低置信 {s['low_conf']}（低置信率 {s['low_conf_rate']}）— 全部需人工核对后才可使用")


def show_report(reports):
    """体检报告展示: 文件名[分诊] 逐条问题 + 建议怎么读"""
    for r in reports:
        badge = TRIAGE_BADGE.get(r["triage"], "❓")
        print(f"\n{badge}  {Path(r['file']).name}  ({r['category']})")
        for issue in r["issues"]:
            print(f"   • {issue}")
        # 打到 sheet 粒度的建议
        for s in r.get("sheets", []):
            mark = TRIAGE_BADGE.get(s["triage"], "")
            print(f"     sheet[{s['sheet']}] {mark} 表头行={s['header_row']}")
            for si in s["issues"][:3]:
                print(f"        - {si}")
    n = len(reports)
    counts = {"pass": 0, "fix": 0, "manual": 0}
    for r in reports:
        counts[r["triage"]] = counts.get(r["triage"], 0) + 1
    print(f"\n── 体检完毕: 共 {n} 份 → 🟢 {counts['pass']} / 🟡 {counts['fix']} / 🔴 {counts['manual']}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0)
    mode, target = sys.argv[1], Path(sys.argv[2])
    want_json = '--json' in sys.argv

    if mode == 'file':
        if not target.exists():
            print(f"文件不存在: {target}")
            sys.exit(2)
        result = check_file(target)
        (json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
         if want_json else show_report([result]))
        sys.exit(0 if result["triage"] == "pass" else 1)
    elif mode == 'ocr':
        if not target.exists():
            print(f"文件不存在: {target}")
            sys.exit(2)
        result = ocr_check(target)
        (json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
         if want_json else _show_ocr(result))
        sys.exit(0)
    elif mode == 'dir':
        results = check_dir(target)
        (json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
         if want_json else show_report(results))
        n_manual = sum(1 for r in results if r["triage"] == "manual")
        sys.exit(2 if n_manual else (1 if any(r["triage"] == "fix" for r in results) else 0))
    else:
        print(f"未知模式: {mode}")
        sys.exit(0)


if __name__ == '__main__':
    main()
