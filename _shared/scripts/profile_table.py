#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
profile_table.py — Excel/CSV 画像器（勾稽 v1.0 配套）

[INPUT]:  表格文件路径（.xlsx/.xls/.csv）+ 可选 --sheet/--out
[OUTPUT]: 画像 JSON（定长统计，不含原始行）+ stdout 摘要；
          exit 0=成功 / 2=文件错误或读表失败；人话模式尾行追 SHEET 答卷
[POS]:    _shared/scripts 的确定性画像工具。产出画像供人手工核对、
          勾稽填 relations.json、探索代理只读画像三方消费；
          表头/空行/混杂列复用 data_health_check（import，不重写）

画像内容（每 sheet 一份）：表级（nrows/header_row/footer/列名/sha）
+ 列级（dtype/null_rate/n_unique/min-max/分位数approx/前5原值）。
禁令：不下语义结论、不勾稽、不写账、不进 data_executor 沙箱。

[PROTOCOL]: 变更时更新此头部，然后检查同级 CLAUDE.md
"""

import sys
import json
import argparse
import hashlib
import random
import warnings
from collections import deque
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from data_health_check import (  # noqa: E402 复用体检探头，不重写
    _find_header_row, _count_empty_rows, _mixed_type_cols)

CHUNK = 20000       # 分块行数（内存恒定）
UNIQUE_CAP = 100000  # 唯一值集合上限，超了标 capped
SAMPLE_N = 10000    # 蓄水池样本量（分位数 approx 来源）
SEED = 42           # 蓄水池定种子（同文件同结果）
FOOTER_KEYS = ("合计", "总计", "小计", "Total")


def file_sha12(path):
    """[I] 文件 sha256 前 12 位（底稿对单号用，流式读不占内存）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


def probe_head(path, sheet, ext):
    """[P] 探头：前 30 行（header=None）+ 复用体检三探针。"""
    import pandas as pd
    if ext == ".csv":
        raw = pd.read_csv(path, header=None, nrows=30, encoding="utf-8-sig")
    else:
        raw = pd.read_excel(path, sheet_name=sheet, header=None, nrows=30)
    return {
        "header_row": int(_find_header_row(raw)),
        "empty_head_rows": int(_count_empty_rows(raw)),
        "columns": [str(c) if c is not None else "" for c in raw.iloc[
            _find_header_row(raw)].tolist()] if len(raw) else [],
        "mixed_cols": [str(c) for c in _mixed_type_cols(
            raw.iloc[_find_header_row(raw):])],
    }


def iter_batches(path, sheet, ext, header_row, chunksize):
    """[B] 分块产数据行：csv 走 pandas chunksize；xlsx 走 openpyxl 只读；xls 全读一批。"""
    import pandas as pd
    if ext == ".csv":
        for ch in pd.read_csv(path, header=header_row, chunksize=chunksize,
                              encoding="utf-8-sig", dtype=str):
            yield ch
    elif ext in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb[sheet] if sheet in wb.sheetnames else wb.active
        cols = None
        batch = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i < header_row:
                continue
            if cols is None:
                cols = [str(c) if c is not None else f"列{j+1}"
                        for j, c in enumerate(row)]
                continue
            vals = list(row[:len(cols)]) + [None] * max(0, len(cols) - len(row))
            batch.append(vals)
            if len(batch) >= chunksize:
                yield pd.DataFrame(batch, columns=cols)
                batch = []
        wb.close()
        if batch:
            yield pd.DataFrame(batch, columns=cols or [])
    else:  # .xls 等：全读一批（老格式罕见，注记）
        yield pd.read_excel(path, sheet_name=sheet, header=header_row, dtype=str)


def scan_column(batches_list, col, seed):
    """[C] 单列累加：空值/唯一（封顶）/数值蓄水池/日期最值/前5原值。"""
    import pandas as pd
    n, nulls = 0, 0
    uniques = set()
    capped = False
    reservoir = []
    rng = random.Random(seed)
    seen_idx = 0
    num_min = num_max = None
    date_min = date_max = None
    samples = []
    for df in batches_list:
        if col not in df.columns:
            continue
        s = df[col]
        n += len(s)
        nulls += int(s.isna().sum())
        body = s.dropna()
        if not capped:
            for v in body.tolist():
                uniques.add(str(v))
                if len(uniques) >= UNIQUE_CAP:
                    capped = True
                    break
        nums = pd.to_numeric(body, errors="coerce").dropna()
        for v in nums.tolist():
            if num_min is None or v < num_min:
                num_min = v
            if num_max is None or v > num_max:
                num_max = v
            # 蓄水池 R 算法（定种子 → 确定性）
            if len(reservoir) < SAMPLE_N:
                reservoir.append(v)
            else:
                j = rng.randrange(seen_idx + 1)
                if j < SAMPLE_N:
                    reservoir[j] = v
            seen_idx += 1
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                dts = pd.to_datetime(body, errors="coerce").dropna()
            if len(dts):
                lo, hi = dts.min(), dts.max()
                if date_min is None or lo < date_min:
                    date_min = lo
                if date_max is None or hi > date_max:
                    date_max = hi
        except Exception:
            pass
        for v in body.tolist():
            if len(samples) < 5:
                samples.append(str(v))
            else:
                break
    out = {"null_rate": round(nulls / n, 4) if n else 0,
           "n_unique": len(uniques), "capped": capped,
           "sample": samples}
    if num_min is not None:
        import numpy as np
        q = np.quantile(reservoir, [0.25, 0.5, 0.75]).tolist()
        out["num"] = {"min": num_min, "max": num_max,
                      "p25": q[0], "p50": q[1], "p75": q[2],
                      "approx": True, "approx_n": len(reservoir)}
    if date_min is not None:
        out["date"] = {"min": str(date_min), "max": str(date_max)}
    return out


def profile_sheet(path, sheet, ext, chunksize):
    """[S] 单表画像：探头 → 分块扫描 → 成稿（key 排序保证确定性）。"""
    import pandas as pd
    probe = probe_head(path, sheet, ext)
    h = probe["header_row"]
    cols = probe["columns"]
    # 分块扫：攒 DataFrame 批次（只存引用，不复制大表）
    batches = list(iter_batches(path, sheet, ext, h, chunksize))
    nrows = sum(len(b) for b in batches)
    # 尾部 5 行扫合计关键词（只标记，不下结论）
    tail = deque(maxlen=5)
    for b in batches:
        for _, r in b.tail(5).iterrows():
            tail.append((len(tail), r.tolist()))
    footer = None
    base = nrows - len(tail)
    for k, vals in enumerate(tail):
        if any(any(key in str(c) for key in FOOTER_KEYS) for c in vals[1]):
            footer = base + k + 1  # 1-based 数据区行号
    if footer is not None:
        # 合计行不是数据：从尾部截掉 footer 及之后的行，列统计也不含它们
        drop = sum(1 for k in range(len(tail)) if base + k + 1 >= footer)
        nrows -= drop
        trimmed = []
        for b in reversed(batches):
            if drop <= 0:
                trimmed.append(b)
            elif len(b) > drop:
                trimmed.append(b.iloc[:-drop])
                drop = 0
            else:
                drop -= len(b)
        batches = [b for b in reversed(trimmed) if len(b)]
    columns = {}
    for j, c in enumerate(cols):
        if not c:
            c = f"列{j+1}"
        stat = scan_column(batches, c, SEED + j)
        # dtype：首批推断 + 混杂覆盖
        stat["dtype"] = "混杂" if c in probe["mixed_cols"] else "文本"
        for b in batches:
            if c in b.columns:
                kind = b[c].dtype.kind
                if kind in "iufc":
                    stat["dtype"] = "混杂" if c in probe["mixed_cols"] else "数值"
                elif kind == "M":
                    stat["dtype"] = "日期"
                break
        columns[c] = stat
    return {"sheet": sheet, "nrows": int(nrows), "ncols": len(columns),
            "header_row": h + 1, "footer_row": footer,
            "empty_head_rows": probe["empty_head_rows"],
            "mixed_cols": probe["mixed_cols"], "columns": columns}


def sheet_names(path, ext, sheet):
    import pandas as pd
    if ext == ".csv":
        return [None]
    if sheet:
        return [sheet]
    if ext in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True)
        names = list(wb.sheetnames)
        wb.close()
        return names
    xl = pd.ExcelFile(path)
    return list(xl.sheet_names)


def main():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure and sys.stdout.encoding != "utf-8":
        reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="表格画像器：输出定长画像 JSON")
    parser.add_argument("path", help="表格文件路径（.xlsx/.xls/.csv）")
    parser.add_argument("--sheet", default=None, help="只画一张表（默认全画）")
    parser.add_argument("--out", default=None, help="画像 JSON 落盘路径")
    parser.add_argument("--chunksize", type=int, default=CHUNK)
    args = parser.parse_args()

    p = Path(args.path)
    if not p.is_file():
        print(f"[ERROR] 文件不存在: {p}", file=sys.stderr)
        sys.exit(2)
    ext = p.suffix.lower()
    if ext not in (".xlsx", ".xls", ".xlsm", ".csv"):
        print(f"[ERROR] 不支持的格式: {ext}（只认 .xlsx/.xls/.csv）", file=sys.stderr)
        sys.exit(2)

    try:
        sheets = [s or "Sheet1" for s in sheet_names(str(p), ext, args.sheet)]
        prof = {"schema_version": "1.0", "file": str(p),
                "file_sha12": file_sha12(str(p)), "sheets": []}
        for s in sheets:
            name = None if ext == ".csv" else s
            prof["sheets"].append(profile_sheet(
                str(p), name, ext, args.chunksize))
    except Exception as e:
        print(f"[ERROR] 画像失败: {e}", file=sys.stderr)
        sys.exit(2)

    out = args.out or str(p.with_suffix("")) + ".profile.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(prof, f, ensure_ascii=False, indent=2, sort_keys=True)

    for s in prof["sheets"]:
        print(f"[OK] {s['sheet']}: {s['nrows']}行 x {s['ncols']}列 "
              f"(表头第{s['header_row']}行"
              f"{', 疑似合计行:' + str(s['footer_row']) if s['footer_row'] else ''})")
    print(f"画像 → {out}")
    print("SHEET:" + json.dumps({
        "tool": "profile-table",
        "action": "pass",
        "message": f"画像 {len(prof['sheets'])} 张表，落盘 {out}",
        "summary": {"total": len(prof["sheets"]),
                    "passed": 1, "warned": 0, "blocked": 0},
        "details": [{"check": "profile", "result": "pass",
                     "message": "; ".join(
                         f"{s['sheet']}:{s['nrows']}行x{s['ncols']}列"
                         for s in prof["sheets"])}],
        "crashed": False,
    }, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        print("SHEET:" + json.dumps({
            "tool": "profile-table",
            "action": "block",
            "message": "脚本崩溃，已转拦下",
            "summary": {"total": 0, "passed": 0, "warned": 0, "blocked": 1},
            "details": [],
            "crashed": True,
        }, ensure_ascii=False))
        traceback.print_exc()
        sys.exit(2)
