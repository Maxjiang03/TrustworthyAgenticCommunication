"""TAB-0 -- the provenance register: corpus | CPU pinning | evidence class | status.

One row per artefact of the AUTHORISED set plus one row per D3-GATED latency
artefact (FIGURE_PLAN.md sections B/C). Pure presentation (ADR 0048): every
provenance field is read from the committed run records (campaign-confirmatory
.json passes[0].run; latency-pilot.json plan block) and printed to stdout; the
register computes, selects, and bins nothing.
"""

import re
import textwrap

from _common import (
    FONT_MIN_PT,
    GHOST,
    INK,
    REPO_ROOT,
    RESULTS_RAW,
    PresentationError,
    load_campaign,
    mpl_setup,
    plt,
    print_render,
    save,
)

ARTEFACT = "TAB-0"

# The two artefact sets, verbatim from the Phase-2 ruling (FIGURE_PLAN.md B;
# tools/figures/build_all.py AUTHORISED). Nothing else is registered.
AUTHORISED = (
    "FIG-1",
    "FIG-3",
    "TAB-0",
    "TAB-1",
    "TAB-2",
    "TAB-3",
    "TAB-4",
    "TAB-5",
    "TAB-9",
    "TAB-10",
)
D3_GATED = ("FIG-4", "FIG-5", "FIG-6", "TAB-6", "TAB-7", "TAB-8")
D3_STATUS = "D3-GATED — specification only; not generated"
AUTH_STATUS = "AUTHORISED — generated (tools/figures/, ADR 0048)"

# Header line, verbatim (FIGURE_PLAN.md A/N.1, E item 9).
HEADER = (
    "Security = CONFIRMATORY corpus; latency = PILOT corpus (ADR 0047: frozen "
    "row 1, PRE_REGISTRATION §6, ADR 0026, §J.3 item 12, analysis/latency.py)"
)

# The campaign JSON carries no run timestamp; the run date is the claims
# record's (DEVIATIONS.md D-005: "ran once on 2026-08-07 at 17e11c9").
RUN_DATE_SOURCE = "DEVIATIONS.md D-005"
RUN_DATE = "2026-08-07"

# CPU-pinning column: code-inspection provenance (FIGURE_PLAN.md B TAB-6 note,
# cross-ref TAB-0). Neither run record has a pinning field; the basis is the
# ABSENCE of any affinity call in the two measurement drivers. The scan below
# re-checks that absence at build time and can only abort, never alter a value.
PINNING_FILES = ("src/harness/campaign_driver.py", "src/harness/latency_collector.py")
PINNING_TOKENS = ("affinity", "pin_to_performance_cores", "measurement_platform")
G3_PINNED_FILE = "smoke/g3/spike.py"
PINNING_SECURITY = (
    "unpinned (no affinity call in campaign_driver.py/latency_collector.py; only gate G-3 pinned)"
)
PINNING_LATENCY = "unpinned"

EVIDENCE_CAMPAIGN = "campaign"
EVIDENCE_FIG3 = "campaign + gate G-14 (cited, not plotted) + none (H4b)"
EVIDENCE_DESCRIPTIVE = "descriptive (RQ4 protocol)"
EVIDENCE_ROW1 = "pre-registered decision (frozen row 1; UNDECIDED until D3)"

FOOTNOTES = (
    "CPU pinning — code-inspection basis: no affinity call in "
    "src/harness/campaign_driver.py or src/harness/latency_collector.py "
    "(re-scanned at build time; neither run record has a pinning field). The only "
    "pinned measurement in the study is gate G-3's isolated microbenchmark "
    "(smoke/g3/spike.py → measurement_platform.pin_to_performance_cores), which is "
    "not a campaign or pilot-latency artefact.",
    "D3 gate (FIGURE_PLAN.md §0.5): FIG-4/5/6 and TAB-6/7/8 exist only as "
    "specifications until BOTH (i) a DEVIATIONS.md entry written BEFORE the run "
    "pre-commits to reporting the row-1 verdict as returned, and (ii) the sealed "
    "analysis/latency.py has run over results/raw/latency-pilot.json with its "
    "output committed. Until then §N.5 prints UNDECIDED and no latency chart exists.",
    "TAB-0 renders no measured quantity; it registers where each artefact's "
    "numbers come from. Exact provenance only; no CI is defined for anything here.",
)


def read_latency_head(nbytes=16384):
    """corpus_root / run_mode of latency-pilot.json, from its first `nbytes`
    only (the file is ~10.7 MB; the plan block sits in its head)."""
    path = RESULTS_RAW / "latency-pilot.json"
    if not path.is_file():
        raise PresentationError(f"missing {path}; the RQ4 latency pass output not found")
    with open(path, "rb") as fh:
        head = fh.read(nbytes).decode("utf-8", errors="replace")
    if '"plan"' not in head:
        raise PresentationError("latency-pilot.json head carries no plan block")
    out = {}
    for key in ("corpus_root", "run_mode"):
        m = re.search(r'"%s"\s*:\s*"([^"]*)"' % key, head)
        if not m:
            raise PresentationError(f"latency-pilot.json head carries no {key!r}")
        out[key] = m.group(1)
    return out


def scan_pinning():
    """Build-time re-check of the code-inspection claim behind the pinning column."""
    hits = {}
    for rel in PINNING_FILES:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8").lower()
        hits[rel] = sum(text.count(tok.lower()) for tok in PINNING_TOKENS)
        print_render(
            ARTEFACT, f"pinning_scan.{rel}.affinity_token_hits [M code inspection]", hits[rel]
        )
    if any(hits.values()):
        raise PresentationError(
            "an affinity/pinning token appears in a measurement driver; the "
            "'unpinned' line would be false -- not patched over"
        )
    g3 = (REPO_ROOT / G3_PINNED_FILE).read_text(encoding="utf-8")
    g3_hits = g3.count("pin_to_performance_cores")
    print_render(
        ARTEFACT,
        f"pinning_scan.{G3_PINNED_FILE}.pin_to_performance_cores [M code inspection]",
        g3_hits,
    )
    if g3_hits == 0:
        raise PresentationError("gate G-3's spike no longer pins; the footnote would be false")


def main():
    campaign = load_campaign()
    passes = campaign["passes"]
    run = passes[0]["run"]
    run_mode = run["run_mode"]
    corpus_root = campaign["corpus_root"]
    git_commit = run["git_commit"]
    git_dirty = run["git_dirty"]
    print_render(ARTEFACT, "campaign.passes[0].run.run_mode [M]", run_mode)
    print_render(ARTEFACT, "campaign.passes[0].run.corpus [M]", run["corpus"])
    print_render(ARTEFACT, "campaign.corpus_root [M]", corpus_root)
    print_render(ARTEFACT, "campaign.passes[0].run.git_commit [M]", git_commit)
    print_render(ARTEFACT, "campaign.passes[0].run.git_dirty [M]", git_dirty)
    print_render(ARTEFACT, "campaign.passes [M]", len(passes))
    for i, p in enumerate(passes):
        if p["run"]["git_commit"] != git_commit or p["run"]["git_dirty"] is not False:
            raise PresentationError(f"pass {i} run record disagrees with pass 0")
        if p["run"]["run_mode"] != run_mode:
            raise PresentationError(f"pass {i} run_mode disagrees with pass 0")
    if run_mode != "confirmatory" or corpus_root != "fixtures/confirmatory":
        raise PresentationError("the campaign record is not the CONFIRMATORY corpus")
    if not run["corpus"].replace("\\", "/").endswith("/" + corpus_root):
        raise PresentationError("passes[0].run.corpus does not end in campaign.corpus_root")
    short = git_commit[:7]
    print_render(ARTEFACT, "git_commit_short [D first 7 hex]", short)
    print_render(ARTEFACT, f"run_date [{RUN_DATE_SOURCE}; not a field of the JSON]", RUN_DATE)
    corpus_security = (
        f"{run_mode.upper()} ({corpus_root}; run once {RUN_DATE} at {short}; git_dirty={git_dirty})"
    )

    lat = read_latency_head()
    print_render(ARTEFACT, "latency.run_mode [M head 16 KB]", lat["run_mode"])
    print_render(ARTEFACT, "latency.corpus_root [M head 16 KB]", lat["corpus_root"])
    if lat["run_mode"] != "pilot":
        raise PresentationError("the latency record is not the PILOT corpus")
    corpus_latency = f"{lat['run_mode'].upper()} ({lat['corpus_root']})"

    scan_pinning()

    rows = []
    for aid in AUTHORISED:
        if aid == "TAB-0":
            rows.append(
                (
                    aid,
                    "both — this register (security rows: "
                    f"{run_mode.upper()}; latency rows: {lat['run_mode'].upper()})",
                    "both passes unpinned (see rows; basis in footnote)",
                    "register (cites; renders no measured quantity)",
                    AUTH_STATUS,
                )
            )
        elif aid == "FIG-3":
            rows.append((aid, corpus_security, PINNING_SECURITY, EVIDENCE_FIG3, AUTH_STATUS))
        else:
            rows.append((aid, corpus_security, PINNING_SECURITY, EVIDENCE_CAMPAIGN, AUTH_STATUS))
    for aid in D3_GATED:
        ev = EVIDENCE_ROW1 if aid in ("FIG-4", "TAB-6") else EVIDENCE_DESCRIPTIVE
        rows.append((aid, corpus_latency, PINNING_LATENCY, ev, D3_STATUS))
    print_render(ARTEFACT, "rows_authorised [D]", len(AUTHORISED))
    print_render(ARTEFACT, "rows_d3_gated [D]", len(D3_GATED))
    print_render(ARTEFACT, "rows_total [D]", len(rows))
    for r in rows:
        print_render(ARTEFACT, f"row.{r[0]}", " | ".join(r[1:]))

    # ---- geometry (inches) ----------------------------------------------
    # C2 (FIGURE_PLAN.md §0.7b): authored to fit A4 landscape's ~9.7 in of
    # text width WITHOUT scaling -- the columns are re-proportioned and the
    # cell text wrapped; the PDF is fig_w + the 0.2 in tight-bbox pad.
    mpl_setup()
    cols = ("artefact", "corpus", "CPU pinning", "evidence class", "status")
    widths = (0.62, 2.48, 2.42, 1.75, 1.83)  # 9.10 in; each column holds its
    # longest unbreakable token at 8 pt (widest: the two-driver path of the
    # CPU-pinning line, 2.28 in), checked by measuring every wrapped line.
    char_w = 0.065  # DejaVu Sans, 8 pt: average advance (lower case 0.062 in,
    # capitals 0.075 in); the -2 below keeps caps-heavy lines inside the column
    wrap = [max(8, int(w / char_w) - 2) for w in widths]
    line_h, pad = 0.135, 0.09
    margin = 0.10
    fig_w = margin * 2 + sum(widths)  # 9.30 in -> a 9.50 in PDF page

    def wrap_text(text, width):
        # Never split a path, an ID, or a date: tokens stay whole.
        return textwrap.wrap(text, width, break_long_words=False, break_on_hyphens=False)

    def wrapped(row):
        return [wrap_text(t, wrap[i]) or [""] for i, t in enumerate(row)]

    full_wrap = int((fig_w - 2 * margin) / char_w) - 2
    header_lines = wrap_text(HEADER, full_wrap)
    foot_lines = []
    for f in FOOTNOTES:
        foot_lines.extend(wrap_text(f, full_wrap))
        foot_lines.append("")
    body = []  # (kind, content, height)
    body.append(("head", wrapped(cols), line_h + pad))
    body.append(("group", "AUTHORISED (Phase-2 ruling 2026-08-14; ADR 0048)", line_h + pad))
    for r in rows[: len(AUTHORISED)]:
        w = wrapped(r)
        body.append(("row", w, max(len(c) for c in w) * line_h + pad))
    body.append(("group", "D3-GATED (FIGURE_PLAN.md §0.5) — PILOT corpus", line_h + pad))
    for r in rows[len(AUTHORISED) :]:
        w = wrapped(r)
        body.append(("row", w, max(len(c) for c in w) * line_h + pad))

    top_h = 0.35 + len(header_lines) * line_h + 0.15
    table_h = sum(h for _, _, h in body)
    foot_h = len(foot_lines) * line_h + 0.25
    fig_h = top_h + table_h + foot_h + margin
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    y = fig_h - margin
    ax.text(
        margin,
        y,
        "TAB-0 — provenance register: one row per artefact — corpus | CPU "
        "pinning | evidence class | status",
        fontsize=FONT_MIN_PT + 1,
        fontweight="bold",
        color=INK,
        va="top",
    )
    y -= 0.35
    for ln in header_lines:
        ax.text(margin, y, ln, fontsize=FONT_MIN_PT, color=INK, va="top")
        y -= line_h
    y -= 0.15

    x0 = [margin]
    for w in widths[:-1]:
        x0.append(x0[-1] + w)
    for kind, content, h in body:
        ax.plot([margin, fig_w - margin], [y, y], color=INK, lw=0.5)
        if kind == "group":
            ax.add_patch(
                plt.Rectangle(
                    (margin, y - h), fig_w - 2 * margin, h, facecolor=GHOST, edgecolor="none"
                )
            )
            ax.text(
                margin + 0.06,
                y - h / 2,
                content,
                fontsize=FONT_MIN_PT,
                fontweight="bold",
                color=INK,
                va="center",
            )
        else:
            for i, lines in enumerate(content):
                yy = y - pad / 2
                for ln in lines:
                    ax.text(
                        x0[i] + 0.05,
                        yy,
                        ln,
                        fontsize=FONT_MIN_PT,
                        fontweight="bold" if kind == "head" else "normal",
                        color=INK,
                        va="top",
                    )
                    yy -= line_h
        y -= h
    ax.plot([margin, fig_w - margin], [y, y], color=INK, lw=0.5)
    y -= 0.25
    for ln in foot_lines:
        ax.text(margin, y, ln, fontsize=FONT_MIN_PT, color=INK, va="top")
        y -= line_h

    save(fig, "tab0_provenance_register", ARTEFACT)


if __name__ == "__main__":
    main()
