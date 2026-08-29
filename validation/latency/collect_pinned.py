"""D-022: the RQ4 latency pass repeated ONCE with the process pinned to the detected
performance cores -- the single variable that D-009 disclosed as uncontrolled
("CPU affinity was not pinned; bimodality from core migration cannot be excluded").

Everything else is the sealed collector as it ran for D-006: same pilot corpus,
same plan block (3 batches x 75 repetitions, warm-up 5 per batch, shuffled arm
order from the same order seed), same spans, ledger off. The sealed
`latency_collector.collect` is called with only its output path changed; nothing
sealed is edited. The pinning is `measurement_platform.pin_to_performance_cores`,
the same call gate G-3 makes, applied to THIS process before the collector runs;
child processes (the AS) inherit the affinity mask.

Run 2 of the row-1 decision (results/tables/results-latency-pilot-run2.json)
remains the pre-registered reported value. This pass is a validation series and
is written to results/validation/, never to results/raw/. Run once; refuses to
overwrite.
"""

import dataclasses
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.harness import latency_collector  # noqa: E402
from src.harness import measurement_platform as mp  # noqa: E402

RAW_RUN2 = REPO / "results" / "raw" / "latency-pilot.json"
OUT = REPO / "results" / "validation" / "latency-pilot-run3-pinned.json"
META = REPO / "results" / "validation" / "latency-pilot-run3-pinned.meta.json"


def _jsonable(obj):
    if dataclasses.is_dataclass(obj):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    return obj if isinstance(obj, (str, int, float, bool)) or obj is None else str(obj)


def main() -> int:
    for path in (OUT, META):
        if path.exists():
            raise SystemExit(f"{path} exists; D-022 runs ONCE and will not overwrite it")
    mp.require_ac_power()
    platform = mp.read_platform()
    pinned = mp.pin_to_performance_cores()
    print(f"pinned to performance cores {list(pinned)}")
    t0 = time.time()
    record = latency_collector.collect(out=OUT)
    elapsed = round(time.time() - t0, 3)
    run2_plan = json.loads(RAW_RUN2.read_text(encoding="utf-8"))["plan"]
    META.write_text(
        json.dumps(
            {
                "_what": (
                    "D-022 sidecar for results/validation/latency-pilot-run3-pinned.json: the "
                    "sealed collector's output is left exactly as written; this file records the "
                    "one variable (CPU affinity pinned to the detected performance cores) and the "
                    "platform as read at run time."
                ),
                "raw_artefact": "results/validation/latency-pilot-run3-pinned.json",
                "cpu_pinning": {
                    "applied": True,
                    "pinned_logical_cpus": list(pinned),
                    "mechanism": (
                        "src.harness.measurement_platform.pin_to_performance_cores (as gate G-3)"
                    ),
                },
                "plan_identical_to_run2": record["plan"] == run2_plan,
                "samples": len(record["samples"]),
                "elapsed_seconds": elapsed,
                "platform": _jsonable(platform),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"samples={len(record['samples'])} elapsed={elapsed}s")
    print(f"plan_identical_to_run2={record['plan'] == run2_plan}")
    print(f"WROTE {OUT}\nWROTE {META}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
