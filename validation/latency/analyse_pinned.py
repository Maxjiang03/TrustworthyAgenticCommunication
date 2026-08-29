"""D-022 analysis root for the PINNED latency pass. COMPOSITION ROOT ONLY.

Calls exactly the sealed functions that run 2's two composition roots call --
`lightweight_claim` as `tools/run_row1_decision.py` does, `span_descriptives` and
`arm_pair_delta` as `tools/run_rq4_descriptives.py` does -- over
`results/validation/latency-pilot-run3-pinned.json`, with the same inputs read from
the same places (margin from the frozen row 1, seed / resamples / warm-up from the
artefact's plan block, control arm B0). Nothing is recomputed, selected, or
filtered here; refusals are written as the sealed layer states them.

Beside the returned values it places run 2's committed values for the same
quantities, read from `results/tables/results-latency-pilot-run2.json` and
`results/tables/results-latency-pilot-rq4-run2.json`, so the one variable
(pinning) can be read off directly. Run 2 remains the pre-registered reported
value (D-009 clause 2). Refuses to overwrite.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from analysis.latency import (  # noqa: E402
    PHASES,
    REFUSAL_PATH_SCENARIO,
    RQ4_SPANS,
    AnalysisError,
    Sample,
    arm_pair_delta,
    discard_warmup,
    lightweight_claim,
    span_descriptives,
)
from src.harness import frozen_parameters  # noqa: E402

RAW = REPO / "results" / "validation" / "latency-pilot-run3-pinned.json"
META = REPO / "results" / "validation" / "latency-pilot-run3-pinned.meta.json"
RUN2_DECISION = REPO / "results" / "tables" / "results-latency-pilot-run2.json"
RUN2_RQ4 = REPO / "results" / "tables" / "results-latency-pilot-rq4-run2.json"
OUT_DECISION = REPO / "results" / "validation" / "latency-run3-pinned-decision.json"
OUT_RQ4 = REPO / "results" / "validation" / "latency-run3-pinned-rq4.json"
CONTROL_ARM = "B0"
SAMPLE_FIELDS = ("arm", "scenario_id", "phase", "batch", "repetition", "span", "value_ms")


def main() -> int:
    for path in (OUT_DECISION, OUT_RQ4):
        if path.exists():
            raise SystemExit(f"{path} exists; D-022 analyses ONCE and will not overwrite it")
    record = json.loads(RAW.read_text(encoding="utf-8"))
    meta = json.loads(META.read_text(encoding="utf-8"))
    run2_decision = json.loads(RUN2_DECISION.read_text(encoding="utf-8"))
    run2_rq4 = json.loads(RUN2_RQ4.read_text(encoding="utf-8"))
    plan = record["plan"]
    margin_ms = frozen_parameters.equivalence_margin_ms()
    seed, resamples, warmup = (
        plan["bootstrap_seed"],
        plan["bootstrap_resamples"],
        plan["warmup_per_batch"],
    )
    print(f"INPUT margin_ms [frozen row 1] = {margin_ms}; seed = {seed}")
    print(f"INPUT resamples = {resamples}; warmup_per_batch = {warmup}")

    all_samples = [Sample(**{k: rec[k] for k in SAMPLE_FIELDS}) for rec in record["samples"]]
    benign = [s for s in all_samples if s.scenario_id != REFUSAL_PATH_SCENARIO]
    kept = discard_warmup(benign, per_batch=warmup)
    print(f"INPUT samples_loaded = {len(all_samples)}")
    print(f"INPUT excluded_refusal_path = {len(all_samples) - len(benign)}")
    print(f"INPUT discarded_warmup = {len(benign) - len(kept)}; into_decision = {len(kept)}")

    # ---- row-1 decision, exactly as run 2 ------------------------------------
    decision = lightweight_claim(kept, margin_ms=margin_ms, seed=seed, resamples=resamples)
    print(f"VERDICT {decision.verdict}  point={decision.point_estimate_ms}")
    print(f"  ci=[{decision.ci.low}, {decision.ci.high}]")
    OUT_DECISION.write_text(
        json.dumps(
            {
                "_what": (
                    "D-022: the frozen row-1 decision function run over the PINNED latency "
                    "pass (results/validation/latency-pilot-run3-pinned.json). A validation "
                    "series: run 2 (results/tables/results-latency-pilot-run2.json) remains "
                    "the pre-registered reported value and is placed beside it, unedited."
                ),
                "corpus": "PILOT (fixtures/pilot/golden_thread), as D-006 / ADR 0047",
                "cpu_pinning": meta["cpu_pinning"],
                "inputs": {
                    "margin_ms": margin_ms,
                    "seed": seed,
                    "resamples": resamples,
                    "warmup_per_batch": warmup,
                    "samples_loaded": len(all_samples),
                    "samples_excluded_refusal_path": len(all_samples) - len(benign),
                    "samples_discarded_warmup": len(benign) - len(kept),
                    "samples_into_decision": len(kept),
                    "plan": plan,
                },
                "decision_run3_pinned": decision.as_dict(),
                "decision_run2_unpinned_REPORTED_VALUE": run2_decision["decision"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # ---- RQ4 descriptive layer, exactly as run 2 ------------------------------
    reports = span_descriptives(all_samples, warmup_per_batch=warmup)
    arms = sorted({s.arm for s in all_samples})
    deltas, refusals = [], []
    for arm in arms:
        if arm == CONTROL_ARM:
            continue
        for phase in PHASES:
            for span in RQ4_SPANS:
                try:
                    d = arm_pair_delta(
                        kept,
                        treatment_arm=arm,
                        control_arm=CONTROL_ARM,
                        span=span,
                        phase=phase,
                        resamples=resamples,
                        seed=seed,
                    )
                except AnalysisError as exc:
                    refusals.append(
                        {
                            "treatment_arm": arm,
                            "control_arm": CONTROL_ARM,
                            "span": span,
                            "phase": phase,
                            "refused": True,
                            "sealed_message": str(exc),
                        }
                    )
                    continue
                deltas.append(d.as_dict())
    print(
        f"EMITTED span_reports = {len(reports)}; deltas = {len(deltas)}; refusals = {len(refusals)}"
    )

    # Side by side with run 2 on the quantity D-022 names: the warm benign
    # boundary-verification descriptives (median, IQR) per arm.
    def _pick(reps, arm):
        for r in reps:
            if (r["arm"], r["phase"], r["span"], r["series"]) == (
                arm,
                "warm",
                "boundary_verification",
                "benign",
            ):
                return r["descriptives"]
        return None

    run3_reports = [r.as_dict() for r in reports]
    iqr_side_by_side = {
        arm: {
            "run2_unpinned": _pick(run2_rq4["span_reports"], arm),
            "run3_pinned": _pick(run3_reports, arm),
        }
        for arm in arms
    }
    for arm, v in iqr_side_by_side.items():
        a, b = v["run2_unpinned"], v["run3_pinned"]
        print(
            f"BOUNDARY warm {arm:24s} run2 median={a['median']:.4f} iqr={a['iqr']:.4f} | "
            f"run3 pinned median={b['median']:.4f} iqr={b['iqr']:.4f}"
        )

    OUT_RQ4.write_text(
        json.dumps(
            {
                "_what": (
                    "D-022: the RQ4 descriptive layer of the sealed analysis/latency.py run over "
                    "the PINNED latency pass, as returned; nothing is recomputed, selected, or "
                    "compared to any margin. Run 2's descriptives are placed beside the "
                    "boundary-verification quantities for comparison and are unedited."
                ),
                "corpus": "PILOT (fixtures/pilot/golden_thread)",
                "cpu_pinning": meta["cpu_pinning"],
                "control_arm": CONTROL_ARM,
                "inputs": {
                    "seed": seed,
                    "resamples": resamples,
                    "warmup_per_batch": warmup,
                    "samples_loaded": len(all_samples),
                    "samples_into_deltas": len(kept),
                    "plan": plan,
                },
                "span_reports": run3_reports,
                "arm_pair_deltas": deltas,
                "refusals": refusals,
                "boundary_verification_warm_benign_side_by_side": iqr_side_by_side,
                "counts": {
                    "span_reports": len(reports),
                    "arm_pair_deltas": len(deltas),
                    "refusals": len(refusals),
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"WROTE {OUT_DECISION}\nWROTE {OUT_RQ4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
