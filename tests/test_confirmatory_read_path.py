"""The confirmatory corpus must be READABLE, and behind the same wall.

ADR 0043 found the sealed generator could not PRODUCE this corpus. Task A1
parameterised the generator and produced it -- and nothing extended the
consumers. `sealed_truth.SEALED_DIRS` still mapped one corpus, the pilot one,
and `runner.run_scenario` called `load_sealed(scenario_id)` with no corpus
argument and no way to pass one, so the first confirmatory cell raised
`SealedTruthAccessError` -- which is not a `RunnerError`, so `run_campaign`'s
handler did not catch it and the whole campaign died on cell one.

The quieter half: `campaign._sealed_document` read the corpus JSON directly,
bypassing `_refuse_sut_frames()`, so the runtime half of the sealed-truth wall
(red line 5) never covered the confirmatory corpus at all.

ADR 0044. Watched failing before it was kept.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))

import types  # noqa: E402

from src.harness import sealed_truth  # noqa: E402

CONFIRMATORY_SEALED = REPO_ROOT / "fixtures" / "confirmatory" / "sealed"


class TestTheConfirmatoryCorpusIsReadable:
    def test_every_confirmatory_scenario_loads(self):
        scenarios = sorted(p.stem for p in CONFIRMATORY_SEALED.glob("*.json"))
        assert scenarios, "fixture precondition: the confirmatory corpus exists"

        for scenario_id in scenarios:
            document = sealed_truth.load_sealed(scenario_id, corpus="confirmatory")
            assert document["scenario_id"] == scenario_id

    def test_the_two_corpora_are_separate_namespaces(self):
        """A `cf-*` id must not resolve under the pilot corpus, and vice versa:
        a campaign that silently fell back to the pilot corpus would adjudicate
        confirmatory arms against pilot ground truth."""
        with pytest.raises(sealed_truth.SealedTruthAccessError):
            sealed_truth.load_sealed("cf-benign", corpus="golden_thread")
        with pytest.raises(sealed_truth.SealedTruthAccessError):
            sealed_truth.load_sealed("gt-benign", corpus="confirmatory")

    def test_a_corpus_nobody_registered_still_fails_closed(self):
        with pytest.raises(sealed_truth.SealedTruthAccessError):
            sealed_truth.load_sealed("cf-benign", corpus="held-out")

    def test_tau_gt_is_present_in_the_confirmatory_records(self):
        document = sealed_truth.load_sealed("cf-benign", corpus="confirmatory")
        assert document["tau_gt"], "the oracle-only ground truth must be carried"


class TestTheWallCoversBothCorpora:
    """Red line 5 is about the CORPUS, not about one directory."""

    @staticmethod
    def _sut_module() -> types.ModuleType:
        module = types.ModuleType("src.sut.agents.rogue")
        source = (
            "from src.harness import sealed_truth\n"
            "def grab(scenario_id, corpus):\n"
            "    return sealed_truth.load_sealed(scenario_id, corpus=corpus)\n"
        )
        exec(compile(source, "<src.sut.agents.rogue>", "exec"), module.__dict__)
        return module

    def test_a_sut_module_cannot_read_confirmatory_sealed_truth(self):
        with pytest.raises(sealed_truth.SealedTruthAccessError):
            self._sut_module().grab("cf-benign", "confirmatory")

    def test_the_campaign_reads_sealed_truth_through_the_wall(self):
        """Structural: `campaign._sealed_document` must not open the file
        itself. A direct `json.loads(path.read_text())` reaches sealed truth
        without passing the SUT-frame tripwire, which is the whole mechanism
        of the wall."""
        import ast

        source = (REPO_ROOT / "src" / "harness" / "campaign.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        reader = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_sealed_document"
        )
        calls = {
            getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            for node in ast.walk(reader)
            if isinstance(node, ast.Call)
        }
        assert "load_sealed" in calls, (
            "_sealed_document opens the sealed file directly, so a SUT frame on the stack "
            "would not be refused: the confirmatory corpus sits outside the wall"
        )


class TestTheRunnerReadsTheCorpusItWasGiven:
    def test_the_runner_resolves_its_corpus_from_its_directory(self):
        from src.harness import runner as runner_mod

        assert runner_mod.corpus_key_for(REPO_ROOT / "fixtures" / "confirmatory") == "confirmatory"
        assert (
            runner_mod.corpus_key_for(REPO_ROOT / "fixtures" / "pilot" / "golden_thread")
            == "golden_thread"
        )

    def test_an_unregistered_corpus_directory_fails_closed(self):
        from src.harness import runner as runner_mod

        with pytest.raises(sealed_truth.SealedTruthAccessError):
            runner_mod.corpus_key_for(REPO_ROOT / "fixtures" / "somewhere-else")

    def test_run_scenario_passes_the_corpus_to_the_wall(self):
        """Structural: the `load_sealed` call in `run_scenario` names a corpus.

        Behavioural coverage needs a live AS and a ledger; this asserts the
        wiring that the campaign's first cell depends on, which is what was
        missing.
        """
        import ast

        source = (REPO_ROOT / "src" / "harness" / "runner.py").read_text(encoding="utf-8")
        calls = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "load_sealed"
        ]
        assert calls, "run_scenario no longer reads sealed truth at all"
        for call in calls:
            assert "corpus" in {kw.arg for kw in call.keywords}, (
                "load_sealed(scenario_id) defaults to the PILOT corpus, so a confirmatory "
                "run either dies on the first cell or reads pilot ground truth"
            )
