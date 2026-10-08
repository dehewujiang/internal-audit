#!/usr/bin/env python3
"""
query_data_sources.py — 统一数据源抽象层

将"数据从哪来"从"怎么查/怎么显示"中分离。SingleProjectSource 和 CrossProjectSource
实现相同接口，消除调用方对数据来源的感知。

[INPUT]:  findings/index.json + findings/F-*.json + evaluator JSONL + projects-index.json
          + program_ir.json（新程序索引，老 *_program_index.json 当备胎）
          + audit-table/*.json（桌子）+ evidence/_evidence_catalog.json（证据柜）
          + current-audit.json（状态账本）
[OUTPUT]: query_findings / search / summary / compare_years 统一返回格式
[POS]:    _shared/scripts 的数据访问层，被 queries.py CLI 入口调用
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


# ── 路径解析 ──────────────────────────────────────────

def find_workspace() -> Path:
    """从 CWD 向上查找 internal-audit-workspace/"""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        ws = parent / "internal-audit-workspace"
        if ws.exists():
            return ws
    return cwd / "internal-audit-workspace"


def get_index_path() -> Path:
    return find_workspace() / "findings" / "index.json"


def get_findings_dir() -> Path:
    return find_workspace() / "findings"


def get_eval_dir() -> Path:
    return Path.home() / ".claude" / "skills" / "internal-audit" / "data" / "evaluations"


def get_policy_analyses_dir() -> Path:
    return find_workspace() / "policy-analyses"


def get_design_assessments_dir() -> Path:
    return find_workspace() / "design-assessments"


def get_audit_programs_dir() -> Path:
    return find_workspace() / "audit-programs"


def load_program_index() -> dict:
    """读取审计程序索引，返回 {steps: [...]} 结构。

    优先读 program_ir.json（新索引，S/X/-C 全认）；没有才回退读
    audit-programs/ 下的 *_program_index.json（老索引）。都没有 → 空结构。
    """
    iw = find_workspace()
    ir_path = iw / "program_ir.json"
    if ir_path.exists():
        try:
            with open(ir_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "steps" not in data:
                data["steps"] = []
            return data
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return load_legacy_program_index()


def load_legacy_program_index() -> dict:
    """读 audit-programs/ 下的 *_program_index.json（老索引，备胎）。"""
    programs_dir = get_audit_programs_dir()
    if not programs_dir.exists():
        return {"steps": []}

    # 查找 *_program_index.json
    for fpath in sorted(programs_dir.glob("*_program_index.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 确保有 steps 字段
            if "steps" not in data:
                data["steps"] = []
            return data
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return {"steps": []}


def get_audit_tables_dir() -> Path:
    return find_workspace() / "audit-table"


def get_evidence_catalog_path() -> Path:
    return find_workspace() / "evidence" / "_evidence_catalog.json"


def get_current_audit_path() -> Path:
    return find_workspace() / "current-audit.json"


def load_audit_tables(ws=None) -> list:
    """读 audit-table/*.json，返回 [(path, table), ...]。没有 → 空。

    ws 为空时读当前工作区；跨项目查询可传入指定项目的 workspace。
    """
    ddir = (ws / "audit-table") if ws is not None else get_audit_tables_dir()
    if not ddir.exists():
        return []
    out = []
    for fpath in sorted(ddir.glob("*.json")):
        try:
            with open(fpath, "r", encoding="utf-8-sig") as f:
                out.append((fpath, json.load(f)))
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return out


def load_table_findings(ws=None) -> list:
    """从桌子的 left[] 格子里提取事实，转成 finding 兼容格式（v2.0 新模式）。"""
    results = []
    for fpath, table in load_audit_tables(ws):
        table_name = table.get("table", fpath.stem)
        for i, entry in enumerate(table.get("left", [])):
            text = entry.get("text", "").strip()
            if not text:
                continue
            src = entry.get("source", {}) or {}
            room = src.get("room", "")
            risk = "高" if entry.get("red") else "中"
            if entry.get("slot") == "说不清的信号":
                risk = "低"
            ref_ids = entry.get("ref_finding_ids") or []
            fid = ref_ids[0] if ref_ids else f"T-{fpath.stem}-{i+1}"
            results.append({
                "finding_id": fid,
                "finding_title": text[:80],
                "risk_classification": {"risk_level": risk},
                "origin": room or "桌子",
                "status": src.get("status", ""),
                "table_slot": entry.get("slot", ""),
                "table_name": table_name,
                "source_ref": src.get("ref", ""),
                "_from_table": True,
            })
    return results


def load_evidence_catalog() -> dict:
    """读 evidence/_evidence_catalog.json。没有 → 空结构。"""
    path = get_evidence_catalog_path()
    if not path.exists():
        return {"items": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"items": []}


def load_current_audit() -> dict:
    """读 current-audit.json。没有 → 空。"""
    path = get_current_audit_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def search_program_steps(term: str) -> list:
    """在程序步骤里全文搜（编号/标题/做法）。返回统一形状的匹配。"""
    index = load_program_index()
    results = []
    for step in index.get("steps", []):
        probe = {"step_id": step.get("step_id", ""), "title": step.get("title", ""),
                 "procedure": step.get("procedure", "")}
        matches = search_in_json(probe, term)
        if matches:
            results.append({
                "kind": "程序步骤",
                "finding_id": step.get("step_id", "?"),
                "title": step.get("title", "")[:50],
                "risk": step.get("track", "-"),
                "matches": matches, "_project": "",
            })
    return results


def search_tables(term: str) -> list:
    """在桌子（左边格子字 + 右边证据）里全文搜。"""
    results = []
    for fpath, table in load_audit_tables():
        probe = {"left": [x.get("text", "") for x in table.get("left", [])],
                 "right": [e.get("file", "") for e in table.get("right", [])]}
        matches = search_in_json(probe, term)
        if matches:
            results.append({
                "kind": "桌子",
                "finding_id": fpath.stem,
                "title": table.get("table", "")[:50],
                "risk": "-",
                "matches": matches, "_project": "",
            })
    return results
    """Find projects-index.json from gold source (same dir as this script's repo)"""
    script_dir = Path(__file__).resolve().parent
    gold_root = script_dir.parent.parent  # _shared/../.. = gold root
    return gold_root / "audit-topics" / "projects-index.json"


# ── 数据读取 ──────────────────────────────────────────

def load_projects_index() -> dict:
    """Load projects-index.json from gold source"""
    path = get_projects_index_path()
    if not path.exists():
        return {"projects": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"projects": []}


def save_projects_index(data: dict):
    """Save projects-index.json to gold source"""
    path = get_projects_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scan_project(path_str: str) -> dict:
    """Scan a project directory and return its stats"""
    pp = Path(path_str).resolve()
    ws = pp / "internal-audit-workspace"
    if not ws.exists():
        ws = pp
        if not (ws / "current-audit.json").exists():
            ws = pp.parent / "internal-audit-workspace"

    info = {"path": str(pp), "findings_count": 0, "topic": "", "period": "", "phase": "unknown"}

    audit_json = ws / "current-audit.json"
    if audit_json.exists():
        try:
            with open(audit_json, "r", encoding="utf-8-sig") as f:
                audit = json.load(f)
            info["topic"] = audit.get("audit_topic", "")
            info["phase"] = audit.get("status", "unknown")
            state = audit.get("audit_state", {})
            info["period"] = state.get("audit_period", audit.get("updated_at", ""))
        except Exception:
            pass

    findings_dir = ws / "findings"
    if findings_dir.exists():
        fj = [f for f in findings_dir.glob("F-*.json")]
        info["findings_count"] = len(fj)

    return info


def load_index() -> dict:
    """读取 findings/index.json"""
    path = get_index_path()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_finding(finding_id: str) -> dict:
    """读取单个 finding JSON"""
    base = get_findings_dir()
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".json") and f != "index.json":
                if finding_id in f:
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fh:
                        return json.load(fh)
    return {}


def load_evaluations(days: int = 30, content_type: str = None) -> list:
    """从 JSONL 历史加载评估记录"""
    eval_dir = get_eval_dir()
    if not eval_dir.exists():
        return []

    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    current = start_date
    while current <= end_date:
        file_path = eval_dir / (current.strftime("%Y-%m-%d") + ".jsonl")
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if content_type and record.get("content_type") != content_type:
                            continue
                        results.append(record)
                    except json.JSONDecodeError:
                        continue
        current += timedelta(days=1)

    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results


# ── 全文搜索工具 ────────────────────────────────────────

def search_in_json(obj, term, path=""):
    """递归搜索 JSON 对象中所有包含 term 的字符串字段，返回 [(field_path, context)]"""
    matches = []
    if isinstance(obj, str):
        if term in obj:
            idx = obj.index(term)
            start = max(0, idx - 30)
            end = min(len(obj), idx + len(term) + 30)
            context = obj[start:end]
            if start > 0:
                context = "..." + context
            if end < len(obj):
                context = context + "..."
            matches.append((path, context))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            matches.extend(search_in_json(v, term, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            matches.extend(search_in_json(v, term, f"{path}[{i}]"))
    return matches


# ── 相似度检测 ─────────────────────────────────────────

def detect_similar_findings(from_findings, to_findings):
    """Detect potentially repeated findings by title character overlap."""
    repeated = []
    for f1 in from_findings:
        t1 = f1.get("finding_title", "")
        words1 = set(t1.replace("，", "").replace(" ", ""))
        for f2 in to_findings:
            t2 = f2.get("finding_title", "")
            words2 = set(t2.replace("，", "").replace(" ", ""))
            if words1 and words2 and len(words1 & words2) / max(len(words1 | words2), 1) > 0.3:
                repeated.append((
                    f1.get("finding_id", ""), f2.get("finding_id", ""),
                    t1[:30], t2[:30],
                ))
    return repeated


# ── 数据源实现 ─────────────────────────────────────────

class SingleProjectSource:
    """单项目数据源 — 使用当前工作区的 index.json 快速索引"""

    def __init__(self):
        self._ws = find_workspace()

    @property
    def name(self):
        return "单项目"

    @property
    def is_cross_project(self):
        return False

    def query_findings(self, risk=None, status=None, keyword=None, year=None, by_origin=None):
        """Return list of finding dicts matching all applied filters (AND logic).

        只认桌子（audit-table/left[]）。旧格式 findings/F-*.json 已停写，
        不再读（2026-10 关双轨；老项目冻结归档，不迁移）。
        """
        results = []

        # 桌子是唯一来源：从 left[] 读
        for tf in load_table_findings():
            if risk and tf.get("risk_classification", {}).get("risk_level") != risk:
                continue
            if status and tf.get("status") != status:
                continue
            if keyword and keyword not in json.dumps(tf, ensure_ascii=False):
                continue
            if by_origin and tf.get("origin") != by_origin:
                continue
            tf["_project"] = ""
            results.append(tf)

        return results

    def search(self, term):
        """Full-text search across all findings. Returns list of match dicts.

        只搜桌子（audit-table/left[]）。旧格式 findings/F-*.json 已停写，不再搜。
        """
        results = []

        # 桌子是唯一来源：搜 left[]
        for tf in load_table_findings():
            matches = search_in_json(tf, term)
            if matches:
                results.append({
                    "finding_id": tf.get("finding_id", ""),
                    "title": tf.get("finding_title", ""),
                    "risk": tf.get("risk_classification", {}).get("risk_level", "-"),
                    "matches": matches, "_project": "",
                })

        return results

    def summary(self):
        """Return summary stats dict.

        只从桌子统计（audit-table/left[]）。形状与旧版一致（total/by_risk/
        by_status/by_origin/by_year），by_year 恒为空——桌子行不带年份
        （跨年对比待新账积累后定，见 2026-10-08 重设计稿 §6）。
        """
        rows = load_table_findings()

        by_risk = {"高": 0, "中": 0, "低": 0}
        by_status = {}
        by_origin = {"design": 0, "execution": 0}
        for tf in rows:
            risk = (tf.get("risk_classification") or {}).get("risk_level", "-")
            if risk in by_risk:
                by_risk[risk] += 1
            st = tf.get("status") or ""
            if st:
                by_status[st] = by_status.get(st, 0) + 1
            room = tf.get("origin") or ""
            if room == "看制度":
                by_origin["design"] += 1
            elif room == "执行取证":
                by_origin["execution"] += 1

        evals = load_evaluations(days=90)
        eval_avg = None
        if evals:
            eval_avg = sum(e.get("overall_score", 0) for e in evals) / len(evals)

        return {
            "total": len(rows),
            "by_risk": by_risk,
            "by_status": by_status,
            "by_origin": by_origin,
            "by_year": {},
            "eval_count": len(evals),
            "eval_avg": eval_avg,
        }

    def compare_years(self, topic, from_year, to_year):
        """Return comparison data between two years."""
        index = load_index()
        if not index:
            return None

        from_year = str(from_year)
        to_year = str(to_year)

        from_data = index.get("by_year", {}).get(from_year, {})
        to_data = index.get("by_year", {}).get(to_year, {})

        from_ids = set(from_data.get("ids", []))
        to_ids = set(to_data.get("ids", []))

        from_findings = [load_finding(fid) for fid in from_ids]
        from_findings = [f for f in from_findings if f]
        to_findings = [load_finding(fid) for fid in to_ids]
        to_findings = [f for f in to_findings if f]

        repeated = detect_similar_findings(from_findings, to_findings)

        repeated_to_ids = {r[1] for r in repeated}
        new_ids = to_ids - from_ids - repeated_to_ids
        truly_new = []
        for fid in sorted(new_ids):
            f = load_finding(fid)
            if f:
                rc = f.get("risk_classification", {})
                risk = rc.get("risk_level", f.get("risk_level", "-"))
                title = f.get("finding_title", f.get("title", ""))[:50]
                truly_new.append((fid, title, risk))

        return {
            "from_count": len(from_ids),
            "to_count": len(to_ids),
            "repeated": repeated,
            "new": truly_new,
        }


def _project_workspace(pp: Path):
    """按 scan_project 同口径解析指定项目的工作区目录；找不到返回 None。"""
    ws = pp / "internal-audit-workspace"
    if not ws.exists():
        ws = pp
        if not (ws / "current-audit.json").exists():
            ws = pp.parent / "internal-audit-workspace"
    if not ws.exists():
        return None
    return ws


class CrossProjectSource:
    """跨项目数据源 — 遍历所有已注册项目的 findings"""

    def __init__(self, projects: list):
        self.projects = [p for p in projects if Path(p.get("path", "")).exists()]

    @property
    def name(self):
        return f"跨项目查询（{len(self.projects)} 个项目）"

    @property
    def is_cross_project(self):
        return True

    def _iter_all(self):
        """Yield (project_info, finding_dict) for every finding across all projects.

        桌子行与旧格式 F-*.json 都吐（老项目冻结但查询不断它们的路；
        新项目只有桌子行）。桌子行带 ``_from_table=True`` 标记。
        """
        for proj in self.projects:
            pp = Path(proj["path"])
            findings_dir = pp / "internal-audit-workspace" / "findings"
            if not findings_dir.exists():
                findings_dir = pp / "findings"
            if findings_dir.exists():
                for fpath in sorted(findings_dir.glob("F-*.json")):
                    try:
                        with open(fpath, "r", encoding="utf-8-sig") as f:
                            finding = json.load(f)
                        finding["_project"] = proj.get("topic", "")
                        yield proj, finding
                    except Exception:
                        continue
            ws = _project_workspace(pp)
            if ws is not None:
                for tf in load_table_findings(ws):
                    tf["_project"] = proj.get("topic", "")
                    yield proj, tf

    def _load_keyword_ids(self, keyword):
        """Load finding IDs matching keyword from all projects' index.json files."""
        kw_ids = set()
        for proj in self.projects:
            pp = Path(proj["path"])
            idx_path = pp / "internal-audit-workspace" / "findings" / "index.json"
            if not idx_path.exists():
                idx_path = pp / "findings" / "index.json"
            if idx_path.exists():
                try:
                    with open(idx_path, "r", encoding="utf-8") as f:
                        pidx = json.load(f)
                    kw_ids.update(pidx.get("by_keyword", {}).get(keyword, []))
                except Exception:
                    pass
        return kw_ids

    def query_findings(self, risk=None, status=None, keyword=None, year=None, by_origin=None):
        """Return list of finding dicts matching all applied filters."""
        risk_label = {"高": "高", "中": "中", "低": "低"}
        status_map = {"待整改": "待整改", "整改中": "整改中", "已整改": "已整改", "延期": "延期"}

        kw_ids = None
        if keyword:
            kw_ids = self._load_keyword_ids(keyword)

        results = []
        for proj, finding in self._iter_all():
            fid = finding.get("finding_id", "")
            rc = finding.get("risk_classification", {})
            frisk = rc.get("risk_level", finding.get("risk_level", "-"))
            fstatus = finding.get("finding_metadata", {}).get("status", finding.get("status", "-"))
            forigin = finding.get("finding_metadata", {}).get("origin", finding.get("origin", "-"))
            fyear = fid.split("-")[1] if fid.startswith("F-") and "-" in fid else ""

            if risk and risk_label.get(risk) != frisk:
                continue
            if status and status_map.get(status, status) != fstatus:
                continue
            if year and fyear != str(year):
                continue
            if by_origin and forigin != by_origin:
                continue
            if kw_ids is not None and fid not in kw_ids:
                if finding.get("_from_table"):
                    # 桌子行从不进 index：关键词直查文本，查不到才跳过
                    if keyword not in json.dumps(finding, ensure_ascii=False):
                        continue
                else:
                    continue

            results.append(finding)

        return results

    def search(self, term):
        """Full-text search across all projects. Returns list of match dicts."""
        all_matches = []
        for proj, finding in self._iter_all():
            matches = search_in_json(finding, term)
            if matches:
                fid = finding.get("finding_id", "")
                title = finding.get("finding_title", finding.get("title", ""))
                rc = finding.get("risk_classification", {})
                risk = rc.get("risk_level", finding.get("risk_level", "-"))
                all_matches.append({
                    "finding_id": fid, "title": title, "risk": risk,
                    "matches": matches, "_project": proj.get("topic", ""),
                })
        return all_matches

    def summary(self):
        """Aggregate stats across all registered projects."""
        risk_counts = {"高": 0, "中": 0, "低": 0}
        status_counts = defaultdict(int)
        by_topic = defaultdict(lambda: {"count": 0, "high": 0})
        total_findings = 0

        for proj, finding in self._iter_all():
            total_findings += 1
            rc = finding.get("risk_classification", {})
            risk = rc.get("risk_level", finding.get("risk_level", "-"))
            status = finding.get("finding_metadata", {}).get("status", finding.get("status", "-"))
            if risk in risk_counts:
                risk_counts[risk] += 1
            status_counts[status] += 1
            topic = proj.get("topic", "未分类")
            by_topic[topic]["count"] += 1
            if risk == "高":
                by_topic[topic]["high"] += 1

        return {
            "total": total_findings,
            "risk_counts": risk_counts,
            "status_counts": dict(status_counts),
            "by_topic": dict(by_topic),
        }

    def compare_years(self, topic, from_year, to_year):
        """Cross-project year-over-year comparison by topic."""
        from_year = str(from_year)
        to_year = str(to_year)

        from_findings = []
        to_findings = []

        for proj, finding in self._iter_all():
            ptopic = proj.get("topic", "")
            if topic and topic not in ptopic:
                continue
            fid = finding.get("finding_id", "")
            fyear = fid.split("-")[1] if fid.startswith("F-") and "-" in fid else ""
            if fyear == from_year:
                from_findings.append(finding)
            elif fyear == to_year:
                to_findings.append(finding)

        repeated = detect_similar_findings(from_findings, to_findings)

        # Identify truly new findings in to_year
        all_from_titles = {f.get("finding_title", "") for f in from_findings}
        truly_new = []
        for f2 in to_findings:
            t2 = f2.get("finding_title", "")
            is_new = True
            for t1 in all_from_titles:
                words1 = set(t1.replace("，", "").replace(" ", ""))
                words2 = set(t2.replace("，", "").replace(" ", ""))
                if words1 and words2 and len(words1 & words2) / max(len(words1 | words2), 1) > 0.3:
                    is_new = False
                    break
            if is_new:
                rc = f2.get("risk_classification", {})
                risk = rc.get("risk_level", f2.get("risk_level", "-"))
                truly_new.append((f2.get("finding_id", ""), t2[:50], risk))

        return {
            "from_count": len(from_findings),
            "to_count": len(to_findings),
            "repeated": repeated,
            "new": truly_new,
        }


# ── 工厂函数 ──────────────────────────────────────────

def create_data_source(args):
    """根据 CLI 参数返回对应的数据源实例。

    这是整个抽象层的唯一入口——cmd_* 函数不需要知道数据来自单项目还是跨项目。
    """
    if getattr(args, "cross_project", False):
        idx = load_projects_index()
        return CrossProjectSource(idx.get("projects", []))
    return SingleProjectSource()
