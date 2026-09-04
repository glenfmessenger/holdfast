# Holdfast — working notes

Decisions and surprises, in the order they happened. For the writeup.

## 2026-09-03 — setup

- Target clones live in `.targets/` (gitignored). Nothing from Django or OpenSSH is vendored;
  contracts and verdicts reference commits by hash only.
- Django fix-commit convention confirmed on `main`: 50 commits whose subject begins
  `Fixed CVE-` between 2019-01-01 and 2024-12-31. Every one has a release note under
  `docs/releases/<version>.txt` with a `CVE-YYYY-NNNNN: <title>` section and a
  plain-language paragraph. That paragraph is the advisory text for each Contract.
- End of the pinned window on Django `main`: `8d9901c961` (2024-12-27). Walks never start
  from HEAD; `--range <fix>..8d9901c961`.
- Surprising: of the ~30 Python source files these 50 fixes touched, only one was ever
  renamed in the window: `django/core/files/storage.py` -> `django/core/files/storage/filesystem.py`
  at `032c09c414` (2022-11-10, storage split into a package). Django refactors mostly happen
  *inside* files, not by moving them. Rename-following matters for exactly the two
  storage contracts (CVE-2020-24583, CVE-2021-45452); "MOVED" for the rest will mean
  a function moved or was rewritten within a file.
- Several fixes are followed by a *second* CVE fix in the same function years later
  (Truncator: CVE-2019-14232 -> CVE-2023-43665; strip_tags: CVE-2019-14233 -> CVE-2024-53907;
  uri_to_iri: CVE-2019-14235 -> CVE-2023-41164; Accept-Language: CVE-2023-23969 -> CVE-2024-39614;
  Storage.save: CVE-2021-45452 -> CVE-2024-39330). These are natural candidates for
  "incomplete fix" verdicts — the later CVE is external evidence that the first property was
  not the whole story.
- OpenSSH (regreSSHion), from the Qualys advisory + repo history, not memory:
  - 2006 fix: `bb59814cd644f78e82df07d820ed00fa7a25e68a` (2006-08-19) adds
    `#ifdef DO_LOG_SAFE_IN_SIGHAND` around the syslog call in `sigdie()` in `log.c`.
  - 2020 regression: `752250caabda3dd24635503c4cd689b32a650794` (2020-10-16,
    "upstream: revised log infrastructure for OpenSSH") drops the guard. It *also* renames
    `sigdie` -> `sshsigdie` (with a `#define sigdie ssh_sigdie` shim in `log.h`), so the
    regressing commit is simultaneously a move and a regression. Good stress test.
  - 16 commits touch `log.c` between the two; under the 40-commit cap.

## 2026-09-03 — first contract (CVE-2021-28658)

- **API key is invalid.** `ANTHROPIC_API_KEY` is set (108 chars, `sk-ant-api...`) but the API
  returns 401 on `/v1/models`. Tier 4 is therefore "not attempted: api-key-invalid" for now, and
  the first contract's `property` is a template, not a model-stated invariant. The client now
  disables itself on a 401 instead of crashing, and does not count the failed call against the budget.
- **Regression tests are extracted, not synthesized.** `create` takes the test files the fix commit
  touched, finds test methods whose lines the fix added/modified (via `ast`), and runs exactly those
  ids: on the parent with the *fix commit's* test files overlaid (must fail) and on the fix (must pass).
  For CVE-2021-28658 that is 3 test ids; parent: 2 failures + 14 errors (the new
  `sanitize_file_name` method doesn't exist yet), fix: all ok. The spec is stored in
  `contracts/tests/<id>_regression.json` — no Django test source is copied into this repo.
- **Fixture-error policy.** Django's own `file_uploads/tests.py` at the fix commit double-removes
  MEDIA_ROOT (an `addCleanup` plus `tearDownClass`), so running the subset always ends with one
  tearDownClass error. Per-test outcomes are parsed from `-v2` output; setUpClass/tearDownClass
  errors are recorded in the summary but do not veto a pass. Test-method errors still do.
- **Interpreter choice.** Old Django doesn't import on Python 3.13 (`cgi` removed). `python_requires`
  at each commit picks `.targets/venv39` (>=3.6/3.8 era) or `.targets/venv311` (>=3.10 era).
  Bug found on the way: resolving the venv's `python` symlink escapes the venv; use the abspath.
- **Worktree bug.** `git -C repo worktree add <relative>` resolves the path relative to the repo,
  not the caller. Always pass absolute paths.
- **Sibling check is grep-only at the moment** (removed lines' call patterns in scope + one-hop
  callers). For CVE-2021-28658 it found nothing. The follow-up CVE-2021-31542 four weeks later
  says the same sanitation was missing in `UploadedFile` and `FieldFile` — `uploadedfile.py:42`
  had the same `os.path.basename(name)` pattern at fix time, but it is not a caller, so the
  one-hop rule never looks at it. Pre-registered as an expected miss in `results/labels.json`.
- CVE-2021-31542 also *rewrites* two of this contract's six guard lines (rfind/basename ->
  rsplit) while strengthening the property. Pre-registered as a false-resurrection trap:
  expected HELD, a REGRESSED verdict there is a miss.

## Scope definition

- The one-hop caller rule misses sibling consumers of the same untrusted value (e.g. `UploadedFile._set_name`
  for CVE-2021-28658), because security properties propagate along data flow rather than the call graph.
  Kept as-is deliberately; this is a core "not possible yet" finding.

## Final target set (confirmed 2026-09-03)

- Swap approved: #1 CVE-2019-6975 (numberformat) replaced by CVE-2023-31047 (`fb4c55d9ec`, multiple-file-upload
  validation bypass, `django/forms/widgets.py`). CVE-2020-7471 left out: its tests need PostgreSQL.
- Budget priority: contract property derivation (tier 4 at create) comes before walk verdicts. If the 150-call
  cap gets tight, walks go UNVERIFIABLE ("budget"), not contracts.

## 2026-09-03 — walks

- **Tier-1 acceptance rule** (set at create time, before any walk): the extracted test must NOT pass on the parent
  (assertion failure, or an error such as AttributeError on a symbol the fix introduces) and MUST pass on the fix.
  Parent outcome kind is recorded in the evidence. 13/20 Django contracts kept an executable test; the other 7 are
  recorded as discarded with the reason (test file errors on the fix commit when run as a subset, or the extracted
  ids don't discriminate). Not investigated further: a labelled stub beats a rabbit hole.
- **Sonnet 5 + max_tokens.** With `max_tokens=4000` the model's adaptive thinking consumed the whole budget and
  returned empty text (`stop_reason: max_tokens`) -> "unparseable" verdict. Raised to 16000. One call wasted; it is
  in `results/model_calls.jsonl` like every other call.
- **Once a guard line is rewritten, the structural tier is blind for the rest of the walk.** CVE-2021-31542
  (`0b79eb3691`) rewrote 2 of CVE-2021-28658's 6 guard lines while strengthening the property. Tier 1 handled that
  commit (the extracted test still passes), but from then on tier 2 permanently reports "4/6 present", and once the
  frozen 2021 test file stops importing (June 2022, `parse_header` removed) every later commit needs tier 4.
  This is the cost of a contract that never re-anchors. Deliberately NOT changed mid-run (it would be a design
  change: contracts would need to evolve after a HELD verdict). Listed under "what I'd build next".
- The model's property for CVE-2021-28658 pins `os.path.basename()` as "the final step". Three weeks later Django
  replaced it with `rsplit`. The model at walk time judged the rewrite HELD anyway ("a rewrite of the sanitization
  guard ... that preserves the same guarantee, not a removal of it"). Property statements are over-specific by
  default; the walk-time judgement compensated here, but it is compensation, not correctness.
- **OpenSSH regreSSHion: caught.** `752250caab` -> REGRESSED, tier 4, high confidence. Tier 2 saw 5/6 guard lines
  (the `#ifdef DO_LOG_SAFE_IN_SIGHAND` in log.c gone, defines.h lines intact) and looked for the missing line
  elsewhere: not found, so no MOVED hypothesis. Tier 4's rationale names the rename explicitly. 88 commits touched
  scope (defines.h is noisy), 40 evaluated by even sampling with the regressing commit force-included.
- Eval labels: 25 pairs. Seven are the same Black reformat commit across seven contracts — deliberately
  over-represented to test one failure mode (quote style) seven times. Stated in labels.json and the README.

## 2026-09-03 — results

- Budget hit exactly 150. Last 8 commits of CVE-2022-34265 are UNVERIFIABLE "budget"; CVE-2023-31047 (walked
  after) needed no tier 4.
- 23 REGRESSED verdicts, 1 true (OpenSSH). The 22 false ones come from four causes, each documented in the README.
  The worst is CVE-2022-34265 @ 877c800f25: Django swapped the whitelist for parameterized SQL in the backends;
  the model saw only the scope-file diff and said REGRESSED (high) nine times. Not fixed.
- CVE-2019-12308's tier-3 false alarms: the only deleted line was `def __init__(self, attrs=None):`. A single
  generic signature line is a terrible resurrection rule input. Left as-is per the no-tuning rule.
- CVE-2021-45452 @ fe4a0bbe20 was never visited: `storage/base.py` came out of the split as a copy, not a rename.
  The walk collects commits from the rename graph upfront; self-healing scope only adds files where guard lines
  are found, and only after the fact.
- CVE-2021-33571 @ 3bbe22dafc: model said MOVED because the manual leading-zero check was dropped when Django
  dropped Python 3.9 (the stdlib now rejects it). Reasonable, unlabelled, and interesting: the property moved to
  the platform.
- The banned-word instruction in the two prompts was itself the only occurrence of the words in the repo; replaced
  with neutral wording after all walks completed so every walk ran with the same prompt.
- `model_only` was initially defined too strictly (all evidence tier 4) and reported 0; corrected to "tier 4
  decided" before writing the README. No verdicts changed.

## 2026-09-03 — completeness check (bounded addition)

- `holdfast complete`: one tier-4 call per contract; context = excerpts (±12 lines) from every source file referencing
  the fix's function names, guard symbols and value variables, ranked by reference count, cap 25. Own budget of 12
  calls on top of the spent 150; 6 used, all logged with `purpose: complete`.
- Pre-registered 4 INCOMPLETE / 2 COMPLETE. Result: 1 hit, 3 misses, 2 correct, 0 false flags.
- The 28658 miss is the instructive one: the model had `uploadedfile.py:42` in front of it and called its bare
  `os.path.basename(name)` a covering layer, because it reasoned the value only enters through MultiPartParser.
  Widening the context found the sibling; judging it still required knowing the sibling's guard is the pre-fix
  pattern. Not tuned after seeing the result.
- Truncator and strip_tags misses are structural: the gap is an insufficient guard on the same path, which a
  "which consumers lack the guard" question cannot express.

## 2026-09-03 — demo PR and replay demo

- Demo PR on the fork glenfmessenger/django (created with `gh repo fork --clone=false`; never against django/django):
  https://github.com/glenfmessenger/django/pull/1. Base `holdfast-base` = 78fea27f69; head `holdfast/cve-2021-28658` =
  cherry-pick of d4d800ca1a, then UploadedFile and FieldFile coverage adapted from 0b79eb3691 (CVE-2021-31542; the
  note is in the 3.2.1/3.1.9/2.2.21 release notes, not 3.2.2/3.1.10), then the record + kept test. 52 tests in the
  touched modules pass at head on Python 3.9. Two '???'/'$.$.$' candidates dropped from the adapted FieldFile test
  because they depend on the get_valid_filename() part of that fix, which the branch does not take.
- Inline review comments must sit on diff lines; the consuming line uploadedfile.py:43 is outside the hunk, so the
  comment is anchored on the new validate_file_name call (line 51) and names line 43 in its text.
- `./demo` replays create -> walk -> complete -> report for the three tour cases from recorded model responses
  (indexed from contracts/, results/verdicts/, results/completeness/) and recorded tier-1 outcomes. 8 seconds, no key.
  The OpenSSH completeness step is UNVERIFIABLE (not recorded) because it was never run live. Writes only demo_out/.
