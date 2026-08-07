"""Build the detached v0.6 seal manifest (Part H step 3, step 6).

Coverage is Part H step 3's list, made concrete file by file; every tracked
file the manifest does NOT cover is enumerated inside the manifest with the
reason for its exclusion, so a reader can tell a deliberate exclusion from an
oversight after the seal, when they can no longer ask. A tracked file that
matches neither the coverage rules nor an exclusion class FAILS the build —
the manifest is exhaustive or it is not emitted.

Hashes are SHA-256 over the **committed git blob bytes** (LF as stored), read
with `git cat-file blob <commit>:<path>` — so a fresh clone made with
`core.autocrlf=false` reproduces every hash with plain file reads and no git
plumbing. The manifest is DETACHED: it lives under `seal/`, which it does not
cover, and no covered file names it.

    uv run python seal/build_manifest.py [--commit HEAD] [--out seal/manifest_v0.6.json]
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Part H step 3's coverage list, as concrete path rules (prefix or exact).
COVERED_EXACT = {
    "docs/EXPERIMENT_ARCHITECTURE_FINAL.md": "the design document",
    "docs/PRE_REGISTRATION.md": "the pre-registration (Part H step 2)",
    "docs/frozen_parameters.md": "every frozen row, including row 9's transcription",
    "docs/measurement_platform.md": "the row 9 sealed-measurement-platform full record",
    "pyproject.toml": "the dependency environment (declaration)",
    "uv.lock": "the dependency environment (resolved versions, with hashes)",
    "Dockerfile": "the dependency environment (pinned container, §J.1 item 2)",
}
COVERED_PREFIX = {
    "src/": "implementation and oracle code, incl. the configuration artifacts "
    "(omega_gamma_v1.json = H(Γ), label_approval_v1.json = H(Λ), "
    "identity_registry_v1.json = H(R)) and the seed→keypair derivation rule "
    "(src/harness/key_material.py)",
    "analysis/": "the analysis code, frozen with the rest (§J.3 item 12)",
    "fixtures/pilot/": "the corpus generator, the PILOT scenario specifications "
    "and the deterministic key seeds (fixtures/pilot/golden_thread/); the "
    "generator produces BOTH corpora from one code path and its location is "
    "historical (ADR 0043)",
    "fixtures/confirmatory/": "the CONFIRMATORY scenario specifications and seed "
    "(Part H step 4) — a SEALED INPUT at v0.6, where at v0.5 this directory held "
    "a README and nothing else. Specifications and seeds only: no token byte and "
    "no signature is stored anywhere under fixtures/, because Biscuit tokens are "
    "not byte-reproducible across mints (ADR 0007)",
    "fixtures/": "any other fixture artifact, covered by the same rule as the two "
    "corpora above so that no fixture path can fall out of coverage silently",
    "docs/row7_snapshot/": "the seal-time snapshot of frozen row 7's two sources",
}
# Every other tracked file must fall in exactly one of these exclusion
# classes, each with its reason stated for the post-seal reader.
EXCLUDED_PREFIX = {
    "tests/": "the validation suite over the covered artifacts; pinned by the "
    "implementation commit and not named by Part H step 3's coverage list — "
    "hashing it would change no campaign computation",
    "smoke/": "gate spikes and adjudication reports; the gate record is "
    "provenance (named in this manifest's `gates` block) and is pinned by the "
    "implementation commit — Part H runs gates at step 1, it does not hash them "
    "at step 3",
    "adr/": "the decision trail; a historical record pinned by the "
    "implementation commit, deliberately outside the hashed candidate so a "
    "post-seal ADR can record a deviation without touching the seal",
    "tools/": "repository-history proofs and re-run records (reframe, workplan, "
    "gate_rerun); records about the repository, not campaign inputs",
    "docs/workplan/": "archived work specifications; history, not apparatus",
    "seal/": "the manifest and its tooling — DETACHED by Part H step 6: a "
    "manifest never covers itself, and the temporal-anchor proof that will sit "
    "beside it cannot be inside what it anchors",
    ".github/": "CI configuration; regression protection, never adjudicative "
    "(frozen row 2's own rule)",
    "results/": "the campaign OUTPUT tree, write-once and empty until step 7 "
    "(three .gitkeep placeholders at seal time); outputs are governed by §J.4's "
    "raw-trace archival rule and are produced by the sealed apparatus, never "
    "sealed before they exist",
}
EXCLUDED_EXACT = {
    "docs/threat_model.md": "threat model and assumptions page; context for the "
    "dissertation, pinned by the implementation commit, not named by step 3",
    "PROJECT_RULES.md": "project governance; process, not apparatus",
    "README.md": "repository front page; navigation, not apparatus",
    "Makefile": "developer convenience targets; not apparatus",
    ".editorconfig": "repository hygiene",
    ".gitignore": "repository hygiene",
    ".pre-commit-config.yaml": "repository hygiene (lint hooks)",
    ".python-version": "developer convenience; the adjudicative interpreter "
    "version is recorded in the row 9 platform record",
    "LICENSE": "licensing; not apparatus",
}


def _git_bytes(*args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True, check=True)
    return result.stdout


def classify(path: str) -> "tuple[str, str] | None":
    """(disposition, reason) for a tracked path, or None if unclassified."""
    if path in COVERED_EXACT:
        return "covered", COVERED_EXACT[path]
    for prefix, reason in COVERED_PREFIX.items():
        if path.startswith(prefix):
            return "covered", reason
    if path in EXCLUDED_EXACT:
        return "excluded", EXCLUDED_EXACT[path]
    for prefix, reason in EXCLUDED_PREFIX.items():
        if path.startswith(prefix):
            return "excluded", reason
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="build the detached v0.6 seal manifest")
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--out", default="seal/manifest_v0.6.json")
    args = parser.parse_args()

    commit = _git_bytes("rev-parse", args.commit).decode().strip()
    tracked = sorted(
        line for line in _git_bytes("ls-tree", "-r", "--name-only", commit).decode().splitlines()
    )

    covered: dict[str, str] = {}
    excluded: list[dict[str, str]] = []
    unclassified: list[str] = []
    for path in tracked:
        disposition = classify(path)
        if disposition is None:
            unclassified.append(path)
        elif disposition[0] == "covered":
            blob = _git_bytes("cat-file", "blob", f"{commit}:{path}")
            covered[path] = hashlib.sha256(blob).hexdigest()
        else:
            excluded.append({"path": path, "reason": disposition[1]})
    if unclassified:
        print("FAIL -- tracked files matching neither coverage nor a stated exclusion:")
        for path in unclassified:
            print(f"  {path}")
        return 1

    manifest = {
        "_what": "Detached seal manifest for the v0.6 candidate "
        "(docs/EXPERIMENT_ARCHITECTURE_FINAL.md, Part H step 3). The manifest is "
        "detached: nothing it covers contains it, and it does not cover seal/. "
        "v0.6 SUPERSEDES v0.5 (seal/superseded/): v0.5 was sealed with inputs from "
        "which no confirmatory corpus was producible, so the corpus was generated "
        "under ADR 0043 and the candidate resealed. The superseded manifest and its "
        "temporal-anchor proof are kept, not deleted -- four independent fail-closed "
        "layers refused the shortcut of relabelling the pilot corpus, and that record "
        "is worth more than a tidy seal directory.",
        "hash_definition": "SHA-256 over the committed git blob bytes (LF as stored). "
        "A fresh clone with core.autocrlf=false reproduces every hash by reading "
        "the checked-out file bytes directly.",
        "implementation_commit": commit,
        "coverage_rule": "Part H step 3's list: design document, implementation "
        "commit, oracle code, analysis code, all configuration, the dependency "
        "environment and the sealed measurement platform, the corpus generator "
        "with its seeds, derivation rule and scenario specifications for BOTH "
        "corpora (fixtures/pilot/ and fixtures/confirmatory/), plus "
        "PRE_REGISTRATION.md and the row 7 source snapshot.",
        "covered": covered,
        "not_covered": excluded,
        "environment_note": "uv.lock (covered) is the resolved dependency set, "
        "enforced by `uv sync --locked`; the adjudicative interpreter and OS are "
        "the row 9 record (docs/measurement_platform.md, frozen row 9).",
        "counts": {"tracked": len(tracked), "covered": len(covered), "excluded": len(excluded)},
    }
    out = REPO_ROOT / args.out
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest written: {args.out}")
    print(
        f"commit {commit}: {len(tracked)} tracked, {len(covered)} covered, "
        f"{len(excluded)} excluded, 0 unclassified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
