"""Phase B: instantiate the FALSIFIABLE cells and score them with the SEALED oracle.

Post-seal adaptive validation (DEVIATIONS D-019). Outside `src/` and `analysis/`;
no sealed file is edited and every covered file stays byte-identical to `ffa216e`,
hash-verified before and after.

**This module drives nothing itself.** Each attack runs through the SEALED campaign
driver against the SEALED corpus, so the nine arms, the artifact minting, the clock
rule, the oracle scoring and the matrix-grouping refusal are all the campaign's own.
Three names are rebound in sealed namespaces and nothing else changes:

1. `campaign_driver._scenarios` -> the single base scenario this attack builds on,
   so one attack costs nine cells rather than 143. The corpus is untouched.
2. `runner.credential_faults` -> a shim that delegates every SEALED fault name to
   the sealed module verbatim and, after it, applies this attack's staged-material
   corruption. Adding a fault name to `src/harness/credential_faults.py` would edit
   a file inside the seal; rebinding does not.
3. `runner._LateBoundToolCaller` -> a caller that substitutes (tool, arguments)
   between the Specialist and the boundary -- the position D.2 names for
   first-use body mutation.

**Separate evidence class.** Output goes to `results/adaptive/`, never to
`results/raw/`, and is never summed with the 143-cell campaign. The campaign's
"run once" is spent and is not touched: nothing here re-runs it, reads its verdicts
as inputs, or writes near it.

**No count is adjusted after the fact.** Every cell is reported exactly as the
sealed oracle returned it, including any cell where the attack is ADMITTED by B3.
D-019 pre-commits that a successful attack is the most valuable result available
here and is reported before any diagnosis.
"""

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.harness import campaign_driver  # noqa: E402
from src.harness import credential_faults as sealed_faults  # noqa: E402
from src.harness import runner as runner_module  # noqa: E402
from validation.adaptive.attacks import ATTACKS  # noqa: E402

BASE_SCENARIO = "cf-benign"
OUT_DIR = REPO / "results" / "adaptive"
ADMITTED_CODES = {"b3_admitted", "b2_admitted", "b1_admitted", "b0_no_boundary_check"}


class Armed:
    """The currently-armed attack. Cells run in sequence, so no race exists."""

    def __init__(self) -> None:
        self.attack: dict[str, Any] | None = None
        self.seed: bytes = b""
        self.stage_notes: list[str] = []
        self.invoke_notes: list[str] = []

    # -- rebind 2: the staged-material seam ---------------------------------
    def apply_to_presentation(self, fault: str, arm: Any, **kw: Any) -> Any:
        """SEALED faults first, verbatim; then this attack's corruption."""
        result = sealed_faults.apply_to_presentation(fault, arm, **kw)
        stage = (self.attack or {}).get("stage")
        if stage is not None:
            self.stage_notes.append(f"{arm.name}: {stage(arm, self.seed)}")
        return result

    def observed_presentation(self, arm: Any, presentation: Any) -> Any:
        return sealed_faults.observed_presentation(arm, presentation)

    def validate(self, fault: str) -> str:
        return sealed_faults.validate(fault)

    def __getattr__(self, name: str) -> Any:  # every other name stays sealed
        return getattr(sealed_faults, name)


def make_tool_caller(armed: Armed):
    """Rebind 3: substitute (tool, arguments) between Specialist and boundary."""
    base = runner_module._LateBoundToolCaller  # noqa: SLF001 -- the sealed seam

    class SubstitutingToolCaller(base):  # type: ignore[misc,valid-type]
        def __call__(self, tool: str, arguments: Mapping[str, Any]) -> Any:
            swap = (armed.attack or {}).get("invoke")
            if swap is None:
                return super().__call__(tool, arguments)
            new_tool, new_args = swap
            armed.invoke_notes.append(f"{tool}{dict(arguments)} -> {new_tool}{dict(new_args)}")
            return super().__call__(new_tool, dict(new_args))

    return SubstitutingToolCaller


def run_attack(attack: Mapping[str, Any], armed: Armed) -> dict[str, Any]:
    out = OUT_DIR / f"campaign-{attack['id']}.json"
    if out.exists():
        raise SystemExit(f"{out} exists; D-019 runs each cell ONCE and will not overwrite")
    armed.attack = dict(attack)
    armed.stage_notes = []
    armed.invoke_notes = []
    record = campaign_driver.run(
        run_mode="confirmatory",
        ledger_backed=False,  # as D-018: the sealed ledger dir is tracked evidence
        sut_mode="in-process",
        out=out,
    )
    cells = [
        {
            "arm": c["arm"],
            "admitted": bool(c["observed_forwarded"]),
            "reason_code_FOR_DIAGNOSIS_ONLY": c["reason_code_FOR_DIAGNOSIS_ONLY"],
            "reference_allow": c["reference_allow"],
            "admission_breach": c["admission_breach"],
            "false_block": c["false_block"],
        }
        for c in record["cells"]
    ]
    admitted = [c for c in cells if c["admitted"]]
    breaches = [c for c in cells if c["admission_breach"]]
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
            "admitted": len(admitted),
            "blocked": len(cells) - len(admitted),
            "admission_breaches": len(breaches),
            "unscorable": len(record["unscorable"]),
        },
        "admission_breaches": breaches,
        "cells": cells,
        "campaign_record": str(out.relative_to(REPO)).replace("\\", "/"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="D-019 Phase B: the adaptive cells")
    parser.add_argument("--out", type=Path, default=OUT_DIR / "adaptive-attacks.json")
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; D-019 runs ONCE and will not overwrite it")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    armed = Armed()
    armed.seed = runner_module.GoldenThreadRunner(
        corpus_dir=REPO / "fixtures" / "confirmatory", run_mode="confirmatory"
    ).seed

    # THE THREE REBINDS.
    campaign_driver._scenarios = lambda _root: (BASE_SCENARIO,)  # noqa: SLF001
    runner_module.credential_faults = armed
    runner_module._LateBoundToolCaller = make_tool_caller(armed)  # noqa: SLF001

    results = []
    for attack in ATTACKS:
        print(f"--- {attack['id']}  ({attack['conjunct']} / {attack['capability']})")
        result = run_attack(attack, armed)
        results.append(result)
        c = result["counts"]
        print(f"    admitted {c['admitted']}/{c['arms']}   breaches {c['admission_breaches']}")
        for cell in result["cells"]:
            mark = "ADMIT" if cell["admitted"] else "block"
            print(f"      {mark} {cell['arm']:24s} {cell['reason_code_FOR_DIAGNOSIS_ONLY']}")

    report = {
        "_what": (
            "D-019 Phase B: the eight unmasked FALSIFIABLE cells of the conjunct-falsifiability "
            "enumeration, instantiated as defence-aware adaptive attacks, each run against all "
            "nine arms on the sealed corpus and scored by the SEALED oracle. A SEPARATE EVIDENCE "
            "CLASS: never summed with the 143-cell campaign, which is untouched."
        ),
        "base_scenario": BASE_SCENARIO,
        "three_rebinds": [
            "campaign_driver._scenarios -> the single base scenario",
            "runner.credential_faults -> sealed faults verbatim, then this attack's corruption",
            "runner._LateBoundToolCaller -> (tool, arguments) substitution before the boundary",
        ],
        "ledger": (
            "ledger_backed=False -- the sealed ledger directory is tracked evidence this run "
            "must not write into. Per ADR 0014 realized_harm is None throughout, so effect-"
            "derived predicates are excluded BY CONSTRUCTION; the comparison target is the "
            "boundary decision and the conjunct that produced it."
        ),
        "attacks": results,
        "totals": {
            "cells_instantiated": len(results),
            "arm_runs": sum(r["counts"]["arms"] for r in results),
            "admitted_total": sum(r["counts"]["admitted"] for r in results),
            "admission_breaches_total": sum(r["counts"]["admission_breaches"] for r in results),
        },
        "not_established": (
            "A blocked attack is not evidence the gate is sound, only that this attack failed. "
            "These eight cells are the table's unmasked FALSIFIABLE set on the constructed "
            "instance set; they are not a search over all adversaries, and every out-of-model "
            "premise (P1-P5) still bounds the result."
        ),
    }
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    t = report["totals"]
    print()
    print(f"CELLS instantiated   = {t['cells_instantiated']}")
    print(f"ARM RUNS             = {t['arm_runs']}")
    print(f"ADMITTED (any arm)   = {t['admitted_total']}")
    print(f"ADMISSION BREACHES   = {t['admission_breaches_total']}")
    print(f"WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
