# G-14 — RETROSPECTIVE record: compiled 2026-08-06 at commit `ca360ae` from a re-run of `spike.py`, NOT the contemporaneous adjudication — G-14's adjudication stands on the `smoke/README.md` board row and on `smoke/g14/spike.py`, which landed at `dfbef6d`.

Every other gate's adjudication left a `REPORT.md` beside its spike; G-14's did not, and the
board row's link to one dangled from the day the gate passed. This file exists to close that
asymmetry **without disguising what it is**: it was written days after the adjudication
(EXP5 STEP 11–12, spike landed at `dfbef6d`), from a re-run, by the Commander's instruction
that a retrospective record must say so in its first line. Nothing here re-adjudicates
anything and no verdict moves; the adjudicative record remains the board row plus the spike
source, exactly as the pre-registration recorded before this file existed.

## The re-run

- Command: `uv run python smoke/g14/spike.py`
- Commit: `ca360ae` (repository HEAD at the time of compilation)
- Date: 2026-08-06
- Platform: Windows 11 Pro 10.0.26200 (the row 9 machine; G-14 itself is
  platform-independent — no effect ledger, nothing timed, clock injected per ADR 0027)
- Exit code: **0** — all eight mandatory checks PASS, all three claims hold

### Actual output

```
GATE G-14 -- the DPoP/INV attribution (EXP5 STEP 11-12)
==============================================================================
G-14.C0 [MANDATORY] PASS -- the two arms hold the SAME cache OBJECT (`is`): True; one class (JtiCache): True; and one shared state, so an id consumed once is a duplicate on the next look: True. Two caches that merely behaved alike would make every difference below an artefact of which arm got which
G-14.C1 [MANDATORY] PASS -- first use: B2-DPoP (True, 'b2_admitted'), B3 (True, 'b3_admitted'); bit-identical replay INSIDE Delta: B2-DPoP (False, 'b2dpop_replay_duplicate'), B3 (False, 'b3_replay_duplicate'). Both admit once and block the replay -- identically, and NEITHER DOES BETTER THAN THE OTHER on this cell. The reason codes differ because the arms name their own conjuncts; the OUTCOME is what the claim is about
G-14.C1.W1 [MANDATORY] PASS -- with NO cache attached, the same bit-identical replay is ADMITTED: B2-DPoP (True, 'b2_admitted'), B3 (True, 'b3_admitted'). So the blocks above are the SHARED CACHE's doing and not another conjunct's
G-14.C2 [MANDATORY] PASS -- a FIRST-USE request whose tool/arguments differ from what was signed: B2-DPoP WITH the shared cache -> (True, 'b2_admitted') (admitted), B3 -> (False, 'b3_invocation_binding') (blocked at invocation binding). The cache cannot catch it because the id is fresh -- this is a first use, not a replay -- and DPoP binds method and URI, not the body. THIS IS THE CELL WHERE INVOCATION BINDING EARNS ITS PLACE
G-14.C2.W1 [MANDATORY] PASS -- the DPoP proof's claims are ['ath', 'htm', 'htu', 'iat', 'jti']: it names `htm` and `htu` (method and URI) and NONE of ['arguments', 'body', 'canonical_request_digest', 'digest', 'tool']. The limitation is readable in the artefact, not inferred from the outcome
G-14.C3 [MANDATORY] PASS -- a bare bearer arm was GIVEN the shared cache and the captured token was replayed: (True, 'b2_admitted') -- ADMITTED. The cache holds 0 entries afterwards, because the arm has no authenticated request id to consume: there is nothing to put in it. 'Not built' and 'impossible' look identical in a results table and mean opposite things; this is the second
G-14.C3.W1 [MANDATORY] PASS -- the arms that can carry it name different mechanisms {'B2-exchange-task-DPoP': 'dpop', 'B3': 'inv'}, so one shared cache cannot let one arm deny the other's request -- which is what the `(mechanism_tag, jti)` namespace is for. A bare bearer appears in neither, because it authenticates no id
G-14.C0.W1 [MANDATORY] PASS -- counterfactual: give the arms two equivalent caches and the identity check fails (True). They would still both 'block replay', which is exactly why behavioural equivalence is not the criterion

GATE G-14: all mandatory checks passed -- all THREE claims hold
```

The spike's closing statements (the attribution and its scope) are printed by the spike
itself and are not duplicated here; they are quoted in full in the board row.

## What this file is, and is not

- It **is** evidence that the spike still passes, unmodified, at `ca360ae` on this platform.
- It is **not** the adjudication (that happened at EXP5 STEP 12 and is recorded on the board),
  **not** a re-adjudication, and **not** contemporaneous with the gate's PASS. A retrospective
  record dressed as a contemporaneous one would be worse than the asymmetry it repairs; hence
  the first line.
