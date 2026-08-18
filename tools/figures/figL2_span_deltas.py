"""FIG-L2 -- per-span latency deltas against B0, small multiples (RQ4).

Every mark is a field of the committed sealed ArmPairDelta records
(results/tables/results-latency-pilot-rq4-run2.json, DEVIATIONS D-014):
the point is `point_estimate_ms` = median(arm) - median(B0) for one span and
phase; the bar is the sealed 95 % bootstrap interval; the number at the right
is the treatment arm's IQR width from the sealed Descriptives. Nothing is
subtracted, pooled or interpolated here. B0 is the zero line; B1 has no row of
marks because the sealed layer REFUSES every pair involving it (ADR 0035), and
that refusal is what its row says.

Cold and warm are DODGED inside each arm row -- warm above the row centre,
cold below -- told apart by position and by marker fill, never by hue, and
never pooled into one mark. One band, so the arm labels, the tier brackets and
the panel headers are drawn once. The one hue on the figure is the
interval bar. Absolute end-to-end latency appears nowhere on this figure (C1);
the only absolute end-to-end value stated is B0's own warm median, in the
footer, as the fixed-testbed-overhead disclosure (CLAIMS_LEDGER A7), read from
the same artefact.

Axis: the rule fixed in D-014 before the data were seen -- log10 iff every
plotted point and interval bound is strictly positive, else symlog -- and the
branch that fired is printed. Pure presentation (ADR 0048).
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

ARTEFACT = "FIG-L2"
STEM = "figL2_span_deltas"

SPANS = ("setup", "delegation", "presentation", "boundary_verification", "end_to_end")
SPAN_TITLE = {
    "setup": "setup",
    "delegation": "delegation",
    "presentation": "presentation",
    "boundary_verification": "boundary verification",
    "end_to_end": "end to end",
}
PHASE_ROWS = ("warm", "cold")  # warm above: the row-1 estimand's phase
# Dodge within the arm row: warm above the centre, cold below. The offset is
# smaller than half the row, so a pair groups more tightly than two arms do.
PHASES_IN_ROW = (("warm", 0.18, True), ("cold", -0.18, False))


def draw_tier_brackets(fig, pos, ys, fig_w, fig_h):
    """FIG-0's ladder tiers beside the arm rows, so the two figures read as one.

    A hairline bracket and a rotated 8 pt label per tier, in the far-left
    column of the gutter. The tier assignment is FIG-0's own transcription of
    section E.1, imported rather than retyped.
    """
    from fig_authority_surface import ARM_GRANT, GRANT_LABEL
    from matplotlib.lines import Line2D

    tiers = {}
    for arm in ARM_ORDER:
        tiers.setdefault(ARM_GRANT[arm], []).append(ys[arm])
    for tier, rows in tiers.items():
        y0 = pos.y0 + (min(rows) + 0.06) / len(ARM_ORDER) * pos.height
        y1 = pos.y0 + (max(rows) + 0.94) / len(ARM_ORDER) * pos.height
        fig.add_artist(
            Line2D([0.16 / fig_w] * 2, [y0, y1], color=MIDGREY, lw=0.8, transform=fig.transFigure)
        )
        fig.text(
            0.10 / fig_w,
            (y0 + y1) / 2,
            GRANT_LABEL[tier],
            ha="center",
            va="center",
            rotation=90,
            fontsize=FONT_MIN_PT,
            color=MIDGREY,
        )


def main():
    mpl_setup()
    art = load_latency_rq4()
    control = art["control_arm"]
    deltas = art["arm_pair_deltas"]
    refusals = art["refusals"]
    print_render(ARTEFACT, "source.artefact", "results/tables/results-latency-pilot-rq4-run2.json")
    print_render(ARTEFACT, "source.control_arm [M]", control)
    print_render(ARTEFACT, "source.deltas [M]", len(deltas))
    print_render(ARTEFACT, "source.refusals [M]", len(refusals))

    by = {}
    for d in deltas:
        by[(d["treatment_arm"], d["phase"], d["span"])] = d
    refused_arms = sorted({r["treatment_arm"] for r in refusals})
    print_render(ARTEFACT, "refused_arms [M sealed]", refused_arms)
    # every refusal must be total for its arm -- a partial refusal would need
    # a different row treatment and is refused here rather than half-drawn
    for arm in refused_arms:
        got = {(r["phase"], r["span"]) for r in refusals if r["treatment_arm"] == arm}
        want = {(p, s) for p in PHASE_ROWS for s in SPANS}
        if got != want:
            raise PresentationError(f"{arm}: refused for {len(got)} of {len(want)} cells; partial")

    labels = {d["label"] for d in deltas}
    mechs = {d["mechanism"] for d in deltas}
    unmod = {len(d["unmodelled"]) for d in deltas}
    ns = {d["treatment"]["n"] for d in deltas} | {d["control"]["n"] for d in deltas}
    print_render(ARTEFACT, "deltas.labels [M]", sorted(labels))
    print_render(ARTEFACT, "deltas.mechanisms [M]", sorted(str(m) for m in mechs))
    print_render(ARTEFACT, "deltas.unmodelled_lengths [M]", sorted(unmod))
    print_render(ARTEFACT, "deltas.n_values [M]", sorted(ns))
    if len(ns) != 1:
        raise PresentationError(f"n differs across deltas: {ns}; the panel header cannot say one n")
    n = ns.pop()

    # ---- the pre-committed axis rule ---------------------------------------
    plotted = []
    for d in deltas:
        plotted += [d["point_estimate_ms"], d["ci_low_ms"], d["ci_high_ms"]]
    nonpos = [v for v in plotted if v <= 0]
    min_pos = min(v for v in plotted if v > 0)
    use_log = not nonpos
    print_render(ARTEFACT, "axis.rule", "log10 iff every point and bound > 0, else symlog (D-014)")
    print_render(ARTEFACT, "axis.values_not_positive [D]", len(nonpos))
    print_render(ARTEFACT, "axis.min_positive_value_ms [D]", min_pos)
    print_render(ARTEFACT, "axis.branch", "log10" if use_log else "symlog")
    linthresh = 10 ** math.floor(math.log10(min_pos))
    print_render(ARTEFACT, "axis.symlog_linthresh_ms [D 10^floor(log10 min positive)]", linthresh)
    xmin = min(plotted)
    xmax = max(plotted)
    print_render(ARTEFACT, "axis.plotted_min_ms [M]", xmin)
    print_render(ARTEFACT, "axis.plotted_max_ms [M]", xmax)

    # A7: the fixed testbed overhead is B0's own warm benign end-to-end median
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

    # ---- geometry, in inches ------------------------------------------------
    gutter = 1.72  # tier bracket + arm labels
    plot_w, iqr_w, gap = 1.036, 0.38, 0.16
    col_w = plot_w + iqr_w + gap
    # ONE band: warm and cold are dodged inside each arm row, so the row is
    # taller and there is no second copy of the labels, brackets or headers.
    top, head_h, row_h = 0.30, 0.32, 0.30
    xtick_h, footer_h = 0.30, 0.34
    fig_w = gutter + len(SPANS) * col_w + 0.05
    fig_h = top + head_h + len(ARM_ORDER) * row_h + xtick_h + footer_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(PAPER)

    y_top = fig_h - top - head_h

    def ax_rect(col):
        x0 = (gutter + col * col_w) / fig_w
        y0 = (y_top - len(ARM_ORDER) * row_h) / fig_h
        return [x0, y0, plot_w / fig_w, len(ARM_ORDER) * row_h / fig_h]

    # Four labelled ticks: at 0.14 in per decade a label per decade collides
    # (the overlap guard said so). Every decade still gets an unlabelled
    # minor tick, so the scale is readable between the labels.
    ticks = [-1, 0, 0.1, 10]
    tick_labels = ["−1", "0", "0.1", "10"]
    minor = [-0.1, -0.01, -0.001, 0.001, 0.01, 1]

    ys = {arm: len(ARM_ORDER) - 1 - i for i, arm in enumerate(ARM_ORDER)}
    if True:  # one band; the loop over phases moved inside the arm row
        for col, span in enumerate(SPANS):
            ax = fig.add_axes(ax_rect(col))
            if use_log:
                ax.set_xscale("log")
                ax.set_xlim(min_pos / 1.6, xmax * 1.6)
            else:
                with warnings.catch_warnings():
                    # matplotlib warns about the DEFAULT limits at scale-set
                    # time; the real limits follow on the next line
                    warnings.simplefilter("ignore", UserWarning)
                    ax.set_xscale("symlog", linthresh=linthresh, linscale=0.45)
                ax.set_xlim(xmin * 1.35, xmax * 1.35)
            ax.set_ylim(-0.5, len(ARM_ORDER) - 0.5)
            ax.set_autoscale_on(False)  # limits are fixed above; no artist may move them
            for sp in ("top", "right", "left"):
                ax.spines[sp].set_visible(False)
            ax.spines["bottom"].set_color(MIDGREY)
            ax.spines["bottom"].set_linewidth(0.5)
            ax.set_yticks([])
            ax.set_xticks(ticks)
            ax.set_xticks(minor, minor=True)
            ax.set_xticklabels(tick_labels)
            ax.tick_params(
                axis="x", colors=INK, labelsize=FONT_MIN_PT, length=2.2, width=0.5, pad=1.5
            )
            ax.tick_params(axis="x", which="minor", colors=MIDGREY, length=1.4, width=0.4)
            # zero: the B0 baseline. (matplotlib re-warns about linthresh on
            # every artist added to a symlog axis; the limits are frozen above.)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                ax.axvline(0, color=MIDGREY, lw=0.5, zorder=1)
            # panel header
            ax.text(
                0.0,
                1.0 + 0.19 / (len(ARM_ORDER) * row_h),
                SPAN_TITLE[span],
                transform=ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=FONT_MIN_PT,
                color=INK,
            )
            ax.text(
                0.0,
                1.0 + 0.04 / (len(ARM_ORDER) * row_h),
                f"n = {n}",
                transform=ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=FONT_MIN_PT,
                color=MIDGREY,
            )
            # IQR column header
            fig.text(
                (gutter + col * col_w + plot_w + iqr_w + 0.08) / fig_w,
                (y_top + 0.19) / fig_h,
                "IQR",
                ha="right",
                va="bottom",
                fontsize=FONT_MIN_PT,
                color=MIDGREY,
            )
            pos = ax.get_position()
            for arm in ARM_ORDER:
                if arm == control or arm in refused_arms:
                    continue
                for phase, dy, filled in PHASES_IN_ROW:
                    y = ys[arm] + dy
                    d = by.get((arm, phase, span))
                    if d is None:
                        raise PresentationError(
                            f"no delta for {arm} / {phase} / {span} and no refusal either"
                        )
                    ax.plot(
                        [d["ci_low_ms"], d["ci_high_ms"]],
                        [y, y],
                        color=LATENCY_SPREAD,
                        lw=1.6,
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
                    # The arm's IQR width, verbatim, on its own mark's line and
                    # in its own mark's weight -- ink for warm, grey for cold --
                    # so the column is read the same way the panel is.
                    fig.text(
                        (gutter + col * col_w + plot_w + iqr_w + 0.08) / fig_w,
                        pos.y0 + (y + 0.5) / len(ARM_ORDER) * pos.height,
                        fmt_ms3(d["treatment"]["iqr"]),
                        ha="right",
                        va="center",
                        fontsize=FONT_MIN_PT,
                        color=INK if filled else MIDGREY,
                    )
                    print_render(
                        ARTEFACT,
                        f"delta.{arm}.{phase}.{span} [M]",
                        f"{d['point_estimate_ms']:.4f} [{d['ci_low_ms']:.4f}, "
                        f"{d['ci_high_ms']:.4f}] "
                        f"iqr={d['treatment']['iqr']:.4f} {d['label']}",
                    )
            # The gutter is drawn ONCE, beside the first panel: one set of arm
            # labels and one set of tier brackets now serve both phases.
            if col == 0:
                draw_tier_brackets(fig, pos, ys, fig_w, fig_h)
                for arm in ARM_ORDER:
                    y = pos.y0 + (ys[arm] + 0.5) / len(ARM_ORDER) * pos.height
                    if arm == control:
                        lab, col_ = f"{arm}   baseline, 0", INK
                    elif arm in refused_arms:
                        lab, col_ = f"{arm}  refused, ADR 0035", MIDGREY
                    else:
                        lab, col_ = arm, INK
                    fig.text(
                        (gutter - 0.10) / fig_w,
                        y,
                        lab,
                        ha="right",
                        va="center",
                        fontsize=FONT_MIN_PT,
                        color=col_,
                    )

    y_x = (footer_h + 0.02) / fig_h
    fig.text(
        (gutter + len(SPANS) * col_w / 2) / fig_w,
        y_x,
        f"median(arm) − median({control}), ms   ·   {'log10' if use_log else 'symlog'}"
        + ("" if use_log else f", linear within ±{linthresh:g} ms")
        + "   ·   IQR = the arm's interquartile width, ms",
        ha="center",
        va="bottom",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    # The key: the marks themselves and a short label each, one line, as FIG-1
    # does it. Every disclosure that used to sit here is in the caption below.
    key = (
        ("dot-filled", "warm"),
        ("dot-open", "cold"),
        ("bar", "95 % bootstrap interval"),
    )
    draw_key(fig, key, x_in=0.10, y_in=0.14)
    footer = ["key line"]
    print_render(ARTEFACT, "footer.lines", len(footer))

    caption = (
        "Per-span latency against the unprotected baseline. Each panel is one span of the "
        "pre-registered decomposition; each row is one arm; the point is the sealed median "
        "difference "
        f"against {control} and the bar its 95 per cent bootstrap interval, both read from the "
        "committed arm-pair record and never subtracted here. The number at the right of each row "
        "is "
        "the arm's interquartile width, printed because the sealed descriptives expose the width "
        "and not the quartiles; a width the column cannot resolve prints as below 0.001. Intervals "
        "narrower than the marker lie under it, and the symlog compression near zero makes the one "
        "interval that crosses zero look widest. Warm and cold are dodged within each arm "
        "row, warm above the row centre, and differ in marker fill "
        f"as well as position. {control} is the zero line. B1 has no marks because the sealed "
        f"layer "
        "refuses every pair involving it, its static shared secret being invisible to the E.5 "
        "bitmask "
        "(ADR 0035); the row says so rather than approximating. The axis is shared and is symlog "
        "rather than log because two interval lower bounds, B2-broad-noexchange end to end in both "
        "phases, are negative; the rule choosing between the two was fixed before the data were "
        "seen. "
        "Every delta is a composite configuration difference: no pair against the baseline "
        "differs by "
        "one E.5 bit, so no delta is a mechanism cost and none is named as one (ADR 0041). No "
        "absolute "
        f"end-to-end latency is drawn; {control}'s warm end-to-end median of {b0_e2e_med:.3f} ms "
        f"is "
        "fixed testbed overhead present in every arm, stated once as the disclosure it is. Data "
        "are "
        "pilot-corpus, unpinned, in-process on one machine; n is 210 per arm and phase after the "
        "pre-registered warm-up discard. The gutter groups the arms into the three ladder tiers "
        "of the authority-surface figure. Colour carries one meaning each and survives greyscale "
        "by lightness: ink for the point, one blue for the sealed interval, grey for structure."
    )
    import textwrap

    for line in textwrap.wrap(caption, 96):
        print(f"CAPTION {ARTEFACT} | {line}")

    enforce_placement(fig, ARTEFACT)
    assert_no_text_overlap(fig, ARTEFACT)
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
