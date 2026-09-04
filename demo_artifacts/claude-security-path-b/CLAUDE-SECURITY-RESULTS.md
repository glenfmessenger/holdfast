# Claude Security results (HAND-BUILT — see PROVENANCE.md)

Scanned: django/http/ at 78fea27f6900 (1 finding).

## F1 — Directory traversal via HTML-entity-encoded upload file name in MultiPartParser

- **Severity:** HIGH  **Confidence:** high  **Location:** django/http/multipartparser.py:215 (`MultiPartParser.parse`)
- **Impact:** An attacker uploading a file with a crafted Content-Disposition filename such as '..&#x2F;target.txt' obtains a name containing '../' after sanitization, so a custom upload handler that uses the name to build a filesystem path can write outside the intended upload directory.
- **Exploit scenario:** POST multipart/form-data with Content-Disposition: form-data; name="file"; filename="..&#x2F;..&#x2F;hax0rd.txt". basename() sees no separator; unescape() then yields '../../hax0rd.txt', which reaches the upload handler's new_file() as the file name.
- **Recommendation:** HTML-unescape the filename first, then strip Windows-style separators, and apply os.path.basename() as the final step, in one sanitize_file_name() helper used at the single call site.


## Holdfast

Completeness check for F1 at patch base `78fea27f69` (record: `records/F1.json`). Protected value: the client-supplied upload filename obtained from the Content-Disposition header in MultiPartParser.parse() (disposition.get('filename')). Verdict: **COMPLETE**.

No uncovered consumers were listed. Cannot verify: This contract only verifies the ordering within sanitize_file_name() and its single call site in parse(); it cannot verify that downstream upload handlers (e.g. custom new_file() implementations) don't perform additional unsafe path construction with the sanitized name, nor does it cover other Django versions/branches or non-multipart file-upload code paths outside this file. Consumers outside this repository (third-party packages, deployment configuration) are not examined; the consumer list is only as complete as the symbol references the query was shown.
