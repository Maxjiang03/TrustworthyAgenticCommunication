# 000Y — Three pre-seal amendments: the Part H list, row 7's rationale, and the `unscorable` definition

## Context

`PRE_REGISTRATION.md` (Part H step 2, authored at `5264f1b`, committed at `ca360ae`) reported
five gaps it was forbidden to repair — places where the repository did not already decide
something, listed for the Commander rather than filled in. The Commander closed them in one
pre-seal pass. Three of the closures amend documents this project otherwise treats as frozen
prose — the design document and a frozen row's rationale — so they belong in one decision
record a reader finds once. (The other two closures are not amendments: G-14's retrospective
`smoke/g14/REPORT.md` states its own provenance in its first line, and the RQ4 ADR received
its number, 0041, by rename.)

## Decision

`[DESIGN]` Three amendments, each the Commander's decision, none touching a frozen value:

1. **Part H's content list names H4a/H4b, not "H1–H9/H4a-b"** (§J.3 item 10). The design
   document defines no hypotheses numbered H1–H9 — the sole occurrence of the string in the
   whole document was the list item itself, and Part D.1's falsifiable content is exactly H4a
   and H4b. The decision is to **amend the list, not to invent hypotheses**: nine numbered
   hypotheses conjured days before a seal would be nine things to maintain and defend that no
   research question asked for. H4a and H4b themselves are untouched, and nothing else in
   Part H changes.

2. **Row 7's rationale loses its unanchored corroborating clause** (`docs/frozen_parameters.md`
   row 7). The clause "a representative tier-2 support agent is reported near 2.7 s median"
   could not be sourced to a dated, retrievable publication (the 2026-08-06 search found only
   an arXiv sales-copilot 2.6 s median — a different quantity from a different domain), and an
   unanchored corroborating clause inside a frozen row's rationale is a claim a reader will
   take as sourced. It is **deleted**. **The values do not move**: `T_full_ms = 2000` and
   `T_ttft_ms = 250` are byte-identical before and after, exactly as row 7's own rule requires
   — a figure that cannot be sourced never causes a value to change, and this edit is not the
   first exception to that rule. The row's sourcing obligation is discharged in the same edit:
   both denominators are anchored to Artificial Analysis (methodology and per-model pages,
   both retrieved 2026-08-06), recorded in the row's Value column, with the seal-time snapshot
   still owed at step 3. The "specialised silicon near 0.18 s" clause is **left in place as
   not-re-verified rather than deleted**: not-re-verified (the 2026-08-06 retrieval did not
   read a current per-provider figure back) is a different state from unsourceable (a search
   that found no dated, retrievable publication at all), and only the second forfeits a
   clause's place in a frozen rationale. The denominator's anchor rests on the mainstream-tier
   figures read back at retrieval, not on either clause.

3. **The design document now defines `unscorable`** (Part I, beside the no-/partial-/
   multi-effect handling). The campaign has routed unjudgeable cells to an `unscorable` list
   since ADRs 0038/0039/0040 built the machinery, but the design document never used the
   word — the pre-registration reported that as a gap and proposed wording, and this
   amendment adds exactly that wording: three recorded causes (`RunnerError`; the wall-clock
   straddle, one clock per cell; a credential validity window not covering the judging
   instant), and the statement that an unscorable cell is not a block, not a `false_block`,
   and not a result at all, exactly as an NA cell is not, with every unscorable cell reported
   with its cause. This is the same-commit design-document update `PROJECT_RULES.md` requires
   of an ADR that changes the design; the machinery itself is unchanged and was built under
   its own ADRs.

## Status

proposed — 2026-08-06 (placeholder letter; the number is the Commander's to assign, as ever)

## Consequences

- The five gaps the pre-registration reported are all closed, and `PRE_REGISTRATION.md` is
  updated in the same commit to record each closure in place of the gap: the list amendment
  (not invented hypotheses), the deletion with values untouched, the definition now present,
  the retrospective G-14 record, and the 0041 citation replacing the `000X` placeholder.
- **No frozen value moved.** The only frozen-parameters edits are row 7's rationale prose and
  its sourcing record; `src/harness/frozen_parameters.py` reads the same `name = value`
  tokens before and after, and `tests/test_pre_registration.py` re-verifies every scalar
  through that reader.
- The §E.4 matrix, H4a/H4b, and every other part of the design document are untouched;
  `tests/test_pre_registration.py`'s cell-for-cell §E.4 comparison still passes.
- Still owed at Part H step 3: the seal-time snapshot of the two Artificial Analysis pages,
  and the ADR 0028 `wrong_principal` re-scan over the exact specification set the manifest
  hashes.
