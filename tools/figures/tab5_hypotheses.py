"""TAB-5 -- H4a/H4b adjudication table (results chapter, MAIN).

One row per entry of results-confirmatory.json `hypotheses`, in file order.
Columns: hypothesis | pre-registered prediction | measured component |
unmeasured component | evidence class for the unmeasured component | verdict.
Verdict strings are rendered EXACTLY as the JSON `verdict` field, in identical
typography for every row; reasons are quoted verbatim from `reasons`.

Pure presentation (ADR 0048): nothing is computed, selected, or binned. The
only arithmetic is one printed cell count. The pre-registration quotations are
hard-coded constants that the script re-verifies verbatim against the sealed
docs/PRE_REGISTRATION.md at build time (a check that can only abort, never
alter the output).
"""

import json
import re
import textwrap

from _common import (
    FONT_MIN_PT,
    GHOST,
    INK,
    PAPER,
    REPO_ROOT,
    ROW_SUBCASE_TOKENS,
    PresentationError,
    load_campaign,
    load_tables,
    mpl_setup,
    plt,
    print_render,
    save,
)
from matplotlib.patches import Rectangle

ARTEFACT = "TAB-5"

PRE_REG = REPO_ROOT / "docs" / "PRE_REGISTRATION.md"

# ---------------------------------------------------------------------------
# Verbatim quotations from the sealed pre-registration (docs/PRE_REGISTRATION.md
# lines 143-155 and 235-250), kept in their markdown form so they can be
# re-verified byte-for-byte (modulo line-wrapping whitespace) at build time.
# ---------------------------------------------------------------------------
PRE_REG_QUOTES = {
    "H4a": {
        "name": "H4a (post-signature, non-holder tampering)",
        "prediction": (
            "Prediction: B2-exchange-task (bearer) admits both; B2-exchange-task-DPoP "
            "admits (ii) at the same endpoint but blocks (i); **B3 blocks both** (HTC "
            "terminal-holder proof blocks (i); the canonical body/args digest in INV "
            "blocks (ii))."
        ),
    },
    "H4b": {
        "name": "H4b (compromised-holder misuse)",
        "prediction": (
            "Prediction: **no** mechanism blocks a compromised holder acting *within* "
            "`C_n`; **all** `C_n`-enforcing mechanisms block it from exceeding `C_n`, "
            "because scope containment is independent of holder identity."
        ),
    },
}
GATE_EVIDENCE_QUOTES = (
    "That is controlled evidence. It is NOT confirmatory-campaign evidence, and this "
    "document does not claim the two are equivalent.",
    "`B3⁺`'s justification in the ladder therefore rests on gate evidence rather than "
    "on campaign evidence, and a reader is entitled to weigh gate evidence differently.",
)

# ---------------------------------------------------------------------------
# Fixed content by rule (FIGURE_PLAN.md §B/§C TAB-5): which half of each
# hypothesis the campaign measured, which half it did not, and what -- if
# anything -- stands behind the unmeasured half. Sealed row keys of
# analysis/matrix.py ROW_SUBCASE_TOKENS name the E.4 rows; nothing is invented.
# ---------------------------------------------------------------------------
H4A_MEASURED_ROW_KEY = "F3 dpop-stolen-AT-key-substitution"
H4A_UNMEASURED_ROW_KEY = "F3 dpop-first-use-body-mutation"
H4B_MEASURED_ROW_KEYS = ("F1-root", "F1-terminal")

FIXED = {
    "H4a": {
        "evidence_class": (
            "gate G-14 criterion C2 (smoke/g14/REPORT.md) — gate evidence, NOT campaign evidence"
        ),
    },
    "H4b": {
        "measured": (
            "in-scope vs out-of-scope containment (F1-root, F1-terminal) — but not "
            "compromised-holder instances"
        ),
        "unmeasured": "compromised-holder premise: never staged by the corpus",
        "evidence_class": "NONE — no gate substitutes",
    },
}

# Column widths in inches -- 9.18 in of table, so that with the side margins
# and the 0.2 in tight-bbox pad the PDF page stays under A4 landscape's ~9.7 in
# of text width without scaling (C2, FIGURE_PLAN.md §0.7b). Each column is at
# least as wide as its longest unbreakable token at 8 pt (bold header token
# `(docs/PRE_REGISTRATION.md,` 1.87 in; `evidence.instantiated=false` 1.57 in;
# bold `unmeasured component` 1.51 in; bold `NOT DETERMINED` 1.12 in), checked
# by measuring every wrapped line; the row heights grow with the wrapping.
COLUMNS = (
    ("hypothesis", 1.00),
    (
        "pre-registered prediction\n(docs/PRE_REGISTRATION.md, the “Prediction:” clause, verbatim)",
        2.02,
    ),
    ("measured component", 1.52),
    ("unmeasured component\n(ghost band = never run)", 1.74),
    ("evidence class for the\nunmeasured component", 1.68),
    ("verdict\n(JSON, verbatim)", 1.22),
)
COLUMN_KEYS = ("hypothesis", "prediction", "measured", "unmeasured", "evidence_class", "verdict")
CHARS_PER_INCH = 15.0  # conservative for DejaVu Sans at 8 pt
TITLE_CHARS_PER_INCH = 12.5  # conservative for the 9 pt bold title line
LINE_H = FONT_MIN_PT * 1.35 / 72.0  # inches per text line
TITLE_LINE_H = (FONT_MIN_PT + 1) * 1.35 / 72.0  # inches per title line
PAD = 0.05  # inches inside each cell
TITLE = (
    "TAB-5 — H4a/H4b adjudication (verdicts read verbatim from "
    "results-confirmatory.json `hypotheses`; the unmeasured half of each "
    "hypothesis is shown, not elided)"
)


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def _demarkdown(s):
    return s.replace("**", "").replace("*", "").replace("`", "")


def verify_verbatim(text, source=PRE_REG):
    """Abort if a hard-coded quotation is not found verbatim in the sealed doc."""
    haystack = _norm(source.read_text(encoding="utf-8"))
    if _norm(text) not in haystack:
        raise PresentationError(f"quotation not found verbatim in {source.name}: {text[:60]!r}...")


def wrap(text, width_in):
    """Wrap at spaces/hyphens only: a token longer than the budget takes a line
    of its own rather than being cut mid-word (the columns are sized so that
    every such token still fits)."""
    width = max(8, int((width_in - 2 * PAD) * CHARS_PER_INCH))
    out = []
    for para in text.split("\n"):
        out.extend(textwrap.wrap(para, width=width, break_long_words=False) or [""])
    return out


def json_literal(v):
    """Render a JSON scalar as the JSON literal it was read from (null/false/...)."""
    return json.dumps(v)


def build_rows(campaign, tables):
    hyps = tables["hypotheses"]
    print_render(ARTEFACT, "hypotheses_count [M]", len(hyps))
    ids = [h["hypothesis"] for h in hyps]
    if sorted(ids) != ["H4a", "H4b"]:
        raise PresentationError(
            f"hypotheses block carries {ids!r}; the fixed-content rule covers H4a, H4b"
        )

    f3cov = tables["class_macro"]["F3"]["coverage"]
    f3_fraction = f"{f3cov['instantiated']}/{f3cov['defined']}"
    print_render(ARTEFACT, "F3_coverage_fraction [M]", f3_fraction)

    # H4a measured half: the E.4 row named by the sealed key -> its corpus token
    # -> the campaign cells carrying that subcase. A lookup, not a selection.
    reuse_token = ROW_SUBCASE_TOKENS[H4A_MEASURED_ROW_KEY]
    reuse_cells = sum(1 for c in campaign["cells"] if c.get("subcase") == reuse_token)
    print_render(ARTEFACT, f"H4a.measured.cells[subcase={reuse_token}] [D count]", reuse_cells)
    if reuse_cells != 9:
        raise PresentationError(
            f"{reuse_token} carries {reuse_cells} scored cells; the FIGURE_PLAN "
            "fixed content states 9 -- the plan and the record disagree"
        )
    # H4a unmeasured half: the sealed mapping refuses this row (token None) and
    # the expected_matrix carries its state verbatim.
    if ROW_SUBCASE_TOKENS[H4A_UNMEASURED_ROW_KEY] is not None:
        raise PresentationError(f"{H4A_UNMEASURED_ROW_KEY} unexpectedly maps to a token")
    np_rows = [
        r for r in tables["expected_matrix"] if r["subcase"].startswith(H4A_UNMEASURED_ROW_KEY)
    ]
    if len(np_rows) != 1:
        raise PresentationError(f"expected one matrix row for {H4A_UNMEASURED_ROW_KEY}")
    np_state = np_rows[0]["state"]
    print_render(ARTEFACT, f"expected_matrix[{np_rows[0]['subcase']}].state [M]", np_state)
    for k in H4B_MEASURED_ROW_KEYS:
        if ROW_SUBCASE_TOKENS[k] is None:
            raise PresentationError(f"{k} maps to no corpus token")

    rows = []
    for h in hyps:
        hid = h["hypothesis"]
        verdict = h["verdict"]
        reasons = list(h["reasons"])
        ev = h["evidence"]
        print_render(ARTEFACT, f"hypotheses.{hid}.verdict [M]", verdict)
        for i, r in enumerate(reasons):
            print_render(ARTEFACT, f"hypotheses.{hid}.reasons[{i}] [M]", r)
        print_render(
            ARTEFACT,
            f"hypotheses.{hid}.evidence [M]",
            json.dumps(ev, ensure_ascii=False, sort_keys=True),
        )

        q = PRE_REG_QUOTES[hid]
        verify_verbatim(q["name"])
        verify_verbatim(q["prediction"])
        prediction = _demarkdown(q["prediction"])
        name_paren = q["name"][len(hid) :].strip()

        if hid == "H4a":
            reuse = ev["reuse"]
            body = ev["body_mutation"]
            if any(v is not None for v in body.values()):
                raise PresentationError(
                    "H4a evidence.body_mutation is not all-null; the 'unmeasured' "
                    "label would mis-state the record"
                )
            measured = (
                f"branch (i) reuse-as-different-caller — {H4A_MEASURED_ROW_KEY}, "
                f"{reuse_cells} cells (F3: {f3_fraction} subcases)\n"
                "JSON evidence.reuse: "
                + "; ".join(f"{arm}={json_literal(v)}" for arm, v in reuse.items())
            )
            unmeasured = (
                f"branch (ii) tool/args substitution after signing — "
                f"{H4A_UNMEASURED_ROW_KEY}: {np_state}\n"
                "JSON evidence.body_mutation: "
                + "; ".join(f"{arm}={json_literal(v)}" for arm, v in body.items())
            )
            evidence_class = FIXED[hid]["evidence_class"]
        else:
            if ev.get("instantiated") is not False:
                raise PresentationError(
                    "H4b evidence.instantiated is not false; the 'unmeasured' label "
                    "would mis-state the record"
                )
            measured = FIXED[hid]["measured"]
            unmeasured = (
                FIXED[hid]["unmeasured"]
                + f"\nJSON evidence.instantiated={json_literal(ev['instantiated'])}"
            )
            evidence_class = FIXED[hid]["evidence_class"]

        cells = [hid + "\n" + name_paren, prediction, measured, unmeasured, evidence_class, verdict]
        for key, text in zip(COLUMN_KEYS, cells):
            print_render(ARTEFACT, f"{hid}.{key}", text.replace("\n", " | "))
        rows.append(dict(id=hid, cells=cells, reasons=reasons))
    return rows, f3_fraction


def main():
    campaign = load_campaign()
    tables = load_tables()
    rows, f3_fraction = build_rows(campaign, tables)
    for q in GATE_EVIDENCE_QUOTES:
        verify_verbatim(q)
    f3_warning = tables["class_macro"]["F3"]["coverage_warning"]
    print_render(ARTEFACT, "class_macro.F3.coverage_warning [M]", f3_warning)

    footer = []
    footer.append(
        (
            "Reasons, verbatim from results-confirmatory.json hypotheses[].reasons "
            "(= results-confirmatory.md, Hypotheses block):",
            True,
        )
    )
    for r in rows:
        for reason in r["reasons"]:
            footer.append((f"{r['id']}: {reason}", False))
    footer.append(("", False))
    footer.append((f"F3 (F3: {f3_fraction} subcases) — {f3_warning}", False))
    footer.append(
        (
            "On the H4a evidence class, the pre-registration's own words "
            "(docs/PRE_REGISTRATION.md, G-14 paragraph): "
            + " ".join(_demarkdown(q) for q in GATE_EVIDENCE_QUOTES),
            False,
        )
    )
    footer.append(
        (
            "Ghost band = never run (shared legend, FIG-1/TAB-1: NOT POPULATED "
            "BY THE CAMPAIGN / never staged). Both verdicts are the JSON strings "
            "in identical typography; NOT DETERMINED is a verdict, not a "
            "direction. Exact counts; no CI is defined for any number on this "
            "table.",
            False,
        )
    )

    # ---- geometry -------------------------------------------------------
    mpl_setup()
    margin_l, margin_r, margin_b = 0.10, 0.10, 0.15
    table_w = sum(w for _, w in COLUMNS)
    fig_w = margin_l + table_w + margin_r  # 9.38 in -> a 9.58 in PDF page
    title_lines = textwrap.wrap(
        TITLE, width=int(table_w * TITLE_CHARS_PER_INCH), break_long_words=False
    )
    margin_t = 0.12 + len(title_lines) * TITLE_LINE_H + 0.12

    header_lines = [wrap(name, w) for name, w in COLUMNS]
    header_h = max(len(ln) for ln in header_lines) * LINE_H + 2 * PAD
    row_lines = []
    row_hs = []
    for r in rows:
        lines = [wrap(text, w) for text, (_, w) in zip(r["cells"], COLUMNS)]
        row_lines.append(lines)
        row_hs.append(max(len(ln) for ln in lines) * LINE_H + 2 * PAD)
    footer_lines = []
    for text, is_head in footer:
        footer_lines.append((wrap(text, table_w) if text else [""], is_head))
    footer_h = sum(len(ln) * LINE_H for ln, _ in footer_lines) + 0.25

    fig_h = margin_t + header_h + sum(row_hs) + footer_h + margin_b
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    ax.text(
        margin_l,
        fig_h - 0.12,
        "\n".join(title_lines),
        fontsize=FONT_MIN_PT + 1,
        fontweight="bold",
        color=INK,
        va="top",
        ha="left",
        linespacing=1.35,
    )

    xs = [margin_l]
    for _, w in COLUMNS:
        xs.append(xs[-1] + w)

    # header
    y_top = fig_h - margin_t
    y = y_top - header_h
    for j, (name, w) in enumerate(COLUMNS):
        ax.add_patch(Rectangle((xs[j], y), w, header_h, facecolor=PAPER, edgecolor=INK, lw=0.8))
        ax.text(
            xs[j] + PAD,
            y + header_h - PAD,
            "\n".join(header_lines[j]),
            fontsize=FONT_MIN_PT,
            fontweight="bold",
            color=INK,
            va="top",
            ha="left",
            linespacing=1.35,
        )
    y_top = y

    # body rows
    verdict_col = len(COLUMNS) - 1
    unmeasured_col = 3
    for r, lines, rh in zip(rows, row_lines, row_hs):
        y = y_top - rh
        for j, (name, w) in enumerate(COLUMNS):
            face = GHOST if j == unmeasured_col else PAPER
            ax.add_patch(Rectangle((xs[j], y), w, rh, facecolor=face, edgecolor=INK, lw=0.6))
            if j == verdict_col:
                # identical typography for every verdict, by construction
                ax.text(
                    xs[j] + w / 2,
                    y + rh / 2,
                    "\n".join(lines[j]),
                    fontsize=FONT_MIN_PT,
                    fontweight="bold",
                    color=INK,
                    ha="center",
                    va="center",
                    linespacing=1.35,
                )
            else:
                ax.text(
                    xs[j] + PAD,
                    y + rh - PAD,
                    "\n".join(lines[j]),
                    fontsize=FONT_MIN_PT,
                    color=INK,
                    ha="left",
                    va="top",
                    linespacing=1.35,
                    style="italic" if j == unmeasured_col else "normal",
                )
        y_top = y

    # footer
    y = y_top - 0.15
    for lines, is_head in footer_lines:
        ax.text(
            margin_l,
            y,
            "\n".join(lines),
            fontsize=FONT_MIN_PT,
            fontweight="bold" if is_head else "normal",
            color=INK,
            ha="left",
            va="top",
            linespacing=1.35,
        )
        y -= len(lines) * LINE_H

    save(fig, "tab5_hypotheses", ARTEFACT)


if __name__ == "__main__":
    main()
