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

from analysis.latency import (  # noqa: E402
    REFUSAL_PATH_SCENARIO,
    Sample,
    discard_warmup,
    lightweight_claim,
)
from src.harness import frozen_parameters  # noqa: E402

RAW = REPO_ROOT / "results" / "raw" / "latency-pilot.json"
TABLES = REPO_ROOT / "results" / "tables"

SAMPLE_FIELDS = ("arm", "scenario_id", "phase", "batch", "repetition", "span", "value_ms")


def out_path(run: int) -> Path:
    """Run 1 keeps the plain name; every later run takes a distinct one.

    D-009 clause 2 keeps the FIRST run's verdict as the reported one, so a
    re-run must never be able to land on run 1's artefact. Separate paths, plus
    the refuse-if-exists guard below, make overwriting it impossible rather
    than merely discouraged.
    """
    return TABLES / (
        "results-latency-pilot.json" if run == 1 else f"results-latency-pilot-run{run}.json"
    )


def main(argv: "list[str] | None" = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    run = 1
    reason = ""
    for i, tok in enumerate(args):
        if tok == "--run":
            run = int(args[i + 1])
        elif tok == "--reason":
            reason = args[i + 1]
    if run != 1 and not reason:
        print(
            "REFUSED: a re-run requires --reason; D-009 clause 2 records every run AND its reason."
        )
        return 1

    out = out_path(run)
    if out.exists():
        print(f"REFUSED: {out} already exists. A second run is a decision (D-009 clause 2).")
        return 1
    print(f"INPUT run_index [given] = {run}")
    print(f"INPUT run_reason [given] = {reason or '(first run)'}")

    record = json.loads(RAW.read_text(encoding="utf-8"))
    plan = record["plan"]

    margin_ms = frozen_parameters.equivalence_margin_ms()
    seed = plan["bootstrap_seed"]
    resamples = plan["bootstrap_resamples"]

    print(f"INPUT margin_ms   [M frozen_parameters row 1] = {margin_ms}")
    print(f"INPUT seed        [M latency-pilot.json plan] = {seed}")
    print(f"INPUT resamples   [M latency-pilot.json plan] = {resamples}")
    print(f"INPUT corpus_root [M latency-pilot.json top level] = {record.get('corpus_root')}")
    print(f"INPUT run_mode    [M latency-pilot.json top level] = {record.get('run_mode')}")

    all_samples = [Sample(**{k: rec[k] for k in SAMPLE_FIELDS}) for rec in record["samples"]]
    print(f"INPUT samples_loaded [M len(samples[])] = {len(all_samples)}")
    # ADR 0026's exclusion, applied with the SEALED constant, not a local rule:
    # `benign_series` refuses rather than filters, so the refusal-path cell is
    # separated here and reported as its own count. Nothing else is dropped.
    samples = [s for s in all_samples if s.scenario_id != REFUSAL_PATH_SCENARIO]
    excluded = len(all_samples) - len(samples)
    print(f"INPUT refusal_path_scenario [M sealed constant] = {REFUSAL_PATH_SCENARIO}")
    print(f"INPUT samples_excluded_refusal_path [D] = {excluded}")

    # §E.5 / frozen_parameters row 1 Sampling: "warm-up discarded". The plan
    # block names BOTH the mechanism and the parameter --
    #   warmup_discarded_by: "analysis.latency.discard_warmup (the sealed layer
    #                         decides)"
    #   warmup_per_batch:    5
    # -- so this is a sealed function called with a frozen argument, not a rule
    # invented here. Run 1 omitted it and reported n=225, the plan block's
    # `recorded_per_configuration`; the pre-registered count is its
    # `kept_after_warmup_per_configuration` of 210. See DEVIATIONS D-009.
    warmup_per_batch = plan["warmup_per_batch"]
    before = len(samples)
    samples = discard_warmup(samples, per_batch=warmup_per_batch)
    print(f"INPUT warmup_per_batch [M latency-pilot.json plan] = {warmup_per_batch}")
    print(f"INPUT warmup_discarded_by [M latency-pilot.json plan] = {plan['warmup_discarded_by']}")
    print(f"INPUT samples_discarded_warmup [D] = {before - len(samples)}")
    print(f"INPUT samples_into_decision [D] = {len(samples)}")

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
        "corpus_root": record.get("corpus_root"),
        "run_mode": record.get("run_mode"),
        "corpus": (
            "PILOT (fixtures/pilot/golden_thread) -- NOT the confirmatory corpus (D-006, ADR 0047)"
        ),
        "cpu_pinning": "none; pinning exists only in smoke/g3/spike.py (D-009 disclosure)",
        "estimand": "median(B3) - median(B0) over presentation + boundary_verification, warm",
        "decision_rule": "the claim stands iff the 95% bootstrap CI UPPER BOUND < margin_ms",
        "run": {
            "index": run,
            "reason": reason or "first run",
            "warmup_discard_applied": True,
            "note": (
                "Run 1 did NOT apply the pre-registered warm-up discard and reported n=225, "
                "the plan block's `recorded_per_configuration`. Every run from 2 onward applies "
                "analysis.latency.discard_warmup with per_batch read from the plan block, giving "
                "the plan block's `kept_after_warmup_per_configuration`. D-009 clause 2 keeps the "
                "FIRST run's verdict as the reported one; runs are recorded alongside one "
                "another, never in place of one another. Read this artefact with DEVIATIONS D-009."
            ),
        },
        "inputs": {
            "margin_ms": margin_ms,
            "seed": seed,
            "resamples": resamples,
            "samples_loaded": len(all_samples),
            "samples_excluded_refusal_path": excluded,
            "samples_discarded_warmup": before - len(samples),
            "warmup_per_batch": warmup_per_batch,
            "samples_into_decision": len(samples),
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
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
