# Superseded seal manifests — kept, never deleted

Two manifests live here. Neither is the seal; the seal is `../manifest_v0.6.json`. Both are kept
because each `.ots` proof anchors **those exact manifest bytes**, and a superseded record that
vanishes is indistinguishable from one that never existed.

## `manifest_v0.5.json` + `.ots` — the v0.5 seal, superseded 2026-08-06 by v0.6

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
