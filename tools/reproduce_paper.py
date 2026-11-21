"""Recompute manuscript tables and Figures 2/3 from archived observations."""
import json
import statistics
import sys
from collections import Counter
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.latency import Sample, benign_series, benign_span_series, bootstrap_median_difference, describe, discard_warmup
from analysis.report import build
from validation.revision.model import score_episode, target_call

REVISION = ROOT / "results/revision"
ARMS = ["B0", "B1", "B2-broad-noexchange", "B2-exchange-broad", "B2-exchange-task", "B2-exchange-task-DPoP", "B-cap", "B3", "B3+"]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    out = ROOT / "_reproduced"
    out.mkdir(exist_ok=True)
    primary = build("confirmatory")
    assert primary["cells_scored"] == 143 and primary["agreement"]["agreed"] == 80
    cells = load(ROOT / "results/raw/campaign-confirmatory.json")["cells"]
    truths = {p.stem: load(p) for p in (ROOT / "fixtures/confirmatory/sealed").glob("*.json")}
    panel_a, panel_b = {}, {}
    for arm in ARMS:
        rows = [r for r in cells if r["arm"] == arm and r["monitor_attached"] is not True]
        attacks = [r for r in rows if not truths[r["scenario_id"]]["is_benign"]]
        panel_a[arm] = {
            "applicable": len(attacks),
            "admitted_by_family": dict(Counter(r["family"] for r in attacks if r["observed_forwarded"])),
            "false_rejections": sum(r["false_block"] for r in rows),
        }
        rows = [r for r in cells if r["arm"] == arm and r["monitor_attached"] is True and not truths[r["scenario_id"]]["is_benign"]]
        panel_b[arm] = dict(Counter(r["family"] for r in rows if r["observed_forwarded"]))
    deterministic = REVISION / "label-binding-fix-2026-11-09/deterministic"
    data = {name: load(deterministic / f"{name}.json")["rows"] for name in ["effects", "policy", "replay", "delegation", "revocation"]}
    table_iv = {}
    for arm in sorted({r["arm"] for r in data["effects"]}):
        rows = [r for r in data["effects"] if r["arm"] == arm and r["attack"] == "argument-substitution"]
        table_iv[arm] = {"requests": len(rows), "admitted": sum(r["admitted"] for r in rows), "content_written": sum(r["before"] != r["after"] for r in rows)}
    aip = [json.loads(line) for line in (REVISION / "systems-confirmed-2026-11-08/aip.jsonl").read_text().splitlines()]
    table_v = {}
    for arm in ["AIP", "B3", "B3+"]:
        table_v[arm] = {}
        for attack in ["benign", "outside-grant", "argument-substitution", "replay"]:
            rows = [r for r in aip if r["arm"] == arm and r["attack"] == attack and (attack != "replay" or r["repeat"] == 1)]
            table_v[arm][attack] = {"requests": len(rows), "admitted": sum(r["admitted"] for r in rows)}
    models = []
    for folder, protocol, attacks in [
        (REVISION / "model02", load(REVISION / "model02/protocol.json"), None),
        (REVISION / "systems-model-2026-11-08/evaluation", load(REVISION / "systems-model-2026-11-08/development-protocol.json"), load(REVISION / "systems-model-2026-11-08/selection.json")["selected"]),
    ]:
        attacks = protocol["attacks"] if attacks is None else attacks
        episodes = [load(p) for p in folder.glob("*.json") if p.name.startswith(("B0-", "B2-exchange-task-", "B3-")) and "-response-" not in p.name]
        assert len(episodes) == 45
        grouped = {}
        for arm in ["B0", "B2-exchange-task", "B3"]:
            grouped[arm] = {}
            for attack in attacks:
                rows = [r for r in episodes if r["arm"] == arm and r["attack"] == attack]
                for row in rows:
                    score = score_episode(row["final"], protocol["source"] + attacks[attack], attack)
                    assert all(score[k] == row[k] for k in ["task_complete", "attacker_success"])
                calls = [c for r in rows for c in r["calls"] if target_call(c, attack)]
                grouped[arm][attack] = {"runs": len(rows), "task_complete": sum(r["task_complete"] for r in rows), "attacker_success": sum(r["attacker_success"] for r in rows), "target_calls": len(calls), "denied_target_calls": sum(not c["admitted"] for c in calls)}
        models.append({"task_runs": len(episodes), "tool_calls": sum(len(r["calls"]) for r in episodes), "outcomes": grouped})
    raw = load(REVISION / "mentor-2026-11-11/raw.json")
    sample_fields = {field.name for field in fields(Sample)}
    samples = [Sample(**{k: r[k] for k in sample_fields}) for r in raw["samples"] if r["scenario_id"] == "gt-benign"]
    kept = discard_warmup(samples, per_batch=5)
    timing_arms = ARMS + ["OAuth-DPoP-call"]
    series = {arm: benign_series(kept, arm=arm) for arm in timing_arms}
    assert all(len(s) == 210 for s in series.values())
    stages = {a: {span: describe(benign_span_series(kept, arm=a, span=span)).as_dict() for span in ["delegation", "presentation", "boundary_verification"]} for a in timing_arms}
    comparisons = []
    for treatment, control in [("B3", "B0"), ("OAuth-DPoP-call", "B2-exchange-task-DPoP"), ("OAuth-DPoP-call", "B3"), ("OAuth-DPoP-call", "B0")]:
        ci = bootstrap_median_difference(series[treatment], series[control], seed=4815162342, resamples=10000)
        comparisons.append({"treatment": treatment, "control": control, "delta_ms": statistics.median(series[treatment]) - statistics.median(series[control]), "ci_low_ms": ci.low, "ci_high_ms": ci.high})
    expected = load(REVISION / "mentor-2026-11-11/summary.json")["contrasts"]
    for actual, recorded in zip(comparisons, expected):
        assert all(abs(actual[k] - recorded[k]) < 1e-10 for k in ["delta_ms", "ci_low_ms", "ci_high_ms"])
    summary = {"primary": {"scored": 143, "inapplicable": len(primary["unscorable"]), "predictions_agreed": 80}, "figure2": {"a": panel_a, "b": panel_b}, "supplementary_counts": {k: len(v) for k, v in data.items()}, "table_iv": table_iv, "table_v": table_v, "models": models, "timing": {"stages": stages, "contrasts": comparisons}}
    (out / "paper-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "primary-analysis.json").write_text(json.dumps(primary, indent=2) + "\n")
    plot(out, panel_a, panel_b, stages)
    print("Rebuilt primary analysis, Tables IV/V, model scores, timing intervals and Figures 2/3.")
    print(json.dumps({"supplementary_counts": summary["supplementary_counts"], "timing": comparisons}, indent=2))


def plot(out, panel_a, panel_b, stages):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for ax, panel, families in [(axes[0], panel_a, ["F1", "F2", "F3", "F4", "F5"]), (axes[1], panel_b, ["F4", "F5"])]:
        bottom = [0] * len(ARMS)
        for family in families:
            values = [panel[a].get("admitted_by_family", panel[a]).get(family, 0) for a in ARMS]
            ax.bar(range(len(ARMS)), values, bottom=bottom, color=colors[int(family[1]) - 1], label=family)
            bottom = [x + y for x, y in zip(bottom, values)]
        ax.set_xticks(range(len(ARMS)), ARMS, rotation=45, ha="right", fontsize=7)
        ax.set_ylabel("Admitted attacks")
        ax.legend(fontsize=7)
    axes[0].bar(range(len(ARMS)), [-panel_a[a]["false_rejections"] for a in ARMS], color="#D00000", label="Legitimate calls refused")
    axes[0].set_title("Without policy monitor")
    axes[1].set_title("F4/F5 with policy monitor")
    fig.tight_layout()
    for ext in ["pdf", "png"]:
        fig.savefig(out / f"figure2.{ext}", dpi=180)
    plt.close(fig)
    order = ARMS[2:6] + ["OAuth-DPoP-call"] + ARMS[6:]
    fig, ax = plt.subplots(figsize=(9, 4))
    for offset, span, color in [(-.18, "delegation", "#A8C8E8"), (.18, "boundary_verification", "#1B3D6E")]:
        values = [stages[a][span]["median"] - stages["B0"][span]["median"] for a in order]
        ax.bar([i + offset for i in range(len(order))], values, width=.36, color=color, label=span.replace("_", " "))
    ax.set_yscale("log")
    ax.set_ylabel("Added time over B0 / ms")
    ax.set_xticks(range(len(order)), order, rotation=35, ha="right", fontsize=8)
    ax.legend(fontsize=8)
    fig.tight_layout()
    for ext in ["pdf", "png"]:
        fig.savefig(out / f"figure3.{ext}", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
