# Holdfast

## What it does

Holdfast turns a security fix into a **remediation contract**: the property the fix establishes, its scope, and tiered
evidence. It re-verifies that property on every later commit touching the scope, one verdict per fix per commit: HELD,
REGRESSED, INCOMPLETE_AT_MERGE, MOVED or UNVERIFIABLE. Tiers never blend: executed test (1), guard lines (2),
resurrection rule (3), model judgement (4). Run on 20 Django CVE fixes and the OpenSSH fix behind CVE-2024-6387.

## How to run it

```sh
uv venv .venv --python 3.13 && uv pip install -e ".[dev]" --python .venv/bin/python
git clone https://github.com/django/django.git .targets/django            # targets are gitignored, never vendored
git clone https://github.com/openssh/openssh-portable.git .targets/openssh-portable
uv python install 3.9 3.11                                                 # old Django does not import on 3.13
uv venv .targets/venv39 --python 3.9  && uv pip install --python .targets/venv39/bin/python asgiref pytz sqlparse
uv venv .targets/venv311 --python 3.11 && uv pip install --python .targets/venv311/bin/python asgiref sqlparse

export ANTHROPIC_API_KEY=sk-ant-...        # tier 4. Without it: tier 4 is recorded as "not attempted: no-api-key",
                                            # properties are templates, and inconclusive walks end UNVERIFIABLE.
.venv/bin/holdfast create --repo .targets/django --fix d4d800ca1a --advisory CVE-2021-28658
.venv/bin/holdfast walk   --contract CVE-2021-28658 --repo .targets/django --range d4d800ca1a..8d9901c961
.venv/bin/holdfast report                   # -> results/report.md
.venv/bin/holdfast eval --labels results/labels.json   # -> results/eval.md
./scripts/create_all.sh && ./scripts/walk_all.sh       # everything in contracts/targets.json
```

`--model` overrides `claude-sonnet-5`; tier 4 is capped at 150 logged calls per run, then UNVERIFIABLE ("budget").

## What's real vs stubbed

| Capability | Status | Detail |
|---|---|---|
| Contract from fix diff + advisory | working | Scope (files, enclosing functions via `ast`, symbols, guard lines, deleted lines, one-hop callers via `git grep`) from the diff; advisory text pulled from the Django release note at the fix commit. |
| Property statement as an invariant | working (model) | Tier-4 call at create time; verbatim reply stored. Without a key the property is a labelled template. |
| Regression tests | **extracted from fix commit, not generated** | The fix's own test ids (methods whose lines the fix touched) run against the parent (must not pass) and the fix (must pass), with the fix's test files overlaid. 13/20 Django contracts kept one; 7 discarded with the reason recorded. No target test source is copied into this repo. |
| Tier 1 EXECUTED in walks | working | Same extracted test run at each later commit in a worktree. Silently degrades: once the frozen test file stops importing, the outcome is `error` and evaluation falls to tier 2. |
| Tier 2 STRUCTURAL | working, brittle | Whitespace-normalised guard-line presence in scope files; rename following via `git log -M`; MOVED when absent lines are found verbatim in other files; scope self-heals to the new file. Blind to quote-style changes and to any rewrite of a guard line, permanently. |
| Tier 3 RULE | working, one rule | "A line the fix deleted reappears in scope" → REGRESSED. Fires falsely on generic lines (see Where it breaks). |
| Tier 4 MODEL | working | `claude-sonnet-5` via the `anthropic` SDK; budget cap, per-call log, rationale verbatim in the verdict; disagreements with tiers 1–3 recorded, not reconciled. |
| Sibling check | partial | grep for the deleted lines' call patterns in scope + callers at fix time, plus a model judgement over those hits. Cannot see sibling consumers that are not callers. |
| INCOMPLETE_AT_MERGE | partial | Emitted only if the model flags it at create (`covered: false`) or at walk time. Never emitted structurally. |
| Sampling over the 40-commit cap | working | Even sampling; labelled commits force-included; evaluated/skipped lists in every verdict of that contract. |
| `report` / `eval` (Wilson CIs) | working | Markdown; eval scores REGRESSED detection and exact-status agreement against pre-registered labels. |
| OpenSSH bolt-on | working, tiers 2–4 only | C preprocessor guards treated as guard lines; no build or test. |
| Tier 5 HUMAN | not attempted | Reserved. |
| Contract re-anchoring after a HELD verdict | not attempted | See "What I'd build next". |

## Results

Across all 392 verdicts, 1 of 23 REGRESSED is a real regression (OpenSSH); the other 22 are false alarms.
21 contracts, 150 tier-4 calls (cap hit; 8 UNVERIFIABLE "budget"). 356 HELD, 23 REGRESSED, 1 MOVED, 12 UNVERIFIABLE;
deciding tier 134 / 127 / 8 / 123. **HELD decided by tier 4 alone: 108 of 356.** Tables: `results/report.md`, `results/eval.md`.

Labelled eval, 25 pairs pre-registered before any walk (24 walked): REGRESSED precision 1/1, recall 1/1,
Wilson 95% [0.21, 1.00]; exact-status agreement 20/24 = 0.83 [0.64, 0.93]; 9/24 model-only. n is tiny; the
interval says so. All 22 false REGRESSED occurred on unlabelled pairs: the matcher failed where nobody had
predicted it would.

1. **Held through a real refactor**, tier 1: `results/verdicts/CVE-2021-28658/34e2148fc7.json`
2. **Regression caught**, OpenSSH, tier 4: `results/verdicts/CVE-2006-5051/752250caab.json`
3. **False resurrection rejected**, guard lines all rewritten, tier 4: `results/verdicts/CVE-2021-33571/bdf3e156b4.json`
4. **The miss**: `results/verdicts/CVE-2022-34265/877c800f25.json`

## Where it breaks

Root cause: the contract's scope is defined structurally (files, lines, one-hop callers) while the property lives
semantically (data flow, architecture). Failure modes by tier:

- **Tier 1, test drift and property/behaviour mismatch.** CVE-2019-14232, 2 × REGRESSED: Truncator rewritten on HTMLParser; the test fails on ellipsis placement, not the DoS property. CVE-2020-24583, 3 × REGRESSED: the frozen 2020 test asserts a file mode Django later changed on purpose. Three relocations called HELD rather than MOVED because the test still passed.
- **Tier 3, line-level rule.** CVE-2019-12308, 8 × REGRESSED: the deleted line `def __init__(self, attrs=None):` reappeared in an unrelated new class.
- **Tier 4, scope blindness.** The miss: `877c800f25` replaced the CVE-2022-34265 whitelist with parameterized SQL in each backend. The model saw only the scope-file diff (whitelist deleted) and said REGRESSED, high confidence, nine commits running. Also CVE-2019-14232, 4 × UNVERIFIABLE: module-level constants have no function to show.
- **Coverage.** CVE-2021-45452 at `fe4a0bbe20` never visited: `storage/base.py` was born by copy, not rename.
- **Sibling check.** 3 of 4 pre-registered INCOMPLETE_AT_MERGE cases missed (sibling consumers are not callers); the one hit flagged the wrong regex.

Base rate: across 20 Django fixes, no silent regression of a correct fix was observed in the walked history; the one
real REGRESSED is OpenSSH. Five of the 20 Django fixes were revisited by a later CVE in the same function; at contract
creation the sibling check flagged one, for a reason unrelated to the later CVE. Incompleteness at merge is the more
common failure in this sample and the one the current scope definition cannot see.

## What I'd build next

1. **Re-anchor contracts on HELD**; today one rewrite blinds tier 2 forever.
2. **Scope from data flow rather than call graph, with copy detection as well as rename detection.**
3. **Separate property tests from behaviour tests.**
