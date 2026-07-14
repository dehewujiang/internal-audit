#!/usr/bin/env python3
"""
queries.py — 审计数据查询工具（CLI 路由器）

瘦身为 argparse 路由 + dispatch。命令实现在 query_commands.py，
显示格式化在 query_display.py，数据访问在 query_data_sources.py。

[INPUT]:  CLI 参数
[OUTPUT]: 结构化查询结果（文本/JSON）
[POS]:    _shared/scripts 的通用查询工具，被 CLAUDE.md 注册为全局可用

用法：
    python queries.py register --path "D:\审计项目\2026-Q3" --topic 存货管理 --period 2026-Q3
    python queries.py register --list
    python queries.py register --remove P-2026-001

    python queries.py findings --risk high [--cross-project]
    python queries.py findings --keyword 废料 --year 2026 [--cross-project]
    python queries.py findings --status 待整改 [--cross-project]
    python queries.py findings --by-origin design [--cross-project]

    python queries.py trend --content-type audit_program
    python queries.py trend --days 90

    python queries.py compare --topic 存货管理 --from 2025 --to 2026 [--cross-project]

    python queries.py summary [--cross-project]

    python queries.py search "SAP 权限" [--cross-project]

    python queries.py analyses --topic 存货管理 --gaps
    python queries.py analyses --verbose

    python queries.py trace F-2026-001
    python queries.py trace A7.2
    python queries.py trace CP-HR-006

    python queries.py decide D-003
    python queries.py decide --all

    python queries.py errata
"""
import sys
import argparse

# Windows GBK 兼容：强制 stdout/stderr 使用 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from query_commands import (
    cmd_findings, cmd_trend, cmd_compare, cmd_summary,
    cmd_search, cmd_analyses, cmd_register, cmd_decide,
    cmd_trace, cmd_errata,
)


def main():
    parser = argparse.ArgumentParser(description="审计数据查询工具")
    sub = parser.add_subparsers(dest="command", required=True)

    # findings
    p_findings = sub.add_parser("findings", help="查找 finding")
    p_findings.add_argument("--risk", choices=["高", "中", "低"], help="按风险等级筛选")
    p_findings.add_argument("--status", choices=["待整改", "整改中", "已整改", "延期", "draft"], help="按状态筛选")
    p_findings.add_argument("--keyword", help="按关键词筛选")
    p_findings.add_argument("--year", type=int, help="按年度筛选")
    p_findings.add_argument("--by-origin", choices=["design", "execution"], help="按来源筛选")
    p_findings.add_argument("--cross-project", action="store_true", help="跨项目查询（需 projects-index.json）")

    # trend
    p_trend = sub.add_parser("trend", help="评估趋势")
    p_trend.add_argument("--days", type=int, default=30, help="天数范围（默认 30）")
    p_trend.add_argument("--content-type", choices=["audit_program", "finding", "audit_report",
                                                     "policy_analysis", "interview"],
                        help="按内容类型筛选")

    # compare
    p_compare = sub.add_parser("compare", help="跨年对比")
    p_compare.add_argument("--topic", default="存货管理", help="审计主题")
    p_compare.add_argument("--from-year", type=int, required=True, help="起始年度")
    p_compare.add_argument("--to-year", type=int, required=True, help="对比年度")
    p_compare.add_argument("--cross-project", action="store_true", help="跨项目对比（按主题跨项目）")

    # summary
    p_summary = sub.add_parser("summary", help="汇总统计")
    p_summary.add_argument("--cross-project", action="store_true", help="跨项目汇总")

    # search
    p_search = sub.add_parser("search", help="全文搜索 finding 正文")
    p_search.add_argument("term", help="搜索关键词")
    p_search.add_argument("--cross-project", action="store_true", help="跨项目搜索")

    # analyses
    p_analyses = sub.add_parser("analyses", help="查询制度分析结果")
    p_analyses.add_argument("--topic", help="按主题筛选")
    p_analyses.add_argument("--gaps", action="store_true", help="显示缺口详情")
    p_analyses.add_argument("--verbose", action="store_true", help="显示高风险点详情")

    # trace
    p_trace = sub.add_parser("trace", help="跨实体追溯（支持 finding/步骤/控制点 ID）")
    p_trace.add_argument("target", help="ID: finding (F-2026-001) / 步骤 (A7.2) / 控制点 (CP-001)")

    # decide
    p_decide = sub.add_parser("decide", help="查询决策追溯链")
    p_decide.add_argument("id_or_finding", nargs="?", help="决策ID (D-YYYY-NNN) 或 finding ID (F-YYYY-NNN)")
    p_decide.add_argument("--phase", help="按阶段筛选 (如 phase_3_execution)")
    p_decide.add_argument("--all", action="store_true", help="显示所有决策点")

    # register
    p_register = sub.add_parser("register", help="注册/管理审计项目")
    p_register.add_argument("--path", help="项目目录路径")
    p_register.add_argument("--id", help="项目 ID（如 P-2026-001），注册时可选，删除时必填")
    p_register.add_argument("--topic", help="审计主题（注册时填写）")
    p_register.add_argument("--period", help="审计期间（如 2026-Q3）")
    p_register.add_argument("--list", action="store_true", help="列出所有已注册项目")
    p_register.add_argument("--remove", metavar="PROJECT_ID", help="删除指定项目注册")

    # errata
    p_errata = sub.add_parser("errata", help="查询审计程序勘误记录")

    args = parser.parse_args()

    commands = {
        "findings": cmd_findings,
        "trend": cmd_trend,
        "compare": cmd_compare,
        "summary": cmd_summary,
        "search": cmd_search,
        "analyses": cmd_analyses,
        "trace": cmd_trace,
        "decide": cmd_decide,
        "register": cmd_register,
        "errata": cmd_errata,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
