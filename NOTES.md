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
