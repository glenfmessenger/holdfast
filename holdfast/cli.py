"""holdfast CLI: create | walk | report | eval"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="holdfast",
                                description="Remediation contracts for security fixes.")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="build a Contract from a fix commit + advisory")
    c.add_argument("--repo", required=True)
    c.add_argument("--fix", required=True, help="fix commit hash")
    c.add_argument("--advisory", required=True, help="CVE/GHSA id")
    c.add_argument("--advisory-text", help="path to advisory text; default: find release note in repo")
    c.add_argument("--test-cmd", help="how to run a targeted test (see docs); omit to skip tier 1")
    c.add_argument("--no-model", action="store_true", help="never call the model")
    c.add_argument("--model", default=None)

    w = sub.add_parser("walk", help="evaluate a contract against later commits")
    w.add_argument("--contract", required=True)
    w.add_argument("--repo", required=True)
    w.add_argument("--range", required=True, help="from..to (never walk from HEAD)")
    w.add_argument("--cap", type=int, default=40)
    w.add_argument("--no-model", action="store_true")
    w.add_argument("--model", default=None)
    w.add_argument("--only", help="comma-separated commit prefixes to evaluate (for eval pairs)")

    r = sub.add_parser("report", help="Markdown summary of all verdicts")
    r.add_argument("--out", default="results/report.md")

    e = sub.add_parser("eval", help="precision/recall vs hand labels")
    e.add_argument("--labels", required=True)
    e.add_argument("--out", default="results/eval.md")

    args = p.parse_args(argv)
    if args.cmd == "create":
        from .contract import create_command
        return create_command(args)
    if args.cmd == "walk":
        from .walk import walk_command
        return walk_command(args)
    if args.cmd == "report":
        from .report import report_command
        return report_command(args)
    if args.cmd == "eval":
        from .evaluate import eval_command
        return eval_command(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
