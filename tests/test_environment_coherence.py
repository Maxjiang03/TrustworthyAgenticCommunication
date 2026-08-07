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


class TestTheConsoleDecodingOfPlatformQueries:
    """DEVIATIONS D-007. The sealed platform reader shells out to PowerShell for
    facts that row 9 seals, and what encoding comes back depends on the PARENT
    process: GBK under a `bash`/`cmd` parent, UTF-8 under a PowerShell one.

    The second instance of a defect class already paid for once -- `smoke/g10/`
    was fixed for it a seal earlier. The shape of the fix matters as much as the
    fix: a FIXED encoding repairs one parent and silently corrupts the other,
    and a corrupted row 9 field is worse than an unread one.
    """

    def test_utf8_console_bytes_decode(self):
        from src.harness.measurement_platform import _decode_console

        assert _decode_console("高性能".encode("utf-8")) == "高性能"

    def test_locale_codepage_bytes_decode_when_they_are_not_utf8(self):
        """The `bash`-parent case on the row 9 platform: cp936 bytes, which are
        NOT valid UTF-8. Derived from this machine's codepage at test time so
        the test states a contract rather than hard-coding cp936."""
        import locale

        from src.harness.measurement_platform import _decode_console

        codec = locale.getencoding()
        try:
            raw = "高性能".encode(codec)
        except UnicodeEncodeError:  # pragma: no cover - a codepage without CJK
            return
        if raw == "高性能".encode("utf-8"):  # pragma: no cover - a UTF-8 locale
            return
        assert _decode_console(raw) == "高性能"
        assert "\ufffd" not in _decode_console(raw)

    def test_undecodable_bytes_are_REFUSED_rather_than_replaced(self):
        """Fail closed. `errors="replace"` here would write mojibake into a
        sealed platform fact, which no later reader could distinguish from a
        machine that really is named that."""
        import pytest

        from src.harness.measurement_platform import PlatformError, _decode_console

        with pytest.raises(PlatformError, match="guessed decoding"):
            _decode_console(b"\xff\xfe\xff\xfe scheme")

    def test_the_literal_fixed_encoding_would_have_corrupted_the_bash_parent(self):
        """The rejected alternative, pinned so nobody re-applies it. This is why
        `_decode_console` tries codecs strictly instead of fixing one."""
        import locale

        codec = locale.getencoding()
        try:
            raw = "高性能".encode(codec)
        except UnicodeEncodeError:  # pragma: no cover
            return
        if raw == "高性能".encode("utf-8"):  # pragma: no cover - a UTF-8 locale
            return
        corrupted = raw.decode("utf-8", errors="replace")
        assert "\ufffd" in corrupted and "高性能" not in corrupted

    def test_powershell_captures_bytes_and_never_asks_subprocess_to_decode(self):
        """Structural, so a future edit that reinstates `text=True` or pins an
        encoding on the subprocess call is a test failure and not a surprise on
        someone else's machine."""
        import ast

        source = (REPO_ROOT / "src" / "harness" / "measurement_platform.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_powershell"
        )
        calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
        ]
        assert len(calls) == 1, "expected exactly one subprocess.run in _powershell"
        keywords = {keyword.arg for keyword in calls[0].keywords}
        assert "text" not in keywords, "text=True makes subprocess guess the codec again"
        assert "encoding" not in keywords, "a fixed encoding corrupts one of the two parents"
        assert "capture_output" in keywords
