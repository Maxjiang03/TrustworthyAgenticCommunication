"""Independently verify the detached v0.5 seal manifest against a fresh clone.

This is NOT the code that produced the manifest and shares none of it: where
`build_manifest.py` enumerates coverage rules and reads blob bytes through git
plumbing, this script takes the manifest as the claim and a FRESH CLONE as the
evidence, reads every covered file as plain bytes from the checked-out tree
(no `git cat-file` anywhere), hashes them itself, and compares. Clone with
`core.autocrlf=false` so the checked-out bytes are the committed bytes.

It also re-checks the manifest's exhaustiveness claim from the clone's own
file list: covered ∪ excluded must equal the tracked files exactly — a file
the manifest neither covers nor excludes-with-reason is a FAIL, because after
the seal nobody can ask whether it was an oversight.

    python seal/verify_manifest.py --manifest <manifest.json> --repo <fresh-clone>
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="independent seal-manifest verification")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    repo = Path(args.repo)

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True, check=True
    ).stdout.strip()
    claimed = manifest["implementation_commit"]
    if head != claimed:
        print(f"FAIL -- clone HEAD {head} is not the manifest's implementation commit {claimed}")
        return 1

    failures: list[str] = []
    verified = 0
    for path, expected in sorted(manifest["covered"].items()):
        target = repo / path
        if not target.is_file():
            failures.append(f"{path}: MISSING from the clone")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            failures.append(
                f"{path}: HASH MISMATCH\n    manifest: {expected}\n    clone:    {actual}"
            )
        else:
            verified += 1

    tracked = set(
        subprocess.run(
            ["git", "ls-files"], cwd=str(repo), capture_output=True, text=True, check=True
        ).stdout.split("\n")
    ) - {""}
    accounted = set(manifest["covered"]) | {entry["path"] for entry in manifest["not_covered"]}
    for path in sorted(tracked - accounted):
        failures.append(
            f"{path}: tracked in the clone but neither covered nor excluded-with-reason"
        )
    for path in sorted(accounted - tracked):
        failures.append(f"{path}: named by the manifest but not tracked in the clone")

    print(f"commit: {head}")
    print(f"covered files re-hashed from plain clone bytes: {verified}/{len(manifest['covered'])}")
    print(
        f"exhaustiveness: {len(tracked)} tracked = {len(manifest['covered'])} covered "
        f"+ {len(manifest['not_covered'])} excluded"
    )
    if failures:
        print(f"FAIL -- {len(failures)} violation(s):")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print("PASS -- every hash independently re-derived; coverage exhaustive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
