# ruff: noqa: E501
"""FIG-BF -- admitted attacks and false blocks, per configuration, by family.

Built on the Commander's instruction of 2026-08-29 ("按照数据，直接构建新图"),
given AFTER the conflict below was reported. It is recorded here so that the
figure never presents itself as uncontested:

  * FIGURE_PLAN.md §G defers FIG-2, a family-by-arm security grid, under ruling
    D8 ("RQ2 is discharged by FIG-1 + TAB-4"); this artefact is a family-by-arm
    security figure and therefore stands on that deferred ground.
  * FIGURE_PLAN.md §B's TAB-4 entry records why bars over exact counts were
    rejected: across unequal denominators they read as sampled estimates. The
    denominators here ARE unequal (8 to 10 attack cells per arm, from the ten
    NA cells), so every bar end prints its own "k of N" and the axis is
    labelled in cells, never in a rate.

What is drawn. One row per arm in ladder order, two bands that are NEVER
summed: the upper band holds every scored cell measured WITHOUT the shared
monitor (`monitor_attached` None or False -- all five families); the lower band
holds the cells measured WITH it (`monitor_attached` True -- only the F4/F5
scenarios exist in that configuration). Within a row, admitted attacks
(`admission_breach`) extend to the right of the zero line, one segment per
family, each labelled by its family name and filled one step of a single-hue
lightness ramp; false blocks (`false_block`, benign cells only) extend to the
left in the suite's amber. Both sides are exact counts of cells. No interval,
error bar or rate appears (D26: the corpus is a census).

Why two bands and not one. The A-dagger rule (G-15): an F4/F5 difference that
exists only because a configuration carries the shared monitor must never be
read as a capability-versus-OAuth advantage, so cells from the two monitor
configurations never share a bar.

Pure presentation (ADR 0048): every count is a sum over cell fields of
`results/raw/campaign-confirmatory.json`; the regrouping is the hard-coded
MONITOR_PARTITION_RULE below, printed verbatim, and it decides no number's
inclusion. Two fail-closed checks that can only abort the build: every admitted
attack must sit on a cell whose sealed E.4 expectation is A (so the subtitle's
agreement clause is verified, not asserted), and B3/B3+ must be identical on
every comparable cell pair (the bracket's claim). The F3 coverage warning and
the F4 qualification are carried VERBATIM in the printed caption from the sealed
tables artefact. On the canvas: words a reader outside the project can decode,
no internal document names (Commander instruction 2026-08-21).

The family glosses on the key are this script's wording, not sealed text, for
F1 to F3 (the sealed names are the subcase tokens); F4 and F5 use the sealed
E.4 row names verbatim.
"""

import textwrap

from _common import (
    ARM_ORDER,
    BLOCKED,
    FALSE_BLOCK,
    FONT_MIN_PT,
    INK,
    LADDER_AT,
    MIDGREY,
    PAPER,
    PORTRAIT,
    TEXT_W_IN,
    PresentationError,
    assert_no_text_overlap,
    load_campaign,
    load_tables,
    mpl_setup,
    plt,
    predicted_rows,
    print_render,
    save,
)
from matplotlib.patches import Rectangle

ARTEFACT = "FIG-BF"
STEM = "fig_breach_by_family"

FAMILIES = ("F1", "F2", "F3", "F4", "F5")
OUTCOME_FIELDS = (
    "admission_breach",
    "false_block",
    "observed_forwarded",
    "realized_harm",
    "log_integrity_failure",
)

MONITOR_PARTITION_RULE = """\
MONITOR_PARTITION_RULE (FIG-BF). Every SCORED cell of campaign-confirmatory.json
is placed in exactly one band by its own `monitor_attached` field:
  band "off" -- monitor_attached is None or False (the shared monitor absent;
                every family is measured in this configuration)
  band "on"  -- monitor_attached is True (the shared monitor attached; only the
                F4/F5 scenarios are measured in this configuration)
Within a band a cell is an ATTACK cell iff reference_allow is False and a
BENIGN cell otherwise. Admitted attacks are attack cells with admission_breach
True, counted per family; false blocks are benign cells with false_block True.
Denominators are the band's attack-cell and benign-cell counts per arm. The
bands are never summed. The partition is a regrouping for display; it decides
nothing about which numbers are reported."""

# Key wording. F4/F5 are the sealed E.4 row names; F1-F3 are glosses (docstring).
FAMILY_GLOSS = {
    "F1": "scope beyond the grant",
    "F2": "credential faults",
    "F3": "token misuse",
    "F4": "sensitive egress, no declassification",
    "F5": "high-risk action, no approval artifact",
}


def _hex_to_rgb(h):
    return tuple(int(h[i : i + 2], 16) / 255 for i in (1, 3, 5))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{round(c * 255):02X}" for c in rgb)


def _luma(rgb):
    r, g, b = (c * 255 for c in rgb)
    return 0.299 * r + 0.587 * g + 0.114 * b


def family_fills():
    """Five steps of ONE hue from BLOCKED to LADDER_AT -- the sequential rule
    the suite already uses for ordered states, applied here so five categorical
    fills survive a monochrome print (each segment is also labelled by name, so
    no family is carried by fill alone). Computed, and printed with its luma."""
    a, b = _hex_to_rgb(BLOCKED), _hex_to_rgb(LADDER_AT)
    fills = {}
    for i, fam in enumerate(FAMILIES):
        t = i / (len(FAMILIES) - 1)
        rgb = tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
        fills[fam] = (_rgb_to_hex(rgb), INK if _luma(rgb) >= 128 else PAPER, _luma(rgb))
    return fills


def _band(cell):
    return "on" if cell.get("monitor_attached") is True else "off"


def tally(campaign):
    """Per band, per arm: breaches by family, attack cells, false blocks, benign cells."""
    out = {
        band: {
            arm: {"breach": {f: 0 for f in FAMILIES}, "attack": 0, "fb": 0, "benign": 0}
            for arm in ARM_ORDER
        }
        for band in ("off", "on")
    }
    for cell in campaign["cells"]:
        arm = cell["arm"]
        if arm not in out["off"]:
            raise PresentationError(f"cell names arm {arm!r}, not in the ladder")
        fam = cell["family"]
        if cell["admission_breach"] and cell["false_block"]:
            raise PresentationError(
                f"cell {cell['correlation_id']} is both a breach and a false block"
            )
        slot = out[_band(cell)][arm]
        if cell["reference_allow"]:
            slot["benign"] += 1
            if cell["admission_breach"]:
                raise PresentationError("admission_breach on a benign cell")
            if cell["false_block"]:
                slot["fb"] += 1
        else:
            slot["attack"] += 1
            if cell["false_block"]:
                raise PresentationError("false_block on an attack cell")
            if cell["admission_breach"]:
                if fam not in FAMILIES:
                    raise PresentationError(f"breach on family {fam!r}, not one of {FAMILIES}")
                slot["breach"][fam] += 1
    return out


def check_breaches_were_predicted(campaign, tables):
    """Fail closed unless every admitted attack sits on a cell E.4 predicted A."""
    rows = predicted_rows(tables)
    checked = 0
    for cell in campaign["cells"]:
        if not cell["admission_breach"]:
            continue
        row = rows.get(cell["subcase"])
        if row is None:
            raise PresentationError(
                f"breach cell subcase {cell['subcase']!r} maps to no predicted row"
            )
        expected = str(row["cells"].get(cell["arm"]))
        if not expected.startswith("A"):
            raise PresentationError(
                f"{cell['scenario_id']} / {cell['arm']}: admitted, but E.4 expects {expected!r}"
            )
        checked += 1
    return checked


def identical_pairs(campaign):
    """Comparable (scenario, monitor) pairs scored for both B3 and B3+, and
    whether every outcome field agrees on each. Raises if any pair differs,
    because the bracket then could not say what it says."""
    by = {}
    for cell in campaign["cells"]:
        if cell["arm"] in ("B3", "B3+"):
            by.setdefault((cell["scenario_id"], cell.get("monitor_attached")), {})[cell["arm"]] = (
                cell
            )
    pairs = 0
    for key, d in sorted(by.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        if len(d) != 2:
            continue
        pairs += 1
        for f in OUTCOME_FIELDS:
            if d["B3"][f] != d["B3+"][f]:
                raise PresentationError(f"B3 and B3+ differ on {f} at {key}")
    return pairs


def main():
    mpl_setup()
    campaign = load_campaign()
    tables = load_tables()
    print_render(ARTEFACT, "source.cells", "results/raw/campaign-confirmatory.json")
    print_render(ARTEFACT, "source.tables", "results/tables/results-confirmatory.json")
    print(MONITOR_PARTITION_RULE)

    cells = campaign["cells"]
    if len(cells) != tables["cells_scored"]:
        raise PresentationError(
            f"{len(cells)} cells in the campaign, {tables['cells_scored']} in the tables"
        )
    print_render(ARTEFACT, "cells_scored [M]", len(cells))
    print_render(ARTEFACT, "cells_unscorable [M]", len(campaign["unscorable"]))

    t = tally(campaign)
    n_off = sum(v["attack"] + v["benign"] for v in t["off"].values())
    n_on = sum(v["attack"] + v["benign"] for v in t["on"].values())
    if n_off + n_on != len(cells):
        raise PresentationError(f"partition covered {n_off + n_on} of {len(cells)} cells")
    print_render(ARTEFACT, "partition.off.cells [D]", n_off)
    print_render(ARTEFACT, "partition.on.cells [D]", n_on)
    for band in ("off", "on"):
        for arm in ARM_ORDER:
            v = t[band][arm]
            k = sum(v["breach"].values())
            per = " ".join(f"{f}={v['breach'][f]}" for f in FAMILIES)
            print_render(
                ARTEFACT,
                f"{band}.{arm} [D]",
                f"admitted {k} of {v['attack']} attack cells ({per}); "
                f"false blocks {v['fb']} of {v['benign']} benign cells",
            )
    total_breach = sum(sum(v["breach"].values()) for b in t.values() for v in b.values())
    total_fb = sum(v["fb"] for b in t.values() for v in b.values())
    im = tables["instance_micro"]
    if total_breach != im["admission_breach"]["count"] or total_fb != im["false_block"]["count"]:
        raise PresentationError("tallies disagree with the sealed instance_micro counts")
    print_render(ARTEFACT, "total.admission_breach [M]", total_breach)
    print_render(ARTEFACT, "total.false_block [M]", total_fb)

    checked = check_breaches_were_predicted(campaign, tables)
    print_render(ARTEFACT, "guard.breaches_predicted_A [D]", f"{checked} of {checked}")
    pairs = identical_pairs(campaign)
    print_render(ARTEFACT, "b3_b3plus_identical_pairs [D]", f"{pairs} of {pairs}")

    agreement = tables["agreement"]
    agreed = agreement["agreed"]
    disagreed = len(agreement["disagreed"])
    print_render(
        ARTEFACT, "agreement [M]", f"{agreed} of {agreed} comparable entries; {disagreed} disagreed"
    )

    fills = family_fills()
    for fam, (hexc, textc, luma) in fills.items():
        print_render(ARTEFACT, f"fill.{fam} [D]", f"{hexc} luma {luma:.0f} text {textc}")

    # ---- geometry, in inches -----------------------------------------------
    fig_w = TEXT_W_IN
    row_h = 0.24
    n_rows = len(ARM_ORDER)
    band_h = n_rows * row_h
    top, title_h, side_h, band_lab_h, xt_h, band_gap = 0.10, 0.44, 0.20, 0.22, 0.26, 0.16
    foot_lines, foot_lh, foot_pad = 6, 0.165, 0.10
    foot_h = foot_lines * foot_lh + foot_pad
    fig_h = top + title_h + side_h + 2 * (band_lab_h + band_h + xt_h) + band_gap + foot_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(PAPER)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def width_in(text, **kw):
        probe = fig.text(0.5, 0.5, text, fontsize=FONT_MIN_PT, **kw)
        w = probe.get_window_extent(renderer).width / fig.dpi
        probe.remove()
        return w

    label_w = max(width_in(a) for a in ARM_ORDER)
    gutter = 0.30 + label_w + 0.10
    left_cells = max(v["benign"] for b in t.values() for v in b.values())
    right_cells = max(v["attack"] for b in t.values() for v in b.values())
    lab_left_w = max(
        width_in(f"{v['fb']} of {v['benign']}") for b in t.values() for v in b.values()
    )
    lab_right_w = max(
        width_in(f"{sum(v['breach'].values())} of {v['attack']}")
        for b in t.values()
        for v in b.values()
    )
    gap = 0.12
    ax_w = fig_w - gutter - 0.10
    cell_in = (ax_w - lab_left_w - lab_right_w - 2 * gap) / (left_cells + right_cells)
    seg_lab_w = max(width_in(f) for f in FAMILIES + ("FB",))
    if cell_in < seg_lab_w + 0.04:
        raise PresentationError(
            f"a one-cell segment ({cell_in:.3f} in) cannot hold its label ({seg_lab_w:.3f} in)"
        )
    x_lo = -left_cells - (lab_left_w + gap) / cell_in
    x_hi = right_cells + (lab_right_w + gap) / cell_in
    print_render(ARTEFACT, "geometry.fig_in [D]", f"{fig_w:.3f} x {fig_h:.3f}")
    print_render(ARTEFACT, "geometry.gutter_in [D]", f"{gutter:.3f} (label {label_w:.3f} measured)")
    print_render(
        ARTEFACT, "geometry.cell_in [D]", f"{cell_in:.3f}; segment label {seg_lab_w:.3f} measured"
    )
    print_render(ARTEFACT, "geometry.xlim_cells [D]", f"{x_lo:.2f} .. {x_hi:.2f}")

    ys = {arm: n_rows - 1 - i for i, arm in enumerate(ARM_ORDER)}
    y_cursor = fig_h - top

    # ---- title + subtitle from the artefacts --------------------------------
    fig.text(
        0.10 / fig_w,
        (y_cursor - 0.02) / fig_h,
        "Admitted attacks and false blocks, per configuration",
        ha="left",
        va="top",
        fontsize=FONT_MIN_PT + 1,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.10 / fig_w,
        (y_cursor - 0.24) / fig_h,
        f"{len(cells)} cells scored  ·  {agreed} of {agreed} comparable entries agreed with the "
        f"pre-registration  ·  {disagreed} disagreed",
        ha="left",
        va="top",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    y_cursor -= title_h

    x0_fig = gutter / fig_w

    def x_fig(xc):
        return (gutter + (xc - x_lo) / (x_hi - x_lo) * ax_w) / fig_w

    from figL23_latency import draw_tier_brackets

    def draw_band(band, label, y_top, headings):
        """Band label, then (upper band only) the two direction headings, one
        on each side of the zero line with an arrow so they read as two
        headings and not as one sentence, then the rows."""
        extra = side_h if headings else 0.0
        y_bot = y_top - band_lab_h - extra - band_h
        fig.text(
            0.10 / fig_w,
            (y_top - 0.03) / fig_h,
            label,
            ha="left",
            va="top",
            fontsize=FONT_MIN_PT,
            fontweight="bold",
            color=INK,
        )
        if headings:
            yh = (y_top - band_lab_h - 0.02) / fig_h
            fig.text(
                x_fig(-0.6),
                yh,
                "← blocked a benign request",
                ha="right",
                va="top",
                fontsize=FONT_MIN_PT,
                color=INK,
                style="italic",
            )
            fig.text(
                x_fig(0.6),
                yh,
                "admitted an attack, by family →",
                ha="left",
                va="top",
                fontsize=FONT_MIN_PT,
                color=INK,
                style="italic",
            )
        ax = fig.add_axes([x0_fig, y_bot / fig_h, ax_w / fig_w, band_h / fig_h])
        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(-0.5, n_rows - 0.5)
        ax.set_autoscale_on(False)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(INK)
        ax.spines["bottom"].set_linewidth(0.6)
        ax.set_yticks([])
        ticks = [-2, 0, 2, 4, 6, 8, 10]
        ax.set_xticks([tk for tk in ticks if x_lo <= tk <= x_hi])
        ax.set_xticklabels([str(abs(tk)) for tk in ticks if x_lo <= tk <= x_hi])
        ax.tick_params(axis="x", colors=INK, labelsize=FONT_MIN_PT, length=2.4, width=0.6, pad=1.5)
        ax.axvline(0, color=INK, lw=0.6, zorder=4)  # above the bars, so it is never hidden
        bar_h = 0.62
        for arm in ARM_ORDER:
            y = ys[arm]
            v = t[band][arm]
            x = 0.0
            for fam in FAMILIES:
                k = v["breach"][fam]
                if k == 0:
                    continue
                hexc, textc, _ = fills[fam]
                ax.add_patch(
                    Rectangle(
                        (x, y - bar_h / 2),
                        k,
                        bar_h,
                        facecolor=hexc,
                        edgecolor=PAPER,
                        linewidth=0.6,
                        zorder=3,
                    )
                )
                ax.text(
                    x + k / 2,
                    y,
                    fam,
                    ha="center",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=textc,
                    fontweight="bold",
                    zorder=4,
                )
                x += k
            k_total = sum(v["breach"].values())
            ax.text(
                x + gap / cell_in,
                y,
                f"{k_total} of {v['attack']}",
                ha="left",
                va="center",
                fontsize=FONT_MIN_PT,
                color=INK,
            )
            if v["fb"]:
                ax.add_patch(
                    Rectangle(
                        (-v["fb"], y - bar_h / 2),
                        v["fb"],
                        bar_h,
                        facecolor=FALSE_BLOCK,
                        edgecolor=PAPER,
                        linewidth=0.6,
                        zorder=3,
                    )
                )
                ax.text(
                    -v["fb"] / 2,
                    y,
                    "FB",
                    ha="center",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=INK,
                    fontweight="bold",
                    zorder=4,
                )
            ax.text(
                -v["fb"] - gap / cell_in,
                y,
                f"{v['fb']} of {v['benign']}",
                ha="right",
                va="center",
                fontsize=FONT_MIN_PT,
                color=INK,
            )
        pos = ax.get_position()
        draw_tier_brackets(fig, pos, ys, fig_w)
        for arm in ARM_ORDER:
            yy = pos.y0 + (ys[arm] + 0.5) / n_rows * pos.height
            fig.text(
                (gutter - 0.10) / fig_w,
                yy,
                arm,
                ha="right",
                va="center",
                fontsize=FONT_MIN_PT,
                color=INK,
            )
        return ax, y_bot - xt_h

    ax_off, y_next = draw_band("off", "without the shared monitor — every family", y_cursor, True)
    # The identity bracket: mandated wherever both arms' security outcomes are
    # shown. Drawn in the empty right half of the B3 / B3+ rows, clear of the
    # "0 of 10" labels (a line, which the text-overlap guard cannot see).
    y3, y3p = ys["B3"], ys["B3+"]
    xb = 2.6
    ax_off.plot(
        [xb, xb + 0.25, xb + 0.25, xb],
        [y3 + 0.3, y3 + 0.3, y3p - 0.3, y3p - 0.3],
        color=INK,
        lw=0.8,
        zorder=5,
    )
    ax_off.text(
        xb + 0.55,
        (y3 + y3p) / 2,
        f"{pairs}/{pairs} pairs identical, in both bands",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
        style="italic",
    )
    y_cursor = y_next - band_gap
    draw_band(
        "on", "with the shared monitor attached — only F4 and F5 are measured here", y_cursor, False
    )

    # ---- key, one item per line so no line can run off the canvas ------------
    def swatch(x_in, y_in, hexc):
        fig.add_artist(
            Rectangle(
                (x_in / fig_w, (y_in - 0.055) / fig_h),
                0.16 / fig_w,
                0.11 / fig_h,
                facecolor=hexc,
                edgecolor=PAPER,
                linewidth=0.4,
                transform=fig.transFigure,
            )
        )

    cov = tables["class_macro"]["F3"]["coverage"]
    lines = [
        (FALSE_BLOCK, "FB  a benign request was blocked (false block)", INK),
        (fills["F1"][0], "F1 … F5  an attack was admitted, labelled by family", INK),
        (None, f"F1 {FAMILY_GLOSS['F1']}  ·  F2 {FAMILY_GLOSS['F2']}", INK),
        (
            None,
            f"F3 {FAMILY_GLOSS['F3']} — {cov['instantiated']} of {cov['defined']} subcases instantiated",
            INK,
        ),
        (None, f"F4 {FAMILY_GLOSS['F4']}  ·  F5 {FAMILY_GLOSS['F5']}", INK),
        (
            None,
            "exact cell counts; the corpus is a census, so no interval exists and none is drawn",
            MIDGREY,
        ),
    ]
    if len(lines) != foot_lines:
        raise PresentationError(f"footer sized for {foot_lines} lines, {len(lines)} written")
    yk = foot_pad + (foot_lines - 0.5) * foot_lh
    for hexc, text, colour in lines:
        x = 0.10
        if hexc is not None:
            swatch(x, yk, hexc)
            x += 0.22
        fig.text(
            x / fig_w, yk / fig_h, text, ha="left", va="center", fontsize=FONT_MIN_PT, color=colour
        )
        yk -= foot_lh

    # ---- caption, printed ----------------------------------------------------
    f3_warning = tables["class_macro"]["F3"]["coverage_warning"]
    f4_qualification = tables["class_macro"]["F4"]["qualification"]
    print_render(ARTEFACT, "caption.f3_coverage_warning_chars [M verbatim]", len(f3_warning))
    print_render(ARTEFACT, "caption.f4_qualification_chars [M verbatim]", len(f4_qualification))
    off_b0 = sum(t["off"]["B0"]["breach"].values())
    paragraphs = [
        "Admitted attacks and false blocks per configuration, by attack family. Rows are the nine "
        "ladder arms in ladder order, grouped in the gutter into the three authority tiers of the "
        "authority-surface figure. To the right of the zero line, each segment is one attack family's "
        "admitted attacks, one cell wide per cell, labelled by family and filled one step of a "
        "single-hue lightness ramp so the segments stay distinct in a monochrome print; the number at "
        "the bar end is the admitted count over the arm's attack cells in that band. To the left, in "
        "amber, are benign requests the boundary blocked, over the arm's benign cells. Denominators "
        "differ between arms because ten cells are unscorable-NA under the sealed record: an arm that "
        "stages no chain or no holder proof has no chain-tamper or wrong-holder-proof cell to score.",
        f"The upper band holds the {n_off} cells measured without the shared monitor, every family; "
        f"the lower band holds the {n_on} cells measured with it, which exist only for the F4 and F5 "
        "scenarios. The bands are never summed and are never read across each other: a difference "
        "between arms that appears only when the monitor is attached belongs to the monitor, not to "
        "the arm's own mechanism, and is not a capability-versus-OAuth result in either direction. "
        f"Every admitted attack in both bands sits on a cell the pre-registered matrix expected to be "
        f"admitted ({checked} of {checked} checked at build time); the ladder's descent from "
        f"{off_b0} admitted at B0 to none at B3 is therefore the pre-registration confirmed, not a "
        "surprise. The four false blocks are B3 and B3+ on the two benign controls without the "
        "monitor, a fail-closed result: the same cells forward when the monitor is attached.",
        f"B3 and B3+ are identical on every outcome field in all {pairs} comparable cell pairs; the "
        "subcase that would distinguish them is not populated by the campaign. These are exact cell "
        "counts; no confidence interval is defined for any of them and none is drawn.",
        f3_warning,
        f4_qualification,
    ]
    for para in paragraphs:
        for line in textwrap.wrap(para, 96):
            print(f"CAPTION {ARTEFACT} | {line}")
        print(f"CAPTION {ARTEFACT} |")

    # Portrait artefact: the shared guard enforces the LANDSCAPE block (the
    # latency set's contract); this one raises against the PORTRAIT block with
    # the same strictness -- an unplaceable canvas is a build error, not a line
    # in a report.
    aw, ah = (float(v) for v in fig.get_size_inches())
    if aw > PORTRAIT[0] + 1e-6 or ah > PORTRAIT[1] + 1e-6:
        raise PresentationError(
            f"{ARTEFACT}: authored {aw:.3f} x {ah:.3f} in exceeds the portrait text block "
            f"{PORTRAIT[0]:.3f} x {PORTRAIT[1]:.3f} in"
        )
    print_render(ARTEFACT, "guard.placement", f"{aw:.3f} x {ah:.3f} in <= portrait")
    # Content overflow RAISES here: save() only reports it, and a clipped key
    # line passed every numeric check once already (this figure's first build).
    fig.canvas.draw()
    tb = fig.get_tightbbox(fig.canvas.get_renderer())
    if tb.width > aw + 0.01 or tb.height > ah + 0.01:
        raise PresentationError(
            f"{ARTEFACT}: drawn content {tb.width:.3f} x {tb.height:.3f} in exceeds the canvas "
            f"{aw:.3f} x {ah:.3f} in"
        )
    print_render(ARTEFACT, "guard.overflow", "drawn content within the canvas")
    assert_no_text_overlap(fig, ARTEFACT)
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
