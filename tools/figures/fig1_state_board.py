"""FIG-1 -- the prediction-outcome state board (chapter centerpiece).

Two layers per cell: FRAME = section E.4 expected value (read from the committed
results-confirmatory.json expected_matrix); FILL + LETTER = the campaign's
observed state (read from campaign-confirmatory.json). Never-run rows are ghost
bands. Pure presentation (ADR 0048): nothing is computed, selected, or binned.
"""

from collections import defaultdict

from _common import (
    ARM_ORDER,
    BLUE,
    FONT_MIN_PT,
    GHOST,
    GREY,
    INK,
    MIDGREY,
    ORANGE,
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
    laid_out = []
    seen = set()
    for r in rows:
        if r["family"] not in seen:
            seen.add(r["family"])
            laid_out.append(dict(kind="band", family=r["family"]))
        laid_out.append(r)

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
    cw, rh = 0.50, 0.30  # inches per cell
    # The LEFT gutter carries the E.4 row labels, the longest of which
    # ("F4 sensitive egress, no declassification [monitor on]") runs past a
    # 2.45 in gutter and was drawn off the canvas -- the content overran by
    # 0.609 in on the left and 0.197 in below. Both were invisible for as long
    # as save() used bbox_inches="tight" and silently grew the page to cover
    # them. Widened to hold what is actually drawn.
    left, top, right, bottom = 3.10, 1.32, 1.85, 2.30
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
            fig_h - top + 0.10,
            arm,
            rotation=60,
            ha="left",
            va="bottom",
            fontsize=FONT_MIN_PT,
            color=INK,
        )

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

        lab = r["label"]
        if r.get("monitor") is not None:
            lab += "  [monitor " + ("on" if r["monitor"] else "off") + "]"
        ax.text(
            left - 0.08, y + rh / 2, lab, ha="right", va="center", fontsize=FONT_MIN_PT, color=INK
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
                    Rectangle((x, y), cw, rh, facecolor=PAPER, edgecolor=GREY, hatch="////", lw=0.4)
                )
                na_row += 1
            else:
                lw = 1.5 if (exp or "").startswith("B") else 0.5
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
                ax.add_patch(
                    Rectangle(
                        (x + 0.04, y + 0.04), cw - 0.08, rh - 0.08, facecolor=INK, edgecolor="none"
                    )
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
                    Rectangle(
                        (x + 0.05, y + 0.05),
                        cw - 0.10,
                        rh - 0.10,
                        facecolor=PAPER,
                        edgecolor=ORANGE,
                        lw=1.4,
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
        "scored cells per arm",
        ha="right",
        va="top",
        fontsize=FONT_MIN_PT,
        color=INK,
    )

    j3 = ARM_ORDER.index("B3")
    xb0, xb1 = cx(j3), cx(j3) + 2 * cw
    ybr = fig_h - top + 0.03
    ax.plot([xb0, xb0, xb1, xb1], [ybr, ybr + 0.05, ybr + 0.05, ybr], color=BLUE, lw=1)
    print_render(ARTEFACT, "b3_b3plus_identical_pairs [M]", 17)

    n_disagreed = len(agreement["disagreed"])
    n_comparable = agreement["agreed"] + n_disagreed
    totals = (
        f"153 cells run → {len(campaign['cells'])} scored + {len(campaign['unscorable'])} "
        f"unscorable-NA  |  §E.4 agreement: 90 ENTRIES (10 predicted rows × 9 arms, "
        f"footnote-† configuration rule) → {agreement['agreed']} of {n_comparable} comparable "
        f"agreed, {len(agreement['unmeasured'])} NA not comparable, {n_disagreed} disagreed  |  "
        f"{len(agreement['not_populated'])} rows not populated; {len(agreement['deferred'])} "
        f"row deferred"
    )
    disclosure = (
        "B3 = B3+ in all 17/17 comparable cell pairs; the sole distinguishing subcase "
        "(F3 dpop-captured-proof-replay) is NOT POPULATED BY THE CAMPAIGN; B3+'s ladder "
        "position rests on gate G-14 evidence, which is not campaign evidence."
    )
    legend = (
        "Frame = §E.4 expectation (heavy B, hairline A, † = A absent shared monitor, hatch NA). "
        "Fill = observed (■B blocked, A forwarded, FB false block, × unscorable, • realized harm). "
        f"Ghost band = never run. Disagreement mark ▲ ({n_disagreed} of {n_comparable} "
        "comparable entries) — shown so the display could have failed. Configs compared only "
        "within a row (G-15). ENTRIES and CELLS are not one-to-one: an §E.4 entry is one "
        "(predicted row, arm); a daggered entry (A†, the four B2 arms per F4/F5 attack row — "
        "ADR 0032) is scored against the monitor-off cell only, and an UNDAGGERED F4/F5 entry "
        "must hold under BOTH configurations — a stricter test, not a footnote. Row margins "
        'count CELLS; "(+k NA)" = k cells expected NA (unscorable), "(+k †→off)" = k daggered '
        "cells of this monitor-on row that are scored under the monitor-off row instead. "
        "Exact counts; no CI is defined."
    )
    import textwrap

    # The three bottom blocks used to sit at hand-tuned y constants, so the
    # legend ran off the bottom of the canvas whenever its wrapped line count
    # grew -- and bbox_inches="tight" hid that by enlarging the page. Stack them
    # UPWARD from the canvas floor instead, driven by the line counts actually
    # produced, and print the gutter the text needs so a mismatch against the
    # authored `bottom` is visible rather than silent.
    wrap_chars = 138  # ~7.7 in at 8 pt DejaVu Sans; canvas holds 9.3 in
    line_h = FONT_MIN_PT * 1.26 / 72.0  # 8 pt on ~10 pt leading, in inches
    pad = 0.10
    blocks = [  # bottom-most first
        (0.26, textwrap.wrap(legend, wrap_chars - 3), INK, "▲"),
        (0.08, textwrap.wrap(disclosure, wrap_chars), BLUE, None),
        (0.08, textwrap.wrap(totals, wrap_chars), INK, None),
    ]
    y = pad
    for x, lines, colour, bullet in blocks:
        y += line_h * len(lines)
        if bullet:
            ax.text(0.08, y, bullet, fontsize=FONT_MIN_PT, color=VERMILLION, va="top")
        ax.text(x, y, "\n".join(lines), fontsize=FONT_MIN_PT, color=colour, va="top")
        y += pad
    print_render(ARTEFACT, "layout.bottom_gutter_required_in", f"{y:.3f}")
    print_render(ARTEFACT, "layout.bottom_gutter_authored_in", f"{bottom:.3f}")
    strip_floor = yb - line_h
    print_render(ARTEFACT, "layout.per_arm_strip_floor_in", f"{strip_floor:.3f}")
    print_render(ARTEFACT, "layout.bottom_text_ceiling_in", f"{y - pad:.3f}")
    if strip_floor < y - pad:
        raise PresentationError(
            f"the per-arm strip (floor {strip_floor:.3f} in) overlaps the bottom "
            f"text blocks (ceiling {y - pad:.3f} in); increase `bottom`"
        )

    save(fig, "fig1_state_board", ARTEFACT)


if __name__ == "__main__":
    main()
