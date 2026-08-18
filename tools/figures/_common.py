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
VERMILLION = "#D55E00"  # the disagreement mark -- drawn 0 times, and that is the result

# The state palette, COMPUTED rather than eyeballed (dataviz skill). The two
# slots doing hue work clear every gate: normal-vision dE 47.7, protanopia
# 41.3, deuteranopia 48.6 (OKLab x100, Machado 2009 severity 1.0), against a
# target of 8 and a hard normal-vision gate of 15. BLOCKED carries chroma
# 0.118, over the 0.10 floor, so it still reads as a hue and not as grey.
#
# It must also survive a MONOCHROME print, which the categorical lightness
# band cannot express: the four fills sit at Rec.601 luma 51 / 162 / 236 /
# 255, minimum adjacent gap 19 of 255. That is why BLOCKED sits outside the
# 0.43-0.77 band -- the same reason the skill gives for not 'fixing' a
# sequential ramp that spans it.
BLOCKED = "#063C7A"  # deep blue fill, PAPER letter
FALSE_BLOCK = "#E69F00"  # amber fill, INK letter
HATCH = "#C0C0C0"  # NA texture, light enough that the glyph over it reads
OFF_CAMPAIGN = "#5A6673"  # dashed outline + letter, no fill

# The SAME blue one step lighter (same OKLCH hue, L 0.363 -> 0.54): an E.4 'B'
# on a row the campaign never populated. Same hue, so it reads as the same
# STATE; lighter, so it is never mistaken for a MEASUREMENT -- which matters
# because letting suite or gate evidence look like campaign evidence is the one
# conflation this figure exists to prevent. Computed, not eyeballed: dE against
# BLOCKED is 17.7 normal / 18.0 protanopia / 17.4 deuteranopia, all over the
# hard gate of 15; greyscale luma 97 sits 46 below the amber and 46 above the
# blue; white text on it clears 5.10:1.
OFF_BLOCKED = "#3A6FB5"

# FIG-0's authority ladder. Its four states are ORDERED -- above / at / below
# the task grant, plus off-scale -- so the rule that applies is the SEQUENTIAL
# one, a single hue light to dark, not the categorical one. The hue is BLOCKED's,
# so the two matrix figures read as one system; the token is its own, because
# "admitted above the grant" and "the boundary blocked the request" are
# different facts and one name across both would invite exactly the wrong
# transfer. Computed: luma 192, which is 141 clear of BLOCKED and 63 clear of
# PAPER, and an INK glyph on it clears 9.68:1.
LADDER_AT = "#B0C3DC"


FONT_MIN_PT = 8  # minimum effective size everywhere (FIGURE_PLAN.md §D)

# ---------------------------------------------------------------------------
# C2 (Commander ruling): artefact size is fixed at AUTHORING time and is never
# resolved by scaling, because scaling an 8 pt figure takes its type below 8 pt.
# The ceiling enforcing that is load-bearing, so it is MEASURED, not assumed:
#   mproj.cls:41-47    geometry -- a4paper, left/right 3.18cm, top/bottom
#                      2.54cm, bindingoffset 0.2in
#   mproj.log:618-619  the compiler's own record --
#                      \textwidth=402.095pt  \textheight=700.50723pt
#                      (TeX pt; 1 in = 72.27 pt)
# The two sources agree: the text block is 5.564 x 9.693 in. Portrait is
# unusable for every matrix artefact here (5.564 in of width), so landscape is
# forced by arithmetic and HEIGHT is the binding constraint.
# ---------------------------------------------------------------------------
TEX_PT_PER_IN = 72.27
TEXT_W_IN = 402.095 / TEX_PT_PER_IN  # 5.564
TEXT_H_IN = 700.50723 / TEX_PT_PER_IN  # 9.693
PORTRAIT = (TEXT_W_IN, TEXT_H_IN)
LANDSCAPE = (TEXT_H_IN, TEXT_W_IN)  # rotated 90 deg, e.g. \begin{sidewaysfigure}

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
            # Serif across the whole suite (Commander ruling 2026-08-17).
            # DejaVu Serif ships WITH matplotlib, so a fresh clone renders the
            # same glyphs on any machine; a system face would break the
            # byte-reproduction the verification pass depends on.
            "font.family": "DejaVu Serif",
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
    """Write PDF + PNG AT THE AUTHORED SIZE, reporting any content overflow.

    C2 requires the authored size to be the delivered size. `bbox_inches="tight"`
    breaks that: it grows the page to whatever the drawn content happened to
    need, which makes `figsize` a suggestion rather than a commitment and hides
    an artefact that does not fit the text block until somebody measures the
    PDF. (It is how FIG-1 came to be authored at 8.80 x 9.45 in and delivered at
    9.60 x 11.41 in.) So the canvas is saved exactly as authored and the overflow
    is PRINTED rather than absorbed -- a figure that overruns its canvas is a
    layout defect to fix, not a page size to accept.
    """
    FIGURES_OUT.mkdir(parents=True, exist_ok=True)
    pdf = FIGURES_OUT / f"{stem}.pdf"
    png = FIGURES_OUT / f"{stem}.png"

    aw, ah = (float(v) for v in fig.get_size_inches())
    fig.canvas.draw()
    tb = fig.get_tightbbox(fig.canvas.get_renderer())
    over_w = max(0.0, tb.width - aw)
    over_h = max(0.0, tb.height - ah)
    fits = [
        name
        for name, (mw, mh) in (("portrait", PORTRAIT), ("landscape", LANDSCAPE))
        if aw <= mw + 1e-6 and ah <= mh + 1e-6
    ]
    print_render(artefact, "canvas.authored_in", f"{aw:.3f} x {ah:.3f}")
    print_render(artefact, "canvas.content_overflow_in", f"{over_w:.3f} w, {over_h:.3f} h")
    print_render(artefact, "canvas.placeable", fits[0] if fits else "NO -- exceeds the text block")
    if over_w > 0.01 or over_h > 0.01:
        print_render(artefact, "canvas.CLIPPED", "drawn content exceeds the authored canvas")

    fig.savefig(pdf, metadata={"CreationDate": None})
    fig.savefig(png)
    print(f"WROTE {artefact} | {pdf}")
    print(f"WROTE {artefact} | {png}")


# ---------------------------------------------------------------------------
# The latency artefacts (FIG-L1/L2/L3): loaders and two guards that RAISE.
# ---------------------------------------------------------------------------
MAX_WIDTH_IN, MAX_HEIGHT_IN = LANDSCAPE  # the measured text block, rotated


def load_row1_decisions():
    """Both committed row-1 decision artefacts (D-009): run 1 and run 2.

    Run 1 (n=225) omitted the pre-registered warm-up discard; run 2 (n=210)
    applied it. D-009 clause 2 keeps run 1's verdict as the reported one, and
    its closure says the descriptives quoted must be run 2's, labelled as such.
    A figure showing both rows, each labelled, is the only shape that does not
    describe two runs as one.
    """
    out = {}
    for run, name in ((1, "results-latency-pilot.json"), (2, "results-latency-pilot-run2.json")):
        path = RESULTS_TABLES / name
        if not path.is_file():
            raise PresentationError(f"missing {path}; the row-1 decision (D-009) is not committed")
        out[run] = json.loads(path.read_text(encoding="utf-8"))
    return out


def load_latency_rq4():
    """The committed RQ4 descriptive layer (D-014): run 2, the reported one.

    Run 1's artefact exists beside it with identical span reports and no
    deltas (its composition root handed refusal-path samples to
    arm_pair_delta and the sealed layer refused); it is not read here.
    """
    path = RESULTS_TABLES / "results-latency-pilot-rq4-run2.json"
    if not path.is_file():
        raise PresentationError(f"missing {path}; the RQ4 layer (D-014) is not committed")
    return json.loads(path.read_text(encoding="utf-8"))


def enforce_placement(fig, artefact):
    """RAISE if the authored canvas exceeds the measured landscape text block.

    `save()` reports placement for the whole suite; the latency artefacts are
    built to a stricter contract in which an unplaceable canvas is an error at
    build time, not a line in a report.
    """
    aw, ah = (float(v) for v in fig.get_size_inches())
    if aw > MAX_WIDTH_IN + 1e-6 or ah > MAX_HEIGHT_IN + 1e-6:
        raise PresentationError(
            f"{artefact}: authored {aw:.3f} x {ah:.3f} in exceeds the landscape text block "
            f"{MAX_WIDTH_IN:.3f} x {MAX_HEIGHT_IN:.3f} in (mproj.cls / mproj.log)"
        )
    print_render(artefact, "guard.placement", f"{aw:.3f} x {ah:.3f} in <= landscape")


def assert_no_text_overlap(fig, artefact, pad_px=0.0):
    """RAISE if any two text artists' rendered bounding boxes intersect.

    Numeric overflow checks cannot see two blocks overprinting inside the
    canvas -- FIG-1's per-arm strip and totals collided at 0.000 overflow.
    This walks every Text artist on the figure (titles, tick labels, in-panel
    numbers, legends), takes its window extent from the renderer, and refuses
    the figure on the first intersection. `pad_px` shrinks each box by that
    many pixels on each side before testing, so a hairline touch is not an
    overlap; the default is zero.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = []
    for artist in fig.findobj(matplotlib.text.Text):
        if not artist.get_visible() or not artist.get_text().strip():
            continue
        bb = artist.get_window_extent(renderer=renderer)
        if bb.width <= 0 or bb.height <= 0:
            continue
        boxes.append((artist.get_text(), bb, artist))
    for i in range(len(boxes)):
        ti, bi, _ = boxes[i]
        for j in range(i + 1, len(boxes)):
            tj, bj, _ = boxes[j]
            x0 = max(bi.x0, bj.x0) + pad_px
            y0 = max(bi.y0, bj.y0) + pad_px
            x1 = min(bi.x1, bj.x1) - pad_px
            y1 = min(bi.y1, bj.y1) - pad_px
            if x0 < x1 and y0 < y1:
                raise PresentationError(
                    f"{artefact}: text overlap -- {ti!r} intersects {tj!r} "
                    f"({x1 - x0:.1f} x {y1 - y0:.1f} px)"
                )
    print_render(artefact, "guard.text_overlap", f"none among {len(boxes)} text artists")


def fmt_ms3(value):
    """Three decimals, right-alignable; a width that would print as 0.000 says <0.001.

    Every latency figure prints IQR widths in one column, so the format is
    shared: rounding 0.0004 to "0.000" would state a zero the sealed record
    does not contain, while "<0.001" is exact about what the column can show.
    """
    return "<0.001" if 0 < value < 0.0005 else f"{value:.3f}"
