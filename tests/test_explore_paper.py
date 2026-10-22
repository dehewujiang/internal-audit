#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[INPUT]: 依赖 _shared/scripts/explore_paper.py（本批次新增）
[OUTPUT]: 断言式测试输出（✅/❌）+ 汇总；exit 0=全过 / 1=有失败
[POS]: tests/ 下的专项测试，锁死探索底稿两件事：
       (1) new 生成含源文件 sha256 的 底稿.md + 底稿.json 骨架
       (2) check 对“事实无依据文件 / 线索无下一步证据”拦截 exit 2，合格放行
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md
"""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "_shared" / "scripts"
SANDBOX = Path(tempfile.mkdtemp(prefix="explore_paper_"))

failures = []


def check(name, actual, expected):
    ok = actual == expected
    print(("  ✅ " if ok else "  ❌ ") + name)
    if not ok:
        print(f"     期望: {expected!r}\n     实际: {actual!r}")
        failures.append(name)


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPTS / "explore_paper.py")] + [str(a) for a in args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(SANDBOX))


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def valid_paper(directory):
    (directory / "result").mkdir(parents=True, exist_ok=True)
    (directory / "result" / "facts.csv").write_text("项,值\nA,1\n", encoding="utf-8")
    (directory / "底稿.md").write_text("# 测试底稿\n", encoding="utf-8")
    return {
        "schema_version": "0.1-prototype",
        "working_paper_id": "EWP-2026-999",
        "title": "测试底稿",
        "status": "draft",
        "sources": [{"file": "源表.xlsx", "sha256": "a" * 64, "grade": "A"}],
        "facts": [{"id": "F-01", "statement": "测试事实", "basis": ["result/facts.csv"]}],
        "leads": [{"id": "L-01", "title": "测试线索", "basis": ["F-01"],
                   "evidence_needed": ["原始工单"], "status": "待查"}],
        "conclusion": {"audit_conclusion": False}
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    src = SANDBOX / "源表.xlsx"
    src.write_bytes(b"fake-xlsx-bytes")
    expected_sha = hashlib.sha256(src.read_bytes()).hexdigest()

    print("\n[一] new：生成骨架并记录 sha256")
    out = SANDBOX / "wp_new"
    r = run("new", "--id", "EWP-2026-999", "--title", "测试底稿",
            "--source", str(src), "--out", str(out))
    check("退出码（成功=0）", r.returncode, 0)
    check("底稿.md 已生成", (out / "底稿.md").is_file(), True)
    check("底稿.json 已生成", (out / "底稿.json").is_file(), True)
    data = json.loads((out / "底稿.json").read_text(encoding="utf-8")) if (out / "底稿.json").is_file() else {}
    check("源文件 sha256 一致", (data.get("sources") or [{}])[0].get("sha256"), expected_sha)
    check("编号写入正确", data.get("working_paper_id"), "EWP-2026-999")
    check("facts/leads 初始为空",
          (data.get("facts"), data.get("leads")), ([], []))
    r2 = run("new", "--id", "EWP-2026-999", "--title", "重复", "--source", str(src), "--out", str(out))
    check("重复建同一目录被拒（exit 2）", r2.returncode, 2)

    print("\n[二] check：事实缺依据 → 拦下")
    bad = SANDBOX / "wp_bad"
    bad.mkdir()
    paper = valid_paper(bad)
    paper["facts"][0]["basis"] = []
    write_json(bad / "底稿.json", paper)
    r = run("check", str(bad))
    check("退出码=2", r.returncode, 2)
    check("提示缺依据", "依据" in r.stdout, True)

    print("\n[三] check：依据文件不存在 → 拦下")
    missing = SANDBOX / "wp_missing"
    missing.mkdir()
    paper = valid_paper(missing)
    paper["facts"][0]["basis"] = ["result/不存在.csv"]
    write_json(missing / "底稿.json", paper)
    r = run("check", str(missing))
    check("退出码=2", r.returncode, 2)
    check("提示文件不存在", "不存在" in r.stdout, True)

    print("\n[四] check：线索缺下一步证据 → 拦下")
    nolead = SANDBOX / "wp_nolead"
    nolead.mkdir()
    paper = valid_paper(nolead)
    paper["leads"][0]["evidence_needed"] = []
    write_json(nolead / "底稿.json", paper)
    r = run("check", str(nolead))
    check("退出码=2", r.returncode, 2)
    check("提示缺下一步证据", "证据" in r.stdout, True)

    print("\n[五] check：合格底稿 → 放行")
    good = SANDBOX / "wp_good"
    good.mkdir()
    write_json(good / "底稿.json", valid_paper(good))
    r = run("check", str(good))
    check("退出码=0", r.returncode, 0)
    check("输出 action=pass", "action=pass" in r.stdout, True)

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
