"""Tier-1 execution: run a targeted regression test at a given commit.

The regression test is *extracted from the fix commit's own test changes*: the test
files the fix touched are materialized (from the fix commit) on top of a worktree at
the commit under evaluation, and only the test ids the fix added/modified are run.
This is not synthesized; it is the project's own test, frozen at the fix.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .gitutil import Repo
from .scope import parse_hunks, is_test

WORKTREES = Path(".targets/worktrees").resolve()


@dataclass
class TestSpec:
    kind: str                       # "extracted_from_fix_commit_tests"
    runner: str                     # "django-runtests"
    source_commit: str              # fix commit that the test files come from
    test_files: list[str]
    test_ids: list[str]
    python_hint: str = "auto"


@dataclass
class TestResult:
    outcome: str      # pass | fail | error | timeout | unavailable
    summary: str
    tail: str
    python: str = ""


def extract_test_ids(repo: Repo, fix: str) -> TestSpec | None:
    """Django layout: tests/<app>/<module>.py -> '<app>.<module>.<Class>.<method>'."""
    diff = repo.commit_diff(fix, "--", "tests/")
    specs: list[str] = []
    files: list[str] = []
    for h in parse_hunks(diff):
        if not is_test(h.path) or not h.path.startswith("tests/"):
            continue
        base = h.path.rsplit("/", 1)[-1]
        if not (base == "tests.py" or base.startswith("test_") or "/tests/" in h.path[6:]):
            files.append(h.path)   # helper module (views.py, urls.py ...): carry it, don't run it
            continue
        src = repo.show_file(fix, h.path)
        if src is None:
            continue
        added = {ln for ln, _ in h.added}
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        mod = h.path[len("tests/"):-3].replace("/", ".")
        touched = False
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test")]:
                end = getattr(fn, "end_lineno", fn.lineno)
                if any(fn.lineno <= ln <= end for ln in added):
                    specs.append(f"{mod}.{cls.name}.{fn.name}")
                    touched = True
        # Module-level constants used by tests (e.g. a list of traversal names) count too:
        # if the file changed but no test method line did, run the whole module's changed classes.
        if not touched and added:
            for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
                end = getattr(cls, "end_lineno", cls.lineno)
                if any(cls.lineno <= ln <= end for ln in added):
                    specs.append(f"{mod}.{cls.name}")
        files.append(h.path)
    # also carry helper files under the same test app (views.py, urls.py, models.py ...)
    for p in repo.changed_files(fix):
        if p.startswith("tests/") and p.endswith(".py") and p not in files:
            files.append(p)
    if not specs:
        return None
    return TestSpec(kind="extracted_from_fix_commit_tests", runner="django-runtests",
                    source_commit=repo.rev_parse(fix), test_files=files, test_ids=sorted(set(specs)))


def select_python(repo: Repo, commit: str) -> str:
    """Pick an interpreter that satisfies the project's python_requires at `commit`."""
    req = ""
    for path, key in (("setup.cfg", "python_requires"), ("pyproject.toml", "requires-python"), ("setup.py", "python_requires")):
        txt = repo.show_file(commit, path) or ""
        m = re.search(key + r"\s*=\s*['\"]?\s*>=\s*3\.(\d+)", txt)
        if m:
            req = m.group(1)
            break
    minor = int(req) if req else 8
    if minor >= 10:
        return os.environ.get("HOLDFAST_PY311", ".targets/venv311/bin/python")
    return os.environ.get("HOLDFAST_PY39", ".targets/venv39/bin/python")


def run_spec(repo: Repo, commit: str, spec: TestSpec, timeout: int = 600) -> TestResult:
    python = select_python(repo, commit)
    if not Path(python).exists():
        return TestResult("unavailable", f"interpreter {python} missing", "", python)
    wt = WORKTREES / commit[:12]
    repo.worktree(commit, wt)
    try:
        for tf in spec.test_files:
            content = repo.show_file(spec.source_commit, tf)
            if content is None:
                continue
            dest = wt / tf
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
        env = dict(os.environ, PYTHONPATH=str(wt.resolve()), PYTHONDONTWRITEBYTECODE="1")
        cmd = [os.path.abspath(python), "runtests.py", "--parallel=1", "-v2", *spec.test_ids]
        try:
            r = subprocess.run(cmd, cwd=wt / "tests", env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return TestResult("timeout", f"timed out after {timeout}s", "", python)
        out = (r.stdout + "\n" + r.stderr)
        tail = "\n".join(out.strip().splitlines()[-40:])
        return _classify(out, tail, python, r.returncode)
    finally:
        repo.remove_worktree(wt)


def _classify(out: str, tail: str, python: str, rc: int) -> TestResult:
    """Per-test outcomes from unittest -v2 output. Fixture (setUpClass/tearDownClass) errors are
    reported but do not turn a set of passing test methods into an error."""
    per = {"ok": 0, "FAIL": 0, "ERROR": 0, "skipped": 0}
    for m in re.finditer(r"^(test\w+) \([\w.]+\)(?: \([^)]*\))?(?:\n.*?)? \.\.\. (ok|FAIL|ERROR|skipped.*)$", out, re.M):
        key = m.group(2).split()[0]
        per[key if key in per else "ERROR"] += 1
    # subtest failures show up only in the summary block
    subtest_fail = len(re.findall(r"^FAIL: test\w+ \(", out, re.M))
    subtest_err = len(re.findall(r"^ERROR: test\w+ \(", out, re.M))
    fixture_err = len(re.findall(r"^ERROR: (?:setUpClass|tearDownClass|setUpModule|tearDownModule) \(", out, re.M))
    summ = re.search(r"^(OK|FAILED \(.*\))", out, re.M)
    summary = (summ.group(1) if summ else f"exit {rc}, no unittest summary")
    if fixture_err:
        summary += f"; {fixture_err} fixture error(s) ignored"
    if not summ and per["ok"] + per["FAIL"] + per["ERROR"] == 0:
        return TestResult("error", summary, tail, python)
    if per["FAIL"] or subtest_fail:
        return TestResult("fail", summary, tail, python)
    if per["ERROR"] or subtest_err:
        return TestResult("error", summary, tail, python)
    if per["ok"] and (rc == 0 or fixture_err):
        return TestResult("pass", summary, tail, python)
    return TestResult("error", summary, tail, python)
