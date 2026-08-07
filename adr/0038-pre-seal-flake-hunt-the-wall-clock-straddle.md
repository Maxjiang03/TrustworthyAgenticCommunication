# 0038 — The pre-seal flake: a **wall-clock straddle** in test fixtures

## Context

Fifteen gates pass and the DAG is closed at `55c1282`. What remains is the pre-registration, the
seal, and one confirmatory campaign — and **after the seal nothing may change**. An intermittent
defect that survives the seal cannot be fixed without invalidating the campaign, and a campaign
result produced by a racing apparatus is not a measurement. Two sightings were outstanding, one of
them with an **unnamed second failure**.

## The reproduction condition, named

| condition | reproduction rate |
|---|---|
| `tests/test_f45_matrix.py` alone, 6 busy loops, 20 CPUs available | **0/6** |
| `tests/test_f45_matrix.py` alone, **pinned to one CPU**, 3 busy loops | **0/4** |
| **full suite (`tests`), pinned to one CPU, 3 busy loops** | **2/3** |

The pinning is what makes the third row a real condition rather than a weaker one: the module-only
runs went from 2.5 s to ~15 s wall clock, so contention **did** bite, and they still did not
reproduce. **The full suite does.** Sighting B was measured in a container reporting one CPU, and the
full suite is what it ran.

Wall-clock durations here are **run metadata** — how long a condition took to exercise. They are not
latency figures; G-3 owns cost and its numbers live in `smoke/g3/REPORT.md` only.

## Every failure, named

Two of the three runs were **1 failed / 1228 passed**; the third was green (1229 passed). **The failing test was different in each of the two red runs**:

**Run 000** — `tests/test_b3_plus.py::TestTheCellB3PlusExistsFor::test_the_replay_is_constructed_WITHIN_delta`

```
assert freshness.is_fresh(now, now)
assert arm.decide("notes.write", ARGS)[0] is True
E   assert False is True
```

The **first** submission — the one that must be admitted before a replay can be tested — was refused.

**Run 001** — `tests/test_frozen_authorizer_semantics.py::test_appended_widening_verifies_but_does_not_widen`

```
assert c2 <= c1
E   AssertionError: assert frozenset({('...es/project')}) <= frozenset({('...es/meeting')})
E     Extra items in the left set: ...
```

An authority set computed at one instant was compared against one computed at another.

> **Corrected by [0039](0039-one-clock-per-cell-the-campaign-adopts-the-cells-clock.md) — this
> attribution only.** That module reads **no wall clock at all**: `NOW` and `EXPIRY` are frozen
> `datetime` constants and `src/harness/authorizer/allowed.py` reads no clock, so there are not two
> clocks here to straddle. Run 001's cause is **undetermined**; 0039 §Site A records a named
> candidate and applies no fix on it. **Run 000's attribution also moved** — 0039 locates its
> straddle at the OAuth access token's 300 s lifetime rather than at Δ — but the straddle diagnosis
> itself stands for run 000. Everything else below is unaffected.

## Root cause

**Fixtures that read the wall clock more than once, and compare the results as if the reads were
simultaneous.** Under severe slowdown the two reads straddle a validity boundary — an INV freshness
window (`Δ`), a token lifetime, or the authorizer's own `time` fact — and a quantity that was valid
when constructed is judged after it expired.

That is the **same shape** as two defects this project has already fixed: `test_b_cap.py`'s
`test_expiry_is_verified` (EXP7), which re-read `int(time.time())` for its negative arm against a
one-second token, and the fixtures blocks 4 and G-14 corrected. It is the **two-clocks hazard** in
its fourth and fifth instances.

**That the failing test differs run to run is the strongest evidence for this cause and against a
per-test bug**: nothing is wrong with either named test in particular. What fails is whichever
time-sensitive assertion happens to be executing when the machine is slow enough for a window to
close mid-test.

## The stated lead, ruled out on evidence

The handoff recorded a lead: `B-cap` / `B3` / `B3⁺` are provisioned from **one shared `b3_setup`
dict**, shallow-copied per arm, with `B3⁺` last. **The sharing is real** — eight nested objects
(`gamma_document`, `registry_document`, `policy_document`, `holder_privates`, `resolved_keys`,
`as_public_jwk`, `label_issuers`, `approvers`) are the same objects in all three arms.

**It is not the cause.** Measured directly: provisioning the triple from one dict mutates **nothing**
in it, and a full `delegate` → `present` → `decide` cycle for all three arms mutates **nothing**
either, with all three admitting `gt-f4-declassified` correctly. `load_document()` also returns a
fresh object per call rather than a memoised singleton. **The sharing exists and is never written
through.** Ruled out as stated, not as assumed.

## One cause or two — and what is still undetermined

**Sighting A and the two reproductions almost certainly share one cause**: A's named test is
`TestF3ExpiredToken::test_the_block_is_attributable_to_the_TOKEN_not_to_a_masking_limb`, which turns
on a 30 s token lifetime judged 45 s later — the same straddle, in a module whose own docstring
records that the window was **already widened once from 5 s**.

**Sighting B is NOT shown to be the same cause, and this ADR does not claim it is.** B's failures
were three `test_f45_matrix.py` cells with `b3_containment` on a benign control, and this session
**did not reproduce them** (0/6 and 0/4 under two named conditions, neither of which was B's
container). Whether B is the same straddle, or a distinct defect, is **undetermined**.

## Direction of failure

- **The two reproductions read AGAINST the hypothesis.** Both make a capability arm look worse than
  it is: `B3⁺` refusing a first submission it should admit, and an authority set appearing to widen.
- **Sighting A reads TOWARD the hypothesis.** Its assertion is that a block is attributable to the
  token rather than to a masking limb; failure means a masking limb fired — Trap 1, a cell reading
  `B` while measuring something else.
- **Sighting B reads AGAINST the hypothesis** — a spurious false block on a benign control.

So the project's §6.1 pattern (*every dormant defect failed toward the hypothesis*) **does not hold
here**. Three of the four known instances fail against it. That is worth recording precisely because
it breaks the pattern: a timing straddle is direction-agnostic, which is what distinguishes it from
the masking defects earlier blocks found.

## Fix location — REFERRED, not applied

The cause is in **test fixtures**, not in `src/sut/` or `src/harness/`: no arm and no harness module
was changed or needs to be, and the sharing that was suspected is inert. The fix is to make every
time-sensitive fixture take **one** instant and inject it, as `_token_window()` and the G-14 fixture
already do.

**It is not applied here.** This session's budget went to reproduction and root cause, which the task
names as the success condition; a fix landed without its own failing-world demonstration would be
the outcome the task forbids. **No frozen parameter was touched, no window widened, no retry added,
no test marked flaky, and nothing in `src/` changed.**

## Sighting C — the A1 seventy-error run, WATCHED AT THE RESEAL AND NOT REPRODUCED

**Recorded 2026-08-06, during task A2's PHASE 1, in this ADR's sighting form rather than as a
resolved defect.** Wall-clock durations below are **run metadata** — how long a condition took to
exercise — on the same footing as the reproduction table above. They are not latency figures; G-3
owns cost and its numbers live in `smoke/g3/REPORT.md` only.

**Sighting C, as first seen (task A1, 2026-08-06).** One full-suite run produced **70 errors, all
in `tests/test_sut_mode_equivalence.py`**, and took about **24 minutes**. It was reported at the
time with the explanation *transient resource contention*, because nine gate spikes were running
concurrently and the same file passed standalone in 8.4 s immediately afterwards, with the very
next full suite green in 34.6 s.

**What the reseal watch measured.** The Commander required the sighting watched during PHASE 1 and
recorded here rather than dismissed. Every run below is a full `tests` run on the row 9 machine:

| run | result | wall clock |
|---|---|---|
| A1, concurrent with nine gate spikes | **70 errors** (`test_sut_mode_equivalence.py`) | ~24 min |
| A1, immediately after, same file alone | 74 passed | 8.4 s |
| A1 × 2, declarations task × 2, PHASE 0 | 1396 / 1396 / 1406 / 1406 / 1408 passed | 33.9–43.6 s |
| **PHASE 1 watch, nothing running concurrently** | **1408 passed, ZERO errors** | **2682 s (44 m 42 s)** |
| immediately after, same file alone | 74 passed | 7.97 s |
| immediately after, full suite with `--durations` | 1408 passed | **33.21 s** |

**The seventy-error failure did NOT recur.** Across six subsequent full-suite runs the suite is
green, and the PHASE 1 watch itself was green.

**A second anomaly did occur, and it falsifies the explanation A1 offered.** The PHASE 1 watch was
green but took **roughly seventy times** the surrounding runs, on an idle machine with **nothing
running concurrently** — so *transient resource contention from concurrent gate spikes* cannot be
the cause of that run, and by extension is no longer evidence for the first. It did not reproduce:
the next full run, minutes later, was 33.21 s.

**Ruled out on evidence, not by argument.** No leaked or spinning process survives the gates — the
process table was read immediately after the slow run and carried no `python`/`uv` process at all.
The named file is not the locus in isolation: 7.97 s standalone, taken between the slow run and
the fast one. `--durations=12` on the fast run puts the slowest single item at 7.16 s of setup in
that same file, with nothing else above 2.7 s, so no test accounts for the missing 44 minutes.

**Cause: UNDETERMINED, for both the seventy-error failure and the wall-clock anomaly, and this ADR
does not claim they share one.** They are recorded as sightings under this ADR's existing standard:
Sighting B is likewise not shown to be Sighting A's cause and is not claimed to be.

**What it does not touch.** The five platform-bound gates all ran **before** this watch, in the
required order, with row 9 read before the first and after the last and **zero of 37 leaf values
differing**. G-3's fifth median (2.6772 ms) falls inside the range of the four runs on record and
separates from the adjudicated run exactly as the pre-registration declares. So the anomaly is not
visible in any sealed figure — but it is inside the v0.6 seal's measurement session, which is
precisely why it is written down here instead of being left in a chat log.

**Consequence for the confirmatory campaign (Part H step 7).** The campaign's security verdicts are
exact counts and deterministic (§5 of the pre-registration), and repetition is used only to detect
nondeterminism, so a slow run is not by itself a threat to them. But an unexplained 70× wall-clock
excursion on the campaign machine **must be reported if it occurs during the campaign**, and a
campaign run exhibiting it must not be quietly accepted as equivalent to one that did not.

## Sighting D — the frozen-authorizer positive arm, full-suite only, CAUSE UNDETERMINED

**Seen 2026-08-07**, during the ADR 0044 repair work, at HEAD `d99cd60`.

`tests/test_frozen_authorizer_semantics.py::test_frozen_gamma_denies_third_party_widening` failed
its **positive arm** — *"a genuinely granted element still authorizes on the same token"* —
with `assert False is True`. The negative arm (the third-party widening fact is denied) passed;
what failed is a **legitimate authorization being refused**.

| condition | runs | failures |
|---|--:|--:|
| full suite, no added contention | 6 | **1** |
| full suite, no added contention (earlier, same HEAD) | 6 | 0 |
| the file alone, no contention | 8 | 0 |
| the file alone, **16 busy-loop workers** | 6 | 0 |

**A proposed mechanism was tested and REFUTED.** `authorize_candidate` catches
`AuthorizationError` and returns it as a **deny**, and `biscuit-rust`'s authorizer carries an
internal evaluation time limit — so "under load the limit trips and a timeout is recorded as a
refusal" is a mechanism that would fit the full-suite-only pattern exactly. It does not survive
its own test: **16-way CPU contention on the file alone reproduced nothing (0/6)**. The
hypothesis is recorded as falsified rather than deleted, because the next person to see this will
think of it too.

**Cause: UNDETERMINED.** What is known: it needs the full suite (never reproduced in isolation
under any condition tried), and the suite runs under `pytest-randomly`, so test ORDER differs per
run — which is consistent with a cross-test state dependency and inconsistent with pure load.
That is a direction, not a finding, and it is not claimed as one.

**Why this one matters more than a flaky test usually would.** Gate **G-2** is one of the three
construct-validity life-or-death gates (red line 3), and this is a G-2 semantics test. The path it
exercises is the one `Allowed(P_i; Γ, κ, Ω)` runs **once per candidate element** to compute every
`C_i`. If a legitimate authorization can intermittently return a denial, an authority set could be
computed **smaller than it is**, and the campaign's amplification measurement is a function of
exactly those sets. **The direction is AGAINST this work's hypothesis** (a capability arm looking
more restrictive than it is), which is the same direction as Sightings B and the two ADR 0038
reproductions — the §6.1 pattern still does not hold.

**The pre-repair control, run rather than argued.** A fresh clone at `cdf185d` — the v0.6 sealing
commit, before any ADR 0044 repair — was given **eighteen** full-suite runs on the same machine:
**seventeen green (1408 passed), one RED with a single failure.** An intermittent full-suite
failure therefore **predates the repairs**, at a rate (1/18) of the same order as the one observed
after them (1/6, and 0/6 in an earlier set at the same HEAD — pooled, 1/12). That is evidence about timing and
rate, not about identity: the harness captured only each run's summary line, so the failing test in
that control run is not named here and is **not asserted to be this one**. What the control
establishes is the claim that matters — the ADR 0044 repairs did not introduce intermittent
full-suite failure into a suite that was previously deterministic, because it was not previously
deterministic.

**Not claimed:** that this is the same cause as Sightings A, B or C; that the pre-repair control's
failure is the same test; or that any of it is resolved.

## Status

accepted — 2026-08-02 (the pre-seal flake hunt; reproduction and root cause, fix referred)

**Sighting C appended 2026-08-06** (task A2 PHASE 1, the v0.6 reseal): task A1's seventy-error run
was watched and **not reproduced**; a distinct wall-clock anomaly — green, on an idle machine, at
about seventy times the surrounding runs — was observed **once** and did not reproduce on the next
run. Both causes are **undetermined**, they are not claimed to be one cause, and A1's
resource-contention explanation is withdrawn as falsified. Nothing above this line changed.

**Partially superseded by [0039](0039-one-clock-per-cell-the-campaign-adopts-the-cells-clock.md) —
on the run-001 root-cause attribution only.** The wall-clock straddle recorded here is **not** the
cause of `test_appended_widening_verifies_but_does_not_widen`; that module reads no wall clock, so
its cause is **undetermined**. 0039 also relocates run 000's straddle from Δ to the OAuth access
token's 300 s lifetime, without disturbing the straddle diagnosis itself. **The reproduction
condition and its rates (0/6, 0/4, 2/3), both named failures, the evidence-based exclusion of the
shared `b3_setup` lead, and the direction-of-failure finding all stand unchanged.**

## Consequences

- The repeat-runner (`tools/repeat_runner.py`) is a committed artifact. It captures **every run's
  complete output to its own file**, so an unnamed failure cannot recur.
- **This defect is pre-seal blocking.** The straddle is direction-agnostic and would corrupt a
  confirmatory campaign silently.
- The fix, and its failing world, belong to the next session.
