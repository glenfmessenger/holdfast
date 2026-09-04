# Holdfast eval

Labels: `results/labels.json` (written 2026-09-03, before walks). 25 pairs; 24 evaluated, 1 not walked.

## REGRESSED detection

- Precision: 1/1 = 1.00  [Wilson 95%: 0.21, 1.00]
- Recall:    1/1 = 1.00  [Wilson 95%: 0.21, 1.00]
- Exact status agreement (HELD vs MOVED distinguished): 20/24 = 0.83  [Wilson 95%: 0.64, 0.93]
- Confusion: TP=1 FP=0 FN=0 TN=23
- Verdicts on labelled pairs that depended on tier 4 only: 9/24

## False resurrections (labelled no-regression, tool said REGRESSED)

- none

## Misses (labelled REGRESSED, tool did not say REGRESSED)

- none

## Contract-level expectations (sibling check at creation)

- ✓ **CVE-2019-14232**: expected INCOMPLETE_AT_MERGE; tool: INCOMPLETE_AT_MERGE flagged. Pre-registered as an expected miss.
- ✗ **CVE-2019-14233**: expected INCOMPLETE_AT_MERGE; tool: not flagged (covered=None). Pre-registered as an expected miss.
- ✗ **CVE-2021-45452**: expected INCOMPLETE_AT_MERGE; tool: not flagged (covered=None). Pre-registered as an expected miss.
- ✗ **CVE-2021-28658**: expected INCOMPLETE_AT_MERGE; tool: not flagged (covered=None). Pre-registered as an expected miss.

## All labelled pairs

| contract | commit | expected | got | tier | |
|---|---|---|---|---|---|
| CVE-2019-14232 | 17b51094d7 | HELD | UNVERIFIABLE | t4* | ✗ |
| CVE-2019-14233 | 49ff1042aa | HELD | HELD | t4* | ✓ |
| CVE-2019-14235 | 3f41d6d629 | HELD | HELD | t1 | ✓ |
| CVE-2023-23969 | 9e9792228a | HELD | HELD | t1 | ✓ |
| CVE-2021-45452 | fe4a0bbe20 | HELD | (not walked) | - |  |
| CVE-2021-45452 | 032c09c414 | MOVED | HELD | t1 | ~ |
| CVE-2020-24583 | 032c09c414 | MOVED | HELD | t1 | ~ |
| CVE-2006-5051 | 752250caab | REGRESSED | REGRESSED | t4* | ✓ |
| CVE-2021-28658 | 0b79eb3691 | HELD | HELD | t1 | ✓ |
| CVE-2019-12781 | 8bcb00858e | HELD | HELD | t1 | ✓ |
| CVE-2019-12781 | 9c19aff7c7 | HELD | HELD | t1 | ✓ |
| CVE-2019-14232 | e3d0b4d550 | HELD | HELD | t1 | ✓ |
| CVE-2019-14233 | e3d0b4d550 | HELD | HELD | t2 | ✓ |
| CVE-2019-14235 | 9c19aff7c7 | HELD | HELD | t1 | ✓ |
| CVE-2021-33571 | bdf3e156b4 | HELD | HELD | t4* | ✓ |
| CVE-2022-36359 | cbce427c17 | MOVED | HELD | t1 | ~ |
| CVE-2022-28346 | 1297c0d0d7 | HELD | HELD | t1 | ✓ |
| CVE-2019-19118 | 9c19aff7c7 | HELD | HELD | t4* | ✓ |
| CVE-2019-19844 | f64c528c17 | HELD | HELD | t4* | ✓ |
| CVE-2019-19844 | 9c19aff7c7 | HELD | HELD | t4* | ✓ |
| CVE-2020-13596 | 9c19aff7c7 | HELD | HELD | t4* | ✓ |
| CVE-2021-45116 | 9c19aff7c7 | HELD | HELD | t4* | ✓ |
| CVE-2022-22818 | 9c19aff7c7 | HELD | HELD | t1 | ✓ |
| CVE-2019-12308 | 2dd4d110c1 | HELD | HELD | t1 | ✓ |
| CVE-2021-33203 | 9c19aff7c7 | HELD | HELD | t2 | ✓ |

`t4*` = model-only verdict. `~` = HELD/MOVED swapped (no alarm either way).
