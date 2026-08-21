"""FIG-AD -- which check stopped each adaptive attack.

Rewritten on the Commander's instruction 2026-08-21: no internal document names
on the canvas (a reader outside this project cannot decode them), no prose
passages, and every mark self-explanatory.

Three design decisions carry that instruction:

1. **The cells name the check, not its index.** The earlier version printed the
   conjunct's position in the admission rule -- 3, 4, 5, 6, 9 -- which means
   nothing without the rule in front of you. Each cell now prints the check in
   a word.
2. **An "aimed at" column replaces the masked-cell footnote.** Where an attack
   was stopped by a check other than the one it was built for, the reader sees
   it by comparing two columns, so the caveat needs no note at all.
3. **The bracket over the two strongest configurations states what the run could
   not separate.** They are identical in all eight attacks; the figure says so
   rather than leaving anyone to compare eighteen cells by eye.

Reads `results/adaptive/run2/adaptive-attacks.json`. Pure presentation
(ADR 0048): nothing is computed here, every mark is a field of that artefact.
"""

import json

from _common import (
    ARM_ORDER,
    BLOCKED,
    FONT_MIN_PT,
    HATCH,
    INK,
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

# What actually refused, in a word a reader can act on. Both planes -- the
# capability boundary's own checks and an OAuth arm's token checks -- collapse
# to one vocabulary on purpose: which subsystem owns a check is internal detail,
# while WHAT was checked is the thing this figure is about.
STOPPED_BY = {
    "b3_htc_chain": "chain",
    "b3_holder_proof": "signer",
    "b3_invocation_binding": "bind",
    "b3_containment": "scope",
    "b3_oauth_resource_authorization": "token",
    "b2_token_scope": "scope",
    "b2_oauth_token_rejected": "token",
    "b2_nothing_presented": "no cred",
    "b1_invalid_credential": "key",
}
# What each attack was built to defeat, in the same vocabulary.
AIMED_AT = {
    "A1": "chain",
    "A2": "signer",
    "A3": "bind",
    "A4": "bind",
    "A5": "scope",
    "A6": "token",
    "A7": "identity",
    "A8": "scope",
}
# The attack in plain words -- what the adversary actually did.
WHAT_IT_DID = {
    "A1": "adds a forged certificate hop",
    "A2": "signs with the wrong key",
    "A3": "swaps the tool after signing",
    "A4": "swaps the arguments after signing",
    "A5": "asks beyond the grant",
    "A6": "presents its own token",
    "A7": "presents its own token",
    "A8": "stolen key, asks beyond the grant",
}


def main():
    mpl_setup()
    report = json.loads(SOURCE.read_text(encoding="utf-8"))
    attacks = report["attacks"]
    totals = report["totals"]
    print_render(ARTEFACT, "source.artefact", "results/adaptive/run2/adaptive-attacks.json")
    for key in ("arm_runs", "attack_applicable_runs", "not_applicable_runs"):
        print_render(ARTEFACT, f"totals.{key} [M]", totals[key])
    print_render(ARTEFACT, "totals.admitted_of_applicable [M]", totals["admitted_of_applicable"])

    if len(attacks) != 8 or any(len(a["cells"]) != len(ARM_ORDER) for a in attacks):
        raise PresentationError("expected 8 attacks over 9 arms")

    # Does anything here separate the top two configurations? COMPUTED, not
    # assumed -- the answer goes on the canvas whichever way it falls.
    def outcome(attack, arm):
        for c in attack["cells"]:
            if c["arm"] == arm:
                return (c["admitted"], c["reason_code_FOR_DIAGNOSIS_ONLY"])
        raise PresentationError(f"no cell for {arm}")

    identical = sum(1 for a in attacks if outcome(a, "B3") == outcome(a, "B3+"))
    print_render(ARTEFACT, "b3_vs_b3plus.identical [M]", f"{identical} of {len(attacks)}")

    # ---- geometry, measured from the strings themselves ----------------------
    scratch = plt.figure(figsize=(1, 1))

    def measure(text, weight="normal"):
        t = scratch.text(0.5, 0.5, text, fontsize=FONT_MIN_PT, fontweight=weight)
        w = t.get_window_extent(renderer=scratch.canvas.get_renderer()).width / scratch.dpi
        t.remove()
        return w

    hdr = max(measure(a) for a in ARM_ORDER) + 0.22
    desc_w = max(measure(v) for v in WHAT_IT_DID.values())
    aim_w = max(measure(v, "bold") for v in AIMED_AT.values())
    used = {
        STOPPED_BY[c["reason_code_FOR_DIAGNOSIS_ONLY"]]
        for a in attacks
        for c in a["cells"]
        if c["attack_applied"] and not c["admitted"]
    } | {"through"}
    cw = max(measure(v, "bold") for v in used) + 0.08
    plt.close(scratch)

    left = 0.10
    gutter = left + desc_w + 0.30 + aim_w + 0.30
    rh = 0.25
    fig_w = gutter + len(ARM_ORDER) * cw + 1.04
    title_h, foot_h, key_h = 0.58, 0.52, 0.84
    fig_h = title_h + hdr + len(attacks) * rh + foot_h + key_h

    fig = plt.figure(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(PAPER)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    print_render(ARTEFACT, "geometry.fig_in [D]", f"{fig_w:.2f} x {fig_h:.2f}")

    y_top = fig_h - title_h - hdr

    def cx(j):
        return gutter + j * cw

    # ---- title, and one line of counts (not prose) --------------------------
    ax.text(
        left,
        fig_h - 0.21,
        "Which check stopped each attack",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT + 3,
        color=INK,
        fontweight="bold",
    )
    ax.text(
        left,
        fig_h - 0.44,
        f"8 attacks  ·  9 configurations  ·  {totals['attack_applicable_runs']} applicable  ·  "
        f"{totals['admitted_of_applicable']} got through",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )

    # ---- headers -------------------------------------------------------------
    ax.text(
        gutter - 0.30,
        y_top + 0.12,
        "aimed at",
        ha="right",
        va="bottom",
        fontsize=FONT_MIN_PT,
        color=INK,
        fontstyle="italic",
    )
    for j, arm in enumerate(ARM_ORDER):
        ax.text(
            cx(j) + cw / 2,
            y_top + 0.07,
            arm,
            ha="left",
            va="center",
            rotation=90,
            rotation_mode="anchor",
            fontsize=FONT_MIN_PT,
            color=INK,
        )

    # ---- rows ----------------------------------------------------------------
    per_arm = dict.fromkeys(ARM_ORDER, 0)
    for i, attack in enumerate(attacks):
        y = y_top - (i + 1) * rh
        aid = attack["id"].split("-")[0]
        by_arm = {c["arm"]: c for c in attack["cells"]}

        ax.text(
            left,
            y + rh / 2,
            WHAT_IT_DID[aid],
            ha="left",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )
        ax.text(
            gutter - 0.30,
            y + rh / 2,
            AIMED_AT[aid],
            ha="right",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
            fontweight="bold",
        )

        for j, arm in enumerate(ARM_ORDER):
            cell = by_arm[arm]
            x = cx(j)
            if not cell["attack_applied"]:
                ax.add_patch(
                    Rectangle(
                        (x, y), cw, rh, facecolor=PAPER, edgecolor=HATCH, lw=0.5, hatch="////"
                    )
                )
                word, colour, weight = "–", INK, "normal"
            elif cell["admitted"]:
                ax.add_patch(Rectangle((x, y), cw, rh, facecolor=PAPER, edgecolor=INK, lw=0.5))
                word, colour, weight = "through", INK, "bold"
                per_arm[arm] += 1
            else:
                code = cell["reason_code_FOR_DIAGNOSIS_ONLY"]
                if code not in STOPPED_BY:
                    raise PresentationError(f"unmapped code {code!r} on {aid}/{arm}")
                ax.add_patch(Rectangle((x, y), cw, rh, facecolor=BLOCKED, edgecolor=INK, lw=0.5))
                word, colour, weight = STOPPED_BY[code], PAPER, "bold"
            ax.text(
                x + cw / 2,
                y + rh / 2,
                word,
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=colour,
                fontweight=weight,
            )

        c = attack["counts"]
        ax.text(
            cx(len(ARM_ORDER)) + 0.14,
            y + rh / 2,
            f"{c['admitted_of_applicable']} of {c['attack_applicable']} through",
            ha="left",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
        )

    # ---- footer --------------------------------------------------------------
    y_foot = y_top - len(attacks) * rh
    ax.plot([gutter, cx(len(ARM_ORDER))], [y_foot - 0.03] * 2, color=INK, lw=0.6)
    ax.text(
        gutter - 0.12,
        y_foot - 0.18,
        "attacks through",
        ha="right",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    for j, arm in enumerate(ARM_ORDER):
        ax.text(
            cx(j) + cw / 2,
            y_foot - 0.18,
            str(per_arm[arm]),
            ha="center",
            va="center",
            fontsize=FONT_MIN_PT,
            color=INK,
            fontweight="bold" if per_arm[arm] == 0 else "normal",
        )
        print_render(ARTEFACT, f"arm.{arm}.through [D]", per_arm[arm])

    # ---- what this run could NOT separate, under the two columns it concerns
    xb0, xb1 = cx(len(ARM_ORDER) - 2), cx(len(ARM_ORDER))
    ybr = y_foot - 0.34
    ax.plot([xb0, xb0, xb1, xb1], [ybr, ybr - 0.06, ybr - 0.06, ybr], color=INK, lw=0.9)
    ax.text(
        (xb0 + xb1) / 2,
        ybr - 0.17,
        f"identical in all {identical}",
        ha="center",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )

    # ---- key: swatches and short labels, no sentences ------------------------
    renderer = fig.canvas.get_renderer()
    ky, kx = 0.58, left
    for kind, label in (
        ("stop", "stopped, by the named check"),
        ("through", "attack got through"),
        ("na", "attack cannot apply here"),
    ):
        if kind == "stop":
            ax.add_patch(
                Rectangle((kx, ky - 0.09), cw, 0.18, facecolor=BLOCKED, edgecolor=INK, lw=0.5)
            )
            ax.text(
                kx + cw / 2,
                ky,
                "scope",
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=PAPER,
                fontweight="bold",
            )
        elif kind == "through":
            ax.add_patch(
                Rectangle((kx, ky - 0.09), cw, 0.18, facecolor=PAPER, edgecolor=INK, lw=0.5)
            )
            ax.text(
                kx + cw / 2,
                ky,
                "through",
                ha="center",
                va="center",
                fontsize=FONT_MIN_PT,
                color=INK,
                fontweight="bold",
            )
        else:
            ax.add_patch(
                Rectangle(
                    (kx, ky - 0.09),
                    cw,
                    0.18,
                    facecolor=PAPER,
                    edgecolor=HATCH,
                    lw=0.5,
                    hatch="////",
                )
            )
            ax.text(kx + cw / 2, ky, "–", ha="center", va="center", fontsize=FONT_MIN_PT, color=INK)
        kx += cw + 0.08
        t = ax.text(kx, ky, label, ha="left", va="center", fontsize=FONT_MIN_PT, color=INK)
        kx += t.get_window_extent(renderer=renderer).width / fig.dpi + 0.32

    ax.text(
        left,
        ky - 0.24,
        "chain = certificate chain   ·   signer = who signed the request   ·   "
        "bind = request matches its signature",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )
    ax.text(
        left,
        ky - 0.42,
        "scope = within the grant   ·   token = access token allows it   ·   "
        "identity = caller matches the key holder",
        ha="left",
        va="center",
        fontsize=FONT_MIN_PT,
        color=INK,
    )

    # Neither standing guard sees a line running off the RIGHT edge: one compares
    # text to text, the other the canvas to the page. Measure it and raise.
    for artist in fig.findobj(match=lambda o: isinstance(o, type(ax.title))):
        if not artist.get_text().strip():
            continue
        if artist.get_window_extent(renderer).x1 / fig.dpi > fig_w - 0.03:
            raise PresentationError(f"text overruns the canvas: {artist.get_text()[:60]!r}")

    enforce_placement(fig, ARTEFACT)
    assert_no_text_overlap(fig, ARTEFACT)
    save(fig, STEM, ARTEFACT)


if __name__ == "__main__":
    main()
