"""The seam between what the runner OBSERVES and what the oracle ADJUDICATES.

Every test here builds its input the way `src/harness/runner.py` builds it --
through the pydantic models of `src/harness/schema.py` -- and then asks the
oracle the question the campaign asks. That is the whole point:
`tests/test_oracle_predicates.py` hands the oracle plain dicts, and a plain
dict never crosses the model boundary where the corruption happened, so the
unit suite was green while the campaign would have been wrong.

ADR 0044. Each test here was watched FAILING against the unrepaired code
before it was kept; a seam test that passes on the broken seam has tested
nothing.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(REPO_ROOT))

from src.harness.oracle import artifacts as oracle_artifacts  # noqa: E402
from src.harness.policy import label_artifacts  # noqa: E402
from src.harness.schema import DeclassificationArtifact, LabelAssertion  # noqa: E402
from src.harness.verifier import label_context as lc  # noqa: E402
from src.sut.authz.reference_monitor import ContextApprovalMonitor  # noqa: E402

SEED = bytes.fromhex("a1" * 32)
NOW = 1_800_000_000
PAYLOAD_VALUE = "the payload bytes"


def _minted_declassification(**overrides):
    """One declassification, minted exactly as the harness mints it."""
    minted = label_artifacts.issue_declassification(
        SEED,
        task_id="task-seam",
        audience="rs.aasc.local",
        tool="mail.send",
        request_digest="a" * 64,
        recipient="auditor@example.test",
        value=PAYLOAD_VALUE,
        from_label="sensitive",
        to_label="public",
        policy_version="label_approval_v1",
        iat=NOW - 10,
        nbf=NOW - 10,
        exp=NOW + 600,
        jti="jti-seam-1",
    )
    return dict(minted, **overrides)


def _minted_label_assertion():
    return label_artifacts.issue_label_assertion(
        SEED, value=PAYLOAD_VALUE, label="sensitive", iat=NOW - 10, exp=NOW + 600
    )


def _payload(minted):
    return {k: v for k, v in minted.items() if k != "signature"}


def _approver_wire(minted):
    _, approvers = label_artifacts.trusted_sets(SEED)
    return approvers[minted["approver_kid"]]


def _issuer_wire(minted):
    issuers, _ = label_artifacts.trusted_sets(SEED)
    return issuers[minted["issuer_kid"]]


class TestTheSignatureSurvivesTheModel:
    """A base64url signature must not be re-encoded on its way to the oracle.

    `schema.py` declared `signature: bytes`, so pydantic encoded the
    86-character base64url TEXT to 86 ASCII bytes, and `_verify` -- seeing
    `isinstance(..., bytes)` -- handed those to Ed25519 as if they were the raw
    64-byte signature. It could never verify, for any artifact, ever.
    """

    def test_a_minted_declassification_still_verifies_after_the_model(self):
        minted = _minted_declassification()
        through_model = DeclassificationArtifact(**minted)

        assert oracle_artifacts._verify(
            lc.DECLASSIFICATION_TAG,
            _payload(minted),
            through_model.signature,
            _approver_wire(minted),
        ), (
            "a validly minted declassification failed oracle verification after passing "
            "through the model -- every F4 declassification cell would be wrong"
        )

    def test_the_model_does_not_change_the_signature(self):
        minted = _minted_declassification()
        through_model = DeclassificationArtifact(**minted)
        assert through_model.signature == minted["signature"], (
            "the model changed the signature it was given"
        )
        assert isinstance(through_model.signature, str), (
            "the signature is base64url TEXT everywhere it is minted (ADR 0030); typing the "
            "field as `bytes` makes pydantic re-encode that text, and the oracle then verifies "
            "86 ASCII bytes as if they were a 64-byte Ed25519 signature"
        )

    def test_a_label_assertion_survives_the_model_too(self):
        minted = _minted_label_assertion()
        through_model = LabelAssertion(**minted)

        assert oracle_artifacts._verify(
            lc.LABEL_ASSERTION_TAG,
            _payload(minted),
            through_model.signature,
            _issuer_wire(minted),
        )
        assert through_model.signature == minted["signature"]

    def test_the_sut_monitor_verifies_the_same_artifact_after_the_model(self):
        """The two verifiers are independent implementations (D13/D21) and are
        repaired on their own terms; both must accept a valid artifact."""
        minted = _minted_declassification()
        through_model = DeclassificationArtifact(**minted)

        assert ContextApprovalMonitor._raw_signature(through_model.signature) == (
            oracle_artifacts._raw_signature(through_model.signature)
        )

    def test_a_tampered_signature_is_still_refused_through_the_model(self):
        """The repair must not turn the verifier into a rubber stamp."""
        minted = _minted_declassification()
        good = minted["signature"]
        forged = ("B" if good[0] != "B" else "C") + good[1:]
        assert forged != good
        through_model = DeclassificationArtifact(**dict(minted, signature=forged))

        assert not oracle_artifacts._verify(
            lc.DECLASSIFICATION_TAG,
            _payload(minted),
            through_model.signature,
            _approver_wire(minted),
        )

    @pytest.mark.parametrize(
        "bad",
        ["!!!not base64!!!", "", "A" * 86, b"", b"\x00" * 64, b"short", b"\xff" * 70, None],
        ids=[
            "not-b64",
            "empty-str",
            "wrong-b64",
            "empty-bytes",
            "zero-64",
            "short",
            "hi-bytes",
            "none",
        ],
    )
    def test_a_signature_of_the_wrong_shape_is_refused_not_crashed(self, bad):
        """`_verify` answers False for anything it cannot verify, and never
        raises: an exception here would read to a caller as 'not applicable'."""
        minted = _minted_declassification()
        assert not oracle_artifacts._verify(
            lc.DECLASSIFICATION_TAG, _payload(minted), bad, _approver_wire(minted)
        )

    def test_raw_64_byte_signatures_are_still_accepted(self):
        """The `bytes` branch existed for a reason; the repair keeps a genuine
        raw signature working rather than deleting the capability."""
        minted = _minted_declassification()
        raw = oracle_artifacts._unb64u(minted["signature"])
        assert len(raw) == 64
        assert oracle_artifacts._verify(
            lc.DECLASSIFICATION_TAG, _payload(minted), raw, _approver_wire(minted)
        )


class TestTheObservationRecordsTheAttackedCredential:
    """`ObservedRequest.evidence` must record the credential as PRESENTED.

    The runner captured `arm.present(...)`'s return value and only then applied
    the credential fault to the arm's staged material, so the observation kept
    the honest token. `credential_result` then re-verified the GOOD token and
    returned `principal_verified=True`, so `realized_harm_F2` -- which is
    `(not ok) and effects` -- could never be True for an arm that admitted a
    corrupted credential and produced an effect.
    """

    @staticmethod
    def _arm_with_token(token):
        import dataclasses

        @dataclasses.dataclass(frozen=True)
        class _Staged:
            access_token: str

        class _Arm:
            name = "probe"

            def __init__(self):
                self._staged = _Staged(access_token=token)

        return _Arm()

    def test_a_corrupted_token_reaches_the_observation(self):
        from src.harness import credential_faults

        honest = "header.payload.signature"
        arm = self._arm_with_token(honest)
        presentation = {"access_token": honest}

        credential_faults.apply_to_presentation(
            "invalid_credential", arm, seed=SEED, now=NOW, wrong_audience_token=None
        )
        observed = credential_faults.observed_presentation(arm, presentation)

        assert observed["access_token"] != honest, (
            "the observation still carries the pre-attack token; the oracle would re-verify "
            "the honest credential and score realized_harm_F2 = False for an arm that "
            "admitted a corrupted one"
        )
        assert observed["access_token"] == arm._staged.access_token, (
            "the observation must be what the boundary saw, not a third version"
        )

    def test_an_emptied_token_is_recorded_as_empty_not_dropped(self):
        from src.harness import credential_faults

        arm = self._arm_with_token("header.payload.signature")
        presentation = {"access_token": "header.payload.signature"}

        credential_faults.apply_to_presentation(
            "unauthenticated_caller", arm, seed=SEED, now=NOW, wrong_audience_token=None
        )
        observed = credential_faults.observed_presentation(arm, presentation)

        assert observed["access_token"] == "", "presenting nothing IS what happened; record it"
        assert "access_token" in observed

    def test_a_clean_presentation_is_unchanged(self):
        """`fault="none"` must leave the observation byte-identical: the
        repair may not perturb the 9 arms x 11 benign scenarios it does not
        concern."""
        from src.harness import credential_faults

        honest = "header.payload.signature"
        arm = self._arm_with_token(honest)
        presentation = {"access_token": honest, "capability_hops": [b"hop"]}

        credential_faults.apply_to_presentation(
            "none", arm, seed=SEED, now=NOW, wrong_audience_token=None
        )
        observed = credential_faults.observed_presentation(arm, presentation)

        assert observed == presentation

    def test_b1s_withdrawn_api_key_leaves_the_observation(self):
        from src.harness import credential_faults

        class _Arm:
            name = "B1"
            _presented = ("key-1", "s3cret")

        arm = _Arm()
        presentation = {"api_key_id": "key-1"}
        credential_faults.apply_to_presentation(
            "unauthenticated_caller", arm, seed=SEED, now=NOW, wrong_audience_token=None
        )
        observed = credential_faults.observed_presentation(arm, presentation)

        assert "api_key_id" not in observed, (
            "B1 under unauthenticated_caller presents nothing at all; an observation that "
            "still names a key would let the oracle verify a credential never sent"
        )
