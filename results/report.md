# Holdfast report

392 verdicts across 21 contracts. Generated from `results/verdicts/`.

## Counts

| status | n |
|---|---|
| HELD | 356 |
| MOVED | 1 |
| REGRESSED | 23 |
| UNVERIFIABLE | 12 |

| deciding tier | n |
|---|---|
| 1 EXECUTED | 134 |
| 2 STRUCTURAL | 127 |
| 3 RULE | 8 |
| 4 MODEL | 123 |

HELD decided by tier 4 only (model-only): **108** of 356 HELD verdicts. All model-only verdicts: 123.
Tier disagreements recorded (model vs tiers 1-3): 0.

## Showcase cases

**1. Fix survived a real refactor (HELD, tier 1)** — CVE-2021-28658 (MultiPartParser traversal) at 34e2148fc7 (2022-05-11, 'Removed use of deprecated cgi module'): the header-parsing code around sanitize_file_name was rewritten and the extracted regression test still passes. Same contract, same tier, at 0b79eb3691 where the sanitizer itself was rewritten. CVE-2019-12781 held at tier 1 through all 28 later commits to request.py, including the move of get_raw_uri (8bcb00858e).
  - `results/verdicts/CVE-2021-28658/34e2148fc7.json`
  - `results/verdicts/CVE-2021-28658/0b79eb3691.json`
  - `results/verdicts/CVE-2019-12781/8bcb00858e.json`

**2. Genuine regression caught (REGRESSED, tier 4, high confidence)** — OpenSSH CVE-2006-5051 contract at 752250caab (2020-10-16, 'revised log infrastructure'), the regreSSHion commit. Tier 2 saw 5/6 guard lines (the #ifdef DO_LOG_SAFE_IN_SIGHAND in log.c gone, defines.h lines intact) and found the missing line nowhere else, so no MOVED hypothesis; tier 4 named the rename explicitly: 'the guard macro's usage at the sigdie call site was dropped when sigdie was renamed/rewritten into sshsigdie, and no equivalent check appears in the new function body'. Pre-registered in results/labels.json with MOVED as the failure under test.
  - `results/verdicts/CVE-2006-5051/752250caab.json`
  - `contracts/CVE-2006-5051.json`

**3. False resurrection correctly rejected (HELD, tier 4)** — CVE-2021-33571 (IPv4 leading zeros) at bdf3e156b4 (2022-01-07, '\d -> [0-9] in regexes'): every recorded guard line changed and tier 2 saw 0/8 present. Tier 4 read the new regex and judged the no-leading-zero grammar intact: HELD. Pre-registered as a rewrite trap. The Black reformat (9c19aff7c7) was rejected the same way in seven contracts, three of them at tier 1 or 2 and four at tier 4.
  - `results/verdicts/CVE-2021-33571/bdf3e156b4.json`
  - `results/verdicts/CVE-2019-19844/9c19aff7c7.json`

**4. The miss: REGRESSED that is not a regression (tier 4, high confidence, nine times)** — CVE-2022-34265 (Trunc/Extract SQL injection) at 877c800f25 (2022-07-06, 'Refs CVE-2022-34265 -- Properly escaped Extract() and Trunc() parameters'). Django replaced the fix's regex whitelist with parameterized SQL in every backend's operations.py. The contract's scope is base/operations.py and functions/datetime.py; the diff the model saw showed only the whitelist being deleted. Verdict: REGRESSED, high confidence, and the same verdict at the next eight commits until the tier-4 budget ran out. The security goal moved to a different mechanism in files outside scope. Not fixed after finding it.
  - `results/verdicts/CVE-2022-34265/877c800f25.json`
  - `results/verdicts/CVE-2022-34265/649b28eab6.json`
  - `contracts/CVE-2022-34265.json`

## Per contract

### CVE-2006-5051 (sampled)

_range bb59814cd6..752250caab: 88 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2006-08-20 | `aa1517ca1e` | HELD | 2 | medium |  - (dtucker) [log.c] Move ifdef to prevent unused variable warning. |
| 2007-03-26 | `99203ec48b` | HELD | 2 | medium | 20070326  - (tim) [auth.c configure.ac defines.h session.c openbsd-com |
| 2007-04-29 | `391de5c023` | HELD | 2 | medium |  - (dtucker) [configure.ac defines.h] Prevent warnings about __attribu |
| 2007-08-09 | `a5b6f72a52` | HELD | 2 | medium |  - (dtucker) [defines.h] Remove _PATH_{CSHELL,SHELLS} which aren't     |
| 2007-09-27 | `bc1bd9dbe3` | HELD | 2 | medium |  - (dtucker) [configure.ac defines.h] Shadow expiry does not work on Q |
| 2008-06-08 | `5b2e2ba9e4` | HELD | 2 | medium |  - (dtucker) [configure.ac defines.h sftp-client.c sftp-server.c sftp. |
| 2008-06-09 | `77001384cc` | HELD | 2 | medium |  - (dtucker) [configure.ac defines.h sftp-client.c M sftp-server.c] Ad |
| 2008-07-04 | `d8968adb5f` | HELD | 2 | medium |  - (djm) [atomicio.c channels.c clientloop.c defines.h includes.h]     |
| 2009-02-01 | `642ebe5b51` | HELD | 2 | medium |  - (dtucker) [defines.h sshconnect.c] INET6_ADDRSTRLEN is now needed i |
| 2009-06-16 | `3278062bf3` | HELD | 2 | medium |  - (dtucker) [configure.ac defines.h] Bug #1607: handle the case where |
| 2010-01-09 | `709d0ce672` | HELD | 2 | medium |  - (dtucker) [defines.h] define PRIu64 for platforms that don't have i |
| 2010-04-09 | `261d93a5cf` | HELD | 2 | medium |  - (dtucker) [configure.ac defines.h loginrec.c logintest.c] Bug #1732 |
| 2010-10-25 | `54b1f3121d` | HELD | 2 | medium |  - (dtucker) [defines.h] Use SIZE_T_MAX for SIZE_MAX for platforms tha |
| 2011-01-17 | `ea52a82969` | HELD | 2 | medium | - (dtucker) [LICENCE Makefile.in audit-bsm.c audit-linux.c audit.c aud |
| 2011-05-04 | `9abb697d4f` | HELD | 2 | medium |  - (tim) [defines.h] Deal with platforms that do not have S_IFSOCK ok  |
| 2011-06-20 | `8f0bf237d4` | HELD | 2 | medium |    - djm@cvs.openbsd.org 2011/06/17 21:44:31      [log.c log.h monitor |
| 2012-09-06 | `50a48d025f` | HELD | 2 | medium |    - dtucker@cvs.openbsd.org 2012/09/06 04:37:39      [clientloop.c lo |
| 2013-03-07 | `9243ef086f` | HELD | 2 | medium |  - (dtucker) [defines.h] Remove SIZEOF_CHAR bits since the test for it |
| 2013-04-23 | `03d4d7e60b` | HELD | 2 | medium |    - dtucker@cvs.openbsd.org 2013/04/07 02:10:33      [log.c log.h ssh |
| 2013-06-02 | `c7aad0058c` | HELD | 2 | medium |  - (dtucker) [configure.ac defines.h] Test for fd_mask, howmany and NF |
| 2014-01-17 | `acad351a5b` | HELD | 2 | medium |  - (dtucker) [defines.h] Add typedefs for uintXX_t types for platforms |
| 2014-04-20 | `4f40209aa4` | HELD | 2 | medium |    - djm@cvs.openbsd.org 2014/03/26 04:55:35      [chacha.h cipher-cha |
| 2014-05-15 | `686c7d9ee6` | HELD | 2 | medium |    - djm@cvs.openbsd.org 2014/05/02 03:27:54      [chacha.h cipher-cha |
| 2014-06-12 | `cf5392c2db` | HELD | 2 | medium |  - (dtucker) [defines.h] Add va_copy if we don't already have it, take |
| 2015-01-27 | `a2c95c1bf3` | HELD | 2 | medium | OSX lacks HOST_NAME_MAX, has _POSIX_HOST_NAME_MAX |
| 2015-02-21 | `28ba006c1a` | HELD | 2 | medium | More correct checking of HAVE_DECL_AI_NUMERICSERV. |
| 2015-02-24 | `38806bda6d` | HELD | 2 | medium | include netdb.h to look for MAXHOSTNAMELEN; ok tim |
| 2015-03-04 | `1598419e38` | HELD | 2 | medium | define __unused to nothing if not already defined |
| 2015-07-15 | `a635bd06b5` | HELD | 2 | medium | upstream commit |
| 2016-07-15 | `af1f084857` | HELD | 2 | medium | upstream commit |
| 2016-08-17 | `1e8013a17f` | HELD | 2 | medium | Remove obsolete CVS $Id from source files. |
| 2017-03-10 | `9747b9c742` | HELD | 2 | medium | upstream commit |
| 2017-05-17 | `54cd41a466` | HELD | 2 | medium | upstream commit |
| 2018-07-31 | `5d14019ba2` | HELD | 2 | medium | upstream: avoid expensive channel_open_message() calls; ok djm@ |
| 2019-07-08 | `4efe1adf05` | HELD | 2 | medium | remove realpath() compat replacement |
| 2019-10-08 | `0c7f8d2326` | HELD | 2 | medium | Make DEF_WEAK more likely to be correct. |
| 2019-11-15 | `134a74f4e0` | HELD | 2 | medium | Add SSIZE_MAX when we define ssize_t. |
| 2020-02-09 | `14ccfdb724` | HELD | 2 | medium | Check if UINT32_MAX is defined before redefining. |
| 2020-07-03 | `c8935081db` | HELD | 2 | medium | upstream: when redirecting sshd's log output to a file, undo this |
| 2020-10-17 | `752250caab` | REGRESSED | 4 | high | upstream: revised log infrastructure for OpenSSH |

### CVE-2019-12308

_range deeba6d920..8d9901c961: 21 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2019-08-27 | `8f6860863e` | HELD | 1 | high | Fixed #30722 -- Added default rate-limiting requests to admin's Select |
| 2020-02-04 | `335c9c94ac` | HELD | 1 | high | Simplified imports from django.db and django.contrib.gis.db. |
| 2020-03-24 | `3a807a6f59` | HELD | 1 | high | Fixed #31365 -- Removed jQuery usage in SelectFilter2.js. |
| 2020-06-03 | `2dd4d110c1` | HELD | 1 | high | Fixed CVE-2020-13596 -- Fixed potential XSS in admin ForeignKeyRawIdWi |
| 2021-01-12 | `3071660acf` | HELD | 1 | high | Fixed #29010, Fixed #29138 -- Added limit_choices_to and to_field supp |
| 2021-03-18 | `03d0f12c82` | HELD | 1 | high | Fixed #32466 -- Corrected autocomplete to_field resolution for complex |
| 2021-09-21 | `8eb5693091` | HELD | 1 | high | Fixed #33070 -- Fixed loading translations with language subtags in ad |
| 2021-11-29 | `05e29da421` | HELD | 1 | high | Fixed #32545 -- Improved admin widget for raw_id_fields for UUIDFields |
| 2022-02-07 | `9c19aff7c7` | HELD | 1 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-02-18 | `3079133c73` | HELD | 1 | high | Fixed #33514 -- Added fallbacks to subsequent language codes in Select |
| 2022-02-25 | `11cc227344` | HELD | 1 | high | Fixed #33267 -- Added link to related item to related widget wrapper i |
| 2022-04-15 | `c72f6f36c1` | HELD | 1 | high | Fixed #11803 -- Allowed admin select widgets to display new related ob |
| 2022-08-03 | `0638b4e23d` | HELD | 1 | high | Fixed #33888 -- Fixed get_select2_language() crash with no language ac |
| 2023-06-09 | `caf80cb41f` | REGRESSED | 3 | medium | Fixed #34645 -- Restored alignment for admin date/time timezone warnin |
| 2023-07-06 | `95cdf9dc66` | REGRESSED | 3 | medium | Used AdminSite.is_registered() where appropriate. |
| 2023-08-30 | `500e01073a` | REGRESSED | 3 | medium |  Fixed #31262 -- Added support for mappings on model fields and Choice |
| 2023-12-14 | `2190096f50` | REGRESSED | 3 | medium | Used model's Options.model_name instead of object_name.lower(). |
| 2024-01-26 | `305757aec1` | REGRESSED | 3 | medium | Applied Black's 2024 stable style. |
| 2024-04-02 | `8665cf03d7` | REGRESSED | 3 | medium | Fixed #35330 -- Fixed the update of related widgets when the reference |
| 2024-06-12 | `719a42b589` | REGRESSED | 3 | medium | Fixed #34789 -- Prevented updateRelatedSelectsOptions from  adding ent |
| 2024-08-06 | `5f1757142f` | REGRESSED | 3 | medium | Fixed CVE-2024-41991 -- Prevented potential ReDoS in django.utils.html |

### CVE-2019-12781

_range 54d0f5e62f..8d9901c961: 28 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2019-10-29 | `e3d0b4d550` | HELD | 1 | high | Fixed #30899 -- Lazily compiled import time regular expressions. |
| 2019-12-05 | `adb9661789` | HELD | 1 | high | Fixed #31010 -- Allowed subdomains of localhost in the Host header by  |
| 2019-12-27 | `e42b68debf` | HELD | 1 | high | Fixed #31114 -- Fixed HttpRequest.build_absolute_uri() crash with reve |
| 2020-01-24 | `d66d72f956` | HELD | 1 | high | Refs #30997 -- Added HttpRequest.accepts(). |
| 2020-01-27 | `e348ab0d43` | HELD | 1 | high | Fixed #30997 -- Deprecated HttpRequest.is_ajax(). |
| 2020-05-12 | `0668164b4a` | HELD | 1 | high | Fixed E128, E741 flake8 warnings. |
| 2020-06-03 | `7fc317ae73` | HELD | 1 | high | Refs #30997 -- Improved HttpRequest.is_ajax() warning message with sta |
| 2020-09-03 | `fd209f62f1` | HELD | 1 | high | Refs #21231 -- Backport urllib.parse.parse_qsl() from Python 3.8. |
| 2020-09-07 | `83dea65ed6` | HELD | 1 | high | Refs #21231 -- Corrected parse_qsl() fallback. |
| 2021-01-14 | `d08977a0f0` | HELD | 1 | high | Refs #30997 -- Removed HttpRequest.is_ajax() per deprecation timeline. |
| 2021-02-10 | `ec0ff40631` | HELD | 1 | high | Fixed #32355 -- Dropped support for Python 3.6 and 3.7 |
| 2021-04-30 | `8bcb00858e` | HELD | 1 | high | Fixed #32698 -- Moved HttpRequest.get_raw_uri() to ExceptionReporter._ |
| 2022-01-07 | `bdf3e156b4` | HELD | 1 | high | Fixed #28628 -- Changed \d to [0-9] in regexes where appropriate. |
| 2022-02-07 | `7119f40c98` | HELD | 1 | high | Refs #33476 -- Refactored code to strictly match 88 characters line le |
| 2022-02-07 | `9c19aff7c7` | HELD | 1 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-03-23 | `1cf60ce601` | HELD | 1 | high | Fixed #33569 -- Added SECURE_PROXY_SSL_HEADER support for list of prot |
| 2022-05-11 | `34e2148fc7` | HELD | 1 | high | Refs #33173 -- Removed use of deprecated cgi module. |
| 2022-06-09 | `e96320c917` | HELD | 1 | high | Fixed #33755 -- Moved ASGI body-file cleanup into request class. |
| 2022-06-28 | `d6e0c7c30c` | HELD | 1 | high | Refs #33697 -- Made MediaType use django.utils.http.parse_header_param |
| 2022-09-14 | `6220c445c4` | HELD | 1 | high | Fixed #29186 -- Fixed pickling HttpRequest and subclasses. |
| 2022-11-14 | `67da22f08e` | HELD | 1 | high | Fixed #34074 -- Added headers argument to RequestFactory and Client cl |
| 2023-01-18 | `23e8868862` | HELD | 1 | high | Refs #34233 -- Used str.removeprefix()/removesuffix(). |
| 2023-02-14 | `85ac33591c` | HELD | 1 | high | Fixed CVE-2023-24580 -- Prevented DoS with too many uploaded files. |
| 2023-04-12 | `280ca147af` | HELD | 1 | high | Fixed #34484, Refs #34482 -- Reverted "Fixed #29186 -- Fixed pickling  |
| 2023-08-02 | `ee36c332b2` | HELD | 1 | high | Simplified django.http.request.split_domain_port(). |
| 2023-08-25 | `11920e7795` | HELD | 1 | high | Fixed #34709 -- Raised BadRequest for non-UTF-8 requests with the appl |
| 2024-01-26 | `305757aec1` | HELD | 1 | high | Applied Black's 2024 stable style. |
| 2024-09-09 | `e161bd4657` | HELD | 1 | high | Fixed #35631 -- Added HttpRequest.get_preferred_type(). |

### CVE-2019-14232

_range 7f65974f82..8d9901c961: 19 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2019-08-01 | `e8d0d2a5ef` | HELD | 1 | high | Removed unneeded ValueError catching in django.utils.text._replace_ent |
| 2019-10-29 | `e3d0b4d550` | HELD | 1 | high | Fixed #30899 -- Lazily compiled import time regular expressions. |
| 2019-12-30 | `b2bd08bb7a` | HELD | 1 | high | Fixed #30892 -- Fixed slugify() and admin's URLify.js for "İ". |
| 2020-05-11 | `d6aff369ad` | HELD | 1 | high | Refs #30116 -- Simplified regex match group access with Match.__getite |
| 2020-05-29 | `0382ecfe02` | HELD | 1 | high | Fixed #28694 -- Made django.utils.text.slugify() strip dashes and unde |
| 2020-05-29 | `3111b434e7` | HELD | 1 | high | Corrected slugify()'s docstring. |
| 2021-01-14 | `157ab32f34` | HELD | 1 | high | Refs #27753 -- Removed django.utils.text.unescape_entities() per depre |
| 2021-03-23 | `6efc35b4fe` | UNVERIFIABLE | 4 | low | Optimized django.utils.text.capfirst(). |
| 2021-05-04 | `0b79eb3691` | UNVERIFIABLE | 4 | low | Fixed CVE-2021-31542 -- Tightened path & file name sanitation in file  |
| 2021-06-21 | `5a468b4c08` | HELD | 4 | medium | Fixed #32859 -- Simplified compress_string() by using gzip.compress(). |
| 2021-12-14 | `e1d673c373` | HELD | 4 | medium | Fixed unescape_string_literal() crash on empty strings. |
| 2021-12-30 | `a21a63cc28` | UNVERIFIABLE | 4 | low | Refs #27753 -- Removed unused django.utils.text._replace_entity() and  |
| 2022-02-07 | `9c19aff7c7` | HELD | 4 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-12-17 | `ab7a85ac29` | HELD | 4 | medium | Fixed #34170 -- Implemented Heal The Breach (HTB) in GzipMiddleware. |
| 2023-07-14 | `6f1b8c00d8` | HELD | 4 | medium | Refs #30686 -- Moved add_truncation_text() helper to a module level. |
| 2023-10-04 | `17b51094d7` | UNVERIFIABLE | 4 | low | Fixed CVE-2023-43665 -- Mitigated potential DoS in django.utils.text.T |
| 2024-02-07 | `6ee37ada32` | REGRESSED | 1 | high | Fixed #30686 -- Used Python HTMLParser in utils.text.Truncator. |
| 2024-02-07 | `70f39e46f8` | HELD | 4 | medium | Refs #30686 -- Fixed text truncation for negative or zero lengths. |
| 2024-02-15 | `3cadeea077` | REGRESSED | 1 | high | Refs #30686 -- Removed unused regexes in django.utils.text. |

### CVE-2019-14233

_range 4b78420d25..8d9901c961: 25 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2019-10-29 | `e3d0b4d550` | HELD | 2 | medium | Fixed #30899 -- Lazily compiled import time regular expressions. |
| 2019-11-25 | `824981b2dc` | HELD | 2 | medium | Removed unused unencoded_ampersands_re regex. |
| 2021-07-07 | `68cc04887b` | HELD | 2 | medium | Fixed #32866 -- Fixed trimming trailing punctuation from escaped strin |
| 2021-10-14 | `514c16e85f` | HELD | 2 | medium | Removed unused DOTS list. |
| 2021-10-15 | `e567670b1a` | HELD | 2 | medium | Fixed #33195 -- Refactored urlize() based on a class. |
| 2021-11-01 | `ad81b606a2` | HELD | 2 | medium | Fixed #33245 -- Made django.utils.html.urlize() thread-safe. |
| 2021-11-03 | `1f9874d4ca` | HELD | 2 | medium | Refs #33245 -- Minor edits to django.utils.html.urlize() changes. |
| 2021-11-22 | `e6e664a711` | HELD | 2 | medium | Fixed #33302 -- Made element_id optional argument for json_script temp |
| 2022-02-07 | `9c19aff7c7` | HELD | 4 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-02-10 | `cda81b79f2` | HELD | 4 | high | Refs #32568 -- Optimized escape() by using SafeString instead of mark_ |
| 2022-02-21 | `b626c5a979` | HELD | 4 | high | Removed unnecessary str type from @keep_lazy decorator for escape()/es |
| 2022-06-28 | `72e41a0df6` | HELD | 4 | high | Fixed #33779 -- Allowed customizing encoder class in django.utils.html |
| 2022-11-10 | `9bd174b9a7` | HELD | 4 | high | Updated documentation and comments for RFC updates. |
| 2023-01-18 | `23e8868862` | HELD | 4 | high | Refs #34233 -- Used str.removeprefix()/removesuffix(). |
| 2023-06-06 | `094b0bea2c` | HELD | 4 | high | Fixed #34609 -- Deprecated calling format_html() without arguments. |
| 2023-07-14 | `1d0dfc0b92` | HELD | 4 | high | Refs #30686 -- Moved Parser.SELF_CLOSING_TAGS to django.utils.html.VOI |
| 2024-03-14 | `95ae37839c` | HELD | 4 | high | Refs #30686 -- Made django.utils.html.VOID_ELEMENTS a frozenset. |
| 2024-07-09 | `d666457453` | HELD | 4 | high | Fixed CVE-2024-38875 -- Mitigated potential DoS in urlize and urlizetr |
| 2024-08-06 | `5f1757142f` | HELD | 4 | high | Fixed CVE-2024-41991 -- Prevented potential ReDoS in django.utils.html |
| 2024-08-06 | `ecf1f8fb90` | HELD | 4 | high | Fixed CVE-2024-41990 -- Mitigated potential DoS in urlize and urlizetr |
| 2024-08-20 | `231c0d8593` | HELD | 4 | high | Fixed #35668 -- Added mapping support to format_html_join. |
| 2024-08-27 | `2b71b2c8dc` | HELD | 4 | high | Refs #34609 -- Fixed deprecation warning stack level in format_html(). |
| 2024-09-03 | `320dd27412` | HELD | 4 | high | Fixed CVE-2024-45230 -- Mitigated potential DoS in urlize and urlizetr |
| 2024-12-04 | `49ff1042aa` | HELD | 4 | high | Fixed CVE-2024-53907 -- Mitigated potential DoS in strip_tags(). |
| 2024-12-17 | `322e49ba30` | HELD | 4 | high | Fixed #36012 -- Made mailto punctuation percent-encoded in Urlizer. |

### CVE-2019-14235

_range 76ed1c49f8..8d9901c961: 11 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2019-08-28 | `1e6b9e29e6` | HELD | 1 | high | Refs #27795 -- Removed an unnecessary force_bytes() call in uri_to_iri |
| 2019-10-30 | `6315a272c5` | HELD | 1 | high | Refs #28428 -- Made filepath_to_uri() support pathlib.Path. |
| 2020-04-20 | `505fec6bad` | HELD | 1 | high | Capitalized Unicode in docs, strings, and comments. |
| 2021-01-14 | `810f037b29` | HELD | 1 | high | Refs #27753 -- Removed django.utils.encoding.force_text() and smart_te |
| 2021-05-29 | `5685b7cd73` | HELD | 1 | high | Fixed typos in comments and docs. |
| 2022-02-07 | `9c19aff7c7` | HELD | 1 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-03-08 | `d4fd31684a` | HELD | 1 | high | Refs #33173 -- Used locale.getlocale() instead of getdefaultlocale(). |
| 2022-11-10 | `9bd174b9a7` | HELD | 1 | high | Updated documentation and comments for RFC updates. |
| 2023-01-18 | `fd21f82aa8` | HELD | 1 | high | Refs #34233 -- Used types.NoneType. |
| 2023-09-04 | `3f41d6d629` | HELD | 1 | high | Fixed CVE-2023-41164 -- Fixed potential DoS in django.utils.encoding.u |
| 2023-11-27 | `174369a990` | HELD | 1 | high | Refs #34986 -- Avoided pickling error in DjangoUnicodeDecodeError. |

### CVE-2019-19118 (sampled)

_range 11c5e0609b..8d9901c961: 65 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2020-01-17 | `68e018010b` | HELD | 2 | medium | Optimized ModelAdmin._changeform_view() by avoiding multiple get_field |
| 2020-04-15 | `d51c50d836` | HELD | 2 | medium | Fixed #31462 -- Allowed overriding autocomplete/raw_id_fields/filter w |
| 2020-04-17 | `dfbd9ca065` | HELD | 2 | medium | Fixed #30311 -- Restored ability to override global admin actions. |
| 2020-05-14 | `81ffedaacc` | HELD | 2 | medium | Fixed #31524 -- Removed minified static assets from the admin. |
| 2020-07-30 | `e74b3d724e` | HELD | 2 | medium | Bumped minimum isort version to 5.1.0. |
| 2020-09-11 | `84609b3205` | HELD | 2 | medium | Fixed #31993 -- Added subtitles to admin change/view pages. |
| 2020-11-13 | `fed8129276` | HELD | 2 | medium | Unified admin action description generation. |
| 2021-01-12 | `3071660acf` | HELD | 2 | medium | Fixed #29010, Fixed #29138 -- Added limit_choices_to and to_field supp |
| 2021-02-15 | `3119a6deca` | HELD | 2 | medium | Fixed #26607 -- Allowed customizing formset kwargs with ModelAdmin.get |
| 2021-04-26 | `4e5bbb6ef2` | HELD | 2 | medium | Fixed #32681 -- Fixed VariableDoesNotExist when rendering some admin t |
| 2021-04-27 | `cd74aad90e` | HELD | 2 | medium | Refs #32682 -- Renamed use_distinct variable to may_have_duplicates. |
| 2021-05-20 | `736bb9868a` | HELD | 2 | medium | Renamed "object" argument of ModelAdmin.log_addition(), log_change(),  |
| 2021-07-05 | `e4da365436` | HELD | 2 | medium | Refs #24121 -- Added __repr__() to AdminSite, DefaultAdminSite, and Mo |
| 2021-07-28 | `9662193aea` | HELD | 2 | medium | Refs #32946 -- Changed internal usage of dynamic Q() objects construct |
| 2021-09-21 | `2f0f30f973` | HELD | 2 | medium | Fixed #33111 -- Fixed passing object to ModelAdmin.get_inlines() when  |
| 2021-12-15 | `76ccce64cc` | HELD | 2 | medium | Fixed #16063 -- Adjusted admin changelist searches spanning multi-valu |
| 2021-12-15 | `ac5cc6cf01` | HELD | 2 | medium | Fixed #33316 -- Added pagination to admin history view. |
| 2022-02-07 | `9c19aff7c7` | HELD | 4 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-02-26 | `e0442a628e` | HELD | 4 | high | Fixed #33527 -- Removed unnecessary code in ModelAdmin._changeform_vie |
| 2022-02-28 | `119f227aa6` | HELD | 4 | high | Fixed #33524 -- Allowed overriding empty_label for ForeignKey in Model |
| 2022-06-22 | `d80a258553` | HELD | 4 | high | Fixed #33028 -- Used ModelAdmin's opts attribute instead of model._met |
| 2022-06-28 | `eb7b8f3699` | HELD | 4 | high | Fixed #33805 -- Made admin's many-to-many widgets do not display help  |
| 2022-07-27 | `9dff316be4` | HELD | 4 | high | Refs #32948, Refs #32946 -- Used Q.create() internally for dynamic Q() |
| 2022-09-24 | `0f31d10c7c` | HELD | 4 | high | Fixed #34023 -- Added inline argument to user_deleted_form(). |
| 2022-10-06 | `7a39a691e1` | HELD | 4 | high | Fixed #32603 -- Made ModelAdmin.list_editable use transactions. |
| 2022-11-08 | `41e8931c2c` | HELD | 4 | high | Fixed typo in BaseModelAdmin.has_delete_permission()'s docstring. |
| 2023-02-01 | `097e3a70c1` | HELD | 4 | high | Refs #33476 -- Applied Black's 2023 stable style. |
| 2023-02-16 | `85366fbca7` | HELD | 4 | high | Fixed #34045 -- Improved accessibility of selecting items in admin cha |
| 2023-03-28 | `45ecd9acca` | HELD | 4 | high | Fixed #28384 -- Fixed ModelAdmin.lookup_allowed() for OneToOneField pr |
| 2023-07-07 | `2584783f46` | HELD | 4 | high | Refs #9602 -- Moved AlreadyRegistered/NotRegistered exceptions to djan |
| 2023-07-07 | `f64fd47a76` | HELD | 4 | high | Fixed #9602 -- Added AdminSite.get_model_admin(). |
| 2023-10-17 | `4a5048b036` | HELD | 4 | high | Removed unreachable code from ModelAdmin.response_change(). |
| 2023-12-07 | `f80669d2f5` | HELD | 4 | high | Fixed #35020 -- Fixed ModelAdmin.lookup_allowed() for non-autofield pr |
| 2024-01-08 | `a9094ec1f4` | HELD | 4 | high | Fixed #35087 -- Reallowed filtering against foreign keys not listed in |
| 2024-02-14 | `8db593de05` | HELD | 4 | high | Fixed #35173 -- Fixed ModelAdmin.lookup_allowed() for lookups on forei |
| 2024-02-21 | `98e6f2396c` | HELD | 4 | high | Fixed #35237 -- Merged system checks for admin actions. |
| 2024-05-29 | `ff308a0604` | HELD | 4 | high | Fixed 35467 -- Replaced urlparse with urlsplit where appropriate. |
| 2024-07-18 | `182f262b15` | HELD | 4 | high | Fixed #35606, Refs #34045 -- Fixed rendering of ModelAdmin.action_chec |
| 2024-08-07 | `54888408a1` | HELD | 4 | high | Fixed #35639 -- Improved admin's delete confirmation page title. |
| 2024-11-05 | `5fa4ccab7e` | HELD | 4 | high | Refs #26001 -- Handled relationship exact lookups in ModelAdmin.search |

### CVE-2019-19844

_range 5b1fbcef7a..8d9901c961: 19 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2020-04-28 | `9ef4a18dbe` | HELD | 2 | medium | Changed django.forms.ValidationError imports to django.core.exceptions |
| 2020-10-28 | `302caa40e4` | HELD | 2 | medium | Made small readability improvements. |
| 2020-12-03 | `d8dfff2ab0` | HELD | 2 | medium | Fixed #32235 -- Made ReadOnlyPasswordHashField disabled by default. |
| 2021-05-19 | `536c155e67` | HELD | 2 | medium | Fixed #32765 -- Removed "for" HTML attribute from ReadOnlyPasswordHash |
| 2022-02-07 | `9c19aff7c7` | HELD | 4 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-10-26 | `b440493eaa` | HELD | 4 | high | Completed test coverage for contrib.auth.forms. |
| 2022-10-27 | `de2c2127b6` | HELD | 4 | high | Fixed #34066 -- Fixed link to password reset view in UserChangeForm.pa |
| 2022-11-11 | `1be7e36f85` | HELD | 4 | high | Fixed typo in SetPasswordForm()'s docstring. |
| 2022-11-29 | `9d726c7902` | HELD | 4 | high | Fixed #34187 -- Made UserCreationForm save many-to-many fields. |
| 2022-12-29 | `298d02a77a` | HELD | 4 | high | Fixed #25617 -- Added case-insensitive unique username validation in U |
| 2023-03-28 | `fcc7dc5781` | HELD | 4 | high | Fixed #34438 -- Reallowed extending UserCreationForm. |
| 2023-11-01 | `05ba4130ee` | HELD | 4 | high | Fixed CVE-2023-46695 -- Fixed potential DoS in UsernameField on Window |
| 2024-02-20 | `e626716c28` | HELD | 4 | high | Fixed #34429 -- Allowed setting unusable passwords for users in the au |
| 2024-02-20 | `f64c528c17` | HELD | 4 | high | Refs #34429 -- Created `SetPasswordMixin` to reuse password validation |
| 2024-03-27 | `944745afe2` | HELD | 4 | high | Fixed #34977 -- Improved accessibility in the UserChangeForm by replac |
| 2024-05-30 | `339977d444` | HELD | 4 | high | Fixed #35477 -- Corrected 'required' errors in auth password set/chang |
| 2024-08-19 | `0ebed5fa95` | HELD | 4 | high | Fixed #35678 -- Removed "usable_password" field from BaseUserCreationF |
| 2024-09-03 | `8c35a0a903` | HELD | 4 | high | Fixed CVE-2024-45231 -- Avoided server error on password reset when em |
| 2024-11-15 | `037e740ec5` | HELD | 4 | high | Refs #28215 -- Marked auth form passwords as sensitive variables. |

### CVE-2020-13596

_range 2dd4d110c1..8d9901c961: 17 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2021-01-12 | `3071660acf` | HELD | 1 | high | Fixed #29010, Fixed #29138 -- Added limit_choices_to and to_field supp |
| 2021-03-18 | `03d0f12c82` | HELD | 2 | medium | Fixed #32466 -- Corrected autocomplete to_field resolution for complex |
| 2021-09-21 | `8eb5693091` | HELD | 2 | medium | Fixed #33070 -- Fixed loading translations with language subtags in ad |
| 2021-11-29 | `05e29da421` | HELD | 2 | medium | Fixed #32545 -- Improved admin widget for raw_id_fields for UUIDFields |
| 2022-02-07 | `9c19aff7c7` | HELD | 4 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-02-18 | `3079133c73` | HELD | 4 | high | Fixed #33514 -- Added fallbacks to subsequent language codes in Select |
| 2022-02-25 | `11cc227344` | HELD | 4 | high | Fixed #33267 -- Added link to related item to related widget wrapper i |
| 2022-04-15 | `c72f6f36c1` | HELD | 4 | high | Fixed #11803 -- Allowed admin select widgets to display new related ob |
| 2022-08-03 | `0638b4e23d` | HELD | 4 | high | Fixed #33888 -- Fixed get_select2_language() crash with no language ac |
| 2023-06-09 | `caf80cb41f` | HELD | 4 | high | Fixed #34645 -- Restored alignment for admin date/time timezone warnin |
| 2023-07-06 | `95cdf9dc66` | HELD | 4 | high | Used AdminSite.is_registered() where appropriate. |
| 2023-08-30 | `500e01073a` | HELD | 4 | high |  Fixed #31262 -- Added support for mappings on model fields and Choice |
| 2023-12-14 | `2190096f50` | HELD | 4 | medium | Used model's Options.model_name instead of object_name.lower(). |
| 2024-01-26 | `305757aec1` | HELD | 4 | high | Applied Black's 2024 stable style. |
| 2024-04-02 | `8665cf03d7` | HELD | 4 | high | Fixed #35330 -- Fixed the update of related widgets when the reference |
| 2024-06-12 | `719a42b589` | HELD | 4 | high | Fixed #34789 -- Prevented updateRelatedSelectsOptions from  adding ent |
| 2024-08-06 | `5f1757142f` | HELD | 4 | high | Fixed CVE-2024-41991 -- Prevented potential ReDoS in django.utils.html |

### CVE-2020-24583

_range 8d7271578d..8d9901c961: 16 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2021-03-19 | `474cc420bf` | HELD | 1 | high | Refs #32508 -- Raised Type/ValueError instead of using "assert" in dja |
| 2021-05-04 | `0b79eb3691` | HELD | 1 | high | Fixed CVE-2021-31542 -- Tightened path & file name sanitation in file  |
| 2021-05-12 | `d06c5b3581` | HELD | 1 | high | Fixed #32366 -- Updated datetime module usage to recommended approach. |
| 2021-06-02 | `ec2727efef` | HELD | 1 | high | Fixed #28154 -- Prevented infinite loop in FileSystemStorage.save() wh |
| 2021-06-07 | `7272e1963f` | HELD | 1 | high | Fixed #32821 -- Updated os.scandir() uses to use a context manager. |
| 2021-07-29 | `1024b5e74a` | HELD | 1 | high | Fixed 32956 -- Lowercased spelling of "web" and "web framework" where  |
| 2022-01-04 | `6d343d01c5` | HELD | 1 | high | Fixed CVE-2021-45452 -- Fixed potential path traversal in storage subs |
| 2022-02-07 | `7119f40c98` | HELD | 1 | high | Refs #33476 -- Refactored code to strictly match 88 characters line le |
| 2022-02-07 | `9c19aff7c7` | HELD | 1 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-03-24 | `bb61f0186d` | HELD | 1 | high | Refs #32365 -- Removed internal uses of utils.timezone.utc alias. |
| 2022-04-11 | `884b4c27f5` | HELD | 1 | high | Fixed #32604 -- Made file upload respect group id when uploading to a  |
| 2022-11-11 | `032c09c414` | HELD | 1 | high | Refs #34110 -- Reorganized django.core.files.storage into a separate m |
| 2022-11-11 | `99b4f90ec6` | HELD | 1 | high | Refs #34110 -- Added StorageSettingsMixin. |
| 2024-05-21 | `0b33a3abc2` | REGRESSED | 1 | high | Fixed #35326 -- Added allow_overwrite parameter to FileSystemStorage. |
| 2024-07-24 | `8d6a20b656` | REGRESSED | 1 | high | Fixed #35604, Refs #35326 -- Made FileSystemStorage.exists() behaviour |
| 2024-08-28 | `47f18a7226` | REGRESSED | 1 | high | Refs #35326 -- Adjusted deprecation warning stacklevel in FileSystemSt |

### CVE-2021-28658

_range d4d800ca1a..8d9901c961: 15 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2021-04-05 | `5def7f3f74` | HELD | 1 | high | Updated various links to HTTPS and new locations. |
| 2021-04-14 | `0b79eb3691` | HELD | 1 | high | Fixed CVE-2021-31542 -- Tightened path & file name sanitation in file  |
| 2022-01-17 | `3fadf141e6` | HELD | 1 | high | Fixed #33062 -- Made MultiPartParser remove non-printable chars from f |
| 2022-01-21 | `fc18f36c4a` | HELD | 1 | high | Fixed CVE-2022-23833 -- Fixed DoS possiblity in file uploads. |
| 2022-02-03 | `9c19aff7c7` | HELD | 1 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-02-04 | `7119f40c98` | HELD | 1 | high | Refs #33476 -- Refactored code to strictly match 88 characters line le |
| 2022-05-10 | `34e2148fc7` | HELD | 1 | high | Refs #33173 -- Removed use of deprecated cgi module. |
| 2022-05-27 | `93cedc82f2` | HELD | 1 | high | Refs #33697 -- Fixed multipart parsing of headers with double quotes a |
| 2022-06-03 | `49b470b918` | HELD | 1 | high | Refs #33697 -- Made MultiPartParser use django.utils.http.parse_header |
| 2022-06-28 | `bff5c114be` | HELD | 1 | high | Removed unnecessary _parse_header() from MultiPartParser. |
| 2022-06-28 | `d4d5427571` | HELD | 4 | medium | Refs #33697 -- Used django.utils.http.parse_header_parameters() for pa |
| 2022-11-04 | `9bd174b9a7` | HELD | 4 | medium | Updated documentation and comments for RFC updates. |
| 2022-12-13 | `85ac33591c` | HELD | 4 | medium | Fixed CVE-2023-24580 -- Prevented DoS with too many uploaded files. |
| 2023-11-10 | `1c6e8ec4ed` | HELD | 4 | medium | Fixed #34968 -- Made multipart parsing of headers raise an error on to |
| 2024-01-26 | `305757aec1` | HELD | 4 | medium | Applied Black's 2024 stable style. |

### CVE-2021-33203

_range 46572de2e9..8d9901c961: 12 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2021-09-22 | `27189af8cf` | HELD | 2 | medium | Refs #32499 -- Added metacharacters helper for simplify_regex(). |
| 2022-01-14 | `0a17666045` | HELD | 2 | medium | Fixed #28135 -- Made simplify_regex() handle non-capturing groups. |
| 2022-02-07 | `9c19aff7c7` | HELD | 2 | medium | Refs #33476 -- Reformatted code with Black. |
| 2022-05-06 | `21d8ea4eb3` | HELD | 2 | medium | Corrected extract_views_from_urlpatterns()'s docstring. |
| 2022-05-17 | `7f3cfaa12b` | HELD | 2 | medium | Fixed #32565 -- Moved internal URLResolver view-strings mapping to adm |
| 2022-09-01 | `974942a750` | HELD | 2 | medium | Fixed #33955, Fixed #33971 -- Reverted "Fixed #32565 -- Moved internal |
| 2023-02-01 | `097e3a70c1` | HELD | 2 | medium | Refs #33476 -- Applied Black's 2023 stable style. |
| 2023-06-23 | `f8092ee9ad` | HELD | 2 | medium | Improved style of n-tuple wording in docs and comments. |
| 2024-01-29 | `b7154f811f` | HELD | 2 | medium | Fixed #24128 -- Made admindocs TemplateDetailView respect template_loa |
| 2024-02-19 | `5e80390add` | HELD | 2 | medium | Fixed #35230 -- Added cached ForeignObjectRel.accessor_name. |
| 2024-11-04 | `968397228f` | HELD | 2 | medium | Fixed #35867, Refs #2411 -- Allowed links in admindocs view details su |
| 2024-11-11 | `c12bc980e5` | HELD | 2 | medium | Fixed #17905 -- Restricted access to model pages in admindocs. |

### CVE-2021-33571

_range e1d787f1b3..8d9901c961: 18 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2021-07-22 | `65b880b726` | HELD | 2 | medium | Fixed #32930 -- Fixed URLValidator when port numbers < 10. |
| 2021-08-06 | `ee46722cb9` | HELD | 2 | medium | Fixed typo in regex for IPv6 literals in EmailValidator. |
| 2021-09-20 | `d25710a625` | HELD | 2 | medium | Refs #31670 -- Removed whitelist argument and domain_whitelist attribu |
| 2021-12-20 | `e8b4feddc3` | HELD | 2 | medium | Fixed #33367 -- Fixed URLValidator crash in some edge cases. |
| 2022-01-07 | `bdf3e156b4` | HELD | 4 | high | Fixed #28628 -- Changed \d to [0-9] in regexes where appropriate. |
| 2022-02-07 | `7119f40c98` | HELD | 4 | high | Refs #33476 -- Refactored code to strictly match 88 characters line le |
| 2022-02-07 | `9c19aff7c7` | HELD | 4 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-05-12 | `3a82b5f655` | HELD | 4 | high | Fixed #32559 -- Added 'step_size’ to numeric form fields. |
| 2022-09-17 | `ae509f8f08` | HELD | 4 | high | Fixed #34014 -- Fixed DecimalValidator validating 0 in positive expone |
| 2023-01-18 | `3bbe22dafc` | MOVED | 4 | medium | Fixed #34233 -- Dropped support for Python 3.8 and 3.9. |
| 2023-06-16 | `1fe0b167af` | HELD | 4 | high | Fixed #34473 -- Fixed step validation for form fields with non-zero mi |
| 2023-07-03 | `ad0410ec4f` | HELD | 4 | high | Fixed CVE-2023-36053 -- Prevented potential ReDoS in EmailValidator an |
| 2023-10-24 | `d22ba07630` | HELD | 4 | high | Fixed #34920 -- Made FileExtensionValidator.__eq__() ignore allowed_ex |
| 2023-10-28 | `a6c7db1d1d` | HELD | 4 | high | Fixed #34943 -- Made EmailValidator.__eq__() ignore domain_allowlist o |
| 2023-11-24 | `eabfa2d0e3` | HELD | 4 | high | Fixed #34818 -- Prevented GenericIPAddressField from mutating error me |
| 2024-05-21 | `4971a9afe5` | HELD | 4 | high | Fixed #18119 -- Added a DomainNameValidator validator. |
| 2024-10-17 | `99dcc59237` | HELD | 4 | high | Fixed #35845 -- Updated DomainNameValidator to require entire string t |
| 2024-12-13 | `5405912595` | HELD | 4 | high | Fixed #36007 -- Removed dead code from URLValidator. |

### CVE-2021-45116

_range 761f449e0d..8d9901c961: 13 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2022-01-10 | `3d7ac6420c` | HELD | 2 | medium | Simplified @stringfilter decorator and Library with unwrap(). |
| 2022-02-07 | `9c19aff7c7` | HELD | 4 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-07-23 | `4d4bf55e0e` | HELD | 4 | high | Fixed #33864 -- Deprecated length_is template filter. |
| 2022-10-24 | `08c5a78726` | HELD | 4 | high | Fixed #34098 -- Fixed loss of precision for Decimal values in floatfor |
| 2023-01-19 | `4b066bde69` | HELD | 4 | high | Fixed #34272 -- Fixed floatformat crash on zero with trailing zeros to |
| 2023-02-22 | `dcd9746983` | HELD | 4 | high | Fixed #34363 -- Fixed floatformat crash on zero with trailing zeros. |
| 2023-04-26 | `7d0e566208` | HELD | 4 | high | Fixed #34518 -- Fixed crash of random() template filter with an empty  |
| 2023-05-19 | `a2da81fe08` | HELD | 4 | high | Fixed #34578 -- Made "join" template filter respect autoescape for joi |
| 2023-05-22 | `061a8a1bd8` | HELD | 4 | high | Fixed #34577 -- Added escapeseq template filter. |
| 2023-09-18 | `14ef92fa9e` | HELD | 4 | high | Refs #33864 -- Removed length_is template filter per deprecation timel |
| 2024-01-26 | `305757aec1` | HELD | 4 | high | Applied Black's 2024 stable style. |
| 2024-04-24 | `e64d42e753` | HELD | 4 | high | Fixed #35395 -- slice filter crashes on an empty dict with Python 3.12 |
| 2024-08-06 | `c19465ad87` | HELD | 4 | high | Fixed CVE-2024-41989 -- Prevented excessive memory consumption in floa |

### CVE-2021-45452

_range 6d343d01c5..8d9901c961: 9 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2022-02-07 | `7119f40c98` | HELD | 1 | high | Refs #33476 -- Refactored code to strictly match 88 characters line le |
| 2022-02-07 | `9c19aff7c7` | HELD | 1 | high | Refs #33476 -- Reformatted code with Black. |
| 2022-03-24 | `bb61f0186d` | HELD | 1 | high | Refs #32365 -- Removed internal uses of utils.timezone.utc alias. |
| 2022-04-11 | `884b4c27f5` | HELD | 1 | high | Fixed #32604 -- Made file upload respect group id when uploading to a  |
| 2022-11-11 | `032c09c414` | HELD | 1 | high | Refs #34110 -- Reorganized django.core.files.storage into a separate m |
| 2022-11-11 | `99b4f90ec6` | HELD | 1 | high | Refs #34110 -- Added StorageSettingsMixin. |
| 2024-05-21 | `0b33a3abc2` | HELD | 4 | medium | Fixed #35326 -- Added allow_overwrite parameter to FileSystemStorage. |
| 2024-07-24 | `8d6a20b656` | HELD | 4 | medium | Fixed #35604, Refs #35326 -- Made FileSystemStorage.exists() behaviour |
| 2024-08-28 | `47f18a7226` | HELD | 4 | medium | Refs #35326 -- Adjusted deprecation warning stacklevel in FileSystemSt |

### CVE-2022-22818

_range 394517f078..8d9901c961: 9 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2022-02-03 | `c5cd878382` | HELD | 1 | high | Refs #33476 -- Refactored problematic code before reformatting by Blac |
| 2022-02-07 | `7119f40c98` | HELD | 1 | high | Refs #33476 -- Refactored code to strictly match 88 characters line le |
| 2022-02-07 | `9c19aff7c7` | HELD | 1 | high | Refs #33476 -- Reformatted code with Black. |
| 2023-02-01 | `097e3a70c1` | HELD | 1 | high | Refs #33476 -- Applied Black's 2023 stable style. |
| 2023-05-18 | `4e73d8c04d` | HELD | 1 | high | Avoided parallel assignment in template classes. |
| 2023-10-26 | `e67d3580ed` | HELD | 1 | high | Fixed #10941 -- Added {% query_string %} template tag. |
| 2023-11-24 | `5e28cd3f2c` | HELD | 1 | high | Fixed #34983 -- Deprecated django.utils.itercompat.is_iterable(). |
| 2024-01-26 | `305757aec1` | HELD | 1 | high | Applied Black's 2024 stable style. |
| 2024-07-15 | `27043bde5b` | HELD | 1 | high | Refs #10941 -- Renamed query_string template tag to querystring. |

### CVE-2022-28346 (sampled)

_range 93cae5cb2f..8d9901c961: 67 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2022-04-11 | `6723a26e59` | HELD | 1 | high | Fixed CVE-2022-28347 -- Protected QuerySet.explain(**options) against  |
| 2022-04-26 | `4282fd468f` | HELD | 1 | high | Fixed #33655 -- Removed unnecessary constant from GROUP BY clause for  |
| 2022-05-13 | `19dc3f0f96` | HELD | 1 | high | Fixed typo in Query.clone()'s docstring. |
| 2022-07-04 | `425718726b` | HELD | 1 | high | Fixed #33816 -- Fixed QuerySet.only() after select_related() crash on  |
| 2022-08-30 | `b3db6c8dcb` | HELD | 1 | high | Fixed #21204 -- Tracked field deferrals by field instead of models. |
| 2022-09-09 | `32797e7fbf` | HELD | 1 | high | Fixed #33975 -- Fixed __in lookup when rhs is a queryset with annotate |
| 2022-10-04 | `4771a1694b` | HELD | 1 | high | Fixed #34012 -- Made QuerySet.order_by() apply transforms on related f |
| 2022-10-06 | `3d734c09ff` | HELD | 1 | high | Refs #33992 -- Refactored subquery grouping logic. |
| 2022-10-31 | `d3cb91db87` | HELD | 1 | high | Used more augmented assignment statements. |
| 2022-11-09 | `59bea9efd2` | HELD | 1 | high | Fixed #28477 -- Stripped unused annotations on aggregation. |
| 2022-11-14 | `10037130c1` | HELD | 1 | high | Refs #28477 -- Fixed handling aliased annotations on aggregation. |
| 2022-11-14 | `b181cae2e3` | HELD | 1 | high | Refs #25307 -- Replaced SQLQuery.rewrite_cols() by replace_expressions |
| 2022-11-23 | `1297c0d0d7` | HELD | 1 | high | Fixed #31679 -- Delayed annotating aggregations. |
| 2023-01-09 | `dd68af62b2` | HELD | 1 | high | Fixed #34176 -- Fixed grouping by ambiguous aliases. |
| 2023-03-20 | `f9f9215d3e` | HELD | 2 | medium | Fixed some typos in comments, docstrings, and tests. |
| 2023-03-24 | `d6b6e5d0fd` | HELD | 2 | medium | Fixed #28553 -- Fixed annotation mismatch with QuerySet.values()/value |
| 2023-03-28 | `3afdc9e9b4` | HELD | 2 | medium | Refs #29799 -- Added field instance lookups to suggestions in FieldErr |
| 2023-04-05 | `87c63bd8df` | HELD | 2 | medium | Fixed #34458 -- Fixed QuerySet.defer() crash on attribute names. |
| 2023-04-07 | `9daf8b4109` | HELD | 2 | medium | Fixed #34464 -- Fixed queryset aggregation over group by reference. |
| 2023-04-24 | `83c9765f45` | HELD | 2 | medium | Refs #33766 -- Removed sql.Query.build_filtered_relation_q(). |
| 2023-05-23 | `2ee01747c3` | HELD | 2 | medium | Refs #34551 -- Fixed QuerySet.aggregate() crash on precending aggregat |
| 2023-06-01 | `2cf76f2d5d` | HELD | 2 | medium | Fixed #34612 -- Fixed QuerySet.only() crash on reverse relationships. |
| 2023-06-14 | `cfc9c94d97` | HELD | 2 | medium | Refs #32143 -- Adjusted a comment about subquery usage in Query.split_ |
| 2023-07-19 | `68912e4f6f` | HELD | 2 | medium | Fixed #34717 -- Fixed QuerySet.aggregate() crash when referencing wind |
| 2023-08-01 | `c9b9a52edc` | HELD | 2 | medium | Fixed #34750 -- Fixed QuerySet.count() when grouping by unused multi-v |
| 2023-08-02 | `9b9c805ced` | HELD | 2 | medium | Removed unneeded escapes in regexes. |
| 2023-08-11 | `59f4754704` | HELD | 2 | medium | Fixed #34362 -- Fixed FilteredRelation() crash on conditional expressi |
| 2023-11-18 | `15cb3c262a` | HELD | 2 | medium | Refs #34975 -- Complemented rhs filtering aggregations for __in lookup |
| 2023-11-18 | `7530cf3900` | HELD | 2 | medium | Fixed #34975 -- Fixed crash of conditional aggregate() over aggregatio |
| 2023-12-16 | `77278929c8` | HELD | 2 | medium | Fixed #35042 -- Fixed a count() crash on combined queries. |
| 2024-01-15 | `f3d10546a8` | HELD | 2 | medium | Refs #35102 -- Optimized replace_expressions()/relabelling aliases by  |
| 2024-01-26 | `305757aec1` | HELD | 2 | medium | Applied Black's 2024 stable style. |
| 2024-02-07 | `d79fba7d8e` | HELD | 2 | medium | Fixed #35099 -- Prevented mutating queryset when combining with & and  |
| 2024-04-23 | `195d885ca0` | HELD | 2 | medium | Refs #35356 -- Clarified select related with masked field logic. |
| 2024-07-03 | `0e65abd2d9` | HELD | 2 | medium | Refs #28900 -- Made Query.has_select_fields a computed property. |
| 2024-07-03 | `65ad4ade74` | HELD | 2 | medium | Refs #28900 -- Made SELECT respect the order specified by values(*sele |
| 2024-07-23 | `f9bf616597` | HELD | 2 | medium | Fixed #35585 -- Corrected Query.exists() call in Query.has_results(). |
| 2024-08-06 | `c87bfaacf8` | HELD | 2 | medium | Fixed CVE-2024-42005 -- Mitigated QuerySet.values() SQL injection atta |
| 2024-08-12 | `e03083917d` | HELD | 2 | medium | Fixed #35586 -- Added support for set-returning database functions. |
| 2024-11-29 | `978aae4334` | HELD | 2 | medium | Fixed #373 -- Added CompositePrimaryKey. |

### CVE-2022-34265

_range 54eb8a374d..8d9901c961: 18 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2022-07-06 | `877c800f25` | REGRESSED | 4 | high | Refs CVE-2022-34265 -- Properly escaped Extract() and Trunc() paramete |
| 2022-10-03 | `649b28eab6` | REGRESSED | 4 | medium | Fixed #34070 -- Added subsecond support to Now() on SQLite and MySQL. |
| 2022-10-24 | `577dbcbb4f` | REGRESSED | 4 | medium | Refs #34070 -- Fixed date format in Now() on SQLite. |
| 2022-11-15 | `5c23d9f0c3` | HELD | 4 | medium | Refs #33308 -- Used get_db_prep_value() to adapt JSONFields. |
| 2022-12-15 | `09ffc5c121` | REGRESSED | 4 | high | Fixed #33308 -- Added support for psycopg version 3. |
| 2023-01-17 | `2fad163257` | REGRESSED | 4 | medium | Refs #32365 -- Removed is_dst argument for various methods and functio |
| 2023-02-01 | `097e3a70c1` | REGRESSED | 4 | medium | Refs #33476 -- Applied Black's 2023 stable style. |
| 2023-04-18 | `9bbf97bcdb` | REGRESSED | 4 | high | Fixed #16055 -- Fixed crash when filtering against char/text GenericRe |
| 2023-05-11 | `72a86ceb33` | REGRESSED | 4 | medium | Fixed #34558 -- Fixed QuerySet.bulk_create() crash with Now() on Oracl |
| 2023-07-30 | `22b0b73c77` | REGRESSED | 4 | medium | Fixed warnings per flake8 6.1.0. |
| 2023-08-31 | `27b399d235` | UNVERIFIABLE | 2 | low | Fixed #34547 -- Deprecated DatabaseOperations.field_cast_sql(). |
| 2023-10-28 | `6375cee490` | UNVERIFIABLE | 2 | low | Refs #29850 -- Added RowRange support for positive integer start and n |
| 2023-11-13 | `b863c5ffde` | UNVERIFIABLE | 2 | low | Fixed #34967 -- Fixed queryset crash when grouping by constants on SQL |
| 2024-01-16 | `0fcee1676c` | UNVERIFIABLE | 2 | low | Fixed #35111 -- Fixed compilation of DateField __in/__range rhs on SQL |
| 2024-01-26 | `305757aec1` | UNVERIFIABLE | 2 | low | Applied Black's 2024 stable style. |
| 2024-03-14 | `912f72a6f0` | UNVERIFIABLE | 2 | low | Refs #35295 -- Added BaseDatabaseOperations.bulk_insert_sql(). |
| 2024-08-28 | `a69f895d7d` | UNVERIFIABLE | 2 | low | Refs #34547 -- Adjusted deprecation warning stacklevel in DatabaseOper |
| 2024-12-09 | `b0b3024720` | UNVERIFIABLE | 2 | low | Refs #35982 -- Made BaseDatabaseOperations.adapt_decimalfield_value()  |

### CVE-2022-36359

_range bd062445cf..8d9901c961: 12 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2022-09-14 | `6220c445c4` | HELD | 1 | high | Fixed #29186 -- Fixed pickling HttpRequest and subclasses. |
| 2022-10-31 | `d3cb91db87` | HELD | 1 | high | Used more augmented assignment statements. |
| 2022-12-05 | `cbce427c17` | HELD | 1 | high | Fixed #34194 -- Added django.utils.http.content_disposition_header(). |
| 2022-12-22 | `0bd2c0c901` | HELD | 1 | high | Fixed #33735 -- Added async support to StreamingHttpResponse. |
| 2023-01-18 | `26a395f27d` | HELD | 1 | high | Refs #34233 -- Used aiter() and anext(). |
| 2023-03-14 | `254ad2e345` | HELD | 1 | high | Fixed #34405 -- Fixed setting Content-Type header in FileResponse for  |
| 2023-04-12 | `173034b005` | HELD | 1 | high | Refs #34482 -- Reverted "Fixed #32969 -- Fixed pickling HttpResponse a |
| 2023-04-12 | `280ca147af` | HELD | 1 | high | Fixed #34484, Refs #34482 -- Reverted "Fixed #29186 -- Fixed pickling  |
| 2024-05-29 | `ff308a0604` | HELD | 1 | high | Fixed 35467 -- Replaced urlparse with urlsplit where appropriate. |
| 2024-08-28 | `c042fe3a74` | HELD | 1 | high | Refs #33735 -- Adjusted warning stacklevel in StreamingHttpResponse.__ |
| 2024-10-16 | `4a685bc0dc` | HELD | 1 | high | Fixed #35727 -- Added HttpResponse.text property. |
| 2024-11-14 | `91c879eda5` | HELD | 1 | high | Fixed #35784 -- Added support for preserving the HTTP request method i |

### CVE-2023-23969

_range 8c660fb592..8d9901c961: 5 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2023-05-02 | `0e444e84f8` | HELD | 1 | high | Fixed #34515 -- Made LocaleMiddleware prefer language from paths when  |
| 2024-01-26 | `305757aec1` | HELD | 1 | high | Applied Black's 2024 stable style. |
| 2024-07-09 | `9e9792228a` | HELD | 1 | high | Fixed CVE-2024-39614 -- Mitigated potential DoS in get_supported_langu |
| 2024-07-25 | `0e94f292cd` | HELD | 1 | high | Fixed #35627 -- Raised a LookupError rather than an unhandled ValueErr |
| 2024-09-16 | `b579485d99` | HELD | 1 | high | Fixed #34221 -- Honored translation precedence with mixed plural forms |

### CVE-2023-31047

_range fb4c55d9ec..8d9901c961: 5 commits touch scope_

| date | commit | status | tier | conf | subject |
|---|---|---|---|---|---|
| 2023-08-30 | `500e01073a` | HELD | 2 | medium |  Fixed #31262 -- Added support for mappings on model fields and Choice |
| 2024-01-26 | `305757aec1` | HELD | 2 | medium | Applied Black's 2024 stable style. |
| 2024-07-31 | `30a60e8492` | HELD | 2 | medium | Fixed #35598 -- Added SearchInput widget. |
| 2024-08-02 | `946c3cf734` | HELD | 2 | medium | Fixed #35599 -- Added ColorInput widget. |
| 2024-08-02 | `b478cae006` | HELD | 2 | medium | Fixed #35601 -- Added TelInput widget. |

