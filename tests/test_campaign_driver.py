"""The Part H step 7 entry point, and the write-once discipline it enforces.

The repository had no command that runs the campaign, and nothing that wrote a
result to `results/raw/`. ADR 0045 records why one campaign is three
`run_campaign` calls across two AS processes, and that this is a property of
the sealed corpus rather than a choice.

These tests do NOT execute a campaign: a pass stands up an AS on loopback TLS
and drives 153 cells, which belongs in a gate, not a unit suite. They pin the
structure a campaign depends on -- the chain split derived from the corpus, the
apparatus constants, and the refusal to overwrite a result.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))

from src.harness import campaign_driver as driver  # noqa: E402
from src.harness.runner import GoldenThreadRunner  # noqa: E402


class TestTheCampaignShapeIsDerivedFromTheCorpus:
    """A hardcoded family list would not notice a corpus growing a third chain."""

    @pytest.mark.parametrize("run_mode", ["pilot", "confirmatory"])
    def test_the_corpus_splits_into_its_task_grant_chains(self, run_mode):
        corpus_root = driver.CORPORA[run_mode]
        runner = GoldenThreadRunner(corpus_dir=corpus_root, run_mode=run_mode)
        scenarios = driver._scenarios(corpus_root)

        groups = driver._split_by_chain(runner, scenarios)

        assert len(groups) == 2, "the corpus declares two chains (ADR 0045)"
        sizes = sorted(len(members) for members in groups.values())
        assert sizes == [4, 9], sizes
        assert sum(sizes) == len(scenarios) == 13
        seen = [s for members in groups.values() for s in members]
        assert sorted(seen) == sorted(scenarios), "every scenario lands in exactly one chain"

    @pytest.mark.parametrize("run_mode", ["pilot", "confirmatory"])
    def test_the_f4_f5_chain_is_the_one_needing_both_configurations(self, run_mode):
        """`A†` is 'admitted ABSENT the shared monitor', so the configuration
        families run twice and everything else once."""
        from src.harness import campaign as C

        corpus_root = driver.CORPORA[run_mode]
        runner = GoldenThreadRunner(corpus_dir=corpus_root, run_mode=run_mode)
        groups = driver._split_by_chain(runner, driver._scenarios(corpus_root))

        needs_both = [
            members
            for members in groups.values()
            if any(
                C._family_of(str(C._sealed_document(corpus_root, s).get("attack_subcase", "")))
                in C.matrix_grouping.CONFIGURATION_FAMILIES
                for s in members
            )
        ]
        assert len(needs_both) == 1
        assert len(needs_both[0]) == 4


class TestTheApparatusConstants:
    def test_the_token_lifetime_covers_a_pass_with_room(self):
        """300 s is the AS default and a pass does not fit in it; the campaign
        value must be well clear, and must stay FINITE so `clock_refusal`
        remains reachable (ADR 0045)."""
        assert driver.CAMPAIGN_TOKEN_LIFETIME_SECONDS >= 3600
        assert driver.CAMPAIGN_TOKEN_LIFETIME_SECONDS < 24 * 3600

    def test_the_wrong_audience_is_not_the_runs_own_audience(self):
        import json

        for corpus_root in driver.CORPORA.values():
            document = json.loads((corpus_root / "corpus.json").read_text(encoding="utf-8"))
            assert driver.WRONG_AUDIENCE != document["audience"], (
                "a token minted for the CORRECT audience would score as the arm admitting "
                "an attack that was never staged"
            )

    def test_the_as_document_refuses_a_wrong_audience_equal_to_the_real_one(self):
        from src.harness import as_process, key_material
        from src.harness.authorizer import frozen_config
        from src.harness.verifier import registry as reg

        registry_document = reg.load_document()
        seed = bytes.fromhex("e1" * 32)
        with pytest.raises(as_process.ASProcessError):
            as_process.golden_thread_as_document(
                corpus={"issuer": "https://as.aasc.local", "audience": "rs.aasc.local"},
                registry_document=registry_document,
                resolved_keys=key_material.resolve_public(seed),
                identity_jwks=key_material.identity_jwks(seed, registry_document["principals"]),
                omega_elements=frozen_config.load_document()["omega"]["elements"],
                wrong_audience="rs.aasc.local",
            )

    def test_the_as_document_carries_both_constants_when_asked(self):
        from src.harness import as_process, key_material
        from src.harness.authorizer import frozen_config
        from src.harness.verifier import registry as reg

        registry_document = reg.load_document()
        seed = bytes.fromhex("e1" * 32)
        document = as_process.golden_thread_as_document(
            corpus={"issuer": "https://as.aasc.local", "audience": "rs.aasc.local"},
            registry_document=registry_document,
            resolved_keys=key_material.resolve_public(seed),
            identity_jwks=key_material.identity_jwks(seed, registry_document["principals"]),
            omega_elements=frozen_config.load_document()["omega"]["elements"],
            task_grant=[["notes.write", "notes/project"]],
            default_lifetime_seconds=driver.CAMPAIGN_TOKEN_LIFETIME_SECONDS,
            wrong_audience=driver.WRONG_AUDIENCE,
            wrong_audience_grant_name=driver.WRONG_AUDIENCE_GRANT,
        )

        assert document["default_lifetime_seconds"] == driver.CAMPAIGN_TOKEN_LIFETIME_SECONDS
        assert driver.WRONG_AUDIENCE in document["resource_servers"]
        assert "rs.aasc.local" in document["resource_servers"]
        grants = document["phase1"]["agent-supervisor"]["additional_grants"]
        assert driver.WRONG_AUDIENCE_GRANT in grants
        assert grants[driver.WRONG_AUDIENCE_GRANT]["audience"] == driver.WRONG_AUDIENCE

    def test_the_default_document_is_unchanged_without_the_new_arguments(self):
        """Every existing caller -- gates included -- must be untouched."""
        from src.harness import as_process, key_material
        from src.harness.authorizer import frozen_config
        from src.harness.verifier import registry as reg

        registry_document = reg.load_document()
        seed = bytes.fromhex("e1" * 32)
        document = as_process.golden_thread_as_document(
            corpus={"issuer": "https://as.aasc.local", "audience": "rs.aasc.local"},
            registry_document=registry_document,
            resolved_keys=key_material.resolve_public(seed),
            identity_jwks=key_material.identity_jwks(seed, registry_document["principals"]),
            omega_elements=frozen_config.load_document()["omega"]["elements"],
        )

        assert "default_lifetime_seconds" not in document
        assert document["resource_servers"] == ["rs.aasc.local"]


class TestWriteOnce:
    def test_an_existing_result_is_refused_by_name(self, tmp_path):
        existing = tmp_path / "campaign-confirmatory.json"
        existing.write_text("{}", encoding="utf-8")

        with pytest.raises(driver.CampaignDriverError) as caught:
            driver.refuse_if_written(existing)

        message = str(caught.value)
        assert "once" in message.lower()
        assert "DEVIATIONS" in message, "an abort must be recorded, not just re-run"

    def test_a_fresh_path_is_permitted(self, tmp_path):
        driver.refuse_if_written(tmp_path / "not-yet.json")

    def test_the_output_path_is_under_results_raw(self):
        for run_mode in driver.CORPORA:
            path = driver.output_path(run_mode)
            assert path.parent == driver.RESULTS_RAW
            assert run_mode in path.name

    def test_run_refuses_before_doing_any_work(self, tmp_path, monkeypatch):
        """The refusal must come BEFORE an AS is spawned: a driver that
        discovers the collision after a 153-cell pass has already burned the
        thing it was protecting."""
        existing = tmp_path / "taken.json"
        existing.write_text("{}", encoding="utf-8")

        def _explode(*_args, **_kwargs):  # pragma: no cover - must never run
            raise AssertionError("the campaign started despite an existing result")

        monkeypatch.setattr(driver, "GoldenThreadRunner", _explode)
        with pytest.raises(driver.CampaignDriverError):
            driver.run(run_mode="confirmatory", out=existing)
