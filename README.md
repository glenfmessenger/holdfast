# Holdfast

## What it does

Holdfast turns a security fix into a **remediation contract**: a durable record of the security property the fix
establishes, with evidence, scoped to the files and functions the property depends on. It then walks forward
through every later commit that touches that scope and re-verifies the property, producing a **verdict** per fix
per commit: HELD, REGRESSED, INCOMPLETE_AT_MERGE, MOVED or UNVERIFIABLE. Evidence is tiered and never blended:
an executed regression test (tier 1), presence of the guard lines the fix introduced (tier 2), a resurrection rule
(tier 3), or a model judgement over the contract and the diff (tier 4). The prototype was run on 20 Django CVE
fixes from 2019–2023 and one OpenSSH fix from 2006 whose 2020 regression became CVE-2024-6387 (regreSSHion).

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

`--model` overrides the default `claude-sonnet-5`. Tier-4 calls are capped at 150 per run and every call is logged
to `results/model_calls.jsonl`; past the cap, verdicts needing tier 4 are UNVERIFIABLE with reason "budget".
Walks are pinned to `--range`, only visit commits touching the contract's scope (following renames), run only
the fix's own test ids, and evaluate at most 40 commits per contract (even sampling, recorded in each verdict).

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

Run: 21 contracts, 392 verdicts, 150 tier-4 calls (the cap; 8 verdicts ended UNVERIFIABLE "budget").
Verdicts: 356 HELD, 23 REGRESSED, 1 MOVED, 12 UNVERIFIABLE. Deciding tier: 134 tier 1, 127 tier 2, 8 tier 3,
123 tier 4. **HELD (model-only): 108 of 356.** Full tables: `results/report.md`, `results/eval.md`.

Eval on 25 pre-registered pairs (24 walked): REGRESSED precision 1/1 and recall 1/1, Wilson 95% [0.21, 1.00];
exact-status agreement 20/24 = 0.83 [0.64, 0.93]; 9/24 pair verdicts were model-only. n is tiny and the
interval says so. Over the whole population, 1 of 23 REGRESSED verdicts is a true regression.

1. **Held through a real refactor** — CVE-2021-28658 at the cgi-module removal, tier 1: `results/verdicts/CVE-2021-28658/34e2148fc7.json`
2. **Regression caught** — OpenSSH regreSSHion commit, tier 4, rename named in the rationale: `results/verdicts/CVE-2006-5051/752250caab.json`
3. **False resurrection rejected** — CVE-2021-33571 with every guard line rewritten, tier 4: `results/verdicts/CVE-2021-33571/bdf3e156b4.json`
4. **The miss** — CVE-2022-34265, see below: `results/verdicts/CVE-2022-34265/877c800f25.json`

## Where it breaks

**The miss.** `877c800f25` replaced the CVE-2022-34265 whitelist with parameterized SQL in each backend. The model
saw only the scope-file diff (whitelist deleted) and said REGRESSED with high confidence, nine commits running.
The property survived by a different mechanism in different files. That is the problem in one sentence: a
security property is continuous across the codebase's evolution in a way that neither guard lines nor a
scope-restricted diff can follow.

Every other wrong verdict, by name:
- CVE-2019-12308, 8 × REGRESSED at tier 3 from `caf80cb41f`: the deleted line `def __init__(self, attrs=None):` reappeared in a new, unrelated widget class. The rule matches text, not identity.
- CVE-2019-14232, 2 × REGRESSED at tier 1 (`6ee37ada32`, `3cadeea077`): Truncator was rewritten on HTMLParser and the regexes deleted; the extracted test fails on ellipsis placement, not on the DoS property. The test encodes 2019 output, not the invariant. Same contract: 4 × UNVERIFIABLE because the guard is two module-level constants with no function to show the model.
- CVE-2020-24583, 3 × REGRESSED at tier 1 from `0b33a3abc2`: the frozen 2020 staticfiles test asserts a file mode Django later changed on purpose; Django's own test passes at that commit. Guard intact.
- CVE-2021-45452 at `fe4a0bbe20` (labelled HELD): never visited. `storage/base.py` was born by copy in the storage split, not by rename, so it never entered the scope.
- Sibling check: 3 of 4 pre-registered INCOMPLETE_AT_MERGE cases missed, including the one-hop-caller miss on CVE-2021-28658 (UploadedFile is a sibling consumer of the same untrusted name, not a caller). The one hit (CVE-2019-14232) flagged `re_tag`, not the regexes the 2023 CVE was actually about: right label, wrong reason.
- HELD vs MOVED: three storage/response relocations were called HELD at tier 1 because the test still passed. No alarm, but the contract never learned where its code went.

## What I'd build next

1. **Re-anchor contracts on HELD.** After a tier-1 or confirmed tier-4 HELD where guard lines changed, re-derive guard lines and scope from the new code. Today one rewrite blinds tier 2 forever and pushes every later commit to the model.
2. **Scope by data flow, not call graph.** Track the untrusted value (file name, lookup_name) to every consumer, including mechanism moves into other files. This would have covered the miss and the sibling-consumer gap.
3. **Distinguish property tests from behaviour tests.** Extract only assertions that exercise the advisory's input class; a test on ellipsis placement should never produce REGRESSED.
