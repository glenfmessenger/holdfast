#!/bin/sh
# Build every contract in contracts/targets.json. Idempotent; re-running overwrites.
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY - <<'PYEOF'
import json, subprocess, sys, time
t = json.load(open("contracts/targets.json"))
jobs = [(t["django"]["repo"], c) for c in t["django"]["contracts"]] + [(t["openssh"]["repo"], c) for c in t["openssh"]["contracts"]]
for repo, c in jobs:
    if c["advisory"] == "CVE-2021-28658":
        continue  # built by hand earlier with the model
    cmd = [".venv/bin/holdfast", "create", "--repo", repo, "--fix", c["fix"], "--advisory", c["advisory"]]
    if c.get("advisory_text"):
        cmd += ["--advisory-text", c["advisory_text"]]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    status = "ok" if r.returncode == 0 else "FAILED"
    print(f"{c['advisory']} {c['fix']}: {status} ({time.time()-t0:.0f}s)", flush=True)
    if r.returncode != 0:
        print(r.stderr[-1500:], flush=True)
PYEOF
