# 000B — RQ4, the half of step 7 that did not run

*Unnumbered: ADR numbers are the Commander's. The placeholder letter is `000B`.*

## Context

**Part H step 7 ran its security half only, and the report said "complete".**

The confirmatory campaign executed once on 2026-08-07 at the v0.7 sealing commit `17e11c9`,
produced 143 scored cells, agreed with §E.4 on every measured cell, and was reported as step 7
finished. It was not. **RQ4 — *"the absolute added latency of each mechanism, separated into setup,
delegation, boundary-verification and end-to-end components, under cold and warm conditions"* — had
no data at all**, and neither did `frozen_parameters` row 1's `lightweight_claim`, whose decision
rule is the upper bound of the 95% bootstrap CI on `median(B3) − median(B0)` against the 20 ms
margin. **Without samples there is no interval, so that claim could neither hold nor be retracted.**

**The reporting failure is the part worth recording.** This project names one failure mode more
often than any other — *an absence that reads as coverage* — and the step 7 report committed it. It
enumerated 143 cells, zero disagreements and ten unscorable cells with causes, and said nothing
about the fourth research question having no data. A reader of that report would have concluded the
campaign was done. The gap was found only because the Commander asked why RQ4 had no data.

### Three causes, and one of them was a false premise nobody had rechecked

1. **`TimingSeams.recorded()` returns names, not values**, and `campaign.py`'s field comment said no
   duration may reach the artifact, citing EXP6 forbidden action 1 — whose stated premise was
   *"G-3 has not run on a locked row 9 platform."* **That premise had been false since 2026-08-02**:
   row 9 was locked, G-3 was adjudicated on it, and it has been re-measured six times since. The
   ban outlived its reason by five days and nobody rechecked it, because a rule that cites a reason
   is read as though the reason still holds.
2. **The campaign driver implements the security protocol** — one run per cell — and RQ4 needs the
   other one. `analysis/latency.py`'s `Sample` requires `phase`, `batch` and `repetition`, and
   **no producer for any of the three existed in `src/`.**
3. **The pre-run audit found this and it was not fixed.** The audit that produced ADR 0044 reported
   it as gap M3, in these words: *"no duration ever leaves the runner"*. The v0.7 reseal then
   repaired six other things and left this one, so the campaign ran with the gap open.

## Decision

`[DESIGN]` **Build the collector, drive the sealed §6 plan unamended, and measure on the PILOT
corpus.**

### The corpus, and why this is not a workaround

The task specification for this work asserted that `cf-f1-chain-tamper` is the cell excluded by name
and that `analysis/latency.py` already refuses it. **That is false, and checking it rather than
satisfying it is what stopped the work before an artifact was built.** Five sealed artifacts name
the refusal-path cell, and **all five name the pilot id**:

| sealed artifact | names `gt-f1-chain-tamper` | names `cf-f1-chain-tamper` |
|---|---:|---:|
| `docs/frozen_parameters.md` row 1 (a frozen row) | 1 | **0** |
| `docs/PRE_REGISTRATION.md` §6 | 1 | **0** |
| ADR 0026 (fixes the estimand and the exclusion) | 1 | **0** |
| `docs/EXPERIMENT_ARCHITECTURE_FINAL.md` §J.3 item 12 | 1 | **0** |
| `analysis/latency.py` (`REFUSAL_PATH_SCENARIO`, 11 uses, no override) | 1 | **0** |

**The sealed latency specification is written for the pilot corpus throughout, so measuring on the
pilot corpus is following the pre-registration.** Had the pass been run on the confirmatory corpus,
`benign_series` would not have refused `cf-f1-chain-tamper` — it names the pilot id — so the
refusal-path samples would have been **silently pooled into the benign per-arm series and into row
1's estimand**, which ADR 0026 says would inflate *"asymmetrically across the ladder … exactly the
arms whose online round trip the study is trying to isolate"*; and `refusal_series` would have
raised on an empty series, so the refusal path could not have been reported at all. **The acceptance
test would have produced a `Decision` while the guard sat inert** — a masked check reading as a
pass.

RQ4 asks for **mechanism** cost, which is a property of the arms rather than of a corpus's attack
content, and G-3 — the boundary-verification cost gate — was itself adjudicated on the golden
thread. **Extending the by-name exclusion across corpora was considered and declined by the
Commander**; it would require editing a sealed analysis module and amending a frozen row's named
exclusion, and it belongs to a separate decision, not to this one.

### What the collector does, and what it refuses to do

- **Raw per-repetition values for all five spans**, never summaries, each carrying the UTC wall
  clock at the start of its repetition.
- **No exclusion or outlier rule.** ADR 0038's Sighting C — the undiagnosed 217 s-versus-36 s
  full-suite stall — has **never been observed as a per-operation stall**, so a threshold now would
  be invented for an effect not shown to exist, and a threshold set later, after seeing the data, is
  precisely what pre-registration forbids. The estimand is a median, robust to a handful of stalls;
  §6 already reports batches separately, so a stall surfaces in that batch's p95 and IQR. **Report,
  do not discard.** This is why raw values matter: a stall inside a summary is invisible.
- **No verdict field reaches the artifact.** The loop executes scenarios, so verdicts are computed
  internally; none is read and none is written. The security half's "once" is consumed, and a
  latency artifact carrying verdicts would be indistinguishable, in a results table, from a re-run.
  The forbidden field list is named in the collector and asserted by test.
- **`analysis/latency.py` is not touched.** It was sealed before the collector existed, so it is the
  specification and the collector fits it. A test pins its blob hash against the v0.7 manifest.

### The ban, corrected rather than deleted

EXP6 forbidden action 1's ban on *producing* a latency number is **lifted**, and the record says so
in place: `campaign.py`'s comment now quotes what it used to say, states that the premise is false
and since when, and names what replaces it. **`smoke/g3/REPORT.md` remains the sole owner of the
boundary-verification cost figure** — no timing figure is published outside it — while the collector
produces the per-component series RQ4 asks for, into `results/raw/`. The campaign's own security
artifact still carries span **names** only, for the same reason it always did.

## Status

proposed — 2026-08-07. **Unnumbered by instruction.** This task does not reseal; task B2 does.
`seal/` is untouched.

## Consequences

- **The results chapter must state plainly that the latency measurement was taken on the pilot
  corpus**, with the five sealed artifacts that make it the specified corpus, and not in a
  footnote. A reader comparing a confirmatory security table with a pilot latency table is entitled
  to know they are different corpora and why.
- **Row 1's `lightweight_claim` becomes decidable** for the first time. Whatever it decides is the
  result: the margin, the estimand, the arms and the decision rule were all fixed by ADR 0026 before
  any sample existed, and the seed is recorded so the 10,000 resamples are reproducible.
- **The step 7 completion report was wrong and stays on the record.** DEVIATIONS.md D-005 describes
  the security half; this ADR is what says the other half was missing and that the report did not
  say so.
- **The v0.7 seal is now behind the code**: `src/harness/runner.py`, `src/harness/campaign.py` and
  the new `src/harness/latency_collector.py` are covered files that have changed. A reseal is owed
  and is task B2's. Until it happens the seal describes `9b75ba1`, which is still exactly what it
  says it describes — the manifest is not wrong, the working tree has simply moved past it.
