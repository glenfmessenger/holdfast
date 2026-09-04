# Holdfast

## What Holdfast does

Holdfast is a merge-time completeness check plus an evidence-tiered remediation record, inside Claude Security: the
completeness and durability layer on top of Claude Security's remediation. It is for AppSec and engineering teams
already merging Claude-generated patches. It runs on the plugin's own artifacts: `/claude-security` scan, then Suggest patches, then `/holdfast` on a patched
finding, which asks whether the value the fix protects still flows to a consumer the fix did not reach, appends any
derived findings to the report in the plugin's schema, and writes a record of the property, the evidence by tier,
and what could not be verified. Derived findings go back through Suggest patches, one PR per patch.

The finding behind it: fixes are rarely undone and often incomplete. Of 20 fixes studied, 5 were revisited by a later
CVE in the same function; none silently regressed in the walked, sampled history. The v1 stance is low recall and zero
false flags, UNVERIFIABLE over guessing, evidence never blended: in the F1 record, the cannot-verify field described
the consumer the verdict missed. Continuous re-verification of the property across
refactoring is the six-month direction; the walk below is the experiment that showed why.

## What the prototype found

Fixes were rarely undone and often incomplete at merge. Continuous re-verification is not ready: 1 real regression in
23 flagged: one wall (scope defined structurally while the property lives semantically) and three bugs left untuned, see
[results/eval.md](results/eval.md). The completeness check is precise and low-recall on a small pre-registered set:
1 hit, 3 misses and 0 false flags on 6 contracts, see [results/completeness.md](results/completeness.md).

## See it without running anything

**Two PRs on a fork, with their roles.**

- **What the tool produced:** [PR #2](https://github.com/glenfmessenger/django/pull/2), opened by `holdfast close` on the F1 report (hand-built in the plugin's
  schema; the plugin did not produce it). A fix commit, a record commit, cannot-verify stated, and no sibling patches,
  because the query judged `uploadedfile.py` covered. Kept test: null in the demo because the hand-built patch carries no
  tests; in the real flow it comes from the patch's own test changes when the fix includes them, as Django's actual
  CVE-2021-28658 commit did.
- **Target output:** [PR #1](https://github.com/glenfmessenger/django/pull/1), what the corrected query would produce: the same fix, then patches for the two
  sibling consumers, commits 2–3 hand-adapted from Django's later CVE-2021-31542 fix, and the record.

The distance between the two PRs is the "not possible yet" section, rendered.

### Example: an incomplete fix (Django, CVE-2021-28658)

Django's fix `d4d800ca1a` moved HTML-unescaping ahead of path stripping in
`MultiPartParser`; the contract's extracted test fails on the parent and passes on the fix
([contract](contracts/CVE-2021-28658.json)). The completeness check was then handed every file referencing the fix's
symbols, saw `django/core/files/uploadedfile.py`, and judged its bare `os.path.basename` "a separate, pre-existing
defense-in-depth layer" because it did not know that pattern was the one the fix had just replaced; it returned COMPLETE
([result](results/completeness/CVE-2021-28658.json), [summary](results/completeness.md)). Django patched `UploadedFile`
and `FieldFile` four weeks later as CVE-2021-31542. What the tool should have produced is shown as a
[demo PR on a fork](https://github.com/glenfmessenger/django/pull/1): the fix, the two sibling patches adapted from Django's own later fix, and the remediation record.

### Example: a caught sibling (Django, CVE-2021-45452)

Asked the same question about `Storage.save()`, the check flagged
`django/contrib/staticfiles/storage.py` at medium confidence: staticfiles calls `_save()` directly, so the new
`validate_file_name` guard in `save()` never runs on that path
([result](results/completeness/CVE-2021-45452.json)). The file matched the
[pre-registered expectation](results/completeness_labels.json); the mechanism did not (I had pre-registered the
overridden-`generate_filename` route that became CVE-2024-39330).

### Example: a regression through a rename (OpenSSH, CVE-2024-6387)

Walking forward from the 2006 fix, the tool returned REGRESSED at `752250caab`,
where `sigdie` was renamed to `sshsigdie` and the `#ifdef DO_LOG_SAFE_IN_SIGHAND` guard dropped; the tier-4 rationale
names the rename ([verdict](results/verdicts/CVE-2006-5051/752250caab.json)), and the same stack produced 22 false
REGRESSED across Django ([eval](results/eval.md), [report](results/report.md)).

## Run the demo

`./demo` replays the three examples (create, walk, complete, report) from recorded model responses and recorded test
outcomes in about 8 seconds, with no API key. It writes only to `demo_out/`; nothing under `results/` is touched.

Prerequisite: the two target repositories must exist as full clones in `.targets/`. Either create them by hand:

```sh
git clone https://github.com/django/django.git .targets/django
git -C .targets/django checkout 8d9901c961                    # end of the walk window (2024-12-27)
git clone https://github.com/openssh/openssh-portable.git .targets/openssh-portable
git -C .targets/openssh-portable checkout 752250caab           # the regressing commit; anything at or after it works
./demo
```

or run `./demo` and let it clone them on first run: if `.targets/` is missing it prints what it is cloning and why
(full history is needed for the walks), clones both, checks out the commits above, and continues. The first-run
clone takes about 30 seconds and 400 MB (measured: 20 s, 412 MB); the replay itself takes about 8 seconds.


Then the plugin-side commands, on a report directory:

```sh
.venv/bin/holdfast integrate --report <CLAUDE-SECURITY-dir> --finding F1   # contract, completeness query, record, derived findings
.venv/bin/holdfast close     --report <CLAUDE-SECURITY-dir> --finding F1   # integrate, then branch + fix commit + record commit + PR
```

`close` creates a branch from the report's stamped revision, commits the patch (and the patch's test changes as a kept
test, when it has any) and the record, and opens a PR on your fork via `gh`; it requires `gh auth`, and nothing is
applied unless you choose close. Both need tier-4 calls: the budget is 150 for the walk plus 12 for the completeness
exercise, and both are fully used in the committed log, so a fresh call returns UNVERIFIABLE "budget". Raising it is a
flag (`--cap` on the model client, `EXERCISE_CAP` in `holdfast/complete.py`) and every call is recorded in
`results/model_calls.jsonl`.

## Inside Claude Security

The flow, end to end: `/claude-security` → **Scan codebase** → **Suggest patches** → **Close finding** (shipped here as
`/holdfast close`) → derived findings back through **Suggest patches** → one PR per patch. Close finding builds the
contract from the patch applied at the report's stamped revision, runs the completeness query, appends derived findings
`F<n>.1`, `F<n>.2` ... to the report's JSONL with a note each and a `derived_from` field, commits the patch and the
record (`.holdfast/records/F<n>.json`) on a branch from the stamped revision, and opens a PR on your fork. Holdfast
writes no patches; derived findings get theirs through Suggest patches. In the product, Close finding is the fourth
item in the `/claude-security` menu; the prototype ships it as a separate command because the plugin's menu isn't
extensible from outside.

```text
/claude-security
  1. Scan codebase
  2. Scan changes
  3. Suggest patches
  4. Close finding        (new)
```

The schema Holdfast reads and writes, and which fields were confirmed against the plugin source versus a real run, is in
`NOTES.md`. Demo path taken: **B**, a report hand-built in the plugin's schema; the plugin did not produce it
(`demo_artifacts/claude-security-path-b/`, see its `PROVENANCE.md`). Path A, the real plugin on the fork scoped to
`django/http/`, was attempted once in a separate session and did not run: the plugin's scan needs the Workflow tool,
which subagent sessions do not have, so no scan started. If path A runs and succeeds, the three provenance labels in this
README change; nothing else does.

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
| Close finding / open PR (`holdfast close`) | working | Branch from the stamped revision, fix commit, kept-test commit when the patch has tests, record commit, PR on the fork via `gh`. Demonstrated on the F1 report (hand-built in the plugin's schema; the plugin did not produce it). |
| Propose patches for derived findings | design; not prototyped | Derived findings go back through Suggest patches; Holdfast writes no patches. |
| Tier 5 HUMAN | not attempted | Reserved. |
| Contract re-anchoring after a HELD verdict | not attempted | See "What I'd build next". |

## Results

Across all 392 verdicts, 1 of 23 REGRESSED is a real regression (OpenSSH); the other 22 are false alarms.
21 contracts, 150 tier-4 calls (cap hit; 8 UNVERIFIABLE "budget"). 356 HELD, 23 REGRESSED, 1 MOVED, 12 UNVERIFIABLE;
deciding tier 134 / 127 / 8 / 123. **HELD decided by tier 4 alone: 108 of 356.** Tables: `results/report.md`, `results/eval.md`.

Labelled eval, 25 pairs pre-registered before any walk (24 walked): exact-status agreement 20/24 = 0.83
[Wilson 95%: 0.64, 0.93]; 9/24 model-only. n is tiny; the interval says so. All 22 false REGRESSED occurred on
unlabelled pairs: the matcher failed where nobody had predicted it would.

1. **Held through a real refactor**, tier 1: `results/verdicts/CVE-2021-28658/34e2148fc7.json`
2. **Regression caught**, OpenSSH, tier 4: `results/verdicts/CVE-2006-5051/752250caab.json`
3. **False resurrection rejected**, guard lines all rewritten, tier 4: `results/verdicts/CVE-2021-33571/bdf3e156b4.json`
4. **The miss**: `results/verdicts/CVE-2022-34265/877c800f25.json`

### Completeness check (value-flow query)

`holdfast complete` asks, at the fix commit, whether the protected value still flows to a consumer the fix did not
reach, with context widened to every file referencing the fix's symbols (cap 25). Pre-registered on six contracts:
1 of 4 INCOMPLETE cases caught (CVE-2021-45452, `django/contrib/staticfiles/storage.py` calling `_save()` directly),
both COMPLETE cases correct, no false flags. It missed CVE-2021-28658's siblings: it saw `django/core/files/uploadedfile.py`
and judged its bare `os.path.basename` a covering "defense-in-depth layer"; `django/db/models/fields/files.py` was
not flagged. Details: `results/completeness.md`.

## Where it breaks

Root cause: the contract's scope is defined structurally (files, lines, one-hop callers) while the property lives
semantically (data flow, architecture). The 22 false REGRESSED split into one wall and three bugs left untuned:

**(a) The wall: model scope-blindness (9).** `877c800f25` replaced the CVE-2022-34265 whitelist with parameterized SQL
in each backend. The model saw only the scope-file diff (whitelist deleted) and said REGRESSED, high confidence, nine
commits running. Also CVE-2019-14232, 4 × UNVERIFIABLE: module-level constants have no function to show.

**(b) Untuned mechanics, left in deliberately (13).**
- **Tier 3, line-level rule (8).** CVE-2019-12308: the deleted line `def __init__(self, attrs=None):` reappeared in an unrelated new class.
- **Tier 1, frozen-test drift and property/behaviour mismatch (5).** CVE-2019-14232, 2 × REGRESSED: Truncator rewritten on HTMLParser; the test fails on ellipsis placement, not the DoS property. CVE-2020-24583, 3 × REGRESSED: the frozen 2020 test asserts a file mode Django later changed on purpose. Three relocations called HELD rather than MOVED because the test still passed.
- **Coverage, copy-not-rename.** CVE-2021-45452 at `fe4a0bbe20` never visited: `storage/base.py` was born by copy, not rename.

Outside the 22: the sibling check missed 3 of 4 pre-registered INCOMPLETE_AT_MERGE cases (sibling consumers are not
callers); the one hit flagged the wrong regex.

Base rate: across 20 Django fixes, no silent regression of a correct fix was observed in the walked history; the one
real REGRESSED is OpenSSH. Five of the 20 Django fixes were revisited by a later CVE in the same function; at contract
creation the sibling check flagged one, for a reason unrelated to the later CVE. Incompleteness at merge is the more
common failure in this sample and the one the current scope definition cannot see.

## What I'd build next

1. **Re-anchor contracts on HELD**; today one rewrite blinds tier 2 forever.
2. **Scope from data flow rather than call graph, with copy detection as well as rename detection.**
3. **Separate property tests from behaviour tests.**

## Reproduce from scratch

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
