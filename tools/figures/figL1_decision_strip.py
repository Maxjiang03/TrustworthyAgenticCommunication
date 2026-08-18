"""FIG-L1 -- the row-1 equivalence decision, as the sealed layer returned it.

ONE decision exists in this study (ADR 0026): median(B3) - median(B0) over the
measured segment (presentation + boundary_verification), warm, and the claim
stands iff the 95 % bootstrap interval's UPPER BOUND is below the 20 ms margin.
This figure draws that rule and nothing else. Both committed runs are shown,
each labelled, because D-009 clause 2 keeps run 1's verdict as the reported
one while its closure says the descriptives quoted must be run 2's -- one row
per run is the only shape that does not describe two runs as one.

Everything drawn is a field of a committed sealed Decision object
(results/tables/results-latency-pilot.json, -run2.json). Nothing is
recomputed; no interval is formed here; the margin is the artefact's own.
Pure presentation (ADR 0048).
"""

from _common import (
    FONT_MIN_PT,
    INK,
    LATENCY_MARGIN,
    LATENCY_SPREAD,
    MIDGREY,
    PAPER,
    assert_no_text_overlap,
    enforce_placement,
    load_row1_decisions,
    mpl_setup,
    plt,
    print_render,
    save,
)

ARTEFACT = "FIG-L1"
STEM = "figL1_decision_strip"


def main():
    mpl_setup()
    runs = load_row1_decisions()

    rows = []
    for run in (2, 1):  # protocol-compliant run on top
        art = runs[run]
        d = art["decision"]
        rows.append(
            dict(
                run=run,
                verdict=d["verdict"],
                point=d["point_estimate_ms"],
                lo=d["ci"]["low"],
                hi=d["ci"]["high"],
                margin=d["margin_ms"],
                conf=d["confidence"],
                resamples=d["resamples"],
                n=d["treatment"]["n"],
                warmup=art.get("run", {}).get("warmup_discard_applied", False),
            )
        )
        for k in ("verdict", "point", "lo", "hi", "margin", "conf", "resamples", "n", "warmup"):
            print_render(ARTEFACT, f"run{run}.{k} [M sealed Decision]", rows[-1][k])
    margins = {r["margin"] for r in rows}
    if len(margins) != 1:
        raise RuntimeError(f"the two runs carry different margins: {margins}")
    margin = margins.pop()
    for r in rows:
        # The rule, applied by the sealed layer; re-stated here only to refuse a
        # figure whose drawn geometry could disagree with the printed word.
        if (r["hi"] < margin) != (r["verdict"] == "stands"):
            raise RuntimeError(
                f"run {r['run']}: verdict {r['verdict']!r} vs hi {r['hi']} / margin {margin}"
            )

    # ---- geometry: portrait-placeable, one strip plus a magnifier ------------
    fig_w, fig_h = 5.50, 3.10
    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(PAPER)

    # main strip: 0 .. margin + 2 ms, linear (a signed difference)
    ax = fig.add_axes([0.05, 0.63, 0.92, 0.28])
    xmax = margin + 2.0
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.6, 2.4)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(MIDGREY)
    ax.spines["bottom"].set_linewidth(0.6)
    ax.set_yticks([])
    ax.set_xticks([0, 5, 10, 15, 20])
    ax.tick_params(axis="x", colors=INK, labelsize=FONT_MIN_PT, length=2.5, width=0.6, pad=2)
    ax.set_xlabel(
        "median(B3) − median(B0), measured segment, warm  [ms]", fontsize=FONT_MIN_PT, labelpad=2
    )

    # the margin: the study's only equivalence decision
    # The one falsification threshold in the study, in the one colour that
    # means falsification across the chapter (FIG-1's disagreement mark).
    ax.axvline(margin, color=LATENCY_MARGIN, lw=1.0, ymin=0.0, ymax=1.0, zorder=2)
    ax.text(
        margin - 0.15,
        2.3,
        f"{margin:g} ms margin",
        ha="right",
        va="top",
        fontsize=FONT_MIN_PT,
        color=INK,
    )

    labels = {2: "run 2 · warm-up discarded · n = %d", 1: "run 1 · warm-up not discarded · n = %d"}
    for y, r in zip((1.3, 0.0), rows):
        # CI bar in the one accent hue; point in ink; the UPPER BOUND as a
        # heavier vertical tick, because that is what the rule reads.
        ax.plot(
            [r["lo"], r["hi"]],
            [y, y],
            color=LATENCY_SPREAD,
            lw=3.0,
            solid_capstyle="butt",
            zorder=3,
        )
        ax.plot([r["point"]], [y], marker="o", ms=4.0, color=INK, zorder=4)
        ax.plot([r["hi"], r["hi"]], [y - 0.28, y + 0.28], color=INK, lw=1.2, zorder=4)
        ax.text(
            0.15,
            y + 0.30,
            labels[r["run"]] % r["n"],
            ha="left",
            va="bottom",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
        ax.text(
            r["hi"] + 0.35,
            y,
            f"upper bound {r['hi']:.4f} ms  <  {margin:g}  →  {r['verdict']}",
            ha="left",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
    ax.set_yticks([])

    # ---- magnifier: the interval region, where the bars are actually readable
    lo_all = min(r["lo"] for r in rows)
    hi_all = max(r["hi"] for r in rows)
    span = hi_all - lo_all
    mx0, mx1 = lo_all - 0.35 * span, hi_all + 0.35 * span
    axm = fig.add_axes([0.05, 0.13, 0.36, 0.30])
    axm.set_xlim(mx0, mx1)
    axm.set_ylim(-0.6, 3.4)
    for spine in ("top", "right", "left"):
        axm.spines[spine].set_visible(False)
    axm.spines["bottom"].set_color(MIDGREY)
    axm.spines["bottom"].set_linewidth(0.6)
    axm.set_yticks([])
    axm.tick_params(axis="x", colors=INK, labelsize=FONT_MIN_PT, length=2.5, width=0.6, pad=2)
    axm.xaxis.set_major_locator(plt.MaxNLocator(4))
    axm.xaxis.set_major_formatter(plt.FormatStrFormatter("%.3f"))
    for y, r in zip((1.6, 0.0), rows):
        axm.plot(
            [r["lo"], r["hi"]],
            [y, y],
            color=LATENCY_SPREAD,
            lw=3.0,
            solid_capstyle="butt",
            zorder=3,
        )
        axm.plot([r["point"]], [y], marker="o", ms=4.0, color=INK, zorder=4)
        axm.plot([r["hi"], r["hi"]], [y - 0.28, y + 0.28], color=INK, lw=1.2, zorder=4)
        axm.text(
            r["point"],
            y + 0.40,
            f"{r['point']:.4f}",
            ha="center",
            va="bottom",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
    axm.text(
        mx1,
        3.30,
        "detail: the interval region, ms",
        ha="right",
        va="top",
        fontsize=FONT_MIN_PT,
        color=MIDGREY,
    )

    # leaders from the strip's interval region to the magnifier
    def fig_ax_x(a, x):
        """Figure-fraction x of data x on axes `a`."""
        x0, x1 = a.get_xlim()
        pos = a.get_position()
        return pos.x0 + (x - x0) / (x1 - x0) * pos.width

    from matplotlib.lines import Line2D

    for xx, mm in ((lo_all, mx0), (hi_all, mx1)):
        fig.add_artist(
            Line2D(
                [fig_ax_x(ax, xx), fig_ax_x(axm, mm)],
                [ax.get_position().y0, axm.get_position().y1],
                transform=fig.transFigure,
                color=MIDGREY,
                lw=0.5,
                linestyle=(0, (2, 2)),
            )
        )

    # ---- provenance box, right of the magnifier ------------------------------
    r2 = rows[0]
    prov = [
        "PILOT corpus, not confirmatory",
        "warm path · refusal path excluded",
        "CPU unpinned · in-process, one machine",
        f"{r2['resamples']:,} resamples · seed 4815162342",
        f"{int(r2['conf'] * 100)} % bootstrap interval",
        "rule: interval UPPER BOUND < margin",
        "ADR 0026: the only equivalence decision",
        "reported verdict is run 1's (D-009 cl. 2)",
        "run 2 is the protocol-compliant re-run",
    ]
    y = 0.47
    for line in prov:
        fig.text(0.56, y, line, ha="left", va="top", fontsize=FONT_MIN_PT, color=MIDGREY)
        y -= 0.052
    print_render(ARTEFACT, "provenance.lines", len(prov))

    # ---- caption ------------------------------------------------------------
    caption = (
        "The row-1 equivalence decision, the study's only one. Each row is a committed sealed "
        "Decision object: the point is the median difference between B3 and B0 over the measured "
        "segment, presentation plus boundary verification, on the warm path; the bar is its "
        f"{int(r2['conf'] * 100)} per cent bootstrap interval; the heavier tick marks the "
        "interval's upper "
        f"bound, which is what the rule reads against the {margin:g} ms margin. Run 2 applied the "
        "pre-registered warm-up discard and is the protocol-compliant run; run 1 did not, and its "
        "verdict is nevertheless the reported one under D-009 clause 2. Both return stands: "
        f"upper bounds {rows[0]['hi']:.4f} and {rows[1]['hi']:.4f} ms. The detail panel shows the "
        "interval region at a scale where the bars can be read; on the main axis they are narrower "
        "than the point marker. Data are pilot-corpus and unpinned; the G-3 5 ms threshold "
        "governs an "
        "isolated pinned microbenchmark and is not drawn. Colour carries one meaning each and "
        "survives greyscale by lightness: ink for the point, one blue for the sealed interval, "
        "vermillion for the margin the interval must not cross, which is the same colour the "
        "state board reserves for a cell that disagreed with the pre-registration."
    )
    import textwrap

    for line in textwrap.wrap(caption, 96):
        print(f"CAPTION {ARTEFACT} | {line}")

    enforce_placement(fig, ARTEFACT)
    assert_no_text_overlap(fig, ARTEFACT)
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
