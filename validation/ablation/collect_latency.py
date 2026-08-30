"""D-023 part (c): the sealed latency collector run ONCE, pinned to the performance
cores (as D-022), with the seven §E.6 variants added to the nine arms, so that each
variant's cost against B3 is a SINGLE-BIT difference -- the one case in which ADR 0041
permits a per-mechanism latency statement.

Same rebinds as `run_ablation.py` (the collector reads `campaign_driver._factories`);
the collector's own plan block (pilot corpus, 3 x 75 repetitions, warm-up 5) is
unchanged. Analysis: for every variant, span and phase, `median(variant) - median(B3)`
with the sealed percentile bootstrap (`analysis.latency.bootstrap_median_difference`,
same seed and resample count as run 2), over `benign_span_series` after the sealed
`discard_warmup`. The sealed `arm_pair_delta` is not used because its bit labelling
knows only the nine ladder arms; the label here is the §E.6 conjunct the variant removes.
Output `results/ablation/latency-ablation-pinned.json` (raw) and
`results/ablation/latency-ablation-deltas.json`. Run once; refuses to overwrite.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from analysis.latency import (  # noqa: E402
    PHASES,
    RQ4_SPANS,
    Sample,
    benign_span_series,
    bootstrap_median_difference,
    describe,
    discard_warmup,
)
from src.harness import latency_collector  # noqa: E402
from src.harness import measurement_platform as mp  # noqa: E402
from validation.ablation import arms as variants  # noqa: E402
from validation.ablation.run_ablation import install_rebinds  # noqa: E402

OUT_DIR = REPO / "results" / "ablation"
RAW = OUT_DIR / "latency-ablation-pinned.json"
DELTAS = OUT_DIR / "latency-ablation-deltas.json"
CONTROL = "B3"
SAMPLE_FIELDS = ("arm", "scenario_id", "phase", "batch", "repetition", "span", "value_ms")
BIT_REMOVED = {
    "B3 -contain": "containment (R subset-of C_n)",
    "B3 -invoke": "invocation binding",
    "B3 -holder-proof": "holder proof (one limb of the htc_holder bit)",
    "B3 -htc-chain": "HTC chain (one limb of the htc_holder bit)",
    "B3 -context": "context policy",
    "B3 -approval": "approval artifact",
    "B3 -attenuation": "attenuation (containment at P_0 instead of P_n)",
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    ).stdout.strip()


def main() -> int:
    for p in (RAW, DELTAS):
        if p.exists():
            raise SystemExit(f"{p} exists; D-023 runs ONCE and will not overwrite it")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    head, dirty = _git("rev-parse", "HEAD"), bool(_git("status", "--porcelain"))
    install_rebinds()
    mp.require_ac_power()
    pinned = mp.pin_to_performance_cores()
    print(f"pinned to performance cores {list(pinned)}")
    t0 = time.time()
    record = latency_collector.collect(out=RAW)
    elapsed = round(time.time() - t0, 3)
    plan = record["plan"]
    seed, resamples, warmup = (
        plan["bootstrap_seed"],
        plan["bootstrap_resamples"],
        plan["warmup_per_batch"],
    )
    samples = [Sample(**{k: r[k] for k in SAMPLE_FIELDS}) for r in record["samples"]]
    benign = [s for s in samples if s.scenario_id != latency_collector.REFUSAL_SCENARIO]
    kept = discard_warmup(benign, per_batch=warmup)
    deltas = []
    for name in variants.VARIANT_NAMES:
        for phase in PHASES:
            for span in RQ4_SPANS:
                treatment = benign_span_series(kept, arm=name, phase=phase, span=span)
                control = benign_span_series(kept, arm=CONTROL, phase=phase, span=span)
                ci = bootstrap_median_difference(treatment, control, seed=seed, resamples=resamples)
                t, c = describe(treatment), describe(control)
                deltas.append(
                    {
                        "treatment_arm": name,
                        "control_arm": CONTROL,
                        "bit_removed": BIT_REMOVED[name],
                        "phase": phase,
                        "span": span,
                        "point_estimate_ms": t.median - c.median,
                        "ci_low_ms": ci.low,
                        "ci_high_ms": ci.high,
                        "treatment": t.as_dict(),
                        "control": c.as_dict(),
                    }
                )
    DELTAS.write_text(
        json.dumps(
            {
                "_what": (
                    "D-023 part (c): median(variant) - median(B3) per span and phase on the "
                    "pilot corpus, pinned to the performance cores, with the sealed percentile "
                    "bootstrap; each variant is B3 with one E.6 conjunct removed, so each delta "
                    "is the cost of that conjunct on this platform (ADR 0041's one permitted "
                    "per-mechanism case)."
                ),
                "cpu_pinning": {"applied": True, "pinned_logical_cpus": list(pinned)},
                "seed": seed,
                "resamples": resamples,
                "warmup_per_batch": warmup,
                "elapsed_seconds": elapsed,
                "git": {"head": head, "dirty": dirty},
                "deltas": deltas,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for d in deltas:
        if d["phase"] == "warm" and d["span"] in (
            "delegation",
            "presentation",
            "boundary_verification",
        ):
            print(
                f"{d['treatment_arm']:18s} {d['span']:22s} {d['point_estimate_ms']:+8.4f} "
                f"[{d['ci_low_ms']:+.4f}, {d['ci_high_ms']:+.4f}]"
            )
    print(f"WROTE {RAW}\nWROTE {DELTAS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
