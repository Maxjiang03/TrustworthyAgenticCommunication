"""Re-adjudicate the sealed campaign's cells by a second route (DEVIATIONS D-015).

READ-ONLY, IN-BAND. Reads only committed artefacts, re-runs nothing, and writes
one output no other artefact consumes. It never imports
`src/harness/oracle/` -- if it did, it would be the oracle agreeing with
itself. Every predicate below is re-derived from the specification text and the
sealed record, and the two implementations are compared cell by cell.

WHAT IS RE-DERIVED, and from what
---------------------------------
`reference_allow`  Part I (0): the containment `R subset-eq C_n`, plus the
                   family gates -- ADR 0036's credential gate, the F4
                   declassification gate, the F5 approval gate. Inputs: the
                   sealed scenario document (`R`, `C_sets`, `credential_fault`,
                   `intended_labels`, `requires_approval`) and the frozen
                   label/approval policy (ADR 0022).
`admission_breach` Part I (2): forwarded AND NOT reference_allow.
`false_block`      Part I (4): benign AND reference_allow AND NOT forwarded,
                   with `is_benign` read from the sealed document.

COVERAGE, committed in D-015 clause 2 before any comparison was computed
-----------------------------------------------------------------------
TWO-SIDED: containment and the credential gate alone settle the verdict, so it
is re-derived in full and compared in both directions.

ONE-SIDED: an F4/F5 artifact gate also applies. Those gates ask whether a VALID
SIGNED ARTIFACT was presented at run time -- an observation that lives in
`results/_ledger/`, which is git-ignored and so is not reproducible from a
fresh clone. Here the auditor can REFUSE an allow that containment or the
credential gate already forbids, but cannot CONFIRM one. Both halves are
counted separately and neither is reported as the other.

WHAT THIS CANNOT CATCH (D-015, stated before the run)
-----------------------------------------------------
A second route through the SAME specification catches transcription defects: a
dropped conjunct, an inverted condition, a mis-read field. It cannot catch an
error in the specification reading itself, which would sit identically on both
sides and show up as agreement. Author-independence is not claimed.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SEALED_DIR = REPO / "fixtures" / "confirmatory" / "sealed"
POLICY = REPO / "src" / "harness" / "policy" / "label_approval_v1.json"
CAMPAIGN = REPO / "results" / "raw" / "campaign-confirmatory.json"
OUT_DIR = REPO / "results" / "validation"


def out_path(run: int) -> Path:
    """Run 1 keeps the plain name; a re-run takes a distinct one (D-015 clause 5)."""
    return OUT_DIR / ("oracle-audit.json" if run == 1 else f"oracle-audit-run{run}.json")


def elements(value) -> frozenset:
    """A set of (action, resource) pairs from the sealed record's list-of-lists."""
    return frozenset(tuple(pair) for pair in (value or ()))


def re_derive_reference_allow(sealed, policy):
    """Part I (0), re-derived. Returns (verdict_or_None, limbs, gated).

    `None` means the artifact gate applies and the auditor cannot see the
    artifact: everything the committed record settles says allow, but the run
    time gate is unverifiable here, so no verdict is claimed.
    """
    limbs = {}

    # Containment: R subset-eq C_n, the LAST chain set (the terminal hop).
    R = elements(sealed.get("R"))
    chain = sealed.get("C_sets") or [[]]
    C_n = elements(chain[-1])
    limbs["contained"] = R <= C_n
    if not limbs["contained"]:
        return False, limbs, False

    # ADR 0036: a credential fault is a scenario property, read from the seal.
    # A correct monitor refuses a credential that does not verify, whatever
    # authority was requested.
    fault = str(sealed.get("credential_fault", "none"))
    limbs["credential_ok"] = fault == "none"
    if not limbs["credential_ok"]:
        return False, limbs, False

    # The artifact gates. Which of them APPLIES is sealed; whether it is
    # SATISFIED is a run-time observation this auditor cannot read.
    sensitive = [
        label
        for label in (sealed.get("intended_labels") or ())
        if str(label) in policy_sensitive(policy)
    ]
    needs_approval = bool(sealed.get("requires_approval"))
    limbs["declassification_gate_applies"] = bool(sensitive)
    limbs["approval_gate_applies"] = needs_approval
    if sensitive or needs_approval:
        return None, limbs, True
    return True, limbs, False


def policy_sensitive(policy) -> frozenset:
    """The sensitive labels, from where ADR 0022 puts them: row 10.

    Row 10 is the oracle classification block, and `sensitive_labels` is a list
    of `{label, necessity}` entries. Read structurally and refuse on any other
    shape rather than falling back to a guess -- a silently empty set would
    disable the F4 gate and make this auditor agree for the wrong reason.
    """
    row10 = policy.get("row10_oracle_classification")
    if not isinstance(row10, dict) or "sensitive_labels" not in row10:
        raise SystemExit(
            f"{POLICY} carries no row10_oracle_classification.sensitive_labels; "
            f"top-level keys are {sorted(policy)}"
        )
    entries = row10["sensitive_labels"]
    labels = frozenset(str(e["label"]) for e in entries if isinstance(e, dict) and "label" in e)
    if len(labels) != len(entries) or not labels:
        raise SystemExit(
            f"{POLICY} row10.sensitive_labels is not a non-empty list of "
            f"{{label, ...}} entries: {entries!r}"
        )
    return labels


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    run, reason = 1, ""
    for i, tok in enumerate(args):
        if tok == "--run":
            run = int(args[i + 1])
        elif tok == "--reason":
            reason = args[i + 1]
    if run != 1 and not reason:
        print(
            "REFUSED: a re-run requires --reason; D-015 clause 5 records every run and its reason."
        )
        return 1
    out = out_path(run)
    if out.exists():
        print(f"REFUSED: {out} already exists. A second run is a decision (D-015 clause 5).")
        return 1

    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    sealed_docs = {}
    for path in sorted(SEALED_DIR.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        sealed_docs[doc["scenario_id"]] = doc
    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    cells = campaign["cells"]

    print(f"INPUT sealed_scenarios [M]   = {len(sealed_docs)}")
    print(f"INPUT scored_cells [M]       = {len(cells)}")
    print(f"INPUT sensitive_labels [M frozen policy] = {sorted(policy_sensitive(policy))}")
    print(f"INPUT run_index [given]      = {run}")
    print(f"INPUT run_reason [given]     = {reason or '(first run)'}")

    two_sided = one_sided = 0
    agree_two = 0
    one_sided_allow = one_sided_refused_by_unseen_gate = 0
    disagreements = []
    identity_breaks = []

    for cell in cells:
        sealed = sealed_docs[cell["scenario_id"]]
        mine, limbs, gated = re_derive_reference_allow(sealed, policy)
        theirs = bool(cell["reference_allow"])
        key = f"{cell['scenario_id']}/{cell['arm']}"
        if cell.get("monitor_attached") is not None:
            key += f"/monitor={'on' if cell['monitor_attached'] else 'off'}"

        if mine is None:
            # ONE-SIDED. Every limb this auditor can read says allow, so it can
            # refute nothing here: a sealed `False` is explained by an artifact
            # gate it cannot see, a sealed `True` agrees with what it can see.
            # Both are consistent -- which is exactly why they are counted
            # SEPARATELY, so the reader sees how much of this set rests on the
            # limb that was not verified rather than on one that was.
            one_sided += 1
            if theirs:
                one_sided_allow += 1
            else:
                one_sided_refused_by_unseen_gate += 1
        else:
            two_sided += 1
            if mine == theirs:
                agree_two += 1
            else:
                disagreements.append(
                    {
                        "cell": key,
                        "family": cell["family"],
                        "subcase": cell["subcase"],
                        "re_derived_reference_allow": mine,
                        "sealed_oracle_reference_allow": theirs,
                        "limbs": limbs,
                        "sealed_facts": {
                            "R": sealed.get("R"),
                            "C_n": (sealed.get("C_sets") or [[]])[-1],
                            "credential_fault": sealed.get("credential_fault", "none"),
                            "intended_labels": sealed.get("intended_labels"),
                            "requires_approval": sealed.get("requires_approval"),
                        },
                    }
                )

        # The two definitional identities, on every cell, against the record's
        # own fields. Internal consistency, not semantics -- labelled as such.
        forwarded = bool(cell["observed_forwarded"])
        want_breach = forwarded and not theirs
        if bool(cell["admission_breach"]) != want_breach:
            identity_breaks.append(
                {
                    "cell": key,
                    "identity": "admission_breach",
                    "recorded": cell["admission_breach"],
                    "implied": want_breach,
                }
            )
        want_fb = bool(sealed["is_benign"]) and theirs and not forwarded
        if bool(cell["false_block"]) != want_fb:
            identity_breaks.append(
                {
                    "cell": key,
                    "identity": "false_block",
                    "recorded": cell["false_block"],
                    "implied": want_fb,
                }
            )

    print()
    print(f"TWO-SIDED cells       = {two_sided}")
    print(f"  agreements          = {agree_two}")
    print(f"  disagreements       = {len(disagreements)}")
    print(f"ONE-SIDED cells       = {one_sided}   (an artifact gate the auditor cannot see)")
    print(
        f"  sealed allow        = {one_sided_allow}   agrees with every limb the auditor CAN read"
    )
    print(
        f"  sealed refuse       = {one_sided_refused_by_unseen_gate}   "
        "rests on the unseen gate alone"
    )
    print(f"IDENTITY checks       = {2 * len(cells)}")
    print(f"  breaks              = {len(identity_breaks)}")
    for d in disagreements:
        print(
            f"DISAGREEMENT {d['cell']}: re-derived {d['re_derived_reference_allow']} "
            f"vs sealed {d['sealed_oracle_reference_allow']} | limbs={d['limbs']}"
        )
    for b in identity_breaks:
        print(
            f"IDENTITY BREAK {b['cell']}: {b['identity']} recorded {b['recorded']} "
            f"implied {b['implied']}"
        )

    payload = {
        "_what": (
            "A second re-derivation of the sealed oracle's per-cell predicates, from the sealed "
            "scenario documents and the frozen policy, compared cell by cell against "
            "results/raw/campaign-confirmatory.json. Read-only; imports no oracle code; re-runs "
            "nothing; changes no reported number. Governed by DEVIATIONS D-015."
        ),
        "not_established": (
            "A second implementation from the SAME specification by the same author. It catches "
            "transcription-class defects; it cannot catch an error in the specification reading, "
            "which would appear identically on both sides and show as agreement. "
            "Author-independence is not claimed."
        ),
        "run": {"index": run, "reason": reason or "(first run)"},
        "inputs": {
            "sealed_scenarios": len(sealed_docs),
            "scored_cells": len(cells),
            "policy": str(POLICY.relative_to(REPO)).replace("\\", "/"),
            "sensitive_labels": sorted(policy_sensitive(policy)),
        },
        "coverage": {
            "two_sided_cells": two_sided,
            "one_sided_cells": one_sided,
            "one_sided_note": (
                "an F4/F5 artifact gate applies; whether a valid signed artifact was "
                "presented is a run-time observation in the git-ignored ledger, so an allow "
                "can be refuted but not "
                "confirmed"
            ),
        },
        "results": {
            "two_sided_agreements": agree_two,
            "two_sided_disagreements": len(disagreements),
            "one_sided_sealed_allow": one_sided_allow,
            "one_sided_sealed_refuse_resting_on_unseen_gate": one_sided_refused_by_unseen_gate,
            "identity_checks": 2 * len(cells),
            "identity_breaks": len(identity_breaks),
        },
        "disagreements": disagreements,
        "identity_break_detail": identity_breaks,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
