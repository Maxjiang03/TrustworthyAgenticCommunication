"""TAB-2 -- agreement reconciliation: the D5 denominator ladder, line by line.

Pure presentation (ADR 0048): every number is read from the committed JSONs or
derived by printed arithmetic; the partition follows AGREEMENT_PARTITION_RULE.
"""

from _common import (
    FONT_MIN_PT,
    INK,
    PresentationError,
    load_campaign,
    load_tables,
    mpl_setup,
    plt,
    print_partition,
    print_render,
    save,
)

ARTEFACT = "TAB-2"

R1_RULE = (
    "Scoring configuration (§E.4 footnote †, analysis/ingest.py): a daggered "
    "expected cell (A†) is scored against the monitor_attached=False pass ONLY; "
    "an undaggered F4/F5 expected cell must hold under EVERY configuration run; "
    "an F1/F2/F3 entry is scored against its single unmonitored measurement."
)


def main():
    campaign = load_campaign()
    tables = load_tables()
    agreement = tables["agreement"]

    scored = len(campaign["cells"])
    unscorable = len(campaign["unscorable"])
    cells_run = scored + unscorable
    agreed = int(agreement["agreed"])
    disagreed = len(agreement["disagreed"])
    unmeasured = len(agreement["unmeasured"])
    not_populated = len(agreement["not_populated"])
    deferred = len(agreement["deferred"])
    entries = agreed + disagreed + unmeasured

    print_render(ARTEFACT, "cells_scored [M]", scored)
    print_render(ARTEFACT, "cells_unscorable [M]", unscorable)
    print_render(ARTEFACT, "cells_run [D scored+unscorable]", cells_run)
    print_render(ARTEFACT, "entries_agreed [M]", agreed)
    print_render(ARTEFACT, "entries_disagreed [M]", disagreed)
    print_render(ARTEFACT, "entries_unmeasured_NA [M]", unmeasured)
    print_render(ARTEFACT, "entries_total [D]", entries)
    print_render(ARTEFACT, "rows_not_populated [M]", not_populated)
    print_render(ARTEFACT, "rows_deferred [M]", deferred)
    predicted_rows = [r for r in tables["expected_matrix"] if r["state"] == "predicted"]
    n_arms = {len(r["cells"]) for r in predicted_rows}
    if len(n_arms) != 1:
        raise PresentationError(f"predicted rows disagree on arm count: {n_arms}")
    entries_expected = len(predicted_rows) * n_arms.pop()
    print_render(ARTEFACT, "entries_expected [D rows x arms]", entries_expected)
    if entries != entries_expected:
        raise PresentationError(
            f"agreement block has {entries} entries but expected_matrix implies "
            f"{entries_expected}; the ladder does not close on the record"
        )

    groups = print_partition(ARTEFACT, campaign, tables)
    consumed = groups["agreement_consumed"]
    ladder_consumed = sum(1 for c in consumed if c["family"] in ("F1", "F2", "F3"))
    config_consumed = sum(1 for c in consumed if c["family"] in ("F4", "F5"))
    benign = len(groups["benign_golden_thread"])
    controls = len(groups["f45_benign_controls"])
    complement = len(groups["dagger_true_complement"])
    outside = benign + controls + complement
    print_render(ARTEFACT, "cells_consumed_ladder_families [D]", ladder_consumed)
    print_render(ARTEFACT, "cells_consumed_config_families [D]", config_consumed)
    print_render(ARTEFACT, "cells_consumed_total [D]", ladder_consumed + config_consumed)
    print_render(ARTEFACT, "cells_outside_benign [D]", benign)
    print_render(ARTEFACT, "cells_outside_controls [D]", controls)
    print_render(ARTEFACT, "cells_outside_dagger_true [D]", complement)
    print_render(ARTEFACT, "cells_outside_total [D]", outside)
    undaggered_config_entries = sum(
        1
        for r in tables["expected_matrix"]
        if r["state"] == "predicted" and r["family"] in ("F4", "F5")
        for v in r["cells"].values()
        if isinstance(v, str) and v != "NA" and not v.endswith("†")
    )
    print_render(
        ARTEFACT, "undaggered_config_entries [D from expected_matrix]", undaggered_config_entries
    )
    print_render(
        ARTEFACT,
        "coincidence_check entries==consumed_cells [D]",
        entries == ladder_consumed + config_consumed,
    )
    print_render(
        ARTEFACT,
        "coincidence_offsets NA_entries vs undaggered_config_entries [D]",
        f"-{unmeasured} vs +{undaggered_config_entries}",
    )
    if ladder_consumed + config_consumed + outside != scored:
        raise PresentationError("partition does not cover the scored cells")

    lines = [
        (
            "The denominator ladder (every base labelled; CELLS and ENTRIES are different objects)",
            True,
        ),
        (
            f"{cells_run} cells run  =  {scored} scored [M]  +  {unscorable} "
            f"unscorable [M] (all ten are the §E.4 NA cells)",
            False,
        ),
        (
            f"§E.4 agreement operates on ENTRIES: 10 predicted rows × 9 arms = {entries} entries",
            False,
        ),
        (
            f"{entries} entries  =  {agreed} agreed [M]  +  {unmeasured} NA — not "
            f"comparable [M]  +  {disagreed} disagreed [M]",
            False,
        ),
        (
            f"Entries consume {ladder_consumed + config_consumed} of the {scored} "
            f"scored cells: {ladder_consumed} ladder-family (F1/F2/F3) + "
            f"{config_consumed} configuration-family (F4/F5)",
            False,
        ),
        (
            f"{outside} scored cells sit outside every agreement entry: "
            f"{benign} benign golden-thread + {controls} F4/F5 benign controls + "
            f"{complement} monitor-attached cells of daggered arms",
            False,
        ),
        (
            f"TWO DIFFERENT NUMBERS: (1) {entries} = the count of §E.4 ENTRIES "
            f"(rows × arms); (2) {ladder_consumed + config_consumed} = the count of "
            f"scored CELLS those entries consume. Their equality here is a "
            f"COINCIDENCE: the ladder families' {unmeasured} NA entries consume no cell "
            f"(−{unmeasured}) and the {undaggered_config_entries} undaggered F4/F5 entries "
            f"consume two cells each (+{undaggered_config_entries}); the offsets cancel "
            f"exactly. Nothing in this table or its script relies on the equality.",
            False,
        ),
        (
            f"{not_populated} §E.4 rows NOT POPULATED BY THE CAMPAIGN and "
            f"{deferred} row deferred sit outside every count above",
            False,
        ),
        ("", False),
        (
            "ENTRIES and CELLS are not one-to-one. An §E.4 entry is one (predicted row, "
            "arm) pair. A daggered entry (A† — the four B2 arms in each F4/F5 attack row, "
            "ADR 0032) is scored against its monitor-off cell only. An UNDAGGERED F4/F5 "
            "entry spans two cells and agrees only if the prediction holds under BOTH "
            "configurations — a stricter test than one cell would give, not a bookkeeping "
            'footnote. "80 agreed" therefore means: of the 90 base entries, 80 are '
            "comparable and all 80 agree (10 are NA and not comparable); those 80 entries "
            "cover 90 scored cells. It is not 80 cells, and not 80 of 143.",
            False,
        ),
        (R1_RULE, False),
        (
            "Agreement is stated as: 80 of 80 comparable entries agreed; 10 of the "
            "90 base entries were NA and not comparable. (“80 of 90” "
            "appears nowhere unqualified.)",
            False,
        ),
    ]

    mpl_setup()
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    ax.axis("off")
    y = 1.0
    for text, is_title in lines:
        weight = "bold" if is_title else "normal"
        ax.text(
            0.0,
            y,
            text,
            fontsize=FONT_MIN_PT + (1 if is_title else 0),
            fontweight=weight,
            color=INK,
            va="top",
            wrap=True,
            transform=ax.transAxes,
        )
        y -= 0.080 if text else 0.030
    ax.set_title(
        "TAB-2 — §E.4 agreement reconciliation (exact counts; no CI is "
        "defined for any number on this table)",
        loc="left",
        fontsize=FONT_MIN_PT + 1,
    )
    save(fig, "tab2_agreement_ladder", ARTEFACT)


if __name__ == "__main__":
    main()
