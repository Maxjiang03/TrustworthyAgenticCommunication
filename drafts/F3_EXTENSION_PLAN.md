# F3 corpus extension — Phase 0 report and feasibility verdict

**Status: ONE subcase buildable (`expired_token`). Ruling A+C received; Q8/Q9 narrowed A to one of its two members.**
*(The original status was RED on all three; that verdict was wrong and is corrected in section 0.)*
Date: 2026-08-16. Phase 0 only; no code written, no artefact touched, no campaign run.

---

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
