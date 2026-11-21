"""Supplementary timing with the online exact-call control (C015)."""

import argparse
import dataclasses
import hashlib
import json
import statistics
from pathlib import Path

from analysis.latency import (
    Sample,
    benign_series,
    benign_span_series,
    bootstrap_median_difference,
    describe,
    discard_warmup,
)
from src.harness import campaign_driver, latency_collector, measurement_platform
from validation.revision.controls import BoundOAuthArm

REPO = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    sources = (
        "validation/revision/matched_latency.py",
        "validation/revision/controls.py",
        "src/harness/latency_collector.py",
        "src/sut/authz/capability_path.py",
    )
    metadata = {
        "evidence_class": "supplementary matched online/offline timing",
        "platform": dataclasses.asdict(measurement_platform.read_platform()),
        "cpu_pinning": "none",
        "source_sha256": {
            name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in sources
        },
    }
    (args.out / "meta.json").write_text(json.dumps(metadata, indent=2) + "\n")
    original = campaign_driver._factories

    def factories(*positional, **keywords):
        result = original(*positional, **keywords)
        result["OAuth-DPoP-call"] = (BoundOAuthArm, result["B2-exchange-task-DPoP"][1])
        return result

    campaign_driver._factories = factories
    try:
        record = latency_collector.collect(out=args.out / "raw.json")
    finally:
        campaign_driver._factories = original
    fields = {field.name for field in dataclasses.fields(Sample)}
    samples = [Sample(**{key: row[key] for key in fields}) for row in record["samples"]]
    benign = [s for s in samples if s.scenario_id == latency_collector.BENIGN_SCENARIO]
    kept = discard_warmup(benign, per_batch=record["plan"]["warmup_per_batch"])
    arms = sorted({s.arm for s in kept})
    totals = {arm: benign_series(kept, arm=arm) for arm in arms}
    stages = {
        arm: {
            span: describe(benign_span_series(kept, arm=arm, span=span)).as_dict()
            for span in ("delegation", "presentation", "boundary_verification")
        }
        for arm in arms
    }
    contrasts = []
    for treatment, control in (
        ("B3", "B0"),
        ("OAuth-DPoP-call", "B2-exchange-task-DPoP"),
        ("OAuth-DPoP-call", "B3"),
        ("OAuth-DPoP-call", "B0"),
    ):
        ci = bootstrap_median_difference(
            totals[treatment], totals[control],
            seed=record["plan"]["bootstrap_seed"],
            resamples=record["plan"]["bootstrap_resamples"],
        )
        contrasts.append({
            "treatment": treatment, "control": control,
            "delta_ms": statistics.median(totals[treatment]) - statistics.median(totals[control]),
            "ci_low_ms": ci.low, "ci_high_ms": ci.high,
        })
    summary = {
        "evidence_class": metadata["evidence_class"],
        "raw_sha256": hashlib.sha256((args.out / "raw.json").read_bytes()).hexdigest(),
        "raw_rows": len(record["samples"]),
        "plan": record["plan"],
        "totals": {arm: describe(values).as_dict() for arm, values in totals.items()},
        "stages": stages, "contrasts": contrasts,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"raw_rows": summary["raw_rows"], "contrasts": contrasts}, indent=2))


if __name__ == "__main__":
    main()
