"""Core data model: Contract and Verdict. Stored as JSON on disk."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any

CONTRACTS_DIR = Path("contracts")
VERDICTS_DIR = Path("results/verdicts")


class Tier(int, Enum):
    EXECUTED = 1    # a regression test ran and passed/failed
    STRUCTURAL = 2  # the guard/pattern the fix introduced is present/absent in scope
    RULE = 3        # a simple pattern rule fired or didn't
    MODEL = 4       # Claude judged whether the property still holds
    HUMAN = 5       # reserved; never emitted by the tool

    @property
    def label(self) -> str:
        return self.name


class Status(str, Enum):
    HELD = "HELD"
    REGRESSED = "REGRESSED"
    INCOMPLETE_AT_MERGE = "INCOMPLETE_AT_MERGE"
    MOVED = "MOVED"
    UNVERIFIABLE = "UNVERIFIABLE"


@dataclass
class Evidence:
    tier: int
    kind: str
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Scope:
    files: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)   # "path::qualname"
    symbols: list[str] = field(default_factory=list)     # bare names the property depends on
    guard_lines: list[str] = field(default_factory=list)  # normalized added lines that carry the guard
    callers: list[str] = field(default_factory=list)     # one hop, cheaply determined


@dataclass
class SiblingCheck:
    checked: bool
    similar_patterns: list[str] = field(default_factory=list)
    covered: bool | None = None
    note: str = ""


@dataclass
class Contract:
    id: str
    advisory: str
    fix_commit: str
    target_repo: str
    vulnerability: str
    property: str
    scope: Scope
    evidence_at_creation: list[Evidence]
    regression_test: str | None
    regression_test_reason: str | None
    sibling_check: SiblingCheck
    uncertainty: str
    parent_commit: str = ""
    fix_subject: str = ""
    created_from_note: str = ""   # release-note path used as advisory text
    removed_lines: list[str] = field(default_factory=list)  # pre-fix lines the fix deleted (tier-3 rule input)

    def save(self, directory: Path = CONTRACTS_DIR) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        p = directory / f"{self.id}.json"
        p.write_text(json.dumps(asdict(self), indent=2) + "\n")
        return p

    @classmethod
    def load(cls, cid: str, directory: Path = CONTRACTS_DIR) -> "Contract":
        d = json.loads((directory / f"{cid}.json").read_text())
        d["scope"] = Scope(**d["scope"])
        d["sibling_check"] = SiblingCheck(**d["sibling_check"])
        d["evidence_at_creation"] = [Evidence(**e) for e in d["evidence_at_creation"]]
        return cls(**d)


@dataclass
class Verdict:
    contract_id: str
    commit: str
    commit_date: str
    commit_subject: str
    status: str
    tier: int
    evidence: list[Evidence]
    rationale: str
    confidence: str            # low | medium | high
    confidence_reason: str
    tier_disagreement: dict[str, Any] | None = None  # when model disagrees with tiers 1-3
    sampled: bool = False      # True if this commit came from an evenly-sampled walk
    walk_note: str = ""

    @property
    def model_only(self) -> bool:
        """True when tier 4 decided: tiers 1-3 ran (or were skipped) without producing a verdict."""
        return self.tier == Tier.MODEL

    def save(self, directory: Path = VERDICTS_DIR) -> Path:
        d = directory / self.contract_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{self.commit[:10]}.json"
        data = asdict(self)
        data["model_only"] = self.model_only
        p.write_text(json.dumps(data, indent=2) + "\n")
        return p

    @classmethod
    def load(cls, path: Path) -> "Verdict":
        d = json.loads(path.read_text())
        d.pop("model_only", None)
        d["evidence"] = [Evidence(**e) for e in d["evidence"]]
        return cls(**d)


def load_all_verdicts(directory: Path = VERDICTS_DIR) -> list[Verdict]:
    out = []
    for p in sorted(directory.glob("*/*.json")):
        out.append(Verdict.load(p))
    return out
