"""Read `results/raw/` back into the objects `analysis/` already consumes.

`analysis/security.py` and `analysis/latency.py` were written against
`Verdict` and `Sample`, and NOTHING produced either: `CellVerdict` has no
`template` field, the timing seams deliberately record span NAMES rather than
durations, and no loader existed at all. The analysis was frozen with the seal
and could not read the campaign it was frozen alongside (ADR 0044).

This is the join, and it is deliberately thin: it renames nothing, computes no
statistic, and drops no cell silently. Where the campaign records something the
analysis has no field for, that is reported rather than discarded.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis.matrix import ROW_SUBCASE_TOKENS, AnalysisError, Matrix, load_matrix, mark_population
from analysis.security import Verdict

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_RAW = REPO_ROOT / "results" / "raw"

# The quantities `security.py` reports on. Each is a named oracle output; a
# cell that did not compute one carries `None`, which the analysis drops from
# the denominator rather than counting as a zero.
QUANTITIES = (
    "reference_allow",
    "observed_forwarded",
    "admission_breach",
    "realized_harm",
    "false_block",
    "log_integrity_failure",
)


@dataclass(frozen=True)
class Campaign:
    """One campaign result, as the driver wrote it."""

    run_mode: str
    corpus_root: Path
    cells: list[dict[str, Any]]
    unscorable: list[list[str]]
    passes: list[dict[str, Any]]
    raw: dict[str, Any]

    @property
    def scenarios(self) -> tuple[str, ...]:
        return tuple(self.raw.get("scenarios", ()))


def load_campaign(path: Path) -> Campaign:
    if not path.is_file():
        raise AnalysisError(
            f"no campaign result at {path}. Part H step 7 has not been run, or was run "
            "elsewhere; the analysis reports nothing rather than inventing a table."
        )
    record = json.loads(path.read_text(encoding="utf-8"))
    return Campaign(
        run_mode=str(record["run_mode"]),
        corpus_root=REPO_ROOT / record["corpus_root"],
        cells=list(record["cells"]),
        unscorable=[list(row) for row in record.get("unscorable", ())],
        passes=list(record.get("passes", ())),
        raw=record,
    )


def campaign_path(run_mode: str) -> Path:
    return RESULTS_RAW / f"campaign-{run_mode}.json"


def _template_of(cell: dict[str, Any]) -> str:
    """The clustering key §D.26 asks for: *"template-derived variants clustered"*.

    `CellVerdict` carries `subcase`, which IS the template a scenario was
    derived from -- one sealed subcase generates the variants of that attack.
    Using it rather than inventing a field keeps the clustering traceable to
    the sealed record instead of to a decision made at analysis time.
    """
    subcase = str(cell.get("subcase") or "")
    return subcase or str(cell.get("family") or "unclassified")


def verdicts(campaign: Campaign) -> list[Verdict]:
    """Every scored cell as a `security.Verdict`.

    Unscorable cells are NOT here: they were never scored, and giving them a
    verdict object with `None` quantities would let them into a denominator by
    accident. They travel separately, with their causes, exactly as the
    pre-registration requires (*"reports every unscorable cell with its cause"*).
    """
    return [
        Verdict(
            scenario_id=str(cell["scenario_id"]),
            arm=str(cell["arm"]),
            family=str(cell.get("family") or ""),
            template=_template_of(cell),
            quantities={name: cell.get(name) for name in QUANTITIES},
        )
        for cell in campaign.cells
    ]


def measured_matrix(campaign: Campaign, matrix: Matrix | None = None) -> Matrix:
    """§E.4, with this campaign's population state applied."""
    return mark_population(matrix or load_matrix(), campaign.corpus_root)


def observed_cells(campaign: Campaign) -> dict[tuple[str, str, Any], str]:
    """`(subcase_token, arm, monitor_attached) -> "A" | "B"`.

    `A` is admitted, `B` is blocked, from the TRUSTED mediation record's
    `observed_forwarded` -- never from a SUT self-verdict (red line 4).

    **The monitor configuration is part of the key, and leaving it out was a
    real defect.** §E.4's `A†` means *admitted ABSENT the shared monitor*, so a
    daggered prediction describes the `monitor_attached=False` pass. Collapsing
    both passes into one entry let the monitored pass overwrite the unmonitored
    one, and every daggered cell then compared `A†` against a `B` measured under
    a monitor -- eight spurious "disagreements" that would have entered the
    results chapter as findings about the mechanisms rather than as an artifact
    of the join.
    """
    observed: dict[tuple[str, str, Any], str] = {}
    for cell in campaign.cells:
        forwarded = cell.get("observed_forwarded")
        if forwarded is None:
            continue
        key = (str(cell.get("subcase") or ""), str(cell["arm"]), cell.get("monitor_attached"))
        observed[key] = "A" if forwarded else "B"
    return observed


def flat_observed(campaign: Campaign) -> dict[tuple[str, str], str]:
    """`(subcase, arm) -> value` for rows with ONE configuration only.

    Used by the hypothesis evaluator, whose rows (F1/F2/F3) run unmonitored --
    `monitor_attached=None` -- so there is exactly one value per cell and no
    dagger to respect.
    """
    return {
        (subcase, arm): value
        for (subcase, arm, monitor), value in observed_cells(campaign).items()
        if monitor is None
    }


def agreement(campaign: Campaign, matrix: Matrix | None = None) -> dict[str, Any]:
    """Cell-for-cell agreement between §E.4's prediction and the measurement.

    A disagreement is a FINDING, recorded as one: §E.4 was written in advance
    precisely so that a cell disagreeing with a measurement is reported rather
    than reconciled (§J.5 item 23). `NOT_POPULATED` rows are excluded from both
    numerator and denominator and listed separately, because counting them
    either way would state something about a cell nobody measured.
    """
    populated = measured_matrix(campaign, matrix)
    observed = observed_cells(campaign)
    agreed: list[dict[str, str]] = []
    disagreed: list[dict[str, str]] = []
    unmeasured: list[dict[str, str]] = []

    for row in populated.rows:
        if not row.populated:
            continue
        token = ROW_SUBCASE_TOKENS[_row_key(row.subcase)]
        for arm, expected in row.cells.items():
            # A DAGGERED prediction is about the unmonitored configuration by
            # definition ("admitted ABSENT the shared monitor"). An undaggered
            # one claims no monitor-dependence, so it must hold in EVERY
            # configuration the cell was run under -- the stricter reading, and
            # the one that can actually catch a monitor-dependent surprise.
            if expected.dagger:
                measured = [observed.get((token, arm, False))]
            else:
                measured = [
                    value
                    for (subcase, cell_arm, _monitor), value in observed.items()
                    if subcase == token and cell_arm == arm
                ] or [None]
            entry = {
                "subcase": row.subcase,
                "arm": arm,
                "expected": expected.value + ("†" if expected.dagger else ""),
                "observed": "/".join(sorted({value or "" for value in measured})),
            }
            if all(value is None for value in measured):
                unmeasured.append(entry)
            elif expected.value == "NA":
                # §E.4's NA means the arm cannot express the case. The campaign
                # records those as unscorable, so a measurement here would be
                # the surprise, not the agreement.
                (agreed if not any(measured) else disagreed).append(entry)
            elif all(value == expected.value for value in measured):
                agreed.append(entry)
            else:
                disagreed.append(entry)

    return {
        "agreed": len(agreed),
        "disagreed": disagreed,
        "unmeasured": unmeasured,
        "not_populated": [
            row.as_dict() for row in populated.rows if row.state.name == "NOT_POPULATED"
        ],
        "deferred": [row.as_dict() for row in populated.rows if row.state.name == "DEFERRED"],
    }


def _row_key(subcase_label: str) -> str:
    from analysis.matrix import row_key

    return row_key(subcase_label)
