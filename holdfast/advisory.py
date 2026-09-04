"""Advisory text. For Django, the security release note in docs/releases/ at the fix commit."""
from __future__ import annotations

import re
from pathlib import Path

from .gitutil import Repo


def find_release_note(repo: Repo, fix: str, advisory: str) -> tuple[str, str] | None:
    """Return (path, section_text) of the release-note section for `advisory` at `fix`."""
    import subprocess
    r = subprocess.run(["git", "-C", str(repo.path), "grep", "-l", "--", advisory, fix, "--", "docs/releases/"],
                       capture_output=True, text=True)
    paths = [l.split(":", 1)[1] for l in r.stdout.splitlines() if ":" in l]
    if not paths:
        return None
    # Prefer the note that actually has a section header for this CVE.
    for path in sorted(paths):
        txt = repo.show_file(fix, path) or ""
        sec = extract_section(txt, advisory)
        if sec:
            return path, sec
    return None


def extract_section(text: str, advisory: str) -> str | None:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(advisory + ":") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= {"=", "-", "~"} and lines[i + 1].strip():
            out = [line]
            j = i + 2
            while j < len(lines):
                # next section header: a line followed by an underline
                if j + 1 < len(lines) and lines[j].strip() and set(lines[j + 1].strip()) <= {"=", "-", "~"} and len(lines[j + 1].strip()) >= 3 and not lines[j].startswith(" "):
                    break
                out.append(lines[j])
                j += 1
            return "\n".join(out).strip()
    return None


def load_advisory(repo: Repo, fix: str, advisory: str, explicit_path: str | None) -> tuple[str, str]:
    """(source_label, text)"""
    if explicit_path:
        return explicit_path, Path(explicit_path).read_text().strip()
    found = find_release_note(repo, fix, advisory)
    if found:
        return found
    return "UNVERIFIABLE", f"No advisory text found for {advisory} in the repository at {fix[:10]}; pass --advisory-text."
