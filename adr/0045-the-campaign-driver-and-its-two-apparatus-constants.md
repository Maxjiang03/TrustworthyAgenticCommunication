# 0045 — The campaign driver, and the two apparatus constants it needs

## Context

Part H step 7 says *"Execute the frozen campaign **once**"* and the repository contained **no
command that does it**. `run_campaign` is a fourteen-parameter library function whose only callers
were tests and one `tools/` script, both pilot-only; nothing wrote to `results/raw/`; and
`make reproduce` was an `echo`. The audit that produced ADR 0044 found this, and it is the reason
step 7 had never been attempted rather than attempted and failed.

Building the driver forces two values to be fixed. Both are **apparatus constants chosen for
feasibility**, not measurements and not `frozen_parameters` rows — this ADR exists so that
distinction is recorded before the run rather than argued after it.

### Why the driver cannot be one call

Three properties of the sealed corpus make "the campaign" more than one `run_campaign` invocation,
and none of them is a choice made here:

1. **`check_configuration_families` refuses** a run containing F4/F5 with `monitor_attached=None`.
   §E.4's `A†` — *admitted **absent** the shared monitor* — is only expressible if the same
   scenarios run under both configurations, so the F4/F5 families need **two** passes.
2. **The corpus declares two distinct task grants.** `runner.task_grant()` refuses without a
   scenario id when a corpus carries more than one chain, so the F1/F2/F3 chain and the F4/F5 chain
   need **separate `ASProcess` instances**: an AS is provisioned for one chain's `C_0 = U_task`.
3. **`B2ExchangeTaskArm.provision` refuses** a token whose authority is not the run's `U_task`, so a
   single shared AS document cannot serve both chains even if the AS allowed it.

So one campaign is **three `run_campaign` calls across two AS processes**, and that is a property of
the sealed corpus, not a decision. What *is* decided here is that they compose into ONE run record
with one manifest of cells, so "once" is auditable as one artifact rather than three that could be
selectively reported.

## Decision

`[DESIGN]` **`src/harness/campaign_driver.py` is the Part H step 7 entry point**, and
`make reproduce` and `python -m src.harness.campaign_driver` are the two names it answers to. It
is manifest-**covered**, deliberately: the artifact that produces the sealed result must itself be
sealed, or the result has a producer nobody hashed.

### Constant 1 — `campaign_token_lifetime_seconds = 3600`

The AS mints Phase-1 tokens **once at start-up** and defaults them to **300 s**
(`src/sut/oauth_as/config.py`). A pass is 13 scenarios × 9 arms × 2 monitor configurations plus a
ledger-backed run, and any cell judged after a token's `exp` is recorded **`unscorable`** by
`campaign.clock_refusal`. That is fail-closed and visible — the cell is never scored `B`, never a
`false_block` — but it would report an **apparatus limit as a measurement gap**, and on the single
allowed run there is no second chance to notice.

**3600 s is chosen as an order of magnitude above the observed pass, not as a tight fit.** The
adjudicated full test suite runs in ~45 s and the heaviest recorded excursion on this platform is
ADR 0038's Sighting C at 2682 s, cause undetermined. An hour therefore covers the normal pass by a
factor of ~50 and still covers the worst excursion ever observed here. It is **not** unbounded:
a token that never expires would make `clock_refusal` untestable and would quietly remove a
fail-closed guard the campaign depends on.

**What this does NOT change.** `Δ` (`frozen_parameters` row 3, 60 s) is untouched: it governs the
`jti` replay cache, the DPoP `iat` window and INV freshness, all of which are per-invocation and
none of which is this. The OAuth token lifetime has never been a frozen row, appears in no
hypothesis, and no predicate reads it. Making it longer cannot make any arm block or admit
differently — an unexpired token is checked by exactly the same conjuncts as a token with 250 s
left.

### Constant 2 — `wrong_audience` = `rs-other.aasc.local`

`F3 audience-mismatch` needs a token *"minted for another resource server"*;
`credential_faults._restage_token` **raises** rather than present the correct token, and nothing in
the repository minted one — so that cell aborted the run mid-matrix.

The second RS is registered in the AS document's `resource_servers` and the token is minted with
**that RS's own RAR objects**, so it is genuinely valid — correctly signed, unexpired, properly
scoped — and simply *for somewhere else*. That is §D.2's captured-credential adversary. A malformed
or empty-authority token would be refused by a different conjunct and the cell would measure
`invalid_credential` a second time instead of the audience check — trap 1, which this corpus has
sprung five times already.

`golden_thread_as_document` **refuses** a `wrong_audience` equal to the run's own audience, because
presenting the correct token would score as the arm admitting an attack that was never staged.

### Output: write-once, and refusing rather than overwriting

`results/raw/` is write-once (§J.4 item 14). The driver **refuses to start** if its output file
exists — it does not append, rotate, or timestamp a second copy — because the reason results are
write-once is that a second run must be a visible decision, not a silent overwrite of the "once".
An abort (Part H's abort rule) discards the partial file explicitly and by name.

## Status

proposed — 2026-08-07. Numbered 0045 by the Commander, following 0044. Part of the v0.7 candidate;
Part H step 7 remains forbidden until v0.7 is sealed.

## Consequences

- **Neither constant can move a verdict**, and both are stated before the run so that claim is
  checkable rather than asserted: the token lifetime is read by no predicate and no hypothesis, and
  the wrong-audience token is presented to exactly one cell, by the injector, under a fault the
  sealed record declares.
- **The three-call structure is recorded as a property of the corpus**, so a reader asking "why is
  the single run three invocations?" finds the answer in the design rather than in a script.
- **A second campaign run cannot happen by accident.** The driver refuses an existing output file,
  and the refusal names Part H's "once".
- **`tools/clock_fix/snapshot_cells.py` is now the second assembly of a campaign**, and it is
  pilot-only and manifest-excluded. It is left alone: it is a completed task's evidence, and
  editing it to share code with the sealed driver would put an excluded file on the sealed path.
