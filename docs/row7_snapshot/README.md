# Frozen row 7's source snapshot — taken at Part H step 3, as the row requires

Frozen row 7 (`docs/frozen_parameters.md`; ADR 0025, sourcing recorded by ADR 0042) requires its
sources "snapshotted at seal time". This directory is that snapshot: the raw HTTP response bytes
of the two Artificial Analysis pages that anchor both denominators, retrieved once each on
**2026-08-06** with a plain GET (`Invoke-WebRequest -UseBasicParsing`), unmodified.

| file | URL |
|---|---|
| `methodology-performance-benchmarking-2026-08-06.html` | https://artificialanalysis.ai/methodology/performance-benchmarking |
| `models-2026-08-06.html` | https://artificialanalysis.ai/models |

What a reader should know about these bytes: they are the server's HTML as served to a plain GET
on the retrieval date — the models page renders much of its table client-side, so the figures the
pre-registration read back on 2026-08-06 were read from the rendered page, and these bytes are
the retrievable record of what the site served that day, not a screenshot of the rendered table.
The anchoring figures themselves are quoted, dated, in `PRE_REGISTRATION.md` §6 and in row 7's
sourcing field. No figure in this directory's files was produced by this project; nothing here is
a measurement.

Both files are covered by the seal manifest, so the snapshot cannot drift after step 3.
