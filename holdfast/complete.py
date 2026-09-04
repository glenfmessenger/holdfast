"""`holdfast complete`: value-flow completeness check at the fix commit.

Question: does the value this fix protects still flow to a consumer the fix did not reach?
Context is deliberately wider than the sibling check's one-hop caller rule: every source file at
the fix commit that references the fix's functions, guard symbols, or the value's variable names,
ranked by reference count and capped at 25 files (excerpts, not whole files).
Own budget: 12 tier-4 calls for the whole exercise, on top of the 150 already logged.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict
from pathlib import Path

from .gitutil import Repo
from .model import ModelClient, CALL_LOG
from .models import Contract
from .scope import is_source, GENERIC_NAMES

EXERCISE_CAP = 12
MAX_FILES = 25
MAX_CHARS = 90_000
OUT_DIR = Path("results/completeness")

SYSTEM = """You are checking whether a security fix is COMPLETE at the moment it was merged.
You are given: the remediation contract (property, vulnerability, the guard the fix introduced),
the fix diff, and excerpts from every file in the repository at the fix commit that references the
fixed functions, the guard symbols, or the protected value's variable names.

Step 1: state the PROTECTED VALUE as one thing (e.g. "the client-supplied upload filename from
Content-Disposition"). If it cannot be stated as a single value, set "protected_value" to null and
explain in "value_note".
Step 2: list every CONSUMER of that value you can see in the excerpts -- places where the value is
used in a way the vulnerability concerns (filesystem path, SQL, regex over unbounded input, ...).
For each, decide whether the fix covers it (the guard is applied on that path) or not.

Reply with ONE JSON object:
{
  "protected_value": string|null,
  "value_note": string,
  "uncovered": [{"file": str, "function": str, "lines": str, "reason": str, "confidence": "low"|"medium"|"high"}],
  "covered":   [{"file": str, "function": str, "reason": str}],
  "context_sufficient": true|false,
  "context_note": string
}
Base every entry on lines you were shown; quote them in "lines". Do not speculate about files you
were not shown. Describe what you saw as evidence; do not claim certainty beyond it."""


def _symbols(c: Contract) -> tuple[list[str], list[str]]:
    fns = [f.split("::")[-1].split(".")[-1] for f in c.scope.functions]
    syms = [s for s in c.scope.symbols if len(s) >= 5 and s.lower() not in GENERIC_NAMES]
    vars_ = []
    for g in c.scope.guard_lines:
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=[^=]", g)
        if m and len(m.group(1)) >= 5 and m.group(1).lower() not in GENERIC_NAMES:
            vars_.append(m.group(1))
    names = list(dict.fromkeys(fns + syms))
    return [n for n in names if len(n) >= 5 and n.lower() not in GENERIC_NAMES], list(dict.fromkeys(vars_))


def gather_context(repo: Repo, fix: str, names: list[str], glob: str) -> tuple[list[tuple[str, int]], list[tuple[str, int]], str, bool]:
    counts: dict[str, int] = {}
    for n in names:
        r = subprocess.run(["git", "-C", str(repo.path), "grep", "-c", "-w", "-e", n, fix, "--", glob],
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            _, path, cnt = line.rsplit(":", 2)
            if is_source(path):
                counts[path] = counts.get(path, 0) + int(cnt)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    chosen, excluded = ranked[:MAX_FILES], ranked[MAX_FILES:]
    pat = re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b")
    parts, truncated = [], False
    for path, _ in chosen:
        src = repo.show_file(fix, path) or ""
        lines = src.splitlines()
        hit = [i for i, l in enumerate(lines) if pat.search(l)]
        keep = set()
        for i in hit:
            keep.update(range(max(0, i - 12), min(len(lines), i + 13)))
        seg, prev = [], None
        for i in sorted(keep):
            if prev is not None and i != prev + 1:
                seg.append("   ...")
            seg.append(f"{i+1:5d}: {lines[i]}")
            prev = i
        parts.append(f"### {path} @ {fix[:10]}\n" + "\n".join(seg))
    ctx = "\n\n".join(parts)
    if len(ctx) > MAX_CHARS:
        ctx, truncated = ctx[:MAX_CHARS] + "\n[TRUNCATED]", True
    return chosen, excluded, ctx, truncated


def exercise_calls() -> int:
    if not CALL_LOG.exists():
        return 0
    return sum(1 for l in CALL_LOG.read_text().splitlines() if l.strip() and json.loads(l).get("purpose") == "complete")


def complete_contract(c: Contract, repo: Repo, model: ModelClient) -> dict:
    fix = c.fix_commit
    glob = "*.py" if any(f.endswith(".py") for f in c.scope.files) else "*.[ch]"
    names, vars_ = _symbols(c)
    chosen, excluded, ctx, truncated = gather_context(repo, fix, names + vars_, glob)
    diff = repo.commit_diff(fix, "--", *c.scope.files)
    result = {"contract": c.id, "fix_commit": fix, "search_symbols": names, "value_variables": vars_,
              "files_in_context": chosen, "files_excluded_by_cap": excluded, "context_truncated": truncated,
              "verdict": None, "protected_value": None, "uncovered": [], "covered": [], "note": ""}
    if exercise_calls() >= EXERCISE_CAP:
        result.update(verdict="UNVERIFIABLE", note=f"exercise budget of {EXERCISE_CAP} calls exhausted")
        return result
    user = (f"CONTRACT {c.id} (fix {fix[:10]}: {c.fix_subject})\nVULNERABILITY: {c.vulnerability}\nPROPERTY: {c.property}\n"
            f"GUARD LINES:\n" + "\n".join(f"  {g}" for g in c.scope.guard_lines) +
            f"\nPRE-FIX LINES DELETED:\n" + "\n".join(f"  {r}" for r in c.removed_lines) +
            f"\n\nFIX DIFF (scope files):\n{diff[:12000]}\n\n"
            f"FILES REFERENCING {names + vars_} AT THE FIX COMMIT ({len(chosen)} of {len(chosen)+len(excluded)}; "
            f"excluded by cap: {[p for p, _ in excluded]}):\n\n{ctx}")
    res = model.call("complete", c.id, fix, SYSTEM, user)
    if res is None:
        result.update(verdict="UNVERIFIABLE", note=f"model unavailable: {model.unavailable_reason()}")
        return result
    result["model_reply_verbatim"] = res["text"]
    p = res["parsed"]
    if p is None:
        result.update(verdict="UNVERIFIABLE", note="model reply not parseable as JSON")
        return result
    result["protected_value"] = p.get("protected_value")
    result["value_note"] = p.get("value_note", "")
    result["uncovered"] = p.get("uncovered") or []
    result["covered"] = p.get("covered") or []
    result["context_sufficient"] = p.get("context_sufficient")
    result["context_note"] = p.get("context_note", "")
    if not p.get("protected_value"):
        result.update(verdict="UNVERIFIABLE", note="protected value could not be stated as a single thing: " + str(p.get("value_note", "")))
    elif truncated and p.get("context_sufficient") is False:
        result.update(verdict="UNVERIFIABLE", note="context truncated below what the model said it needed")
    elif any(u.get("confidence") in ("medium", "high") for u in result["uncovered"]):
        result["verdict"] = "INCOMPLETE"
    else:
        result["verdict"] = "COMPLETE"
    return result


def complete_command(args) -> int:
    c = Contract.load(args.contract)
    repo = Repo(Path(args.repo))
    # Own budget: the run-wide cap (150) is already spent; allow exactly EXERCISE_CAP more, all logged as before.
    model = ModelClient(args.model, disabled=args.no_model, cap=150 + EXERCISE_CAP)
    r = complete_contract(c, repo, model)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{c.id}.json"
    out.write_text(json.dumps(r, indent=2) + "\n")
    print(f"{c.id}: {r['verdict']} | value: {r['protected_value']} | uncovered: "
          f"{[(u.get('file'), u.get('confidence')) for u in r['uncovered']]} | files: {len(r['files_in_context'])} (+{len(r['files_excluded_by_cap'])} excluded)")
    return 0
