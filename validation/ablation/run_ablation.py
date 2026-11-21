"""D-023 part (a): the sealed campaign driven once over the sealed corpus with the seven
§E.6 variants ADDED to the nine ladder arms, in process, ledger off.

Three rebinds in sealed namespaces, nothing sealed edited:

1. `campaign_driver.CORPORA["pilot"]` -> `fixtures/confirmatory`. The sealed identity rule
   refuses an ablation variant on a `confirmatory` run, so the run is labelled `pilot`;
   the corpus is the sealed confirmatory one, and the envelope says so (D-012).
2. `campaign_driver._factories` -> the sealed factories plus the seven variants, each on
   B3's own setup (`validation/ablation/arms.py`).
3. `matrix_grouping.ARMS` -> the ladder plus the variant names, so `matrix_grouping.Cell`
   (constructed for every cell) accepts them. The grouping rules themselves are untouched.

Output `results/ablation/campaign-ablation.json` (the driver's record, verbatim, in an
evidence envelope) and `results/ablation/ablation-summary.json`: for each variant, every
cell where it differs from B3 IN THE SAME RUN, and the agreement of those differences with
the frozen predictions of `predictions.py`. Separate evidence class; never summed with the
campaign. Run once; refuses to overwrite.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.harness import (  # noqa: E402
    campaign_driver,
    matrix_grouping,
)
from validation.ablation import arms as variants  # noqa: E402
from validation.ablation.predictions import CAMPAIGN as PREDICTED  # noqa: E402

OUT_DIR = REPO / "results" / "ablation"
RECORD = OUT_DIR / "campaign-ablation.json"
SUMMARY = OUT_DIR / "ablation-summary.json"
CONFIRMATORY = REPO / "fixtures" / "confirmatory"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    ).stdout.strip()


def install_rebinds() -> None:
    campaign_driver.CORPORA["pilot"] = CONFIRMATORY
    sealed_factories = campaign_driver._factories  # noqa: SLF001

    def factories_with_variants(*args: Any, **kwargs: Any) -> dict[str, Any]:
        base = sealed_factories(*args, **kwargs)
        _, b3_setup = base["B3"]
        return {**base, **variants.variant_factories(dict(b3_setup))}

    campaign_driver._factories = factories_with_variants  # noqa: SLF001
    matrix_grouping.ARMS = tuple(matrix_grouping.ARMS) + tuple(
        n for n in variants.VARIANT_NAMES if n not in matrix_grouping.ARMS
    )


def _key(c: dict[str, Any]) -> tuple[str, Any]:
    return (c["scenario_id"], c["monitor_attached"])


def _outcome(c: dict[str, Any]) -> str:
    return "admit" if c["observed_forwarded"] else c["reason_code_FOR_DIAGNOSIS_ONLY"]


def summarise(record: dict[str, Any]) -> dict[str, Any]:
    by_arm: dict[str, dict[tuple[str, Any], dict[str, Any]]] = {}
    for c in record["cells"]:
        by_arm.setdefault(c["arm"], {})[_key(c)] = c
    b3 = by_arm["B3"]
    out = {}
    for name in variants.VARIANT_NAMES:
        cells = by_arm.get(name, {})
        differences = []
        for k, cell in sorted(cells.items(), key=str):
            ref = b3.get(k)
            if ref is None:
                differences.append({"cell": list(k), "note": "no B3 cell to compare"})
                continue
            if _outcome(cell) != _outcome(ref):
                differences.append(
                    {"cell": list(k), "B3": _outcome(ref), "variant": _outcome(cell)}
                )
        predicted = {tuple(k): v for k, v in PREDICTED[name].items()}
        observed = {tuple(d["cell"]): d["variant"] for d in differences if "variant" in d}
        agree = sorted(str(k) for k in predicted if observed.get(k) == predicted[k])
        missing = sorted(str(k) for k in predicted if k not in observed)  # predicted, not seen
        unexpected = sorted(str(k) for k in observed if k not in predicted)  # seen, not predicted
        wrong = sorted(str(k) for k in predicted if k in observed and observed[k] != predicted[k])
        out[name] = {
            "cells_run": len(cells),
            "cells_identical_to_B3": len(cells) - len(differences),
            "differences_from_B3": differences,
            "prediction": {
                "predicted_differences": len(predicted),
                "agree": agree,
                "predicted_but_identical_to_B3": missing,
                "unpredicted_differences": unexpected,
                "predicted_differently": wrong,
                "held_in_full": not missing and not unexpected and not wrong,
            },
        }
    return out


def main() -> int:
    for p in (RECORD, SUMMARY):
        if p.exists():
            raise SystemExit(f"{p} exists; D-023 runs ONCE and will not overwrite it")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    head, dirty = _git("rev-parse", "HEAD"), bool(_git("status", "--porcelain"))
    install_rebinds()
    t0 = time.time()
    record = campaign_driver.run(
        run_mode="pilot", ledger_backed=False, sut_mode="in-process", out=RECORD
    )
    elapsed = round(time.time() - t0, 3)
    RECORD.write_text(
        json.dumps(
            {
                "evidence_class": "ablation",
                "NOT_A_CAMPAIGN_RESULT": (
                    "DEVIATIONS D-023 ablation run. The nested record is labelled run_mode "
                    "'pilot' because the sealed identity rule refuses an ablation variant on a "
                    "confirmatory run; the corpus is fixtures/confirmatory (sealed). Ledger off, "
                    "so every effect-derived field is None. Never sum with, and never substitute "
                    "for, results/raw/campaign-confirmatory.json."
                ),
                "corpus_root_actual": "fixtures/confirmatory",
                "variants": list(variants.VARIANT_NAMES),
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
    summary = {
        "_what": (
            "D-023 part (a): each §E.6 variant compared cell by cell with B3 in the SAME run "
            "on the sealed corpus (ledger off), and the differences checked against the frozen "
            "predictions of validation/ablation/predictions.py. A separate evidence class."
        ),
        "arms_run": sorted({c["arm"] for c in record["cells"]}),
        "cells_total": len(record["cells"]),
        "unscorable_total": len(record["unscorable"]),
        "elapsed_seconds": elapsed,
        "git": {"head": head, "dirty": dirty},
        "variants": summarise(record),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for name, v in summary["variants"].items():
        p = v["prediction"]
        print(
            f"{name:18s} cells={v['cells_run']:3d} identical={v['cells_identical_to_B3']:3d} "
            f"diff={len(v['differences_from_B3']):2d} predicted={p['predicted_differences']} "
            f"held={p['held_in_full']}"
        )
        for d in v["differences_from_B3"]:
            print(f"    {d}")
    print(f"WROTE {RECORD}\nWROTE {SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
