"""The latency artifact must fit the SEALED analysis layer, unchanged.

`analysis/latency.py` was sealed before this collector existed, so it is the
specification and the collector is the new thing. A collector whose output
needed the analysis layer edited to read it has failed. ADR 0047.

Two properties are asserted here that a weaker acceptance standard would have
let through:

* the by-name refusal guard is **WATCHED FIRING**, not assumed. A guard nobody
  has seen refuse anything is untested code making a claim — and this project
  has already been bitten by exactly that: the confirmatory corpus's
  `cf-f1-chain-tamper` never triggers the sealed guard, which names the pilot
  id, so an acceptance test could have "passed" while the guard sat inert.
* the artifact's `scenario_id` values are the **pilot ids as generated**, never
  rewritten. Rewriting an id to satisfy a constant would make the artifact lie
  about which scenario it measured.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))

from analysis import latency  # noqa: E402
from analysis.security import AnalysisError  # noqa: E402
from src.harness import latency_collector as collector  # noqa: E402

ARTIFACT = collector.output_path()
pytestmark = pytest.mark.skipif(
    not ARTIFACT.is_file(), reason="the latency pass has not been run on this machine"
)


def _record() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _samples() -> list[latency.Sample]:
    """The artifact, as the SEALED `Sample` — no adapter, no field renaming."""
    return [
        latency.Sample(
            arm=row["arm"],
            scenario_id=row["scenario_id"],
            phase=row["phase"],
            batch=row["batch"],
            repetition=row["repetition"],
            span=row["span"],
            value_ms=row["value_ms"],
        )
        for row in _record()["samples"]
    ]


class TestNoVerdictReachesTheArtifact:
    """The security half's "once" is consumed. A latency artifact carrying
    verdicts would be indistinguishable, in a results table, from a re-run."""

    def test_no_forbidden_field_name_appears_anywhere_in_the_artifact(self):
        blob = ARTIFACT.read_text(encoding="utf-8")
        # The FORBIDDEN list is named in the collector so a reader can check it.
        offenders = [name for name in collector.FORBIDDEN_VERDICT_FIELDS if f'"{name}"' in blob]
        assert offenders == [], f"verdict field(s) reached the latency artifact: {offenders}"

    def test_a_sample_row_carries_exactly_the_expected_keys(self):
        rows = _record()["samples"]
        assert rows, "the artifact carries no samples"
        expected = {
            "arm",
            "scenario_id",
            "phase",
            "batch",
            "repetition",
            "span",
            "value_ms",
            "started_at",
        }
        for row in (rows[0], rows[len(rows) // 2], rows[-1]):
            assert set(row) == expected, set(row) ^ expected

    def test_the_guard_is_not_vacuous(self):
        """Negative arm: the check WOULD catch a verdict field if one appeared."""
        blob = json.dumps({"samples": [{"arm": "B3", "admission_breach": False}]})
        assert any(f'"{name}"' in blob for name in collector.FORBIDDEN_VERDICT_FIELDS)


class TestTheScenarioIdsAreThePilotIdsAsGenerated:
    def test_no_confirmatory_id_appears(self):
        blob = ARTIFACT.read_text(encoding="utf-8")
        assert "cf-" not in blob, (
            "a confirmatory id appears in a PILOT latency artifact; ids must be recorded as "
            "generated, never rewritten to satisfy a constant"
        )

    def test_the_scenarios_are_exactly_the_two_the_plan_measures(self):
        seen = {row["scenario_id"] for row in _record()["samples"]}
        assert seen == {collector.BENIGN_SCENARIO, collector.REFUSAL_SCENARIO}

    def test_the_refusal_scenario_is_the_one_the_sealed_layer_names(self):
        assert collector.REFUSAL_SCENARIO == latency.REFUSAL_PATH_SCENARIO


class TestTheSealedRefusalGuardFires:
    """WATCHED, not assumed."""

    def test_benign_series_refuses_a_refusal_path_sample(self):
        samples = _samples()
        assert any(s.scenario_id == latency.REFUSAL_PATH_SCENARIO for s in samples), (
            "the artifact carries no refusal-path samples, so the guard could not be watched"
        )

        with pytest.raises(AnalysisError) as caught:
            latency.benign_series(samples, arm="B3", phase="warm")

        assert latency.REFUSAL_PATH_SCENARIO in str(caught.value)
        assert "BENIGN series" in str(caught.value)

    def test_refusal_series_finds_samples_rather_than_raising_on_an_empty_one(self):
        values = latency.refusal_series(_samples(), arm="B3", phase="warm")
        assert values, "the refusal series is empty; an empty series is not a result"
        assert all(v > 0 for v in values)

    def test_the_benign_series_is_computable_once_the_refusal_path_is_separated(self):
        benign = [s for s in _samples() if s.scenario_id != latency.REFUSAL_PATH_SCENARIO]
        values = latency.benign_series(benign, arm="B3", phase="warm")
        assert values


class TestTheSealedPlanIsImplementedAsWritten:
    def test_at_least_200_repetitions_per_configuration_across_at_least_3_batches(self):
        record = _record()
        kept = latency.discard_warmup(_samples(), per_batch=record["plan"]["warmup_per_batch"])
        for arm in {s.arm for s in kept}:
            for phase in latency.PHASES:
                rows = [
                    s
                    for s in kept
                    if s.arm == arm
                    and s.phase == phase
                    and s.span == "end_to_end"
                    and s.scenario_id == collector.BENIGN_SCENARIO
                ]
                assert len(rows) >= 200, (arm, phase, len(rows))
                assert len({s.batch for s in rows}) >= 3, (arm, phase)

    def test_cold_and_warm_are_both_present_and_never_pooled(self):
        samples = _samples()
        assert {s.phase for s in samples} == set(latency.PHASES)
        # `_segment_values` filters by phase, so a pooled call is impossible by
        # construction; this pins that both phases actually carry data.
        for phase in latency.PHASES:
            assert latency.benign_series(
                [s for s in samples if s.scenario_id != latency.REFUSAL_PATH_SCENARIO],
                arm="B0",
                phase=phase,
            )

    def test_every_seed_is_recorded_not_merely_used(self):
        plan = _record()["plan"]
        assert isinstance(plan["bootstrap_seed"], int)
        assert isinstance(plan["order_seed"], int)
        assert plan["bootstrap_resamples"] == 10_000

    def test_no_exclusion_rule_was_applied(self):
        assert "NONE" in _record()["plan"]["exclusion_rule"]

    def test_every_repetition_carries_a_wall_clock_timestamp(self):
        from datetime import datetime

        rows = _record()["samples"]
        stamps = {row["started_at"] for row in rows}
        assert len(stamps) > 1, "one timestamp for the whole pass locates no stall"
        for stamp in list(stamps)[:50]:
            datetime.fromisoformat(stamp)  # raises if not a real timestamp

    def test_all_five_spans_are_persisted_per_repetition(self):
        rows = _record()["samples"]
        by_rep: dict[tuple, set] = {}
        for row in rows:
            key = (row["arm"], row["scenario_id"], row["phase"], row["batch"], row["repetition"])
            by_rep.setdefault(key, set()).add(row["span"])
        missing = {k: sorted(set(collector.SPANS) - v) for k, v in by_rep.items() if len(v) != 5}
        assert missing == {}, list(missing.items())[:3]


class TestTheSealedAnalysisConsumesItUnchangedAndDecides:
    """The acceptance standard: a `Decision` from the row 1 estimand, produced
    by the sealed layer with no edit to it."""

    def test_the_row_1_estimand_produces_a_decision(self):
        from src.harness import frozen_parameters as fp

        record = _record()
        benign = [
            s
            for s in latency.discard_warmup(
                _samples(), per_batch=record["plan"]["warmup_per_batch"]
            )
            if s.scenario_id != latency.REFUSAL_PATH_SCENARIO
        ]

        decision = latency.lightweight_claim(
            benign,
            margin_ms=fp.equivalence_margin_ms(),
            seed=record["plan"]["bootstrap_seed"],
            resamples=record["plan"]["bootstrap_resamples"],
        )

        assert isinstance(decision, latency.Decision)
        # The vocabulary is the SEALED layer's, not this test's: ADR 0026's
        # rule is "stands iff the CI upper bound is < margin_ms", and the
        # verdict words are `stands` / `retracted`. This test first asserted
        # `supported`/`not supported`, which is a vocabulary the specification
        # does not use — corrected here rather than by widening the assertion,
        # because the collector fits the analysis layer and so does its test.
        assert decision.verdict in {"stands", "retracted"}
        assert decision.margin_ms == fp.equivalence_margin_ms()
        assert decision.ci.low <= decision.point_estimate_ms <= decision.ci.high
        # The rule itself, recomputed rather than trusted.
        assert decision.verdict == (
            "stands" if decision.ci.high < decision.margin_ms else "retracted"
        )
        # Both arms contributed the plan's kept sample count.
        assert decision.treatment.n >= 200 and decision.control.n >= 200

    def test_analysis_latency_is_unmodified_since_it_was_first_sealed(self):
        """The collector fits the analysis layer, not the reverse.

        Checked against EVERY manifest that covers the file -- the current seal
        and every superseded one under seal/superseded/ -- rather than against
        one named manifest. Two reasons, both learned at the v0.8 seal: naming
        `seal/manifest_v0.7.json` broke this test the moment v0.7 was relocated
        into seal/superseded/, and pinning to a single manifest would let a
        future reseal quietly relax the pin by restating a new hash. Agreement
        across all of them is the actual claim -- that this file has not moved
        since it was first sealed.
        """
        import hashlib
        import json as _json
        import subprocess

        blob = subprocess.run(
            ["git", "cat-file", "blob", "HEAD:analysis/latency.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            check=True,
        ).stdout
        actual = hashlib.sha256(blob).hexdigest()

        seal = REPO_ROOT / "seal"
        current = sorted(seal.glob("manifest_v*.json"))
        assert len(current) == 1, f"expected exactly one current seal manifest, found {current}"
        checked = []
        for path in current + sorted((seal / "superseded").glob("manifest_v*.json")):
            manifest = _json.loads(path.read_text(encoding="utf-8"))
            expected = manifest["covered"].get("analysis/latency.py")
            if expected is None:  # a manifest predating the file
                continue
            assert actual == expected, (
                f"analysis/latency.py changed; it is the sealed specification and forbidden "
                f"action 3. {path.name} pins {expected}, the tree has {actual}"
            )
            checked.append(path.name)
        assert len(checked) >= 2, f"only {checked} pinned the file; expected the seal and a prior"
