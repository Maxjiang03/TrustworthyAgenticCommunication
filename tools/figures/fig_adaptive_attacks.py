"""FIG-AD -- the adaptive attack outcomes: eight attacks, nine arms, one grid.

A SEPARATE EVIDENCE CLASS. These cells are DEVIATIONS D-019 Phase B and are
never summed with the 143-cell confirmatory campaign. The figure says so on its
own face, because a grid of arms against outcomes is exactly the shape a reader
might otherwise mistake for the state board.

What the grid shows is the ONE thing this run can support: **which conjunct
refused**. The sealed oracle cannot score an adaptive cell -- it judges each
against the sealed record of the base scenario while the attack substitutes the
request -- so `reference_allow`, `admission_breach`, `false_block` and every
effect-derived field are void and appear nowhere here.

Three encodings a reader must not confuse, and each has its own mark:

* **n/a** -- the arm stages no HTC chain, no INV or no access token, so it cannot
  express this corruption and ran the UNMODIFIED base scenario. Hatched, with a
  dash. It is NOT an admission: printing these as admissions is precisely the
  defect run 1's reporting had, and the figure must not reintroduce it.
* **admitted** -- open cell, letter `A`. The attack was applied and got through.
* **refused** -- filled, with the conjunct that refused. DEEP blue and a NUMBER
  where an SS A.5 conjunct refused (only B-cap, B3 and B3+ evaluate any); LIGHTER
  blue and a letter where the arm's own mechanism refused, because that is a
  different check under a different name and the module vector says so.

Reads from `results/adaptive/run2/adaptive-attacks.json` -- run 2, the one
carrying D-012's evidence_class stamping. Run 1 is byte-identical in every cell
(72/72) and either would draw the same grid. Pure presentation (ADR 0048):
nothing is computed here, every mark is a field of that artefact.
"""

import json

from _common import (
    ARM_ORDER,
    BLOCKED,
    FONT_MIN_PT,
    HATCH,
    INK,
    OFF_BLOCKED,
    PAPER,
    REPO_ROOT,
    PresentationError,
    assert_no_text_overlap,
    enforce_placement,
    mpl_setup,
    plt,
    print_render,
    save,
)
from matplotlib.patches import Rectangle

ARTEFACT = "FIG-AD"
STEM = "fig_adaptive_attacks"
SOURCE = REPO_ROOT / "results" / "adaptive" / "run2" / "adaptive-attacks.json"

# Reason code -> (glyph, which plane refused). An SS A.5 conjunct is numbered by
# its position in the admission rule; an arm's own check gets a letter, so the
# two planes never share a symbol.
CONJUNCT_GLYPH = {
    "b3_htc_chain": ("3", "conjunct"),
    "b3_holder_proof": ("4", "conjunct"),
    "b3_invocation_binding": ("5", "conjunct"),
    "b3_containment": ("6", "conjunct"),
    "b3_oauth_resource_authorization": ("9", "conjunct"),
    "b2_token_scope": ("s", "own"),
    "b2_oauth_token_rejected": ("o", "own"),
    "b2_nothing_presented": ("n", "own"),
    "b1_invalid_credential": ("k", "own"),
}
# Cells the Phase A table published as FALSIFIABLE-and-unmasked but Phase B
# measured as MASKED: an earlier conjunct fires, so the attack never reaches the
# conjunct it was built for. Marked on the row label, not hidden in a caption.
MASKED = {"A5", "A6", "A7"}
# A8's K-holder construction re-mints the INV under the terminal holder identity
# key. Only B3 and B3+ stage such an assertion at all, so only they faced the
# COMPROMISED-HOLDER adversary; for the other seven the attack degenerated to a
# plain scope substitution, which is a different adversary. Marked, because
# "every arm enforcing C_n refused a compromised holder" overstated the coverage.
PARTIAL_K_HOLDER = {"A8"}
# The admission rule's own name for the containment conjunct.
PRETTY = {"R subset-of C_n": "R ⊆ Cₙ"}


def main():
    mpl_setup()
    report = json.loads(SOURCE.read_text(encoding="utf-8"))
    attacks = report["attacks"]
    totals = report["totals"]
    print_render(ARTEFACT, "source.artefact", "results/adaptive/run2/adaptive-attacks.json")
    print_render(ARTEFACT, "evidence_class", "extension -- never summed with the 143-cell campaign")
    for key in (
        "arm_runs",
        "attack_applicable_runs",
        "not_applicable_runs",
        "admitted_of_applicable",
    ):
        print_render(ARTEFACT, f"totals.{key} [M]", totals[key])

    if len(attacks) != 8 or any(len(a["cells"]) != len(ARM_ORDER) for a in attacks):
        raise PresentationError("expected 8 attacks over 9 arms")

    # ---- geometry, in inches. The header band is MEASURED from the longest
    # arm name rendered at the 8 pt floor, not guessed: a remembered constant is
    # how FIG-0's panel titles came to overprint their own band.
    scratch = plt.figure(figsize=(1, 1))
    hdr = (
        max(
            scratch.text(0.5, 0.5, arm, fontsize=FONT_MIN_PT)
            .get_window_extent(renderer=scratch.canvas.get_renderer())
            .width
            for arm in ARM_ORDER
        )
        / scratch.dpi
    ) + 0.30
    plt.close(scratch)
    gutter, fig_w = 3.05, 9.30
    cw, rh = 0.46, 0.25  # row height trimmed so the canvas fits the landscape text block
    top, key_h = 0.06, 0.92
    foot_h = 0.28  # the per-arm admitted row, which needs its OWN allocation:
    # carving it out of the key band is what made the two collide
    banner_h = 0.62  # the banner gets its own band ABOVE the vertical arm labels
    grid_h = len(attacks) * rh
    fig_h = top + banner_h + hdr + grid_h + foot_h + key_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(PAPER)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    print_render(ARTEFACT, "geometry.fig_in [D]", f"{fig_w:.2f} x {fig_h:.2f}")
    print_render(ARTEFACT, "geometry.header_band_in [M]", f"{hdr:.2f}")

    y_top = fig_h - top - banner_h - hdr

    def cx(j):
        return gutter + j * cw

    # ---- arm headers, VERTICAL. At 55 degrees the long names overlapped one
    # another (the overlap guard caught it); upright, a column need only be
    # wider than the 8 pt line height, which 0.46 in comfortably is.
    for j, arm in enumerate(ARM_ORDER):
        ax.text(
            cx(j) + cw / 2,
            y_top + 0.07,
            arm,
            ha="left",
            va="center",
            rotation=90,
            # anchor mode, so the label extends strictly UPWARD from the grid
            # edge instead of straddling it -- without it the descender half sat
            # inside the first row and the overlap guard caught it.
            rotation_mode="anchor",
            fontsize=FONT_MIN_PT,
            color=INK,
        )

    # ---- the grid ------------------------------------------------------------
    per_arm_admit = dict.fromkeys(ARM_ORDER, 0)
    for i, attack in enumerate(attacks):
        y = y_top - (i + 1) * rh
        aid = attack["id"].split("-")[0]
        by_arm = {c["arm"]: c for c in attack["cells"]}

        for j, arm in enumerate(ARM_ORDER):
            cell = by_arm[arm]
            x = cx(j)
            if not cell["attack_applied"]:
                # NOT an admission. The arm could not express the corruption and
                # ran the unmodified base scenario; SS E.4's rule is that such a
                # cell is not a result at all.
                ax.add_patch(
                    Rectangle(
                        (x, y),
                        cw,
                        rh,
                        facecolor=PAPER,
                        edgecolor=HATCH,
                        lw=0.5,
                        hatch="////",
                    )
                )
                glyph, colour = "–", INK
            elif cell["admitted"]:
                ax.add_patch(Rectangle((x, y), cw, rh, facecolor=PAPER, edgecolor=INK, lw=0.5))
                glyph, colour = "A", INK
                per_arm_admit[arm] += 1
            else:
                code = cell["reason_code_FOR_DIAGNOSIS_ONLY"]
                if code not in CONJUNCT_GLYPH:
                    raise PresentationError(f"unmapped refusal code {code!r} on {aid}/{arm}")
                glyph, plane = CONJUNCT_GLYPH[code]
                fill = BLOCKED if plane == "conjunct" else OFF_BLOCKED
                ax.add_patch(Rectangle((x, y), cw, rh, facecolor=fill, edgecolor=INK, lw=0.5))
                colour = PAPER
            ax.text(
                x + cw / 2,
                y + rh / 2,
                glyph,
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=colour,
                fontweight="bold" if glyph != "–" else "normal",
            )

        # row label: what this attack targeted, and whether it was masked
        targeted = PRETTY.get(attack["conjunct_targeted"], attack["conjunct_targeted"])
        label = f"{aid}  {targeted}"
        if aid in MASKED:
            label += "  †"
        if aid in PARTIAL_K_HOLDER:
            label += "  ‡"
        ax.text(
            gutter - 1.30,
            y + rh / 2,
            label,
            ha="right",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
        ax.text(
            gutter - 1.24,
            y + rh / 2,
            f"{attack['capability']} · {attack['tampering_point'].split()[0]}",
            ha="left",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
        c = attack["counts"]
        ax.text(
            cx(len(ARM_ORDER)) + 0.10,
            y + rh / 2,
            f"{c['admitted_of_applicable']} of {c['attack_applicable']} admitted",
            ha="left",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
        print_render(
            ARTEFACT,
            f"attack.{aid} [M]",
            f"{attack['conjunct_targeted']} | applicable {c['attack_applicable']} | "
            f"admitted {c['admitted_of_applicable']}",
        )

    # ---- per-arm admissions, under the grid ---------------------------------
    y_foot = y_top - len(attacks) * rh
    ax.plot([gutter, cx(len(ARM_ORDER))], [y_foot - 0.02] * 2, color=INK, lw=0.6)
    ax.text(
        gutter - 0.10,
        y_foot - 0.17,
        "admitted, of applicable",
        ha="right",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    for j, arm in enumerate(ARM_ORDER):
        ax.text(
            cx(j) + cw / 2,
            y_foot - 0.17,
            str(per_arm_admit[arm]),
            ha="center",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
            fontweight="bold" if per_arm_admit[arm] == 0 else "normal",
        )
        print_render(ARTEFACT, f"arm.{arm}.admitted [D]", per_arm_admit[arm])

    # ---- key ----------------------------------------------------------------
    ky = 0.80  # four key lines, laid down from the top of the 0.92 in key band
    kx = 0.10

    def swatch(x, kind):
        if kind == "na":
            ax.add_patch(
                Rectangle(
                    (x, ky - 0.09),
                    0.30,
                    0.18,
                    facecolor=PAPER,
                    edgecolor=HATCH,
                    lw=0.5,
                    hatch="////",
                )
            )
            ax.text(x + 0.15, ky, "–", ha="center", va="center", fontsize=FONT_MIN_PT, color=INK)
        elif kind == "admit":
            ax.add_patch(
                Rectangle((x, ky - 0.09), 0.30, 0.18, facecolor=PAPER, edgecolor=INK, lw=0.5)
            )
            ax.text(
                x + 0.15,
                ky,
                "A",
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=INK,
                fontweight="bold",
            )
        else:
            fill = BLOCKED if kind == "conjunct" else OFF_BLOCKED
            ax.add_patch(
                Rectangle((x, ky - 0.09), 0.30, 0.18, facecolor=fill, edgecolor=INK, lw=0.5)
            )
            ax.text(
                x + 0.15,
                ky,
                "5" if kind == "conjunct" else "s",
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=PAPER,
                fontweight="bold",
            )
        return x + 0.30

    for kind, text in (
        ("na", "attack not applicable to this arm — ran the unmodified base, NOT an admission"),
        ("admit", "attack admitted"),
    ):
        kx = swatch(kx, kind) + 0.08
        t = ax.text(kx, ky, text, ha="left", va="center", fontsize=FONT_MIN_PT, color=INK)
        kx += t.get_window_extent(renderer=fig.canvas.get_renderer()).width / fig.dpi + 0.26

    ky -= 0.22
    kx = 0.10
    for kind, text in (
        ("conjunct", "refused by the numbered A.5 conjunct (B-cap, B3, B3⁺ only)"),
        ("own", "refused by the arm's own check: s scope, o OAuth token"),
    ):
        kx = swatch(kx, kind) + 0.08
        t = ax.text(kx, ky, text, ha="left", va="center", fontsize=FONT_MIN_PT, color=INK)
        kx += t.get_window_extent(renderer=fig.canvas.get_renderer()).width / fig.dpi + 0.26

    ax.text(
        0.10,
        ky - 0.23,
        "† measured as MASKED: an earlier conjunct refused first, so the attack never reached "
        "the conjunct it was built for",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    ax.text(
        0.10,
        ky - 0.44,
        "‡ A8's compromised-holder construction reached B3 and B3⁺ only; the other seven "
        "stage no invocation assertion, so for them it was a plain scope substitution",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )

    # Neither guard above catches a line running off the RIGHT edge: the overlap
    # guard compares text to text, and the placement guard compares the canvas to
    # the text block. Measure every line against the canvas and raise, because the
    # last footnote silently overflowed once and only a rendered look caught it.
    renderer = fig.canvas.get_renderer()
    for artist in fig.findobj(match=lambda o: isinstance(o, type(ax.title))):
        if not artist.get_text().strip():
            continue  # empty axis title/label artists sit at the canvas edge
        box = artist.get_window_extent(renderer)
        if box.x1 / fig.dpi > fig_w - 0.04:
            raise PresentationError(
                f"text overruns the canvas by "
                f"{box.x1 / fig.dpi - fig_w:.3f} in: {artist.get_text()[:60]!r}"
            )

    # ---- the banner this figure must carry ----------------------------------
    ax.text(
        0.10,
        fig_h - top - 0.13,
        "Adaptive attacks (DEVIATIONS D-019 Phase B) — a SEPARATE EVIDENCE CLASS, "
        "never summed with the 143-cell campaign",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT + 1,
        color=INK,
        fontweight="bold",
    )
    ax.text(
        0.10,
        fig_h - top - 0.34,
        f"{totals['arm_runs']} arm runs · {totals['attack_applicable_runs']} with an attack "
        f"applied · {totals['not_applicable_runs']} not applicable · "
        f"{totals['admitted_of_applicable']} admitted. B3 and B3⁺ admitted none.",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    ax.text(
        0.10,
        fig_h - top - 0.53,
        "The sealed oracle cannot score an adaptive cell, so no verdict column is drawn: "
        "what is shown is which conjunct refused.",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )

    enforce_placement(fig, ARTEFACT)
    assert_no_text_overlap(fig, ARTEFACT)
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
