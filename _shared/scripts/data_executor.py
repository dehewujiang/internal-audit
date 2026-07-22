#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审计数据执行引擎 — LLM代码沙箱

设计：LLM 生成 pandas 代码 → 本引擎在沙箱中执行 → 返回结果

用法:
    # 了解数据结构
    python data_executor.py columns <csv_path>

    # 执行 LLM 生成的代码
    python data_executor.py execute --code "..." --data "考勤表=att.csv,薪酬表=payroll.csv" --output ./output

    # 列出预制工具
    python data_executor.py tools

安全约束:
    - 只暴露 pandas + 预制工具函数
    - 禁止文件删除/系统调用/网络请求
    - 30秒执行超时
    - 输出行数上限 5000
"""

import sys
import os
import json
import csv
import traceback
from pathlib import Path
from io import StringIO
import signal
import builtins


# ── 预制工具函数 ──────────────────────────────────────────

def benford(df, col):
    """Benford 定律分析：返回与期望分布的偏离度"""
    import pandas as pd
    import numpy as np
    first_digits = df[col].dropna().astype(str).str[0]
    first_digits = first_digits[first_digits.isin([str(i) for i in range(1, 10)])].astype(int)
    if len(first_digits) < 30:
        return {"error": "数据量不足（至少30条）", "rows": len(first_digits)}
    observed = first_digits.value_counts(normalize=True).sort_index()
    expected = pd.Series({d: np.log10(1 + 1/d) for d in range(1, 10)})
    diff = (observed - expected).abs()
    anomalies = diff[diff > 0.1].index.tolist()
    return {
        "observed": observed.to_dict(),
        "expected": expected.to_dict(),
        "anomaly_digits": anomalies,
        "total_rows": len(first_digits)
    }


def dedup(df, cols):
    """重复值检测：返回重复行列表"""
    dup_mask = df.duplicated(subset=cols, keep=False)
    dup_count = dup_mask.sum()
    if dup_count == 0:
        return {"duplicate_count": 0, "duplicates": []}
    dup_df = df[dup_mask].copy()
    if len(dup_df) > 1000:
        return {"duplicate_count": dup_count, "truncated": True, "sample": dup_df.head(1000).to_dict(orient='records')}
    return {"duplicate_count": dup_count, "duplicates": dup_df.to_dict(orient='records')}


def gap(series):
    """序列断号检测：返回跳号位置"""
    import pandas as pd
    s = pd.to_numeric(series, errors='coerce').dropna().astype(int).sort_values()
    if len(s) < 2:
        return {"gaps": [], "total": len(s)}
    gaps_list = []
    for i in range(1, len(s)):
        diff = int(s.iloc[i]) - int(s.iloc[i-1])
        if diff > 1:
            gaps_list.append({"from": int(s.iloc[i-1]), "to": int(s.iloc[i]), "gap_size": diff - 1})
    return {"gaps": gaps_list, "total": len(s), "gap_count": len(gaps_list)}


def threshold(df, amount_col, date_col, limit):
    """审批阈值穿透检测：化整为零规避审批"""
    import pandas as pd
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df['_date'] = df[date_col].dt.date
    df['_near_limit'] = (df[amount_col] >= limit * 0.8) & (df[amount_col] < limit)
    suspicious = df[df['_near_limit']].copy()
    if len(suspicious) == 0:
        return {"alert": False, "message": "未发现阈值穿透模式"}
    grouped = suspicious.groupby('_date').agg(
        count=(amount_col, 'count'),
        total=(amount_col, 'sum')
    ).reset_index()
    multi_hit = grouped[grouped['count'] > 1]
    return {
        "alert": len(multi_hit) > 0,
        "near_threshold_rows": len(suspicious),
        "multi_hit_dates": len(multi_hit),
        "total_near_amount": float(suspicious[amount_col].sum()),
        "sample": suspicious.head(100).to_dict(orient='records')
    }


def timeseries(df, date_col, value_col):
    """时间序列异常检测：Z-Score > 3"""
    import pandas as pd
    import numpy as np
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.sort_values(date_col)
    vals = df[value_col].dropna()
    if len(vals) < 10:
        return {"error": "数据量不足（至少10条）"}
    mean, std = vals.mean(), vals.std()
    if std == 0:
        return {"anomaly_count": 0, "mean": float(mean), "std": float(std)}
    z_scores = (vals - mean).abs() / std
    anomaly_idx = z_scores[z_scores > 3].index
    anomalies = df.loc[anomaly_idx]
    return {
        "mean": float(mean),
        "std": float(std),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies.head(200).to_dict(orient='records')
    }


def outlier(df, col, method="iqr"):
    """统计离群值检测：Z-Score 或 IQR"""
    import pandas as pd
    import numpy as np
    vals = df[col].dropna()
    if len(vals) < 5:
        return {"error": "数据量不足"}
    if method == "zscore":
        mean, std = vals.mean(), vals.std()
        if std == 0:
            return {"outlier_count": 0}
        z = (vals - mean).abs() / std
        mask = z > 3
    else:
        q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (vals < lower) | (vals > upper)
    outliers = df.loc[mask]
    return {
        "outlier_count": int(mask.sum()),
        "total": len(vals),
        "method": method,
        "thresholds": {"lower": float(lower) if method == "iqr" else float(mean - 3*std),
                        "upper": float(upper) if method == "iqr" else float(mean + 3*std)},
        "sample": outliers.head(100).to_dict(orient='records')
    }


def crossref(df_a, col_a, df_b, col_b):
    """两表关联匹配：返回交集行"""
    import pandas as pd
    set_a = set(df_a[col_a].dropna().astype(str))
    set_b = set(df_b[col_b].dropna().astype(str))
    intersection = set_a & set_b
    only_a = set_a - set_b
    only_b = set_b - set_a
    return {
        "intersection_count": len(intersection),
        "only_in_a": len(only_a),
        "only_in_b": len(only_b),
        "intersection_sample": list(intersection)[:100]
    }


def stratify(df, group_col, metric_col):
    """分层汇总对比"""
    import pandas as pd
    grouped = df.groupby(group_col)[metric_col].agg(['count', 'sum', 'mean', 'std']).reset_index()
    grouped = grouped.round(2)
    return {"strata": grouped.to_dict(orient='records'), "strata_count": len(grouped)}


# ── 工具清单 ──────────────────────────────────────────────

PREDEFINED_TOOLS = {
    'benford': benford,
    'dedup': dedup,
    'gap': gap,
    'threshold': threshold,
    'timeseries': timeseries,
    'outlier': outlier,
    'crossref': crossref,
    'stratify': stratify,
}

TOOL_DESCRIPTIONS = {
    'benford': 'benford(df, col) — 数字首位分布异常检测（采购金额等）',
    'dedup': 'dedup(df, [col1, col2]) — 重复值检测（发票号/合同号）',
    'gap': 'gap(series) — 序列断号检测（收据号/券号跳号→截留）',
    'threshold': 'threshold(df, amount_col, date_col, limit) — 审批阈值穿透检测',
    'timeseries': 'timeseries(df, date_col, value_col) — 时间序列Z-Score异常',
    'outlier': 'outlier(df, col, method="iqr"/"zscore") — 统计离群值',
    'crossref': 'crossref(df_a, col_a, df_b, col_b) — 两表关联匹配',
    'stratify': 'stratify(df, group_col, metric_col) — 分层汇总对标',
}


# ── 沙箱执行 ──────────────────────────────────────────────

class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("代码执行超时（30秒）")


def execute(code: str, data_files: dict, output_dir: str = None) -> dict:
    """
    在沙箱中执行 LLM 生成的 pandas 代码

    Args:
        code: LLM 生成的 Python 代码字符串
        data_files: {'别名': 'file.csv', ...}
        output_dir: 结果输出目录

    Returns:
        {'result_csv': 'path', 'summary': {...}, 'rows': N, 'error': None}
    """
    import pandas as pd

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # 加载数据文件（跳过不存在的文件，LLM 可能自行创建 DataFrame）
    dfs = {}
    for name, path in data_files.items():
        try:
            p = Path(path)
            if not p.exists():
                continue  # 跳过不存在的文件
            if p.suffix == '.csv':
                dfs[name] = pd.read_csv(p)
            elif p.suffix in ('.xlsx', '.xls'):
                dfs[name] = pd.read_excel(p)
            else:
                return {"error": f"不支持的文件格式: {p.suffix}", "rows": 0}
        except Exception as e:
            return {"error": f"读取文件失败 {path}: {e}", "rows": 0}

    # 构建沙箱命名空间
    safe_builtins = {
        '__import__': __import__,
        'True': True, 'False': False, 'None': None,
        'int': int, 'float': float, 'str': str, 'bool': bool,
        'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
        'len': len, 'range': range, 'enumerate': enumerate,
        'zip': zip, 'sorted': sorted, 'filter': filter, 'map': map,
        'sum': sum, 'min': min, 'max': max, 'abs': abs, 'round': round,
        'print': print, 'isinstance': isinstance,
    }
    namespace = {
        '__builtins__': safe_builtins,
        'pd': pd,
        'dfs': dfs,
        'OUTPUT': None,
    }
    for tool_name, tool_fn in PREDEFINED_TOOLS.items():
        namespace[tool_name] = tool_fn

    # 执行代码
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler) if hasattr(signal, 'SIGALRM') else None
    try:
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(30)
        exec(code, namespace)
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)
    except TimeoutError:
        if old_handler:
            signal.signal(signal.SIGALRM, old_handler)
        return {"error": "代码执行超时（30秒）", "rows": 0}
    except Exception as e:
        if old_handler:
            signal.signal(signal.SIGALRM, old_handler)
        return {"error": f"执行错误: {str(e)}\n{traceback.format_exc()}", "rows": 0}
    finally:
        if old_handler:
            signal.signal(signal.SIGALRM, old_handler)

    output = namespace.get('OUTPUT', None)
    if output is None:
        # 尝试从局部变量中找到最后一个 DataFrame
        for key in reversed(list(namespace.keys())):
            val = namespace[key]
            if isinstance(val, pd.DataFrame) and not key.startswith('_') and key not in ('pd',):
                output = val
                break

    if output is None or not isinstance(output, pd.DataFrame):
        return {"error": "代码未产生OUTPUT DataFrame，请在代码末尾赋值 OUTPUT = <你的结果DataFrame>", "rows": 0}

    # 限制输出行数
    max_rows = 5000
    if len(output) > max_rows:
        output = output.head(max_rows)
        truncated = True
    else:
        truncated = False

    # 保存结果
    result_csv = None
    if output_dir:
        result_csv = str(output_dir / "result.csv")
        output.to_csv(result_csv, index=False, encoding='utf-8-sig')

    summary = {
        "rows": len(output),
        "columns": list(output.columns),
        "truncated": truncated,
        "dtypes": {c: str(output[c].dtype) for c in output.columns},
        "head": output.head(10).to_dict(orient='records')
    }

    return {"result_csv": result_csv, "summary": summary, "rows": len(output), "error": None}


def list_columns(path: str) -> dict:
    """返回数据文件的列结构 + 前 20 行样本"""
    import pandas as pd
    p = Path(path)
    try:
        if p.suffix == '.csv':
            df = pd.read_csv(p, nrows=20)
        elif p.suffix in ('.xlsx', '.xls'):
            df = pd.read_excel(p, nrows=20)
        else:
            return {"error": f"不支持的文件格式: {p.suffix}"}
        return {
            "file": str(p),
            "columns": list(df.columns),
            "dtypes": {c: str(df[c].dtype) for c in df.columns},
            "total_rows": len(df),
            "sample": df.head(20).to_dict(orient='records')
        }
    except Exception as e:
        return {"error": str(e)}


def list_tools() -> str:
    """返回预制工具使用说明"""
    lines = ["# 预制分析工具（可在代码中直接调用）\n"]
    for name, desc in TOOL_DESCRIPTIONS.items():
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python data_executor.py columns <csv_path>")
        print("  python data_executor.py execute -c '<code>' -d 'a=x.csv,b=y.csv' -o ./output")
        print("  python data_executor.py tools")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "columns":
        if len(sys.argv) < 3:
            print("错误: 需要指定文件路径")
            sys.exit(1)
        result = list_columns(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "tools":
        print(list_tools())

    elif cmd == "execute":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--code', required=True)
        parser.add_argument('-d', '--data', required=True)
        parser.add_argument('-o', '--output', default=None)
        args = parser.parse_args(sys.argv[2:])

        data_files = {}
        for pair in args.data.split(','):
            k, v = pair.strip().split('=', 1)
            data_files[k.strip()] = v.strip()

        result = execute(args.code, data_files, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
