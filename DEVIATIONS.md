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

## D-006 — 2026-08-07 — RQ4's latency pass. The half of step 7 that had not run.

**Not a departure from the plan; a departure from what was REPORTED.** The step 7 completion report
(D-005) described the security half and said nothing about RQ4 having no data. This entry and
**ADR 000B** record that, in the terms this project uses for it: *an absence that reads as
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
