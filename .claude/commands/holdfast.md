---
description: Holdfast on a Claude Security finding that has a patch — check completeness (integrate) or close it as a PR (close)
argument-hint: "[integrate|close] [finding F<n>] [path to CLAUDE-SECURITY-<ts> dir]"
allowed-tools: Bash(ls:*), Bash(find:*), Bash(cat:*), Bash(python3:*), Bash(gh auth status:*), Bash(*/holdfast integrate:*), Bash(*/holdfast close:*), Read, Glob
---

You are running Holdfast, the completeness and durability layer on top of Claude Security's remediation. It has two
jobs, matching the plugin's convention of naming a job and a finding in plain language ("close finding F1",
"check F3", "integrate F2"):

- **integrate** — build the contract from the finding's patch, run the completeness query, append derived findings
  `F<n>.1`, `F<n>.2` ... to the report's JSONL with a note each, write `records/F<n>.json`, append a Holdfast section
  to the report. Writes no patches and touches no branch.
- **close** — everything integrate does, then in the target repository: branch `holdfast/close-F<n>-<rev>` from the
  report's stamped revision, the patch as one commit (tests in the patch as a separate kept-test commit), the record
  committed at `.holdfast/records/F<n>.json`, and a pull request on the user's fork against `holdfast-base-<rev>`.

Steps:
1. Read `$ARGUMENTS`. "close ..." / "close finding F1" selects close; "integrate", "check", or no verb selects
   integrate. A token matching `F<n>` names the finding. A path names the report directory.
2. Locate the report: the named directory, else the `CLAUDE-SECURITY-*` directory in the current repository with the
   latest timestamp, else the included demo copy `demo_artifacts/claude-security-path-b/` (hand-built in the plugin's
   schema; the plugin did not produce it — say so). If none exists, say so and stop: Holdfast runs after
   `/claude-security` scan and Suggest patches. For the included demo copy the target repository is not beside the
   report: add `--repo .targets/django` (created by `./demo`) to the command in step 5.
3. List the findings that have a patch: for each `patches/F<n>.patch`, print id, title, `file:line`, severity and
   confidence from `CLAUDE-SECURITY-RESULTS.jsonl`. Findings without a patch are listed as "no patch — run Suggest
   patches first" and cannot be chosen.
4. If no finding was named, ask which one. Never guess. For close, also run `gh auth status` first; if it is not
   authenticated, stop and tell the user — nothing is done.
5. Run one standalone command from the repository root (in this repository the binary is `.venv/bin/holdfast`):
   `holdfast integrate --report <dir> --finding F<n>`  or  `holdfast close --report <dir> --finding F<n>`
6. Report the printed JSON: verdict (COMPLETE / INCOMPLETE / UNVERIFIABLE), derived finding ids with consumer and
   confidence, record path, and for close the commits and the PR URL. Close with one line: derived findings get
   patches through `/claude-security` Suggest patches, one PR per patch; nothing merges automatically.
