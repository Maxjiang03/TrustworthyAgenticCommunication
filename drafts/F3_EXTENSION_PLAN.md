# F3 corpus extension — Phase 0 report and feasibility verdict

**Status: RED STATE. STOPPED, NOT WORKED AROUND.**
Date: 2026-08-16. Phase 0 only; no code written, no artefact touched, no campaign run.

---

## 0. Verdict, first

The Commander's ruling — instantiate the three unpopulated F3 subcases as a
separate once-only extension campaign — is **technically impossible under the
prohibitions as written**. Not for one subcase, but for all three, and for three
*different* reasons. Per the standing instruction I have stopped and am
reporting rather than falling back to any workaround.

The obstruction is not the seal, not the "run once" property, and not the output
path. Those are all solved or solvable. **The obstruction is that the sealed
scenario vocabulary cannot express any of the three attacks.** A campaign
scenario describes exactly one invocation; each of these three subcases needs
something a single invocation record cannot carry.

| subcase | what it needs | why the campaign cannot express it |
|---|---|---|
| `dpop-first-use-body-mutation` | the presented tool/args to differ from the signed ones | `IntendedInvocation` carries **one** digest, `intended_request_digest` (`src/harness/schema.py:129`). There is no signed-vs-presented pair. |
| `expired-token` | an expired credential in the arm's setup | `clock_refusal` refuses exactly this shape and routes the cell to `unscorable` for **every** arm (`src/harness/campaign.py:523-532`). Zero scored cells. |
| `dpop-captured-proof-replay` | two presentations of one proof | The schema describes **one** invocation; `grep -niE "replay\|second_use\|repeat\|duplicate"` over `runner.py` and `schema.py` returns **nothing**. No replay seam exists. |

`attack_subcase` cannot rescue any of them: it is consumed only for family
grouping and as a recorded label (`campaign.py:669`, `:898`; `schema.py:139`).
It switches no attack behaviour, so a new subcase string produces no new
behaviour.

**Scope of the "does not exist" conclusion.** Established over
`src/harness/schema.py`, `src/harness/runner.py`, and the `attack_subcase`
call sites across `src/`. I did not exhaustively read all ~1000 lines of
`src/harness/campaign.py` nor `src/sut/`. If the Commander wants the negative
strengthened, that is the remaining place to look.

**Blindness disclosure, stated plainly.** During this task I did not read
`results/raw/campaign-confirmatory.json`, `results/tables/`, or
`results/_ledger/`. I had, however, read them earlier in this same session for
the fresh-clone verification pass, so those numbers were already in my context.
I cannot honestly claim to have designed blind, and I am not going to pretend
otherwise. Nothing below is derived from them.

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

## 2. What is actually possible

Stated so the Commander can rule, not as a recommendation to proceed.

**Option 1 — accept the finding.** All three subcases remain NOT POPULATED, and
the results chapter reports them exactly as the pre-registration already
requires, with G-14 C1/C2 named as carriers for two and **no carrier** named for
`expired-token`. Zero code, zero reseal, zero risk. The honesty cost is already
being paid and is already pre-registered.

**Option 2 — extend the sealed scenario vocabulary.** Add a signed-vs-presented
digest pair and a replay seam to `IntendedInvocation` and the runner, and give
`clock_refusal` a narrow, named exemption for a deliberately-expired fixture.
This is a v0.9 unseal/reseal touching `src/harness/schema.py`,
`src/harness/runner.py` and `src/harness/campaign.py`, plus both corpora, plus
four count constants in the structural-matching test. It changes how every
existing scenario is loaded. **My assessment: the risk is not proportionate to
the gain**, because the three rows' predictions are already carried by gate
evidence or already reported as uncarried, and the primary campaign's authority
rests on the apparatus these edits would touch.

**Option 3 — extend the GATE, not the campaign.** `smoke/` is excluded from the
seal (`build_manifest.py:70`). A new gate limb — G-14 C4, or a G-16 — could
carry `expired-token` at the same evidence class as C1/C2, closing the one
subcase that currently has **no carrier at all**. No reseal, no corpus change,
no test constant edited, and it directly addresses the weakest link identified
in the earlier F3 analysis.

**Option 3 is the one I would put to the Commander.** It buys the thing actually
missing (a carrier for `expired-token`) at the lowest cost, and it does not
pretend a gate is a campaign.

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

## 4. §F — DEVIATIONS.md entry, for the Commander to commit

The pre-commitment now owed is not "we will build three fixtures". It is the
finding itself, recorded before any decision follows from it.

> ## D-010 — The three unpopulated F3 subcases cannot be campaign cells
>
> **Status:** OPEN — recorded before any remedial decision is taken.
> **Date:** 2026-08-16.
> **Authority:** Commander ruling of 2026-08-16 (extension campaign), and the
> stop-and-report instruction that accompanied it.
>
> **What was asked.** Instantiate `dpop-first-use-body-mutation`,
> `expired-token` and `dpop-captured-proof-replay` as a separate once-only
> extension campaign, leaving `campaign-confirmatory.json` untouched.
>
> **What was found.** The obstruction is not the seal, the run-once property, or
> the output path — all three of those are solved. The sealed scenario
> vocabulary cannot express any of the three attacks. `IntendedInvocation`
> (`src/harness/schema.py:120-139`) describes exactly one invocation: one tool,
> one `intended_request_digest`, no replay field, no signed-vs-presented pair.
> `attack_subcase` is a label consumed only for family grouping and switches no
> behaviour. And `clock_refusal` (`src/harness/campaign.py:523-532`) refuses any
> setup credential whose window does not cover the judging instant, routing the
> cell to `unscorable` for every arm — which is precisely the shape an
> expired-token fixture has.
>
> **What follows, pre-committed.** The three rows remain NOT POPULATED BY THE
> CAMPAIGN and are reported exactly as pre-registered §4 requires. This entry
> does not authorise a fixture, a reseal, or a campaign run. If a remedy is
> later adopted, it is recorded here as its own decision with its own reason,
> and this finding is not edited to match it.
>
> **The residual, stated rather than left implicit.** `expired-token` has no
> carrier at all: G-14's C1 and C2 carry the other two, and no gate names it.
> That gap is a fact about this study's evidence base and travels with any
> statement about F3 coverage.

---

## 5. Prohibitions observed

- §E.4 expected matrix: not read for editing, not edited. The three frozen rows
  are quoted in this document from the Commander's own task text only.
- `results/raw/campaign-confirmatory.json`, `results/tables/`,
  `results/_ledger/`: **not read during this task** — with the prior-session
  disclosure in §0 above.
- Oracle, scoring predicates, structural-matching test, disjointness test,
  existing scenarios: read only; nothing modified.
- No campaign run. No code written. No artefact touched.
