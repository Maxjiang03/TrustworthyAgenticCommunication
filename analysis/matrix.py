"""The §E.4 expected matrix, as DATA, and what the campaign did to it.

The matrix existed as markdown in two covered documents and nowhere as
something code could compare against. The only machine-readable fragment was
four pilot scenarios in an excluded test file. So the pre-registered
commitments that speak about the matrix -- above all *"the results chapter MUST
report those three rows as NOT POPULATED BY THE CAMPAIGN"* -- had no
representation at all, and the default behaviour of a per-family count is the
exact reading that declaration forbids (ADR 0044).

Three states, and the third is the point:

* `PREDICTED` — a row the campaign instantiates. Its cells carry the
  prediction and, once a campaign result is joined, the measurement.
* `DEFERRED` — `F2 wrong_principal`, deferred by decision (ADR 0028) and never
  to be filled. It reads *deferred — unscored*, **not** `NA`: `NA` would assert
  the arms cannot express the case, which is false.
* `NOT_POPULATED` — a row §E.4 predicts and the campaign does not instantiate.
  Three F3 subcases are in this state, one of them (`dpop-captured-proof-replay`)
  being the only row in the entire matrix where `B3⁺` differs from `B3`.

A `NOT_POPULATED` row is never counted as agreeing, never folded into a family
rate, and carries its own reason. `family_coverage` reports the fraction
alongside every family total, because *"F3's measured coverage is two subcases
out of five, and that fraction travels with every F3 number this study
reports."*

The matrix is PARSED from `docs/PRE_REGISTRATION.md` rather than transcribed:
a copy here would be a second frozen artifact that could drift from the sealed
one, and the drift would be invisible.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PRE_REGISTRATION = REPO_ROOT / "docs" / "PRE_REGISTRATION.md"
MATRIX_HEADER = "| Subcase (family) |"


class AnalysisError(Exception):
    """The analysis refused to report something it cannot support."""


class RowState(Enum):
    PREDICTED = "predicted"
    DEFERRED = "deferred — unscored (ADR 0028)"
    NOT_POPULATED = "NOT POPULATED BY THE CAMPAIGN"


@dataclass(frozen=True)
class ExpectedCell:
    """One prediction. `dagger` is §E.4's `A†` -- admitted ABSENT the monitor."""

    arm: str
    value: str
    dagger: bool = False

    @property
    def predicts_block(self) -> bool:
        return self.value == "B"


@dataclass(frozen=True)
class ExpectedRow:
    subcase: str
    family: str
    cells: dict[str, ExpectedCell]
    state: RowState = RowState.PREDICTED
    reason: str = ""

    @property
    def populated(self) -> bool:
        return self.state is RowState.PREDICTED

    def as_dict(self) -> dict[str, Any]:
        return {
            "subcase": self.subcase,
            "family": self.family,
            "state": self.state.value,
            "reason": self.reason,
            "cells": (
                {arm: cell.value + ("†" if cell.dagger else "") for arm, cell in self.cells.items()}
                if self.populated
                else {}
            ),
        }


@dataclass
class Matrix:
    rows: list[ExpectedRow] = field(default_factory=list)

    @property
    def arms(self) -> tuple[str, ...]:
        for row in self.rows:
            if row.cells:
                return tuple(row.cells)
        raise AnalysisError("the matrix carries no cells")

    def by_family(self, family: str) -> list[ExpectedRow]:
        return [row for row in self.rows if row.family == family]

    def family_coverage(self, family: str) -> tuple[int, int]:
        """`(instantiated, defined)` for one family.

        The fraction §4's F3 declaration requires to travel with every F3
        number. `DEFERRED` rows are excluded from the denominator: they are not
        coverage this campaign forfeited, they are scope this study never
        claimed (ADR 0028).
        """
        rows = [row for row in self.by_family(family) if row.state is not RowState.DEFERRED]
        return sum(1 for row in rows if row.populated), len(rows)


_ARM_HEADINGS = {
    "B0": "B0",
    "B1": "B1",
    "B2-broad-noexch": "B2-broad-noexchange",
    "B2-exch-broad": "B2-exchange-broad",
    "B2-exch-task": "B2-exchange-task",
    "B2-DPoP": "B2-exchange-task-DPoP",
    "B-cap": "B-cap",
    "B3": "B3",
    "B3⁺": "B3+",
}


def _split(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def _family_of(subcase: str) -> str:
    match = re.match(r"^(F\d)", subcase)
    if match is None:
        raise AnalysisError(f"subcase names no family: {subcase!r}")
    return match.group(1)


def _cell(raw: str, arm: str) -> ExpectedCell:
    """`**B**`, `A`, `A†` -- the emphasis is markdown, not meaning."""
    text = raw.replace("*", "").strip()
    dagger = "†" in text
    value = text.replace("†", "").strip()
    if value not in ("A", "B", "NA"):
        raise AnalysisError(f"unreadable matrix cell {raw!r} for {arm}")
    return ExpectedCell(arm=arm, value=value, dagger=dagger)


def load_matrix(path: Path = PRE_REGISTRATION) -> Matrix:
    """Parse §E.4's table out of the sealed pre-registration."""
    text = path.read_text(encoding="utf-8")
    if text.count(MATRIX_HEADER) != 1:
        raise AnalysisError("the expected matrix is not uniquely identifiable")
    lines = text[text.index(MATRIX_HEADER) :].splitlines()
    arms = [_ARM_HEADINGS[name] for name in _split(lines[0])[1:]]

    rows: list[ExpectedRow] = []
    for line in lines[2:]:
        if not line.startswith("|"):
            break
        parts = _split(line)
        subcase, values = parts[0], parts[1:]
        if len(values) != len(arms):
            raise AnalysisError(f"row {subcase!r} has {len(values)} cells, expected {len(arms)}")
        if any("deferred" in value for value in values):
            rows.append(
                ExpectedRow(
                    subcase=subcase,
                    family=_family_of(subcase),
                    cells={},
                    state=RowState.DEFERRED,
                    reason=(
                        "row 5 has no anchor outside the author's judgement, so freezing it "
                        "would measure conformance to an artifact this author invented "
                        "(ADR 0028). Reported as deferred — unscored, never as NA."
                    ),
                )
            )
            continue
        rows.append(
            ExpectedRow(
                subcase=subcase,
                family=_family_of(subcase),
                cells={arm: _cell(value, arm) for arm, value in zip(arms, values, strict=True)},
            )
        )
    if not rows:
        raise AnalysisError("the expected matrix parsed to no rows")
    return Matrix(rows=rows)


# §E.4's row labels are PROSE ("F4 sensitive egress, no declassification")
# while a sealed record's `attack_subcase` is a TOKEN
# ("F4:label-confusion:no-declassification"). They do not share a spelling, and
# fuzzy-matching one to the other would silently mis-mark a row -- which is the
# single thing the F3 declaration cannot tolerate, because a mis-marked row
# reads as covered.
#
# So the correspondence is EXPLICIT and checked fail-closed, the same discipline
# the seal manifest uses: every row is mapped, deferred, or declared
# not-instantiated, every corpus subcase maps to exactly one row, and anything
# unaccounted RAISES rather than defaulting. A corpus that grew a scenario, or a
# matrix that grew a row, breaks this loudly instead of quietly reporting a
# coverage fraction that is no longer true.
ROW_SUBCASE_TOKENS = {
    "F1-root": "F1:root",
    "F1-terminal": "F1:terminal",
    "F1-chain-tamper": "F1:chain-tamper",
    "F2 invalid_credential": "F2:invalid_credential",
    "F2 wrong_holder_proof": "F2:wrong_holder_proof",
    "F2 unauthenticated_caller": "F2:unauthenticated_caller",
    "F3 dpop-stolen-AT-key-substitution": "F3:dpop-stolen-AT-key-substitution",
    "F3 dpop-first-use-body-mutation": None,  # not instantiated (pre-registered §4)
    "F3 audience mismatch": "F3:audience_mismatch",
    "F3 expired token": None,  # not instantiated (pre-registered §4)
    "F3 dpop-captured-proof-replay": None,  # not instantiated; B3⁺'s only row
    "F4 sensitive egress": "F4:label-confusion:no-declassification",
    "F5 high-risk action": "F5:approval-forgery:no-artifact",
}

# Benign controls instantiate no attack row by construction. Named so that
# "unaccounted" means unaccounted, rather than quietly absorbing a control.
CONTROL_PREFIX = "benign:"


def row_key(subcase_label: str) -> str:
    """The mapping key for a §E.4 row label (its text before any qualifier)."""
    for key in ROW_SUBCASE_TOKENS:
        if subcase_label.startswith(key):
            return key
    raise AnalysisError(
        f"§E.4 row {subcase_label!r} has no entry in ROW_SUBCASE_TOKENS. Add it -- a row that "
        "is neither mapped nor declared not-instantiated would be reported as covered."
    )


def instantiated_subcases(corpus_root: Path) -> set[str]:
    """The attack subcase TOKENS a corpus instantiates (controls excluded)."""
    import json

    found: set[str] = set()
    for path in sorted((corpus_root / "sealed").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        subcase = str(document.get("attack_subcase", ""))
        if subcase and not subcase.startswith(CONTROL_PREFIX):
            found.add(subcase)
    return found


def mark_population(matrix: Matrix, corpus_root: Path) -> Matrix:
    """Set `NOT_POPULATED` on every predicted row the corpus does not instantiate.

    §4 of the pre-registration: those rows *"MUST be reported as NOT POPULATED
    BY THE CAMPAIGN — not as passing, not as confirmed, not as agreeing with
    the prediction, and never inside a per-family count that would read as
    though F3 had been covered."*

    Fail-closed both ways. A corpus subcase that maps to no row raises: it
    would otherwise be measured and never reported. A row whose mapped token is
    absent from the corpus becomes `NOT_POPULATED` with its reason recorded.
    """
    present = instantiated_subcases(corpus_root)
    mapped = {token for token in ROW_SUBCASE_TOKENS.values() if token is not None}
    unaccounted = present - mapped
    if unaccounted:
        raise AnalysisError(
            f"corpus subcase(s) {sorted(unaccounted)} map to no §E.4 row. They would be "
            "measured and never reported; add the row or the mapping."
        )

    marked: list[ExpectedRow] = []
    for row in matrix.rows:
        if row.state is RowState.DEFERRED:
            marked.append(row)
            continue
        token = ROW_SUBCASE_TOKENS[row_key(row.subcase)]
        if token is not None and token in present:
            marked.append(row)
            continue
        marked.append(
            ExpectedRow(
                subcase=row.subcase,
                family=row.family,
                cells=row.cells,
                state=RowState.NOT_POPULATED,
                reason=(
                    "the campaign does not instantiate this subcase; its prediction is "
                    "untouched by the measurement and is NOT reported as confirmed, as "
                    "passing, or inside any per-family count (pre-registered §4)"
                ),
            )
        )
    return Matrix(rows=marked)
