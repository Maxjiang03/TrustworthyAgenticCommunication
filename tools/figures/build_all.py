"""`make figures` -- run every AUTHORISED presentation-layer script in order.

Each script is a pure function of results/raw/ + results/tables/ (ADR 0048),
prints every number it renders, and writes PDF + PNG to results/figures/.
The D3-GATED latency artefacts (FIG-4/5/6, TAB-6/7/8) are deliberately absent:
they are specifications only until the D3 preconditions are satisfied and are
authorised separately.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Phase-2 authorisation (Commander ruling, 2026-08-14): exactly these.
AUTHORISED = (
    "fig1_state_board.py",
    "fig3_evidence_provenance.py",
    "tab0_provenance_register.py",
    "tab1_state_legend.py",
    "tab2_agreement_ladder.py",
    "tab3_unscorable_cells.py",
    "tab4_class_macro.py",
    "tab5_hypotheses.py",
    "tab9_instance_micro.py",
    "tab10_clustered_by_template.py",
)


def main() -> int:
    failures = []
    for name in AUTHORISED:
        script = HERE / name
        if not script.is_file():
            print(f"MISSING {name}")
            failures.append(name)
            continue
        print(f"=== {name} ===", flush=True)
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(script)],
            cwd=str(HERE.parents[1]),
        )
        if proc.returncode != 0:
            print(f"FAILED {name} (exit {proc.returncode})")
            failures.append(name)
    if failures:
        print("build_all: FAILED:", ", ".join(failures))
        return 1
    # FIGURE_PLAN.md section D acceptance step: greyscale renders + PDF/type check.
    print("=== acceptance_check.py ===", flush=True)
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(HERE / "acceptance_check.py")],
        cwd=str(HERE.parents[1]),
    )
    if proc.returncode != 0:
        print("build_all: acceptance_check FAILED")
        return 1
    print("build_all: all authorised artefacts regenerated and acceptance-checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
