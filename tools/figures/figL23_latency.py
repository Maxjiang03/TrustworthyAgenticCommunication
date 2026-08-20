"""FIG-L23 -- the RQ4 latency decomposition: benign deltas and the refusal path,
one figure, two bands, five shared columns.

UPPER BAND (benign path): median(arm) - median(B0) per span with the sealed
95 % bootstrap interval, from the committed ArmPairDelta records (DEVIATIONS
D-014). Signed, so the shared axis is symlog by the pre-committed rule. B0 is
the zero line; B1 has no marks because the sealed layer REFUSES every pair
involving it (ADR 0035), and its row says so.

LOWER BAND (refusal path, chain-tamper scenario): the sealed absolute
Descriptives -- median and p95 -- under series = refusal_path, log10. Its own
series, never pooled with the benign path: on that scenario the exchange arms
perform a FAILED AS round trip, which lands in delegation, while the capability
arms do purely local work. No delta exists for this band because the sealed
arm_pair_delta builds from the benign series alone; none is computed here. Its
end-to-end panel is not drawn (C1). B1 appears here
because the descriptive layer does not refuse it; only the bit-labelled delta
does.

The two bands share the five span columns, so each cell is read down one
column: what the span costs against the baseline when the request is benign,
and what it costs in absolute terms when the chain is tampered. The bands are
never summed, never overlaid, and carry different axes, each named on its own
band label.

Interquartile widths are NOT drawn (Commander ruling 2026-08-19, merging the
two figures onto one page): they stand verbatim in the committed artefact this
figure reads, and drawing an arm's absolute IQR on a delta axis would be a
unit error in any case. Nothing here subtracts, pools or interpolates; every
mark is a field of results/tables/results-latency-pilot-rq4-run2.json. Pure
presentation (ADR 0048).

Every dot's value is printed (Commander rulings 2026-08-20), and the values
are set as TWO RIGHT-ALIGNED COLUMNS at the right edge of every panel --
warm then cold, one line per arm row on the row's centre -- in the suite's
shared three-decimal millisecond format. The first cut placed each number
beside its own mark; the Commander rejected it as untidy, so the numbers now
live where a table would put them and the axes yield the width the columns
need. Column widths are MEASURED from the rendered strings -- the
per-character estimate is a closed defect class in this suite -- per span
column and shared by both bands, so the two bands' axes stay vertically
aligned and each span is still read down one column. The major ticks thin to
what the narrowed axes can hold without collision; the dropped decades stay
as unlabelled minor ticks. In the delta band the baseline row prints
nothing (its label already says "baseline, 0" -- a printed 0 would state a
measurement the record does not contain) and the refused row prints
nothing (ADR 0035).
"""

import math
import warnings

from _common import (
    ARM_ORDER,
    FONT_MIN_PT,
    INK,
    LATENCY_SPREAD,
    PAPER,
    VERMILLION,
    PresentationError,
    assert_no_text_overlap,
    draw_key,
    enforce_placement,
    fmt_ms3,
    load_latency_rq4,
    mpl_setup,
    plt,
    print_render,
    save,
)
from matplotlib.ticker import FixedFormatter, NullFormatter

ARTEFACT = "FIG-L23"
STEM = "figL23_latency"

SPANS = ("setup", "delegation", "presentation", "boundary_verification", "end_to_end")
SPAN_TITLE = {
    "setup": "setup",
    "delegation": "delegation",
    "presentation": "presentation",
    "boundary_verification": "boundary verification",
    "end_to_end": "end to end",
}
REF_SPANS = SPANS[:4]
OMITTED = "end_to_end"
PHASES = ("warm", "cold")
# Dodge within the arm row: warm above the centre, cold below. The offset is
# smaller than half the row, so a pair groups more tightly than two arms do.
PHASES_IN_ROW = (("warm", 0.18, True), ("cold", -0.18, False))
SERIES_REF = "refusal_path"
# The value-column strip at the right edge of every panel, in inches: axes |
# ML | warm column | GAP | cold column | MR. Column widths are measured per
# span from the rendered strings; these are only the fixed separations.
COL_ML, COL_GAP, COL_MR = 0.08, 0.07, 0.03
AX_W_FLOOR = 0.50


def _text_width_in(fig, renderer, text):
    """The rendered width of `text` in inches -- measured, never estimated.

    Per-character estimates are a closed defect class in this suite. The probe
    is a figure-level text, measured against the live renderer and removed.
    """
    probe = fig.text(0.5, 0.5, text, fontsize=FONT_MIN_PT)
    width = probe.get_window_extent(renderer).width / fig.dpi
    probe.remove()
    return width


def draw_tier_brackets(fig, pos, ys, fig_w):
    """FIG-0's ladder tiers beside the arm rows, so the figures read as one.

    The tier assignment is FIG-0's own transcription of section E.1, imported
    rather than retyped. Ink, not grey: the bracket is structure a reader must
    follow, and this figure keeps grey for de-emphasis only.
    """
    from fig_authority_surface import ARM_GRANT, GRANT_LABEL
    from matplotlib.lines import Line2D

    tiers = {}
    for arm in ARM_ORDER:
        tiers.setdefault(ARM_GRANT[arm], []).append(ys[arm])
    for tier, rows in tiers.items():
        y0 = pos.y0 + (min(rows) + 0.08) / len(ARM_ORDER) * pos.height
        y1 = pos.y0 + (max(rows) + 0.92) / len(ARM_ORDER) * pos.height
        fig.add_artist(
            Line2D([0.16 / fig_w] * 2, [y0, y1], color=INK, lw=0.8, transform=fig.transFigure)
        )
        fig.text(
            0.09 / fig_w,
            (y0 + y1) / 2,
            GRANT_LABEL[tier],
            ha="center",
            va="center",
            rotation=90,
            fontsize=FONT_MIN_PT,
            color=INK,
        )


def main():
    mpl_setup()
    art = load_latency_rq4()
    control = art["control_arm"]
    print_render(ARTEFACT, "source.artefact", "results/tables/results-latency-pilot-rq4-run2.json")
    print_render(ARTEFACT, "source.control_arm [M]", control)

    # ---- the delta band's records ------------------------------------------
    by_delta = {(d["treatment_arm"], d["phase"], d["span"]): d for d in art["arm_pair_deltas"]}
    refused_arms = sorted({r["treatment_arm"] for r in art["refusals"]})
    print_render(ARTEFACT, "deltas [M]", len(art["arm_pair_deltas"]))
    print_render(ARTEFACT, "refused_arms [M sealed]", refused_arms)
    for arm in refused_arms:
        got = {(r["phase"], r["span"]) for r in art["refusals"] if r["treatment_arm"] == arm}
        want = {(p, s) for p in PHASES for s in SPANS}
        if got != want:
            raise PresentationError(f"{arm}: refused for {len(got)} of {len(want)} cells; partial")

    # ---- the refusal band's records ----------------------------------------
    by_ref = {
        (r["arm"], r["phase"], r["span"]): r["descriptives"]
        for r in art["span_reports"]
        if r["series"] == SERIES_REF
    }
    want = {(a, p, s) for a in ARM_ORDER for p in PHASES for s in SPANS}
    if set(by_ref) != want:
        raise PresentationError(f"refusal-path coverage: {len(by_ref)} of {len(want)} cells")
    print_render(ARTEFACT, "refusal_reports [M]", len(by_ref))
    print_render(ARTEFACT, "refusal.panel_omitted [C1]", OMITTED)

    ns = {d["treatment"]["n"] for d in art["arm_pair_deltas"]}
    ns |= {d["control"]["n"] for d in art["arm_pair_deltas"]}
    ns |= {d["n"] for d in by_ref.values()}
    if len(ns) != 1:
        raise PresentationError(f"n differs across records: {ns}")
    n = ns.pop()
    print_render(ARTEFACT, "n_per_cell [M]", n)

    # ---- axes: the pre-committed rule for the delta band, log10 for the
    # refusal band (absolute, positivity checked) ----------------------------
    plotted = []
    for d in art["arm_pair_deltas"]:
        plotted += [d["point_estimate_ms"], d["ci_low_ms"], d["ci_high_ms"]]
    nonpos = [v for v in plotted if v <= 0]
    min_pos = min(v for v in plotted if v > 0)
    use_log = not nonpos
    linthresh = 10 ** math.floor(math.log10(min_pos))
    xmin, xmax = min(plotted), max(plotted)
    print_render(
        ARTEFACT, "delta.axis.rule", "log10 iff every point and bound > 0, else symlog (D-014)"
    )
    print_render(ARTEFACT, "delta.axis.values_not_positive [D]", len(nonpos))
    print_render(ARTEFACT, "delta.axis.branch", "log10" if use_log else "symlog")
    print_render(ARTEFACT, "delta.axis.symlog_linthresh_ms [D]", linthresh)

    ref_plotted = []
    for (a, p, s), d in by_ref.items():
        if s == OMITTED:
            continue
        ref_plotted += [d["median"], d["p95"]]
    if any(v <= 0 for v in ref_plotted):
        raise PresentationError(
            "a refusal-path median or p95 is not positive; log10 cannot hold it"
        )
    dec_lo = math.floor(math.log10(min(ref_plotted)))
    dec_hi = math.ceil(math.log10(max(ref_plotted)))
    print_render(ARTEFACT, "refusal.axis.branch", "log10 (every plotted value > 0)")
    print_render(
        ARTEFACT, "refusal.axis.decades [D]", f"{dec_lo}..{dec_hi}; xlim = data / 1.4 .. data x 1.4"
    )

    # A7: the one absolute end-to-end value stated anywhere, read from the artefact
    b0_e2e = [
        r
        for r in art["span_reports"]
        if r["arm"] == control
        and r["phase"] == "warm"
        and r["span"] == "end_to_end"
        and r["series"] == "benign"
    ]
    if len(b0_e2e) != 1:
        raise PresentationError(
            f"expected one B0 warm benign end_to_end report, found {len(b0_e2e)}"
        )
    b0_e2e_med = b0_e2e[0]["descriptives"]["median"]
    print_render(ARTEFACT, "A7.fixed_overhead_B0_warm_end_to_end_median_ms [M]", b0_e2e_med)

    # ---- geometry, in inches. Two bands, five shared columns, no IQR column,
    # so the panels get the width the numbers used to hold. -------------------
    gutter = 1.66
    fig_w = 9.65
    col_gap = 0.10
    plot_w = (fig_w - gutter - 0.05) / len(SPANS) - col_gap
    col_w = plot_w + col_gap
    row_h = 0.21
    band_h = len(ARM_ORDER) * row_h
    top, hdr_h, blab_h, xt_h, band_gap, key_h = 0.05, 0.24, 0.20, 0.24, 0.08, 0.20
    glyph_h = 0.13  # the column-header line: a filled dot over warm, an open dot over cold
    band_block = blab_h + glyph_h + band_h + xt_h
    fig_h = top + hdr_h + band_block + band_gap + band_block + key_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(PAPER)
    print_render(ARTEFACT, "geometry.fig_in [D]", f"{fig_w:.2f} x {fig_h:.2f}")

    ys = {arm: len(ARM_ORDER) - 1 - i for i, arm in enumerate(ARM_ORDER)}
    y_hdr = fig_h - top - hdr_h
    y1_top = y_hdr - blab_h - glyph_h
    y1_bot = y1_top - band_h
    y2_top = y1_bot - xt_h - band_gap - blab_h - glyph_h
    y2_bot = y2_top - band_h

    # ---- shared span headers, once. The first and last are nudged right
    # (Commander, 2026-08-19): "setup" otherwise hangs at the band label's
    # left edge and "end to end" at the canvas edge.
    hdr_dx = {"setup": 0.15, "end_to_end": 0.15}
    for col, span in enumerate(SPANS):
        fig.text(
            (gutter + col * col_w + hdr_dx.get(span, 0.0)) / fig_w,
            (y_hdr + 0.06) / fig_h,
            SPAN_TITLE[span],
            ha="left",
            va="bottom",
            fontsize=FONT_MIN_PT + 1,
            color=INK,
            fontweight="bold",
        )

    def band_label(y_bot, bold):
        fig.text(
            (gutter - 1.40) / fig_w,
            (y_bot + band_h + glyph_h + 0.04) / fig_h,
            bold,
            ha="left",
            va="bottom",
            fontsize=FONT_MIN_PT,
            color=INK,
            fontweight="bold",
        )

    def style_axis(ax):
        ax.set_ylim(-0.5, len(ARM_ORDER) - 0.5)
        ax.set_autoscale_on(False)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(INK)
        ax.spines["bottom"].set_linewidth(0.6)
        ax.set_yticks([])
        ax.tick_params(axis="x", colors=INK, labelsize=FONT_MIN_PT, length=2.4, width=0.6, pad=1.5)
        ax.tick_params(axis="x", which="minor", colors=INK, length=1.4, width=0.4)

    # ---- the value columns: widths measured per span, shared by both bands,
    # so the bands' axes stay vertically aligned and the numbers set as two
    # right-aligned columns (warm, then cold) at every panel's right edge.
    renderer = fig.canvas.get_renderer()
    num_w = {}
    for span in SPANS:
        strings = [
            fmt_ms3(by_delta[(arm, ph, span)]["point_estimate_ms"])
            for arm in ARM_ORDER
            if arm != control and arm not in refused_arms
            for ph in PHASES
        ]
        if span != OMITTED:
            strings += [
                fmt_ms3(by_ref[(arm, ph, span)]["median"]) for arm in ARM_ORDER for ph in PHASES
            ]
        num_w[span] = max(_text_width_in(fig, renderer, s) for s in strings)
    ax_w = {s: plot_w - (COL_ML + 2 * num_w[s] + COL_GAP + COL_MR) for s in SPANS}
    for span in SPANS:
        if ax_w[span] < AX_W_FLOOR:
            raise PresentationError(f"{span}: value columns leave {ax_w[span]:.2f} in of axis")
        print_render(
            ARTEFACT,
            f"columns.{span} [D]",
            f"col_w={num_w[span]:.2f} in (measured), ax_w={ax_w[span]:.2f} in",
        )

    def column_glyphs(span, col, y_bot):
        """The column headers: a filled dot over the warm column, open over cold."""
        from matplotlib.lines import Line2D

        x_warm = gutter + col * col_w + ax_w[span] + COL_ML + num_w[span]
        x_cold = x_warm + COL_GAP + num_w[span]
        y = (y_bot + band_h + glyph_h / 2) / fig_h
        for x, face in ((x_warm, INK), (x_cold, PAPER)):
            fig.add_artist(
                Line2D(
                    [(x - num_w[span] / 2) / fig_w],
                    [y],
                    marker="o",
                    ms=2.9,
                    markerfacecolor=face,
                    markeredgecolor=INK,
                    markeredgewidth=0.8,
                    linestyle="none",
                    transform=fig.transFigure,
                )
            )

    def value_columns(span, col, y_bot, values):
        """One panel's two columns: (arm -> (warm, cold)) at each row centre."""
        x_warm = gutter + col * col_w + ax_w[span] + COL_ML + num_w[span]
        x_cold = x_warm + COL_GAP + num_w[span]
        for arm, (s_warm, s_cold) in values.items():
            y = (y_bot + (ys[arm] + 0.5) * row_h) / fig_h
            for x, s in ((x_warm, s_warm), (x_cold, s_cold)):
                fig.text(x / fig_w, y, s, ha="right", va="center", fontsize=FONT_MIN_PT, color=INK)

    # ---- band 1: benign deltas against B0 ----------------------------------
    band_label(y1_bot, f"benign path — median(arm) − median({control}), ms")
    # Majors thinned to what the narrowed axes hold without collision; the
    # dropped decades remain as unlabelled minors.
    ticks1, labels1 = [-1, 0, 10], ["−1", "0", "10"]
    minor1 = [-0.1, -0.01, -0.001, 0.001, 0.01, 0.1, 1]
    for col, span in enumerate(SPANS):
        ax = fig.add_axes(
            [(gutter + col * col_w) / fig_w, y1_bot / fig_h, ax_w[span] / fig_w, band_h / fig_h]
        )
        if use_log:
            ax.set_xscale("log")
            # Right headroom sized so the rightmost DOT clears the spine in the
            # narrowed axes -- at x1.6 the end-to-end markers clipped to half-circles.
            ax.set_xlim(min_pos / 1.6, xmax * 3.5)
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                ax.set_xscale("symlog", linthresh=linthresh, linscale=0.45)
            # Same right headroom as the log branch, same reason.
            ax.set_xlim(xmin * 1.35, xmax * 3.5)
        style_axis(ax)
        ax.set_xticks(ticks1)
        ax.set_xticks(minor1, minor=True)
        ax.set_xticklabels(labels1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            ax.axvline(0, color=INK, lw=0.6, zorder=1)
        pos = ax.get_position()
        for arm in ARM_ORDER:
            if arm == control or arm in refused_arms:
                continue
            for phase, dy, filled in PHASES_IN_ROW:
                y = ys[arm] + dy
                d = by_delta.get((arm, phase, span))
                if d is None:
                    raise PresentationError(f"no delta for {arm} / {phase} / {span} and no refusal")
                ax.plot(
                    [d["ci_low_ms"], d["ci_high_ms"]],
                    [y, y],
                    color=LATENCY_SPREAD,
                    lw=1.8,
                    solid_capstyle="butt",
                    zorder=3,
                )
                ax.plot(
                    [d["point_estimate_ms"]],
                    [y],
                    marker="o",
                    ms=2.6,
                    markerfacecolor=INK if filled else PAPER,
                    markeredgecolor=INK,
                    markeredgewidth=0.8,
                    linestyle="none",
                    zorder=4,
                )
                print_render(
                    ARTEFACT,
                    f"delta.{arm}.{phase}.{span} [M]",
                    f"{d['point_estimate_ms']:.4f} [{d['ci_low_ms']:.4f}, "
                    f"{d['ci_high_ms']:.4f}] {d['label']}",
                )
        column_glyphs(span, col, y1_bot)
        value_columns(
            span,
            col,
            y1_bot,
            {
                arm: tuple(fmt_ms3(by_delta[(arm, ph, span)]["point_estimate_ms"]) for ph in PHASES)
                for arm in ARM_ORDER
                if arm != control and arm not in refused_arms
            },
        )
        if col == 0:
            draw_tier_brackets(fig, pos, ys, fig_w)
            for arm in ARM_ORDER:
                y = pos.y0 + (ys[arm] + 0.5) / len(ARM_ORDER) * pos.height
                if arm == control:
                    lab, c = f"{arm}   baseline, 0", INK
                elif arm in refused_arms:
                    lab, c = f"{arm}  refused", VERMILLION
                else:
                    lab, c = arm, INK
                fig.text(
                    (gutter - 0.10) / fig_w,
                    y,
                    lab,
                    ha="right",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=c,
                )

    # ---- band 2: the refusal path, absolute --------------------------------
    band_label(y2_bot, "refusal path (chain-tamper) — absolute span latency, ms")
    decades = list(range(dec_lo, dec_hi + 1))
    ticks2 = [10**k for k in decades if (k - dec_lo) % 2 == 1]
    # Majors thinned to the ends of the decade ladder -- the narrowed axes
    # cannot hold three labelled decades without collision -- and the xlim
    # tightened to the data (±40 %), so the plotted range is not padded out to
    # decade boundaries the data never reaches. Dropped decades stay as
    # unlabelled minors.
    minor2 = sorted(set(10**k for k in decades if (k - dec_lo) % 2 == 0) | set(ticks2[1:-1]))
    ticks2 = [ticks2[0], ticks2[-1]] if len(ticks2) > 2 else ticks2
    labels2 = [f"{t:g}" for t in ticks2]
    for col, span in enumerate(REF_SPANS):
        ax = fig.add_axes(
            [(gutter + col * col_w) / fig_w, y2_bot / fig_h, ax_w[span] / fig_w, band_h / fig_h]
        )
        ax.set_xscale("log")
        ax.set_xlim(min(ref_plotted) / 1.4, max(ref_plotted) * 1.4)
        style_axis(ax)
        ax.set_xticks(ticks2)
        ax.set_xticks(minor2, minor=True)
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.xaxis.set_major_formatter(FixedFormatter(labels2))
        pos = ax.get_position()
        for arm in ARM_ORDER:
            for phase, dy, filled in PHASES_IN_ROW:
                y = ys[arm] + dy
                d = by_ref[(arm, phase, span)]
                ax.plot(
                    [d["p95"], d["p95"]],
                    [y - 0.17, y + 0.17],
                    color=LATENCY_SPREAD,
                    lw=1.2,
                    solid_capstyle="butt",
                    zorder=3,
                )
                ax.plot(
                    [d["median"]],
                    [y],
                    marker="o",
                    ms=2.6,
                    markerfacecolor=INK if filled else PAPER,
                    markeredgecolor=INK,
                    markeredgewidth=0.8,
                    linestyle="none",
                    zorder=4,
                )
                print_render(
                    ARTEFACT,
                    f"refusal.{arm}.{phase}.{span} [M]",
                    f"median={d['median']:.4f} p95={d['p95']:.4f} n={d['n']}",
                )
        column_glyphs(span, col, y2_bot)
        value_columns(
            span,
            col,
            y2_bot,
            {
                arm: tuple(fmt_ms3(by_ref[(arm, ph, span)]["median"]) for ph in PHASES)
                for arm in ARM_ORDER
            },
        )
        if col == 0:
            draw_tier_brackets(fig, pos, ys, fig_w)
            for arm in ARM_ORDER:
                y = pos.y0 + (ys[arm] + 0.5) / len(ARM_ORDER) * pos.height
                fig.text(
                    (gutter - 0.10) / fig_w,
                    y,
                    arm,
                    ha="right",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=INK,
                )
    # the fifth column of this band is deliberately empty (C1); the caption says why

    print_render(ARTEFACT, "labels.count [D]", 2 * (len(SPANS) * 7 + len(REF_SPANS) * 9))
    print_render(ARTEFACT, "labels.value", "the dot -- delta point estimate above, median below")
    print_render(
        ARTEFACT, "labels.format", "fmt_ms3: three-decimal ms, <0.001 below 0.0005 (shared)"
    )
    print_render(
        ARTEFACT,
        "labels.layout",
        "two right-aligned columns at each panel's right edge (warm, cold), row-centred",
    )

    # ---- one key, one provenance line --------------------------------------
    x_end = draw_key(
        fig,
        (
            ("dot-filled", "warm"),
            ("dot-open", "cold"),
            ("bar", "95 % bootstrap interval"),
            ("tick", "p95"),
        ),
        x_in=0.10,
        y_in=0.10,
    )
    fig.text(
        (fig_w - 0.05) / fig_w,
        0.10 / fig_h,
        f"n = {n} per arm, phase and span",
        ha="right",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    print_render(ARTEFACT, "key.end_x_in [D]", f"{x_end:.2f}")

    # ---- caption ------------------------------------------------------------
    caption = (
        "The RQ4 latency decomposition in one figure: the benign path against the baseline above, "
        "the refusal path below, five shared span columns, warm and cold dodged within each arm "
        "row (warm above the row centre; filled and open markers). UPPER BAND: the point is the "
        f"sealed median difference against {control} and the bar its 95 per cent bootstrap "
        "interval, read from the committed arm-pair record and never subtracted here; the axis is "
        f"symlog rather than log, linear within ±{linthresh:g} ms of zero, because two interval "
        "lower bounds, B2-broad-noexchange end to end "
        "in both phases, are negative -- the rule choosing between the two was fixed before the "
        "data were seen; intervals narrower than the marker lie under it, and the symlog "
        "compression near zero makes the one interval that crosses zero look widest. "
        f"{control} is the zero line. B1 has no marks because the sealed layer "
        "refuses every pair involving it, its static shared secret being invisible to the E.5 "
        "bitmask (ADR 0035); the row says so in vermillion rather than approximating. Every delta "
        "is a composite "
        "configuration difference: no pair against the baseline differs by one E.5 bit, so no "
        "delta is a mechanism cost and none is named as one (ADR 0041). LOWER BAND: the refusal "
        "path on the chain-tamper scenario, reported as its own series and never pooled with the "
        "benign path -- the exchange arms perform a failed round trip to the authorization server, "
        "which lands in the delegation span, while the capability arms do purely local work. "
        "Values are absolute (median dot, p95 tick, log10) because the sealed arm-pair delta is "
        "built from the benign series alone and emits nothing for this path; B1 appears here "
        "because the descriptive layer does not refuse it. Its end-to-end panel is not drawn: an "
        "absolute end-to-end latency represents no deployment on this in-process harness (C1), "
        f"and the one absolute end-to-end value stated is {control}'s own warm median, "
        f"{b0_e2e_med:.3f} ms, the fixed testbed overhead present in every arm. The two bands "
        "carry different quantities on different axes and are never summed or compared cell to "
        "cell. Every dot's value is set in the two right-aligned columns at its panel's right "
        "edge -- warm then cold, one line per arm row -- the median difference in the upper "
        "band, the median in the lower, in the suite's shared three-decimal millisecond format, "
        "in which a value under 0.0005 prints as <0.001 and never as a zero the record does not "
        "contain. The baseline row prints nothing (a printed 0 would state a measurement the "
        "record does not contain) and the refused row prints nothing. Interval bounds and "
        "p95 values are not printed and stand at full precision in the committed artefact. "
        "Interquartile widths are not drawn; they stand verbatim in the committed artefact "
        "this figure reads, and the interval shown in the upper band is the uncertainty of the "
        "median difference, not the spread of the data. The gutter groups the arms into the three "
        f"ladder tiers of the authority-surface figure. n is {n} per arm, phase and span after "
        "the pre-registered warm-up discard; pilot corpus, CPU unpinned, one machine."
    )
    import textwrap

    for line in textwrap.wrap(caption, 96):
        print(f"CAPTION {ARTEFACT} | {line}")

    enforce_placement(fig, ARTEFACT)
    assert_no_text_overlap(fig, ARTEFACT)
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
