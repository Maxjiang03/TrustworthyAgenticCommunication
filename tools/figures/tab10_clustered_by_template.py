"""TAB-10 -- clustered_by_template: 6 quantities x 13 templates (appendix listing).

Pure presentation (ADR 0048): every count / total / rate is read verbatim from
results-confirmatory.json `clustered_by_template`; the row order is the stored
key order; row and column labels are the JSON keys verbatim. The header carries
the F3 2/5 fraction (built from class_macro.F3.coverage) and the pre-registered
F4 qualification verbatim (class_macro.F4.qualification, cross-checked against
results-confirmatory.md line 69). Nothing is computed, selected, or binned; the
only arithmetic is printed cross-check sums against the sealed record.
"""

import re

from _common import (
    FONT_MIN_PT,
    GREY,
    INK,
    MIDGREY,
    RESULTS_TABLES,
    PresentationError,
    load_campaign,
    load_tables,
    mpl_setup,
    plt,
    print_render,
    save,
)
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

ARTEFACT = "TAB-10"
STEM = "tab10_clustered_by_template"

# The pre-registered wording rules this artefact must obey (FIGURE_PLAN.md §E).
BANNED_STEM = "generali"  # generalize / generalise / -ization / -isation: nowhere
F3_FRACTION_PHRASE = "2/5 subcases"  # travels with every F3 number
F4_MARK = "¶"  # row marker pointing at the header's verbatim F4 qualification

# Layout (inches). Every text is FONT_MIN_PT or FONT_MIN_PT + 1 (title only).
LINE = 0.155  # body line pitch at 8 pt
ROW_H = 0.21  # table row height
PAD_X = 0.14  # data-column padding (both sides together)
LABEL_PAD = 0.20
MARGIN = 0.15

_FP = FontProperties(family="DejaVu Sans", size=FONT_MIN_PT)
_FP_BOLD = FontProperties(family="DejaVu Sans", size=FONT_MIN_PT, weight="bold")


def text_width(s, fp=_FP):
    """Rendered width in inches of one line at the given font (TextPath metric)."""
    if not s:
        return 0.0
    return TextPath((0, 0), s, prop=fp).get_extents().width / 72.0


def wrap_words(text, width_in, fp=_FP):
    """Greedy word wrap by measured width; lossless on single-spaced text."""
    if " ".join(text.split()) != text:
        raise PresentationError("wrap would alter whitespace of a verbatim string")
    lines, cur = [], ""
    for word in text.split(" "):
        cand = f"{cur} {word}" if cur else word
        if not cur or text_width(cand, fp) <= width_in:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def wrap_key(key, width_in, fp=_FP_BOLD):
    """Break a JSON key only after underscores; characters are unchanged."""
    tokens = [t for t in re.split(r"(?<=_)", key) if t]
    lines, cur = [], ""
    for tok in tokens:
        cand = cur + tok
        if not cur or text_width(cand, fp) <= width_in:
            cur = cand
        else:
            lines.append(cur)
            cur = tok
    if cur:
        lines.append(cur)
    if "".join(lines) != key:
        raise PresentationError(f"header wrap altered the key {key!r}")
    return lines


def main():
    tables = load_tables()
    campaign = load_campaign()
    cbt = tables["clustered_by_template"]
    class_macro = tables["class_macro"]

    # ---- shape [M] ------------------------------------------------------
    quantities = list(cbt.keys())  # stored order
    templates = list(cbt[quantities[0]].keys())  # stored order
    for q in quantities:
        if list(cbt[q].keys()) != templates:
            raise PresentationError(
                f"quantity {q!r} carries a different template key set/order; "
                "the presentation layer will not reconcile it"
            )
    if templates != sorted(templates):
        raise PresentationError(
            "clustered_by_template keys are not stored in sorted order; the spec "
            "(row order = sorted keys as stored) is ambiguous on this record"
        )
    print_render(ARTEFACT, "n_quantities [M]", len(quantities))
    print_render(ARTEFACT, "n_templates [M]", len(templates))
    if len(quantities) != 6 or len(templates) != 13:
        raise PresentationError("expected 6 quantities x 13 templates")
    print_render(ARTEFACT, "quantity_order [M, column labels verbatim]", quantities)
    print_render(ARTEFACT, "template_order [M, sorted as stored; row labels verbatim]", templates)

    # ---- family per template [M -- campaign cells[].family] ----------------
    family_of = {}
    cells_of = {}
    for cell in campaign["cells"]:
        tpl = str(cell.get("subcase") or "")
        family_of.setdefault(tpl, set()).add(cell["family"])
        cells_of[tpl] = cells_of.get(tpl, 0) + 1
    for tpl in templates:
        fams = family_of.get(tpl)
        if not fams or len(fams) != 1:
            raise PresentationError(
                f"template {tpl!r} maps to families {fams!r} in campaign cells; "
                "expected exactly one"
            )
        family_of[tpl] = next(iter(fams))
        print_render(ARTEFACT, f"family.{tpl} [M campaign cells[].family]", family_of[tpl])
    extra = sorted(set(cells_of) - set(templates))
    if extra:
        raise PresentationError(f"campaign carries subcases absent from the table: {extra}")

    # ---- row labels: JSON key verbatim + rule-driven suffixes ---------------
    print(
        "ROW-LABEL RULE (printed verbatim): the row label is the template key "
        "verbatim; a template whose family has class_macro coverage "
        "instantiated < defined carries the suffix ' — <family>: "
        "<instantiated>/<defined> subcases'; a template whose family carries "
        f"class_macro.<family>.qualification carries the suffix ' {F4_MARK}' "
        "pointing at the header's verbatim qualification. No name is invented."
    )
    row_labels = {}
    for tpl in templates:
        fam = family_of[tpl]
        label = tpl
        cm = class_macro.get(fam)
        if cm is None:
            raise PresentationError(f"family {fam!r} of {tpl!r} is not in class_macro")
        cov = cm["coverage"]
        if cov["instantiated"] != cov["defined"]:
            label += f" — {fam}: {cov['instantiated']}/{cov['defined']} subcases"
        if "qualification" in cm:
            label += f" {F4_MARK}"
        row_labels[tpl] = label
        print_render(ARTEFACT, f"row_label.{tpl} [D]", label)

    # ---- the cells [M] ------------------------------------------------------
    cell_text = {}
    col_sum_count = {q: 0 for q in quantities}
    col_sum_total = {q: 0 for q in quantities}
    for q in quantities:
        for tpl in templates:
            rec = cbt[q][tpl]
            count, total, rate = rec["count"], rec["total"], rec["rate"]
            print_render(ARTEFACT, f"{q}.{tpl}.count [M]", count)
            print_render(ARTEFACT, f"{q}.{tpl}.total [M]", total)
            print_render(ARTEFACT, f"{q}.{tpl}.rate [M]", rate)
            txt = f"{count}/{total} ({rate:.3f})"
            print_render(ARTEFACT, f"{q}.{tpl}.cell [D count/total (rate 3dp)]", txt)
            cell_text[(q, tpl)] = txt
            col_sum_count[q] += count
            col_sum_total[q] += total
            if total != cells_of[tpl]:
                raise PresentationError(
                    f"{q}.{tpl}: total {total} != {cells_of[tpl]} scored campaign cells"
                )

    # ---- printed cross-checks against the sealed record (not rendered) ------
    cells_scored = int(tables["cells_scored"])
    for q in quantities:
        im = tables["instance_micro"][q]
        print(
            f"CHECK {ARTEFACT} | sum_count.{q} [D] = {col_sum_count[q]} ; "
            f"instance_micro.{q}.count [M] = {im['count']}"
        )
        print(
            f"CHECK {ARTEFACT} | sum_total.{q} [D] = {col_sum_total[q]} ; "
            f"instance_micro.{q}.total [M] = {im['total']} ; cells_scored [M] = "
            f"{cells_scored}"
        )
        if (
            col_sum_count[q] != im["count"]
            or col_sum_total[q] != im["total"]
            or im["total"] != cells_scored
        ):
            raise PresentationError(f"template sums for {q} do not close on the record")
    sum_totals_any = col_sum_total[quantities[0]]
    print_render(ARTEFACT, "sum_totals_over_templates [D]", sum_totals_any)
    print_render(ARTEFACT, "cells_scored [M]", cells_scored)

    # ---- F3 fraction [M] ----------------------------------------------------
    f3cov = class_macro["F3"]["coverage"]
    print_render(ARTEFACT, "F3.coverage.instantiated [M]", f3cov["instantiated"])
    print_render(ARTEFACT, "F3.coverage.defined [M]", f3cov["defined"])
    f3_line = (
        f"F3 templates: {f3cov['instantiated']}/{f3cov['defined']} subcases "
        "instantiated — this fraction travels with every F3 number."
    )
    if F3_FRACTION_PHRASE not in f3_line:
        raise PresentationError("F3 caption does not carry the binding 2/5 fraction")
    print_render(ARTEFACT, "caption.F3 [D from M]", f3_line)

    # ---- F4 qualification [M], verbatim, cross-checked against the .md ------
    f4_text = class_macro["F4"]["qualification"]
    md_lines = (RESULTS_TABLES / "results-confirmatory.md").read_text(encoding="utf-8").split("\n")
    md69 = md_lines[68]
    if md69 != "> " + f4_text:
        raise PresentationError(
            "class_macro.F4.qualification differs from results-confirmatory.md line 69"
        )
    print(
        f"CHECK {ARTEFACT} | results-confirmatory.md line 69 == '> ' + "
        "class_macro.F4.qualification : True"
    )
    f4_lead = (
        "F4 qualification (pre-registered; travels with every F4 result; "
        f"class_macro.F4.qualification verbatim; rows marked {F4_MARK}):"
    )
    print_render(ARTEFACT, "caption.F4.lead [D]", f4_lead)
    print_render(ARTEFACT, "caption.F4.qualification [M verbatim]", f4_text)

    # ---- false_block identity [M -- campaign cells], E.11 -------------------
    fb_cells = [c for c in campaign["cells"] if c.get("false_block")]
    fb_ids = []
    for c in fb_cells:
        ident = (
            f"{c['arm']} / {c['subcase']} / {c['scenario_id']} / "
            f"monitor_attached={c['monitor_attached']}"
        )
        fb_ids.append(ident)
        print_render(ARTEFACT, "false_block_cell [M]", ident)
    print_render(ARTEFACT, "false_block_cells_n [M len]", len(fb_cells))
    print_render(ARTEFACT, "false_block_column_sum [D]", col_sum_count["false_block"])
    if len(fb_cells) != col_sum_count["false_block"]:
        raise PresentationError("false_block column does not equal the campaign's cells")
    fb_note = (
        f"false_block: the {col_sum_count['false_block']} counts in the false_block "
        f"column are exactly these campaign cells (cells[] with false_block=true): "
        + "; ".join(fb_ids)
        + ". They are a G-15(ii) fail-closed RESULT (D4 evidence chain, "
        "FIGURE_PLAN.md §0.3: the monitor was genuinely absent); not a "
        "capability-vs-OAuth comparison; never read across monitor configurations."
    )

    stat_note = tables["statistical_note"]
    print_render(ARTEFACT, "statistical_note [M verbatim]", stat_note)

    title = (
        f"{ARTEFACT} — clustered_by_template: {len(quantities)} quantities × "
        f"{len(templates)} templates (exact counts; cell = count/total (rate); "
        "no CI anywhere)"
    )
    footer_1 = (
        "Row order = the template keys as stored in clustered_by_template (sorted); "
        "row and column labels are the JSON keys verbatim; each cell = count/total "
        "(rate to 3 dp) exactly as stored; total = the scored campaign cells carrying "
        f"that template (Σ totals over the {len(templates)} templates = "
        f"{sum_totals_any} = cells_scored {cells_scored}). Rates never travel "
        "without count/total."
    )
    footer_2 = (
        f"{F4_MARK} = row of family F4 (campaign cells[].family): the header's "
        "pre-registered F4 qualification travels with every number on that row."
    )
    footer_4 = (
        "Source: results/tables/results-confirmatory.json (clustered_by_template; "
        "class_macro.F3.coverage; class_macro.F4.qualification; statistical_note; "
        "instance_micro + cells_scored for the printed cross-check sums) and "
        "results/raw/campaign-confirmatory.json (cells[].family; false_block cell "
        "identities). Presentation layer, ADR 0048."
    )
    for key, val in (
        ("footer.1 [D]", footer_1),
        ("footer.2 [D]", footer_2),
        ("footer.3.false_block [D from M]", fb_note),
        ("footer.4 [D]", footer_4),
        ("title [D]", title),
    ):
        print_render(ARTEFACT, key, val)

    # ---- wording audit over everything rendered ---------------------------
    rendered_strings = (
        [title, f3_line, f4_lead, f4_text, fb_note, stat_note, footer_1, footer_2, footer_4]
        + list(row_labels.values())
        + quantities
        + list(cell_text.values())
    )
    for s in rendered_strings:
        if BANNED_STEM in s.lower():
            raise PresentationError(f"banned word stem in rendered text: {s!r}")
        if "80 of 90" in s:
            raise PresentationError("unqualified '80 of 90' in rendered text")
    print(
        f"CHECK {ARTEFACT} | banned stem {BANNED_STEM!r} absent from all rendered "
        f"text: True ({len(rendered_strings)} strings)"
    )

    # ---- geometry ----------------------------------------------------------
    mpl_setup()
    label_w = max(text_width(row_labels[t]) for t in templates) + LABEL_PAD
    col_w = {}
    for q in quantities:
        w_cells = max(text_width(cell_text[(q, t)]) for t in templates)
        w_tokens = max(text_width(tok, _FP_BOLD) for tok in re.split(r"(?<=_)", q) if tok)
        col_w[q] = max(w_cells, w_tokens) + PAD_X
    uniform = max(col_w.values())  # equal data columns (layout only)
    col_w = {q: uniform for q in quantities}
    table_w = label_w + sum(col_w.values())
    fig_w = MARGIN + table_w + MARGIN
    wrap_w = table_w
    header_lines = {q: wrap_key(q, col_w[q] - 0.03) for q in quantities}
    n_hdr = max(len(v) for v in header_lines.values())
    f4_lines = wrap_words(f4_text, wrap_w - 0.18)
    footer_blocks = [
        wrap_words(footer_1, wrap_w),
        wrap_words(footer_2, wrap_w),
        wrap_words(fb_note, wrap_w),
        wrap_words(stat_note, wrap_w),
        wrap_words(footer_4, wrap_w),
    ]
    title_lines = wrap_words(
        title, wrap_w, FontProperties(family="DejaVu Sans", size=FONT_MIN_PT + 1, weight="bold")
    )

    GAP = 0.08
    fig_h = (
        MARGIN
        + len(title_lines) * (LINE + 0.03)
        + 0.05
        + LINE  # F3 line
        + LINE  # F4 lead
        + len(f4_lines) * LINE
        + GAP
        + n_hdr * LINE
        + 0.08  # header block
        + len(templates) * ROW_H
        + GAP
        + sum(len(b) for b in footer_blocks) * LINE
        + (len(footer_blocks) - 1) * 0.05
        + MARGIN
    )

    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    x0 = MARGIN
    t = MARGIN  # cursor measured downward from the top edge

    def y_at(tt):
        return fig_h - tt

    # title
    for ln in title_lines:
        ax.text(
            x0,
            y_at(t),
            ln,
            fontsize=FONT_MIN_PT + 1,
            fontweight="bold",
            color=INK,
            va="top",
            ha="left",
        )
        t += LINE + 0.03
    t += 0.05
    # F3 caption line
    ax.text(x0, y_at(t), f3_line, fontsize=FONT_MIN_PT, color=INK, va="top", fontweight="bold")
    t += LINE
    # F4 qualification: bold lead-in, then the verbatim text beside a bar
    ax.text(x0, y_at(t), f4_lead, fontsize=FONT_MIN_PT, color=INK, va="top", fontweight="bold")
    t += LINE
    bar_top = t
    for ln in f4_lines:
        ax.text(x0 + 0.18, y_at(t), ln, fontsize=FONT_MIN_PT, color=INK, va="top")
        t += LINE
    ax.plot([x0 + 0.06, x0 + 0.06], [y_at(bar_top) - 0.01, y_at(t) + 0.03], color=MIDGREY, lw=1.2)
    t += GAP

    # header block
    ax.plot([x0, x0 + table_w], [y_at(t), y_at(t)], color=INK, lw=0.8)
    t += 0.04
    hdr_top = t
    xc = x0 + label_w
    ax.text(
        x0,
        y_at(hdr_top + n_hdr * LINE - 0.02),
        "template (row label = JSON key)",
        fontsize=FONT_MIN_PT,
        color=INK,
        va="bottom",
        ha="left",
        style="italic",
    )
    for q in quantities:
        lines = header_lines[q]
        # bottom-align the header lines so multi-line keys sit on the rule
        for i, ln in enumerate(reversed(lines)):
            ax.text(
                xc + col_w[q] / 2,
                y_at(hdr_top + n_hdr * LINE - 0.02 - i * LINE),
                ln,
                fontsize=FONT_MIN_PT,
                fontweight="bold",
                color=INK,
                va="bottom",
                ha="center",
            )
        xc += col_w[q]
    t = hdr_top + n_hdr * LINE + 0.04
    ax.plot([x0, x0 + table_w], [y_at(t), y_at(t)], color=INK, lw=0.8)

    # rows
    for i, tpl in enumerate(templates):
        yc = y_at(t + (i + 0.5) * ROW_H)
        ax.text(x0, yc, row_labels[tpl], fontsize=FONT_MIN_PT, color=INK, va="center", ha="left")
        xc = x0 + label_w
        for q in quantities:
            ax.text(
                xc + col_w[q] / 2,
                yc,
                cell_text[(q, tpl)],
                fontsize=FONT_MIN_PT,
                color=INK,
                va="center",
                ha="center",
            )
            xc += col_w[q]
        if i < len(templates) - 1:
            yl = y_at(t + (i + 1) * ROW_H)
            ax.plot([x0, x0 + table_w], [yl, yl], color=GREY, lw=0.4)
    t += len(templates) * ROW_H
    ax.plot([x0, x0 + table_w], [y_at(t), y_at(t)], color=INK, lw=0.8)
    t += GAP

    # footers
    for bi, block in enumerate(footer_blocks):
        for ln in block:
            ax.text(x0, y_at(t), ln, fontsize=FONT_MIN_PT, color=INK, va="top")
            t += LINE
        if bi < len(footer_blocks) - 1:
            t += 0.05

    print_render(ARTEFACT, "figure_size_in [D]", f"{fig_w:.2f} x {fig_h:.2f}")
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
