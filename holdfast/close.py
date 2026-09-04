"""`holdfast close`: integrate, then close the finding as a PR on the user's fork.

Runs `integrate` exactly as today (contract, completeness query, record and derived findings into the
report dir), then in the target repository: branch `holdfast/close-<finding>-<shortrev>` from the report's
stamped revision, apply the finding's patch as one commit (tests in the patch as a separate "kept test"
commit), write and commit `.holdfast/records/<finding>.json`, push branch + base to the fork, open a PR
with `gh pr create` whose body is built from the record. Nothing is applied without the user choosing close.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from .gitutil import Repo
from .integrate import integrate, load_findings, stamped_commit, patch_body
from .model import ModelClient
from .complete import EXERCISE_CAP


def _run(args, cwd=None, check=True) -> str:
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"{' '.join(args)}\n{r.stderr.strip()}")
    return r.stdout.strip()


def provenance_line(report: Path) -> str:
    p = report / "PROVENANCE.md"
    if p.exists() and "HAND-BUILT" in p.read_text().upper():
        return "Patch hand-built in the plugin's schema — see PROVENANCE.md."
    return "Patch produced by Claude Security plugin."


def gh_repo_from_remote(repo_path: Path, remote: str) -> str:
    url = _run(["git", "-C", str(repo_path), "remote", "get-url", remote])
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    if not m:
        raise SystemExit(f"cannot derive GitHub repo from remote {remote} ({url})")
    return m.group(1)


def close(report: Path, fid: str, repo_path: Path | None, model: ModelClient, remote: str = "fork") -> dict:
    r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if "Logged in" not in (r.stdout + r.stderr):
        raise SystemExit("gh is not authenticated; run `gh auth login` and retry. Nothing was done.")
    report = report.resolve()
    repo_path = (repo_path or report.parent).resolve()
    repo = Repo(repo_path)
    gh_repo = gh_repo_from_remote(repo_path, remote)

    # 1. integrate, exactly as today
    result = integrate(report, fid, repo_path, model)
    record = json.loads((report / "records" / f"{fid}.json").read_text())
    parent = next(f for f in load_findings(report) if f["id"] == fid)
    base = stamped_commit(report) or repo.rev_parse("HEAD")
    short = base[:10]
    prov = provenance_line(report)

    # 2. branches in the target repo
    base_branch = f"holdfast-base-{short}"
    branch = f"holdfast/close-{fid}-{short}"
    if _run(["git", "-C", str(repo_path), "rev-parse", "--verify", "-q", base_branch], check=False) == "":
        _run(["git", "-C", str(repo_path), "branch", base_branch, base])
    _run(["git", "-C", str(repo_path), "branch", "-f", branch, base])
    wt = Path(".targets/worktrees").resolve() / f"close-{fid}-{short}"
    _run(["git", "-C", str(repo_path), "worktree", "remove", "--force", str(wt)], check=False)
    _run(["git", "-C", str(repo_path), "worktree", "prune"])
    _run(["git", "-C", str(repo_path), "worktree", "add", "-q", str(wt), branch])
    commits = []
    try:
        patch = patch_body((report / "patches" / f"{fid}.patch").read_text())
        (wt / ".holdfast.patch").write_text(patch)
        _run(["git", "-C", str(wt), "apply", ".holdfast.patch"])
        (wt / ".holdfast.patch").unlink()
        changed = subprocess.run(["git", "-C", str(wt), "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
        paths = [l.split(None, 1)[1] for l in changed if l.strip()]
        test_paths = [p for p in paths if p.startswith("tests/") or "/tests/" in p or "/test_" in p]
        src_paths = [p for p in paths if p not in test_paths]
        ident = ["-c", "user.name=Holdfast", "-c", "user.email=holdfast@localhost"]
        # 3. fix commit
        _run(["git", "-C", str(wt), "add", "--", *src_paths])
        _run(["git", "-C", str(wt), *ident, "commit", "-q", "-m", f"Close {fid}: {parent['title']}", "-m", f"Closes {fid}. {prov}"])
        commits.append(("fix", _run(["git", "-C", str(wt), "rev-parse", "HEAD"]), f"Close {fid}: {parent['title']}"))
        # 4. kept test
        if test_paths:
            _run(["git", "-C", str(wt), "add", "--", *test_paths])
            _run(["git", "-C", str(wt), *ident, "commit", "-q", "-m", f"Kept test for {fid}",
                  "-m", f"Test changes carried by {fid}'s patch, kept as the regression test for the record."])
            commits.append(("kept test", _run(["git", "-C", str(wt), "rev-parse", "HEAD"]), f"Kept test for {fid}"))
            kept_test = {"paths": test_paths, "reason": None}
        else:
            kept_test = {"paths": None, "reason": "patch carries no tests"}
        # 5. record in a committed location
        record["kept_test"] = kept_test
        record["close"] = {"branch": branch, "base_branch": base_branch, "base_commit": base, "commits": [
            {"role": r, "sha": s, "subject": t} for r, s, t in commits], "provenance": prov}
        rec_dir = wt / ".holdfast" / "records"
        rec_dir.mkdir(parents=True, exist_ok=True)
        (rec_dir / f"{fid}.json").write_text(json.dumps(record, indent=2) + "\n")
        _run(["git", "-C", str(wt), "add", "--", f".holdfast/records/{fid}.json"])
        _run(["git", "-C", str(wt), *ident, "commit", "-q", "-m", f"Add Holdfast record for {fid}",
              "-m", f"Property, evidence by tier, kept test ({'present' if test_paths else 'null: ' + kept_test['reason']}), "
                    f"cannot-verify, completeness verdict {record['completeness']['verdict']}."])
        commits.append(("record", _run(["git", "-C", str(wt), "rev-parse", "HEAD"]), f"Add Holdfast record for {fid}"))
        record["close"]["commits"] = [{"role": r, "sha": s, "subject": t} for r, s, t in commits]
        # 6. push + PR
        _run(["git", "-C", str(wt), "push", "-q", "-f", remote, f"{base_branch}:{base_branch}", f"{branch}:{branch}"])
    finally:
        _run(["git", "-C", str(repo_path), "worktree", "remove", "--force", str(wt)], check=False)

    body = render_pr_body(record, parent["title"], fid)
    body_path = report / "records" / f"{fid}.pr-body.md"
    body_path.write_text(body)
    url = _run(["gh", "pr", "create", "--repo", gh_repo, "--base", base_branch, "--head", branch,
                "--title", f"{fid}: {parent['title']} — closed by Holdfast", "--body-file", str(body_path)])
    record["close"]["pr_url"] = url
    (report / "records" / f"{fid}.json").write_text(json.dumps(record, indent=2) + "\n")
    return {"finding": fid, "verdict": record["completeness"]["verdict"], "derived": record.get("derived_findings") or [],
            "commits": record["close"]["commits"], "kept_test": kept_test, "pr_url": url}


def render_pr_body(record: dict, title: str, fid: str, commits: list[dict] | None = None) -> str:
    """PR body from the record. The user-facing completeness text never says COMPLETE: it lists what was
    examined and then what cannot be verified. The internal verdict enum stays in the record JSON."""
    cl = record["close"]
    k = record["completeness"]
    kept = record["kept_test"]
    derived = record.get("derived_findings") or []
    commits = commits or cl["commits"]
    fix = next(c for c in commits if c["role"] == "fix")
    rec = next(c for c in commits if c["role"] == "record")
    kept_c = next((c for c in commits if c["role"] == "kept test"), None)
    scratch = (record.get("scratch_commit") or "")[:10]
    rev = cl["base_commit"][:10]
    where = f"scratch commit {scratch} (the patch applied at {rev}); branch commit {fix['sha'][:10]}"
    def cite(detail: str) -> str:
        # tier-1 text says "PASS on fix <scratch>"; make the scratch/branch distinction explicit
        if not scratch:
            return detail
        if f"on fix {scratch}" in detail:
            return detail.replace(f"on fix {scratch}", f"on {where}")
        return detail.replace(scratch, f"scratch commit {scratch}")
    ev = "\n".join(f"  - tier {e['tier']} {e['kind']}: {cite(e['detail'])}" for e in record["evidence_by_tier"])
    examined = k.get("covered") or []
    ex_lines = "\n".join(f"- `{c.get('function')}` in `{c.get('file')}` — {c.get('reason', '')}" for c in examined) or "- (none listed)"
    kept_line = (f"commit `{kept_c['sha'][:10]}`, paths {', '.join(kept['paths'])}" if kept.get("paths") and kept_c
                 else f"null — {kept.get('reason')}")
    low = [u for u in (k.get("uncovered") or []) if u.get("confidence") not in ("medium", "high")]
    if derived:
        derived_text = (", ".join(derived) + (f" ({len(low)} listed at low confidence, below the verdict threshold)" if low else "")
                        + ". Derived findings go back through Suggest patches; no sibling patches are in this PR.")
    else:
        derived_text = "none. Derived findings, when listed, go back through Suggest patches; no sibling patches are in this PR."
    headline = (f"No uncovered consumers at medium or high confidence among the {len(examined) + len(low)} examined; "
                f"{len(low)} listed at low confidence (see derived findings)" if low
                else f"No uncovered consumers found among the {len(examined)} examined")
    return f"""**Closed by Holdfast** (`holdfast close`). Base `{cl['base_branch']}` is the report's stamped revision {cl['base_commit'][:10]}. {cl['provenance']}

## Property

{record['property']}

## Evidence by tier, per commit

- **Fix commit** `{fix['sha'][:10]}` — {fix.get('subject', title)} (evidence gathered on {where}):
{ev}
- **Kept test:** {kept_line}
- **Record commit** `{rec['sha'][:10]}` — `.holdfast/records/{fid}.json`

## Completeness

{headline} (protected value: {k.get('protected_value')}; {len(k.get('files_in_context', []))} files in context):

{ex_lines}
{chr(10).join(f"- `{u.get('function')}` in `{u.get('file')}` — listed at {u.get('confidence')} confidence: {u.get('reason', '')}" for u in low)}

Cannot verify: {record['cannot_verify']}

Derived findings: {derived_text}

---
Nothing in this PR was applied without the user choosing close.
"""


def close_command(args) -> int:
    model = ModelClient(args.model, disabled=args.no_model, cap=(args.cap or 150 + EXERCISE_CAP))
    r = close(Path(args.report), args.finding, Path(args.repo) if args.repo else None, model, remote=args.remote)
    print(json.dumps(r, indent=2))
    print(r["pr_url"])
    return 0
