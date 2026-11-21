"""Explicit supplementary profiles; historical arms are imported unchanged."""

import json
from base64 import urlsafe_b64decode
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.sut.baselines.b2_dpop import B2ExchangeTaskDPoPArm
from src.sut.capability.digests import access_token_hash, h_jcs
from src.sut.capability.signer import sign_wire, signing_input

TAG = b"CLAMP-OAUTH-CALL-v1"


class BoundOAuthArm(B2ExchangeTaskDPoPArm):
    """DPoP plus an exact-call signature by the same token-bound holder."""

    name = "OAuth-DPoP-call"

    def provision(self, setup):
        super().provision(setup)
        raw = setup["dpop_private_jwk"]["d"]
        self._call_key = Ed25519PrivateKey.from_private_bytes(
            urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        )

    def present(self, credentials, invocation):
        result = super().present(credentials, invocation)
        if self._staged.access_token is None:
            return result
        self._call_payload = {
            "schema_version": 1,
            "token": access_token_hash(self._staged.access_token),
            "task": invocation.task_id,
            "audience": invocation.audience,
            "method": invocation.method,
            "tool": invocation.tool,
            "arguments": h_jcs(dict(invocation.arguments)),
        }
        assertion = sign_wire(TAG, self._call_payload, self._call_key)
        self._call_signature = json.loads(assertion)["signature"]
        return dict(result, call_assertion=assertion)

    def decide(self, tool, arguments):
        allowed, reason = super().decide(tool, arguments)
        if not allowed:
            return allowed, reason
        payload = dict(
            self._call_payload,
            token=access_token_hash(self._staged.access_token),
            task=self._staged.task_id,
            audience=self._staged.audience,
            tool=tool,
            arguments=h_jcs(dict(arguments)),
        )
        signature = urlsafe_b64decode(self._call_signature + "=" * (-len(self._call_signature) % 4))
        try:
            self._call_key.public_key().verify(signature, signing_input(TAG, payload))
        except InvalidSignature:
            return False, "oauth_call_binding"
        return True, reason


@dataclass(frozen=True)
class TaskStatus:
    """Trusted administrative snapshot, shared by both delegation profiles."""

    updated_at: int
    revoked_tasks: frozenset[str] = frozenset()
    max_age: int = 30

    def decide(self, task_id, now):
        if not 0 <= now - self.updated_at <= self.max_age:
            return False, "status_stale"
        if task_id in self.revoked_tasks:
            return False, "task_revoked"
        return True, "status_current"


@dataclass
class StatusGate:
    """Task handle is pinned by the server when the grant is provisioned."""

    arm: object
    task_id: str
    snapshot: TaskStatus
    now: int

    def decide(self, tool, arguments):
        allowed, reason = self.snapshot.decide(self.task_id, self.now)
        return self.arm.decide(tool, arguments) if allowed else (False, reason)
