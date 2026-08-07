"""The sealed environment must be ONE environment.

`uv.lock` is a universal resolve, so an interpreter pin decides which versions
it hands you. The Dockerfile pinned 3.11 while `frozen_parameters` row 9 -- the
sealed measurement platform, READ off the machine rather than chosen -- records
Python 3.13.5. Two sealed artifacts disagreeing about the interpreter meant
"the pinned environment" was two environments, resolving different numpy/scipy
versions (ADR 0044).

A reproduction container that cannot be built from a working tree, or that
builds a different environment than the one measured, is not a reproduction.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))


def _sealed_python() -> str:
    """The interpreter row 9 records, as major.minor."""
    from src.harness import frozen_parameters

    platform = frozen_parameters.sealed_measurement_platform()
    match = re.search(r"Python (\d+)\.(\d+)", platform)
    if match is None:  # the row records it in docs/measurement_platform.md
        text = (REPO_ROOT / "docs" / "measurement_platform.md").read_text(encoding="utf-8")
        match = re.search(r"`(\d+)\.(\d+)\.\d+`", text[text.index("| Python") :])
    assert match is not None, "row 9 records no interpreter version"
    return f"{match.group(1)}.{match.group(2)}"


class TestTheInterpreterIsTheSealedOne:
    def test_the_dockerfile_pins_the_sealed_interpreter(self):
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        pinned = re.search(r"FROM python:(\d+\.\d+)", dockerfile)
        assert pinned is not None
        assert pinned.group(1) == _sealed_python(), (
            "the reproduction container builds a different interpreter than the one the "
            "campaign is measured on; uv.lock resolves differently for each"
        )

    def test_ci_runs_the_sealed_interpreter(self):
        """CI is never adjudicative (row 2), but it should protect the version
        the campaign runs on rather than a different one."""
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        pinned = re.search(r'python-version:\s*"(\d+\.\d+)"', workflow)
        assert pinned is not None
        assert pinned.group(1) == _sealed_python()


class TestEveryDeclaredDependencyIsImported:
    """An unused dependency in a sealed environment is a claim the seal cannot
    support -- and numpy/scipy/pyyaml were also the sole cause of the split
    resolution above."""

    SEARCH_ROOTS = ("src", "analysis", "fixtures", "tests", "smoke", "tools")
    # Import name where it differs from the distribution name.
    IMPORT_NAMES = {"biscuit-python": "biscuit_auth", "mcp": "mcp", "rfc8785": "rfc8785"}

    def _declared(self) -> set[str]:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        block = text[text.index("dependencies = [") : text.index("[dependency-groups]")]
        return {
            re.split(r"[<>=!]", line.strip().strip('",'))[0].strip()
            for line in block.splitlines()
            if line.strip().startswith('"')
        }

    def _sources(self) -> str:
        chunks = []
        for root in self.SEARCH_ROOTS:
            for path in (REPO_ROOT / root).rglob("*.py"):
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        return "\n".join(chunks)

    def test_no_declared_dependency_is_imported_nowhere(self):
        sources = self._sources()
        unused = []
        for name in sorted(self._declared()):
            module = self.IMPORT_NAMES.get(name, name.replace("-", "_"))
            if not re.search(rf"^\s*(import|from)\s+{re.escape(module)}\b", sources, re.M):
                unused.append(name)
        assert unused == [], (
            f"declared but imported nowhere: {unused}. An unused pin in a sealed "
            "environment is a claim the seal cannot support."
        )

    def test_the_three_removed_ones_stay_removed(self):
        declared = self._declared()
        for name in ("numpy", "scipy", "pyyaml"):
            assert name not in declared, (
                f"{name} was removed in ADR 0044: it was imported nowhere and split the "
                "lock resolution between 3.11 and the sealed 3.13"
            )


class TestTheDockerContextExcludesTheHostVirtualenv:
    def test_a_dockerignore_exists_and_excludes_the_venv(self):
        path = REPO_ROOT / ".dockerignore"
        assert path.is_file(), (
            "without one, `COPY . .` copies the host's WINDOWS .venv over the Linux "
            "environment `uv sync` just built, and ENV PATH points at nothing"
        )
        ignored = path.read_text(encoding="utf-8")
        for entry in (".venv/", "results/", ".git/"):
            assert entry in ignored, entry

    def test_the_dockerfile_still_copies_after_sync(self):
        """The ordering is deliberate (layer caching); the .dockerignore is
        what makes it safe, so this pins the shape the fix assumes."""
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert dockerfile.index("uv sync") < dockerfile.index("COPY . .")
