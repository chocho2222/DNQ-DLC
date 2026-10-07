#!/usr/bin/env python3
"""Build a provenance-preserving comparison of nominal and strict endpoints.

The nominal endpoint is the archived legacy benchmark completion.  The strict
endpoint is the post-hoc physics/event audit.  They intentionally retain their
original denominators because they come from different, frozen protocols.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/tits_dynamic_graph_expanded/current_paper_data_20260916/analysis"
E1_NOMINAL = ROOT / "outputs/tits_dynamic_graph_expanded/e1_200_summary/tables/online_benchmark_nature_direct_statistics.csv"
E1_STRICT = ROOT / "outputs/tits_dynamic_graph_expanded/e1_200_budget_matched/strict_endpoint_audit_E1_final_20260916/aggregate.csv"
E0_NOMINAL = ROOT / "outputs/tits_dynamic_graph_expanded/e0_two_agent_fairness_20260918"
E0_STRICT = E0_NOMINAL / "e0_strict_endpoint_aggregate.csv"


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1.0 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    rad = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return max(0.0, ctr - rad), min(1.0, ctr + rad)


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def nominal_e1():
    rows = []
    for r in read_csv(E1_NOMINAL):
        if r["metric"] != "overtake_success_rate":
            continue
        n = int(r["n"])
        # The archived statistic is a binary episode-level endpoint.
        k = round(float(r["mean"]) * n)
        lo, hi = wilson(k, n)
        rows.append({
            "experiment": "E1",
            "endpoint": "nominal_legacy_completion",
            "algorithm": r["algorithm"],
            "label": r["algorithm_label"],
            "n": n,
            "count": k,
            "rate": k / n,
            "ci95_low": lo,
            "ci95_high": hi,
            "protocol_note": "Archived legacy benchmark; crossing-based completion only; no strict contact, containment, sustained-lead, or post-pass requirement.",
        })
    return rows


def strict_e1():
    rows = []
    for r in read_csv(E1_STRICT):
        if r["endpoint"] != "strict_completion":
            continue
        rows.append({
            "experiment": "E1",
            "endpoint": "strict_completion",
            "algorithm": r["algorithm"],
            "label": r["algorithm"],
            "n": int(r["n"]),
            "count": int(r["count"]),
            "rate": float(r["rate"]),
            "ci95_low": float(r["wilson_low"]),
            "ci95_high": float(r["wilson_high"]),
            "protocol_note": "Post-hoc physics/event audit; contact-free, on-track, sustained lead, post-pass stability, and available hold window are required.",
        })
    return rows


def nominal_e0():
    rows = []
    # Each run directory contains a copied top-level summary as well as the
    # algorithm-owned summary.  Use only the latter to keep one row per
    # algorithm--track--seed case.
    for path in sorted(E0_NOMINAL.glob("runs/*/seed*/*/summaries/*.summary.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append(data)
    algs = sorted({r["algorithm"] for r in rows})
    out = []
    for alg in algs:
        subset = [r for r in rows if r["algorithm"] == alg]
        n = len(subset)
        k = sum(bool(r.get("overtake_success")) for r in subset)
        lo, hi = wilson(k, n)
        out.append({
            "experiment": "E0",
            "endpoint": "nominal_legacy_completion",
            "algorithm": alg,
            "label": alg,
            "n": n,
            "count": k,
            "rate": k / n if n else 0.0,
            "ci95_low": lo,
            "ci95_high": hi,
            "protocol_note": "Matched two-agent rollout using the evaluator's archived crossing event; reported only as a nominal diagnostic.",
        })
    return out


def strict_e0():
    rows = []
    for r in read_csv(E0_STRICT):
        if r["endpoint"] != "strict_completion":
            continue
        rows.append({
            "experiment": "E0",
            "endpoint": "strict_completion",
            "algorithm": r["algorithm"],
            "label": r["algorithm"],
            "n": int(r["n"]),
            "count": int(r["count"]),
            "rate": float(r["rate"]),
            "ci95_low": float(r["wilson_low"]),
            "ci95_high": float(r["wilson_high"]),
            "protocol_note": "Matched two-agent post-hoc strict endpoint audit.",
        })
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = nominal_e1() + strict_e1() + nominal_e0() + strict_e0()
    fields = ["experiment", "endpoint", "algorithm", "label", "n", "count", "rate", "ci95_low", "ci95_high", "protocol_note"]
    csv_path = OUT / "nominal_strict_endpoint_comparison_20260918.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    md_path = OUT / "nominal_strict_endpoint_comparison_20260918.md"
    lines = [
        "# Nominal versus strict endpoint comparison",
        "",
        "The nominal endpoint is retained as a legacy diagnostic. It is not interchangeable with strict completion because the protocols and denominators differ.",
        "",
        "| Experiment | Method | Nominal completion | Strict completion | Interpretation |",
        "|---|---|---:|---:|---|",
    ]
    for exp in ("E1", "E0"):
        methods = sorted({r["algorithm"] for r in rows if r["experiment"] == exp})
        for alg in methods:
            nrow = next((r for r in rows if r["experiment"] == exp and r["algorithm"] == alg and r["endpoint"] == "nominal_legacy_completion"), None)
            srow = next((r for r in rows if r["experiment"] == exp and r["algorithm"] == alg and r["endpoint"] == "strict_completion"), None)
            nominal = f"{nrow['count']}/{nrow['n']} ({float(nrow['rate']):.3f})" if nrow else "--"
            strict = f"{srow['count']}/{srow['n']} ({float(srow['rate']):.3f})" if srow else "--"
            interpretation = "Nominal event can overstate robust completion" if nrow and float(nrow["rate"]) > 0 and (not srow or float(srow["rate"]) == 0) else "Use as diagnostic only"
            lines.append(f"| {exp} | {alg} | {nominal} | {strict} | {interpretation} |")
    lines += [
        "",
        "Recommended manuscript wording: the legacy completion endpoint is reported to preserve comparability with prior DLC evaluations, while the primary claim uses the strict endpoint. All methods must be shown when the nominal endpoint is reported.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"csv": str(csv_path), "markdown": str(md_path), "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
