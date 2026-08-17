# F3 corpus extension — Phase 0 report and feasibility verdict

**Status: CLOSED. The extension collapses — no subcase is built. F3 stays 2/5; all three subcases carried or declined on three distinct, evidenced reasons. No code was ever written.**
*Scope: ONE fixture, `expired_token`. F3 coverage 2/5 -> 3/5, two subcases unbuilt.*
*(The original status was RED on all three; that verdict was wrong and is corrected in section 0.)*
Date: 2026-08-16. Phase 0 only; no code written, no artefact touched, no campaign run.

---

> **CORRECTED 2026-08-17, see DEVIATIONS D-013.** Every statement in this
> document that `expired_token` has "no carrier at all" is WRONG.
> `tests/test_f3_matrix.py` measures it, and `dpop-captured-proof-replay`,
> **cell by cell across all nine arms** against §E.4. What was established was
> that no GATE names it; that gate-scoped negative was reported as an unscoped
> one. All five F3 subcases have evidence, at three distinct evidence classes.
> The extension's closure is unaffected on its other reasons; this one reason is
> void and must not be repeated.

## 0. Verdict — CORRECTED 2026-08-16, after the residual check this report itself called for

**The first verdict in this document was WRONG on two of its three findings, and
it is corrected here rather than silently rewritten.**

§0 originally reported all three subcases infeasible and recommended extending
the gate instead of the campaign. I had flagged my own residual: the negative was
established over `schema.py`, `runner.py` and the `attack_subcase` call sites,
*not* over all of `campaign.py` or `src/sut/`. Closing that residual found the
seam I had said did not exist.

**`src/harness/credential_faults.py` is exactly that seam.** Its own first line
names it: *"The attacker between the arm and the resource server (EXP7 STEP 3)."*
`apply_to_presentation(...)` **corrupts what the arm STAGED** — it runs at
`runner.py:805`, after `arm.present(...)` returns and after ADR 0026's
`presentation` span closes, so the arm is never charged for the attacker's work.
And it is **scenario-selectable**: `campaign.py:901` reads
`sealed.get("credential_fault", "none")` and validates it against a closed
tuple.

That is precisely the signed-vs-presented divergence §D.2 describes, and it is
already used by five faults.

### Corrected per-subcase verdict

| subcase | first verdict | corrected verdict | why it changed |
|---|---|---|---|
| `dpop-first-use-body-mutation` | infeasible — "no signed-vs-presented seam" | **FEASIBLE** as a new credential fault | The seam exists and is literally *"corrupt what the arm staged"*. Restaging tool/args after the proof was signed over the originals is structurally what `_restage_token` and `_restage_dpop_proof` already do. |
| `expired-token` | infeasible — "`clock_refusal` routes every arm to `unscorable`" | **FEASIBLE** as a new credential fault | I conflated two different objects. `clock_refusal` inspects `credentials=setup` — the **provisioning** dict (`campaign.py:933`; the token enters it at `runner.py:368,523`). `_restage_token` writes to `arm._staged.access_token` (`credential_faults.py:150-152`), which the guard never reads. A deliberately staged expired token evades it **by construction**, and correctly so: the guard exists to catch a Phase-1 token that *aged during the pass*, not one an attacker staged on purpose. |
| `dpop-captured-proof-replay` | infeasible | **INFEASIBLE as a credential fault — confirmed, and it is the load-bearing one** | G-14 C1 builds it at `smoke/g14/fixture.py:147-152`: the arm is armed ONCE, then `arm.decide(TOOL, ARGS)` is called **twice** at the same injected instant. The replay is a second boundary **decision**, not a corrupted credential. A credential fault cannot produce it, because faults corrupt `arm._staged` and not the number of decisions a cell makes. |

### What this does to the cost estimate

The original report put the change at "schema + runner + campaign, changing how
every existing scenario is loaded". That was wrong. For the first two subcases
the change is: **new entries in `FAULTS` plus their `_restage_*` implementations
in ONE sealed file** (`src/harness/credential_faults.py`), following a pattern
that file already implements five times — plus the corpus additions and the four
count constants in Q1.

`FAULTS` today is six values (`credential_faults.py:49-56`) and contains none of
the three: `none`, `invalid_credential`, `unauthenticated_caller`,
`audience_mismatch`, `wrong_registered_holder`, `stolen_AT_key_substitution`.

**I withdraw the Option 3 recommendation.** It rested on a premise that was false
for two of three subcases. The revised options are in §2.

### What remains true from the first verdict

- The seal, the run-once property and the output path are **not** obstructions.
  `--out` exists, `refuse_if_written` guards the destination rather than a fixed
  path, and `run_campaign` already takes a `scenarios` parameter.
- `check_run_mode` still refuses any third run mode (`campaign.py:241-242`).
- Q1's collision is unchanged and still needs your ruling: the structural-match
  test asserts identical subcase sets across both corpora **and** hardcodes 13 in
  four places, and the task forbids modifying that test.
- Q2, Q4 and Q7 are unaffected.

**Blindness disclosure, unchanged.** During this task I did not read
`results/raw/campaign-confirmatory.json`, `results/tables/`, or
`results/_ledger/`. I had read them earlier in this session for the fresh-clone
verification pass, so those numbers were already in my context. I am not going to
claim to have designed blind.

**Scope of the remaining negative.** The replay finding is established over
`credential_faults.py`, `runner.py`'s presentation path, and `schema.py`. I have
not read `src/sut/` or the `Specialist` drive loop, which is where a second
presentation would have to originate if it is possible at all.

---

## 1. Phase 0 — the seven questions

### Q1. Does the structural-matching test force the pilot to carry the same subcase set?

**YES.** `tests/test_confirmatory_corpus.py:203-211`, verbatim:

```python
def test_the_family_coverage_and_subcase_sets_are_identical(self):
    def subcases(directory):
        return {doc["attack_subcase"] for doc in _sealed(directory).values()}
    def families(directory):
        return {doc["attack_subcase"].split(":")[0] for doc in _sealed(directory).values()}
    assert subcases(PILOT_DIR) == subcases(CONFIRMATORY_DIR)
    assert families(PILOT_DIR) == families(CONFIRMATORY_DIR)
```

and the pairing is one-to-one (`:189-193`):

```python
assert len(pilot) == len(confirmatory) == 13
siblings = {doc["matched_pilot_sibling"] for doc in confirmatory.values()}
assert siblings == set(pilot), "the pairing is not one-to-one"
```

**Full consequence.** The pilot gains three scenarios too — sixteen each side,
paired. Four assertions hardcode 13 [M]:

| line | assertion |
|---|---|
| `:83` | `assert len(regenerated) == 1 + 2 * 13` |
| `:140` | `assert len(pilot) == len(confirmatory) == 2 * 13` |
| `:148` | `assert len(pilot) == len(confirmatory) == 1 + 2 * 13` |
| `:192` | `assert len(pilot) == len(confirmatory) == 13` |

**This is a direct collision with the prohibitions.** The task forbids modifying
the structural-matching test and the disjointness test. Both live in this file,
and all four constants must change for any extension to pass. *Whether editing a
count constant is "modifying the test" is the Commander's call, not mine.* I
flag it rather than assume the permissive reading.

The file's own docstring (`:9-12`) states the stake: the pilot corpus is what
*"fifteen gates were adjudicated against"*, and *"one changed byte would mean
the gate record no longer describes the corpus it was adjudicated on"*. Adding
files changes no existing byte, which is materially safer than editing one — but
it does change what the corpus *is*, and that distinction should be ruled on
rather than assumed benign.

### Q2. Which gates are adjudicated against the pilot corpus?

Nine spikes reference it [M — grep over `smoke/`]: **G-1, G-3, G-6, G-7, G-10,
G-12, G-13, G-14, G-15**.

**None of them enumerates the corpus directory** [M — no `corpus_scenarios`,
`glob("*.json")` or equivalent in any spike]. Every gate names its fixtures.
So adding scenarios changes no gate's scenario count, and no gate's adjudication
is arithmetically invalidated by the addition.

Claim-dependent, and markable deferred: **G-15**, whose dependency column reads
`claim-dependent` on the board (`smoke/README.md:59`). **G-3** is re-triggered
only by a change to frozen row 9 (platform), not by corpus content, so it does
not re-run. **G-14** does not re-run either, but its status is *claim-relevant*:
it is the current carrier for two of the three subcases, and if a campaign cell
ever existed for them, the relationship between gate and campaign evidence would
need restating.

### Q3. Can `campaign_driver` run a named subset and write to a distinct path?

Three parts, three different answers.

**Distinct output path — YES, no sealed change.** `--out` exists
(`campaign_driver.py:291`) and reaches `run_campaign` as
`destination = out if out is not None else output_path(run_mode)` (`:201`).

**Once-only guard — YES, and it already works correctly for an extension.**
`refuse_if_written(destination)` guards *the destination* (`:202`), and is
re-checked after the pass because "the pass took time, and time is when races
happen" (`:281`). A distinct destination therefore gets its own independent
once-only protection automatically. Nothing to change.

**Scenario subset — the capability EXISTS in sealed code but is not reachable
from the CLI.** `run_campaign` already takes a `scenarios` parameter
(`campaign.py:865-868`):

```python
# DEFAULT TO EVERYTHING. A caller that needs a subset must narrow this
# explicitly; the campaign never runs a short list because someone forgot a
# scenario existed.
scenarios = corpus_scenarios(corpus_root) if scenarios is None else tuple(scenarios)
```

and `campaign_driver` already passes it per chain group (`:252`). But the CLI
exposes only `--run-mode`, `--out`, `--no-ledger` (`:290-296`), and the corpus
root comes from `CORPORA`, a two-entry dict (`:54-57`).

**Two further sealed constraints:**

- `check_run_mode` refuses any third mode outright (`campaign.py:241-242`):
  `if run_mode not in ("pilot", "confirmatory"): raise PreconditionFailed(...)`.
  So `--run-mode f3_extension` is impossible without editing sealed code.
- The ledger directory is `results/_ledger/<run_mode>` (`campaign_driver.py:206`).
  An extension run under `run_mode="confirmatory"` would write its ledger rows
  **into the primary campaign's ledger directory**. New scenarios mean new
  filenames so nothing is overwritten, but the two campaigns' ledgers would
  share one directory. Flagged, not decided.

**What would have to change, and whether it is sealed:** an unsealed composition
root under `tools/` could import `campaign.run_campaign` and pass
`scenarios=`, `corpus_root=` and `out=` directly — the ADR 0048 third-exception
pattern already used for `tools/run_row1_decision.py`. That avoids editing
`campaign_driver.py`. It does **not** avoid `check_run_mode`, which the extension
would have to satisfy by running as `confirmatory` from a corpus root outside
`fixtures/pilot/`.

### Q4. v0.9 reseal scope

`fixtures/` carries a **catch-all covered rule** (`seal/build_manifest.py:60-61`):
*"any other fixture artifact, covered by the same rule as the two corpora above
so that no fixture path can fall out of coverage silently."*

So a new `fixtures/f3_extension/` directory is **covered automatically** — the
design specifically forecloses escaping the seal by choosing a new path.

Covered artefacts that would change or be added:

| artefact | change | covered by |
|---|---|---|
| `fixtures/pilot/golden_thread/` — 3 new scenarios × 2 documents | added | `fixtures/pilot/` (`:51`) |
| `fixtures/pilot/golden_thread/generator.py` — `SCENARIOS` + `CONFIRMATORY_SCENARIOS` | edited | `fixtures/pilot/` (`:51`) |
| `fixtures/confirmatory/` or a new extension corpus — 3 new scenarios | added | `fixtures/confirmatory/` (`:55`) or the `fixtures/` catch-all (`:60`) |
| `src/harness/campaign_driver.py` — only if `CORPORA` gains an entry | edited | `src/` (`:46`) |
| `src/harness/campaign.py` — only if `check_run_mode` gains a mode | edited | `src/` (`:46`) |

Not covered, so changing freely: `tests/` (`EXCLUDED_PREFIX`, `:67`), `smoke/`
(`:70`), `tools/`, `drafts/`, `results/`.

New seal artefacts: `seal/manifest_v0.9.json` + `.ots`, with v0.8 moved to
`seal/superseded/`. Counts would move from v0.8's `{tracked 418, covered 167,
excluded 251}` [M — manifest].

### Q5. Is `dpop-first-use-body-mutation` a scenario input or a harness seam?

> **SUPERSEDED by §0's correction.** The answer below is wrong: it is a harness
> seam, but the harness **exposes that seam to scenarios** through
> `credential_fault`. The G-14 evidence quoted remains accurate; the conclusion
> drawn from it does not. Retained so the error is visible.

**A harness seam. It is NOT expressible as a scenario input.**

G-14 C2 constructs it at `smoke/g14/fixture.py:161-164`:

```python
def dpop_body_mutation(self) -> dict:
    """FIRST USE with a mutated body: a fresh id, so the cache cannot help."""
    arm = self._armed_dpop(cache=JtiCache())
    return {"mutated": arm.decide(MUTATED_TOOL, MUTATED_ARGS)}
```

The arm is armed with a genuine proof, then `decide` is called with *different*
tool/args. The divergence is produced **between arming and decision**, by the
caller.

The sealed scenario vocabulary has no such seam. `IntendedInvocation`
(`src/harness/schema.py:120-139`) carries one `tool` and one
`intended_request_digest`; the digest is consumed by the *oracle*, to detect
that an observed request diverged from intent (`oracle/predicates.py:497`).
It is a detector, not a generator — nothing in the scenario says *"sign over X,
present Y."*

**Plainly, as invited: this subcase genuinely cannot be a campaign cell, and
G-14 C2 is its proper and only carrier.** Forcing it would mean adding a second
digest to the sealed schema and a substitution point to the runner, changing how
every existing scenario is loaded.

### Q6. What does the expired-token fixture require?

**An injected clock already exists and is pre-registered** — frozen row 3
requires every consumer to take `now` as an injected parameter, with over-window
fixtures advancing the injected instant and real waiting forbidden. So no SUT
modification is needed for time itself.

> **SUPERSEDED by §0's correction.** The guard does NOT fire on a staged
> fixture: it reads the provisioning setup dict, and a restaged token lives on
> `arm._staged`. The description of the guard below is accurate; the inference
> that it blocks this fixture is not.

**But the guard fires, and that is decisive.** `clock_refusal` is called with the
arm's provisioning setup dict as `credentials` (`campaign.py:931-936`), and
`credential_windows` finds every time-bound credential in it **by shape** —
JWT-shaped or PEM-shaped — explicitly so that "a third time-bound credential
added to any setup is picked up by existing code" (`:451-462`). Any credential
whose window does not cover the judging instant returns a refusal
(`:523-532`), and the cell is routed to `unscorable` (`:938`).

So an expired access token placed in the setup dict makes **every one of the
nine arms unscorable**. The row would produce zero scored cells, not
`A A B B B B B B B`.

The docstring says why this cannot simply be relaxed (`:500-517`): the guard was
built because a real expired Phase-1 token produced *"one defect, two
behaviours, one of them silent"* — capability arms scored `false_block = True`
on the benign control while `B2` arms aborted the pass. Disabling it to admit
this fixture would reintroduce exactly that.

`credential_windows` also records the one escape hatch (`:466-467`): *"HTC, INV
and DPoP proofs carry windows but are minted **inside** the cell at its own
instant and never appear here."* An expired *proof* would evade the guard — but
that is a different subcase from §E.4's `expired token`, whose predicted row
(`A A B B B B B B B`) distinguishes arms by whether they read a **token**.

### Q7. ADR 0044 relative to the campaign commit

**EARLIER, and an ancestor.** [M — git]

| | commit | timestamp |
|---|---|---|
| ADR 0044 first appears | `a2f9730` | 2026-08-07 14:52:19 +0100 |
| campaign / v0.7 seal | `17e11c9` | 2026-08-07 19:01:10 +0100 |

Four hours nine minutes earlier [D], and `git merge-base --is-ancestor` confirms
ancestry. The pre-campaign audit preceded the campaign it audited.

---

## 2. What is actually possible — revised

**Option A — the two staged-credential subcases, as new credential faults.**
`expired_token` and `first_use_body_mutation` join `FAULTS`
(`credential_faults.py:49-56`) with a `_restage_*` implementation each,
following the five that exist. `_restage_token` already swaps the staged access
token; an expired one is the same operation with a different token.
`_restage_dpop_proof` already re-signs the staged proof under a different key;
signing it over different tool/arguments is the same operation with a different
payload. Scenarios select them through the existing `credential_fault` field
(`campaign.py:901`). One sealed file, an established pattern, no schema change,
no runner change.

Still required, and not free: three scenarios in **both** corpora (Q1), the four
count constants (Q1), a v0.9 reseal covering `credential_faults.py` and both
fixture trees (Q4), and a decision on whether the extension runs as
`confirmatory` from a separate corpus root or the driver gains a `CORPORA`
entry (Q3).

**Option B — the replay subcase.** Not reachable this way. It needs a cell that
makes two boundary decisions on one staged proof. That changes what a *cell*
is — one verdict per cell today — and touches ADR 0026 measured segment, which
brackets exactly one `arm.decide`. I would not bundle it with Option A; it is a
different decision with a different risk profile, and it should be ruled on
separately rather than carried along.

**Option C — APPROVED, with the wording the ruling requires.** C is no longer
"this row was not instantiated". The sentence the results chapter carries is:

> Instantiation of `dpop-captured-proof-replay` as a campaign cell was
> **evaluated and judged infeasible**, because it requires a single cell to make
> **two boundary decisions** — verified at `smoke/g14/fixture.py:147-152`, where
> the gate arms the arm once and then calls `arm.decide(TOOL, ARGS)` twice at
> the same injected instant — and this study's measurement unit is one cell, one
> decision. **This judgement was made after the primary results were known**, and
> is therefore not a pre-registration decision. The row's evidence remains gate
> G-14 C1.

Both halves are load-bearing: *verified rather than assumed*, and *after the
primary results were known*. Neither may be dropped when the sentence is
compressed for the page.

**What I would put to you:** Option A **plus** Option C — instantiate the two
that are cheap and honest, and leave the replay row to the gate that was built
for it. That closes `expired-token`, which is the only subcase with **no carrier
at all**, and it does not spend a change to the cell concept on a row whose
limitation is already pre-registered in the strongest terms in the document.

I am not confident enough in Option B cost to recommend for or against it
without reading `src/sut/` and the `Specialist` drive loop, which I have not
done.

## §B — Pre-build verification: Q8, Q9, and a second correction

**Prohibition 3 observed.** In answering these I did not read
`results/raw/campaign-confirmatory.json`, `results/tables/`, or
`results/_ledger/`. Everything below is from `src/`, `tests/`, `smoke/` and the
frozen documents. The prior-session disclosure in §0 still stands and is not
re-litigated here.

### Q8 — does `clock_refusal` still catch a Phase-1 token expiring mid-pass?

**Yes, and the enumeration that makes it work is pinned by a test.** Evidence,
not inference:

1. The Phase-1 access token **is in the provisioning setup dict**:
   `"access_token": access_token` at `src/harness/runner.py:368` (the `b3_setup`
   shape) and `:523` (the `b2_setup` shape). Its origin is the AS —
   `tests/test_credential_enumeration.py:107,112,117` builds these setups from
   `live_as.phase1_tokens[...]`, which is exactly the credential the guard was
   written for.
2. `clock_refusal` reads that dict: it is called with `credentials=setup`
   (`src/harness/campaign.py:933`), and `credential_windows` finds time-bound
   credentials in it by shape (`campaign.py:451-462`).
3. **The set is test-pinned.** `test_the_time_bound_set_is_exactly_this`
   (`tests/test_credential_enumeration.py:142-148`) asserts the discovered
   time-bound set equals `EXPECTED[arm_shape]`, where B2 and B2-DPoP are
   `("access_token", "as_tls_cert_pem")` and B3 is `("access_token",)`
   (`:136-138`). If `access_token` ever left the provisioning dict, that test
   fails rather than the guard silently going blind.
4. The new fault writes somewhere else: `_restage_token` mutates
   `arm._staged.access_token` (`src/harness/credential_faults.py:149-152`), and
   `apply_to_setup` is an explicit no-op whose docstring is
   *"**The arm is provisioned legitimately. Nothing is corrupted here.**"*
   (`credential_faults.py:82-89`).

**Consequence.** The two paths touch disjoint objects. A staged expired token is
invisible to the guard *because the guard inspects provisioning*, and a Phase-1
token aging during a pass remains fully visible *because it never leaves
provisioning*. The fault does not widen the hole the guard closes; it operates
beside it. The guard's own refusal text names the case it keeps
(`campaign.py:527-532`): a credential "minted ONCE, before the pass", recording
"how long the campaign has been running and not what the mechanism did".

`expired_token` is therefore clear to build.

### Q9 — does `invocation_binding_ok` read the mutated tool/args or a snapshot?

**The check point is safe. The seam is on the wrong side of it, and that kills
the fixture.**

*The check point, first, because it is the part that is fine.*
`_invocation_binding_ok(self, p, tool, arguments, state)`
(`src/sut/authz/capability_path.py:726`) re-derives the digest from the **live**
arguments:

```python
if inv["canonical_request_digest"] != h_jcs(dict(arguments)):   # :742
    raise ConjunctFailed("invocation_binding_ok",
        "INV.canonical_request_digest does not match the concrete arguments")
...
    raise ConjunctFailed("invocation_binding_ok",
        "INV.tool does not bind the invoked tool")                # :756
```

No snapshot. The comparison is against what `decide` was actually called with,
so a mutation reaching that call **is** caught. Your stated worry — that INV
might validate a pre-`apply_to_presentation` snapshot — does not occur.

*Now the part that does not work.* Those `tool` and `arguments` reach the arm
from the boundary dispatch, not from anything a fault can touch:
`return arm.decide(tool, arguments)` (`src/harness/runner.py:753`), and the
observer passes straight through (`:1043-1044`). Meanwhile
`apply_to_presentation(fault, arm, ...)` receives **only the arm**
(`credential_faults.py:95-108`) and reaches `arm._staged`.

So a credential fault can move the **signed** side and never the **presented**
side. §D.2's attack, and G-14 C2's construction, move the presented side:
`arm.decide(MUTATED_TOOL, MUTATED_ARGS)` after arming with the genuine proof
(`smoke/g14/fixture.py:161-164`).

**Implementing it credential-side produces exactly the false B you predicted.**
Re-signing the staged INV over different arguments makes
`inv["canonical_request_digest"] != h_jcs(dict(arguments))` fail, so B3 blocks —
but the request that arrived is unchanged, so the oracle's request-tampering
predicate reads **False**:

```python
def observation_was_tampered(intent, observation) -> bool:      # predicates.py:488
    return oracle_request_digest(observation) != _row_value(intent, "intended_request_digest")
```

The cell would record a strong arm blocking a request the independent oracle
certifies as untampered. That is not a measurement of invocation binding; it is
the apparatus disagreeing with itself. The oracle's own docstring frames the
correct pairing — *"an arm that blocks a tampered request produces this `True`
with `realized_harm_F3` `False`, and that pairing is the mechanism working"*
(`predicates.py:492-495`) — and the credential-side construction cannot produce
that `True`.

### The resulting correction — the second in this thread

`first_use_body_mutation` is **NOT implementable as a credential fault.** My
corrected verdict was right that the seam exists and is scenario-selectable, and
wrong that this attack fits through it. The reason is structurally the same one
that rules out replay: the campaign's cell shape does not expose the side of the
boundary the attack has to move.

| subcase | status after Q8/Q9 | carrier |
|---|---|---|
| `expired_token` | **BUILD** — credential-side attack, seam fits, guard intact | campaign cell (extension) |
| `first_use_body_mutation` | **NOT BUILDABLE** as a credential fault | G-14 C2, as now |
| `dpop-captured-proof-replay` | not buildable (two decisions per cell) | G-14 C1, as now |

I am not proposing a way around this. Moving the presented side would mean the
runner handing `decide` something other than what the dispatch produced, which
is the same class of change as B — it alters what a cell *is* — and you have
declined that class for this dissertation.

**What the ruling still buys, and it is the thing that mattered.**
`expired_token` was the only one of the three with **no carrier at all**. The
extension closes exactly that gap and leaves the two rows that already have
G-14 evidence where they are. The outcome is narrower than A as approved, and
better targeted than A as approved.

**A consequence for Q1 that shrinks with it.** One new subcase, not three: one
scenario per corpus rather than three, and the four hardcoded `13` constants
become `14` rather than `16` (`tests/test_confirmatory_corpus.py:83,140,148,192`)
[D]. The collision with the "do not modify the structural-matching test"
prohibition is unchanged in kind, only smaller in size, and still needs your
ruling.

---

---

## §C — the Q1 collision is NOT forced, and the way out is cleaner than either option offered

The earlier report presented one path: add the new subcase to **both** corpora,
and change the four hardcoded `13` constants in the file the prohibition names.
That framing was incomplete.

`tests/test_confirmatory_corpus.py` hardcodes exactly two directories —
`PILOT_DIR` and `CONFIRMATORY_DIR` (`:39-40`) — and every assertion in the file
reads only those two through `_sealed(directory)`. Nothing globs `fixtures/`
broadly. **An extension corpus at a third root is invisible to it.** All four
`13` constants stay true, the structural-match assertions still compare 13
against 13, and both existing corpora stay byte-identical — including the pilot
corpus that fifteen gates were adjudicated against.

The run path supports it with **no sealed-code edit at all** [M]:

| need | provided by |
|---|---|
| a third corpus directory | `run_campaign(corpus_root=...)` — `campaign.py:820` |
| only the new scenario runs | `run_campaign(scenarios=...)` — `campaign.py:810` |
| a distinct output path | `out=` — `campaign_driver.py:201,291` |
| once-only on that path | `refuse_if_written(destination)` — `campaign_driver.py:202`, re-checked `:281` |
| the mode is accepted | `check_run_mode` refuses only a corpus under `fixtures/pilot/` — `campaign.py:245` |

An unsealed composition root under `tools/`, on the ADR 0048 third-exception
pattern already used by `tools/run_row1_decision.py`, can pass all four. The only
covered change left is the new fixture files themselves, which land under
`fixtures/` and are picked up by the catch-all coverage rule
(`build_manifest.py:60-61`) — so v0.9 adds entries and **modifies no existing
covered file**.

**The cost, stated rather than buried.** The structural-matching test is the
**bias guard**, and its own docstring says why: *"Instances authored after
watching the pilot behave are exactly where an author would — without meaning to
— pick easier or harder cases."* A third-root instance sits outside it: no
matched pilot sibling, no identical-subcase-set assertion, no paired
`relation`/`is_benign` check. And this instance is authored after the **primary
results** are known, which is a stronger form of the same hazard than the one the
guard was built for.

So the choice is not "edit the test or not". It is:

- **Path 1 — third corpus root.** No test edit, no prohibition collision, both
  existing corpora byte-identical, no sealed file modified. The instance is
  outside the bias guard, and that absence must travel with every extension
  number. Committed as D-011 clause 7.
- **Path 2 — add to both corpora.** The bias guard applies in full. Four
  constants in the named file change, and both corpora — including the one the
  gate record describes — stop being byte-identical to what was adjudicated.

**I would put Path 1 to you.** The guard it forgoes cannot actually protect this
instance: a matched sibling authored in the same session, after the same results,
by the same author, satisfies the assertion without supplying the independence
the assertion is a proxy for. Path 2 would buy the appearance of the guard and
not the guard. Path 1 forgoes it openly and discloses it, which is the honest
version of the same position — and it leaves the primary campaign's corpus, and
the fifteen gate adjudications that describe it, untouched.

This is a ruling I am not making. Both paths are live until you rule.

---

## S1 — RESOLVED: the scope narrowed to one fixture, deliberately, on a reported finding

**Plainly: the scope narrowed. The numbers are right for the narrowed plan.**
Ruling A approved two fixtures; one of them cannot be built. `expired_token` is
built; **`first_use_body_mutation` is dropped**. Coverage therefore goes 2/5 →
**3/5**, with **two** unbuilt, not 4/5 with one.

It was reported as a finding, not absorbed — §B of this document and commit
`d23fbcc`, whose subject line is *"A narrows to one subcase; body-mutation is not
buildable"*. What I did not do is flag the **arithmetic delta against the
ruling** (4/5 → 3/5) as its own line item, which is how the discrepancy reached
you as numbers rather than as a decision. That is the reporting defect, and it is
mine.

### The evidence, re-verified rather than restated

Your framing of the obstacle — *does `invocation_binding_ok` validate the mutated
tool/args or a pre-mutation staged snapshot* — has a clean answer, and it is
**not** the obstacle:

> `_invocation_binding_ok` re-derives the digest from the **live** arguments:
> `if inv["canonical_request_digest"] != h_jcs(dict(arguments))`
> (`src/sut/authz/capability_path.py:742`), and checks the live tool at `:756`.
> **No snapshot.** A mutation that reached that call would be caught.

The obstacle is upstream of it, and the re-check makes it sharper than my
earlier statement. In `src/sut/agents/specialist.py:58-77`:

```python
def receive(self, envelope: DelegationEnvelope) -> Any:
    """The transport handler: one scripted tool call per delegation."""
    tool = envelope.intent["tool"]                      # :60
    arguments = dict(envelope.intent["arguments"])      # :61
    self._arm.present(
        envelope.credentials,
        InvocationContext(tool=tool, arguments=arguments, ...),   # :66
    )
    return self._tool_caller(tool, arguments)           # :77
```

**The signed side and the presented side are the same two Python locals, read
once from `envelope.intent` and used three lines apart.** The INV is minted over
`tool`/`arguments`; the identical `tool`/`arguments` go to the tool caller, the
boundary dispatch, and `arm.decide(tool, arguments)` (`runner.py:753`, passed
through at `:1043-1044`).

There is no seam between them and no scenario field that separates them, because
there is only **one source**. Meanwhile `apply_to_presentation(fault, arm, ...)`
receives only the arm and reaches `arm._staged` (`credential_faults.py:95-108`) —
the credential, never `envelope.intent`.

Prising the two apart means editing `Specialist`, which is **a SUT agent**.
Modifying the system under test in order to stage an attack against it is not a
fixture; it is the measurement writing its own result. That is the reason this
is a finding and not a cost.

**And building it credential-side instead produces the false B you named.**
Re-signing the staged INV over different arguments makes B3 block, while the
request that arrived is unchanged — so the oracle reads no tampering:

```python
def observation_was_tampered(intent, observation) -> bool:   # predicates.py:488
    return oracle_request_digest(observation) != _row_value(intent, "intended_request_digest")
```

A strong arm blocking a request the independent oracle certifies as untampered
is the apparatus disagreeing with itself, not a result.

`first_use_body_mutation` therefore joins `dpop-captured-proof-replay` with gate
G-14 — C2 and C1 respectively — for structurally the same reason: **the campaign
cell does not expose the side of the boundary the attack has to move.**

---

## P1a — the itemised disclosure list

"Outside the guardrail" is replaced by this table. It is what travels with every
extension number.

### Checks the extension instance DOES undergo

Instance-local checks have no reason not to apply, and all of them do — every one
takes `corpus_root` or is corpus-independent.

| check | where | what it establishes |
|---|---|---|
| Sealed-document schema validation | `IntendedInvocation(...)` construction, `runner.py:981-998` (pydantic) | every sealed field present, correctly typed, `U_task`/`C_sets`/`R`/`tau_gt` well-formed |
| Ω membership of every `(action, resource)` | frozen `Ω`, `omega_gamma_v1.json` | the instance is a harder case, not a malformed request |
| Configuration-family coverage | `check_configuration_families(scenarios=…, corpus_root=…)`, `campaign.py:871` | the monitor configurations this corpus needs are the ones run |
| Frozen-row conformance | `check_frozen_rows()`, `campaign.py:869` | Δ, margins, policy hashes unchanged at run time |
| Run-mode preconditions | `check_run_mode(...)`, `campaign.py:874` — see P1b | no ablation arm, no PILOT-PROVISIONAL policy document |
| Single-process constraint | `check_single_process_campaign(...)`, `campaign.py:879` | ADR 0034 holds for this run too |
| Ledger availability, non-degrading | `check_ledger_available(...)`, `campaign.py:880` | ADR 0014: effect evidence or refusal, never a silent fallback |
| Stack non-duplication | `the_stack_is_not_duplicated()`, `campaign.py:868` | one boundary, one interposition |
| Per-cell clock/validity refusal | `clock_refusal(...)`, `campaign.py:931` | a cell judged outside its credential's window is unscorable, not scored |
| **Oracle independence** | G-12, structural (AST over the oracle source) | **unchanged and fully applicable** — it is a property of the oracle, not of the corpus, so the extension cell is scored by the same demonstrably independent oracle |

### Checks the extension instance does NOT undergo

All six live in `tests/test_confirmatory_corpus.py` and are **pairwise by
construction** — they compare a confirmatory instance against its matched pilot
sibling. A third root has no sibling, so these cannot apply rather than have been
waived.

| check | where | what is therefore not established |
|---|---|---|
| one-to-one matched pilot sibling | `:189-193` | that the instance has a pilot counterpart at all |
| identical subcase and family sets | `:203-211` | that both corpora cover the same ground |
| paired `attack_subcase`/`is_benign`/`requires_approval` | `:196-201` | that the pair agrees on what must not vary |
| paired `relation` | `:213-220` | that the structural relation matches its sibling |
| identical §E.4 prediction across all nine arms per pair | `:222-235` | that the pair predicts identically |
| byte-for-byte pilot regeneration | `:77-83` | *(unaffected: the pilot is untouched, so this still passes as-is)* |

**The honest consequence, stated once and carried:** the extension instance was
authored after the primary results were known, and it is not held to the pairwise
bias guard that the confirmatory corpus is held to. The guard exists because
instances authored after watching a corpus behave are where an author picks
easier or harder cases without meaning to.

### Disjointness — MUST be evaluated across all three roots

Accepted, and it is the one item in the second list that is **not** pairwise by
nature. Set disjointness generalises to three sets; only the current test's
arity is two (`:129-158`, on specification and seed **content hashes**, never on
token bytes — two mints of one capability differ in bytes, ADR 0007).

The standard is ADR 0035's, applied repeatedly in this project: an instance
byte-identical to an existing one **double-counts one instance rather than
measuring a second**. That is precisely why the four `F1-chain-tamper` `NA` cells
survived ADR 0035's audit.

A **new** test asserts three-way disjointness across
`fixtures/pilot/golden_thread/`, `fixtures/confirmatory/` and the extension root,
on specification and seed content hashes. It is a new file, not an edit to
`test_confirmatory_corpus.py`, so the prohibition on modifying the disjointness
test is respected in letter and in purpose.

---

## P1b — `check_run_mode` and the third root: an unconsidered gap, safe in coverage, with one real hazard it creates

**Judgement, not observation.**

The guard's own docstring states its purpose (`campaign.py:233-239`): *"Refuse a
confirmatory run carrying any pilot-provisional artifact. Three ways a
provisional artifact reaches a run, and all three refuse"* — a fixture from
`fixtures/pilot/`, an §E.6 ablation variant, and a policy document still marked
`PILOT-PROVISIONAL`.

**It is a gap in contemplation.** The author was separating two corpora, not
admitting a third. Nothing in the docstring, the error strings, or the structure
contemplates one.

**It is not a gap in coverage.** Of its three limbs, two are corpus-independent
and fire on the extension unchanged: the ablation check reads `arms`
(`campaign.py:250-259`), and the `PILOT-PROVISIONAL` check reads the frozen
policy document (`:263-267`). The third limb — the `fixtures/pilot/` path check
(`:245-249`) — does not fire, and **correctly does not**: the extension corpus is
not the pilot corpus, and the property that limb protects is not at risk.

**But the gap creates a hazard, and it fails toward the hypothesis exactly as you
describe.** `run_mode` is restricted to `("pilot", "confirmatory")`
(`campaign.py:241-242`), so the extension must run as **`confirmatory`**. That
string is then:

- stamped into the output record — `"run_mode": run_mode` (`campaign_driver.py:271`), and
- used to select the ledger directory — `results/_ledger/<run_mode>` (`campaign_driver.py:206`).

So without intervention the extension's own artefact would **declare
`run_mode: "confirmatory"`**, and its ledger rows would land **inside the primary
campaign's ledger directory**. A reader holding the extension JSON alone would
see the same run-mode string the primary campaign carries. That is the precise
confusion the evidence-class separation exists to prevent, and it would arrive by
default rather than by choice.

**Why it is nonetheless safe in this use, given two required mitigations:**

1. The composition root builds its own runner and passes an explicit,
   **distinct ledger directory** (`results/_ledger/f3-extension/`), so no
   extension ledger row lands in the primary campaign's directory. The runner
   accepts `ledger_dir` — `campaign_driver.py:206` passes it — so this needs no
   sealed change.
2. The composition root stamps an explicit `evidence_class` and the seal version
   into the output alongside the inherited `run_mode`, so `run_mode:
   "confirmatory"` can never be read alone (P1c).

Both are recorded as a DEVIATIONS entry rather than left as build notes, because
a dormant check becoming load-bearing is this project's recurring failure and
this is an instance of it caught before it fired.

---

## P1c — the asset Path 1 gives, and how it is claimed

The primary campaign ran under seal **v0.7** at `17e11c9` (2026-08-07 19:01:10)
[M — git]. The extension will run under **v0.9**. The evidence-class distinction
is therefore anchored by two distinct manifests and two distinct OpenTimestamps
chains, not by a label a later editor could change: **anyone can read from the
seal version which body of results predates the other**, and the ordering is
cryptographic rather than asserted.

Path 2 would have destroyed this, because it would have changed the corpus the
v0.7-era gate record describes.

**How it is claimed, concretely:**

- The extension output carries `seal_version`, `seal_manifest`,
  `implementation_commit`, and `evidence_class: "extension"` in its top-level
  metadata.
- Every artefact rendering extension numbers carries a header line naming both
  seals: *primary — seal v0.7, commit `17e11c9`; extension — seal v0.9, commit
  `<hash>`*.
- **One honest limitation:** the primary campaign's own record carries no
  `seal_version` field, and it is write-once and committed, so it is **not
  retro-stamped**. The mapping is stated in the artefacts and derivable from the
  commit each run was executed at; it is not read back out of the primary JSON.

---

---

## Phase 2 — HALTED before any code. The change surface is five sealed files, not one.

**Prohibition observed.** In this phase I did not read
`results/raw/campaign-confirmatory.json`, `results/tables/`, or
`results/_ledger/`.

I told you Option A was *"new entries in `FAULTS` plus their `_restage_*`
implementations in ONE sealed file, following a pattern that file already
implements five times."* That is wrong. I had traced the fault **seam** and not
the **token supply chain** behind it.

### Why one file cannot do it

`expired_token` must present a token that is **validly signed and simply
expired**. A locally forged one fails at the signature and scores as
`invalid_credential`, which is a different attack. So the token must come from
the AS — and the harness is barred from importing it: `runner.py:490` records the
constraint keeping *"the harness from importing `src/sut/oauth_as/`"*. The AS
signing key is seed-derived (`src/sut/oauth_as/keys.py:75-77`) but lives on the
far side of that boundary.

The established route is the one `audience_mismatch` uses: the AS mints an
**additional named grant** and the driver hands the resulting token to the
injector. That route is five files wide.

| # | file | change | sealed? |
|---|---|---|---|
| 1 | `src/harness/as_process.py` | add an `expired` additional grant (`:152`, `:180`, `:213-219`) | **yes** — `src/` |
| 2 | `src/harness/campaign_driver.py` | fetch `agent-supervisor:expired`, pass it down (cf. `:234-240`, `:263`) | **yes** |
| 3 | `src/harness/campaign.py` | plumb the parameter through `run_campaign` (cf. `:822`, `:949`) | **yes** |
| 4 | `src/harness/runner.py` | plumb to `apply_to_presentation` (cf. `:595`, `:810`) | **yes** |
| 5 | `src/harness/credential_faults.py` | `FAULTS` entry + `_restage_token` branch + parameter | **yes** |

One thing goes the easy way: `src/sut/oauth_as/__main__.py:115` already passes
`lifetime_seconds=extra.get("lifetime_seconds", spec.get("lifetime_seconds"))`
per additional grant, so the AS needs no change — the expiry is document data.

### Why this bears on your ruling rather than just on effort

You declined B because it *"re-founds the bookkeeping that already produced
80/0"*, and accepted A because *"A leaves all of that untouched."* On the
corrected surface, **A does not leave all of it untouched**: files 1 and 2 are
the AS provisioning and the campaign driver — the code that produced the primary
campaign.

The honest counter-argument, which I believe is correct but have **not**
demonstrated: every change is **purely additive**. A new additional grant is
minted only if the driver requests it; a new `FAULTS` entry fires only for a
scenario that declares it, and every existing scenario declares `none` or one of
the five. The primary campaign committed JSON is write-once and unchanged either
way, and it remains regenerable by checking out `17e11c9`, where seal v0.7 still
describes the code exactly.

That argument should be **demonstrated, not asserted** — the cheapest
demonstration is that the full suite passes unchanged and that a re-run of the
existing scenarios at the new code produces byte-identical cells. I have not run
either, and on a third consecutive wrong estimate I am not asking you to take my
word for the fourth.

### A second hazard, in the fixture itself

The expired token must be **deterministically** expired, not short-lived. A grant
with a small positive `lifetime_seconds` expires at some point during the pass,
which is nondeterministic and reproduces precisely the apparatus-timing defect
`clock_refusal` was built to catch (`campaign.py:500-517`). The fixture must
back-date `exp` so the token is already expired when minted, and the run must not
depend on how long the pass takes to reach the cell.

### What I need from you

The scope is unchanged and the fixture is still the right one. What changed is
its cost and where it lands. Three ways forward:

1. **Proceed as specified**, with the additive-only property demonstrated before
   the reseal — full suite green, plus byte-identical re-run of the existing
   scenarios at the new code.
2. **Proceed, and treat files 1-2 as the finding** — record in DEVIATIONS that
   the extension modified the primary campaign provisioning and driver, with the
   demonstration attached, so a reader is told rather than left to discover it
   from a manifest diff.
3. **Reconsider A** now that its surface is known, and leave `expired_token` with
   the disclosure it already has: no carrier, stated plainly.

I recommend **2**, and I am not proceeding on my own reading of your ruling when
the premise it rested on has moved.

---

## SPLIT ruling — S1 answered, R2 accepted, Q9/Q10 traced

**Prohibition observed.** I did not read `results/raw/campaign-confirmatory.json`,
`results/tables/`, or `results/_ledger/` in this phase.

### S1 — `first_use_body_mutation` was CUT, and I failed to re-declare it

Plainly: **cut**, not forgotten and not silently assumed. It was cut in the
Q8/Q9 turn on stated evidence (`specialist.py:58-77`), recorded in commit
`d23fbcc`, and I answered S1 on it in the following turn with that evidence.

What went wrong is narrower and is still mine: the Phase-2 halt report traced
only `expired_token` and wrote *"the fixture is still the right one"* —
singular — without restating that the set had already gone from two to one. A
scope that has been narrowed must be re-declared every time the scope is touched
again, not carried silently on the assumption the earlier declaration is still in
view. That is the second scope question passed over, and the rule I am adopting
from it is stated as such.

**And the cut was wrong on its cost.** See Q10.

### R2 — accepted. `expired_token` is not built.

Your reason 1 is the strongest and I had not noticed it. Verified:

```
docs/PRE_REGISTRATION.md:210  | F3 audience mismatch (OAuth neg. control) | A | A | B | B | B | B | B | B | B |
docs/PRE_REGISTRATION.md:211  | F3 expired token (OAuth neg. control)     | A | A | B | B | B | B | B | B | B |
```

The two rows are **byte-identical across all nine arms**. `audience_mismatch` is
already populated, so `expired_token` is a second instance of one predicted
class, not a new class. Its marginal content is whether an arm validates `exp` as
well as `aud` — an OAuth-library question, not a cross-protocol boundary
question.

I am not arguing to reinstate it. Reasons 2 and 3 stand on their own, and reason
1 makes the cost/value ratio clear without them.

**The deterministic-expiry hazard, recorded in case this is ever revisited.** A
grant with a small positive `lifetime_seconds` expires partway through a pass,
which is nondeterministic and reproduces exactly the apparatus-timing defect
`clock_refusal` was built to catch (`campaign.py:500-517`). Any future
`expired_token` fixture must back-date `exp` so the token is already expired when
minted, and must not depend on how long the pass takes to reach the cell.

### Q9 — answered definitively: no snapshot. The mutation IS seen.

`_invocation_binding_ok(self, p, tool, arguments, state)`
(`src/sut/authz/capability_path.py:726`) reads **both** sides at decide time:

- `p` is the staged presentation — the object `apply_to_presentation` has already
  modified, since it runs after `arm.present(...)` returns (`runner.py:805`) and
  before `arm.decide(...)` (`runner.py:753`);
- `arguments` are the live arguments from the boundary dispatch.

```python
if inv["canonical_request_digest"] != h_jcs(dict(arguments)):   # :742
```

Neither operand is a pre-mutation snapshot. A mutation to the staged INV is
visible to the check, and a mutation to the live arguments would be too. **The
check point does not bypass, and cannot yield a false B or false A by that
route.**

### Q10 — traced, not estimated: `credential_faults.py` ONLY. One file.

You were right in R1, and my cut was wrong on cost. I generalised from
`expired_token`'s supply chain to a fixture that has no supply chain.

`first_use_body_mutation` needs **nothing from the AS**, because it needs no
externally-minted material. Everything is already in the arm:

| requirement | already present | evidence |
|---|---|---|
| the arm's own holder key | in the provisioning setup dict | `runner.py:364-367` mints `holder_privates` for `holder-supervisor/-specialist/-worker` |
| reading it from inside a fault | already done | `_rebind_inv` reads `setup["holder_privates"]["holder-specialist"]`, `credential_faults.py:198-201` |
| re-sealing an INV | already done | `seal(INV_TAG, payload, Ed25519PrivateKey.from_private_bytes(raw))`, `:219` |
| writing it back to the staged presentation | already done | `arm._staged = dataclasses.replace(staged, invocation_assertion=...)`, `:217-220` |
| the field to change | `payload["canonical_request_digest"]` | read by the boundary at `capability_path.py:742` |

`_rebind_inv` (`:180-220`) already performs the whole operation and *changes
exactly one field*. A body-mutation fault is the same function changing a
different field. The only genuinely new import is `h_jcs`, from the same
`verifier` package the file already imports `access_token_hash` and
`INV_TAG, seal` from.

**No AS, no driver, no plumbing, no new parameter.** One sealed file, and the
established pattern is not an analogy this time — it is the same function.

### But there is a substantive objection, and it is not cost

Building it this way means the fault **re-signs the INV with the holder's private
key**. That is what makes the mismatch: proof-over-X, request-as-Y.

§D.2's attack is the mirror image — the attacker alters the **request** after the
holder signed it, reusing the holder's genuine untouched proof. G-14 C2 builds it
that way and needs no key: `arm.decide(MUTATED_TOOL, MUTATED_ARGS)` after arming
(`smoke/g14/fixture.py:161-164`).

Two consequences follow, and both are real:

1. **The construction assumes the attacker holds the holder key.** That is the
   compromised-holder premise, which Part D.1 places explicitly out of scope —
   *"B3 does not claim to stop a compromised holder from misusing authority it
   legitimately holds"* (`PRE_REGISTRATION.md:157`) — and which H4b was left NOT
   DETERMINED for want of staging. A fixture that quietly assumes it would be
   measuring inside a premise the study says it does not model.
2. **The oracle would record the difference.** With the request unchanged,
   `observation_was_tampered` reads **False**
   (`oracle/predicates.py:488-497`), where §D.2's attack gives True. The §E.4
   block/admit prediction `A A A A A A A B B` is still reproduced — that
   predicate is *"reported ALONGSIDE `realized_harm_F3`, never folded into it"* —
   so the agreement scoring is unaffected. But the extension cell would carry an
   auxiliary field saying the request was not tampered with, in a row named
   `body-mutation`.

The counter-reading, which I do not think is wrong: `_rebind_inv` already uses
the holder key, and does so precisely to *avoid* measuring the wrong thing —
keeping the token as the only attack surface. On that reading the key use is
apparatus, not modelled attacker capability, and what the fixture measures is
what the row asks: does the boundary bind the invocation to the body.

**I am not cutting this one.** I have cut two subcases and been wrong about the
cost of one of them; this is a judgement about threat-model fidelity, which is
yours. The cost question is settled — one file — and the question left is whether
a proof-side construction is an acceptable stand-in for a request-side attack, or
whether that lands `first_use_body_mutation` in the same place as replay: a row
whose faithful instantiation the campaign cell shape cannot express.

### Consequences of R2 carried forward

F3 coverage with the extension is **3/5** if `body_mutation` is built, and stays
**2/5** if it is not. The primary campaign's own F3 remains **2/5 permanently**
(D-011 clause 6).

**Two unbuilt subcases, two different kinds of gap, never written as one:**

- `dpop-captured-proof-replay` — instantiation **evaluated and judged
  infeasible**, evidenced at `smoke/g14/fixture.py:147-152`, the judgement made
  **after the primary results were known**. Carrier: G-14 C1.
- `expired_token` — instantiation **evaluated and judged not worth its cost**,
  because its §E.4 row is byte-identical to the already-populated
  `audience_mismatch` row (`PRE_REGISTRATION.md:210-211`) and building it would
  have modified the AS provisioning and the campaign driver. **Not infeasible —
  declined.** Carrier: **none**, stated plainly.

D-011 clause 5 covers the first. It needs a second sentence for the second, whose
reason is not infeasibility and must not be blurred into it.

---

## FINAL — the extension collapses. Q11 finds no seam; Q13 finds my own framing was the error.

**Prohibition observed.** I did not read `results/raw/campaign-confirmatory.json`,
`results/tables/`, or `results/_ledger/` in this phase. No code was written, no
artefact touched, no campaign run.

### Q13 — what `d23fbcc` actually cut on, and why my "wrong on cost" was itself wrong

**The cut was made on the seam and on fidelity. Not on cost.** Its two stated
reasons were:

1. *"a credential fault can move the **signed** side and never the **presented**
   side"* — a claim about **capability**, evidenced at `runner.py:753`,
   `:1043-1044` and `credential_faults.py:95-108`; and
2. *"implementing it credential-side produces exactly the false B you
   predicted"* — a claim about **fidelity**, evidenced at
   `oracle/predicates.py:488-497`.

Q10 refuted neither. Q10 priced the **mirror** construction — the very thing
reason 2 had already rejected — and found it cheap. I then wrote that the cut
was *"wrong on its cost"*, which was confused in a way that matters: **the cut
was never made on cost, so a cost finding could not overturn it.** I re-priced a
rejected option and presented the price as a refutation.

You are right that this would have revived a correctly-cut fixture in a
construction that bypassed the decision already made. The reasoning you are now
ruling on in R4 is the same fidelity objection reason 2 raised, in a stronger and
better-grounded form than I gave it.

### R4, R5, R6 — accepted, and R4's decisive reason is one I did not reach

I had the compromised-holder premise (Part D.1, `PRE_REGISTRATION.md:157`). I did
not connect it to **H4a's adversary definition**, where K-none is a *constituent
of the hypothesis* rather than background. A cell requiring K-holder cannot
adjudicate H4a branch (ii) at all — so the mirror construction fails not on
elegance but on the one thing the extension was primarily for.

Your coherence argument is the part I would not have produced: a holder-key
adversary would sign a **valid** assertion over whatever request they wanted,
which is H4b's residual. Signing an assertion that cannot match one's own request
is self-defeating. The real §D.2 attacker is coherent **because** the capability
constraint produces the attack shape — lacking the key, he alters what he can
(the body) and reuses what he cannot (the genuine proof). The mirror inverts
that and keeps only the silhouette.

R5 accepted: `_rebind_inv` uses the key to **maintain** consistency so a fault
created elsewhere stays the sole attack surface; the mirror uses the key to
**manufacture** the fault. Same function, opposite direction. My report joined
"same function" (cost) and "therefore fine" (fidelity) in one sentence, which is
exactly the elision.

### Q12 — confirmed, and worse than I stated: a class_macro quantity inverts

`realized_harm_F3` (`oracle/predicates.py:~465-485`) walks the effect set:

```python
observed = oracle_request_digest(observation)
for effect in effects_of(ledger, cid):
    actual = _row_value(effect, "effect_request_digest")
    if actual != intended:  return True   # not what the task authorized
    if actual != observed:  return True   # diverged from what arrived
```

| | real §D.2 attack | mirror construction |
|---|---|---|
| intended (sealed) | X | X |
| what arrives | **Y** (mutated) | X |
| what an admitting arm forwards | Y | X |
| `actual != intended` | Y ≠ X → **True** | X ≠ X → False |
| **`realized_harm_F3`** | **True** | **False** |

So for the **seven admitting arms**, `realized_harm` inverts. That is not a
reported-alongside diagnostic: `realized_harm` is one of the six `class_macro`
quantities and is TAB-4 body content and F3 per-family count material.

`effect_count` does **not** differ — the tool runs either way. That makes it
worse, not better: the cell would look populated and well-formed, with an effect
recorded, and only the field saying whether harm occurred would be wrong. A row
named `body-mutation` would report that seven arms forwarded an attack and none
of them realised any harm, because none of them did — there was no attack in the
request.

### Q11 — NO. The faithful construction needs a seam that does not exist.

The faithful attack mutates the **dispatch arguments** after the INV is sealed
and before dispatch, leaving proof and INV untouched. Traced:

1. `Specialist.receive` reads `arguments = dict(envelope.intent["arguments"])`
   (`specialist.py:61`) — one fresh dict.
2. It passes that dict **by reference** into `InvocationContext`
   (`specialist.py:66`); the field is `arguments: Mapping[str, Any]`
   (`src/sut/baselines/base.py:183`), no defensive copy. **An alias therefore
   exists.**
3. `arm.present(...)` consumes it to compute `h_jcs(arguments)` into the INV
   payload, and **drops it**. `B3Presentation` is `@dataclass(frozen=True)` and
   carries only wire material — `capability_hops`, `htc_chain`,
   `invocation_assertion`, `access_token`, `task_id`, `audience`, `method`,
   `now_epoch`, labels, approval artifact, `resource_owner`, `oauth_actor`
   (`capability_path.py:323-344`). **No `arguments` field. No
   `InvocationContext`.**
4. `Specialist` then dispatches with its own local: `self._tool_caller(tool,
   arguments)` (`specialist.py:77`).

`apply_to_presentation(fault, arm, ...)` receives **only the arm**
(`credential_faults.py:95-108`). The arm retains no handle to the arguments dict,
so **the fault has no path to the object the alias points at.** The alias lives
in the Specialist's frame and nothing reachable from the fault holds it.

**Cost of creating the seam, exactly, per your instruction:**

- *Mutate `Specialist`* — a **SUT agent**. Modifying the system under test to
  stage an attack against it is the measurement writing its own result. Refused
  on principle, not on cost.
- *Add a harness-side interception between `present` and dispatch* — a new
  capability in `runner.py` and the tool-caller path (`runner.py:789-820`, the
  `_LateBoundToolCaller` at `:807`). It changes the dispatch path **for every
  scenario in every campaign**, not only for this fixture, and it is sealed
  `src/`. That is the multi-file cost that killed `expired_token`, on a hotter
  path.

Per your standing instruction I am reporting and stopping. **I have not built the
mirror as a fallback and am not looking for a third construction.**

### The extension collapses, and I agree it is the acceptable outcome

- **F3 coverage stays 2/5.** No extension instance is built.
- **`dpop-captured-proof-replay`** — evaluated, judged **infeasible**, evidenced
  (`smoke/g14/fixture.py:147-152`), judgement made after the primary results were
  known. Carrier: G-14 C1.
- **`expired_token`** — evaluated, judged **not worth its cost**, evidenced
  (its §E.4 row is byte-identical to the populated `audience mismatch` row,
  `PRE_REGISTRATION.md:210-211`). Not infeasible. Carrier: **none**.
- **`first_use_body_mutation`** — evaluated; the faithful construction **needs a
  seam the harness does not have**, and the available construction requires
  K-holder, which H4a's adversary definition excludes as a constituent of the
  hypothesis. Carrier: **G-14 C2**.
- **H4a stays NOT DETERMINED**, carried by G-14 C2 — which is built faithfully,
  needs no key, and reads the DPoP claim set directly off the artifact rather
  than inferring the limitation from an outcome (`smoke/g14/spike.py:149-157`).

Three subcases, three distinct reasons, none of them "we did not get to it". That
is a better paragraph than a fourth coverage tick would have been.

**D-011 closes unbuilt.** It was a pre-commitment for an extension that is not
happening; nothing it constrained was ever executed, and the entry stands as the
record that the constraints were fixed before the question was settled rather
than after.

---

## 3. Sections B, C, D — not written, and why

The task's §B (fixture specifications), §C (extension execution design) and §D
(evidence-class labelling) all presuppose that at least one subcase can become a
campaign cell. None can. Writing fixture specifications for cells the harness
cannot run, or an evidence-class scheme for rows that cannot exist, would be
producing plausible work product for an outcome the investigation has ruled out.
They are withheld deliberately, not overlooked.

If the Commander rules for Option 2, §B/§C/§D become writable and I will produce
them against whatever seam the ruling authorises. If the Commander rules for
Option 3, the equivalent sections belong to a gate design, not a corpus plan.

---

## 4. §F — DEVIATIONS.md entries, for the Commander to commit

Two are owed, not one: the correction, and whatever is decided.

> ## D-010 — A detailed, sourced, wrong report would have been executed; the scoped-negative rule is what stopped it
>
> **Status:** CLOSED on the same day it opened.
> **Date:** 2026-08-16.
>
> The F3 extension feasibility report first concluded that all three unpopulated
> subcases were impossible as campaign cells, and recommended extending a gate
> instead. Two of those three findings were wrong. The report had flagged its own
> residual — the negative was established over `schema.py` and `runner.py`, not
> over all of `campaign.py` or `src/sut/` — and closing that residual found
> `src/harness/credential_faults.py`, whose `apply_to_presentation` is exactly
> the signed-vs-presented seam the report said did not exist, and which is
> already scenario-selectable through a `credential_fault` field.
>
> A second error travelled with it: `clock_refusal` was said to make an
> expired-token fixture unscorable. It inspects the **provisioning** setup dict;
> a restaged token lives on `arm._staged`. Two different objects.
>
> **The failure mode, which is the point of this entry.** A report can be
> detailed, sourced to file:line, internally consistent, and wrong — and in that
> combination it does not look like a report that needs checking. It would have
> been executed. What stopped it was not review and not a second opinion: it was
> the rule, adopted after the CLAIMS_LEDGER incident, that a negative conclusion
> must state the scope over which it was established. That rule looked like
> formalism when it was adopted. It is the only thing that worked here, twice —
> the same declared residual also caught the §B error below.
>
> No artefact, fixture, or campaign was built on the wrong finding; nothing needs
> unwinding.

> ## D-011 — Pre-commitment: the F3 `expired_token` extension
>
> **Status:** OPEN — to be committed BEFORE any code is written, alone, with no
> result-bearing content, following the D-009 precedent verified from git
> (`6da1570` 22:43:49, the runner not yet written; verdict at `2284837`
> 22:55:36, eleven minutes and forty-seven seconds later).
> **Date:** 2026-08-16.
> **Scope:** ONE subcase. The ruling approved two; Q8/Q9 established that
> `first_use_body_mutation` cannot be built as a credential fault, so it stays
> with G-14 C2 alongside `dpop-captured-proof-replay` with G-14 C1.
>
> 1. The extension is a **separate, once-only campaign**.
>    `results/raw/campaign-confirmatory.json` is not re-run, not overwritten and
>    not superseded; its cells and its agreement remain the primary result.
> 2. The `F3 expired token` §E.4 row — `A A B B B B B B B` — is **frozen** and is
>    not edited. An instance is added; the prediction is not. If a measured outcome contradicts a frozen
>    prediction, that disagreement is **reported as the finding it is** and the
>    matrix is not amended to match it.
> 3. The extension rows are reported at a **distinct evidence class** in every
>    artefact and in prose, and never inside a primary-campaign count. The fact
>    that they were instantiated **after the primary results were seen** travels
>    with every extension number.
> 4. Whatever the extension measures is reported as returned, including a result
>    that weakens this study own position.
> 5. The two subcases that are NOT built are stated in the results chapter in the
>    form the ruling fixes: instantiation was **evaluated and judged infeasible**,
>    on evidence, **after the primary results were known** — not left to be
>    inferred from a coverage fraction, and not written so it reads as a
>    pre-registration decision. `B3+` dependence on G-14 C1 is restated in the
>    same place.
> 6. F3 coverage becomes **3 of 5** subcases once the extension runs, and that
>    fraction replaces 2/5 on every F3-bearing artefact. The primary campaign's
>    own F3 coverage remains **2 of 5** and is never restated as 3 of 5: the
>    third instance is not one of its cells.

## 5. Prohibitions observed

- §E.4 expected matrix: not read for editing, not edited. The three frozen rows
  are quoted in this document from the Commander's own task text only.
- `results/raw/campaign-confirmatory.json`, `results/tables/`,
  `results/_ledger/`: **not read during this task** — with the prior-session
  disclosure in §0 above.
- Oracle, scoring predicates, structural-matching test, disjointness test,
  existing scenarios: read only; nothing modified.
- No campaign run. No code written. No artefact touched.
