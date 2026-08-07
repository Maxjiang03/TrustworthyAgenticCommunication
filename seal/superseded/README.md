# Superseded seal manifests — kept, never deleted

Four manifests live here. None is the seal; the seal is `../manifest_v0.8.json`. All are kept
because each `.ots` proof anchors **those exact manifest bytes**, and a superseded record that
vanishes is indistinguishable from one that never existed.

**Read the dates.** Each entry below is a statement about the supersession it describes, at the
time it happened. In particular, both entries under v0.6 and v0.5 say *"no result is superseded,
because Part H step 7 has never run."* **That was true when written and is no longer true of the
project**: step 7 ran once on 2026-08-07, under **v0.7**. It remains true of what those entries
claim — neither v0.5 nor v0.6 ever produced a result — and the sentences are left exactly as
written rather than retrofitted, because a superseded record that gets edited to match later facts
is no longer a record.

## `manifest_v0.7.json` + `.ots` — the v0.7 seal, superseded 2026-08-07 by v0.8

Built over commit `9b75ba1` and anchored; the sealing commit was `17e11c9`.

**v0.7 IS THE SEAL UNDER WHICH THE EXPERIMENT WAS RUN, and superseding it does not disturb that.**
Part H step 7 executed **once**, on 2026-08-07, at `17e11c9`: 143 scored cells, 10 unscorable, no
abort and no re-run (DEVIATIONS D-005). The raw trace is archived at
`results/raw/campaign-confirmatory.json`. **No result is superseded by v0.8** — v0.7 is the
manifest the confirmatory campaign must be checked against, its anchor still covers those exact
bytes, and it is the reason this file must never be deleted.

**Why it was superseded — three reasons, none of them a defect that touched a campaign result:**

- **RQ4's instrument was outside the seal.** `src/harness/latency_collector.py` did not exist at
  v0.7, so the latency pass that produced `results/raw/latency-pilot.json` — the only data RQ4 and
  frozen row 1's `lightweight_claim` have — ran on an **unsealed collector** (DEVIATIONS D-006,
  ADR 0047). v0.8 covers it. The apparatus behind a reported number belongs inside the seal.
- **The sealed platform reader crashed under a PowerShell parent process**, so `frozen_parameters`
  row 9 could not be read and G-3 could not be adjudicated from that parent at all — a
  reproducibility defect in a covered file (D-007, ADR `000C`). It failed **closed**, so no row 9
  value ever sealed is in doubt.
- **The G-3 drift disclosure in `docs/PRE_REGISTRATION.md` had become false.** A seventh median
  (2.9684 ms) was the first to land above the adjudicated 2.8264, which falsified the recorded
  claims that the medians were *"monotone downward"* and that the drift *"favours the lightweight
  framing"*. It was amended **by dated addition with the original wording preserved verbatim**. A
  **disclosure**, never a hypothesis: no hypothesis, decision rule or gate criterion was touched,
  and the adjudicated figure is unchanged.

**This is the first supersession that is not a repair of a broken seal.** v0.5 and v0.6 were
superseded because the trees they sealed could not do what the design said; v0.7 could, and did.

## `manifest_v0.6.json` + `.ots` — the v0.6 seal, superseded 2026-08-07 by v0.7

Built over commit `b5afa10` and anchored; the sealing commit was `cdf185d`.

**Why it was superseded, stated plainly: v0.6 sealed a tree whose apparatus could not EXECUTE Part
H step 7, and which would, in two places, have measured wrongly.** Found by auditing the sealed
tree before running it rather than by publishing from it (ADR 0044):

- the confirmatory corpus had **no sealed-truth read path** — `SEALED_DIRS` mapped only the pilot
  directory, so the campaign died on its first cell;
- **no entry point existed** for step 7 at all, nothing wrote `results/raw/`, and the analysis
  could not read a campaign result even if one had been produced;
- the oracle **could never verify a `DeclassificationArtifact`** (a pydantic `bytes` coercion of a
  base64url string), so every arm correctly admitting the benign control `cf-f4-declassified` —
  `B3` and `B3⁺` included — would have been scored `admission_breach`;
- **`realized_harm_F4` was structurally always `False`**: the ingestion `LabelDirectory` was never
  constructed anywhere in `src/`, so a sensitive egress that really executed scored as no harm.

A third defect was found while validating the repairs and is recorded in **ADR 0046**: a Datalog
evaluation timeout was returned as a **denial**, and `Allowed()` runs the authorizer once per
element of `Ω`, so a busy machine could silently shrink an authority set — the quantity this study
measures.

**No result is superseded, because Part H step 7 has never run.** The "once" is unspent. v0.6 is
a correct seal over the tree it described, its OpenTimestamps anchor remains valid over those exact
bytes, and it proves the confirmatory corpus existed and was hashed on 2026-08-07 before any of
these repairs were written. That is why it stays.

## `manifest_v0.5.json` + `.ots` — the v0.5 seal, superseded 2026-08-06 by v0.6 (itself now superseded)

Built over commit `7872311` and anchored; the sealing commit was `805425e`.

**Why it was superseded, stated plainly: v0.5 was sealed with inputs from which no confirmatory
corpus was producible.** Part H step 3's own words say the seal covers *"the sealed inputs from
which the confirmatory corpus is deterministically produced"* — and it did not. The only corpus
generator in the repository was pilot-only in three hardcoded ways (output directory, seed and
task id, and a guard that refused to run while `fixtures/confirmatory/` held anything but a
README), so the only corpus those sealed bytes could produce was the pilot corpus, byte for byte.
Part H step 4 stopped there. The full finding is ADR 0043.

**This is not a failure of the seal — it is the seal working, and that is why the file stays.**
Four independent fail-closed layers each refused the obvious shortcut of relabelling the pilot
corpus as confirmatory: the generator's own empty-directory guard; Part H step 5's hash
disjointness; `check_run_mode`'s refusal of a confirmatory run reading from `fixtures/pilot/`; and
this manifest's own coverage of the generator, which made editing it visibly a **reseal** rather
than a fix. Nothing was quietly repaired. The record of that is worth more in the dissertation
than a tidy `seal/` directory.

What changed between v0.5 and v0.6, all of it visible in the git history between `805425e` and the
v0.6 sealing commit: the generator was parameterised so it can produce both corpora (the pilot
still regenerates **byte for byte**), `run_mode` was threaded through the runner, the confirmatory
corpus was generated, two declarations were pre-registered (F3's partial instantiation, F4's weaker
confirmatory independence), and ADR 0043 was written and numbered.

## `manifest_v0.5-20f68f5.json` + `.ots` — an intermediate v0.5 build, superseded within the day

Describes commit `20f68f5`. After it was built and anchored, commit `aeee0ea` changed
`docs/PRE_REGISTRATION.md`, which the manifest covers, so the v0.5 seal was rebuilt over the later
candidate before it was ever signed.
