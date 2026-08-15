# 0048 — The presentation layer lives outside the seal

## Context

Part H step 7 has run and the results chapter needs figures. §J.3 item 12 freezes
*analysis* code in the seal ("Every table/figure regenerated from `results/raw/`
by one command … Freeze it in the seal so results cannot be massaged post hoc"),
and the v0.8 manifest covers `analysis/` by prefix (`seal/build_manifest.py:50`).
Placing new plotting scripts under `analysis/figures/` would therefore force a
v0.9 unseal/reseal for code that computes nothing. The Commander ruled on
2026-08-14 (FIGURE_PLAN.md Phase-2 approval, amendments D2 and R1–R3) that a
narrower category exists and where it lives.

## Decision

[DESIGN] **A presentation layer exists, and it lives in `tools/figures/`,
outside the seal manifest.** A script belongs to the presentation layer iff it is
a pure function of already-frozen artefacts (`results/raw/`, `results/tables/`)
that makes **no selection, exclusion, binning, or statistical decision of its
own**. Such a script is not analysis code under §J.3 item 12. Any script that
would need such a decision **is** analysis code: it is out of the presentation
layer's scope, is surfaced rather than written there, and — if written at all —
lands under `analysis/` and triggers the Part H unseal/reseal rule.

[VERIFIED] `results/tables/results-confirmatory.json` `expected_matrix` carries
per-cell expected values including `A†`, `NA`, and row states, so the expected
layer of every figure reads from the committed tables JSON, strictly downstream
of the sealed analysis.

[DESIGN] **Named exception, exhaustive:** the presentation layer imports from the
sealed `analysis/matrix.py` exactly `{ROW_SUBCASE_TOKENS, row_key,
CONTROL_PREFIX}` (`analysis/matrix.py:209-238`) — the §E.4 row-label ↔
corpus-subcase-token mapping parsed from the sealed pre-registration. It is a
pure label mapping; importing it avoids hand-authoring a second copy that could
drift. No other import from `analysis/` is permitted.

[DESIGN] **Second named exception — read-only verbatim-quotation guards.** A
presentation-layer script MAY read a frozen text file outside `results/`
(`docs/PRE_REGISTRATION.md`, `results/tables/results-confirmatory.md`, and the
two measurement drivers `src/harness/campaign_driver.py` /
`src/harness/latency_collector.py`) for exactly one purpose: to assert, at
build time, that a sentence it prints verbatim exists in the sealed source, or
that a provenance claim it prints ("unpinned") still holds in the code. Such a
read is fail-closed only — it can abort the build, and it can NEVER supply,
change, select, or bin a rendered value. (Used by FIG-3, TAB-1, TAB-5, TAB-0.)

[DESIGN] **Also under this class — the FIG-1 agreement reconstruction.** FIG-1
re-derives the §E.4 agreement entry-by-entry from the cells it draws (a daggered
entry against its monitor-off cell; an undaggered F4/F5 entry against BOTH
configuration cells) solely to assert that the count matches the sealed
`agreement` block; on mismatch it aborts. The reconstruction is read-only and
abort-only: every agreement number FIG-1 renders is read from the sealed block,
never from the reconstruction. Likewise, every per-row margin FIG-1 renders is
printed to stdout with its row identifier at every build (`RENDER FIG-1 |
margin.<row> = ...`) so the annotation is verifiable from output, not from
description.

[DESIGN] **The one non-JSON datum.** `campaign-confirmatory.json` carries no run
timestamp. TAB-0 prints the run date `2026-08-07` from the claims record
(`DEVIATIONS.md` D-005) and labels that provenance on the artefact and in its
stdout; the commit hash `17e11c9` and `git_dirty=False` are read from the JSON.

[DESIGN] **Regrouping rule (R2):** a presentation-layer script may partition or
regroup cells only when the partition (i) uses existing cell fields plus the
sealed expected values, (ii) is hard-coded as a named constant
(`AGREEMENT_PARTITION_RULE` in `tools/figures/_common.py`), (iii) is printed
verbatim to stdout at build time, and (iv) determines no number's inclusion or
exclusion — every group is printed and nothing is dropped.

[DESIGN] **Output and reproducibility:** figure outputs are written to
`results/figures/` and stay git-ignored; `.gitignore` is not edited. Every script
prints every number it renders to stdout for cross-check against the source
files, and a single `make figures` regenerates everything from `results/raw/` and
`results/tables/`. matplotlib only; deterministic; no network.

## Status

accepted — 2026-08-14

## Consequences

- No v0.9 reseal is needed for plotting code; the seal's "apparatus in, results
  out" asymmetry (`seal/build_manifest.py:144`) is preserved, and `tools/` keeps
  its existing excluded-with-reason classification in the manifest.
- The boundary is auditable per script: adding any selection, exclusion, binning,
  or statistical behaviour to a `tools/figures/` script violates this ADR and
  moves that file under §J.3 item 12 — reseal territory.
- The latency artefacts (FIG-4/5/6, TAB-6/7/8 of FIGURE_PLAN.md) remain gated by
  the separate D3 preconditions; this ADR authorises no latency computation.
