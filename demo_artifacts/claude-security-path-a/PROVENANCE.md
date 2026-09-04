# PROVENANCE

Produced by the Claude Security plugin v0.11.0 on 2026-09-04 (demo path A), scanning the worktree
`.targets/django-scan` of glenfmessenger/django at 78fea27f690028204c03c28d821cb0c0240a7398, scoped to `django/http/`,
effort medium: CLAUDE-SECURITY-RESULTS.{md,jsonl,sarif}, CLAUDE-SECURITY-REVISION-78fea27f6900.json, and, from the
plugin's Suggest patches job, patches/F2.patch, F2.md, PATCHES.md, patches.jsonl. F1 (unbounded file parts) was not
patched. The report's own `.gitignore` was removed for this committed copy only.

## Files added by Holdfast (prototype output, not plugin output)

- `records/F2.json`, `records/F2.advisory.txt`, `records/F2.pr-body.md` — the remediation record, the advisory text
  built from F2, and the PR body rendered from the record.
- `patches/F2.1.md` and the appended `F2.1` line in CLAUDE-SECURITY-RESULTS.jsonl — the derived finding the
  completeness query listed at low confidence (below the verdict threshold).
- The `## Holdfast` section appended to CLAUDE-SECURITY-RESULTS.md.
- Closed as https://github.com/glenfmessenger/django/pull/3 by `holdfast close`.
