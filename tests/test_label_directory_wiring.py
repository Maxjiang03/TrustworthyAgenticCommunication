"""The ingestion label directory must actually be attached to the ledger.

`LabelDirectory` was built, tested and documented -- and never constructed
anywhere in `src/`. Both wiring points (`LedgerEffector` and
`install_ingress_recorder`) default to `label_directory.EMPTY`, so every
`EffectEvent` carried `data_labels_touched = []`, and `realized_harm_F4` --
whose body iterates that list -- could never be True. A sensitive egress that
actually executed was scored as no harm, which is verbatim the outcome ADR 0030
and `label_directory.py`'s own docstring say must never happen.

ADR 0044. Watched failing before it was kept.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))

import json  # noqa: E402

from src.harness import runner as runner_mod  # noqa: E402
from src.harness.policy import label_directory  # noqa: E402

PILOT = REPO_ROOT / "fixtures" / "pilot" / "golden_thread" / "sut_visible"
CONFIRMATORY = REPO_ROOT / "fixtures" / "confirmatory" / "sut_visible"


def _visible(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestTheRunnerBuildsADirectoryFromTheScenario:
    def test_a_scenario_with_labelled_values_yields_a_populated_directory(self):
        visible = _visible(CONFIRMATORY / "cf-f4-sensitive-egress.json")
        assert visible.get("labelled_values"), "fixture precondition: the scenario labels a value"

        directory = runner_mod.ingestion_directory(visible)

        assert len(directory) == len(visible["labelled_values"]), (
            "the ledger would record data_labels_touched = [] and realized_harm_F4 "
            "could never be True for the very attack it exists to catch"
        )

    def test_the_directory_resolves_the_value_by_its_bytes(self):
        visible = _visible(CONFIRMATORY / "cf-f4-sensitive-egress.json")
        entry = visible["labelled_values"][0]
        directory = runner_mod.ingestion_directory(visible)

        found = directory.lookup(entry["value"])
        assert found is not None, "the labelled value must resolve by its own bytes"
        assert found.label == entry["label"]
        assert found.value_id == entry["value_id"]

    def test_an_unlabelled_value_is_unknown_not_an_error(self):
        visible = _visible(CONFIRMATORY / "cf-f4-sensitive-egress.json")
        directory = runner_mod.ingestion_directory(visible)
        assert directory.lookup("a string nobody ever labelled") is None

    def test_a_scenario_with_no_labelled_values_yields_an_empty_directory(self):
        visible = _visible(PILOT / "gt-benign.json")
        assert not visible.get("labelled_values")
        assert len(runner_mod.ingestion_directory(visible)) == 0

    def test_both_corpora_are_covered_by_the_same_construction(self):
        """The pilot and confirmatory F4 scenarios must both populate; a
        directory built only for one corpus is the ADR 0043 defect again."""
        for path in (
            PILOT / "gt-f4-sensitive-egress.json",
            CONFIRMATORY / "cf-f4-sensitive-egress.json",
            PILOT / "gt-f4-declassified.json",
            CONFIRMATORY / "cf-f4-declassified.json",
        ):
            visible = _visible(path)
            directory = runner_mod.ingestion_directory(visible)
            assert len(directory) == len(visible.get("labelled_values", [])) > 0, path.name


class TestTheDirectoryReachesTheLedger:
    """The construction is worthless if it is not passed to the two sinks."""

    def test_the_effector_receives_the_directory_not_the_empty_default(self):
        from src.harness.effectors import LedgerEffector

        visible = _visible(CONFIRMATORY / "cf-f4-sensitive-egress.json")
        directory = runner_mod.ingestion_directory(visible)

        class _Writer:
            def append(self, **_):
                return None

        effector = LedgerEffector(
            _Writer(),
            audience="rs.aasc.local",
            principal="specialist",
            correlation_provider=lambda: "cid",
            labels=directory,
            label_order=("public", "internal", "sensitive"),
        )
        assert effector._labels is directory
        assert effector._labels is not label_directory.EMPTY

    def test_the_runner_passes_a_label_order_from_the_frozen_policy(self):
        """Row 4's total order decides which label GOVERNS a multi-label
        effect; passing `()` would leave the governing payload unnamed."""
        order = runner_mod.frozen_label_order()
        assert order, "the label order must come from the frozen policy, never be empty"
        assert order[-1] == "sensitive", (
            "the most restrictive label must sort last under row 4's total order"
        )

    def test_the_wiring_sites_no_longer_fall_back_to_empty(self):
        """Structural: the two constructor calls in runner.py name `labels=`.

        A behavioural test alone would pass again the moment someone drops the
        argument, because the fallback is silent by design.
        """
        import ast

        source = (REPO_ROOT / "src" / "harness" / "runner.py").read_text(encoding="utf-8")
        wanted = {"LedgerEffector", "install_ingress_recorder"}
        seen: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name not in wanted:
                continue
            seen.add(name)
            passed = {kw.arg for kw in node.keywords}
            assert "labels" in passed, f"{name}(...) still falls back to label_directory.EMPTY"
            assert "label_order" in passed, (
                f"{name}(...) passes no label_order, so the GOVERNING label of a "
                "multi-label effect would be unnamed"
            )
        assert seen == wanted, f"wiring site(s) not found in runner.py: {sorted(wanted - seen)}"
