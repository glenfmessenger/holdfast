---
description: Run Holdfast's completeness check on a Claude Security finding that has a patch
argument-hint: "[F<n>] [path to CLAUDE-SECURITY-<ts> dir]"
allowed-tools: Bash(ls:*), Bash(find:*), Bash(cat:*), Bash(python3:*), Bash(*/holdfast integrate:*), Read, Glob
---

You are running Holdfast, the completeness and durability layer on top of Claude Security's remediation.

1. Locate the newest Claude Security report: the `CLAUDE-SECURITY-*` directory in the current repository
   (or the directory the user passed in `$ARGUMENTS`) with the latest timestamp in its name. If none exists,
   say so and stop: Holdfast runs after `/claude-security` scan and Suggest patches.
2. List the findings that have a patch: for each `patches/F<n>.patch` in that directory, print the finding's id,
   title, `file:line`, severity and confidence from `CLAUDE-SECURITY-RESULTS.jsonl`. Findings without a patch are
   listed as "no patch — run Suggest patches first" and cannot be chosen.
3. Choose the finding: the id given in `$ARGUMENTS` if there is one, otherwise ask the user which of the listed
   findings to check. Never guess.
4. Run, as one standalone command from the repository root:
   `<path to holdfast venv>/bin/holdfast integrate --report <CLAUDE-SECURITY dir> --finding F<n>`
   (in this repository: `.venv/bin/holdfast`). It appends derived findings `F<n>.1`, `F<n>.2` ... to the JSONL,
   writes a note per derived finding beside the patches, writes `records/F<n>.json`, and appends a "Holdfast"
   section to `CLAUDE-SECURITY-RESULTS.md`. It writes no patches.
5. Report the printed JSON: the verdict (COMPLETE / INCOMPLETE / UNVERIFIABLE), the derived finding ids with
   their consumer and confidence, and the record path. Close with one line: derived findings get patches through
   `/claude-security` Suggest patches, one PR per patch; nothing merges automatically.
