"""Diff the artefacts' RENDER stream against the independent CHECK stream.

Correspondences are declared explicitly: a number that the artefacts print and
the independent recomputation also derives must agree. Anything declared here
and missing from either stream is reported as a gap, so the table cannot quietly
shrink to the subset that happens to pass.
"""

import re
import subprocess
import sys
from pathlib import Path

FC = Path(sys.argv[1])

render = {}
for line in (FC.parent / "render.txt").read_text(encoding="utf-8", errors="replace").splitlines():
    m = re.match(r"^RENDER (\S+) \| (.+?) = (.*)$", line)
    if m:
        render[f"{m.group(1)}|{m.group(2)}"] = m.group(3).strip()

out = subprocess.run(
    [sys.executable, "-X", "utf8", "independent_recompute.py"],
    cwd=FC,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
check = {}
for line in out.stdout.splitlines():
    m = re.match(r"^CHECK (.+?) = (.*)$", line)
    if m:
        check[m.group(1)] = m.group(2).strip()

# (independent CHECK key, artefact RENDER key)
PAIRS = [
    ("ladder.cells_scored", "FIG-1|cells_scored_drawn [D]"),
    ("ladder.unscorable", "FIG-1|unscorable [M]"),
    ("entries.agreed", "FIG-1|agreed [M]"),
    ("entries.agreed", "FIG-1|entries_agreed_reconstructed [D]"),
    ("entries.disagreed", "FIG-1|disagreed [M]"),
    ("entries.disagreed", "FIG-1|entries_disagreed_reconstructed [D]"),
    ("entries.na", "FIG-1|unmeasured_NA [M]"),
    ("entries.na", "FIG-1|cells_expected_NA"),
    ("rows.not_populated", "FIG-1|not_populated_rows [M]"),
    ("rows.deferred", "FIG-1|deferred_rows [M]"),
    ("b3_vs_b3plus.comparable_pairs", "FIG-1|b3_b3plus_identical_pairs [M]"),
    ("false_block.count", "FIG-1|cells_FB"),
    ("class_macro.F1.total", "FIG-1|band_F1_n"),
    ("class_macro.F2.total", "FIG-1|band_F2_n"),
    ("class_macro.F3.total", "FIG-1|band_F3_n"),
    ("class_macro.F4.total", "FIG-1|band_F4_n"),
    ("class_macro.F5.total", "FIG-1|band_F5_n"),
]
for arm in (
    "B0",
    "B1",
    "B2-broad-noexchange",
    "B2-exchange-broad",
    "B2-exchange-task",
    "B2-exchange-task-DPoP",
    "B-cap",
    "B3",
    "B3+",
):
    PAIRS.append((f"per_arm_scored.{arm}", f"FIG-1|per_arm_scored.{arm}"))

# Every class_macro quantity, wherever TAB-4 prints it.
for fam in ("F1", "F2", "F3", "F4", "F5"):
    for q in (
        "admission_breach",
        "false_block",
        "log_integrity_failure",
        "observed_forwarded",
        "realized_harm",
        "reference_allow",
    ):
        PAIRS.append((f"class_macro.{fam}.{q}", f"TAB-4|{fam}.{q}.count [M]"))
    PAIRS.append((f"class_macro.{fam}.total", f"TAB-4|{fam}.n [M observed_forwarded.total]"))
    for q in (
        "admission_breach",
        "false_block",
        "log_integrity_failure",
        "observed_forwarded",
        "realized_harm",
        "reference_allow",
    ):
        PAIRS.append((f"class_macro.{fam}.total", f"TAB-4|{fam}.{q}.total [M]"))

agree = mismatch = missing = 0
print(f"{'independent CHECK':46s} {'artefact RENDER':44s} verdict")
print("-" * 108)
for ck, rk in PAIRS:
    cv, rv = check.get(ck), render.get(rk)
    if cv is None or rv is None:
        missing += 1
        where = "CHECK" if cv is None else "RENDER"
        print(f"{ck:46s} {rk:44s} GAP (absent from {where})")
        continue
    if cv == rv:
        agree += 1
    else:
        mismatch += 1
        print(f"{ck:46s} {rk:44s} MISMATCH {cv!r} vs {rv!r}")
print("-" * 108)
print(
    f"agree={agree}  mismatch={mismatch}  gap={missing}  (of {len(PAIRS)} declared correspondences)"
)
print("RECOMPUTE stream tail:", out.stdout.strip().splitlines()[-1])
sys.exit(1 if (mismatch or missing) else 0)
