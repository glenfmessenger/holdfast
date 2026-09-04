# Completeness check (value-flow query at the fix commit)

Pre-registered in `results/completeness_labels.json` before the command existed. Six contracts, six tier-4 calls (`purpose: complete` in `results/model_calls.jsonl`), own budget 12. Per-contract JSON with the verbatim model reply in `results/completeness/`.

| contract | expected | actual | protected value (model) | files in context | flagged consumers |
|---|---|---|---|---|---|
| CVE-2021-28658 | INCOMPLETE | **COMPLETE** | the uploaded file's filename parsed from the Content-Disposition header in MultiPartParser | 15 (+0 excluded) | none |
| CVE-2019-14232 | INCOMPLETE | **COMPLETE** | the HTML string passed to Truncator.chars()/words() (via truncatechars_html/truncatewords_ | 25 (+33 excluded) | none |
| CVE-2019-14233 | INCOMPLETE | **COMPLETE** | the loop-termination condition in strip_tags() (i.e., the untrusted HTML string being repe | 2 (+0 excluded) | none |
| CVE-2021-45452 | INCOMPLETE | **INCOMPLETE** | the storage-relative file name passed to / returned by Storage.save() (i.e., the name that | 25 (+3 excluded) | django/contrib/staticfiles/storage.py (medium), django/contrib/staticfiles/storage.py (low) |
| CVE-2019-14235 | COMPLETE | **COMPLETE** | the raw request URI/path bytes passed into repercent_broken_unicode() (e.g. WSGI PATH_INFO | 25 (+13 excluded) | none |
| CVE-2023-23969 | COMPLETE | **COMPLETE** | the raw Accept-Language HTTP header value (lang_string) passed into parse_accept_lang_head | 19 (+0 excluded) | none |

## Counts

- INCOMPLETE cases (4): hits 1, misses 3
- COMPLETE cases (2): correct 2, incorrect 0
- False flags (uncovered consumer at medium/high on a COMPLETE-labelled contract): 0

## Flagged consumers vs pre-registration

- **CVE-2021-45452** flagged `django/contrib/staticfiles/storage.py` / HashedFilesMixin.post_process (medium): matches a pre-registered consumer file, by a different mechanism (direct `_save()` calls bypassing `save()`, not an overridden `generate_filename`). Model reason: These calls invoke Storage._save() (i.e. FileSystemStorage._save()) directly rather than going through Storage.save(), so the newly added `validate_file_name(name, allow_relative_path=True)` guard in Storage.save() is never executed on this path. The relpath normalization inside FileSystemStorage._s
- **CVE-2021-45452** flagged `django/contrib/staticfiles/storage.py` / ManifestStaticFilesStorage.save_manifest (low): same file, same mechanism; low confidence, does not drive the verdict. Model reason: Direct call to _save() bypasses Storage.save()'s validate_file_name() guard. manifest_name appears to be a fixed/internal name so risk is low, but the guard added by the fix is not exercised on this call path.

## Misses, by name

- **CVE-2021-28658**: expected INCOMPLETE with consumers ['django/core/files/uploadedfile.py', 'django/db/models/fields/files.py']; got COMPLETE. Files the model judged covered: django/http/multipartparser.py (MultiPartParser.parse); django/core/files/uploadhandler.py (FileUploadHandler.new_file / TemporaryFileUploadHandler.new_file); django/core/files/uploadedfile.py (UploadedFile._set_name).
  - It saw the expected consumer `django/core/files/uploadedfile.py` and judged it covered: "This is a separate, pre-existing defense-in-depth layer that itself calls os.path.basename(name) at line 42 on the name property setter, independent of the CVE fix, so the same sanitized value passing through here is not a bypass path."
- **CVE-2019-14232**: expected INCOMPLETE with consumers ['django/utils/text.py (Truncator.chars/words html=True path, re_words/re_chars over unbounded input)']; got COMPLETE. Files the model judged covered: django/utils/text.py (Truncator._truncate_html).
  - It saw the expected consumer `django/utils/text.py` and judged it covered: "The only consumer of re_words/re_chars found in the excerpts is the `regex = re_words if words else re_chars` / `m = regex.search(text, pos)` loop at lines 169-172 of django/utils/text.py. Both re_words and re_chars were rewritten in the diff to use `<[^>]+?>` and `[^<>\s]+` instead of the vulnerable `<.*?>` / nested `(?:\w[-\w]*|&.*?;)+` patterns,"
- **CVE-2019-14233**: expected INCOMPLETE with consumers ['django/utils/html.py (strip_tags loop: bounded-progress deep recursion still unbounded)']; got COMPLETE. Files the model judged covered: django/utils/html.py (strip_tags); django/template/defaultfilters.py (striptags).
  - It saw the expected consumer `django/utils/html.py` and judged it covered: "The guard `if value.count('<') == new_value.count('<'):` replaces the old length-based check directly in the loop that drives _strip_once(), which is the sole location controlling the vulnerable iteration."

## Reading

The one hit (CVE-2021-45452) is the case where the gap is on a *different call path* (staticfiles calling `_save()` directly); the file matches the pre-registration, the mechanism does not. The three misses are cases where the gap is inside the same function: an unbounded input to the same regex (Truncator), bounded-progress recursion in the same loop (strip_tags), or a sibling consumer the model saw and judged covered because it reasoned the value only enters via the fixed parser (UploadedFile._set_name). A value-flow query finds missing guards on other paths; it does not find an insufficient guard on the same path, and it trusts a sibling's own weaker guard.
