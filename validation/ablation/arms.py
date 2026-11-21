"""The §E.6 matched leave-one-out variants of B3, as post-seal validation arms (DEVIATIONS D-023).

Each variant is `B3` with exactly one conjunct of the admission rule removed, built on
the seams the sealed code already provides and nothing else:

* six variants use `ArmIdentity(is_ablation=True, ablates=<conjunct>)` and the sealed
  decision path's `disabled` seam (`CapabilityDecisionPath`, guarded by
  `ArmIdentity.check_disabled`: exactly one conjunct, never on a confirmatory run);
* `-attenuation` is §E.6's UNSAFE CONTROL. The frozen `gamma_ablations.minus_attenuation`
  override (`evaluation.prefix = P_0`) is consumed by the harness verifier, not by the
  SUT decision path, which evaluates `P_n` unconditionally; so this variant realises
  the override as §E.6 says it must be realised -- "an unsafe reference monitor that
  bypasses Biscuit attenuation" -- by evaluating containment against the authority
  prefix `P_0` instead of the terminal prefix `P_n`. The sealed `authority.allowed_set`
  is called unchanged; only the prefix handed to it differs. It is a control, never a
  deployable arm, and it is refused on a confirmatory run like every other variant.

§E.6 names `-holder` as removing BOTH `holder_proof_ok` and `htc_chain_ok`; the sealed
identity rule permits exactly one conjunct per variant, so `-holder` is run as its two
single-conjunct limbs, `-holder-proof` and `-htc-chain`, and reported as such.

Nothing in `src/` or `analysis/` is edited. The ladder's nine arms run in the same
campaign unchanged, so every comparison is within one run.
"""

from typing import Any

from src.sut.authz import capability_path as cp
from src.sut.baselines.b3 import B3Arm
from src.sut.baselines.base import ArmIdentity
from src.sut.capability import authority
from src.sut.protocol.required_authority import RequiredAuthorityError, required_authority

# variant name -> the ONE sealed conjunct its `disabled` set names (CONJUNCT_ORDER)
DISABLED_VARIANTS: dict[str, str] = {
    "B3 -contain": "containment_ok",
    "B3 -invoke": "invocation_binding_ok",
    "B3 -holder-proof": "holder_proof_ok",
    "B3 -htc-chain": "htc_chain_ok",
    "B3 -context": "context_policy_ok",
    "B3 -approval": "approval_artifact_ok",
}
ATTENUATION_VARIANT = "B3 -attenuation"
VARIANT_NAMES: tuple[str, ...] = tuple(DISABLED_VARIANTS) + (ATTENUATION_VARIANT,)


def _make_disabled_variant(name: str, conjunct: str) -> type[B3Arm]:
    class Variant(B3Arm):
        def __init__(self, identity: ArmIdentity | None = None) -> None:
            super().__init__(identity or ArmIdentity(name=name, is_ablation=True, ablates=conjunct))

    Variant.__name__ = "B3Minus_" + conjunct
    Variant.__qualname__ = Variant.__name__
    return Variant


class RootOnlyDecisionPath(cp.CapabilityDecisionPath):
    """§E.6 `-attenuation`: containment evaluated against `P_0`, every attenuation block
    ignored. Adds no state; installed on the variant's decision path by class swap."""

    def _containment_ok(self, p, tool, arguments, state) -> None:  # type: ignore[override]
        try:
            required = required_authority(tool, arguments)
        except RequiredAuthorityError as exc:
            raise cp.ConjunctFailed("containment_ok", f"no well-formed R: {exc}") from exc
        allowed = authority.allowed_set(
            bytes(p.capability_hops[0]),  # P_0, not P_n: the unsafe control
            self._root_public,
            self._gamma,
            now_epoch=p.now_epoch,
            audience=p.audience,
            task_id=p.task_id,
        )
        state["C_n"] = allowed
        state["ablation_prefix"] = "P_0"
        if not required <= allowed:
            outside = sorted(required - allowed)
            raise cp.ConjunctFailed(
                "containment_ok", f"R exceeds Allowed(P_0) by {outside} (unsafe control)"
            )


class B3MinusAttenuation(B3Arm):
    def __init__(self, identity: ArmIdentity | None = None) -> None:
        super().__init__(
            identity
            or ArmIdentity(
                name=ATTENUATION_VARIANT,
                is_ablation=True,
                ablates="containment prefix: Allowed(P_0) instead of Allowed(P_n)",
            )
        )

    def provision(self, setup: Any) -> None:
        setup = dict(setup)
        if setup.get("run_mode") == "confirmatory":
            raise RuntimeError(f"{self.name} may not drive a confirmatory run")
        super().provision(setup)
        assert self._decision_path is not None
        # The subclass adds no attributes, so the swap changes one method's
        # behaviour and nothing else -- the same device `attach_replay_cache`
        # uses on `_jti_cache`, applied to the containment conjunct.
        self._decision_path.__class__ = RootOnlyDecisionPath


def variant_factories(b3_setup: dict[str, Any]) -> dict[str, tuple[type, dict[str, Any]]]:
    """The seven variants as campaign factories, each on B3's own setup."""
    out: dict[str, tuple[type, dict[str, Any]]] = {}
    for name, conjunct in DISABLED_VARIANTS.items():
        setup = dict(b3_setup)
        setup["disabled"] = (conjunct,)
        out[name] = (_make_disabled_variant(name, conjunct), setup)
    out[ATTENUATION_VARIANT] = (B3MinusAttenuation, dict(b3_setup))
    return out
