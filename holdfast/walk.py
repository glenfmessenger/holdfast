"""`holdfast walk`: re-verify a contract on every later commit that touches its scope.

Tiers are tried in order 1 -> 4 and evaluation stops at the first tier that yields a
confident verdict. Every piece of evidence is labelled with the tier that produced it;
tiers are never blended. When the model disagrees with tiers 1-3, both are recorded.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict
from pathlib import Path

from .gitutil import Repo
from .model import ModelClient
from .models import Contract, Evidence, Status, Tier, Verdict
from .scope import normalize, is_source
from . import testrun

SYSTEM_WALK = """You are re-verifying a "remediation contract": a security property that a past fix
established, checked against a later commit in the same repository. You are given the
contract (property, vulnerability, the guard the fix introduced), what the cheaper checks
found at this commit (tier 1: test execution; tier 2: guard-line presence; tier 3: rules),
this commit's diff restricted to the contract's scope, and the current text of the scope
functions.

Decide whether the property still holds AT THIS COMMIT. Reply with ONE JSON object:
- "status": one of "HELD", "REGRESSED", "INCOMPLETE_AT_MERGE", "MOVED", "UNVERIFIABLE"
    HELD: property holds (including when guard code was rewritten but the invariant is intact).
    REGRESSED: the invariant no longer holds -- the guard was removed or bypassed.
    MOVED: the code carrying the property was relocated/renamed and the invariant is intact there.
    INCOMPLETE_AT_MERGE: this commit reveals the original fix never fully established the property.
    UNVERIFIABLE: you cannot tell from what you were shown; say what is missing.
- "rationale": 2-4 sentences grounded in the diff/code shown. Quote the decisive line(s).
- "confidence": "low" | "medium" | "high"
- "confidence_reason": one sentence.
Judge the INVARIANT, not the literal lines: a rename or rewrite that preserves the guarantee
is HELD or MOVED, not REGRESSED. A rename that also drops the guarantee is REGRESSED.
Describe what you saw as evidence; do not claim certainty beyond it."""

DISTINCTIVE_MIN = 14
GENERIC_LINES = {"#endif", "#else", "return", "break", "continue", "pass", "va_end(args);", "va_start(args, fmt);"}


def distinctive(line: str) -> bool:
    s = line.strip()
    return len(s) >= DISTINCTIVE_MIN and s not in GENERIC_LINES and not s.startswith(("import ", "from "))


# ---------------------------------------------------------------- scope over time
def collect_commits(repo: Repo, rng: str, paths: list[str]) -> tuple[list[tuple[str, str, str]], dict[str, str], list[tuple[str, str, str]]]:
    """Commits in rng touching `paths` or any path they are renamed to inside rng.
    Returns (commits oldest-first, rename map old->new, renames list)."""
    renames = repo.renames_in_range(rng)
    tracked = set(paths)
    rename_map: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for _, old, new in renames:
            if old in tracked and new not in tracked:
                tracked.add(new)
                rename_map[old] = new
                changed = True
    commits = repo.log_range(rng, *sorted(tracked))
    return commits, rename_map, [r for r in renames if r[1] in tracked]


def sample(commits: list, cap: int, include: set[str]) -> tuple[list, list]:
    """Evenly sample to `cap`, always keeping first, last and any `include` prefixes."""
    if len(commits) <= cap:
        return commits, []
    n = len(commits)
    idx = sorted({round(i * (n - 1) / (cap - 1)) for i in range(cap)})
    keep = set(idx)
    for i, (h, _, _) in enumerate(commits):
        if any(h.startswith(p) for p in include):
            keep.add(i)
    chosen = [commits[i] for i in sorted(keep)]
    skipped = [c for i, c in enumerate(commits) if i not in keep]
    return chosen, skipped


# ---------------------------------------------------------------- tier helpers
def guard_presence(repo: Repo, ref: str, files: list[str], guard_lines: list[str]) -> tuple[list[str], list[str], dict[str, list[str]]]:
    per_file: dict[str, list[str]] = {}
    corpus = ""
    for f in files:
        txt = repo.show_file(ref, f)
        if txt is None:
            continue
        norm = [normalize(l) for l in txt.splitlines()]
        per_file[f] = [g for g in guard_lines if g in norm]
        corpus += "\n" + "\n".join(norm)
    present = [g for g in guard_lines if g in corpus]
    absent = [g for g in guard_lines if g not in corpus]
    return present, absent, per_file


def find_elsewhere(repo: Repo, ref: str, lines: list[str], exclude: list[str], glob: str) -> dict[str, list[str]]:
    """Where else in the repo (source files) do these distinctive guard lines appear at ref?"""
    import subprocess
    found: dict[str, list[str]] = {}
    for g in lines:
        if not distinctive(g):
            continue
        # search on a stable fragment: the longest token-ish chunk
        r = subprocess.run(["git", "-C", str(repo.path), "grep", "-n", "-F", "-e", g.split(" = ")[-1][:60] if " = " in g else g[:60],
                            ref, "--", glob], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            _, path, ln, txt = line.split(":", 3)
            if path in exclude or not is_source(path):
                continue
            if normalize(txt) == g:
                found.setdefault(path, []).append(g)
    return found


def function_sources(repo: Repo, ref: str, files: list[str], qualnames: list[str], limit: int = 9000) -> str:
    """Current text of the scope functions at ref (Python via ast; C via brace matching-lite)."""
    out = []
    for f in files:
        src = repo.show_file(ref, f)
        if src is None:
            out.append(f"## {f}: (missing at this commit)")
            continue
        wanted = [q.split("::", 1)[1] for q in qualnames if q.startswith(f + "::")]
        if not wanted:
            continue
        if f.endswith(".py"):
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            lines = src.splitlines()
            def walk(node, prefix):
                for ch in ast.iter_child_nodes(node):
                    if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        q = f"{prefix}.{ch.name}" if prefix else ch.name
                        if q in wanted:
                            seg = "\n".join(lines[ch.lineno - 1: getattr(ch, "end_lineno", ch.lineno)])
                            out.append(f"## {f}::{q} @ {ref[:10]}\n{seg[:3000]}")
                        walk(ch, q)
                    else:
                        walk(ch, prefix)
            walk(tree, "")
            missing = [q for q in wanted if not any(o.startswith(f"## {f}::{q} ") for o in out)]
            for q in missing:
                out.append(f"## {f}::{q}: NOT FOUND by name at this commit (renamed, moved or removed)")
        else:
            lines = src.splitlines()
            for q in wanted:
                for i, l in enumerate(lines):
                    if re.match(r"^" + re.escape(q) + r"\s*\(", l):
                        out.append(f"## {f}::{q} @ {ref[:10]}\n" + "\n".join(lines[max(0, i - 2): i + 30]))
                        break
                else:
                    out.append(f"## {f}::{q}: NOT FOUND by name at this commit (renamed, moved or removed)")
    return "\n\n".join(out)[:limit]


# ---------------------------------------------------------------- main evaluation
def evaluate_commit(repo: Repo, c: Contract, commit: str, date: str, subject: str, files: list[str],
                    prev_present: list[str] | None, model: ModelClient, spec, glob: str,
                    run_tests: bool) -> tuple[Verdict, list[str]]:
    ev: list[Evidence] = []
    guard = c.scope.guard_lines
    status = None
    tier = None
    rationale = ""
    conf = "low"
    conf_reason = ""
    disagreement = None

    # ---- Tier 1: EXECUTED
    t1 = None
    if spec is not None and run_tests:
        res = testrun.run_spec(repo, commit, spec)
        t1 = res.outcome
        ev.append(Evidence(Tier.EXECUTED, "regression_test", f"{res.outcome}: {res.summary}",
                           {"test_ids": spec.test_ids, "python": res.python, "tail": res.tail[-1200:]}))
        if res.outcome == "pass":
            status, tier, conf = Status.HELD, Tier.EXECUTED, "high"
            rationale = f"The regression test extracted from the fix commit ({len(spec.test_ids)} test id(s)) passes at this commit."
            conf_reason = "executed test passed"
        elif res.outcome == "fail":
            status, tier, conf = Status.REGRESSED, Tier.EXECUTED, "high"
            rationale = f"The regression test extracted from the fix commit fails at this commit: {res.summary}."
            conf_reason = "executed test failed with assertion failures"
    elif spec is None:
        ev.append(Evidence(Tier.EXECUTED, "regression_test", f"skipped: {c.regression_test_reason or 'no regression test in contract'}"))
    else:
        ev.append(Evidence(Tier.EXECUTED, "regression_test", "skipped: --no-tests"))

    # ---- Tier 2: STRUCTURAL (always computed; it is also the input to tiers 3-4)
    present, absent, per_file = guard_presence(repo, commit, files, guard)
    elsewhere = find_elsewhere(repo, commit, absent, files, glob) if absent else {}
    newly_lost = [g for g in absent if prev_present is None or g in prev_present]
    t2_detail = (f"{len(present)}/{len(guard)} guard lines present in scope files; "
                 f"{len(newly_lost)} lost at this commit"
                 + (f"; {sum(len(v) for v in elsewhere.values())} of the absent lines found in other files: {sorted(elsewhere)}" if elsewhere else ""))
    ev.append(Evidence(Tier.STRUCTURAL, "guard_lines", t2_detail,
                       {"present": present, "absent": absent, "newly_lost": newly_lost, "elsewhere": elsewhere,
                        "per_file": per_file, "files_checked": files}))
    moved_to = sorted(elsewhere)
    if status is None:
        if not absent:
            status, tier, conf = Status.HELD, Tier.STRUCTURAL, "medium"
            rationale = (f"All {len(guard)} guard lines the fix introduced are present in the scope files at this commit"
                         f" ({', '.join(files)}). This commit did not remove any of them.")
            conf_reason = "guard lines intact; a new bypass path outside these lines would not be detected"
        elif absent and elsewhere and all(any(g in v for v in elsewhere.values()) for g in absent if distinctive(g)):
            status, tier, conf = Status.MOVED, Tier.STRUCTURAL, "medium"
            rationale = (f"{len(absent)} guard line(s) are no longer in {', '.join(files)} but every distinctive one "
                         f"is found verbatim in {', '.join(moved_to)}. The code carrying the property moved.")
            conf_reason = "verbatim guard lines relocated; invariant assumed intact at new location"

    # ---- Tier 3: RULE — the pre-fix (vulnerable) line reappears in scope
    if status is None or status == Status.MOVED:
        corpus = ""
        for f in files + moved_to:
            corpus += "\n" + "\n".join(normalize(l) for l in (repo.show_file(commit, f) or "").splitlines())
        resurrected = [r for r in c.removed_lines if distinctive(r) and r in corpus]
        ev.append(Evidence(Tier.RULE, "removed_line_reappears",
                           f"{len(resurrected)} of {len([r for r in c.removed_lines if distinctive(r)])} distinctive pre-fix lines reappear in scope",
                           {"resurrected": resurrected}))
        if resurrected:
            status, tier, conf = Status.REGRESSED, Tier.RULE, "medium"
            rationale = (f"A line the fix deleted is back in scope: {resurrected[0]!r}. The vulnerable pre-fix "
                         f"construct has reappeared.")
            conf_reason = "verbatim reappearance of deleted vulnerable code; context not analysed"

    # ---- Tier 4: MODEL
    if status is None or (status == Status.MOVED and tier == Tier.STRUCTURAL):
        # MOVED at tier 2 is a hypothesis; the model confirms whether the invariant survived the move.
        diff = repo.commit_diff(commit, "--", *dict.fromkeys(files + moved_to))
        fn_src = function_sources(repo, commit, files + moved_to, c.scope.functions)
        lower = "\n".join(f"- tier {e.tier}: {e.kind}: {e.detail}" for e in ev)
        user = (f"CONTRACT {c.id} (fix {c.fix_commit[:10]}):\nVULNERABILITY: {c.vulnerability}\nPROPERTY: {c.property}\n"
                f"GUARD LINES AT FIX:\n" + "\n".join(f"  {g}" for g in guard) +
                f"\nPRE-FIX LINES THE FIX DELETED:\n" + "\n".join(f"  {r}" for r in c.removed_lines) +
                f"\n\nCOMMIT {commit[:10]} ({date}): {subject}\n\nLOWER-TIER FINDINGS AT THIS COMMIT:\n{lower}\n\n"
                f"DIFF OF THIS COMMIT (scope files only):\n{diff[:14000]}\n\nCURRENT SCOPE FUNCTIONS AT THIS COMMIT:\n{fn_src}")
        res = model.call("walk", c.id, commit, SYSTEM_WALK, user)
        if res is None:
            reason = model.unavailable_reason()
            ev.append(Evidence(Tier.MODEL, "judgement", f"not attempted: {reason}"))
            if status is None:
                status, tier, conf = Status.UNVERIFIABLE, Tier.STRUCTURAL, "low"
                rationale = (f"Tiers 1-3 were inconclusive ({len(absent)} of {len(guard)} guard lines absent, no rule fired) "
                             f"and tier 4 was unavailable: {reason}.")
                conf_reason = reason
        elif res["parsed"] is None:
            ev.append(Evidence(Tier.MODEL, "judgement", "model reply not parseable as JSON",
                               {"model_rationale_verbatim": res["text"]}))
            if status is None:
                status, tier, conf = Status.UNVERIFIABLE, Tier.MODEL, "low"
                rationale = "Tiers 1-3 inconclusive and the model reply could not be parsed."
                conf_reason = "unparseable model output"
        else:
            p = res["parsed"]
            m_status = str(p.get("status", "UNVERIFIABLE")).upper()
            if m_status not in Status.__members__:
                m_status = "UNVERIFIABLE"
            ev.append(Evidence(Tier.MODEL, "judgement", f"model says {m_status} ({p.get('confidence','?')})",
                               {"model_rationale_verbatim": p.get("rationale", ""), "model_reply_verbatim": res["text"],
                                "model": res["usage"]["model"]}))
            if status is not None and status.value != m_status:
                disagreement = {"lower_tier": {"tier": int(tier), "status": status.value, "rationale": rationale},
                                "model": {"status": m_status, "rationale": p.get("rationale", "")},
                                "note": "Recorded, not reconciled. The verdict below takes the model's status because the lower tier's MOVED was a hypothesis about verbatim lines, but both are data."}
            status, tier = Status(m_status), Tier.MODEL
            rationale = p.get("rationale", "")
            conf = p.get("confidence", "low") if p.get("confidence") in ("low", "medium", "high") else "low"
            conf_reason = "model: " + str(p.get("confidence_reason", ""))

    v = Verdict(contract_id=c.id, commit=commit, commit_date=date, commit_subject=subject, status=status.value,
                tier=int(tier), evidence=ev, rationale=rationale, confidence=conf, confidence_reason=conf_reason,
                tier_disagreement=disagreement)
    return v, present


def walk_contract(c: Contract, repo: Repo, rng: str, cap: int, model: ModelClient, only: set[str] | None,
                  include: set[str], run_tests: bool = True, out_dir: Path = Path("results/verdicts")) -> list[Verdict]:
    glob = "*.py" if any(f.endswith(".py") for f in c.scope.files) else "*.[ch]"
    commits, rename_map, renames = collect_commits(repo, rng, c.scope.files)
    chosen, skipped = sample(commits, cap, include)
    if only:
        chosen = [x for x in chosen if any(x[0].startswith(p) for p in only)]
    walk_note = (f"range {rng}: {len(commits)} commits touch scope; evaluated {len(chosen)}"
                 + (f", skipped {len(skipped)} by even sampling (cap {cap})" if skipped else "")
                 + (f"; renames followed: {[(r[0][:10], r[1], r[2]) for r in renames]}" if renames else ""))
    spec = None
    if c.regression_test and Path(c.regression_test).exists():
        spec = testrun.TestSpec(**json.loads(Path(c.regression_test).read_text()))
    files = list(c.scope.files)
    prev_present: list[str] | None = list(c.scope.guard_lines)
    verdicts: list[Verdict] = []
    rename_by_commit: dict[str, list[tuple[str, str]]] = {}
    for h, old, new in renames:
        rename_by_commit.setdefault(h, []).append((old, new))
    for h, date, subject in commits:
        # apply renames that happen at this commit before checking (new path holds the content)
        if h in rename_by_commit:
            for old, new in rename_by_commit[h]:
                files = [new if f == old else f for f in files]
        if not any(h == ch for ch, _, _ in chosen):
            continue
        v, present = evaluate_commit(repo, c, h, date, subject, files, prev_present, model, spec, glob, run_tests)
        v.sampled = bool(skipped)
        v.walk_note = walk_note + (f"; evaluated={[x[0][:10] for x in chosen]}; skipped={[x[0][:10] for x in skipped]}" if skipped else "")
        if h in rename_by_commit:
            v.evidence.insert(0, Evidence(Tier.STRUCTURAL, "rename_followed", f"scope paths renamed at this commit: {rename_by_commit[h]}"))
        # self-healing scope: if MOVED, add the new locations to the files we watch from now on
        t2 = next((e for e in v.evidence if e.kind == "guard_lines"), None)
        if t2 and t2.data.get("elsewhere"):
            for f in t2.data["elsewhere"]:
                if f not in files:
                    files.append(f)
        prev_present = present
        v.save(out_dir)
        verdicts.append(v)
        print(f"  {h[:10]} {date} {v.status:<20} tier={v.tier} {subject[:60]}", flush=True)
    return verdicts


def walk_command(args) -> int:
    c = Contract.load(args.contract)
    repo = Repo(Path(args.repo))
    model = ModelClient(args.model, disabled=args.no_model)
    only = set(args.only.split(",")) if args.only else None
    include = set(args.include.split(",")) if getattr(args, "include", None) else set()
    print(f"walk {c.id}: scope {c.scope.files}")
    vs = walk_contract(c, repo, args.range, args.cap, model, only, include, run_tests=not getattr(args, "no_tests", False))
    print(f"{len(vs)} verdicts written to results/verdicts/{c.id}/")
    return 0
