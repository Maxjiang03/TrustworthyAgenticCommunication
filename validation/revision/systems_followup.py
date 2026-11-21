"""Pinned AIP comparison and rerun of the existing observation fault gate."""

import argparse
import base64
import copy
import hashlib
import json
import runpy
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from validation.revision.run import close, invoke, lab, prepare, record_case, write_record
from validation.revision.tools import Store

REPO = Path(__file__).resolve().parents[2]
THIRD_PARTY = REPO / "validation/third_party"
AIP_SOURCE = THIRD_PARTY / "aip-69695e6f89cbdd34796d1c2b8fdf379f825d36bf/python"
sys.path[:0] = [str(AIP_SOURCE), str(THIRD_PARTY / "deps")]

from aip_core.crypto import KeyPair  # noqa: E402
from aip_mcp.middleware import verify_request  # noqa: E402
from aip_token.chained import ChainedToken  # noqa: E402
from aip_token.error import TokenError  # noqa: E402


def scope(tool, resource):
    return "tool:" + tool + "@" + resource


class AIPArm:
    def __init__(self, visible):
        key = KeyPair.generate()
        self.public_key = key.public_key_bytes()
        root = ChainedToken.create_authority(
            issuer="aip:key:clamp-evaluation",
            keypair=key,
            budget_cents=None,
            max_depth=2,
            ttl_seconds=600,
            scopes=[scope(*pair) for pair in visible["authority_elements"]],
        )
        child = root.delegate(
            delegator="supervisor",
            delegate="specialist",
            budget_cents=None,
            scopes=[scope(*pair) for pair in visible["attenuation_elements"]],
            context="release-note task",
        )
        self.headers = {"X-AIP-Token": child.to_base64()}

    def decide(self, tool, arguments):
        try:
            verify_request(self.headers, self.public_key, scope(tool, arguments["resource"]))
        except TokenError as exc:
            return False, exc.code
        return True, "aip_admitted"


def fault_gate(out):
    from src.harness.runner import GoldenThreadRunner

    source = REPO / "smoke/g12/spike.py"
    namespace = runpy.run_path(str(source))
    original = GoldenThreadRunner.run_scenario
    records = out / "fault-runs"
    records.mkdir()

    def capture(runner, *args, **kwargs):
        run = original(runner, *args, **kwargs)
        write_record(
            records / f"{run.correlation_id}.json",
            dict(
                scenario=run.scenario_id,
                fault=kwargs.get("fault", "none"),
                correlation_id=run.correlation_id,
                intent=run.intent.model_dump(mode="json"),
                observed=json.loads(
                    json.dumps(
                        run.observed.model_dump(),
                        default=lambda value: {
                            "__bytes_base64__": base64.b64encode(value).decode("ascii")
                        },
                    )
                ),
                mediation_events=[e.model_dump(mode="json") for e in run.mediation_events],
                ledger=run.ledger_entries(),
            ),
        )
        return run

    GoldenThreadRunner.run_scenario = capture
    try:
        with (out / "fault-console.log").open("w", encoding="utf-8") as stream:
            with redirect_stdout(stream):
                status = namespace["main"]()
    finally:
        GoldenThreadRunner.run_scenario = original
    rows = namespace["RESULTS"]
    write_record(
        out / "fault-gate.json",
        dict(
            exit_status=status,
            checks=[dict(name=n, mandatory=m, passed=p, evidence=e) for n, m, p, e in rows],
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        ),
    )
    if status:
        raise RuntimeError("Fault gate failed; observations retained")
    print("fault gate", len(rows), "checks", flush=True)


def aip_comparison(out):
    rows = []
    with lab() as (_, base, factories):
        for backend in ("files", "sqlite"):
            for index in range(10):
                for attack in ("benign", "argument-substitution", "outside-grant", "replay"):
                    visible = copy.deepcopy(base)
                    intended = dict(resource="notes/project", content=f"summary-{index}")
                    sent = copy.deepcopy(intended)
                    tool = "notes.write"
                    if attack == "argument-substitution":
                        sent["content"] = f"CORRUPTED-{index}"
                    elif attack == "outside-grant":
                        tool, sent = "notes.read", {"resource": "notes/meeting"}
                    visible["delegation_intent"] = dict(
                        tool=tool, arguments=sent if attack == "outside-grant" else intended
                    )
                    for name in ("AIP", "B3", "B3+"):
                        arm = (
                            AIPArm(visible)
                            if name == "AIP"
                            else prepare(
                                factories[name],
                                visible,
                                suffix=f"systems-{backend}-{index}-{attack}-{name}",
                            )[0]
                        )
                        try:
                            with tempfile.TemporaryDirectory() as directory:
                                store = Store(Path(directory), backend)
                                try:
                                    for repeat in range(2 if attack == "replay" else 1):
                                        observed = invoke(arm, store, tool, sent)
                                        row = dict(
                                            arm=name,
                                            backend=backend,
                                            variant=index,
                                            attack=attack,
                                            repeat=repeat,
                                            tool=tool,
                                            arguments=sent,
                                            **observed,
                                        )
                                        record_case(rows, row, out / "aip.jsonl")
                                        expected = (
                                            attack != "outside-grant"
                                            and not (
                                                name != "AIP" and attack == "argument-substitution"
                                            )
                                            and not (name == "B3+" and repeat == 1)
                                        )
                                        assert observed["admitted"] == expected, row
                                        assert all(observed["checks"].values()), row
                                finally:
                                    store.close()
                        finally:
                            close(arm)
    summary = {}
    for name in ("AIP", "B3", "B3+"):
        summary[name] = {}
        for attack in ("benign", "argument-substitution", "outside-grant", "replay"):
            cases = [r for r in rows if r["arm"] == name and r["attack"] == attack]
            summary[name][attack] = dict(
                calls=len(cases),
                admitted=sum(r["admitted"] for r in cases),
                changed_storage=sum(r["before"] != r["after"] for r in cases),
                duplicate_admitted=sum(r["admitted"] for r in cases if r["repeat"] == 1),
            )
    write_record(out / "aip-summary.json", summary)
    print("AIP comparison", len(rows), "calls", flush=True)


def adapter_faults(out):
    from src.harness.oracle import predicates as P

    class WrongResourceStore(Store):
        def write(self, resource, content):
            super().write("notes/meeting", content)

    rows = []
    with lab() as (_, base, factories):
        for backend in ("files", "sqlite"):
            for faulty in (False, True):
                visible = copy.deepcopy(base)
                arguments = dict(resource="notes/project", content="fault-probe")
                visible["delegation_intent"] = dict(tool="notes.write", arguments=arguments)
                arm = prepare(factories["B3"], visible, suffix=f"fault-{backend}-{faulty}")[0]
                try:
                    with tempfile.TemporaryDirectory() as directory:
                        store = (WrongResourceStore if faulty else Store)(Path(directory), backend)
                        try:
                            observed = invoke(arm, store, "notes.write", arguments)
                        finally:
                            store.close()
                    ledger = [
                        dict(effect_id=str(i), correlation_id="fault", action=a, resource=r)
                        for i, (a, r) in enumerate(observed["effects"])
                    ]
                    detected = P.realized_harm_F1(
                        {"C_sets": [visible["attenuation_elements"]]}, ledger, "fault"
                    )
                    record_case(
                        rows,
                        dict(backend=backend, faulty=faulty, detected=detected, **observed),
                        out / "adapter-faults.jsonl",
                    )
                    assert observed["admitted"] and detected == faulty
                finally:
                    close(arm)
    write_record(out / "adapter-faults.json", rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    provenance = json.loads((THIRD_PARTY / "aip-provenance.json").read_text())
    provenance["source_hashes"] = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            Path(__file__),
            REPO / "validation/revision/run.py",
            AIP_SOURCE / "aip_mcp/middleware.py",
            AIP_SOURCE / "aip_token/chained.py",
        ]
    }
    write_record(args.out / "provenance.json", provenance)
    fault_gate(args.out)
    aip_comparison(args.out)
    adapter_faults(args.out)
    write_record(args.out / "status.json", dict(status="complete"))


if __name__ == "__main__":
    main()
