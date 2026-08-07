"""`make reproduce`: every table, from `results/raw/`, by one command.

Design §J.3 item 12 -- *"Every table/figure regenerated from `results/raw/` by
one command (`make reproduce`); no manual spreadsheet steps."* The target was an
`echo` until ADR 0044/0045.

Three pre-registered commitments are enforced HERE, in the code that produces
the numbers, rather than left to whoever writes the results chapter:

1. The three uninstantiated F3 rows are rendered as **NOT POPULATED BY THE
   CAMPAIGN**, are absent from every per-family count, and carry F3's
   two-of-five coverage fraction alongside every F3 number.
2. Every F4 number carries the **weaker-independence qualification** -- F4
   agreement is not replication of the same strength as the other families,
   because `Ω`'s frozen size leaves its confirmatory instances sharing their
   pilot siblings' whole `(tool, resource)` element.
3. H4a and H4b are evaluated against their own falsification conditions, and
   `NOT DETERMINED` is a real verdict rather than a soft `SUPPORTED`.

Security outcomes are exact counts and rates only. **No confidence interval is
placed on any security proportion** (§D.26): a fixed author-constructed suite
has no random-sampling population and the verdicts are deterministic. Latency is
the only quantity with repeated sampling, and this module does not compute one:
timing lives in `analysis/latency.py` and is reported only from a run that
carried the repetitions §6 requires.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from analysis import hypotheses, ingest
from analysis.matrix import AnalysisError, RowState
from analysis.security import class_macro, clustered_by_template, instance_micro

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES = REPO_ROOT / "results" / "tables"

# The qualification that travels with every F4 number (pre-registered §2).
F4_QUALIFICATION = (
    "F4 agreement between the two corpora MUST NOT be reported as replication of the same "
    "strength as F1, F2, F3 or F5: `Ω`'s frozen size makes `(mail.send, mail/outbox)` the "
    "entire derivable egress set, so the F4 confirmatory instances share their pilot "
    "siblings' whole (tool, resource) element and are less independent of the pilot than "
    "the other families' are. This is a limit on what was measured; it does not mitigate "
    "instance-selection bias, which stays unmitigated (ADR 0037, §J.5 item 23)."
)


def _counts(counts) -> dict[str, Any]:
    """A `Counts` as data, without touching `.rate` on an empty denominator."""
    if counts.total == 0:
        return {"count": counts.count, "total": 0, "rate": None}
    return {"count": counts.count, "total": counts.total, "rate": counts.rate}


def build(run_mode: str, *, path: Path | None = None) -> dict[str, Any]:
    campaign = ingest.load_campaign(path or ingest.campaign_path(run_mode))
    matrix = ingest.measured_matrix(campaign)
    verdicts = ingest.verdicts(campaign)
    observed = ingest.flat_observed(campaign)

    families = sorted({row.family for row in matrix.rows})
    per_family: dict[str, Any] = {}
    for family in families:
        coverage = matrix.family_coverage(family)
        entry: dict[str, Any] = {
            "coverage": {"instantiated": coverage[0], "defined": coverage[1]},
            "quantities": {},
        }
        if coverage[1] and coverage[0] < coverage[1]:
            entry["coverage_warning"] = (
                f"{family} is instantiated in part: {coverage[0]} of {coverage[1]} subcases. "
                "This fraction travels with every number in this row (pre-registered §4)."
            )
        if family == "F4":
            entry["qualification"] = F4_QUALIFICATION
        for quantity in ingest.QUANTITIES:
            buckets = class_macro(verdicts, quantity)
            if family in buckets:
                entry["quantities"][quantity] = _counts(buckets[family])
        per_family[family] = entry

    report = {
        "run_mode": campaign.run_mode,
        "corpus": str(campaign.corpus_root.name),
        "scenarios": list(campaign.scenarios),
        "cells_scored": len(campaign.cells),
        "class_macro": per_family,
        "instance_micro": {
            quantity: _counts(instance_micro(verdicts, quantity)) for quantity in ingest.QUANTITIES
        },
        "clustered_by_template": {
            quantity: {
                template: _counts(counts)
                for template, counts in clustered_by_template(verdicts, quantity).items()
            }
            for quantity in ingest.QUANTITIES
        },
        "expected_matrix": [row.as_dict() for row in matrix.rows],
        "not_populated": [
            row.as_dict() for row in matrix.rows if row.state is RowState.NOT_POPULATED
        ],
        "deferred": [row.as_dict() for row in matrix.rows if row.state is RowState.DEFERRED],
        "agreement": ingest.agreement(campaign, matrix),
        "unscorable": [
            {"scenario_id": row[0], "arm": row[1], "cause": row[2]} for row in campaign.unscorable
        ],
        "hypotheses": hypotheses.evaluate(observed),
        "statistical_note": (
            "Security and blocking outcomes are exact counts and rates only. No confidence "
            "interval is placed on any security proportion (§D.26): a fixed "
            "author-constructed suite has no random-sampling population and the verdicts "
            "are deterministic. Repetition is used only to detect nondeterminism."
        ),
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    """The results tables, as the chapter will carry them."""
    lines = [
        f"# Campaign results — {report['run_mode']}",
        "",
        f"Corpus `{report['corpus']}`, {len(report['scenarios'])} scenarios, "
        f"{report['cells_scored']} scored cells, {len(report['unscorable'])} unscorable.",
        "",
        "## Expected matrix (§E.4) — state of every row",
        "",
        "| Subcase | Family | State |",
        "|---|---|---|",
    ]
    for row in report["expected_matrix"]:
        lines.append(f"| {row['subcase']} | {row['family']} | {row['state']} |")

    if report["not_populated"]:
        lines += [
            "",
            "### NOT POPULATED BY THE CAMPAIGN",
            "",
            "These rows are predictions the campaign leaves untouched. They are **not** "
            "reported as passing, as confirmed, or as agreeing with the prediction, and they "
            "appear in no per-family count.",
            "",
        ]
        for row in report["not_populated"]:
            lines.append(f"- **{row['subcase']}** — {row['reason']}")

    lines += ["", "## Per-family outcomes (class-macro)", ""]
    for family, entry in sorted(report["class_macro"].items()):
        coverage = entry["coverage"]
        lines.append(
            f"### {family} — coverage {coverage['instantiated']}/{coverage['defined']} subcases"
        )
        if "coverage_warning" in entry:
            lines.append(f"> {entry['coverage_warning']}")
        if "qualification" in entry:
            lines.append(f"> {entry['qualification']}")
        lines += ["", "| Quantity | Count | Total | Rate |", "|---|--:|--:|--:|"]
        for quantity, counts in sorted(entry["quantities"].items()):
            rate = "—" if counts["rate"] is None else f"{counts['rate']:.3f}"
            lines.append(f"| {quantity} | {counts['count']} | {counts['total']} | {rate} |")
        lines.append("")

    lines += ["## Hypotheses", ""]
    for verdict in report["hypotheses"]:
        lines.append(f"### {verdict['hypothesis']} — **{verdict['verdict']}**")
        for reason in verdict["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")

    disagreements = report["agreement"]["disagreed"]
    lines += [
        "## Agreement with §E.4",
        "",
        f"{report['agreement']['agreed']} cells agreed; {len(disagreements)} disagreed.",
        "",
    ]
    if disagreements:
        lines += [
            "A disagreement is a **finding**, recorded rather than reconciled: §E.4 was "
            "written in advance for exactly this reason.",
            "",
            "| Subcase | Arm | Expected | Observed |",
            "|---|---|:--:|:--:|",
        ]
        for entry in disagreements:
            lines.append(
                f"| {entry['subcase']} | {entry['arm']} | {entry['expected']} | "
                f"{entry['observed']} |"
            )
        lines.append("")

    if report["unscorable"]:
        lines += [
            "## Unscorable cells, with causes",
            "",
            "| Scenario | Arm | Cause |",
            "|---|---|---|",
        ]
        for entry in report["unscorable"]:
            lines.append(f"| {entry['scenario_id']} | {entry['arm']} | {entry['cause']} |")
        lines.append("")

    lines += ["---", "", report["statistical_note"], ""]
    return "\n".join(lines)


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="regenerate every table from results/raw/")
    parser.add_argument("--run-mode", default="confirmatory")
    parser.add_argument("--raw", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=TABLES)
    args = parser.parse_args(argv)

    try:
        report = build(args.run_mode, path=args.raw)
    except AnalysisError as exc:
        print(f"analysis refused: {exc}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / f"results-{args.run_mode}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out_dir / f"results-{args.run_mode}.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    print(
        f"{args.run_mode}: {report['cells_scored']} cells, "
        f"{len(report['not_populated'])} rows NOT POPULATED, "
        f"{len(report['agreement']['disagreed'])} disagreements"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(main())
