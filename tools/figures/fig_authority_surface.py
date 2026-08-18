"""FIG-0 — the boundary authority surface (RQ1, specification analysis).

Nine ladder arms x the seven elements of the frozen ontology `Omega`, each cell
placed on a THREE-STEP LADDER against the user's task grant `U_task`:

    +   admitted, ABOVE the grant   the amplification -- TV23 itself
    .   admitted, AT the grant      the arm may do what the task needs
    -   in the grant, NARROWED AWAY the intended contraction, NOT a failure
    (blank) outside the grant and not admitted

`required` is `U_task`, NOT the concrete request `R`. `R` appears only as the
filled/open probe marker on the column headers; it never enters the cell state.
That is deliberate: the surface is about what an arm's credential PERMITS
against what the task NEEDS, and `R` is one request drawn from that space.

WHAT THIS FIGURE IS. The authority SURFACE, derived from frozen artefacts. It
addresses RQ1 (which authorization properties the specifications guarantee and
which they defer), NOT RQ2 (measured excess): no exercised dimension is present,
so nothing here is a campaign measurement. Every count is DERIVED. Inputs, all
sealed and read-only:

  Omega, the seven (action, resource) elements   src/harness/authorizer/omega_gamma_v1.json
  U_task and the capability chain C_sets         fixtures/confirmatory/sealed/*.json
  which grant each arm carries                   the SS E.1 ladder, see ARM_GRANT below

`C_n` and `U_task` differ between the F1/F2/F3+benign scenarios and the F4/F5
scenarios, so the surface is drawn once per configuration rather than averaged.

Every number rendered is printed to stdout (ADR 0048).
"""

import json

from _common import (
    ARM_ORDER,
    BLOCKED,
    FONT_MIN_PT,
    INK,
    LADDER_AT,
    LANDSCAPE,
    MIDGREY,
    PAPER,
    PORTRAIT,
    REPO_ROOT,
    PresentationError,
    mpl_setup,
    plt,
    print_render,
    save,
)
from matplotlib.patches import Rectangle

ARTEFACT = "FIG-0"
STEM = "fig_authority_surface"

# Which grant each SS E.1 arm carries. This is not a choice made here: it is
# read off the arm construction and recorded with its source, because the whole
# figure turns on it.
#   B0                      no boundary check at all -- src/sut/baselines/b0.py,
#                           campaign_driver.py:159 provisions it with {}
#   B1                      "expresses no authority, no audience and no scope"
#                           -- runner.py:451-458 (a shared secret authenticates,
#                           it does not authorize)
#   B2-broad-*              ladder_grant="broad" -> "the coarse `Omega` grant"
#                           -- campaign_driver.py:142-147, runner.py:497-500
#   B2-exchange-task[-DPoP] ladder_grant="task"  -> "C_0 = U_task"
#                           -- campaign_driver.py:148-157, runner.py:496-497
#   B-cap, B3, B3+          the capability chain; the boundary enforces C_n
#                           -- campaign_driver.py:164-166, capability_path.py:814
ARM_GRANT = {
    "B0": "omega",
    "B1": "omega",
    "B2-broad-noexchange": "omega",
    "B2-exchange-broad": "omega",
    "B2-exchange-task": "u_task",
    "B2-exchange-task-DPoP": "u_task",
    "B-cap": "c_n",
    "B3": "c_n",
    "B3+": "c_n",
}
# Kept short: these run vertically beside their own tier and must fit inside that
# tier's height AT 8 pt. The floor is not negotiable, so the label gives way.
GRANT_LABEL = {"omega": "Ω grant", "u_task": "C₀ task", "c_n": "Cₙ chain"}

# The two chain configurations the corpus defines. Named by the scenario whose
# sealed file supplies the sets; both are read, never assumed equal.
CONFIGS = (
    ("I", "F1 · F2 · F3 · benign", "cf-f1-root"),
    ("II", "F4 · F5", "cf-f4-sensitive-egress"),
)

# The ladder, in ladder order. Each state carries fill AND a glyph, so none is
# distinguishable by colour alone and all four survive greyscale
# (FIGURE_PLAN.md §D). The glyphs ARE the ladder: + above the grant, · at it,
# − below it.
# ONE hue at four weights. These states are ORDERED -- above / at / below the
# task grant, plus off-scale -- so the sequential rule applies, not the
# categorical one: a single hue, light to dark, never a set of unrelated hues.
# It is the state board's hue, so the two matrix figures read as one system,
# and the ORDER of the fills is the reading: the darkest cell is the one
# furthest above the grant, which is the finding this figure exists to show.
LADDER_TOP = BLOCKED  # same ink as a measured block, a different fact -- see the key
S_AMP, S_AT, S_NARROWED, S_OUT = "amplified", "at_grant", "narrowed", "outside"
GLYPH = {S_AMP: "+", S_AT: "·", S_NARROWED: "−", S_OUT: ""}


def load_omega():
    path = REPO_ROOT / "src" / "harness" / "authorizer" / "omega_gamma_v1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    elements = [tuple(e) for e in doc["omega"]["elements"]]
    if len(elements) != 7:
        raise PresentationError(f"Omega must have 7 elements, found {len(elements)}")
    return elements


def load_config(scenario_id):
    """Returns (U_task, C_n). `U_task` is what `required` means in this figure."""
    path = REPO_ROOT / "fixtures" / "confirmatory" / "sealed" / f"{scenario_id}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    u_task = {tuple(x) for x in doc["U_task"]}
    c_sets = [{tuple(x) for x in c} for c in doc["C_sets"]]
    if c_sets[0] != u_task:
        raise PresentationError(f"{scenario_id}: C_0 is not U_task; the ladder claim is wrong")
    if not c_sets[-1] <= u_task:
        raise PresentationError(
            f"{scenario_id}: C_n is not contained in U_task, so the chain did not "
            "contract and the narrowed state would be meaningless"
        )
    return u_task, c_sets[-1]


def probed_elements(scenario_ids):
    """Which Omega elements the corpus actually REQUESTS (`R`) in this config.

    Feeds the column markers only. `R` never enters a cell state.
    """
    out = set()
    for sid in scenario_ids:
        path = REPO_ROOT / "fixtures" / "confirmatory" / "sealed" / f"{sid}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        out |= {tuple(x) for x in doc.get("R", [])}
    return out


def scenarios_of(config_key):
    root = REPO_ROOT / "fixtures" / "confirmatory" / "sealed"
    ids = sorted(p.stem for p in root.glob("*.json"))
    if config_key == "I":
        return [s for s in ids if not s.startswith(("cf-f4", "cf-f5"))]
    return [s for s in ids if s.startswith(("cf-f4", "cf-f5"))]


def state_of(element, admitted, required):
    in_a, in_r = element in admitted, element in required
    if in_a and not in_r:
        return S_AMP
    if in_a and in_r:
        return S_AT
    if in_r:
        return S_NARROWED
    return S_OUT


def draw_cell(ax, x, y, w, h, state):
    """Fill PLUS glyph for every state; the amplification is the only heavy ink.

    `narrowed` was formerly a hatched cell with a warning-weight orange border,
    sitting beside the black amplification in the legend -- four channels all
    reading as a defect. C_n subset U_task IS delegation monotonicity, the thing
    the capability arms are built to do, so it carries the lightest weight of the
    hue, subordinate to the amplification rather than parallel to it.

    Weight tracks POSITION ON THE LADDER and nothing else, so the eye reads the
    surface in the order the quantity runs: solid above the grant, a tint at it,
    an outline below it, nothing off it. Greyscale luma 51 / 192 / 255 / 255, and
    the two that share paper are separated by their glyph and their outline
    weight -- which is why every state on this figure carries a glyph at all.
    """
    if state == S_AMP:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=LADDER_TOP, edgecolor=LADDER_TOP, lw=0.6))
        glyph_colour = PAPER
    elif state == S_AT:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=LADDER_AT, edgecolor=LADDER_AT, lw=0.5))
        glyph_colour = INK
    elif state == S_NARROWED:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=PAPER, edgecolor=LADDER_TOP, lw=0.7))
        glyph_colour = LADDER_TOP
    else:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=PAPER, edgecolor="#dddddd", lw=0.5))
        glyph_colour = MIDGREY
    if GLYPH[state]:
        ax.text(
            x + w / 2,
            y + h / 2,
            GLYPH[state],
            ha="center",
            va="center",
            fontsize=FONT_MIN_PT,
            color=glyph_colour,
            fontweight="bold",
        )


def measured_width_in(strings, size=FONT_MIN_PT):
    """The widest of these strings, in inches, as matplotlib will actually set it.

    Text extents depend on the font and the point size, not on the figure that
    hosts them, so a throwaway canvas at the same dpi answers the question
    before the real figure exists -- which is what lets the header band be
    MEASURED rather than guessed at.
    """
    probe = plt.figure(figsize=(1, 1))
    r = probe.canvas.get_renderer()
    widest = 0.0
    for text in strings:
        t = probe.text(0, 0, text, fontsize=size)
        widest = max(widest, t.get_window_extent(renderer=r).width / probe.dpi)
    plt.close(probe)
    return widest


def main():
    mpl_setup()
    omega = load_omega()
    print_render(ARTEFACT, "omega.elements [M omega_gamma_v1.json]", len(omega))

    # ---- geometry, authored to fit the landscape text block. Explicit vertical
    # bands, so nothing sits at a hand-tuned constant a longer string outgrows.
    cw, rh = 0.38, 0.27
    title_band = 0.40
    # The 45 deg headers rise by width x sin(45) from their anchor, and the band
    # that has to clear them was a CONSTANT -- "about 1.29 in" -- taken from
    # eyeballing an earlier render. The longest element label outgrew it and put
    # a header through the panel title, the fourth overprint of this kind on
    # this suite. It is measured now: the widest string that will be drawn,
    # rotated, plus the anchor offset and a gap under the title baseline.
    # Both markers, because the two glyphs need not set to the same width.
    header_strings = [f"{m} {a} | {b}" for a, b in omega for m in ("●", "○")]
    header_strings += ["amplified [D]", "narrowed [D]"]
    header_reach = 0.7072 * measured_width_in(header_strings)
    header_band = header_reach + 0.10
    print_render(ARTEFACT, "geometry.header_reach_in [M rendered extent]", f"{header_reach:.3f}")
    print_render(ARTEFACT, "geometry.header_band_in [D]", f"{header_band:.3f}")
    legend_band = 0.54  # two rows
    note_band = 0.0  # the caption is printed, not drawn
    top = title_band + header_band
    bottom = legend_band + note_band + 0.10
    left = 1.55
    # The right margin holds the 45 deg header of the last count column AND
    # the B3/B3+ bracket, so it is wider than a column gutter would suggest.
    gap, cnt_w, right = 0.40, 0.42, 0.62
    ncol = len(omega)
    panel_w = ncol * cw + 2 * cnt_w  # two count columns: amplified, narrowed
    fig_w = left + panel_w + gap + panel_w + right
    fig_h = top + len(ARM_ORDER) * rh + bottom
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    def row_y(i):
        return fig_h - top - (i + 1) * rh

    for i, arm in enumerate(ARM_ORDER):
        ax.text(
            left - 0.10,
            row_y(i) + rh / 2,
            arm,
            ha="right",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )

    tier_rows = {}
    for i, arm in enumerate(ARM_ORDER):
        tier_rows.setdefault(ARM_GRANT[arm], []).append(i)
    for tier, rows in tier_rows.items():
        y0, y1 = row_y(rows[-1]), row_y(rows[0]) + rh
        label = GRANT_LABEL[tier]
        need = len(label) * 0.055
        if need > (y1 - y0):
            raise PresentationError(
                f"tier label {label!r} needs {need:.2f} in but its tier is "
                f"{y1 - y0:.2f} in tall; shorten the label, never the type"
            )
        ax.plot([0.10, 0.10], [y0 + 0.03, y1 - 0.03], color=MIDGREY, lw=0.8)
        ax.text(
            0.06,
            (y0 + y1) / 2,
            label,
            ha="center",
            va="center",
            rotation=90,
            fontsize=FONT_MIN_PT,
            color=MIDGREY,
        )
        print_render(ARTEFACT, f"tier.{tier}.arms", len(rows))

    # No on-canvas text block at all (Commander ruling, 2026-08-17, extended
    # 2026-08-18). The RQ tag was the last of it, and a figure that has to
    # label itself with its own research question is not carrying its weight.
    # Everything that argued rather than decoded -- the evidence class, the
    # `required` definition, the marker key, the B3/B3+ disclosure -- is in
    # the caption, PRINTED below so it travels with the artefact instead of
    # being retyped into LaTeX.

    probed_by_config = {}
    for p, (key, families, source_scenario) in enumerate(CONFIGS):
        x0 = left + p * (panel_w + gap)
        required, c_n = load_config(source_scenario)
        probed = probed_elements(scenarios_of(key))
        probed_by_config[key] = probed
        print_render(ARTEFACT, f"config{key}.source [M sealed scenario]", source_scenario)
        print_render(ARTEFACT, f"config{key}.required_is [M]", "U_task (not R)")
        print_render(ARTEFACT, f"config{key}.U_task_size [M]", len(required))
        print_render(ARTEFACT, f"config{key}.C_n_size [M]", len(c_n))
        print_render(ARTEFACT, f"config{key}.requested_elements [M union of R]", len(probed))

        admitted_by_tier = {"omega": set(omega), "u_task": required, "c_n": c_n}

        # Titles sit above the header band, which is now derived from the
        # headers' own rendered extent rather than from a remembered number.
        ax.text(
            x0,
            fig_h - 0.32,
            f"Configuration {key}   ·   {families}",
            ha="left",
            va="bottom",
            fontsize=FONT_MIN_PT + 1,
            color=INK,
            fontweight="bold",
        )

        for j, el in enumerate(omega):
            marker = "●" if el in probed else "○"
            ax.text(
                x0 + j * cw + cw / 2,
                fig_h - top + 0.12,
                f"{marker} {el[0]} | {el[1]}",
                rotation=45,
                ha="left",
                va="bottom",
                fontsize=FONT_MIN_PT,
                color=INK if el in probed else MIDGREY,
            )
        for k, head in enumerate(("amplified [D]", "narrowed [D]")):
            ax.text(
                x0 + ncol * cw + k * cnt_w + cnt_w / 2,
                fig_h - top + 0.12,
                head,
                rotation=45,
                ha="left",
                va="bottom",
                fontsize=FONT_MIN_PT,
                color=INK,
            )

        for i, arm in enumerate(ARM_ORDER):
            admitted = admitted_by_tier[ARM_GRANT[arm]]
            y = row_y(i)
            amp = narrowed = 0
            for j, el in enumerate(omega):
                st = state_of(el, admitted, required)
                draw_cell(ax, x0 + j * cw, y, cw, rh, st)
                amp += st == S_AMP
                narrowed += st == S_NARROWED
            for k, (val, prefix) in enumerate(((amp, "+"), (narrowed, "−"))):
                cx = x0 + ncol * cw + k * cnt_w
                ax.add_patch(
                    Rectangle(
                        (cx + 0.03, y),
                        cnt_w - 0.06,
                        rh,
                        facecolor=PAPER,
                        edgecolor="#dddddd",
                        lw=0.5,
                    )
                )
                ax.text(
                    cx + cnt_w / 2,
                    y + rh / 2,
                    f"{prefix}{val}" if val else "0",
                    ha="center",
                    va="center",
                    fontsize=FONT_MIN_PT,
                    color=INK if val else MIDGREY,
                    fontweight="bold" if val else "normal",
                )
            print_render(ARTEFACT, f"config{key}.{arm}.admitted_size [D]", len(admitted))
            print_render(ARTEFACT, f"config{key}.{arm}.amplified [D admitted minus U_task]", amp)
            print_render(
                ARTEFACT, f"config{key}.{arm}.narrowed [D U_task minus admitted]", narrowed
            )

        # C4 -- B3 / B3+ carry identical authority BY CONSTRUCTION. Bracketed on
        # the last panel with a leader to the note. This is a design fact, not a
        # corpus gap, so the wording differs from FIG-1's disclosure.
        if p == len(CONFIGS) - 1:
            i3, i3p = ARM_ORDER.index("B3"), ARM_ORDER.index("B3+")
            yb0, yb1 = row_y(max(i3, i3p)), row_y(min(i3, i3p)) + rh
            xb = x0 + panel_w + 0.08
            ax.plot(
                [xb, xb + 0.06, xb + 0.06, xb],
                [yb0 + 0.02, yb0 + 0.02, yb1 - 0.02, yb1 - 0.02],
                color=LADDER_TOP,
                lw=0.9,
            )
            ax.text(
                xb + 0.10,
                (yb0 + yb1) / 2,
                "‡",
                ha="left",
                va="center",
                fontsize=FONT_MIN_PT,
                color=LADDER_TOP,
            )

    # C3 -- the marker counts are PER PANEL; the cross-panel figure is separate.
    open_i = len(omega) - len(probed_by_config["I"])
    open_ii = len(omega) - len(probed_by_config["II"])
    never_either = [e for e in omega if all(e not in probed_by_config[k] for k, _, _ in CONFIGS)]
    print_render(ARTEFACT, "markers.open_config_I [D]", open_i)
    print_render(ARTEFACT, "markers.open_config_II [D]", open_ii)
    print_render(ARTEFACT, "markers.never_requested_under_EITHER [D]", len(never_either))

    # ---- legend, read as a LADDER rather than as a defect list (C1). Two rows,
    # ordered top-of-ladder first, so `narrowed` never sits beside `amplified`.
    keys = (
        (S_AMP, "+  admitted, ABOVE the task grant — the amplification (TV23)"),
        (S_AT, "·  admitted, AT the task grant"),
        (
            S_NARROWED,
            "−  in the grant, narrowed away by the chain — the intended contraction, not a failure",
        ),
        (S_OUT, "    outside the grant and not admitted"),
    )
    # Advance by the width the text ACTUALLY renders at. The conservative
    # per-character constant this replaces was already a patch over one overlap,
    # and the same guess failed twice more on FIG-1 -- no fixed factor is right
    # for both a bullet and a capitalised phrase in a proportional serif.
    sw, pad = 0.22, 0.24
    ly = 0.12
    for row in (keys[2:], keys[:2]):  # drawn bottom-up, so the ladder reads top-down
        lx = 0.10
        for st, text in row:
            draw_cell(ax, lx, ly, sw, 0.18, st)
            t = ax.text(
                lx + sw + 0.07,
                ly + 0.09,
                text,
                ha="left",
                va="center",
                fontsize=FONT_MIN_PT,
                color=INK,
            )
            w_in = t.get_window_extent(renderer=fig.canvas.get_renderer()).width / fig.dpi
            lx += sw + 0.07 + w_in + pad
        print_render(ARTEFACT, "legend.row_width_in [D]", f"{lx:.2f}")
        if lx > fig_w - 0.10:
            raise PresentationError(f"legend row needs {lx:.2f} in, canvas is {fig_w:.2f} in")
        ly += 0.22

    # The caption is no longer drawn on the canvas. It is PRINTED, so the text
    # that must travel with the artefact is generated from the same numbers the
    # figure renders and cannot drift from them by being retyped.
    caption = (
        "Boundary authority surface, the specification analysis for RQ1. Each cell places one "
        "element of the frozen ontology Omega "
        "on a three-step ladder against U_task, the authority the user's task grant confers. An "
        "element an arm admits without the task needing it sits above the grant, and those cells "
        "are the scope amplification the threat vector names; an element the task needs and the "
        "arm admits sits at it; an element the grant holds but the per-hop capability chain has "
        "narrowed away sits below it. The last of these is the contraction the capability arms "
        "exist to perform, not a refusal to be counted against them. A blank cell is outside the "
        "grant and was not admitted. Weight tracks position on that ladder and nothing else: a "
        "solid cell sits above the grant, a tint at it, an outlined cell below it, and a blank "
        "cell off the scale, so the eye reads the surface in the order the quantity runs and "
        "the darkest cells are the finding. The hue is the state board's, so the two matrix "
        "figures read as one system, but they share no dictionary of states: a solid cell here "
        "is authority admitted beyond the task grant, not a request the boundary stopped. The "
        "two right-hand columns count the cells above and below "
        "the grant on each row, and the row groups follow the ladder the arms themselves form: an "
        "unscoped or coarse resource-server grant, a task-scoped grant equal to U_task, and the "
        "attenuated chain end C_n. Read down those groups and the figure gives its result, which "
        "is that scoping the base grant to the task removes the amplification without any "
        "capability machinery, and that the capability arms then narrow further still."
        "\n\n"
        "The surface is derived, not measured. Omega, U_task and C_n are read from the sealed "
        "configuration and corpus, and the grant each arm carries from the ladder definition, so "
        "no exercised dimension appears and no cell reports a campaign outcome. What the corpus "
        "actually requests is carried only by the column markers, filled where a configuration "
        f"requests that element and open where it does not: {open_i} open in Configuration I, "
        f"{open_ii} in Configuration II, and {len(never_either)} requested under neither. C_n and "
        "U_task differ between the configurations, so the surface is drawn once for each rather "
        "than averaged. B3 and B3+ carry identical authority by construction and differ only in "
        "duplicate detection, which this surface does not describe."
    )
    import textwrap

    for para in caption.split("\n\n"):
        for line in textwrap.wrap(para, 96):
            print(f"CAPTION {ARTEFACT} | {line}")
        print(f"CAPTION {ARTEFACT} |")

    # C8 -- acceptance, reported by the artefact itself.
    print_render(ARTEFACT, "acceptance.max_width_in [M _common.LANDSCAPE]", f"{LANDSCAPE[0]:.3f}")
    print_render(ARTEFACT, "acceptance.max_height_in [M _common.LANDSCAPE]", f"{LANDSCAPE[1]:.3f}")
    print_render(
        ARTEFACT,
        "acceptance.portrait_ceiling_in [M _common.PORTRAIT]",
        f"{PORTRAIT[0]:.3f} x {PORTRAIT[1]:.3f}",
    )
    print_render(ARTEFACT, "acceptance.min_effective_font_pt [M]", FONT_MIN_PT)
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
