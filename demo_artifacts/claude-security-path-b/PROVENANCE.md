# PROVENANCE

This CLAUDE-SECURITY directory was HAND-BUILT on 2026-09-03 for Holdfast demo path B. The Claude Security
plugin did not produce it. It follows the plugin's v0.11.0 schema (finding field order from scripts/lib/finding.py,
stamp keys from render_report.py, patches/ layout from patch_artifacts.py) so that `holdfast integrate` can be shown
on a report of the right shape.

- F1 is the CVE-2021-28658 multipart filename traversal at 78fea27f6900 (the fix's parent), written by hand from the
  Django release note and the code.
- patches/F1.patch is Django's own fix d4d800ca1a restricted to django/http/multipartparser.py, with a hand-written
  header; no patch-generator/patch-verifier agents ran, and the claims in patches.jsonl are marked UNSURE.
- CLAUDE-SECURITY-RESULTS.sarif is omitted; the SARIF renderer is the plugin's and was not run.
- The verification block in the revision stamp says status "not-verified" for the same reason.

## Files added by `holdfast integrate` (prototype output, not plugin output)

- `records/F1.json`, `records/F1.advisory.txt` — the remediation record and the advisory text Holdfast built from F1.
- The `## Holdfast` section appended to `CLAUDE-SECURITY-RESULTS.md`.
- No derived findings were appended to the JSONL and no `patches/F1.<k>.md` notes were written, because the
  completeness query returned COMPLETE (it judged `django/core/files/uploadedfile.py` covered). The ground truth is
  INCOMPLETE; see the Holdfast README, "Where it breaks".
- This copy was taken from `.targets/django-b/CLAUDE-SECURITY-20260904-052717/` after the run; the report's own
  `.gitignore` was removed so the copy could be committed here as a demo artifact.
