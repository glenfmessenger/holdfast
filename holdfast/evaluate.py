"""`holdfast eval`: precision/recall for REGRESSED detection against hand labels, with Wilson 95% CIs."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .models import load_all_verdicts

POSITIVE = {"REGRESSED"}          # what counts as "the tool raised an alarm"
NEGATIVE_OK = {"HELD", "MOVED"}   # ground-truth statuses that mean "no regression"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def fmt_ci(k, n):
    if n == 0:
        return "n/a (0 cases)"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k/n:.2f}  [Wilson 95%: {lo:.2f}, {hi:.2f}]"


def eval_command(args) -> int:
    labels = json.loads(Path(args.labels).read_text())
    vs = {(v.contract_id, v.commit[:10]): v for v in load_all_verdicts()}
    rows = []
    tp = fp = fn = tn = 0
    missing = []
    false_resurrections = []   # labelled HELD/MOVED, tool said REGRESSED
    misses = []                # labelled REGRESSED, tool did not say REGRESSED
    exact = 0
    model_only_dep = 0
    for p in labels["pairs"]:
        key = (p["contract"], p["commit"][:10])
        v = vs.get(key)
        if v is None:
            missing.append(p)
            rows.append((p["contract"], p["commit"][:10], p["expected"], "(not walked)", "-", ""))
            continue
        got = v.status
        exp = p["expected"]
        if v.model_only:
            model_only_dep += 1
        if got == exp:
            exact += 1
        alarm = got in POSITIVE
        truth = exp in POSITIVE
        if alarm and truth:
            tp += 1
        elif alarm and not truth:
            fp += 1
            false_resurrections.append((p, v))
        elif not alarm and truth:
            fn += 1
            misses.append((p, v))
        else:
            tn += 1
        rows.append((p["contract"], p["commit"][:10], exp, got, f"t{v.tier}" + ("*" if v.model_only else ""),
                     "✓" if got == exp else ("~" if (got in NEGATIVE_OK and exp in NEGATIVE_OK) else "✗")))
    n = len(labels["pairs"]) - len(missing)
    out = ["# Holdfast eval", ""]
    out.append(f"Labels: `{args.labels}` (written {labels.get('_written','?')}, before walks). "
               f"{len(labels['pairs'])} pairs; {n} evaluated, {len(missing)} not walked.")
    out.append("")
    out.append("## REGRESSED detection")
    out.append("")
    out.append(f"- Precision: {fmt_ci(tp, tp + fp)}")
    out.append(f"- Recall:    {fmt_ci(tp, tp + fn)}")
    out.append(f"- Exact status agreement (HELD vs MOVED distinguished): {fmt_ci(exact, n)}")
    out.append(f"- Confusion: TP={tp} FP={fp} FN={fn} TN={tn}")
    out.append(f"- Verdicts on labelled pairs that depended on tier 4 only: {model_only_dep}/{n}")
    out.append("")
    out.append("## False resurrections (labelled no-regression, tool said REGRESSED)")
    out.append("")
    for p, v in false_resurrections or []:
        out.append(f"- **{p['contract']} @ {p['commit'][:10]}** (tier {v.tier}): {v.rationale[:300]}")
    if not false_resurrections:
        out.append("- none")
    out.append("")
    out.append("## Misses (labelled REGRESSED, tool did not say REGRESSED)")
    out.append("")
    for p, v in misses or []:
        out.append(f"- **{p['contract']} @ {p['commit'][:10]}**: tool said {v.status} (tier {v.tier}). {v.rationale[:300]}")
    if not misses:
        out.append("- none")
    out.append("")
    out.append("## Contract-level expectations (sibling check at creation)")
    out.append("")
    for ce in labels.get("contract_expectations", []):
        cp = Path("contracts") / f"{ce['contract']}.json"
        got = "?"
        if cp.exists():
            c = json.loads(cp.read_text())
            cov = c["sibling_check"].get("covered")
            got = "INCOMPLETE_AT_MERGE flagged" if cov is False else ("not flagged (covered=%s)" % cov)
        hit = "✓" if (ce["expected_sibling_check"] == "INCOMPLETE_AT_MERGE" and got.startswith("INCOMPLETE")) else "✗"
        out.append(f"- {hit} **{ce['contract']}**: expected {ce['expected_sibling_check']}; tool: {got}. "
                   f"Pre-registered as {'catchable' if ce.get('tool_expected_to_catch') else 'an expected miss'}.")
    out.append("")
    out.append("## All labelled pairs")
    out.append("")
    out.append("| contract | commit | expected | got | tier | |\n|---|---|---|---|---|---|")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    out.append("")
    out.append("`t4*` = model-only verdict. `~` = HELD/MOVED swapped (no alarm either way).")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(out) + "\n")
    print("\n".join(out[:12]))
    print(f"wrote {args.out}")
    return 0
