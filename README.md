# CLAMP: anonymous research artifact

Code and data for **Capability-Limited Authorization for Multi-Agent Protocols**. CLAMP carries task-scoped grants through agent delegation to an MCP tool gateway and checks decisions against independently observed tool effects.

## Quick start

Tested environment: Python 3.13.5, Windows 11 25H2, Intel Core i7-12700H. Package versions are fixed in `requirements.txt`. No model weights, service credentials, virtual environment, or package cache are included.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe reproduce.py
```

On Linux/macOS, use `.venv/bin/python` instead. The offline command rebuilds the primary analysis, Tables IV/V, both archived model evaluations, the four bootstrap intervals, and data plots for Figures 2/3, then runs the included implementation tests. It makes no model API requests. Outputs go to `_reproduced/` and leave the archived records unchanged.

Release validation: 1531 tests pass and 16 report skips in the tested environment. New executions match all 143 primary combinations, 2703 supplementary security checks, and 300 AIP comparison calls. The nine observation-fault checks and four adapter-fault cases also reproduce their recorded outcomes.

For statistics and plots without the test suite:

```powershell
.venv\Scripts\python.exe reproduce.py --skip-tests
```

Large JSON records are stored as deterministic gzip files. `tools/prepare_data.py` restores their original JSON paths locally before analysis. Restored files, generated figures, and logs are ignored by Git. `FILE_MANIFEST.json` records the distributed files and their SHA-256 digests. Verify a downloaded copy with `python tools/check_integrity.py`.

## Repository structure

```text
src/sut/                 Authorization implementations and protocol adapters
src/harness/             Scenario runner, independent verification, observation
analysis/                Primary analysis and bootstrap estimators
fixtures/                Pilot and 13-scenario primary corpora and generator
tests/                   Current implementation and integration tests
smoke/                   Executable component validation programs
validation/adaptive/     Modified-request and holder-key probes
validation/ablation/     Seven mechanism-removal variants
validation/revision/     File/SQLite, policy, replay, delegation and model tests
validation/third_party/  Pinned AIP source and its upstream license
results/                 Paper records indexed in DATA.md
docs/                    Specifications required by the runner and analysis
tools/                   Data preparation, integrity checking, paper analysis
```

## Paper results

| Evidence | Record count | Location |
|---|---:|---|
| Primary security campaign | 143 scored combinations, 10 inapplicable | `results/raw/campaign-confirmatory.json` |
| Prediction agreement | 80 comparable entries | Rebuilt by `analysis.report` |
| Real file/SQLite effects | 1400 calls | `results/revision/label-binding-fix-2026-11-09/deterministic/` |
| Matched policy checks | 1080 | Same directory |
| Replay / two-hop / revocation checks | 15 / 8 / 200 | Same directory |
| Pinned AIP comparison | 300 calls | `results/revision/systems-confirmed-2026-11-08/` |
| Model evaluations | Two sets of 45 task runs and 98 calls | See `DATA.md` |
| Matched timing | Ten configurations, 210 retained warm benign samples each | `results/revision/mentor-2026-11-11/` |

The timing estimator sums presentation and boundary verification within each repetition before comparing medians. B3 minus B0 is 3.27545 ms, with a 95% bootstrap interval of 3.1915175–3.42275 ms. Adding an exact-call signature to exchange with DPoP adds 0.1761 ms, with an interval of 0.14154875–0.20335125 ms. Delegation/issuance time is reported separately. `tools/reproduce_paper.py` recomputes these values from the raw samples using 10,000 draws and seed 4815162342.

## Execute new experiments

Use a new output path for every run. These commands execute new observations rather than changing the paper records.

```powershell
python -m src.harness.campaign_driver --run-mode confirmatory --out _reproduced/new-primary.json
python -m validation.revision.run --out _reproduced/new-security
python -m validation.revision.systems_followup --out _reproduced/new-systems
python -m validation.revision.matched_latency --out _reproduced/new-timing
```

The systems command uses the included, unmodified AIP Python packages at commit `69695e6f89cbdd34796d1c2b8fdf379f825d36bf`. Its required `base58` dependency is pinned in `requirements.txt`. No dependency cache or second AIP checkout is required.

Model experiments use a hosted API and require the operator's own credentials. They are separate from offline reproduction and can incur provider charges. Set `DEEPSEEK_API_KEY` locally, or use the hidden prompt:

```powershell
python -m validation.revision.model --out _reproduced/new-model --key-stdin
python -m validation.revision.model_followup --out _reproduced/new-model-followup
```

See `MODELS.md` for the recorded model identifiers and parameters. The follow-up command freezes selection from 11 development trials before its separate 45-run evaluation.

## Artifact notes

The Windows observation tests exercise OS-specific ledger behavior; those tests report skips on other platforms. The published timing values describe the recorded machine; new timing runs produce new measurements.

This snapshot uses neutral synthetic identities and an example application namespace. `ANONYMIZATION.md` lists the transformations and distinguishes archived observations from anonymized validation captures. Two historical-document/Git-audit test modules and two historical audit methods are omitted; the current implementation tests are included. No authorization check is disabled for publication.

Project code is MIT-licensed. The pinned AIP dependency retains its upstream license and attribution. No paper-author names, affiliations, contact details, repository owner links, or original Git history are included in the downloadable artifact.
