"""RQ4's measurement: the sealed §6 sampling plan, driven, durations persisted.

Part H step 7 ran its **security half only**. RQ4 had no data and neither did
`frozen_parameters` row 1's `lightweight_claim`, whose decision rule is the 95%
bootstrap CI upper bound on `median(B3) − median(B0)` against the 20 ms margin —
without samples there is no interval, so that claim could neither hold nor be
retracted. This is the other half. ADR 0047.

**Measured on the PILOT corpus, and that is what the sealed specification
says.** Frozen row 1, `docs/PRE_REGISTRATION.md` §6, ADR 0026, the design
document's §J.3 item 12 and `analysis/latency.py` all name the refusal-path cell
`gt-f1-chain-tamper` — a **pilot** id — and none of them names the confirmatory
one. Measuring on the corpus the specification names is following the
pre-registration, not working around it. RQ4 asks for **mechanism** cost, which
is a property of the arms rather than of a corpus's attack content, and G-3 was
itself adjudicated on the golden thread.

**No verdict reaches this artifact.** The loop executes scenarios, so verdicts
are computed internally; none is read and none is written. The security half's
"once" is consumed, and a latency artifact carrying verdicts would be
indistinguishable, in a results table, from a re-run.

**Raw per-repetition values, never summaries, each with a wall-clock stamp.**
That is the Sighting C decision: the undiagnosed 217 s-versus-36 s stall is
invisible inside a summary and visible, locatable and reportable inside a raw
series. **No outlier or exclusion rule is applied** — Sighting C has never been
observed as a per-operation stall, so a threshold now would be invented for an
effect not shown to exist, and a threshold set later, after seeing the data, is
what pre-registration forbids. The estimand is a median, which is robust to a
handful of stalls, and the plan already reports batches separately, so a stall
surfaces in that batch's p95 and IQR. Report, do not discard.

    uv run python -m src.harness.latency_collector [--out PATH]
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.harness import campaign_driver as driver
from src.harness.runner import GoldenThreadRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_RAW = REPO_ROOT / "results" / "raw"
PILOT_CORPUS = REPO_ROOT / "fixtures" / "pilot" / "golden_thread"

# The two cells this pass measures, and why only two. ADR 0026 frames the
# estimand as a BENIGN per-arm series with one cell excluded by name, so the
# pass needs exactly that pair: the benign golden thread, and the refusal path
# as its own series. Adding attack cells would pool credential-fault work into
# a "benign" mean that `analysis/latency.py` would not refuse, because its
# by-name refusal names only the refusal path.
BENIGN_SCENARIO = "gt-benign"
REFUSAL_SCENARIO = "gt-f1-chain-tamper"
SCENARIOS = (BENIGN_SCENARIO, REFUSAL_SCENARIO)

# §6, implemented as written and NOT amended: "≥ 200 end-to-end repetitions per
# configuration across ≥ 3 independent batches" with "warm-up discarded".
# 3 × 75 = 225 recorded per (arm, scenario, phase); `discard_warmup(per_batch=5)`
# drops the first 5 of each group, leaving 3 × 70 = 210 ≥ 200. The warm-up is
# recorded and discarded by the ANALYSIS, not dropped here: this file persists
# what happened and the sealed layer decides what counts.
BATCHES = 3
REPETITIONS_PER_BATCH = 75
WARMUP_PER_BATCH = 5

# Cold and warm are reported separately and never pooled (§6). The
# operationalisation is stated rather than assumed, because "cold" has no
# meaning independent of what is fresh:
#   cold — the FIRST invocation of a freshly provisioned arm instance;
#   warm — the subsequent invocations of that same instance.
# A fresh arm per cold repetition is what makes ≥ 200 cold samples possible;
# the AS process, its TLS listener and every Ed25519 key are created ONCE for
# the whole pass, so handshakes and key generation stay out of the measured
# path exactly as §6 requires.
PHASES = ("cold", "warm")

# Recorded, not merely used (§6: "seed required and recorded"). Two seeds: one
# orders the arms within each batch, one drives the bootstrap. A seed nobody
# wrote down makes 10,000 resamples unreproducible.
ORDER_SEED = 20260807
BOOTSTRAP_SEED = 4815162342
RESAMPLES = 10_000

SPANS = ("setup", "delegation", "presentation", "boundary_verification", "end_to_end")

# Every field the campaign's SECURITY artifact carries that this one must not.
# Named here so the guard is a list a reader can check rather than a promise.
FORBIDDEN_VERDICT_FIELDS = (
    "reference_allow",
    "observed_forwarded",
    "admission_breach",
    "realized_harm",
    "false_block",
    "log_integrity_failure",
    "linkage",
    "admitted",
    "reason_code",
    "effect_count",
)


class LatencyCollectorError(Exception):
    """The collection refused to run, or refused to overwrite a result."""


def output_path() -> Path:
    return RESULTS_RAW / "latency-pilot.json"


def refuse_if_written(path: Path) -> None:
    """Write-once, the same rule the campaign driver follows (§J.4 item 14)."""
    if path.exists():
        raise LatencyCollectorError(
            f"{path} already exists. Raw traces are write-once: this collector will not "
            "overwrite one. Delete it deliberately and record the reason in DEVIATIONS.md."
        )


def _arm_order(batch: int, arms: list[str]) -> list[str]:
    """§6: condition order randomized within each batch, from a RECORDED seed.

    Seeded per batch so the order differs between batches — which is the point
    of counterbalancing — while the whole pass stays reproducible from
    `ORDER_SEED` alone.
    """
    ordered = list(arms)
    random.Random(ORDER_SEED + batch).shuffle(ordered)
    return ordered


def collect(*, out: Path | None = None) -> dict[str, Any]:
    """Drive the sealed plan and persist raw per-repetition durations."""
    destination = out if out is not None else output_path()
    refuse_if_written(destination)

    runner = GoldenThreadRunner(corpus_dir=PILOT_CORPUS, run_mode="pilot")
    corpus_document = json.loads((PILOT_CORPUS / "corpus.json").read_text(encoding="utf-8"))
    corpus = {"issuer": corpus_document["issuer"], "audience": corpus_document["audience"]}
    document = driver._as_document(runner, BENIGN_SCENARIO, corpus=corpus)  # noqa: SLF001

    samples: list[dict[str, Any]] = []
    started = time.perf_counter()

    # ONE AS process for the whole pass: persistent TLS, and every Ed25519 key
    # minted once at start-up (§6 — handshakes and signature randomness out of
    # the measured path).
    with driver.ASProcess(document, runner.seed) as running_as:
        factories = driver._factories(  # noqa: SLF001
            runner, running_as, document, monitor_attached=None, scenario_id=BENIGN_SCENARIO
        )
        arms = list(factories)
        for batch in range(BATCHES):
            for arm_name in _arm_order(batch, arms):
                factory, setup = factories[arm_name]
                for scenario_id in SCENARIOS:
                    # COLD: a fresh arm each repetition, first invocation only.
                    for repetition in range(REPETITIONS_PER_BATCH):
                        samples.extend(
                            _one_repetition(
                                runner,
                                factory(),
                                setup,
                                scenario_id=scenario_id,
                                arm=arm_name,
                                phase="cold",
                                batch=batch,
                                repetition=repetition,
                            )
                        )
                    # WARM: one arm instance, invoked repeatedly.
                    warm_arm = factory()
                    for repetition in range(REPETITIONS_PER_BATCH):
                        samples.extend(
                            _one_repetition(
                                runner,
                                warm_arm,
                                setup,
                                scenario_id=scenario_id,
                                arm=arm_name,
                                phase="warm",
                                batch=batch,
                                repetition=repetition,
                            )
                        )

    record = {
        "_what": (
            "RQ4's per-component latency series, raw per-repetition, measured on the PILOT "
            "corpus because the sealed specification names it: frozen row 1, PRE_REGISTRATION "
            "§6, ADR 0026, the design document §J.3 item 12 and analysis/latency.py all name "
            "the refusal-path cell `gt-f1-chain-tamper`. NO VERDICT FIELD APPEARS HERE: the "
            "security half of Part H step 7 ran once and its 'once' is consumed, and a latency "
            "artifact carrying verdicts would be indistinguishable from a re-run."
        ),
        "run_mode": "pilot",
        "corpus_root": "fixtures/pilot/golden_thread",
        "scenarios": list(SCENARIOS),
        "spans": list(SPANS),
        "plan": {
            "source": "docs/PRE_REGISTRATION.md §6, implemented as written and not amended",
            "batches": BATCHES,
            "repetitions_per_batch": REPETITIONS_PER_BATCH,
            "recorded_per_configuration": BATCHES * REPETITIONS_PER_BATCH,
            "warmup_per_batch": WARMUP_PER_BATCH,
            "kept_after_warmup_per_configuration": BATCHES
            * (REPETITIONS_PER_BATCH - WARMUP_PER_BATCH),
            "phases": list(PHASES),
            "phase_definition": {
                "cold": "the first invocation of a freshly provisioned arm instance",
                "warm": "a subsequent invocation of that same instance",
            },
            "order": "arms shuffled within each batch from ORDER_SEED + batch",
            "order_seed": ORDER_SEED,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": RESAMPLES,
            "warmup_discarded_by": "analysis.latency.discard_warmup (the sealed layer decides)",
            "exclusion_rule": (
                "NONE. No outlier or stall rule is applied. Sighting C has never been observed "
                "as a per-operation stall, so a threshold now would be invented for an effect "
                "not shown to exist, and a threshold set after seeing data is what "
                "pre-registration forbids. Raw values are reported, not discarded."
            ),
            "ledger_backed": False,
            "ledger_note": (
                "the effect ledger is instrument, not mechanism, and ADR 0026 excludes every "
                "ledger append from the measured segment by name; `end_to_end` here therefore "
                "carries no ledger write"
            ),
        },
        "wall_clock_note": (
            "every sample carries `started_at`, the UTC wall clock at the start of its "
            "repetition, so a stall can be located in time (ADR 0038 Sighting C)"
        ),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "samples": samples,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    refuse_if_written(destination)
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def _one_repetition(
    runner: GoldenThreadRunner,
    instance: Any,
    setup: Any,
    *,
    scenario_id: str,
    arm: str,
    phase: str,
    batch: int,
    repetition: int,
) -> list[dict[str, Any]]:
    """One invocation; five span rows out, no verdict.

    `run_scenario` returns a full `ScenarioRun` carrying the sealed intent, the
    observation and the mediation records. **Only `run.timing` is read**, and
    only its durations; nothing else on that object is touched.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    run = runner.run_scenario(
        scenario_id,
        instance,
        setup=dict(setup or {}),
        ledger_backed=False,
        sut_mode="in-process",
    )
    durations = run.timing.durations_ms() if run.timing is not None else {}
    return [
        {
            "arm": arm,
            "scenario_id": scenario_id,
            "phase": phase,
            "batch": batch,
            "repetition": repetition,
            "span": span,
            "value_ms": durations[span],
            "started_at": started_at,
        }
        for span in SPANS
        if span in durations
    ]


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="RQ4 latency collection over the pilot corpus")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        record = collect(out=args.out)
    except LatencyCollectorError as exc:
        print(f"latency collection refused: {exc}", file=sys.stderr)
        return 1
    print(
        f"pilot: {len(record['samples'])} span rows, "
        f"{record['plan']['recorded_per_configuration']} repetitions per configuration, "
        f"{record['elapsed_seconds']} s"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(main())
