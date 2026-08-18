"""Run the sealed RQ4 descriptive layer over the pilot latency data, once.

COMPOSITION ROOT ONLY (ADR 0048, third named exception, dated addition of
2026-08-18). This script selects nothing, computes nothing, and decides
nothing. It invokes exactly two sealed functions and writes what they return:

  span_descriptives   Descriptives for EVERY arm x phase x span x series
                      (benign / refusal_path); discards warm-up internally
                      through the sealed discard_warmup with the per_batch
                      handed to it here, READ from the plan block.
  arm_pair_delta      median(arm) - median(B0) with a bootstrap interval, for
                      EVERY arm against B0, EVERY span, BOTH phases; labelled
                      by the sealed E.5 bit derivation. It does NOT discard
                      warm-up itself, so the samples are passed through the
                      sealed discard_warmup first, exactly as run 2 of the
                      row-1 decision did (DEVIATIONS D-009, D-014 clause 2).

Every input is read from a frozen source:

  seed, resamples, warmup_per_batch  <- results/raw/latency-pilot.json  plan
  control arm                        <- "B0", the study's unprotected baseline
                                        (ADR 0026's control; CLAIMS_LEDGER C1)
  samples                            <- results/raw/latency-pilot.json samples[]

Refusals are recorded as refusals: the sealed layer refuses any pair involving
B1 (ADR 0035, analysis/latency.py e5_bit_difference), and that refusal is
written into the artefact with the sealed message, never worked around.

The script refuses to overwrite an existing result: a second run is a decision
recorded in D-014, never a default. Nothing here carries a verdict, a margin,
or a comparison to the 20 ms row-1 margin (D-014 clause 6).
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.latency import (  # noqa: E402
    PHASES,
    REFUSAL_PATH_SCENARIO,
    RQ4_SPANS,
    AnalysisError,
    Sample,
    arm_pair_delta,
    discard_warmup,
    span_descriptives,
)

RAW = REPO_ROOT / "results" / "raw" / "latency-pilot.json"
TABLES = REPO_ROOT / "results" / "tables"
CONTROL_ARM = "B0"

SAMPLE_FIELDS = ("arm", "scenario_id", "phase", "batch", "repetition", "span", "value_ms")


def out_path(run: int) -> Path:
    """Run 1 keeps the plain name; every later run takes a distinct one (D-014 clause 5)."""
    return TABLES / (
        "results-latency-pilot-rq4.json" if run == 1 else f"results-latency-pilot-rq4-run{run}.json"
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
            "REFUSED: a re-run requires --reason; D-014 clause 5 records every run AND its reason."
        )
        return 1

    out = out_path(run)
    if out.exists():
        print(f"REFUSED: {out} already exists. A second run is a decision (D-014 clause 5).")
        return 1
    print(f"INPUT run_index [given] = {run}")
    print(f"INPUT run_reason [given] = {reason or '(first run)'}")

    record = json.loads(RAW.read_text(encoding="utf-8"))
    plan = record["plan"]
    seed = plan["bootstrap_seed"]
    resamples = plan["bootstrap_resamples"]
    warmup_per_batch = plan["warmup_per_batch"]

    print(f"INPUT seed             [M latency-pilot.json plan] = {seed}")
    print(f"INPUT resamples        [M latency-pilot.json plan] = {resamples}")
    print(f"INPUT warmup_per_batch [M latency-pilot.json plan] = {warmup_per_batch}")
    print(f"INPUT warmup_discarded_by [M plan] = {plan['warmup_discarded_by']}")
    print(
        f"INPUT kept_after_warmup_per_configuration [M plan] = "
        f"{plan['kept_after_warmup_per_configuration']}"
    )
    print(f"INPUT corpus_root [M top level] = {record.get('corpus_root')}")
    print(f"INPUT run_mode    [M top level] = {record.get('run_mode')}")
    print(f"INPUT control_arm [fixed: ADR 0026 control, C1 baseline] = {CONTROL_ARM}")

    all_samples = [Sample(**{k: rec[k] for k in SAMPLE_FIELDS}) for rec in record["samples"]]
    print(f"INPUT samples_loaded [M len(samples[])] = {len(all_samples)}")

    # ---- span_descriptives: the sealed function discards warm-up itself -------
    reports = span_descriptives(all_samples, warmup_per_batch=warmup_per_batch)
    print(f"EMITTED span_reports = {len(reports)}")
    ns = sorted({r.descriptives.n for r in reports})
    print(f"EMITTED span_reports.distinct_n = {ns}")
    for r in reports:
        d = r.descriptives
        print(
            f"SPAN {r.arm} | {r.phase} | {r.span} | {r.series} | "
            f"n={d.n} median={d.median} p95={d.p95} iqr={d.iqr}"
        )

    # ---- arm_pair_delta: refusal path separated, then warm-up discarded, both
    # by the SEALED constant and the SEALED function -------------------------
    # ADR 0026's exclusion, applied exactly as tools/run_row1_decision.py:96-100
    # applies it: `benign_span_series` REFUSES rather than filters when the
    # refusal-path scenario reaches it, so that scenario is separated here with
    # the sealed constant and its count is printed. Run 1 of D-014 omitted this
    # and every delta was refused by the sealed layer -- the artefact of that
    # run is kept, unedited, and D-014 records it. Nothing else is dropped.
    benign_only = [s for s in all_samples if s.scenario_id != REFUSAL_PATH_SCENARIO]
    print(f"INPUT refusal_path_scenario [M sealed constant] = {REFUSAL_PATH_SCENARIO}")
    print(
        f"INPUT samples_separated_refusal_path_for_deltas [D] = "
        f"{len(all_samples) - len(benign_only)}"
    )
    before = len(benign_only)
    kept = discard_warmup(benign_only, per_batch=warmup_per_batch)
    print(f"INPUT samples_discarded_warmup_for_deltas [D] = {before - len(kept)}")
    print(f"INPUT samples_into_deltas [D] = {len(kept)}")

    arms = sorted({s.arm for s in all_samples})
    deltas = []
    refusals = []
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
                    print(f"REFUSED {arm} vs {CONTROL_ARM} | {phase} | {span} | {exc}")
                    continue
                deltas.append(d.as_dict())
                print(
                    f"DELTA {arm} vs {CONTROL_ARM} | {phase} | {span} | {d.label} | "
                    f"point={d.point_estimate_ms} ci=[{d.ci.low}, {d.ci.high}] | "
                    f"treatment n={d.treatment.n} median={d.treatment.median} "
                    f"p95={d.treatment.p95} iqr={d.treatment.iqr} | "
                    f"control n={d.control.n} median={d.control.median} | "
                    f"mechanism={d.mechanism} unmodelled={len(d.unmodelled)}"
                )
    print(f"EMITTED deltas = {len(deltas)}")
    print(f"EMITTED refusals = {len(refusals)}")

    payload = {
        "_what": (
            "The RQ4 descriptive layer of the sealed analysis/latency.py, run ONCE over "
            "results/raw/latency-pilot.json by the composition root named in DEVIATIONS "
            "D-014: every SpanReport from span_descriptives and every ArmPairDelta from "
            "arm_pair_delta against B0, as returned. Nothing here is recomputed, selected, "
            "or compared to any margin. Refusals are recorded as the sealed layer states them."
        ),
        "corpus_root": record.get("corpus_root"),
        "run_mode": record.get("run_mode"),
        "corpus": (
            "PILOT (fixtures/pilot/golden_thread) -- NOT the confirmatory corpus (D-006, ADR 0047)"
        ),
        "cpu_pinning": "none; pinning exists only in smoke/g3/spike.py (D-009 / D-014 disclosure)",
        "substrate": ("in-process harness on one machine (ADR 0034); no network hop is implied"),
        "control_arm": CONTROL_ARM,
        "run": {"index": run, "reason": reason or "(first run)"},
        "inputs": {
            "seed": seed,
            "resamples": resamples,
            "warmup_per_batch": warmup_per_batch,
            "samples_loaded": len(all_samples),
            "samples_separated_refusal_path_for_deltas": len(all_samples) - len(benign_only),
            "samples_discarded_warmup_for_deltas": before - len(kept),
            "samples_into_deltas": len(kept),
            "plan": plan,
        },
        "span_reports": [r.as_dict() for r in reports],
        "arm_pair_deltas": deltas,
        "refusals": refusals,
        "counts": {
            "span_reports": len(reports),
            "span_reports_distinct_n": ns,
            "arm_pair_deltas": len(deltas),
            "refusals": len(refusals),
        },
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
