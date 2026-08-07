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
