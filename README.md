# Trustworthy Agentic Communication

This archive contains the source code and experiment records for the MSc Cybersecurity dissertation, *Authorization Propagation at the A2A-to-MCP Boundary: A Controlled Evaluation of Online Token Exchange and Offline Capability Attenuation*.

Public repository: https://github.com/Maxjiang03/TrustworthyAgenticCommunication

The submission archive is the self-contained evidence snapshot. It includes the final experiment records used in the dissertation and does not require access to the public repository.

## Formulation

The study represents authority as subsets of a fixed seven-element ontology, denoted by `Omega`. For a capability chain, the effective authority at hop `i` is `C_i`. The monotonicity requirement is `C_i subseteq C_(i-1)`. At the A2A-to-MCP boundary, a request requiring authority `R` is admitted only if the full ten-condition rule holds, including chain verification, holder proof, invocation binding, policy checks, identity consistency, and `R subseteq C_n`. After execution, the independent oracle checks the exercised authority `A` against `R`, `C_n`, and the initial task grant.

Nine configurations are evaluated under the same scenarios, initial task authorization, narrowing requests, and execution substrate. They differ in the authority-bearing object and the checks available at the boundary.

## Assumptions and scope

The benchmark covers one A2A-to-MCP boundary, one MCP server, one resource domain, and a fixed ontology. Agents are deterministic scripted principals, so language-model sampling is outside the experiment. The scenarios are an author-constructed test corpus rather than a random sample of deployed systems. Security outcomes are exact counts for that corpus. They are not population estimates.

The task-scoped exchange result depends on the tested deployment profile: OAuth 2.1 authentication, RFC 8693 token exchange, RFC 9396 authorization details, and a local authorization-server policy that issues only a monotonic subset. It is not a property of OAuth or token exchange alone. Latency results are in-process measurements from the sealed Windows platform and should not be treated as network or production benchmarks.

The sealed measurement platform was Windows 11 25H2, build 26200.8875, Python 3.13.5, an Intel Core i7-12700H, and 15.75 GiB RAM. The effect-ledger independence check is Windows-specific. Other tests can run on supported non-Windows systems, where the Windows-only cases are skipped.

## Dissertation hypothesis labels

The dissertation uses the reader-facing labels **Hypothesis A** and **Hypothesis B**. They correspond, respectively, to `H4a` and `H4b` in the sealed pre-registration, analysis code, and result records. Only the presentation labels differ; the hypothesis statements, predictions, and evidence status are unchanged.

## Setup

Install Python 3.13 and `uv` 0.10.6 or a compatible recent `uv` release. From the archive root, run:

```powershell
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

`requirements.txt` pins the complete tested Python environment, including the packages used to regenerate the figures. `pyproject.toml` and `uv.lock` preserve the original sealed application environment.

## Exact reproduction command

The following command runs the portable test suite, rebuilds the confirmatory tables from the archived raw record, regenerates the four data figures used in the dissertation, checks their placement, and writes console logs to `_reproduced`:

```powershell
powershell -ExecutionPolicy Bypass -File .\reproduce.ps1
```

The submission archive omits `.git`, which would add about 103 MB of version-control data. When `.git` is absent, the script deselects three tests that inspect historical Git objects. It still runs every executable, corpus, policy, oracle, analysis, and current-file integrity test. A clone of the public repository retains `.git`, so the same script runs all tests there.

The stored confirmatory campaign is write-once. To execute an independent campaign without overwriting it, use a new output path:

```powershell
New-Item -ItemType Directory -Force _reproduced | Out-Null
.\.venv\Scripts\python.exe -m src.harness.campaign_driver --run-mode confirmatory --out _reproduced\campaign-confirmatory.json
```

Raw and derived records are under `results`. The primary records are `results/raw/campaign-confirmatory.json`, `results/raw/latency-pilot.json`, and the console logs stored with the validation, replication, adaptive, and ablation results. The detached seal is under `seal`. The reproduction script replaces the generated `results/figures` directory; it does not alter the archived raw records.

## Compact results

The confirmatory campaign contains 13 scenarios, 143 scored cells, and 10 unscorable cells. All 80 comparable pre-registered predictions matched the observations. The two pre-registered hypotheses were not determined by the confirmatory corpus because their full premises were not instantiated.

In the fixed corpus, the four broad-authority configurations admitted three of the seven ontology elements that the task did not use. The configured task-scoped exchange admitted no excess element, subject to the local subset-issuance policy. The adaptive campaign admitted 13 of 54 applicable attacks overall; B3 and B3+ admitted none of their eight applicable attacks. These adaptive observations are separate from the confirmatory counts.

The pre-specified in-process latency series places about 16 ms of additional work at delegation for the exchange configurations and about 6 ms at the boundary for the capability configurations. CPU pinning reduced both measurements without changing where the cost occurred.

## Approximate active time spent

The repository records work on 22 distinct dates between 14 July and 30 August 2026. This corresponds to about 176 hours at an eight-hour working-day equivalent. No time tracker was used, so this is an approximate effort measure rather than logged active time.

## Archive contents

`src` contains the measured system and harness. `analysis` rebuilds the reported tables. `fixtures` contains the pilot and confirmatory corpora. `tests` contains the automated checks. `validation` contains the post-confirmatory analyses. `results` contains the frozen raw records and experiment logs. `tools/figures` regenerates the dissertation figures. `docs`, `adr`, `DEVIATIONS.md`, and `seal` record the design, assumptions, decisions, deviations, and integrity metadata.

Virtual environments, package caches, Git history, temporary files, dissertation editing copies, and generated figure binaries are intentionally excluded.
