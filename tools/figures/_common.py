"""Shared presentation-layer helpers (ADR 0048).

Every script in tools/figures/ is a pure function of already-frozen artefacts
(results/raw/, results/tables/): it makes no selection, exclusion, binning, or
statistical decision of its own, prints every number it renders to stdout, and
writes PDF + PNG to results/figures/ (git-ignored). The ONLY import from the
sealed analysis code is the named exception of ADR 0048: the label-token mapping
{ROW_SUBCASE_TOKENS, row_key, CONTROL_PREFIX} from analysis/matrix.py.
"""

import json
import os
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Deterministic output: matplotlib stamps PDF CreationDate from
# SOURCE_DATE_EPOCH; fix it before pyplot is imported anywhere.
os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
random.seed(20260814)  # no script draws random numbers; seeded on principle

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (re-exported for scripts)

# ADR 0048 named exception -- the sealed row-label <-> subcase-token mapping.
sys.path.insert(0, str(REPO_ROOT))
from analysis.matrix import CONTROL_PREFIX, ROW_SUBCASE_TOKENS, row_key  # noqa: E402

RESULTS_RAW = REPO_ROOT / "results" / "raw"
RESULTS_TABLES = REPO_ROOT / "results" / "tables"
FIGURES_OUT = REPO_ROOT / "results" / "figures"

# §E.1 ladder order -- fixed for every artefact.
ARM_ORDER = (
    "B0",
    "B1",
    "B2-broad-noexchange",
    "B2-exchange-broad",
    "B2-exchange-task",
    "B2-exchange-task-DPoP",
    "B-cap",
    "B3",
    "B3+",
)

# Okabe-Ito-derived, near-monochrome by design (FIGURE_PLAN.md §D).
INK = "#1a1a1a"  # blocked fill, text
PAPER = "#ffffff"  # allowed
GREY = "#b0b0b0"  # NA hatch lines
GHOST = "0.90"  # NOT-POPULATED ghost bands
MIDGREY = "0.55"
BLUE = "#0072B2"  # disclosure brackets / leaders
ORANGE = "#E69F00"  # false-block dashed border
VERMILLION = "#D55E00"  # RESERVED: the (unused) disagreement chevron

FONT_MIN_PT = 8  # minimum effective size everywhere (FIGURE_PLAN.md §D)

# ---------------------------------------------------------------------------
# R2 -- the partition rule, hard-coded, printed verbatim by every user of it.
# It uses only existing cell fields plus the sealed per-cell expected values,
# and it determines NO number's inclusion or exclusion: every group is printed
# and nothing is dropped.
# ---------------------------------------------------------------------------
AGREEMENT_PARTITION_RULE = """\
AGREEMENT_PARTITION_RULE (ADR 0048 / FIGURE_PLAN.md §0.6 R2). Every SCORED cell
of campaign-confirmatory.json is placed in exactly one group, using only the
cell fields (family, subcase, monitor_attached) plus the sealed per-cell
expected values of results-confirmatory.json expected_matrix (daggers included)
and the sealed label-token mapping of analysis/matrix.py:
  1. benign_golden_thread  -- subcase == 'benign:golden-thread'
  2. f45_benign_controls   -- any other subcase starting 'benign:'
  3. dagger_true_complement-- subcase maps to a predicted E.4 row, the row's
                              expected value for this arm carries the dagger,
                              and the cell's monitor_attached is True (a
                              daggered prediction is scored against the False
                              pass only -- E.4 footnote dagger, ingest.py)
  4. agreement_consumed    -- every other scored cell (F1/F2/F3 cells; F4/F5
                              daggered cells measured under False; F4/F5
                              undaggered cells under BOTH configurations)
The partition is a regrouping for display; it decides nothing about which
numbers are reported."""


class PresentationError(RuntimeError):
    """Fail loudly: a presentation script never patches over a surprise."""


def load_campaign():
    path = RESULTS_RAW / "campaign-confirmatory.json"
    if not path.is_file():
        raise PresentationError(f"missing {path}; Part H step 7 output not found")
    return json.loads(path.read_text(encoding="utf-8"))


def load_tables():
    path = RESULTS_TABLES / "results-confirmatory.json"
    if not path.is_file():
        raise PresentationError(f"missing {path}; run `make reproduce` first")
    return json.loads(path.read_text(encoding="utf-8"))


def predicted_rows(tables):
    """The 10 predicted E.4 rows, keyed by their corpus subcase token."""
    by_token = {}
    for row in tables["expected_matrix"]:
        if row["state"] != "predicted":
            continue
        token = ROW_SUBCASE_TOKENS[row_key(row["subcase"])]
        if token is None:
            raise PresentationError(
                f"predicted row {row['subcase']!r} maps to no corpus token; "
                "matrix and corpus disagree"
            )
        by_token[token] = row
    if len(by_token) != 10:
        raise PresentationError(f"expected 10 predicted rows, found {len(by_token)}")
    return by_token


def is_daggered(expected_value):
    return isinstance(expected_value, str) and expected_value.endswith("†")


def partition_cells(campaign, tables):
    """Apply AGREEMENT_PARTITION_RULE to every scored cell. Nothing is dropped."""
    rows = predicted_rows(tables)
    groups = {
        "benign_golden_thread": [],
        "f45_benign_controls": [],
        "dagger_true_complement": [],
        "agreement_consumed": [],
    }
    for cell in campaign["cells"]:
        subcase = str(cell.get("subcase") or "")
        if subcase == "benign:golden-thread":
            groups["benign_golden_thread"].append(cell)
        elif subcase.startswith(CONTROL_PREFIX):
            groups["f45_benign_controls"].append(cell)
        else:
            row = rows.get(subcase)
            if row is None:
                raise PresentationError(
                    f"scored cell subcase {subcase!r} maps to no predicted row and "
                    "is not a control; the partition would silently drop it"
                )
            expected = row["cells"].get(cell["arm"])
            if is_daggered(expected) and cell.get("monitor_attached") is True:
                groups["dagger_true_complement"].append(cell)
            else:
                groups["agreement_consumed"].append(cell)
    total = sum(len(v) for v in groups.values())
    if total != len(campaign["cells"]):
        raise PresentationError(f"partition covered {total} cells of {len(campaign['cells'])}")
    return groups


def print_partition(artefact, campaign, tables):
    """Print the rule verbatim and every group size (R2 duty)."""
    print(AGREEMENT_PARTITION_RULE)
    groups = partition_cells(campaign, tables)
    for name in (
        "agreement_consumed",
        "benign_golden_thread",
        "f45_benign_controls",
        "dagger_true_complement",
    ):
        print_render(artefact, f"partition.{name}", len(groups[name]))
    return groups


def print_render(artefact, key, value):
    """Every number an artefact renders is printed through this, one per line."""
    print(f"RENDER {artefact} | {key} = {value}")


def mpl_setup():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": FONT_MIN_PT,
            "axes.titlesize": FONT_MIN_PT + 1,
            "axes.labelsize": FONT_MIN_PT,
            "xtick.labelsize": FONT_MIN_PT,
            "ytick.labelsize": FONT_MIN_PT,
            "legend.fontsize": FONT_MIN_PT,
            "figure.dpi": 100,
            "savefig.dpi": 300,
            "svg.hashsalt": "aasc-tv23",
        }
    )


def save(fig, stem, artefact):
    FIGURES_OUT.mkdir(parents=True, exist_ok=True)
    pdf = FIGURES_OUT / f"{stem}.pdf"
    png = FIGURES_OUT / f"{stem}.png"
    fig.savefig(pdf, bbox_inches="tight", metadata={"CreationDate": None})
    fig.savefig(png, bbox_inches="tight")
    print(f"WROTE {artefact} | {pdf}")
    print(f"WROTE {artefact} | {png}")
