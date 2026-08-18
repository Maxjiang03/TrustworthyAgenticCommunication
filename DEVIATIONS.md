# DEVIATIONS — departures from the pre-registration, dated, with reasons

**Design §J.4 item 13.** Every departure from `docs/PRE_REGISTRATION.md`, every abort and re-run,
and every infrastructure fix with its commit hash, is recorded here as it happens. Reviewers trust
a study that reports its deviations far more than one that appears flawless — and a deviation
recorded after the results are visible is a confession, not a record.

**This file is manifest-EXCLUDED, deliberately.** It must be appendable after the seal without
forcing a reseal; that is what it is for. Its entries cite the sealed artifacts they depart from.

**What belongs here.** A departure from a pre-registered predicate, threshold, predicate scope,
analysis rule or sampling plan; an abort of a campaign run and what was discarded; an
infrastructure fix applied between the seal and a re-run, with the fix commit's hash; any
environment drift observed on the row 9 platform. **What does not:** ordinary development before
the seal, which the git history and the ADR log already record.

**Status: THE CONFIRMATORY CAMPAIGN RAN ONCE on 2026-08-07, at the v0.7 sealing commit
`17e11c9`.** Part H step 7's "once" is **spent**. It completed in a single execution: **no abort,
no re-run, and no post-seal infrastructure fix.** Every one of the 10 unscorable cells is a cell
§E.4 marks `NA` in the sealed record — **none** was unscorable for a wall-clock straddle, an
exhausted authorizer, or a runner error. The raw trace is archived at
`results/raw/campaign-confirmatory.json` (both its committed-blob and on-disk SHA-256 recorded in
D-005), admitted to version control by a deliberate `.gitignore` change as §J.4 item 14 requires.

The entries below D-005 are **pre-campaign**, and are kept because each changes what a reader
should expect from the sealed record.

---

## D-014 — Pre-commitment: reporting the RQ4 descriptive layer (span descriptives and arm-pair deltas)

**Status:** OPEN — written BEFORE the analysis is run.
**Date:** 2026-08-18
**Authority:** Commander task 2026-08-18 ("RQ4 overhead analysis and figures"), continued after the
Phase 0 STOP; D3(i); frozen_parameters row 1 (sampling clause); ADR 0041; ADR 0047; ADR 0048
third named exception; D-006; D-009.

**Context.** D-009 decided the row-1 lightweight claim, twice, in agreement, and closed with "No
further run"; it covered `lightweight_claim` and nothing else. The RQ4 layer of the sealed
`analysis/latency.py` — `span_descriptives` (`Descriptives` for every arm × phase × span × series)
and `arm_pair_delta` (median difference against a control arm with a bootstrap interval, labelled
by the §E.5 bit derivation) — has never been executed over `results/raw/latency-pilot.json` with
its output committed. Every RQ4 latency number in any draft chapter is therefore, today,
UNVERIFIED: the Phase 0 investigation of 2026-08-18 found no committed artefact under `results/`
producing any of them (`0.2284`, `31.0037`, `39.7833`, `22.7360`, the cold-start percentages, or
the forty-five hand-typed pgfplots medians in `drafts/3_8_latency.tex`), while `6.4432` was found
to be run 2's treatment median of the MEASURED SEGMENT (presentation + boundary_verification)
mislabelled in prose as boundary verification alone. This entry commits, before the layer is run,
to how its output will be reported.

**Disclosure that precedes the pre-commitment.** During Phase 0, to answer the Commander's B2
(whether the presentation span is effectively zero), the sealed `span_descriptives` was executed
uncommitted and its `presentation`-span rows ONLY were printed to the terminal — all nine arms,
both phases, both series. No other span's descriptives and no arm-pair delta was viewed. That
readout is recorded here so no reader has to take it on trust that nothing below was shaped by it;
the reporting rule below leaves nothing to shape, because it reports everything the layer emits.

**Pre-commitment.**

1. **Everything the sealed layer emits is committed verbatim, and nothing else is computed.** The
   output artefact carries every `SpanReport` from `span_descriptives` — every arm, both phases,
   all five spans, both series (`benign`, `refusal_path`) — and every `ArmPairDelta` from
   `arm_pair_delta` for every arm against control `B0`, for every one of the five spans, for both
   phases. No row is selected, dropped, binned or reordered by the composition root; no median,
   quantile, delta or interval is computed outside `analysis/latency.py`.
2. **Warm-up is discarded by the sealed `discard_warmup`, with `per_batch` READ from the plan
   block** (`warmup_per_batch: 5`), before `arm_pair_delta` is called — because `arm_pair_delta`,
   like `lightweight_claim`, does not discard it itself (`analysis/latency.py:802-857` has no such
   call), and run 1 of D-009 is the record of what omitting this looks like. `span_descriptives`
   applies the same sealed function internally (`:503`); the composition root passes it the same
   `per_batch`. Every kept `n` is expected to equal the plan block's
   `kept_after_warmup_per_configuration` (210) and any other value is reported, not fixed.
3. **Refusals are reported as refusals.** `arm_pair_delta` refuses any pair involving `B1`
   (§E.5 carries no bit for its static shared secret, ADR 0035; `analysis/latency.py:713-719`).
   The `B1 vs B0` delta is therefore recorded, for every span and phase, as REFUSED with the
   sealed layer's own message — not omitted, not approximated from descriptives, not computed
   another way.
4. **Seed, resamples and confidence are the plan block's** (`bootstrap_seed`,
   `bootstrap_resamples`) and the sealed defaults; identical for every delta; not re-seeded, not
   varied. Corpus, phases, spans, series and the refusal-path constant are the sealed layer's own.
5. **The layer is run ONCE.** If it is re-run for any reason, every run and its reason is recorded
   in this entry, the first run's artefact is neither overwritten nor edited, and the runner
   refuses to overwrite an existing output.
6. **No decision, no margin, no verdict.** `arm_pair_delta` carries no verdict and no margin by
   construction (its docstring, `analysis/latency.py:754-761`); none is added, and no delta is
   compared to the 20 ms row-1 margin anywhere — in the artefact, in a figure, or in prose.
7. **Every delta is reported under the sealed label** (`mechanism-increment` or
   `composite-delta`), with `differing_bits`, `mechanism` and `unmodelled` carried verbatim. Every
   delta against `B0` is expected to be a `composite-delta` with `mechanism = None`; a
   configuration difference is what it is called, never a mechanism cost (ADR 0041).
8. **The chapter's numbers are not reconciled by this run.** After the artefact is committed the
   draft chapter's figures may be COMPARED to it, and the comparison reported; agreement does not
   retroactively verify the chapter's provenance, and disagreement is reported as the finding it
   is. Nothing in the run is adjusted to meet a number already in prose.

**Presentation rules fixed before the numbers are seen (Commander ruling R4, 2026-08-18).**
- C1: no figure plots or states an absolute end-to-end latency for any protected arm; every span
  is shown as the sealed delta against `B0`. The one absolute end-to-end value stated is `B0`'s own
  warm benign median, as the fixed-testbed-overhead disclosure CLAIMS_LEDGER A7 requires, and it is
  read from this artefact, never carried from prose.
- FIG-L1 reads the COMMITTED row-1 decision (run 2's descriptives, run 1's verdict per D-009
  clause 2 — both `stands`); no third decision run.
- FIG-L2 shows, per arm and span, the delta point and the sealed interval; the sealed layer emits
  no p95 delta, so no p95 tick is drawn on a delta axis and no p95 difference is computed; the
  treatment arm's IQR width is printed as the number the sealed `Descriptives` gives.
- Axis rule: `log10` if and only if every plotted value — every point and every interval bound —
  is strictly positive; otherwise `symlog`. Which branch fired is printed by the script.
- FIG-L3 shows the refusal-path series in the only form the sealed layer emits for it —
  `span_descriptives` under `series = refusal_path` — because `arm_pair_delta` builds from the
  benign series alone (`analysis/latency.py:836-841`) and emits no refusal-path delta. Its
  end-to-end panel is not drawn (C1); the omission is stated on the figure.

**Disclosures that travel with every number this run produces, regardless of what it shows.**
PILOT corpus (`fixtures/pilot/golden_thread`), not confirmatory (D-006, ADR 0047). No CPU affinity
pinning on this pass (the only pinned measurement in the repository is the G-3 gate). In-process
harness on one machine (ADR 0034): no network hop is implied by any figure. The G-3 5 ms threshold
governs an isolated pinned microbenchmark and appears on no artefact here. ADR 0041 bars any
per-mechanism cost for the online exchange or across the exchange partition; every delta here is a
configuration difference. Cold and warm are never pooled; the refusal path is never pooled with
the benign path.

**On exit.** When the run completes, this entry is updated in the same commit as the committed
output with the run commit hash, the artefact path, the count of reports and deltas emitted, the
count of refusals, and whether every kept `n` equalled 210. The pre-commitment text above is not
edited.

---

## D-013 — "no carrier at all" was wrong: a nine-arm test carries two of the three unpopulated F3 rows

**Status:** CLOSED on the day it opened.
**Date:** 2026-08-17.
**Authority:** found by an adversarial verification pass over the F3 carrier audit.

**The error.** Throughout the F3 extension work I reported that
`F3 expired token` has **no carrier at all**. That statement reached
`DEVIATIONS.md` D-011 clause 5 ("Carrier: **none**, stated plainly"),
`drafts/F3_EXTENSION_PLAN.md`, and the recommendation that closed the extension.

It is false. `tests/test_f3_matrix.py` — 629 lines, 48 tests, green in the suite
— measures **both** `F3 expired token` and `F3 dpop-captured-proof-replay`
**cell by cell across all nine arms**, against the §E.4 predictions, with
`B-cap` carrying the ADR 0031 correction. Its own first line says so:
*"§E.4's two buildable F3 rows, over all nine arms (EXP4 STEP 6-7)."* And it
holds the same discipline the campaign does: *"A cell that disagrees with §E.4
is a finding to report, not a number to adjust — and neither is the prediction
to be edited to match the cell."*

**How the error was made.** I searched for a **gate**. No gate names
`expired token`, and that finding is correct — `smoke/g1..g15` was searched
exhaustively and the nearest hit is a G-4 RFC 8693 conformance row with no
criterion id and no per-arm F3 cells. I then reported the gate-scoped negative
as an unscoped one. **"No gate covers it" and "no carrier at all" are different
claims, and only the first was established.**

This is the same failure the scoped-negative rule exists to prevent (D-010), and
this time the rule did not catch it because I stated the scope of the *search*
and not the scope of the *conclusion*.

**Corrected carrier map for F3, five subcases.**

| subcase | evidence | arms covered |
|---|---|---|
| `dpop-stolen-AT-key-substitution` | confirmatory campaign cell | 9 |
| `audience mismatch` | confirmatory campaign cell | 9 |
| `expired token` | `tests/test_f3_matrix.py`, per-cell vs §E.4 | **9** |
| `dpop-captured-proof-replay` | `tests/test_f3_matrix.py` **and** gate G-14 C1 | **9** (test); 2 (gate) |
| `dpop-first-use-body-mutation` | gate G-14 C2 only | 2 (`B2-DPoP`, `B3`) |

So **all five subcases have evidence**, four of them across all nine arms, at
**three distinct evidence classes** — campaign cell, gate adjudication, and
suite test. No subcase is uncarried.

**What does NOT change.** F3's *campaign* coverage remains **2 of 5**, and that
fraction still travels with every F3 number reported from the campaign
(pre-registered §4). A suite test is not a campaign cell and is not a gate
adjudication: it exercises the mechanism on an instance built for the test,
inside the same process, and it is not part of the 143-cell record or the 80/0
agreement. Nothing about the primary result moves.

**What does change.** The decision to close the F3 extension was argued partly
on `expired token` being the one subcase with no carrier at all. That argument
is void. The other reasons stand unaffected — its §E.4 row is byte-identical to
the already-populated `audience mismatch` row, and building it would have
touched the AS provisioning and the campaign driver — so the outcome is
unchanged, but one of its stated reasons must not be repeated.

**Correction discipline.** D-011 is closed and its pre-commitment text is not
edited. This entry supersedes its clause 5 on the single point of
`expired token`'s carrier, and is the text to cite.

---

## D-012 — `check_run_mode` does not contemplate a third corpus root, and the gap is a labelling hazard

**Status:** OPEN — recorded before the run it concerns.
**Date:** 2026-08-16.
**Authority:** Commander ruling of 2026-08-16 (PATH 1, item P1b).

**The gap.** `check_run_mode` (`src/harness/campaign.py:232-267`) was written to
refuse a confirmatory run carrying a pilot-provisional artifact, by three limbs:
a fixture under `fixtures/pilot/`, an §E.6 ablation variant, and a policy
document still marked `PILOT-PROVISIONAL`. Its author was separating **two**
corpora. Nothing in it contemplates a third, and the F3 extension corpus passes
the pilot-path limb simply by not being the pilot corpus.

**Why it is not a hole in coverage.** Two of the three limbs are
corpus-independent and fire on the extension unchanged — the ablation check reads
`arms` (`:250-259`) and the `PILOT-PROVISIONAL` check reads the frozen policy
document (`:263-267`). The limb that does not fire protects a property that is
not at risk here.

**The hazard the gap does create.** `run_mode` is restricted to
`("pilot", "confirmatory")` (`:241-242`), so the extension must run as
`confirmatory`. That string is stamped into the output record
(`campaign_driver.py:271`) and selects the ledger directory
(`campaign_driver.py:206`). Left alone, the extension artefact would **declare
itself `run_mode: "confirmatory"`** and its ledger rows would land **in the
primary campaign's ledger directory** — the exact confusion the evidence-class
separation exists to prevent, arriving by default rather than by choice.

**Recorded because of the pattern, not the severity.** A check that looks dormant
becoming load-bearing, and failing toward the hypothesis, is this project's
recurring failure. This is an instance caught before it fired rather than after.

**Mitigations, both at the unsealed composition root, neither touching the seal.**

1. A distinct ledger directory (`results/_ledger/f3-extension/`) is passed
   explicitly, so no extension ledger row enters the primary campaign's directory.
2. `evidence_class: "extension"` and the seal version are stamped into the output
   alongside the inherited `run_mode`, so `run_mode: "confirmatory"` can never be
   read alone.

**Not fixed in the sealed code, and why.** Widening `check_run_mode` to know
about a third mode is a change to a covered file whose current behaviour is
correct for everything it was written for. The gap is in what it contemplates,
not in what it does. It is disclosed here and handled at the caller.

---

## D-011 — Pre-commitment: the F3 `expired_token` extension

**Status:** CLOSED UNBUILT, 2026-08-16. No fixture, no code and no run ever
followed it: the extension was closed when the faithful construction of its last
candidate was found to need a dispatch-argument seam the harness does not have,
and the available construction required the terminal holder key that H4a's
adversary definition excludes. The entry stands as the record that these
constraints were fixed **before** the question was settled rather than after.
Nothing it constrained was executed, so nothing needs unwinding.

**Status when written:** OPEN — committed BEFORE any fixture, any code, and any run.
**Date:** 2026-08-16.
**Authority:** Commander ruling of 2026-08-16 (A + C; B declined for this
dissertation).

**Precedent this follows, verified from git rather than recalled.** D-009's
pre-commitment was committed at `6da1570`, 2026-08-15 22:43:49, containing
`DEVIATIONS.md` alone, 48 insertions, no verdict and no number — the three
occurrences of `stands`/`retracted` in it are the pre-commitment naming both
outcomes symmetrically. The runner did not exist until `05ff409` at 22:52:20,
and the verdict landed at `2284837`, 22:55:36. The commitment therefore could not
have been shaped by anything the code or the data revealed. This entry is
committed on the same terms.

**Scope: ONE subcase.** The ruling approved two. Pre-build verification
established that `first_use_body_mutation` cannot be built as a credential fault
(see D-010), so it stays with gate G-14 C2, alongside
`dpop-captured-proof-replay` with G-14 C1. `expired_token` was the only one of
the three with no carrier at all, and it is the one that is buildable.

**Pre-commitment.**

1. The extension is a **separate, once-only campaign**.
   `results/raw/campaign-confirmatory.json` is not re-run, not overwritten and
   not superseded. Its cells and its agreement remain the primary result, and the
   extension is **never summed with it** in any artefact.
2. The `F3 expired token` §E.4 row — `A A B B B B B B B` — is **frozen** and is
   not edited. An instance is added; the prediction is not. If the measured
   outcome contradicts the frozen prediction, that disagreement is **reported as
   the finding it is**, and the matrix is not amended to match it.
3. The extension row is reported at a **distinct evidence class** in every
   artefact and in prose, and never inside a primary-campaign count. The fact
   that it was **instantiated after the primary results were known** travels with
   every extension number.
4. Whatever the extension measures is reported as returned, including a result
   that weakens this study's own position.
5. The subcases NOT built are stated in the form the ruling fixes, and the two
   kinds of gap are **never written as one** (Commander ruling, 2026-08-16):
   - `dpop-captured-proof-replay` — instantiation was **evaluated and judged
     INFEASIBLE**, on evidence, **after the primary results were known**: it
     requires a single cell to make two boundary decisions, and this study's
     measurement unit is one cell, one decision. Carrier: gate G-14 C1, and
     `B3⁺`'s dependence on it is restated in the same place.
   - `expired_token` — instantiation was **evaluated and judged NOT WORTH ITS
     COST**, also after the primary results were known. **This is not
     infeasibility and is not written as such.** Its §E.4 row is byte-identical
     across all nine arms to the already-populated `F3 audience mismatch` row
     (`docs/PRE_REGISTRATION.md:210-211`), so it is a second instance of one
     predicted class rather than a new class; and building it would have
     required modifying the AS provisioning and the campaign driver, the code
     that produced the primary campaign. Carrier: **none**, stated plainly.
   Neither is written so it reads as a pre-registration decision.
6. F3 coverage becomes **3 of 5** subcases **if and only if** an extension
   instance is actually built and run, and that fraction then replaces 2/5 on
   F3-bearing artefacts that include the extension. If none is built it stays
   2/5. The **primary campaign's own F3 coverage remains 2 of 5 permanently** and
   is never restated as 3 of 5: an extension instance is not one of its cells.
7. **The bias-guard status of the extension instance is disclosed, whichever
   corpus placement is chosen.** The structural-matching test
   (`tests/test_confirmatory_corpus.py`) pairs the pilot and confirmatory corpora
   only. An extension instance placed in a third corpus root is therefore outside
   that guard: no matched pilot sibling, no identical-subcase-set assertion, no
   paired `relation`/`is_benign` check. The guard exists because instances
   authored after watching a corpus behave are where an author would, without
   meaning to, pick easier or harder cases — and this instance is authored after
   the **primary results** are known, which is a stronger version of exactly that
   hazard. Its absence is stated wherever the extension result is stated.

**On exit.** When the extension runs, this entry is updated in the same commit as
the committed output with the outcome as returned, the commit hash of the run,
and the artefact path. The pre-commitment text above is not edited.

---

## D-010 — A detailed, sourced, wrong report would have been executed; the scoped-negative rule is what stopped it

**Status:** CLOSED on the day it opened.
**Date:** 2026-08-16.
**Authority:** Commander ruling of 2026-08-16.

**What happened.** The F3 extension feasibility report concluded that all three
unpopulated F3 subcases were impossible as campaign cells, and recommended
extending a gate instead. Two of those three findings were wrong.

`src/harness/credential_faults.py` — *"The attacker between the arm and the
resource server"* — is exactly the signed-versus-presented seam the report said
did not exist. Its `apply_to_presentation` corrupts what the arm staged, runs at
`runner.py:805`, and is already scenario-selectable through a `credential_fault`
field read at `campaign.py:901`. Five faults already use it. Separately, the
report claimed `clock_refusal` would make an expired-token fixture unscorable;
that guard inspects the **provisioning** setup dict, while a restaged token lives
on `arm._staged`. Two different objects.

**The failure mode, which is the point of this entry.** A report can be
detailed, sourced to file:line, internally consistent, and wrong — and in that
combination it does not look like a report that needs checking. It would have
been executed. What stopped it was not review and not a second opinion: it was
the rule, adopted after the CLAIMS_LEDGER incident, that a negative conclusion
must state the scope over which it was established. That rule looked like
formalism when it was adopted.

It is now the only thing that has worked, and it worked **twice**. The same
declared residual that caught the error above also caught a second one: the
corrected report then claimed `first_use_body_mutation` was buildable as a
credential fault, and the pre-build verification the Commander demanded
(Q8/Q9) found that a credential fault can move only the signed side of the
boundary, never the presented side — so that construction would have produced a
strong arm blocking a request the independent oracle certifies as untampered.

**Standing rule, restated because it earned it.** A "does not exist" or "cannot
be done" conclusion must name the scope over which it was established. A negative
without a stated scope is not a finding; it is an assumption wearing one.

**Nothing was built on either wrong finding, so nothing needs unwinding.**

---

## D-009 — Pre-commitment: reporting the row-1 lightweight claim verdict

**Status:** OPEN — written BEFORE the analysis is run.
**Date:** 2026-08-15
**Authority:** Commander ruling D3(i); frozen_parameters row 1; ADR 0047; D-006.

**Context.** `results/raw/latency-pilot.json` has existed since the RQ4 pass but
`analysis/latency.py` has never been executed over it. No latency analysis,
table, figure, or verdict has been committed. Running the sealed
`lightweight_claim` function therefore decides the pre-registered row-1
equivalence claim for the first time, and the decision is final.

**Pre-commitment.** The verdict returned by the sealed `Decision` object will be
reported exactly as returned, whether it is `stands` or `retracted`. Specifically:

1. The verdict, point estimate, 95% bootstrap CI, margin, confidence level,
   resample count, and seed are reported as emitted. No value is recomputed,
   re-run, re-seeded, or re-derived outside the sealed layer.
2. The analysis is run ONCE. If it is re-run for any reason, every run and its
   reason is recorded in this entry, and the first run's verdict remains the
   reported one.
3. A `retracted` verdict is reported in the body of the results chapter with the
   same prominence as `stands`, not relegated to an appendix or a footnote.
4. No parameter, corpus, warm-up count, phase selection, span definition, or
   filter is changed after the verdict is seen. Any such change invalidates the
   run and is recorded here as a deviation.
5. The decision rule is unchanged: it turns on whether the 95% bootstrap CI
   UPPER BOUND of the median difference falls below the 20 ms margin, not on the
   point estimate.

**Disclosures that travel with the verdict regardless of its direction.**
- The data are from the PILOT corpus, not the confirmatory corpus (D-006 /
  ADR 0047). The security results are confirmatory-corpus; the two are never
  presented as one evidence base.
- Neither the campaign nor the RQ4 latency pass applied CPU affinity pinning
  (pinning exists only in `smoke/g3/spike.py`), so bimodality from core
  migration cannot be excluded.
- The G-3 gate's 5 ms threshold is out of scope here: it governs an isolated,
  pinned microbenchmark. It appears on no campaign or pilot-latency artefact.
- ADR 0041 restricts per-mechanism attribution; no per-mechanism cost is stated
  for the online exchange or across the exchange partition.

**On exit.** When the run completes, this entry is updated in the same commit as
the committed output with: the verdict as returned, the commit hash of the run,
and the output artefact path. The pre-commitment text above is not edited.

---

### CLOSED — the run, the verdict as returned, and one finding

**Run commit:** `677e7c7` (tree clean at run time). **Output artefact:**
`results/tables/results-latency-pilot.json`, admitted to version control by a
deliberate `.gitignore` exception, the mechanism that file's rule requires.
**Invocation:** `tools/run_row1_decision.py`, ADR 0048's third named exception
(sealed-decision invocation), committed before the verdict existed.

**VERDICT AS RETURNED: `stands`.**

| field | value as emitted |
|---|---|
| verdict | `stands` |
| point_estimate_ms | 6.4503 |
| 95% bootstrap CI | [6.3931, 6.473405] |
| margin_ms | 20.0 |
| confidence | 0.95 |
| resamples | 10000 |
| seed | 4815162342 |
| treatment `B3` | n=225, median 6.4518, p95 7.2079, IQR 3.2979 |
| control `B0` | n=225, median 0.0015, p95 0.00198, IQR 0.0003 |

The decision rule is the CI **upper bound** against the margin: 6.473405 < 20,
so the pre-registered "lightweight" claim stands. Nothing above is recomputed;
every value is the sealed `Decision` object's own field.

**FINDING, recorded because it was found after the verdict and clause 4 forbids
changing it now.** The run did NOT apply the pre-registered warm-up discard.
Evidence: the descriptives report `n=225` per arm, which is the plan block's
`recorded_per_configuration`, not its `kept_after_warmup_per_configuration` of
210; and `discard_warmup` is called at `analysis/latency.py:503` inside
`span_descriptives` ONLY — it appears nowhere in the row-1 chain
(`lightweight_claim` → `benign_series` → `_segment_values`), so the sealed layer
does not apply it on this path and the composition root did not either. The
collector records the intent explicitly: `warmup_discarded_by:
"analysis.latency.discard_warmup (the sealed layer decides)"`
(`src/harness/latency_collector.py:222`) with `warmup_per_batch: 5`, 3 batches.

This is an omission in the invocation, not a departure chosen after seeing the
result: the pre-registration asks for warm-up to be discarded (§E.5) and this
run did not do it. Under clause 4 no correction is applied here, and under
clause 2 any corrected re-run must be recorded in this entry with its reason,
with the FIRST run's verdict — `stands` — remaining the reported one. The
decision whether to re-run is the Commander's.

Direction of the omission, stated so it is not mistaken for a hidden
convenience: the discarded repetitions are the first of each batch, the ones
most likely to be slow, so removing them would if anything reduce the treatment
median and move the interval further below the margin. That is a structural
expectation, NOT a result, and it is not reported as one.

**Disclosures that travel with this verdict** (pre-committed above, repeated
because they are not optional): PILOT corpus, not confirmatory; no CPU affinity
pinning on this pass; the G-3 5 ms threshold is out of scope and appears on no
artefact here; ADR 0041 bars any per-mechanism cost for the exchange.

**SECOND RUN — authorised by the Commander 2026-08-15, and recorded HERE BEFORE
IT RUNS, as clause 2 requires.**

*Reason.* Run 1 did not apply the pre-registered warm-up discard. The evidence is
closed above and is not a matter of interpretation: `docs/frozen_parameters.md`
row 1 states the sampling protocol as *"warm-up discarded"*; the plan block names
the mechanism (`warmup_discarded_by: analysis.latency.discard_warmup`) and its
parameter (`warmup_per_batch: 5`); and the arithmetic closes — 3 batches × 5 = 15,
225 − 15 = 210 = `kept_after_warmup_per_configuration`. Run 1 reported n=225.
The omission is in the composition root, not in the sealed layer.

*What changes, exactly.* One call is added to `tools/run_row1_decision.py`:

    samples = discard_warmup(samples, per_batch=plan["warmup_per_batch"])

`discard_warmup` is the sealed function the plan block names. `per_batch` is READ
from the frozen plan block, not chosen here. **Nothing else changes** — not the
corpus, the margin, the seed, the resample count, the phase selection, the span
definition, the refusal-path filter, or the decision rule.

*What does not change.* Clause 2 governs: **the first run's verdict, `stands`,
remains the reported one.** Run 2 is recorded alongside it, never in place of it.
Run 1's artefact `results/tables/results-latency-pilot.json` is not overwritten,
not edited and not deleted; run 2 writes to a distinct path so both records
survive independently.

*Pre-commitment for run 2, written before its verdict is seen.* Run 2's verdict
is reported exactly as the sealed `Decision` object returns it, whether `stands`
or `retracted`. **If run 2 returns `retracted` while run 1 returned `stands`,
both are reported in the body of the results chapter with equal prominence, and
the disagreement is presented as the finding it would be** — not resolved in
favour of either, and not relegated to a footnote. No third run is taken to break
a tie.

*Run 2 result — recorded on exit.* Executed at clean-tree commit `c6d9253`,
artefact `results/tables/results-latency-pilot-run2.json`.

| | run 1 | run 2 (warm-up discarded) |
|---|---|---|
| n per arm | 225 (`recorded_per_configuration`) | **210** (`kept_after_warmup_per_configuration`) |
| verdict | `stands` | **`stands`** |
| point estimate | 6.4503 ms | 6.44175 ms |
| 95% bootstrap CI | [6.3931, 6.473405] | [6.37215, 6.46405] |
| treatment `B3` | median 6.4518, p95 7.2079, IQR 3.2979 | median 6.44325, p95 7.37380, IQR 3.30197 |
| control `B0` | median 0.0015, p95 0.00198, IQR 0.0003 | median 0.0015, p95 0.00195, IQR 0.0003 |

Margin, seed, resample count, confidence level, corpus, phase, span definition
and refusal-path exclusion are identical across both runs; the ONLY difference
is the warm-up discard. Its arithmetic closes exactly: 54 groups
(9 arms × 1 benign scenario × 2 phases × 3 batches) × 5 repetitions × 5 spans =
1350 samples dropped, 20250 − 1350 = 18900 into the decision, and 3 × (75 − 5) =
**210** per arm per phase, which is the plan block's own
`kept_after_warmup_per_configuration`.

**The two runs agree on the verdict.** The correction moved the point estimate
down by 0.0086 ms and the CI upper bound down by 0.0094 ms — the direction
recorded above as a structural expectation before run 2 was authorised, and it
is now an observed result rather than an expectation. Both intervals sit roughly
three times below the 20 ms margin, so the decision was never close to its
threshold and the omission could not have flipped it.

`p95` rose slightly on the treatment arm (7.2079 → 7.3738 ms) while the median
fell. Removing fifteen values per arm moves the p95 order statistic's index, so
this is an artifact of a smaller n rather than a finding; it bears on no
decision, and no claim is made from it.

**Clause 2 is honoured as written: the FIRST run's verdict remains the reported
one.** It is `stands`, and run 2 is `stands` also, so the reported verdict is
unaffected by which run is cited. Run 1's artefact is unmodified. Where the
results chapter needs the descriptives behind the decision, run 2's are the ones
that follow the pre-registered sampling protocol, and any artefact quoting them
must say so — a table showing n=210 beside a verdict attributed to run 1 would
be describing two different runs as one.

**No further run.** The claim is decided, twice, in agreement.


---

## D-008 — 2026-08-07 — The seventh G-3 median changed an auxiliary finding, and the v0.8 seal STOPPED on it

**Environment drift observed on the row 9 platform**, which is what this file exists to carry.

Task B2's PHASE 1 re-measured G-3 on the v0.8 sealing candidate `8ac7b21`, first and alone, before
any other gate. **The gate PASSED: median 2.9684 ms against the ADR 0025 threshold of 5 ms.** No
pre-registered predicate, threshold or analysis rule changed, and none was edited.

**What did change** is the auxiliary claim `smoke/g3/REPORT.md` has carried since the first
seal-time re-run: *"the confirmation run does not separate from the adjudicated one; every
seal-time re-run does, completely."* Recomputed exactly over all C(8,4) = 70 labelings, this run
gives **U = 14, exact two-sided p = 0.1143, batch range 2.8338–3.4035, which OVERLAPS** the
adjudicated 2.7511–2.9190. Four of five seal-time re-runs separate completely; this one does not.
The full table, the seven medians and the evidence that the drifted code is **not** the cause
(`b3.py`, `base.py`, `authority.py` and `allowed.py` are byte-identical between `17e11c9` and
`8ac7b21`, and G-3 times `B3Arm.decide` alone) are in `smoke/g3/REPORT.md`.

**The seal was STOPPED at this point** — the B2 brief makes a changed finding a stopping condition.
Gates G-6, G-7, G-10 and G-12 were **not** run; no manifest was built, no anchor stamped, nothing
superseded and no sealing commit made. `docs/PRE_REGISTRATION.md` is untouched.

**Not re-run for a better number.** One run was taken. The rule binds hardest when the number is
unwelcome.

**RESOLVED 2026-08-07 by the Commander's decision: the declaration was AMENDED, and the seal then
completed as v0.8.** Re-measurement after seeing an unwelcome number was explicitly **refused** as
result-driven measurement; retracting the disclosure entirely was refused as going too far. What
was amended is a **disclosure**, by dated addition with the original wording preserved verbatim —
no hypothesis, decision rule or gate criterion was touched, and the adjudicated 2.8264 ms is
unchanged. The corrected reading is that the scatter across seven runs is **itself** the evidence
that the pairwise separations measured run-to-run variation rather than drift.

**An eighth median followed, under a revised stopping condition** (stop only if it falls outside
2.6772–2.9684 ms or fails the 5 ms threshold): **2.7527 ms**, inside the band, PASS, with the IQR
back to 0.1161 ms from re-run 5's 0.4413 ms. The record now contains its own sharpest illustration
— re-run 2 (2.7363 ms) and re-run 6 (2.7527 ms) differ by **0.0164 ms** and still "separate
completely" at U = 16, p = 0.0286, with `b3.py` byte-identical at both commits.

**One transient consequence, recorded because D-002 exists.** The v0.8 sealing commit `52692d4`
relocated `seal/manifest_v0.7.json` into `seal/superseded/`, and one test pinned
`analysis/latency.py` against that path, so the suite was **red at that single commit**. The
**sealed tree is green**: the manifest's implementation commit is `ffa216e`, where the file had not
yet moved and the suite passed 1605. Fixed in the following commit by pinning against *every*
manifest that covers the file rather than one named path — which is also the stronger claim.

## D-007 — 2026-08-07 — The sealed platform reader crashes under a PowerShell parent process. **FIXED at task B2 STEP 2 (ADR `000C`).**

**A latent defect in a COVERED file**, `src/harness/measurement_platform.py`, found while reading
frozen row 9 for the v0.8 seal. Recorded, **not fixed**, because fixing it mid-seal would add a
third drifted covered file to a reseal whose scope the Commander had already measured.

**What it is.** `_powershell()` calls `subprocess.run(..., text=True)` with **no `encoding=`**, so
Python decodes the child's bytes with the locale codepage — `cp936` on this machine. What the child
emits depends on the *parent*: under a `bash`/`cmd` parent, nested PowerShell writes **GBK**, which
cp936 decodes correctly; under a **PowerShell** parent it writes **UTF-8**, which cp936 cannot
decode. The result is `UnicodeDecodeError` inside `subprocess`, then `AttributeError: 'NoneType'
object has no attribute 'strip'` at `active_power_scheme()`. **Row 9 cannot be read and G-3 cannot
be adjudicated from a PowerShell parent.** This is the same defect class as the `smoke/g10/spike.py`
decode fault fixed at the v0.7 seal.

**Why it is not urgent: it fails CLOSED.** It either returns the correct value or crashes loudly.
It never returns a *wrong* platform fact, so no measurement taken through it is in doubt — unlike
the G-10 fault, which silently discarded evidence, or ADR 0046's, which turned a timeout into a
denial. Row 9 as read for this seal is correct and complete: 37 leaves, `power_scheme_name` =
U+9AD8 U+6027 U+80FD with zero replacement characters, matching `docs/measurement_platform.md`.

**Why it matters anyway.** It is a **reproducibility** defect in sealed apparatus: an independent
reproducer on Windows driving the campaign from PowerShell hits it on the first step.

**FIXED, at the Commander's instruction, in the v0.8 seal (ADR `000C`).** `_powershell()` now
captures bytes and `_decode_console()` tries `utf-8` then the locale codepage **strictly**, taking
the first clean decode and **raising** if neither works.

**The instructed fix was `encoding="utf-8", errors="replace"` — the same one G-10 received — and it
was measured before being applied, which is why it was not applied literally.** On this machine it
repairs the PowerShell parent and **silently corrupts the `bash` parent**, turning `高性能` into
`������` — and `bash` is the parent every one of the seven G-3 runs and every row 9 read has used.
That would have traded a **loud crash** for a **quiet wrong answer inside a sealed platform fact**,
which is the opposite of the direction this project fails in. The strict fallback chain is correct
under both parents; all three behaviours are tabulated in ADR `000C`.

**Verified after the fix:** row 9 read under a `bash` parent and under a PowerShell parent is
**byte-identical, 37 leaves, 0 differing**, `power_scheme_name` = U+9AD8 U+6027 U+80FD, no
replacement character under either. **No previously sealed row 9 value is in doubt** — the defect
crashed or was correct, never wrong.

## D-006 — 2026-08-07 — RQ4's latency pass. The half of step 7 that had not run.

**Not a departure from the plan; a departure from what was REPORTED.** The step 7 completion report
(D-005) described the security half and said nothing about RQ4 having no data. This entry and
**ADR 0047** record that, in the terms this project uses for it: *an absence that reads as
coverage*.

**What ran.** `python -m src.harness.latency_collector`, once, on the **PILOT** corpus, at working
tree `dc1ef22` plus the collector. 9 arms × 2 scenarios × 2 phases × 3 batches × 75 repetitions =
**40,500 span rows, 225 repetitions per configuration**, 274.7 s. `analysis/latency.py` was **not
modified** — a test pins its blob hash against the v0.7 manifest.

**Why the pilot corpus, stated here as well as in the ADR because the results chapter must carry
it plainly:** every sealed artifact that names the refusal-path cell names the **pilot** id
`gt-f1-chain-tamper` — frozen row 1, §6, ADR 0026, the design document §J.3 item 12, and
`analysis/latency.py` — and none names the confirmatory one. Measuring on the corpus the
specification names is following the pre-registration. Had the pass run on the confirmatory corpus,
the sealed by-name refusal would have sat **inert** and the refusal path would have been silently
pooled into the benign estimand.

**Artifact, BOTH hashes** — the fourth appearance of the CRLF/LF split, handled **in advance** this
time rather than after a reader would have recomputed a different value:

| artifact | committed blob (SHA-256) — **what a clone reproduces** | on disk after checkout |
|---|---|---|
| `results/raw/latency-pilot.json` | `6d93e713b533c24a9136f8e5e7a1c7f69bd543e410a284a7470a6ac09ec442f5` | `2a51e5e4d41b38793fdc6d9b54561320e8dba109f215798c227d65c5ca92f73f` |

The on-disk file carries 405,044 CR bytes; the committed blob carries none, and the two differ by
the line-ending conversion alone.

**No exclusion rule was applied, and that is a decision rather than an omission.** ADR 0038's
Sighting C has never been observed as a per-operation stall, so a threshold now would be invented
for an effect not shown to exist, and a threshold set after seeing the data is what pre-registration
forbids. Raw per-repetition values with per-repetition wall-clock stamps are persisted precisely so
a stall is locatable in time rather than absorbed into a summary. **No per-operation stall was
observed during this pass** — had one been, it would have changed the Commander's decision and this
entry would say so.

**No verdict field reaches the latency artifact**, asserted by test over the field list the
collector names. The security half's "once" stays consumed and unre-run.

## D-005 — 2026-08-07 — Part H step 7 executed. One run, no abort, no re-run.

**Not a departure.** Recorded here because §J.4 item 13 asks for abort and re-run events, and the
honest report of "there were none" is worth as much as a list of them — a deviations log with a
gap where the campaign should be is indistinguishable from one nobody kept.

**What ran.** `python -m src.harness.campaign_driver --run-mode confirmatory` (ADR 0045), once, at
the sealing commit **`17e11c9`**, with **`git_dirty: false`**, on the row 9 platform, in-process and
ledger-backed. Wall time 13.6 s.

**The cell arithmetic, stated exactly rather than loosely.** The campaign is **not** 13 × 9 × 3:
the three passes do not each cover all thirteen scenarios. The F1/F2/F3 chain runs **once**, with
no monitor configuration to vary, and only the F4/F5 chain runs twice, because §E.4's `A†` —
*admitted **absent** the shared monitor* — is only expressible if the same scenarios run under both.

| pass | scenarios | arms | cells |
|---|---:|---:|---:|
| F1/F2/F3 chain, monitor-agnostic (`monitor_attached=None`) | 9 | 9 | 81 |
| F4/F5 chain, `monitor_attached=False` | 4 | 9 | 36 |
| F4/F5 chain, `monitor_attached=True` | 4 | 9 | 36 |
| **total** | | | **153** |

**153 cells − 10 unscorable = 143 scored.** The split into two chains is a property of the sealed
corpus and not a choice: the corpus declares two distinct task grants, so each chain needs its own
provisioned AS (ADR 0045).

**Artifacts, with BOTH hashes, because they differ and the difference has bitten this project
three times.** Git converted LF to CRLF on checkout (`core.autocrlf=true` on this machine), so the
bytes on disk are **not** the bytes in the commit. **A third party who clones and recomputes gets
the committed-blob hash** — that is the one to check a copy against. The on-disk hash is what the
run produced locally and is recorded only so the two are never confused for evidence of tampering.

| artifact | committed blob (SHA-256) — **what a clone reproduces** | on disk after checkout (SHA-256) |
|---|---|---|
| `results/raw/campaign-confirmatory.json` | `5b7729c409c690a43f01275addaeebf465d7752c7d6581cc2659b9302b7258b3` | `406b51f98c40a491e8c6a9aa645c89fa9aa67b6cc746457b41cefc2ee79c8495` |
| `results/tables/results-confirmatory.json` | `bf41635f2cf65bb113880261b000fa425f572302373f1b70aeea618594942f23` | `c5df94cc39f52b9178a6054bec88fedc0808f528445f0a701a6343ab5b67118e` |
| `results/tables/results-confirmatory.md` | `83d6305eaa51815965f6f742742d7c60e221f1dbad721f9c98aed927c87a2c94` | `b6e163b8a8d2508eb62bb5c52b25528ed32e5bb9ce9a8bbfe86c0bc42e1c4170` |

**Which is which was established mechanically, not by assertion.** For all three artifacts the
committed blob contains **zero** CR bytes and the on-disk file contains 7672 / 1065 / 121 of them,
and `on-disk bytes == committed blob with every LF replaced by CRLF` holds **exactly** in each
case. Nothing but the line-ending conversion separates them; **no byte of any trace was rewritten,
and nothing was re-run.**

*Correction, same day.* This entry first recorded only the on-disk hash, as if it were the hash of
the artifact. It is not the one anyone else can compute: a clone yields the committed blob, so a
reader recomputing would have got a different value and been entitled to conclude the primary
evidence artifact had been altered. **This is the CRLF/LF defect's third appearance** — it corrupted
v0.5's manifest anchor, was handled deliberately at v0.6 and v0.7 by staging the manifest from raw
disk bytes, and was then missed here because `results/` went in through a plain `git add`. The
trace is **not** rewritten to match a hash; both hashes are recorded and named instead.

The run record inside the raw trace carries `git_commit = 17e11c9…`, `git_dirty = false`, and the
three frozen digests `H(Γ)`/`H(R)`/`H(Λ)` matching `docs/frozen_parameters.md` exactly.

**Every unscorable cell, with its cause** (the pre-registration requires each to be reported):
all **10** read *"NA per the sealed record"* — 4 on `cf-f1-chain-tamper` (`B0`, `B1`,
`B2-broad-noexchange`, `B2-exchange-broad`) and 6 on `cf-f2-wrong-holder-proof` (those four plus
`B2-exchange-task` and `B-cap`). These are §E.4's own `NA` cells: arms that cannot express the
case. **No cell was lost to a wall-clock straddle, to an exhausted authorizer, or to a runner
error** — the three apparatus failure modes that would have made a cell unmeasurable for a reason
having nothing to do with the mechanisms.

**No result-driven change was made after seeing any number.** Nothing in the apparatus, the
analysis, the corpus or the pre-registration has been edited since the seal; this entry and the
`.gitignore` line that archives the trace are the only writes, and neither can alter a verdict.

## D-001 — 2026-08-07 — The v0.6 seal is superseded before any campaign, for apparatus defects found by pre-run audit

**Departure from:** nothing in the pre-registration's predictions — this is a Part H
unseal/reseal, which Part H provides for explicitly ("Any change to sealed design, oracle, config,
or corpus → full unseal/reseal").

**What happened.** Before executing step 7, the sealed tree was audited against the question of
whether the confirmatory campaign was runnable and would measure what the pre-registration says.
It was not runnable, and two defects would have produced wrong numbers rather than a crash. Full
finding: **ADR 0044**.

**What it means for the record.** The v0.6 seal (`cdf185d`) stands as a correct seal over the tree
it described and keeps its OpenTimestamps anchor; it is superseded, not deleted, and moves to
`seal/superseded/`. **No result is carried over, because none was produced** — no campaign was
started, so the step 7 "once" is unspent and nothing is being re-run to obtain a different verdict.

**The two defects that would have changed published numbers**, recorded here as well as in ADR 0044
because the dissertation must report them rather than absorb them into the apparatus:

- The oracle could never verify a `DeclassificationArtifact` (a pydantic `bytes` coercion of a
  base64url string). Every arm correctly admitting the benign control `cf-f4-declassified` would
  have been scored `admission_breach`, including `B3`/`B3⁺`, and `false_block` would have been
  unreachable for that scenario.
- `realized_harm_F4` was structurally always `False` (the ingestion `LabelDirectory` was never
  wired, so every effect carried no labels). A sensitive egress that actually executed would have
  been scored as no harm.

**Why this is not "fixing the result".** Both defects were found and fixed **before** any
measurement existed. Neither changes a prediction, a predicate's definition, a threshold or a
frozen row; they restore the oracle to what §Part I and ADR 0030 already specify. Had either been
found after the run, Part H's no-result-driven-tuning rule would have forbidden the fix and the
affected families would have been reported as invalid.

## D-004 — 2026-08-07 — A G-2 semantics test failed intermittently. ROOT CAUSE FOUND AND FIXED before the campaign (ADR 0046).

**Departure from:** nothing pre-registered — this was a defect in the apparatus, recorded here
because it bears on a red-line gate and on the quantity the study measures.

**What happened.** `tests/test_frozen_authorizer_semantics.py::test_frozen_gamma_denies_third_party_widening`
failed once in six full-suite runs at HEAD `d99cd60`. The failure is in the **positive arm** — a
genuinely granted element failing to authorize — not in the security assertion. Full record,
including a proposed mechanism that was tested and **refuted**, in **ADR 0038, Sighting D**.

**Why it is recorded as a deviation rather than a flaky test.** Gate **G-2** is one of the three
construct-validity life-or-death gates (`PROJECT_RULES.md` red line 3), and the code path this
test exercises is the one that computes every `C_i = Allowed(P_i; Γ, κ, Ω)` — once per candidate
element. If a legitimate authorization can intermittently return a denial, an authority set can be
computed **smaller than it is**, and authorization-scope amplification is a function of exactly
those sets. A flake here is not cosmetic; it is a threat to the measurement.

**Direction: AGAINST this work's hypothesis** — it makes a capability arm look more restrictive
than it is. That is the same direction as ADR 0038's Sighting B and both of its reproductions, and
it is stated because the project's §6.1 pattern (*every dormant defect failed toward the
hypothesis*) still does not hold.

**Status: ROOT CAUSE FOUND AND FIXED, before any campaign ran (ADR 0046).** The pinned
`biscuit-python` authorizer defaults to a **one-millisecond wall-clock** evaluation budget, and a
breach raises the same exception class a policy denial raises — so both call sites recorded a
timeout as a refusal. Under full-suite load a normally sub-millisecond evaluation occasionally
exceeded it. The budget is now set explicitly (1 s, ~1000× the observed cost) and **a limits breach
raises instead of denying**, on both sides independently.

**What this would have done to the results, stated plainly because it is the reason this entry
exists:** an element could be dropped from an authority set on a busy machine, silently. Amplification
is a function of those sets, so a table could have carried a number that was an artifact of machine
load — in the direction that makes a capability arm look *more* restrictive than it is. **No result
is affected, because no campaign has run.** Had it been found afterwards, Part H's no-result-driven-
tuning rule would have forbidden the repair and the affected families would have had to be reported
as unreliable.

Not attributed to the ADR 0044 repairs: the defect is in `biscuit-python`'s defaults and in error
handling that predates them, and an eighteen-run control at `cdf185d` showed intermittent failure
before any repair.

## D-003 — 2026-08-07 — The campaign driver was smoke-tested against the CONFIRMATORY corpus before the seal. Reported, not buried.

**Departure from:** `PROJECT_RULES.md` red line 2 and Part H's ordering — no confirmatory campaign
before the seal. Every one of the fifteen gates was adjudicated on the **pilot** corpus precisely so
that the confirmatory corpus stayed untouched until step 7.

**What happened.** While building `src/harness/campaign_driver.py` (ADR 0045) I ran it once with
`--run-mode confirmatory`, writing to a scratch path outside the repository, to verify that the new
entry point executed end to end. It did: it reported **143 cells, 10 unscorable, 3 passes**. That
was the wrong corpus to smoke-test on, and the pilot corpus — which is what the gates used and what
the driver supports with `--run-mode pilot` — was the correct one. The same smoke test was then
re-run on the pilot corpus and reports the identical structural counts.

**What was and was not observed, stated precisely because the distinction is the whole point.**
The only output read was the three aggregate counts above, which are structural (how many cells the
matrix has, how many the sealed records mark `NA`, how many passes the corpus's two chains require)
and contain **no verdict for any cell**. The result file was **deleted without being opened**;
its SHA-256 was `0d417fa643ca31fa59b9aebb28aa635492d27bb99e2eaa88fa495084607ea2df` and its size
246,863 bytes, recorded here so the claim is checkable rather than asserted. The effect-ledger tree
the run produced was deleted with it. No `A`/`B` cell value, no per-family rate, no
`admission_breach`, `false_block` or `realized_harm` value was read by me or written into any
document, commit, or test.

**Why this is a deviation to report rather than an incident that invalidates anything.** Part H's
"once" governs the **frozen** campaign — the one executed against sealed artifacts after step 6.
This ran against an **unsealed working tree**, mid-repair, on code that is not the v0.7 candidate's
final state, so it is not the "once" and the "once" remains unspent. Nor is it result-driven
tuning: no apparatus decision in this branch was made after, or because of, anything this run
produced. The repairs it followed were all specified in ADR 0044 and 0045 **before** it ran.

**What guards against it recurring.** The driver refuses to overwrite an existing
`results/raw/campaign-<mode>.json`, so a second run is a visible decision rather than a default.
That guard did not apply here because the smoke run wrote outside `results/` entirely, which is
itself worth recording: the write-once protection lives in the driver, and a `--out` override
bypasses it by design (a scratch smoke test must not be able to claim the real path).

**The honest residue.** A reader is entitled to know that the confirmatory corpus has been executed
once by the apparatus before sealing, even though no verdict was inspected, and that is why this
entry exists rather than a quieter one.

## D-002 — 2026-08-07 — CI was red from `ca360ae` to `cdf185d`, across two sealing commits

**Departure from:** design §J.2 item 7 (CI runs the gates on every push, as regression protection).

**What happened.** GitHub Actions failed on every push from 2026-08-06 (`ca360ae`) through the v0.6
sealing commit (`cdf185d`) and this was not noticed while sealing. The cause is entirely in the CI
configuration: `actions/checkout@v5` clones at depth 1, and three provenance tests in
`tests/test_pre_registration.py` walk real git history (`git log -- <path>`,
`git merge-base --is-ancestor`), which a shallow clone cannot answer.

**Reproduced, not assumed:** a local depth-1 clone of the same commit gives **3 failed, 1405
passed** — 1405 + 3 = 1408, the full suite's count on the row 9 platform — and the three failures
are exactly those history-dependent tests.

**Effect on the seal: none, and the reason is pre-registered.** `frozen_parameters` row 2 fixes
that a Linux CI run is *"regression protection only and is never adjudicative"*. Every adjudicative
gate was measured on the row 9 platform, and the local suite was green (1408 passed) immediately
before the sealing commit.

**Fixed** by `fetch-depth: 0` in `.github/workflows/ci.yml`, a manifest-excluded file, so no reseal
is required for this item alone.

**Recorded because the honest statement is uncomfortable:** for a week the local suite was the only
thing being read, and a red CI badge sat on two sealing commits. That is a fact about this project's
assurance practice and belongs in the record rather than in a commit message.
