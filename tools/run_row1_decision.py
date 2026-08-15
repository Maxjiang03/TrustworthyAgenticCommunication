"""Run the sealed row-1 lightweight-claim decision over the pilot latency data.

COMPOSITION ROOT ONLY. This script selects nothing, computes nothing, and
decides nothing. Every input is read from a frozen source:

  margin_ms  <- src/harness/frozen_parameters.py `equivalence_margin_ms()`,
                which parses the sealed docs/frozen_parameters.md row 1
  seed       <- results/raw/latency-pilot.json  plan.bootstrap_seed
  resamples  <- results/raw/latency-pilot.json  plan.bootstrap_resamples
  samples    <- results/raw/latency-pilot.json  samples[]  (1:1 field mirror
                of analysis.latency.Sample: arm, scenario_id, phase, batch,
                repetition, span, value_ms)

and every SELECTION lives inside the sealed analysis/latency.py functions:
`lightweight_claim` fixes the arms (B3 vs B0, ADR 0026) and the warm phase;
`benign_series` excludes the refusal-path scenario; `discard_warmup` drops the
warm-up repetitions; `MEASURED_SEGMENT_SPANS` fixes presentation +
boundary_verification. Nothing here may be substituted without violating
ADR 0026 and DEVIATIONS D-009.

The verdict is written as returned. The script refuses to overwrite an existing
result: a second run is a decision recorded in D-009, never a default.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.latency import Sample, lightweight_claim  # noqa: E402
from src.harness import frozen_parameters  # noqa: E402

RAW = REPO_ROOT / "results" / "raw" / "latency-pilot.json"
OUT = REPO_ROOT / "results" / "tables" / "results-latency-pilot.json"

SAMPLE_FIELDS = ("arm", "scenario_id", "phase", "batch", "repetition", "span", "value_ms")


def main() -> int:
    if OUT.exists():
        print(f"REFUSED: {OUT} already exists. A second run is a decision (D-009 clause 2).")
        return 1
    record = json.loads(RAW.read_text(encoding="utf-8"))
    plan = record["plan"]

    margin_ms = frozen_parameters.equivalence_margin_ms()
    seed = plan["bootstrap_seed"]
    resamples = plan["bootstrap_resamples"]

    print(f"INPUT margin_ms   [M frozen_parameters row 1] = {margin_ms}")
    print(f"INPUT seed        [M latency-pilot.json plan] = {seed}")
    print(f"INPUT resamples   [M latency-pilot.json plan] = {resamples}")
    print(f"INPUT corpus_root [M latency-pilot.json plan] = {plan.get('corpus_root')}")
    print(f"INPUT run_mode    [M latency-pilot.json plan] = {plan.get('run_mode')}")

    samples = [Sample(**{k: rec[k] for k in SAMPLE_FIELDS}) for rec in record["samples"]]
    print(f"INPUT samples_loaded [M len(samples[])] = {len(samples)}")

    decision = lightweight_claim(samples, margin_ms=margin_ms, seed=seed, resamples=resamples)

    print(f"VERDICT {decision.verdict}")
    print(f"  point_estimate_ms = {decision.point_estimate_ms}")
    print(f"  ci_low            = {decision.ci.low}")
    print(f"  ci_high           = {decision.ci.high}")
    print(f"  margin_ms         = {decision.margin_ms}")
    print(f"  confidence        = {decision.confidence}")
    print(f"  resamples         = {decision.resamples}")
    for label, d in (("treatment", decision.treatment), ("control", decision.control)):
        print(f"  {label}: n={d.n} median={d.median} p95={d.p95} iqr={d.iqr}")

    payload = {
        "_what": (
            "The pre-registered frozen row 1 equivalence decision, run ONCE over "
            "results/raw/latency-pilot.json by the composition root named in "
            "DEVIATIONS D-009. The verdict is as returned by the sealed "
            "analysis/latency.py lightweight_claim; nothing here is recomputed."
        ),
        "corpus": (
            "PILOT (fixtures/pilot/golden_thread) -- NOT the confirmatory corpus (D-006, ADR 0047)"
        ),
        "cpu_pinning": "none; pinning exists only in smoke/g3/spike.py (D-009 disclosure)",
        "estimand": "median(B3) - median(B0) over presentation + boundary_verification, warm",
        "decision_rule": "the claim stands iff the 95% bootstrap CI UPPER BOUND < margin_ms",
        "inputs": {
            "margin_ms": margin_ms,
            "seed": seed,
            "resamples": resamples,
            "samples_loaded": len(samples),
            "plan": plan,
        },
        "decision": {
            "verdict": decision.verdict,
            "point_estimate_ms": decision.point_estimate_ms,
            "ci": {"low": decision.ci.low, "high": decision.ci.high},
            "margin_ms": decision.margin_ms,
            "confidence": decision.confidence,
            "resamples": decision.resamples,
            "treatment": {
                "n": decision.treatment.n,
                "median": decision.treatment.median,
                "p95": decision.treatment.p95,
                "iqr": decision.treatment.iqr,
            },
            "control": {
                "n": decision.control.n,
                "median": decision.control.median,
                "p95": decision.control.p95,
                "iqr": decision.control.iqr,
            },
        },
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
