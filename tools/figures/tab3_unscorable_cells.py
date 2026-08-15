"""TAB-3 -- the ten unscorable cells, each with its cause.

Pure presentation (ADR 0048): one row per entry of campaign-confirmatory.json
`unscorable` (a list of [scenario_id, arm, cause] triples), in the record's own
order, joined to the sealed section E.4 expectation of results-confirmatory.json
`agreement.unmeasured` by (subcase token, arm). The join is mechanical: the
scenario_id -> subcase token comes from the campaign's own scored cells (every
scored cell carries both fields), and the E.4 row label -> token comes from the
sealed mapping re-exported by _common (ROW_SUBCASE_TOKENS / row_key). If the
join cannot be made for any row, the artefact says so and lists both sources
side by side instead of guessing. Nothing is selected, sorted, binned, or
computed beyond the counts printed here.
"""

import textwrap
from collections import Counter, defaultdict

from _common import (
    FONT_MIN_PT,
    INK,
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

ARTEFACT = "TAB-3"

# The three apparatus failure modes that the sealed campaign records as an
# unscorable cell WITH its cause instead of scoring it (the unscorable.append
# sites of src/harness/campaign.py; named as the three in DEVIATIONS.md, v0.8
# entry). Their names are quoted from that record; none is invented here.
FAIL_CLOSED_CAUSES = (
    "a wall-clock straddle (clock_refusal, ADR 0046)",
    'an exhausted authorizer ("the authorizer did not finish")',
    'a runner error ("the run did not complete")',
)


def scenario_tokens(campaign):
    """scenario_id -> the set of subcase tokens its scored cells carry [M]."""
    seen = defaultdict(set)
    for cell in campaign["cells"]:
        seen[cell["scenario_id"]].add(str(cell.get("subcase") or ""))
    return seen


def unmeasured_by_token_arm(tables):
    """(subcase token, arm) -> the unmeasured entry [M]; the row label kept."""
    index = {}
    for entry in tables["agreement"]["unmeasured"]:
        token = ROW_SUBCASE_TOKENS[row_key(entry["subcase"])]
        if token is None:
            raise PresentationError(
                f"unmeasured entry {entry['subcase']!r} maps to no corpus token"
            )
        key = (token, entry["arm"])
        if key in index:
            raise PresentationError(f"duplicate unmeasured entry for {key}")
        index[key] = entry
    return index


def expected_matrix_value(tables, row_label, arm):
    """The sealed expected_matrix cell, for cross-check [M]."""
    for row in tables["expected_matrix"]:
        if row["subcase"] == row_label:
            return row["cells"].get(arm)
    raise PresentationError(f"expected_matrix has no row labelled {row_label!r}")


def main():
    campaign = load_campaign()
    tables = load_tables()
    agreement = tables["agreement"]

    unscorable = campaign["unscorable"]
    unmeasured = agreement["unmeasured"]
    n_rows = len(unscorable)
    print_render(ARTEFACT, "unscorable_rows [M]", n_rows)
    print_render(ARTEFACT, "unmeasured_entries [M]", len(unmeasured))

    # Distinct-cause census: every cause string, verbatim, with its count.
    census = Counter(str(row[2]) for row in unscorable)
    print_render(ARTEFACT, "distinct_causes [D]", len(census))
    for cause, count in census.items():
        print_render(ARTEFACT, f"cause_count[{cause!r}] [D]", count)
    for name in FAIL_CLOSED_CAUSES:
        # A named fail-closed cause produced a cell iff its string is in the
        # census; the census above is the full record, so this is a lookup.
        hits = sum(v for k, v in census.items() if k != "NA per the sealed record")
        print_render(
            ARTEFACT,
            f"fail_closed_cause_cells[{name}] [D]",
            0 if hits == 0 else f"{hits} non-NA cause cells -- see census",
        )

    tokens = scenario_tokens(campaign)
    index = unmeasured_by_token_arm(tables)
    matched = {}
    table_rows = []
    all_matched = True
    for i, row in enumerate(unscorable):
        scenario_id, arm, cause = str(row[0]), str(row[1]), str(row[2])
        toks = tokens.get(scenario_id, set())
        entry = token = None
        if len(toks) == 1:
            token = next(iter(toks))
            entry = index.get((token, arm))
        if entry is None:
            all_matched = False
            expected_txt = "(no mechanical match -- see side-by-side list)"
            print_render(ARTEFACT, f"row[{i}]", f"{scenario_id} | {arm} | UNMATCHED | {cause}")
        else:
            key = (token, arm)
            if key in matched:
                raise PresentationError(f"unmeasured entry {key} matched twice")
            matched[key] = entry
            em = expected_matrix_value(tables, entry["subcase"], arm)
            if em != entry["expected"]:
                raise PresentationError(
                    f"expected_matrix {entry['subcase']!r}/{arm} = {em!r} but "
                    f"agreement.unmeasured says {entry['expected']!r}"
                )
            expected_txt = f"{entry['expected']}  ({entry['subcase']})"
            print_render(
                ARTEFACT,
                f"row[{i}]",
                f"{scenario_id} | {arm} | expected={entry['expected']} "
                f"(E.4 row {entry['subcase']!r}; expected_matrix={em}) | {cause}",
            )
        table_rows.append((scenario_id, arm, expected_txt, cause))
    print_render(ARTEFACT, "rows_matched_to_unmeasured [D]", len(matched))
    unmatched_unmeasured = [e for k, e in index.items() if k not in matched]
    print_render(ARTEFACT, "unmeasured_entries_left_unmatched [D]", len(unmatched_unmeasured))

    agreed = int(agreement["agreed"])
    disagreed = len(agreement["disagreed"])
    comparable = agreed + disagreed
    base = comparable + len(unmeasured)
    print_render(ARTEFACT, "entries_agreed [M]", agreed)
    print_render(ARTEFACT, "entries_disagreed [M]", disagreed)
    print_render(ARTEFACT, "entries_comparable [D agreed+disagreed]", comparable)
    print_render(ARTEFACT, "entries_base [D comparable+unmeasured]", base)

    # ---- render ------------------------------------------------------------
    # C2 (FIGURE_PLAN.md §0.7b): authored 9.2 in wide so the tight-bbox PDF
    # page stays under A4 landscape's ~9.7 in of text width; nothing is scaled.
    # Every length below is in inches; the axes is placed in inches too.
    mpl_setup()
    header = ("scenario_id", "arm", "§E.4 expected (row label)", "cause (verbatim)")
    fig_w = 9.2
    side = 0.10  # axes inset, each side
    ax_w = fig_w - 2 * side  # 9.0 in of table
    row_h = 0.225  # one table row (8 pt type, 1.35x leading, cell padding)
    line_h = FONT_MIN_PT * 1.3 / 72.0  # one footer text line
    para_gap, table_gap, top_pad, bottom_pad = 0.08, 0.25, 0.40, 0.15

    if len(census) == 1:
        (only_cause,) = census
        footer1 = (
            f"All {n_rows} causes: “{only_cause}” [M]; the three defined "
            f"fail-closed causes produced zero cells: {FAIL_CLOSED_CAUSES[0]}, "
            f"{FAIL_CLOSED_CAUSES[1]}, {FAIL_CLOSED_CAUSES[2]} — 0 cells each "
            "(src/harness/campaign.py unscorable sites; DEVIATIONS.md v0.8 entry)."
        )
    else:
        footer1 = (
            "Distinct causes: " + "; ".join(f"“{k}” × {v}" for k, v in census.items()) + " [M]."
        )
    footer2 = (
        f"These {n_rows} cells are §E.4's own NA cells (ADR 0035: NA is a statement about "
        f"the corpus — no second instance to score — never about a measurable admission) "
        f"and are the {len(unmeasured)} NA-unmeasured agreement entries: "
        f"{agreed} of {comparable} comparable entries agreed; {len(unmeasured)} of the "
        f"{base} base entries were NA and not comparable. Rows are in the record's own "
        "order."
    )
    lines = [footer1, footer2]
    if not all_matched:
        lines.append(
            "The (scenario_id, arm) → §E.4 row join could not be "
            "made mechanically for every row; agreement.unmeasured verbatim:"
        )
        for e in unmeasured:
            lines.append(
                f"  arm={e['arm']} | expected={e['expected']} | "
                f"observed={e['observed']!r} | subcase={e['subcase']}"
            )
    # Each footer paragraph is wrapped to the table's width (a conservative
    # ~14.5 characters per inch at 8 pt DejaVu Sans), never to the figure edge.
    paras = [
        textwrap.wrap(t, width=int(ax_w * 14.5), break_long_words=False) or [""] for t in lines
    ]
    foot_h = sum(len(p) for p in paras) * line_h + (len(paras) - 1) * para_gap
    table_h = (n_rows + 1) * row_h
    ax_h = table_h + table_gap + foot_h
    fig_h = top_pad + ax_h + bottom_pad
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([side / fig_w, bottom_pad / fig_h, ax_w / fig_w, ax_h / fig_h])
    ax.axis("off")
    ax.set_title(
        "TAB-3 — the ten unscorable cells, with causes (exact listing; no CI is "
        "defined for any number on this table)",
        loc="left",
        fontsize=FONT_MIN_PT + 1,
    )
    # The table fills the axes width exactly (bbox, not loc: loc="upper left"
    # would inset it by 2% of the axes and let it overhang the right edge).
    tbl = ax.table(
        cellText=[list(r) for r in table_rows],
        colLabels=list(header),
        colWidths=[0.20, 0.17, 0.39, 0.24],
        cellLoc="left",
        colLoc="left",
        bbox=[0.0, 1.0 - table_h / ax_h, 1.0, table_h / ax_h],
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(FONT_MIN_PT)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(INK)
        cell.set_linewidth(0.4)
        cell.get_text().set_color(INK)
        if r == 0:
            cell.get_text().set_fontweight("bold")

    # The footer starts below the table's bottom edge; each paragraph advances
    # by its own wrapped line count (axes fraction = inches / ax_h).
    y = 1.0 - (table_h + table_gap) / ax_h
    for para in paras:
        ax.text(
            0.0,
            y,
            "\n".join(para),
            fontsize=FONT_MIN_PT,
            color=INK,
            va="top",
            ha="left",
            linespacing=1.3,
            transform=ax.transAxes,
        )
        y -= (len(para) * line_h + para_gap) / ax_h
    save(fig, "tab3_unscorable_cells", ARTEFACT)


if __name__ == "__main__":
    main()
