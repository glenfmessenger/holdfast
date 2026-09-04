# Claude Security results

Scanned `django/http/` in `/Users/glen/projects/holdfast/.targets/django-scan` (remote `https://github.com/django/django`) at commit `78fea27f690028204c03c28d821cb0c0240a7398` (clean tree, self-reported revision) on 2026-09-04 at 16:14 UTC. Mode: scoped codebase scan, effort `medium`, focus on production attack surface. Two findings survived verification, both MEDIUM severity, both in the multipart request-body parser.

## Coverage

The scope resolved to 5 tracked files: `django/http/__init__.py`, `cookie.py`, `multipartparser.py`, `request.py`, and `response.py`. Because the scope is at most 5 files, the run collapsed to the proportionate single-researcher shape at `medium` (`coverage.collapsed` = `small-scope`, `coverage.scopeFiles` = 5): one targeted research pass over the whole scope plus a secrets pass, rather than the full component matrix. Two researchers were dispatched and both returned. This was a fast targeted pass, still panel-verified, not an exhaustive read.

Completeness of the whole tree was not checked (`coverage.completenessCheckOutcome` = `not-applicable`) because the target is the scope, not the repository. No components were skipped or dropped. Focus was `attack-surface`, so test files, fixtures, and vendored copies were treated as background rather than audit targets; none exist inside the scope. Code outside `django/http/` was consulted only to trace callers and consumers (for example the upload handlers in `django/core/files/`) and was not itself audited. The researchers' own not-read accounting did not run for this collapsed shape.

The panel took 1 verification run. Two candidates were produced, none were duplicates, none were lost, and none were handed to a further run. No severities were lowered by the panel. Nothing in this scan executed the repository's code: no tests were run and no exploit was fired. Every finding below is derived from reading the source.

## Findings

### F1 — Unbounded number of uploaded file parts allows resource-exhaustion DoS (MEDIUM, confidence medium)

**Impact.** An unauthenticated client can make the server create an arbitrarily large number of temporary files and upload-handler invocations from a single request, exhausting file descriptors, inodes, disk space, and CPU. This snapshot has no `DATA_UPLOAD_MAX_NUMBER_FILES` setting and no `TooManyFilesSent` exception, so there is no Django-level cap at all.

**Where.** `django/http/multipartparser.py:235` in `MultiPartParser.parse`

**What.** The parser counts FIELD parts against `settings.DATA_UPLOAD_MAX_NUMBER_FIELDS` (lines 178 to 184), but the FILE branch that starts at line 210 has no counter. For every file part the request body contains, line 235 calls `handler.new_file()` on each configured upload handler. Multipart bodies are streamed directly (`request.py`) and bypass `DATA_UPLOAD_MAX_MEMORY_SIZE`, so the part count is bounded only by whatever body-size limit the front-end server imposes. `Parser.__iter__` (lines 647 to 651) yields one part per boundary without limit.

**Exploit scenario.** An attacker POSTs `multipart/form-data` to any view that reads `request.POST` or `request.FILES`, or whose middleware does (CSRF middleware reads `request.POST` on unsafe methods). The body contains hundreds of thousands of minimal file parts, each roughly 70 bytes: a `Content-Disposition` with a filename and empty content. For each part the parser calls `new_file()` on the handlers. With the default handler chain, bodies over 2.5 MB fall to `TemporaryFileUploadHandler`, which opens a new on-disk `NamedTemporaryFile` per part. The server runs out of file descriptors or disk before the request finishes.

**Preconditions.**
- A request path that triggers multipart parsing (any view accessing `request.POST` or `request.FILES` on a POST, or middleware doing so).
- The default `FILE_UPLOAD_HANDLERS`, or any configuration that includes `TemporaryFileUploadHandler`.
- No front-end proxy enforcing a strict request-body-size or part-count limit.

**Fix.** Add a per-request limit on the number of file parts in the FILE branch, mirroring the FIELD check: introduce a `DATA_UPLOAD_MAX_NUMBER_FILES` setting, count file parts as they are encountered, and raise a `TooManyFilesSent` exception once the limit is exceeded. This is the mitigation Django later shipped for CVE-2023-24580.

**Verification.** 3/3 lens verifiers confirmed.

### F2 — Multipart filename sanitized before HTML-unescape, allowing path separators to be reintroduced (MEDIUM, confidence low)

**Impact.** The parser hands upload handlers a filename such as `../../x` or `..` derived from an attacker-supplied `Content-Disposition` header. Django's built-in `UploadedFile._set_name` re-applies `os.path.basename`, which neutralizes embedded separators, but a name of exactly `..` survives both basename calls. An application that saves an upload under the client-supplied name can then be steered to write one directory above its intended location. This is the weakness class behind CVE-2021-28658 and CVE-2021-31542, whose fixes are not ancestors of this commit.

**Where.** `django/http/multipartparser.py:217` in `MultiPartParser.parse`

**What.** The filename from the `Content-Disposition` header (line 213) is passed through `os.path.basename` at line 215, and only afterwards through `html.unescape` at line 217. Unescaping can reintroduce `/` (for example from `&#47;` or `&#x2F;`) and path components after basename has already run. `IE_sanitize` (line 311) strips only backslash-prefixed Windows paths. Nothing else in `django/http/` validates the result before it reaches `handler.new_file()` at line 235.

**Exploit scenario.** An attacker submits `multipart/form-data` with `filename="..&#47;..&#47;x.txt"`. The parser produces `file_name = "../../x.txt"` and passes it to the upload handlers. With Django's built-in handlers, `UploadedFile._set_name` reduces this back to `x.txt`, so the built-in path is safe against embedded separators. A filename of exactly `..` is not reduced by basename and reaches the application as `..`; an application that calls `storage.save(uploaded_file.name, ...)` or otherwise uses the name in a path then writes outside the upload directory. Custom upload handlers that use the raw name from `new_file()` are exposed to the full traversal string.

**Preconditions.**
- The application saves uploaded files using the client-supplied `uploaded_file.name` via a Storage backend, or uses a custom upload handler that trusts the name passed to `new_file()`.
- The downstream Storage does not independently reject `..` or path components (this is outside `django/http/`).

**Fix.** Apply `html.unescape` and `force_str` before `os.path.basename`, and explicitly reject names that are `.`, `..`, or contain a path separator, raising a `SuspiciousFileOperation`. This is what Django's later `validate_file_name` helper does.

**Verification.** 2/3 lens verifiers confirmed. The dissenting verifier agreed the ordering defect is real but held that the reintroduced separator never reaches a filesystem operation through Django's own upload handlers, since `UploadedFile._set_name` re-basenames the value. One confirming verifier rated the impact LOW for the same reason. Treat this as a real ordering bug whose practical severity depends on how your application and storage backend consume the filename.

## What was verified

Both findings came from one targeted research pass over the 5 files in `django/http/` plus a secrets pass, then went to a three-voter adversarial panel (reachability, impact, and defenses lenses) where a finding needs at least 2 of 3 confirming votes to survive. F1 was confirmed unanimously and F2 by 2 of 3. Verification was by reading and tracing the code only; nothing was executed. The vote tally is code-computed by the scan workflow, and the revision stamp beside this report records the `verification.status` the renderer derived from it.


## Holdfast

Completeness check for F2 at patch base `78fea27f69` (record: `records/F2.json`). Protected value: the client-supplied upload filename parsed from the Content-Disposition header in MultiPartParser.parse (file_name). Verdict: **COMPLETE**.

Derived findings (no patches written; route through Suggest patches):

| id | consumer | file:line | confidence | note |
|---|---|---|---|---|
| F2.1 | `_set_name` | `django/core/files/uploadedfile.py:0` | low | `patches/F2.1.md` |
