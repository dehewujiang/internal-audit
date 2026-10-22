#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审计数据执行引擎 — LLM代码沙箱

[INPUT]:  execute: 代码字符串 + 数据文件（别名=路径[#工作表]）+ 输出目录 + timeout
          columns: 数据文件路径[#工作表]
[OUTPUT]: execute: result.csv + code.py + run.json；stdout JSON；exit 0=成功 / 2=出错
          columns: JSON（列名/类型/样例）
[POS]:    _shared/scripts 的沙箱执行引擎，供 audit-execution-assistant 数据预处理调用；
          探索车道的执行层，产物由 explore_paper.py 组织成底稿
[PROTOCOL]: 变更时更新此头部，然后检查同级 CLAUDE.md
拆分候选：本文件已超 300 行，下次改动前评估把“预制工具”与“沙箱执行”分文件。

设计：LLM 生成 pandas 代码 → 本引擎在沙箱中执行 → 返回结果

用法:
    # 了解数据结构
    python data_executor.py columns <path>[#sheet]

    # 执行 LLM 生成的代码（执行后落 code.py + run.json）
    python data_executor.py execute --code "..." --data "考勤表=att.csv,薪酬表=payroll.xlsx#Sheet2" --output ./output [--timeout 30]

    注：路径本身含 # 时，若整条路径是已存在的文件，按整条路径处理，不当作工作表分隔符。

    # 列出预制工具
    python data_executor.py tools

安全约束:
    - 只暴露 pandas + 预制工具函数
    - 禁止文件删除/系统调用/网络请求
    - 默认30秒执行超时（子进程到点被杀，不再只是设标志）
    - 输出行数上限 5000
    - 每次执行留痕：code.py（代码原文）+ run.json（源文件 sha/起止/状态/行列数）
"""

import sys
import os
import json
import csv
import hashlib
import subprocess
import tempfile
import time
import traceback
from datetime import datetime
from pathlib import Path
import builtins


DEFAULT_TIMEOUT = 30.0
MAX_ROWS = 5000


# ── 数据参数与留痕 ────────────────────────────────────────

def split_data_spec(value: str):
    """'path#sheet' -> (path, sheet)；不带 # 时 sheet=None。

    路径本身含 # 时：若整条字符串是一个存在的文件，按整条路径处理；
    否则按最后一个 # 切分（# 后为工作表名）。
    """
    if Path(value).is_file():
        return value, None
    path, sep, sheet = value.rpartition('#')
    if not sep:
        return value, None
    return path, (sheet or None)


def parse_data_pair(pair: str):
    """'alias=path#sheet' -> (alias, path, sheet)。"""
    if '=' not in pair:
        raise ValueError(f"数据参数须为 别名=路径[#工作表]: {pair}")
    alias, value = pair.split('=', 1)
    path, sheet = split_data_spec(value.strip())
    return alias.strip(), path.strip(), sheet


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def normalize_data_files(data_files: dict) -> dict:
    """兼容 {'别名': 'path'} 与 {'别名': {'path': ..., 'sheet': ...}} 两种写法。"""
    out = {}
    for alias, val in data_files.items():
        if isinstance(val, dict):
            out[alias] = {'path': str(val.get('path')), 'sheet': val.get('sheet')}
        else:
            path, sheet = split_data_spec(str(val))
            out[alias] = {'path': path, 'sheet': sheet}
    return out


def _now():
    return datetime.now().isoformat(timespec='seconds')


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

def _safe_import(name, *args, **kwargs):
    """白名单 import：只允许 pandas/numpy 及标准科学库"""
    allowed = {'pandas', 'numpy', 'math', 'datetime', 'collections', 'itertools', 'json', 'csv', 're', 'functools'}
    top_level = name.split('.')[0]
    if top_level not in allowed:
        raise ImportError(f"安全沙箱禁止导入模块: {name}")
    return __import__(name, *args, **kwargs)


class TimeoutError(Exception):
    pass


def execute(code: str, data_files: dict, output_dir: str = None,
            timeout: float = DEFAULT_TIMEOUT) -> dict:
    """在子进程中执行沙箱代码，并落 code.py + run.json。

    Args:
        code: LLM 生成的 Python 代码字符串
        data_files: {'别名': 'path'} 或 {'别名': 'path#工作表'}
        output_dir: 结果输出目录
        timeout: 秒；到点杀子进程

    Returns:
        {'result_csv': 'path', 'summary': {...}, 'rows': N, 'error': None}
    """
    data = normalize_data_files(data_files)

    out_path = Path(output_dir) if output_dir else None
    if out_path:
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / 'code.py').write_text(code, encoding='utf-8')

    data_meta = []
    for alias, spec in data.items():
        p = Path(spec['path'])
        meta = {'alias': alias, 'path': str(p), 'sheet': spec.get('sheet'),
                'exists': p.is_file()}
        if p.is_file():
            meta['size_bytes'] = p.stat().st_size
            meta['sha256'] = sha256_file(p)
        data_meta.append(meta)

    started_at = _now()
    t0 = time.time()
    status = 'error'
    result = {'error': '未知错误', 'rows': 0}

    with tempfile.TemporaryDirectory(prefix='data_executor_') as tmp:
        tmp = Path(tmp)
        job_path = tmp / 'job.json'
        result_path = tmp / 'result.json'
        job = {
            'code': code,
            'data_files': data,
            'output_dir': str(out_path) if out_path else None,
            'max_rows': MAX_ROWS,
        }
        job_path.write_text(json.dumps(job, ensure_ascii=False), encoding='utf-8')
        cmd = [sys.executable, str(Path(__file__).resolve()), '_worker',
               str(job_path), str(result_path)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  encoding='utf-8', errors='replace',
                                  timeout=timeout)
        except subprocess.TimeoutExpired:
            status = 'timeout'
            result = {'error': f'代码执行超时（{timeout:g}秒）', 'rows': 0}
        else:
            if result_path.is_file():
                try:
                    result = json.loads(result_path.read_text(encoding='utf-8'))
                except Exception as e:
                    result = {'error': f'结果读取失败: {e}', 'rows': 0}
            else:
                detail = (proc.stderr or proc.stdout or '').strip()
                result = {'error': f'执行进程异常退出（code={proc.returncode}）: {detail[:2000]}',
                          'rows': 0}
            status = 'ok' if result.get('error') is None else 'error'

    finished_at = _now()
    duration = round(time.time() - t0, 3)

    if out_path:
        summary = result.get('summary') or {}
        run_meta = {
            'tool': 'data-executor',
            'schema_version': '1.0',
            'status': status,
            'started_at': started_at,
            'finished_at': finished_at,
            'duration_sec': duration,
            'timeout_sec': timeout,
            'code_file': 'code.py',
            'code_sha256': hashlib.sha256(code.encode('utf-8')).hexdigest(),
            'data': data_meta,
            'rows': result.get('rows', 0),
            'columns': len(summary.get('columns') or []),
            'column_names': summary.get('columns') or [],
            'result_csv': result.get('result_csv'),
            'error': result.get('error'),
        }
        (out_path / 'run.json').write_text(
            json.dumps(run_meta, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8')

    return result


def _execute_local(code: str, data_files: dict, output_dir: str = None,
                   max_rows: int = MAX_ROWS) -> dict:
    """子进程内实际执行：加载数据 → 沙箱 exec → 写 result.csv。

    data_files 必须是 normalize_data_files 之后的 {'别名': {'path','sheet'}}。
    """
    import pandas as pd

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # 加载数据文件（跳过不存在的文件，LLM 可能自行创建 DataFrame）
    dfs = {}
    for name, spec in data_files.items():
        try:
            p = Path(spec['path'])
            if not p.exists():
                continue
            sheet = spec.get('sheet')
            if p.suffix == '.csv':
                dfs[name] = pd.read_csv(p)
            elif p.suffix in ('.xlsx', '.xls'):
                dfs[name] = pd.read_excel(p, sheet_name=sheet) if sheet else pd.read_excel(p)
            else:
                return {"error": f"不支持的文件格式: {p.suffix}", "rows": 0}
        except Exception as e:
            return {"error": f"读取文件失败 {spec.get('path')}: {e}", "rows": 0}

    # 构建沙箱命名空间
    safe_builtins = {
        '__import__': _safe_import,
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

    try:
        exec(code, namespace)
    except Exception as e:
        return {"error": f"执行错误: {str(e)}\n{traceback.format_exc()}", "rows": 0}

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


def _worker_main(job_path: str, result_path: str) -> int:
    """子进程入口：读 job.json → 本地执行 → 写 result.json。"""
    job = json.loads(Path(job_path).read_text(encoding='utf-8'))
    try:
        result = _execute_local(job['code'], job['data_files'],
                                job.get('output_dir'), job.get('max_rows', MAX_ROWS))
    except Exception as e:
        result = {'error': f'执行错误: {e}\n{traceback.format_exc()}', 'rows': 0}
    Path(result_path).write_text(
        json.dumps(result, ensure_ascii=False, default=str), encoding='utf-8')
    return 0 if result.get('error') is None else 2


def list_columns(path: str) -> dict:
    """返回数据文件的列结构 + 前 20 行样本；支持 path#sheet。"""
    import pandas as pd
    path, sheet = split_data_spec(path)
    p = Path(path)
    try:
        if p.suffix == '.csv':
            df = pd.read_csv(p, nrows=20)
        elif p.suffix in ('.xlsx', '.xls'):
            df = pd.read_excel(p, sheet_name=sheet, nrows=20) if sheet else pd.read_excel(p, nrows=20)
        else:
            return {"error": f"不支持的文件格式: {p.suffix}"}
        return {
            "file": str(p),
            "sheet": sheet,
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
    # 统一 UTF-8 输出，避免 Windows 控制台把中文错误信息变成乱码
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure and sys.stdout.encoding != "utf-8":
        reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        print("用法:")
        print("  python data_executor.py columns <path>[#sheet]")
        print("  python data_executor.py execute -c '<code>' -d 'a=x.csv,b=y.xlsx#Sheet2' -o ./output [--timeout 30]")
        print("  python data_executor.py tools")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "_worker":
        if len(sys.argv) < 4:
            print("内部命令，勿直接调用")
            sys.exit(2)
        sys.exit(_worker_main(sys.argv[2], sys.argv[3]))

    if cmd == "columns":
        if len(sys.argv) < 3:
            print("错误: 需要指定文件路径")
            sys.exit(1)
        result = list_columns(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    elif cmd == "tools":
        print(list_tools())

    elif cmd == "execute":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--code', required=True)
        parser.add_argument('-d', '--data', required=True)
        parser.add_argument('-o', '--output', default=None)
        parser.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT,
                            help=f'执行超时秒数（默认 {DEFAULT_TIMEOUT:g}）')
        args = parser.parse_args(sys.argv[2:])

        data_files = {}
        for pair in args.data.split(','):
            if not pair.strip():
                continue
            alias, path, sheet = parse_data_pair(pair)
            data_files[alias] = {'path': path, 'sheet': sheet}

        result = execute(args.code, data_files, args.output, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        sys.exit(0 if result.get('error') is None else 2)

    else:
        print(f"未知命令: {cmd}")
        sys.exit(2)


if __name__ == "__main__":
    main()
