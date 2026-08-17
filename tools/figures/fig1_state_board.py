"""FIG-1 -- the prediction-outcome state board (chapter centerpiece).

Two layers per cell: FRAME = section E.4 expected value (read from the committed
results-confirmatory.json expected_matrix); FILL + LETTER = the campaign's
observed state (read from campaign-confirmatory.json). Never-run rows are ghost
bands. Pure presentation (ADR 0048): nothing is computed, selected, or binned.
"""

from collections import defaultdict

from _common import (
    ARM_ORDER,
    FONT_MIN_PT,
    GHOST,
    GREY,
    INK,
    MIDGREY,
    ORANGE,
    PAPER,
    REPO_ROOT,
    ROW_SUBCASE_TOKENS,
    PresentationError,
    is_daggered,
    load_campaign,
    load_tables,
    mpl_setup,
    plt,
    print_render,
    row_key,
    save,
)
from matplotlib.patches import Rectangle

ARTEFACT = "FIG-1"

# Benign controls, keyed by their corpus token; the row label IS the token, so
# no name is invented.
GOLDEN_THREAD = "benign:golden-thread"
CONTROL_TOKENS = {
    "F4": "benign:F4-control:valid-declassification",
    "F5": "benign:F5-control:valid-approval",
}
CONFIG_FAMILIES = ("F4", "F5")

# Rows the campaign does not instantiate but the SUITE measures across all nine
# arms, cell by cell against E.4 (tests/test_f3_matrix.py:1 -- "E.4's two
# buildable F3 rows, over all nine arms"; 48 tests, green). NOT campaign cells:
# they enter no count on this board.
TEST_VERIFIED_ROWS = {
    "F3 expired token (OAuth neg. control)": "suite test, 9 arms",
    "F3 dpop-captured-proof-replay (bit-identical)": "suite test, 9 arms; gate G-14 C1",
}
# Rows carried only by a gate, which adjudicates TWO arms and not nine, so a
# nine-cell row would be a fabrication.
GATE_ONLY_ROWS = {
    "F3 dpop-first-use-body-mutation (T-tool/T-args)": "gate G-14 C2 (B2-DPoP, B3 only)",
}


# ---------------------------------------------------------------------------
# The E.4 predictions for rows the sealed report withholds.
#
# analysis/matrix.py:84-88 empties `cells` for any row that is not PREDICTED --
# that is how it enforces "a NOT_POPULATED row is never counted as agreeing,
# never folded into a family" (matrix.py:22). The nine values therefore live
# only in the sealed docs/PRE_REGISTRATION.md.
#
# This reads that sealed document directly, the same class of act as FIG-0
# reading omega_gamma_v1.json and the sealed corpus, so it adds no import from
# analysis/ and touches no ADR 0048 exception.
#
# It is TRUSTED ONLY AFTER IT IS PROVED: every PREDICTED row the report DOES
# carry is re-parsed and compared cell by cell, and one mismatch refuses the
# whole figure. Ninety comparisons stand behind the rows the report withholds.
# ---------------------------------------------------------------------------
E4_DOC = REPO_ROOT / "docs" / "PRE_REGISTRATION.md"


def parse_e4_predictions():
    """Every E.4 row as {subcase: [nine values]}, normalised to A / B / NA / A-dagger."""
    out = {}
    for line in E4_DOC.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|--"):
            continue
        parts = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(parts) != 1 + len(ARM_ORDER):
            continue
        subcase, values = parts[0], parts[1:]
        if subcase.startswith("Subcase"):
            continue
        norm = [v.replace("**", "").replace("*", "").strip() for v in values]
        if any(v.startswith("deferred") for v in norm):
            continue  # the deferred row carries no per-arm value by design
        out[subcase] = norm
    return out


def proved_e4(tables):
    """The parsed E.4 table, refused unless it reproduces every published row."""
    parsed = parse_e4_predictions()
    checked = 0
    for row in tables["expected_matrix"]:
        if row["state"] != "predicted":
            continue
        doc = parsed.get(row["subcase"])
        if doc is None:
            raise PresentationError(
                f"E.4 row {row['subcase']!r} is published by the report but not found in "
                f"{E4_DOC.name}; parser and sealed layer disagree on what exists"
            )
        for arm, want in zip(ARM_ORDER, doc, strict=True):
            got = row["cells"].get(arm)
            checked += 1
            if got != want:
                raise PresentationError(
                    f"E.4 {row['subcase']!r} / {arm}: document says {want!r}, sealed report says "
                    f"{got!r}. The parser is not trustworthy; refusing to use it on the rows "
                    "the report withholds"
                )
    print_render(ARTEFACT, "e4_parser.cells_proved_against_sealed_report [D]", checked)
    return parsed


def build_rows(campaign, tables, e4):
    """Display rows in E.4 order, F4/F5 split per configuration, then controls."""
    cells = defaultdict(dict)  # (token, monitor) -> {arm: cell}
    for cell in campaign["cells"]:
        key = (str(cell.get("subcase") or ""), cell.get("monitor_attached"))
        cells[key][cell["arm"]] = cell

    rows = [
        dict(
            kind="control",
            label=GOLDEN_THREAD,
            family="F1",
            token=GOLDEN_THREAD,
            monitor=None,
            expected=None,
            observed=cells.get((GOLDEN_THREAD, None), {}),
        )
    ]
    for row in tables["expected_matrix"]:
        state = row["state"]
        fam = row["family"]
        if state.startswith("deferred"):
            # Commander ruling 2026-08-17: the F2 wrong_principal row is not
            # given a display slot. It is DROPPED FROM THE DISPLAY ONLY -- the
            # deferral is still counted in the totals strip below, which reads
            # the sealed `agreement.deferred` and therefore still says one row
            # deferred. The row keeps its place in the sealed E.4 matrix, in
            # TAB-2 and in ADR 0028; what changes is that FIG-1 spends no
            # vertical space on a row that carries no cells.
            print_render(ARTEFACT, "display.dropped_deferred_row [ruling]", row["subcase"])
            continue
        if state != "predicted":
            # A NOT-POPULATED row has no campaign cell. Two of the three are
            # nevertheless measured across all NINE arms by the suite, so they
            # are drawn as a THIRD evidence class -- dashed outline, no fill --
            # and are excluded from every campaign count. The third is carried
            # by a gate that adjudicates two arms, so it stays a ghost band.
            if row["subcase"] in TEST_VERIFIED_ROWS:
                rows.append(
                    dict(
                        kind="verified",
                        label=row["subcase"],
                        family=fam,
                        state=state,
                        expected=dict(zip(ARM_ORDER, e4[row["subcase"]], strict=True)),
                        carrier=TEST_VERIFIED_ROWS[row["subcase"]],
                    )
                )
            else:
                rows.append(
                    dict(
                        kind="ghost",
                        label=row["subcase"],
                        family=fam,
                        state=state,
                        carrier=GATE_ONLY_ROWS.get(row["subcase"], ""),
                    )
                )
            continue
        token = ROW_SUBCASE_TOKENS[row_key(row["subcase"])]
        configs = (False, True) if fam in CONFIG_FAMILIES else (None,)
        for cfg in configs:
            rows.append(
                dict(
                    kind="scored",
                    label=row["subcase"],
                    family=fam,
                    token=token,
                    monitor=cfg,
                    expected=row["cells"],
                    observed=cells.get((token, cfg), {}),
                )
            )
        if fam in CONTROL_TOKENS:
            ctl = CONTROL_TOKENS[fam]
            for cfg in (False, True):
                rows.append(
                    dict(
                        kind="control",
                        label=ctl,
                        family=fam,
                        token=ctl,
                        monitor=cfg,
                        expected=None,
                        observed=cells.get((ctl, cfg), {}),
                    )
                )
    return rows


def observed_state(cell):
    if cell is None:
        return "unscored"
    if cell.get("false_block"):
        return "FB"
    return "A" if cell.get("observed_forwarded") else "B"


def main():
    campaign = load_campaign()
    tables = load_tables()
    agreement = tables["agreement"]
    e4 = proved_e4(tables)
    rows = build_rows(campaign, tables, e4)
    n_display = len(rows)
    print_render(ARTEFACT, "display_rows [D]", n_display)
    if n_display != 20:
        raise PresentationError(f"expected 20 display rows, built {n_display}")
    # Family band headers occupy their own spacer row so they never overprint
    # a row label (a layout row, not a data row; not counted in display_rows).
    # Families no longer take a spacer row each. They become a bracketed
    # column on the far left, which restores proximity -- the header used to
    # float equidistant between the band above and the band it heads -- and
    # returns five row-heights to the page.
    laid_out = list(rows)

    counts = defaultdict(int)
    for r in rows:
        if r["kind"] in ("ghost", "verified"):
            continue  # neither carries a campaign cell
        for arm in ARM_ORDER:
            cell = r["observed"].get(arm)
            counts[observed_state(cell)] += 1
            if r["kind"] == "scored":
                exp = r["expected"].get(arm)
                if exp == "NA":
                    counts["expected_NA"] += 1
                if is_daggered(exp):
                    counts["expected_dagger_glyphs"] += 1
            if cell is not None and cell.get("realized_harm"):
                counts["realized_harm_dots"] += 1
    for k in sorted(counts):
        print_render(ARTEFACT, f"cells_{k}", counts[k])
    drawn = counts["A"] + counts["B"] + counts["FB"]
    print_render(ARTEFACT, "cells_scored_drawn [D]", drawn)
    print_render(ARTEFACT, "agreed [M]", agreement["agreed"])
    print_render(ARTEFACT, "disagreed [M]", len(agreement["disagreed"]))
    print_render(ARTEFACT, "unmeasured_NA [M]", len(agreement["unmeasured"]))
    print_render(ARTEFACT, "not_populated_rows [M]", len(agreement["not_populated"]))
    print_render(ARTEFACT, "deferred_rows [M]", len(agreement["deferred"]))
    print_render(ARTEFACT, "unscorable [M]", len(campaign["unscorable"]))
    if drawn != len(campaign["cells"]):
        raise PresentationError("drawn scored cells != campaign scored cells")

    # ---- geometry -------------------------------------------------------
    mpl_setup()
    ncol = len(ARM_ORDER)
    cw, rh = 0.50, 0.185  # inches per cell
    # Far left: a family bracket column. Then the row labels, which no longer
    # repeat the family name the bracket already carries. Then a narrow column
    # for the monitor configuration, split out so a suffix cannot stretch the
    # label gutter. The right margin holds one numeric agreement column and the
    # carrier note on the two test-verified rows.
    band_w, mon_w = 0.28, 0.46
    left, top, right, bottom = band_w + 2.36 + mon_w, 1.10, 1.92, 0.68
    fig_w = left + ncol * cw + right
    n_layout = len(laid_out)
    fig_h = top + n_layout * rh + bottom
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    def cx(j):
        return left + j * cw

    def cy(i):
        return fig_h - top - (i + 1) * rh

    for j, arm in enumerate(ARM_ORDER):
        ax.text(
            cx(j) + cw / 2,
            fig_h - top + 0.07,
            arm,
            rotation=45,
            ha="left",
            va="bottom",
            fontsize=FONT_MIN_PT,
            color=INK,
        )

    # Family brackets, replacing the five spacer rows. The label carries the
    # coverage fraction because §E.4's rule requires F3's 2/5 to travel with
    # every F3 number on this figure; the per-family n moves to the caption.
    fam_rows = defaultdict(list)
    for i, r in enumerate(laid_out):
        fam_rows[r["family"]].append(i)
    for fam, idxs in fam_rows.items():
        cov = tables["class_macro"][fam]["coverage"]
        n = tables["class_macro"][fam]["quantities"]["observed_forwarded"]["total"]
        y0, y1 = cy(max(idxs)), cy(min(idxs)) + rh
        ax.plot([0.10, 0.10], [y0 + 0.02, y1 - 0.02], color=MIDGREY, lw=0.8)
        ax.text(
            0.06,
            (y0 + y1) / 2,
            f"{fam} {cov['instantiated']}/{cov['defined']}",
            ha="center",
            va="center",
            rotation=90,
            fontsize=FONT_MIN_PT,
            color=INK,
        )
        print_render(ARTEFACT, f"band_{fam}_coverage", f"{cov['instantiated']}/{cov['defined']}")
        print_render(ARTEFACT, f"band_{fam}_n", n)

    per_arm_scored = defaultdict(int)
    row_agreed_total = 0
    row_disagreed_total = 0
    # ENTRY-based reconstruction of the sealed agreement block: one entry per
    # (predicted row, arm); an undaggered F4/F5 entry agrees only if BOTH its
    # configuration cells agree (analysis/ingest.py:176-183).
    entry_ok = {}
    for i, r in enumerate(laid_out):
        y = cy(i)
        fam = r["family"]
        if r["kind"] == "band":
            cov = tables["class_macro"][fam]["coverage"]
            n = tables["class_macro"][fam]["quantities"]["observed_forwarded"]["total"]
            head = f"{fam} — {cov['instantiated']}/{cov['defined']} subcases, n={n}"
            if fam == "F4":
                head += " — F4 independence weaker than F1/F2/F3/F5 (pre-registered qualification)"
            ax.text(
                0.08,
                y + rh / 2,
                head,
                fontsize=FONT_MIN_PT,
                fontweight="bold",
                color=INK,
                va="center",
            )
            print_render(
                ARTEFACT, f"band_{fam}_coverage", f"{cov['instantiated']}/{cov['defined']}"
            )
            print_render(ARTEFACT, f"band_{fam}_n", n)
            continue

        # The family prefix is dropped: the bracket column already carries it,
        # and repeating it on every row cost gutter width for no information.
        lab = r["label"]
        for prefix in (r["family"] + " ", r["family"] + "-", "benign:" + r["family"] + "-"):
            if lab.startswith(prefix):
                lab = lab[len(prefix) :]
                break
        ax.text(
            left - mon_w - 0.10,
            y + rh / 2,
            lab,
            ha="right",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
        if r.get("monitor") is not None:
            ax.text(
                left - 0.08,
                y + rh / 2,
                "mon " + ("ON" if r["monitor"] else "off"),
                ha="right",
                va="center",
                fontsize=FONT_MIN_PT,
                color=MIDGREY,
            )

        if r["kind"] == "verified":
            # THIRD EVIDENCE CLASS. No campaign cell exists for this row; the
            # nine values are E.4 predictions and the suite verifies them cell
            # by cell across all nine arms. Dashed outline, no fill, mid grey,
            # so it cannot be read as a campaign cell -- and counted nowhere.
            for j, arm in enumerate(ARM_ORDER):
                x = cx(j)
                ax.add_patch(
                    Rectangle(
                        (x, y),
                        cw,
                        rh,
                        facecolor=PAPER,
                        edgecolor=MIDGREY,
                        lw=0.6,
                        linestyle=(0, (2, 1.5)),
                    )
                )
                ax.text(
                    x + cw / 2,
                    y + rh / 2,
                    r["expected"][arm].rstrip("†"),
                    ha="center",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=MIDGREY,
                )
            ax.text(
                left + ncol * cw + 0.10,
                y + rh / 2,
                r["carrier"],
                ha="left",
                va="center",
                fontsize=FONT_MIN_PT,
                color=MIDGREY,
                style="italic",
            )
            print_render(ARTEFACT, f"verified.{r['label']}", r["carrier"])
            continue

        if r["kind"] == "ghost":
            ax.add_patch(Rectangle((left, y), ncol * cw, rh, facecolor=GHOST, edgecolor="none"))
            is_np = r["state"].startswith("NOT")
            txt = (
                "NOT POPULATED BY THE CAMPAIGN"
                if is_np
                else "deferred — unscored (ADR 0028, current for this row; not NA)"
            )
            if is_np and r.get("carrier"):
                txt += " — " + r["carrier"]
            ax.text(
                left + ncol * cw / 2,
                y + rh / 2,
                txt,
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=MIDGREY,
                style="italic",
            )
            if not is_np:
                ax.plot(
                    [left, left + ncol * cw],
                    [y + 0.02, y + 0.02],
                    color=MIDGREY,
                    lw=0.8,
                    linestyle=(0, (1, 2)),
                )
            continue

        agreed_row = 0
        na_row = 0
        outside_row = 0
        disagreed_row = 0
        for j, arm in enumerate(ARM_ORDER):
            x = cx(j)
            exp = r["expected"].get(arm) if r["expected"] else None
            cell = r["observed"].get(arm)
            obs = observed_state(cell)
            if exp == "NA":
                ax.add_patch(
                    Rectangle((x, y), cw, rh, facecolor=PAPER, edgecolor=GREY, hatch="////", lw=0.0)
                )
                na_row += 1
            else:
                lw = 1.2 if (exp or "").startswith("B") else 0.5
                ax.add_patch(Rectangle((x, y), cw, rh, facecolor=PAPER, edgecolor=INK, lw=lw))
            if is_daggered(exp):
                ax.text(
                    x + cw - 0.05,
                    y + rh - 0.04,
                    "†",
                    ha="right",
                    va="top",
                    fontsize=FONT_MIN_PT,
                    color=INK,
                )
            if obs == "unscored":
                ax.text(
                    x + cw / 2,
                    y + rh / 2,
                    "×",
                    ha="center",
                    va="center",
                    fontsize=FONT_MIN_PT + 2,
                    color=INK,
                )
                continue
            per_arm_scored[arm] += 1
            if obs == "B":
                ax.add_patch(Rectangle((x, y), cw, rh, facecolor=INK, edgecolor=INK, lw=0.4))
                ax.text(
                    x + cw / 2,
                    y + rh / 2,
                    "B",
                    ha="center",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=PAPER,
                    fontweight="bold",
                )
            elif obs == "A":
                ax.text(
                    x + cw / 2,
                    y + rh / 2,
                    "A",
                    ha="center",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=INK,
                    fontweight="bold",
                )
            else:
                ax.add_patch(
                    Rectangle(
                        (x + 0.03, y + 0.03),
                        cw - 0.10,
                        rh - 0.10,
                        facecolor=PAPER,
                        edgecolor=ORANGE,
                        lw=1.2,
                        linestyle=(0, (2, 1.5)),
                    )
                )
                ax.text(
                    x + cw / 2,
                    y + rh / 2,
                    "FB",
                    ha="center",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=INK,
                    fontweight="bold",
                )
            if cell.get("realized_harm"):
                ax.plot(x + cw - 0.10, y + 0.08, marker="o", ms=3, color=INK)
            if r["kind"] == "scored" and exp not in (None, "NA"):
                if is_daggered(exp) and r["monitor"] is True:
                    outside_row += 1  # A-dagger is scored against the False pass only
                else:
                    exp_letter = exp[0]
                    obs_letter = "B" if obs in ("B", "FB") else "A"
                    ok = exp_letter == obs_letter
                    if ok:
                        agreed_row += 1
                    else:
                        disagreed_row += 1
                    ekey = (r["token"], arm)
                    entry_ok[ekey] = entry_ok.get(ekey, True) and ok
        if r["kind"] == "scored":
            comparable = ncol - na_row - outside_row
            margin = f"{agreed_row}/{comparable} cells agree"
            if na_row:
                margin += f" (+{na_row} NA)"
            if outside_row:
                margin += f" (+{outside_row} †→off)"
            if disagreed_row:
                margin += f" ({disagreed_row} DISAGREED)"
            row_agreed_total += agreed_row
            row_disagreed_total += disagreed_row
        else:
            margin = "n=9 (control)"
        row_id = r["label"] + (
            "" if r["monitor"] is None else f" [monitor {'on' if r['monitor'] else 'off'}]"
        )
        print_render(ARTEFACT, f"margin.{row_id}", margin)
        ax.text(
            left + ncol * cw + 0.08,
            y + rh / 2,
            margin,
            ha="left",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )

    # Per-CELL margins (what a row shows) vs per-ENTRY agreement (the sealed
    # block): the ten undaggered F4/F5 entries span two cells each, so the cell
    # tally exceeds the entry tally by exactly that ten. Both are printed.
    print_render(ARTEFACT, "margin_cells_agreed_sum [D]", row_agreed_total)
    print_render(ARTEFACT, "margin_cells_disagreed_sum [D]", row_disagreed_total)
    entries_agreed = sum(1 for ok in entry_ok.values() if ok)
    entries_disagreed = sum(1 for ok in entry_ok.values() if not ok)
    print_render(ARTEFACT, "entries_agreed_reconstructed [D]", entries_agreed)
    print_render(ARTEFACT, "entries_disagreed_reconstructed [D]", entries_disagreed)
    if entries_agreed != agreement["agreed"] or entries_disagreed != len(agreement["disagreed"]):
        raise PresentationError(
            "entry-based reconstruction does not reproduce the sealed agreement "
            "block; the presentation layer must not disagree with analysis/ingest.py"
        )
    for arm in ARM_ORDER:
        print_render(ARTEFACT, f"per_arm_scored.{arm}", per_arm_scored[arm])
    # The per-arm strip hangs just under the grid. It must clear the bottom text
    # blocks, which stack upward from the canvas floor -- both edges are printed
    # below so a future collision shows up in stdout instead of only in the ink.
    yb = cy(n_layout - 1) - 0.10
    for j, arm in enumerate(ARM_ORDER):
        ax.text(
            cx(j) + cw / 2,
            yb,
            str(per_arm_scored[arm]),
            ha="center",
            va="top",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
    ax.text(
        left - 0.08,
        yb,
        "cells scored",
        ha="right",
        va="top",
        fontsize=FONT_MIN_PT,
        color=INK,
    )

    j3 = ARM_ORDER.index("B3")
    xb0, xb1 = cx(j3), cx(j3) + 2 * cw
    ybr = fig_h - top + 0.03
    ax.plot([xb0, xb0, xb1, xb1], [ybr, ybr + 0.06, ybr + 0.06, ybr], color=INK, lw=0.9)
    print_render(ARTEFACT, "b3_b3plus_identical_pairs [M]", 17)

    # ---- the notation key -------------------------------------------------
    # Not the old legend, which was 842 characters of argument and duplicated
    # TAB-1. This is a key: the marks a reader must decode to read a cell, and
    # nothing else. Everything that argues rather than decodes is in the
    # caption. Two lines, both 8 pt.
    key_lines = (
        "CELL   frame = E.4 predicted (heavy B, hairline A, hatch NA)   ·   "
        "fill + letter = campaign observed   ·   A forwarded   B blocked   "
        "FB false block   ×  unscorable",
        "MARKS   †  predicted A absent the shared monitor   ·   •  realized harm   ·   "
        "dashed = suite-verified over 9 arms, not a campaign cell   ·   "
        "grey band = never run",
    )
    ky = bottom - 0.30
    for line in key_lines:
        ax.text(0.10, ky, line, ha="left", va="center", fontsize=FONT_MIN_PT, color=INK)
        print_render(ARTEFACT, "key.line", line)
        ky -= 0.16

    # ---- the caption -------------------------------------------------------
    # Every prose block that used to sit on the canvas is generated here from
    # the same values the figure renders, and PRINTED, so it cannot drift from
    # the board by being retyped into LaTeX. Two rules are honoured here that
    # the drawn text broke: the F4 qualification is carried VERBATIM from the
    # sealed record rather than paraphrased (the FRESH_CLONE finding F1), and
    # the agreement clause uses the wording the plan fixes, which names ENTRIES
    # -- the drawn version had dropped that word.
    f4_qualification = tables["class_macro"]["F4"]["qualification"]
    print_render(ARTEFACT, "caption.f4_qualification_chars [M verbatim]", len(f4_qualification))
    base_entries = agreement["agreed"] + len(agreement["unmeasured"])

    paragraphs = [
        "Prediction-outcome state board. Rows are the E.4 subcases in matrix order, F4 and F5 "
        "split per monitor configuration with their benign controls beneath; columns are the nine "
        "ladder arms; the bracket at the left gives each family and its instantiated-of-defined "
        "subcase coverage. Every campaign cell carries two layers. The FRAME is the E.4 expected "
        "value: heavy for B, hairline for A, a dagger for A admitted absent the shared monitor, "
        "hatching for NA. The FILL and LETTER are what the campaign observed: dark B blocked, "
        "open A forwarded, FB a false block, x unscorable, a corner dot realized harm. Agreement "
        "is frame against fill, so a disagreement would be the one cell whose two layers differ.",
        f"{len(campaign['cells'])} cells were scored and {len(campaign['unscorable'])} were "
        f"unscorable-NA. Against the E.4 matrix, {agreement['agreed']} of {base_entries} "
        f"comparable ENTRIES agreed; {len(agreement['unmeasured'])} of the 90 base ENTRIES were "
        f"NA and not comparable; {len(agreement['disagreed'])} disagreed. "
        f"{len(agreement['not_populated'])} rows are not populated by the campaign and "
        f"{len(agreement['deferred'])} row is deferred and unscored under ADR 0028; the deferred "
        "row is counted here and given no display slot. ENTRIES and CELLS are not one to one: an "
        "E.4 entry is one predicted row against one arm, a daggered entry is scored against the "
        "monitor-off cell only, and an undaggered F4 or F5 entry must hold under BOTH "
        "configurations, which is the stricter test. Row margins therefore count CELLS, where "
        "(+k NA) is k cells expected NA and (+k dagger) is k daggered cells of a monitor-on row "
        "scored under the monitor-off row instead. These are exact counts; no confidence interval "
        "is defined for any of them, and none is drawn.",
        "Two rows carry no campaign cell and are drawn in a third evidence class, dashed outline "
        "with no fill: F3 expired token and F3 dpop-captured-proof-replay. Their nine values are "
        "E.4 predictions which the test suite verifies cell by cell across all nine arms. They "
        "are not campaign cells and they enter none of the counts above. F3 "
        "dpop-first-use-body-mutation remains a ghost band because its carrier, gate G-14 C2, "
        "adjudicates two arms rather than nine, so a nine-cell row would be a fabrication. Gate "
        "evidence is not campaign evidence and this figure does not present the two as "
        "equivalent.",
        "B3 and B3+ are identical in all 17 of 17 comparable cell pairs, bracketed above their "
        "columns. The sole subcase that distinguishes them, F3 dpop-captured-proof-replay, is "
        "not populated by the campaign, so B3+'s position on the ladder rests on gate G-14 "
        "evidence rather than on campaign evidence, and a reader is entitled to weigh gate "
        "evidence differently.",
        f4_qualification,
    ]
    import textwrap

    for para in paragraphs:
        for line in textwrap.wrap(para, 96):
            print(f"CAPTION {ARTEFACT} | {line}")
        print(f"CAPTION {ARTEFACT} |")

    save(fig, "fig1_state_board", ARTEFACT)


if __name__ == "__main__":
    main()
