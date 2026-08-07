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

**Status: no campaign has been run.** Part H step 7's "once" is unspent. There is therefore no
abort, no re-run and no post-seal infrastructure fix to report. The entries below are pre-campaign
and are recorded because each one changes what a reader should expect from the sealed record.

---

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
