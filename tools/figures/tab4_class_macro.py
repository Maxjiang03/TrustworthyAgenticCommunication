"""TAB-4 -- class-macro exact counts: count | total | rate per family, F1..F5.

Pure presentation (ADR 0048): every number is the sealed `class_macro` block of
results/tables/results-confirmatory.json rendered AS STORED -- counts and totals
verbatim, rates as the exact decimal lexeme written in the JSON (no recomputation,
no rounding). Family headers read `coverage` {instantiated, defined} and the
`observed_forwarded` total; the F3 `coverage_warning` and the F4 `qualification`
are printed verbatim. The only cross-file read is the identity of the false_block
cells (campaign-confirmatory.json), listed so the F4/F5 false_block counts never
travel without their per-arm, per-configuration identity (FIGURE_PLAN.md E.11).
Nothing is selected, excluded, binned, or computed.
"""

import json
import textwrap

from _common import (
    FONT_MIN_PT,
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

ARTEFACT = "TAB-4"

# The pre-registered family order and class_macro's own six quantity keys, in the
# order the specification fixes. Both sets are checked against the JSON at build
# time: nothing is renamed, added, or dropped.
FAMILY_ORDER = ("F1", "F2", "F3", "F4", "F5")
QUANTITY_ORDER = (
    "admission_breach",
    "realized_harm",
    "false_block",
    "log_integrity_failure",
    "observed_forwarded",
    "reference_allow",
)
COVERAGE_KEYS = ("instantiated", "defined")
N_QUANTITY = "observed_forwarded"  # the family n in every block header

FOOTER_D26 = (
    "Exact counts and rates only; no confidence interval is placed on any "
    "security proportion (D26)."
)
FOOTER_RQ3 = "RQ3 is answered on the constructed instance set only (ADR 0037)."
FOOTER_STORED = (
    "Every count, total and rate is the value stored in results-confirmatory.json "
    "class_macro (rates unrounded, as written); n per family = the "
    f"{N_QUANTITY} total. Rates never travel without count/total."
)

WRAP = 112  # characters per wrapped line for the verbatim paragraphs


def load_class_macro_verbatim():
    """Re-read the tables JSON with floats kept as their stored lexemes.

    json.loads(parse_float=str) returns each rate exactly as written in the
    file, so the artefact prints the stored value and never a re-formatted one.
    """
    path = RESULTS_TABLES / "results-confirmatory.json"
    return json.loads(path.read_text(encoding="utf-8"), parse_float=str)["class_macro"]


def family_label(fam, cov):
    frac = f"{cov['instantiated']}/{cov['defined']}"
    if fam == "F3":
        return f"F3 ({frac} subcases)"
    return fam


def main():
    tables = load_tables()
    campaign = load_campaign()
    class_macro = tables["class_macro"]
    verbatim = load_class_macro_verbatim()

    if tuple(sorted(class_macro)) != tuple(sorted(FAMILY_ORDER)):
        raise PresentationError(
            f"class_macro families {sorted(class_macro)} != {sorted(FAMILY_ORDER)}"
        )

    # ---- read every number, printing each one ---------------------------
    blocks = []
    for fam in FAMILY_ORDER:
        block = class_macro[fam]
        cov = block["coverage"]
        if tuple(sorted(cov)) != tuple(sorted(COVERAGE_KEYS)):
            raise PresentationError(f"{fam}.coverage keys {sorted(cov)} unexpected")
        quantities = block["quantities"]
        if tuple(sorted(quantities)) != tuple(sorted(QUANTITY_ORDER)):
            raise PresentationError(
                f"{fam}.quantities keys {sorted(quantities)} != {sorted(QUANTITY_ORDER)}"
            )
        n = quantities[N_QUANTITY]["total"]
        label = family_label(fam, cov)
        print_render(ARTEFACT, f"{fam}.coverage.instantiated [M]", cov["instantiated"])
        print_render(ARTEFACT, f"{fam}.coverage.defined [M]", cov["defined"])
        print_render(ARTEFACT, f"{fam}.n [M {N_QUANTITY}.total]", n)
        print_render(ARTEFACT, f"{fam}.header_label", label)
        rows = []
        for q in QUANTITY_ORDER:
            rec = quantities[q]
            if tuple(sorted(rec)) != ("count", "rate", "total"):
                raise PresentationError(f"{fam}.{q} keys {sorted(rec)} unexpected")
            count = rec["count"]
            total = rec["total"]
            rate_lexeme = verbatim[fam]["quantities"][q]["rate"]
            if not isinstance(rate_lexeme, str) or float(rate_lexeme) != rec["rate"]:
                raise PresentationError(
                    f"{fam}.{q}.rate lexeme {rate_lexeme!r} does not round-trip "
                    f"to the loaded value {rec['rate']!r}"
                )
            print_render(ARTEFACT, f"{fam}.{q}.count [M]", count)
            print_render(ARTEFACT, f"{fam}.{q}.total [M]", total)
            print_render(ARTEFACT, f"{fam}.{q}.rate [M as stored]", rate_lexeme)
            rows.append((q, count, total, rate_lexeme))
        warning = block.get("coverage_warning")
        qualification = block.get("qualification")
        if fam == "F3":
            if not warning:
                raise PresentationError("class_macro.F3.coverage_warning is missing")
            print_render(ARTEFACT, "F3.coverage_warning [M verbatim]", warning)
        if fam == "F4":
            if not qualification:
                raise PresentationError("class_macro.F4.qualification is missing")
            print_render(ARTEFACT, "F4.qualification [M verbatim]", qualification)
        blocks.append(
            dict(
                fam=fam,
                label=label,
                n=n,
                cov=cov,
                rows=rows,
                warning=warning,
                qualification=qualification,
            )
        )

    # ---- the false_block identity footnote (FIGURE_PLAN.md E.11) ---------
    # Every campaign cell whose stored false_block field is true is listed with
    # its arm, subcase and monitor configuration; nothing else is read from it,
    # and the per-family tally is checked against the stored class_macro count.
    fb_cells = [c for c in campaign["cells"] if c.get("false_block")]
    fb_by_family = {}
    for c in fb_cells:
        fb_by_family[c["family"]] = fb_by_family.get(c["family"], 0) + 1
    for i, c in enumerate(fb_cells, 1):
        print_render(
            ARTEFACT,
            f"false_block_cell.{i} [M]",
            f"family={c['family']} arm={c['arm']} subcase={c['subcase']} "
            f"monitor_attached={c['monitor_attached']}",
        )
    print_render(ARTEFACT, "false_block_cells_total [D]", len(fb_cells))
    for fam in FAMILY_ORDER:
        stored = class_macro[fam]["quantities"]["false_block"]["count"]
        listed = fb_by_family.get(fam, 0)
        print_render(ARTEFACT, f"{fam}.false_block.cells_listed [D]", listed)
        if listed != stored:
            raise PresentationError(
                f"{fam}: {listed} false_block cells in the campaign record but "
                f"class_macro stores count {stored}"
            )
    fb_items = "; ".join(
        f"{c['family']}: {c['arm']} on {c['subcase']} (monitor_attached={c['monitor_attached']})"
        for c in fb_cells
    )
    fb_note = (
        f"The false_block counts above are exactly these {len(fb_cells)} cells "
        f"[campaign-confirmatory.json]: {fb_items}. They stand as a G-15(ii) "
        "fail-closed RESULT (the monitor was genuinely absent — D4 evidence chain, "
        "FIGURE_PLAN.md 0.3); they are not a capability-vs-OAuth comparison and "
        "are never read across monitor configurations."
    )

    # ---- layout: a list of baselines, each a list of (x, ha, text, style) --
    mpl_setup()
    W = 8.5
    lh = 0.165  # inches per baseline
    top, bottom = 0.55, 0.30
    x_lab, x_q, x_cnt, x_tot, x_rate = 0.10, 0.35, 3.75, 4.55, 4.95
    x_par = 0.42  # indented paragraphs

    TITLE = dict(fontsize=FONT_MIN_PT + 1, fontweight="bold", color=INK)
    HEAD = dict(fontsize=FONT_MIN_PT + 1, fontweight="bold", color=INK)
    COLH = dict(fontsize=FONT_MIN_PT, fontweight="bold", color=INK)
    BODY = dict(fontsize=FONT_MIN_PT, color=INK)
    PARA = dict(fontsize=FONT_MIN_PT, color=INK)
    LEAD = dict(fontsize=FONT_MIN_PT, color=MIDGREY)

    lines = []  # (items, gap_after, marker)

    def add(items, gap=0.0, marker=None):
        lines.append((items, gap, marker))

    def add_paragraph(text, style, marker=None):
        for part in textwrap.wrap(text, WRAP):
            add([(x_par, "left", part, style)], marker=marker)

    add(
        [
            (
                x_lab,
                "left",
                "TAB-4 — class-macro exact counts by family: count | total | rate, "
                "as stored in class_macro (RQ3, RQ2)",
                TITLE,
            )
        ],
        gap=0.06,
    )
    add(
        [
            (x_q, "left", "quantity", COLH),
            (x_cnt, "right", "count", COLH),
            (x_tot, "right", "total", COLH),
            (x_rate, "left", "rate (as stored)", COLH),
        ],
        gap=0.03,
        marker="rule",
    )

    for b in blocks:
        fam = b["fam"]
        if fam == "F4":
            add(
                [
                    (
                        x_par,
                        "left",
                        "Pre-registered F4 qualification (class_macro.F4.qualification, "
                        "verbatim) — it travels with every F4 result:",
                        LEAD,
                    )
                ]
            )
            add_paragraph(b["qualification"], PARA, marker="quote")
            add([], gap=0.02)
        cov = b["cov"]
        if fam == "F3":
            head = f"{b['label']} — n={b['n']}"
        else:
            head = f"{b['label']} — {cov['instantiated']}/{cov['defined']} subcases, n={b['n']}"
        add([(x_lab, "left", head, HEAD)], gap=0.01)
        if fam == "F3":
            add_paragraph(b["warning"], PARA)
        for q, count, total, rate in b["rows"]:
            add(
                [
                    (x_q, "left", q, BODY),
                    (x_cnt, "right", str(count), BODY),
                    (x_tot, "right", str(total), BODY),
                    (x_rate, "left", rate, BODY),
                ]
            )
        add([], gap=0.04)

    add([], gap=0.0, marker="rule")
    add([(x_lab, "left", FOOTER_D26, BODY)])
    add([(x_lab, "left", FOOTER_RQ3, BODY)])
    for part in textwrap.wrap(FOOTER_STORED, WRAP + 6):
        add([(x_lab, "left", part, BODY)])
    for part in textwrap.wrap(fb_note, WRAP + 6):
        add([(x_lab, "left", part, BODY)])

    H = top + sum(lh + gap for _, gap, _ in lines) + bottom
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    y = H - top
    quote_span = [None, None]
    for items, gap, marker in lines:
        for x, ha, text, style in items:
            ax.text(x, y, text, ha=ha, va="top", **style)
        if marker == "quote":
            quote_span[0] = y if quote_span[0] is None else quote_span[0]
            quote_span[1] = y - lh
        if marker == "rule":
            ax.plot([x_lab, W - 0.10], [y - lh + 0.02, y - lh + 0.02], color=INK, lw=0.6)
        y -= lh + gap
    if quote_span[0] is not None:
        ax.plot(
            [x_par - 0.10, x_par - 0.10],
            [quote_span[0], quote_span[1] + 0.03],
            color=MIDGREY,
            lw=1.4,
        )

    save(fig, "tab4_class_macro", ARTEFACT)


if __name__ == "__main__":
    main()
