"""The confirmatory corpus: disjoint from the pilot, and structurally matched to it.

Part H steps 4 and 5, and the bias guard that is the point of the exercise
(ADR 0043).

Three properties, and the third is the one that matters:

1. **The pilot still regenerates byte for byte.** The generator was
   parameterised, and the pilot profile carries exactly the values the file
   carried when fifteen gates were adjudicated against its output. One changed
   byte would mean the gate record no longer describes the corpus it was
   adjudicated on, so this is asserted document by document.
2. **Disjointness on SPECIFICATION AND SEED CONTENT HASHES** (Part H step 5),
   never on token bytes: two mints of the same logical capability differ in
   bytes (ADR 0007), so a token-byte comparison would report a disjointness
   that means nothing and would hide a real overlap.
3. **Structural match.** Identical family coverage, identical `attack_subcase`
   sets, identical `relation`/`is_benign`/`requires_approval` per matched pair,
   and identical SS E.4 predicted outcomes across all nine arms. Instances
   authored after watching the pilot behave are exactly where an author would
   -- without meaning to -- pick easier or harder cases; ADR 0037 declares
   instance-selection bias unmitigated and this test does not mitigate it
   either. It bounds what could drift **silently**.

Every scenario's `(action, resource)` pairs are also asserted inside the frozen
`Omega`: an instance outside it would be a malformed-request test, not a harder
instance.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_DIR = REPO_ROOT / "fixtures" / "pilot" / "golden_thread"
CONFIRMATORY_DIR = REPO_ROOT / "fixtures" / "confirmatory"

spec = importlib.util.spec_from_file_location("gt_generator_cf", PILOT_DIR / "generator.py")
generator = importlib.util.module_from_spec(spec)
sys.modules.setdefault("gt_generator_cf", generator)
spec.loader.exec_module(generator)


def _documents(directory: Path) -> dict[str, dict]:
    """Every corpus document under `directory`, keyed by relative path."""
    found: dict[str, dict] = {}
    for path in sorted(directory.rglob("*.json")):
        relative = path.relative_to(directory).as_posix()
        found[relative] = json.loads(path.read_text(encoding="utf-8"))
    return found


def _digest(document: dict) -> str:
    """A content hash of a SPECIFICATION -- never of a token byte."""
    canonical = json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sealed(directory: Path) -> dict[str, dict]:
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((directory / "sealed").glob("*.json"))
    }


def _omega() -> frozenset:
    from src.harness.authorizer import frozen_config

    return frozen_config.omega(frozen_config.load_document())


class TestThePilotIsUnchanged:
    def test_the_pilot_regenerates_byte_for_byte(self):
        """The acceptance standard's first clause, asserted per document."""
        regenerated = generator.generate(write=False, profile=generator.PILOT)
        for relative, document in regenerated.items():
            on_disk = json.loads((PILOT_DIR / relative).read_text(encoding="utf-8"))
            assert on_disk == document, f"{relative} drifted from the pilot profile"
        assert len(regenerated) == 1 + 2 * 13  # corpus.json + 13 scenarios x 2 documents

    def test_the_pilot_profile_still_carries_the_sealed_values(self):
        profile = generator.PILOT
        assert profile.seed_hex == "e1" * 32
        assert profile.task_id == "task-gt-pilot"
        assert profile.corpus_name == "golden_thread(pilot)"
        assert profile.output_dir == PILOT_DIR
        on_disk = json.loads((PILOT_DIR / "corpus.json").read_text(encoding="utf-8"))
        assert on_disk["seed_hex"] == profile.seed_hex
        assert on_disk["task_id"] == profile.task_id


class TestTheSymmetricGuard:
    """Both halves watched failing. The guard REPLACED the pre-seal
    empty-directory check rather than deleting it, and it constrains both
    corpora rather than one."""

    def test_the_pilot_profile_refuses_to_write_into_the_confirmatory_directory(self):
        import dataclasses

        stray = dataclasses.replace(generator.PILOT, output_dir=CONFIRMATORY_DIR)
        with pytest.raises(SystemExit) as caught:
            generator.generate(write=False, profile=stray)
        assert "may write ONLY to" in str(caught.value)

    def test_the_confirmatory_profile_refuses_to_write_into_the_pilot_directory(self):
        import dataclasses

        stray = dataclasses.replace(generator.CONFIRMATORY, output_dir=PILOT_DIR)
        with pytest.raises(SystemExit) as caught:
            generator.generate(write=False, profile=stray)
        assert "may write ONLY to" in str(caught.value)

    def test_an_unknown_mode_fails_closed(self):
        import dataclasses

        stray = dataclasses.replace(generator.CONFIRMATORY, mode="rehearsal")
        with pytest.raises(SystemExit) as caught:
            generator.generate(write=False, profile=stray)
        assert "unknown corpus mode" in str(caught.value)


class TestDisjointness:
    """Part H step 5. On specification and seed content hashes, never tokens."""

    def test_no_scenario_file_is_shared(self):
        """`corpus.json` is the corpus-level runner-inputs document, not a
        scenario file; both corpora have one by construction and their CONTENTS
        are compared below. The scenario files are what must not be shared."""

        def scenario_files(directory):
            return {name for name in _documents(directory) if name != "corpus.json"}

        pilot = scenario_files(PILOT_DIR)
        confirmatory = scenario_files(CONFIRMATORY_DIR)
        assert pilot & confirmatory == set()
        assert len(pilot) == len(confirmatory) == 2 * 13
        pilot_corpus = json.loads((PILOT_DIR / "corpus.json").read_text(encoding="utf-8"))
        conf_corpus = json.loads((CONFIRMATORY_DIR / "corpus.json").read_text(encoding="utf-8"))
        assert _digest(pilot_corpus) != _digest(conf_corpus)

    def test_no_specification_content_hash_is_shared(self):
        pilot = {_digest(doc) for doc in _documents(PILOT_DIR).values()}
        confirmatory = {_digest(doc) for doc in _documents(CONFIRMATORY_DIR).values()}
        assert len(pilot) == len(confirmatory) == 1 + 2 * 13
        assert pilot & confirmatory == set(), "a specification is shared between the corpora"

    def test_the_seed_content_hashes_differ(self):
        pilot = json.loads((PILOT_DIR / "corpus.json").read_text(encoding="utf-8"))
        confirmatory = json.loads((CONFIRMATORY_DIR / "corpus.json").read_text(encoding="utf-8"))
        assert pilot["seed_hex"] != confirmatory["seed_hex"]
        pilot_seed = hashlib.sha256(bytes.fromhex(pilot["seed_hex"])).hexdigest()
        confirmatory_seed = hashlib.sha256(bytes.fromhex(confirmatory["seed_hex"])).hexdigest()
        assert pilot_seed != confirmatory_seed
        assert pilot["task_id"] != confirmatory["task_id"]

    def test_the_derivation_rule_is_deliberately_the_same(self):
        """The RULE is sealed (ADR 0007/0019 fix the labels and the derivation,
        never key bytes); the SEED is the instance parameter. Disjoint keys come
        from the seed, so the prefix stays identical and the runner's existing
        drift check keeps passing for both corpora."""
        from src.harness import key_material

        pilot = json.loads((PILOT_DIR / "corpus.json").read_text(encoding="utf-8"))
        confirmatory = json.loads((CONFIRMATORY_DIR / "corpus.json").read_text(encoding="utf-8"))
        expected = key_material.DERIVATION_INFO_PREFIX.decode("ascii")
        assert pilot["derivation_info_prefix"] == expected
        assert confirmatory["derivation_info_prefix"] == expected

    def test_the_derived_key_material_actually_differs(self):
        """Not asserted from the seeds alone: the derivation is run."""
        from src.harness import key_material

        pilot = json.loads((PILOT_DIR / "corpus.json").read_text(encoding="utf-8"))
        confirmatory = json.loads((CONFIRMATORY_DIR / "corpus.json").read_text(encoding="utf-8"))
        for label in ("kappa", "holder-supervisor", "holder-specialist", "holder-worker"):
            first = key_material.derive_raw(bytes.fromhex(pilot["seed_hex"]), label)
            second = key_material.derive_raw(bytes.fromhex(confirmatory["seed_hex"]), label)
            assert first != second, label


class TestStructuralMatch:
    """The bias guard. A confirmatory corpus that predicts differently from the
    pilot is not a fresh instance set, it is a different experiment."""

    def test_every_confirmatory_scenario_names_its_matched_pilot_sibling(self):
        pilot = _sealed(PILOT_DIR)
        confirmatory = _sealed(CONFIRMATORY_DIR)
        assert len(pilot) == len(confirmatory) == 13
        siblings = {doc["matched_pilot_sibling"] for doc in confirmatory.values()}
        assert siblings == set(pilot), "the pairing is not one-to-one"

    def test_matched_pairs_agree_on_everything_that_must_not_vary(self):
        pilot = _sealed(PILOT_DIR)
        for scenario_id, document in _sealed(CONFIRMATORY_DIR).items():
            sibling = pilot[document["matched_pilot_sibling"]]
            for field in ("attack_subcase", "is_benign", "requires_approval"):
                assert document[field] == sibling[field], (scenario_id, field)

    def test_the_family_coverage_and_subcase_sets_are_identical(self):
        def subcases(directory):
            return {doc["attack_subcase"] for doc in _sealed(directory).values()}

        def families(directory):
            return {doc["attack_subcase"].split(":")[0] for doc in _sealed(directory).values()}

        assert subcases(PILOT_DIR) == subcases(CONFIRMATORY_DIR)
        assert families(PILOT_DIR) == families(CONFIRMATORY_DIR)

    def test_the_relations_match_pair_for_pair(self):
        """`relation` lives in the generator's spec rather than in the written
        document, so it is read from the spec sets and matched by sibling."""
        pilot = {s["scenario_id"]: s for s in generator.SCENARIOS}
        for scenario in generator.CONFIRMATORY_SCENARIOS:
            sibling = pilot[scenario["matched_pilot_sibling"]]
            assert scenario["relation"] == sibling["relation"], scenario["scenario_id"]
            assert scenario["attack_subcase"] == sibling["attack_subcase"]
            assert scenario["is_benign"] == sibling["is_benign"]

    def test_the_e4_predicted_outcomes_are_identical_across_all_nine_arms(self):
        """The prediction is a function of the SUBCASE, which is what SS E.4 is
        indexed by -- so identical subcases with identical NA sets predict
        identically for every one of the nine arms. Both halves are asserted:
        the subcase strings, and the per-arm NA sets that decide which cells
        are scored at all."""
        from src.harness import matrix_grouping

        assert len(matrix_grouping.ARMS) == 9
        pilot = _sealed(PILOT_DIR)
        for document in _sealed(CONFIRMATORY_DIR).values():
            sibling = pilot[document["matched_pilot_sibling"]]
            assert document["attack_subcase"] == sibling["attack_subcase"]
            mine = set(document["not_applicable"]["arms"])
            theirs = set(sibling["not_applicable"]["arms"])
            assert mine == theirs, document["scenario_id"]
            assert mine <= set(matrix_grouping.ARMS)

    def test_every_element_lies_inside_the_frozen_omega(self):
        omega = _omega()
        for directory in (PILOT_DIR, CONFIRMATORY_DIR):
            for document in _sealed(directory).values():
                for row in document["R"]:
                    assert tuple(row) in omega, (document["scenario_id"], row)
                for row in document["tau_gt"]:
                    assert tuple(row) in omega, (document["scenario_id"], row)
                for chain in document["C_sets"]:
                    for row in chain:
                        assert tuple(row) in omega, (document["scenario_id"], row)

    def test_the_instances_actually_differ(self):
        """The other half of the constraint: matched is not the same as equal."""
        pilot = _sealed(PILOT_DIR)
        varied = []
        unvaried = []
        for document in _sealed(CONFIRMATORY_DIR).values():
            sibling = pilot[document["matched_pilot_sibling"]]
            # The (action, resource) PAIR is what an instance is, so that is
            # what must move -- `F1:terminal` keeps `calendar.read` and changes
            # the resource, which is as much a different instance as a changed
            # action would be.
            mine = {tuple(row) for row in document["R"]}
            theirs = {tuple(row) for row in sibling["R"]}
            (varied if mine != theirs else unvaried).append(document["scenario_id"])
            assert document["intended_request_digest"] != sibling["intended_request_digest"], (
                document["scenario_id"],
                "the arguments are byte-identical to the pilot sibling's",
            )
        # `mail.send`/`mail/outbox` is the WHOLE derived egress set over the
        # frozen Omega, so the two F4 instances cannot vary their element
        # without ceasing to be F4 instances at all. Every other scenario does,
        # and the exception is enumerated rather than counted loosely.
        assert sorted(unvaried) == ["cf-f4-declassified", "cf-f4-sensitive-egress"]
        assert len(varied) == 11


class TestProvenance:
    def test_every_confirmatory_scenario_carries_provenance(self):
        for document in _sealed(CONFIRMATORY_DIR).values():
            provenance = document["provenance"]
            assert provenance["family_properties"], document["scenario_id"]
            assert provenance["verification"], document["scenario_id"]

    def test_no_provenance_claims_a_paper_defines_the_families(self):
        """No paper defines F1-F5; they are this study's operationalisation of
        TV23, and each instantiates a published property."""
        blob = json.dumps(_sealed(CONFIRMATORY_DIR), ensure_ascii=False)
        for forbidden in ("defines F1", "defines the families", "taken from"):
            assert forbidden not in blob

    def test_the_agentrfc_facts_are_stated_correctly_or_not_at_all(self):
        corpus = (CONFIRMATORY_DIR / "corpus.json").read_text(encoding="utf-8")
        assert "P1-P11" not in corpus and "P1–P11" not in corpus
        assert "P1-P8" in corpus
        assert "NOT_SPECIFIED" in corpus
        assert "MCP -> A2A" in corpus and "A2A -> MCP" in corpus
        assert "PREPRINT" in corpus

    def test_the_unverifiable_anchor_was_dropped_rather_than_reached_for(self):
        """Denning's lattice model reached this project through a secondary
        reference list; the primary could not be opened, so no content claim
        rests on it."""
        blob = json.dumps(_sealed(CONFIRMATORY_DIR), ensure_ascii=False)
        assert "Denning" in blob
        assert "is NOT cited" in blob


class TestRunModeThreading:
    """STEP 3: both sites, and both directions."""

    def test_a_default_runner_still_emits_pilot(self):
        from src.harness.runner import GoldenThreadRunner

        runner = GoldenThreadRunner()
        assert runner.run_mode == "pilot"
        setup = runner.b3_setup(access_token="t", as_public_jwk={"kty": "OKP"})
        assert setup["run_mode"] == "pilot"

    def test_a_confirmatory_runner_emits_confirmatory_at_both_sites(self):
        from src.harness.runner import GoldenThreadRunner

        runner = GoldenThreadRunner(run_mode="confirmatory")
        b3 = runner.b3_setup(access_token="t", as_public_jwk={"kty": "OKP"})
        # `scenario_id` is required because the corpus carries two distinct
        # task grants and `task_grant` fails closed rather than picking one --
        # pre-existing behaviour, unrelated to `run_mode`.
        b2 = runner.b2_setup(
            access_token="t",
            as_public_jwk={"kty": "OKP"},
            as_port=1,
            as_tls_cert_pem="pem",
            scenario_id="gt-benign",
        )
        assert b3["run_mode"] == "confirmatory"
        assert b2["run_mode"] == "confirmatory"

    def test_an_unknown_run_mode_fails_closed(self):
        from src.harness.runner import GoldenThreadRunner, RunnerError

        with pytest.raises(RunnerError, match="unknown run_mode"):
            GoldenThreadRunner(run_mode="rehearsal")
