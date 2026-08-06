# 0043 — The confirmatory corpus, and the sealed generator that could not produce it

## Context

**Part H step 4 stopped, and the reason was a property of the seal itself.** The v0.5 seal
(`805425e`, manifest over `7872311`) covers the only corpus generator in the repository,
`fixtures/pilot/golden_thread/generator.py`, at hash `09b9c72d…fc13`. Step 3's own words say the
seal covers *"the corpus generator — its code, the deterministic key seeds …, and the scenario
specifications, **the sealed inputs from which the confirmatory corpus is deterministically
produced**"*. The repository did not contain those inputs. The sealed generator was pilot-only in
three hardcoded ways:

1. `CORPUS_DIR = Path(__file__).resolve().parent` — it could write to the pilot directory and
   nowhere else, with no output parameter, no mode and no flag;
2. `SEED_HEX = "e1"*32`, `TASK_ID = "task-gt-pilot"`, derivation prefix `AASC-EXP1-PILOT-KEY:`,
   corpus name `golden_thread(pilot)` and the thirteen `SCENARIOS` were sealed constants, so the
   only corpus it could produce was **the pilot corpus, byte for byte** — which shares every
   specification hash and the seed hash with `fixtures/pilot/`, and would have failed Part H
   step 5's disjointness assertion by construction;
3. its first act was to refuse to run while `fixtures/confirmatory/` held anything but a README —
   a **pre-seal** invariant baked into the sealed bytes, with no branch that ever populated that
   directory.

**How it was found, and what it says about the seal.** It was found by attempting step 4 and
reading the sealed generator rather than assuming it generalised. Four independent fail-closed
layers each refused the shortcut of relabelling the pilot corpus as confirmatory: the generator's
own empty-directory guard; Part H step 5's hash discipline; `check_run_mode`'s refusal of a
confirmatory run whose corpus lives under `fixtures/pilot/`; and the manifest's coverage of the
generator, which made editing it visibly a reseal rather than a fix. **The seal worked.** Nothing
was quietly repaired: step 4 stopped, the finding was reported, and the Commander chose to fix the
inputs properly rather than relabel a corpus.

## Decision

`[DESIGN]` **This is the first half of a Part H unseal/reseal.** It knowingly edits files the v0.5
manifest covers. It does **not** build a manifest, anchor, sign, or mark v0.5 superseded — that is
task A2, after independent review — and `seal/` is untouched.

### Sealed files edited — THREE, and why each had to be

| file | edit | why |
|---|---|---|
| `fixtures/pilot/golden_thread/generator.py` | a `CorpusProfile` parameterises output directory, seed, task id, corpus name, derivation prefix, context label, both delegation chains and the scenario set; `PILOT` carries the previous values unchanged; `CONFIRMATORY` is new | it is the object that could not produce a second corpus |
| `src/harness/runner.py` | `run_mode` threaded through the constructor, **defaulting to `"pilot"`**, replacing the string hardcoded at both setup sites | a confirmatory campaign would otherwise have emitted records labelled `pilot`, and a mislabelled record is worse than no record |
| `fixtures/confirmatory/README.md` | rewritten from the placeholder that described an empty directory to the record of a generated corpus: how it is produced, the disjointness and structural-match properties, the ADR 0007 seed-disclosure warning carried verbatim, and its unsealed status | it is the only document in the corpus directory that is not itself generated, and leaving it describing an empty directory would have made the sealed record wrong about its own contents |

**A correction to this record, made rather than buried.** This ADR first reported **two** sealed
files edited. That count was wrong: `fixtures/confirmatory/README.md` sits under the v0.5
manifest's `fixtures/` coverage prefix and is in its covered set, so editing it was a third
knowing edit to a sealed file. The edit itself was authorised — task A1's STEP 2 names the
directory's README — and nothing about what was changed is in question; only the count was. It is
recorded here because a reseal whose own ADR undercounts the sealed files it touched is exactly
the kind of small drift the seal exists to make impossible.

**Nothing else sealed changed.** No frozen value, no frozen row, no `Ω`, no `Γ`, no policy
artifact, no identity registry, no family definition, no §E.4 cell, no arm, and no pilot scenario.
The three frozen digests `H(Γ)`/`H(Λ)`/`H(R)` are verified by the generator on every run and were
unchanged throughout.

### The pilot regenerates byte for byte

Established two ways, both committed: `tests/test_pilot_fixtures.py` compares every committed
document against a fresh in-memory regeneration (its pre-existing test, unchanged in substance),
and `tests/test_confirmatory_corpus.py::TestThePilotIsUnchanged` re-asserts it per document against
the `PILOT` profile. Measured after the refactor: running the generator produced **no diff** in
`fixtures/pilot/` — 27 documents rewritten, zero bytes changed. If one byte had moved, that would
have been a silent change to the corpus fifteen gates were adjudicated against, and this task's
stopping conditions require halting there.

### The derivation prefix is a parameter whose value is deliberately identical in both profiles

It is the derivation **rule** — ADR 0007 and ADR 0019 seal the labels and the rule, never key bytes
— not an instance parameter. The **seed** is the instance parameter, and a different seed already
yields a wholly disjoint key set (asserted by running the derivation, not by comparing seeds). This
also keeps the runner's existing check that the corpus's declared prefix matches
`key_material.DERIVATION_INFO_PREFIX` passing for both corpora, with no edit to key derivation.

### The guard became symmetric rather than being deleted

The pre-seal check refused to run while `fixtures/confirmatory/` was non-empty. It is **replaced**,
not removed, by a mode-aware guard: the pilot profile may write only to
`fixtures/pilot/golden_thread`, the confirmatory profile only to `fixtures/confirmatory`, and an
unknown mode fails closed. That is strictly stronger than what it replaced — it constrains both
corpora rather than one, and an emptiness check could never have caught a hand-edited scenario
while this does. **All three halves are watched failing** in
`tests/test_confirmatory_corpus.py::TestTheSymmetricGuard`.

### The generator keeps its location

It stays at `fixtures/pilot/golden_thread/generator.py` although it now produces both corpora.
Moving it would churn path citations — the manifest, the pre-registration, the ADR 0028 scan record
and several tests all name that path — days before a reseal, for no gain. Recorded here so the odd
location is explained rather than merely odd.

### Provenance, and what could not be anchored

Every confirmatory scenario carries a `provenance` field. **No paper defines F1–F5**: they are this
study's operationalisation of MCPShield's **TV23 Cross-Protocol Confusion** (category TC7, surface
`S_compose`), and each family instantiates a published property.

| anchor | status |
|---|---|
| MCPShield Property 3 (Privilege Boundedness) → F1; Property 2 (Data Confinement) → F4; TV13 → F5; TV14/TV15 → F2; TV22 → F3 | source text verified by the reviewer; used as written |
| AgentRFC P3 (Delegation Monotonicity), ADV-3 → F1; P1/P2 → F2; P5 → F5 | as above, cited as a **preprint** whose evaluation is explicitly incomplete |
| RFC 9449 §11.8 *Access Token and Public Key Binding* → F2 wrong-holder-proof and F3 key-substitution | **opened 2026-08-06.** Covers exactly the substitution attack: the binding "relies on the hash function having sufficient second-preimage resistance so as to make it computationally infeasible to find or create another key that produces to the same hash output value" |
| OAuth 2.1 §5.3.1/§5.3.2 → F2 invalid-credential and unauthenticated-caller | **opened 2026-08-06**, `draft-ietf-oauth-v2-1-15`, 2 March 2026. Recorded as a draft revision, never as an RFC, because section numbers move between revisions |
| RFC 9068 §4 *Validating JWT Access Tokens* → F3 audience-mismatch | **opened 2026-08-06.** The only opened source that actually requires the check |
| Denning's lattice model → F4 | **DROPPED.** Its bibliographic record was confirmed (CACM 19(5):236–243, May 1976, doi 10.1145/360051.360056) but the primary text could not be opened, so no content claim rests on it. F4's anchor is MCPShield Property 2 |

**Two findings from opening the sources rather than assuming them.** RFC 9449 does **not** mandate
any resource-server audience check — it mentions audience-restricted tokens once, in §2, as an
alternative that "has proven to be prohibitively cumbersome" — and **OAuth 2.1 core does not
either**. The assumption that F3's audience subcase maps onto RFC 9449's Security Considerations is
therefore false, and it is recorded as false. The covering requirement is RFC 9068 §4. Separately,
OAuth 2.1 §3.2.1 *is* titled *Client Authentication*, but it governs the **token endpoint**, which
is a different location from this subcase's resource-server presentation; the scenario records that
distinction instead of stretching the clause.

### What could not vary, and why

The task requires the tool and resource to vary within the frozen `Ω`. Eleven of the thirteen
instances do. **Two cannot**: `mail.send`/`mail/outbox` is the *entire* derived egress set over the
frozen `Ω`, so both F4 instances must use it or stop being F4 instances; what varies there is the
recipient, the subject, the payload and the chain. Widening `Ω` to create an alternative is
forbidden and would make the two corpora incomparable. Two further limits are recorded rather than
worked around: `notes.read` carries one argument, so the five F2/F3 instances vary their arguments
across only the two `notes.read` elements their chain holds; and the **principal identities do not
vary** — the identity registry is frozen, and the campaign provisions its arms once from the
registry defaults, so routing the delegation to `agent-worker` would require editing sealed campaign
plumbing this task does not authorise and could not be verified without running the confirmatory
campaign, which it forbids.

### The F5 isolation is now machine-checked

The pilot isolates the approval conjunct by choosing a **non-egress** high-risk action, so rows 4/6
permit at every label; `notes.delete`/`notes/project` is the only such element in `Ω`, so repeating
that choice would have left the tool, the resource *and* the arguments identical to the pilot's.
The confirmatory F5 instances isolate the same conjunct the other way — `mail.send` with a
**public** label to an internal sink, which row 6 permits — and `check_f5_isolation` asserts that
against the frozen policy artifact on every generation, so the masking hazard the pilot's own
comment warns about is caught by code rather than by prose.

### Four pre-seal guards were re-pointed, not deleted

Red line 1 reads *"do NOT create or populate `fixtures/confirmatory/` **before sealing**"*. The seal
happened, so four tests asserting emptiness were asserting the opposite of the design. Each was
re-pointed at what it was protecting: the confirmatory directory must contain **exactly** the
generator's output and nothing hand-authored (strictly stronger than emptiness); no pilot scenario
may appear there; the pre-registration's thirteen-`_banner` count is scoped to the **pilot** corpus,
which is what its sentence is about; and its README-only claim is verified against the **sealed
commit** `7872311`, where it is true and will remain true forever.

## Status

proposed — 2026-08-06. **The reseal is owed:** task A2 must rebuild the manifest over the new
candidate, re-anchor, re-verify from a fresh clone, re-sign, and mark v0.5 superseded. Until it
does, the repository is **unsealed**.

## Consequences

- A confirmatory corpus exists: 13 scenarios, 27 documents under `fixtures/confirmatory/`,
  generated from sealed inputs by the confirmatory profile, disjoint from the pilot on
  specification and seed content hashes and on derived key material.
- `tests/test_confirmatory_corpus.py` is the bias guard. It bounds what could drift **silently**;
  it does **not** mitigate instance-selection bias, which ADR 0037 declares unmitigated and which
  stays unmitigated. RQ3's qualification is unchanged.
- Part H step 7 is still forbidden until the reseal: running the confirmatory campaign before v0.6
  would produce results against an unsealed candidate.
- Re-triggered by: any amendment to `Ω`, `Γ`, the policy artifact or the registry (the generator
  verifies all three digests on every run), and any change to §E.4 (the structural-match test reads
  the subcases the matrix is indexed by).
