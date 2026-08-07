"""A Datalog execution-limit breach must never be recorded as a denial.

ADR 0038's Sighting D, root cause. `biscuit-python`'s authorizer carries
default limits, and one of them is a **wall-clock** budget:

    max_facts = 1000, max_iterations = 100, max_time = 1 millisecond

Exceeding any of them raises `AuthorizationError("Reached Datalog execution
limits")` -- the same exception class a genuine policy denial raises. Both
`authorize_candidate` (harness/oracle side) and `permits`
(SUT side) caught that class and returned **False**, so a run that ran out of
time was indistinguishable from a run that was refused on the merits.

Why that is a measurement defect and not a flaky test: `Allowed(P_i; Γ, κ, Ω)`
runs the authorizer **once per candidate element** of `Ω`, for every hop, arm
and scenario. A timeout therefore silently drops an element from an authority
set, and authorization-scope amplification is a function of exactly those
sets -- computed smaller than it is, in the direction that makes a capability
arm look more restrictive than it is.

A verdict that depends on machine load is not a measurement. ADR 0046.
"""

import datetime
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))

from biscuit_auth import AuthorizerBuilder, KeyPair  # noqa: E402

from src.harness.authorizer import allowed as ev  # noqa: E402
from src.harness.authorizer import frozen_config  # noqa: E402
from src.sut.capability import authority as sut_authority  # noqa: E402

NOW = datetime.datetime(2026, 7, 29, 12, 0, tzinfo=datetime.timezone.utc)
EXPIRY = datetime.datetime(2027, 1, 1, tzinfo=datetime.timezone.utc)
AUDIENCE = "mcp-boundary"
TASK = "task-g2-pilot"
U_TASK = [("notes.write", "notes/project"), ("calendar.read", "calendar/work")]


@pytest.fixture
def doc():
    return frozen_config.load_document()


@pytest.fixture
def keypair():
    return KeyPair()


@pytest.fixture
def chain(doc, keypair):
    return ev.build_chain(
        doc,
        keypair.private_key,
        keypair.public_key,
        U_TASK,
        [U_TASK],
        audience=AUDIENCE,
        task=TASK,
        expiry=EXPIRY,
    )


@pytest.fixture
def context():
    return ev.RequestContext(now=NOW, audience=AUDIENCE, task=TASK)


class TestTheLibraryDefaultIsAWallClockBudget:
    """Pinned so a version bump that changes it is visible rather than silent."""

    def test_the_default_max_time_is_a_wall_clock_millisecond(self):
        limits = AuthorizerBuilder("allow if true;").limits()
        assert isinstance(limits.max_time, datetime.timedelta)
        assert limits.max_time <= datetime.timedelta(milliseconds=1), (
            "the default budget is wall clock; a verdict computed under it depends on machine load"
        )

    def test_the_harness_sets_its_own_limits_rather_than_inheriting(self):
        source = (REPO_ROOT / "src" / "harness" / "authorizer" / "allowed.py").read_text(
            encoding="utf-8"
        )
        assert "set_limits" in source, "the authorizer inherits a 1 ms wall-clock default"

    def test_the_sut_sets_its_own_limits_rather_than_inheriting(self):
        source = (REPO_ROOT / "src" / "sut" / "capability" / "authority.py").read_text(
            encoding="utf-8"
        )
        assert "set_limits" in source, "the authorizer inherits a 1 ms wall-clock default"


class TestALimitsBreachIsNeverADenial:
    """Both implementations, independently (D13/D21)."""

    def test_the_harness_raises_rather_than_denying(
        self, chain, doc, context, keypair, monkeypatch
    ):
        gamma = frozen_config.gamma(doc)
        monkeypatch.setattr(ev, "AUTHORIZER_MAX_TIME", datetime.timedelta(0))

        with pytest.raises(ev.AuthorizerExhausted) as caught:
            ev.authorize_candidate(chain.prefix(0), keypair.public_key, gamma, U_TASK[0], context)
        assert "limit" in str(caught.value).lower()

    def test_the_sut_raises_rather_than_denying(self, chain, doc, keypair, monkeypatch):
        monkeypatch.setattr(sut_authority, "AUTHORIZER_MAX_TIME", datetime.timedelta(0))

        with pytest.raises(sut_authority.AuthorizerExhausted):
            sut_authority.permits(
                chain.prefix(0),
                keypair.public_key,
                doc,
                U_TASK[0],
                now_epoch=int(NOW.timestamp()),
                audience=AUDIENCE,
                task_id=TASK,
            )

    def test_a_genuine_denial_is_still_a_denial_on_both_sides(self, chain, doc, context, keypair):
        """The repair must not turn every refusal into an exception."""
        outside = ("mail.send", "mail/outbox")
        gamma = frozen_config.gamma(doc)

        permitted, why = ev.authorize_candidate(
            chain.prefix(0), keypair.public_key, gamma, outside, context
        )
        assert permitted is False
        assert "limit" not in why.lower(), "a policy denial must not read as a limits breach"

        assert (
            sut_authority.permits(
                chain.prefix(0),
                keypair.public_key,
                doc,
                outside,
                now_epoch=int(NOW.timestamp()),
                audience=AUDIENCE,
                task_id=TASK,
            )
            is False
        )

    def test_a_granted_element_still_authorizes_on_both_sides(self, chain, doc, context, keypair):
        permitted, _ = ev.authorize_candidate(
            chain.prefix(0), keypair.public_key, gamma_of(doc), U_TASK[0], context
        )
        assert permitted is True
        assert (
            sut_authority.permits(
                chain.prefix(0),
                keypair.public_key,
                doc,
                U_TASK[0],
                now_epoch=int(NOW.timestamp()),
                audience=AUDIENCE,
                task_id=TASK,
            )
            is True
        )


def gamma_of(doc):
    return frozen_config.gamma(doc)


class TestTheBudgetIsGenerousEnoughToBeMeaningful:
    def test_the_configured_budget_is_orders_above_the_observed_cost(self):
        """A breach must mean a runaway evaluation, not a GC pause."""
        assert ev.AUTHORIZER_MAX_TIME >= datetime.timedelta(milliseconds=500)
        assert sut_authority.AUTHORIZER_MAX_TIME >= datetime.timedelta(milliseconds=500)

    def test_both_sides_agree_on_the_budget(self):
        """They are independent implementations, but a DIFFERENT budget would
        make one side's authority set depend on a limit the other does not
        share -- an apparatus difference reported as a mechanism difference."""
        assert ev.AUTHORIZER_MAX_TIME == sut_authority.AUTHORIZER_MAX_TIME


class TestAnExhaustedAuthorizerIsUnscorableNotAVerdict:
    """The second half of the repair, and the half that protects the matrix.

    Raising is not enough on its own: the mediation boundary converts ANY arm
    exception into a denial (fail closed, and correct for a genuine arm
    failure), so an exhausted authorizer would have re-entered the matrix as a
    `B` -- reading as the arm refusing when the instrument merely failed to
    finish. It now propagates through the boundary and the campaign records the
    cell UNSCORABLE with its cause, exactly as the wall-clock straddle is.
    """

    def test_the_boundary_re_raises_rather_than_recording_a_denial(self):
        import ast

        source = (REPO_ROOT / "src" / "harness" / "runner.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        handlers = [
            handler
            for node in ast.walk(tree)
            if isinstance(node, ast.Try)
            for handler in node.handlers
            if "AuthorizerExhausted" in ast.dump(handler)
        ]
        assert handlers, "the boundary does not mention AuthorizerExhausted at all"
        for handler in handlers:
            assert any(isinstance(stmt, ast.Raise) for stmt in handler.body), (
                "the boundary swallows an exhausted authorizer into a verdict"
            )

    def test_the_campaign_records_it_unscorable(self):
        import ast

        source = (REPO_ROOT / "src" / "harness" / "campaign.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        handlers = [
            handler
            for node in ast.walk(tree)
            if isinstance(node, ast.Try)
            for handler in node.handlers
            if "AuthorizerExhausted" in ast.dump(handler)
        ]
        assert handlers, "the campaign has no handler for an exhausted authorizer"
        for handler in handlers:
            rendered = ast.dump(handler)
            assert "unscorable" in rendered, "an exhausted authorizer must not be scored"

    def test_both_exhaustion_types_are_known_to_the_boundary(self):
        """Two independent implementations (D13/D21) means two exception types,
        and missing either would leave that side silently scored."""
        from src.harness import campaign as C
        from src.harness import runner as R

        for module in (R, C):
            names = {
                "SutAuthorizerExhausted": getattr(module, "SutAuthorizerExhausted", None),
                "HarnessAuthorizerExhausted": getattr(module, "HarnessAuthorizerExhausted", None),
            }
            assert all(value is not None for value in names.values()), (module.__name__, names)
        assert R.SutAuthorizerExhausted is sut_authority.AuthorizerExhausted
        assert R.HarnessAuthorizerExhausted is ev.AuthorizerExhausted
