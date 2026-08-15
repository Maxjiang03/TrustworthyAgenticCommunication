"""TAB-9 -- instance-micro listing of all 143 scored cells (appendix).

One row per scored cell of campaign-confirmatory.json cells[]; every column is a
cell field rendered under its verbatim key with the source file's JSON literal.
Pure presentation (ADR 0048): nothing is selected, excluded, binned, or
computed beyond row counts. Two LAYOUT splits, both positional, neither a
selection:
  * by row index -- pages of at most ROWS_PER_PAGE rows; every row appears
    exactly once per column group and the page ranges are printed;
  * by column -- the 13 fields side by side measure 12.2 in, over the 9.7 in
    page width fixed by the C2 ruling (FIGURE_PLAN.md section 0.7b; enforced by
    acceptance_check.py MAX_WIDTH_IN and never resolved by scaling), so they are
    laid out in two column GROUPS that both repeat the four identity-key columns
    (family | subcase | arm | monitor_attached). Both groups list the same rows
    in the same order with the same page breaks; a cell's full 13-field record
    is read by aligning the two groups on the identity key.
"""

import json
import math

from _common import (
    ARM_ORDER,
    FONT_MIN_PT,
    GHOST,
    INK,
    MIDGREY,
    ORANGE,
    PAPER,
    PresentationError,
    load_campaign,
    load_tables,
    mpl_setup,
    plt,
    print_render,
    save,
)
from matplotlib.patches import Rectangle

ARTEFACT = "TAB-9"
STEM = "tab9_instance_micro"

# Column keys, verbatim from cells[], in the specified order. Excluded by the
# spec: reason_code_FOR_DIAGNOSIS_ONLY and correlation_id (the remaining
# unlisted fields scenario_id, note, timing_seams_recorded are not columns).
COLUMNS = (
    "family",
    "subcase",
    "arm",
    "monitor_attached",
    "reference_allow",
    "observed_forwarded",
    "admission_breach",
    "realized_harm",
    "false_block",
    "log_integrity_failure",
    "effect_count",
    "ledger_backed",
    "linkage",
)
EXCLUDED_BY_SPEC = ("reason_code_FOR_DIAGNOSIS_ONLY", "correlation_id")

# Column GROUPS -- a layout split of the 13 keys, not a selection. The identity
# key is repeated in every group; every other column appears in exactly one
# group; the spec order is kept inside a group (both checked at build time).
# Output files are <STEM>_<group>_p<page>.
IDENTITY_KEY = ("family", "subcase", "arm", "monitor_attached")
COLUMN_GROUPS = (
    (
        "A",
        IDENTITY_KEY
        + ("reference_allow", "observed_forwarded", "admission_breach", "realized_harm"),
    ),
    (
        "B",
        IDENTITY_KEY
        + ("false_block", "log_integrity_failure", "effect_count", "ledger_backed", "linkage"),
    ),
)
# C2 ruling: A4 landscape gives ~9.7 in of usable text width; a page wider than
# this would have to be scaled and would take 8 pt type below 8 pt. Checked here
# against the width _common.save() will write, and again by acceptance_check.py.
PAGE_WIDTH_MAX_IN = 9.7

# Header line breaks are inserted only AFTER an underscore (layout only): the
# two header lines concatenated read the key verbatim.
HEADER_LINES = {
    "monitor_attached": ("monitor_", "attached"),
    "reference_allow": ("reference_", "allow"),
    "observed_forwarded": ("observed_", "forwarded"),
    "admission_breach": ("admission_", "breach"),
    "realized_harm": ("realized_", "harm"),
    "false_block": ("false_", "block"),
    "log_integrity_failure": ("log_integrity_", "failure"),
    "effect_count": ("effect_", "count"),
    "ledger_backed": ("ledger_", "backed"),
}
LEFT_ALIGNED = ("family", "subcase", "arm", "linkage")

ROWS_PER_PAGE = 45  # layout constant; a page break by row index, not a selection
# Sort position of monitor_attached (JSON null < false < true). Within one
# (family, subcase) group only one of {null} or {false, true} ever occurs.
MONITOR_SORT = {None: 0, False: 1, True: 2}
SORT_RULE = (
    "sort key = (family asc, subcase asc [codepoint order], monitor_attached in "
    "order null < false < true, arm in _common.ARM_ORDER (section E.1 ladder))"
)


def literal(value):
    """Render a cell value as the source file's JSON literal (strings bare)."""
    if isinstance(value, bool) or value is None:
        return json.dumps(value)  # true / false / null
    return str(value)


def sort_key(cell):
    arm = cell.get("arm")
    mon = cell.get("monitor_attached")
    if arm not in ARM_ORDER:
        raise PresentationError(f"cell arm {arm!r} is not in ARM_ORDER")
    if mon not in MONITOR_SORT:
        raise PresentationError(f"cell monitor_attached {mon!r} is not null/false/true")
    return (str(cell["family"]), str(cell["subcase"]), MONITOR_SORT[mon], ARM_ORDER.index(arm))


def text_width_in(fig, renderer, s, weight="normal"):
    t = fig.text(0, 0, s, fontsize=FONT_MIN_PT, fontweight=weight)
    w = t.get_window_extent(renderer=renderer).width / fig.dpi
    t.remove()
    return w


def title_width_in(fig, renderer, s):
    """Width at the title size. The size is written as a literal on purpose so
    acceptance_check.py can decide every fontsize this file sets."""
    t = fig.text(0, 0, s, fontsize=FONT_MIN_PT + 1, fontweight="bold")
    w = t.get_window_extent(renderer=renderer).width / fig.dpi
    t.remove()
    return w


def wrap_to_width(fig, renderer, text, width_in, measure=text_width_in):
    """Greedy word wrap measured with the real renderer (deterministic)."""
    lines, cur = [], ""
    for word in text.split(" "):
        cand = word if not cur else cur + " " + word
        if cur and measure(fig, renderer, cand) > width_in:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def main():
    campaign = load_campaign()
    tables = load_tables()

    cells = campaign["cells"]
    for c in cells:
        missing = [k for k in COLUMNS if k not in c]
        if missing:
            raise PresentationError(f"cell lacks fields {missing}: {c}")
    rows = sorted(cells, key=sort_key)
    total = len(rows)

    print_render(ARTEFACT, "columns [M keys, spec order]", " | ".join(COLUMNS))
    print_render(ARTEFACT, "excluded_by_spec", ", ".join(EXCLUDED_BY_SPEC))
    print_render(ARTEFACT, "sort_rule", SORT_RULE)
    print_render(ARTEFACT, "rows_total [M len(cells)]", total)
    if total != 143:
        raise PresentationError(f"expected 143 scored cells, found {total}")
    if total != int(tables["cells_scored"]):
        raise PresentationError("campaign cells[] and tables cells_scored disagree")

    # Column groups: printed verbatim; checked to be identity key + a
    # spec-ordered subset each, and to cover every non-key column exactly once.
    n_groups = len(COLUMN_GROUPS)
    print_render(ARTEFACT, "column_groups [layout]", n_groups)
    print_render(
        ARTEFACT, "identity_key_columns [layout, repeated in every group]", " | ".join(IDENTITY_KEY)
    )
    non_key_seen = []
    for g, gcols in COLUMN_GROUPS:
        if (
            gcols[: len(IDENTITY_KEY)] != IDENTITY_KEY
            or tuple(k for k in COLUMNS if k in gcols) != gcols
        ):
            raise PresentationError(
                f"column group {g} is not the identity key + a spec-ordered subset of COLUMNS"
            )
        non_key_seen += list(gcols[len(IDENTITY_KEY) :])
        print_render(ARTEFACT, f"group_{g}.columns [layout]", " | ".join(gcols))
    if sorted(non_key_seen) != sorted(k for k in COLUMNS if k not in IDENTITY_KEY):
        raise PresentationError("column groups do not cover every non-key column exactly once")
    fb_group = next(g for g, gcols in COLUMN_GROUPS if "false_block" in gcols)

    # Per-family row counts, cross-checked against the sealed class_macro totals.
    fam_counts = {}
    for c in rows:
        fam_counts[c["family"]] = fam_counts.get(c["family"], 0) + 1
    for fam in sorted(fam_counts):
        macro_total = tables["class_macro"][fam]["quantities"]["observed_forwarded"]["total"]
        print_render(ARTEFACT, f"rows_family_{fam} [D count]", fam_counts[fam])
        print_render(ARTEFACT, f"class_macro_{fam}_total [M]", macro_total)
        if fam_counts[fam] != macro_total:
            raise PresentationError(f"family {fam}: listing rows != class_macro total")

    fb_rows = [c for c in rows if c["false_block"] is True]
    print_render(ARTEFACT, "false_block_true_rows [D count]", len(fb_rows))
    for c in fb_rows:
        print_render(
            ARTEFACT,
            "false_block_true_row [M]",
            f"{c['family']} | {c['subcase']} | {c['arm']} | "
            f"monitor_attached={literal(c['monitor_attached'])}",
        )

    # Footer texts (F3 fraction and F4 qualification read from the tables JSON).
    cov = tables["class_macro"]["F3"]["coverage"]
    f3_fraction = f"{cov['instantiated']}/{cov['defined']}"
    f4_qual = tables["class_macro"]["F4"]["qualification"]
    print_render(ARTEFACT, "footer.F3_fraction [M class_macro.F3.coverage]", f3_fraction)
    print_render(ARTEFACT, "footer.F4_qualification [M class_macro.F4.qualification]", f4_qual)
    footer_f3f4 = f"F3 rows: {f3_fraction} subcases instantiated. F4 rows: {f4_qual}"
    footer_notes = (
        "Values are the source file's JSON literals (true/false/null), nothing is "
        "recoded; exact per-cell records, no CI is defined for any entry. "
        f"false_block = true ({len(fb_rows)} rows, dashed frame) is a G-15(ii) "
        "fail-closed result of the monitor being genuinely absent under "
        "monitor_attached=false (FIGURE_PLAN.md section 0.3, D4); it is read within its "
        "own monitor configuration only and is not a capability-vs-OAuth comparison. "
        "Agreement is not shown here; it is stated in TAB-2 as 80 of 80 comparable "
        "entries agreed; 10 of the 90 base entries were NA and not comparable."
    )
    print_render(ARTEFACT, "footer.notes", footer_notes)
    group_desc = "; ".join(
        f"group {g} = {' | '.join(gcols[len(IDENTITY_KEY) :])}" for g, gcols in COLUMN_GROUPS
    )
    group_names = " and ".join(f"group {g}" for g, _ in COLUMN_GROUPS)
    footer_layout = (
        f"Layout: the {len(COLUMNS)} fields are laid out in {n_groups} column groups "
        f"({group_desc}), each repeating the identity-key columns "
        f"{' | '.join(IDENTITY_KEY)}, so that no page exceeds {PAGE_WIDTH_MAX_IN} in at "
        "8 pt (FIGURE_PLAN.md section 0.7b, C2: re-authored, not scaled). Both groups list "
        f"the same {total} rows in the same order with the same page breaks; a cell's full "
        f"record is read by aligning {group_names} on the identity key (same page number, "
        f"same row position). The false_block dashed frame appears in group {fb_group}."
    )
    print_render(ARTEFACT, "footer.layout_note", footer_layout)

    # Pages: consecutive chunks of ROWS_PER_PAGE by row index, the same for
    # every column group.
    n_pages = math.ceil(total / ROWS_PER_PAGE)
    print_render(ARTEFACT, "rows_per_page_max", ROWS_PER_PAGE)
    print_render(ARTEFACT, "pages [D ceil(total/rows_per_page)]", n_pages)
    pages = []
    for p in range(n_pages):
        chunk = rows[p * ROWS_PER_PAGE : (p + 1) * ROWS_PER_PAGE]
        first, last = p * ROWS_PER_PAGE + 1, p * ROWS_PER_PAGE + len(chunk)
        pages.append((chunk, first, last))
        print_render(ARTEFACT, f"page_{p + 1}.rows [D]", len(chunk))
        print_render(ARTEFACT, f"page_{p + 1}.range [D]", f"{first}-{last} of {total}")
    if sum(len(pg[0]) for pg in pages) != total:
        raise PresentationError("page split does not cover every row exactly once")

    # Every rendered row, one line each (all 13 fields; the column groups
    # re-lay these same values out, they add nothing).
    for i, c in enumerate(rows, start=1):
        print_render(ARTEFACT, f"row_{i:03d} [M]", " | ".join(literal(c[k]) for k in COLUMNS))

    # ---- geometry: measure with the real renderer, then draw ---------------
    mpl_setup()
    mfig = plt.figure(figsize=(1, 1))
    renderer = mfig.canvas.get_renderer()
    pad = 0.14
    col_w = {}
    for k in COLUMNS:  # measured once over every row: the key block is identical in every group
        head = HEADER_LINES.get(k, (k,))
        w = max(text_width_in(mfig, renderer, h, weight="bold") for h in head)
        for c in rows:
            w = max(w, text_width_in(mfig, renderer, literal(c[k])))
        col_w[k] = w + pad
    left, right = 0.25, 0.25
    tight_pad = plt.rcParams["savefig.pad_inches"]  # _common.save(): bbox_inches="tight"
    rh = 0.165
    head_h = 0.36  # two-line header
    bottom = 0.10

    # Per-group geometry and wrapped text, all measured before anything is drawn.
    layouts = []
    for g, gcols in COLUMN_GROUPS:
        table_w = sum(col_w[k] for k in gcols)
        fig_w = left + table_w + right
        page_w = fig_w + 2 * tight_pad
        print_render(ARTEFACT, f"group_{g}.table_width_in [layout]", f"{table_w:.2f}")
        print_render(
            ARTEFACT,
            f"group_{g}.page_width_in [layout, figure + 2 x savefig.pad_inches]",
            f"{page_w:.2f}",
        )
        if page_w > PAGE_WIDTH_MAX_IN:
            raise PresentationError(
                f"group {g} page would be {page_w:.2f} in wide, over the "
                f"{PAGE_WIDTH_MAX_IN} in C2 limit; re-author the columns, do not scale"
            )
        subtitle = (
            "Source: results/raw/campaign-confirmatory.json cells[] — one row per scored "
            f"cell, {len(COLUMNS)} fields under their verbatim keys, laid out in {n_groups} "
            f"column groups that each repeat the identity key ({' | '.join(IDENTITY_KEY)}); "
            f"this page shows group {g}; " + SORT_RULE
        )
        subtitle_lines = wrap_to_width(mfig, renderer, subtitle, table_w)
        footer_lines = (
            wrap_to_width(mfig, renderer, footer_f3f4, table_w)
            + [""]
            + wrap_to_width(mfig, renderer, footer_notes, table_w)
            + [""]
            + wrap_to_width(mfig, renderer, footer_layout, table_w)
        )
        page_titles = []
        for p, (chunk, first, last) in enumerate(pages, start=1):
            title = (
                f"TAB-9 — instance-micro listing of all {total} scored cells — "
                f"column group {g} of {n_groups} — page {p} of {n_pages} "
                f"(rows {first}–{last} of {total})"
            )
            page_titles.append(
                wrap_to_width(mfig, renderer, title, table_w, measure=title_width_in)
            )
        layouts.append((g, gcols, table_w, fig_w, subtitle_lines, footer_lines, page_titles))
    plt.close(mfig)

    for g, gcols, table_w, fig_w, subtitle_lines, footer_lines, page_titles in layouts:
        footer_h = 0.16 * len(footer_lines) + 0.25
        print_render(
            ARTEFACT, f"group_{g}.pages [D, the same row-index split as every group]", n_pages
        )
        rendered = 0
        for p, (chunk, first, last) in enumerate(pages, start=1):
            title_lines = page_titles[p - 1]
            top = 0.42 + 0.16 * (len(title_lines) - 1) + 0.15 * len(subtitle_lines)
            n = len(chunk)
            fig_h = top + head_h + n * rh + footer_h + bottom
            fig = plt.figure(figsize=(fig_w, fig_h))
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_xlim(0, fig_w)
            ax.set_ylim(0, fig_h)
            ax.axis("off")

            yt = fig_h - 0.12
            for line in title_lines:
                ax.text(
                    left, yt, line, fontsize=FONT_MIN_PT + 1, fontweight="bold", color=INK, va="top"
                )
                yt -= 0.16
            ys = fig_h - 0.34 - 0.16 * (len(title_lines) - 1)
            for line in subtitle_lines:
                ax.text(left, ys, line, fontsize=FONT_MIN_PT, color=INK, va="top")
                ys -= 0.15

            # Column x-positions.
            xs = {}
            x = left
            for k in gcols:
                xs[k] = x
                x += col_w[k]

            y_head_top = fig_h - top
            y_head_bot = y_head_top - head_h
            for k in gcols:
                lines = HEADER_LINES.get(k, (k,))
                hx = xs[k] + (0.04 if k in LEFT_ALIGNED else col_w[k] / 2)
                ha = "left" if k in LEFT_ALIGNED else "center"
                txt = "\n".join(lines)
                ax.text(
                    hx,
                    y_head_bot + 0.05,
                    txt,
                    fontsize=FONT_MIN_PT,
                    fontweight="bold",
                    color=INK,
                    ha=ha,
                    va="bottom",
                    linespacing=1.15,
                )
            ax.plot([left, left + table_w], [y_head_top, y_head_top], color=INK, lw=0.8)
            ax.plot([left, left + table_w], [y_head_bot, y_head_bot], color=INK, lw=0.8)

            prev_fam = None
            for i, c in enumerate(chunk):
                y0 = y_head_bot - (i + 1) * rh
                if i % 2 == 1:
                    ax.add_patch(
                        Rectangle(
                            (left, y0), table_w, rh, facecolor=GHOST, edgecolor="none", zorder=0
                        )
                    )
                if prev_fam is not None and c["family"] != prev_fam:
                    ax.plot([left, left + table_w], [y0 + rh, y0 + rh], color=MIDGREY, lw=0.6)
                prev_fam = c["family"]
                for k in gcols:
                    val = literal(c[k])
                    if k in LEFT_ALIGNED:
                        ax.text(
                            xs[k] + 0.04,
                            y0 + rh / 2,
                            val,
                            fontsize=FONT_MIN_PT,
                            color=INK,
                            ha="left",
                            va="center",
                        )
                    else:
                        ax.text(
                            xs[k] + col_w[k] / 2,
                            y0 + rh / 2,
                            val,
                            fontsize=FONT_MIN_PT,
                            color=INK,
                            ha="center",
                            va="center",
                        )
                    if k == "false_block" and c[k] is True:
                        ax.add_patch(
                            Rectangle(
                                (xs[k] + 0.03, y0 + 0.015),
                                col_w[k] - 0.06,
                                rh - 0.03,
                                facecolor=PAPER,
                                edgecolor=ORANGE,
                                lw=1.2,
                                linestyle=(0, (2, 1.5)),
                                zorder=0.5,
                            )
                        )
            y_tab_bot = y_head_bot - n * rh
            ax.plot([left, left + table_w], [y_tab_bot, y_tab_bot], color=INK, lw=0.8)

            yf = y_tab_bot - 0.14
            for line in footer_lines:
                ax.text(left, yf, line, fontsize=FONT_MIN_PT, color=INK, va="top")
                yf -= 0.16

            save(fig, f"{STEM}_{g}_p{p}", ARTEFACT)
            plt.close(fig)
            rendered += n
            print_render(ARTEFACT, f"group_{g}.page_{p}.rows [D]", n)
            print_render(ARTEFACT, f"group_{g}.page_{p}.range [D]", f"{first}-{last} of {total}")
        print_render(ARTEFACT, f"group_{g}.rows_rendered_total [D sum of pages]", rendered)
        if rendered != total:
            raise PresentationError(f"group {g} rendered {rendered} rows, expected {total}")


if __name__ == "__main__":
    main()
