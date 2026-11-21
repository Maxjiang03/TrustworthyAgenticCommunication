"""Run the reviewer experiments: python -m validation.revision.run --out PATH."""

import argparse
import asyncio
import copy
import hashlib
import json
import platform
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from src.harness import frozen_parameters
from src.harness.as_process import ASProcess
from src.harness.campaign_driver import _as_document, _factories
from src.harness.mediation.boundary import install_boundary
from src.harness.policy.label_artifacts import mint_for_scenario
from src.harness.runner import GoldenThreadRunner
from src.sut.authz.jti_cache import JtiCache
from src.sut.authz.label_context import label_assertions_digest
from src.sut.baselines.base import HopContext, InvocationContext
from src.sut.capability import signer
from validation.revision.controls import BoundOAuthArm, StatusGate, TaskStatus
from validation.revision.tools import RESOURCES, Store, build_server

REPO = Path(__file__).resolve().parents[2]
ARMS = ("B2-exchange-task", "B2-exchange-task-DPoP", "OAuth-DPoP-call", "B3", "B3+")


@contextmanager
def lab(scenario="gt-benign", monitor=True):
    runner = GoldenThreadRunner()
    visible = runner.visible(scenario)
    document = _as_document(runner, scenario, corpus=runner._corpus)
    with ASProcess(document, runner.seed) as process:
        factories = _factories(
            runner, process, document, monitor_attached=monitor, scenario_id=scenario
        )
        factories["OAuth-DPoP-call"] = (BoundOAuthArm, factories["B2-exchange-task-DPoP"][1])
        factories["B3-worker"] = (
            factories["B3"][0],
            runner.b3_setup(
                access_token=process.phase1_tokens["agent-worker"],
                as_public_jwk=process.public_jwk,
                actor_id="agent-worker",
                monitor_attached=monitor,
            ),
        )
        yield runner, visible, factories


def prepare(factory, visible, *, suffix="case", artifacts=None):
    make, setup = factory
    arm = make()
    arm.provision(setup)
    now = int(time.time())
    hop = HopContext(
        task_id=visible["task_id"],
        audience=visible["audience"],
        from_agent=visible["supervisor"],
        to_agent=visible["specialist"],
        authority_elements=tuple(map(tuple, visible["authority_elements"])),
        attenuation_elements=tuple(map(tuple, visible["attenuation_elements"])),
        now_epoch=now,
        expiry_epoch=now + visible["validity_seconds"],
    )
    credentials = arm.delegate(hop)
    request = visible["delegation_intent"]
    invocation = InvocationContext(
        tool=request["tool"],
        arguments=request["arguments"],
        method=visible["method"],
        task_id=visible["task_id"],
        audience=visible["audience"],
        invocation_id=suffix,
        now_epoch=now,
        **(artifacts or {}),
    )
    arm.present(credentials, invocation)
    return arm, credentials, invocation


def close(arm):
    if hasattr(arm, "close"):
        arm.close()


def invoke(arm, store, tool, arguments):
    """Observe storage and MCP result independently of the arm's verdict."""
    server, events = build_server(store), []
    install_boundary(
        server, decide=arm.decide, correlation_provider=lambda: "revision", emit=events.append
    )
    before = store.snapshot()
    started = time.perf_counter_ns()
    try:
        content, _ = asyncio.run(server.call_tool(tool, dict(arguments)))
        error = None
        result = "\n".join(item.text for item in content if item.type == "text")
    except Exception as exc:
        if not events:
            raise
        result, error = "", type(exc).__name__
    elapsed = (time.perf_counter_ns() - started) / 1e6
    after = store.snapshot()
    effects = []
    for resource in RESOURCES:
        if before["resources"][resource] != after["resources"][resource]:
            action = "notes.delete" if after["resources"][resource] is None else "notes.write"
            effects.append([action, resource])
    if before["outbox"] != after["outbox"]:
        effects.append(["mail.send", "mail/outbox"])
    if error is None and tool in ("notes.read", "calendar.read"):
        effects.append([tool, arguments["resource"]])
    admitted = events[-1].admitted
    checks = {
        "read_content_matches": error is not None
        or tool not in ("notes.read", "calendar.read")
        or result == (before["resources"][arguments["resource"]] or ""),
        "refusal_has_no_effect": admitted or (before == after and not effects),
        "admitted_tool_completed": not admitted or error is None,
    }
    return dict(
        admitted=admitted,
        reason=events[-1].reason_code,
        effects=effects,
        before=before,
        after=after,
        result=result,
        error=error,
        elapsed_ms=elapsed,
        checks=checks,
    )


def write_record(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def record_case(rows, row, journal):
    rows.append(row)
    if journal is not None:
        with journal.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def policy_cases(journal=None):
    rows = []
    for scenario in ("gt-benign", "gt-f4-declassified", "gt-f5-approved"):
        for monitor in (False, True):
            with lab(scenario, monitor) as (runner, base, factories):
                modes = (
                    ("valid",)
                    if scenario == "gt-benign"
                    else ("valid", "missing", "invalid", "expired")
                )
                for index in range(12):
                    for mode in modes:
                        visible = copy.deepcopy(base)
                        visible["task_id"] += f"-revision-{index}"
                        args = visible["delegation_intent"]["arguments"]
                        if "subject" in args:
                            args["subject"] += f" {index}"
                        elif "content" in args:
                            args["content"] += f" {index}"
                        for name in ARMS:
                            setup = factories[name][1]
                            artifacts = mint_for_scenario(
                                runner.seed,
                                visible,
                                now=int(time.time()) - (301 if mode == "expired" else 0),
                                resource_owner=setup["resource_owner"],
                                oauth_actor=setup["oauth_actor"],
                                policy_version=frozen_parameters.expected_h_policy(),
                            )
                            if mode == "missing":
                                artifacts = {}
                            elif mode == "invalid":
                                artifacts["approval_artifact"] = b"invalid"
                            arm, _, inv = prepare(
                                factories[name],
                                visible,
                                suffix=f"{scenario}-{index}-{mode}",
                                artifacts=artifacts,
                            )
                            admitted, reason = arm.decide(inv.tool, inv.arguments)
                            # Full-policy admissibility is fixed before observing the decision.
                            expected = mode == "valid"
                            record_case(
                                rows,
                                dict(
                                    scenario=scenario,
                                    variant=index,
                                    evidence=mode,
                                    monitor=monitor,
                                    arm=name,
                                    admitted=admitted,
                                    policy_admissible=expected,
                                    reason=reason,
                                ),
                                journal,
                            )
                            if monitor:
                                assert admitted == expected, (name, scenario, mode, reason)
                            elif scenario == "gt-benign":
                                assert admitted
                            close(arm)
    return rows


def actual_effect_cases(journal=None):
    rows = []
    with lab() as (_, base, factories):
        for backend in ("files", "sqlite"):
            for index in range(20):
                for attack in (
                    "benign",
                    "argument-substitution",
                    "outside-terminal",
                    "outside-task",
                    "in-grant-malicious",
                    "path-alias",
                    "sql-payload",
                ):
                    visible = copy.deepcopy(base)
                    request = visible["delegation_intent"]
                    request["arguments"] = {
                        "resource": "notes/project",
                        "content": f"summary-{index}",
                    }
                    sent = copy.deepcopy(request)
                    if attack in ("argument-substitution", "in-grant-malicious"):
                        sent["arguments"]["content"] = f"CORRUPTED-{index}"
                    elif attack == "outside-terminal":
                        sent = {"tool": "calendar.read", "arguments": {"resource": "calendar/work"}}
                    elif attack == "outside-task":
                        sent = {"tool": "notes.read", "arguments": {"resource": "notes/meeting"}}
                    elif attack == "path-alias":
                        sent["arguments"]["resource"] = "notes/../meeting"
                    elif attack == "sql-payload":
                        sent["arguments"]["content"] = f"'); DROP TABLE notes; -- {index}\n中文"
                    if attack != "argument-substitution":
                        visible["delegation_intent"] = copy.deepcopy(sent)
                    for name in ARMS:
                        arm, _, _ = prepare(
                            factories[name], visible, suffix=f"effect-{index}-{attack}"
                        )
                        with tempfile.TemporaryDirectory() as directory:
                            store = Store(Path(directory), backend)
                            observed = invoke(arm, store, sent["tool"], sent["arguments"])
                            store.close()
                        grant = set(map(tuple, visible["attenuation_elements"]))
                        outside = [e for e in observed["effects"] if tuple(e) not in grant]
                        record_case(
                            rows,
                            dict(
                                arm=name,
                                backend=backend,
                                variant=index,
                                attack=attack,
                                request=sent,
                                outside_grant=outside,
                                **observed,
                            ),
                            journal,
                        )
                        assert all(observed["checks"].values()), observed
                        assert not outside, (name, attack, outside)
                        if attack in ("outside-terminal", "outside-task", "path-alias"):
                            assert not observed["admitted"], (name, attack)
                        if attack == "argument-substitution":
                            assert observed["admitted"] == (name in ARMS[:2]), (name, observed)
                        if attack in ("benign", "in-grant-malicious", "sql-payload"):
                            assert observed["admitted"], (name, observed)
                            assert (
                                observed["after"]["resources"]["notes/project"]
                                == sent["arguments"]["content"]
                            )
                        close(arm)
    return rows


def replay_cases(journal=None):
    rows = []
    with lab() as (_, visible, factories):
        for name in ("B3", "B3+"):
            for offset in (0, 30, 60, 61):
                arm, _, inv = prepare(factories[name], visible)
                first = arm.decide(inv.tool, inv.arguments)
                arm._staged = replace(arm._staged, now_epoch=inv.now_epoch + offset)
                second = arm.decide(inv.tool, inv.arguments)
                record_case(
                    rows,
                    dict(arm=name, case="duplicate", offset=offset, first=first, second=second),
                    journal,
                )
                assert first[0]
                assert second[0] == (name == "B3" and offset <= 60)
            arm, credentials, inv = prepare(factories[name], visible)
            with ThreadPoolExecutor(max_workers=8) as pool:
                outcomes = list(pool.map(lambda _: arm.decide(inv.tool, inv.arguments), range(16)))
            record_case(rows, dict(arm=name, case="concurrent", outcomes=outcomes), journal)
            assert sum(item[0] for item in outcomes) == (16 if name == "B3" else 1)
            arm.present(credentials, replace(inv, invocation_id="new-business-attempt"))
            outcome = arm.decide(inv.tool, inv.arguments)
            record_case(
                rows, dict(arm=name, case="new-signed-identifier", outcome=outcome), journal
            )
            assert outcome[0]
            if name == "B3+":
                arm, _, inv = prepare(factories[name], visible)
                first = arm.decide(inv.tool, inv.arguments)
                arm.attach_replay_cache(JtiCache())
                outcome = arm.decide(inv.tool, inv.arguments)
                record_case(
                    rows,
                    dict(arm=name, case="cache-restart", first=first, outcome=outcome),
                    journal,
                )
                assert first[0] and outcome[0]  # volatile cache restart is measured
                arm, _, inv = prepare(factories[name], visible)
                arm.attach_replay_cache(JtiCache(capacity=1))
                first = arm.decide(inv.tool, inv.arguments)
                outcome = arm.decide(inv.tool, inv.arguments)
                record_case(
                    rows,
                    dict(arm=name, case="capacity-existing-id", first=first, outcome=outcome),
                    journal,
                )
                assert first[0] and not outcome[0]
                credentials = arm.delegate(
                    HopContext(
                        task_id=visible["task_id"],
                        audience=visible["audience"],
                        from_agent=visible["supervisor"],
                        to_agent=visible["specialist"],
                        authority_elements=tuple(map(tuple, visible["authority_elements"])),
                        attenuation_elements=tuple(map(tuple, visible["attenuation_elements"])),
                        now_epoch=inv.now_epoch,
                        expiry_epoch=inv.now_epoch + 3600,
                    )
                )
                arm.present(credentials, replace(inv, invocation_id="capacity-new"))
                outcome = arm.decide(inv.tool, inv.arguments)
                record_case(rows, dict(arm=name, case="capacity-new-id", outcome=outcome), journal)
                assert outcome == (False, "b3_replay_capacity")
    return rows


def revocation_cases(journal=None):
    rows = []
    with lab() as (_, visible, factories):
        for name in ("B2-exchange-task", "B3"):
            arm, _, inv = prepare(factories[name], visible)
            for delay in (0, 5, 30):
                revoked_at = inv.now_epoch + 1
                for elapsed in range(32):
                    now = revoked_at + elapsed
                    arm._staged = replace(arm._staged, now_epoch=now)
                    base = arm.decide(inv.tool, inv.arguments)
                    delivered = elapsed >= delay
                    snapshot = TaskStatus(
                        now if delivered else inv.now_epoch,
                        frozenset({inv.task_id}) if delivered else frozenset(),
                    )
                    status = snapshot.decide(inv.task_id, now)
                    gate = StatusGate(arm, inv.task_id, snapshot, now)
                    with tempfile.TemporaryDirectory() as directory:
                        store = Store(Path(directory))
                        observation = invoke(gate, store, inv.tool, inv.arguments)
                        store.close()
                    record_case(
                        rows,
                        dict(
                            arm=name,
                            delivery_delay=delay,
                            elapsed=elapsed,
                            base_admitted=base[0],
                            status_admitted=status[0],
                            effects=observation["effects"],
                            before=observation["before"],
                            after=observation["after"],
                            checks=observation["checks"],
                            reason=status[1],
                        ),
                        journal,
                    )
                    assert base[0]
                    assert status[0] == (not delivered)
                    assert observation["admitted"] == status[0]
                    assert all(observation["checks"].values())
            for age in (29, 30, 31, 60):
                now = inv.now_epoch + age
                arm._staged = replace(arm._staged, now_epoch=now)
                gate = StatusGate(arm, inv.task_id, TaskStatus(inv.now_epoch), now)
                with tempfile.TemporaryDirectory() as directory:
                    store = Store(Path(directory))
                    observation = invoke(gate, store, inv.tool, inv.arguments)
                    store.close()
                record_case(
                    rows,
                    dict(
                        arm=name,
                        case="snapshot-not-updated",
                        snapshot_age=age,
                        admitted=observation["admitted"],
                        reason=observation["reason"],
                        **{
                            key: observation[key]
                            for key in ("before", "after", "effects", "checks")
                        },
                    ),
                    journal,
                )
                assert observation["admitted"] == (age <= 30)
                assert all(observation["checks"].values())
                if age > 30:
                    assert observation["reason"] == "status_stale"
            close(arm)
    return rows


def delegation_cases(journal=None):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    rows = []
    with lab() as (_, visible, factories):
        for case in (
            "valid",
            "widen",
            "wrong-holder",
            "wrong-task",
            "wrong-audience",
            "prefix",
            "unregistered-key",
            "wrong-oauth-actor",
        ):
            arm, credentials, inv = prepare(
                factories["B3" if case == "wrong-oauth-actor" else "B3-worker"], visible
            )
            previous = signer.MintedHop(
                credentials["capability_hops"][-1], tuple(credentials["block_ids"][-1])
            )
            wanted = [("notes.write", "notes/project")]
            if case == "widen":
                wanted += [("calendar.read", "calendar/work")]
            terminal = arm._issuer.attenuate(previous, wanted)
            private = Ed25519PrivateKey.from_private_bytes(
                arm._setup["holder_privates"]["holder-specialist"]
            )
            worker = Ed25519PrivateKey.from_private_bytes(
                arm._setup["holder_privates"]["holder-worker"]
            )
            if case == "unregistered-key":
                worker = Ed25519PrivateKey.generate()
            hop = signer.issue_htc_hop(
                terminal,
                index=2,
                signer_private=private,
                signer_kid="kid-holder-specialist",
                next_holder_pubkey=signer.public_wire(worker),
                task_id="other-task" if case == "wrong-task" else inv.task_id,
                audience="https://other.test" if case == "wrong-audience" else inv.audience,
                iat=inv.now_epoch,
                nbf=inv.now_epoch,
                exp=inv.now_epoch + 200,
            )
            credentials["capability_hops"].append(terminal.token_bytes)
            credentials["block_ids"].append(list(terminal.block_ids))
            credentials["htc_chain"].append(hop)
            if case == "widen":
                inv = replace(inv, tool="calendar.read", arguments={"resource": "calendar/work"})
            arm.present(credentials, inv)
            assertion = signer.issue_inv(
                terminal,
                holder_private=worker,
                holder_kid="kid-holder-worker",
                raw_at=credentials["access_token"],
                raw_arguments=dict(inv.arguments),
                task_id=inv.task_id,
                audience=inv.audience,
                method=inv.method,
                tool=inv.tool,
                label_assertions_digest=label_assertions_digest([]),
                invocation_id=inv.invocation_id,
                iat=inv.now_epoch,
                nbf=inv.now_epoch,
                exp=inv.now_epoch + 200,
            )
            arm._staged = replace(arm._staged, invocation_assertion=assertion)
            if case == "wrong-holder":
                wrong = json.loads(assertion)
                wrong["signature"] = signer.b64u(private.sign(b"not-the-invocation"))
                arm._staged = replace(arm._staged, invocation_assertion=json.dumps(wrong).encode())
            elif case == "prefix":
                arm._staged = replace(
                    arm._staged,
                    capability_hops=arm._staged.capability_hops[:1]
                    + arm._staged.capability_hops[-1:],
                )
            tool, args = inv.tool, inv.arguments
            outcome = arm.decide(tool, args)
            record_case(rows, dict(case=case, outcome=outcome, hops=2), journal)
            assert outcome[0] == (case == "valid"), (case, outcome)
            if case == "unregistered-key":
                assert outcome[1] == "b3_htc_chain"
            elif case == "wrong-oauth-actor":
                assert outcome[1] == "b3_identity_plane_consistency"
    return rows


def run_suite(destination, suites=None):
    if not __debug__:
        raise RuntimeError("The experiment requires assertions enabled")
    destination.mkdir(parents=True, exist_ok=False)
    source = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((REPO / "validation/revision").glob("*.py"))
    }
    write_record(
        destination / "provenance.json",
        dict(
            source_commit=None,
            source_sha256=source,
            python=platform.python_version(),
            platform=platform.platform(),
            arm_order=ARMS,
        ),
    )
    counts = {}
    try:
        for name, run in (
            suites
            if suites is not None
            else (
                ("replay", replay_cases),
                ("delegation", delegation_cases),
                ("revocation", revocation_cases),
                ("policy", policy_cases),
                ("effects", actual_effect_cases),
            )
        ):
            started = time.time()
            rows = run(journal=destination / f"{name}.jsonl")
            write_record(
                destination / f"{name}.json", dict(evidence_class="supplementary", rows=rows)
            )
            counts[name] = len(rows)
            print(f"{name}: {len(rows)} checks, {time.time() - started:.1f}s", flush=True)
    except Exception as exc:
        write_record(
            destination / "status.json",
            dict(
                status="failed",
                completed_counts=counts,
                active_suite=name,
                error_type=type(exc).__name__,
                error=str(exc),
            ),
        )
        raise
    write_record(destination / "status.json", dict(status="complete", counts=counts))
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_suite(args.out)), flush=True)


if __name__ == "__main__":
    main()
