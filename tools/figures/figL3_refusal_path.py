"""FIG-L3 -- refusal-path latency, its own series, never pooled with the benign path.

On the chain-tamper scenario the exchange arms perform a FAILED round trip to
the authorization server, which lands in `delegation`, while the capability
arms do purely local work; pooling that cell with the benign path would
average a network refusal with local cryptography (ADR 0026, section J.3 item
12). The sealed layer therefore reports it under `series = refusal_path`, and
this figure draws that series alone.

The form is the only one the sealed layer emits for this series: absolute
`Descriptives` (median, p95, IQR) from `span_descriptives`. `arm_pair_delta`
builds from the benign series alone and emits no refusal-path delta, so no
delta is drawn and none is computed here. The end-to-end panel is NOT drawn:
C1 forbids stating an absolute end-to-end latency for any protected arm, and
no sealed delta exists to draw instead. The four component spans are drawn.
Every mark is a field of the committed D-014 artefact. Pure presentation
(ADR 0048).
"""

import math

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

ARTEFACT = "FIG-L3"
STEM = "figL3_refusal_path"

SPANS = ("setup", "delegation", "presentation", "boundary_verification")
OMITTED = "end_to_end"
SPAN_TITLE = {
    "setup": "setup",
    "delegation": "delegation",
    "presentation": "presentation",
    "boundary_verification": "boundary verification",
}
PHASE_ROWS = ("warm", "cold")
SERIES = "refusal_path"
# Dodge within the arm row, as FIG-L2 does: warm above the centre, cold below.
PHASES_IN_ROW = (("warm", 0.18, True), ("cold", -0.18, False))

from figL2_span_deltas import draw_tier_brackets  # noqa: E402  (one idiom, one definition)


def main():
    mpl_setup()
    art = load_latency_rq4()
    reports = [r for r in art["span_reports"] if r["series"] == SERIES]
    print_render(ARTEFACT, "source.artefact", "results/tables/results-latency-pilot-rq4-run2.json")
    print_render(ARTEFACT, "source.series [M sealed constant]", SERIES)
    print_render(ARTEFACT, "source.reports [M]", len(reports))
    by = {(r["arm"], r["phase"], r["span"]): r["descriptives"] for r in reports}
    want = {(a, p, s) for a in ARM_ORDER for p in PHASE_ROWS for s in SPANS + (OMITTED,)}
    if set(by) != want:
        raise PresentationError(
            f"refusal-path reports do not cover arms x phases x spans: {len(by)} of {len(want)}"
        )
    ns = {d["n"] for d in by.values()}
    if len(ns) != 1:
        raise PresentationError(f"n differs across refusal-path reports: {ns}")
    n = ns.pop()
    print_render(ARTEFACT, "reports.n [M]", n)
    print_render(ARTEFACT, "panel.omitted [C1]", OMITTED)

    plotted = []
    for (a, p, s), d in by.items():
        if s == OMITTED:
            continue
        plotted += [d["median"], d["p95"]]
    if any(v <= 0 for v in plotted):
        raise PresentationError(
            "a refusal-path median or p95 is not positive; a log axis cannot hold it"
        )
    lo, hi = min(plotted), max(plotted)
    print_render(ARTEFACT, "axis.branch", "log10 (every plotted value > 0)")
    print_render(ARTEFACT, "axis.plotted_min_ms [M]", lo)
    print_render(ARTEFACT, "axis.plotted_max_ms [M]", hi)

    # ---- geometry, in inches ------------------------------------------------
    gutter = 1.72  # tier bracket + arm labels
    iqr_w, gap = 0.38, 0.16
    fig_w = 9.65
    plot_w = (fig_w - gutter - 0.05) / len(SPANS) - iqr_w - gap
    col_w = plot_w + iqr_w + gap
    # ONE band, warm and cold dodged inside each arm row (see FIG-L2).
    top, head_h, row_h = 0.46, 0.32, 0.30
    xtick_h, footer_h = 0.30, 0.34
    fig_h = top + head_h + len(ARM_ORDER) * row_h + xtick_h + footer_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(PAPER)

    y_top = fig_h - top - head_h

    def ax_rect(col):
        x0 = (gutter + col * col_w) / fig_w
        y0 = (y_top - len(ARM_ORDER) * row_h) / fig_h
        return [x0, y0, plot_w / fig_w, len(ARM_ORDER) * row_h / fig_h]

    dec_lo = math.floor(math.log10(lo))
    dec_hi = math.ceil(math.log10(hi))
    # Label every second decade -- at ~0.23 in per decade a label per decade
    # collides (the overlap guard says so); the decades between keep an
    # unlabelled minor tick, so the scale reads between the labels.
    decades = list(range(dec_lo, dec_hi + 1))
    ticks = [10**k for k in decades if (k - dec_lo) % 2 == 1]
    tick_labels = [f"{t:g}" for t in ticks]
    minor = [10**k for k in decades if (k - dec_lo) % 2 == 0]

    fig.text(
        0.05 / fig_w,
        (fig_h - 0.12) / fig_h,
        "Refusal-path latency (chain-tamper scenario)",
        ha="left",
        va="top",
        fontsize=FONT_MIN_PT + 1,
        color=INK,
        fontweight="bold",
    )

    ys = {arm: len(ARM_ORDER) - 1 - i for i, arm in enumerate(ARM_ORDER)}
    if True:  # one band; the loop over phases moved inside the arm row
        for col, span in enumerate(SPANS):
            ax = fig.add_axes(ax_rect(col))
            ax.set_xscale("log")
            ax.set_xlim(10**dec_lo / 1.5, 10**dec_hi * 1.5)
            ax.set_ylim(-0.5, len(ARM_ORDER) - 0.5)
            ax.set_autoscale_on(False)
            for sp in ("top", "right", "left"):
                ax.spines[sp].set_visible(False)
            ax.spines["bottom"].set_color(MIDGREY)
            ax.spines["bottom"].set_linewidth(0.5)
            ax.set_yticks([])
            ax.set_xticks(ticks)
            ax.set_xticks(minor, minor=True)
            # a log axis labels its minor ticks by default; nothing here may
            ax.xaxis.set_minor_formatter(NullFormatter())
            ax.xaxis.set_major_formatter(FixedFormatter(tick_labels))
            ax.tick_params(
                axis="x", colors=INK, labelsize=FONT_MIN_PT, length=2.2, width=0.5, pad=1.5
            )
            ax.tick_params(axis="x", which="minor", colors=MIDGREY, length=1.4, width=0.4)
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
                for phase, dy, filled in PHASES_IN_ROW:
                    y = ys[arm] + dy
                    d = by[(arm, phase, span)]
                    # p95: the sealed value as a tick beside its own median
                    ax.plot(
                        [d["p95"], d["p95"]],
                        [y - 0.13, y + 0.13],
                        color=LATENCY_SPREAD,
                        lw=0.9,
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
                    fig.text(
                        (gutter + col * col_w + plot_w + iqr_w + 0.08) / fig_w,
                        pos.y0 + (y + 0.5) / len(ARM_ORDER) * pos.height,
                        fmt_ms3(d["iqr"]),
                        ha="right",
                        va="center",
                        fontsize=FONT_MIN_PT,
                        color=INK if filled else MIDGREY,
                    )
                    print_render(
                        ARTEFACT,
                        f"refusal.{arm}.{phase}.{span} [M]",
                        f"median={d['median']:.4f} p95={d['p95']:.4f} "
                        f"iqr={d['iqr']:.4f} n={d['n']}",
                    )
            # The gutter is drawn ONCE, beside the first panel.
            if col == 0:
                draw_tier_brackets(fig, pos, ys, fig_w, fig_h)
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

    y_x = (footer_h + 0.02) / fig_h
    fig.text(
        (gutter + len(SPANS) * col_w / 2) / fig_w,
        y_x,
        "absolute span latency, ms   ·   log10   ·   IQR = interquartile width, ms",
        ha="center",
        va="bottom",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    key = (
        ("dot-filled", "warm median"),
        ("dot-open", "cold median"),
        ("tick", "p95"),
    )
    draw_key(fig, key, x_in=0.10, y_in=0.14)
    footer = ["key line"]
    print_render(ARTEFACT, "footer.lines", len(footer))

    caption = (
        "Refusal-path latency on the chain-tamper scenario, reported as its own series and never "
        "pooled with the benign path: on that cell the exchange arms perform a failed round trip "
        "to "
        "the authorization server, which lands in the delegation span, while the capability arms "
        "do "
        "purely local work, so a pooled figure would average a network refusal with local "
        "cryptography. Each panel is one component span; each row is one arm; the point is the "
        "sealed median, the tick the sealed p95, and the number at the right the interquartile "
        "width, "
        "all read verbatim from the committed span descriptives. Values are absolute, and the "
        "axis is "
        "log10 because every plotted value is positive and the spans differ by four orders of "
        "magnitude; this differs from the delta figure by necessity, because the sealed arm-pair "
        "delta is built from the benign series alone and emits nothing for this path, and no "
        "delta is "
        "computed outside the sealed layer. The end-to-end panel is omitted: an absolute "
        "end-to-end "
        "latency represents no deployment on this in-process harness (C1) and no sealed delta "
        "exists "
        "to draw in its place. B1 appears here because the descriptive layer does not refuse it; "
        "only "
        "the bit-labelled delta does. Warm and cold are dodged within each arm row, warm above "
        "the row centre, distinguished by position and marker "
        f"fill; n is {n} per arm and phase after the pre-registered warm-up discard; pilot corpus, "
        "unpinned, one machine. The gutter groups the arms into the three ladder tiers of the "
        "authority-surface figure. Colour carries one meaning each and survives greyscale by "
        "lightness: ink for the median, one blue for the sealed p95, grey for structure."
    )
    import textwrap

    for line in textwrap.wrap(caption, 96):
        print(f"CAPTION {ARTEFACT} | {line}")

    enforce_placement(fig, ARTEFACT)
    assert_no_text_overlap(fig, ARTEFACT)
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
