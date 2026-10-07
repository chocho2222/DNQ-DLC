#!/usr/bin/env python3
"""Post-hoc strict endpoint audit for the E0 two-agent matrix."""
import csv
import json
from pathlib import Path
from audit_main_matrix_strict_endpoint import track_arclength, detect_events, strict_event, wilson


ROOT = Path(__file__).resolve().parents[1]
E0 = ROOT / "outputs/tits_dynamic_graph_expanded/e0_two_agent_fairness_20260918"


def main():
    rows = []
    for suite_path in sorted(E0.glob("runs/*/seed*/**/online_suite_n2_seed*.json")):
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
        summary = suite.get("summaries", [None])[0]
        if not summary:
            continue
        summary_path = Path(summary["summary_path"])
        trace_path = Path(summary["trace_path"])
        initial_path = trace_path.with_name(trace_path.name.replace(".trace.json", ".initial.json"))
        if not initial_path.exists():
            initial_path = trace_path.parent / (trace_path.stem.replace(".trace", ".initial") + ".json")
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        initial = json.loads(initial_path.read_text(encoding="utf-8"))
        target = int(summary.get("target_agent", 1))
        geometry = track_arclength(initial["track"])
        events = detect_events(trace, target, geometry, 20.0, 4.0)
        audited = [strict_event(trace, e, target, 50, 4.0, 0.45, 0.82, 0.25, 1.0) for e in events]
        available = [e for e in audited if e.get("available")]
        rows.append({
            "track_id": suite_path.parts[-4], "seed": int(summary["seed"]),
            "algorithm": summary["algorithm"], "status": "ok",
            "event_count": len(events), "available_event_count": len(available),
            "post_pass_censored": bool(events) and not bool(available),
            "strict_completion": any(e.get("strict_completion", False) for e in available),
            "physical_pass": any(e.get("physical_pass", False) for e in available),
            "event_contact_free": any(e.get("contact_free", False) for e in available),
            "event_on_track": any(e.get("on_track", False) for e in available),
            "sustained_lead": any(e.get("sustained_lead", False) for e in available),
            "post_pass_stable": any(e.get("post_pass_stable", False) for e in available),
            "target_progress": summary.get("target_progress"), "rank_gain": summary.get("rank_gain"),
            "target_grass_rate": summary.get("target_grass_rate"),
            "target_heading_error_mean_rad": summary.get("target_heading_error_mean_rad"),
        })
    out = E0 / "e0_strict_endpoint_audit.csv"
    fields = list(rows[0]) if rows else []
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    aggregates = []
    for algorithm in sorted({r["algorithm"] for r in rows}):
        subset = [r for r in rows if r["algorithm"] == algorithm]
        for endpoint in ["strict_completion", "physical_pass", "event_contact_free", "event_on_track", "sustained_lead", "post_pass_stable"]:
            n = len(subset); k = sum(bool(r[endpoint]) for r in subset); lo, hi = wilson(k, n)
            aggregates.append({"algorithm": algorithm, "endpoint": endpoint, "n": n, "count": k,
                               "rate": k / n if n else 0.0, "wilson_low": lo, "wilson_high": hi})
    agg = E0 / "e0_strict_endpoint_aggregate.csv"
    with agg.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(aggregates[0])); writer.writeheader(); writer.writerows(aggregates)
    manifest = {"experiment_id": "E0_two_agent_baseline_validity", "rows": len(rows), "algorithms": sorted({r["algorithm"] for r in rows}),
                "hold_steps": 50, "approach_distance_m": 20.0, "pass_margin_m": 4.0,
                "lateral_limit": 0.45, "heading_cos_min": 0.82, "denominator_policy": "all completed method-seed rows"}
    (E0 / "e0_strict_endpoint_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
