"""`holdfast integrate`: run Holdfast against one finding of a Claude Security report.

Reads CLAUDE-SECURITY-<ts>/CLAUDE-SECURITY-RESULTS.jsonl, the finding's patches/F<n>.patch and
F<n>.md, builds a contract from the patch applied at the stamped revision (in a scratch worktree,
as a scratch commit on no branch), runs the completeness query, and writes back in the plugin's
own schema: derived findings F<n>.1, F<n>.2 ... appended to the JSONL (each with a note file and a
"derived_from" field), records/F<n>.json, and a "Holdfast" section appended to the report markdown.
No patches are written for derived findings; they go through Suggest patches.
Schema source: claude-security plugin v0.11.0, scripts/lib/finding.py and render_report.py.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

from .complete import complete_contract, EXERCISE_CAP
from .contract import create_contract
from .gitutil import Repo
from .model import ModelClient

JSONL = "CLAUDE-SECURITY-RESULTS.jsonl"
REPORT_MD = "CLAUDE-SECURITY-RESULTS.md"
FIELD_ORDER = ["id", "title", "impact", "file", "line", "description", "exploit_scenario", "preconditions",
               "category", "severity", "confidence", "recommendation", "cwe_id", "snippet", "symbol",
               "declared_line", "derived_from", "claudeSecurityPluginFindingId"]


def load_findings(report: Path) -> list[dict]:
    return [json.loads(l) for l in (report / JSONL).read_text().splitlines() if l.strip()]


def stamped_commit(report: Path) -> str | None:
    for p in report.glob("CLAUDE-SECURITY-REVISION-*.json"):
        d = json.loads(p.read_text())
        rev = d.get("revision") or {}
        return rev.get("commit") or rev.get("head")
    return None


def patch_body(patch_text: str) -> str:
    """Drop the plugin's '#' header comment; git apply ignores it but we want the bare diff."""
    i = patch_text.find("diff --git")
    return patch_text[i:] if i >= 0 else patch_text


def scratch_commit_with_patch(repo: Repo, base: str, patch: str, tag: str) -> str:
    """Apply the patch at `base` in a scratch worktree and commit it there (detached; no branch)."""
    wt = Path(".targets/worktrees").resolve() / f"integrate-{tag}"
    repo.worktree(base, wt)
    try:
        (wt / ".holdfast.patch").write_text(patch)
        subprocess.run(["git", "-C", str(wt), "apply", ".holdfast.patch"], check=True)
        (wt / ".holdfast.patch").unlink()
        subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(wt), "-c", "user.name=holdfast", "-c", "user.email=holdfast@localhost",
                        "commit", "-q", "-m", f"holdfast scratch: {tag} applied at {base[:10]}"], check=True)
        return subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    finally:
        repo.remove_worktree(wt)


def derived_finding(parent: dict, k: int, u: dict) -> dict:
    lines = str(u.get("lines", ""))
    m = re.search(r"\b(\d{1,6})\b", lines)
    line = int(m.group(1)) if m else 0
    d = {
        "id": f"{parent['id']}.{k}",
        "title": f"Sibling consumer not covered by {parent['id']}'s patch: {u.get('function') or u.get('file')}",
        "impact": parent.get("impact", ""),
        "file": u.get("file", ""),
        "line": line,
        "description": (f"The value protected by {parent['id']} also reaches {u.get('function')} in {u.get('file')} "
                        f"without the guard the patch introduces. {u.get('reason', '')}").strip(),
        "exploit_scenario": f"As for {parent['id']}, via {u.get('function') or u.get('file')} instead of the patched site.",
        "preconditions": list(parent.get("preconditions", [])),
        "category": parent.get("category", ""),
        "severity": parent.get("severity", "MEDIUM"),
        "confidence": u.get("confidence", "low"),
        "recommendation": (f"Apply the same guard as {parent['id']} at this consumer, or route the value through the "
                           f"patched path. Not patched here: run Suggest patches on this finding."),
        "cwe_id": parent.get("cwe_id", ""),
        "snippet": lines if not lines.isdigit() else "",
        "symbol": u.get("function", ""),
        "declared_line": line,
        "derived_from": parent["id"],
        "claudeSecurityPluginFindingId": f"{parent.get('claudeSecurityPluginFindingId', parent['id'])}.{k}",
    }
    return {key: d[key] for key in FIELD_ORDER if key in d}


def integrate(report: Path, fid: str, repo_path: Path | None, model: ModelClient) -> dict:
    report = report.resolve()
    repo_path = (repo_path or report.parent).resolve()
    repo = Repo(repo_path)
    findings = load_findings(report)
    parent = next((f for f in findings if f["id"] == fid), None)
    if parent is None:
        raise SystemExit(f"{fid} not in {report / JSONL}")
    patch_path = report / "patches" / f"{fid}.patch"
    note_path = report / "patches" / f"{fid}.md"
    if not patch_path.exists():
        raise SystemExit(f"{fid} has no patch file ({patch_path}); Holdfast needs the patch to build the contract")
    base = stamped_commit(report) or repo.rev_parse("HEAD")
    patch = patch_body(patch_path.read_text())
    note = note_path.read_text() if note_path.exists() else ""

    scratch = scratch_commit_with_patch(repo, base, patch, fid)
    advisory_text = (f"{parent['id']}: {parent['title']}\n{'=' * (len(parent['id']) + len(parent['title']) + 2)}\n\n"
                     f"{parent.get('description', '')}\n\nImpact: {parent.get('impact', '')}\n\n"
                     f"Exploit scenario: {parent.get('exploit_scenario', '')}\n\nRecommendation: {parent.get('recommendation', '')}\n"
                     f"\nPatch note (Claude Security):\n{note}")
    adv_file = report / "records"
    adv_file.mkdir(exist_ok=True)
    (adv_file / f"{fid}.advisory.txt").write_text(advisory_text)
    c = create_contract(str(repo_path), scratch, fid, str(adv_file / f"{fid}.advisory.txt"), model, run_tests=True)
    c.target_repo = str(repo_path.name)
    k = complete_contract(c, repo, model)

    derived = []
    for i, u in enumerate([u for u in k["uncovered"] if u.get("confidence") in ("medium", "high", "low")], 1):
        derived.append(derived_finding(parent, i, u))
    # write back: JSONL, notes, record, report section
    existing = {f["id"] for f in findings}
    with (report / JSONL).open("a") as f:
        for d in derived:
            if d["id"] not in existing:
                f.write(json.dumps(d) + "\n")
    (report / "patches").mkdir(exist_ok=True)
    for d, u in zip(derived, k["uncovered"]):
        (report / "patches" / f"{d['id']}.md").write_text(
            f"# {d['id']} — derived by Holdfast from {fid}\n\n"
            f"**Consumer:** `{d['symbol']}` in `{d['file']}`, line {d['line']}.\n\n"
            f"**Line(s) that consume the protected value:**\n\n```\n{u.get('lines', '')}\n```\n\n"
            f"**Why it is not covered by {fid}'s patch:** {u.get('reason', '')}\n\n"
            f"**Confidence:** {d['confidence']} (the completeness query's own confidence for this consumer).\n\n"
            f"**Protected value:** {k.get('protected_value')}\n\n"
            f"No patch is written for a derived finding. Run Suggest patches on `{d['id']}` to get one; "
            f"it will be built and reviewed like any other patch.\n")
    record = {
        "finding": fid, "report": str(report), "patch": str(patch_path), "patch_base_commit": base,
        "scratch_commit": scratch, "scratch_note": "patch applied at the stamped revision in a scratch worktree; "
                                                    "this commit is on no branch and is not pushed",
        "property": c.property, "vulnerability": c.vulnerability, "scope": asdict(c.scope),
        "evidence_by_tier": [asdict(e) for e in c.evidence_at_creation],
        "kept_test": c.regression_test, "kept_test_reason": c.regression_test_reason,
        "completeness": {kk: v for kk, v in k.items() if kk != "model_reply_verbatim"},
        "completeness_model_reply_verbatim": k.get("model_reply_verbatim"),
        "cannot_verify": (c.uncertainty + " Consumers outside this repository (third-party packages, deployment "
                          "configuration) are not examined; the consumer list is only as complete as the symbol "
                          "references the query was shown."),
        "derived_findings": [d["id"] for d in derived],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance": "holdfast integrate (prototype); plugin artifacts above were not modified except the appends listed",
    }
    (report / "records" / f"{fid}.json").write_text(json.dumps(record, indent=2) + "\n")
    sec = [f"\n\n## Holdfast\n\nCompleteness check for {fid} at patch base `{base[:10]}` "
           f"(record: `records/{fid}.json`). Protected value: {k.get('protected_value')}. Verdict: **{k['verdict']}**.\n"]
    if derived:
        sec.append("\nDerived findings (no patches written; route through Suggest patches):\n\n")
        sec.append("| id | consumer | file:line | confidence | note |\n|---|---|---|---|---|\n")
        for d in derived:
            sec.append(f"| {d['id']} | `{d['symbol']}` | `{d['file']}:{d['line']}` | {d['confidence']} | `patches/{d['id']}.md` |\n")
    else:
        sec.append("\nNo uncovered consumers were listed. Cannot verify: " + record["cannot_verify"] + "\n")
    md = (report / REPORT_MD).read_text()
    cut = md.find("\n\n## Holdfast\n")
    if cut >= 0:
        md = md[:cut]   # re-runs replace the Holdfast section rather than stacking copies
    (report / REPORT_MD).write_text(md + "".join(sec))
    return {"finding": fid, "verdict": k["verdict"], "derived": [d["id"] for d in derived],
            "record": str(report / "records" / f"{fid}.json"), "protected_value": k.get("protected_value")}


def integrate_command(args) -> int:
    model = ModelClient(args.model, disabled=args.no_model, cap=(args.cap or 150 + EXERCISE_CAP))
    r = integrate(Path(args.report), args.finding, Path(args.repo) if args.repo else None, model)
    print(json.dumps(r, indent=2))
    return 0
