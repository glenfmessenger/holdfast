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
    c.add_argument("--no-tests", action="store_true", help="skip tier-1 execution")
    c.add_argument("--model", default=None)

    w = sub.add_parser("walk", help="evaluate a contract against later commits")
    w.add_argument("--contract", required=True)
    w.add_argument("--repo", required=True)
    w.add_argument("--range", required=True, help="from..to (never walk from HEAD)")
    w.add_argument("--cap", type=int, default=40)
    w.add_argument("--no-model", action="store_true")
    w.add_argument("--model", default=None)
    w.add_argument("--only", help="comma-separated commit prefixes to evaluate (for eval pairs)")
    w.add_argument("--include", help="comma-separated commit prefixes that sampling must keep (labelled commits)")
    w.add_argument("--no-tests", action="store_true", help="skip tier-1 execution")

    r = sub.add_parser("report", help="Markdown summary of all verdicts")
    r.add_argument("--out", default="results/report.md")

    e = sub.add_parser("eval", help="precision/recall vs hand labels")
    e.add_argument("--labels", required=True)
    e.add_argument("--out", default="results/eval.md")

    k = sub.add_parser("complete", help="value-flow completeness check at the fix commit")
    k.add_argument("--contract", required=True)
    k.add_argument("--repo", required=True)
    k.add_argument("--no-model", action="store_true")
    k.add_argument("--model", default=None)
    k.add_argument("--cap", type=int, default=None, help="override the tier-4 call cap for this run (recorded in the call log)")

    i = sub.add_parser("integrate", help="run Holdfast on one Claude Security finding (report dir + F<n>)")
    i.add_argument("--report", required=True, help="CLAUDE-SECURITY-<ts> directory")
    i.add_argument("--finding", required=True, help="finding id, e.g. F1")
    i.add_argument("--repo", help="repository the report belongs to (default: parent of --report)")
    i.add_argument("--no-model", action="store_true")
    i.add_argument("--model", default=None)
    i.add_argument("--cap", type=int, default=None, help="override the tier-4 call cap for this run (recorded in the call log)")

    cl = sub.add_parser("close", help="integrate, then close the finding as a PR on the fork")
    cl.add_argument("--report", required=True)
    cl.add_argument("--finding", required=True)
    cl.add_argument("--repo")
    cl.add_argument("--remote", default="fork", help="git remote of the fork to push to and open the PR on")
    cl.add_argument("--no-model", action="store_true")
    cl.add_argument("--model", default=None)
    cl.add_argument("--cap", type=int, default=None, help="override the tier-4 call cap for this run (recorded in the call log)")

    args = p.parse_args(argv)
    if args.cmd == "create":
        from .contract import create_command
        return create_command(args)
    if args.cmd == "walk":
        from .walk import walk_command
        return walk_command(args)
    if args.cmd == "close":
        from .close import close_command
        return close_command(args)
    if args.cmd == "integrate":
        from .integrate import integrate_command
        return integrate_command(args)
    if args.cmd == "complete":
        from .complete import complete_command
        return complete_command(args)
    if args.cmd == "report":
        from .report import report_command
        return report_command(args)
    if args.cmd == "eval":
        from .evaluate import eval_command
        return eval_command(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
