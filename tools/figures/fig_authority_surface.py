"""Paper Figure 1 -- the boundary authority surface (RQ1/RQ2).

Nine ladder arms x the seven elements of the frozen ontology `Omega`, each cell
in one of four states against the user's task grant `U_task`:

    admitted and required        the arm may do what the task needs
    ADMITTED, NOT REQUIRED       the amplification -- TV23 itself
    required, NOT admitted       withheld though the task needs it
    neither                      correctly withheld

WHAT THIS FIGURE IS, STATED PRECISELY. It is the authority SURFACE, derived
from frozen artefacts -- not a campaign measurement. Every input is sealed and
read-only:

  Omega, the seven (action, resource) elements   src/harness/authorizer/omega_gamma_v1.json
  U_task and the capability chain C_sets         fixtures/confirmatory/sealed/*.json
  which grant each arm carries                   the SS E.1 ladder, see ARM_GRANT below

The campaign measured something narrower and is not plotted here: each scenario
requests exactly ONE element, only five of the seven are ever requested, and
four scenarios share `mail.send|mail/outbox` across attacks AND benign controls
under two monitor configurations. A measured 9x7 matrix therefore does not
exist, and one built by merging those cells would average an attack with its own
control. Elements the corpus actually probes are marked; their outcomes belong
to the state board, not here.

`C_n` and `U_task` differ between the F1/F2/F3+benign scenarios and the F4/F5
scenarios, so the surface is drawn once per configuration rather than averaged.

Every number rendered is printed to stdout (ADR 0048).
"""

import json

from _common import (
    ARM_ORDER,
    FONT_MIN_PT,
    GHOST,
    INK,
    MIDGREY,
    ORANGE,
    PAPER,
    REPO_ROOT,
    PresentationError,
    mpl_setup,
    plt,
    print_render,
    save,
)
from matplotlib.patches import Rectangle

ARTEFACT = "FIG-A"
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
# Kept short on purpose: these run vertically beside their own tier and must fit
# inside that tier's height AT 8 pt -- the floor is not negotiable, so the label
# gives way instead. The expansion belongs in the caption. Guarded below.
GRANT_LABEL = {
    "omega": "Ω grant",
    "u_task": "C₀ task",
    "c_n": "Cₙ chain",
}

# The two chain configurations the corpus defines. Named by the scenario whose
# sealed file supplies the sets; both are read, never assumed equal.
CONFIGS = (
    ("I", "F1 · F2 · F3 · benign", "cf-f1-root"),
    ("II", "F4 · F5", "cf-f4-sensitive-egress"),
)

# Four states, each with fill + texture, never colour alone (FIGURE_PLAN.md §D).
S_BOTH, S_AMP, S_WITHHELD, S_NEITHER = "both", "amplified", "withheld", "neither"


def load_omega():
    path = REPO_ROOT / "src" / "harness" / "authorizer" / "omega_gamma_v1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    elements = [tuple(e) for e in doc["omega"]["elements"]]
    if len(elements) != 7:
        raise PresentationError(f"Omega must have 7 elements, found {len(elements)}")
    return elements


def load_config(scenario_id):
    path = REPO_ROOT / "fixtures" / "confirmatory" / "sealed" / f"{scenario_id}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    u_task = {tuple(x) for x in doc["U_task"]}
    c_sets = [{tuple(x) for x in c} for c in doc["C_sets"]]
    if c_sets[0] != u_task:
        raise PresentationError(
            f"{scenario_id}: C_0 is not U_task; the ladder claim would be wrong"
        )
    return u_task, c_sets[-1]


def probed_elements(scenario_ids):
    """Which Omega elements the corpus actually requests in this configuration."""
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
    if in_a and in_r:
        return S_BOTH
    if in_a:
        return S_AMP
    if in_r:
        return S_WITHHELD
    return S_NEITHER


def draw_cell(ax, x, y, w, h, state):
    if state == S_AMP:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=INK, edgecolor=INK, lw=0.6))
    elif state == S_BOTH:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=GHOST, edgecolor=MIDGREY, lw=0.5))
    elif state == S_WITHHELD:
        ax.add_patch(
            Rectangle((x, y), w, h, facecolor=PAPER, edgecolor=ORANGE, lw=0.9, hatch="/////")
        )
    else:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=PAPER, edgecolor="#dddddd", lw=0.5))


def main():
    mpl_setup()
    omega = load_omega()
    print_render(ARTEFACT, "omega.elements [M omega_gamma_v1.json]", len(omega))

    # ---- geometry, authored to fit the 9.693 x 5.564 in landscape text block.
    # Explicit vertical bands, so nothing is positioned by a hand-tuned constant
    # that a longer string can silently outgrow.
    cw, rh = 0.42, 0.28
    title_band = 0.34  # panel titles, ABOVE the rotated headers
    header_band = 1.50  # rotated column labels at 45 deg
    legend_band = 0.34
    note_band = 0.52
    top = title_band + header_band
    bottom = legend_band + note_band + 0.10
    left = 1.62
    # 45 deg headers extend as far right as they do up, so the right margin has
    # to hold the last column's label, not just the last column.
    gap, cnt_w, right = 0.40, 0.46, 0.48
    ncol = len(omega)
    panel_w = ncol * cw + cnt_w
    fig_w = left + panel_w + gap + panel_w + right
    fig_h = top + len(ARM_ORDER) * rh + bottom
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    def row_y(i):
        return fig_h - top - (i + 1) * rh

    # ---- arm labels, once, on the left
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

    # ---- grant-tier brackets down the far left
    tier_start = {}
    for i, arm in enumerate(ARM_ORDER):
        tier_start.setdefault(ARM_GRANT[arm], []).append(i)
    for tier, rows in tier_start.items():
        y0, y1 = row_y(rows[-1]), row_y(rows[0]) + rh
        label = GRANT_LABEL[tier]
        # These run vertically inside their own tier. At 8 pt a label longer than
        # the tier is tall would overprint its neighbour -- which is how the
        # first version came to shrink the type instead. Refuse, do not shrink.
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

    totals = {}
    for p, (key, families, source_scenario) in enumerate(CONFIGS):
        x0 = left + p * (panel_w + gap)
        required, c_n = load_config(source_scenario)
        probed = probed_elements(scenarios_of(key))
        print_render(ARTEFACT, f"config{key}.source [M sealed scenario]", source_scenario)
        print_render(ARTEFACT, f"config{key}.required |U_task|", len(required))
        print_render(ARTEFACT, f"config{key}.capability |C_n|", len(c_n))
        print_render(ARTEFACT, f"config{key}.probed_elements", len(probed))

        admitted_by_tier = {"omega": set(omega), "u_task": required, "c_n": c_n}

        # Panel title, in its own band at the very top -- it used to sit inside
        # the header band and was overprinted by the rotated labels.
        ax.text(
            x0,
            fig_h - title_band + 0.08,
            f"Configuration {key}   ·   {families}",
            ha="left",
            va="bottom",
            fontsize=FONT_MIN_PT + 1,
            color=INK,
            fontweight="bold",
        )

        # column headers, 45 deg: shallower than 60 deg, so the same strings
        # need 1.29 in of height instead of 1.58 in
        for j, el in enumerate(omega):
            label = f"{el[0]} | {el[1]}"
            marker = "●" if el in probed else "○"
            ax.text(
                x0 + j * cw + cw / 2,
                fig_h - top + 0.12,
                f"{marker} {label}",
                rotation=45,
                ha="left",
                va="bottom",
                fontsize=FONT_MIN_PT,
                color=INK if el in probed else MIDGREY,
            )
        ax.text(
            x0 + ncol * cw + cnt_w / 2,
            fig_h - top + 0.12,
            "amplified",
            rotation=45,
            ha="left",
            va="bottom",
            fontsize=FONT_MIN_PT,
            color=INK,
        )

        for i, arm in enumerate(ARM_ORDER):
            admitted = admitted_by_tier[ARM_GRANT[arm]]
            y = row_y(i)
            amp = 0
            for j, el in enumerate(omega):
                st = state_of(el, admitted, required)
                draw_cell(ax, x0 + j * cw, y, cw, rh, st)
                if st == S_AMP:
                    amp += 1
            withheld = len(required - admitted)
            totals.setdefault(arm, {})[key] = (amp, withheld)
            ax.add_patch(
                Rectangle(
                    (x0 + ncol * cw + 0.04, y),
                    cnt_w - 0.08,
                    rh,
                    facecolor=PAPER,
                    edgecolor="#dddddd",
                    lw=0.5,
                )
            )
            ax.text(
                x0 + ncol * cw + cnt_w / 2,
                y + rh / 2,
                f"+{amp}" if amp else "0",
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=INK if amp else MIDGREY,
                fontweight="bold" if amp else "normal",
            )
            print_render(ARTEFACT, f"config{key}.{arm}.admitted", len(admitted))
            print_render(ARTEFACT, f"config{key}.{arm}.amplified [D |A\\R|]", amp)
            print_render(ARTEFACT, f"config{key}.{arm}.withheld [D |R\\A|]", withheld)

    # ---- legend: one row, four keys, laid out on measured slot widths rather
    # than a guessed stride (the first version overprinted two of the four).
    keys = (
        (S_BOTH, "admitted ∧ required"),
        (S_AMP, "admitted, NOT required — the amplification"),
        (S_WITHHELD, "required, NOT admitted"),
        (S_NEITHER, "neither"),
    )
    sw, char_w, pad = 0.24, 0.052, 0.30
    slots = [sw + 0.08 + len(t) * char_w + pad for _, t in keys]
    lx = 0.10
    ly = note_band + 0.14
    print_render(ARTEFACT, "legend.width_in [D]", f"{sum(slots):.2f}")
    if sum(slots) > fig_w - 0.20:
        raise PresentationError(f"legend needs {sum(slots):.2f} in, canvas has {fig_w - 0.20:.2f}")
    for (st, text), slot in zip(keys, slots):
        draw_cell(ax, lx, ly, sw, 0.19, st)
        ax.text(
            lx + sw + 0.08,
            ly + 0.095,
            text,
            ha="left",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
        lx += slot

    # Deliberately short: the argument is made in the running text, and a note
    # long enough to carry it is also long enough to fall off the canvas.
    note = (
        "Authority surface, derived from frozen artefacts (Ω, U_task, Cₙ, and the SS E.1 grant "
        "each arm carries) — not a campaign measurement. ● an element the corpus requests, "
        "○ one it never does (2 of 7). Cₙ and U_task differ across the two configurations, so "
        "neither is averaged."
    )
    import textwrap

    lines = textwrap.wrap(note, 158)
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

    for arm in ARM_ORDER:
        a1, w1 = totals[arm]["I"]
        a2, w2 = totals[arm]["II"]
        if (a1, w1) != (a2, w2):
            print_render(ARTEFACT, f"asymmetry.{arm}", f"I=(+{a1},-{w1}) II=(+{a2},-{w2})")

    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
