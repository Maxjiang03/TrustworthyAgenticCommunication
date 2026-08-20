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
end-to-end panel is not drawn (C1) and the empty slot says so. B1 appears here
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

Every dot prints its value beside it (Commander ruling 2026-08-20), in the
suite's shared three-decimal millisecond format. Placement is MEASURED, not
estimated -- the per-character estimate is a closed defect class in this
suite -- and decided per arm row from the rendered label widths against the
room the panel actually has: warm right of the row's marks and cold left
where both sides fit; both labels chained on whichever single side fits
where one does not; and inside the row's own interval bar, knocked out on
paper, for the one row whose zero-crossing interval leaves no room on
either side. Association is by sub-row: the warm value sits on the warm
sub-row, the cold value on the cold, exactly like the marks.
"""

import math
import warnings

from _common import (
    ARM_ORDER,
    FONT_MIN_PT,
    INK,
    LATENCY_SPREAD,
    MIDGREY,
    PAPER,
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
# The value labels sit a shade inside the mark's dodge (0.15 vs 0.18 row
# units): the 8 pt line box then clears the neighbouring row's labels, and the
# 0.006 in of vertical slack against the mark is imperceptible while the
# sub-row association stays unambiguous.
LABEL_DY = 0.15


def _label_width_px(ax, renderer, text, x_probe, y_probe):
    """The rendered width of `text`, measured, never estimated.

    Per-character estimates are a closed defect class in this suite; the probe
    is drawn at a finite in-axis position (x=0 breaks a log transform),
    measured, and removed.
    """
    probe = ax.text(x_probe, y_probe, text, fontsize=FONT_MIN_PT)
    width = probe.get_window_extent(renderer).width
    probe.remove()
    return width


def place_row_labels(ax, renderer, union, items, counts):
    """One arm row's two value labels, placed where measurement says they fit.

    `union` is the row's full mark extent in data coords (both phases' bars in
    the delta band; median-to-p95 in the refusal band). `items` is
    ((y, dot_x, text)) for warm then cold. The ladder of placements, tried in
    order against MEASURED widths: warm right of the union and cold left of it
    (the default); both chained on the left; both chained on the right; and
    last, inside the union itself on the stretch clear of the dots, knocked
    out on paper -- needed only where a zero-crossing interval spans nearly
    the whole panel. Association is by sub-row y throughout. A row that fits
    nowhere raises rather than printing a cropped or overprinted number.
    """
    bbox = ax.get_window_extent(renderer)
    dpi = ax.figure.dpi
    pad = 0.030 * dpi
    edge = 0.020 * dpi
    to_px = ax.transData.transform
    to_data = ax.transData.inverted().transform
    x0p = to_px((union[0], 0.0))[0]
    x1p = to_px((union[1], 0.0))[0]
    (y_w, dot_w, s_w, bar_w), (y_c, dot_c, s_c, bar_c) = items
    w_w = _label_width_px(ax, renderer, s_w, union[1], y_w)
    w_c = _label_width_px(ax, renderer, s_c, union[1], y_c)

    def put(x_px, y, s, ha):
        ax.text(
            to_data((x_px, 0.0))[0],
            y,
            s,
            ha=ha,
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
            zorder=3.6,
            bbox=dict(facecolor=PAPER, edgecolor="none", pad=0.15),
        )

    room_right = bbox.x1 - edge - x1p
    room_left = x0p - (bbox.x0 + edge)
    if room_right >= w_w + pad and room_left >= w_c + pad:
        put(x1p + pad, y_w, s_w, "left")
        put(x0p - pad, y_c, s_c, "right")
        counts["split"] += 1
    elif room_left >= w_w + w_c + 3 * pad:
        put(x0p - pad, y_c, s_c, "right")
        put(x0p - 2 * pad - w_c, y_w, s_w, "right")
        counts["chained-left"] += 1
    elif room_right >= w_w + w_c + 3 * pad:
        put(x1p + pad, y_w, s_w, "left")
        put(x1p + 2 * pad + w_w, y_c, s_c, "left")
        counts["chained-right"] += 1
    else:
        dots = sorted(to_px((x, 0.0))[0] for x in (dot_w, dot_c))
        stretches = ((x0p, dots[0]), (dots[-1], x1p))
        s0, s1 = max(stretches, key=lambda pair: pair[1] - pair[0])
        if (s1 - s0) < w_w + w_c + 4 * pad:
            raise PresentationError(
                f"no measured room for the value pair {s_w!r}/{s_c!r} on any side or on the bar"
            )
        # The left slot goes to the phase whose own bar starts leftmost, inset
        # so that bar's END TIP stays visible past the knockout -- an interval
        # endpoint is data and a label must not eat it. The right slot lands
        # mid-bar, where both of its own endpoints are clear of it anyway.
        tip = min(0.10 * dpi, (s1 - s0) - (w_w + w_c + 4 * pad))
        warm_takes_left = to_px((bar_w[0], 0.0))[0] <= to_px((bar_c[0], 0.0))[0]
        (yl, sl), (yr, sr) = (
            ((y_w, s_w), (y_c, s_c)) if warm_takes_left else ((y_c, s_c), (y_w, s_w))
        )
        put(s0 + pad + tip, yl, sl, "left")
        put(s1 - pad, yr, sr, "right")
        counts["on-bar"] += 1


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
    print_render(ARTEFACT, "refusal.axis.decades [D]", f"{dec_lo}..{dec_hi}")

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
    top, hdr_h, blab_h, xt_h, band_gap, key_h = 0.06, 0.24, 0.20, 0.24, 0.10, 0.26
    fig_h = top + hdr_h + blab_h + band_h + xt_h + band_gap + blab_h + band_h + xt_h + key_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(PAPER)
    print_render(ARTEFACT, "geometry.fig_in [D]", f"{fig_w:.2f} x {fig_h:.2f}")

    ys = {arm: len(ARM_ORDER) - 1 - i for i, arm in enumerate(ARM_ORDER)}
    y_hdr = fig_h - top - hdr_h
    y1_top = y_hdr - blab_h
    y1_bot = y1_top - band_h
    y2_top = y1_bot - xt_h - band_gap - blab_h
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
            (y_bot + band_h + 0.05) / fig_h,
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

    # Every dot's value label, collected while the marks are drawn and placed
    # AFTER both bands exist, from one rendered measurement pass.
    pending_labels = []

    # ---- band 1: benign deltas against B0 ----------------------------------
    band_label(y1_bot, f"benign path — median(arm) − median({control}), ms")
    ticks1, labels1 = [-1, 0, 0.1, 10], ["−1", "0", "0.1", "10"]
    minor1 = [-0.1, -0.01, -0.001, 0.001, 0.01, 1]
    for col, span in enumerate(SPANS):
        ax = fig.add_axes(
            [(gutter + col * col_w) / fig_w, y1_bot / fig_h, plot_w / fig_w, band_h / fig_h]
        )
        if use_log:
            ax.set_xscale("log")
            ax.set_xlim(min_pos / 1.6, xmax * 1.6)
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                ax.set_xscale("symlog", linthresh=linthresh, linscale=0.45)
            ax.set_xlim(xmin * 1.35, xmax * 1.35)
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
            row = {}
            for phase, dy, filled in PHASES_IN_ROW:
                y = ys[arm] + dy
                d = by_delta.get((arm, phase, span))
                if d is None:
                    raise PresentationError(f"no delta for {arm} / {phase} / {span} and no refusal")
                row[phase] = d
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
                    ms=3.4,
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
            pending_labels.append(
                (
                    ax,
                    (
                        min(r["ci_low_ms"] for r in row.values()),
                        max(r["ci_high_ms"] for r in row.values()),
                    ),
                    tuple(
                        (
                            ys[arm] + (LABEL_DY if ph == "warm" else -LABEL_DY),
                            row[ph]["point_estimate_ms"],
                            fmt_ms3(row[ph]["point_estimate_ms"]),
                            (row[ph]["ci_low_ms"], row[ph]["ci_high_ms"]),
                        )
                        for ph in PHASES
                    ),
                )
            )
        if col == 0:
            draw_tier_brackets(fig, pos, ys, fig_w)
            for arm in ARM_ORDER:
                y = pos.y0 + (ys[arm] + 0.5) / len(ARM_ORDER) * pos.height
                if arm == control:
                    lab, c = f"{arm}   baseline, 0", INK
                elif arm in refused_arms:
                    lab, c = f"{arm}  refused", MIDGREY
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
    labels2 = [f"{t:g}" for t in ticks2]
    minor2 = [10**k for k in decades if (k - dec_lo) % 2 == 0]
    for col, span in enumerate(REF_SPANS):
        ax = fig.add_axes(
            [(gutter + col * col_w) / fig_w, y2_bot / fig_h, plot_w / fig_w, band_h / fig_h]
        )
        ax.set_xscale("log")
        ax.set_xlim(10**dec_lo / 1.5, 10**dec_hi * 1.5)
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
                    [y - 0.14, y + 0.14],
                    color=LATENCY_SPREAD,
                    lw=1.0,
                    solid_capstyle="butt",
                    zorder=3,
                )
                ax.plot(
                    [d["median"]],
                    [y],
                    marker="o",
                    ms=3.4,
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
            ref_row = {ph: by_ref[(arm, ph, span)] for ph in PHASES}
            pending_labels.append(
                (
                    ax,
                    (
                        min(r["median"] for r in ref_row.values()),
                        max(r["p95"] for r in ref_row.values()),
                    ),
                    tuple(
                        (
                            ys[arm] + (LABEL_DY if ph == "warm" else -LABEL_DY),
                            ref_row[ph]["median"],
                            fmt_ms3(ref_row[ph]["median"]),
                            (ref_row[ph]["median"], ref_row[ph]["p95"]),
                        )
                        for ph in PHASES
                    ),
                )
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
    # the fifth column of this band is deliberately empty
    fig.text(
        (gutter + 4 * col_w + plot_w / 2) / fig_w,
        (y2_bot + band_h / 2) / fig_h,
        "not drawn",
        ha="center",
        va="center",
        fontsize=FONT_MIN_PT,
        color=MIDGREY,
    )

    # ---- the value labels: one measurement pass over the finished bands ----
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    counts = {"split": 0, "chained-left": 0, "chained-right": 0, "on-bar": 0}
    for ax, union, items in pending_labels:
        place_row_labels(ax, renderer, union, items, counts)
    print_render(ARTEFACT, "labels.count [D]", 2 * len(pending_labels))
    print_render(ARTEFACT, "labels.value", "the dot -- delta point estimate above, median below")
    print_render(
        ARTEFACT, "labels.format", "fmt_ms3: three-decimal ms, <0.001 below 0.0005 (shared)"
    )
    print_render(ARTEFACT, "labels.placement_by_measure [D]", counts)

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
        y_in=0.13,
    )
    fig.text(
        (x_end + 0.34) / fig_w,
        0.13 / fig_h,
        "each dot prints its value, three-decimal ms",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=MIDGREY,
    )
    fig.text(
        (fig_w - 0.05) / fig_w,
        0.13 / fig_h,
        f"n = {n} per arm, phase and span",
        ha="right",
        va="center",
        fontsize=FONT_MIN_PT,
        color=MIDGREY,
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
        "bitmask (ADR 0035); the row says so rather than approximating. Every delta is a composite "
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
        "cell. Every dot prints its value beside its own sub-row -- the median difference above, "
        "the median below -- in the suite's shared three-decimal millisecond format, in which a "
        "value under 0.0005 prints as <0.001 and never as a zero the record does not contain; "
        "labels sit left or right of the row's marks wherever the panel has measured room, and "
        "inside the one interval wide enough to hold them where it has none. Interval bounds and "
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
