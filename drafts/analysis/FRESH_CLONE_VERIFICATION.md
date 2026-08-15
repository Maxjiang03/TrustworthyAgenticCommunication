# Fresh-clone independent recomputation pass

**Run:** 2026-08-16. **Subject commit:** `a4a3f60`.
**Scope:** FIGURE_PLAN.md §0.8, extended to cover the row-1 decision (both runs).
**Method:** a clone taken from `origin` into a scratch directory, with no file
copied in from the working repository except the two verification scripts, which
import nothing from `tools/figures/` and nothing from `analysis/` except where a
sealed function is itself the specification being checked.

**Result: PASS on every recomputed quantity.** Two findings and one known
deferral are recorded at the end; neither finding is a wrong number.

---

## 0. The clone, and the trap it would have sprung

    git -c core.autocrlf=false clone <origin> fc

The `-c core.autocrlf=false` is **load-bearing, not decoration.** The manifest's
own `hash_definition` says so — *"SHA-256 over the committed git blob bytes (LF
as stored). A fresh clone with `core.autocrlf=false` reproduces every hash by
reading the checked-out file bytes directly."* This machine has
`core.autocrlf = true` globally and the repository carries no `.gitattributes`,
so a default clone checks out CRLF and the working-tree bytes no longer hash to
the manifest.

This was found by walking into it. Hashing working-tree bytes in the main
repository reported **24 of 167 covered files mismatched** — an apparently broken
seal. Hashing the git blob bytes, which is what the manifest specifies, reported
**0 of 167**. In the correctly-cloned copy the working tree reproduces all 167
hashes directly.

**Any future verification pass must clone with `core.autocrlf=false`,** or it
will report a seal breach that does not exist.

## 1. Seal integrity

| check | result |
|---|---|
| `verify_manifest.py` at the pinned commit `ffa216e` | **PASS** — 167/167 covered files re-hashed from plain clone bytes |
| exhaustiveness | 418 tracked = 167 covered + 251 excluded |
| covered files changed since the seal | **0** (26 paths changed, all excluded) |
| seal commits signed | all five — v0.5 `805425e`, v0.6 `cdf185d`, v0.7 `17e11c9`, v0.8 builder `ffa216e`, v0.8 `52692d4` — `%G?` = `G` |

The manifest is committed *after* the commit it attests to, so it must be
supplied to the verifier from outside the checkout. That is its designed use, not
a workaround.

## 2. Independent recomputation of the security results

`independent_recompute.py` reads only `results/raw/campaign-confirmatory.json`
and `results/tables/results-confirmatory.json` and derives each quantity from the
pre-registered rules as stated in prose.

The one genuinely hard part is the **row-label → corpus-token mapping**: the
expected matrix labels rows in prose (`F1-root (R ⊄ U_task)`) while the corpus
uses structured tokens (`F1:root`). The sealed `analysis/matrix.py` holds a
hand-written table for this, and the presentation layer imports it under ADR
0048's first named exception. Importing it here would have made the check
circular, so the mapping was **reconstructed from the two JSONs alone** — group
both sides by family; where a family has exactly one predicted row and one attack
subcase they correspond with no string comparison needed; otherwise match on
shared words with both sides consumed so no token can be claimed twice. The
reconstruction is injective and recovers all ten pairs.

| quantity | recomputed | sealed record |
|---|---|---|
| cells run → scored + unscorable | 153 → 143 + 10 | ✓ |
| unscorable causes | all 10 `"NA per the sealed record"` | ✓ |
| §E.4 entries | 90 = 10 predicted rows × 9 arms | ✓ |
| **entries agreed** | **80** | **80** ✓ |
| **entries disagreed** | **0** | **0** ✓ |
| entries NA (not comparable) | 10 | 10 ✓ |
| entries unresolved | 0 | — |
| rows not populated / deferred | 3 / 1 | ✓ |
| display partition of the 143 cells | 9 + 36 + 8 + 90 | ✓ |
| per-arm scored counts | 15,15,15,15,16,17,16,17,17 | ✓ |
| `false_block` cells | 4 | ✓ |
| B3 vs B3⁺ comparable pairs / differing | 17 / **0** | ✓ |
| dagger census | 8 entries across 2 rows | ✓ |
| `class_macro`, all 5 families × 6 quantities | all | ✓ |

The agreement figure was derived by applying the footnote-dagger rule
independently: a daggered expectation is scored against the monitor-off cell
only, an undaggered F4/F5 expectation must hold under **both** configurations.
Deriving 80/0 that way, from a mapping reconstructed rather than imported, is the
substance of this pass — **it is evidence rather than tautology.**

## 3. Diff against what the artefacts actually print

Every artefact was rebuilt in the clone and its `RENDER` stream captured, then
compared to the independent `CHECK` stream over an explicitly declared
correspondence table, so the comparison cannot quietly shrink to the subset that
happens to pass.

    agree=91  mismatch=0  gap=0   (of 91 declared correspondences)

All ten scripts ran without error in the clone.

## 4. The row-1 decision

Reproduced by calling the sealed functions directly rather than through
`tools/run_row1_decision.py`, so the composition root is not verifying itself.

| | recomputed | committed (run 2) |
|---|---|---|
| verdict | `stands` | `stands` |
| point estimate | 6.44175 | 6.44175 |
| CI | [6.37215, 6.46405] | identical |
| n per arm | 210 | 210 |
| treatment median | 6.44325 | 6.44325 |

Both runs' artefacts were also checked against the decision rule itself
(CI upper bound < margin) and against the plan block: the warm-up arithmetic
closes exactly — 225 − 3 × 5 = 210 = `kept_after_warmup_per_configuration`.

## 5. Wording rules

| rule | result |
|---|---|
| ADR 0037 banned stem in authored artefact text | **none** — the only occurrences are TAB-10's own fail-closed guard constant (`BANNED_STEM = "generali"`) and its explanatory comment |
| F3 `2/5` travels with every F3-bearing artefact | present on FIG-1, FIG-3, TAB-4, TAB-9, TAB-10 |
| F4 qualification on every F4-bearing artefact | verbatim on TAB-1, TAB-4, TAB-9, TAB-10 — see finding F1 |
| unqualified "80 of 90" | none; TAB-10 raises on it and TAB-2 renders it only inside its explanation |

## 6. Findings

**F1 — FIG-1 paraphrases the F4 qualification where §E requires it verbatim.**
FIG-1's F4 band header reads *"F4 independence weaker than F1/F2/F3/F5
(pre-registered qualification)"*. The sealed wording is *"F4 agreement between
the two corpora MUST NOT be reported as replication of the same strength as F1,
F2, F3 or F5…"*, which TAB-1, TAB-4, TAB-9 and TAB-10 all carry verbatim.
FIGURE_PLAN §E requires every F4-bearing artefact to carry it verbatim. The
substance is present and no number is affected; the form departs from the plan.
Not fixed here — figure content is deferred to the writing directory.

**F2 — the `.ots` attestations were not verified.** All five files are present
(`manifest_v0.8` and the four superseded), but no OpenTimestamps client is
available in this environment, so the anchoring is confirmed to exist and is
**not** confirmed to attest. This remains open.

**Known deferral — placement.** `acceptance_check` FAILs: 14 of 17 rendered
artefacts do not fit the dissertation text block (5.564 × 9.693 in) in either
orientation. This is the recorded, Commander-deferred layout defect
(FIGURE_PLAN §0.10) and is not a numerical defect. All artefacts are vector, and
no script sets type below 8 pt.

## 7. What this pass does not cover

- The `.ots` attestations (F2 above).
- Visual inspection of the rendered PNGs. Wording was checked against the source
  strings and the `RENDER` stream, not by reading the images. The collision
  defect fixed in `9fb0de0` is the standing proof that numeric checks alone do
  not certify a render.
- The security corpus itself. This pass verifies that the reported numbers follow
  from the committed campaign record; it cannot verify that the campaign record
  reflects what the apparatus did, which is what the seal and the gates are for.
