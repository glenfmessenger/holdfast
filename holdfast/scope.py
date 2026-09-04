"""Derive a contract's scope from the fix diff: files, functions, symbols, guard lines,
removed lines, and one hop of callers where cheaply determinable."""
from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass, field

from .gitutil import Repo

TEST_DIR_MARKERS = ("/tests/", "tests/", "/test_", "regress/")
DOC_MARKERS = ("docs/", ".txt", ".rst", ".md", "ChangeLog")
GENERIC_NAMES = {"save", "get", "set", "run", "main", "init", "parse", "clean", "close", "open",
                 "read", "write", "name", "value", "self", "data", "path", "file", "text", "str",
                 "strip", "rfind", "find", "lower", "upper", "split", "join", "append", "replace",
                 "startswith", "endswith", "encode", "decode", "items", "keys", "values", "update",
                 "pop", "extend", "insert", "copy", "count", "index", "format"}
PY_BUILTINS = {"len", "str", "int", "isinstance", "range", "list", "dict", "set", "print", "super",
               "getattr", "setattr", "hasattr", "enumerate", "zip", "max", "min", "any", "all",
               "sorted", "tuple", "bool", "float", "bytes", "repr", "format", "type", "iter", "next"}


@dataclass
class Hunk:
    path: str
    added: list[tuple[int, str]] = field(default_factory=list)    # (new lineno, text)
    removed: list[tuple[int, str]] = field(default_factory=list)  # (old lineno, text)


def is_source(path: str) -> bool:
    if any(m in path for m in DOC_MARKERS):
        return False
    if path.startswith("tests/") or "/tests/" in path or "/test/" in path:
        return False
    return path.endswith((".py", ".c", ".h"))


def is_test(path: str) -> bool:
    return (path.startswith("tests/") or "/tests/" in path) and path.endswith(".py")


def parse_hunks(diff: str) -> list[Hunk]:
    hunks: list[Hunk] = []
    cur: Hunk | None = None
    new_ln = old_ln = 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            p = line[4:].strip()
            p = p[2:] if p.startswith("b/") else p
            cur = Hunk(path=p)
            hunks.append(cur)
        elif line.startswith("@@") and cur is not None:
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            old_ln, new_ln = int(m.group(1)), int(m.group(2))
        elif cur is None or line.startswith("---") or line.startswith("diff ") or line.startswith("index "):
            continue
        elif line.startswith("+"):
            cur.added.append((new_ln, line[1:])); new_ln += 1
        elif line.startswith("-"):
            cur.removed.append((old_ln, line[1:])); old_ln += 1
        elif line.startswith("\\"):
            continue
        else:
            new_ln += 1; old_ln += 1
    return [h for h in hunks if h.path != "/dev/null"]


def normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def substantive(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith(("#", "//", "*", "/*", '"""', "'''")):
        return False
    if s in ("pass", "else:", "try:", "{", "}", "):", ")"):
        return False
    return len(s) > 3


def enclosing_qualnames(src: str, linenos: set[int]) -> list[str]:
    """Python only: qualified names of defs/classes containing the given lines."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    found: dict[str, None] = {}

    def visit(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = f"{prefix}.{child.name}" if prefix else child.name
                end = getattr(child, "end_lineno", child.lineno)
                if any(child.lineno <= ln <= end for ln in linenos):
                    if isinstance(child, ast.ClassDef):
                        # only record the class if no nested def matches
                        before = len(found)
                        visit(child, q)
                        if len(found) == before:
                            found[q] = None
                        continue
                    found[q] = None
                visit(child, q)
            else:
                visit(child, prefix)
    visit(tree, "")
    return list(found)


def c_enclosing_functions(src: str, linenos: set[int]) -> list[str]:
    """Crude C: nearest preceding line that looks like a function definition."""
    lines = src.splitlines()
    out: dict[str, None] = {}
    for ln in sorted(linenos):
        for i in range(min(ln, len(lines)) - 1, -1, -1):
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(", lines[i])
            if m and not lines[i].startswith((" ", "\t")):
                out[m.group(1)] = None
                break
    return list(out)


def called_names(lines: list[str], dotted: bool = False) -> list[str]:
    """Names called in `lines`. With dotted=True keep 'os.path.basename' rather than 'basename'."""
    names: dict[str, None] = {}
    for l in lines:
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_.]*)\s*\(", l):
            full = m.group(1)
            n = full.split(".")[-1]
            if n in PY_BUILTINS or n in ("if", "while", "for", "return", "elif", "not", "and", "or"):
                continue
            if n.lower() in GENERIC_NAMES:
                continue
            names[full if dotted else n] = None
    return list(names)


def defined_names(lines: list[str]) -> list[str]:
    names: dict[str, None] = {}
    for l in lines:
        m = re.match(r"\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", l)
        if m:
            names[m.group(1)] = None
        m = re.match(r"^([A-Z][A-Z0-9_]{3,})\s*=", l)  # module-level constant
        if m:
            names[m.group(1)] = None
        m = re.match(r"\s*#\s*(?:ifdef|ifndef|define)\s+([A-Za-z_][A-Za-z0-9_]*)", l)
        if m:
            names[m.group(1)] = None
    return list(names)


def find_callers(repo: Repo, ref: str, names: list[str], scope_files: list[str], glob: str, cap: int = 12) -> list[str]:
    out: list[str] = []
    for n in names:
        if len(n) < 5 or n.lower() in GENERIC_NAMES:
            continue
        r = subprocess.run(["git", "-C", str(repo.path), "grep", "-n", "-w", "-e", n, ref, "--", glob],
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            _, path, ln, txt = line.split(":", 3)
            if path in scope_files or not is_source(path):
                continue
            if re.search(r"\b(def|class)\s+" + re.escape(n) + r"\b", txt):
                continue
            out.append(f"{path}:{ln} -> {n}")
            if len(out) >= cap:
                return out
    return out
