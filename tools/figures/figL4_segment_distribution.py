# ruff: noqa: E501
"""FIG-L4 -- how the measured segment's latency is DISTRIBUTED, per arm.

Built on the Commander's instruction of 2026-08-29 ("按照数据，直接构建新图"),
given AFTER the conflict below was reported, and recorded here so the figure
never presents itself as uncontested:

  * FIGURE_PLAN.md §H: a tools/figures script needing any statistical decision
    of its own is analysis code, "surface it, do not write it". A kernel
    density has one such decision, its bandwidth. It is taken here by the
    fixed, named rule below (Scott's factor, n^(-1/5), over log10 ms), printed
    per arm, and every recorded sample is drawn beneath the density so a reader
    can see what the smoothing was fitted to.
  * FIGURE_PLAN.md §E.7: the warm-up discard must be the sealed
    `discard_warmup` with the count stated. No committed artefact carries the
    post-discard samples, only their descriptives, so this script RUNS the
    sealed functions on the frozen raw record -- `discard_warmup`,
    `benign_series`, `describe` from analysis/latency.py -- rather than
    re-implementing them. That is an import beyond ADR 0048's named exception
    (the label-token mapping); the alternative, a second implementation of a
    sealed rule in the presentation layer, was judged worse. Sealed code is run,
    never modified. Two fail-closed checks tie the run to the committed
    decision artefact: the sample accounting (loaded, excluded, discarded, into
    decision) must equal the artefact's `inputs`, and the B3 and B0 medians
    produced here must equal `decision.treatment.median` and
    `decision.control.median` exactly.

What is drawn. One row per arm in ladder order. The quantity is the row-1
estimand's own segment, presentation + boundary verification, warm phase,
benign path, after the sealed warm-up discard (n = 210 per arm). The axis is
log10 milliseconds: the samples run from below 0.001 ms (B0) to above 10 ms
(the capability arms), more than three decades, and a linear axis would flatten
five arms to zero width. Each row carries: the smoothed density (blue, the
suite's spread hue); every sample as a hairline tick beneath it (ink); the
median as a filled dot and the p95 as a tick, both from the sealed `describe`.
B0's median is repeated down the figure as a grey dashed rule, because the
study's rule is deltas against B0 (C1) and the samples are unpaired, so the
reference is a line rather than a differenced axis.

What is NOT drawn: no end-to-end span (C1); no 20 ms margin (it binds the
median difference, not a sample distribution); no G-3 line; no per-arm interval
(the sealed bootstrap exists for the B3 - B0 difference only); no mechanism
label on any arm (ADR 0041: every configuration difference here is composite).
Values printed to stdout for cross-check are tagged [D] where they were
computed by the sealed functions here rather than read from a committed
artefact; only B3's and B0's medians coincide with a committed number and are
tagged [M].
"""

import json
import math
import statistics
import textwrap

from _common import (
    ARM_ORDER,
    FONT_MIN_PT,
    INK,
    LATENCY_SPREAD,
    MIDGREY,
    PAPER,
    RESULTS_RAW,
    TEXT_W_IN,
    PresentationError,
    assert_no_text_overlap,
    enforce_placement,
    load_row1_decisions,
    mpl_setup,
    plt,
    print_render,
    save,
)
from matplotlib.lines import Line2D

from analysis.latency import (  # sealed: RUN here, never modified (docstring)
    MEASURED_SEGMENT_SPANS,
    REFUSAL_PATH_SCENARIO,
    Sample,
    benign_series,
    describe,
    discard_warmup,
)

ARTEFACT = "FIG-L4"
STEM = "figL4_segment_distribution"
SAMPLE_FIELDS = ("arm", "scenario_id", "phase", "batch", "repetition", "span", "value_ms")
PHASE = "warm"
KDE_POINTS = 256
BANDWIDTH_RULE = "Scott: bandwidth = n^(-1/5) x std(log10 ms), Gaussian kernel, in log10 space"


def main():
    mpl_setup()
    raw_path = RESULTS_RAW / "latency-pilot.json"
    if not raw_path.is_file():
        raise PresentationError(f"missing {raw_path}")
    record = json.loads(raw_path.read_text(encoding="utf-8"))
    decision_art = load_row1_decisions()[2]  # run 2, the protocol-compliant run
    print_render(ARTEFACT, "source.samples", "results/raw/latency-pilot.json")
    print_render(
        ARTEFACT, "source.decision", "results/tables/results-latency-pilot-run2.json (run 2)"
    )

    # ---- the sealed pipeline, run as the composition root ran it -------------
    all_samples = [Sample(**{k: rec[k] for k in SAMPLE_FIELDS}) for rec in record["samples"]]
    benign = [s for s in all_samples if s.scenario_id != REFUSAL_PATH_SCENARIO]
    per_batch = record["plan"]["warmup_per_batch"]
    kept = discard_warmup(benign, per_batch=per_batch)
    inputs = decision_art["inputs"]
    accounting = {
        "samples_loaded": len(all_samples),
        "samples_excluded_refusal_path": len(all_samples) - len(benign),
        "samples_discarded_warmup": len(benign) - len(kept),
        "samples_into_decision": len(kept),
        "warmup_per_batch": per_batch,
    }
    for key, val in accounting.items():
        if inputs[key] != val:
            raise PresentationError(f"{key}: this run {val}, committed decision {inputs[key]}")
        print_render(ARTEFACT, f"accounting.{key} [M]", val)

    values, desc = {}, {}
    for arm in ARM_ORDER:
        values[arm] = benign_series(kept, arm=arm, phase=PHASE)
        if any(v <= 0 for v in values[arm]):
            raise PresentationError(f"{arm}: a non-positive sample; log10 cannot hold it")
        desc[arm] = describe(values[arm])
    ns = {d.n for d in desc.values()}
    if len(ns) != 1 or ns.pop() != decision_art["decision"]["treatment"]["n"]:
        raise PresentationError(f"n per arm {ns} differs from the committed decision's n")
    n = desc["B3"].n
    for arm, side in (("B3", "treatment"), ("B0", "control")):
        committed = decision_art["decision"][side]["median"]
        if desc[arm].median != committed:
            raise PresentationError(
                f"{arm} median here {desc[arm].median} != committed {committed}"
            )
        print_render(ARTEFACT, f"median.{arm} [M = committed {side}]", committed)
    for arm in ARM_ORDER:
        d = desc[arm]
        print_render(
            ARTEFACT,
            f"describe.{arm} [D sealed describe]",
            f"n={d.n} median={d.median:.4f} p95={d.p95:.4f} iqr={d.iqr:.4f}",
        )
    print_render(
        ARTEFACT, "segment", " + ".join(MEASURED_SEGMENT_SPANS) + f", {PHASE}, benign path"
    )

    logs = {arm: [math.log10(v) for v in values[arm]] for arm in ARM_ORDER}
    lo = min(min(v) for v in logs.values())
    hi = max(max(v) for v in logs.values())
    xlim = (math.floor(lo * 10) / 10 - 0.15, math.ceil(hi * 10) / 10 + 0.15)
    print_render(ARTEFACT, "axis.log10_ms.data_range [D]", f"{lo:.3f} .. {hi:.3f}")
    print_render(ARTEFACT, "axis.log10_ms.xlim [D]", f"{xlim[0]:.2f} .. {xlim[1]:.2f}")
    print_render(ARTEFACT, "kde.rule", BANDWIDTH_RULE)
    print_render(ARTEFACT, "kde.points", KDE_POINTS)
    for arm in ARM_ORDER:
        sd = statistics.pstdev(logs[arm])
        print_render(
            ARTEFACT,
            f"kde.bandwidth.{arm} [D]",
            f"{n ** (-0.2):.4f} x {sd:.4f} = {n ** (-0.2) * sd:.4f} log10 ms",
        )

    # ---- geometry, in inches -----------------------------------------------
    fig_w = TEXT_W_IN
    n_rows = len(ARM_ORDER)
    row_h = 0.36
    band_h = n_rows * row_h
    top, title_h, xt_h, foot_h = 0.10, 0.62, 0.42, 0.34
    fig_h = top + title_h + band_h + xt_h + foot_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(PAPER)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def width_in(text):
        probe = fig.text(0.5, 0.5, text, fontsize=FONT_MIN_PT)
        w = probe.get_window_extent(renderer).width / fig.dpi
        probe.remove()
        return w

    gutter = 0.30 + max(width_in(a) for a in ARM_ORDER) + 0.10
    ax_w = fig_w - gutter - 0.12
    print_render(ARTEFACT, "geometry.fig_in [D]", f"{fig_w:.3f} x {fig_h:.3f}")
    print_render(ARTEFACT, "geometry.gutter_in [D]", f"{gutter:.3f} (measured label)")

    y_cursor = fig_h - top
    fig.text(
        0.10 / fig_w,
        (y_cursor - 0.02) / fig_h,
        "How the boundary cost is distributed, per configuration",
        ha="left",
        va="top",
        fontsize=FONT_MIN_PT + 1,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.10 / fig_w,
        (y_cursor - 0.24) / fig_h,
        f"n = {n} per configuration after the warm-up discard  ·  pilot corpus  ·  CPU unpinned",
        ha="left",
        va="top",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    fig.text(
        0.10 / fig_w,
        (y_cursor - 0.42) / fig_h,
        "density smoothed over log10 ms (Scott); every sample is drawn beneath it",
        ha="left",
        va="top",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    y_cursor -= title_h
    y_bot = y_cursor - band_h

    ax = fig.add_axes([gutter / fig_w, y_bot / fig_h, ax_w / fig_w, band_h / fig_h])
    ax.set_xlim(*xlim)
    ax.set_ylim(-0.5, n_rows - 0.5)
    ax.set_autoscale_on(False)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(INK)
    ax.spines["bottom"].set_linewidth(0.6)
    ax.set_yticks([])
    decades = [
        k for k in range(math.floor(xlim[0]), math.ceil(xlim[1]) + 1) if xlim[0] <= k <= xlim[1]
    ]
    ax.set_xticks(decades)
    ax.set_xticklabels([f"{10.0**k:g}" for k in decades])
    minors = [
        k + math.log10(m)
        for k in range(math.floor(xlim[0]) - 1, math.ceil(xlim[1]) + 1)
        for m in (2, 5)
        if xlim[0] <= k + math.log10(m) <= xlim[1]
    ]
    ax.set_xticks(minors, minor=True)
    ax.tick_params(axis="x", colors=INK, labelsize=FONT_MIN_PT, length=2.4, width=0.6, pad=1.5)
    ax.tick_params(axis="x", which="minor", colors=INK, length=1.4, width=0.4)
    ax.set_xlabel(
        "presentation + boundary verification, warm, ms",
        fontsize=FONT_MIN_PT,
        color=INK,
        labelpad=2,
    )

    ys = {arm: n_rows - 1 - i for i, arm in enumerate(ARM_ORDER)}
    b0_med = math.log10(desc["B0"].median)
    ax.axvline(b0_med, color=MIDGREY, lw=0.7, ls=(0, (3, 2)), zorder=1)

    for arm in ARM_ORDER:
        y = ys[arm]
        parts = ax.violinplot(
            [logs[arm]],
            positions=[y],
            vert=False,
            widths=0.82,
            showmeans=False,
            showextrema=False,
            showmedians=False,
            points=KDE_POINTS,
            bw_method="scott",
        )
        for body in parts["bodies"]:
            body.set_facecolor(LATENCY_SPREAD)
            body.set_edgecolor(LATENCY_SPREAD)
            body.set_alpha(0.45)
            body.set_linewidth(0.6)
            body.set_zorder(2)
        ax.vlines(logs[arm], y - 0.10, y + 0.10, color=INK, lw=0.35, alpha=0.55, zorder=3)
        d = desc[arm]
        ax.plot(
            [math.log10(d.p95)] * 2,
            [y - 0.22, y + 0.22],
            color=LATENCY_SPREAD,
            lw=1.2,
            solid_capstyle="butt",
            zorder=4,
        )
        ax.plot(
            [math.log10(d.median)],
            [y],
            marker="o",
            ms=3.0,
            markerfacecolor=INK,
            markeredgecolor=PAPER,
            markeredgewidth=0.6,
            linestyle="none",
            zorder=5,
        )

    from figL23_latency import draw_tier_brackets

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

    # ---- key, one line ------------------------------------------------------
    yk = 0.16
    x = 0.12
    tf = fig.transFigure
    items = []
    fig.add_artist(
        Line2D(
            [x / fig_w],
            [yk / fig_h],
            marker="o",
            ms=3.0,
            markerfacecolor=INK,
            markeredgecolor=PAPER,
            markeredgewidth=0.6,
            linestyle="none",
            transform=tf,
        )
    )
    items.append((x + 0.08, "median"))
    x += 0.08 + width_in("median") + 0.28
    fig.add_artist(
        Line2D(
            [x / fig_w] * 2,
            [(yk - 0.05) / fig_h, (yk + 0.05) / fig_h],
            color=LATENCY_SPREAD,
            lw=1.2,
            transform=tf,
        )
    )
    items.append((x + 0.07, "p95"))
    x += 0.07 + width_in("p95") + 0.28
    for dx in (0.0, 0.03, 0.05, 0.09, 0.10, 0.14):
        fig.add_artist(
            Line2D(
                [(x + dx) / fig_w] * 2,
                [(yk - 0.035) / fig_h, (yk + 0.035) / fig_h],
                color=INK,
                lw=0.35,
                alpha=0.55,
                transform=tf,
            )
        )
    items.append((x + 0.21, "one sample each"))
    x += 0.21 + width_in("one sample each") + 0.28
    fig.add_artist(
        Line2D(
            [x / fig_w, (x + 0.18) / fig_w],
            [yk / fig_h] * 2,
            color=MIDGREY,
            lw=0.7,
            ls=(0, (3, 2)),
            transform=tf,
        )
    )
    items.append((x + 0.25, "B0 median, the baseline"))
    for xx, label in items:
        fig.text(
            xx / fig_w, yk / fig_h, label, ha="left", va="center", fontsize=FONT_MIN_PT, color=INK
        )

    # ---- caption, printed ----------------------------------------------------
    caption = (
        "Distribution of the measured segment, presentation plus boundary verification, per "
        "configuration: warm phase, benign path, pilot corpus, after the pre-registered warm-up "
        f"discard, n = {n} per arm. Each row shows the smoothed density of the samples on a log10 "
        "millisecond axis (Scott's bandwidth over log10 values, printed per arm at build time), every "
        "recorded sample as a hairline tick beneath the density, the median as a filled dot and the p95 "
        "as a tick, both from the sealed descriptive functions; the dashed rule repeats B0's median "
        f"({desc['B0'].median:.4f} ms, the committed control median) down the figure, because the "
        "study reports latency as "
        "differences against B0 and the samples are unpaired, so the reference is a line rather than a "
        "differenced axis. The axis is logarithmic because the samples span more than three decades. "
        "The capability arms' densities are bimodal: their samples fall into two separated groups, "
        "visible as two lobes of the density and two bands of ticks, which is consistent with the "
        "disclosed absence of CPU pinning (core migration cannot be excluded) and is presented as a "
        "threat to the precision of the descriptives, not as a finding about any mechanism; no "
        "statistic of the split is computed. No interval is drawn: the sealed bootstrap exists for the B3 minus B0 median "
        "difference only, and the 20 ms margin binds that difference, not a sample distribution, so it "
        "does not appear here. Every difference between arms is a composite configuration difference "
        "and none is named as a mechanism cost. B3 and B3+ differ in configuration only by the jti "
        "cache; their campaign security outcomes are identical, see the state board. Pilot corpus, not "
        "the confirmatory corpus; CPU unpinned; one machine."
    )
    for line in textwrap.wrap(caption, 96):
        print(f"CAPTION {ARTEFACT} | {line}")

    enforce_placement(fig, ARTEFACT)
    assert_no_text_overlap(fig, ARTEFACT)
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
