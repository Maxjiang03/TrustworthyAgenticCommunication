"""Adaptive run 3 (DEVIATIONS D-020): ONE additional cell, A9, staged exactly as A8 was.

A9 is the in-scope half of H4b. A8 showed that a compromised holder who re-mints a
valid INV for a request OUTSIDE C_n is refused at scope containment. A9 asks the
complementary question the pre-registration also poses: a compromised holder who
re-mints a valid INV for a request INSIDE C_n -- the same argument substitution as
A4, but signed under the terminal holder identity key -- must be ADMITTED by every
configuration, because no conjunct has grounds to refuse it. H4b is falsified in
its over-blocking half if any C_n-enforcing configuration refuses this request.

The cell also disambiguates A4: A4's substituted resource was inside C_n and B3
refused it at invocation binding (the INV did not match the bytes). If A9 is
admitted, A4's refusal is shown to rest on the binding and not on scope.

Post-seal adaptive validation, outside `src/` and `analysis/`; imports the sealed
arms read-only and modifies none of them. Uses the seams and helpers of
`validation/adaptive/attacks.py` (the D-019 module) unchanged.
"""

import dataclasses
from typing import Any

from src.harness.verifier.at_digest import access_token_hash
from src.harness.verifier.holder_binding import INV_TAG, seal
from validation.adaptive.attacks import (
    BASE_TOOL,
    IN_SCOPE_RESOURCE,
    _field,
    _holder_key,
    _jcs_digest,
    _open_envelope,
    _staged,
)


def remint_inv_in_scope(arm: Any, seed: bytes, **_: Any) -> str:
    """K-HOLDER: re-mint a fully valid INV binding an IN-SCOPE substituted request.

    Every binding field is set correctly for the substituted request and the
    assertion is signed under the genuine terminal holder identity key, so
    conjuncts 1-5, 9 and 10 are satisfied; the request lies inside C_n, so
    conjunct 6 is satisfied too. No conjunct should fire.
    """
    staged = _staged(arm)
    key = _holder_key(arm)
    if staged is None or not _field(staged, "invocation_assertion") or key is None:
        return "not applicable: this arm stages no INV under a terminal holder key"
    payload = _open_envelope(staged.invocation_assertion)
    payload["tool"] = BASE_TOOL
    payload["canonical_request_digest"] = _jcs_digest({"resource": IN_SCOPE_RESOURCE})
    payload["access_token_hash"] = access_token_hash(staged.access_token)
    arm._staged = dataclasses.replace(staged, invocation_assertion=seal(INV_TAG, payload, key))
    return (
        f"re-minted a VALID INV under the terminal holder key binding "
        f"{BASE_TOOL} on {IN_SCOPE_RESOURCE} (inside C_n)"
    )


# The pre-registered prediction (D-020) travels with the cell and is reported
# beside the outcome, never in place of it.
ATTACKS_RUN3: tuple[dict[str, Any], ...] = (
    {
        "id": "A9-in-scope-K-holder-T3",
        "conjunct": "none -- H4b's in-scope half: no conjunct has grounds to fire",
        "capability": "K-holder",
        "tampering_point": "T3 argument substitution, inside C_n",
        "stage": remint_inv_in_scope,
        "invoke": (BASE_TOOL, {"resource": IN_SCOPE_RESOURCE}),
        "expect": (
            "ADMITTED by all nine arms: B0 b0_no_boundary_check, B1 b1_admitted, the four "
            "B2 arms b2_admitted, B-cap/B3/B3+ b3_admitted. Any refusal by a C_n-enforcing "
            "arm falsifies H4b's over-blocking half for that arm."
        ),
    },
)
