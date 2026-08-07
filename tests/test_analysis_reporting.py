"""The three pre-registered commitments, enforced where the numbers are made.

`analysis/` was frozen with the seal and could not read the campaign it was
frozen alongside: no loader, no matrix as data, no representation for
NOT-POPULATED, no F4 qualification, no H4a/H4b evaluator. ADR 0044.

The commitments under test, verbatim from `docs/PRE_REGISTRATION.md`:

* §4 — the three uninstantiated F3 rows *"MUST be reported as NOT POPULATED BY
  THE CAMPAIGN — not as passing, not as confirmed, not as agreeing with the
  prediction, and never inside a per-family count"*, and F3's two-of-five
  coverage *"travels with every F3 number this study reports"*.
* §2 — F4 agreement *"must not be reported as replication of the same strength
  as F1, F2, F3 or F5"*.
* §3 — H4a and H4b, with their own falsification conditions.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))

from analysis import hypotheses, ingest, report  # noqa: E402
from analysis.matrix import (  # noqa: E402
    ROW_SUBCASE_TOKENS,
    AnalysisError,
    RowState,
    load_matrix,
    mark_population,
)

CORPORA = {
    "pilot": REPO_ROOT / "fixtures" / "pilot" / "golden_thread",
    "confirmatory": REPO_ROOT / "fixtures" / "confirmatory",
}

CONFIGURATION_FAMILIES = {"F4", "F5"}


def _synthetic_campaign(flip: tuple[str, str] | None = None) -> ingest.Campaign:
    """A campaign record built FROM the expected matrix, over the PILOT corpus.

    Synthetic, and labelled as such: it proves the JOIN -- that a daggered
    prediction is compared against the unmonitored pass, that NOT_POPULATED
    rows stay out of every count -- and it proves nothing about the mechanisms,
    because its cells are the predictions. The end-to-end run against a real
    campaign result is a gate's job, not a unit suite's.

    `flip` inverts one cell so the comparison can be watched FIRING; a
    comparison that cannot disagree has not been tested.
    """
    matrix = mark_population(load_matrix(), CORPORA["pilot"])
    cells = []
    for row in matrix.rows:
        if not row.populated:
            continue
        token = ROW_SUBCASE_TOKENS[
            __import__("analysis.matrix", fromlist=["row_key"]).row_key(row.subcase)
        ]
        monitors = (False, True) if row.family in CONFIGURATION_FAMILIES else (None,)
        for monitor in monitors:
            for arm, expected in row.cells.items():
                if expected.value == "NA":
                    continue
                value = expected.value
                # A daggered cell is `A` unmonitored and blocks once the shared
                # monitor is attached -- that is what the dagger MEANS.
                if expected.dagger and monitor is True:
                    value = "B"
                forwarded = value == "A"
                if flip == (token, arm) and monitor is not True:
                    forwarded = not forwarded
                cells.append(
                    {
                        "scenario_id": f"scn-{token}",
                        "arm": arm,
                        "family": row.family,
                        "subcase": token,
                        "monitor_attached": monitor,
                        "observed_forwarded": forwarded,
                        "reference_allow": forwarded,
                        "admission_breach": False,
                        "false_block": False,
                        "realized_harm": False,
                        "log_integrity_failure": False,
                    }
                )
    return ingest.Campaign(
        run_mode="pilot",
        corpus_root=CORPORA["pilot"],
        cells=cells,
        unscorable=[["scn-x", "B0", "NA per the sealed record"]],
        passes=[],
        raw={"run_mode": "pilot", "scenarios": ["scn-synthetic"]},
    )


@pytest.fixture
def smoke_campaign() -> ingest.Campaign:
    return _synthetic_campaign()


@pytest.fixture
def pilot_report(smoke_campaign, monkeypatch) -> dict:
    monkeypatch.setattr(ingest, "load_campaign", lambda _path: smoke_campaign)
    return report.build("pilot", path=Path("ignored-by-the-monkeypatch"))


class TestTheMatrixIsParsedNotTranscribed:
    def test_it_parses_to_fourteen_rows_and_nine_arms(self):
        matrix = load_matrix()
        assert len(matrix.rows) == 14
        assert len(matrix.arms) == 9

    def test_the_arms_are_the_ladder_the_harness_knows(self):
        from src.harness.matrix_grouping import ARMS

        assert load_matrix().arms == tuple(ARMS)

    def test_a_second_copy_of_the_matrix_does_not_exist_in_analysis(self):
        """A transcription here would be a second frozen artifact that could
        drift from the sealed one, invisibly."""
        source = (REPO_ROOT / "analysis" / "matrix.py").read_text(encoding="utf-8")
        assert "F1-root (R" not in source, "the matrix is parsed from the sealed document"


class TestNotPopulatedIsRepresented:
    @pytest.mark.parametrize("corpus", sorted(CORPORA))
    def test_exactly_the_three_declared_f3_rows_are_not_populated(self, corpus):
        matrix = mark_population(load_matrix(), CORPORA[corpus])
        missing = sorted(
            row.subcase.split("(")[0].strip()
            for row in matrix.rows
            if row.state is RowState.NOT_POPULATED
        )
        assert missing == [
            "F3 dpop-captured-proof-replay",
            "F3 dpop-first-use-body-mutation",
            "F3 expired token",
        ], "the pre-registration names exactly these three (§4)"

    @pytest.mark.parametrize("corpus", sorted(CORPORA))
    def test_f3_coverage_is_two_of_five(self, corpus):
        matrix = mark_population(load_matrix(), CORPORA[corpus])
        assert matrix.family_coverage("F3") == (2, 5)

    def test_wrong_principal_is_deferred_and_never_na(self):
        matrix = load_matrix()
        row = next(r for r in matrix.rows if "wrong_principal" in r.subcase)
        assert row.state is RowState.DEFERRED
        assert "ADR 0028" in row.state.value
        assert "NA" not in row.reason.split("never as NA")[0].replace("ADR 0028", "")

    def test_a_not_populated_row_publishes_no_cells(self):
        """Rendering its predictions as though measured is precisely the
        reading §4 forbids."""
        matrix = mark_population(load_matrix(), CORPORA["confirmatory"])
        for row in matrix.rows:
            if row.state is RowState.NOT_POPULATED:
                assert row.as_dict()["cells"] == {}
                assert "NOT POPULATED BY THE CAMPAIGN" in row.as_dict()["state"]

    def test_an_unmapped_corpus_subcase_fails_closed(self, tmp_path):
        """A scenario that maps to no row would be measured and never
        reported; that must raise, not pass quietly."""
        sealed = tmp_path / "sealed"
        sealed.mkdir()
        (sealed / "x.json").write_text(
            json.dumps({"attack_subcase": "F9:something-new"}), encoding="utf-8"
        )
        with pytest.raises(AnalysisError) as caught:
            mark_population(load_matrix(), tmp_path)
        assert "F9:something-new" in str(caught.value)

    def test_every_matrix_row_has_a_mapping_entry(self):
        from analysis.matrix import row_key

        for row in load_matrix().rows:
            if row.state is RowState.DEFERRED:
                continue
            assert row_key(row.subcase) in ROW_SUBCASE_TOKENS


class TestTheF4QualificationTravels:
    def test_the_qualification_names_what_it_forfeits(self):
        text = report.F4_QUALIFICATION
        assert "must not be reported as replication of the same strength" in text.lower()
        assert "mail.send" in text and "mail/outbox" in text
        assert "instance-selection bias" in text

    def test_it_is_attached_to_the_f4_family_block(self, pilot_report):
        assert "qualification" in pilot_report["class_macro"]["F4"]
        assert "qualification" not in pilot_report["class_macro"]["F1"]

    def test_the_coverage_warning_travels_with_f3(self, pilot_report):
        assert "2 of 5" in pilot_report["class_macro"]["F3"]["coverage_warning"]


class TestTheDaggerIsRespected:
    """`A†` is 'admitted ABSENT the shared monitor'.

    Collapsing the two monitor passes into one entry let the monitored pass
    overwrite the unmonitored one, and every daggered cell then compared `A†`
    against a `B` measured under a monitor: eight spurious disagreements that
    would have entered the results chapter as findings about the mechanisms.
    """

    def test_the_observed_key_carries_the_monitor_configuration(self, smoke_campaign):
        keys = ingest.observed_cells(smoke_campaign)
        assert all(len(key) == 3 for key in keys)
        monitors = {key[2] for key in keys}
        assert monitors == {None, False, True}, monitors

    def test_a_daggered_prediction_is_compared_against_the_unmonitored_pass(
        self, smoke_campaign, pilot_report
    ):
        daggered = [
            entry
            for entry in pilot_report["agreement"]["disagreed"]
            if entry["expected"].endswith("†")
        ]
        assert daggered == [], (
            "a daggered cell disagreed, which means it was compared against the wrong "
            "monitor configuration"
        )

    def test_the_synthetic_campaign_agrees_with_the_expected_matrix(self, pilot_report):
        assert pilot_report["agreement"]["disagreed"] == []
        assert pilot_report["agreement"]["agreed"] > 0

    def test_the_comparison_can_actually_disagree(self, monkeypatch):
        """Watched firing. A comparison that never disagrees would report
        perfect agreement with a matrix it is not really checking."""
        flipped = _synthetic_campaign(flip=("F1:root", "B3"))
        monkeypatch.setattr(ingest, "load_campaign", lambda _path: flipped)
        built = report.build("pilot", path=Path("ignored"))

        disagreements = built["agreement"]["disagreed"]
        assert len(disagreements) == 1, disagreements
        assert disagreements[0]["arm"] == "B3"
        assert disagreements[0]["expected"] == "B"
        assert disagreements[0]["observed"] == "A"


class TestTheHypothesesAreEvaluated:
    def test_h4a_is_not_determined_while_its_second_attack_is_unpopulated(self, pilot_report):
        h4a = next(h for h in pilot_report["hypotheses"] if h["hypothesis"] == "H4a")
        assert h4a["verdict"] == "NOT DETERMINED"
        assert any("NOT POPULATED" in reason for reason in h4a["reasons"])

    def test_h4b_is_not_determined_and_says_why(self, pilot_report):
        h4b = next(h for h in pilot_report["hypotheses"] if h["hypothesis"] == "H4b")
        assert h4b["verdict"] == "NOT DETERMINED"
        assert any("compromised-holder" in reason for reason in h4b["reasons"])

    def test_h4a_is_falsified_when_b3_admits(self):
        """The falsification condition must be able to FIRE."""
        observed = {(hypotheses.H4A_REUSE, hypotheses.STRONG): "A"}
        verdict = hypotheses.evaluate_h4a(observed)
        assert verdict.verdict == "FALSIFIED"
        assert any("ADMITTED" in reason for reason in verdict.reasons)

    def test_h4a_is_falsified_when_dpop_blocks_body_mutation(self, monkeypatch):
        monkeypatch.setattr(hypotheses, "H4A_BODY_MUTATION", "F3:dpop-first-use-body-mutation")
        observed = {("F3:dpop-first-use-body-mutation", hypotheses.DPOP): "B"}
        verdict = hypotheses.evaluate_h4a(observed)
        assert verdict.verdict == "FALSIFIED"


class TestNoConfidenceIntervalOnASecurityProportion:
    def test_the_report_states_the_rule_and_publishes_no_interval(self, pilot_report):
        assert "No confidence interval" in pilot_report["statistical_note"]
        rendered = json.dumps(pilot_report)
        for forbidden in ("ci_low", "ci_high", "confidence_interval"):
            assert forbidden not in rendered

    def test_a_zero_denominator_reports_none_rather_than_zero(self):
        from analysis.security import Counts

        assert report._counts(Counts(0, 0))["rate"] is None


class TestTheAnalysisRefusesRatherThanInvents:
    def test_a_missing_campaign_result_is_refused_by_name(self, tmp_path):
        with pytest.raises(AnalysisError) as caught:
            ingest.load_campaign(tmp_path / "nothing.json")
        assert "step 7" in str(caught.value)
