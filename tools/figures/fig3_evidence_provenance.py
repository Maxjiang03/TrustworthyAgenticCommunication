"""FIG-3 -- the evidence-provenance map for H4a / H4b (FIGURE_PLAN.md §C FIG-3).

A typed two-column diagram. LEFT: the two H4a branches, the H4b premise, and
B3+'s single distinguishing §E.4 cell. RIGHT: the three possible carriers of
evidence -- the sealed CONFIRMATORY campaign, gate G-14 (cited, never charted),
and the empty carrier ∅. Edge STYLE carries the evidence class (solid heavy =
campaign; dashed = gate; dotted hairline = no carrier), never hue alone.

Pure presentation (ADR 0048): every string and count is read from
results/tables/results-confirmatory.json or results/raw/campaign-confirmatory.json
(verdicts, reasons, row states, the F3 carrying-cell count, the F3 coverage
fraction) or quoted verbatim from the sealed pre-registration; nothing is
selected, binned, or computed. No quantity is plotted; no CI exists here.
"""

import re
import textwrap

from _common import (
    BLUE,
    FONT_MIN_PT,
    GHOST,
    INK,
    MIDGREY,
    PAPER,
    REPO_ROOT,
    ROW_SUBCASE_TOKENS,
    PresentationError,
    load_campaign,
    load_tables,
    mpl_setup,
    plt,
    print_render,
    row_key,
    save,
)
from matplotlib.patches import FancyBboxPatch, Rectangle

ARTEFACT = "FIG-3"

# Sealed pre-registration: the G-14 paragraph (docs/PRE_REGISTRATION.md, lines
# 235-250). Two sentences are quoted VERBATIM on the figure; the script re-reads
# the file at build time and refuses to render if either sentence is not found
# there (markdown emphasis/code markers stripped, whitespace collapsed).
PRE_REGISTRATION = REPO_ROOT / "docs" / "PRE_REGISTRATION.md"
G14_REPORT = REPO_ROOT / "smoke" / "g14" / "REPORT.md"

QUOTE_WEIGH = (
    "B3⁺'s justification in the ladder therefore rests on gate evidence rather "
    "than on campaign evidence, and a reader is entitled to weigh gate evidence "
    "differently."
)
QUOTE_CONTROLLED = (
    "That is controlled evidence. It is NOT confirmatory-campaign evidence, and "
    "this document does not claim the two are equivalent."
)

# The three §E.4 F3 rows this map is about, addressed by their key in the sealed
# label-token mapping (ADR 0048 named exception) -- no label is authored here;
# the rendered row label and its state are read from expected_matrix.
ROW_KEY_REUSE = "F3 dpop-stolen-AT-key-substitution"
ROW_KEY_BODY_MUTATION = "F3 dpop-first-use-body-mutation"
ROW_KEY_PROOF_REPLAY = "F3 dpop-captured-proof-replay"

# Geometry (inches; the axes are drawn 1:1 in figure inches).
LEFT_X, LEFT_W = 0.25, 2.85
GAP_W = 1.50
RIGHT_W = 2.65
RIGHT_X = LEFT_X + LEFT_W + GAP_W
FIG_W = RIGHT_X + RIGHT_W + 0.25
PAD = 0.09  # inner padding of every node
LH = 0.142  # line height at 8 pt (inches)
WRAP_LEFT = 45  # characters per line inside a left node (8 pt DejaVu ~ 17 ch/in)
WRAP_RIGHT = 42  # characters per line inside a right node
WRAP_FULL = 104  # characters per line for full-width legend/footer text
NODE_GAP = 0.30  # vertical gap between stacked nodes


def _normalise_md(text):
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def verify_quote(quote, label):
    """Find the verbatim sentence in the sealed pre-registration; print its lines."""
    if not PRE_REGISTRATION.is_file():
        raise PresentationError(f"missing {PRE_REGISTRATION}")
    lines = PRE_REGISTRATION.read_text(encoding="utf-8").splitlines()
    joined = _normalise_md(" ".join(lines))
    if quote not in joined:
        raise PresentationError(
            f"{label}: sentence not found verbatim in {PRE_REGISTRATION.name}; "
            "the figure will not quote what the pre-registration does not say"
        )
    # Locate the 1-indexed line span the sentence occupies (for the audit trail).
    first_words = quote.split(" ")[:3]
    last_words = quote.split(" ")[-3:]
    start = end = None
    for i, raw in enumerate(lines, start=1):
        n = _normalise_md(raw)
        if start is None and " ".join(first_words) in n:
            start = i
        if start is not None and " ".join(last_words) in n:
            end = i
            break
    print_render(
        ARTEFACT,
        f"{label}.source [M]",
        f"{PRE_REGISTRATION.relative_to(REPO_ROOT)} lines {start}-{end}",
    )
    print_render(ARTEFACT, f"{label}.text [M]", quote)


def find_row(tables, key):
    """The expected_matrix row whose sealed mapping key is `key` (exactly one).

    The sealed row_key() refuses the deferred row (it is deliberately absent from
    ROW_SUBCASE_TOKENS), so rows are pre-filtered by the same prefix rule row_key
    applies, and row_key is then asserted on the single hit.
    """
    if key not in ROW_SUBCASE_TOKENS:
        raise PresentationError(f"{key!r} is not a key of the sealed mapping")
    hits = [r for r in tables["expected_matrix"] if r["subcase"].startswith(key)]
    if len(hits) != 1:
        raise PresentationError(f"expected exactly one §E.4 row for {key!r}, found {len(hits)}")
    if row_key(hits[0]["subcase"]) != key:
        raise PresentationError(f"sealed row_key disagrees with the prefix match for {key!r}")
    return hits[0]


def hypothesis(tables, hid):
    hits = [h for h in tables["hypotheses"] if h["hypothesis"] == hid]
    if len(hits) != 1:
        raise PresentationError(f"expected exactly one hypotheses entry for {hid!r}")
    return hits[0]


def wrap(text, width):
    return textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False) or [""]


class Node:
    """A boxed node: bold title, optional verdict chip line, wrapped body lines."""

    def __init__(self, ident, title, body, width, wrapw, chip=None, fill=PAPER, edge=INK):
        self.ident = ident
        self.title = title
        self.chip = chip
        self.width = width
        self.fill = fill
        self.edge = edge
        self.title_lines = wrap(title, wrapw - 7)  # bold runs wider than roman
        self.body_lines = []
        for para in body:
            self.body_lines.extend(wrap(para, wrapw))
        n_lines = len(self.title_lines) + (1 if chip else 0) + len(self.body_lines)
        self.height = n_lines * LH + 2 * PAD + (0.08 if chip else 0)
        self.x = None
        self.top = None  # data-y of the top edge

    @property
    def bottom(self):
        return self.top - self.height

    @property
    def cy(self):
        return self.top - self.height / 2

    def draw(self, ax, renderer):
        ax.add_patch(
            Rectangle(
                (self.x, self.bottom),
                self.width,
                self.height,
                facecolor=self.fill,
                edgecolor=self.edge,
                lw=0.8,
            )
        )
        y = self.top - PAD
        for line in self.title_lines:
            ax.text(
                self.x + PAD,
                y,
                line,
                fontsize=FONT_MIN_PT,
                fontweight="bold",
                color=INK,
                va="top",
                ha="left",
            )
            y -= LH
        if self.chip:
            draw_chip(ax, renderer, self.x + PAD, y - 0.04, self.chip)
            y -= LH + 0.08
        for line in self.body_lines:
            ax.text(self.x + PAD, y, line, fontsize=FONT_MIN_PT, color=INK, va="top", ha="left")
            y -= LH


def draw_chip(ax, renderer, x, top, verdict):
    """The verdict chip: ONE function, so H4a and H4b get identical typography.

    The box is sized from the rendered text extent (no guessed glyph widths).
    """
    cy = top - LH / 2
    t = ax.text(
        x + 0.08,
        cy,
        verdict,
        fontsize=FONT_MIN_PT,
        fontweight="bold",
        color=INK,
        ha="left",
        va="center",
        zorder=3,
    )
    bb = t.get_window_extent(renderer=renderer).transformed(ax.transData.inverted())
    ax.add_patch(
        FancyBboxPatch(
            (bb.x0 - 0.06, bb.y0 - 0.03),
            bb.width + 0.12,
            bb.height + 0.06,
            boxstyle="round,pad=0.0,rounding_size=0.05",
            facecolor=PAPER,
            edgecolor=INK,
            lw=1.0,
            zorder=2,
        )
    )
    ax.text(
        bb.x1 + 0.16, cy, "verdict [M]", fontsize=FONT_MIN_PT, color=INK, ha="left", va="center"
    )


EDGE_STYLES = {
    # class -> (colour, linewidth, linestyle)
    "campaign": (BLUE, 2.6, "solid"),
    "gate": (MIDGREY, 1.3, (0, (4.5, 3.0))),
    "none": (MIDGREY, 0.8, (0, (1.0, 2.6))),
}


def draw_edge(ax, src, dst, cls, label, dst_frac=0.5, src_frac=0.5):
    colour, lw, ls = EDGE_STYLES[cls]
    x0, y0 = src.x + src.width, src.top - src.height * src_frac
    x1, y1 = dst.x, dst.top - dst.height * dst_frac
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="-|>",
            color=colour,
            lw=lw,
            linestyle=ls,
            mutation_scale=11,
            shrinkA=0,
            shrinkB=0,
        ),
    )
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    ax.text(
        xm,
        ym,
        label,
        fontsize=FONT_MIN_PT,
        color=INK,
        ha="center",
        va="center",
        bbox=dict(facecolor=PAPER, edgecolor="none", pad=1.0),
    )


def main():
    campaign = load_campaign()
    tables = load_tables()

    # ---- read the record ---------------------------------------------------
    h4a = hypothesis(tables, "H4a")
    h4b = hypothesis(tables, "H4b")
    v4a = h4a["verdict"]
    v4b = h4b["verdict"]
    print_render(ARTEFACT, "verdict.H4a [M]", v4a)
    print_render(ARTEFACT, "verdict.H4b [M]", v4b)
    for i, r in enumerate(h4a["reasons"]):
        print_render(ARTEFACT, f"H4a.reasons[{i}] [M]", r)
    for i, r in enumerate(h4b["reasons"]):
        print_render(ARTEFACT, f"H4b.reasons[{i}] [M]", r)
    reuse_ev = h4a["evidence"]["reuse"]
    body_ev = h4a["evidence"]["body_mutation"]
    for arm in sorted(reuse_ev):
        print_render(ARTEFACT, f"H4a.evidence.reuse.{arm} [M]", reuse_ev[arm])
    for arm in sorted(body_ev):
        print_render(ARTEFACT, f"H4a.evidence.body_mutation.{arm} [M]", body_ev[arm])
    h4b_inst = h4b["evidence"]["instantiated"]
    print_render(ARTEFACT, "H4b.evidence.instantiated [M]", h4b_inst)

    row_reuse = find_row(tables, ROW_KEY_REUSE)
    row_body = find_row(tables, ROW_KEY_BODY_MUTATION)
    row_replay = find_row(tables, ROW_KEY_PROOF_REPLAY)
    for tag, row in (
        ("reuse", row_reuse),
        ("body_mutation", row_body),
        ("proof_replay", row_replay),
    ):
        print_render(ARTEFACT, f"row.{tag}.subcase [M]", row["subcase"])
        print_render(ARTEFACT, f"row.{tag}.state [M]", row["state"])
    token_reuse = ROW_SUBCASE_TOKENS[ROW_KEY_REUSE]
    print_render(ARTEFACT, "row.reuse.corpus_token [M sealed mapping]", token_reuse)
    for tag, key in (
        ("body_mutation", ROW_KEY_BODY_MUTATION),
        ("proof_replay", ROW_KEY_PROOF_REPLAY),
    ):
        print_render(
            ARTEFACT, f"row.{tag}.corpus_token [M sealed mapping]", ROW_SUBCASE_TOKENS[key]
        )

    carrying = [c for c in campaign["cells"] if c.get("subcase") == token_reuse]
    n_carry = len(carrying)
    carry_arms = sorted(c["arm"] for c in carrying)
    print_render(ARTEFACT, "campaign.run_mode [M]", campaign["run_mode"])
    print_render(ARTEFACT, "campaign.corpus_root [M]", campaign["corpus_root"])
    print_render(ARTEFACT, f"campaign.cells[subcase == {token_reuse}] [M]", n_carry)
    print_render(ARTEFACT, "campaign.carrying_cell_arms [M]", ", ".join(carry_arms))
    if len(set(carry_arms)) != n_carry:
        raise PresentationError(
            "carrying cells are not one per arm; the map's caption would mis-state"
        )
    f3cov = tables["class_macro"]["F3"]["coverage"]
    print_render(ARTEFACT, "F3.coverage.instantiated [M]", f3cov["instantiated"])
    print_render(ARTEFACT, "F3.coverage.defined [M]", f3cov["defined"])
    print_render(
        ARTEFACT, "F3.coverage_warning [M]", tables["class_macro"]["F3"]["coverage_warning"]
    )
    f3_frac = f"{f3cov['instantiated']}/{f3cov['defined']} subcases"

    if not G14_REPORT.is_file():
        raise PresentationError(f"gate G-14 record missing: {G14_REPORT}")
    g14_rel = G14_REPORT.relative_to(REPO_ROOT).as_posix()
    print_render(ARTEFACT, "G14.report_path [M exists]", G14_REPORT)
    verify_quote(QUOTE_WEIGH, "prereg.quote_weigh")
    verify_quote(QUOTE_CONTROLLED, "prereg.quote_controlled")

    # ---- nodes -------------------------------------------------------------
    left = [
        Node(
            "L1",
            "H4a branch (i): reuse as different caller",
            [
                f"row [M]: {row_reuse['subcase']} — state: {row_reuse['state']}",
                "the measured half of H4a (its cells sit on FIG-1; outcomes are not "
                "re-plotted here)",
            ],
            LEFT_W,
            WRAP_LEFT,
            chip=v4a,
        ),
        Node(
            "L2",
            "H4a branch (ii): tool/args substitution after signing",
            [
                f"row [M]: {row_body['subcase']} — state: {row_body['state']}",
                "reason [M]: " + h4a["reasons"][0],
            ],
            LEFT_W,
            WRAP_LEFT,
            chip=v4a,
        ),
        Node(
            "L3",
            "B3+ distinguishing cell: F3 dpop-captured-proof-replay",
            [
                f"row [M]: {row_replay['subcase']} — state: {row_replay['state']}",
                "the only §E.4 row where B3⁺'s expectation differs from B3's "
                "(PRE_REGISTRATION.md, G-14 paragraph); it is B3⁺'s reason to exist",
            ],
            LEFT_W,
            WRAP_LEFT,
        ),
        Node(
            "L4",
            "H4b: compromised-holder premise",
            [
                f"evidence.instantiated [M]: {h4b_inst}",
                "reason [M]: " + h4b["reasons"][0],
                "reason [M]: " + h4b["reasons"][1],
            ],
            LEFT_W,
            WRAP_LEFT,
            chip=v4b,
        ),
    ]
    right = {
        "campaign": Node(
            "R1",
            "Campaign (sealed, CONFIRMATORY corpus)",
            [
                f"run_mode [M]: {campaign['run_mode']}; corpus_root [M]: {campaign['corpus_root']}",
                f"carrying cells [M]: {token_reuse} — {n_carry} cells, one per arm "
                f"({carry_arms[0]} … {carry_arms[-1]})",
                f"F3 coverage [M]: {f3_frac} — this fraction travels with every F3 number",
                "evidence class: confirmatory-campaign evidence (solid heavy edge)",
            ],
            RIGHT_W,
            WRAP_RIGHT,
        ),
        "gate": Node(
            "R2",
            "Gate G-14 C1/C2/C3 (locked platform)",
            [
                f"record [M]: {g14_rel} — cited here, never charted",
                "C1 — bit-identical in-Δ replay (with C1.W1 negative control); "
                "C2 — first use whose tool/arguments differ from what was signed "
                "(with C2.W1); C3 — bare bearer arm given the same cache",
                f"“{QUOTE_CONTROLLED}” (PRE_REGISTRATION.md, G-14 paragraph)",
            ],
            RIGHT_W,
            WRAP_RIGHT,
        ),
        "none": Node(
            "R3",
            "∅ — no carrier",
            [
                "no campaign cell and no gate criterion stages this premise; "
                "the map shows the absence rather than substituting one"
            ],
            RIGHT_W,
            WRAP_RIGHT,
            fill=GHOST,
            edge=MIDGREY,
        ),
    }
    for n in left + list(right.values()):
        n.x = LEFT_X if n.ident.startswith("L") else RIGHT_X
        print_render(ARTEFACT, f"node.{n.ident}", n.title)

    # The dashed-edge label: the pre-registration's own sentence, verbatim.
    quote_lines = [
        "dashed edges (gate evidence) carry",
        "the pre-registration's own caveat, verbatim:",
    ]
    quote_lines += wrap(f"“{QUOTE_WEIGH}”", WRAP_RIGHT)
    quote_lines += ["(docs/PRE_REGISTRATION.md, G-14 paragraph)"]
    n_quote_head = 2
    quote_h = len(quote_lines) * LH + 0.10

    # ---- layout (top-down, in inches from the top of the figure) -------------
    title_h = 0.70
    d = title_h
    for n in left:
        n.top_d = d
        d += n.height + NODE_GAP
    # Right column: campaign aligned to L1's top; gate a little below L2's top so
    # both dashed edges (from L2 and L3) enter it; the quote hangs beneath the
    # gate; ∅ aligned to L4's top.
    right["campaign"].top_d = left[0].top_d
    right["gate"].top_d = max(
        left[1].top_d + 0.20, right["campaign"].top_d + right["campaign"].height + NODE_GAP
    )
    quote_top_d = right["gate"].top_d + right["gate"].height + 0.10
    need_l4_top = quote_top_d + quote_h + NODE_GAP
    if left[3].top_d < need_l4_top:
        left[3].top_d = need_l4_top
    right["none"].top_d = left[3].top_d
    content_bottom_d = max(
        left[3].top_d + left[3].height, right["none"].top_d + right["none"].height
    )
    legend_top_d = content_bottom_d + 0.35
    samples = [
        (
            "campaign",
            "campaign evidence — sealed CONFIRMATORY corpus, scored cells "
            "(results/raw/campaign-confirmatory.json)",
        ),
        (
            "gate",
            "gate evidence — G-14 on the locked platform; controlled evidence, "
            "NOT confirmatory-campaign evidence (smoke/g14/REPORT.md, cited)",
        ),
        (
            "none",
            "no carrier — the edge terminates in ∅; nothing is substituted for the "
            "unstaged premise",
        ),
    ]
    legend_wrapped = [(cls, wrap(words, WRAP_FULL - 8)) for cls, words in samples]
    legend_h = sum(len(lines) * LH + 0.10 for _, lines in legend_wrapped)
    footer_lines = [
        "Typed provenance only: no quantity is plotted, no rate, no CI (none is defined for any "
        "security number). Edge STYLE carries the evidence class; colour is never the sole "
        "channel.",
        f"Every F3 number carries F3's coverage: {f3_frac} instantiated. Sources: "
        "results/tables/results-confirmatory.json (hypotheses, expected_matrix, class_macro.F3), "
        "results/raw/campaign-confirmatory.json (cells), docs/PRE_REGISTRATION.md (G-14 "
        f"paragraph, quoted verbatim), {g14_rel} (cited).",
    ]
    footer_wrapped = []
    for f in footer_lines:
        footer_wrapped.extend(wrap(f, WRAP_FULL))
    footer_top_d = legend_top_d + legend_h + 0.15
    fig_h = footer_top_d + len(footer_wrapped) * LH + 0.25

    def y_of(dd):
        return fig_h - dd

    for n in left + list(right.values()):
        n.top = y_of(n.top_d)

    # ---- draw ----------------------------------------------------------------
    mpl_setup()
    fig = plt.figure(figsize=(FIG_W, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, FIG_W)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    ax.text(
        LEFT_X,
        fig_h - 0.18,
        "FIG-3 — Evidence provenance for H4a and H4b: what carries each claim",
        fontsize=FONT_MIN_PT + 1,
        fontweight="bold",
        color=INK,
        va="top",
    )
    subtitle = (
        "left: the claims  ·  right: the carriers  ·  edge style = evidence class "
        "(solid heavy = campaign; dashed = gate; dotted = none)  ·  G-14 is cited, "
        "never charted"
    )
    for i, line in enumerate(wrap(subtitle, WRAP_FULL)):
        ax.text(LEFT_X, fig_h - 0.36 - i * LH, line, fontsize=FONT_MIN_PT, color=INK, va="top")

    renderer = fig.canvas.get_renderer()
    for n in left + list(right.values()):
        n.draw(ax, renderer)

    edges = [
        (left[0], right["campaign"], "campaign", "campaign evidence\n(solid heavy)", 0.5, 0.5),
        (left[1], right["gate"], "gate", "gate evidence:\nG-14 C2 (dashed)", 0.30, 0.5),
        (left[2], right["gate"], "gate", "gate evidence:\nG-14 C1 (dashed)", 0.70, 0.5),
        (left[3], right["none"], "none", "premise never staged;\nno gate substitutes", 0.5, 0.5),
    ]
    for src, dst, cls, label, dfrac, sfrac in edges:
        draw_edge(ax, src, dst, cls, label, dst_frac=dfrac, src_frac=sfrac)
        print_render(
            ARTEFACT,
            f"edge.{src.ident}->{dst.ident}",
            f"class={cls}; style={EDGE_STYLES[cls][2]}; label={label!r}",
        )

    # Dashed-edge label block beneath the gate node.
    qy = y_of(quote_top_d)
    ax.plot(
        [RIGHT_X, RIGHT_X + 0.45],
        [qy - 0.07, qy - 0.07],
        color=MIDGREY,
        lw=1.3,
        linestyle=EDGE_STYLES["gate"][2],
    )
    for i, line in enumerate(quote_lines):
        style = "italic" if n_quote_head <= i < len(quote_lines) - 1 else "normal"
        xoff = 0.52 if i == 0 else 0.0
        ax.text(
            RIGHT_X + xoff,
            qy - i * LH,
            line,
            fontsize=FONT_MIN_PT,
            color=INK,
            va="top",
            ha="left",
            style=style,
        )

    # Legend: the three edge classes, drawn as line samples + words.
    yy = y_of(legend_top_d)
    for cls, lines in legend_wrapped:
        colour, lw, ls = EDGE_STYLES[cls]
        ax.plot(
            [LEFT_X, LEFT_X + 0.55], [yy - LH / 2, yy - LH / 2], color=colour, lw=lw, linestyle=ls
        )
        for j, line in enumerate(lines):
            ax.text(LEFT_X + 0.68, yy - j * LH, line, fontsize=FONT_MIN_PT, color=INK, va="top")
        print_render(ARTEFACT, f"legend.{cls}", " ".join(lines))
        yy -= len(lines) * LH + 0.10

    fy = y_of(footer_top_d)
    for i, line in enumerate(footer_wrapped):
        ax.text(LEFT_X, fy - i * LH, line, fontsize=FONT_MIN_PT, color=INK, va="top")

    print_render(ARTEFACT, "figure_size_in [D]", f"{FIG_W:.2f} x {fig_h:.2f}")
    save(fig, "fig3_evidence_provenance", ARTEFACT)


if __name__ == "__main__":
    main()
