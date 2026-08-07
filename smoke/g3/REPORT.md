# Gate G-3 — boundary-verification cost — **PASS**

> **This file and `smoke/g3/spike.py` are the only places in the repository where a timing number
> appears.** The project's "no timing number" invariant became *narrower* on 2026-08-02, not void:
> no latency figure belongs in an ADR, a README, a commit message, or any other gate's report.

**Part G's row:** *"Sign/verify 1,000 HTC+INV pairs (Ed25519); time boundary verification."*
**Criterion (`frozen_parameters` row 2, ADR 0025):** the **median single boundary-verification cost**
is `≤ 5 ms` on the row 9 sealed measurement platform.

**Adjudicated 2026-08-02 on the row 9 platform**
(`Windows 25H2 build 26200.8875; i7-12700H; 14C/20T; 15.75 GiB DDR4; High performance; on AC`),
recorded in full in `docs/measurement_platform.md`. Row 9 was **locked in a separate commit before
this measurement was taken**, so the platform was sealed before the number existed.

## Result

| quantity | value |
|---|---|
| **median** | **2.8264 ms** |
| p95 | 3.4841 ms |
| IQR | 0.2898 ms |
| pairs timed | 1,000 (4 batches × 250) |
| warm-up discarded | 100 |
| per-batch medians | 2.9190, 2.8259, 2.8213, 2.7511 ms |
| last-vs-first batch drift | **−5.8%** |

**Verdict: `2.8264 ms ≤ 5 ms` — PASS.** Nothing else decides it.

## The quantity is `boundary_verification` ALONE

This is **row 2**, not row 1, and ADR 0026 separated them deliberately:

| | row 2 (this gate) | row 1 (after the seal, not here) |
|---|---|---|
| quantity | `boundary_verification` alone — `arm.decide(...)` | `presentation + boundary_verification` |
| statistic | median, single invocation | `median(B3) − median(B0)`, 95% bootstrap CI upper bound |
| bar | ≤ 5 ms | < 20 ms |

The two bars differ on purpose — a gate threshold wants headroom, an equivalence margin encodes what
the field tolerates. **Nothing here says anything about row 1's estimand**, and the number above must
not be quoted as though it did.

Each of the 1,000 iterations re-runs `delegate` (signing the HTC chain) and `present` (signing the
INV), so a **fresh pair is signed** as Part G's row requires; only `decide` — the verification — is
inside the timed span.

## The headroom is real but **thinner than ADR 0025 argued**, and that is a finding

ADR 0025 justified 5 ms partly on the expectation that *"Ed25519 plus RFC 8785 canonicalization over
the golden-thread payloads sit well below it, leaving roughly three- to tenfold headroom — so both
outcomes are informative and the gate can fail."*

**Measured headroom is 1.77×, not three- to tenfold.** The gate passes and the threshold is
untouched — it was fixed in advance precisely so the data could not move it — but the ADR's
*quantitative* expectation about the margin was optimistic by roughly a factor of two. Recorded here
because a reader comparing the ADR's prose to this result would otherwise find a discrepancy and have
to guess which was adjusted. **Neither was.**

The direction matters for what comes next: **row 1's estimand includes `presentation` as well**, and
`presentation` is where `B3`'s per-invocation signing lives. Nothing here predicts row 1's outcome —
that is RQ4's campaign, after the seal — but the margin is not so large that the result can be
assumed.

## What a failing world looks like here

The comparison is a plain `median <= threshold` on the number printed above, so a failure needs the
verification to cost **1.77× more** than it does — about 5 ms. That is not a hypothetical régime: it
is roughly what this same measurement would report if the process were **not pinned** and a
meaningful share of repetitions landed on E-cores, or if it ran **on battery**. Both are refused by
the spike rather than left to chance (`G-3.H1`, `G-3.H2`), and both would otherwise have moved the
number in the direction that fails.

So the gate is not one whose criterion cannot fail: two ordinary and *unremarkable* conditions on
this machine would push it over, which is why the hazards are handled rather than hoped away.

## The three hazards

**1. P-core / E-core scheduling — pinned, and the mask was DETECTED.**
`GetSystemCpuSetInformation` was walked record by record and each logical processor's
`EfficiencyClass` read; **two classes** were found and the process was pinned to the highest,
logical processors `[0…11]`. The detection **fails closed** — no mask is guessed — because a guessed
logical-processor range would silently reintroduce exactly the bias the pinning removes. Unpinned,
Thread Director scatters repetitions across E-cores and the distribution goes bimodal, so the p95 and
IQR §E.5 requires would be reporting the **scheduler's** spread as the mechanism's.

**2. AC power — asserted.** `G-3.H2` confirms mains; the spike refuses on battery with a named error,
because a laptop throttles on battery whatever the power plan says.

**3. Thermal — measured, and NOT observed.** Four batches, medians `2.9190, 2.8259, 2.8213,
2.7511 ms`. The last batch is **5.8% faster** than the first, not slower, so there is **no thermal
degradation across this run** — if anything the warm-up continued mildly past its first 100
iterations. Stated explicitly because the check exists to be able to say the opposite: a
systematically slower late batch would have been thermal, and it would have been reported rather than
averaged into the median.

**Hazard state as found, and deliberately not changed** (changing the power plan between locking
row 9 and adjudicating G-3 is forbidden): sleep on AC is **600 s and is not off**; hibernate is
never; USB selective suspend is enabled. The run is far shorter than ten minutes, and no USB device
is in the measured path — G-3 times signature verification with no effect ledger involved.

## Warm-up

**100 iterations discarded**, ~10% of the sample. Fixed *in advance* rather than chosen by looking at
where the curve flattens, which would be fitting the warm-up to the data. It is comfortably past the
first-call effects that dominate early iterations here: lazy imports in the crypto and Biscuit paths,
first-touch allocation, and cold branch predictors.

## Linux CI is regression protection only, and is **never adjudicative**

Row 2 names *the row 9 sealed measurement platform*. On any non-Windows platform the spike prints
that it is **NOT ADJUDICATED**, completes the pairs as a regression check, and **records no verdict**
— the same rule G-12 applies to its ledger-backed limbs. A Windows-platform criterion must not be
laundered into a green Linux tick.

## IA-3

**Moves to verified.** Fixing a threshold was never verifying an assumption — ADR 0025 says so
explicitly — and measuring against it on the sealed platform is.

## Scope

This gate establishes **cost on this platform for `boundary_verification`**. It does **not**
establish row 1's estimand, the equivalence margin, or anything about `B0`; it adjudicates no other
gate; and it re-triggers if row 9 changes — a power-plan, hardware, driver or Windows-build change
invalidates this adjudication (ADR 0025).

---

## Seal-time re-run — 2026-08-06, at the commit being sealed (`396c2b6`), NOT a re-adjudication

Part H step 3's ordering requires the five platform-bound gates re-run **on the commit that is
sealed**, so that no line of the sealed gate record is derived from a measurement taken on a
different commit. This section is that record for G-3; the figures land here and nowhere else,
because this file is the only place a timing number may appear. **The adjudicated record above —
2.8264 ms, 2026-08-02 — stands unchanged**; this re-run confirms it on the sealing candidate.

Run **first among the five, alone, on the idle row 9 machine**, before G-6/G-7/G-12/G-10 heated
it. Row 9 was machine-read before the first gate and after the last: **all 27 read fields
identical, zero differ** (power-scheme GUID `da75b896-…` byte-identical; hazard state 600/0/1 as
found and unchanged). `G-3.H1` (pinned to detected P-cores `[0…11]`) and `G-3.H2` (on AC) both
passed.

| quantity | adjudicated 2026-08-02 | seal-time re-run 2026-08-06 |
|---|---|---|
| **median** | **2.8264 ms** | **2.6856 ms** |
| p95 | 3.4841 ms | 3.2656 ms |
| IQR | 0.2898 ms | 0.0998 ms |
| per-batch medians | 2.9190, 2.8259, 2.8213, 2.7511 | 2.6750, 2.6920, 2.6890, 2.6858 |
| last-vs-first drift | −5.8% | +0.4% |
| verdict | PASS (≤ 5 ms) | **PASS (≤ 5 ms)** |

The re-run median sits **−0.1408 ms (−5.0%)** below the adjudicated one — the same magnitude and
direction as the 2026-08-03 confirmation run (2.6928 ms, `tools/gate_rerun/REPORT.md`, which also
showed the two do not separate: Mann-Whitney U = 12, p = 0.34). Today's spread is tighter
(IQR 0.0998 vs 0.2898) and drift is flat. Run once; not re-run for a better number. **G-10's `L4`
then re-ran this spike warm as a subprocess later the same session and it PASSED**; `L4` records
pass/fail only, so no warm median exists to quote — exactly the limitation the gate-rerun report
recorded.

### Seal-time re-run 2 — 2026-08-06, at the sealing candidate `aeee0ea`, after the signing stop

The first seal attempt stopped, correctly, at unconfigured commit signing; the pre-registration's
G-3 declaration then gained the three-run separation record, and the completed seal re-measures on
the commit actually sealed. Same discipline: first among the five, alone, idle machine, row 9 read
before and after (**all 27 fields identical, zero differ**), `G-3.H1`/`G-3.H2` both PASS.

| quantity | value |
|---|---|
| **median** | **2.7363 ms** — **PASS (≤ 5 ms)** |
| p95 / IQR | 3.6292 ms / 0.2243 ms |
| batch medians | 2.7306, 2.7458, 2.7431, 2.7395 ms |
| drift | +0.3% |

**The four medians: 2.8264 (adjudicated, the record) → 2.6928 → 2.6856 → 2.7363.** The separation
finding, recomputed with this run included, is **unchanged**: against the adjudicated batches,
U = 16 and exact two-sided p = 0.0286 again — complete separation, the ranges 2.7306–2.7458
(this run) and 2.7511–2.9190 (adjudicated) do not overlap, though the gap is thin (0.0053 ms).
What this run adds honestly: the monotone-downward pattern the pre-registration declares **across
the three runs it names** does not extend to a fourth — 2.7363 sits above both ~2.69 runs — which
reinforces, rather than undermines, that declaration's own caution: repeated runs on one machine
cannot distinguish machine-state variation from genuine drift, and no cause is claimed. The
adjudicated **2.8264 ms stands as the record and remains the conservative figure**; the gate
verdict is unaffected; the pre-registration's declaration, scoped to the three runs it names,
remains true as written and is not edited.

### Seal-time re-run 3 — 2026-08-06, at the v0.6 sealing candidate `9db1404`

The v0.5 seal was superseded before the confirmatory campaign ran: the sealed generator could not
produce a confirmatory corpus (ADR 0043), so the corpus was generated, two declarations were
pre-registered, and the reseal re-measures on the commit actually sealed. Same discipline as the
two runs above: **first among the five, alone, on the idle row 9 machine**, before G-6/G-7/G-12
and before G-10 heated it, under the cp936 console codepage the platform reader assumes. Row 9
machine-read before the first gate and after the last: **37 leaf values compared element-wise,
zero differ** — the two reads are byte-identical documents, power-scheme GUID
`da75b896-eea0-461c-a43a-73a73caf9f43` included, hazard state 600/0/1 as found. `G-3.H1` (pinned
to the detected P-cores `[0…11]`, read from `GetSystemCpuSetInformation`) and `G-3.H2` (on AC)
both PASS.

| quantity | value |
|---|---|
| **median** | **2.6772 ms** — **PASS (≤ 5 ms)** |
| p95 / IQR | 3.2769 ms / 0.1303 ms |
| batch medians | 2.6726, 2.6971, 2.6910, 2.6664 ms |
| drift | −0.2% |
| headroom to the bar | 2.3228 ms |

**The five medians: 2.8264 (adjudicated, the record) → 2.6928 → 2.6856 → 2.7363 → 2.6772.**

**The separation finding, recomputed with this run included, is UNCHANGED.** Recomputed exactly
over the recorded batch tables (all C(8,4) = 70 labelings), against the adjudicated batches
2.9190 / 2.8259 / 2.8213 / 2.7511:

| run | U | exact two-sided p | batch range | separates? |
|---|---:|---:|---|---|
| confirmation 2026-08-03 (2.6928) | 12 | 0.3429 | 2.6574–3.0324 (overlaps) | **no** |
| seal-time re-run 1 (2.6856) | 16 | 0.0286 | 2.6750–2.6920 (disjoint) | yes, completely |
| seal-time re-run 2 (2.7363) | 16 | 0.0286 | 2.7306–2.7458 (disjoint) | yes, completely |
| **seal-time re-run 3 (2.6772)** | **16** | **0.0286** | **2.6664–2.6971 (disjoint)** | **yes, completely** |

This is exactly what `docs/PRE_REGISTRATION.md` declares: the confirmation run does not separate
from the adjudicated one, and every seal-time run does, completely. U = 16 and p = 0.0286 are the
**extremes** available at n = 4 against 4 — no arrangement of four batch medians can separate more
strongly, and none can reach p < 0.0286 — so the fifth run cannot strengthen or weaken that
declaration, only fail to contradict it, which it does not. The declaration is sealed as written
and was **not** edited to accommodate this run.

What the fifth run adds: the difference from the adjudicated median is **+0.1492 ms (5.28%)** —
**0.75% of the 20 ms equivalence margin** and **0.51 of the adjudicated IQR (0.2898 ms)** — and,
like every re-run, it sits **below** the record, so the adjudicated **2.8264 ms remains the
conservative figure** and the direction of the drift continues to favour the lightweight framing
rather than this work's own hypothesis. The monotone-downward pattern still does not extend: the
five values run 2.8264 → 2.6928 → 2.6856 → 2.7363 → 2.6772, up once and down again. **Five runs
on one machine cannot distinguish machine-state variation from genuine drift, and no cause is
claimed.** Run once; not re-run for a better number.

### Seal-time re-run 4 — 2026-08-07, at the v0.7 sealing candidate `6dc66eb`

Re-run for the **v0.7** reseal (ADR 0044/0046), first and alone on an idle machine under the cp936
console codepage, before G-10 heated it. Not a re-adjudication: G-3's verdict is the 2026-08-02
adjudication, and this is the confirmation Part H requires on the commit being sealed.

| | |
|---|---|
| **median** | **2.7145 ms** — **PASS (≤ 5 ms)** |
| p95 / IQR | 3.3476 / 0.1337 ms |
| batch medians | 2.7290, 2.7134, 2.7111, 2.7107 ms |
| last-vs-first drift | −0.7% |
| headroom to the bar | 2.2855 ms |
| G-3.H1 / G-3.H2 | PASS (P-cores from `GetSystemCpuSetInformation`) / PASS (on AC) |

**The six medians: 2.8264 (adjudicated, the record) → 2.6928 → 2.6856 → 2.7363 → 2.6772 → 2.7145.**

**The separation finding, recomputed with this run included, is UNCHANGED.** Recomputed exactly
over the recorded batch tables (all C(8,4) = 70 labelings), against the adjudicated batches
2.9190 / 2.8259 / 2.8213 / 2.7511:

| run | U | exact two-sided p | batch range | separates? |
|---|---:|---:|---|---|
| confirmation 2026-08-03 (2.6928) | 12 | 0.3429 | 2.6574–3.0324 (overlaps) | **no** |
| seal-time re-run 1 (2.6856) | 16 | 0.0286 | 2.6750–2.6920 (disjoint) | yes, completely |
| seal-time re-run 2 (2.7363) | 16 | 0.0286 | 2.7306–2.7458 (disjoint) | yes, completely |
| seal-time re-run 3 (2.6772) | 16 | 0.0286 | 2.6664–2.6971 (disjoint) | yes, completely |
| **seal-time re-run 4 (2.7145)** | **16** | **0.0286** | **2.7107–2.7290 (disjoint)** | **yes, completely** |

Same declaration, same outcome: the confirmation run does not separate from the adjudicated one,
every seal-time run does, completely. U = 16 and p = 0.0286 remain the **extremes** available at
n = 4 against 4, so this run — like the three before it — **cannot strengthen or weaken the
declaration, only fail to contradict it**, which it does not. `docs/PRE_REGISTRATION.md` is not
edited.

What the sixth run adds: the difference from the adjudicated median is **+0.1119 ms (3.96%)** —
**0.56% of the 20 ms equivalence margin** and **0.39 of the adjudicated IQR (0.2898 ms)**. It sits
**below** the record like every re-run, so **2.8264 ms remains the conservative figure** and the
drift continues to run against this work's own hypothesis rather than toward it. The six values are
2.8264 → 2.6928 → 2.6856 → 2.7363 → 2.6772 → 2.7145: no monotone trend, up and down twice. **Six
runs on one machine still cannot distinguish machine-state variation from genuine drift, and no
cause is claimed.** Run once; not re-run for a better number.

**One thing this run measured that the previous four did not.** ADR 0046 replaced the authorizer's
inherited 1 ms wall-clock Datalog budget with an explicit 1 s one, and `decide` is what G-3 times.
The median moved by less than the spread between the existing re-runs (2.6772 … 2.7363 already
spans 0.0591 ms; this run's 2.7145 sits inside that band), so the change is **not visible in the
boundary-verification cost** — which is what one would expect from raising a limit that was never
reached on the happy path, and is recorded because "we changed the authorizer and the timing gate
is unchanged" is a claim that should rest on a measurement rather than on an argument.

### Seal-time re-run 5 — 2026-08-07, at the v0.8 sealing candidate `8ac7b21` — **THE SEPARATION FINDING CHANGED; THE SEAL STOPPED HERE**

Re-run for the **v0.8** reseal (task B2 PHASE 1), first and alone under the cp936 console codepage,
before any other gate ran. Not a re-adjudication: G-3's verdict is the 2026-08-02 adjudication.

| | |
|---|---|
| **median** | **2.9684 ms** — **PASS (≤ 5 ms)** |
| p95 / IQR | 3.9760 / **0.4413** ms |
| batch medians | 3.1689, 2.8338, 2.9024, 3.4035 ms |
| last-vs-first drift | **+7.4%** |
| headroom to the bar | 2.0316 ms |
| G-3.H1 / G-3.H2 | PASS (P-cores from `GetSystemCpuSetInformation`) / PASS (on AC) |

**The seven medians: 2.8264 (adjudicated, the record) → 2.6928 → 2.6856 → 2.7363 → 2.6772 →
2.7145 → 2.9684.** This is the **first** re-run to land **above** the adjudicated record
(+0.1420 ms, **+5.02%**); all five before it landed below it.

**The separation finding is CHANGED, and this run is why.** Recomputed exactly over the recorded
batch tables (all C(8,4) = 70 labelings), against the adjudicated batches 2.9190 / 2.8259 / 2.8213
/ 2.7511. The recomputation reproduces every previously published `(U, p)` pair before being
trusted on the new one:

| run | U | exact two-sided p | batch range | separates? |
|---|---:|---:|---|---|
| confirmation 2026-08-03 (2.6928) | 12 | 0.3429 | 2.6574–3.0324 (overlaps) | **no** |
| seal-time re-run 1 (2.6856) | 16 | 0.0286 | 2.6750–2.6920 (disjoint) | yes, completely |
| seal-time re-run 2 (2.7363) | 16 | 0.0286 | 2.7306–2.7458 (disjoint) | yes, completely |
| seal-time re-run 3 (2.6772) | 16 | 0.0286 | 2.6664–2.6971 (disjoint) | yes, completely |
| seal-time re-run 4 (2.7145) | 16 | 0.0286 | 2.7107–2.7290 (disjoint) | yes, completely |
| **seal-time re-run 5 (2.9684)** | **14** | **0.1143** | **2.8338–3.4035 (OVERLAPS)** | **NO** |

The declaration carried since the first re-run — *"the confirmation run does not separate from the
adjudicated one; every seal-time re-run does, completely"* — **is no longer true as written.** Its
first clause survives; its second does not. `docs/PRE_REGISTRATION.md` is **not** edited: changing
a pre-registered document because a later measurement disagreed with it is the thing
pre-registration exists to prevent. The disagreement is recorded here instead, and what to do about
it is the Commander's.

**What this run does NOT license.** It is a single run. U = 14 with p = 0.1143 is *weaker* evidence
of a difference than the four disjoint runs, not evidence of *no* difference; and the gate verdict
is untouched — 2.9684 ms passes the ADR 0025 threshold of 5 ms with 1.68× headroom, and every
mandatory limb passed. **G-3 is still PASS.** What changed is the auxiliary claim about whether
seal-time runs separate from the adjudicated run, never the gate.

**Not re-run.** The rule this report has applied since the first re-run is *run once, not re-run
for a better number*, and it binds hardest when the number is unwelcome. One run was taken and it
is the one recorded.

**The code is not the cause, and that is measured rather than argued.** Between the v0.7 seal
(`17e11c9`) and this candidate (`8ac7b21`) exactly three covered files changed —
`src/harness/campaign.py`, `src/harness/runner.py`, `src/harness/latency_collector.py`. G-3 times
`B3Arm.decide` alone; `src/sut/baselines/b3.py`, `src/sut/baselines/base.py`,
`src/sut/capability/authority.py` and `src/harness/authorizer/allowed.py` all carry **byte-identical
git blobs** at the two commits. `campaign.py` and `latency_collector.py` are not imported by the
spike at all, and `runner.py`'s change is purely additive — a new `TimingSeams.durations_ms()` that
nothing on the timed path calls, plus a docstring. Nothing inside the timed span moved.

**What the run's own shape says.** The IQR is **0.4413 ms against 0.1337 ms** last time — 3.3×
wider — the drift is **+7.4%** where the previous five ran between −5.8% and −0.2%, and the batch
medians are not a monotone thermal ramp (the *lowest*, 2.8338, is batch 2; the *highest*, 3.4035,
is batch 4). A wider spread with an erratic batch order is the signature of contention rather than
of a slower mechanism. Ambient load was sampled **before** the run and not during it — 4.85
CPU-seconds over 8 s across 20 logical processors, roughly 3% of capacity, the largest consumers a
browser and an editor which, like the pinned spike, prefer the P-cores. That is evidence, not a
cause: **no cause is established, and none is claimed.**

**Sighting C is not thereby explained either.** This is a spread within a 1,000-pair timing run,
not the per-operation stall whose appearance would make Sighting C a measurement problem; the raw
per-pair values are not persisted by the spike, so this run cannot settle that question in
either direction.

### Seal-time re-run 6 — 2026-08-07, at the v0.8 sealing candidate `c9d63ee` — the EIGHTH median

Re-run for the **v0.8** reseal (task B2 STEP 3), first and alone under the cp936 console codepage,
before any other gate. Not a re-adjudication. Taken **after** the declaration in
`docs/PRE_REGISTRATION.md` was amended (2026-08-07) and under the Commander's revised stopping
condition: **stop only if this median falls outside the observed band 2.6772–2.9684 ms or fails the
5 ms threshold.** It does neither.

| | |
|---|---|
| **median** | **2.7527 ms** — **PASS (≤ 5 ms)** |
| p95 / IQR | 3.1683 / **0.1161** ms |
| batch medians | 2.7574, 2.7512, 2.7571, 2.7475 ms |
| last-vs-first drift | **−0.4%** |
| headroom to the bar | 2.2473 ms |
| G-3.H1 / G-3.H2 | PASS (P-cores from `GetSystemCpuSetInformation`) / PASS (on AC) |

**The eight medians: 2.8264 (adjudicated, the record) → 2.6928 → 2.6856 → 2.7363 → 2.6772 →
2.7145 → 2.9684 → 2.7527.** The eighth sits **inside** the band the seventh widened, so the span
is **unchanged at 2.6772–2.9684 ms (0.2912 ms, 1.46% of the 20 ms margin)** and the adjudicated
2.8264 still sits inside it. **No stopping condition is met.**

**The run's shape returned to the earlier pattern, which is itself informative.** IQR **0.1161 ms**
against re-run 5's **0.4413 ms** — back to the 0.11–0.14 band of re-runs 1–4 — and drift **−0.4%**
against re-run 5's **+7.4%**, with the batch medians tight (2.7475–2.7574, a spread of 0.0099 ms).
Re-run 5 was the wide, erratic one and re-run 6 is not; **no cause is claimed for either**, and the
two are recorded side by side rather than averaged.

**Recomputed over all eight runs** (exact Mann-Whitney, all C(8,4) = 70 labelings per pair, from the
recorded batch tables): **18 of the 28 pairwise comparisons separate completely** at U = 16,
p = 0.0286, and 10 do not; **excluding the adjudicated run, 14 of 21 separate.** Re-run 6 separates
completely from re-runs 1, 2, 3, 4 and 5, and does **not** separate from the adjudicated run.

**The sharpest illustration the record now contains.** Re-run 2 (median 2.7363 ms) and re-run 6
(median **2.7527 ms**) differ by **0.0164 ms — six tenths of one percent** — and the test reports
**complete separation, U = 16, p = 0.0286**, the extreme attainable value. Two runs sixteen
microseconds apart cannot meaningfully be said to differ, and `src/sut/baselines/b3.py`, which owns
the `decide` call that is the only thing G-3 times, carries the **byte-identical blob `03ec47be`**
at both commits. This is the amended declaration's point made as plainly as the data can make it:
**at n = 4 vs 4 the statistic reaches its extreme whenever four tightly-clustered batch medians sit
above four others, so "separates completely" here reports the tightness of each run, not a
difference between them.**

**The apparatus changed between re-run 5 and re-run 6, and not on the timed path.** `c9d63ee`
carries the D-007 fix to `src/harness/measurement_platform.py` (ADR `000C`) and the amended
`docs/PRE_REGISTRATION.md`. Neither is imported by the timed span: the platform reader runs once at
start-up to pin cores and confirm AC, and `b3.py` is unchanged.
