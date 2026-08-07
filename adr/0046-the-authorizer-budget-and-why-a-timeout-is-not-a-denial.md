# 0046 — The authorizer's evaluation budget, and why a timeout is not a denial

## Context

**ADR 0038's Sighting D has a root cause, and it is worse than a flaky test.**

`biscuit-python`'s authorizer carries default evaluation limits. Read off the pinned library
(`biscuit-python==0.4.0`) rather than assumed:

```
max_facts = 1000        max_iterations = 100        max_time = 0:00:00.001000
```

`max_time` is **one millisecond of WALL CLOCK**. Exceeding any of the three raises
`AuthorizationError("Reached Datalog execution limits")` — **the same exception class a genuine
policy denial raises**. Both authorizer call sites caught that class and returned a refusal:

- `src/harness/authorizer/allowed.py` — `except AuthorizationError: return False, str(exc)`
- `src/sut/capability/authority.py` — `except AuthorizationError: return False`

So an evaluation that ran out of time was recorded as *the token does not authorize this element*,
indistinguishable from a refusal on the merits. The harness module's own docstring said *"Any other
exception propagates — this never converts an error into a verdict"*; that was true of every error
class except the one that actually fires.

### Why this is a measurement defect, not a nuisance

`§A.0.1`'s `C_i = Allowed(P_i; Γ, κ, Ω)` is computed by **running the authorizer once per candidate
element of `Ω`** — that is ADR 0016's specification and the reason G-2 exists. `Ω` has seven
elements, and the campaign evaluates every hop of every arm of every scenario. Each of those runs
carried a one-millisecond wall-clock budget.

A breach therefore **silently drops an element from an authority set**. Authorization-scope
amplification — the quantity this study exists to measure — is a function of exactly those sets, so
a busy machine could shrink one and nothing downstream would know. The direction is **against this
work's hypothesis**: a capability arm computed with a missing element looks *more* restrictive than
it is, which is the same direction as ADR 0038's Sighting B and both of its reproductions. The
project's §6.1 pattern (*every dormant defect failed toward the hypothesis*) still does not hold.

### How it was found, and what was refuted on the way

Sighting D was a ~1-in-12 full-suite failure of
`test_frozen_gamma_denies_third_party_widening`, in its **positive arm** — a granted element
failing to authorize. Three hypotheses were tested and two were refuted:

| hypothesis | test | result |
|---|---|---|
| the random `KeyPair()` makes it probabilistic | 300 direct iterations, fresh keys | **refuted**, 0/300 |
| CPU contention alone | 16 busy-loop workers, file alone | **refuted**, 0/6 |
| randomised test ORDER (`pytest-randomly`) | checked whether the plugin is installed | **refuted** — it is not installed; order is deterministic |
| an in-process limits breach under full-suite load | read the library's defaults; forced `max_time=0` | **confirmed** — raises `AuthorizationError("Reached Datalog execution limits")`, which the callers returned as a deny |

The assertion that failed discarded the evidence string `authorize_candidate` returns, so the
refusal's *reason* was thrown away at the point it would have been diagnostic. That is why it took
several reproduction runs; the assertion now carries the reason.

## Decision

`[DESIGN]` **Set the budget explicitly, and never convert a limits breach into a verdict.**

1. **`AUTHORIZER_MAX_TIME = 1 second`**, set on the builder at both call sites rather than
   inherited. That is ~1000× the observed per-run cost, so a breach means a runaway evaluation
   rather than a garbage-collection pause. It stays **finite**: an unbounded authorizer could hang
   the campaign instead of failing it.
2. **A limits breach raises `AuthorizerExhausted`** — a new exception on each side — and propagates.
   The caller fails closed by *crashing*, not by quietly denying. An abort is a Part H abort:
   discard the partial run, record it, re-run the same sealed artifacts. That is a far better
   outcome than a table with a silently missing element.
3. **`max_facts` and `max_iterations` keep the library's defaults.** They are structural — bounded
   by `Ω` and `Γ`, which are frozen — and do not depend on how busy the machine is. Only the
   wall-clock limit had the property that made it dangerous.
4. **Both sides carry the same value, and a test asserts they agree.** The two implementations stay
   independent (D13/D21 — the oracle must not import the SUT's arithmetic), but a *different* budget
   would make one side's authority set depend on a limit the other does not share, which is an
   apparatus difference that would be reported as a mechanism difference.

**This is not a frozen-parameters row.** It is an apparatus constant that bounds a runaway, in the
same category as ADR 0045's token lifetime: no hypothesis reads it, no predicate reads it, and no
verdict can depend on it — because the entire point of the change is that a verdict may no longer
depend on it.

## Status

proposed — 2026-08-07. Numbered 0046 by the Commander, following 0045. Part of the v0.7 candidate.

## Consequences

- **ADR 0038's Sighting D moves from OPEN/cause-undetermined to ROOT CAUSE IDENTIFIED**, and
  `DEVIATIONS.md` D-004 is updated in place rather than closed silently. The sighting record is
  kept: two of the four hypotheses it names were refuted by experiment, and that is worth more to
  the next reader than a tidy entry.
- **A previously invisible failure mode is now loud.** Any limits breach during the campaign aborts
  it with the element named. This trades a silent wrong number for a visible stop, which is the
  trade this project makes everywhere else.
- **No result is affected, because no result exists.** Part H step 7 has not run. Had this been
  found after the campaign, the affected families could not have been repaired — Part H forbids
  result-driven changes after the seal — and the honest outcome would have been to report the
  amplification measurements as unreliable.
- **The gates were adjudicated under the old behaviour.** No gate is invalidated by this: a gate
  that passed did so with the authorizer answering correctly, and the failure mode only ever
  *removed* authority. But G-2's adjudication should be re-run on the v0.7 candidate along with the
  other platform-bound gates, which the reseal does anyway.
- **A library-version bump can reintroduce it.** A test pins that the *default* is a wall-clock
  millisecond, so if `biscuit-python` changes that, the change is visible rather than silent.
