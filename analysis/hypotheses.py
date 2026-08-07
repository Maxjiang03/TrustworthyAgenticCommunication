"""H4a and H4b, and the conditions that FALSIFY them, as executable predicates.

Part D.1's falsifiable content is exactly H4a and H4b (ADR 0042), and until now
neither existed in code: the only occurrence of the strings in the repository
was a substring assertion on document prose. A hypothesis whose falsification
condition is not executable is one that gets re-read after the results are in
(ADR 0044).

Both are stated here as the pre-registration states them, and the verdicts are
the pre-registration's own words -- SUPPORTED, FALSIFIED, or NOT DETERMINED.
The third is not a hedge: with three of five F3 subcases not instantiated, some
of what H4a predicts is simply not measured, and reporting that as support
would be the exact reading §4's declaration forbids.
"""

from dataclasses import dataclass
from typing import Any

from analysis.matrix import ROW_SUBCASE_TOKENS

# H4a's two attacks, in §E.4's vocabulary.
#   (i)  reuse a captured credential as a DIFFERENT caller
#   (ii) substitute tool/arguments AFTER signing
H4A_REUSE = "F3:dpop-stolen-AT-key-substitution"
H4A_BODY_MUTATION = ROW_SUBCASE_TOKENS["F3 dpop-first-use-body-mutation"]  # None: not instantiated

BEARER = "B2-exchange-task"
DPOP = "B2-exchange-task-DPoP"
STRONG = "B3"


@dataclass(frozen=True)
class HypothesisVerdict:
    name: str
    verdict: str  # SUPPORTED | FALSIFIED | NOT DETERMINED
    reasons: list[str]
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "hypothesis": self.name,
            "verdict": self.verdict,
            "reasons": self.reasons,
            "evidence": self.evidence,
        }


def _observed(cells: dict[tuple[str, str], str], subcase: str | None, arm: str) -> str | None:
    if subcase is None:
        return None
    return cells.get((subcase, arm))


def evaluate_h4a(observed: dict[tuple[str, str], str]) -> HypothesisVerdict:
    """H4a: post-signature, non-holder tampering.

    Prediction: bearer admits both; DPoP admits (ii) at the same endpoint but
    blocks (i); **B3 blocks both**.
    **Falsified if** B3 admits either, or if DPoP blocks same-endpoint
    tool/argument substitution.
    """
    reasons: list[str] = []
    evidence = {
        "reuse": {arm: _observed(observed, H4A_REUSE, arm) for arm in (BEARER, DPOP, STRONG)},
        "body_mutation": {
            arm: _observed(observed, H4A_BODY_MUTATION, arm) for arm in (BEARER, DPOP, STRONG)
        },
    }

    falsified = False
    # Limb 1 of the falsification condition: B3 admits either attack.
    for attack, subcase in (("reuse", H4A_REUSE), ("body_mutation", H4A_BODY_MUTATION)):
        seen = _observed(observed, subcase, STRONG)
        if seen == "A":
            falsified = True
            reasons.append(f"FALSIFYING: {STRONG} ADMITTED the {attack} attack (predicted block)")
    # Limb 2: DPoP blocks same-endpoint tool/argument substitution.
    if _observed(observed, H4A_BODY_MUTATION, DPOP) == "B":
        falsified = True
        reasons.append(
            f"FALSIFYING: {DPOP} BLOCKED same-endpoint body mutation, which the hypothesis "
            "predicts it cannot see"
        )

    if falsified:
        return HypothesisVerdict("H4a", "FALSIFIED", reasons, evidence)

    if H4A_BODY_MUTATION is None:
        reasons.append(
            "attack (ii), tool/argument substitution after signing, is the "
            "`F3 dpop-first-use-body-mutation` row -- NOT POPULATED BY THE CAMPAIGN "
            "(pre-registered §4). Half of H4a's prediction is therefore unmeasured, and "
            "the measured half alone does not support the whole hypothesis."
        )
        return HypothesisVerdict("H4a", "NOT DETERMINED", reasons, evidence)

    measured = [v for v in evidence["reuse"].values() if v is not None]
    if not measured:
        reasons.append("no cell of H4a was measured")
        return HypothesisVerdict("H4a", "NOT DETERMINED", reasons, evidence)

    reasons.append("no falsifying cell was measured, and every predicted cell agreed")
    return HypothesisVerdict("H4a", "SUPPORTED", reasons, evidence)


def evaluate_h4b(observed: dict[tuple[str, str], str]) -> HypothesisVerdict:
    """H4b: compromised-holder misuse.

    Prediction: **no** mechanism blocks a compromised holder acting *within*
    `C_n`; **all** `C_n`-enforcing mechanisms block it from exceeding `C_n`.
    **Falsified if** B3 blocks in-scope compromised-holder actions
    (over-blocking) or any `C_n`-enforcing mechanism admits out-of-`C_n`
    actions.

    The campaign instantiates no compromised-holder scenario: the corpus's
    holder faults substitute a DIFFERENT holder's key, which is H4a's
    non-holder adversary, not H4b's. Reported as NOT DETERMINED rather than
    inferred from an adjacent family.
    """
    return HypothesisVerdict(
        "H4b",
        "NOT DETERMINED",
        [
            "the corpus instantiates no compromised-holder scenario: its holder faults "
            "substitute another holder's key (H4a's adversary, who does NOT possess the "
            "terminal holder identity key), so H4b's premise is never staged",
            "in-scope-vs-out-of-scope containment IS measured, by F1-root and F1-terminal, "
            "but those are not compromised-holder instances and are not reported as if "
            "they were",
        ],
        {"instantiated": False},
    )


def evaluate(observed: dict[tuple[str, str], str]) -> list[dict[str, Any]]:
    return [evaluate_h4a(observed).as_dict(), evaluate_h4b(observed).as_dict()]
