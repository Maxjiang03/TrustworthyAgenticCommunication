# 0044 — The pre-campaign audit, and the v0.7 reseal it obliges

## Context

**The v0.6 seal (`cdf185d`, manifest over `b5afa10`) is complete and sound as a seal, and the
apparatus it seals cannot execute Part H step 7.** This was found by auditing the sealed tree
against the question *"is the confirmatory campaign runnable, and would it measure what the
pre-registration says it measures?"* before running it, rather than by running it and reading a
stack trace. Every finding below is in a **manifest-covered** file, so the repair is a Part H
unseal/reseal by construction, not by choice.

**The shape of the failure is the same one ADR 0043 records, one stage further down the pipe.**
ADR 0043 found that the sealed generator could not *produce* the confirmatory corpus. Task A1
parameterised the generator and produced it — and stopped there. Nothing extended the **consumers**:
the runner still reads sealed truth from a pilot-only directory, and the sealed analysis code still
names a pilot scenario id. A corpus that can be generated but not read, and not analysed, is not an
input to an experiment.

### What the audit found, and what each finding would have done to the results

The five that stop the run outright — each fails closed, none would have produced a quiet wrong
number:

1. **The confirmatory corpus has no sealed-truth read path.** `src/harness/sealed_truth.py`'s
   `SEALED_DIRS` maps only `golden_thread` → `fixtures/pilot/golden_thread/sealed`, and
   `src/harness/runner.py` calls `load_sealed(scenario_id)` with no corpus argument and no way to
   pass one. `SealedTruthAccessError` is not a `RunnerError`, so `campaign.run_campaign`'s handler
   does not catch it: **the campaign dies on the first cell.** A second consequence is quieter and
   worse — `campaign.py`'s `_sealed_document` reads the corpus JSON directly, bypassing
   `_refuse_sut_frames()`, so the runtime half of the sealed-truth wall (red line 5) never covered
   the confirmatory corpus at all.
2. **No entry point exists.** `run_campaign` is a 14-parameter library function whose only callers
   are tests and one `tools/` script, both pilot-only. Nothing in the repository defines the command
   that Part H step 7 names.
3. **Nothing writes results.** No code writes `results/raw|tables|figures`; the write-once
   discipline of §J.4 item 14 has no implementation; `make reproduce` is an `echo`.
4. **`wrong_audience_token` has no producer.** `cf-f3-audience-mismatch` carries the
   `audience_mismatch` fault, whose handler in `src/harness/credential_faults.py` raises rather than
   present the correct token — correctly, since presenting it would score as an arm admitting an
   attack that was never staged. But nothing mints the second-audience token, so the cell aborts
   the run mid-matrix.
5. **Phase-1 access tokens live 300 s** and are minted once at AS start-up, while a full pass is
   13 scenarios × 9 arms × 2 monitor configurations. Cells past the 300 s mark are recorded
   `unscorable` by `clock_refusal` — visible and fail-closed, but the single allowed run would
   return a matrix whose tail is empty for an apparatus reason.

The two that would have produced **wrong numbers**, which is why this ADR exists rather than a
bug-fix commit:

6. **Every `DeclassificationArtifact` fails oracle verification.** `schema.py` declares
   `signature: bytes`; `policy/label_artifacts.py` mints it as a base64url **str**; pydantic encodes
   that text to UTF-8 when it enters `ObservedRequest`; `oracle/artifacts.py` sees `isinstance(...,
   bytes)` and hands 86 ASCII bytes to `Ed25519PublicKey.verify` as a 64-byte signature. It can
   never verify. `cf-f4-declassified` is a **benign control carrying a valid declassification**, so
   every arm that correctly admits it — all nine, monitored and unmonitored — would have been
   scored `admission_breach = True`, including `B3` and `B3⁺`. In the other direction `false_block`
   becomes unreachable for that scenario, silently exonerating exactly the G-15 finding
   `predicates.false_block`'s own docstring says it must not exempt. The SUT-side monitor is
   unaffected (it reads the raw dict), so this is an **oracle** defect: the independent adjudicator
   was the thing that was wrong.
7. **`realized_harm_F4` is structurally always `False`.** `runner.py` constructs `LedgerEffector`
   and `install_ingress_recorder` without `labels=`, so both fall back to `label_directory.EMPTY`,
   every `EffectEvent` carries `data_labels_touched = []`, and the predicate's loop body never
   executes. `cf-f4-sensitive-egress` admitted by `B0`/`B1` sends the sensitive payload and is
   scored **no harm** — verbatim the outcome ADR 0030 and `label_directory.py`'s own docstring say
   must never happen. Nothing in `src/` has ever constructed a `LabelDirectory`; only a test does.

**Why the suite was green through all of this.** `tests/test_oracle_predicates.py` passes
declassification artifacts as plain dicts, which never cross the pydantic boundary that corrupts
them; no test builds a `security.Verdict` or a `latency.Sample` from a real `CellVerdict` or
`TimingSeams`; and no analysis test uses a `cf-*` scenario id, so the hardcoded pilot id compares
only against literals equal to itself. **The tests were correct about the units and silent about
the seams**, which is the failure mode a unit suite has whenever the wiring is the defect. The
regression tests this ADR's implementation adds are therefore seam tests: each one is watched
failing against the unrepaired code before it is kept.

### The analysis layer cannot consume a campaign result

`analysis/` is manifest-covered because §J.3 item 12 requires the analysis frozen with the rest, so
results cannot be massaged post hoc. What is frozen does not connect to what the campaign emits:
`CellVerdict` has no `template` field though `security.Verdict` requires one; `latency.Sample`'s
`phase`/`batch`/`repetition` have no producer anywhere in `src/` (the timing seams deliberately
record span **names**, never durations); `analysis/latency.py` hardcodes `REFUSAL_PATH_SCENARIO =
"gt-f1-chain-tamper"`, so on confirmatory samples ADR 0026's by-name exclusion **silently stops
applying** and the refusal path is pooled into the benign per-arm mean — the precise averaging of a
network refusal with local cryptography that the rule exists to forbid, failing in the direction
that flatters this work's own hypothesis.

And three pre-registered commitments have **no representation in code at all**: the
NOT-POPULATED-BY-THE-CAMPAIGN state the F3 declaration requires for three of five subcases (the
default `class_macro` behaviour is the per-family count that declaration forbids); the F4
weaker-independence qualification that "travels with every F4 result"; and H4a/H4b's falsification
conditions, which no code evaluates.

**This is the reason the repair cannot wait until after the run.** Writing the loader, the matrix
assembler, the NOT-POPULATED renderer and the hypothesis evaluator after step 7 would produce
analysis code that is provably post-hoc, against a seal whose entire purpose is to make that
impossible.

## Decision

`[DESIGN]` **Repair the apparatus, then reseal as v0.7. The v0.6 seal is marked superseded and
kept, exactly as v0.5 was; no result is carried over, because none was produced.** Part H's
unseal/reseal rule is followed as written: bump the candidate version, re-hash every artifact,
regenerate the manifest, record the reason, and re-run the platform-bound gates on the commit being
sealed.

Three constraints govern the repair, and they are the reason this is an ADR rather than a
changelog:

- **No frozen row moves, and no scenario changes.** `Ω`, `Γ`, the identity registry, the label
  policy, the eleven `frozen_parameters` rows, `§E.4`'s expected matrix and both corpora are
  untouched. The defects are in the apparatus that reads them, never in what was frozen. The one
  new constant this work fixes — the AS token lifetime for a campaign pass — is an **apparatus
  constant chosen for feasibility**, recorded in ADR 0045, and is not a `frozen_parameters` row.
- **Every repair carries a seam test that was watched failing first.** A repair whose test passes
  against the unrepaired code has tested nothing; the audit exists because that happened at the
  unit/seam boundary once already.
- **The pre-registration is amended only where it is factually stale** (it still says nothing is
  sealed and `fixtures/confirmatory/` is empty). **No prediction, predicate, threshold or
  declaration is touched**, and the two declarations pre-registered before the v0.6 reseal stand
  verbatim.

## Status

proposed — 2026-08-07. Numbered 0044 by the Commander (0043 was the previous number issued;
the placeholder-letter convention of ADR 0042/0043 is not used here because the number was issued
before the file was written). **The reseal is owed:** the v0.7 candidate is not sealed by this ADR,
and Part H step 7 remains forbidden until it is.

## Consequences

- **Part H step 7 stays blocked** until the v0.7 seal is complete. The audit's finding that the
  campaign is unrunnable is the reason no run has been attempted; there is no partial result to
  discard, and the "once" of step 7 is unspent.
- **The v0.6 seal is not a failure and is not deleted.** It sealed the tree it described,
  correctly, and its OTS anchor remains valid over those exact bytes. What it proves is that the
  corpus existed and was hashed on 2026-08-07 before any of this repair was written — which is
  worth more to the record than a tidy `seal/` directory. It moves to `seal/superseded/` alongside
  v0.5 when v0.7 is built.
- **CI was red from `ca360ae` through `cdf185d` and nobody noticed** — across two sealing commits.
  The cause is not in the apparatus: `actions/checkout@v5` clones at depth 1, and three provenance
  tests in `tests/test_pre_registration.py` walk real history (`git log -- <path>`,
  `git merge-base --is-ancestor`). Reproduced locally with a depth-1 clone: **3 failed, 1405
  passed**, the three being exactly those tests. Fixed with `fetch-depth: 0` in
  `.github/workflows/ci.yml` (a manifest-excluded file; no reseal). Recorded here because "the
  gates were green and CI was red for a week" is a fact about this project's assurance, not a
  footnote: the local suite was the only thing being read.
- **`docs/row7_snapshot/` closes ADR 0042's outstanding sourcing obligation** — the two Artificial
  Analysis pages are snapshotted, tracked and covered by the v0.6 manifest. `docs/frozen_parameters.md`
  and ADR 0042 still describe it as owed; that prose is stale and is corrected in the v0.7 candidate.
- **Superseded by this ADR's own honesty requirement:** if any repair below turns out to change a
  measurement rather than enable one, it must be reported as a finding in the results chapter, not
  absorbed into the apparatus. Two of the seven (the declassification signature and the label
  directory) would have changed published numbers, and the dissertation says so.
