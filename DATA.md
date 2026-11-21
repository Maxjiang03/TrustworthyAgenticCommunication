# Data and experiment index

All task contents, notes, addresses under `example.test`, labels, and malicious instructions are synthetic test data. The artifact contains no production user dataset. The frozen corpora and their generator are under `fixtures/`.

| Paper section | Inputs and observations | Reproduction |
|---|---|---|
| VI-A/B and Figure 2 | `results/raw/campaign-confirmatory.json`, `fixtures/confirmatory/`, `docs/PRE_REGISTRATION.md` | `python -m analysis.report --out-dir _reproduced/primary` |
| VI-C, modified requests | `results/adaptive/`, including the later applicable-run/holder-key records in `run3/` | Source in `validation/adaptive/` |
| VI-C, Table III | `results/ablation/campaign-ablation.json.gz`, `ablation-summary.json`, `adaptive-summary.json` | Source in `validation/ablation/` |
| VI-C, independent checks | `results/validation/oracle-audit-extended.json`, `real-transport-campaign.json`, `real-transport-sweep.json` | Source in `validation/` |
| VI-C, fault observation | `results/revision/systems-confirmed-2026-11-08/fault-gate.json`, `adapter-faults.json`, `fault-recorded/fault-runs/` | `validation.revision.systems_followup` |
| VI-D, policies and real effects | `results/revision/label-binding-fix-2026-11-09/deterministic/{policy,effects}.json` | `validation.revision.run` |
| VI-D, replay/delegation/revocation | Same directory, `{replay,delegation,revocation}.json` | `validation.revision.run` |
| VI-D, Table V | `results/revision/systems-confirmed-2026-11-08/aip.jsonl` | `validation.revision.systems_followup` |
| VI-E, first model evaluation | `results/revision/model02/` | Archived protocol, responses, task traces and offline scoring |
| VI-E, selected-payload evaluation | `results/revision/systems-model-2026-11-08/` | Separate development records, selection and evaluation traces |
| VI-F and Figure 3 | `results/revision/mentor-2026-11-11/raw.json.gz` and metadata | `validation.revision.matched_latency`; offline analysis in `tools/reproduce_paper.py` |

Run `python tools/prepare_data.py` before commands that read a compressed record's JSON path. Compression changes storage size, not numeric precision. The preparation step restores every retained sample, not a sampled subset.

The main campaign and supplementary experiments have separate denominators. In Table V, replay counts refer only to the second presentation, whereas its raw file includes both presentations. The 15 additional replay entries are test cases; each concurrency case contains 16 presentations.

The timing directory contains the only timing series used for the final paper. Older timing passes, failed development runs, intermediate reports, duplicate JSONL exports, generated figure binaries and editing history are excluded. The model development records used to select the reported payloads are retained.

The offline plotter regenerates the numerical content of Figures 2/3 as PDF and PNG. Figure 1 is an architecture illustration, not a plot derived from experimental samples.
