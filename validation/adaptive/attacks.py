"""The eight adaptive attacks, one per unmasked FALSIFIABLE cell of the table.

Post-seal adaptive validation apparatus (DEVIATIONS D-019, Phase B). Outside
`src/` and `analysis/`; imports the sealed arms, runner and oracle read-only and
modifies none of them.

Each attack is a **defence-aware** construction: it is built from the admission
rule itself (`src/sut/authz/capability_path.py`, Equation 3.1), targeting one
named conjunct at one of Table 3.1's five tampering points under one of the two
key-possession classes. The enumeration in
`drafts/adaptive/CONJUNCT_ENUMERATION.md` is the pre-registration; this file
instantiates exactly the cells that table marks FALSIFIABLE and unmasked, and
nothing else.

**Two attack seams, both outside the seal.**

1. `stage(...)` corrupts what the arm STAGED, after the sealed `arm.present()`
   returns. This is the seam `src/harness/runner.py:805` already exposes to
   `credential_faults`; the adaptive harness reaches it by rebinding one name
   rather than by adding a fault to the sealed module, which is inside the seal.
2. `invoke(...)` substitutes the tool or arguments BETWEEN the Specialist's call
   and the boundary. This is the position §D.2 names for
   `dpop-first-use-body-mutation`: "a malicious component between the holder's
   proof signing and the TLS client alters the body/tool on the FIRST use,
   reusing the holder's genuine, not-yet-seen proof."

**Capability classes are enforced here, not assumed.** A `K-none` attack may
never sign under `holder-specialist`'s key; only the two `K-holder` attacks
touch `holder_privates`. `ATTACKER_LABEL` derives a key that is in no registry
entry by construction.

**Nothing is weakened.** No conjunct is disabled, no arm modified, no oracle
touched. What the boundary receives is well-formed material presented by the
wrong party, or a genuine assertion carried onto a request it does not bind.
"""

import dataclasses
import json
from collections.abc import Mapping
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.harness import key_material
from src.harness.verifier.at_digest import access_token_hash
from src.harness.verifier.holder_binding import HTC_TAG, INV_TAG, seal

# A key under a label that appears in NO registry entry, by construction rather
# than by hoping -- the same device `credential_faults.ATTACKER_HOLDER_LABEL`
# uses for the sealed corpus.
ATTACKER_LABEL = "adaptive-attacker-not-in-the-registry"

# cf-benign's legitimate invocation, and the effective authority it carries.
#   C_n = {(notes.read, notes/meeting), (notes.read, notes/project)}
# read from fixtures/confirmatory/sut_visible/cf-benign.json [M].
BASE_TOOL = "notes.read"
BASE_ARGS: dict[str, Any] = {"resource": "notes/meeting"}
IN_SCOPE_RESOURCE = "notes/project"  # inside C_n
OUT_OF_SCOPE_RESOURCE = "notes/secret"  # outside C_n and outside C_0
HIGH_RISK_TOOL = "notes.delete"  # frozen high-risk (ADR 0022 row 10)


def _attacker_key(seed: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(key_material.derive_raw(seed, ATTACKER_LABEL))


def _holder_key(arm: Any) -> Ed25519PrivateKey | None:
    """The terminal holder identity key. K-HOLDER ATTACKS ONLY."""
    setup = getattr(arm, "_setup", None) or {}
    raw = (setup.get("holder_privates") or {}).get("holder-specialist")
    return None if raw is None else Ed25519PrivateKey.from_private_bytes(raw)


def _staged(arm: Any):
    return getattr(arm, "_staged", None)


def _field(staged: Any, name: str) -> Any:
    """A staged field, or None if this arm's presentation type has no such field.

    B0, B1 and the B2 arms stage their own presentation types -- `B2Presentation`
    carries no `htc_chain` and no `invocation_assertion` at all. An attack that
    reached for those attributes directly would raise inside the sealed runner
    and abort the cell, which is the defect this helper closes: an arm that
    cannot express the attack must record NOT APPLICABLE and still be scored,
    exactly as SS E.4's NA rule requires.
    """
    return getattr(staged, name, None)


def _open_envelope(wire: bytes) -> dict[str, Any]:
    return dict(json.loads(bytes(wire))["payload"])


# --------------------------------------------------------------------------
# staged-material attacks
# --------------------------------------------------------------------------
def forge_htc_hop(arm: Any, seed: bytes, **_: Any) -> str:
    """Targets CONJUNCT 3 (certificate-chain-valid). Wired to attack A1.

    Appends an HTC hop naming the attacker as the next holder.

    Targets `certificate-chain-valid` (conjunct 3). HTC_i must be signed by
    HTC_{i-1}.next_holder_pubkey (`capability_path.py:669-676`); K-none holds no
    such key, so the appended hop is signed by the attacker's own.
    """
    staged = _staged(arm)
    if staged is None or not _field(staged, "htc_chain"):
        return "not applicable: this arm stages no HTC chain"
    key = _attacker_key(seed)
    pub = key.public_key().public_bytes_raw().hex()
    last = _open_envelope(staged.htc_chain[-1])
    forged = dict(last)
    forged["depth"] = int(last["depth"]) + 1
    forged["kid"] = ATTACKER_LABEL
    forged["signer_pubkey"] = pub
    forged["next_holder_pubkey"] = pub
    arm._staged = dataclasses.replace(
        staged, htc_chain=tuple(staged.htc_chain) + (seal(HTC_TAG, forged, key),)
    )
    return f"appended a self-signed HTC hop at depth {forged['depth']} naming the attacker"


def resign_inv_as_attacker(arm: Any, seed: bytes, **_: Any) -> str:
    """Targets CONJUNCT 4 (holder-proof-valid). Wired to attack A2.

    Re-signs the staged INV under an unregistered attacker key.

    Targets `holder-proof-valid` (conjunct 4). The payload is left byte-identical
    so that only WHO SIGNED changes -- the binding fields stay correct, which is
    what keeps `invocation_binding_ok` from firing first and masking the limb.
    """
    staged = _staged(arm)
    if staged is None or not _field(staged, "invocation_assertion"):
        return "not applicable: this arm stages no INV"
    payload = _open_envelope(staged.invocation_assertion)
    arm._staged = dataclasses.replace(
        staged, invocation_assertion=seal(INV_TAG, payload, _attacker_key(seed))
    )
    return "re-signed the INV under an unregistered attacker key, payload unchanged"


def substitute_access_token(arm: Any, seed: bytes, **_: Any) -> str:
    """Targets CONJUNCTS 9 and 10 (resource-authorized, identity-consistent).
    Wired to attacks A6 and A7.

    Presents the attacker's own access token.

    Targets `resource-authorized` (9) and `identity-consistent` (10). The INV is
    NOT re-bound, because K-none cannot re-sign it -- which is the honest form of
    this attack and, per the table, may leave `invocation_binding_ok` (5) firing
    first. Whether it does is what this cell measures.
    """
    staged = _staged(arm)
    if staged is None or not _field(staged, "access_token"):
        return "not applicable: this arm stages no access token"
    arm._staged = dataclasses.replace(staged, access_token="adaptive.attacker.token")
    return "swapped the staged access token for the attacker's own; INV left as signed"


def remint_inv_out_of_scope(arm: Any, seed: bytes, **_: Any) -> str:
    """Targets CONJUNCT 6 (R subset-of C_n) under K-HOLDER. Wired to attack A8.

    Re-mints a fully valid INV binding an out-of-scope request.

    Targets `R subset-of C_n` (conjunct 6) under K-holder -- the H4b staging.
    Every binding field is set CORRECTLY for the substituted request, and the
    assertion is signed under the genuine terminal holder identity key, so
    conjuncts 1-5 and 10 are all satisfied. Only containment can refuse it.
    """
    staged = _staged(arm)
    key = _holder_key(arm)
    if staged is None or not _field(staged, "invocation_assertion") or key is None:
        return "not applicable: this arm stages no INV under a terminal holder key"
    payload = _open_envelope(staged.invocation_assertion)
    payload["tool"] = HIGH_RISK_TOOL
    payload["canonical_request_digest"] = _jcs_digest({"resource": OUT_OF_SCOPE_RESOURCE})
    payload["access_token_hash"] = access_token_hash(staged.access_token)
    arm._staged = dataclasses.replace(staged, invocation_assertion=seal(INV_TAG, payload, key))
    return (
        f"re-minted a VALID INV under the terminal holder key binding "
        f"{HIGH_RISK_TOOL} on {OUT_OF_SCOPE_RESOURCE} (outside C_n)"
    )


def _jcs_digest(arguments: Mapping[str, Any]) -> str:
    from src.sut.jcs import h_jcs

    return h_jcs(dict(arguments))


# --------------------------------------------------------------------------
# the eight cells
# --------------------------------------------------------------------------
# `stage` runs after the sealed present(); `invoke` rewrites (tool, arguments)
# between the Specialist and the boundary. `expect` is the PRE-REGISTERED
# prediction and is reported beside the outcome, never in place of it.
ATTACKS: tuple[dict[str, Any], ...] = (
    {
        "id": "A1-htc-chain-K-none-T1",
        "conjunct": "certificate-chain-valid",
        "capability": "K-none",
        "tampering_point": "T1 caller substitution",
        "stage": forge_htc_hop,
        "invoke": None,
        "expect": "b3_htc_chain",
    },
    {
        "id": "A2-holder-proof-K-none-T1",
        "conjunct": "holder-proof-valid",
        "capability": "K-none",
        "tampering_point": "T1 caller substitution",
        "stage": resign_inv_as_attacker,
        "invoke": None,
        "expect": "b3_holder_proof",
    },
    {
        "id": "A3-invocation-bound-K-none-T2",
        "conjunct": "invocation-bound",
        "capability": "K-none",
        "tampering_point": "T2 tool substitution",
        "stage": None,
        "invoke": (HIGH_RISK_TOOL, dict(BASE_ARGS)),
        "expect": "b3_invocation_binding",
    },
    {
        "id": "A4-invocation-bound-K-none-T3",
        "conjunct": "invocation-bound",
        "capability": "K-none",
        "tampering_point": "T3 argument substitution",
        # NO staged-material corruption of any kind: the INV that reaches the
        # boundary is the one the sealed arm minted, untouched and unre-signed.
        "stage": None,
        # Substituted WITHIN C_n on purpose, so containment cannot also fire and
        # the cell isolates conjunct 5 rather than measuring two at once.
        "invoke": (BASE_TOOL, {"resource": IN_SCOPE_RESOURCE}),
        "expect": "b3_invocation_binding",
    },
    {
        "id": "A5-containment-K-none-T4",
        "conjunct": "R subset-of C_n",
        "capability": "K-none",
        "tampering_point": "T4 scope excess",
        "stage": None,
        "invoke": (BASE_TOOL, {"resource": OUT_OF_SCOPE_RESOURCE}),
        "expect": "b3_invocation_binding on B3 (masks); b3_containment on B-cap",
    },
    {
        "id": "A6-resource-authorized-K-none-T1",
        "conjunct": "resource-authorized",
        "capability": "K-none",
        "tampering_point": "T1 caller substitution",
        "stage": substitute_access_token,
        "invoke": None,
        "expect": "b3_invocation_binding on B3 (masks); b3_oauth_resource_authorization on B-cap",
    },
    {
        "id": "A7-identity-consistent-K-none-T1",
        "conjunct": "identity-consistent",
        "capability": "K-none",
        "tampering_point": "T1 caller substitution",
        "stage": substitute_access_token,
        "invoke": None,
        "expect": "unreachable under K-none; conjunct 5 or 9 fires first",
    },
    {
        "id": "A8-containment-K-holder-T4",
        "conjunct": "R subset-of C_n",
        "capability": "K-holder",
        "tampering_point": "T4 scope excess",
        "stage": remint_inv_out_of_scope,
        "invoke": (HIGH_RISK_TOOL, {"resource": OUT_OF_SCOPE_RESOURCE}),
        "expect": "b3_containment -- the only conjunct that can refuse a compromised holder",
    },
)
