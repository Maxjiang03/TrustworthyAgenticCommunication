"""Phase B: instantiate the FALSIFIABLE cells and OBSERVE the boundary's decision.

RUN 2 (D-019 addendum): provenance only. Run 1's findings are unchanged; this run
exists to record them on a clean tree and under D-012's evidence_class stamping.

THE SEALED ORACLE CANNOT SCORE THESE CELLS, and the module no longer pretends it
can. The oracle judges each cell against the sealed record of the BASE scenario,
while the attack substitutes the request -- so it adjudicates a request that was
never made. Four verdict columns are void here (`reference_allow`,
`admission_breach`, `false_block`, and every effect-derived field, the last
because the run is `ledger_backed=False`). They are emitted with a `_VOID` suffix
so no reader can lift them out. What stands is `observed_forwarded` and the reason
code: harness-side observations of which conjunct refused, which is exactly what a
reachability question needs.

Post-seal adaptive validation (DEVIATIONS D-019). Outside `src/` and `analysis/`;
no sealed file is edited and every covered file stays byte-identical to `ffa216e`,
hash-verified before and after.

**This module drives nothing itself.** Each attack runs through the SEALED campaign
driver against the SEALED corpus, so the nine arms, the artifact minting, the clock
rule and the matrix-grouping refusal are all the campaign's own.
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

**No count is adjusted after the fact**, including any cell where the attack is
ADMITTED by B3: D-019 pre-commits that a successful attack is the most valuable
result available here and is reported before any diagnosis. Admissions are counted
over APPLICABLE arm runs only -- an arm that cannot express the corruption runs the
unmodified base scenario, and counting that as an attack success is the defect run
1's reporting had.
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
OUT_DIR = REPO / "results" / "adaptive" / "run2"
SEAL_MANIFEST = "seal/manifest_v0.8.json"
SEAL_IMPLEMENTATION_COMMIT = "ffa216e7ae116fe3f20b9dda4522d8b88ede0de0"
EVIDENCE_CLASS = "extension"
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
    # D-012's pre-committed mitigation, applied AT WRITE TIME. The sealed
    # driver's record is nested VERBATIM inside an evidence envelope -- not
    # altered, wrapped -- so `run_mode: "confirmatory"` can never be read alone
    # and the artefact cannot be mistaken for a campaign result.
    out.write_text(
        json.dumps(
            {
                "evidence_class": EVIDENCE_CLASS,
                "NOT_A_CAMPAIGN_RESULT": (
                    "An adaptive attack from DEVIATIONS D-019 Phase B. The nested record's "
                    "run_mode, family and subcase are inherited from the BASE scenario the "
                    "attack was built on (cf-benign) and describe that base, NOT this cell. "
                    "Never sum with the 143-cell confirmatory campaign."
                ),
                "seal_manifest": SEAL_MANIFEST,
                "seal_implementation_commit": SEAL_IMPLEMENTATION_COMMIT,
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
    # WHICH ARMS THE ATTACK COULD ACTUALLY BE APPLIED TO. An arm that stages no
    # HTC chain, no INV or no access token cannot express a corruption of it;
    # the stage function records "not applicable" and the arm then runs the
    # UNMODIFIED base scenario. Counting such a run as an admission would report
    # an untouched benign request as an attack success -- the defect run 1's
    # reporting had. SS E.4's rule is that an NA cell is not a result.
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
    not_applicable = [c for c in cells if not c["attack_applied"]]
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
            "not_applicable_ran_unmodified_base": len(not_applicable),
            "admitted_of_applicable": len(admitted),
            "blocked_of_applicable": len(applicable) - len(admitted),
            "unscorable_reported_by_driver": len(record["unscorable"]),
        },
        "not_applicable_arms": [c["arm"] for c in not_applicable],
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
        print(
            f"    applicable {c['attack_applicable']}/{c['arms']}   "
            f"admitted {c['admitted_of_applicable']}/{c['attack_applicable']}"
        )
        for cell in result["cells"]:
            if not cell["attack_applied"]:
                mark = "n/a  "
            elif cell["admitted"]:
                mark = "ADMIT"
            else:
                mark = "block"
            print(f"      {mark} {cell['arm']:24s} {cell['reason_code_FOR_DIAGNOSIS_ONLY']}")

    report = {
        "_what": (
            "D-019 Phase B: the eight unmasked FALSIFIABLE cells of the conjunct-falsifiability "
            "enumeration, instantiated as defence-aware adaptive attacks, each run against all "
            "nine arms on the sealed corpus. THE SEALED ORACLE CANNOT SCORE THEM: it judges each "
            "cell against the sealed record of the BASE scenario while the attack substitutes the "
            "request, so four verdict columns are VOID and are suffixed _VOID. What stands is the "
            "boundary decision and the conjunct that produced it. A SEPARATE EVIDENCE CLASS: never "
            "summed with the 143-cell campaign, which is untouched."
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
            "attack_applicable_runs": sum(r["counts"]["attack_applicable"] for r in results),
            "not_applicable_runs": sum(
                r["counts"]["not_applicable_ran_unmodified_base"] for r in results
            ),
            "admitted_of_applicable": sum(r["counts"]["admitted_of_applicable"] for r in results),
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
    print(f"CELLS instantiated        = {t['cells_instantiated']}")
    print(f"ARM RUNS                  = {t['arm_runs']}")
    print(f"  attack applicable       = {t['attack_applicable_runs']}")
    print(f"  NA (ran unmodified base)= {t['not_applicable_runs']}")
    print(f"ADMITTED of applicable    = {t['admitted_of_applicable']}")
    print(f"WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
