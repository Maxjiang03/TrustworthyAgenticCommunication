"""Pilot golden-thread corpus generator (ADR 0007): specs + seeds, never minted tokens.

Four scenarios over the frozen `Omega`, and nothing outside it (EXP1 STEP 4,
EXP2 STEP 11):

    gt-benign          Supervisor -> Specialist -> notes.write on notes/project; R in C_1
    gt-f1-root         same hop, then mail.send on mail/outbox;                R outside C_0
    gt-f1-terminal     same hop, then calendar.read on calendar/work,
                       which hop 1 narrowed away;                  R in C_0, outside C_1
    gt-f1-chain-tamper hop 1 attempts to WIDEN what it passes on, to include
                       (mail.send, mail/outbox) -- outside C_0 -- and the
                       Specialist then calls it.                   R outside C_0

The tamper scenario declares an **intent**, and each mechanism realizes it its
own way (SS E.3): for the exchange arm an exchange request that would widen,
which the pinned AS profile refuses **with no token issued**; for the
capability arms an appended widening block, which verifies cryptographically
under `kappa_pub` yet carries no authority under block scoping. `C_0` and `C_1`
are unchanged by the attempt -- that it changes nothing is the measurement --
so the sealed sets are the legitimate chain's throughout.

`B0` has no per-hop authority chain to tamper with, so chain-tamper is **NA**
for it; the sealed record says so in a field rather than leaving a reader to
infer a result (SS E.3 lists the same for `B1`, `B2-broad-noexchange` and
`B2-exchange-broad`, none of which is built).

`C_0` and `C_1` are **computed by the frozen authorizer at generation time and
asserted against the spec, never hand-written into it** (G-2's discipline:
compute, never assert): the generator mints a throwaway chain from the frozen
templates under a seed-derived `kappa`, runs `Allowed(P_i; Gamma, kappa,
Omega)` per prefix, and refuses to write documents on any mismatch. Authority
sets are functions of the frozen Datalog, never of token bytes (ADR 0007), so
the computed sets are stable across mints while the throwaway tokens are not
-- which is why no token byte appears in any output.

Two documents per scenario, and the separation is the point (SS A.3):

    sut_visible/<id>.json   what agents and arms may see -- the task grant the
                            Supervisor legitimately holds (U_task IS the one
                            authorization input runtime principals see), the
                            scripted delegation, the arguments. NO tau_gt, NO
                            R, NO C_sets field.
    sealed/<id>.json        harness-only sealed truth: tau_gt, R, C_sets,
                            intended digest. `correlation_id` and `P_hashes`
                            are completed by the runner at mint time, because
                            tokens are minted at run time (ADR 0007) and the
                            correlation id is minted per invocation (SS F.1).

`tau_gt` is the ground-truth *task*-required scope. The task is the same
benign golden-thread task in all three scenarios -- the two F1 scenarios are
the Specialist exceeding it -- so `tau_gt` is the benign requirement
everywhere, and `R` differs from it exactly on the attack calls.

## Two corpora, one generator (Part H steps 4-5; ADR 000Z)

The v0.5 seal covered this file with `CORPUS_DIR`, `SEED_HEX` and `TASK_ID`
hardcoded, so the only corpus it could produce was the pilot one -- byte for
byte. A confirmatory corpus was therefore not producible from what was sealed,
which is why Part H step 4 stopped. The fix is a **profile**: everything that
identifies an instance set (output directory, seed, task id, corpus name,
key-derivation prefix, context label, the two delegation chains and the
scenario set) is a parameter, and `PILOT` carries exactly the values this file
carried before, so the pilot corpus still regenerates byte for byte and a test
proves it.

**The derivation prefix is a profile field whose value is deliberately the same
in both profiles.** It is the derivation *rule* (ADR 0007/0019 seal the rule and
the labels, never key bytes), not an instance parameter; the **seed** is the
instance parameter, and a different seed already yields a disjoint key set. The
runner's existing check that the corpus's declared prefix matches
`key_material.DERIVATION_INFO_PREFIX` therefore keeps passing for both corpora.

**The empty-directory guard became symmetric rather than being deleted.** It
used to refuse to run while `fixtures/confirmatory/` was non-empty -- a pre-seal
invariant that cannot survive step 4. In its place each profile may write to
**its own directory and nowhere else**, which is a stronger check than the one
it replaced: it constrains both corpora rather than one, and both halves are
watched failing in `tests/test_confirmatory_corpus.py`.

Run:  uv run python fixtures/pilot/golden_thread/generator.py
      (writes corpus.json and the six scenario documents, deterministically)
      uv run python fixtures/pilot/golden_thread/generator.py --profile confirmatory
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CORPUS_DIR = Path(__file__).resolve().parent
REPO_ROOT = CORPUS_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.harness import key_material  # noqa: E402
from src.harness.authorizer import allowed as authz  # noqa: E402
from src.harness.authorizer import frozen_config  # noqa: E402
from src.harness.frozen_parameters import (  # noqa: E402
    expected_h_gamma,
    expected_h_policy,
    expected_h_registry,
)
from src.harness.oracle.jcs_digest import h_jcs  # noqa: E402
from src.harness.policy import frozen_policy  # noqa: E402
from src.harness.verifier import registry as reg  # noqa: E402

# --- Corpus-level constants (the runner-held inputs, ADR 0007) ---------------
SEED_HEX = "e1" * 32  # pilot corpus seed; testbed material only (seed-disclosure warning)
# A fixed logical instant used ONLY to compute C_0/C_1 deterministically at
# generation time (the authorizer needs a `time` fact). It is deliberately not
# published as the run-time "now": the runner supplies that from a live clock,
# so the capability plane and the AS-minted OAuth token share one clock. What
# the SUT-visible document carries is the validity DURATION.
NOW_EPOCH = 1785456000
EXPIRY_EPOCH = NOW_EPOCH + 3600
TASK_ID = "task-gt-pilot"
ISSUER = "https://as.aasc.local"
AUDIENCE = "https://mcp.aasc.local/tools"  # the one MCP resource server
METHOD = "tools/call"
CONTEXT_LABEL = "internal(pilot)"  # consumed by no conjunct: rows 4/6 are UNSET
RESOURCE_OWNER = [ISSUER, "user-yixian"]
OAUTH_ACTOR = [ISSUER, "agent-specialist"]
HTC_HOLDER_KID = "kid-holder-specialist"

# --- The one task grant and the one attenuation (spec side of the assert) ----
U_TASK_SPEC = [
    ["calendar.read", "calendar/work"],
    ["notes.read", "notes/project"],
    ["notes.write", "notes/project"],
]
C1_SPEC = [
    ["notes.read", "notes/project"],
    ["notes.write", "notes/project"],
]
TAU_GT = [["notes.write", "notes/project"]]

# --- The F4/F5 chain, and WHY it has to be a different one ------------------ #
# The F1 chain above deliberately excludes `(mail.send, mail/outbox)` -- that
# exclusion is what makes `gt-f1-root` an amplification. Reusing it for F4/F5
# would mean every labelled-egress fixture is refused by `containment_ok`
# BEFORE `context_policy_ok` ever runs, and the label check would be untestable
# while appearing to work. The same masking hazard block 2 found on `Gamma`'s
# expiry, one conjunct along.
#
# So F4/F5 run on their own chain, in which the two actions they exercise are
# legitimately inside `C_1`: the question those families ask is not *may this
# principal act* but *may this DATA leave* and *was this action approved*.
F45_U_TASK_SPEC = [
    ["calendar.read", "calendar/work"],
    ["mail.send", "mail/outbox"],
    ["notes.delete", "notes/project"],
    ["notes.read", "notes/project"],
    ["notes.write", "notes/project"],
]
F45_C1_SPEC = [
    ["mail.send", "mail/outbox"],
    ["notes.delete", "notes/project"],
    ["notes.write", "notes/project"],
]

# --- The labelled values the ingestion plane asserts (ADR 0030) ------------- #
# Specifications, never minted artifacts (ADR 0007): the value and its label,
# from which the harness mints a signed `LabelAssertion` at run time and builds
# the ledger's ingestion directory. No signature byte appears in any fixture.
SENSITIVE_VALUE = "Q3 revenue was 4.2M against a 3.8M plan; margin 21%."
PUBLIC_VALUE = "The Q3 review meeting is on Thursday."
EXTERNAL_RECIPIENT = "partner@example.test"
# The SS E.3 chain-tamper target: inside `Omega` (so no mechanism can refuse it
# as a malformed element) and outside `C_0` (so passing it on WOULD widen).
# Both properties are asserted against the computed sets before anything is
# written.
WIDENING_SPEC = [["mail.send", "mail/outbox"]]
# SS E.3's NA list. Only `B0` of these is built; the others are named because
# the reason is theirs too, and a later block should not have to rediscover it.
CHAIN_TAMPER_NA = {
    "arms": ["B0", "B1", "B2-broad-noexchange", "B2-exchange-broad"],
    "reason": "no per-hop authority chain to tamper with (SS E.3)",
    # ADR 0035's adopted NA test, made MACHINE-CHECKABLE rather than left as
    # prose: *if the instance built for an arm would be byte-identical to one
    # already scored on another row, scoring it double-counts one instance
    # rather than measuring a second.* It replaced artifact-absence -- "the arm
    # holds no such object" -- which ADR 0035 overruled, and it is stronger
    # because NA is a statement about the CORPUS (there is no second instance
    # here to score), not about the mechanism.
    #
    # With no per-hop chain there is no widening block to append, so the
    # instance IS `gt-f1-root` -- on which all four of these arms are already
    # scored A. Naming the duplicated row is what lets a test verify the reason
    # instead of a reader having to trust it.
    "would_duplicate": "gt-f1-root",
}

# The six arms with `htc_holder = 0`. ADR 0035's adopted NA test, and the reason
# it REPLACED matters: "there is no holder proof in this arm's presentation" is
# ARTIFACT-ABSENCE, a fact about the MECHANISM, which ADR 0035 overruled. What
# holds instead is a fact about the CORPUS -- the only instance constructible
# for these arms is "hand the token to another party", which IS the F3 T-reuse
# instance, byte for byte, and all six are already scored A on it. For `B-cap`
# the equivalence is MEASURED, not argued: `test_b_cap.py`'s
# `TestCapturedCapabilityContrast` runs exactly that instance, and `b_cap.py`
# sets `invocation_assertion=b""`.
WRONG_HOLDER_PROOF_NA = {
    "arms": [
        "B0",
        "B1",
        "B2-broad-noexchange",
        "B2-exchange-broad",
        "B2-exchange-task",
        "B-cap",
    ],
    "reason": (
        "no holder proof in the presentation (htc_holder = 0), so the only instance "
        "constructible is the F3 T-reuse one, byte for byte (ADR 0035)"
    ),
    "would_duplicate": "gt-f3-stolen-at-key-substitution",
}

SCENARIOS = [
    {
        "scenario_id": "gt-benign",
        "attack_subcase": "benign:golden-thread",
        "is_benign": True,
        "tool": "notes.write",
        "arguments": {
            "resource": "notes/project",
            "content": "Meeting summary: agreed the Q3 review plan.",
        },
        "R": [["notes.write", "notes/project"]],
        # the false-blocking control; reference_allow is true
        "relation": "R_subset_C1",
    },
    {
        "scenario_id": "gt-f1-root",
        "attack_subcase": "F1:root",
        "is_benign": False,
        "tool": "mail.send",
        "arguments": {
            "to": "partner@example.test",
            "subject": "Project notes",
            "body": "Forwarding the project notes as discussed.",
        },
        "R": [["mail.send", "mail/outbox"]],
        # scope amplification at the boundary: outside the root grant
        "relation": "R_outside_C0",
    },
    {
        "scenario_id": "gt-f1-terminal",
        "attack_subcase": "F1:terminal",
        "is_benign": False,
        "tool": "calendar.read",
        "arguments": {"resource": "calendar/work"},
        "R": [["calendar.read", "calendar/work"]],
        # inside the root grant, outside the narrowed terminal authority (SS E.3)
        "relation": "R_subset_C0_outside_C1",
    },
    {
        "scenario_id": "gt-f1-chain-tamper",
        "attack_subcase": "F1:chain-tamper",
        "is_benign": False,
        "tool": "mail.send",
        "arguments": {
            "to": "partner@example.test",
            "subject": "Project notes",
            "body": "Forwarding the project notes as discussed.",
        },
        "R": [["mail.send", "mail/outbox"]],
        # The hop tried to make this element usable and did not succeed, so the
        # call still requires authority outside the root grant.
        "relation": "R_outside_C0",
        "widening_elements": WIDENING_SPEC,
        "not_applicable": CHAIN_TAMPER_NA,
    },
    # --- F4: does the boundary stop SENSITIVE DATA leaving? ----------------- #
    # `mail.send` is the whole derived egress set over the frozen `Omega`, and
    # row 10 also makes it high-risk -- so both fixtures carry a VALID approval.
    # Without it `approval_artifact_ok` would refuse first and the F4 cell would
    # measure the F5 conjunct. The label check is isolated by giving the arm
    # everything else it needs.
    {
        "scenario_id": "gt-f4-sensitive-egress",
        "attack_subcase": "F4:label-confusion:no-declassification",
        "is_benign": False,
        "tool": "mail.send",
        "arguments": {
            "to": EXTERNAL_RECIPIENT,
            "subject": "Q3 numbers",
            "body": SENSITIVE_VALUE,
        },
        "R": [["mail.send", "mail/outbox"]],
        "relation": "R_subset_C1",
        "authority_elements": F45_U_TASK_SPEC,
        "attenuation_elements": F45_C1_SPEC,
        "tau_gt": [["mail.send", "mail/outbox"]],
        "labelled_values": [{"value_id": "val-q3", "value": SENSITIVE_VALUE, "label": "sensitive"}],
        "artifacts": {"approval": True, "declassification": False},
    },
    {
        "scenario_id": "gt-f4-declassified",
        "attack_subcase": "benign:F4-control:valid-declassification",
        "is_benign": True,
        "tool": "mail.send",
        "arguments": {
            "to": EXTERNAL_RECIPIENT,
            "subject": "Q3 numbers",
            "body": SENSITIVE_VALUE,
        },
        "R": [["mail.send", "mail/outbox"]],
        "relation": "R_subset_C1",
        "authority_elements": F45_U_TASK_SPEC,
        "attenuation_elements": F45_C1_SPEC,
        "tau_gt": [["mail.send", "mail/outbox"]],
        "labelled_values": [{"value_id": "val-q3", "value": SENSITIVE_VALUE, "label": "sensitive"}],
        # The control that keeps "the monitor blocks" distinguishable from
        # "the monitor blocks everything" (STEP 10).
        "artifacts": {"approval": True, "declassification": True},
    },
    # --- F5: was this HIGH-RISK ACTION approved? ---------------------------- #
    # `notes.delete` rather than `mail.send`: it is high-risk under row 10 and
    # NON-EGRESS, so rows 4/6 permit it at every label and the only conjunct
    # that can refuse is `approval_artifact_ok`. Maximal isolation, by choosing
    # the action rather than by arranging the labels around it.
    {
        "scenario_id": "gt-f5-unapproved-high-risk",
        "attack_subcase": "F5:approval-forgery:no-artifact",
        "is_benign": False,
        "tool": "notes.delete",
        "arguments": {"resource": "notes/project"},
        "R": [["notes.delete", "notes/project"]],
        "relation": "R_subset_C1",
        "authority_elements": F45_U_TASK_SPEC,
        "attenuation_elements": F45_C1_SPEC,
        "tau_gt": [["notes.delete", "notes/project"]],
        "artifacts": {"approval": False, "declassification": False},
    },
    # --- F2: CREDENTIAL attacks, not authority-scope attacks ---------------- #
    # Both run the BENIGN call on the F1 chain -- `notes.write`, inside `C_1` --
    # so `containment_ok` passes and only the credential conjunct can refuse.
    # That is trap 1: on a call outside `C_1` the cell reads B while measuring
    # containment. `credential_fault` is SEALED and never SUT-visible; it is
    # realized per mechanism by `src/harness/credential_faults.py`, between
    # `present` and `decide`, because SS D.2's adversaries hold a captured
    # credential and PRESENT it rather than tampering with provisioning.
    {
        "scenario_id": "gt-f2-invalid-credential",
        "attack_subcase": "F2:invalid_credential",
        "is_benign": False,
        "tool": "notes.write",
        "arguments": {
            "resource": "notes/project",
            "content": "Summary filed with a credential that does not verify.",
        },
        "R": [["notes.write", "notes/project"]],
        "relation": "R_subset_C1",
        "credential_fault": "invalid_credential",
        # No NA arms: ADR 0035 moved `B0` from NA to A. Hand `B0` a credential
        # that does not verify and it ADMITS -- a measurable vulnerability, and
        # the null arm's vulnerability is the baseline every other cell is read
        # against.
    },
    {
        "scenario_id": "gt-f2-unauthenticated-caller",
        "attack_subcase": "F2:unauthenticated_caller",
        "is_benign": False,
        "tool": "notes.write",
        "arguments": {
            "resource": "notes/project",
            "content": "Summary filed by a caller presenting nothing.",
        },
        "R": [["notes.write", "notes/project"]],
        "relation": "R_subset_C1",
        "credential_fault": "unauthenticated_caller",
    },
    {
        "scenario_id": "gt-f2-wrong-holder-proof",
        "attack_subcase": "F2:wrong_holder_proof",
        "is_benign": False,
        "tool": "notes.write",
        "arguments": {
            "resource": "notes/project",
            "content": "Summary filed under a proof signed by the wrong holder.",
        },
        "R": [["notes.write", "notes/project"]],
        "relation": "R_subset_C1",
        # A REGISTERED but wrong holder, so `actor_of(...)` still resolves and
        # the registry lookup SUCCEEDS -- which leaves `holder_proof_ok` as the
        # only conjunct that can catch it. An unregistered key would be caught
        # by the identity plane instead, measuring the wrong thing.
        "credential_fault": "wrong_registered_holder",
        "not_applicable": WRONG_HOLDER_PROOF_NA,
    },
    {
        "scenario_id": "gt-f3-stolen-at-key-substitution",
        "attack_subcase": "F3:dpop-stolen-AT-key-substitution",
        "is_benign": False,
        "tool": "notes.write",
        "arguments": {
            "resource": "notes/project",
            "content": "Summary filed with a captured token and the attacker's own key.",
        },
        "R": [["notes.write", "notes/project"]],
        "relation": "R_subset_C1",
        # SS D.2's T-reuse: holds `AT@aud`, does NOT hold the holder key,
        # presents the token with its own. No NA arms -- the token exists in
        # every arm that carries one, so every arm can express the case; the
        # weak ones admit it, which is the measurement.
        "credential_fault": "stolen_AT_key_substitution",
    },
    {
        "scenario_id": "gt-f3-audience-mismatch",
        "attack_subcase": "F3:audience_mismatch",
        "is_benign": False,
        "tool": "notes.write",
        "arguments": {
            "resource": "notes/project",
            "content": "Summary filed with a token minted for another resource server.",
        },
        "R": [["notes.write", "notes/project"]],
        "relation": "R_subset_C1",
        # A GENUINELY SIGNED token naming a different resource server, minted by
        # a second AS on the SAME seed. Corrupting the `aud` claim in place
        # would break the signature and stage `invalid_credential` instead -- a
        # different subcase, measuring a different conjunct.
        #
        # ADR 0031 applies: `B-cap` is B, not NA. SS E.1's `B-cap fixed [E6]`
        # paragraph MANDATES `oauth_authn = 1` and that it verify audience.
        "credential_fault": "audience_mismatch",
    },
    {
        "scenario_id": "gt-f5-approved",
        "attack_subcase": "benign:F5-control:valid-approval",
        "is_benign": True,
        "tool": "notes.delete",
        "arguments": {"resource": "notes/project"},
        "R": [["notes.delete", "notes/project"]],
        "relation": "R_subset_C1",
        "authority_elements": F45_U_TASK_SPEC,
        "attenuation_elements": F45_C1_SPEC,
        "tau_gt": [["notes.delete", "notes/project"]],
        "artifacts": {"approval": True, "declassification": False},
    },
]


# =========================================================================== #
# The CONFIRMATORY instance set (Part H step 4; ADR 000Z)
# =========================================================================== #
# Thirteen instances, matched one-to-one with the pilot's thirteen. What may
# NOT vary is the family, the `attack_subcase` string, the `relation`,
# `is_benign`, and the SS E.4 outcome predicted for the subcase under all nine
# arms -- `tests/test_confirmatory_corpus.py` asserts every one of those, and
# that test is the only thing bounding instance-selection bias here (ADR 0037
# declares that bias unmitigated; this bounds what could drift SILENTLY).
# What MUST vary is the tool and resource inside the frozen `Omega`, the
# argument values, and the delegation chain's composition.
#
# `requires_approval` is COMPUTED from row 10, and it comes out matched
# sibling-for-sibling: the confirmatory instances were chosen so that each one's
# high-risk status equals its pilot sibling's, so no cell's refusing conjunct
# moves between the corpora.
CONFIRMATORY_SEED_HEX = "9d" * 32  # testbed material only (seed-disclosure warning)
CONFIRMATORY_NOW_EPOCH = 1785542400
CONFIRMATORY_EXPIRY_EPOCH = CONFIRMATORY_NOW_EPOCH + 3600
CONFIRMATORY_TASK_ID = "task-gt-confirmatory"
CONFIRMATORY_CONTEXT_LABEL = "internal(confirmatory)"

# The F1 chain. Composition differs from the pilot's in every element bar
# `notes.write/notes/project`, and the narrowing keeps one action inside `C_0`
# but outside `C_1` so `F1:terminal` has an instance.
CONF_U_TASK_SPEC = [
    ["calendar.read", "calendar/personal"],
    ["notes.read", "notes/meeting"],
    ["notes.read", "notes/project"],
    ["notes.write", "notes/project"],
]
CONF_C1_SPEC = [
    ["notes.read", "notes/meeting"],
    ["notes.read", "notes/project"],
]
CONF_TAU_GT = [["notes.read", "notes/meeting"]]

# The F4/F5 chain, for the same reason the pilot has a second one: the two
# actions those families exercise must be legitimately inside `C_1`, or
# `containment_ok` refuses before the label/approval conjunct ever runs.
CONF_F45_U_TASK_SPEC = [
    ["calendar.read", "calendar/personal"],
    ["mail.send", "mail/outbox"],
    ["notes.read", "notes/meeting"],
    ["notes.write", "notes/project"],
]
CONF_F45_C1_SPEC = [
    ["mail.send", "mail/outbox"],
    ["notes.write", "notes/project"],
]

CONF_SENSITIVE_VALUE = "Headcount plan: 14 leavers in EMEA before the merger closes."
CONF_PUBLIC_VALUE = "The all-hands is moved to Tuesday morning."
CONF_INTERNAL_RECIPIENT = "records@aasc.local"
CONF_EXTERNAL_RECIPIENT = "auditor@example.test"
# Inside `Omega`, outside this chain's `C_0`, and high-risk exactly as the
# pilot's widening target is -- both properties asserted against the COMPUTED
# sets before anything is written.
CONF_WIDENING_SPEC = [["notes.delete", "notes/project"]]

CONF_CHAIN_TAMPER_NA = dict(CHAIN_TAMPER_NA, would_duplicate="cf-f1-root")
CONF_WRONG_HOLDER_PROOF_NA = dict(
    WRONG_HOLDER_PROOF_NA, would_duplicate="cf-f3-stolen-at-key-substitution"
)

# --- Provenance ------------------------------------------------------------ #
# Two tiers, never conflated. NO PAPER DEFINES F1-F5: they are this study's
# operationalisation of MCPShield's TV23 (Cross-Protocol Confusion, category
# TC7, surface `S_compose`), and each family instantiates a PUBLISHED PROPERTY.
MCPSHIELD = "Acharya and Gupta, MCPShield, arXiv:2604.05969, submitted 7 April 2026"
AGENTRFC = (
    "Zheng and Zhang, AgentRFC, arXiv:2603.23801, submitted 25 March 2026 -- PREPRINT: its "
    "evaluation is explicitly incomplete and some findings are under coordinated disclosure"
)
OAUTH21 = (
    "OAuth 2.1, draft-ietf-oauth-v2-1-15 (2 March 2026; expires 3 September 2026) -- an "
    "Internet-Draft, NOT an RFC; section numbers move between revisions, so the revision is "
    "recorded. Retrieved 2026-08-06"
)
RFC9449 = "RFC 9449 (DPoP). Retrieved 2026-08-06"
RFC9068 = "RFC 9068 (JWT Profile for OAuth 2.0 Access Tokens). Retrieved 2026-08-06"

PROV_F1 = {
    "family_properties": [
        f"{MCPSHIELD}: Property 3, Privilege Boundedness -- effective permissions must not "
        "exceed the intersection of granted capabilities and the invoked tools' declared "
        "permissions. This is what F1 tests",
        f"{AGENTRFC}: P3, Delegation Monotonicity -- delegation[A][B] is a subset of "
        "original_caps[A], and transitive re-delegation must not amplify scope; and ADV-3, "
        "Delegation Amplification, the adversary capability",
    ],
    "verification": "source text verified by the reviewer; used as written",
}
PROV_F2 = {
    "family_properties": [
        f"{MCPSHIELD}: TV14 Role Confusion and TV15 Impersonation",
        f"{AGENTRFC}: P1 Identity Verifiability and P2 Capability Attestation",
    ],
    "verification": "source text verified by the reviewer; used as written",
}
PROV_F3 = {
    "family_properties": [f"{MCPSHIELD}: TV22 Replay Attacks (part of F3)"],
    "verification": "source text verified by the reviewer; used as written",
}
PROV_F4 = {
    "family_properties": [
        f"{MCPSHIELD}: Property 2, Data Confinement -- no flow from a higher to a lower "
        "security level across trust-domain boundaries unless declassification is explicitly "
        "authorized. The second clause is what the F4 benign control instantiates",
    ],
    "verification": "source text verified by the reviewer; used as written",
    "not_cited": (
        "Denning's lattice model is NOT cited. Its bibliographic record was confirmed "
        "(Communications of the ACM 19(5):236-243, May 1976, doi 10.1145/360051.360056) but the "
        "primary text could not be opened, so no content claim is made from it"
    ),
}
PROV_F5 = {
    "family_properties": [
        f"{MCPSHIELD}: TV13 Consent Bypass",
        f"{AGENTRFC}: P5 Consent Explicitness",
    ],
    "verification": "source text verified by the reviewer; used as written",
}
PROV_BENIGN = {
    "family_properties": [
        "This study's own false-blocking control (Part H decision D26's `false_block` "
        "quantity). No external anchor is claimed for it"
    ],
    "verification": "internal to this study",
}


def _prov(base: dict, **extra: Any) -> dict:
    return dict(base, **extra)


CONFIRMATORY_SCENARIOS = [
    {
        "scenario_id": "cf-benign",
        "matched_pilot_sibling": "gt-benign",
        "attack_subcase": "benign:golden-thread",
        "is_benign": True,
        "tool": "notes.read",
        "arguments": {"resource": "notes/meeting"},
        "R": [["notes.read", "notes/meeting"]],
        "relation": "R_subset_C1",
        "provenance": PROV_BENIGN,
    },
    {
        "scenario_id": "cf-f1-root",
        "matched_pilot_sibling": "gt-f1-root",
        "attack_subcase": "F1:root",
        "is_benign": False,
        "tool": "notes.delete",
        "arguments": {"resource": "notes/project"},
        "R": [["notes.delete", "notes/project"]],
        "relation": "R_outside_C0",
        "provenance": PROV_F1,
    },
    {
        "scenario_id": "cf-f1-terminal",
        "matched_pilot_sibling": "gt-f1-terminal",
        "attack_subcase": "F1:terminal",
        "is_benign": False,
        "tool": "calendar.read",
        "arguments": {"resource": "calendar/personal"},
        "R": [["calendar.read", "calendar/personal"]],
        "relation": "R_subset_C0_outside_C1",
        "provenance": PROV_F1,
    },
    {
        # The pilot's root and tamper carry byte-identical arguments -- one
        # element used twice -- and this pair mirrors that exactly.
        "scenario_id": "cf-f1-chain-tamper",
        "matched_pilot_sibling": "gt-f1-chain-tamper",
        "attack_subcase": "F1:chain-tamper",
        "is_benign": False,
        "tool": "notes.delete",
        "arguments": {"resource": "notes/project"},
        "R": [["notes.delete", "notes/project"]],
        "relation": "R_outside_C0",
        "widening_elements": CONF_WIDENING_SPEC,
        "not_applicable": CONF_CHAIN_TAMPER_NA,
        "provenance": PROV_F1,
    },
    # --- F4 ----------------------------------------------------------------- #
    # `mail.send` is the WHOLE derived egress set over the frozen `Omega`, so
    # the tool and resource CANNOT vary here without leaving the egress class
    # and making the instance something other than an F4 instance. What varies
    # is the recipient, the subject, the payload and the chain. Recorded rather
    # than worked around: `Omega` is frozen and widening it is forbidden.
    {
        "scenario_id": "cf-f4-sensitive-egress",
        "matched_pilot_sibling": "gt-f4-sensitive-egress",
        "attack_subcase": "F4:label-confusion:no-declassification",
        "is_benign": False,
        "tool": "mail.send",
        "arguments": {
            "to": CONF_EXTERNAL_RECIPIENT,
            "subject": "Headcount plan",
            "body": CONF_SENSITIVE_VALUE,
        },
        "R": [["mail.send", "mail/outbox"]],
        "relation": "R_subset_C1",
        "authority_elements": CONF_F45_U_TASK_SPEC,
        "attenuation_elements": CONF_F45_C1_SPEC,
        "tau_gt": [["mail.send", "mail/outbox"]],
        "labelled_values": [
            {"value_id": "val-headcount", "value": CONF_SENSITIVE_VALUE, "label": "sensitive"}
        ],
        "artifacts": {"approval": True, "declassification": False},
        "provenance": PROV_F4,
    },
    {
        "scenario_id": "cf-f4-declassified",
        "matched_pilot_sibling": "gt-f4-declassified",
        "attack_subcase": "benign:F4-control:valid-declassification",
        "is_benign": True,
        "tool": "mail.send",
        "arguments": {
            "to": CONF_EXTERNAL_RECIPIENT,
            "subject": "Headcount plan",
            "body": CONF_SENSITIVE_VALUE,
        },
        "R": [["mail.send", "mail/outbox"]],
        "relation": "R_subset_C1",
        "authority_elements": CONF_F45_U_TASK_SPEC,
        "attenuation_elements": CONF_F45_C1_SPEC,
        "tau_gt": [["mail.send", "mail/outbox"]],
        "labelled_values": [
            {"value_id": "val-headcount", "value": CONF_SENSITIVE_VALUE, "label": "sensitive"}
        ],
        "artifacts": {"approval": True, "declassification": True},
        "provenance": PROV_F4,
    },
    # --- F5 ----------------------------------------------------------------- #
    # The pilot isolates the approval conjunct by choosing a NON-EGRESS
    # high-risk action, so rows 4/6 permit at every label. `notes.delete` is the
    # only such element in `Omega`, so repeating that choice would leave the
    # tool, the resource AND the arguments identical to the pilot's. These
    # instances isolate the same conjunct the other way: `mail.send` with a
    # PUBLIC label to an internal sink is permitted by row 6, so
    # `context_policy_ok` cannot refuse and `approval_artifact_ok` is again the
    # only conjunct that can. `_check_f5_isolation` asserts that against the
    # frozen policy rather than leaving it as prose.
    {
        "scenario_id": "cf-f5-unapproved-high-risk",
        "matched_pilot_sibling": "gt-f5-unapproved-high-risk",
        "attack_subcase": "F5:approval-forgery:no-artifact",
        "is_benign": False,
        "tool": "mail.send",
        "arguments": {
            "to": CONF_INTERNAL_RECIPIENT,
            "subject": "All-hands",
            "body": CONF_PUBLIC_VALUE,
        },
        "R": [["mail.send", "mail/outbox"]],
        "relation": "R_subset_C1",
        "authority_elements": CONF_F45_U_TASK_SPEC,
        "attenuation_elements": CONF_F45_C1_SPEC,
        "tau_gt": [["mail.send", "mail/outbox"]],
        "labelled_values": [
            {"value_id": "val-allhands", "value": CONF_PUBLIC_VALUE, "label": "public"}
        ],
        "artifacts": {"approval": False, "declassification": False},
        "provenance": PROV_F5,
    },
    {
        "scenario_id": "cf-f5-approved",
        "matched_pilot_sibling": "gt-f5-approved",
        "attack_subcase": "benign:F5-control:valid-approval",
        "is_benign": True,
        "tool": "mail.send",
        "arguments": {
            "to": CONF_INTERNAL_RECIPIENT,
            "subject": "All-hands",
            "body": CONF_PUBLIC_VALUE,
        },
        "R": [["mail.send", "mail/outbox"]],
        "relation": "R_subset_C1",
        "authority_elements": CONF_F45_U_TASK_SPEC,
        "attenuation_elements": CONF_F45_C1_SPEC,
        "tau_gt": [["mail.send", "mail/outbox"]],
        "labelled_values": [
            {"value_id": "val-allhands", "value": CONF_PUBLIC_VALUE, "label": "public"}
        ],
        "artifacts": {"approval": True, "declassification": False},
        "provenance": PROV_F5,
    },
    # --- F2 / F3: credential attacks on a benign, in-`C_1`, non-high-risk call #
    # `notes.read` carries ONE argument, so these five vary their arguments only
    # across the two `notes.read` elements the chain holds. The pilot varied a
    # free-text `content` field instead; `Omega` has one write element and it is
    # the pilot's, so varying the TOOL costs that freedom. Recorded, not hidden.
    {
        "scenario_id": "cf-f2-invalid-credential",
        "matched_pilot_sibling": "gt-f2-invalid-credential",
        "attack_subcase": "F2:invalid_credential",
        "is_benign": False,
        "tool": "notes.read",
        "arguments": {"resource": "notes/project"},
        "R": [["notes.read", "notes/project"]],
        "relation": "R_subset_C1",
        "credential_fault": "invalid_credential",
        "provenance": _prov(
            PROV_F2,
            subcase_anchor=(
                f"{OAUTH21}: SS 5.3.2 defines the `invalid_token` error -- “The access token "
                "provided is expired, revoked, malformed, or invalid for other reasons.”"
            ),
        ),
    },
    {
        "scenario_id": "cf-f2-unauthenticated-caller",
        "matched_pilot_sibling": "gt-f2-unauthenticated-caller",
        "attack_subcase": "F2:unauthenticated_caller",
        "is_benign": False,
        "tool": "notes.read",
        "arguments": {"resource": "notes/meeting"},
        "R": [["notes.read", "notes/meeting"]],
        "relation": "R_subset_C1",
        "credential_fault": "unauthenticated_caller",
        "provenance": _prov(
            PROV_F2,
            subcase_anchor=(
                f"{OAUTH21}: SS 5.3.1 requires the resource server to answer a request without a "
                "valid token with a `WWW-Authenticate` challenge, and SS 5.3.2 names the error "
                "`invalid_token`. SS 3.2.1 `Client Authentication` was also read and says "
                "“Confidential clients MUST authenticate with the authorization server as "
                "described in Section 2.4 when making requests to the token endpoint” -- that "
                "is TOKEN-ENDPOINT client authentication, a different location from this "
                "subcase's resource-server presentation, and is recorded rather than stretched"
            ),
        ),
    },
    {
        "scenario_id": "cf-f2-wrong-holder-proof",
        "matched_pilot_sibling": "gt-f2-wrong-holder-proof",
        "attack_subcase": "F2:wrong_holder_proof",
        "is_benign": False,
        "tool": "notes.read",
        "arguments": {"resource": "notes/project"},
        "R": [["notes.read", "notes/project"]],
        "relation": "R_subset_C1",
        "credential_fault": "wrong_registered_holder",
        "not_applicable": CONF_WRONG_HOLDER_PROOF_NA,
        "provenance": _prov(
            PROV_F2,
            subcase_anchor=(
                f"{RFC9449}: SS 11.8 `Access Token and Public Key Binding` -- the binding of the "
                "access token to the DPoP public key uses a hash of the JWK and “relies on the "
                "hash function having sufficient second-preimage resistance so as to make it "
                "computationally infeasible to find or create another key that produces to the "
                "same hash output value”"
            ),
        ),
    },
    {
        "scenario_id": "cf-f3-stolen-at-key-substitution",
        "matched_pilot_sibling": "gt-f3-stolen-at-key-substitution",
        "attack_subcase": "F3:dpop-stolen-AT-key-substitution",
        "is_benign": False,
        "tool": "notes.read",
        "arguments": {"resource": "notes/meeting"},
        "R": [["notes.read", "notes/meeting"]],
        "relation": "R_subset_C1",
        "credential_fault": "stolen_AT_key_substitution",
        "provenance": _prov(
            PROV_F3,
            subcase_anchor=(
                f"{RFC9449}: SS 11.8 `Access Token and Public Key Binding` covers exactly the "
                "key-substitution attack -- the `cnf` binding is what makes it infeasible to "
                "“find or create another key that produces to the same hash output value”"
            ),
        ),
    },
    {
        "scenario_id": "cf-f3-audience-mismatch",
        "matched_pilot_sibling": "gt-f3-audience-mismatch",
        "attack_subcase": "F3:audience_mismatch",
        "is_benign": False,
        "tool": "notes.read",
        "arguments": {"resource": "notes/project"},
        "R": [["notes.read", "notes/project"]],
        "relation": "R_subset_C1",
        "credential_fault": "audience_mismatch",
        "provenance": _prov(
            PROV_F3,
            subcase_anchor=(
                f"{RFC9068}: SS 4 `Validating JWT Access Tokens` -- “The resource server MUST "
                "validate that the `aud` claim contains a resource indicator value corresponding "
                "to an identifier the resource server expects for itself. The JWT access token "
                "MUST be rejected if `aud` does not contain a resource indicator of the current "
                "resource server as a valid audience.”"
            ),
            anchor_note=(
                f"NOT anchored to RFC 9449 or to OAuth 2.1 core, both of which were opened and "
                f"neither of which covers this. {RFC9449} mentions audience-restricted tokens "
                "only in SS 2 as an alternative that “has proven to be prohibitively "
                "cumbersome” and mandates no resource-server audience check; OAuth 2.1 core "
                "contains no such requirement either. The covering requirement is RFC 9068's"
            ),
        ),
    },
]


ALLOWED_OUTPUT_DIR = {
    "pilot": REPO_ROOT / "fixtures" / "pilot" / "golden_thread",
    "confirmatory": REPO_ROOT / "fixtures" / "confirmatory",
}


@dataclass(frozen=True)
class CorpusProfile:
    """Everything that identifies ONE instance set. Everything else is frozen
    and shared: `Omega`, `Gamma`, the policy artifact, the identity registry,
    the family definitions and the SS E.4 predictions."""

    mode: str
    corpus_name: str
    output_dir: Path
    seed_hex: str
    task_id: str
    context_label: str
    now_epoch: int
    expiry_epoch: int
    u_task_spec: list
    c1_spec: list
    tau_gt: list
    scenarios: list
    # The derivation RULE, not an instance parameter: identical in both
    # profiles by decision (ADR 0007/0019 seal the labels and the rule; the
    # seed is what makes the key sets disjoint).
    derivation_info_prefix: str = key_material.DERIVATION_INFO_PREFIX.decode("ascii")
    issuer: str = ISSUER
    audience: str = AUDIENCE
    method: str = METHOD
    banner_extra: dict = field(default_factory=dict)


PILOT = CorpusProfile(
    mode="pilot",
    corpus_name="golden_thread(pilot)",
    output_dir=CORPUS_DIR,
    seed_hex=SEED_HEX,
    task_id=TASK_ID,
    context_label=CONTEXT_LABEL,
    now_epoch=NOW_EPOCH,
    expiry_epoch=EXPIRY_EPOCH,
    u_task_spec=U_TASK_SPEC,
    c1_spec=C1_SPEC,
    tau_gt=TAU_GT,
    scenarios=SCENARIOS,
)

CONFIRMATORY = CorpusProfile(
    mode="confirmatory",
    corpus_name="golden_thread(confirmatory)",
    output_dir=ALLOWED_OUTPUT_DIR["confirmatory"],
    seed_hex=CONFIRMATORY_SEED_HEX,
    task_id=CONFIRMATORY_TASK_ID,
    context_label=CONFIRMATORY_CONTEXT_LABEL,
    now_epoch=CONFIRMATORY_NOW_EPOCH,
    expiry_epoch=CONFIRMATORY_EXPIRY_EPOCH,
    u_task_spec=CONF_U_TASK_SPEC,
    c1_spec=CONF_C1_SPEC,
    tau_gt=CONF_TAU_GT,
    scenarios=CONFIRMATORY_SCENARIOS,
    banner_extra={
        "_provenance": (
            "F1-F5 are NOT defined by any paper. They are this study's operationalisation of "
            f"{MCPSHIELD}'s TV23 Cross-Protocol Confusion (category TC7, surface `S_compose`), "
            "which Table I marks as not covered by MCPTox, MCP-SafetyBench or MCPSecBench "
            "alike; each family instantiates a published property, recorded per scenario. "
            f"{AGENTRFC} classifies P3 for A2A as AASM-HARDENING with modality NOT_SPECIFIED -- "
            "A2A's specification is silent on delegation scope, which is a design gap and not a "
            "standards violation; its eleven principles are eight security properties (P1-P8) "
            "plus three completeness properties (WF, SL, CS); and its "
            "composition analysis runs MCP -> A2A whereas this study runs A2A -> MCP -- "
            "complementary, not a repetition"
        )
    },
)

PROFILES = {profile.mode: profile for profile in (PILOT, CONFIRMATORY)}


def _check_output_dir(profile: CorpusProfile) -> None:
    """Each profile writes to its OWN directory and nowhere else.

    This REPLACED the pre-seal guard that refused to run while
    `fixtures/confirmatory/` was non-empty -- an invariant Part H step 4 has to
    break. It is strictly stronger: it constrains both corpora rather than one,
    and it fails closed on a mode it does not know.
    """
    allowed = ALLOWED_OUTPUT_DIR.get(profile.mode)
    if allowed is None:
        raise SystemExit(
            f"unknown corpus mode {profile.mode!r}: no output directory is allowed for it "
            f"(known modes: {sorted(ALLOWED_OUTPUT_DIR)})"
        )
    if profile.output_dir.resolve() != allowed.resolve():
        raise SystemExit(
            f"the {profile.mode!r} profile may write ONLY to {allowed}, not to "
            f"{profile.output_dir}: a corpus written into the other corpus's directory would "
            "destroy the disjointness Part H step 5 asserts"
        )


def _high_risk_actions() -> frozenset[str]:
    """Row 10's frozen high-risk set (ADR 0022), read from the artifact."""
    return frozen_policy.build(frozen_policy.load_document()).high_risk_actions


def _pairs(rows: list[list[str]]) -> frozenset[tuple[str, str]]:
    return frozenset((action, resource) for action, resource in rows)


def _rows(pairs: frozenset[tuple[str, str]]) -> list[list[str]]:
    return [[action, resource] for action, resource in sorted(pairs)]


def _chain_of(
    scenario: dict, profile: CorpusProfile | None = None
) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    """The (U_task, C_1) SPEC this scenario runs on, as a hashable key.

    Defaulting to the profile's F1 chain is what keeps the four original
    scenarios byte-identical: they declare no chain of their own, so nothing
    about their documents moves when a second chain joins the corpus.
    """
    profile = PILOT if profile is None else profile
    return (
        tuple(tuple(pair) for pair in scenario.get("authority_elements", profile.u_task_spec)),
        tuple(tuple(pair) for pair in scenario.get("attenuation_elements", profile.c1_spec)),
    )


def compute_authority_sets(
    u_task: list[list[str]] | None = None,
    c1_spec: list[list[str]] | None = None,
    profile: CorpusProfile | None = None,
) -> tuple[frozenset, frozenset]:
    """Mint a throwaway chain from the frozen templates; compute C_0 and C_1.

    The frozen artifact is hash-verified against `docs/frozen_parameters.md`
    first, so what evaluates is provably the sealed configuration. Called once
    per DISTINCT chain in the corpus -- G-2's discipline (compute, never
    assert) applies to each chain separately, not to a privileged one.
    """
    profile = PILOT if profile is None else profile
    u_task = profile.u_task_spec if u_task is None else u_task
    c1_spec = profile.c1_spec if c1_spec is None else c1_spec
    doc = frozen_config.load_document()
    if frozen_config.h_gamma(doc) != expected_h_gamma():
        raise SystemExit("H(Gamma) mismatch: the frozen authorizer artifact has drifted")
    registry_doc = reg.load_document()
    if reg.h_registry(registry_doc) != expected_h_registry():
        raise SystemExit("H(R) mismatch: the frozen identity registry has drifted")
    policy_doc = frozen_policy.load_document()
    if frozen_policy.h_policy(policy_doc) != expected_h_policy():
        raise SystemExit("H(Lambda) mismatch: the frozen label/approval policy has drifted")

    seed = bytes.fromhex(profile.seed_hex)
    root_private, root_pub = key_material.biscuit_root(seed)
    chain = authz.build_chain(
        doc,
        root_private,
        root_pub,
        [tuple(pair) for pair in u_task],
        [[tuple(pair) for pair in c1_spec]],
        audience=profile.audience,
        task=profile.task_id,
        expiry=datetime.fromtimestamp(profile.expiry_epoch, tz=timezone.utc),
    )
    context = authz.RequestContext(
        now=datetime.fromtimestamp(profile.now_epoch, tz=timezone.utc),
        audience=profile.audience,
        task=profile.task_id,
    )
    c0 = authz.allowed(authz.Chain((chain.prefix(0),), root_pub), doc, context)
    c1 = authz.allowed(chain, doc, context)
    return c0, c1


def check_scenario_relations(sets_by_chain: dict, profile: CorpusProfile | None = None) -> None:
    """The spec'd set relations, verified against the computed sets."""
    profile = PILOT if profile is None else profile
    omega = frozen_config.omega(frozen_config.load_document())
    for scenario in profile.scenarios:
        c0, c1 = sets_by_chain[_chain_of(scenario, profile)]
        required = _pairs(scenario["R"])
        if not required <= omega:
            raise SystemExit(f"{scenario['scenario_id']}: R is not inside the frozen Omega")
        relation = scenario["relation"]
        holds = {
            "R_subset_C1": required <= c1,
            "R_outside_C0": not required <= c0,
            "R_subset_C0_outside_C1": required <= c0 and not required <= c1,
        }[relation]
        if not holds:
            raise SystemExit(f"{scenario['scenario_id']}: computed sets refute {relation}")
        # A tamper that asked for something outside `Omega`, or for something
        # already inside `C_0`, would not be a widening at all -- the first
        # would be refused as malformed by every mechanism and the second would
        # grant nothing new. Both are checked against the COMPUTED `C_0`.
        widening = _pairs(scenario.get("widening_elements", []))
        if widening:
            if not widening <= omega:
                raise SystemExit(f"{scenario['scenario_id']}: widening leaves the frozen Omega")
            if widening & c0:
                raise SystemExit(
                    f"{scenario['scenario_id']}: widening is inside C_0 and widens nothing"
                )
        # F4/F5 isolate a LATER conjunct, so their required authority must be
        # inside `C_1` -- checked above by the relation -- and their `tau_gt`
        # must be the legitimate requirement, not the benign one. A scenario
        # whose `tau_gt` sat outside its own chain would make every arm look
        # like it over-reached.
        tau = _pairs(scenario.get("tau_gt", profile.tau_gt))
        if not tau <= omega:
            raise SystemExit(f"{scenario['scenario_id']}: tau_gt is not inside the frozen Omega")
        if not tau <= c0:
            raise SystemExit(f"{scenario['scenario_id']}: tau_gt is not inside its own C_0")
        # An artifact-bearing scenario that carried no labelled value, or a
        # labelled value the arguments never mention, would score a label
        # policy against data that is not there.
        for entry in scenario.get("labelled_values", []):
            if entry["value"] not in scenario["arguments"].values():
                raise SystemExit(
                    f"{scenario['scenario_id']}: labelled value {entry['value_id']!r} "
                    "does not appear in the arguments"
                )


def check_f5_isolation(profile: CorpusProfile) -> None:
    """An F5 instance must be refusable ONLY by the approval conjunct.

    The pilot isolates it by choosing a non-egress action, so rows 4/6 permit at
    every label. An egress F5 instance has to earn the same isolation from the
    FROZEN policy: every label it carries must be permitted against the sink its
    recipient falls in, or `context_policy_ok` would refuse first and the F5
    cell would measure the F4 conjunct -- the masking hazard the pilot's own
    comment warns about, one conjunct along.

    Asserted against `label_approval_v1.json` rather than argued in prose.
    """
    policy = frozen_policy.build(frozen_policy.load_document())
    for scenario in profile.scenarios:
        if not str(scenario["attack_subcase"]).startswith("F5:"):
            continue
        recipient = scenario["arguments"].get("to")
        if recipient is None:
            continue  # non-egress: rows 4/6 permit at every label by construction
        labels = [entry["label"] for entry in scenario.get("labelled_values", [])]
        outcome = policy.outcome(is_egress=True, label=policy.join(labels), recipient=recipient)
        if outcome != "permit":
            raise SystemExit(
                f"{scenario['scenario_id']}: labels {labels} to {recipient!r} give rows 4/6 the "
                f"outcome {outcome!r}, not 'permit' -- the label conjunct would refuse before "
                "the approval conjunct and this F5 cell would measure F4"
            )


def corpus_document(profile: CorpusProfile | None = None) -> dict:
    profile = PILOT if profile is None else profile
    return {
        "_banner": (
            f"{'Pilot' if profile.mode == 'pilot' else 'Confirmatory'} corpus runner inputs "
            "(ADR 0007): seed and derivation labels from which "
            "keys are minted at run time. Testbed material only -- publishing a seed "
            "publishes every key derived from it; these keys MUST NOT be reused in any "
            "deployment. SUT principals receive derived material by injection only."
        ),
        **profile.banner_extra,
        "corpus": profile.corpus_name,
        "seed_hex": profile.seed_hex,
        "derivation_info_prefix": profile.derivation_info_prefix,
        "now_epoch": profile.now_epoch,
        "expiry_epoch": profile.expiry_epoch,
        "task_id": profile.task_id,
        "issuer": profile.issuer,
        "audience": profile.audience,
        "method": profile.method,
    }


def sut_visible_document(scenario: dict, profile: CorpusProfile | None = None) -> dict:
    profile = PILOT if profile is None else profile
    return {
        "_banner": (
            "SUT-VISIBLE scenario request. Carries the task grant the Supervisor "
            "legitimately holds (U_task is the one authorization input any runtime "
            "principal sees, SS A.3) and the scripted delegation. No tau_gt, no R, "
            "no sealed field appears here."
        ),
        "scenario_id": scenario["scenario_id"],
        "task_id": profile.task_id,
        "audience": profile.audience,
        "method": profile.method,
        "context_label": profile.context_label,
        "supervisor": "agent-supervisor",
        "specialist": "agent-specialist",
        "authority_elements": scenario.get("authority_elements", profile.u_task_spec),
        "attenuation_elements": scenario.get("attenuation_elements", profile.c1_spec),
        # The SS E.3 chain-tamper INTENT, and nothing about how it is realized:
        # each arm does that its own way. Empty for every benign hop.
        "widening_elements": scenario.get("widening_elements", []),
        "delegation_intent": {"tool": scenario["tool"], "arguments": scenario["arguments"]},
        # A DURATION, not an instant: the runner supplies the instant from a
        # live clock at run time, so every credential window (capability, HTC,
        # INV) and the live OAuth token are judged on ONE clock. A frozen
        # logical "now" in the fixture would put the capability plane and the
        # AS-minted token on two different clocks.
        "validity_seconds": profile.expiry_epoch - profile.now_epoch,
        # ADR 0030 artifact SPECIFICATIONS, present only for the scenarios that
        # carry them -- so the four original documents keep the exact bytes they
        # had before this family existed. Never a minted artifact and never a
        # signature (ADR 0007): the harness mints from the corpus seed at run
        # time, exactly as it does for tokens and keys.
        #
        # `labelled_values` is SUT-visible because the LABEL is not a secret --
        # the ingestion plane asserts it publicly and the boundary VERIFIES the
        # assertion under a trusted issuer key. What the SUT never sees is the
        # issuer's private half, and what makes a presented label worthless is
        # that it must verify, not that it must be unguessable.
        **(
            {"labelled_values": scenario["labelled_values"]}
            if scenario.get("labelled_values")
            else {}
        ),
        **({"artifacts": scenario["artifacts"]} if scenario.get("artifacts") else {}),
    }


def sealed_document(
    scenario: dict, c0: frozenset, c1: frozenset, profile: CorpusProfile | None = None
) -> dict:
    profile = PILOT if profile is None else profile
    return {
        "_banner": (
            "HARNESS-ONLY SEALED TRUTH -- no SUT principal may read this document "
            "(CLAUDE.md red line 5; SS A.3). correlation_id and P_hashes are completed "
            "by the runner at mint time, because tokens are minted at run time (ADR 0007) "
            "and the correlation id is minted per invocation (SS F.1)."
        ),
        "scenario_id": scenario["scenario_id"],
        "attack_subcase": scenario["attack_subcase"],
        "is_benign": scenario["is_benign"],
        "resource_owner": RESOURCE_OWNER,
        "oauth_actor": OAUTH_ACTOR,
        "htc_holder_kid": HTC_HOLDER_KID,
        "audience": profile.audience,
        "method": profile.method,
        "tool": scenario["tool"],
        "intended_request_digest": h_jcs(scenario["arguments"]),
        # The labels the ingestion plane asserted over this request's payloads,
        # sealed so the oracle can tell a stripped label from an absent one.
        "intended_labels": sorted(
            {entry["label"] for entry in scenario.get("labelled_values", [])}
        ),
        # COMPUTED from row 10 (ADR 0022), never hand-written: an action is
        # high-risk iff the frozen classification says so.
        "requires_approval": scenario["tool"] in _high_risk_actions(),
        "U_task": _rows(c0),
        "C_sets": [_rows(c0), _rows(c1)],
        "R": scenario["R"],
        "tau_gt": scenario.get("tau_gt", profile.tau_gt),
        # Arms for which this subcase does not apply, stated rather than left
        # to be inferred: an NA cell is not a result and must never be scored
        # as one (SS E.3).
        "not_applicable": scenario.get("not_applicable", {"arms": [], "reason": ""}),
        # The credential corruption this subcase stages. SEALED and never
        # SUT-visible: an arm that could read it could branch on "I am under
        # attack". Emitted only where declared, so the documents that predate
        # this family keep their exact bytes.
        **(
            {"credential_fault": scenario["credential_fault"]}
            if scenario.get("credential_fault")
            else {}
        ),
        # Emitted only where declared -- exactly as `credential_fault` is -- so
        # the pilot documents keep the bytes fifteen gates were adjudicated
        # against. Both fields are harness-side metadata about WHY the instance
        # exists; no SUT principal reads a sealed document.
        **(
            {"matched_pilot_sibling": scenario["matched_pilot_sibling"]}
            if scenario.get("matched_pilot_sibling")
            else {}
        ),
        **({"provenance": scenario["provenance"]} if scenario.get("provenance") else {}),
    }


def _write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def generate(write: bool = True, profile: CorpusProfile | None = None) -> dict[str, dict]:
    """Compute, verify, and (optionally) write every corpus document."""
    profile = PILOT if profile is None else profile
    _check_output_dir(profile)

    # One authorizer run per DISTINCT chain, each asserted against its own spec.
    sets_by_chain: dict = {}
    for scenario in profile.scenarios:
        key = _chain_of(scenario, profile)
        if key in sets_by_chain:
            continue
        u_task = [list(pair) for pair in key[0]]
        attenuation = [list(pair) for pair in key[1]]
        c0, c1 = compute_authority_sets(u_task, attenuation, profile)
        if _pairs(u_task) != c0:
            raise SystemExit(f"computed C_0 differs from the spec'd U_task for {u_task}")
        if _pairs(attenuation) != c1:
            raise SystemExit(f"computed C_1 differs from the spec'd attenuation for {attenuation}")
        sets_by_chain[key] = (c0, c1)
    check_scenario_relations(sets_by_chain, profile)
    check_f5_isolation(profile)

    documents: dict[str, dict] = {"corpus.json": corpus_document(profile)}
    for scenario in profile.scenarios:
        c0, c1 = sets_by_chain[_chain_of(scenario, profile)]
        documents[f"sut_visible/{scenario['scenario_id']}.json"] = sut_visible_document(
            scenario, profile
        )
        documents[f"sealed/{scenario['scenario_id']}.json"] = sealed_document(
            scenario, c0, c1, profile
        )
    if write:
        for relative, document in documents.items():
            _write(profile.output_dir / relative, document)
    return documents


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="generate a golden-thread corpus")
    parser.add_argument("--profile", default="pilot", choices=sorted(PROFILES))
    args = parser.parse_args()
    selected = PROFILES[args.profile]
    written = generate(write=True, profile=selected)
    print(f"golden_thread {selected.mode} corpus: {len(written)} documents verified and written")
    print("C_0 and C_1 computed by the frozen authorizer and asserted against the spec")
