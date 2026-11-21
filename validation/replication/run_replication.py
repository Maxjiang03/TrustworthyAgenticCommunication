"""D-021: the sealed confirmatory campaign re-driven IN PROCESS N times, to detect
nondeterminism -- the only use of repetition the descriptive-statistics rule permits
(PRE_REGISTRATION §5, D26).

This is NOT a re-run of Part H step 7. The sealed result at
`results/raw/campaign-confirmatory.json` is read for comparison only and is not a
candidate for overwriting even by accident: the sealed driver's own
`refuse_if_written` guard is pointed at `results/replication/run-<k>.json`.
Nothing sealed is edited; the sealed driver, corpus, arms, AS and oracle run as
they are. The one difference from the campaign is `ledger_backed=False` (the sealed
ledger directory is tracked evidence, D-016/D-018), so every effect-derived field
is None here and is excluded from comparison BY CONSTRUCTION.

Comparison target, per cell keyed (scenario_id, arm, monitor_attached): the fields
the oracle derives without the ledger -- `observed_forwarded`, the reason code,
`reference_allow`, `admission_breach`, `false_block` -- plus the unscorable set.
Any disagreement is the finding and is listed; nothing is averaged.

Run once per index; refuses to overwrite.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.harness import campaign_driver  # noqa: E402

SEALED = REPO / "results" / "raw" / "campaign-confirmatory.json"
OUT_DIR = REPO / "results" / "replication"
SUMMARY = OUT_DIR / "replication-summary.json"
COMPARE = (
    "observed_forwarded",
    "reason_code_FOR_DIAGNOSIS_ONLY",
    "reference_allow",
    "admission_breach",
    "false_block",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    ).stdout.strip()


def _key(cell: dict[str, Any]) -> tuple[str, str, Any]:
    return (cell["scenario_id"], cell["arm"], cell["monitor_attached"])


def _index(cells: list[dict[str, Any]]) -> dict[tuple[str, str, Any], dict[str, Any]]:
    idx = {}
    for c in cells:
        k = _key(c)
        if k in idx:
            raise SystemExit(f"duplicate cell key {k}")
        idx[k] = c
    return idx


def _unscorable_set(rows: list[Any]) -> set[str]:
    return {json.dumps(r, sort_keys=True) for r in rows}


def compare(sealed: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    a, b = _index(sealed["cells"]), _index(record["cells"])
    only_sealed = sorted(str(k) for k in a.keys() - b.keys())
    only_run = sorted(str(k) for k in b.keys() - a.keys())
    disagreements = []
    for k in sorted(a.keys() & b.keys(), key=str):
        for field in COMPARE:
            if a[k].get(field) != b[k].get(field):
                disagreements.append(
                    {
                        "cell": list(k),
                        "field": field,
                        "sealed": a[k].get(field),
                        "run": b[k].get(field),
                    }
                )
    ua, ub = _unscorable_set(sealed["unscorable"]), _unscorable_set(record["unscorable"])
    return {
        "compared_cells": len(a.keys() & b.keys()),
        "cells_only_in_sealed": only_sealed,
        "cells_only_in_run": only_run,
        "field_disagreements": disagreements,
        "unscorable_sealed": len(ua),
        "unscorable_run": len(ub),
        "unscorable_identical": ua == ub,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="D-021: in-process replication of the campaign")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args(argv)
    if SUMMARY.exists():
        raise SystemExit(f"{SUMMARY} exists; D-021 runs ONCE and will not overwrite it")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sealed = json.loads(SEALED.read_text(encoding="utf-8"))
    head, dirty = _git("rev-parse", "HEAD"), bool(_git("status", "--porcelain"))

    runs = []
    for k in range(1, args.runs + 1):
        out = OUT_DIR / f"run-{k}.json"
        if out.exists():
            raise SystemExit(f"{out} exists; each replication index runs ONCE")
        t0 = time.time()
        record = campaign_driver.run(
            run_mode="confirmatory", ledger_backed=False, sut_mode="in-process", out=out
        )
        elapsed = round(time.time() - t0, 3)
        # D-012 mitigation at write time: the sealed driver's record is nested
        # verbatim inside an evidence envelope so `run_mode: "confirmatory"`
        # can never be read alone.
        out.write_text(
            json.dumps(
                {
                    "evidence_class": "replication",
                    "NOT_A_CAMPAIGN_RESULT": (
                        "DEVIATIONS D-021 replication run; ledger_backed=False so every "
                        "effect-derived field is None. Never sum with, and never substitute "
                        "for, results/raw/campaign-confirmatory.json."
                    ),
                    "run_index": k,
                    "elapsed_seconds": elapsed,
                    "git": {"head": head, "dirty": dirty},
                    "campaign_driver_record": record,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        cmp = compare(sealed, record)
        cmp.update(
            {
                "run_index": k,
                "elapsed_seconds": elapsed,
                "artefact": f"results/replication/run-{k}.json",
            }
        )
        runs.append(cmp)
        print(
            f"run {k}: {cmp['compared_cells']} cells compared, "
            f"{len(cmp['field_disagreements'])} field disagreements, "
            f"unscorable identical={cmp['unscorable_identical']}, {elapsed}s"
        )

    all_agree = all(
        not r["field_disagreements"]
        and not r["cells_only_in_sealed"]
        and not r["cells_only_in_run"]
        and r["unscorable_identical"]
        for r in runs
    )
    summary = {
        "_what": (
            "D-021: the sealed confirmatory campaign re-driven in process, ledger off, "
            f"{args.runs} times, each compared cell by cell against "
            "results/raw/campaign-confirmatory.json on the ledger-independent fields. "
            "Repetition here detects nondeterminism and nothing else (D26); no value is "
            "averaged and no sealed number changes."
        ),
        "sealed_artefact": "results/raw/campaign-confirmatory.json",
        "compared_fields": list(COMPARE),
        "excluded_by_construction": [
            "realized_harm",
            "effect_count",
            "linkage",
            "log_integrity_failure",
        ],
        "git": {"head": head, "dirty": dirty},
        "runs": runs,
        "all_runs_agree_with_sealed": all_agree,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"ALL RUNS AGREE WITH SEALED = {all_agree}\nWROTE {SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
