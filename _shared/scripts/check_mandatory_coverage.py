#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
constitution #10 mandatory 模块覆盖检查

检查 topic.json 中定义的 mandatory 模块是否在 documents/ 中有对应文档。
缺失模块标记为"制度空白"，风险等级至少为"高"，写入 signals。

用法:
    python check_mandatory_coverage.py --topic 人力资源管理
    python check_mandatory_coverage.py --topic 存货管理
"""

import sys
import json
from pathlib import Path


def find_gold_root():
    """从当前脚本位置推导金源仓库根目录"""
    return Path(__file__).resolve().parent.parent.parent


def find_workspace():
    """查找 internal-audit-workspace 目录"""
    cwd = Path.cwd()
    candidates = [
        cwd / "internal-audit-workspace",
        cwd.parent / "internal-audit-workspace",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_topic_config(gold_root, topic_name):
    """加载主题配置"""
    topic_path = gold_root / "audit-topics" / topic_name / "topic.json"
    if not topic_path.exists():
        return {"error": f"主题配置不存在: {topic_path}"}
    with open(topic_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_documents(workspace):
    """列出 documents/ 中的文件"""
    docs_dir = workspace / "documents"
    if not docs_dir.exists():
        return []
    files = []
    for f in docs_dir.iterdir():
        if f.is_file():
            files.append(f.name)
    return files


def check_coverage(topic_config, documents):
    """检查 mandatory 模块覆盖"""
    rf = topic_config.get("reference_framework")
    if not rf:
        return {
            "error": "topic.json 缺少 reference_framework 字段",
            "missing_modules": [],
            "risk": "高"
        }

    mandatory = rf.get("mandatory", [])
    if not mandatory:
        return {
            "covered": 0,
            "total": 0,
            "missing_modules": [],
            "message": "无 mandatory 模块定义，跳过检查"
        }

    doc_names_lower = [d.lower() for d in documents]
    missing = []
    covered = 0

    for module in mandatory:
        module_id = module.get("id", "")
        module_name = module.get("name", "")
        # 模糊匹配：模块 id 或 name 的任意部分出现在文档名中
        matched = False
        search_terms = [module_id.lower(), module_name.lower()]
        for term in search_terms:
            if any(term in d for d in doc_names_lower):
                matched = True
                break
        if matched:
            covered += 1
        else:
            missing.append({"id": module_id, "name": module_name, "risk": "高"})

    return {
        "covered": covered,
        "total": len(mandatory),
        "missing_modules": missing,
        "covered_modules": [m["name"] for m in mandatory if m.get("id") not in [x["id"] for x in missing]],
    }


def write_signals(workspace, missing_modules, topic_name):
    """将缺失模块写入 current-audit.json 的 signals"""
    audit_json = workspace / "current-audit.json"
    if not audit_json.exists():
        return False
    with open(audit_json, "r", encoding="utf-8-sig") as f:
        state = json.load(f)
    audit_state = state.get("audit_state", {})
    signals = audit_state.get("signals", [])
    for m in missing_modules:
        signal = {
            "source": "constitution_#10",
            "type": "制度空白",
            "module": m["name"],
            "risk": "高",
            "detail": f"审计主题'{topic_name}'缺少 mandatory 模块'{m['name']}'的制度文档",
            "timestamp": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }
        if signal not in signals:
            signals.append(signal)
    audit_state["signals"] = signals
    state["audit_state"] = audit_state
    with open(audit_json, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return True


def main():
    topic_name = None
    for i, arg in enumerate(sys.argv):
        if arg == "--topic" and i + 1 < len(sys.argv):
            topic_name = sys.argv[i + 1]
            break

    if not topic_name:
        print("用法: python check_mandatory_coverage.py --topic <主题名>")
        sys.exit(1)

    gold_root = find_gold_root()
    workspace = find_workspace()

    if not workspace:
        print(f"[MANDATORY CHECK] 未找到 internal-audit-workspace 目录")
        print(f"[MANDATORY CHECK] 在审计项目目录中运行此脚本")
        sys.exit(1)

    topic_config = load_topic_config(gold_root, topic_name)
    if "error" in topic_config:
        print(f"[MANDATORY CHECK] ❌ {topic_config['error']}")
        sys.exit(1)

    documents = list_documents(workspace)
    result = check_coverage(topic_config, documents)

    if "error" in result:
        print(f"[MANDATORY CHECK] ⚠️ {result['error']}")
        sys.exit(1)

    print(f"[MANDATORY CHECK] 审计主题: {topic_name}")
    print(f"[MANDATORY CHECK] 制度文档: {len(documents)} 个文件")
    print(f"[MANDATORY CHECK] Mandatory 模块: {result['total']} 个")
    print(f"[MANDATORY CHECK] 已覆盖: {result['covered']}/{result['total']}")

    if result["missing_modules"]:
        print(f"[MANDATORY CHECK] ❌ 制度空白 ({len(result['missing_modules'])} 个):")
        for m in result["missing_modules"]:
            print(f"[MANDATORY CHECK]   - {m['name']} ({m['id']}) 风险: {m['risk']}")
        write_signals(workspace, result["missing_modules"], topic_name)
        print(f"[MANDATORY CHECK] 已写入 {len(result['missing_modules'])} 个信号到 current-audit.json")
        sys.exit(1)
    else:
        print(f"[MANDATORY CHECK] ✅ 全部 mandatory 模块已覆盖")
        sys.exit(0)


if __name__ == "__main__":
    main()
