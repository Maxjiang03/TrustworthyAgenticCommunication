"""Drive the SEALED arms over a REAL loopback MCP transport (DEVIATIONS D-017).

POST-SEAL VALIDATION APPARATUS. Lives outside `src/` and `analysis/`; imports
the sealed arms, corpus, AS and setup helpers READ-ONLY and unmodified; writes
only to `results/validation/`. It re-runs no campaign and amends no sealed
number: the confirmatory result at `17e11c9` stands untouched.

THE ONE VARIABLE
----------------
The sealed campaign connects a real `ClientSession` to a real `FastMCP` over
IN-MEMORY object streams inside one process. This harness connects the same
client API to the same server builder over a REAL STDIO TRANSPORT to a CHILD
PROCESS: genuine framing, genuine bytes on a pipe, a genuine OS process
boundary. Corpus, arms, AS, frozen policy and the decision function are the
sealed ones. Nothing else moves.

WHERE THE MONITOR GOES, AND WHY THAT IS THE WORK
------------------------------------------------
In the sealed apparatus the reference monitor is installed by wrapping the
harness server's own `Tool.fn` (`src/harness/mediation/boundary.py:123`). A
server in another process has no `Tool.fn` this harness can reach, so
`arm.decide` runs CLIENT-SIDE, immediately before `session.call_tool`, and a
refusal means the call is never issued -- the tool cannot run, which is the
guarantee the server-side boundary gives, obtained at the other end of the
pipe. The DECISION stays the sealed arm's; only the interposition point moves.
D-017 states this up front as the single substantive difference.

SCOPE, and why it is narrower than D-017 first committed
--------------------------------------------------------
D-017 clause 1 named all 13 sealed scenarios. Delivering that faithfully needs
this harness to reproduce two more pieces of sealed orchestration: the
credential-fault injection of `src/harness/credential_faults.py`, applied at an
exact point inside the presentation span, and the ADR 0030 artifact minting
that F4/F5 depend on. Reproducing either outside the sealed runner risks a
subtly infidel harness -- and a subtly infidel harness that reports AGREEMENT
would be worth less than no validation at all, because it would look like
evidence. So this run covers the scenarios that need NEITHER, selected by a
structural criterion fixed before running: `credential_fault` absent from the
sealed document, `intended_labels` empty, `requires_approval` false. On the
confirmatory corpus that is `cf-benign` and `cf-f1-terminal`, nine arms each.
The narrowing is reported with the result, not folded into it.

WHAT IS COMPARED
----------------
Per cell: whether the boundary admitted or refused, against the sealed
campaign's `observed_forwarded`. Nothing else. No latency is measured or
reported -- ADR 0034 excludes a loopback round trip from the measured segment
by name, and reporting one would present an apparatus difference as a
mechanism difference.
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from mcp import ClientSession  # noqa: E402
from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: E402
from src.sut.identity import registry as reg  # noqa: E402

from src.harness import key_material  # noqa: E402
from src.harness.as_process import ASProcess, golden_thread_as_document  # noqa: E402
from src.harness.campaign_driver import (  # noqa: E402
    CAMPAIGN_TOKEN_LIFETIME_SECONDS,
    WRONG_AUDIENCE,
    WRONG_AUDIENCE_GRANT,
    _factories,
)
from src.harness.runner import GoldenThreadRunner  # noqa: E402
from src.sut.agents.specialist import Specialist  # noqa: E402
from src.sut.agents.supervisor import Supervisor  # noqa: E402
from src.sut.authz import frozen_config  # noqa: E402
from src.sut.protocol.a2a import InProcessDelegationTransport  # noqa: E402

CORPUS_DIR = REPO / "fixtures" / "confirmatory"
CAMPAIGN = REPO / "results" / "raw" / "campaign-confirmatory.json"
OUT_DIR = REPO / "results" / "validation"
SERVER_CHILD = REPO / "validation" / "real_transport" / "mcp_server_child.py"
VENV_PYTHON = REPO / ".venv" / "Scripts" / "python.exe"

ARM_ORDER = (
    "B0",
    "B1",
    "B2-broad-noexchange",
    "B2-exchange-broad",
    "B2-exchange-task",
    "B2-exchange-task-DPoP",
    "B-cap",
    "B3",
    "B3+",
)


def out_path(run: int) -> Path:
    """Run 1 keeps the plain name; a re-run takes a distinct one (D-017 clause 6)."""
    return OUT_DIR / ("real-transport.json" if run == 1 else f"real-transport-run{run}.json")


def eligible_scenarios(corpus_dir: Path):
    """The scenarios this harness can drive faithfully, by structural criterion.

    Fixed before running and applied to the SEALED documents: no credential
    fault to inject, no sensitive label and no approval requirement, therefore
    no ADR 0030 artifact to mint. Anything else needs sealed orchestration this
    harness would have to reproduce, and a reproduction it cannot vouch for is
    worse than an admitted gap.
    """
    eligible, excluded = [], []
    for path in sorted((corpus_dir / "sealed").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        reasons = []
        if str(doc.get("credential_fault", "none")) != "none":
            reasons.append(f"credential_fault={doc['credential_fault']}")
        if doc.get("intended_labels"):
            reasons.append(f"intended_labels={doc['intended_labels']}")
        if doc.get("requires_approval"):
            reasons.append("requires_approval")
        (excluded if reasons else eligible).append((doc["scenario_id"], reasons))
    return eligible, excluded


async def drive_one(session, arm, visible, run_epoch, correlation_id):
    """One cell over the real transport. Returns (admitted, reason, tool_error).

    The sealed `Supervisor` and `Specialist` do the A2A hop exactly as the
    campaign does -- `arm.delegate`, then `arm.present` -- and the tool caller
    they are handed is where this harness differs: it runs `arm.decide` and,
    only on an admission, crosses the real pipe.
    """
    outcome = {"admitted": None, "reason": "", "tool_error": None}
    loop = asyncio.get_running_loop()

    def tool_caller(tool, arguments):
        # THE RELOCATED MONITOR. Server-side interposition is unavailable
        # against a child process, so the sealed arm's own decision runs here,
        # before anything crosses the wire. A refusal never reaches the pipe.
        admitted, reason = arm.decide(tool, dict(arguments))
        outcome["admitted"] = bool(admitted)
        outcome["reason"] = str(reason)
        if not admitted:
            return {"refused": reason}
        future = asyncio.run_coroutine_threadsafe(session.call_tool(tool, dict(arguments)), loop)
        result = future.result(timeout=30)
        outcome["tool_error"] = bool(result.isError)
        return result

    transport = InProcessDelegationTransport()
    specialist = Specialist(
        arm=arm,
        tool_caller=tool_caller,
        method=visible["method"],
        audience=visible["audience"],
        clock=lambda: run_epoch,
        invocation_id_provider=lambda: correlation_id,
        artifacts={},
    )
    transport.register(visible["specialist"], specialist.receive)
    supervisor = Supervisor(arm=arm, transport=transport, clock=lambda: run_epoch)
    await asyncio.to_thread(supervisor.run, visible)
    return outcome


async def run_all(session, runner, running_as, document, corpus, eligible, sealed_forwarded):
    cells, disagreements = [], []
    for scenario_id, _ in eligible:
        visible = json.loads(
            (CORPUS_DIR / "sut_visible" / f"{scenario_id}.json").read_text(encoding="utf-8")
        )
        factories = _factories(
            runner, running_as, document, monitor_attached=None, scenario_id=scenario_id
        )
        for arm_name in ARM_ORDER:
            cls, setup = factories[arm_name]
            arm = cls(**setup) if setup else cls()
            run_epoch = int(time.time())
            cid = f"validation-{scenario_id}-{arm_name}"
            try:
                outcome = await drive_one(session, arm, visible, run_epoch, cid)
                error = ""
            except Exception as exc:  # reported, never swallowed
                outcome = {"admitted": None, "reason": "", "tool_error": None}
                error = f"{type(exc).__name__}: {exc}"
            key = (scenario_id, arm_name)
            sealed = sealed_forwarded.get(key)
            row = {
                "scenario_id": scenario_id,
                "arm": arm_name,
                "real_transport_admitted": outcome["admitted"],
                "sealed_observed_forwarded": sealed,
                "reason_code_FOR_DIAGNOSIS_ONLY": outcome["reason"],
                "harness_error": error,
            }
            cells.append(row)
            print(
                f"CELL {scenario_id:20s} {arm_name:22s} real={outcome['admitted']} "
                f"sealed={sealed} {('ERROR ' + error) if error else ''}"
            )
            if error:
                continue
            if sealed is not None and bool(outcome["admitted"]) != bool(sealed):
                disagreements.append(row)
    return cells, disagreements


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    run, reason = 1, ""
    for i, tok in enumerate(args):
        if tok == "--run":
            run = int(args[i + 1])
        elif tok == "--reason":
            reason = args[i + 1]
    if run != 1 and not reason:
        print("REFUSED: a re-run requires --reason (D-017 clause 6).")
        return 1
    out = out_path(run)
    if out.exists():
        print(f"REFUSED: {out} already exists. A second run is a decision (D-017 clause 6).")
        return 1

    eligible, excluded = eligible_scenarios(CORPUS_DIR)
    print(f"INPUT run_index [given] = {run}")
    print(f"INPUT run_reason [given] = {reason or '(first run)'}")
    print("INPUT transport [fixed by D-017] = real stdio to a child process")
    print("INPUT server [sealed builder] = src/sut/protocol/mcp_tools.build_server")
    print(f"INPUT corpus [sealed] = {CORPUS_DIR.relative_to(REPO)}")
    for sid, _ in eligible:
        print(f"ELIGIBLE {sid}")
    for sid, reasons in excluded:
        print(f"EXCLUDED {sid}: {', '.join(reasons)}")

    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    sealed_forwarded = {}
    for cell in campaign["cells"]:
        # The eligible scenarios run under one configuration only, so a cell is
        # keyed by (scenario, arm) without ambiguity; assert rather than assume.
        key = (cell["scenario_id"], cell["arm"])
        if key in sealed_forwarded and sealed_forwarded[key] != bool(cell["observed_forwarded"]):
            raise SystemExit(f"{key} appears twice in the campaign with different outcomes")
        sealed_forwarded[key] = bool(cell["observed_forwarded"])

    runner = GoldenThreadRunner(corpus_dir=CORPUS_DIR, run_mode="confirmatory")
    corpus = json.loads((CORPUS_DIR / "corpus.json").read_text(encoding="utf-8"))
    registry_document = reg.load_document()
    document = golden_thread_as_document(
        corpus=corpus,
        registry_document=registry_document,
        resolved_keys=key_material.resolve_public(runner.seed),
        identity_jwks=key_material.identity_jwks(runner.seed, registry_document["principals"]),
        omega_elements=frozen_config.load_document()["omega"]["elements"],
        task_grant=runner.task_grant(eligible[0][0]),
        default_lifetime_seconds=CAMPAIGN_TOKEN_LIFETIME_SECONDS,
        wrong_audience=WRONG_AUDIENCE,
        wrong_audience_grant_name=WRONG_AUDIENCE_GRANT,
    )

    effects = Path(tempfile.mkdtemp()) / "effects.jsonl"
    env = dict(os.environ)
    env["AASC_VALIDATION_EFFECTS"] = str(effects)
    env["PYTHONIOENCODING"] = "utf-8"
    params = StdioServerParameters(
        command=str(VENV_PYTHON),
        args=["-X", "utf8", str(SERVER_CHILD)],
        env=env,
        cwd=str(REPO),
    )

    async def go():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                print(f"TRANSPORT tools_over_real_stdio = {sorted(t.name for t in tools.tools)}")
                with ASProcess(document, runner.seed) as running_as:
                    return await run_all(
                        session, runner, running_as, document, corpus, eligible, sealed_forwarded
                    )

    cells, disagreements = asyncio.run(go())
    errors = [c for c in cells if c["harness_error"]]
    compared = [
        c for c in cells if not c["harness_error"] and c["sealed_observed_forwarded"] is not None
    ]
    agreements = len(compared) - len(disagreements)
    print()
    print(f"CELLS driven      = {len(cells)}")
    print(f"  harness errors  = {len(errors)}")
    print(f"  compared        = {len(compared)}")
    print(f"  agreements      = {agreements}")
    print(f"  DISAGREEMENTS   = {len(disagreements)}")
    for d in disagreements:
        print(
            f"DISAGREEMENT {d['scenario_id']} {d['arm']}: "
            f"real={d['real_transport_admitted']} sealed={d['sealed_observed_forwarded']}"
        )

    payload = {
        "_what": (
            "The SEALED arms driven over a REAL loopback stdio MCP transport against the sealed "
            "five-tool server in a CHILD PROCESS, compared per cell against the sealed campaign's "
            "observed_forwarded. Governed by DEVIATIONS D-017. Post-seal validation: it re-runs no "
            "campaign, amends no sealed number, and does not supersede the confirmatory result."
        ),
        "the_one_variable": (
            "the transport. Corpus, arms, AS, frozen policy and the decision function are the "
            "sealed ones; the server is the sealed builder. The interposition point moves: "
            "arm.decide runs client-side before call_tool, because a child-process server has no "
            "Tool.fn this harness can wrap."
        ),
        "no_latency_claim": (
            "ADR 0034 excludes a loopback round trip from the measured segment by name. Nothing "
            "here is timed and no latency is reported."
        ),
        "scope_narrowing": {
            "committed_in_d017": "all 13 sealed scenarios, nine arms",
            "delivered": [sid for sid, _ in eligible],
            "criterion_fixed_before_running": (
                "no credential_fault to inject, no intended_labels, no requires_approval -- so no "
                "sealed orchestration this harness would have to reproduce"
            ),
            "excluded": [{"scenario_id": s, "reasons": r} for s, r in excluded],
            "why": (
                "reproducing credential-fault injection and ADR 0030 artifact minting outside the "
                "sealed runner risks a subtly infidel harness, and a subtly infidel harness that "
                "reported AGREEMENT would be worth less than no validation at all"
            ),
        },
        "run": {"index": run, "reason": reason or "(first run)"},
        "counts": {
            "cells_driven": len(cells),
            "harness_errors": len(errors),
            "compared": len(compared),
            "agreements": agreements,
            "disagreements": len(disagreements),
        },
        "cells": cells,
        "disagreements": disagreements,
        "residuals_that_travel_with_any_agreement": (
            "the A2A hop is still an in-process port; the tools are still sandboxed intent "
            "recorders; the server is still the harness's own five-tool stub, not a third-party "
            "implementation; the machine is still one machine. This moves exactly one variable, "
            "which is what makes a difference attributable and equally what bounds the claim."
        ),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
