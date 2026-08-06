# fixtures/confirmatory — the confirmatory corpus (Part H step 4)

Thirteen scenarios, twenty-seven documents, **generated** — never hand-authored — by the sealed
corpus generator under its confirmatory profile:

```
uv run python fixtures/pilot/golden_thread/generator.py --profile confirmatory
```

The generator lives at `fixtures/pilot/golden_thread/generator.py` and produces **both** corpora
from one code path; its location is historical and is explained in ADR 000Z. `C_0` and `C_1` are
computed by the frozen authorizer at generation time and asserted against the specification —
never hand-written — and the three frozen digests `H(Γ)`, `H(Λ)` and `H(R)` are verified before
anything is written.

**Seed-disclosure warning (ADR 0007), binding.** Publishing the corpus seeds publishes **every
private key derived from them**. This corpus is a **testbed artifact only**; its keys **MUST NOT
be reused in any deployment**. Keys are minted at campaign runtime from the sealed seed and the
sealed seed→keypair derivation rule; no token byte and no signature appears in any document here
(ADR 0007 — Biscuit tokens are not byte-reproducible across mints).

## Disjointness from the pilot (Part H step 5)

Proved in `tests/test_confirmatory_corpus.py` on **scenario-specification and seed content
hashes**, and on the derived key material — **never on token bytes**, which differ between two
mints of the same logical capability and would report a disjointness that means nothing while
hiding a real overlap. No scenario file is shared, no specification hash is shared, the seeds and
task identifiers differ, and the derivation is run to show the key material genuinely differs.

## Structural match to the pilot (the bias guard)

Each scenario names its `matched_pilot_sibling`. Across every matched pair the family, the
`attack_subcase`, the `relation`, `is_benign`, `requires_approval` and the §E.4 predicted outcomes
across all nine arms are **identical**; the tool and resource, the argument values and the
delegation chain differ. Instances authored after watching the pilot behave are exactly where an
author would, without meaning to, pick easier or harder cases — so the criterion is structural
rather than editorial. **This does not mitigate instance-selection bias**, which ADR 0037 declares
unmitigated and which stays unmitigated; it bounds what could drift silently.

Two limits are recorded rather than worked around: `mail.send`/`mail/outbox` is the entire derived
egress set over the frozen `Ω`, so both F4 instances necessarily reuse it; and the principal
identities do not vary, because the identity registry is frozen. See ADR 000Z.

## Provenance

Every scenario carries a `provenance` field naming the published property it instantiates, with
each anchor's verification status. **No paper defines F1–F5** — they are this study's
operationalisation of MCPShield's TV23 (Cross-Protocol Confusion, category TC7, surface
`S_compose`). Anchors that could not be verified against a primary source were dropped or marked,
never reached for.

## Status

**Generated, not sealed.** The v0.5 seal (`seal/manifest_v0.5.json`, commit `7872311`) predates
this corpus and does not cover it. Part H's unseal/reseal is owed: the manifest must be rebuilt
over the new candidate, re-anchored, re-verified and re-signed, with v0.5 marked superseded.
**The confirmatory campaign (Part H step 7) must not run until that reseal is complete.**
