"""D-023 part (b): the nine adaptive attacks (A1-A8 of D-019, A9 of D-020) against the
ladder PLUS the seven §E.6 variants, so that `-invoke` meets its orthogonal fixture (A4)
and every other variant is exercised on the cells its conjunct would have refused.

Same apparatus as adaptive runs 2/3 (`validation/adaptive/run_adaptive.py`: the three
rebinds `_scenarios`, `credential_faults`, `_LateBoundToolCaller`), plus the three D-023
rebinds of `run_ablation.py` (corpus label, factories with variants, ARMS). The sealed
oracle cannot score these cells; what stands is the boundary decision and the reason
code. Output `results/ablation/adaptive-<id>.json` and `results/ablation/adaptive-summary.json`.
Run once; refuses to overwrite.
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
from validation.ablation import arms as variants  # noqa: E402
from validation.ablation.predictions import ADAPTIVE as PREDICTED  # noqa: E402
from validation.ablation.run_ablation import install_rebinds  # noqa: E402
from validation.adaptive import run_adaptive as run2  # noqa: E402
from validation.adaptive.attacks import ATTACKS  # noqa: E402
from validation.adaptive.attacks_run3 import ATTACKS_RUN3  # noqa: E402

OUT_DIR = REPO / "results" / "ablation"
SUMMARY = OUT_DIR / "adaptive-summary.json"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    ).stdout.strip()


def run_attack(attack: dict[str, Any], armed: run2.Armed) -> dict[str, Any]:
    out = OUT_DIR / f"adaptive-{attack['id']}.json"
    if out.exists():
        raise SystemExit(f"{out} exists; D-023 runs each cell ONCE and will not overwrite")
    armed.attack = dict(attack)
    armed.stage_notes = []
    armed.invoke_notes = []
    record = campaign_driver.run(
        run_mode="pilot", ledger_backed=False, sut_mode="in-process", out=out
    )
    out.write_text(
        json.dumps(
            {
                "evidence_class": "ablation",
                "NOT_A_CAMPAIGN_RESULT": (
                    "DEVIATIONS D-023 part (b): an adaptive attack (D-019/D-020 apparatus) on "
                    "the base scenario cf-benign against the ladder and the §E.6 variants. "
                    "run_mode 'pilot' is the label the identity rule requires for a variant; the "
                    "corpus is fixtures/confirmatory. The oracle cannot score these cells."
                ),
                "adaptive_attack": {
                    k: attack[k] for k in ("id", "conjunct", "capability", "tampering_point")
                },
                "campaign_driver_record": record,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    na_arms = {n.split(":", 1)[0].strip() for n in armed.stage_notes if "not applicable" in n}
    substituted = bool(armed.invoke_notes)
    cells = {
        c["arm"]: {
            "attack_applied": substituted or c["arm"] not in na_arms,
            "outcome": "admit" if c["observed_forwarded"] else c["reason_code_FOR_DIAGNOSIS_ONLY"],
        }
        for c in record["cells"]
    }
    return {
        "id": attack["id"],
        "seams_used": {
            "staged_material": armed.stage_notes,
            "tool_substitution": sorted(set(armed.invoke_notes)),
        },
        "cells": cells,
        "campaign_record": str(out.relative_to(REPO)).replace("\\", "/"),
    }


def main() -> int:
    if SUMMARY.exists():
        raise SystemExit(f"{SUMMARY} exists; D-023 runs ONCE and will not overwrite it")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    head, dirty = _git("rev-parse", "HEAD"), bool(_git("status", "--porcelain"))
    install_rebinds()
    armed = run2.Armed()
    armed.seed = runner_module.GoldenThreadRunner(
        corpus_dir=REPO / "fixtures" / "confirmatory", run_mode="pilot"
    ).seed
    campaign_driver._scenarios = lambda _root: (run2.BASE_SCENARIO,)  # noqa: SLF001
    runner_module.credential_faults = armed
    runner_module._LateBoundToolCaller = run2.make_tool_caller(armed)  # noqa: SLF001

    results = [run_attack(a, armed) for a in tuple(ATTACKS) + tuple(ATTACKS_RUN3)]

    per_variant = {}
    for name in variants.VARIANT_NAMES:
        differences = []
        for r in results:
            b3 = r["cells"]["B3"]["outcome"]
            v = r["cells"][name]["outcome"]
            if v != b3:
                differences.append({"attack": r["id"], "B3": b3, "variant": v})
        predicted = PREDICTED[name]
        observed = {d["attack"]: d["variant"] for d in differences}
        per_variant[name] = {
            "differences_from_B3": differences,
            "prediction": {
                "agree": sorted(k for k in predicted if observed.get(k) == predicted[k]),
                "predicted_but_identical_to_B3": sorted(k for k in predicted if k not in observed),
                "unpredicted_differences": sorted(k for k in observed if k not in predicted),
                "predicted_differently": sorted(
                    k for k in predicted if k in observed and observed[k] != predicted[k]
                ),
            },
        }
        p = per_variant[name]["prediction"]
        p["held_in_full"] = not (
            p["predicted_but_identical_to_B3"]
            or p["unpredicted_differences"]
            or p["predicted_differently"]
        )
    summary = {
        "_what": (
            "D-023 part (b): nine adaptive attacks against the ladder and the §E.6 variants; "
            "each variant's outcome compared with B3's in the same run and against the frozen "
            "predictions. Oracle verdicts are void here; outcomes are boundary decisions and "
            "reason codes. Separate evidence class."
        ),
        "git": {"head": head, "dirty": dirty},
        "matrix": {r["id"]: {arm: c["outcome"] for arm, c in r["cells"].items()} for r in results},
        "variants": per_variant,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for r in results:
        print(r["id"])
        for arm, c in r["cells"].items():
            print(f"    {arm:22s} {c['outcome']}")
    for name, v in per_variant.items():
        held = v["prediction"]["held_in_full"]
        print(f"{name:18s} diff={len(v['differences_from_B3'])} held={held}")
    print(f"WROTE {SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
