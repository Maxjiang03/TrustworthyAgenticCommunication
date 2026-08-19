"""Cross-check every latency number three ways.

A. INDEPENDENT (no sealed code): filter the raw samples by hand, drop the first
   five repetition indices of every (arm, scenario, phase, batch) group, take
   the median with the standard library and p25/p75/p95 with numpy's linear
   interpolation, and compare against the committed RQ4 artefact (run 2) and
   the committed row-1 artefact (run 2). If the sealed layer and a naive
   re-implementation agree to the last float, the artefact is what the data
   say.
B. SEALED RECOMPUTE: call the sealed span_descriptives and arm_pair_delta from
   the raw file with the plan block's parameters and compare every field of
   every record with the committed artefact. Deterministic seed => equality.
C. RENDERED vs ARTEFACT: run each figure script, parse its RENDER lines, and
   compare each printed value with the artefact field it claims to render.
D. TICKS: for every axes on the three figures, the tick label text must equal
   the tick position formatted; and a handful of data values must land, in
   axes fraction, where the axis type says they should.
"""

import json
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools" / "figures"))

raw = json.loads((REPO / "results/raw/latency-pilot.json").read_text(encoding="utf-8"))
rq4 = json.loads(
    (REPO / "results/tables/results-latency-pilot-rq4-run2.json").read_text(encoding="utf-8")
)
row1_r2 = json.loads(
    (REPO / "results/tables/results-latency-pilot-run2.json").read_text(encoding="utf-8")
)
row1_r1 = json.loads(
    (REPO / "results/tables/results-latency-pilot.json").read_text(encoding="utf-8")
)
plan = raw["plan"]
PER_BATCH = plan["warmup_per_batch"]
REFUSAL = "gt-f1-chain-tamper"

problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)


# ---------------------------------------------------------------- A. independent
def kept_values(arm, scenario, phase, span):
    rows = [
        s
        for s in raw["samples"]
        if s["arm"] == arm and s["scenario_id"] == scenario and s["phase"] == phase
    ]
    by_batch = {}
    for s in rows:
        by_batch.setdefault(s["batch"], set()).add(s["repetition"])
    drop = {b: sorted(reps)[:PER_BATCH] for b, reps in by_batch.items()}
    vals = [
        s["value_ms"] for s in rows if s["span"] == span and s["repetition"] not in drop[s["batch"]]
    ]
    return vals


def naive_desc(vals):
    v = np.array(sorted(vals))
    return dict(
        n=len(v),
        median=statistics.median(vals),
        p95=float(np.percentile(v, 95, method="linear")),
        iqr=float(np.percentile(v, 75, method="linear") - np.percentile(v, 25, method="linear")),
    )


print("A. INDEPENDENT recompute of all 180 span reports (no sealed code)")
mism = 0
for r in rq4["span_reports"]:
    scen = REFUSAL if r["series"] == "refusal_path" else "gt-benign"
    d = naive_desc(kept_values(r["arm"], scen, r["phase"], r["span"]))
    for k in ("n", "median", "p95", "iqr"):
        a, b = d[k], r["descriptives"][k]
        if not (a == b or math.isclose(a, b, rel_tol=0, abs_tol=1e-9)):
            mism += 1
            print(
                f"   MISMATCH {r['arm']} {r['phase']} {r['span']} {r['series']} {k}: "
                f"naive {a} vs artefact {b}"
            )
print(f"   180 reports x 4 fields compared; mismatches = {mism}")
check(mism == 0, "A: span_reports independent recompute mismatch")

print("A. INDEPENDENT recompute of the 70 delta point estimates and per-arm descriptives")
mism = 0
for d in rq4["arm_pair_deltas"]:
    t = kept_values(d["treatment_arm"], "gt-benign", d["phase"], d["span"])
    c = kept_values(d["control_arm"], "gt-benign", d["phase"], d["span"])
    pe = statistics.median(t) - statistics.median(c)
    if not math.isclose(pe, d["point_estimate_ms"], abs_tol=1e-9):
        mism += 1
        print(
            f"   MISMATCH point {d['treatment_arm']} {d['phase']} {d['span']}: "
            f"{pe} vs {d['point_estimate_ms']}"
        )
    for side, vals in (("treatment", t), ("control", c)):
        nd = naive_desc(vals)
        for k in ("n", "median", "p95", "iqr"):
            if not math.isclose(nd[k], d[side][k], abs_tol=1e-9):
                mism += 1
                print(
                    f"   MISMATCH {side}.{k} {d['treatment_arm']} {d['phase']} {d['span']}: "
                    f"{nd[k]} vs {d[side][k]}"
                )
    check(
        d["ci_low_ms"] <= d["point_estimate_ms"] <= d["ci_high_ms"],
        f"CI does not bracket point: {d['treatment_arm']} {d['phase']} {d['span']}",
    )
    check(d["control_arm"] == "B0", "control arm not B0")
    check(
        d["label"] == "composite-delta" and d["mechanism"] is None and d["unmodelled"] == [],
        "delta label/mechanism unexpected",
    )
    check(
        d["resamples"] == plan["bootstrap_resamples"] and d["confidence"] == 0.95,
        "delta resamples/confidence unexpected",
    )
print(f"   70 deltas: point estimates + 2x4 descriptives compared; mismatches = {mism}")
check(mism == 0, "A: arm_pair_deltas independent recompute mismatch")

print("A. INDEPENDENT recompute of the row-1 measured segment (run 2, warm-up discarded)")


def segment_vals(arm, drop_warmup):
    rows = [
        s
        for s in raw["samples"]
        if s["arm"] == arm and s["scenario_id"] == "gt-benign" and s["phase"] == "warm"
    ]
    by_batch = {}
    for s in rows:
        by_batch.setdefault(s["batch"], set()).add(s["repetition"])
    drop = {b: (sorted(reps)[:PER_BATCH] if drop_warmup else []) for b, reps in by_batch.items()}
    per_rep = {}
    for s in rows:
        if s["repetition"] in drop[s["batch"]]:
            continue
        if s["span"] in ("presentation", "boundary_verification"):
            per_rep.setdefault((s["batch"], s["repetition"]), {})[s["span"]] = s["value_ms"]
    return [v["presentation"] + v["boundary_verification"] for v in per_rep.values()]


for run, art, dw in ((2, row1_r2, True), (1, row1_r1, False)):
    b3, b0 = segment_vals("B3", dw), segment_vals("B0", dw)
    pe = statistics.median(b3) - statistics.median(b0)
    dec = art["decision"]
    ok = (
        len(b3) == dec["treatment"]["n"]
        and len(b0) == dec["control"]["n"]
        and math.isclose(pe, dec["point_estimate_ms"], abs_tol=1e-9)
        and math.isclose(statistics.median(b3), dec["treatment"]["median"], abs_tol=1e-9)
        and math.isclose(statistics.median(b0), dec["control"]["median"], abs_tol=1e-9)
        and math.isclose(naive_desc(b3)["p95"], dec["treatment"]["p95"], abs_tol=1e-9)
        and math.isclose(naive_desc(b3)["iqr"], dec["treatment"]["iqr"], abs_tol=1e-9)
        and (dec["ci"]["high"] < dec["margin_ms"]) == (dec["verdict"] == "stands")
        and dec["margin_ms"] == 20.0
        and dec["resamples"] == 10000
        and dec["confidence"] == 0.95
    )
    print(
        f"   run {run}: n_B3={len(b3)} n_B0={len(b0)} point={pe:.6f} "
        f"(artefact {dec['point_estimate_ms']}) med_B3={statistics.median(b3)} "
        f"med_B0={statistics.median(b0)} -> {'OK' if ok else 'MISMATCH'}"
    )
    check(ok, f"A: row-1 run {run} independent recompute mismatch")
check(row1_r2["inputs"]["seed"] == plan["bootstrap_seed"] == 4815162342, "seed mismatch")
check(rq4["inputs"]["seed"] == plan["bootstrap_seed"], "rq4 seed mismatch")
check(rq4["inputs"]["resamples"] == plan["bootstrap_resamples"] == 10000, "resamples mismatch")
check(
    rq4["inputs"]["warmup_per_batch"] == 5
    and plan["batches"] == 3
    and plan["kept_after_warmup_per_configuration"] == 210,
    "plan mismatch",
)

# ---------------------------------------------------------------- B. sealed recompute
print(
    "B. SEALED recompute from raw (span_descriptives + all 70 arm_pair_delta), "
    "field-exact vs artefact"
)
from analysis.latency import (  # noqa: E402
    Sample,
    arm_pair_delta,
    discard_warmup,
    span_descriptives,
)

samples = [
    Sample(
        **{
            k: s[k]
            for k in ("arm", "scenario_id", "phase", "batch", "repetition", "span", "value_ms")
        }
    )
    for s in raw["samples"]
]
reps = span_descriptives(samples, warmup_per_batch=PER_BATCH)
art_reps = [json.dumps(r, sort_keys=True) for r in rq4["span_reports"]]
new_reps = [json.dumps(r.as_dict(), sort_keys=True) for r in reps]
print(f"   span_reports identical: {art_reps == new_reps}")
check(art_reps == new_reps, "B: span_reports differ from sealed recompute")
benign = [s for s in samples if s.scenario_id != REFUSAL]
kept = discard_warmup(benign, per_batch=PER_BATCH)
mism = 0
for d in rq4["arm_pair_deltas"]:
    nd = arm_pair_delta(
        kept,
        treatment_arm=d["treatment_arm"],
        control_arm=d["control_arm"],
        span=d["span"],
        phase=d["phase"],
        resamples=plan["bootstrap_resamples"],
        seed=plan["bootstrap_seed"],
    ).as_dict()
    if json.dumps(nd, sort_keys=True) != json.dumps(d, sort_keys=True):
        mism += 1
        print(f"   DIFF {d['treatment_arm']} {d['phase']} {d['span']}")
print(f"   70 deltas field-exact vs artefact; differences = {mism}")
check(mism == 0, "B: arm_pair_deltas differ from sealed recompute")

# ---------------------------------------------------------------- C. rendered vs artefact
print("C. RENDERED values (RENDER lines) vs artefact fields")


def render_lines(script):
    out = subprocess.run(
        [sys.executable, "-X", "utf8", str(REPO / "tools/figures" / script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO),
    )
    return [ln for ln in out.stdout.splitlines() if ln.startswith("RENDER")]


# L1
lines = render_lines("figL1_decision_strip.py")
got = {}
for ln in lines:
    m = re.match(r"RENDER FIG-L1 \| run(\d)\.(\w+) \[M sealed Decision\] = (.*)$", ln)
    if m:
        got[(int(m.group(1)), m.group(2))] = m.group(3)
for run, art in ((1, row1_r1), (2, row1_r2)):
    dec = art["decision"]
    exp = {
        "verdict": dec["verdict"],
        "point": dec["point_estimate_ms"],
        "lo": dec["ci"]["low"],
        "hi": dec["ci"]["high"],
        "margin": dec["margin_ms"],
        "conf": dec["confidence"],
        "resamples": dec["resamples"],
        "n": dec["treatment"]["n"],
    }
    for k, v in exp.items():
        g = got.get((run, k))
        ok = (str(v) == g) if isinstance(v, str) else math.isclose(float(g), v, abs_tol=1e-12)
        check(ok, f"C: L1 run{run}.{k} rendered {g} vs artefact {v}")
print(f"   L1: {len(got)} rendered fields checked")

# L23 -- the merged two-band figure: deltas (no IQR is drawn; the widths stand
# verbatim in the committed artefact) and the refusal path (median, p95, n).
lines = render_lines("figL23_latency.py")
by = {(d["treatment_arm"], d["phase"], d["span"]): d for d in rq4["arm_pair_deltas"]}
byr = {
    (r["arm"], r["phase"], r["span"]): r["descriptives"]
    for r in rq4["span_reports"]
    if r["series"] == "refusal_path"
}
b0e2e = [
    r
    for r in rq4["span_reports"]
    if r["arm"] == "B0"
    and r["phase"] == "warm"
    and r["span"] == "end_to_end"
    and r["series"] == "benign"
][0]["descriptives"]["median"]
n_l23 = 0
for ln in lines:
    m = re.match(
        r"RENDER FIG-L23 \| delta\.(.+?)\.(warm|cold)\.(\w+) \[M\] = ([-\d.]+) "
        r"\[([-\d.]+), ([-\d.]+)\] (\S+)$",
        ln,
    )
    if not m:
        continue
    arm, phase, span, pe, lo, hi, label = m.groups()
    d = by[(arm, phase, span)]
    ok = (
        math.isclose(float(pe), d["point_estimate_ms"], abs_tol=5.01e-5)
        and math.isclose(float(lo), d["ci_low_ms"], abs_tol=5.01e-5)
        and math.isclose(float(hi), d["ci_high_ms"], abs_tol=5.01e-5)
        and label == d["label"]
    )
    check(ok, f"C: L23 {arm} {phase} {span} rendered {pe} [{lo},{hi}] vs artefact")
    n_l23 += 1
n_l23_r = 0
for ln in lines:
    m = re.match(
        r"RENDER FIG-L23 \| refusal\.(.+?)\.(warm|cold)\.(\w+) \[M\] = median=([\d.]+) "
        r"p95=([\d.]+) n=(\d+)$",
        ln,
    )
    if not m:
        continue
    arm, phase, span, med, p95, n = m.groups()
    d = byr[(arm, phase, span)]
    ok = (
        math.isclose(float(med), d["median"], abs_tol=5.01e-5)
        and math.isclose(float(p95), d["p95"], abs_tol=5.01e-5)
        and int(n) == d["n"]
    )
    check(ok, f"C: L23 refusal {arm} {phase} {span} rendered vs artefact")
    n_l23_r += 1
a7_l23 = [ln for ln in lines if "A7.fixed_overhead" in ln][0].split("= ")[1]
check(float(a7_l23) == b0e2e, f"C: L23 A7 {a7_l23} vs {b0e2e}")
print(f"   L23: {n_l23} deltas (70 expected) + {n_l23_r} refusal rows (72 expected); A7 = {a7_l23}")
check(n_l23 == 70, "C: L23 rendered fewer than 70 deltas")
check(n_l23_r == 72, "C: L23 rendered refusal rows != 72")


# ---------------------------------------------------------------- D. ticks
print("D. TICKS: label text == formatted position; data values land where the scale says")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import _common  # noqa: E402,F401  (side effect: Agg + SOURCE_DATE_EPOCH)

figs = {}


def grab(stem):
    def fake_save(fig, s, a):
        figs[stem] = fig

    return fake_save


import importlib  # noqa: E402

for mod, stem in (
    ("figL1_decision_strip", "L1"),
    ("figL23_latency", "L23"),
):
    m = importlib.import_module(mod)
    m.save = grab(stem)
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        m.main()
for stem, fig in figs.items():
    fig.canvas.draw()
    n_axes = 0
    for ax in fig.axes:
        locs = list(ax.get_xticks())
        labs = [t.get_text() for t in ax.get_xticklabels()]
        if any(labs):
            for loc, lab in zip(locs, labs):
                if not lab:
                    continue
                lab_n = float(lab.replace("−", "-"))
                check(
                    math.isclose(lab_n, loc, rel_tol=1e-9, abs_tol=1e-12),
                    f"D: {stem} tick label {lab!r} at position {loc}",
                )
        # position sanity: a value between two labelled ticks must map between them
        x0, x1 = ax.get_xlim()
        for v in [loc for loc in locs if x0 < loc < x1]:
            frac = ax.transAxes.inverted().transform(ax.transData.transform((v, 0)))[0]
            check(0.0 <= frac <= 1.0, f"D: {stem} tick {v} outside axes")
        n_axes += 1
    print(f"   {stem}: {n_axes} axes, tick labels consistent with positions")

# L23: axes[0] is the delta band (symlog); axes[5] the refusal band (log10)
ax = figs["L23"].axes[0]


def frac23(v):
    return ax.transAxes.inverted().transform(ax.transData.transform((v, 0)))[0]


check(frac23(0.001) < frac23(0.01) < frac23(0.1) < frac23(1) < frac23(10), "D: L23 symlog ordering")
check(
    abs((frac23(1) - frac23(0.1)) - (frac23(10) - frac23(1))) < 1e-9,
    "D: L23 symlog decades equal width",
)
check(abs(frac23(0.001) + frac23(-0.001) - 2 * frac23(0)) < 1e-9, "D: L23 symlog symmetric about 0")
print("   L23 symlog: decades equal width, symmetric about zero, ordered")
ax = figs["L23"].axes[5]


def frac23l(v):
    return ax.transAxes.inverted().transform(ax.transData.transform((v, 0)))[0]


check(
    abs((frac23l(1) - frac23l(0.1)) - (frac23l(10) - frac23l(1))) < 1e-9,
    "D: L23 log decades equal width",
)
print("   L23 log10: decades equal width")

print()
if problems:
    print("PROBLEMS:")
    for p in problems:
        print("  -", p)
    raise SystemExit(1)
print("ALL CHECKS PASSED")
