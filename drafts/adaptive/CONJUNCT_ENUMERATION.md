# Conjunct-falsifiability enumeration — the pre-registration for adaptive validation

**Phase A. Nothing is instantiated. No campaign was run, no sealed artefact modified.**
Status: written BEFORE any adaptive attack exists, and committed as the pre-registration that
binds Phase B to report every cell's outcome as returned.

Every number below is tagged **[M]** measured this session from a named file, or **[D]** derived
by stated arithmetic from [M] values. Nothing is remembered and nothing is estimated.

---

## 0. Two things to settle before the table can be read

### 0.1 A terminological collision in the task, surfaced rather than silently resolved

The task defines **FALSIFIABLE** as *"an adversary with this capability can make this conjunct
false at this tampering point … and which arms would then admit."* Under that definition, a
conjunct is FALSIFIABLE exactly when it **fires** — it evaluates false, the arms carrying it
**block**, and the arms lacking it **admit**. FALSIFIABLE is therefore a statement that the
conjunct *catches* the attack.

The task's expected finding 2 uses the opposite sense: *"R ⊆ Cₙ is expected to remain
**unfalsifiable** under K-holder, since a scope bound holds regardless of who holds the key … a
positive result about what scope containment still **guarantees**."* There, "unfalsifiable" means
the adversary cannot **evade** it.

These are inverses. A conjunct that catches everything is maximally FALSIFIABLE in sense 1 and
maximally unfalsifiable in sense 2. Left unresolved this would make the headline result
unreadable, so this document reports **both axes explicitly** for every cell:

| Axis | Question | Values |
|---|---|---|
| **FIRES** (the task's formal definition) | Can the adversary make this conjunct evaluate **false** here? | FALSIFIABLE / STRUCTURALLY UNREACHABLE / OUT OF MODEL / NOT EXPRESSIBLE |
| **EVADABLE** (finding 2's sense) | Can the adversary get this conjunct to evaluate **true** while the attack still succeeds? | EVADABLE / UNEVADABLE / n/a |

The four labels the task specifies are used verbatim on the FIRES axis. The EVADABLE axis is
additional and is marked as such.

### 0.2 Source register, and one wrong-scope near-miss recorded

The task's rules warn that this project has produced three false negatives from searching the
wrong scope. This pass nearly produced a fourth and it is recorded rather than tidied away: the
dissertation was searched for **inside** the repository, found absent, and was one step from being
reported as a red state. It is not missing — it sits one directory **above** the repository, at
`e:/Dissertation/Agentic AI/Glasgow_MSc_Project___Yixian_2026 (2)/mproj.tex` [M]. No red state
exists. The lesson is the same one the rule states: a negative result is only as good as the scope
it was searched in, and the scope must be named.

| Task's citation | Actual authoritative source | Evidence |
|---|---|---|
| §3.3.3's ten conjuncts | Equation 3.1 in `mproj.tex:724-737`, implemented in `src/sut/authz/capability_path.py:161-172` (`CONJUNCT_ORDER`) and dispatched at `:473-483` | [M] |
| Table 3.1's five tampering points | `mproj.tex:574-599` (`tab:tampering`) | [M] |
| §3.2.3's two key-possession classes | `mproj.tex:562-568` (prose above the table) | [M] |
| §D.1's out-of-scope premises | `mproj.tex:552-558` (in-process boundary; transport assumed) **and** Appendix A "Trust Assumptions" `mproj.tex:1425-1438` (five components) | [M] |
| Appendix B module vector | `mproj.tex:1507-1573` (`tab:module-vector`) | [M] |

Cross-check: the repository's own single-source-of-truth carries the same taxonomy under different
numbering — `docs/EXPERIMENT_ARCHITECTURE_FINAL.md:199` (tampering points and key classes, as
T-reuse / T-tool / T-args / T-scope / T-replay and K-none / K-holder), `:178-184` (§D.1, H4a/H4b),
`:201-209` (the existing partial matrix). The dissertation's Table 3.1 uses prose names; the
architecture doc uses the T-codes. **They agree cell for cell** [M]. This document uses the
dissertation's names with the T-codes in brackets, because the task names the dissertation.

---

## 1. The ten conjuncts, named as the admission rule names them

Equation 3.1 (`mproj.tex:726-737`) states: admit ⟺ the conjunction of ten conditions. The mapping
to implementation is one-to-one and is **[M]**, not assumed:

| # | Eq. 3.1 name | Implementation | Body | Reason code |
|---|---|---|---|---|
| 1 | chain-verified(Pₙ, κ) | `crypto_chain_ok` | `capability_path.py:584-607` | `b3_crypto_chain` |
| 2 | authorizer-permits(Γ, Pₙ) | `authorizer_policy_ok` | `:609-640` | `b3_authorizer_policy` |
| 3 | certificate-chain-valid | `htc_chain_ok` | `:642-707` | `b3_htc_chain` |
| 4 | holder-proof-valid | `holder_proof_ok` | `:709-724` | `b3_holder_proof` |
| 5 | invocation-bound | `invocation_binding_ok` | `:726-787` | `b3_invocation_binding` |
| 6 | R ⊆ Cₙ | `containment_ok` | `:797-816` | `b3_containment` |
| 7 | label-policy-satisfied | `context_policy_ok` | `:818-872` | `b3_context_policy` |
| 8 | approval-valid | `approval_artifact_ok` | `:896-927` | `b3_approval_artifact` |
| 9 | resource-authorized | `oauth_resource_authorization_ok` | `:929-953` | `b3_oauth_resource_authorization` |
| 10 | identity-consistent | `identity_plane_consistency_ok` | `:955-985` | `b3_identity_plane_consistency` |

**Evaluation is short-circuiting in `CONJUNCT_ORDER`** (`:487-495`): the first failure names the
block and conjuncts after it are never evaluated. This is load-bearing for §3 and is the reason a
conjunct can be false without ever being observed false.

**The `jti` replay cache is deliberately not one of the ten** (`capability_path.py:498-504`,
verbatim: *"it is not an SS A.5 conjunct — SS A.5 lists ten and this is not one of them"*). It is
consumed after all ten pass and before the tool executes (`:515-551`). This matters at tampering
point T5 and is the whole of B3⁺'s distinction from B3.

---

## 2. Module vector — corrected against a descriptive/operative distinction

The task asks which arms evaluate each conjunct "from the module vector". Taking
`ArmBitmask.enabled_conjuncts()` at face value across all nine arms produces a **wrong** answer,
and the correction is itself a finding.

`enabled_conjuncts()` is consulted **only** by arms that construct a `CapabilityDecisionPath` —
that is `B3` (`b3.py:119,130`), `B3⁺`, and `B-cap` (`b_cap.py:47`, `class BCapArm(B3Arm)`). For
every other arm the bitmask is **descriptive metadata about the mechanism**, not a selector.
`b2_dpop.py:95-99` states it in the source: *"the column is non-zero because the arm IS
holder-bound. It selects no SS A.5 conjunct — this arm runs no `CapabilityDecisionPath` at all, so
`enabled_conjuncts()` is not consulted for it."* Appendix B's footnotes (a) and (b) make the same
distinction in the dissertation (`mproj.tex:1563-1568`): B2-exchange-task's containment is
"enforced by the scope of the token the authorization server issues rather than by a component at
the boundary", and B2-DPoP's holder binding is "the proof-of-possession confirmation claim rather
than … a holder-transition chain".

**Which arms evaluate each §A.5 conjunct — operative [M]:**

| Conjunct | B0 | B1 | B2-bn | B2-eb | B2-et | B2-DPoP | B-cap | B3 | B3⁺ |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 chain-verified | — | — | — | — | — | — | ✔ | ✔ | ✔ |
| 2 authorizer-permits | — | — | — | — | — | — | ✔ | ✔ | ✔ |
| 3 certificate-chain-valid | — | — | — | — | — | — | — | ✔ | ✔ |
| 4 holder-proof-valid | — | — | — | — | — | — | — | ✔ | ✔ |
| 5 invocation-bound | — | — | — | — | — | — | — | ✔ | ✔ |
| 6 R ⊆ Cₙ | — | — | — | — | — | — | ✔ | ✔ | ✔ |
| 7 label-policy-satisfied | — | — | — | — | — | — | — | ✔ | ✔ |
| 8 approval-valid | — | — | — | — | — | — | — | ✔ | ✔ |
| 9 resource-authorized | — | — | — | — | — | — | ✔ | ✔ | ✔ |
| 10 identity-consistent | — | — | — | — | — | — | — | ✔ | ✔ |

Derived from `ArmBitmask.enabled_conjuncts()` restricted to the three `CapabilityDecisionPath`
arms [M]; B-cap's four are stated independently in `b_cap.py:25-28` and agree.

**"—" does not mean "no check".** The other six arms run functionally analogous checks in their
own reason-code namespaces, which is why the campaign records `b2_oauth_token_rejected` (8),
`b2_token_scope` (4), `b2dpop_holder_proof` (2), `b1_invalid_credential` (1) [M]. A Phase-B result
must therefore be reported as *"arms that carry conjunct C block; arms that do not carry C admit
**unless their own mechanism catches it**"* — never as "the system blocks".

---

## 3. What the campaign corpus actually exercises — the first expected finding

**Method.** For each B3/B3⁺ cell (`n = 34` [M], both arms carry all ten), the recorded
`reason_code_FOR_DIAGNOSIS_ONLY` determines exactly which conjuncts were *reached*: every conjunct
earlier in `CONJUNCT_ORDER` than the failing one was evaluated and passed; the failing one was
false; every later one was never evaluated. `b3_admitted` means all ten passed. This is exact, not
a sample.

| # | Conjunct | reached | passed | **falsified** | unreached (masked) |
|---|---|--:|--:|--:|--:|
| 1 | chain-verified | 34 | 34 | **0** | 0 |
| 2 | authorizer-permits | 34 | 34 | **0** | 0 |
| 3 | certificate-chain-valid | 34 | 34 | **0** | 0 |
| 4 | holder-proof-valid | 34 | 30 | 4 | 0 |
| 5 | invocation-bound | 30 | 30 | **0** | 4 |
| 6 | R ⊆ Cₙ | 30 | 24 | 6 | 4 |
| 7 | label-policy-satisfied | 24 | 14 | 10 | 10 |
| 8 | approval-valid | 14 | 12 | 2 | 20 |
| 9 | resource-authorized | 12 | 6 | 6 | 22 |
| 10 | identity-consistent | 6 | 6 | **0** | 28 |

All [M] from `results/raw/campaign-confirmatory.json`; columns sum to 34 per row as
`reached + unreached` [D].

### 3.1 The task's four candidates: three are wrong, one is right

The task nominated **label-policy-satisfied, approval-valid, resource-authorized and
identity-consistent** as candidates for "never targeted". Measured:

- **label-policy-satisfied — EXERCISED.** Falsified in 10 of the 24 cells that reached it. It is
  the *most* exercised conjunct in the corpus.
- **resource-authorized — EXERCISED.** Falsified 6 times.
- **approval-valid — EXERCISED.** Falsified 2 times.
- **identity-consistent — NOT EXERCISED.** 0 falsifications, and reached in only 6 of 34 cells.

Three of the four candidates are refuted. The finding the task predicted is real, but its
membership is different.

### 3.2 The conjuncts the corpus never falsifies, each with the scope its negative holds in

Short-circuiting means "never named as the block" is **not** the same as "never false". The scope
of each negative is set by how much of the conjunct's own column was reached:

| Conjunct | Verdict | Scope in which the negative holds |
|---|---|---|
| **chain-verified** | never falsified — **unconditional** | Position 1: nothing can mask it. Reached in 34/34. The corpus contains no instance in which the capability chain fails to verify under κ. |
| **authorizer-permits** | never falsified — **unconditional** | Position 2, and position 1 never fired, so it was reached 34/34. Genuinely never false. |
| **certificate-chain-valid** | never falsified — **unconditional** | Position 3, positions 1–2 never fired, reached 34/34. Genuinely never false. |
| **invocation-bound** | never falsified — **conditional** | Reached and passed in 30/34. On the 4 cells where holder-proof fired first it was **never evaluated**, so its value there is unknown. The negative holds on 30 of 34 cells, not on all 34. |
| **identity-consistent** | never falsified — **weak** | Reached in only **6** of 34 cells, all six admitted. On 28 cells it was never evaluated. The corpus establishes almost nothing about this conjunct: it has passed six times and been tested zero times. |

**Five of ten conjuncts are never falsified by the 143-cell campaign** [D: rows with falsified = 0].
Three of those five (chain-verified, authorizer-permits, certificate-chain-valid) are known
unconditionally never to have been false. One (invocation-bound) is unknown on 4 cells. One
(identity-consistent) is essentially unmeasured.

This is the answer to the task's first expected output, and it is the strongest single argument
for Phase B: **half the admission rule has never been put under load by the corpus that validates
it**, which is precisely the static-benchmark critique the task cites, arising inside this study's
own instrument.

---

## 4. Tampering points and key-possession classes

**Table 3.1** (`mproj.tex:574-599`) — five points, each with the key-possession case under which
the dissertation declares it **meaningful** [M]:

| # | Table 3.1 name | T-code | Definition (verbatim, condensed) | Meaningful under |
|---|---|---|---|---|
| T1 | Caller substitution | T-reuse | Presenting a captured credential as a caller other than the one to which it was issued | Captured credential |
| T2 | Tool substitution | T-tool | Substituting a different tool at the same endpoint after the request has been signed | Captured credential |
| T3 | Argument substitution | T-args | Substituting different arguments to the same tool after the request has been signed | Captured credential |
| T4 | Scope excess | T-scope | Requesting authority outside that carried by the credential presented | **Both key-possession** |
| T5 | Replay | T-replay | Resubmitting a bit-identical request within its validity window | Captured credential |

**Key possession** (`mproj.tex:562-568`) [M]:

- **K-none** — "holds only a captured credential and cannot produce a fresh signature under the
  terminal holder identity key".
- **K-holder** — "possesses that key, which corresponds to a compromised specialist agent and
  permits fresh signatures over requests of its own choosing".

The dissertation states the reason the axis is kept separate, and it pre-empts part of the matrix:
*"a tampering point meaningful against one can be vacuous against the other."* **Table 3.1 already
declares four of the five points vacuous under K-holder.** That is the model's own commitment, not
an inference of mine, and §6 shows it is structurally correct.

**Out-of-model premises** (`mproj.tex:552-558` and Appendix A `:1425-1438`) [M]:

- **P1** — network position at the A2A hop: *"Because the boundary is realised as an in-process
  call, an adversary positioned on the network at that hop falls outside the model."* Transport
  security is assumed to hold.
- **P2** — the AS issues only what its profile permits, and the label issuer labels correctly.
- **P3** — the mediation layer is complete; no tool call escapes observation.
- **P4** — the harness holds sealed material no SUT principal can reach. **This is what puts κ,
  the AS root signing key, the trusted label-issuer keys and the trusted approver keys beyond
  every adversary in the model.**
- **P5** — tools perform only the action requested, with no hidden side effect.

---

## 5. The reachability matrix

Read as: *at this tampering point, with this capability, can the adversary make this conjunct
evaluate **false**?* Labels are the task's four. `EV` gives the second axis from §0.1 — whether
the adversary can instead get the conjunct to pass while the attack succeeds.

Legend — **F** FALSIFIABLE · **SU** STRUCTURALLY UNREACHABLE · **OM** OUT OF MODEL ·
**NE** NOT EXPRESSIBLE. A superscript ᵐ marks a cell that is FALSIFIABLE but **masked on B3/B3⁺**
by an earlier conjunct in `CONJUNCT_ORDER` — it fires only on an arm that lacks the earlier one.

### 5.1 K-none (captured credential; cannot sign under the terminal holder key)

| # | Conjunct | T1 caller sub. | T2 tool sub. | T3 arg sub. | T4 scope excess | T5 replay |
|---|---|:--:|:--:|:--:|:--:|:--:|
| 1 | chain-verified | SU | SU | SU | SU | SU |
| 2 | authorizer-permits | SU | SU | SU | **SU** (by design) | SU |
| 3 | certificate-chain-valid | **F** | SU | SU | SU | SU |
| 4 | holder-proof-valid | **F** | SU | SU | SU | SU |
| 5 | invocation-bound | SU | **F** | **F** | SU | SU |
| 6 | R ⊆ Cₙ | SU | **F**ᵐ | **F**ᵐ | **F** | SU |
| 7 | label-policy-satisfied | SU | **F**ᵐ | **F**ᵐ | **F**ᵐ | SU |
| 8 | approval-valid | SU | **F**ᵐ | **F**ᵐ | **F**ᵐ | SU |
| 9 | resource-authorized | **F** | **F**ᵐ | **F**ᵐ | **F**ᵐ | SU |
| 10 | identity-consistent | **F** | SU | SU | SU | SU |

**Row-by-row mechanism, with file:line.**

1. **chain-verified — SU at every point.** The capability is presented unchanged at T1/T2/T3/T5,
   so it still verifies. At T4 the adversary would need a *wider* capability: `_crypto_chain_ok`
   verifies every hop under κ's public key and requires hop *i*'s revocation ids to be a prefix
   extension of hop *i−1* (`capability_path.py:591-604`), and Biscuit blocks only ever narrow
   (`signer.py:157`, *"the Supervisor only ever narrows it"*). Minting a wider chain that verifies
   requires κ, which **P4** places outside the model. **Making this conjunct false is trivial
   (present garbage) and useless — it blocks. Making it false *while being admitted* is OM.**
   EV: **UNEVADABLE** under P4.
2. **authorizer-permits — SU at T4, and deliberately so.** This conjunct evaluates the **authority
   prefix P₀ only**, which carries no attenuation block. The source states the intent
   (`:612-618`): *"Nothing there can fail for a narrowing reason, so an empty Allowed(P₀) means one
   of Γ's own checks refused — and a narrowed-away or out-of-C₀ candidate falls through to
   containment, unmasked."* A scope-excess request is therefore **routed past** this conjunct by
   construction so that containment measures it. This is a designed non-catch, not a gap.
3. **certificate-chain-valid — F at T1.** To present as a different caller the adversary must
   extend the HTC chain naming itself as `next_holder_pubkey`; HTC_i must be signed by
   HTC_{i−1}.`next_holder_pubkey` (`:669-676`) and the adversary holds no such key. Any appended
   hop fails the signature or the registry lookup. Arms that would then admit: **all but B3/B3⁺**.
4. **holder-proof-valid — F at T1.** The INV must verify under the terminal holder key the last
   HTC names (`:709-723`). K-none cannot produce that signature. This is §D.3's canonical T-reuse
   catch and the corpus exercises it (4 falsifications [M]). Arms admitting: all but B3/B3⁺ —
   B2-DPoP blocks by its own RFC 9449 binding, not by this conjunct.
5. **invocation-bound — F at T2 and T3.** `inv["tool"] != tool` (`:756`) and
   `inv["canonical_request_digest"] != h_jcs(dict(arguments))` (`:742-747`). This is the exact gap
   §D.3 attributes to INV: DPoP closes T1 but not T2/T3 at a shared endpoint. Arms admitting:
   **every arm except B3/B3⁺, including B2-exchange-task-DPoP.**
6. **R ⊆ Cₙ — F at T4** (the canonical case; 6 falsifications [M]), and **Fᵐ at T2/T3** because a
   substituted tool or argument changes the required authority. R is computed server-side from
   tool + resource + arguments (`required_authority.py:109-117`); the dissertation makes the
   reason explicit (`mproj.tex:719-723`): *"an agent free to declare its own requirement would
   declare one that fits the authority it holds."* Arms admitting at T4: B0, B1,
   B2-broad-noexchange, B2-exchange-broad (B2-exchange-task blocks by token scope — measured as
   `b2_token_scope` ×4 [M]).
7. **label-policy-satisfied — Fᵐ at T2/T3/T4.** Egress is derived from the server policy, not
   enumerated (`:820-824`), so substituting to `mail.send` or altering a payload argument changes
   the verified-label decision. Minting a *believed* label instead requires a trusted label-issuer
   key — **OM under P2/P4**.
8. **approval-valid — Fᵐ at T2/T3/T4.** Substituting to a frozen high-risk action (`mail.send`,
   `notes.delete`) with no artifact fails at `:906-913`. Forging an artifact requires an approver
   key from a set disjoint from the label issuers (`:900-905`) — **OM under P4**.
9. **resource-authorized — F at T1** (present the adversary's own AT, which lacks the scope:
   `:934-951`) and **Fᵐ at T2/T3/T4**. This is the `stolen_AT_key_substitution` /
   `audience_mismatch` family the corpus already carries (6 falsifications [M]).
10. **identity-consistent — F at T1, and this is the live gap.** The conjunct maps the OAuth actor
    claim to the terminal holder key the chain names and refuses on mismatch (`:955-985`). An
    adversary presenting **its own access token together with the victim's capability chain**
    produces exactly that mismatch. **The corpus never constructs this**: 0 falsifications and
    only 6 of 34 cells even reach it [M]. `credential_faults.py:62-65` shows the corpus
    deliberately steers *around* it — the wrong-holder fault uses a **registered** holder
    precisely *"so that `actor_of(...)` still resolves and the registry lookup SUCCEEDS — which
    leaves `holder_proof_ok` as the only conjunct that can catch the substitution. An unregistered
    key here would be caught by the identity plane instead, measuring the wrong thing."* The
    identity plane was designed out of the corpus's measurement path on purpose, which is a good
    reason for its absence and **not** a reason to believe it works.

**T5 (replay) is STRUCTURALLY UNREACHABLE for all ten conjuncts, and that is the row's finding.**
A bit-identical in-window resubmission satisfies every one of the ten by construction — it *is* a
legitimate request, replayed. Nothing in §A.5 can fire. Only the `jti` cache catches it, and the
source states the cache is not one of the ten (`:498-504`). This reproduces §D.3 row 5 exactly
(B3 ❌ admits, B3⁺ ✅ blocks) and is the entire justification for B3⁺'s existence. **EV for the
whole column: EVADABLE on B3, UNEVADABLE on B3⁺.**

### 5.2 K-holder (possesses the terminal holder identity key)

| # | Conjunct | T1 caller sub. | T2 tool sub. | T3 arg sub. | T4 scope excess | T5 replay |
|---|---|:--:|:--:|:--:|:--:|:--:|
| 1 | chain-verified | NE | NE | NE | **SU** | NE |
| 2 | authorizer-permits | NE | NE | NE | **SU** | NE |
| 3 | certificate-chain-valid | NE | NE | NE | **SU** | NE |
| 4 | holder-proof-valid | NE | NE | NE | **SU** | NE |
| 5 | invocation-bound | NE | NE | NE | **SU** | NE |
| 6 | R ⊆ Cₙ | NE | NE | NE | **F** | NE |
| 7 | label-policy-satisfied | NE | NE | NE | **F**ᵐ | NE |
| 8 | approval-valid | NE | NE | NE | **F**ᵐ | NE |
| 9 | resource-authorized | NE | NE | NE | **F**ᵐ | NE |
| 10 | identity-consistent | NE | NE | NE | **SU** | NE |

**The NE columns are vacuity, and it is the model's own.** Table 3.1 declares T1, T2, T3 and T5
meaningful only under a captured credential. That is structurally correct rather than a
convention: an adversary who can sign fresh assertions has no reason to substitute a tool *after*
signing — it signs the tool it wants. T1 collapses because the holder **is** the caller; T2/T3
collapse into "the holder signs what it chose"; T5 collapses because fresh minting is available.
Every one of them reduces to either a legitimate in-scope request or to T4. **The K-holder column
has exactly one live tampering point.**

**Why rows 1–5 and 10 are SU at T4.** A compromised holder signing a fresh, well-formed request
**satisfies** them all: it holds the key so holder-proof verifies (`:709-723`); it computes the
digests itself so invocation-binding matches (`:726-787`); the capability and HTC chains are
presented unchanged so chain-verified and certificate-chain-valid pass; its own actor claim maps
to its own holder key so identity-consistent passes (`:955-985`). None of these six conjuncts can
be made false by this adversary, and therefore **none of them catches it**. This is H4b's
concession, now derived per-conjunct rather than asserted.

---

## 6. The K-holder column's shape — the second expected finding, verified

**Result: confirmed, and stronger than the task's phrasing.**

Of the ten conjuncts, at the single live K-holder tampering point (T4, scope excess), **exactly
one fires on its own merits: R ⊆ Cₙ.** Three more (label-policy, approval, resource-authorized)
can fire but only as consequences of *which* out-of-scope tool was chosen, and all three are
masked on B3/B3⁺ by containment at position 6. Six cannot fire at all.

**Stated on both axes, so it cannot be misread:**

- On the task's formal axis: R ⊆ Cₙ is **FALSIFIABLE** under K-holder at T4 — the adversary can
  make it false, which is exactly what causes the block.
- On finding 2's axis: R ⊆ Cₙ is **UNEVADABLE** under K-holder. To be admitted while exceeding the
  grant the adversary must widen Cₙ. `allowed_set` is computed from the **cryptographically
  verified terminal capability** (`capability_path.py:806-813`), attenuation blocks only narrow
  (`signer.py:157`), and minting a wider chain requires κ, which **P4** places outside the model.
  Holding the terminal holder identity key confers no power over the authority plane.

**This converts H4b from an unstaged premise into a positive structural result**, in the exact
terms §D.1 predicted (`EXPERIMENT_ARCHITECTURE_FINAL.md:183`): *"no mechanism blocks a compromised
holder acting within Cₙ; all Cₙ-enforcing mechanisms block it from exceeding Cₙ, because scope
containment is independent of holder identity."* The enumeration shows **why**, conjunct by
conjunct: the holder key is a credential-plane object and Cₙ is an authority-plane object, and the
ten conditions touch the two planes disjointly.

**Three scope conditions on that result, stated because it is a positive claim.** It holds only
while (a) κ and the AS root key remain unreachable — **P4**; (b) required authority stays
server-computed from tool, resource and arguments (`required_authority.py:109-117`), since an
agent-declared R would let the holder declare one that fits; and (c) Biscuit attenuation remains
monotone-narrowing. If any of the three fails the cell moves from UNEVADABLE to EVADABLE. **This
is a structural argument, not a measurement — no cell of it has been instantiated. That is what
Phase B is for.**

**The residual, stated plainly and not softened.** Containment bounds a compromised holder at Cₙ
and concedes everything inside it. Within Cₙ **no conjunct of the ten fires**, by construction.
B3 does not claim otherwise (`EXPERIMENT_ARCHITECTURE_FINAL.md:185`), and this enumeration
confirms the concession is total rather than partial.

---

## 7. Phase B candidate set — derived, not authorised

Cells marked **F** and **not** masked on B3/B3⁺ are the instantiable set; masked cells would
measure the masking conjunct instead, which is the trap `credential_faults.py:186-193` already
names for a different case. **[D] from §5:**

| Priority | Cell | Why it is worth running | Corpus status |
|---|---|---|---|
| **1** | **identity-consistent × K-none × T1** | The only never-falsified conjunct that is reachable, and the corpus was deliberately steered around it (`credential_faults.py:62-65`). Highest information gain in the table. | 0 falsifications, 6/34 reached [M] |
| **2** | **invocation-bound × K-none × T2** and **× T3** | Never falsified in 30 reached cells [M]; carries H4a branch (ii), which is currently **NOT DETERMINED** and rests on the unpopulated `F3 dpop-first-use-body-mutation` row. | 0 falsifications [M] |
| **3** | **certificate-chain-valid × K-none × T1** | Never falsified, unconditionally [M]; §D.3 names it a T-reuse catch jointly with holder-proof, but only holder-proof has ever fired. | 0 falsifications [M] |
| **4** | **R ⊆ Cₙ × K-holder × T4** | Stages H4b for the first time. Currently NOT DETERMINED with **no gate substituting**. | premise never staged |
| — | chain-verified, authorizer-permits | Not candidates. Both are SU everywhere in model; falsifying them positively needs κ (**OM under P4**). | 0 falsifications [M] |

**Feasibility, checked and reported rather than assumed.** The existing attacker seam is
presentation-level only — `credential_faults.py:12-23` states *"Every fault is presentation-level.
There is no provisioning level"*, and records that building one disproved it. `_rebind_inv`
(`:180-220`) already re-mints a staged INV under `setup["holder_privates"]["holder-specialist"]`,
which **is** the terminal holder identity key. So a K-holder adversary is **expressible** with the
primitive that already exists.

**One constraint bites and must be settled before Phase B.** Adding a new fault name would mean
editing `src/harness/credential_faults.py`, which is inside the seal (`COVERED_PREFIX = src/`) and
the standing constraints forbid it. Phase B must therefore stage its attacks from the **unsealed**
adaptive harness by intervening on `arm._staged` after the sealed `present()` returns — the same
pattern D-018 used to move the transport without editing sealed code. This is feasible and is
recorded now, before any instantiation, so that a Phase-B failure cannot later be attributed to a
seam that was known to be missing.

---

## 8. What this table does not establish

It is an enumeration of the admission rule as **written and implemented**, not a measurement.
Every SU cell is an argument from mechanism with a file:line, and an argument from mechanism is
exactly what the static-benchmark critique says should not be trusted on its own — including when
this study makes it. No cell has been instantiated; nothing here is evidence that B3 blocks
anything it has not already been measured blocking.

The enumeration is also bounded by its own scope, named so a later reader can test it: it covers
the ten §A.5 conjuncts, the five Table 3.1 tampering points, and the two key-possession classes.
An adversary outside those axes — one with network position at the A2A hop (**P1**), sealed
harness material (**P4**), a mis-issuing AS (**P2**), an incomplete mediation layer (**P3**), or a
tool with hidden side effects (**P5**) — is out of model, and this table says nothing whatever
about it. Four of those five are assumptions this apparatus cannot check about itself.
