"""FIG-1 -- the prediction-outcome state board (chapter centerpiece).

A cell's FILL + LETTER are the campaign's observed state (read from
campaign-confirmatory.json). Section E.4's expected value (read from the
committed results-confirmatory.json expected_matrix) is NOT drawn as a second
layer over every cell; it is drawn only where it was not met, as the vermillion
disagreement mark. Rows the campaign never populated are drawn in a third
evidence class -- dashed outline, a lighter blue for a predicted block, counted
nowhere. Pure presentation (ADR 0048): nothing is computed, selected, or binned.
"""

from collections import defaultdict

from _common import (
    ARM_ORDER,
    BLOCKED,
    FALSE_BLOCK,
    FONT_MIN_PT,
    GHOST,
    HATCH,
    INK,
    MIDGREY,
    OFF_BLOCKED,
    OFF_CAMPAIGN,
    PAPER,
    REPO_ROOT,
    ROW_SUBCASE_TOKENS,
    VERMILLION,
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
from matplotlib.patches import Circle, Polygon, Rectangle

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
    "F3 expired token (OAuth neg. control)": "suite test 9 arms",
    "F3 dpop-captured-proof-replay (bit-identical)": "suite test 9 arms + G-14 C1",
}
# Carried by a gate rather than by the suite. The E.4 predictions are drawn for
# all nine arms, but ONLY the arms the gate actually adjudicates are marked as
# adjudicated -- the scope is read off the gate's own imports
# (smoke/g14/fixture.py:21,23 import B2ExchangeTaskDPoPArm and B3Arm and nothing
# else), so the figure never implies the gate ruled on seven arms it never
# instantiated.
GATE_ADJUDICATED_ROWS = {
    "F3 dpop-first-use-body-mutation (T-tool/T-args)": (
        "gate G-14 C2",
        ("B2-exchange-task-DPoP", "B3"),
    ),
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
            # by a gate that instantiated two arms, so its nine predictions are
            # drawn with a corner tick on exactly those two: the row shows what
            # E.4 predicts without implying the gate ruled on all nine.
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
            elif row["subcase"] in GATE_ADJUDICATED_ROWS:
                carrier, arms = GATE_ADJUDICATED_ROWS[row["subcase"]]
                rows.append(
                    dict(
                        kind="verified",
                        label=row["subcase"],
                        family=fam,
                        state=state,
                        expected=dict(zip(ARM_ORDER, e4[row["subcase"]], strict=True)),
                        carrier=f"{carrier} · {len(arms)}/{len(ARM_ORDER)} arms",
                        adjudicated=set(arms),
                    )
                )
            else:
                rows.append(
                    dict(kind="ghost", label=row["subcase"], family=fam, state=state, carrier="")
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
    band_w, mon_w = 0.46, 0.46
    left, top, right, bottom = band_w + 2.40 + mon_w, 1.10, 1.70, 0.68
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

    def monitor_icon(mx, my, on):
        """The shared monitor's presence, drawn rather than spelled.

        Two rows of every F4/F5 scenario differ ONLY by whether the monitor was
        attached, and "mon off" / "mon ON" spent a text column saying so on
        every one of them. A screen with a lens reads at a glance and, being
        geometry rather than type, is unaffected by the 8 pt floor. Filled with
        an open lens = attached; hollow and struck through = absent. The two
        differ in fill, in the slash, and in overall darkness, so the pair
        survives greyscale and needs no hue at all.
        """
        w, h = 0.15, 0.095
        ax.add_patch(
            Rectangle(
                (mx - w / 2, my - h / 2 + 0.012),
                w,
                h,
                facecolor=INK if on else PAPER,
                edgecolor=INK,
                lw=0.7,
            )
        )
        ax.plot(
            [mx - 0.035, mx + 0.035],
            [my - h / 2 + 0.008, my - h / 2 + 0.008],
            color=INK,
            lw=0.9,
            solid_capstyle="butt",
        )
        if on:
            ax.add_patch(Circle((mx, my + 0.012), 0.022, facecolor=PAPER, edgecolor="none"))
        else:
            ax.plot(
                [mx - w / 2 + 0.012, mx + w / 2 - 0.012],
                [my - h / 2 + 0.024, my + h / 2],
                color=INK,
                lw=0.9,
                solid_capstyle="butt",
            )

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

    # The B fill runs edge to edge, so a run of blocked cells used to merge
    # into one undifferentiated slab in which no reader could count a cell.
    # Hairline paper rules on every column boundary, drawn over the fills,
    # restore cell identity without reintroducing the inset that made each cell
    # read as a button.
    def draw_grid_rules(rows_drawn):
        # Hairline paper rules on every cell boundary, drawn over the fills.
        # Column rules alone left runs of blocked cells merging vertically; a
        # reader could not count a cell in either direction.
        top_y, bottom_y = cy(0) + rh, cy(rows_drawn - 1)
        for j in range(len(ARM_ORDER) + 1):
            ax.plot(
                [cx(j), cx(j)],
                [bottom_y, top_y],
                color=PAPER,
                lw=0.7,
                zorder=3,
                solid_capstyle="butt",
            )
        for i in range(rows_drawn + 1):
            yy = cy(i - 1) if i else top_y
            ax.plot(
                [cx(0), cx(len(ARM_ORDER))],
                [yy, yy],
                color=PAPER,
                lw=0.7,
                zorder=3,
                solid_capstyle="butt",
            )

    # Family brackets, replacing the five spacer rows. The label carries the
    # coverage fraction because §E.4's rule requires F3's 2/5 to travel with
    # every F3 number on this figure; the per-family n moves to the caption.
    # The golden thread is the STUDY-WIDE benign control, not an F1 subcase; it
    # is carried under F1 only so it lands at the top of the board. Enclosing it
    # in F1's rules would say it is one of the three subcases the 3/3 counts,
    # so it sits above the block with the table's head rule over it. The F4/F5
    # controls stay inside their own blocks, which is where they belong.
    fam_rows = defaultdict(list)
    for i, r in enumerate(laid_out):
        if r["label"] == GOLDEN_THREAD:
            ax.plot([0.10, cx(ncol)], [cy(i) + rh] * 2, color=INK, lw=0.9, zorder=4)
            continue
        fam_rows[r["family"]].append(i)
    for fam, idxs in fam_rows.items():
        cov = tables["class_macro"][fam]["coverage"]
        n = tables["class_macro"][fam]["quantities"]["observed_forwarded"]["total"]
        y0, y1 = cy(max(idxs)), cy(min(idxs)) + rh
        # A rule above and below the block, run from the family label to the end
        # of the grid, so a reader sees which subcases the family CONTAINS.
        for yy in (y0, y1):
            ax.plot([0.10, cx(ncol)], [yy, yy], color=INK, lw=0.9, zorder=4)
        ax.text(
            0.10,
            (y0 + y1) / 2,
            fam,
            ha="left",
            va="center",
            fontsize=FONT_MIN_PT + 1,
            color=INK,
            fontweight="bold",
        )
        ax.text(
            0.10,
            (y0 + y1) / 2 - 0.135,
            f"{cov['instantiated']}/{cov['defined']}",
            ha="left",
            va="center",
            fontsize=FONT_MIN_PT,
            color=MIDGREY,
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
            monitor_icon(left - 0.08 - 0.075, y + rh / 2, r["monitor"])

        if r["kind"] == "verified":
            # THIRD EVIDENCE CLASS. No campaign cell exists for this row; the
            # nine values are E.4 predictions and the suite verifies them cell
            # by cell across all nine arms. Dashed outline, no fill, mid grey,
            # so it cannot be read as a campaign cell -- and counted nowhere.
            for j, arm in enumerate(ARM_ORDER):
                x = cx(j)
                letter = r["expected"][arm].rstrip("†")
                # An E.4 'B' here takes the SAME blue one step lighter. Leaving
                # these rows unfilled made the one thing worth seeing -- that
                # captured-proof-replay is predicted blocked at B3+ and nowhere
                # else -- invisible against nine grey letters. Filling them in
                # the measured blue instead would have said the campaign
                # measured them, so the fill is the same hue at a lighter step
                # and the dashed outline stays: same STATE, different EVIDENCE.
                blocked_pred = letter == "B"
                ax.add_patch(
                    Rectangle(
                        (x, y),
                        cw,
                        rh,
                        facecolor=OFF_BLOCKED if blocked_pred else PAPER,
                        edgecolor=OFF_CAMPAIGN,
                        lw=0.6,
                        linestyle=(0, (2, 1.5)),
                    )
                )
                ax.text(
                    x + cw / 2,
                    y + rh / 2,
                    letter,
                    ha="center",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=PAPER if blocked_pred else OFF_CAMPAIGN,
                )
                if arm in r.get("adjudicated", ()):
                    # A filled corner tick: this arm, and only this arm, was
                    # actually adjudicated by the named carrier. INK on every
                    # cell, filled or not. Flipping it to PAPER on a blue fill
                    # bought contrast at the cost of the mark no longer matching
                    # the black square the key shows -- two colours read as two
                    # different marks. INK on OFF_BLOCKED still separates by 71
                    # of 255 in greyscale, which is enough.
                    ax.add_patch(
                        Rectangle(
                            (x + cw - 0.055, y + rh - 0.045),
                            0.04,
                            0.032,
                            facecolor=INK,
                            edgecolor="none",
                        )
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
                    Rectangle(
                        (x, y), cw, rh, facecolor=PAPER, edgecolor=HATCH, hatch="////", lw=0.0
                    )
                )
                na_row += 1
            else:
                # Uniform hairline. The frame USED to carry E.4's prediction by
                # weight -- heavy for B, hairline for A -- and that channel was
                # measured and found half blind: a BLOCKED fill covers its own
                # cell, and the paper grid rule painted over the boundary at
                # zorder 3 erases a 0.5 pt frame entirely while leaving about
                # 0.25 pt of a 1.2 pt one. So "predicted B" read as a faint dark
                # edge and "predicted A" read as its ABSENCE -- meaning the one
                # thing the board must be able to show, a cell where E.4 said A
                # and the campaign did B, was signalled by nothing being there.
                # The prediction layer now speaks through the explicit
                # disagreement mark below instead (Commander ruling 2026-08-17).
                ax.add_patch(Rectangle((x, y), cw, rh, facecolor=PAPER, edgecolor=INK, lw=0.5))
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
                ax.add_patch(
                    Rectangle((x, y), cw, rh, facecolor=BLOCKED, edgecolor=BLOCKED, lw=0.4)
                )
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
                    Rectangle((x, y), cw, rh, facecolor=FALSE_BLOCK, edgecolor=INK, lw=1.2)
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
                # Bottom-LEFT, so it never crowds the dagger at top-right, and
                # in the fill's own contrast colour: drawn in INK on a blocked
                # cell it would have been invisible. No campaign cell is both
                # blocked and harmful today, but the code no longer relies on
                # that holding.
                ax.plot(
                    x + 0.075,
                    y + 0.05,
                    marker="o",
                    ms=2.4,
                    color=PAPER if obs in ("B",) else INK,
                )
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
                        # THE DISAGREEMENT MARK. Drawn from the SAME predicate
                        # that feeds this row's margin and the totals strip, so
                        # a mark and a count can never tell different stories.
                        # Above the fill AND above the paper grid rules, which
                        # is the whole lesson of the frame it replaces: a
                        # signal that another layer can paint over is not a
                        # signal. Vermillion appears nowhere else on the board.
                        ax.add_patch(
                            Rectangle(
                                (x, y),
                                cw,
                                rh,
                                facecolor="none",
                                edgecolor=VERMILLION,
                                lw=1.8,
                                zorder=5,
                            )
                        )
                        ax.add_patch(
                            Polygon(
                                [
                                    (x, y + rh),
                                    (x + 0.13, y + rh),
                                    (x, y + rh - 0.09),
                                ],
                                closed=True,
                                facecolor=VERMILLION,
                                edgecolor="none",
                                zorder=5,
                            )
                        )
                        print_render(
                            ARTEFACT,
                            f"DISAGREEMENT [M] {r['label']} / {arm}",
                            f"E.4 predicts {exp}, campaign observed {obs}",
                        )
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
    draw_grid_rules(len(laid_out))
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
    # The bracket is the MANDATED on-figure B3/B3+ disclosure, so it has to say
    # something: an unlabelled mark discharges nothing and the caption cannot
    # stand in for a rule that specifies the figure. Three words, in the right
    # margin the header row leaves empty; the caption carries the consequence.
    ax.text(
        xb1 + 0.08,
        ybr + 0.06,
        "17/17 pairs identical",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=MIDGREY,
        style="italic",
    )
    print_render(ARTEFACT, "b3_b3plus_identical_pairs [M]", 17)

    # ---- the notation key -------------------------------------------------
    # Not the old legend, which was 842 characters of argument and duplicated
    # TAB-1. This is a key: the marks a reader must decode to read a cell, and
    # nothing else. Everything that argues rather than decodes is in the
    # caption. Two lines, both 8 pt.
    # A key made of the marks themselves, not sentences about them. Each swatch
    # is drawn exactly as the matrix draws it, with a one- or two-token label.
    def swatch(x, kind):
        w, h = 0.26, 0.135
        yy = ky - h / 2
        if kind == "B":
            ax.add_patch(Rectangle((x, yy), w, h, facecolor=BLOCKED, edgecolor=BLOCKED, lw=1.2))
            ax.text(x + w / 2, ky, "B", ha="center", va="center", fontsize=FONT_MIN_PT, color=PAPER)
        elif kind == "A":
            ax.add_patch(Rectangle((x, yy), w, h, facecolor=PAPER, edgecolor=INK, lw=0.5))
            ax.text(x + w / 2, ky, "A", ha="center", va="center", fontsize=FONT_MIN_PT, color=INK)
        elif kind == "FB":
            ax.add_patch(Rectangle((x, yy), w, h, facecolor=FALSE_BLOCK, edgecolor=INK, lw=1.2))
            ax.text(
                x + w / 2,
                ky,
                "FB",
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=INK,
            )
        elif kind == "NA":
            ax.add_patch(
                Rectangle((x, yy), w, h, facecolor=PAPER, edgecolor=HATCH, hatch="////", lw=0.0)
            )
            ax.text(x + w / 2, ky, "×", ha="center", va="center", fontsize=FONT_MIN_PT, color=INK)
        elif kind == "pred":
            # Drawn as a predicted B, because that is the variant a reader has
            # to be able to tell from a measured B at a glance.
            ax.add_patch(
                Rectangle(
                    (x, yy),
                    w,
                    h,
                    facecolor=OFF_BLOCKED,
                    edgecolor=OFF_CAMPAIGN,
                    lw=0.6,
                    linestyle=(0, (2, 1.5)),
                )
            )
            ax.text(
                x + w / 2,
                ky,
                "B",
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=PAPER,
            )
        elif kind == "DIS":
            ax.add_patch(Rectangle((x, yy), w, h, facecolor=PAPER, edgecolor=INK, lw=0.5))
            ax.text(x + w / 2, ky, "B", ha="center", va="center", fontsize=FONT_MIN_PT, color=INK)
            ax.add_patch(
                Rectangle((x, yy), w, h, facecolor="none", edgecolor=VERMILLION, lw=1.8, zorder=5)
            )
            ax.add_patch(
                Polygon(
                    [(x, yy + h), (x + 0.075, yy + h), (x, yy + h - 0.055)],
                    closed=True,
                    facecolor=VERMILLION,
                    edgecolor="none",
                    zorder=5,
                )
            )
        elif kind == "ghost":
            ax.add_patch(Rectangle((x, yy), w, h, facecolor=GHOST, edgecolor="none"))
        return x + w

    ky = bottom - 0.30
    kx = 0.10
    # The ghost swatch is CONDITIONAL. Every not-populated row now carries an
    # off-campaign carrier, so no ghost band is drawn and a "never run" key
    # would send the reader hunting for a state that is not on the board. It
    # returns by itself the moment a row without a carrier appears.
    cells_compared = row_agreed_total + row_disagreed_total
    print_render(ARTEFACT, "key.cells_compared [D]", cells_compared)
    key_items = [
        ("B", "blocked"),
        ("A", "forwarded"),
        ("FB", "false block"),
        ("NA", "not applicable"),
        ("pred", "predicted off-campaign"),
        ("DIS", f"disagrees with E.4 — {row_disagreed_total} of {cells_compared}"),
    ]
    if any(r["kind"] == "ghost" for r in laid_out):
        key_items.append(("ghost", "never run"))
    print_render(ARTEFACT, "key.ghost_swatch_drawn [D]", ("ghost", "never run") in key_items)

    # Advance by the width the text ACTUALLY renders at, not by a per-character
    # guess. The guess has now failed twice on this key -- once when em-dashes
    # and capitals overran a neighbour's swatch, and once when the eight-letter
    # word "unmarked" ran straight into its own label -- because a fixed factor
    # cannot be right for both "•" and "unmarked" in a proportional serif.
    def place(s, x, **kw):
        t = ax.text(x, ky, s, ha="left", va="center", fontsize=FONT_MIN_PT, **kw)
        return x + t.get_window_extent(renderer=fig.canvas.get_renderer()).width / fig.dpi

    for kind, label in key_items:
        kx = place(label, swatch(kx, kind) + 0.07, color=INK) + 0.26

    ky -= 0.17
    kx = 0.10
    # The monitor icons are named here, since they replace words on the rows.
    # Both in one entry, in the order the words then run, so the two glyphs are
    # read against each other rather than as two unrelated marks.
    monitor_icon(kx + 0.075, ky, True)
    monitor_icon(kx + 0.075 + 0.19, ky, False)
    kx = place("shared monitor attached / absent", kx + 0.42, color=MIDGREY) + 0.26
    for mark, label in (
        ("†", "predicted A absent the monitor; scored on that row"),
        ("•", "realized harm"),
        ("▪", "arm adjudicated by the carrier"),
    ):
        kx = place(mark, kx, color=INK) + 0.09
        kx = place(label, kx, color=MIDGREY) + 0.24

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
        "split per monitor configuration with their benign controls beneath, the icon in the "
        "left gutter marking whether the shared monitor was attached; columns are the nine "
        "ladder arms; the rules at the left enclose each family and give its "
        "instantiated-of-defined subcase coverage. A cell's FILL and LETTER are what the campaign "
        "observed: a filled blue cell lettered B is a block, an open cell lettered A a forwarded "
        "request, a filled amber cell lettered FB a false block, x over hatching an unscorable "
        "cell, and a corner dot realized harm. The fills are separated for colour-vision "
        "deficiency and in lightness, so the states stay distinct in a monochrome print and no "
        "state is carried by hue alone. E.4's PREDICTION is not drawn as a second layer over the "
        "cell; it is drawn only where it was not met. A cell that disagrees with E.4 carries a "
        "vermillion border and corner wedge, above every other layer, and vermillion appears "
        "nowhere else on the board. An unmarked cell therefore matched the prediction, with one "
        "exception the key also states: a daggered cell of a monitor-on row shows B against a "
        "predicted A and is nevertheless not a disagreement, because a daggered entry is scored "
        "on the monitor-off row instead. This replaces an earlier encoding in which the cell's "
        "border weight carried the prediction. That channel was measured and found half blind -- "
        "a filled cell covers its own border, and the hairline rules drawn over every cell "
        "boundary erase a light border entirely -- so the case the board most needs to be able "
        "to show, E.4 predicting A where the campaign blocked, was signalled by the absence of a "
        "mark rather than the presence of one.",
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
        "Three rows carry no campaign cell and are drawn in a third evidence class, under a "
        "dashed outline. Their nine values are E.4 predictions, and the row's right margin names "
        "what has actually tested each one. A predicted block is filled in the same blue as a "
        "measured one, one step lighter: the state is the same, the evidence is not, and the "
        "distinction is carried by lightness and by the dashed outline rather than by hue, so it "
        "survives a monochrome print. Reading these rows as filled cells is what makes the "
        "pattern visible at all -- that dpop-captured-proof-replay is predicted blocked at B3+ "
        "and at no earlier arm, which is B3+'s entire reason to occupy a rung. F3 expired token "
        "and F3 dpop-captured-proof-replay are verified cell by cell across all nine arms by the "
        "test suite. F3 dpop-first-use-body-mutation is not: its carrier, gate G-14 C2, "
        "instantiated two arms rather than nine, and a corner tick marks exactly those two, so "
        "the seven unticked cells are predictions no evidence of any class has touched. Gate "
        "evidence is not campaign evidence, a suite test is neither, and none of these values "
        "enters any count above; the figure does not present the three classes as equivalent.",
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
