# TrustworthyAgent

Trustworthy Agentic Communication: a pre-registered, reproducible testbed that measures
authorization-scope propagation and its cost at the A2A→MCP boundary (the cross-protocol
confused-deputy problem, TV23). MSc Cybersecurity dissertation, University of Glasgow.

## Current phase

**Sealed, awaiting the confirmatory campaign.** As of 2026-08-07: **all fifteen** feasibility
smoke gates pass on the pilot corpus (`smoke/README.md` is the board), **all nine arms** are
built, the pre-registration is authored (`docs/PRE_REGISTRATION.md`), the confirmatory corpus is
generated (ADR 0043), and the repository has been sealed twice — v0.5 (`805425e`) and v0.6
(`cdf185d`), each with a detached manifest and an OpenTimestamps anchor.

**A v0.7 reseal is owed, and Part H step 7 — the confirmatory campaign — has NOT run.** A pre-run
audit (ADR 0044) found that the apparatus could not execute step 7 and would, in two places, have
measured wrongly; the repairs are in place and the reseal follows. Every deviation is recorded in
`DEVIATIONS.md` rather than in a commit message.

All eleven `docs/frozen_parameters.md` rows are settled — ten set, one (`task_authorization_policy`)
deferred by decision (ADR 0028) and never to be filled. **The only timing figures that exist are
G-3's, and they live in `smoke/g3/REPORT.md` and nowhere else.**

*(Update note, 2026-07-30: this section previously read "Repository skeleton — pre-smoke-test.
Implementation logic has not begun," which was true when written and stopped being true in the
pass that built the apparatus.)*

## Authoritative design

`docs/EXPERIMENT_ARCHITECTURE_FINAL.md` is the single source of truth. Working rules for
contributors (human or AI) are in `PROJECT_RULES.md`; decisions are recorded in `adr/`.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). The locked environment (`uv.lock`)
is committed.

| Command | Action |
|---|---|
| `make setup` | `uv sync` — create the pinned environment |
| `make lint` | `pre-commit run --all-files` (ruff + ruff-format) |
| `make test` | `pytest -q` |
| `make gate GATE=g1` | run one gate's spike (`smoke/g{1,2,4,5,6,7,8,11}/`). POSIX-flavoured — on Windows run `uv run python smoke/g11/spike.py` directly |
| `make campaign` | Part H step 7 — runs the frozen campaign ONCE, refuses to overwrite a result (ADR 0045) |
| `make reproduce` | regenerates every table from `results/raw/` (`analysis/report.py`) |

Without `make` (e.g. plain Windows), run the underlying commands directly:
`uv sync`, `uvx pre-commit run --all-files`, `uv run pytest -q`.

**Platform note (ADR 0014):** the effect-ledger suite (`tests/test_effect_ledger.py`) and the
G-7 spike are **Windows-only** — the ledger's independence enforcement is Win32 share-mode
locking, so on other platforms those tests are *skipped* (and the spike refuses to run). A
green CI run on `ubuntu-latest` therefore does **not** verify the ledger; every other suite is
cross-platform. Windows is the sealed measurement platform; the POSIX variant is deferred.

## Layout

- `src/sut/` — the measured system (must never import from the harness)
- `src/sut/oauth_as/` — the pinned experiment OAuth 2.1 AS (ADR 0015; built at G-4 Phase 2). Runs
  out-of-process on loopback with its signing key never in an agent process. No other `src/sut/`
  module may import it (agents reach it over the wire), and **`src/harness/` may never import it**
  — the oracle and the G-13 verifier reimplement token verification independently (D13/D21)
- `src/harness/` — the instrument (imports `sut`, never the reverse; except `src/sut/oauth_as/`,
  which it may never import). All three import rules are enforced by an AST suite
  (`tests/test_import_redlines.py`), not by convention alone
- `docs/` — architecture, threat model, frozen parameters, pre-registration
- `adr/` — one file per decision
- `fixtures/pilot/` vs `fixtures/confirmatory/` — strictly disjoint; confirmatory stays **empty** until post-seal
- `results/raw|tables|figures/` — write-once raw traces and derived outputs (later phases)

License: MIT (© 2026 Yixian Jiang).
