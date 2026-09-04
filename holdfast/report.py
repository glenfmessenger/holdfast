"""`holdfast report`: Markdown summary of every verdict, per contract over time."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .models import load_all_verdicts, Tier

SHOWCASE = Path("results/showcase.json")  # hand-written pointers to the four showcase cases


def render_report(vs, showcase_path: Path = SHOWCASE) -> str:
    by_c: dict[str, list] = {}
    for v in vs:
        by_c.setdefault(v.contract_id, []).append(v)
    out = ["# Holdfast report", ""]
    out.append(f"{len(vs)} verdicts across {len(by_c)} contracts. Generated from `results/verdicts/`.")
    out.append("")
    # counts
    st = Counter(v.status for v in vs)
    tiers = Counter(v.tier for v in vs)
    model_only = [v for v in vs if v.model_only]
    out.append("## Counts")
    out.append("")
    out.append("| status | n |\n|---|---|")
    for k, n in sorted(st.items()):
        out.append(f"| {k} | {n} |")
    out.append("")
    out.append("| deciding tier | n |\n|---|---|")
    for k, n in sorted(tiers.items()):
        out.append(f"| {k} {Tier(k).name} | {n} |")
    out.append("")
    out.append(f"HELD decided by tier 4 only (model-only): **{sum(1 for v in model_only if v.status == 'HELD')}** "
               f"of {st.get('HELD', 0)} HELD verdicts. All model-only verdicts: {len(model_only)}.")
    dis = [v for v in vs if v.tier_disagreement]
    out.append(f"Tier disagreements recorded (model vs tiers 1-3): {len(dis)}.")
    out.append("")
    if showcase_path and showcase_path.exists():
        sc = json.loads(showcase_path.read_text())
        out.append("## Showcase cases")
        out.append("")
        for k, item in sc.items():
            out.append(f"**{k}. {item['title']}** — {item['summary']}")
            for f in item.get("files", []):
                out.append(f"  - `{f}`")
            out.append("")
    out.append("## Per contract")
    out.append("")
    for cid, lst in sorted(by_c.items()):
        lst.sort(key=lambda v: (v.commit_date, v.commit))
        note = lst[0].walk_note.split(";")[0] if lst else ""
        sampled = " (sampled)" if any(v.sampled for v in lst) else ""
        out.append(f"### {cid}{sampled}")
        out.append("")
        out.append(f"_{note}_")
        out.append("")
        out.append("| date | commit | status | tier | conf | subject |\n|---|---|---|---|---|---|")
        for v in lst:
            flag = " ⚠" if v.tier_disagreement else ""
            out.append(f"| {v.commit_date} | `{v.commit[:10]}` | {v.status}{flag} | {v.tier} | {v.confidence} | {v.commit_subject[:70].replace('|', '/')} |")
        out.append("")
    return "\n".join(out) + "\n"


def report_command(args) -> int:
    vs = load_all_verdicts()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(render_report(vs))
    print(f"wrote {args.out}: {len(vs)} verdicts, {len({v.contract_id for v in vs})} contracts")
    return 0
