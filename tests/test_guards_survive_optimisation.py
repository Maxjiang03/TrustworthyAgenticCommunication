"""Guards that must not evaporate, and failures that must not be invisible.

Two habits this repository already has, applied where they were missing:

* a check that only exists as `assert` is not a check under `python -O`, and
  domain separation is the property that stops one digest being reinterpreted
  as another;
* a swallowed failure is only safe if something still records that it
  happened.

ADR 0044.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from src.harness.verifier import at_digest  # noqa: E402


class TestDomainSeparationSurvivesDashO:
    def test_the_guard_raises_rather_than_asserts(self):
        source = (REPO_ROOT / "src" / "harness" / "verifier" / "at_digest.py").read_text(
            encoding="utf-8"
        )
        assert "assert TAG not in _TAGS_IN_USE" not in source
        assert "def _check_domain_separation" in source

    def test_a_collision_is_refused(self):
        original = at_digest._TAGS_IN_USE
        try:
            at_digest._TAGS_IN_USE = original + (at_digest.TAG,)
            with pytest.raises(at_digest.AccessTokenDigestError):
                at_digest._check_domain_separation()
        finally:
            at_digest._TAGS_IN_USE = original

    def test_the_guard_still_fires_under_python_dash_o(self):
        """The whole point: `-O` strips `assert`, and this check must not be
        strippable. Run in a subprocess because -O is an interpreter flag."""
        code = (
            "from src.harness.verifier import at_digest as m\n"
            "m._TAGS_IN_USE = m._TAGS_IN_USE + (m.TAG,)\n"
            "try:\n"
            "    m._check_domain_separation()\n"
            "    print('NOT REFUSED')\n"
            "except m.AccessTokenDigestError:\n"
            "    print('REFUSED')\n"
        )
        result = subprocess.run(
            [sys.executable, "-O", "-c", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        assert "REFUSED" in result.stdout, result.stdout + result.stderr

    def test_every_tag_in_service_is_distinct(self):
        tags = at_digest._TAGS_IN_USE + (at_digest.TAG,)
        assert len(set(tags)) == len(tags)


class TestASwallowedAuditFailureIsRecorded:
    """The verdict must NOT change -- an arm that blocked because its own sink
    failed would be measuring the sink -- but the failure must leave a trace."""

    SITES = (
        "src/sut/baselines/b1.py",
        "src/sut/baselines/b2_exchange_task.py",
        "src/sut/authz/capability_path.py",
    )

    @pytest.mark.parametrize("site", SITES)
    def test_the_handler_records_rather_than_passes(self, site):
        source = (REPO_ROOT / site).read_text(encoding="utf-8")
        assert "log loss is never a prevention outcome" in source, site
        marker = source.index("log loss is never a prevention outcome")
        handler = source[marker : marker + 700]
        assert "audit_write_failures" in handler, (
            f"{site} still swallows an audit-write failure with no record; "
            "G-12's log_integrity_failure cannot detect what nobody recorded"
        )

    def test_a_failing_audit_sink_does_not_change_the_verdict(self):
        """The rationale, kept: the arm answers the same way either way."""
        from src.sut.baselines.b1 import B1Arm

        arm = B1Arm()
        arm.provision({"api_key_id": "k", "api_key_secret": "s"})
        arm.present({"api_key_id": "k", "api_key_secret": "s"}, None)
        clean, _ = arm.decide("notes.write", {})

        class _Exploding(list):
            def append(self, _item):
                raise OSError("the sink is gone")

        arm.audit_log = _Exploding()
        with_failure, _ = arm.decide("notes.write", {})

        assert with_failure == clean, "a log failure changed the verdict"
        assert getattr(arm, "audit_write_failures", 0) >= 1, "the failure left no trace"
