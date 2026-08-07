# Pre-Registration — the frozen design, recorded before any confirmatory data exists

**Status: AUTHORED. SEALED at v0.5 and v0.6; a v0.7 reseal is owed and Part H step 7 has not
run.** This is Part H **step 2** of the seal loop (`docs/EXPERIMENT_ARCHITECTURE_FINAL.md`,
Part H), authored after all fifteen Part G gates were adjudicated on the pilot corpus and **before
any confirmatory measurement exists** — which is still true, and is the only clause here that
carries evidential weight.

*Dated correction, 2026-08-07 (ADR 0044). The paragraph above read "Step 3 … has **not** been
performed; nothing in this repository is sealed yet, and `fixtures/confirmatory/` is empty." All
three clauses were true when written and are now false: the confirmatory corpus was generated
(ADR 0043, commit `cbd3638`), step 3 was performed twice — v0.5 at `805425e` and v0.6 at
`cdf185d`, both anchored — and v0.6 is superseded by a v0.7 candidate after a pre-run audit found
the apparatus could not execute step 7 and would, in two places, have measured wrongly. The
correction is dated rather than silently applied: a pre-registration whose status line is edited
without a record is no longer a pre-registration. **No prediction, predicate, threshold, hypothesis
or declaration in this document has been altered by any reseal**, and the two declarations in §2
and §4 stand verbatim as first registered.*

Any earlier draft of this document is superseded and must not be reused.

**Derivation rule.** Every statement here restates a decision the repository already records — a
frozen row in `docs/frozen_parameters.md`, an ADR, a gate report, or the design document — and
cites it. Nothing is decided in this document. Where the repository does not decide something,
the gap is stated as a gap. `tests/test_pre_registration.py` verifies every quantitative claim
below against its source, so this document cannot silently drift from the repository it
pre-registers. No ADR is cited by placeholder any longer: the RQ4 analysis ADR is ADR 0041 and
the pre-seal amendments ADR is ADR 0042 — each was cited by a placeholder letter when first
authored and received its number from the author before the seal, so nothing sealed cites a
number that does not exist.

Authored 2026-08-06 at repository HEAD `5264f1b`
(github.com/Maxjiang03/TrustworthyAgenticCommunication). Amended the same day at `ca360ae`,
on the author's decisions: the five gaps this document reported are closed (ADR 0042 and the
0041 assignment), and each closure is recorded in place below — nothing else changed.

---

## 1. The frozen-benchmark thesis

§A.1 of the design document fixes the thesis, and this document restates its substance without
weakening its scope guards:

MCP defines an **optional** OAuth 2.1 authorization profile; A2A v1.0 defines authentication,
leaves authorization to the implementation, and specifies in-task credential acquisition
(`TASK_STATE_AUTH_REQUIRED`) with **no** standardized task grant and **no** normative per-hop
monotone transformation preserving an upstream task grant as a bound on downstream MCP tool
effects. Whether a user's task grant survives the A2A-to-MCP boundary is therefore a deployment
property, not a protocol guarantee. This study constructs a **frozen benchmark** of delegation
scenarios and measures, on that benchmark, how a ladder of nine deployment mechanisms behaves
when authority crosses the boundary: whether the authority exercised at an MCP tool call remains
within the user's task grant, and what security and runtime cost each mechanism incurs.
Task-authorization semantics, the action/resource ontology `Ω`, and the execution substrate are
held identical across mechanisms. **All quantitative results are properties of this frozen
benchmark; the study makes no claim about the frequency of such failures in deployed systems,
nor about how widely any mechanism is adopted** (§A.1, decision D40).

The nine arms (§E.1, D19), spelled as the code spells them: B0, B1, B2-broad-noexchange,
B2-exchange-broad, B2-exchange-task, B2-exchange-task-DPoP, B-cap, B3, B3+ (rendered B3⁺ in the
design document). Every strong baseline receives the identical per-hop authority `C_0..C_n`
(gate G-13: `Allowed(AT_i) = C_i` recomputed independently for every hop of every strong arm).

**Scope declaration — the A2A adapter (ADR 0020; §J.5 item 20).** The Supervisor→Specialist hop
runs behind a one-operation transport port with an in-process adapter. Its divergences from A2A
v1.0 are disclosed, not absorbed: no wire, no task lifecycle, no `TASK_STATE_AUTH_REQUIRED`,
in-envelope credentials, in-process errors. Results are statements about the boundary mechanisms
over this port, not about a conformant A2A wire deployment.

**Scope declaration — Phase-1 user-to-AS authentication is modelled, not executed (§E.2;
ADR 0021).** §E.2 specifies auth-code + PKCE over TLS; ADR 0021 realises it as a pre-issued
fixture minted once at AS start-up. Phase 1 is identical across arms, measured separately as
`setup_cost`, and excluded from the delegation estimand. The study makes no claim about end-user
authentication.

## 2. Research questions

Restated from §A.2, with RQ3's amendment carried in full:

- **RQ1.** Which authorization properties do the MCP and A2A specifications guarantee at the
  A2A-to-MCP boundary, and which do they defer to the implementer?
- **RQ2.** On the frozen benchmark, how often does the authority actually exercised at the
  boundary exceed the user's task grant, and under which configurations does the excess survive?
  Decomposed into the authority admitted at the boundary, the authority the request required, and
  the authority actually exercised (from an independent effect ledger).
- **RQ3.** For each baseline and each matched leave-one-out variant, what is the per-family
  attack outcome under each family's own success predicate, and the false-blocking outcome on a
  benign workload with near-miss cases, **on the constructed instance set**?
- **RQ4.** What is the absolute added latency of each mechanism, separated into setup,
  delegation, boundary-verification, and end-to-end components, under cold and warm conditions,
  and how does the security-versus-overhead trade-off compare?

**Declaration — instance-selection bias is UNMITIGATED, not controlled (ADR 0037; §J.5
item 23).** The held-out third of the confirmatory corpus was **cut**; the split machinery was
cancelled, not deferred. Pre-registration and a held-out subset defend against **different**
threats: this document seals the design, predicates, thresholds and analysis so they cannot be
chosen after seeing results — that protection stands — but it does **not** substitute for a
held-out subset, which would have addressed the risk that an author-constructed suite contains
instances the mechanisms were, consciously or not, built to catch. **That protection is
forfeited, and no other part of the design substitutes for it.** The partial mitigations — the
mechanisms and frozen parameters were fixed before most scenarios were written; every gate
criterion was shown able to fail; §E.4's expected matrix was written in advance — are reported
as **partial, never as replacements**. RQ3 is answered on the constructed instance set only,
this qualification travels with RQ3's answer wherever it appears, and the word *generalizes*
and its variants must not appear in any RQ3 claim.

**Declaration — F4's CONFIRMATORY INDEPENDENCE IS WEAKER THAN THE OTHER FAMILIES'
(pre-registered 2026-08-06, before the confirmatory campaign; it belongs here, beside the
declaration above, and not in a footnote).** Each confirmatory scenario is matched one-to-one
with a pilot sibling and moves the authority element under test. **Three do not move it
completely.** `cf-f1-terminal` reuses its sibling's **tool** (`calendar.read`) while moving the
resource (`calendar/work` → `calendar/personal`); `cf-f4-sensitive-egress` and
`cf-f4-declassified` reuse their siblings' **entire `(tool, resource)` element**,
`(mail.send, mail/outbox)`, unchanged.

For the two F4 instances **the cause is `Ω`'s frozen size, not an authoring choice.** `Ω` is
frozen at seven `(action, resource)` elements, and the egress set is **derived** from it as *the
effect carries a recipient* rather than enumerated (`frozen_parameters` rows 4/6/10,
ADR 0022/0023), which makes `(mail.send, mail/outbox)` **the entire derivable egress set — one
element**. An F4 instance has no second egress element to move to; there is no authoring choice
available, and the only way to create one would be to amend `Ω`, which is frozen, hashed as part
of `H(Γ)`, and sealed. `cf-f1-terminal` is **not** structurally forced in the same way: `Ω`
gives `calendar.read` two resources and the confirmatory instance takes the other one, so the
shared tool there is an authoring choice inside a five-tool ontology and is recorded here
rather than defended.

**The consequence, stated without softening.** The held-out third was cut (ADR 0037 above), so
there is **no** set of instances the mechanisms were never built against. Under that condition the
F4 confirmatory instances are **less independent of the pilot than the other families' are**:
whatever the pilot's F4 instances were, consciously or not, built to catch, the confirmatory F4
instances put the **same authority element** to the same mechanism. Their independence rests on
the recipient, the subject and payload bytes, the value carrying the `sensitive` label, the
delegation chain, the task identifier and the context label — never on the element under test.
**F4 agreement between the two corpora must therefore not be reported as replication of the same
strength as F1, F2, F3 or F5**, and this qualification travels with every F4 result. It does not
mitigate instance-selection bias, which stays unmitigated; it states, in advance, where the
confirmatory corpus is thinnest.

## 3. Hypotheses

The design document's falsifiable hypothesis content is **H4a and H4b** (Part D.1, decision D35)
plus the **§E.4 expected matrix** (§4 below), and this document freezes exactly that content.

- **H4a (post-signature, non-holder tampering).** An adversary who captured a valid credential
  but does **not** possess the terminal holder identity key attempts to (i) reuse it as a
  different caller, or (ii) substitute tool/arguments after signing. Prediction:
  B2-exchange-task (bearer) admits both; B2-exchange-task-DPoP admits (ii) at the same endpoint
  but blocks (i); **B3 blocks both** (HTC terminal-holder proof blocks (i); the canonical
  body/args digest in INV blocks (ii)). **Falsified if** B3 admits either, or if DPoP blocks
  same-endpoint tool/argument substitution.
- **H4b (compromised-holder misuse).** An adversary who **does** possess the terminal holder
  identity key attempts to exceed the grant. Prediction: **no** mechanism blocks a compromised
  holder acting *within* `C_n`; **all** `C_n`-enforcing mechanisms block it from exceeding
  `C_n`, because scope containment is independent of holder identity. **Falsified if** B3 blocks
  in-scope compromised-holder actions (over-blocking) or any `C_n`-enforcing mechanism admits
  out-of-`C_n` actions.

B3 does not claim to stop a compromised holder from misusing authority it legitimately holds
(Part D.1). Part D.3's attacker × key-possession × tampering-point matrix and the four-way DPoP
taxonomy (D.2) are part of the frozen prediction set; gate G-14 already measured the attribution
they predict (DPoP and invocation binding block different things — indistinguishable on
captured-proof-replay given the same cache, separated on first-use body mutation, the residual
credited to INV).

**Enumeration gap, closed by amendment rather than by hypotheses (2026-08-06, ADR 0042).**
Part H's content list for this document originally named "H1–H9/H4a-b", while the design
document enumerates no hypotheses numbered H1–H9: its falsifiable content is H4a/H4b and the
§E.4 matrix. This document first recorded that as a gap for the author, following the §F.4
enumeration-gap precedent; the author's decision was to **amend the list to name H4a/H4b** —
what Part D.1 actually defines — rather than to invent nine numbered hypotheses days before a
seal. No hypothesis was added, renumbered or reworded, and H4a/H4b above are verbatim as
before.

## 4. Per-family predicates

**Families (§E.3, §E.4).** F1 amplification (root / terminal / chain-tamper); F2 identity
(invalid_credential; wrong_holder_proof / wrong_dpop_key; unauthenticated_caller; and
wrong_principal, deferred — below); F3 invocation integrity (dpop-stolen-AT-key-substitution,
dpop-first-use-body-mutation, audience-mismatch and expired-token as OAuth negative controls,
dpop-captured-proof-replay); F4 information-flow/egress; F5 human approval.

**The oracle's quantities (Part I).** Each predicate reads only raw evidence, the sealed
`IntendedInvocation`, and the trusted mediation/ledger records — never a SUT-computed verdict or
digest (PROJECT_RULES red line 4; gate G-12 asserts this structurally). Reported quantities are
separated: `reference_allow` (R ⊆ C_n from sealed truth, plus family-specific gates),
`observed_forwarded` (trusted mediation record), `admission_breach` (admitted against the
reference), `realized_harm_F1..F5` (each family's own predicate over the **set** of correlated
effects from the independent ledger), `false_block` (a benign, reference-allowed request not
forwarded), and `log_integrity_failure` (blocked per the record, yet an effect exists). Zero
effects ⇒ no realized harm; any violating effect ⇒ realized harm; `admission_breach` (decision
property) and `realized_harm` (effect property) are reported separately for every family. F3
compares sealed-intended, independently-observed, and actual-effect digests — never an effect
against a possibly-tampered observed digest alone (Part I; `H_JCS` per ADR 0009/0012).

**The expected matrix (§E.4), frozen as predictions.** Exact counts are to be measured on the
sealed corpus, never asserted. B = expected block, A = expected allow, NA = not applicable under
the would-be-identical-instance standard (ADR 0035: NA is a statement about the corpus — no
second instance exists to score — never about a measurable admission):

| Subcase (family) | B0 | B1 | B2-broad-noexch | B2-exch-broad | B2-exch-task | B2-DPoP | B-cap | B3 | B3⁺ |
|------------------|:--:|:--:|:---------------:|:-------------:|:------------:|:-------:|:-----:|:--:|:---:|
| F1-root (R ⊄ U_task) | A | A | A | A | **B** | **B** | **B** | **B** | **B** |
| F1-terminal (R ⊆ U_task, R ⊄ C_n) | A | A | A | A | **B** | **B** | **B** | **B** | **B** |
| F1-chain-tamper | NA | NA | NA | NA | **B** | **B** | **B** | **B** | **B** |
| F2 invalid_credential | A | **B** | **B** | **B** | **B** | **B** | **B** | **B** | **B** |
| F2 wrong_principal (frozen task→principal policy) | *deferred — unscored (ADR 0028)* | *deferred* | *deferred* | *deferred* | *deferred* | *deferred* | *deferred* | *deferred* | *deferred* |
| F2 wrong_holder_proof / wrong_dpop_key | NA | NA | NA | NA | NA | **B** | NA | **B** | **B** |
| F2 unauthenticated_caller | A | **B** | **B** | **B** | **B** | **B** | **B** | **B** | **B** |
| F3 dpop-stolen-AT-key-substitution (T-reuse) | A | A | A | A | A | **B** | A | **B** | **B** |
| F3 dpop-first-use-body-mutation (T-tool/T-args) | A | A | A | A | A | A | A | **B** | **B** |
| F3 audience mismatch (OAuth neg. control) | A | A | **B** | **B** | **B** | **B** | **B** | **B** | **B** |
| F3 expired token (OAuth neg. control) | A | A | **B** | **B** | **B** | **B** | **B** | **B** | **B** |
| F3 dpop-captured-proof-replay (bit-identical) | A | A | A | A | A | A | A | A | **B** |
| F4 sensitive egress, no declassification | A | A | A† | A† | A† | A† | A | **B** | **B** |
| F5 high-risk action, no approval artifact | A | A | A† | A† | A† | A† | A | **B** | **B** |

The replay/holder four-way subtable and the `F3 dpop-captured-proof-replay` within-`Δ` fixture
constraint (ADR 0027) are frozen as written in §E.4; the bit-identical replay MUST be constructed
within `Δ`, because a replay outside `Δ` would be blocked by B3 for an unrelated reason and the
B3/B3⁺ distinction — the single cell that is B3⁺'s reason to exist — would collapse in the
direction that flatters this work's hypothesis.

**Declaration — F3 IS INSTANTIATED IN PART: three of its five subcases are not run
(pre-registered 2026-08-06, before the confirmatory campaign).** §E.4 defines F3 with **five**
subcases — `dpop-stolen-AT-key-substitution`, `dpop-first-use-body-mutation`,
`audience-mismatch`, `expired-token`, `dpop-captured-proof-replay`. Both corpora, pilot and
confirmatory alike, instantiate exactly **two** of them: `dpop-stolen-AT-key-substitution` and
`audience-mismatch`. The campaign therefore **does not instantiate `dpop-first-use-body-mutation`,
`expired-token`, or `dpop-captured-proof-replay`**. Their rows in the expected matrix above are
predictions the campaign leaves untouched, and the results chapter **MUST report those three rows
as NOT POPULATED BY THE CAMPAIGN** — not as passing, not as confirmed, not as agreeing with the
prediction, and never inside a per-family count that would read as though F3 had been covered.
F3's measured coverage is two subcases out of five, and that fraction travels with every F3
number this study reports.

One of the three is load-bearing. **`F3 dpop-captured-proof-replay` is the only row in the entire
expected matrix where `B3⁺` differs from `B3`** (A against **B**) — it is the single cell that is
`B3⁺`'s reason to exist, and the campaign does not populate it. What stands behind that cell, and
behind the DPoP-versus-INV attribution generally, is **gate G-14's pre-registered adjudication**:
its C1 criterion (both arms admit a first use and block the bit-identical in-`Δ` replay, neither
doing better than the other, with its C1.W1 negative control showing the block is the shared
cache's doing), its C2 criterion (a first use whose tool/arguments differ from what was signed —
DPoP admits, INV blocks, with C2.W1 reading the limitation out of the proof's own claim set), and
its C3 criterion (a bare bearer arm given the same cache is admitted, so *not built* and
*impossible* are told apart) — run on the locked measurement platform, recorded in
`smoke/g14/REPORT.md`, and supported by targeted tests. **That is controlled evidence. It is NOT
confirmatory-campaign evidence, and this document does not claim the two are equivalent.** A gate
exercises a mechanism on an instance built to isolate it; the campaign scores a sealed instance
under the same conditions as every other arm and family. **`B3⁺`'s justification in the ladder
therefore rests on gate evidence rather than on campaign evidence, and a reader is entitled to
weigh gate evidence differently.**

The omission is a **recorded decision, not an oversight**: adding the three subcases would require
changing the pilot corpus, which is the corpus all fifteen gates were adjudicated against, and the
author weighed that and declined. This declaration is made **before** the confirmatory campaign
runs, so that it is a pre-registration rather than something confessed in a results chapter.

**Declaration — row 5 is deferred by decision (ADR 0028).** `frozen_parameters` row 5
(`task_authorization_policy`) is deliberately not frozen and never will be by default: it has no
anchor outside the author's judgement, so any value would make `F2 wrong_principal` measure
conformance to an invented artifact, indistinguishable in the results tables from the anchored
rows. The subfamily is **deferred — unscored**, emphatically **not** NA: NA would assert the
arms cannot express the case, which is false — every arm could, and the study declines to score
it. The other three F2 subfamilies are retained and scored in full.

**The ADR 0028 scan, discharged against what exists at this HEAD.** The confirmatory corpus is
generated post-seal, so the objects scanned are the ones the seal will cover: the only corpus
generator in the repository (`fixtures/pilot/golden_thread/generator.py`), every scenario
specification under `fixtures/` (the pilot `corpus.json` and the thirteen sealed scenario
documents), and the fault vocabulary (`src/harness/credential_faults.py`). Result: **no
wrong_principal variant exists in any of them**; the string's only occurrences in the repository
are the deferral records themselves (the row 5 reader, two frozen-artifact scope-boundary notes,
and the AS configuration note). Because the confirmatory scenario specifications do not yet
exist as separate objects at this HEAD, **this scan must be re-run at step 3 over the exact
specification set the manifest hashes**, and the seal must not proceed if it finds one.

**Declarations owned by gate G-15, restated without softening.** (i) Under a shared
boundary-owned monitor, F4/F5 measure the **monitor**, not the mechanism: no
capability-versus-OAuth advantage may be claimed from those two families in either direction.
(ii) Without a monitor configured, B3 and B3⁺ refuse the **benign controls** too — both policy
conjuncts fail closed — so the capability policy plane is useful **only when a monitor is
configured**. Both are results for the results chapter, not limitations; every F4/F5 cell is
recorded and compared under a named `monitor_attached` configuration, and cross-arm F4/F5 claims
mixing configurations are refused by construction (`src/harness/matrix_grouping.py`).

**Unscorable cells, fail-closed (built and tested; ADRs 0038/0039/0040).** The campaign routes a
cell to an `unscorable` list — never to a verdict — for three recorded causes: the runner raised
(`RunnerError`); the cell's artifact was minted at one instant and judged more than `Δ` away (the
wall-clock straddle, one clock per cell); or a credential's validity window does not cover the
judging instant. An unscorable cell is not a B, not a false_block, not a result at all, exactly
as an NA cell is not (`src/harness/campaign.py`; `tests/test_campaign_clock.py`). The results
chapter reports every unscorable cell with its cause. This document first reported that the
design document never used the word and proposed a definition; the design document now carries
it, in Part I beside the effect-handling rule (added 2026-08-06, ADR 0042 — the machinery
itself is unchanged).

## 5. The descriptive-statistics rule

Part H's statistical protocol (decision D26), frozen verbatim in substance: **security and
blocking outcomes are exact counts and rates only** — blocked/total, attack-success count,
false-block count, per-family exact results, at class-macro (per family) and instance-micro (per
instance) granularity, with template-derived variants clustered. **No confidence interval is
placed on any security or blocking proportion**: a fixed author-constructed suite has no
random-sampling population and verdicts are deterministic. Repetition of a security verdict is
used **only** to detect nondeterminism, and one disagreeing cell invalidates the run it is in
(`analysis/security.py` implements exactly this and exposes no interval estimator — asserted
structurally by its tests). Each sealed scenario is evaluated **once** for its verdict; the
latency repetitions are the only repeated sampling (Part H, "what once means").

## 6. The latency protocol

**Estimand and decision rule (`frozen_parameters` row 1; ADR 0026).** `equivalence_margin_ms = 20`.
The estimand is `median(B3) − median(B0)` over the measured segment
`presentation + boundary_verification`, **warm**. The "lightweight" claim **stands iff the upper
bound of the 95% bootstrap confidence interval on that difference is < 20 ms**; a point estimate
below the margin with a CI upper bound above it does **not** support the claim. The arms are
named by the ADR and are not renegotiated after seeing results. This is the **only** equivalence
decision in the study.

**Smoke threshold (`frozen_parameters` row 2; ADR 0025).** `g3_threshold_ms = 5`, fixed before
row 1 and independently of it; adjudicative only on the row 9 platform.

**Spans and segment.** The runner records five spans per repetition, correlated by
`correlation_id`: setup, delegation, presentation, boundary_verification, end_to_end
(`src/harness/runner.py`; transcribed and pinned in `analysis/latency.py`). The measured segment
sums exactly `presentation + boundary_verification` per repetition; a repetition missing either
half is refused, never summed from one. Excluded from the segment by name (ADR 0026):
instrument bookkeeping, the `MediationEvent` emission, every effect-ledger append, the tool's own
execution, `provision` (= setup) and `delegate` (= delegation). The audit sink inside `decide`
must be a bounded in-memory buffer flushed outside the segment.

**Sampling plan (row 1; Part H).** ≥ 200 end-to-end repetitions per configuration across ≥ 3
independent batches; micro-benchmarks ≥ ~1,000 timed iterations per configuration; cold and warm
reported separately and never pooled; condition order randomized or Latin-square counterbalanced
within each batch; warm-up discarded; persistent TLS and Ed25519 keep handshakes and signature
randomness out of the measured path. Reported shape: median, p95, IQR, with a percentile
bootstrap CI (10,000 resamples, seed required and recorded) on the estimand. **Refusal-path
latency is its own series**: on `gt-f1-chain-tamper` the exchange arms perform a failed AS round
trip while capability arms do purely local work, so that cell is excluded by name from every
benign per-arm series and from the estimand, and the exclusion is enforced by refusal in
`analysis/latency.py`. The freshness window and cache budget are frozen:
`delta_seconds = 60`, `replay_cache_capacity = 65536` (row 3; ADR 0027).

**Row 7 denominators and their sources (`frozen_parameters` row 7; ADR 0025).**
`T_full_ms = 2000` (primary) and `T_ttft_ms = 250` (conservative secondary) are **fixed
constants for interpretation, never measurements, never re-fitted to observed data**; the
fraction-of-one-LLM-turn framing is a **secondary interpretive aid only**, on which no
hypothesis, gate criterion or retraction rule depends. Sourcing, discharged here as the row
requires before step 3:

- **Primary anchor for both denominators:** Artificial Analysis — the independent benchmark
  publishing per-model Time to First Token and total response time on a fixed, documented
  methodology (TTFT = seconds from request to first token; total response time computed from
  TTFT and output speed; 1k/10k-token workloads tested 8 times daily; figures reported as P50
  over 72 hours). Methodology: https://artificialanalysis.ai/methodology/performance-benchmarking
  — retrieved 2026-08-06. Per-model figures: https://artificialanalysis.ai/models — retrieved
  2026-08-06. At retrieval, the lowest mainstream time-to-first-token shown was 0.33 s
  (Gemini 2.5 Flash-Lite, non-reasoning), with other frontier models at 0.44–0.53 s, so
  `T_ttft_ms = 250` sits at or below the fastest mainstream tier; and a 500-token response at
  mainstream output speeds implies end-to-end times above 2 s, so `T_full_ms = 2000` sits at or
  below the low end of per-turn full-response times. Both denominators therefore make the
  reported overhead fraction **larger** than a generous choice would — the framing is held to
  the stricter standard, as ADR 0025 intended. Both URLs and the retrieval date are now also
  recorded in row 7's own sourcing field (ADR 0042); the seal-time snapshot remains owed at
  step 3.
- **Unanchored, and closed by deletion with the values untouched (2026-08-06, ADR 0042):** the
  rationale clause "a representative tier-2 support agent is reported near 2.7 s median" could
  not be sourced to a dated, retrievable publication (searches on 2026-08-06 found no such
  figure; the nearest match is an arXiv sales-copilot report of a 2.6 s median — a different
  quantity from a different domain, and stretching it into this citation would invent a
  source). This document first reported the clause as **unanchored**; the author's decision was
  to **delete it from the row's rationale**, because an unanchored corroborating clause inside
  a frozen row reads as sourced. Per row 7's own rule **the frozen values stay unchanged** —
  `T_full_ms`'s anchoring never rested on the deleted clause. The row's "specialised silicon
  near 0.18 s" clause was likewise not re-verified in the 2026-08-06 retrieval (the same source
  publishes those per-provider figures, but no current number was read back) and is **left in
  place as not-re-verified** — a different state from unsourceable, per ADR 0042; the
  denominator's anchor is the mainstream tier read back above.

**Declaration — the per-mechanism claim boundary (ADR 0041; enforced in
`analysis/latency.py`).** Isolated per-mechanism latency costs may be stated for exactly: DPoP
holder binding (B2-exchange-task → B2-exchange-task-DPoP, the htc/holder bit), the jti replay
cache (B3 → B3⁺, the jti bit), and each of the six §E.6 matched ablations (each a single bit off
B3 by construction). They may **not** be stated for the online exchange, for B1's static-secret
verification, or for anything read off a pair that straddles the exchange partition — §E.5's
bitmask carries no bit for the exchange (B2-broad-noexchange and B2-exchange-broad have
identical rows yet only one performs a round trip) and no bit for B1's shared secret (ADR 0035).
The labelling code refuses or downgrades exactly those cases; a composite delta is never
reported under a single mechanism's name, and no per-mechanism interval is ever compared to a
margin — row 1's decision is the only threshold in the study.

**Declaration — B3⁺'s replay cache is measured single-process only (ADR 0034; §J.5 item 22).**
The confirmatory campaign is single-process; the ladder's B3⁺ carries an in-process cache, and
gate G-9's multi-process atomicity result is about the arbiter, a different object. **A green
G-9 does not license the statement "the ladder arm has multi-process atomicity," and the
dissertation must not make it.** The campaign refuses a confirmatory multi-process run while
this holds.

**Declaration — the G-3 record, all three runs, the conservative figure (`smoke/g3/REPORT.md`;
`tools/gate_rerun/REPORT.md`).** The adjudicated G-3 median `boundary_verification` cost is
**2.8264 ms** against the 5 ms threshold — measured once on the row 9 platform, 2026-08-02, and
that figure is the record. Measured headroom is therefore **1.77×, not the three- to tenfold
ADR 0025's prose argued**; neither the threshold nor the ADR was changed. G-3 has since been
re-measured twice on the same platform, and the three medians are **monotone downward**:
2.8264 ms (adjudicated, 2026-08-02) → 2.6928 ms (confirmation at `7b59e19`, 2026-08-03) →
2.6856 ms (seal-time re-run at `396c2b6`, 2026-08-06). The confirmation **does not separate**
from the adjudicated run (Mann-Whitney U = 12, exact two-sided p = 0.34, n = 4 vs 4 batch
medians, computed from the recorded batch tables); **the seal-time re-run separates
completely**: U = 16, the largest value attainable at n = 4 vs 4, exact two-sided p = 0.0286,
the smallest attainable — the batch-median ranges (2.6750–2.6920 seal-time against
2.7511–2.9190 adjudicated) do not overlap. The difference is **0.1408 ms — 0.70% of row 1's
20 ms equivalence margin and 0.49 of the adjudicated IQR (0.2898 ms)** — and both medians sit
far below the 5 ms threshold, so the gate verdict is unaffected. **The adjudicated 2.8264 ms
stands as the record, and it is the conservative figure: every claim reported against row 2's
threshold or row 7's denominators uses the worse number.** The drift's direction **favours the
lightweight framing** — later, faster measurements make the mechanism look cheaper — which is
exactly why it is declared here rather than noted in passing. What is not known, stated
plainly: three runs on one machine cannot distinguish machine-state variation from genuine
drift, and no cause is claimed.

## 7. The sealing and temporal-anchor procedure

**What step 3 seals (Part H).** The v0.5 candidate: the design document, the implementation
commit, the oracle code, the analysis code, all configuration — `Ω`/`Γ` with
`H(Γ) = f63320c9da3731a6ea04dc51d9f6852f3a3e130182ce3a7fe251158751333deb`, the identity-plane
registry with `H(R) = d1bfc5ffcb22e2ded736f5248b99b9f019ba314b93ddd808e50ea522b3fb4cbe`, the
label/sink/classification policy with
`H(Λ) = ce4e1e75c782e7bf83cdb7407ace64a91f86683c23ee58c6d9846728814183a7`, and the deferred
row 5 recorded as deferred — the pinned dependency environment **including the sealed
measurement platform** (`frozen_parameters` row 9; ADR 0014), and the **corpus generator**: its
code, the deterministic key seeds, the seed→keypair derivation rule, and the scenario
specifications. The seal covers **generators and seeds, never pre-minted token bytes**
(ADR 0007): Biscuit tokens are not byte-reproducible across mints, so determinism rests on
sealed inputs, and every oracle verdict is a function of the sealed scenario and
`C_n = Allowed(P_n; Γ, κ, Ω)`, never of token bytes. Publishing the seeds publishes every
derived private key; the corpus is a testbed artifact whose keys must never be reused.

**Procedure (Part H steps 4–7).** Generate the confirmatory corpus deterministically from the
sealed inputs — a **single set, no held-out third** (ADR 0037). Verify pilot/confirmatory
**disjointness** on scenario-specification and seed content hashes, never token bytes
(ADR 0007). Emit a **detached manifest** (never written into a file it hashes), add a public
temporal anchor — OpenTimestamps and/or an OSF registration — plus a signed commit to the public
remote, then perform the final seal. Execute the frozen campaign **once**. Abort discards the
partial run in full; infrastructure fixes that touch nothing sealed are recorded and appended
without a reseal; **any** change to sealed design, oracle, configuration or corpus forces a full
unseal/reseal with the previous seal marked superseded; no result-driven tuning after the seal.

**The gate state at authoring.** All fifteen Part G gates are adjudicated **PASS** on the pilot
corpus. The adjudicative records are the gate reports under `smoke/`; the commit given for each
is the one that landed its report, derived from git history (later touches to some reports are
citation-only edits — e.g. the documentation reframe — not re-adjudications):

| gate | record | report landed at |
|---|---|---|
| G-1 | smoke/g1/REPORT.md (restored to PASS by the ADR 0003 corrective pass) | dca755b (updated b385e6d) |
| G-2 | smoke/g2/REPORT.md | e7bb8e0 |
| G-3 | smoke/g3/REPORT.md — the only timing record in the repository | 6a342c4 |
| G-4 | smoke/g4/REPORT.md (+ DESIGN.md, SCOPE.md) | 3da17e7 |
| G-5 | smoke/g5/REPORT.md | 9cf08eb |
| G-6 | smoke/g6/REPORT.md | 8a46d9d |
| G-7 | smoke/g7/REPORT.md | 8a46d9d |
| G-8 | smoke/g8/REPORT.md | d7e38fd |
| G-9 | smoke/g9/REPORT.md | 80d91c1 (flaky-limb update 8b25484) |
| G-10 | smoke/g10/REPORT.md — the last gate; the DAG is closed | 55c1282 |
| G-11 | smoke/g11/REPORT.md | 1761ae6 |
| G-12 | smoke/g12/REPORT.md | b98ac5e |
| G-13 | smoke/g13/REPORT.md | 9431934 |
| G-14 | the smoke/README.md board row and smoke/g14/spike.py; smoke/g14/REPORT.md is a **retrospective** record — compiled 2026-08-06 at `ca360ae` from a re-run, stating so in its first line, never the adjudication (the gap this document first recorded, closed without disguising the asymmetry) | dfbef6d (spike) |
| G-15 | smoke/g15/REPORT.md | 71dd5ce |

**The five platform-bound gates — G-3, G-6, G-7, G-12, G-10 — are adjudicated on the row 9
sealed measurement platform** (`sealed_platform` = Windows 25H2 build 26200.8875, i7-12700H,
recorded machine-read in row 9), and were re-confirmed unchanged at commit `7b59e19` on
2026-08-03 (`tools/gate_rerun/REPORT.md`). **At step 3 these five are RE-RUN ON THE SEALING
COMMIT, so that no line of the sealed gate record is derived from an earlier commit.** The ten
platform-independent gates are confirmed by the suite and the off-platform verifier at the
sealing commit.

**Declaration — two undetermined sightings (ADR 0038).** Two intermittent test-level failures
(the flake-hunt ADR's Sightings A and B) were never reproduced and remain undetermined. Neither
reaches the campaign path. Recorded here so the seal proceeds over a stated residual rather than
a silent one.

**Declaration — retained historical references, deliberate.** Thirteen `_banner` fields in the
sealed pilot scenario documents (and the generator template line that produces them) cite the
project-rules file by its pre-rename name, as does the `SealedTruthAccessError` message in
`src/harness/sealed_truth.py` — the sealed pilot bytes were left untouched by the rename by a
recorded decision. Seven step identifiers cited from the implementation do not resolve to an
archived specification (four to EXP8B, whose specification was never archived, and three to
EXP6 STEP 3.1/3.2/3.4, sub-step numbers the archived specification never carried); all seven
were already unresolvable before the workplan rename and were left alone. None affects a result.

END. Sealed only at Part H step 3, by the author, after this document is reviewed.
