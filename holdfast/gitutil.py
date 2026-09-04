"""Thin subprocess wrapper around git. No GitPython dependency."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


@dataclass
class Repo:
    path: Path

    def run(self, *args: str, check: bool = True, text: bool = True) -> str:
        r = subprocess.run(["git", "-C", str(self.path), *args],
                           capture_output=True, text=text)
        if check and r.returncode != 0:
            raise GitError(f"git {' '.join(args)}: {r.stderr.strip()}")
        return r.stdout

    def rev_parse(self, ref: str) -> str:
        return self.run("rev-parse", ref).strip()

    def subject(self, ref: str) -> str:
        return self.run("log", "-1", "--format=%s", ref).strip()

    def date(self, ref: str) -> str:
        return self.run("log", "-1", "--format=%ad", "--date=short", ref).strip()

    def parent(self, ref: str) -> str:
        return self.rev_parse(f"{ref}~1")

    def show_file(self, ref: str, path: str) -> str | None:
        r = subprocess.run(["git", "-C", str(self.path), "show", f"{ref}:{path}"],
                           capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None

    def changed_files(self, ref: str) -> list[str]:
        return [l for l in self.run("show", "--format=", "--name-only", ref).splitlines() if l]

    def diff(self, a: str, b: str, *paths: str) -> str:
        return self.run("diff", "-M", a, b, "--", *paths) if paths else self.run("diff", "-M", a, b)

    def commit_diff(self, ref: str, *paths: str) -> str:
        return self.run("show", "-M", "--format=", ref, "--", *paths) if paths else \
            self.run("show", "-M", "--format=", ref)

    def log_range(self, rng: str, *paths: str, follow_renames: bool = True) -> list[tuple[str, str, str]]:
        """Commits in `rng` touching `paths`, oldest first: (hash, date, subject)."""
        args = ["log", "--reverse", "--format=%H%x1f%cd%x1f%s", "--date=short", rng]
        if paths:
            args += ["--", *paths]
        out = []
        for line in self.run(*args).splitlines():
            h, d, s = line.split("\x1f", 2)
            out.append((h, d, s))
        return out

    def renames_in_range(self, rng: str) -> list[tuple[str, str, str]]:
        """(commit, old_path, new_path) for every rename in rng, oldest first."""
        out = []
        cur = None
        txt = self.run("log", "-M", "--diff-filter=R", "--name-status", "--reverse",
                       "--format=@%H", rng)
        for line in txt.splitlines():
            if line.startswith("@"):
                cur = line[1:]
            elif line.startswith("R") and cur:
                parts = line.split("\t")
                if len(parts) == 3:
                    out.append((cur, parts[1], parts[2]))
        return out

    def is_ancestor(self, a: str, b: str) -> bool:
        r = subprocess.run(["git", "-C", str(self.path), "merge-base", "--is-ancestor", a, b])
        return r.returncode == 0

    def grep_file(self, ref: str, path: str, pattern: str) -> list[str]:
        r = subprocess.run(["git", "-C", str(self.path), "grep", "-n", "-e", pattern, ref, "--", path],
                           capture_output=True, text=True)
        return [l.split(":", 2)[-1] for l in r.stdout.splitlines()]

    def worktree(self, ref: str, dest: Path) -> None:
        import shutil
        dest = dest.resolve()
        if dest.exists():
            self.run("worktree", "remove", "--force", str(dest), check=False)
            shutil.rmtree(dest, ignore_errors=True)
        self.run("worktree", "prune")
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.run("worktree", "add", "--detach", str(dest), ref)

    def remove_worktree(self, dest: Path) -> None:
        import shutil
        self.run("worktree", "remove", "--force", str(dest.resolve()), check=False)
        shutil.rmtree(dest, ignore_errors=True)
