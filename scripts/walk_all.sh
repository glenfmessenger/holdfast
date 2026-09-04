#!/bin/sh
# Walk every contract over its pinned range. Labelled commits are force-included so even sampling
# never drops them (recorded in each verdict's walk_note). Never walks from HEAD.
set -e
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PYEOF'
import json, subprocess, time
t = json.load(open("contracts/targets.json"))
labels = json.load(open("results/labels.json"))
inc = {}
for p in labels["pairs"]:
    inc.setdefault(p["contract"], set()).add(p["commit"][:10])
jobs = []
for c in t["openssh"]["contracts"]:
    jobs.append((t["openssh"]["repo"], c["advisory"], c["walk_range"]))
end = t["django"]["walk_end"]
# contracts with labelled pairs first (budget priority), then the rest
dj = t["django"]["contracts"]
dj.sort(key=lambda c: (c["advisory"] not in inc, c["advisory"]))
for c in dj:
    if c["advisory"] == "CVE-2021-28658":
        continue  # already walked
    jobs.append((t["django"]["repo"], c["advisory"], f"{c['fix']}..{end}"))
for repo, cid, rng in jobs:
    cmd = [".venv/bin/holdfast", "walk", "--contract", cid, "--repo", repo, "--range", rng]
    if inc.get(cid):
        cmd += ["--include", ",".join(sorted(inc[cid]))]
    t0 = time.time()
    print(f"=== {cid} {rng}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout, flush=True)
    if r.returncode != 0:
        print("FAILED:", r.stderr[-2000:], flush=True)
    print(f"    ({time.time()-t0:.0f}s)", flush=True)
PYEOF
