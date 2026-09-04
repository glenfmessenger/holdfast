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
