#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checklist.py — 打勾纸（只看不拦，机器打勾人只看）

[INPUT]:  老项目根目录（内含 internal-audit-workspace/）
[OUTPUT]: 6个勾/叉 + 去哪补（中文），退出码永远0（纸不拦路）
[POS]:    ledger/ 的打勾纸零件，是 phase_gate.py 旧闸机的接班人；
          旧闸机"不行不让过"，这张纸"行不行都告诉你，过不过你定"。
[PROTOCOL]: 变更时更新此头部, 然后检查同级 CLAUDE.md

6句话：
  ①制度看全了吗   documents有文件且policy-analyses非空
  ②问话发出收回吗 interview-materials有问卷
  ③检查单列好吗   audit-programs有检查单
  ④证据够了吗     证据柜有槽且有填充，或问题单里有证据条（报数）
  ⑤红格看了吗     高/舞弊单子列出来，机器只能查到"有没有"，看懂没看懂待你看
  ⑥报告写完吗     reports有报告

用法:
    python ledger/checklist.py --workspace D:\某个审计项目
"""

import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def _names(d: Path, *exts: str) -> list:
    if not d.exists():
        return []
    return [f.name for f in sorted(d.iterdir())
            if f.is_file() and (not exts or f.suffix.lower() in exts)]


def _tick(ok: bool) -> str:
    return "✅" if ok else "❌"


def main() -> int:
    ap = argparse.ArgumentParser(description="打勾纸：只看不拦")
    ap.add_argument("--workspace", required=True)
    ws = Path(ap.parse_args().workspace) / "internal-audit-workspace"

    docs = _names(ws / "documents")
    analyses = _names(ws / "policy-analyses", ".json")
    print(f"①制度看全了吗 {_tick(bool(docs and analyses))} 制度{len(docs)}份/分析{len(analyses)}份" +
          ("" if docs and analyses else " → 去documents补制度，或跑看制度那步"))
    interviews = _names(ws / "interview-materials", ".xlsx")
    print(f"②问话发出收回吗 {_tick(bool(interviews))} 问卷{len(interviews)}份" +
          ("" if interviews else " → 去interview-materials看"))
    programs = _names(ws / "audit-programs", ".md")
    print(f"③检查单列好吗 {_tick(bool(programs))} 检查单{len(programs)}份" +
          ("" if programs else " → 去audit-programs看"))
    filled, total, fevd = 0, 0, 0
    for cand in (ws / "evidence" / "_evidence_catalog.json",
                 ws / "evidence" / "_evidence_catalog.json.old"):
        if cand.exists():
            try:
                cat = json.loads(cand.read_text(encoding="utf-8-sig"))
                items = cat.get("items", [])
                total = cat.get("total_slots", len(items))
                filled = sum(1 for i in items if i.get("file"))
                break
            except Exception:
                pass
    fdir = ws / "findings"
    fids = []
    if fdir.exists():
        for p in sorted(fdir.glob("F-*.json")):
            try:
                f = json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            fids.append(p.stem)
            fevd += len(f.get("evidence", []) or [])
    if total:
        print(f"④证据够了吗 {_tick(filled > 0)} 证据柜{filled}/{total}槽，问题单里{fevd}条" +
              ("" if filled else " → 去evidence补"))
    else:
        print(f"④证据够了吗 {_tick(fevd > 0)} 证据柜没启用，问题单里{fevd}条" +
              ("" if fevd else " → 去现场补证据"))
    hot = []
    if fdir.exists():
        for p in sorted(fdir.glob("F-*.json")):
            try:
                f = json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            if "舞弊" in str(f.get("category", "")) or str(f.get("risk_level", "")) == "高":
                hot.append(p.stem)
    print(f"⑤红格看了吗 ⏳待你看 高/舞弊{len(hot)}张" +
          (f"（{','.join(hot)}）" if hot else "（无）") + " → 看懂了你点头")
    reports = _names(ws / "reports", ".md", ".docx", ".pdf")
    print(f"⑥报告写完吗 {_tick(bool(reports))} 报告{len(reports)}份" +
          ("" if reports else " → 去reports看"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
