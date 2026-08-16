# F3 corpus extension — Phase 0 report and feasibility verdict

**Status: AMBER. Two subcases feasible, one not. Phase 1 B/C/D awaiting your ruling.**
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

**Option C — leave the replay row to G-14 C1, as now.** The pre-registration
already states plainly that `B3+` ladder position rests on gate evidence and
that a reader may weigh gate evidence differently. Option A would close the two
subcases that currently have carriers, and leave the one that already has the
most explicit disclosure exactly where it is.

**What I would put to you:** Option A **plus** Option C — instantiate the two
that are cheap and honest, and leave the replay row to the gate that was built
for it. That closes `expired-token`, which is the only subcase with **no carrier
at all**, and it does not spend a change to the cell concept on a row whose
limitation is already pre-registered in the strongest terms in the document.

I am not confident enough in Option B cost to recommend for or against it
without reading `src/sut/` and the `Specialist` drive loop, which I have not
done.

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

> ## D-010 — A feasibility finding was reported wrong, and corrected before it was acted on
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
> **Recorded because the failure mode is the point.** The first report was
> detailed, evidenced, and wrong, and it would have been acted on. What caught it
> was not review but the residual the report itself declared. A stated scope on a
> negative finding is not a formality.
>
> No artefact, fixture, or campaign was built on the wrong finding; nothing needs
> unwinding.

> ## D-011 — Pre-commitment: the F3 extension, if authorised
>
> **Status:** OPEN — to be committed BEFORE any code is written.
> **Date:** 2026-08-16.
>
> 1. The extension is a **separate, once-only campaign**.
>    `results/raw/campaign-confirmatory.json` is not re-run, not overwritten and
>    not superseded; its cells and its agreement remain the primary result.
> 2. The three §E.4 rows predictions are **frozen** and are not edited. Instances
>    are added; predictions are not. If a measured outcome contradicts a frozen
>    prediction, that disagreement is **reported as the finding it is** and the
>    matrix is not amended to match it.
> 3. The extension rows are reported at a **distinct evidence class** in every
>    artefact and in prose, and never inside a primary-campaign count. The fact
>    that they were instantiated **after the primary results were seen** travels
>    with every extension number.
> 4. Whatever the extension measures is reported as returned, including a result
>    that weakens this study own position.
> 5. If the replay subcase is not built, that is stated, with `B3+` dependence
>    on G-14 C1 restated in the same place — not left to be inferred from a
>    coverage fraction.

## 5. Prohibitions observed

- §E.4 expected matrix: not read for editing, not edited. The three frozen rows
  are quoted in this document from the Commander's own task text only.
- `results/raw/campaign-confirmatory.json`, `results/tables/`,
  `results/_ledger/`: **not read during this task** — with the prior-session
  disclosure in §0 above.
- Oracle, scoring predicates, structural-matching test, disjointness test,
  existing scenarios: read only; nothing modified.
- No campaign run. No code written. No artefact touched.
