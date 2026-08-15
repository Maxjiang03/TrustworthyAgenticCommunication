"""TAB-1 -- the single normative state legend + the cell accounting.

Block 1: the eight cell states (plus the defined-but-unused disagreement mark),
each with fill/texture + glyph + letters + meaning -- referenced by every matrix
artefact so no per-figure partial legend can drift. Block 2: the cell
accounting (cells run = scored + unscorable; unscorable cause census; scored
cells by observed state; family denominators), every number read from the
committed JSONs or derived by printed arithmetic. Pure presentation (ADR 0048):
nothing is selected, excluded, binned, or estimated.
"""

import textwrap
from collections import Counter

from _common import (
    ARM_ORDER,
    FONT_MIN_PT,
    GHOST,
    GREY,
    INK,
    MIDGREY,
    ORANGE,
    PAPER,
    RESULTS_TABLES,
    VERMILLION,
    PresentationError,
    is_daggered,
    load_campaign,
    load_tables,
    mpl_setup,
    plt,
    predicted_rows,
    print_render,
    save,
)
from matplotlib.patches import Rectangle

ARTEFACT = "TAB-1"

# The pre-registered F4 qualification is quoted verbatim from
# results/tables/results-confirmatory.md line 69 (a blockquote line, "> ...");
# the same sentence is carried by results-confirmatory.json class_macro.F4.
# The two are cross-checked and the script refuses if they differ.
F4_QUALIFICATION_MD_LINE = 69


def observed_state(cell):
    """FB if false_block; else A if observed_forwarded; else B (FIG-1's rule)."""
    if cell.get("false_block"):
        return "FB"
    return "A" if cell.get("observed_forwarded") else "B"


def read_md_line(path, lineno):
    lines = path.read_text(encoding="utf-8").splitlines()
    if lineno > len(lines):
        raise PresentationError(f"{path} has no line {lineno}")
    return lines[lineno - 1]


def wrap(text, width):
    return textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)


def main():
    campaign = load_campaign()
    tables = load_tables()
    agreement = tables["agreement"]
    class_macro = tables["class_macro"]

    # ---- Block 2 numbers: cell accounting ---------------------------------
    scored = len(campaign["cells"])
    unscorable = campaign["unscorable"]
    n_unscorable = len(unscorable)
    cells_run = scored + n_unscorable
    print_render(ARTEFACT, "cells_scored [M]", scored)
    print_render(ARTEFACT, "cells_unscorable [M]", n_unscorable)
    print_render(ARTEFACT, "cells_run [D scored+unscorable]", cells_run)
    if tables["cells_scored"] != scored:
        raise PresentationError("tables cells_scored != campaign cells length")

    # Unscorable cause census: each unscorable entry is [scenario_id, arm, cause].
    for entry in unscorable:
        if len(entry) != 3:
            raise PresentationError(f"unscorable entry shape unexpected: {entry!r}")
    cause_census = Counter(entry[2] for entry in unscorable)
    for cause, n in sorted(cause_census.items()):
        print_render(ARTEFACT, f"unscorable_cause_count [M] {cause!r}", n)
    print_render(ARTEFACT, "unscorable_distinct_causes [D]", len(cause_census))
    for entry in unscorable:
        print_render(
            ARTEFACT,
            "unscorable_cell [M]",
            f"scenario_id={entry[0]} arm={entry[1]} cause={entry[2]!r}",
        )

    # Scored cells by observed state (a categorisation by the cell's own fields).
    state_census = Counter(observed_state(c) for c in campaign["cells"])
    for st in ("A", "B", "FB"):
        print_render(ARTEFACT, f"scored_by_observed_state.{st} [M]", state_census[st])
    if sum(state_census.values()) != scored or set(state_census) - {"A", "B", "FB"}:
        raise PresentationError("observed-state census does not cover the scored cells")
    fb_cells = [c for c in campaign["cells"] if c.get("false_block")]
    for c in fb_cells:
        print_render(
            ARTEFACT,
            "false_block_cell [M]",
            f"arm={c['arm']} scenario_id={c['scenario_id']} "
            f"subcase={c['subcase']} monitor_attached={c['monitor_attached']}",
        )

    # Family denominators from class_macro.<F>.quantities.observed_forwarded.total.
    families = ("F1", "F2", "F3", "F4", "F5")
    fam_total = {}
    for fam in families:
        fam_total[fam] = class_macro[fam]["quantities"]["observed_forwarded"]["total"]
        print_render(ARTEFACT, f"family_denominator.{fam} [M]", fam_total[fam])
    fam_sum = sum(fam_total.values())
    print_render(ARTEFACT, "family_denominator_sum [D]", fam_sum)
    if fam_sum != scored:
        raise PresentationError("family denominators do not sum to the scored cells")
    f3_cov = class_macro["F3"]["coverage"]
    f3_fraction = f"{f3_cov['instantiated']}/{f3_cov['defined']}"
    print_render(ARTEFACT, "F3_coverage [M]", f3_fraction)
    f3_warning = class_macro["F3"]["coverage_warning"]
    print_render(ARTEFACT, "F3_coverage_warning [M]", f3_warning)
    f4_qual = class_macro["F4"]["qualification"]
    md_line = read_md_line(RESULTS_TABLES / "results-confirmatory.md", F4_QUALIFICATION_MD_LINE)
    if md_line.startswith("> "):
        md_line = md_line[2:]
    if md_line != f4_qual:
        raise PresentationError(
            f"class_macro.F4.qualification differs from results-confirmatory.md line "
            f"{F4_QUALIFICATION_MD_LINE}; the verbatim quotation is not unique"
        )
    print_render(ARTEFACT, f"F4_qualification [M md line {F4_QUALIFICATION_MD_LINE}]", f4_qual)

    # ---- Block 1 numbers: legend-row counts --------------------------------
    rows = predicted_rows(tables)
    n_predicted = len(rows)
    n_arms = len(ARM_ORDER)
    base_entries = n_predicted * n_arms
    print_render(ARTEFACT, "predicted_rows [M]", n_predicted)
    print_render(ARTEFACT, "arms [M]", n_arms)
    print_render(ARTEFACT, "base_entries [D rows*arms]", base_entries)
    n_expected_na = sum(1 for r in rows.values() for v in r["cells"].values() if v == "NA")
    n_expected_dagger = sum(1 for r in rows.values() for v in r["cells"].values() if is_daggered(v))
    print_render(ARTEFACT, "expected_NA_cells [M]", n_expected_na)
    print_render(ARTEFACT, "expected_dagger_cells [M]", n_expected_dagger)
    agreed = int(agreement["agreed"])
    disagreed = len(agreement["disagreed"])
    unmeasured = agreement["unmeasured"]
    n_unmeasured = len(unmeasured)
    comparable = agreed + disagreed
    print_render(ARTEFACT, "entries_agreed [M]", agreed)
    print_render(ARTEFACT, "entries_disagreed [M]", disagreed)
    print_render(ARTEFACT, "entries_unmeasured_NA [M]", n_unmeasured)
    print_render(ARTEFACT, "entries_comparable [D agreed+disagreed]", comparable)
    if comparable + n_unmeasured != base_entries:
        raise PresentationError("agreement block does not close on the entry base")
    not_populated = agreement["not_populated"]
    deferred = agreement["deferred"]
    print_render(ARTEFACT, "rows_not_populated [M]", len(not_populated))
    print_render(ARTEFACT, "rows_deferred [M]", len(deferred))
    for r in not_populated:
        print_render(ARTEFACT, "not_populated_row [M]", f"{r['subcase']} | {r['state']}")
    for r in deferred:
        print_render(ARTEFACT, "deferred_row [M]", f"{r['subcase']} | {r['state']}")
    np_families = sorted({r["family"] for r in not_populated})
    print_render(ARTEFACT, "not_populated_families [M]", ",".join(np_families))

    # Identity of the ten unscorable cells with the ten E.4 NA cells: the
    # subcase->scenario_id map is read off the scored cells' own fields; the
    # E.4 row label -> subcase token map is the ADR 0048 named exception.
    token_to_scenario = {}
    for c in campaign["cells"]:
        token_to_scenario.setdefault(str(c.get("subcase") or ""), set()).add(c["scenario_id"])
    label_to_token = {r["subcase"]: tok for tok, r in rows.items()}
    na_pairs = set()
    for u in unmeasured:
        tok = label_to_token[u["subcase"]]
        scen = token_to_scenario.get(tok, set())
        if len(scen) != 1:
            raise PresentationError(f"token {tok!r} maps to {len(scen)} scenario ids")
        na_pairs.add((next(iter(scen)), u["arm"]))
    unscorable_pairs = {(e[0], e[1]) for e in unscorable}
    identical = na_pairs == unscorable_pairs
    print_render(ARTEFACT, "unscorable_equals_E4_NA_cells [D]", identical)
    if not identical:
        raise PresentationError(
            "the unscorable cells are not the E.4 NA cells; the legend text would mis-state"
        )

    # ---- Layout ------------------------------------------------------------
    mpl_setup()
    fs = FONT_MIN_PT
    line_h = 0.15  # inches per 8 pt line
    fig_w = 8.8
    # column x positions (inches)
    x_state, x_swatch, x_glyph, x_letters, x_meaning = 0.08, 1.60, 2.70, 3.20, 3.85
    sw_w, sw_h = 0.62, 0.30  # swatch = one FIG-1 cell
    meaning_chars = 80
    texture_chars = 24
    right_margin = 0.12

    def state_row(state, texture, glyph, letters, meaning):
        return dict(
            state=state,
            texture=wrap(texture, texture_chars),
            glyph=glyph,
            letters=letters,
            meaning=wrap(meaning, meaning_chars),
        )

    fb_ids = "; ".join(
        f"{c['arm']} × {c['scenario_id']} (monitor_attached={c['monitor_attached']})"
        for c in fb_cells
    )
    cause_text = "; ".join(f"'{cause}' × {n}" for cause, n in sorted(cause_census.items()))
    np_labels = "; ".join(r["subcase"] for r in not_populated)
    def_labels = "; ".join(r["subcase"] for r in deferred)
    def_state = "; ".join(r["state"] for r in deferred)
    np_state = "; ".join(sorted({r["state"] for r in not_populated}))

    legend = [
        state_row(
            "B  blocked",
            "near-black fill",
            "■",
            "B (white)",
            "the arm refused: observed_forwarded=false and false_block=false. "
            f"{state_census['B']} of the {scored} scored cells [M].",
        ),
        state_row(
            "A  forwarded",
            "paper",
            "A",
            "A",
            "the arm admitted the request: observed_forwarded=true. "
            f"{state_census['A']} of the {scored} scored cells [M].",
        ),
        state_row(
            "A†  forwarded,\nno monitor",
            "paper + printed dagger",
            "†",
            "A†",
            "admitted absent the shared monitor, §E.4 footnote † (spelled out: the "
            "dagger glyph). An EXPECTED-layer value, scored against the "
            f"monitor_attached=False pass only (R1); {n_expected_dagger} expected "
            "cells carry it [M] — the four B2 arms in each F4/F5 attack row.",
        ),
        state_row(
            "FB  false block",
            "paper + orange dashed inner border",
            "▢",
            "FB",
            f"false_block=true. {state_census['FB']} cells [M]: {fb_ids}. A G-15(ii) "
            "fail-closed RESULT with the D4 evidence chain (FIGURE_PLAN §0.3): the "
            "monitor was genuinely absent; never read across monitor configurations "
            "and never a capability-vs-OAuth comparison.",
        ),
        state_row(
            "NA",
            "grey 45° hatch, no frame",
            "▨",
            "NA",
            "ADR 0035: a statement about the corpus — no second instance to score — "
            f"never about a measurable admission. {n_expected_na} expected cells [M]; "
            f"{n_unmeasured} of the {base_entries} base entries are NA and not "
            "comparable [M].",
        ),
        state_row(
            "unscorable",
            '"×" over the NA hatch',
            "×",
            "×",
            "× spelled out: the cross glyph. The fail-closed causes DEFINED in the sealed harness "
            '(src/harness/campaign.py: RunnerError "the run did not complete"; the '
            "wall-clock straddle; the credential validity window; authorizer-budget "
            "exhaustion, ADR 0046) produced ZERO cells; the "
            f"{n_unscorable} observed unscorable cells are exactly the "
            f"{n_expected_na} §E.4 NA cells [M], cause census {cause_text} [M]. "
            "Cause per cell: TAB-3.",
        ),
        state_row(
            "deferred",
            "dotted band",
            "┄",
            "DEF",
            f'{def_labels}: state "{def_state}" — ADR 0028; deferred, emphatically NOT NA. '
            f"{len(deferred)} row [M]; outside every count.",
        ),
        state_row(
            "NOT POPULATED",
            "ghost band (10% grey), no cells",
            "▭",
            "words",
            f"{len(not_populated)} {'/'.join(np_families)} rows [M]: {np_labels}. State "
            f'"{np_state}": outside every count; not passing, not confirmed. '
            "The absence of cells IS the encoding: no frame, fill, or glyph appears.",
        ),
        state_row(
            "▲  disagreement",
            "vermillion chevron (reserved)",
            "▲",
            "▲",
            f"{disagreed} of {comparable} comparable entries [M] — defined so the "
            "display could have failed; vermillion appears nowhere else, so its "
            "absence is itself the 0-disagreement result.",
        ),
    ]

    accounting_w = 128
    accounting = [
        ("Cell accounting (every base labelled; CELLS and ENTRIES are different objects)", True),
        (
            f"{cells_run} cells run [D]  =  {scored} scored [M]  +  {n_unscorable} unscorable [M]",
            False,
        ),
        (f"unscorable cause census [M]: {cause_text}  ({len(cause_census)} distinct cause)", False),
        (
            f"scored cells by observed state [M]: A forwarded {state_census['A']}  |  "
            f"B blocked {state_census['B']}  |  FB false block {state_census['FB']}  "
            f"(sum {state_census['A'] + state_census['B'] + state_census['FB']} [D])",
            False,
        ),
        (
            f"family denominators [M]: F1 {fam_total['F1']}  |  F2 {fam_total['F2']}  |  "
            f"F3 ({f3_fraction} subcases) {fam_total['F3']}  |  F4 {fam_total['F4']}  |  "
            f"F5 {fam_total['F5']}  (sum {fam_sum} [D])",
            False,
        ),
        (
            f"§E.4 agreement (ENTRIES, {n_predicted} predicted rows × {n_arms} arms = "
            f"{base_entries} [D]): {agreed} of {comparable} comparable entries agreed; "
            f"{n_unmeasured} of the {base_entries} base entries were NA and not comparable; "
            f"{disagreed} disagreed [M]",
            False,
        ),
        (f"F3 coverage warning [M]: {f3_warning}", False),
        (
            f"F4 qualification [M, results-confirmatory.md:{F4_QUALIFICATION_MD_LINE}]: {f4_qual}",
            False,
        ),
        ("Exact counts; no CI is defined for any number on this table.", False),
    ]

    # Row heights: legend rows sized to their wrapped meaning; accounting lines
    # to their wrapped width.
    header_h = 0.34
    row_hs = [
        max(len(r["meaning"]) * line_h, sw_h + 0.04 + len(r["texture"]) * line_h) + 0.16
        for r in legend
    ]
    acc_wrapped = [(wrap(t, accounting_w) if not b else [t], b) for t, b in accounting]
    acc_h = sum(len(ls) * line_h + 0.06 for ls, _ in acc_wrapped)
    top_pad, gap, bottom_pad = 0.42, 0.30, 0.15
    fig_h = top_pad + header_h + sum(row_hs) + gap + acc_h + bottom_pad
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    ax.text(
        x_state,
        fig_h - 0.10,
        "TAB-1 — the normative cell-state legend and the cell accounting "
        "(referenced by every matrix artefact)",
        fontsize=fs + 1,
        fontweight="bold",
        color=INK,
        va="top",
    )

    # header
    y = fig_h - top_pad
    for x, head in (
        (x_state, "state"),
        (x_swatch, "fill / texture"),
        (x_glyph, "glyph"),
        (x_letters, "letters"),
        (x_meaning, "meaning"),
    ):
        ax.text(x, y - header_h / 2, head, fontsize=fs, fontweight="bold", color=INK, va="center")
    ax.plot([x_state, fig_w - right_margin], [y - header_h, y - header_h], color=INK, lw=0.6)
    y -= header_h

    def swatch(kind, x, yb):
        """Draw the FIG-1 cell for this state at (x, yb) -- three channels each."""
        if kind == "B":
            ax.add_patch(Rectangle((x, yb), sw_w, sw_h, facecolor=PAPER, edgecolor=INK, lw=1.5))
            ax.add_patch(
                Rectangle(
                    (x + 0.04, yb + 0.04), sw_w - 0.08, sw_h - 0.08, facecolor=INK, edgecolor="none"
                )
            )
            ax.text(
                x + sw_w / 2,
                yb + sw_h / 2,
                "B",
                ha="center",
                va="center",
                fontsize=fs,
                color=PAPER,
                fontweight="bold",
            )
        elif kind == "A":
            ax.add_patch(Rectangle((x, yb), sw_w, sw_h, facecolor=PAPER, edgecolor=INK, lw=0.5))
            ax.text(
                x + sw_w / 2,
                yb + sw_h / 2,
                "A",
                ha="center",
                va="center",
                fontsize=fs,
                color=INK,
                fontweight="bold",
            )
        elif kind == "A†":
            ax.add_patch(Rectangle((x, yb), sw_w, sw_h, facecolor=PAPER, edgecolor=INK, lw=0.5))
            ax.text(
                x + sw_w / 2,
                yb + sw_h / 2,
                "A",
                ha="center",
                va="center",
                fontsize=fs,
                color=INK,
                fontweight="bold",
            )
            ax.text(
                x + sw_w - 0.05, yb + sw_h - 0.04, "†", ha="right", va="top", fontsize=fs, color=INK
            )
        elif kind == "FB":
            ax.add_patch(Rectangle((x, yb), sw_w, sw_h, facecolor=PAPER, edgecolor=INK, lw=0.5))
            ax.add_patch(
                Rectangle(
                    (x + 0.05, yb + 0.05),
                    sw_w - 0.10,
                    sw_h - 0.10,
                    facecolor=PAPER,
                    edgecolor=ORANGE,
                    lw=1.4,
                    linestyle=(0, (2, 1.5)),
                )
            )
            ax.text(
                x + sw_w / 2,
                yb + sw_h / 2,
                "FB",
                ha="center",
                va="center",
                fontsize=fs,
                color=INK,
                fontweight="bold",
            )
        elif kind == "NA":
            ax.add_patch(
                Rectangle(
                    (x, yb), sw_w, sw_h, facecolor=PAPER, edgecolor=GREY, hatch="////", lw=0.4
                )
            )
            ax.text(
                x + sw_w / 2,
                yb + sw_h / 2,
                "NA",
                ha="center",
                va="center",
                fontsize=fs,
                color=INK,
                fontweight="bold",
            )
        elif kind == "unscorable":
            ax.add_patch(
                Rectangle(
                    (x, yb), sw_w, sw_h, facecolor=PAPER, edgecolor=GREY, hatch="////", lw=0.4
                )
            )
            ax.text(
                x + sw_w / 2,
                yb + sw_h / 2,
                "×",
                ha="center",
                va="center",
                fontsize=fs + 2,
                color=INK,
            )
        elif kind == "deferred":
            ax.add_patch(Rectangle((x, yb), sw_w, sw_h, facecolor=GHOST, edgecolor="none"))
            ax.plot(
                [x, x + sw_w], [yb + 0.02, yb + 0.02], color=MIDGREY, lw=0.8, linestyle=(0, (1, 2))
            )
            ax.text(
                x + sw_w / 2,
                yb + sw_h / 2,
                "DEF",
                ha="center",
                va="center",
                fontsize=fs,
                color=MIDGREY,
                style="italic",
            )
        elif kind == "NOT POPULATED":
            ax.add_patch(Rectangle((x, yb), sw_w, sw_h, facecolor=GHOST, edgecolor="none"))
            ax.text(
                x + sw_w / 2,
                yb + sw_h / 2,
                "words",
                ha="center",
                va="center",
                fontsize=fs,
                color=MIDGREY,
                style="italic",
            )
        elif kind == "disagreement":
            ax.add_patch(Rectangle((x, yb), sw_w, sw_h, facecolor=PAPER, edgecolor=INK, lw=0.5))
            ax.text(
                x + sw_w / 2,
                yb + sw_h / 2,
                "▲",
                ha="center",
                va="center",
                fontsize=fs + 1,
                color=VERMILLION,
            )

    kinds = ("B", "A", "A†", "FB", "NA", "unscorable", "deferred", "NOT POPULATED", "disagreement")
    for kind, r, rh in zip(kinds, legend, row_hs):
        ytop = y
        ax.text(
            x_state, ytop - 0.06, r["state"], fontsize=fs, fontweight="bold", color=INK, va="top"
        )
        swatch(kind, x_swatch, ytop - 0.06 - sw_h)
        for k, ln in enumerate(r["texture"]):
            ax.text(
                x_swatch,
                ytop - 0.06 - sw_h - 0.04 - k * line_h,
                ln,
                fontsize=fs,
                color=INK,
                va="top",
            )
        glyph_color = VERMILLION if kind == "disagreement" else INK
        ax.text(
            x_glyph + 0.15,
            ytop - 0.06,
            r["glyph"],
            fontsize=fs + 2,
            color=glyph_color,
            va="top",
            ha="center",
        )
        ax.text(x_letters, ytop - 0.06, r["letters"], fontsize=fs, color=INK, va="top")
        for k, ln in enumerate(r["meaning"]):
            ax.text(x_meaning, ytop - 0.06 - k * line_h, ln, fontsize=fs, color=INK, va="top")
        y -= rh
        ax.plot([x_state, fig_w - right_margin], [y, y], color=GREY, lw=0.4)

    # Block 2 -- accounting
    y -= gap
    for lines, is_title in acc_wrapped:
        for ln in lines:
            ax.text(
                x_state,
                y,
                ln,
                fontsize=fs + (1 if is_title else 0),
                fontweight="bold" if is_title else "normal",
                color=INK,
                va="top",
            )
            y -= line_h
        y -= 0.06

    save(fig, "tab1_state_legend", ARTEFACT)


if __name__ == "__main__":
    main()
