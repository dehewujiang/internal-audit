#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/data_executor.py、pandas/openpyxl（现场生成夹具）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]: tests/ 下的专项测试，锁死探索车道三项能力：
       (1) 执行后落 code.py + run.json（含源文件 sha、起止时间、状态）
       (2) Excel 多工作表可用 -d 别名=路径#工作表 指定
       (3) 真超时：死循环到点被杀，不再“设标志等跑完”
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "_shared" / "scripts"
SANDBOX = Path(tempfile.mkdtemp(prefix="explore_lane_"))

failures = []


def check(name, actual, expected):
    ok = actual == expected
    print(("  ✅ " if ok else "  ❌ ") + name)
    if not ok:
        print(f"     期望: {expected!r}\n     实际: {actual!r}")
        failures.append(name)


def run_exec(code, data, out, timeout=None, timeout_sec=20):
    cmd = [sys.executable, str(SCRIPTS / "data_executor.py"), "execute",
           "-c", code, "-d", data, "-o", str(out)]
    if timeout is not None:
        cmd += ["--timeout", str(timeout)]
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(SANDBOX),
                          timeout=timeout_sec)


def make_csv(name="t.csv"):
    p = SANDBOX / name
    p.write_text("甲,乙\n1,10\n2,20\n", encoding="utf-8")
    return p


def make_xlsx(name="两张表.xlsx"):
    import pandas as pd
    p = SANDBOX / name
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        pd.DataFrame({"第一张列": [1, 2]}).to_excel(w, sheet_name="第一张", index=False)
        pd.DataFrame({"第二张列": ["来自第二张"]}).to_excel(w, sheet_name="第二张", index=False)
    return p


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("\n[一] 执行后留痕：code.py + run.json")
    csv_path = make_csv()
    out1 = SANDBOX / "out1"
    code = "OUTPUT = dfs['t'].copy()\nOUTPUT['新列'] = 1\n"
    r = run_exec(code, f"t={csv_path}", out1)
    check("退出码（成功=0）", r.returncode, 0)
    check("result.csv 已生成", (out1 / "result.csv").is_file(), True)
    check("code.py 已生成", (out1 / "code.py").is_file(), True)
    check("code.py 内容与执行代码一致",
          (out1 / "code.py").read_text(encoding="utf-8") if (out1 / "code.py").is_file() else None,
          code)
    run_meta = {}
    if (out1 / "run.json").is_file():
        run_meta = json.loads((out1 / "run.json").read_text(encoding="utf-8"))
    check("run.json 已生成", bool(run_meta), True)
    check("run.json 状态=ok", run_meta.get("status"), "ok")
    check("run.json 记录源文件 sha256（64位）",
          len((run_meta.get("data") or [{}])[0].get("sha256", "")), 64)
    check("run.json 记录开始/结束时间",
          bool(run_meta.get("started_at")) and bool(run_meta.get("finished_at")), True)
    check("run.json 记录列数", run_meta.get("columns"), 3)
    check("run.json 记录列名", run_meta.get("column_names"), ["甲", "乙", "新列"])

    print("\n[二] 指定工作表：别名=路径#工作表")
    xlsx = make_xlsx()
    out2 = SANDBOX / "out2"
    r = run_exec("OUTPUT = dfs['t']", f"t={xlsx}#第二张", out2)
    check("退出码（成功=0）", r.returncode, 0)
    body = (out2 / "result.csv").read_text(encoding="utf-8-sig") if (out2 / "result.csv").is_file() else ""
    check("结果来自第二张表", "来自第二张" in body, True)
    check("结果不含第一张表的列", "第一张列" in body, False)
    meta2 = json.loads((out2 / "run.json").read_text(encoding="utf-8")) if (out2 / "run.json").is_file() else {}
    check("run.json 记录工作表名",
          (meta2.get("data") or [{}])[0].get("sheet"), "第二张")

    print("\n[三] 真超时：死循环到点被杀")
    out3 = SANDBOX / "out3"
    t0 = time.time()
    r = run_exec("while True:\n    pass\n", f"t={csv_path}", out3, timeout=2, timeout_sec=10)
    elapsed = time.time() - t0
    check("超时后退出码=2", r.returncode, 2)
    check("错误信息含“超时”", "超时" in r.stdout, True)
    check("2 秒超时在 10 秒内返回", elapsed < 10, True)
    meta3 = json.loads((out3 / "run.json").read_text(encoding="utf-8")) if (out3 / "run.json").is_file() else {}
    check("run.json 状态=timeout", meta3.get("status"), "timeout")

    print("\n[四] 路径本身含 #：不误当工作表")
    hash_csv = SANDBOX / "带#号.csv"
    hash_csv.write_text("甲,乙\n1,10\n", encoding="utf-8")
    out4 = SANDBOX / "out4"
    r = run_exec("OUTPUT = dfs['t']", f"t={hash_csv}", out4)
    check("退出码（成功=0）", r.returncode, 0)
    body4 = (out4 / "result.csv").read_text(encoding="utf-8-sig") if (out4 / "result.csv").is_file() else ""
    check("整条路径被正确读取", "甲" in body4, True)
    meta4 = json.loads((out4 / "run.json").read_text(encoding="utf-8")) if (out4 / "run.json").is_file() else {}
    check("run.json 工作表为空", (meta4.get("data") or [{}])[0].get("sheet"), None)

    print()
    if failures:
        print(f"FAIL — {len(failures)} 条断言未通过：")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
