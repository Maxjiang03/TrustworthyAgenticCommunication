"""The FROZEN predictions of DEVIATIONS D-023, committed before any ablation cell runs.

Rule: every variant is predicted IDENTICAL to B3 (same run) on every cell, except the
cells listed here. A listed value is either "admit" or the reason code of the conjunct
predicted to refuse instead. Derived mechanically from B3's per-cell reason codes in
the sealed campaign (results/raw/campaign-confirmatory.json) and in adaptive runs 2/3,
plus the evaluation order of CONJUNCT_ORDER and §E.6's orthogonal-fixture claims;
nothing here was seen after a run.
"""

# (scenario_id, monitor_attached) -> prediction, per variant
CAMPAIGN: dict[str, dict[tuple[str, bool | None], str]] = {
    "B3 -contain": {
        ("cf-f1-root", None): "admit",
        ("cf-f1-terminal", None): "admit",
        ("cf-f1-chain-tamper", None): "admit",
    },
    "B3 -attenuation": {
        ("cf-f1-terminal", None): "admit",  # R in C_0 \ C_n: the §E.6 fixture
    },
    "B3 -holder-proof": {
        ("cf-f2-wrong-holder-proof", None): "admit",
        ("cf-f3-stolen-at-key-substitution", None): "admit",
    },
    "B3 -htc-chain": {},
    "B3 -invoke": {},
    "B3 -context": {
        ("cf-f4-declassified", False): "b3_approval_artifact",
        ("cf-f4-sensitive-egress", False): "b3_approval_artifact",
        ("cf-f5-approved", False): "b3_approval_artifact",
        ("cf-f5-unapproved-high-risk", False): "b3_approval_artifact",
        ("cf-f4-sensitive-egress", True): "admit",
    },
    "B3 -approval": {
        ("cf-f5-unapproved-high-risk", True): "admit",
    },
}

# attack id -> prediction, per variant (B3's own outcomes: A1 htc, A2 holder, A3-A7
# invocation binding, A8 containment, A9 admit)
ADAPTIVE: dict[str, dict[str, str]] = {
    "B3 -contain": {"A8-containment-K-holder-T4": "admit"},
    "B3 -attenuation": {},
    "B3 -holder-proof": {"A2-holder-proof-K-none-T1": "admit"},
    "B3 -htc-chain": {"A1-htc-chain-K-none-T1": "b3_holder_proof"},
    "B3 -invoke": {
        "A3-invocation-bound-K-none-T2": "b3_containment",
        "A4-invocation-bound-K-none-T3": "admit",
        "A5-containment-K-none-T4": "b3_containment",
        "A6-resource-authorized-K-none-T1": "b3_oauth_resource_authorization",
        "A7-identity-consistent-K-none-T1": "b3_oauth_resource_authorization",
    },
    "B3 -context": {},
    "B3 -approval": {},
}
