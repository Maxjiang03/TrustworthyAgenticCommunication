"""The sealed-truth wall: `tau_gt` and every sealed object live behind this accessor.

PROJECT_RULES.md red line 5 / SS A.3: `tau_gt` is oracle-only; **no system-under-test
principal may read it**. Two mechanisms enforce that, layered:

1. **Structural** (the guarantee): `src/sut/` must never import `src/harness/`
   (red line 6, asserted by the AST red-line suite), and this accessor is the
   only reader of `fixtures/pilot/**/sealed/`. SUT modules receive scenario
   material exclusively as the SUT-visible document, injected by the runner.
2. **Runtime** (defense in depth): every accessor call walks the interpreter
   stack and refuses if ANY frame belongs to a `src.sut.*` module -- so even a
   hypothetical harness helper invoked from SUT code cannot launder sealed
   truth through itself. `tests/test_sealed_truth_wall.py` proves the refusal
   fires and that the same call succeeds from harness/test context.

The runtime guard is a tripwire, not the security boundary: a determined
in-process reader could bypass `inspect` (the G-7/G-12 residual about
in-process reachability applies here too, excluded architecturally by SUT
process separation in the campaign). What it guarantees in THIS apparatus is
that no accidental call path from SUT code can ever return sealed truth.
"""

import inspect
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
# One entry per corpus, and an unregistered name fails closed. The confirmatory
# corpus was missing here until ADR 0044: it had been GENERATED (ADR 0043) and
# was still unreadable, so `run_scenario` -- which called `load_sealed` with no
# corpus argument -- raised on the first confirmatory cell, and
# `SealedTruthAccessError` is not a `RunnerError`, so `run_campaign` did not
# catch it. The allowlist stays an allowlist: a corpus is reachable because it
# is named here, never because a path was assembled from a caller's string.
SEALED_DIRS = {
    "golden_thread": REPO_ROOT / "fixtures" / "pilot" / "golden_thread" / "sealed",
    "confirmatory": REPO_ROOT / "fixtures" / "confirmatory" / "sealed",
}
# `corpus_dir` -> the key above, so a runner holding a directory can name its
# corpus without either restating the mapping or building a path itself.
CORPUS_KEYS = {directory.parent: key for key, directory in SEALED_DIRS.items()}


class SealedTruthAccessError(Exception):
    """A SUT principal reached for sealed truth. Always an error, never a warning."""


def _refuse_sut_frames() -> None:
    for frame_info in inspect.stack():
        module = frame_info.frame.f_globals.get("__name__", "")
        if module == "src.sut" or module.startswith("src.sut."):
            raise SealedTruthAccessError(
                f"sealed truth requested from SUT module {module!r} "
                "(CLAUDE.md red line 5; SS A.3: tau_gt is oracle-only)"
            )


def corpus_key(corpus_dir: Path) -> str:
    """The registered corpus name for a corpus directory. Fails closed.

    A runner is constructed with a directory, and the wall is keyed by name;
    this is the only bridge between the two, so no caller ever assembles a
    sealed path of its own.
    """
    key = CORPUS_KEYS.get(Path(corpus_dir).resolve())
    if key is None:
        raise SealedTruthAccessError(
            f"no sealed corpus is registered for {corpus_dir}; "
            f"registered corpora are {sorted(SEALED_DIRS)}"
        )
    return key


def load_sealed(scenario_id: str, *, corpus: str = "golden_thread") -> dict[str, Any]:
    """The harness-only read path for one scenario's sealed-truth document."""
    _refuse_sut_frames()
    directory = SEALED_DIRS.get(corpus)
    if directory is None:
        raise SealedTruthAccessError(f"unknown corpus {corpus!r}")
    path = directory / f"{scenario_id}.json"
    if not path.is_file():
        raise SealedTruthAccessError(f"no sealed document for scenario {scenario_id!r}")
    return json.loads(path.read_text(encoding="utf-8"))
