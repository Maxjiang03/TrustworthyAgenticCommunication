"""INDEPENDENT recomputation of every number the results artefacts render.

Written for the fresh-clone verification pass. It imports NOTHING from
tools/figures/ and nothing from analysis/ -- it reads the two committed JSONs
and derives each quantity from the pre-registered rules as stated in prose, so
that agreement with the artefacts is evidence rather than tautology.

Inputs (the only two):
  results/raw/campaign-confirmatory.json
  results/tables/results-confirmatory.json
plus, for the row-1 numbers:
  results/tables/results-latency-pilot.json          (run 1)
  results/tables/results-latency-pilot-run2.json     (run 2)
  results/raw/latency-pilot.json                     (the samples)

Every derived value is printed as `CHECK <key> = <value>`, in the same shape the
artefacts print `RENDER`, so the two streams can be diffed mechanically.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAMPAIGN = json.loads((ROOT / "results/raw/campaign-confirmatory.json").read_text(encoding="utf-8"))
TABLES = json.loads((ROOT / "results/tables/results-confirmatory.json").read_text(encoding="utf-8"))

ARMS = (
    "B0",
    "B1",
    "B2-broad-noexchange",
    "B2-exchange-broad",
    "B2-exchange-task",
    "B2-exchange-task-DPoP",
    "B-cap",
    "B3",
    "B3+",
)

fail = []


def check(key, got, want=None):
    print(f"CHECK {key} = {got}")
    if want is not None and got != want:
        fail.append(f"{key}: recomputed {got!r} but the sealed record says {want!r}")


# ---------------------------------------------------------------------------
# 1. the cell ladder: 153 run -> 143 scored + 10 unscorable
# ---------------------------------------------------------------------------
cells = CAMPAIGN["cells"]
unscorable = CAMPAIGN["unscorable"]
check("ladder.cells_scored", len(cells), TABLES["cells_scored"])
check("ladder.unscorable", len(unscorable), len(TABLES["unscorable"]))
check("ladder.cells_run", len(cells) + len(unscorable))

# every unscorable cell must be an E.4 NA cell (the plan's claim)
causes = Counter(u[2] for u in unscorable)  # [scenario_id, arm, cause]
check("ladder.unscorable_causes", dict(causes))

# ---------------------------------------------------------------------------
# 2. the 90-ENTRY agreement under the footnote-dagger rule
#    An E.4 entry is one (predicted row, arm). A daggered expectation is scored
#    against the monitor-OFF cell only; an undaggered F4/F5 expectation must
#    hold under BOTH configurations.
# ---------------------------------------------------------------------------
predicted = [r for r in TABLES["expected_matrix"] if r["state"] == "predicted"]
check("entries.predicted_rows", len(predicted))
check("entries.total", len(predicted) * len(ARMS))

# index the raw cells by (subcase, arm, monitor_attached)
by_key = defaultdict(list)
for c in cells:
    by_key[(c["subcase"], c["arm"])].append(c)


def observed_letter(cell):
    """B iff the boundary refused to forward; A otherwise. `false_block` marks
    an A-expected cell that was refused, which is still a refusal (B-shaped
    behaviour) but on a benign control -- controls carry no E.4 expectation, so
    this function is only ever applied to attack rows."""
    return "A" if cell["observed_forwarded"] else "B"


# Map an expected-matrix subcase LABEL (prose, e.g. "F1-root (R not-subset
# U_task)") to the corpus subcase TOKEN (structured, e.g. "F1:root"). The sealed
# analysis/matrix.py has a hand-written table for this; deriving it here instead
# is the point -- the mapping must be reconstructible from the two JSONs alone,
# or the artefacts rest on a table nobody can check.
#
# Rule, using only family structure and the strings themselves:
#   (a) group both sides by family;
#   (b) if a family has exactly one predicted row and one attack subcase, they
#       correspond -- no string comparison can be needed or wrong;
#   (c) otherwise match on a normalised distinctive token.
def norm(text):
    """Atomic words, both sides split identically.

    The first attempt merged "F1-root" into one token while splitting "F1:root"
    into two, so nothing in F1 could ever match; and it left F3's two rows tied
    at one shared word, so both grabbed the same token. Split on EVERY
    non-alphanumeric and compare word sets.
    """
    return {w for w in "".join(ch if ch.isalnum() else " " for ch in text.lower()).split() if w}


attack_subcases = sorted(
    {c["subcase"] for c in cells if c["subcase"] and not c["subcase"].startswith("benign:")}
)
by_fam_rows = defaultdict(list)
for row in predicted:
    by_fam_rows[row["family"]].append(row["subcase"])
by_fam_tok = defaultdict(list)
for tok in attack_subcases:
    by_fam_tok[tok.split(":")[0]].append(tok)

row_token = {}
for fam, labels in by_fam_rows.items():
    toks = list(by_fam_tok.get(fam, []))
    if len(labels) == 1 and len(toks) == 1:
        row_token[labels[0]] = toks[0]  # unique in its family; no string test needed
        continue
    # Rank every (label, token) pair by shared words and assign greedily with
    # BOTH sides consumed, so one token cannot be claimed twice.
    pairs = sorted(
        ((len(norm(lb) & norm(tk)), lb, tk) for lb in labels for tk in toks), reverse=True
    )
    taken_l, taken_t = set(), set()
    for score, lb, tk in pairs:
        if score == 0 or lb in taken_l or tk in taken_t:
            continue
        row_token[lb] = tk
        taken_l.add(lb)
        taken_t.add(tk)
    for lb in labels:
        row_token.setdefault(lb, None)
check("mapping.rows_mapped", sum(1 for v in row_token.values() if v))
check("mapping.rows_unmapped", sum(1 for v in row_token.values() if not v))
check("mapping.is_injective", len({v for v in row_token.values() if v}) == len(predicted), True)
for label in sorted(row_token):
    check(f"mapping.{label}", row_token[label])

agreed = disagreed = na_entries = 0
unresolved = []
for row in predicted:
    token = row_token[row["subcase"]]
    for arm in ARMS:
        exp = row["cells"].get(arm)
        if exp == "NA":
            na_entries += 1
            continue
        daggered = isinstance(exp, str) and exp.endswith("†")
        want = exp.rstrip("†") if isinstance(exp, str) else exp
        pool = by_key.get((token, arm), [])
        if not pool:
            unresolved.append((row["subcase"], arm))
            continue
        if daggered:
            scored = [c for c in pool if c["monitor_attached"] is not True]
        else:
            scored = pool  # every configuration must hold
        if not scored:
            unresolved.append((row["subcase"], arm))
            continue
        if all(observed_letter(c) == want for c in scored):
            agreed += 1
        else:
            disagreed += 1

check("entries.agreed", agreed, TABLES["agreement"]["agreed"])
check("entries.disagreed", disagreed, len(TABLES["agreement"]["disagreed"]))
check("entries.na", na_entries, len(TABLES["agreement"]["unmeasured"]))
check("entries.unresolved", len(unresolved))
if unresolved:
    for u in unresolved[:10]:
        print(f"   unresolved: {u}")
check("entries.sum", agreed + disagreed + na_entries)

check("rows.not_populated", len(TABLES["agreement"]["not_populated"]))
check("rows.deferred", len(TABLES["agreement"]["deferred"]))

# ---------------------------------------------------------------------------
# 3. the display partition of the 143 scored CELLS
# ---------------------------------------------------------------------------
dagger_rows = {}
for row in predicted:
    token = row_token[row["subcase"]]
    dagger_rows[token] = {
        arm
        for arm in ARMS
        if isinstance(row["cells"].get(arm), str) and row["cells"][arm].endswith("†")
    }

groups = Counter()
for c in cells:
    sub = c["subcase"] or ""
    if sub == "benign:golden-thread":
        groups["benign_golden_thread"] += 1
    elif sub.startswith("benign:"):
        groups["f45_benign_controls"] += 1
    elif c["arm"] in dagger_rows.get(sub, set()) and c["monitor_attached"] is True:
        groups["dagger_true_complement"] += 1
    else:
        groups["agreement_consumed"] += 1
for k in (
    "agreement_consumed",
    "benign_golden_thread",
    "f45_benign_controls",
    "dagger_true_complement",
):
    check(f"partition.{k}", groups[k])
check("partition.total", sum(groups.values()), len(cells))

# ---------------------------------------------------------------------------
# 4. per-arm scored counts, false_block cells, B3/B3+ pairs, dagger census
# ---------------------------------------------------------------------------
per_arm = Counter(c["arm"] for c in cells)
for arm in ARMS:
    check(f"per_arm_scored.{arm}", per_arm[arm])

fb = [c for c in cells if c["false_block"]]
check("false_block.count", len(fb))
for c in sorted(fb, key=lambda x: (x["subcase"], x["arm"])):
    check(
        f"false_block.cell.{c['scenario_id']}.{c['arm']}",
        f"monitor_attached={c['monitor_attached']} reason={c['reason_code_FOR_DIAGNOSIS_ONLY']}",
    )

OUTCOME = (
    "admission_breach",
    "observed_forwarded",
    "false_block",
    "realized_harm",
    "log_integrity_failure",
    "reference_allow",
    "effect_count",
    "ledger_backed",
    "linkage",
)
b3 = {(c["scenario_id"], c["monitor_attached"]): c for c in cells if c["arm"] == "B3"}
b3p = {(c["scenario_id"], c["monitor_attached"]): c for c in cells if c["arm"] == "B3+"}
common = sorted(set(b3) & set(b3p))
diffs = [k for k in common if any(b3[k][f] != b3p[k][f] for f in OUTCOME)]
check("b3_vs_b3plus.comparable_pairs", len(common))
check("b3_vs_b3plus.differing_pairs", len(diffs))

census = sum(len(v) for v in dagger_rows.values())
check("dagger.census_entries", census)
check("dagger.rows_with_daggers", sum(1 for v in dagger_rows.values() if v))

# ---------------------------------------------------------------------------
# 5. class_macro and clustered_by_template, re-derived from the raw cells
# ---------------------------------------------------------------------------
QUANT = (
    "admission_breach",
    "false_block",
    "log_integrity_failure",
    "observed_forwarded",
    "realized_harm",
    "reference_allow",
)
by_family = defaultdict(list)
for c in cells:
    by_family[c["family"]].append(c)
for fam in sorted(by_family):
    check(f"class_macro.{fam}.total", len(by_family[fam]))
    for q in QUANT:
        got = sum(1 for c in by_family[fam] if c[q])
        sealed = TABLES["class_macro"].get(fam, {}).get("quantities", {}).get(q, {})
        check(f"class_macro.{fam}.{q}", got, sealed.get("count"))

tmpl = TABLES["clustered_by_template"]
check("clustered_by_template.templates", len(tmpl))

# ---------------------------------------------------------------------------
# 6. the row-1 decision artefacts
# ---------------------------------------------------------------------------
for label, name in (
    ("run1", "results-latency-pilot.json"),
    ("run2", "results-latency-pilot-run2.json"),
):
    p = ROOT / "results/tables" / name
    if not p.is_file():
        check(f"row1.{label}", "ABSENT")
        continue
    d = json.loads(p.read_text(encoding="utf-8"))["decision"]
    check(f"row1.{label}.verdict", d["verdict"])
    check(f"row1.{label}.n", d["treatment"]["n"])
    check(f"row1.{label}.ci_high", d["ci"]["high"])
    check(f"row1.{label}.margin", d["margin_ms"])
    check(f"row1.{label}.rule_holds", d["ci"]["high"] < d["margin_ms"], True)

plan = json.loads((ROOT / "results/raw/latency-pilot.json").read_text(encoding="utf-8"))["plan"]
check("row1.plan.recorded_per_configuration", plan["recorded_per_configuration"])
check("row1.plan.kept_after_warmup_per_configuration", plan["kept_after_warmup_per_configuration"])
check("row1.plan.warmup_per_batch", plan["warmup_per_batch"])
check("row1.plan.batches", plan["batches"])
check(
    "row1.warmup_arithmetic_closes",
    plan["recorded_per_configuration"] - plan["batches"] * plan["warmup_per_batch"]
    == plan["kept_after_warmup_per_configuration"],
    True,
)

print()
if fail:
    print(f"INDEPENDENT RECOMPUTATION: {len(fail)} MISMATCH(ES)")
    for f in fail:
        print("  !!", f)
    raise SystemExit(1)
print("INDEPENDENT RECOMPUTATION: every cross-checked value matches the sealed record")
