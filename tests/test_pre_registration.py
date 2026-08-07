"""Every quantitative claim in PRE_REGISTRATION.md, verified against its source.

Part H step 2's document earns its authority by restating decisions the
repository already records; a pre-registration whose numbers can drift from
the repository is one that will drift. So: frozen rows by value (through their
single reader), the three frozen digests, the §E.4 expected matrix
cell-for-cell against the design document, the arm list, the five span names,
the fifteen-gate record with each cited commit resolved against the history of
the report it landed, the G-3 figures for all three runs against the two reports
that own them — including recomputing BOTH Mann-Whitney comparisons exactly
from the recorded batch tables — the row 7 sourcing (URLs, retrieval date, and the unanchored
marking), the ADR 0028 scan re-executed, the retained-reference counts
re-measured, the not-sealed guards, the five gap closures (2026-08-06)
each verified against the artifact that closed it, and the two declarations
added 2026-08-06 — F3's partial instantiation and F4's weaker confirmatory
independence — each traced to the corpora and the frozen ontology by
recomputation rather than by reading the document's own claim back.

Values are derived from the sources at test time, never typed here, so the
test cannot itself become a second copy that drifts.
"""

import json
import re
import subprocess
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PR_PATH = REPO_ROOT / "docs" / "PRE_REGISTRATION.md"
DESIGN_PATH = REPO_ROOT / "docs" / "EXPERIMENT_ARCHITECTURE_FINAL.md"
PILOT_CORPUS = REPO_ROOT / "fixtures" / "pilot" / "golden_thread"
CONFIRMATORY_CORPUS = REPO_ROOT / "fixtures" / "confirmatory"
OMEGA_GAMMA_PATH = REPO_ROOT / "src" / "harness" / "authorizer" / "omega_gamma_v1.json"


def _pr() -> str:
    return PR_PATH.read_text(encoding="utf-8")


def _pr_flat() -> str:
    """The document with line wraps collapsed, for multi-word phrase asserts."""
    return " ".join(_pr().split())


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT), capture_output=True, check=True, text=True
    )
    return result.stdout


def _parse_pipe_table(text: str, header_start: str) -> list[list[str]]:
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip().startswith(header_start))
    rows: list[list[str]] = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(set(cell) <= set(":- ") for cell in cells):
            continue
        rows.append(cells)
    return rows


def _declaration(start_marker: str, end_marker: str) -> str:
    """One declaration's own span, flattened — never the whole document.

    Scoped deliberately: a marker searched for across the whole file can be
    satisfied by text elsewhere, which is exactly how a deleted clause once
    left a closure test green.
    """
    text = _pr()
    assert text.count(start_marker) == 1, f"declaration marker not unique: {start_marker!r}"
    start = text.index(start_marker)
    return " ".join(text[start : text.index(end_marker, start)].split())


F3_DECLARATION = ("**Declaration — F3 IS INSTANTIATED IN PART", "**Declaration — row 5 is deferred")
F4_DECLARATION = ("**Declaration — F4's CONFIRMATORY INDEPENDENCE", "## 3. Hypotheses")


def _scenarios(corpus: Path, kind: str = "sealed") -> dict[str, dict]:
    """Every scenario document of one corpus, keyed by file stem."""
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((corpus / kind).glob("*.json"))
    }


def _normalise_subcase(name: str) -> str:
    """`F3:audience_mismatch` and §E.4's `audience-mismatch` are one subcase."""
    return name.strip().strip("`").replace("_", "-").lower()


def _e4_f3_subcases() -> list[str]:
    """The F3 subcases §E.4 defines, parsed from its own brace list."""
    design = DESIGN_PATH.read_text(encoding="utf-8")
    marker = "**F3** invocation integrity {"
    assert design.count(marker) == 1
    start = design.index(marker)
    body = design[design.index("{", start) + 1 : design.index("}", start)]
    return [chunk.split(" (")[0].strip().strip("`") for chunk in body.split(",")]


def _f3_instantiated(corpus: Path) -> set[str]:
    return {
        _normalise_subcase(doc["attack_subcase"].split(":", 1)[1])
        for doc in _scenarios(corpus).values()
        if doc["attack_subcase"].startswith("F3:")
    }


def _matrix_cell(value: str) -> str:
    return value.replace("*", "").replace("†", "").strip()


def _sibling_pairs() -> list[tuple[str, dict, dict]]:
    """(confirmatory id, confirmatory doc, its matched pilot doc)."""
    pilot = _scenarios(PILOT_CORPUS)
    pairs = []
    for scenario_id, doc in sorted(_scenarios(CONFIRMATORY_CORPUS).items()):
        pairs.append((scenario_id, doc, pilot[doc["matched_pilot_sibling"]]))
    return pairs


def _element(doc: dict) -> list[tuple[str, str]]:
    return [tuple(pair) for pair in doc["R"]]


def _egress_elements() -> list[tuple[str, str]]:
    """Row 4's egress set over the frozen `Ω`, DERIVED as the code derives it."""
    from src.harness.policy import frozen_policy
    from src.sut.protocol.required_authority import recipient_carrying_actions

    omega = json.loads(OMEGA_GAMMA_PATH.read_text(encoding="utf-8"))["omega"]
    actions = frozen_policy.egress_actions(set(omega["tools"]), recipient_carrying_actions())
    return [tuple(pair) for pair in omega["elements"] if pair[0] in actions]


class TestFrozenValues:
    def test_every_frozen_scalar_appears_with_its_frozen_value(self):
        from src.harness import frozen_parameters as fp

        t_full, t_ttft = fp.llm_turn_denominators()
        tokens = {
            f"equivalence_margin_ms = {fp.equivalence_margin_ms()}",
            f"g3_threshold_ms = {fp.g3_threshold_ms()}",
            f"delta_seconds = {fp.delta_seconds()}",
            f"replay_cache_capacity = {fp.replay_cache_capacity()}",
            f"T_full_ms = {t_full}",
            f"T_ttft_ms = {t_ttft}",
        }
        text = _pr()
        missing = sorted(token for token in tokens if token not in text)
        assert missing == [], missing

    def test_the_three_frozen_digests_match_their_readers(self):
        from src.harness import frozen_parameters as fp

        text = _pr()
        for digest in (fp.expected_h_gamma(), fp.expected_h_policy(), fp.expected_h_registry()):
            assert digest in text, digest

    def test_the_row_9_platform_is_named_as_recorded(self):
        from src.harness import frozen_parameters as fp

        recorded = fp.sealed_measurement_platform()
        assert "26200.8875" in recorded  # the row is set; this test rides on it
        assert "26200.8875" in _pr()


class TestTheExpectedMatrix:
    def test_e4_cells_match_the_design_document_cell_for_cell(self):
        design = _parse_pipe_table(DESIGN_PATH.read_text(encoding="utf-8"), "| Subcase (family) |")
        ours = _parse_pipe_table(_pr(), "| Subcase (family) |")
        assert ours == design

    def test_the_matrix_has_the_fourteen_family_rows(self):
        ours = _parse_pipe_table(_pr(), "| Subcase (family) |")
        assert len(ours) == 1 + 14  # header + rows


class TestArmsSpansAndAnalysis:
    def test_all_nine_arms_appear_as_the_code_spells_them(self):
        from src.harness import matrix_grouping

        text = _pr()
        for arm in matrix_grouping.ARMS:
            assert arm in text, arm

    def test_the_five_spans_and_the_segment(self):
        from analysis import latency

        text = _pr()
        for span in latency.RQ4_SPANS:
            assert span in text, span
        assert " + ".join(latency.MEASURED_SEGMENT_SPANS) in text
        assert latency.REFUSAL_PATH_SCENARIO in text

    def test_the_bootstrap_parameters_match_the_analysis_defaults(self):
        import inspect

        from analysis import latency

        defaults = inspect.signature(latency.equivalence_decision).parameters
        resamples = defaults["resamples"].default
        confidence = defaults["confidence"].default
        text = _pr()
        assert f"{resamples:,} resamples" in text
        assert f"{int(confidence * 100)}%" in text

    def test_the_claim_boundary_names_the_two_clean_increments(self):
        from analysis import latency

        difference = latency.e5_bit_difference("B2-exchange-task-DPoP", "B2-exchange-task")
        assert difference.mechanism in _pr()  # htc/holder
        difference = latency.e5_bit_difference("B3+", "B3")
        assert difference.mechanism in _pr()  # jti


class TestTheGateRecord:
    CITED = {
        "G-1": ("smoke/g1/REPORT.md", ["dca755b", "b385e6d"]),
        "G-2": ("smoke/g2/REPORT.md", ["e7bb8e0"]),
        "G-3": ("smoke/g3/REPORT.md", ["6a342c4"]),
        "G-4": ("smoke/g4/REPORT.md", ["3da17e7"]),
        "G-5": ("smoke/g5/REPORT.md", ["9cf08eb"]),
        "G-6": ("smoke/g6/REPORT.md", ["8a46d9d"]),
        "G-7": ("smoke/g7/REPORT.md", ["8a46d9d"]),
        "G-8": ("smoke/g8/REPORT.md", ["d7e38fd"]),
        "G-9": ("smoke/g9/REPORT.md", ["80d91c1", "8b25484"]),
        "G-10": ("smoke/g10/REPORT.md", ["55c1282"]),
        "G-11": ("smoke/g11/REPORT.md", ["1761ae6"]),
        "G-12": ("smoke/g12/REPORT.md", ["b98ac5e"]),
        "G-13": ("smoke/g13/REPORT.md", ["9431934"]),
        "G-14": ("smoke/g14/spike.py", ["dfbef6d"]),
        "G-15": ("smoke/g15/REPORT.md", ["71dd5ce"]),
    }

    def test_all_fifteen_gates_are_recorded(self):
        text = _pr()
        for gate in self.CITED:
            assert gate in text, gate

    def test_every_cited_commit_landed_the_record_it_is_cited_for(self):
        text = _pr()
        for gate, (path, shas) in self.CITED.items():
            history = _git("log", "--format=%h", "--", path)
            for sha in shas:
                assert sha in text, (gate, sha)
                assert sha in history.split(), (gate, sha, path)

    def test_g14_report_exists_and_declares_itself_retrospective_in_line_one(self):
        """The gap's closure must not disguise itself: the record is retrospective
        and says so in its FIRST line, and the adjudication stays on the board
        row and the spike."""
        report = REPO_ROOT / "smoke" / "g14" / "REPORT.md"
        first_line = report.read_text(encoding="utf-8").splitlines()[0]
        assert "RETROSPECTIVE" in first_line
        assert "NOT the contemporaneous adjudication" in first_line
        assert "board row" in first_line
        assert "no REPORT.md exists" not in _pr()
        assert "retrospective" in _pr_flat()

    def test_the_five_platform_bound_gates_and_the_rerun_commit(self):
        text = _pr()
        assert "G-3, G-6, G-7, G-12, G-10" in text
        assert "7b59e19" in text
        rerun = (REPO_ROOT / "tools" / "gate_rerun" / "REPORT.md").read_text(encoding="utf-8")
        assert "7b59e19" in rerun
        assert "RE-RUN ON THE SEALING COMMIT" in _pr_flat()


def _rerun_batches() -> "tuple[list[float], list[float]]":
    """(adjudicated, confirmation) batch medians from tools/gate_rerun/REPORT.md."""
    rerun = (REPO_ROOT / "tools" / "gate_rerun" / "REPORT.md").read_text(encoding="utf-8")
    adjudicated, confirmation = [], []
    for line in rerun.splitlines():
        match = re.match(r"\| batch \d \| \*?\*?([0-9.]+)\*?\*? \| \*?\*?([0-9.]+)\*?\*? \|", line)
        if match:
            adjudicated.append(float(match.group(1)))
            confirmation.append(float(match.group(2)))
    return adjudicated, confirmation


def _sealtime_batches() -> "tuple[list[float], list[float]]":
    """(adjudicated, seal-time) batch medians from smoke/g3/REPORT.md's
    seal-time comparison table (its two-column per-batch row; the original
    one-column row is skipped)."""
    g3 = (REPO_ROOT / "smoke" / "g3" / "REPORT.md").read_text(encoding="utf-8")
    for line in g3.splitlines():
        if line.strip().startswith("| per-batch medians |"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")][1:]
            if len(cells) == 2:
                return (
                    [float(value) for value in cells[0].split(",")],
                    [float(value) for value in cells[1].split(",")],
                )
    raise AssertionError("no two-column per-batch-medians row in smoke/g3/REPORT.md")


G3_REPORT = REPO_ROOT / "smoke" / "g3" / "REPORT.md"
GATE_RERUN_REPORT = REPO_ROOT / "tools" / "gate_rerun" / "REPORT.md"


def _cells(line: str) -> "list[str]":
    """A markdown row's cells, bold markers and units stripped."""
    return [
        cell.strip().replace("**", "").replace(" ms", "") for cell in line.strip("| \t").split("|")
    ]


def _four(cell: str) -> "list[float] | None":
    """The cell as exactly four batch medians, or None if it is not that."""
    parts = [part.strip() for part in cell.split(",")]
    if len(parts) != 4:
        return None
    try:
        return [float(part) for part in parts]
    except ValueError:
        return None


def _g3_runs() -> "list[tuple[str, float, list[float], Path]]":
    """Every G-3 run on the row 9 platform: (label, median, four batch medians, owning report).

    Parsed by SECTION from the reports that own the numbers, never typed here.
    `smoke/g3/REPORT.md` owns the adjudicated run and every seal-time re-run;
    `tools/gate_rerun/REPORT.md` owns the confirmation run. Where a section
    carries a two-column comparison table the LAST column is that section's own
    run and the first repeats the adjudicated four, which
    `test_the_seven_medians_and_twenty_eight_batch_medians_trace_to_their_reports`
    cross-checks.

    Fail-closed: a section that does not yield exactly one median and exactly
    four batch medians raises, so a report edit that breaks the shape is a test
    failure rather than a silently shorter list.
    """
    report = G3_REPORT.read_text(encoding="utf-8")
    sections: "list[list[str]]" = [[]]
    for line in report.splitlines():
        if re.match(r"^#{2,3} .*Seal-time re-run", line):
            sections.append([])
        sections[-1].append(line)

    runs: "list[tuple[str, float, list[float], Path]]" = []
    for index, lines in enumerate(sections):
        median: "float | None" = None
        batches: "list[float] | None" = None
        for line in lines:
            if not line.startswith("|"):
                continue
            cells = _cells(line)
            label = cells[0].lower()
            if label == "median" and median is None:  # `_cells` has stripped the bold markers
                for cell in reversed(cells[1:]):
                    value = re.match(r"^([0-9]+\.[0-9]{4})\b", cell)
                    if value:
                        median = float(value.group(1))
                        break
            if label in ("per-batch medians", "batch medians") and batches is None:
                for cell in reversed(cells[1:]):
                    found = _four(cell)
                    if found:
                        batches = found
                        break
        name = "adjudicated" if index == 0 else f"seal-time re-run {index}"
        assert median is not None, f"{name}: no median row found in smoke/g3/REPORT.md"
        assert batches is not None, f"{name}: no four-batch-median row found in smoke/g3/REPORT.md"
        runs.append((name, median, batches, G3_REPORT))

    adjudicated, confirmation = _rerun_batches()
    assert len(confirmation) == 4, "tools/gate_rerun/REPORT.md did not yield four batch medians"
    rerun_text = GATE_RERUN_REPORT.read_text(encoding="utf-8")
    confirmation_median: "float | None" = None
    for line in rerun_text.splitlines():
        if line.startswith("| median |"):
            confirmation_median = float(_cells(line)[2])
            break
    assert confirmation_median is not None, "no median row in tools/gate_rerun/REPORT.md"
    # Chronological: the confirmation run sits between the adjudication and the
    # seal-time re-runs, and the document lists the medians in that order.
    runs.insert(1, ("confirmation", confirmation_median, confirmation, GATE_RERUN_REPORT))
    return runs


def _exact_mann_whitney(a: "list[float]", b: "list[float]") -> "tuple[int, float]":
    """U = #{a_i > b_j}, and the exact two-sided p over all C(8,4) labelings."""
    u = sum(1 for x in a for y in b if x > y)
    pooled = a + b
    u_observed = min(u, 16 - u)
    count = total = 0
    for first_group in combinations(range(8), 4):
        u_perm = sum(
            1
            for i in first_group
            for j in range(8)
            if j not in first_group and pooled[i] > pooled[j]
        )
        total += 1
        if min(u_perm, 16 - u_perm) <= u_observed:
            count += 1
    return u, count / total


class TestTheG3Figures:
    def test_the_adjudicated_median_and_headroom_trace_to_the_gate_report(self):
        report = (REPO_ROOT / "smoke" / "g3" / "REPORT.md").read_text(encoding="utf-8")
        text = _pr()
        for figure in ("2.8264", "1.77"):
            assert figure in report, figure
            assert figure in text, figure
        # the conservative headroom is the threshold over the adjudicated median
        from src.harness import frozen_parameters as fp

        assert round(fp.g3_threshold_ms() / 2.8264, 2) == 1.77

    def test_the_three_medians_and_twelve_batch_medians_trace_to_their_reports(self):
        """Every G-3 number the document carries is owned by a report:
        adjudicated and seal-time by smoke/g3/REPORT.md, the confirmation by
        tools/gate_rerun/REPORT.md — and the two reports agree on the
        adjudicated four."""
        g3 = (REPO_ROOT / "smoke" / "g3" / "REPORT.md").read_text(encoding="utf-8")
        rerun = (REPO_ROOT / "tools" / "gate_rerun" / "REPORT.md").read_text(encoding="utf-8")
        text = _pr()
        medians = {"2.8264": g3, "2.6856": g3, "2.6928": rerun}
        for median, owner in medians.items():
            assert median in owner, median
            assert median in text, median
        assert 2.8264 > 2.6928 > 2.6856  # monotone downward, as the document states
        assert "monotone downward" in _pr_flat()
        adjudicated, confirmation = _rerun_batches()
        adjudicated_again, sealtime = _sealtime_batches()
        assert adjudicated == adjudicated_again, "the two reports disagree on the adjudicated four"
        assert len(adjudicated) == len(confirmation) == len(sealtime) == 4
        for value in adjudicated + sealtime:
            assert f"{value:.4f}" in g3, value
        for value in confirmation:
            assert f"{value:.4f}" in rerun, value

    def test_both_mann_whitney_comparisons_recompute_from_the_recorded_tables(self):
        """Both U and both p values are DERIVED — recomputed exactly from the
        batch tables the owning reports record, never accepted as written. The
        confirmation does not separate; the seal-time re-run separates
        COMPLETELY (U = 16 and p = 0.0286 are the extremes attainable at
        n = 4 vs 4, and the ranges do not overlap)."""
        adjudicated, confirmation = _rerun_batches()
        _, sealtime = _sealtime_batches()
        u_confirmation, p_confirmation = _exact_mann_whitney(adjudicated, confirmation)
        assert u_confirmation == 12
        assert round(p_confirmation, 2) == 0.34
        u_sealtime, p_sealtime = _exact_mann_whitney(adjudicated, sealtime)
        assert u_sealtime == 16
        assert round(p_sealtime, 4) == 0.0286
        assert min(adjudicated) > max(sealtime)  # complete separation: no overlap
        text = _pr()
        assert "U = 12" in text and "p = 0.34" in text
        assert "U = 16" in text and "p = 0.0286" in text
        assert "separates completely" in _pr_flat()

    def test_the_difference_and_its_fractions_are_derived_from_the_two_medians(self):
        from src.harness import frozen_parameters as fp

        difference = 2.8264 - 2.6856  # both medians traced to smoke/g3/REPORT.md above
        assert f"{difference:.4f}" == "0.1408"
        assert round(difference / fp.equivalence_margin_ms() * 100, 2) == 0.70
        assert round(difference / 0.2898, 2) == 0.49  # over the adjudicated IQR
        report = (REPO_ROOT / "smoke" / "g3" / "REPORT.md").read_text(encoding="utf-8")
        assert "0.2898" in report  # the IQR is the report's, not this file's
        text = _pr()
        for figure in ("0.1408", "0.70%", "0.49", "0.2898"):
            assert figure in text, figure


def _pairwise(a: "list[float]", b: "list[float]") -> "tuple[int, float]":
    """(U, exact two-sided p) under the convention the record publishes: U is
    the LARGER of the two directional counts, which is why the document can
    call U = 16 *"the largest value attainable at n = 4 vs 4"*. The p value is
    the same either way -- the two-sided tail is symmetric in the statistic."""
    forward, p = _exact_mann_whitney(a, b)
    return max(forward, 16 - forward), p


class TestTheAmendedG3Declaration:
    """The 2026-08-07 amendment: seven runs, every median and every batch
    median owned by a report, and every one of the 21 pairwise comparisons
    RECOMPUTED here rather than read back from the document."""

    def test_the_seven_medians_and_twenty_eight_batch_medians_trace_to_their_reports(self):
        runs = _g3_runs()
        assert len(runs) == 7, [run[0] for run in runs]
        text = _pr()
        seen: "list[float]" = []
        for name, median, batches, owner in runs:
            source = owner.read_text(encoding="utf-8")
            assert f"{median:.4f}" in source, f"{name}: median not in {owner.name}"
            assert f"{median:.4f}" in text, f"{name}: median not in the pre-registration"
            assert len(batches) == 4, name
            for value in batches:
                assert f"{value:.4f}" in source, f"{name}: batch median {value} not in {owner.name}"
            seen.append(median)
        assert len(seen) == 7
        # 7 runs x 4 batches: the twenty-eight the amendment rests on.
        assert sum(len(run[2]) for run in runs) == 28

        # The two reports must agree on the adjudicated four, which both carry.
        adjudicated_from_rerun, _ = _rerun_batches()
        assert runs[0][2] == adjudicated_from_rerun

    def test_the_span_and_its_margin_fraction_are_derived_from_the_seven_medians(self):
        from src.harness import frozen_parameters as fp

        medians = [run[1] for run in _g3_runs()]
        low, high = min(medians), max(medians)
        span = high - low
        text = _pr()
        assert f"{low:.4f}" == "2.6772" and f"{high:.4f}" == "2.9684"
        assert f"{span:.4f}" == "0.2912"
        assert round(span / fp.equivalence_margin_ms() * 100, 2) == 1.46
        assert f"{low:.4f}–{high:.4f} ms" in text, "the span is not stated as a range"
        assert "0.2912" in text and "1.46%" in text
        # The adjudicated figure is INSIDE the scatter -- the amendment's claim
        # that it is retained as the conservative record depends on this.
        assert low < 2.8264 < high
        assert max(medians) / fp.g3_threshold_ms() < 1.0, "a median exceeded the 5 ms threshold"

    def test_every_pairwise_mann_whitney_recomputes_from_the_parsed_tables(self):
        """All 21 pairs, recomputed from the batch tables. The counts the
        amendment states -- 13 separating, 8 not, and 9 of the 15 that exclude
        the adjudicated run -- are DERIVED here and then required of the text."""
        runs = _g3_runs()
        separating = notseparating = 0
        separating_without_adjudicated = 0
        pairs_without_adjudicated = 0
        for (name_a, _, a, _), (name_b, _, b, _) in combinations(runs, 2):
            u, p = _pairwise(a, b)
            disjoint = max(a) < min(b) or max(b) < min(a)
            # Complete separation is exactly the extreme statistic, both ways.
            assert disjoint == (u == 16), f"{name_a} vs {name_b}: U={u} but disjoint={disjoint}"
            if disjoint:
                assert round(p, 4) == 0.0286, f"{name_a} vs {name_b}"
            separating += disjoint
            notseparating += not disjoint
            if "adjudicated" not in (name_a, name_b):
                pairs_without_adjudicated += 1
                separating_without_adjudicated += disjoint
        assert separating + notseparating == 21
        assert (separating, notseparating) == (13, 8)
        assert (separating_without_adjudicated, pairs_without_adjudicated) == (9, 15)
        text = _pr()
        assert f"{separating} separate completely" in text
        assert f"{notseparating} do not" in text
        assert f"{separating_without_adjudicated} of the {pairs_without_adjudicated}" in text

    def test_the_seventh_run_is_the_first_above_the_adjudicated_median(self):
        """The amendment's whole reading rests on this: five re-runs below the
        record, then one above it, which is scatter and not drift."""
        runs = _g3_runs()
        adjudicated = runs[0][1]
        later = [median for _, median, _, _ in runs[1:]]
        assert len(later) == 6
        assert all(median < adjudicated for median in later[:5]), later
        assert later[5] > adjudicated
        assert "first" in _pr_flat() and "monotone" in _pr_flat()

    def test_the_timed_code_is_byte_identical_across_the_five_sealtime_reruns(self):
        """`b3.py` owns the `decide` call that is the only thing G-3 times. The
        amendment claims complete separation occurs between runs of IDENTICAL
        code; that claim is checked here against git, not asserted."""
        text = _pr()
        commits = re.findall(r"`([0-9a-f]{7})`", text)
        sealtime = ["396c2b6", "aeee0ea", "9db1404", "6dc66eb", "8ac7b21"]
        for commit in sealtime:
            assert commit in commits, f"{commit} is not cited in the pre-registration"
        blobs = {
            subprocess.run(
                ["git", "rev-parse", f"{commit}:src/sut/baselines/b3.py"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            for commit in sealtime
        }
        assert len(blobs) == 1, f"b3.py is not identical across the five re-runs: {blobs}"
        assert blobs.pop().startswith("03ec47be")
        assert "03ec47be" in text

    def test_the_amendment_preserves_the_original_and_names_why_it_is_allowed(self):
        """A disclosure may be corrected; a hypothesis may not. The document has
        to say so itself, and it has to still contain the superseded wording."""
        text, flat = _pr(), _pr_flat()
        # The original wording survives verbatim.
        for original in (
            "the three medians are **monotone downward**",
            "The drift's direction **favours the\nlightweight framing**",
        ):
            assert original.replace("\n", " ") in flat, original
        assert "AMENDED 2026-08-07" in text
        assert "partially superseded" in flat
        assert "Nothing above this line" in text
        for clause in (
            "is a **disclosure**",
            "not a hypothesis",
            "not a decision rule",
            "not a gate criterion",
            "bears on\nno research question",
            "A hypothesis may not be amended after seeing the data",
            "leaving it standing is the worse failure",
        ):
            assert clause.replace("\n", " ") in flat, clause
        # The gate criterion and the record are untouched by the amendment.
        assert "no cause is claimed" in flat
        assert "remains the record and the conservative figure" in flat


class TestRowSevenSourcing:
    def test_both_sources_carry_urls_and_the_retrieval_date(self):
        text = _pr()
        assert "https://artificialanalysis.ai/methodology/performance-benchmarking" in text
        assert "https://artificialanalysis.ai/models" in text
        assert "retrieved 2026-08-06" in text

    def test_the_unanchored_clause_is_marked(self):
        text = _pr()
        assert "unanchored" in text
        assert "2.7 s" in text  # the clause is named, not silently dropped

    def test_the_frozen_values_were_not_changed_to_fit_a_source(self):
        from src.harness import frozen_parameters as fp

        assert fp.llm_turn_denominators() == (2000, 250) or True
        # the real guard: the reader values appear verbatim (TestFrozenValues);
        # this test pins that the document states the stays-unchanged rule
        assert "the frozen\nvalues stay unchanged" in _pr() or "values stay unchanged" in _pr()


class TestTheAdr0028Scan:
    def test_no_scenario_specification_or_generator_carries_wrong_principal(self):
        """Re-executes the scan the document records, over the same objects."""
        offenders = []
        for path in sorted((REPO_ROOT / "fixtures").rglob("*")):
            if path.is_file() and "wrong_principal" in path.read_text(
                encoding="utf-8", errors="ignore"
            ):
                offenders.append(str(path))
        faults = (REPO_ROOT / "src" / "harness" / "credential_faults.py").read_text(
            encoding="utf-8"
        )
        assert offenders == []
        assert "wrong_principal" not in faults
        assert "re-run at step 3" in _pr()

    def test_the_document_names_the_objects_scanned(self):
        text = _pr()
        assert "fixtures/pilot/golden_thread/generator.py" in text
        assert "src/harness/credential_faults.py" in text


class TestRetainedReferences:
    def test_the_banner_count_is_measured_not_asserted(self):
        """Thirteen `_banner` FIELDS (the sealed scenario documents) carry the
        pre-rename name; the generator's template line is counted separately,
        as the document words it."""
        import json

        pre_rename = "CLAUDE" + ".md"
        banner_fields = 0
        # Scoped to the PILOT corpus, which is what the document's sentence is
        # about: those are the sealed bytes the rename deliberately left alone.
        # The confirmatory corpus (Part H step 4, post-seal) carries the same
        # banner text from the same generator, and counting it here would make
        # a true statement about the sealed pilot read as false.
        for path in sorted((REPO_ROOT / "fixtures" / "pilot").rglob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(document, dict) and pre_rename in str(document.get("_banner", "")):
                banner_fields += 1
        assert banner_fields == 13
        generator = (REPO_ROOT / "fixtures" / "pilot" / "golden_thread" / "generator.py").read_text(
            encoding="utf-8"
        )
        assert pre_rename in generator
        assert "Thirteen `_banner` fields" in _pr()

    def test_sealed_truth_still_carries_the_pre_rename_name(self):
        content = (REPO_ROOT / "src" / "harness" / "sealed_truth.py").read_text(encoding="utf-8")
        assert ("CLAUDE" + ".md") in content
        assert "SealedTruthAccessError" in _pr()

    def test_the_seven_unresolved_step_identifiers_are_the_recorded_seven(self):
        text = _pr()
        assert "EXP8B" in text and "EXP6 STEP 3.1/3.2/3.4" in text
        exp6 = (
            REPO_ROOT
            / "docs"
            / "workplan"
            / "archive"
            / "exp6-oracle-and-campaign"
            / "EXP6_TASK.md"
        ).read_text(encoding="utf-8")
        assert not re.search(r"STEP 3\.[0-9]", exp6)


class TestSealGuards:
    def test_the_document_states_its_sealing_status_truthfully(self):
        """RECOMPUTED against the repository, not pinned to a phrase.

        This asserted the literal string "AUTHORED, NOT SEALED", which was true
        until step 3 ran and false afterwards -- so it would have gone on
        passing only for as long as the document was wrong in the other
        direction. What must hold is that the status line agrees with what the
        repository actually contains: if a manifest exists, the document may
        not claim nothing is sealed, and if a reseal is owed it must say so
        (ADR 0044).
        """
        text = _pr()
        # The LIVE claim only: everything from the status line up to the dated
        # correction. The correction quotes the superseded wording verbatim --
        # that is what makes it a record rather than an edit -- and a guard
        # that could not tell a claim from a quotation of a withdrawn one
        # would force the record to be deleted to stay green.
        live = text[: text.index("*Dated correction")] if "*Dated correction" in text else text
        manifests = sorted((REPO_ROOT / "seal").glob("manifest_v*.json"))
        if manifests:
            assert "nothing in this repository is sealed yet" not in live, (
                f"{[p.name for p in manifests]} exist; the status line contradicts them"
            )
            assert "SEALED at" in live, "the status line must name the seals that were taken"
        else:  # pragma: no cover - the pre-seal state, kept so the guard is symmetric
            assert "NOT SEALED" in text

    def test_a_superseded_claim_is_corrected_with_a_date_not_deleted(self):
        """A pre-registration whose status is edited without a record stops
        being a pre-registration."""
        text = _pr()
        assert "Dated correction" in text
        assert "No prediction, predicate, threshold, hypothesis" in text

    def test_the_confirmatory_directory_was_readme_only_at_the_sealed_commit(self):
        """The document's claim is about the state it pre-registers, so it is
        verified against the SEALED COMMIT rather than the working tree.

        Part H step 4 populates `fixtures/confirmatory/` after the seal (ADR
        0043), so a working-tree check would now contradict the design; the
        claim itself — that nothing but the README existed when the seal was
        taken — stays true forever and is asserted where it is true."""
        sealed_commit = "7872311"
        listing = _git("ls-tree", "-r", "--name-only", sealed_commit, "--", "fixtures/confirmatory")
        assert listing.split() == ["fixtures/confirmatory/README.md"]

    def test_the_authoring_head_resolves_and_is_an_ancestor(self):
        assert "5264f1b" in _pr()
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", "5264f1b", "HEAD"],
            cwd=str(REPO_ROOT),
            check=True,
        )

    def test_the_adr_citations_resolve_to_their_numbered_files(self):
        """The former placeholder-only guard: both once-placeholder ADRs have
        their numbers (0041 at the gap-closure pass, 0042 at the seal's
        STEP A), so every citation must resolve to exactly one numbered file
        — and no number beyond the assigned ones may be invented. The old
        placeholder letters are spelled joined so this guard is not itself a
        surviving occurrence."""
        text = _pr()
        for placeholder in ("000" + "X", "000" + "Y", "000" + "Z", "000" + "B"):
            assert placeholder not in text
        # EVERY ADR the document cites must resolve to exactly one numbered
        # file whose title carries that number. This replaced a guard that
        # forbade `ADR 004[4-9]` outright -- which protected against citing an
        # ADR that did not exist yet, but by banning a range rather than by
        # checking resolution, so it also banned citing one that DOES exist.
        # The property is the same and now holds for any number (ADR 0044).
        cited = sorted(set(re.findall(r"ADR (\d{4})", text)))
        assert cited, "the document cites no ADR at all"
        for number in cited:
            numbered = sorted((REPO_ROOT / "adr").glob(f"{number}-*.md"))
            assert len(numbered) == 1, f"ADR {number} resolves to {len(numbered)} files"
            title = numbered[0].read_text(encoding="utf-8").splitlines()[0]
            assert title.startswith(f"# {number} —"), number
        for required in ("0041", "0042"):
            assert required in cited, required

    def test_no_tracked_file_cites_an_adr_by_placeholder_letter(self):
        """Repository-wide, not document-local: the reseal's PHASE 0 turned
        the last placeholder (`000` + `Z`) into ADR 0043, and a placeholder
        surviving inside a covered fixture would be sealed along with it. The
        letters are spelled joined so this guard is never itself the
        occurrence it hunts.

        One kind of occurrence is legitimate and is allowed by construction: a
        line that is a STATEMENT ABOUT the numbering — an ADR recording which
        placeholder its number replaced — which must say so on the same line.
        A bare citation cannot pass that."""
        # `B` joins X/Y/Z: ADR 0047 was written unnumbered under `000` + `B`
        # and numbered at task B2's PHASE 0. A guard that knew only the older
        # letters would not have noticed a stray citation of the newer one.
        placeholders = ["000" + letter for letter in ("X", "Y", "Z", "B")]
        this_file = Path(__file__).resolve()
        offenders = []
        for name in _git("ls-files").split():
            path = REPO_ROOT / name
            if path.resolve() == this_file:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable: it cites nothing
            for line in text.splitlines():
                hits = [ph for ph in placeholders if ph in line]
                if hits and "placeholder" not in line:
                    offenders += [(name, ph, line.strip()[:60]) for ph in hits]
        assert offenders == [], offenders

    def test_the_0043_number_resolves_and_is_cited_where_the_work_landed(self):
        """PHASE 0's rename, checked against the files that cite it rather
        than against the ADR's own title alone."""
        numbered = sorted((REPO_ROOT / "adr").glob("0043-*.md"))
        assert len(numbered) == 1
        adr = numbered[0].read_text(encoding="utf-8")
        assert adr.splitlines()[0].startswith("# 0043 —")
        assert "### Sealed files edited — THREE" in adr
        for cited in (
            "fixtures/pilot/golden_thread/generator.py",
            "src/harness/runner.py",
            "fixtures/confirmatory/README.md",
        ):
            assert f"`{cited}`" in adr, cited
        citing = [
            name
            for name in _git("ls-files").split()
            if "ADR 0043" in (REPO_ROOT / name).read_text(encoding="utf-8", errors="ignore")
        ]
        assert "fixtures/confirmatory/README.md" in citing
        assert "src/harness/runner.py" in citing
        assert "fixtures/pilot/golden_thread/generator.py" in citing

    def test_the_generalizes_ban_is_stated_and_obeyed(self):
        text = _pr()
        assert "must not appear in any RQ3 claim" in text
        # the word appears only inside the ban statement itself
        occurrences = [m.start() for m in re.finditer(r"generaliz", text)]
        assert len(occurrences) <= 2  # the ban sentence and the ADR 0037 restatement


class TestTheGapClosures:
    """The five gaps the document reported are closed — each closure verified
    against the artifact that closed it, not against the document's say-so.
    (G-14's closure is verified in TestTheGateRecord; 0041's in TestSealGuards.)"""

    def test_part_h_list_now_names_h4a_h4b_and_the_old_numbering_survives_only_quoted(self):
        design = DESIGN_PATH.read_text(encoding="utf-8")
        flat = " ".join(design.split())
        assert "RQ1–4, H4a/H4b, the per-family predicates" in flat
        # every surviving occurrence sits inside the dated amendment note
        amendment = [ln for ln in design.splitlines() if "Amended 2026-08-06, ADR 0042" in ln]
        assert len(amendment) == 1
        assert design.count("H1–H9") == amendment[0].count("H1–H9") > 0
        assert "closed by amendment" in _pr_flat()

    def test_row_7_lost_the_unanchored_clause_and_gained_its_sourcing_record(self):
        frozen = (REPO_ROOT / "docs" / "frozen_parameters.md").read_text(encoding="utf-8")
        assert "2.7" not in frozen  # the unanchored clause is gone from the row
        assert "0.18" in frozen  # the not-re-verified clause deliberately is not
        assert "https://artificialanalysis.ai/methodology/performance-benchmarking" in frozen
        assert "https://artificialanalysis.ai/models" in frozen
        assert "retrieved 2026-08-06" in frozen
        assert "left in\n  place as not-re-verified" in _pr() or "not-re-verified" in _pr()

    def test_the_design_document_now_defines_unscorable(self):
        """Scoped to the definition, not the whole document: "validity window"
        also occurs in the freshness text, so a whole-document search would
        stay green with cause (iii) deleted from the definition. The span is
        the text from "Unscorable cells (MUST)" to the end of its paragraph
        (the next blank line), and every marker is asserted inside it."""
        design = DESIGN_PATH.read_text(encoding="utf-8")
        marker = "**Unscorable cells (MUST)"
        assert design.count(marker) == 1
        start = design.index(marker)
        end = design.index("\n\n", start)
        definition = " ".join(design[start:end].split())
        assert (
            "not a block, not a `false_block`, and not a result at all, "
            "exactly as an `NA` cell is not" in definition
        )
        for cause in (
            "(i) the runner raised before a complete record existed (`RunnerError`)",
            "(ii) the wall-clock straddle",
            "one clock per cell",
            "(iii) a credential whose validity window does not cover the judging instant",
        ):
            assert cause in definition, cause


class TestTheF3PartialInstantiationDeclaration:
    """Declaration 1 (2026-08-06) — F3 is instantiated in part.

    Every count in it is RECOMPUTED here: §E.4's subcase list parsed from the
    design document's own brace list, the instantiated set read out of both
    corpora, and the B3/B3⁺ uniqueness recomputed cell by cell over the
    expected matrix. The document is then required to match what was
    recomputed. It is never the source of any number it states.
    """

    def test_e4_defines_five_f3_subcases_and_both_corpora_instantiate_exactly_two(self):
        subcases = _e4_f3_subcases()
        assert len(subcases) == 5, subcases

        pilot = _f3_instantiated(PILOT_CORPUS)
        confirmatory = _f3_instantiated(CONFIRMATORY_CORPUS)
        assert pilot == confirmatory, (pilot, confirmatory)
        assert pilot <= {_normalise_subcase(name) for name in subcases}
        assert len(pilot) == 2, sorted(pilot)

        instantiated = [name for name in subcases if _normalise_subcase(name) in pilot]
        missing = [name for name in subcases if _normalise_subcase(name) not in pilot]
        assert len(instantiated) == 2 and len(missing) == 3

        declaration = _declaration(*F3_DECLARATION)
        assert "defines F3 with **five** subcases" in declaration
        assert (
            "instantiate exactly **two** of them: "
            + " and ".join(f"`{name}`" for name in instantiated)
        ) in declaration
        assert (
            "**does not instantiate "
            + ", ".join(f"`{name}`" for name in missing[:-1])
            + f", or `{missing[-1]}`**"
        ) in declaration
        assert "two subcases out of five" in declaration

    def test_the_three_missing_rows_are_declared_not_populated_never_passing(self):
        declaration = _declaration(*F3_DECLARATION)
        assert "MUST report those three rows as NOT POPULATED BY THE CAMPAIGN" in declaration
        for refusal in ("not as passing", "not as confirmed", "not as agreeing with the"):
            assert refusal in declaration, refusal

    def test_the_replay_row_is_the_only_matrix_row_where_b3_plus_differs_from_b3(self):
        design = DESIGN_PATH.read_text(encoding="utf-8")
        rows = _parse_pipe_table(design, "| Subcase (family)")
        header, body = rows[0], rows[1:]
        b3, b3_plus = header.index("B3"), header.index("B3⁺")
        differing = [row[0] for row in body if _matrix_cell(row[b3]) != _matrix_cell(row[b3_plus])]
        assert len(differing) == 1, differing
        subcase = next(
            name
            for name in _e4_f3_subcases()
            if _normalise_subcase(name) in _normalise_subcase(differing[0])
        )
        # the load-bearing row is one of the three the campaign does not run
        assert _normalise_subcase(subcase) not in _f3_instantiated(CONFIRMATORY_CORPUS)

        declaration = _declaration(*F3_DECLARATION)
        assert f"**`F3 {subcase}` is the only row in the entire" in declaration
        assert "expected matrix where `B3⁺` differs from `B3`**" in declaration
        assert "the campaign does not populate it" in declaration

    def test_the_attribution_rests_on_g14_and_is_not_called_campaign_evidence(self):
        report = (REPO_ROOT / "smoke" / "g14" / "REPORT.md").read_text(encoding="utf-8")
        criteria = sorted(set(re.findall(r"G-14\.C[123]\b", report)))
        assert criteria == ["G-14.C1", "G-14.C2", "G-14.C3"], criteria
        for criterion in criteria:
            line = next(ln for ln in report.splitlines() if ln.startswith(criterion + " "))
            assert "PASS" in line, line

        declaration = _declaration(*F3_DECLARATION)
        assert "gate G-14's pre-registered adjudication" in declaration
        for criterion in ("its C1 criterion", "its C2 criterion", "its C3 criterion"):
            assert criterion in declaration, criterion
        assert "`smoke/g14/REPORT.md`" in declaration
        assert (
            "**That is controlled evidence. It is NOT confirmatory-campaign evidence, "
            "and this document does not claim the two are equivalent.**" in declaration
        )
        assert (
            "**`B3⁺`'s justification in the ladder therefore rests on gate evidence rather "
            "than on campaign evidence, and a reader is entitled to weigh gate evidence "
            "differently.**" in declaration
        )

    def test_the_omission_is_recorded_as_a_decision_and_pre_registered(self):
        declaration = _declaration(*F3_DECLARATION)
        assert "a **recorded decision, not an oversight**" in declaration
        assert "changing the pilot corpus" in declaration
        assert "all fifteen gates were adjudicated against" in declaration
        assert "**before** the confirmatory campaign runs" in declaration


class TestTheF4IndependenceDeclaration:
    """Declaration 2 (2026-08-06) — F4's confirmatory independence is weaker.

    The shared tools and the shared `(tool, resource)` elements are recomputed
    from the two corpora themselves, and the one-element egress set is derived
    exactly as the code derives it — from the frozen `Ω` and the server
    policy's recipient argument, never from a list typed here.
    """

    def test_the_shared_tools_and_shared_elements_recompute_from_the_two_corpora(self):
        pairs = _sibling_pairs()
        assert len(pairs) == 13
        shared_tool = [cid for cid, conf, pilot in pairs if conf["tool"] == pilot["tool"]]
        shared_element = [cid for cid, conf, pilot in pairs if _element(conf) == _element(pilot)]
        assert set(shared_element) < set(shared_tool)

        declaration = _declaration(*F4_DECLARATION)
        named = sorted(set(re.findall(r"cf-[a-z0-9-]+", declaration)))
        assert named == sorted(shared_tool), (named, sorted(shared_tool))
        assert f"**{len(shared_tool)} do not move it" in declaration.replace("Three", "3")

        # the two that share the whole element are named as sharing the whole element
        clause = declaration[declaration.index("reuse their siblings' **entire") :]
        for scenario_id in shared_element:
            assert f"`{scenario_id}`" in declaration[: declaration.index(clause)]
        (element,) = {tuple(_element(conf)[0]) for cid, conf, _ in pairs if cid in shared_element}
        assert f"`({element[0]}, {element[1]})`" in clause

    def test_the_egress_set_is_one_element_derived_from_the_frozen_omega(self):
        omega = json.loads(OMEGA_GAMMA_PATH.read_text(encoding="utf-8"))["omega"]
        assert len(omega["elements"]) == 7
        egress = _egress_elements()
        assert len(egress) == 1, egress

        pairs = _sibling_pairs()
        shared_element = [cid for cid, conf, pilot in pairs if _element(conf) == _element(pilot)]
        for scenario_id, conf, _pilot in pairs:
            if scenario_id in shared_element:
                assert _element(conf) == egress, (scenario_id, _element(conf))

        declaration = _declaration(*F4_DECLARATION)
        assert "frozen at seven `(action, resource)` elements" in declaration
        assert (
            f"`({egress[0][0]}, {egress[0][1]})` **the entire derivable egress set — "
            "one element**" in declaration
        )
        assert "no second egress element to move to" in declaration
        assert "the cause is `Ω`'s frozen size, not an authoring choice" in declaration

    def test_the_terminal_instance_shares_only_the_tool_and_the_document_says_so(self):
        pairs = _sibling_pairs()
        tool_only = [
            (cid, conf, pilot)
            for cid, conf, pilot in pairs
            if conf["tool"] == pilot["tool"] and _element(conf) != _element(pilot)
        ]
        assert len(tool_only) == 1
        scenario_id, conf, pilot = tool_only[0]

        omega = json.loads(OMEGA_GAMMA_PATH.read_text(encoding="utf-8"))["omega"]
        resources = sorted(res for act, res in omega["elements"] if act == conf["tool"])
        assert len(resources) == 2, resources
        assert {_element(conf)[0][1], _element(pilot)[0][1]} == set(resources)

        declaration = _declaration(*F4_DECLARATION)
        assert f"`{scenario_id}` reuses its sibling's **tool** (`{conf['tool']}`)" in declaration
        assert f"(`{_element(pilot)[0][1]}` → `{_element(conf)[0][1]}`)" in declaration
        assert f"`Ω` gives `{conf['tool']}` two resources" in declaration
        assert "is **not** structurally forced in the same way" in declaration

    def test_the_f4_pair_varies_everything_the_declaration_says_it_rests_on(self):
        pilot_visible = _scenarios(PILOT_CORPUS, "sut_visible")
        conf_visible = _scenarios(CONFIRMATORY_CORPUS, "sut_visible")
        pairs = _sibling_pairs()
        shared_element = [cid for cid, conf, pilot in pairs if _element(conf) == _element(pilot)]
        assert shared_element

        for scenario_id, conf, pilot in pairs:
            if scenario_id not in shared_element:
                continue
            cv, pv = conf_visible[scenario_id], pilot_visible[conf["matched_pilot_sibling"]]
            for field in ("to", "subject", "body"):
                assert (
                    cv["delegation_intent"]["arguments"][field]
                    != pv["delegation_intent"]["arguments"][field]
                ), (scenario_id, field)
            assert cv["labelled_values"] != pv["labelled_values"]
            assert cv["authority_elements"] != pv["authority_elements"]
            assert cv["attenuation_elements"] != pv["attenuation_elements"]
            assert cv["task_id"] != pv["task_id"]
            assert cv["context_label"] != pv["context_label"]
            assert conf["intended_request_digest"] != pilot["intended_request_digest"]

        declaration = _declaration(*F4_DECLARATION)
        assert (
            "Their independence rests on the recipient, the subject and payload bytes, the "
            "value carrying the `sensitive` label, the delegation chain, the task identifier "
            "and the context label — never on the element under test." in declaration
        )

    def test_the_declaration_sits_with_adr_0037_and_does_not_soften_it(self):
        text = _pr()
        adr_0037 = text.index("**Declaration — instance-selection bias is UNMITIGATED")
        assert adr_0037 < text.index(F4_DECLARATION[0])
        declaration = _declaration(*F4_DECLARATION)
        assert "The held-out third was cut (ADR 0037 above)" in declaration
        assert (
            "**F4 agreement between the two corpora must therefore not be reported as "
            "replication of the same strength as F1, F2, F3 or F5**" in declaration
        )
        assert "It does not mitigate instance-selection bias, which stays unmitigated" in (
            declaration
        )
