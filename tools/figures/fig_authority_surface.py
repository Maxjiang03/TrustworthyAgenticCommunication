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
    BLUE,
    FONT_MIN_PT,
    GHOST,
    INK,
    LANDSCAPE,
    MIDGREY,
    ORANGE,
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
    the capability arms are built to do, so it is now a light fill with a thin
    outline, subordinate to the amplification rather than parallel to it.
    """
    if state == S_AMP:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=INK, edgecolor=INK, lw=0.6))
        glyph_colour = PAPER
    elif state == S_AT:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=GHOST, edgecolor=MIDGREY, lw=0.5))
        glyph_colour = INK
    elif state == S_NARROWED:
        ax.add_patch(Rectangle((x, y), w, h, facecolor="#fbf7f2", edgecolor=ORANGE, lw=0.7))
        glyph_colour = ORANGE
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


def main():
    mpl_setup()
    omega = load_omega()
    print_render(ARTEFACT, "omega.elements [M omega_gamma_v1.json]", len(omega))

    # ---- geometry, authored to fit the landscape text block. Explicit vertical
    # bands, so nothing sits at a hand-tuned constant a longer string outgrows.
    cw, rh = 0.38, 0.27
    title_band = 0.40
    header_band = 1.45
    legend_band = 0.54  # two rows
    note_band = 0.60
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

    # C6 -- the RQ and the evidence class on the FIGURE, not only in a caption.
    ax.text(
        0.10,
        fig_h - 0.10,
        "RQ1 — specification analysis.   Evidence class: DERIVED from frozen artefacts.   "
        "Not a campaign measurement: no exercised dimension is present.",
        ha="left",
        va="top",
        fontsize=FONT_MIN_PT,
        color=BLUE,
    )

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

        # Titles sit ABOVE the reach of the 45 deg headers, which extend about
        # 1.29 in up from their anchor -- they were overprinted twice before.
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
                color=BLUE,
                lw=0.9,
            )
            ax.text(
                xb + 0.10,
                (yb0 + yb1) / 2,
                "‡",
                ha="left",
                va="center",
                fontsize=FONT_MIN_PT,
                color=BLUE,
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
    # Conservative per-character width: the true average is nearer 0.055,
    # but em-dashes, capitals and parentheses exceed it and two legend
    # items overlapped the next swatch at that figure.
    sw, char_w, pad = 0.22, 0.062, 0.24
    ly = note_band + 0.12
    for row in (keys[2:], keys[:2]):  # drawn bottom-up, so the ladder reads top-down
        lx = 0.10
        for st, text in row:
            draw_cell(ax, lx, ly, sw, 0.18, st)
            ax.text(
                lx + sw + 0.07,
                ly + 0.09,
                text,
                ha="left",
                va="center",
                fontsize=FONT_MIN_PT,
                color=INK,
            )
            lx += sw + 0.07 + len(text) * char_w + pad
        print_render(ARTEFACT, "legend.row_width_in [D]", f"{lx:.2f}")
        if lx > fig_w - 0.10:
            raise PresentationError(f"legend row needs {lx:.2f} in, canvas is {fig_w:.2f} in")
        ly += 0.22

    note = (
        "Authority surface, DERIVED from frozen artefacts (Ω, U_task, Cₙ, and the SS E.1 grant "
        "each arm carries). `required` is U_task, NOT the concrete request R. ● an element the "
        f"corpus requests IN THAT PANEL, ○ one it does not — {open_i} open in Config I and "
        f"{open_ii} in Config II, of which {len(never_either)} are never requested under EITHER "
        "configuration. Cₙ and U_task "
        "differ across the two configurations, so neither is averaged. ‡ B3 and B3⁺ carry "
        "identical authority by construction; they differ only in duplicate detection, which is "
        "not a property of the authority surface."
    )
    import textwrap

    lines = textwrap.wrap(note, 168)
    line_h = FONT_MIN_PT * 1.26 / 72.0
    print_render(ARTEFACT, "note.lines [D]", len(lines))
    if len(lines) * line_h > note_band:
        raise PresentationError(
            f"the note needs {len(lines) * line_h:.2f} in but the band is {note_band:.2f} in"
        )
    ax.text(
        0.10,
        note_band - 0.04,
        "\n".join(lines),
        ha="left",
        va="top",
        fontsize=FONT_MIN_PT,
        color=MIDGREY,
    )

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
