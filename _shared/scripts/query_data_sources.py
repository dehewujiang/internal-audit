#!/usr/bin/env python3
"""
query_data_sources.py — 统一数据源抽象层

将"数据从哪来"从"怎么查/怎么显示"中分离。SingleProjectSource 和 CrossProjectSource
实现相同接口，消除调用方对数据来源的感知。

[INPUT]:  findings/index.json + findings/F-*.json + evaluator JSONL + projects-index.json
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
    """读取 audit-programs/ 下的 program_index.json，返回 {steps: [...]} 结构。

    如果索引文件不存在，返回空结构（不报错——索引文件是可选的伴生文件）。
    """
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


def get_projects_index_path() -> Path:
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
        """Return list of finding dicts matching all applied filters (AND logic)."""
        index = load_index()
        if not index:
            return []

        filters = [
            ("by_risk", risk),
            ("by_status", status),
            ("by_keyword", keyword),
            ("by_origin", by_origin),
        ]

        matched_ids = None
        for idx_key, value in filters:
            if value:
                ids = set(index.get(idx_key, {}).get(value, []))
                matched_ids = ids if matched_ids is None else matched_ids & ids

        if year:
            yids = set(index.get("by_year", {}).get(str(year), {}).get("ids", []))
            matched_ids = yids if matched_ids is None else matched_ids & yids

        # No filters → all findings
        if matched_ids is None:
            matched_ids = set()
            for year_data in index.get("by_year", {}).values():
                matched_ids.update(year_data.get("ids", []))

        results = []
        for fid in sorted(matched_ids):
            finding = load_finding(fid)
            if finding:
                finding["_project"] = ""
                results.append(finding)
        return results

    def search(self, term):
        """Full-text search across all findings. Returns list of match dicts."""
        findings_dir = get_findings_dir()
        if not findings_dir.exists():
            return []

        results = []
        for fpath in sorted(findings_dir.glob("F-*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                continue

            matches = search_in_json(data, term)
            if matches:
                fid = data.get("finding_id", fpath.stem)
                title = data.get("finding_title", data.get("title", ""))
                rc = data.get("risk_classification", {})
                risk = rc.get("risk_level", data.get("risk_level", "-"))
                results.append({
                    "finding_id": fid, "title": title, "risk": risk,
                    "matches": matches, "_project": "",
                })
        return results

    def summary(self):
        """Return summary stats dict."""
        index = load_index()
        if not index:
            return None

        by_risk = index.get("by_risk", {})
        by_status = index.get("by_status", {})
        by_origin = index.get("by_origin", {})
        by_year = index.get("by_year", {})

        evals = load_evaluations(days=90)
        eval_avg = None
        if evals:
            eval_avg = sum(e.get("overall_score", 0) for e in evals) / len(evals)

        return {
            "total": index.get("total_findings", 0),
            "by_risk": {k: len(v) for k, v in by_risk.items()},
            "by_status": {k: len(v) for k, v in by_status.items() if v},
            "by_origin": {"design": len(by_origin.get("design", [])),
                          "execution": len(by_origin.get("execution", []))},
            "by_year": {y: d["count"] for y, d in sorted(by_year.items())},
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
        """Yield (project_info, finding_dict) for every finding across all projects."""
        for proj in self.projects:
            pp = Path(proj["path"])
            findings_dir = pp / "internal-audit-workspace" / "findings"
            if not findings_dir.exists():
                findings_dir = pp / "findings"
            if not findings_dir.exists():
                continue
            for fpath in sorted(findings_dir.glob("F-*.json")):
                try:
                    with open(fpath, "r", encoding="utf-8-sig") as f:
                        finding = json.load(f)
                    finding["_project"] = proj.get("topic", "")
                    yield proj, finding
                except Exception:
                    continue

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
