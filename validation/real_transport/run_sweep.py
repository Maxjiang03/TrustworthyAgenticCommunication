"""The real-transport sweep over EVERY scored cell (DEVIATIONS D-018).

Post-seal validation apparatus. Outside `src/` and `analysis/`; no sealed file
is edited and every covered file stays byte-identical to `ffa216e`.

**This module drives nothing itself.** D-017 delivered 18 of 143 cells and named
the blocker: the remaining scenarios need credential-fault injection and ADR 0030
artifact minting, and reproducing those outside the sealed runner risks a harness
whose AGREEMENT would look like evidence. The answer is not to reproduce them.
Every piece of that orchestration -- NA routing from the sealed record,
`label_artifacts.mint_for_scenario`, `clock_refusal`, `credential_faults.validate`,
the wrong-audience token, one-clock-per-cell, both monitor configurations, and
the oracle scoring -- already lives in sealed `campaign.py` / `campaign_driver.py`.
So this calls **the sealed campaign driver** and moves the transport underneath
it. All 143 cells are orchestrated by sealed code.

**Exactly two names are rebound**, in the `src.harness.runner` namespace:

1. `create_connected_server_and_client_session` -- the SDK's IN-MEMORY object
   stream pair (`runner.py:864`) becomes a real `stdio_client` to a child
   process. This is the one variable under test. ADR 0020 anticipated it: "an
   SDK-backed adapter later replaces one constructor call site."
2. `install_boundary` -- intercepted ONLY to carry the runner's own sealed
   closures (`decide`, `correlation_provider`, `emit`) across to the child,
   where SEALED `install_boundary` installs the SEALED boundary on the SEALED
   server. The closures execute in the parent, unmodified.

The parent's own `server` object is still built by sealed `build_server` and is
then inert: the real server is the child's. That is stated rather than hidden.

**Comparison target**, unchanged from D-017 clause 3: per cell, whether the
boundary admitted or refused, against `campaign-confirmatory.json`'s
`observed_forwarded`. The sweep runs `ledger_backed=False` (D-018 states why),
so effect-derived predicates are configuration artefacts here and are excluded
from comparison BY CONSTRUCTION, not by selection.

**A seam fault is never scored.** If the channel breaks, the sealed boundary
cannot get an answer, raises, and the cell would read as BLOCKED -- a harness
fault wearing the costume of a result. Every cell that saw a seam fault is
reported as a harness error and removed from the comparable denominator in the
open.
"""

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from mcp import ClientSession  # noqa: E402
from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: E402

from src.harness import campaign_driver  # noqa: E402
from src.harness import runner as runner_module  # noqa: E402
from validation.real_transport.seam_channel import SeamServer  # noqa: E402

SEALED_CAMPAIGN = REPO / "results" / "raw" / "campaign-confirmatory.json"
DEFAULT_OUT = REPO / "results" / "validation" / "real-transport-sweep.json"
DEFAULT_RECORD = REPO / "results" / "validation" / "real-transport-campaign.json"
CHILD = REPO / "validation" / "real_transport" / "mcp_boundary_child.py"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"


class Sweep:
    """Holds the cross-process state the two rebinds need."""

    def __init__(self) -> None:
        self.seams = SeamServer()
        self.effects_dir = Path(tempfile.mkdtemp(prefix="aasc-sweep-"))
        self.current_cid: str | None = None
        self.faults_by_cell: dict[str, list[str]] = {}
        self.children_spawned = 0
        self.tools_over_the_wire: list[str] = []

    # -- rebind 1 ------------------------------------------------------------
    def install_boundary(self, server: Any, *, decide, correlation_provider, emit) -> None:
        """Stands in for `runner.install_boundary` in the PARENT only.

        The parent's server is left unwrapped on purpose -- it is never called,
        because the real server is the child's. The three closures are the
        runner's own and are bound for the child to reach.
        """
        self.current_cid = str(correlation_provider())
        self.seams.bind(decide=decide, correlation_provider=correlation_provider, emit=emit)
        return None

    # -- rebind 2 ------------------------------------------------------------
    @asynccontextmanager
    async def session(self, _mcp_server: Any):
        """Stands in for the SDK's in-memory pair: a REAL stdio transport.

        `_mcp_server` is the parent's inert server object and is deliberately
        ignored; the child builds its own from the same sealed `build_server`.
        """
        effects = self.effects_dir / f"effects-{self.children_spawned:04d}.jsonl"
        env = dict(os.environ)
        env["AASC_VALIDATION_EFFECTS"] = str(effects)
        env["AASC_SEAM_PORT"] = str(self.seams.port)
        env["PYTHONIOENCODING"] = "utf-8"
        params = StdioServerParameters(
            command=str(PYTHON),
            args=["-X", "utf8", str(CHILD)],
            env=env,
            cwd=str(REPO),
        )
        self.children_spawned += 1
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    if not self.tools_over_the_wire:
                        listed = await client.list_tools()
                        self.tools_over_the_wire = sorted(t.name for t in listed.tools)
                    yield client
        finally:
            if self.current_cid is not None:
                faults = self.seams.faults_this_cell()
                if faults:
                    self.faults_by_cell.setdefault(self.current_cid, []).extend(faults)


def compare(record: Mapping[str, Any], sealed: Mapping[str, Any], sweep: Sweep) -> dict[str, Any]:
    """Per cell: did the boundary reach the same admit/refuse decision?"""

    def key(cell: Mapping[str, Any]) -> tuple[str, str, Any]:
        return (str(cell["scenario_id"]), str(cell["arm"]), cell.get("monitor_attached"))

    sealed_by_key = {key(c): c for c in sealed["cells"]}

    agreements: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    harness_errors: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []

    for cell in record["cells"]:
        k = key(cell)
        cid = str(cell.get("correlation_id", ""))
        row = {
            "scenario_id": k[0],
            "arm": k[1],
            "monitor_attached": k[2],
            "real": bool(cell["observed_forwarded"]),
            "reason_FOR_DIAGNOSIS_ONLY": cell.get("reason_code_FOR_DIAGNOSIS_ONLY"),
        }
        if cid in sweep.faults_by_cell:
            harness_errors.append(dict(row, seam_faults=sweep.faults_by_cell[cid]))
            continue
        reference = sealed_by_key.get(k)
        if reference is None:
            unmatched.append(row)
            continue
        row["sealed"] = bool(reference["observed_forwarded"])
        (agreements if row["real"] == row["sealed"] else disagreements).append(row)

    sealed_keys = set(sealed_by_key)
    real_keys = {key(c) for c in record["cells"]}
    return {
        "counts": {
            "sealed_campaign_cells": len(sealed_keys),
            "cells_driven_over_real_transport": len(record["cells"]),
            "child_processes_spawned": sweep.children_spawned,
            "harness_errors": len(harness_errors),
            "compared": len(agreements) + len(disagreements),
            "agreements": len(agreements),
            "disagreements": len(disagreements),
            "unscorable_this_run": len(record["unscorable"]),
            "cells_in_sealed_campaign_not_driven_here": len(sealed_keys - real_keys),
        },
        "disagreements": disagreements,
        "harness_errors": harness_errors,
        "cells_in_sealed_campaign_not_driven_here": sorted(
            list(k) for k in (sealed_keys - real_keys)
        ),
        "unmatched_cells_not_in_sealed_campaign": unmatched,
        "unscorable_this_run": record["unscorable"],
        "cells": agreements + disagreements,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="D-018: the real-transport sweep, every cell")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--record", type=Path, default=DEFAULT_RECORD)
    args = parser.parse_args(argv)

    if args.out.exists():
        raise SystemExit(f"{args.out} exists; D-018 runs ONCE and will not overwrite it")

    sealed = json.loads(SEALED_CAMPAIGN.read_text(encoding="utf-8"))
    sweep = Sweep()

    # THE TWO REBINDS. Nothing else about the sealed campaign changes.
    runner_module.install_boundary = sweep.install_boundary
    runner_module.create_connected_server_and_client_session = sweep.session

    print(f"seam channel on 127.0.0.1:{sweep.seams.port}; child = {CHILD.name}")
    record = campaign_driver.run(
        run_mode="confirmatory",
        ledger_backed=False,  # D-018: the ledger directory is fixed and is tracked evidence
        sut_mode="in-process",
        out=args.record,
    )
    sweep.seams.close()

    report = compare(record, sealed, sweep)
    report = {
        "_what": (
            "D-018: every scored cell of the sealed confirmatory campaign, re-driven with a REAL "
            "stdio MCP transport to the sealed server in a CHILD PROCESS, where the SEALED "
            "mediation boundary decides on wire-parsed arguments. The campaign orchestration is "
            "the sealed campaign driver's, unmodified; two names are rebound in the runner "
            "namespace and nothing sealed is re-implemented."
        ),
        "the_two_rebinds": [
            "src.harness.runner.create_connected_server_and_client_session -> real stdio child",
            "src.harness.runner.install_boundary -> carries the runner's own sealed closures "
            "to the child, where SEALED install_boundary installs the SEALED boundary",
        ],
        "boundary_placement": (
            "SERVER-SIDE, in the child, wrapping Tool.fn as the campaign does. D-017 run 1 had to "
            "move it client-side; that residual is retired here."
        ),
        "no_latency_claim": (
            "ADR 0034 excludes a loopback round trip from the measured segment by name. No timing "
            "from this run is a result, and none is reported."
        ),
        "ledger": (
            "ledger_backed=False -- the ledger directory is fixed at results/_ledger/<run_mode>/ "
            "and the confirmatory ledger is tracked evidence this run must not write into. Per "
            "ADR 0014, realized_harm is then None for every cell, so effect-derived predicates "
            "are configuration artefacts here and are excluded from comparison BY CONSTRUCTION."
        ),
        "comparison_target": (
            "observed_forwarded, per cell, keyed (scenario_id, arm, monitor_attached)"
        ),
        "transport_evidence": {
            "tools_listed_over_real_stdio": sweep.tools_over_the_wire,
            "child_processes_spawned": sweep.children_spawned,
        },
        "campaign_record": str(args.record.relative_to(REPO)).replace("\\", "/"),
        **report,
        "residuals_that_travel_with_any_agreement": [
            "the A2A hop is still an in-process port, not a network protocol",
            "the tools are still sandboxed intent recorders; nothing is sent, written or deleted",
            "the server is still the harness's own five-tool stub, not a"
            " third-party implementation",
            "the machine is still one machine",
            "this run has no effect ledger, so the harm columns are not validated here",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=False, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    c = report["counts"]
    print(f"TRANSPORT tools_over_real_stdio = {sweep.tools_over_the_wire}")
    print(f"CHILDREN spawned = {c['child_processes_spawned']}")
    for row in report["disagreements"]:
        print(
            f"DISAGREE {row['scenario_id']:32s} {row['arm']:24s} "
            f"real={row['real']} sealed={row['sealed']}"
        )
    for row in report["harness_errors"]:
        print(f"HARNESS-ERROR {row['scenario_id']:28s} {row['arm']:24s} {row['seam_faults']}")
    print(f"  cells driven    = {c['cells_driven_over_real_transport']}")
    print(f"  harness errors  = {c['harness_errors']}")
    print(f"  compared        = {c['compared']}")
    print(f"  agreements      = {c['agreements']}")
    print(f"  DISAGREEMENTS   = {c['disagreements']}")
    print(f"  unscorable here = {c['unscorable_this_run']}")
    print(f"  sealed cells not driven here = {c['cells_in_sealed_campaign_not_driven_here']}")
    print(f"WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
