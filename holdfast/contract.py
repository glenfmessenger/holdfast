"""`holdfast create`: build one Contract from a fix commit and its advisory text."""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from .advisory import load_advisory
from .gitutil import Repo
from .model import ModelClient
from .models import Contract, Evidence, Scope, SiblingCheck, Tier
from .scope import (parse_hunks, is_source, normalize, substantive, enclosing_qualnames,
                    c_enclosing_functions, called_names, defined_names, find_callers)
from . import testrun

TESTS_DIR = Path("contracts/tests")

SYSTEM_CREATE = """You are helping build a "remediation contract" for a security fix: a durable record of
the security property the fix establishes, so it can be re-verified on later commits.
You are given the advisory text, the fix diff, the derived scope, and grep hits for
similar patterns elsewhere in the codebase at fix time.

Reply with ONE JSON object and nothing else, with these keys:
- "vulnerability": 1-2 plain-language sentences: what was exploitable, before the fix.
- "property": the security property the fix establishes, stated as an invariant over
  the code in scope (e.g. "user-supplied path is canonicalized before filesystem access in X").
  Be concrete: name the function(s) and the ordering/guard that must hold.
- "guard_summary": one sentence naming the specific code construct that carries the property.
- "sibling": {"covered": true|false|null, "note": "..."} -- do similar dangerous patterns exist
  elsewhere in scope at fix time, and did this fix cover them? null if you cannot tell.
  Base this ONLY on the grep hits and diff provided; do not speculate about code you were not shown.
- "uncertainty": 1-3 sentences on what this contract cannot verify about the property.
Describe what you saw as evidence; do not claim certainty beyond it."""


def _source_diff(repo: Repo, fix: str) -> tuple[str, list[str]]:
    files = [p for p in repo.changed_files(fix) if is_source(p)]
    return (repo.commit_diff(fix, "--", *files) if files else ""), files


def _lang_glob(files: list[str]) -> str:
    return "*.py" if any(f.endswith(".py") for f in files) else "*.[ch]"


def build_scope(repo: Repo, fix: str, diff: str, files: list[str]) -> tuple[Scope, list[str]]:
    hunks = parse_hunks(diff)
    functions: list[str] = []
    added_lines: list[str] = []
    removed_lines: list[str] = []
    for h in hunks:
        added_lines += [t for _, t in h.added]
        removed_lines += [t for _, t in h.removed]
        src = repo.show_file(fix, h.path)
        if src is None:
            continue
        lang = "py" if h.path.endswith(".py") else "c"
        linenos = {ln for ln, t in h.added if substantive(t, lang)}
        if h.path.endswith(".py"):
            names = enclosing_qualnames(src, linenos)
        else:
            names = c_enclosing_functions(src, linenos)
        functions += [f"{h.path}::{n}" for n in names]
    lang = "py" if any(f.endswith(".py") for f in files) else "c"
    guard = [normalize(l) for l in added_lines if substantive(l, lang)]
    removed = [normalize(l) for l in removed_lines if substantive(l, lang)]
    # lines that merely moved (present in both) are not guards
    guard_only = [g for g in guard if g not in removed]
    removed_only = [r for r in removed if r not in guard]
    symbols = list(dict.fromkeys(defined_names(added_lines) + called_names([l for l in added_lines if substantive(l, lang)])))
    symbols = [s for s in symbols if s not in ("self", "cls")][:25]
    fn_names = [f.split("::")[-1].split(".")[-1] for f in functions] + defined_names(added_lines)
    callers = find_callers(repo, fix, list(dict.fromkeys(fn_names)), files, _lang_glob(files))
    scope = Scope(files=files, functions=list(dict.fromkeys(functions)), symbols=symbols,
                  guard_lines=guard_only, callers=callers)
    return scope, removed_only


def structural_check(repo: Repo, ref: str, scope: Scope) -> tuple[list[str], list[str]]:
    """Which guard lines are present/absent in the scope files at `ref` (whitespace-normalized)."""
    corpus = ""
    for f in scope.files:
        corpus += "\n" + "\n".join(normalize(l) for l in (repo.show_file(ref, f) or "").splitlines())
    present = [g for g in scope.guard_lines if g in corpus]
    absent = [g for g in scope.guard_lines if g not in corpus]
    return present, absent


def sibling_grep(repo: Repo, fix: str, removed_lines: list[str], scope: Scope, glob: str) -> list[str]:
    """Look for the *pre-fix* dangerous pattern (removed lines' key calls) elsewhere in scope+callers."""
    pats = [n for n in called_names(removed_lines, dotted=True)
            if len(n.split(".")[-1]) >= 5 and n.split(".")[-1] not in ("force_str", "unescape", "force_bytes")]
    hits: list[str] = []
    seen = set()
    search_files = list(scope.files) + [c.split(":")[0] for c in scope.callers]
    for name in pats:
        pat = re.compile(r"(?<![A-Za-z0-9_.])" + re.escape(name) + r"\s*\(")
        for f in dict.fromkeys(search_files):
            src = repo.show_file(fix, f) or ""
            for i, line in enumerate(src.splitlines(), 1):
                if pat.search(line) and normalize(line) not in scope.guard_lines:
                    key = (f, i)
                    if key not in seen:
                        seen.add(key)
                        hits.append(f"{f}:{i}: {line.strip()}  [pattern: {name}(]")
    return hits[:30]


def create_contract(repo_path: str, fix: str, advisory: str, advisory_text: str | None,
                    model: ModelClient, run_tests: bool = True) -> Contract:
    repo = Repo(Path(repo_path))
    fix_full = repo.rev_parse(fix)
    parent = repo.parent(fix_full)
    diff, files = _source_diff(repo, fix_full)
    if not files:
        raise SystemExit(f"no source files changed in {fix}")
    note_path, note_text = load_advisory(repo, fix_full, advisory, advisory_text)
    scope, removed_only = build_scope(repo, fix_full, diff, files)
    glob = _lang_glob(files)
    evidence: list[Evidence] = []

    # Tier 2: the guard is present at the fix and absent at the parent.
    present_fix, absent_fix = structural_check(repo, fix_full, scope)
    present_parent, _ = structural_check(repo, parent, scope)
    evidence.append(Evidence(Tier.STRUCTURAL, "guard_lines",
                             f"{len(present_fix)}/{len(scope.guard_lines)} guard lines present at fix; "
                             f"{len(present_parent)} of them already present at parent (should be 0).",
                             {"present_at_fix": present_fix, "absent_at_fix": absent_fix,
                              "present_at_parent": present_parent}))
    # Tier 3: removed (vulnerable) lines are gone at the fix.
    corpus_fix = "\n".join(normalize(l) for f in files for l in (repo.show_file(fix_full, f) or "").splitlines())
    still = [r for r in removed_only if r in corpus_fix]
    evidence.append(Evidence(Tier.RULE, "removed_lines_absent",
                             f"{len(removed_only)} removed lines recorded; {len(still)} still present at fix.",
                             {"removed_lines": removed_only, "still_present": still}))

    # Tier 1: extracted regression test, run on parent (must fail) and fix (must pass).
    reg_path: str | None = None
    reg_reason: str | None = None
    spec = testrun.extract_test_ids(repo, fix_full) if glob == "*.py" else None
    if spec is None:
        reg_reason = "no test changes found in the fix commit to extract from" if glob == "*.py" else \
            "non-Python target: build/test out of scope (tiers 2-4 only)"
        evidence.append(Evidence(Tier.EXECUTED, "regression_test", f"not produced: {reg_reason}"))
    elif not run_tests:
        reg_reason = "test extraction succeeded but execution was skipped (--no-tests)"
        evidence.append(Evidence(Tier.EXECUTED, "regression_test", reg_reason, asdict(spec)))
    else:
        on_parent = testrun.run_spec(repo, parent, spec)
        on_fix = testrun.run_spec(repo, fix_full, spec)
        detail = {"spec": asdict(spec), "parent": asdict(on_parent), "fix": asdict(on_fix)}
        # Acceptance rule: the test must NOT pass on the parent (fail, or error such as AttributeError
        # on a symbol the fix introduces) and MUST pass on the fix. The parent outcome kind is recorded.
        if on_parent.outcome in ("fail", "error") and on_fix.outcome == "pass":
            TESTS_DIR.mkdir(parents=True, exist_ok=True)
            reg_path = str(TESTS_DIR / f"{advisory}_regression.json")
            Path(reg_path).write_text(json.dumps(asdict(spec), indent=2) + "\n")
            evidence.append(Evidence(Tier.EXECUTED, "regression_test",
                                     f"extracted test(s) {spec.test_ids}: {on_parent.outcome.upper()} on parent {parent[:10]} "
                                     f"({on_parent.summary}), PASS on fix {fix_full[:10]}.", detail))
        else:
            reg_reason = (f"extracted test did not behave as a regression test: parent={on_parent.outcome} "
                          f"({on_parent.summary}), fix={on_fix.outcome} ({on_fix.summary}); discarded")
            evidence.append(Evidence(Tier.EXECUTED, "regression_test", reg_reason, detail))

    # Sibling check: grep for the pre-fix pattern elsewhere in scope at fix time.
    hits = sibling_grep(repo, fix_full, removed_only, scope, glob)
    sibling = SiblingCheck(checked=True, similar_patterns=hits, covered=None,
                           note="grep-based: occurrences of the removed lines' call patterns in scope files "
                                "and one-hop callers at fix time, excluding the fixed lines themselves. "
                                "Coverage judgement requires tier 4.")

    # Tier 4: property statement + sibling judgement + uncertainty.
    vulnerability = note_text.split("\n\n")[1].strip() if "\n\n" in note_text else note_text
    prop = f"[template] The change introduced by {fix_full[:10]} in {', '.join(scope.functions) or ', '.join(files)} remains in effect."
    uncertainty = "Property statement is a template (no model available); structural checks compare normalized source lines only."
    user = (f"ADVISORY ({advisory}, from {note_path}):\n{note_text}\n\n"
            f"FIX COMMIT {fix_full[:10]}: {repo.subject(fix_full)}\n\nDIFF (source files only):\n{diff[:12000]}\n\n"
            f"DERIVED SCOPE:\n{json.dumps(asdict(scope), indent=1)[:4000]}\n\n"
            f"SIBLING GREP HITS (pre-fix patterns elsewhere in scope at fix time):\n" + ("\n".join(hits) or "(none)"))
    res = model.call("create", advisory, fix_full, SYSTEM_CREATE, user)
    if res is None:
        evidence.append(Evidence(Tier.MODEL, "property_derivation", f"not attempted: {model.unavailable_reason()}"))
    elif res["parsed"] is None:
        evidence.append(Evidence(Tier.MODEL, "property_derivation", "model reply was not parseable JSON; template used",
                                 {"model_reply_verbatim": res["text"]}))
    else:
        p = res["parsed"]
        vulnerability = p.get("vulnerability", vulnerability)
        prop = p.get("property", prop)
        uncertainty = p.get("uncertainty", uncertainty)
        sib = p.get("sibling") or {}
        sibling.covered = sib.get("covered")
        sibling.note += " MODEL: " + str(sib.get("note", ""))
        evidence.append(Evidence(Tier.MODEL, "property_derivation",
                                 "model-stated property and sibling judgement (verbatim reply in data)",
                                 {"model_reply_verbatim": res["text"], "model": res["usage"]["model"],
                                  "guard_summary": p.get("guard_summary")}))

    c = Contract(id=advisory, advisory=advisory, fix_commit=fix_full, target_repo=str(Path(repo_path).name),
                 vulnerability=vulnerability, property=prop, scope=scope, evidence_at_creation=evidence,
                 regression_test=reg_path, regression_test_reason=reg_reason, sibling_check=sibling,
                 uncertainty=uncertainty, parent_commit=parent, fix_subject=repo.subject(fix_full),
                 created_from_note=note_path)
    c.removed_lines = removed_only
    return c


def create_command(args) -> int:
    model = ModelClient(args.model, disabled=args.no_model)
    c = create_contract(args.repo, args.fix, args.advisory, args.advisory_text, model,
                        run_tests=not getattr(args, "no_tests", False))
    p = c.save()
    print(f"wrote {p}")
    return 0
