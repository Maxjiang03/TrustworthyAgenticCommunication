"""Part H step 7: execute the frozen campaign ONCE, and write `results/raw/`.

This is the entry point the design named and the repository did not have.
`run_campaign` is a library function with fourteen parameters; until ADR 0045
its only callers were tests and one `tools/` script, both pilot-only, and
nothing anywhere wrote a campaign result to disk.

**One campaign is three `run_campaign` calls across two AS processes, and that
is a property of the sealed corpus rather than a choice made here** (ADR 0045):
`check_configuration_families` refuses an F4/F5 run with `monitor_attached=None`
so those families need both configurations; the corpus declares two distinct
task grants, so the F1/F2/F3 chain and the F4/F5 chain need separately
provisioned AS processes; and `B2ExchangeTaskArm.provision` refuses a token
whose authority is not the run's `U_task`, so one document cannot serve both.
The three passes compose into ONE record with one list of cells, so the "once"
is auditable as a single artifact rather than three that could be selectively
reported.

**Write-once, and refusing rather than overwriting.** The driver will not start
if its output file exists. Results are write-once (§J.4 item 14) because a
second run must be a visible decision; an abort discards the partial file by
name (Part H's abort rule) rather than leaving it to be mistaken for a result.

Run it as either:

    make reproduce
    uv run python -m src.harness.campaign_driver [--run-mode confirmatory]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.harness import campaign as C
from src.harness import key_material
from src.harness.as_process import ASProcess, golden_thread_as_document
from src.harness.authorizer import frozen_config
from src.harness.runner import GoldenThreadRunner
from src.harness.verifier import registry as reg
from src.sut.baselines.b0 import B0Arm
from src.sut.baselines.b1 import B1Arm
from src.sut.baselines.b2_broad import B2BroadNoExchangeArm, B2ExchangeBroadArm
from src.sut.baselines.b2_dpop import B2ExchangeTaskDPoPArm
from src.sut.baselines.b2_exchange_task import B2ExchangeTaskArm
from src.sut.baselines.b3 import B3Arm
from src.sut.baselines.b3_plus import B3PlusArm
from src.sut.baselines.b_cap import BCapArm

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_RAW = REPO_ROOT / "results" / "raw"

CORPORA = {
    "pilot": REPO_ROOT / "fixtures" / "pilot" / "golden_thread",
    "confirmatory": REPO_ROOT / "fixtures" / "confirmatory",
}

# ADR 0045 constant 1. The AS mints Phase-1 tokens once at start-up and
# defaults them to 300 s; a pass is 13 scenarios x 9 arms x 2 monitor
# configurations, and a cell judged after `exp` is recorded `unscorable`. An
# hour is ~50x the observed pass and still covers ADR 0038's 2682 s excursion.
# It is not unbounded: `clock_refusal` must stay reachable and testable.
CAMPAIGN_TOKEN_LIFETIME_SECONDS = 3600

# ADR 0045 constant 2. `F3 audience-mismatch` needs a token that is genuinely
# valid and simply minted for ANOTHER resource server (§D.2's captured
# credential). Registered as a second RS so the token is well-formed for the
# audience it names -- a malformed one would be refused by a different
# conjunct and the cell would measure `invalid_credential` twice.
WRONG_AUDIENCE = "rs-other.aasc.local"
WRONG_AUDIENCE_GRANT = "wrong-audience"

RAR_TYPE = "urn:aasc:mcp-invoke"


class CampaignDriverError(Exception):
    """The campaign refused to start, or refused to overwrite a result."""


def _scenarios(corpus_root: Path) -> tuple[str, ...]:
    return tuple(sorted(path.stem for path in (corpus_root / "sealed").glob("*.json")))


def _split_by_chain(runner: GoldenThreadRunner, scenarios: tuple[str, ...]) -> dict[str, list[str]]:
    """Group scenarios by the task grant their chain needs.

    Derived from the corpus by asking the runner for each scenario's grant,
    never from a hardcoded family list: a corpus that grew a third chain would
    produce a third group here instead of silently joining one of these two.
    """
    groups: dict[str, list[str]] = {}
    for scenario_id in scenarios:
        grant = runner.task_grant(scenario_id)
        key = json.dumps(grant, sort_keys=True)
        groups.setdefault(key, []).append(scenario_id)
    return groups


def _as_document(
    runner: GoldenThreadRunner, task_grant_scenario: str, *, corpus: dict[str, Any]
) -> dict[str, Any]:
    registry_document = reg.load_document()
    return golden_thread_as_document(
        corpus=corpus,
        registry_document=registry_document,
        resolved_keys=key_material.resolve_public(runner.seed),
        identity_jwks=key_material.identity_jwks(runner.seed, registry_document["principals"]),
        omega_elements=frozen_config.load_document()["omega"]["elements"],
        task_grant=runner.task_grant(task_grant_scenario),
        default_lifetime_seconds=CAMPAIGN_TOKEN_LIFETIME_SECONDS,
        wrong_audience=WRONG_AUDIENCE,
        wrong_audience_grant_name=WRONG_AUDIENCE_GRANT,
    )


def _factories(
    runner: GoldenThreadRunner,
    running_as: ASProcess,
    document: dict[str, Any],
    *,
    monitor_attached: bool | None,
    scenario_id: str,
) -> dict[str, Any]:
    """Every arm under ONE configuration, so the configuration is a property
    of the run rather than of whichever arm happened to carry it."""
    common: dict[str, Any] = {
        "as_public_jwk": running_as.public_jwk,
        "as_port": running_as.port,
        "as_tls_cert_pem": running_as.tls_cert_pem,
        "scenario_id": scenario_id,
    }
    b3_extra: dict[str, Any] = {}
    if monitor_attached is not None:
        common["monitor_attached"] = monitor_attached
        b3_extra["monitor_attached"] = monitor_attached
    b3_setup = runner.b3_setup(
        access_token=running_as.phase1_tokens["agent-specialist"],
        as_public_jwk=running_as.public_jwk,
        **b3_extra,
    )
    broad = runner.b2_setup(
        access_token=running_as.phase1_tokens["agent-supervisor:broad"],
        ladder_grant="broad",
        **common,
    )
    task = runner.b2_setup(
        access_token=running_as.phase1_tokens["agent-supervisor"],
        ladder_grant="task",
        **common,
    )
    dpop = runner.b2_dpop_setup(
        access_token=running_as.phase1_tokens["agent-supervisor"],
        as_token_endpoint=document["token_endpoint"],
        **common,
    )
    return {
        "B0": (B0Arm, {}),
        "B1": (B1Arm, runner.b1_setup()),
        "B2-broad-noexchange": (B2BroadNoExchangeArm, broad),
        "B2-exchange-broad": (B2ExchangeBroadArm, broad),
        "B2-exchange-task": (B2ExchangeTaskArm, task),
        "B2-exchange-task-DPoP": (B2ExchangeTaskDPoPArm, dpop),
        "B-cap": (BCapArm, b3_setup),
        "B3": (B3Arm, b3_setup),
        "B3+": (B3PlusArm, b3_setup),
    }


def output_path(run_mode: str) -> Path:
    return RESULTS_RAW / f"campaign-{run_mode}.json"


def refuse_if_written(path: Path) -> None:
    """Write-once (§J.4 item 14). A second run is a DECISION, never a default.

    Part H's "once" governs the deterministic security verdicts: each sealed
    scenario is evaluated once for its verdict, and no scenario is re-run to
    obtain a different one. Silently overwriting would make that unauditable
    from the artifact alone.
    """
    if path.exists():
        raise CampaignDriverError(
            f"{path} already exists. Part H step 7 executes the frozen campaign ONCE, and "
            "results/raw/ is write-once: this driver will not overwrite a result. If the "
            "previous run was an ABORT (crash or resource exhaustion), Part H requires the "
            "partial run be discarded in full -- delete the file deliberately, record the "
            "abort in DEVIATIONS.md, and re-run the SAME sealed artifacts."
        )


def run(
    *,
    run_mode: str = "confirmatory",
    ledger_backed: bool = True,
    sut_mode: str = "in-process",
    out: Path | None = None,
) -> dict[str, Any]:
    """The whole campaign: every scenario, every arm, both configurations."""
    corpus_root = CORPORA[run_mode]
    destination = out if out is not None else output_path(run_mode)
    refuse_if_written(destination)

    runner = GoldenThreadRunner(
        corpus_dir=corpus_root,
        ledger_dir=(REPO_ROOT / "results" / "_ledger" / run_mode) if ledger_backed else None,
        run_mode=run_mode,
    )
    if ledger_backed:
        runner._ledger_dir.mkdir(parents=True, exist_ok=True)  # noqa: SLF001 - own attribute

    corpus_document = json.loads((corpus_root / "corpus.json").read_text(encoding="utf-8"))
    corpus = {"issuer": corpus_document["issuer"], "audience": corpus_document["audience"]}

    scenarios = _scenarios(corpus_root)
    groups = _split_by_chain(runner, scenarios)

    passes: list[dict[str, Any]] = []
    for members in groups.values():
        configuration_family = any(
            C._family_of(  # noqa: SLF001 - the campaign's own classifier, not a second copy
                str(C._sealed_document(corpus_root, scenario_id).get("attack_subcase", ""))
            )
            in C.matrix_grouping.CONFIGURATION_FAMILIES
            for scenario_id in members
        )
        # §E.4's `A†` is "admitted ABSENT the shared monitor", so a family whose
        # verdict depends on the monitor is run under BOTH configurations and
        # neither pass is the whole answer. Everything else runs once, with the
        # configuration recorded as `None` rather than invented.
        configurations: tuple[bool | None, ...] = (False, True) if configuration_family else (None,)
        document = _as_document(runner, members[0], corpus=corpus)
        with ASProcess(document, runner.seed) as running_as:
            wrong_audience_token = running_as.phase1_tokens.get(
                f"agent-supervisor:{WRONG_AUDIENCE_GRANT}"
            )
            if wrong_audience_token is None:
                raise CampaignDriverError(
                    "the AS minted no wrong-audience token; F3 audience-mismatch would abort "
                    "the run mid-matrix (ADR 0045)"
                )
            for configured in configurations:
                result = C.run_campaign(
                    runner=runner,
                    factories=_factories(
                        runner,
                        running_as,
                        document,
                        monitor_attached=configured,
                        scenario_id=members[0],
                    ),
                    scenarios=tuple(members),
                    seed=runner.seed,
                    as_issuer=corpus["issuer"],
                    as_public_jwk=running_as.public_jwk,
                    resource_server=corpus["audience"],
                    rar_type=RAR_TYPE,
                    monitor_attached=configured,
                    sut_mode=sut_mode,
                    run_mode=run_mode,
                    ledger_backed=ledger_backed,
                    corpus_root=corpus_root,
                    wrong_audience_token=wrong_audience_token,
                )
                passes.append(
                    dict(result.as_dict(), monitor_attached=configured, scenarios=list(members))
                )

    record = {
        "part_h_step": 7,
        "run_mode": run_mode,
        "corpus_root": str(corpus_root.relative_to(REPO_ROOT)).replace("\\", "/"),
        "scenarios": list(scenarios),
        "token_lifetime_seconds": CAMPAIGN_TOKEN_LIFETIME_SECONDS,
        "wrong_audience": WRONG_AUDIENCE,
        "passes": passes,
        "cells": [cell for one_pass in passes for cell in one_pass["cells"]],
        "unscorable": [row for one_pass in passes for row in one_pass["unscorable"]],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    refuse_if_written(destination)  # re-checked: the pass took time, and time is when races happen
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description="Part H step 7 -- execute the frozen campaign once"
    )
    parser.add_argument("--run-mode", choices=sorted(CORPORA), default="confirmatory")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--no-ledger",
        action="store_true",
        help="run without the effect ledger; `realized_harm` is then None for every cell",
    )
    args = parser.parse_args(argv)
    try:
        record = run(run_mode=args.run_mode, ledger_backed=not args.no_ledger, out=args.out)
    except (CampaignDriverError, C.CampaignError) as exc:
        print(f"campaign refused to run: {exc}", file=sys.stderr)
        return 1
    print(
        f"{args.run_mode}: {len(record['cells'])} cells, "
        f"{len(record['unscorable'])} unscorable, {len(record['passes'])} passes"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(main())
