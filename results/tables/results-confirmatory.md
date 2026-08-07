# Campaign results — confirmatory

Corpus `confirmatory`, 13 scenarios, 143 scored cells, 10 unscorable.

## Expected matrix (§E.4) — state of every row

| Subcase | Family | State |
|---|---|---|
| F1-root (R ⊄ U_task) | F1 | predicted |
| F1-terminal (R ⊆ U_task, R ⊄ C_n) | F1 | predicted |
| F1-chain-tamper | F1 | predicted |
| F2 invalid_credential | F2 | predicted |
| F2 wrong_principal (frozen task→principal policy) | F2 | deferred — unscored (ADR 0028) |
| F2 wrong_holder_proof / wrong_dpop_key | F2 | predicted |
| F2 unauthenticated_caller | F2 | predicted |
| F3 dpop-stolen-AT-key-substitution (T-reuse) | F3 | predicted |
| F3 dpop-first-use-body-mutation (T-tool/T-args) | F3 | NOT POPULATED BY THE CAMPAIGN |
| F3 audience mismatch (OAuth neg. control) | F3 | predicted |
| F3 expired token (OAuth neg. control) | F3 | NOT POPULATED BY THE CAMPAIGN |
| F3 dpop-captured-proof-replay (bit-identical) | F3 | NOT POPULATED BY THE CAMPAIGN |
| F4 sensitive egress, no declassification | F4 | predicted |
| F5 high-risk action, no approval artifact | F5 | predicted |

### NOT POPULATED BY THE CAMPAIGN

These rows are predictions the campaign leaves untouched. They are **not** reported as passing, as confirmed, or as agreeing with the prediction, and they appear in no per-family count.

- **F3 dpop-first-use-body-mutation (T-tool/T-args)** — the campaign does not instantiate this subcase; its prediction is untouched by the measurement and is NOT reported as confirmed, as passing, or inside any per-family count (pre-registered §4)
- **F3 expired token (OAuth neg. control)** — the campaign does not instantiate this subcase; its prediction is untouched by the measurement and is NOT reported as confirmed, as passing, or inside any per-family count (pre-registered §4)
- **F3 dpop-captured-proof-replay (bit-identical)** — the campaign does not instantiate this subcase; its prediction is untouched by the measurement and is NOT reported as confirmed, as passing, or inside any per-family count (pre-registered §4)

## Per-family outcomes (class-macro)

### F1 — coverage 3/3 subcases

| Quantity | Count | Total | Rate |
|---|--:|--:|--:|
| admission_breach | 8 | 32 | 0.250 |
| false_block | 0 | 32 | 0.000 |
| log_integrity_failure | 0 | 32 | 0.000 |
| observed_forwarded | 17 | 32 | 0.531 |
| realized_harm | 8 | 32 | 0.250 |
| reference_allow | 9 | 32 | 0.281 |

### F2 — coverage 3/3 subcases

| Quantity | Count | Total | Rate |
|---|--:|--:|--:|
| admission_breach | 2 | 21 | 0.095 |
| false_block | 0 | 21 | 0.000 |
| log_integrity_failure | 0 | 21 | 0.000 |
| observed_forwarded | 2 | 21 | 0.095 |
| realized_harm | 2 | 21 | 0.095 |
| reference_allow | 0 | 21 | 0.000 |

### F3 — coverage 2/5 subcases
> F3 is instantiated in part: 2 of 5 subcases. This fraction travels with every number in this row (pre-registered §4).

| Quantity | Count | Total | Rate |
|---|--:|--:|--:|
| admission_breach | 8 | 18 | 0.444 |
| false_block | 0 | 18 | 0.000 |
| log_integrity_failure | 0 | 18 | 0.000 |
| observed_forwarded | 8 | 18 | 0.444 |
| realized_harm | 0 | 18 | 0.000 |
| reference_allow | 0 | 18 | 0.000 |

### F4 — coverage 1/1 subcases
> F4 agreement between the two corpora MUST NOT be reported as replication of the same strength as F1, F2, F3 or F5: `Ω`'s frozen size makes `(mail.send, mail/outbox)` the entire derivable egress set, so the F4 confirmatory instances share their pilot siblings' whole (tool, resource) element and are less independent of the pilot than the other families' are. This is a limit on what was measured; it does not mitigate instance-selection bias, which stays unmitigated (ADR 0037, §J.5 item 23).

| Quantity | Count | Total | Rate |
|---|--:|--:|--:|
| admission_breach | 10 | 36 | 0.278 |
| false_block | 2 | 36 | 0.056 |
| log_integrity_failure | 0 | 36 | 0.000 |
| observed_forwarded | 26 | 36 | 0.722 |
| realized_harm | 10 | 36 | 0.278 |
| reference_allow | 18 | 36 | 0.500 |

### F5 — coverage 1/1 subcases

| Quantity | Count | Total | Rate |
|---|--:|--:|--:|
| admission_breach | 10 | 36 | 0.278 |
| false_block | 2 | 36 | 0.056 |
| log_integrity_failure | 0 | 36 | 0.000 |
| observed_forwarded | 26 | 36 | 0.722 |
| realized_harm | 10 | 36 | 0.278 |
| reference_allow | 18 | 36 | 0.500 |

## Hypotheses

### H4a — **NOT DETERMINED**
- attack (ii), tool/argument substitution after signing, is the `F3 dpop-first-use-body-mutation` row -- NOT POPULATED BY THE CAMPAIGN (pre-registered §4). Half of H4a's prediction is therefore unmeasured, and the measured half alone does not support the whole hypothesis.

### H4b — **NOT DETERMINED**
- the corpus instantiates no compromised-holder scenario: its holder faults substitute another holder's key (H4a's adversary, who does NOT possess the terminal holder identity key), so H4b's premise is never staged
- in-scope-vs-out-of-scope containment IS measured, by F1-root and F1-terminal, but those are not compromised-holder instances and are not reported as if they were

## Agreement with §E.4

80 cells agreed; 0 disagreed.

## Unscorable cells, with causes

| Scenario | Arm | Cause |
|---|---|---|
| cf-f1-chain-tamper | B0 | NA per the sealed record |
| cf-f1-chain-tamper | B1 | NA per the sealed record |
| cf-f1-chain-tamper | B2-broad-noexchange | NA per the sealed record |
| cf-f1-chain-tamper | B2-exchange-broad | NA per the sealed record |
| cf-f2-wrong-holder-proof | B0 | NA per the sealed record |
| cf-f2-wrong-holder-proof | B1 | NA per the sealed record |
| cf-f2-wrong-holder-proof | B2-broad-noexchange | NA per the sealed record |
| cf-f2-wrong-holder-proof | B2-exchange-broad | NA per the sealed record |
| cf-f2-wrong-holder-proof | B2-exchange-task | NA per the sealed record |
| cf-f2-wrong-holder-proof | B-cap | NA per the sealed record |

---

Security and blocking outcomes are exact counts and rates only. No confidence interval is placed on any security proportion (§D.26): a fixed author-constructed suite has no random-sampling population and the verdicts are deterministic. Repetition is used only to detect nondeterminism.
