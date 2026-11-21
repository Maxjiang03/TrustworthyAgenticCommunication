"""Adaptive run 3 (DEVIATIONS D-020): instantiate A9 and OBSERVE the boundary's decision.

Same apparatus as run 2 (`validation/adaptive/run_adaptive.py`): the sealed campaign
driver runs the base scenario `cf-benign` against all nine arms with three names
rebound in sealed namespaces -- `_scenarios`, `credential_faults` and
`_LateBoundToolCaller` -- and nothing sealed is modified. The `Armed` shim and the
substituting tool caller are imported from the run-2 module unchanged; only the
attack table and the output directory differ.

THE SEALED ORACLE CANNOT SCORE THIS CELL either (it judges against the sealed
record of the base scenario while the attack substitutes the request), so the four
verdict columns are emitted with a `_VOID` suffix exactly as in run 2. What stands
is `observed_forwarded` and the reason code.

Separate evidence class: output goes to `results/adaptive/run3/`, never to
`results/raw/`, and is never summed with the 143-cell campaign. Run once; refuses
to overwrite.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.harness import campaign_driver  # noqa: E402
from src.harness import runner as runner_module  # noqa: E402
from validation.adaptive import run_adaptive as run2  # noqa: E402
from validation.adaptive.attacks_run3 import ATTACKS_RUN3  # noqa: E402

OUT_DIR = REPO / "results" / "adaptive" / "run3"
REPORT = OUT_DIR / "adaptive-run3.json"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    ).stdout.strip()


def run_attack(attack: dict[str, Any], armed: run2.Armed) -> dict[str, Any]:
    out = OUT_DIR / f"campaign-{attack['id']}.json"
    if out.exists():
        raise SystemExit(f"{out} exists; D-020 runs the cell ONCE and will not overwrite")
    armed.attack = dict(attack)
    armed.stage_notes = []
    armed.invoke_notes = []
    record = campaign_driver.run(
        run_mode="confirmatory",
        ledger_backed=False,  # the sealed ledger directory is tracked evidence (D-018)
        sut_mode="in-process",
        out=out,
    )
    out.write_text(
        json.dumps(
            {
                "evidence_class": run2.EVIDENCE_CLASS,
                "NOT_A_CAMPAIGN_RESULT": (
                    "An adaptive attack from DEVIATIONS D-020 (adaptive run 3). The nested "
                    "record's run_mode, family and subcase are inherited from the BASE scenario "
                    "the attack was built on (cf-benign) and describe that base, NOT this cell. "
                    "Never sum with the 143-cell confirmatory campaign."
                ),
                "seal_manifest": run2.SEAL_MANIFEST,
                "seal_implementation_commit": run2.SEAL_IMPLEMENTATION_COMMIT,
                "adaptive_attack": {
                    "id": attack["id"],
                    "conjunct_targeted": attack["conjunct"],
                    "capability": attack["capability"],
                    "tampering_point": attack["tampering_point"],
                },
                "campaign_driver_record": record,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    na_arms = {
        note.split(":", 1)[0].strip() for note in armed.stage_notes if "not applicable" in note
    }
    substituted = bool(armed.invoke_notes)
    cells = [
        {
            "arm": c["arm"],
            "attack_applied": substituted or c["arm"] not in na_arms,
            "admitted": bool(c["observed_forwarded"]),
            "reason_code_FOR_DIAGNOSIS_ONLY": c["reason_code_FOR_DIAGNOSIS_ONLY"],
            "reference_allow_VOID": c["reference_allow"],
            "admission_breach_VOID": c["admission_breach"],
            "false_block_VOID": c["false_block"],
        }
        for c in record["cells"]
    ]
    applicable = [c for c in cells if c["attack_applied"]]
    admitted = [c for c in applicable if c["admitted"]]
    return {
        "id": attack["id"],
        "conjunct_targeted": attack["conjunct"],
        "capability": attack["capability"],
        "tampering_point": attack["tampering_point"],
        "prediction_PRE_REGISTERED": attack["expect"],
        "seams_used": {
            "staged_material": armed.stage_notes,
            "tool_substitution": sorted(set(armed.invoke_notes)),
        },
        "counts": {
            "arms": len(cells),
            "attack_applicable": len(applicable),
            "not_applicable_ran_unmodified_base": len(cells) - len(applicable),
            "admitted_of_applicable": len(admitted),
            "blocked_of_applicable": len(applicable) - len(admitted),
            "unscorable_reported_by_driver": len(record["unscorable"]),
        },
        "cells": cells,
        "campaign_record": str(out.relative_to(REPO)).replace("\\", "/"),
    }


def main() -> int:
    if REPORT.exists():
        raise SystemExit(f"{REPORT} exists; D-020 runs ONCE and will not overwrite it")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    armed = run2.Armed()
    armed.seed = runner_module.GoldenThreadRunner(
        corpus_dir=REPO / "fixtures" / "confirmatory", run_mode="confirmatory"
    ).seed
    # THE THREE REBINDS, as in run 2.
    campaign_driver._scenarios = lambda _root: (run2.BASE_SCENARIO,)  # noqa: SLF001
    runner_module.credential_faults = armed
    runner_module._LateBoundToolCaller = run2.make_tool_caller(armed)  # noqa: SLF001

    results = []
    for attack in ATTACKS_RUN3:
        print(f"--- {attack['id']}  ({attack['capability']}; {attack['tampering_point']})")
        result = run_attack(attack, armed)
        results.append(result)
        for cell in result["cells"]:
            mark = (
                "n/a  "
                if not cell["attack_applied"]
                else ("ADMIT" if cell["admitted"] else "block")
            )
            print(f"      {mark} {cell['arm']:24s} {cell['reason_code_FOR_DIAGNOSIS_ONLY']}")

    report = {
        "_what": (
            "D-020: adaptive run 3, one cell (A9, K-holder, in-scope argument substitution with "
            "a re-minted valid INV) against all nine arms on the sealed corpus. The sealed oracle "
            "cannot score it; the verdict columns are VOID. What stands is the boundary decision "
            "and the reason code. A SEPARATE EVIDENCE CLASS: never summed with the 143-cell "
            "campaign or with adaptive run 2."
        ),
        "base_scenario": run2.BASE_SCENARIO,
        "git": {"head": _git("rev-parse", "HEAD"), "dirty": bool(_git("status", "--porcelain"))},
        "attacks": results,
        "totals": {
            "cells_instantiated": len(results),
            "arm_runs": sum(r["counts"]["arms"] for r in results),
            "attack_applicable_runs": sum(r["counts"]["attack_applicable"] for r in results),
            "admitted_of_applicable": sum(r["counts"]["admitted_of_applicable"] for r in results),
        },
        "not_established": (
            "An admitted in-scope request is evidence that these arms do not over-block a "
            "compromised holder on THIS instance; it is not evidence about the rest of the "
            "authority surface, and it does not touch H4b's out-of-scope half (A8)."
        ),
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    t = report["totals"]
    print(
        f"\nARM RUNS = {t['arm_runs']}  applicable = {t['attack_applicable_runs']}  "
        f"ADMITTED = {t['admitted_of_applicable']}\nWROTE {REPORT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
