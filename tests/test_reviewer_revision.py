"""Minimal regression checks for the new profiles and actual-effect observation."""

import copy
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from src.harness.policy.label_artifacts import issue_label_assertion
from validation.revision.controls import BoundOAuthArm, StatusGate, TaskStatus
from validation.revision.model import score_episode, target_call
from validation.revision.run import (
    close,
    delegation_cases,
    invoke,
    lab,
    policy_cases,
    prepare,
    replay_cases,
    revocation_cases,
    run_suite,
)
from validation.revision.tools import Store


def test_reviewer_security_paths():
    assert len(replay_cases()) == 15
    assert len(delegation_cases()) == 8
    with lab() as (_, visible, factories):
        for name in ("B2-exchange-task", "OAuth-DPoP-call", "B3"):
            arm, credentials, inv = prepare(factories[name], copy.deepcopy(visible))
            with tempfile.TemporaryDirectory() as directory:
                store = Store(Path(directory), "sqlite", initial={"notes/project": "a\nb"})
                read = dict(resource="notes/project")
                arm.present(credentials, replace(inv, tool="notes.read", arguments=read))
                assert invoke(arm, store, "notes.read", read)["result"] == "a\nb"
                store.close()
            close(arm)
            arm, _, inv = prepare(factories[name], visible)
            with tempfile.TemporaryDirectory() as directory:
                store = Store(Path(directory))
                changed = dict(inv.arguments, content="substituted")
                outcome = invoke(arm, store, inv.tool, changed)
                assert outcome["admitted"] == (name == "B2-exchange-task")
                # A revocation uses a server-pinned task handle, even if the presentation changes.
                arm._staged = replace(arm._staged, task_id="attacker-chosen-task")
                gate = StatusGate(
                    arm,
                    inv.task_id,
                    TaskStatus(inv.now_epoch, frozenset({inv.task_id})),
                    inv.now_epoch,
                )
                assert invoke(gate, store, inv.tool, inv.arguments)["reason"] == "task_revoked"
                store.close()
            close(arm)
    assert TaskStatus(100).decide("task", 130)[0]
    assert not TaskStatus(100).decide("task", 131)[0]


def test_failure_is_saved_before_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(BoundOAuthArm, "decide", lambda self, tool, arguments: (False, "injected"))
    destination = tmp_path / "failed"
    with pytest.raises(AssertionError):
        run_suite(destination, suites=[("policy", policy_cases)])
    status = json.loads((destination / "status.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (destination / "policy.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert status["status"] == "failed" and status["active_suite"] == "policy"
    assert rows[-1]["reason"] == "injected" and not rows[-1]["admitted"]
    assert not (destination / "policy.json").exists()
    with pytest.raises(FileExistsError):
        run_suite(destination, suites=[])


def test_stale_snapshot_cases_are_recorded(tmp_path):
    journal = tmp_path / "revocation.jsonl"
    rows = revocation_cases(journal=journal)
    assert len(rows) == 200
    stale = [row for row in rows if row["reason"] == "status_stale"]
    assert len(stale) == 4
    assert all(row["before"] == row["after"] and not row["effects"] for row in stale)
    assert len(journal.read_text(encoding="utf-8").splitlines()) == len(rows)


def test_existing_model_scores_reproduce():
    root = Path(__file__).resolve().parents[1] / "results/revision/model02"
    protocol = json.loads((root / "protocol.json").read_text(encoding="utf-8"))
    count = 0
    for path in root.glob("B*.json"):
        if "-response-" in path.name:
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        scores = score_episode(
            row["final"], protocol["source"] + protocol["attacks"][row["attack"]], row["attack"]
        )
        assert scores["task_complete"] == row["task_complete"]
        assert scores["attacker_success"] == row["attacker_success"]
        targets = [call for call in row["calls"] if target_call(call, row["attack"])]
        assert len(targets) == (1 if row["attack"] == "private-read" else 0)
        count += 1
    assert count == 45


def test_optimized_run_is_rejected_before_execution(tmp_path):
    destination = tmp_path / "optimized"
    env = dict(os.environ, PYTHONUTF8="1")
    result = subprocess.run(
        [sys.executable, "-O", "-m", "validation.revision.run", "--out", str(destination)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0 and "assertions enabled" in result.stderr
    assert not destination.exists()


@pytest.mark.parametrize("name", ("B3", "B3+"))
@pytest.mark.parametrize("change", ("unchanged", "reordered", "removed", "added", "malformed"))
def test_invocation_binds_presented_label_references(name, change):
    with lab() as (runner, visible, factories):
        arm, credentials, invocation = prepare(factories[name], visible)
        labels = tuple(
            issue_label_assertion(
                runner.seed, value=invocation.arguments["content"], label="public",
                iat=invocation.now_epoch - offset, exp=invocation.now_epoch + 120,
            )
            for offset in (1, 2)
        )
        signed_labels = () if change == "added" else labels
        arm.present(credentials, replace(invocation, payload_labels=signed_labels))
        presentations = {
            "unchanged": signed_labels,
            "reordered": tuple(reversed(signed_labels)),
            "removed": (),
            "added": labels,
            "malformed": ({"label": "public"},),
        }
        arm._staged = replace(arm._staged, payload_labels=presentations[change])
        admitted, reason = arm.decide(invocation.tool, invocation.arguments)
        assert admitted == (change in ("unchanged", "reordered"))
        if not admitted:
            assert reason == "b3_invocation_binding"
        close(arm)
