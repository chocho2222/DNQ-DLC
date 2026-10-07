#!/usr/bin/env python
import argparse
import json
from pathlib import Path


ARTIFACTS = [
    {
        "name": "main_multiseed_suite",
        "outputs": [
            "evaluations/multiseed_suite/multiseed_suite_summary.json",
            "tables/main_multiseed_suite_report.md",
            "tables/main_multiseed_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt", "materials/scripts/run_multiseed_overtake_suite.py"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/multiseed_suite "
            "--methods graph_soft_shield,lane_base_only,overtake_base_only "
            "--seeds 3,7,11,17,23,29,31,37,41,43 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/multiseed_suite/multiseed_suite_summary.json "
            "--prefix main_multiseed_suite"
        ),
    },
    {
        "name": "adaptive_gate_suite",
        "outputs": [
            "evaluations/adaptive_gate_suite/multiseed_suite_summary.json",
            "tables/adaptive_gate_suite_report.md",
            "tables/adaptive_gate_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/adaptive_gate_suite "
            "--methods adaptive_gate_only,graph_adaptive_shield "
            "--seeds 3,7,11,17,23,29,31,37,41,43 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/adaptive_gate_suite/multiseed_suite_summary.json "
            "--prefix adaptive_gate_suite"
        ),
    },
    {
        "name": "recovery_adaptive_suite",
        "outputs": [
            "evaluations/recovery_adaptive_suite/multiseed_suite_summary.json",
            "tables/recovery_adaptive_suite_report.md",
            "tables/recovery_adaptive_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/recovery_adaptive_suite "
            "--methods graph_recovery_adaptive_shield "
            "--seeds 3,7,11,17,23,29,31,37,41,43 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/recovery_adaptive_suite/multiseed_suite_summary.json "
            "--prefix recovery_adaptive_suite"
        ),
    },
    {
        "name": "full_statistical_report",
        "outputs": [
            "tables/full_statistical_report.md",
            "tables/full_statistical_report.json",
            "tables/full_statistical_report_method_summary.csv",
            "tables/full_statistical_report_pairwise.csv",
        ],
        "inputs": [
            "evaluations/multiseed_suite/multiseed_suite_summary.json",
            "evaluations/adaptive_gate_suite/multiseed_suite_summary.json",
            "evaluations/recovery_adaptive_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_full_statistical_report.py"],
        "command": "python scripts/export_full_statistical_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "portfolio_oracle",
        "outputs": ["tables/portfolio_oracle.md", "tables/portfolio_oracle.json", "tables/portfolio_oracle_rows.csv"],
        "inputs": [
            "evaluations/multiseed_suite/multiseed_suite_summary.json",
            "evaluations/adaptive_gate_suite/multiseed_suite_summary.json",
            "evaluations/recovery_adaptive_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_portfolio_oracle_report.py"],
        "command": "python scripts/export_portfolio_oracle_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "geometry_selector_loso",
        "outputs": ["tables/portfolio_selector_loso.md", "tables/portfolio_selector_loso.json", "tables/portfolio_selector_loso_rows.csv"],
        "inputs": [
            "evaluations/multiseed_suite/multiseed_suite_summary.json",
            "evaluations/adaptive_gate_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_portfolio_selector_report.py"],
        "command": "python scripts/export_portfolio_selector_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "online_probe_selector",
        "outputs": [
            "evaluations/portfolio_probe_selector/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector.md",
            "tables/portfolio_probe_selector.json",
            "tables/portfolio_probe_selector_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "python scripts/run_portfolio_probe_selector.py --root outputs/paper_multicar_overtake_20260618 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --skip-existing"
        ),
    },
    {
        "name": "online_probe_selector_1200",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200.md",
            "tables/portfolio_probe_selector_1200.json",
            "tables/portfolio_probe_selector_1200_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "python scripts/run_portfolio_probe_selector.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200 "
            "--table-prefix portfolio_probe_selector_1200 --probe-steps 1200 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --skip-existing"
        ),
    },
    {
        "name": "heldout_multiseed_suite",
        "outputs": [
            "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json",
            "tables/heldout_multiseed_suite_report.md",
            "tables/heldout_multiseed_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_multiseed_suite "
            "--methods lane_base_only,overtake_base_only "
            "--seeds 47,53,59,61,67,71,73,79,83,89 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_multiseed_suite/multiseed_suite_summary.json "
            "--prefix heldout_multiseed_suite"
        ),
    },
    {
        "name": "heldout_adaptive_suite",
        "outputs": [
            "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json",
            "tables/heldout_adaptive_suite_report.md",
            "tables/heldout_adaptive_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_adaptive_suite "
            "--methods graph_adaptive_shield "
            "--seeds 47,53,59,61,67,71,73,79,83,89 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_adaptive_suite/multiseed_suite_summary.json "
            "--prefix heldout_adaptive_suite"
        ),
    },
    {
        "name": "heldout_expert_gate_suite",
        "outputs": [
            "evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json",
            "tables/heldout_expert_gate_suite_report.md",
            "tables/heldout_expert_gate_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_expert_gate_suite "
            "--methods expert_gate_only "
            "--seeds 47,53,59,61,67,71,73,79,83,89 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json "
            "--prefix heldout_expert_gate_suite"
        ),
    },
    {
        "name": "heldout_expert_fast_smoke",
        "outputs": [
            "evaluations/heldout_expert_fast_smoke/multiseed_suite_summary.json",
            "tables/heldout_expert_fast_smoke_report.md",
            "tables/heldout_expert_fast_smoke_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_expert_fast_smoke "
            "--methods expert_fast_only --seeds 61,71,73,89 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_expert_fast_smoke/multiseed_suite_summary.json "
            "--prefix heldout_expert_fast_smoke"
        ),
    },
    {
        "name": "heldout_expert_barrier_smoke",
        "outputs": [
            "evaluations/heldout_expert_barrier_smoke/multiseed_suite_summary.json",
            "tables/heldout_expert_barrier_smoke_report.md",
            "tables/heldout_expert_barrier_smoke_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_expert_barrier_smoke "
            "--methods expert_barrier_only --seeds 61,71,73,89 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_expert_barrier_smoke/multiseed_suite_summary.json "
            "--prefix heldout_expert_barrier_smoke"
        ),
    },
    {
        "name": "heldout_expert_recovery_smoke",
        "outputs": [
            "evaluations/heldout_expert_recovery_smoke/multiseed_suite_summary.json",
            "tables/heldout_expert_recovery_smoke_report.md",
            "tables/heldout_expert_recovery_smoke_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_expert_recovery_smoke "
            "--methods expert_recovery_only --seeds 61,71,73,89 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_expert_recovery_smoke/multiseed_suite_summary.json "
            "--prefix heldout_expert_recovery_smoke"
        ),
    },
    {
        "name": "graph_dagger_recovery_training",
        "outputs": [
            "models/graph_dagger_recovery/graph_dagger_recovery.graph.pt",
            "models/graph_dagger_recovery/train_summary.json",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/train_graph_dagger_recovery.py"],
        "command": (
            "python scripts/train_graph_dagger_recovery.py --hard-seeds 61,71,89 "
            "--support-seeds 3,7,11,17,23,29,31,37,41,43 --repeats 1 --max-steps 2400 "
            "--train-steps 1800 --batch-size 2048 --device cuda:0 "
            "--out-dir outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery"
        ),
    },
    {
        "name": "heldout_graph_dagger_recovery_smoke",
        "outputs": [
            "evaluations/heldout_graph_dagger_recovery_smoke/multiseed_suite_summary.json",
            "tables/heldout_graph_dagger_recovery_smoke_report.md",
            "tables/heldout_graph_dagger_recovery_smoke_rows.csv",
        ],
        "inputs": ["models/graph_dagger_recovery/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_smoke "
            "--model-path outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery/graph_dagger_recovery.graph.pt "
            "--methods graph_adaptive_shield,graph_expert_gate_shield,graph_expert_recovery_shield "
            "--seeds 61,71,73,89 --devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_smoke/multiseed_suite_summary.json "
            "--prefix heldout_graph_dagger_recovery_smoke"
        ),
    },
    {
        "name": "dagger_failure_diagnosis",
        "outputs": [
            "tables/dagger_failure_diagnosis.json",
            "tables/dagger_failure_diagnosis.md",
            "tables/dagger_failure_diagnosis_rows.csv",
        ],
        "inputs": ["evaluations/heldout_graph_dagger_recovery_smoke/multiseed_suite_summary.json"],
        "scripts": ["scripts/export_dagger_failure_diagnosis.py"],
        "command": (
            "python scripts/export_dagger_failure_diagnosis.py "
            "--root outputs/paper_multicar_overtake_20260618"
        ),
    },
    {
        "name": "graph_dagger_recovery_v2_training",
        "outputs": [
            "models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
            "models/graph_dagger_recovery_v2/train_summary.json",
        ],
        "inputs": ["models/graph_dagger_recovery/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/train_graph_dagger_recovery.py"],
        "command": (
            "python scripts/train_graph_dagger_recovery.py "
            "--init-model outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery/graph_dagger_recovery.graph.pt "
            "--hard-seeds 61,71,73,89 --support-seeds 3,7,11,17,23,29,31,37,41,43 "
            "--oracle-policy expert_gate --target-speed 21.0 --repeats 1 --max-steps 3200 "
            "--train-steps 2200 --batch-size 2048 --lr 8e-5 --device cuda:0 "
            "--out-dir outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2"
        ),
    },
    {
        "name": "heldout_graph_dagger_recovery_v2_smoke",
        "outputs": [
            "evaluations/heldout_graph_dagger_recovery_v2_smoke/multiseed_suite_summary.json",
            "tables/heldout_graph_dagger_recovery_v2_smoke_report.md",
            "tables/heldout_graph_dagger_recovery_v2_smoke_rows.csv",
        ],
        "inputs": ["models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_v2_smoke "
            "--model-path outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt "
            "--methods graph_adaptive_shield,graph_expert_gate_shield,graph_expert_recovery_shield "
            "--seeds 61,71,73,89 --devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_v2_smoke/multiseed_suite_summary.json "
            "--prefix heldout_graph_dagger_recovery_v2_smoke"
        ),
    },
    {
        "name": "dagger_v2_failure_diagnosis",
        "outputs": [
            "tables/dagger_v2_failure_diagnosis.json",
            "tables/dagger_v2_failure_diagnosis.md",
            "tables/dagger_v2_failure_diagnosis_rows.csv",
        ],
        "inputs": ["evaluations/heldout_graph_dagger_recovery_v2_smoke/multiseed_suite_summary.json"],
        "scripts": ["scripts/export_dagger_failure_diagnosis.py"],
        "command": (
            "python scripts/export_dagger_failure_diagnosis.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_v2_smoke/multiseed_suite_summary.json "
            "--prefix dagger_v2_failure_diagnosis"
        ),
    },
    {
        "name": "heldout_graph_dagger_recovery_v2_suite",
        "outputs": [
            "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "tables/heldout_graph_dagger_recovery_v2_suite_report.md",
            "tables/heldout_graph_dagger_recovery_v2_suite_rows.csv",
        ],
        "inputs": ["models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_v2_suite "
            "--model-path outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt "
            "--methods graph_expert_gate_shield,graph_adaptive_shield "
            "--seeds 47,53,59,61,67,71,73,79,83,89 --devices cuda:0,cuda:1,cuda:2,cuda:3 "
            "--parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json "
            "--prefix heldout_graph_dagger_recovery_v2_suite"
        ),
    },
    {
        "name": "heldout_graph_dagger_recovery_v2_more_graph_suite",
        "outputs": [
            "evaluations/heldout_graph_dagger_recovery_v2_more_graph_suite/multiseed_suite_summary.json",
            "tables/heldout_graph_dagger_recovery_v2_more_graph_suite_report.md",
            "tables/heldout_graph_dagger_recovery_v2_more_graph_suite_report.json",
            "tables/heldout_graph_dagger_recovery_v2_more_graph_suite_rows.csv",
        ],
        "inputs": ["models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_multiseed_overtake_suite.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_v2_more_graph_suite "
            "--model-path outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt "
            "--methods graph_expert_gate_shield_more_graph "
            "--seeds 47,53,59,61,67,71,73,79,83,89 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_multiseed_suite_report.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_v2_more_graph_suite/multiseed_suite_summary.json "
            "--prefix heldout_graph_dagger_recovery_v2_more_graph_suite"
        ),
    },
    {
        "name": "dagger_v2_heldout_failure_diagnosis",
        "outputs": [
            "tables/dagger_v2_heldout_failure_diagnosis.json",
            "tables/dagger_v2_heldout_failure_diagnosis.md",
            "tables/dagger_v2_heldout_failure_diagnosis_rows.csv",
        ],
        "inputs": ["evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json"],
        "scripts": ["scripts/export_dagger_failure_diagnosis.py"],
        "command": (
            "python scripts/export_dagger_failure_diagnosis.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json "
            "--prefix dagger_v2_heldout_failure_diagnosis"
        ),
    },
    {
        "name": "heldout_v2_portfolio",
        "outputs": [
            "tables/heldout_v2_portfolio.json",
            "tables/heldout_v2_portfolio.md",
            "tables/heldout_v2_portfolio_method_summary.csv",
        ],
        "inputs": [
            "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_heldout_v2_portfolio_report.py"],
        "command": "python scripts/export_heldout_v2_portfolio_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "online_probe_selector_1200_heldout",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200_heldout/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200_heldout.md",
            "tables/portfolio_probe_selector_1200_heldout.json",
            "tables/portfolio_probe_selector_1200_heldout_rows.csv",
        ],
        "inputs": [
            "models/graph_bc/graph_bc.graph.pt",
            "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "python scripts/run_portfolio_probe_selector.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200_heldout "
            "--table-prefix portfolio_probe_selector_1200_heldout --probe-steps 1200 "
            "--seeds 47,53,59,61,67,71,73,79,83,89 "
            "--full-suite-main evaluations/heldout_multiseed_suite/multiseed_suite_summary.json "
            "--full-suite-adaptive evaluations/heldout_adaptive_suite/multiseed_suite_summary.json "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --skip-existing"
        ),
    },
    {
        "name": "online_probe_selector_1200_heldout_expert",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200_heldout_expert/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200_heldout_expert.md",
            "tables/portfolio_probe_selector_1200_heldout_expert.json",
            "tables/portfolio_probe_selector_1200_heldout_expert_rows.csv",
        ],
        "inputs": [
            "models/graph_bc/graph_bc.graph.pt",
            "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "python scripts/run_portfolio_probe_selector.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200_heldout_expert "
            "--table-prefix portfolio_probe_selector_1200_heldout_expert "
            "--methods lane_base_only,overtake_base_only,graph_adaptive_shield,expert_gate_only "
            "--probe-steps 1200 --seeds 47,53,59,61,67,71,73,79,83,89 "
            "--full-suite-main evaluations/heldout_multiseed_suite/multiseed_suite_summary.json "
            "--full-suite-adaptive evaluations/heldout_adaptive_suite/multiseed_suite_summary.json "
            "--full-suite-expert evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --skip-existing"
        ),
    },
    {
        "name": "online_probe_selector_1200_heldout_dagger_v2",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200_heldout_dagger_v2/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.md",
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2_rows.csv",
        ],
        "inputs": [
            "models/graph_bc/graph_bc.graph.pt",
            "models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
            "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "python scripts/run_portfolio_probe_selector.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200_heldout_dagger_v2 "
            "--table-prefix portfolio_probe_selector_1200_heldout_dagger_v2 "
            "--methods lane_base_only,overtake_base_only,graph_adaptive_shield,expert_gate_only,dagger_v2_graph_expert_gate_shield "
            "--probe-steps 1200 --seeds 47,53,59,61,67,71,73,79,83,89 "
            "--full-suite-main evaluations/heldout_multiseed_suite/multiseed_suite_summary.json "
            "--full-suite-adaptive evaluations/heldout_adaptive_suite/multiseed_suite_summary.json "
            "--full-suite-expert evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json "
            "--full-suite-dagger-v2 evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --skip-existing"
        ),
    },
    {
        "name": "heldout2_multiseed_suite",
        "outputs": [
            "evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json",
            "tables/heldout2_multiseed_suite_report.md",
            "tables/heldout2_multiseed_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout2_multiseed_suite "
            "--methods lane_base_only,overtake_base_only --seeds 97,101,103,107,109,113,127,131,137,139 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json "
            "--prefix heldout2_multiseed_suite"
        ),
    },
    {
        "name": "heldout2_adaptive_suite",
        "outputs": [
            "evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json",
            "tables/heldout2_adaptive_suite_report.md",
            "tables/heldout2_adaptive_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout2_adaptive_suite "
            "--methods graph_adaptive_shield --seeds 97,101,103,107,109,113,127,131,137,139 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json "
            "--prefix heldout2_adaptive_suite"
        ),
    },
    {
        "name": "heldout2_expert_gate_suite",
        "outputs": [
            "evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json",
            "tables/heldout2_expert_gate_suite_report.md",
            "tables/heldout2_expert_gate_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout2_expert_gate_suite "
            "--methods expert_gate_only --seeds 97,101,103,107,109,113,127,131,137,139 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json "
            "--prefix heldout2_expert_gate_suite"
        ),
    },
    {
        "name": "heldout2_graph_dagger_recovery_v2_suite",
        "outputs": [
            "evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "tables/heldout2_graph_dagger_recovery_v2_suite_report.md",
            "tables/heldout2_graph_dagger_recovery_v2_suite_rows.csv",
        ],
        "inputs": ["models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "python scripts/run_multiseed_overtake_suite.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout2_graph_dagger_recovery_v2_suite "
            "--model-path outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt "
            "--methods graph_expert_gate_shield,graph_adaptive_shield --seeds 97,101,103,107,109,113,127,131,137,139 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "python scripts/export_multiseed_suite_report.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json "
            "--prefix heldout2_graph_dagger_recovery_v2_suite"
        ),
    },
    {
        "name": "heldout2_overtake_conservative_traffic_targeted",
        "outputs": [
            "evaluations/heldout2_overtake_conservative_traffic_targeted/multiseed_suite_summary.json",
            "tables/heldout2_overtake_conservative_traffic_targeted_report.md",
            "tables/heldout2_overtake_conservative_traffic_targeted_report.json",
            "tables/heldout2_overtake_conservative_traffic_targeted_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_multiseed_overtake_suite.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout2_overtake_conservative_traffic_targeted "
            "--methods overtake_conservative_traffic --seeds 97,101,103 "
            "--devices cuda:0,cuda:1,cuda:2 --parallel 3 --no-gif --no-trace && "
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_multiseed_suite_report.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout2_overtake_conservative_traffic_targeted/multiseed_suite_summary.json "
            "--prefix heldout2_overtake_conservative_traffic_targeted"
        ),
    },
    {
        "name": "heldout2_dagger_v2_recovery_conservative_suite",
        "outputs": [
            "evaluations/heldout2_dagger_v2_recovery_conservative_suite/multiseed_suite_summary.json",
            "tables/heldout2_dagger_v2_recovery_conservative_suite_report.md",
            "tables/heldout2_dagger_v2_recovery_conservative_suite_report.json",
            "tables/heldout2_dagger_v2_recovery_conservative_suite_rows.csv",
        ],
        "inputs": ["models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_multiseed_overtake_suite.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout2_dagger_v2_recovery_conservative_suite "
            "--model-path outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt "
            "--methods graph_recovery_adaptive_conservative_traffic "
            "--seeds 97,101,103,107,109,113,127,131,137,139 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_multiseed_suite_report.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout2_dagger_v2_recovery_conservative_suite/multiseed_suite_summary.json "
            "--prefix heldout2_dagger_v2_recovery_conservative_suite"
        ),
    },
    {
        "name": "heldout2_dagger_v2_expert_blend_targeted",
        "outputs": [
            "evaluations/heldout2_dagger_v2_expert_blend_targeted/multiseed_suite_summary.json",
            "tables/heldout2_dagger_v2_expert_blend_targeted_report.md",
            "tables/heldout2_dagger_v2_expert_blend_targeted_report.json",
            "tables/heldout2_dagger_v2_expert_blend_targeted_rows.csv",
        ],
        "inputs": ["models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_multiseed_overtake_suite.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout2_dagger_v2_expert_blend_targeted "
            "--model-path outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt "
            "--methods graph_expert_gate_shield_base_heavy,graph_expert_gate_shield_balanced,graph_expert_gate_shield_more_graph "
            "--seeds 101,103 --devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_multiseed_suite_report.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout2_dagger_v2_expert_blend_targeted/multiseed_suite_summary.json "
            "--prefix heldout2_dagger_v2_expert_blend_targeted"
        ),
    },
    {
        "name": "heldout2_dagger_v2_expert_more_graph_suite",
        "outputs": [
            "evaluations/heldout2_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "tables/heldout2_dagger_v2_expert_more_graph_suite_report.md",
            "tables/heldout2_dagger_v2_expert_more_graph_suite_report.json",
            "tables/heldout2_dagger_v2_expert_more_graph_suite_rows.csv",
        ],
        "inputs": ["models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_multiseed_overtake_suite.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout2_dagger_v2_expert_more_graph_suite "
            "--model-path outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt "
            "--methods graph_expert_gate_shield_more_graph "
            "--seeds 97,101,103,107,109,113,127,131,137,139 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_multiseed_suite_report.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout2_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json "
            "--prefix heldout2_dagger_v2_expert_more_graph_suite"
        ),
    },
    {
        "name": "online_probe_selector_1200_heldout_expanded",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200_heldout_expanded/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200_heldout_expanded.md",
            "tables/portfolio_probe_selector_1200_heldout_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout_expanded_rows.csv",
        ],
        "inputs": [
            "models/graph_bc/graph_bc.graph.pt",
            "models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
            "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout_graph_dagger_recovery_v2_more_graph_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_portfolio_probe_selector.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200_heldout_expanded "
            "--table-prefix portfolio_probe_selector_1200_heldout_expanded "
            "--methods lane_base_only,overtake_base_only,graph_adaptive_shield,expert_gate_only,dagger_v2_graph_expert_gate_shield,dagger_v2_graph_expert_gate_more_graph "
            "--probe-steps 1200 --seeds 47,53,59,61,67,71,73,79,83,89 "
            "--full-suite-main evaluations/heldout_multiseed_suite/multiseed_suite_summary.json "
            "--full-suite-adaptive evaluations/heldout_adaptive_suite/multiseed_suite_summary.json "
            "--full-suite-expert evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json "
            "--full-suite-dagger-v2 evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json "
            "--full-suite-dagger-v2-more-graph evaluations/heldout_graph_dagger_recovery_v2_more_graph_suite/multiseed_suite_summary.json "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4"
        ),
    },
    {
        "name": "online_probe_selector_1200_heldout2_expanded",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200_heldout2_expanded/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200_heldout2_expanded.md",
            "tables/portfolio_probe_selector_1200_heldout2_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout2_expanded_rows.csv",
        ],
        "inputs": [
            "models/graph_bc/graph_bc.graph.pt",
            "models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
            "evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_portfolio_probe_selector.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200_heldout2_expanded "
            "--table-prefix portfolio_probe_selector_1200_heldout2_expanded "
            "--methods lane_base_only,overtake_base_only,graph_adaptive_shield,expert_gate_only,dagger_v2_graph_expert_gate_shield,dagger_v2_graph_expert_gate_more_graph "
            "--probe-steps 1200 --seeds 97,101,103,107,109,113,127,131,137,139 "
            "--full-suite-main evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json "
            "--full-suite-adaptive evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json "
            "--full-suite-expert evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json "
            "--full-suite-dagger-v2 evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json "
            "--full-suite-dagger-v2-more-graph evaluations/heldout2_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4"
        ),
    },
    {
        "name": "expanded_selector_generalization",
        "outputs": [
            "tables/expanded_selector_generalization.md",
            "tables/expanded_selector_generalization.json",
            "tables/expanded_selector_generalization_rows.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout2_expanded.json",
            "tables/heldout2_candidate_expansion.json",
            "tables/heldout3_external_validation.json",
        ],
        "scripts": ["scripts/export_expanded_selector_report.py"],
        "command": "python scripts/export_expanded_selector_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "expanded_selector_distillation",
        "outputs": [
            "tables/expanded_selector_distillation_report.md",
            "tables/expanded_selector_distillation_report.json",
            "tables/expanded_selector_distillation_grid.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout2_expanded.json",
            "tables/expanded_selector_generalization.json",
        ],
        "scripts": ["scripts/export_expanded_selector_distillation_report.py"],
        "command": "python scripts/export_expanded_selector_distillation_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "learned_selector_diagnostic",
        "outputs": [
            "tables/learned_selector_report.md",
            "tables/learned_selector_report.json",
            "tables/learned_selector_rows.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout2_expanded.json",
            "tables/expanded_selector_generalization.json",
        ],
        "scripts": ["scripts/export_learned_selector_report.py"],
        "command": "python scripts/export_learned_selector_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "heldout3_multiseed_suite",
        "outputs": [
            "evaluations/heldout3_multiseed_suite/multiseed_suite_summary.json",
            "tables/heldout3_multiseed_suite_report.md",
            "tables/heldout3_multiseed_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_multiseed_overtake_suite.py "
            "--root outputs/paper_multicar_overtake_20260618 --out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout3_multiseed_suite "
            "--methods lane_base_only,overtake_base_only --seeds 149,151,157,163,167,173,179,181,191,193 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_multiseed_suite_report.py "
            "--root outputs/paper_multicar_overtake_20260618 --suite outputs/paper_multicar_overtake_20260618/evaluations/heldout3_multiseed_suite/multiseed_suite_summary.json "
            "--prefix heldout3_multiseed_suite"
        ),
    },
    {
        "name": "heldout3_adaptive_suite",
        "outputs": [
            "evaluations/heldout3_adaptive_suite/multiseed_suite_summary.json",
            "tables/heldout3_adaptive_suite_report.md",
            "tables/heldout3_adaptive_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_multiseed_overtake_suite.py "
            "--root outputs/paper_multicar_overtake_20260618 --out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout3_adaptive_suite "
            "--methods graph_adaptive_shield --seeds 149,151,157,163,167,173,179,181,191,193 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_multiseed_suite_report.py "
            "--root outputs/paper_multicar_overtake_20260618 --suite outputs/paper_multicar_overtake_20260618/evaluations/heldout3_adaptive_suite/multiseed_suite_summary.json "
            "--prefix heldout3_adaptive_suite"
        ),
    },
    {
        "name": "heldout3_expert_gate_suite",
        "outputs": [
            "evaluations/heldout3_expert_gate_suite/multiseed_suite_summary.json",
            "tables/heldout3_expert_gate_suite_report.md",
            "tables/heldout3_expert_gate_suite_rows.csv",
        ],
        "inputs": ["models/graph_bc/graph_bc.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_multiseed_overtake_suite.py "
            "--root outputs/paper_multicar_overtake_20260618 --out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout3_expert_gate_suite "
            "--methods expert_gate_only --seeds 149,151,157,163,167,173,179,181,191,193 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace && "
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_multiseed_suite_report.py "
            "--root outputs/paper_multicar_overtake_20260618 --suite outputs/paper_multicar_overtake_20260618/evaluations/heldout3_expert_gate_suite/multiseed_suite_summary.json "
            "--prefix heldout3_expert_gate_suite"
        ),
    },
    {
        "name": "heldout3_dagger_v2_suites",
        "outputs": [
            "evaluations/heldout3_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "tables/heldout3_graph_dagger_recovery_v2_suite_report.md",
            "tables/heldout3_graph_dagger_recovery_v2_suite_rows.csv",
            "evaluations/heldout3_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "tables/heldout3_dagger_v2_expert_more_graph_suite_report.md",
            "tables/heldout3_dagger_v2_expert_more_graph_suite_rows.csv",
        ],
        "inputs": ["models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "Two heldout3 DAgger-v2 full-suite runs using "
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python and cuda:0,cuda:1,cuda:2,cuda:3."
        ),
    },
    {
        "name": "online_probe_selector_1200_heldout3_expanded",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200_heldout3_expanded/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200_heldout3_expanded.md",
            "tables/portfolio_probe_selector_1200_heldout3_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout3_expanded_rows.csv",
        ],
        "inputs": [
            "models/graph_bc/graph_bc.graph.pt",
            "models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
            "evaluations/heldout3_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_portfolio_probe_selector.py "
            "--root outputs/paper_multicar_overtake_20260618 --out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200_heldout3_expanded "
            "--table-prefix portfolio_probe_selector_1200_heldout3_expanded "
            "--methods lane_base_only,overtake_base_only,graph_adaptive_shield,expert_gate_only,dagger_v2_graph_expert_gate_shield,dagger_v2_graph_expert_gate_more_graph "
            "--probe-steps 1200 --seeds 149,151,157,163,167,173,179,181,191,193 "
            "--full-suite-main evaluations/heldout3_multiseed_suite/multiseed_suite_summary.json "
            "--full-suite-adaptive evaluations/heldout3_adaptive_suite/multiseed_suite_summary.json "
            "--full-suite-expert evaluations/heldout3_expert_gate_suite/multiseed_suite_summary.json "
            "--full-suite-dagger-v2 evaluations/heldout3_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json "
            "--full-suite-dagger-v2-more-graph evaluations/heldout3_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4"
        ),
    },
    {
        "name": "heldout3_external_validation",
        "outputs": [
            "tables/heldout3_external_validation.md",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_external_validation_rows.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout3_expanded.json",
            "tables/learned_selector_report.json",
        ],
        "scripts": ["scripts/export_heldout3_external_validation.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_heldout3_external_validation.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "heldout4_external_validation_suites",
        "outputs": [
            "evaluations/heldout4_multiseed_suite/multiseed_suite_summary.json",
            "tables/heldout4_multiseed_suite_report.md",
            "tables/heldout4_multiseed_suite_rows.csv",
            "evaluations/heldout4_adaptive_suite/multiseed_suite_summary.json",
            "tables/heldout4_adaptive_suite_report.md",
            "tables/heldout4_adaptive_suite_rows.csv",
            "evaluations/heldout4_expert_gate_suite/multiseed_suite_summary.json",
            "tables/heldout4_expert_gate_suite_report.md",
            "tables/heldout4_expert_gate_suite_rows.csv",
            "evaluations/heldout4_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "tables/heldout4_graph_dagger_recovery_v2_suite_report.md",
            "tables/heldout4_graph_dagger_recovery_v2_suite_rows.csv",
            "evaluations/heldout4_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "tables/heldout4_dagger_v2_expert_more_graph_suite_report.md",
            "tables/heldout4_dagger_v2_expert_more_graph_suite_rows.csv",
            "evaluations/heldout4_traffic_adaptive_conservative_suite/multiseed_suite_summary.json",
            "tables/heldout4_traffic_adaptive_conservative_suite_report.md",
            "tables/heldout4_traffic_adaptive_conservative_suite_rows.csv",
        ],
        "inputs": [
            "models/graph_bc/graph_bc.graph.pt",
            "models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
            "models/heldout3_targeted_recovery/graph_dagger_recovery.graph.pt",
        ],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "Heldout4 full-rollout suites on unused prime seeds "
            "197,199,211,223,227,229,233,239,241,251 using cuda:0,cuda:1,cuda:2,cuda:3."
        ),
    },
    {
        "name": "online_probe_selector_1200_heldout4_targeted_expanded",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200_heldout4_targeted_expanded/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.md",
            "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded_rows.csv",
        ],
        "inputs": [
            "evaluations/heldout4_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_traffic_adaptive_conservative_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_portfolio_probe_selector.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200_heldout4_targeted_expanded "
            "--table-prefix portfolio_probe_selector_1200_heldout4_targeted_expanded --probe-steps 1200 "
            "--methods lane_base_only,overtake_base_only,graph_adaptive_shield,expert_gate_only,dagger_v2_graph_expert_gate_shield,dagger_v2_graph_expert_gate_more_graph,heldout3_traffic_adaptive_conservative "
            "--seeds 197,199,211,223,227,229,233,239,241,251 --devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4"
        ),
    },
    {
        "name": "heldout4_external_validation",
        "outputs": [
            "tables/heldout4_external_validation.md",
            "tables/heldout4_external_validation.json",
            "tables/heldout4_external_validation_rows.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json",
            "evaluations/heldout4_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_traffic_adaptive_conservative_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_heldout4_external_validation.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_heldout4_external_validation.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "cross_heldout_validation_synthesis",
        "outputs": [
            "tables/cross_heldout_validation_synthesis.md",
            "tables/cross_heldout_validation_synthesis.json",
            "tables/cross_heldout_validation_synthesis_rows.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout2_expanded.json",
            "tables/heldout3_external_validation.json",
            "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json",
            "tables/heldout4_external_validation.json",
        ],
        "scripts": ["scripts/export_cross_heldout_validation_synthesis.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_cross_heldout_validation_synthesis.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "heldout4_failure_atlas",
        "outputs": [
            "tables/heldout4_failure_atlas.md",
            "tables/heldout4_failure_atlas.json",
            "tables/heldout4_failure_atlas_seed_rows.csv",
            "tables/heldout4_failure_atlas_method_matrix.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json",
            "tables/heldout4_external_validation.json",
            "evaluations/heldout4_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_traffic_adaptive_conservative_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_heldout4_failure_atlas.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_heldout4_failure_atlas.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "cross_heldout_validation_figure",
        "outputs": [
            "figures/figure_3_cross_heldout_validation.png",
            "figures/figure_3_cross_heldout_validation.pdf",
            "figures/figure_3_cross_heldout_validation.svg",
            "figures/figure_3_cross_heldout_validation.tiff",
            "figures/figure_3_source_data.csv",
            "figures/figure_3_manifest.json",
        ],
        "inputs": [
            "tables/cross_heldout_validation_synthesis.json",
        ],
        "scripts": ["scripts/export_cross_heldout_validation_figure.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_cross_heldout_validation_figure.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "cross_heldout_statistical_supplement",
        "outputs": [
            "tables/cross_heldout_statistical_supplement.md",
            "tables/cross_heldout_statistical_supplement.json",
            "tables/cross_heldout_statistical_supplement_rows.csv",
            "figures/figure_3_source_data_dictionary.csv",
        ],
        "inputs": [
            "tables/cross_heldout_validation_synthesis.json",
            "tables/heldout4_external_validation.json",
            "figures/figure_3_source_data.csv",
        ],
        "scripts": ["scripts/export_cross_heldout_statistical_supplement.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_cross_heldout_statistical_supplement.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "seed_outcome_ledger",
        "outputs": [
            "tables/seed_outcome_ledger.md",
            "tables/seed_outcome_ledger.json",
            "tables/seed_outcome_ledger.csv",
            "tables/seed_outcome_ledger_stage_summary.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout2_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout3_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json",
        ],
        "scripts": ["scripts/export_seed_outcome_ledger.py"],
        "command": "python scripts/export_seed_outcome_ledger.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "heldout3_targeted_recovery_training",
        "outputs": [
            "models/heldout3_targeted_recovery/graph_dagger_recovery.graph.pt",
            "models/heldout3_targeted_recovery/train_summary.json",
        ],
        "inputs": ["models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/train_graph_dagger_recovery.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/train_graph_dagger_recovery.py "
            "--init-model outputs/paper_multicar_overtake_20260618/models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt "
            "--hard-seeds 157,173 --support-seeds 3,7,11,17,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,101,107,127,131,137,139 "
            "--oracle-policy expert_gate --target-speed 21.0 --repeats 1 --max-steps 3200 --train-steps 2600 "
            "--batch-size 4096 --lr 7e-5 --device cuda:0 --out-dir outputs/paper_multicar_overtake_20260618/models/heldout3_targeted_recovery"
        ),
    },
    {
        "name": "heldout3_targeted_recovery_suites",
        "outputs": [
            "evaluations/heldout3_targeted_recovery_suite/multiseed_suite_summary.json",
            "tables/heldout3_targeted_recovery_suite_report.md",
            "tables/heldout3_targeted_recovery_suite_rows.csv",
            "evaluations/heldout3_targeted_recovery_conservative_traffic_suite/multiseed_suite_summary.json",
            "tables/heldout3_targeted_recovery_conservative_traffic_suite_report.md",
            "tables/heldout3_targeted_recovery_conservative_traffic_suite_rows.csv",
        ],
        "inputs": ["models/heldout3_targeted_recovery/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "Two heldout3 targeted recovery suites using cuda:0,cuda:1,cuda:2,cuda:3; the conservative-traffic suite "
            "adds --baseline-policies telemetry_cruise,telemetry_yield,telemetry_adaptive_conservative."
        ),
    },
    {
        "name": "heldout3_candidate_expansion",
        "outputs": [
            "tables/heldout3_candidate_expansion.md",
            "tables/heldout3_candidate_expansion.json",
            "tables/heldout3_candidate_expansion_rows.csv",
        ],
        "inputs": [
            "tables/heldout3_external_validation.json",
            "tables/heldout3_targeted_recovery_suite_report.json",
            "tables/heldout3_targeted_recovery_conservative_traffic_suite_report.json",
            "tables/seed157_traffic_ablation.json",
            "evaluations/heldout3_targeted_recovery_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_targeted_recovery_conservative_traffic_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_heldout3_candidate_expansion.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_heldout3_candidate_expansion.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "heldout3_traffic_adaptive_conservative_suite",
        "outputs": [
            "evaluations/heldout3_traffic_adaptive_conservative_suite/multiseed_suite_summary.json",
            "tables/heldout3_traffic_adaptive_conservative_suite_report.md",
            "tables/heldout3_traffic_adaptive_conservative_suite_report.json",
            "tables/heldout3_traffic_adaptive_conservative_suite_rows.csv",
        ],
        "inputs": [
            "models/heldout3_targeted_recovery/graph_dagger_recovery.graph.pt",
            "tables/seed157_traffic_ablation.json",
        ],
        "scripts": ["scripts/run_multiseed_overtake_suite.py", "scripts/export_multiseed_suite_report.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_multiseed_overtake_suite.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/heldout3_traffic_adaptive_conservative_suite "
            "--model-path outputs/paper_multicar_overtake_20260618/models/heldout3_targeted_recovery/graph_dagger_recovery.graph.pt "
            "--methods heldout3_traffic_adaptive_conservative --seeds 149,151,157,163,167,173,179,181,191,193 "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --no-gif --no-trace"
        ),
    },
    {
        "name": "online_probe_selector_1200_heldout3_targeted_expanded",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200_heldout3_targeted_expanded/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.md",
            "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded_rows.csv",
        ],
        "inputs": [
            "evaluations/heldout3_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_traffic_adaptive_conservative_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_portfolio_probe_selector.py "
            "--root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200_heldout3_targeted_expanded "
            "--table-prefix portfolio_probe_selector_1200_heldout3_targeted_expanded --probe-steps 1200 "
            "--methods lane_base_only,overtake_base_only,graph_adaptive_shield,expert_gate_only,dagger_v2_graph_expert_gate_shield,dagger_v2_graph_expert_gate_more_graph,heldout3_traffic_adaptive_conservative "
            "--seeds 149,151,157,163,167,173,179,181,191,193 --devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4"
        ),
    },
    {
        "name": "heldout3_targeted_selector_generalization",
        "outputs": [
            "tables/heldout3_targeted_selector_generalization.md",
            "tables/heldout3_targeted_selector_generalization.json",
            "tables/heldout3_targeted_selector_generalization_rows.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout3_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json",
            "tables/heldout3_traffic_adaptive_conservative_suite_report.json",
            "tables/heldout3_candidate_expansion.json",
        ],
        "scripts": ["scripts/export_heldout3_targeted_selector_generalization.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_heldout3_targeted_selector_generalization.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "heldout3_targeted_meta_selector",
        "outputs": [
            "tables/heldout3_targeted_meta_selector.md",
            "tables/heldout3_targeted_meta_selector.json",
            "tables/heldout3_targeted_meta_selector_rows.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json",
            "tables/heldout3_targeted_selector_generalization.json",
        ],
        "scripts": ["scripts/export_heldout3_targeted_meta_selector.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_heldout3_targeted_meta_selector.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "seed157_traffic_ablation",
        "outputs": [
            "evaluations/seed157_traffic_ablation",
            "tables/seed157_traffic_ablation.md",
            "tables/seed157_traffic_ablation.json",
            "tables/seed157_traffic_ablation_rows.csv",
        ],
        "inputs": ["models/heldout3_targeted_recovery/graph_dagger_recovery.graph.pt"],
        "scripts": ["scripts/run_seed157_traffic_ablation.py"],
        "command": (
            "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/run_seed157_traffic_ablation.py "
            "--root outputs/paper_multicar_overtake_20260618 --out-dir outputs/paper_multicar_overtake_20260618/evaluations/seed157_traffic_ablation "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4"
        ),
    },
    {
        "name": "dagger_v2_heldout2_failure_diagnosis",
        "outputs": [
            "tables/dagger_v2_heldout2_failure_diagnosis.json",
            "tables/dagger_v2_heldout2_failure_diagnosis.md",
            "tables/dagger_v2_heldout2_failure_diagnosis_rows.csv",
        ],
        "inputs": ["evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json"],
        "scripts": ["scripts/export_dagger_failure_diagnosis.py"],
        "command": (
            "python scripts/export_dagger_failure_diagnosis.py --root outputs/paper_multicar_overtake_20260618 "
            "--suite outputs/paper_multicar_overtake_20260618/evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json "
            "--prefix dagger_v2_heldout2_failure_diagnosis"
        ),
    },
    {
        "name": "online_probe_selector_1200_heldout2_dagger_v2",
        "outputs": [
            "evaluations/portfolio_probe_selector_1200_heldout2_dagger_v2/portfolio_probe_selector_summary.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.md",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2_rows.csv",
        ],
        "inputs": [
            "models/graph_bc/graph_bc.graph.pt",
            "models/graph_dagger_recovery_v2/graph_dagger_recovery.graph.pt",
            "evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/run_portfolio_probe_selector.py"],
        "command": (
            "python scripts/run_portfolio_probe_selector.py --root outputs/paper_multicar_overtake_20260618 "
            "--out-dir outputs/paper_multicar_overtake_20260618/evaluations/portfolio_probe_selector_1200_heldout2_dagger_v2 "
            "--table-prefix portfolio_probe_selector_1200_heldout2_dagger_v2 "
            "--methods lane_base_only,overtake_base_only,graph_adaptive_shield,expert_gate_only,dagger_v2_graph_expert_gate_shield "
            "--probe-steps 1200 --seeds 97,101,103,107,109,113,127,131,137,139 "
            "--full-suite-main evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json "
            "--full-suite-adaptive evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json "
            "--full-suite-expert evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json "
            "--full-suite-dagger-v2 evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json "
            "--devices cuda:0,cuda:1,cuda:2,cuda:3 --parallel 4 --skip-existing"
        ),
    },
    {
        "name": "heldout_generalization",
        "outputs": [
            "tables/heldout_generalization.json",
            "tables/heldout_generalization.md",
            "tables/heldout_generalization_method_rows.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
            "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_heldout_generalization_report.py"],
        "command": "python scripts/export_heldout_generalization_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "selector_calibration",
        "outputs": [
            "tables/selector_calibration.json",
            "tables/selector_calibration.md",
            "tables/selector_calibration_decisions.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
        ],
        "scripts": ["scripts/export_selector_calibration_report.py"],
        "command": "python scripts/export_selector_calibration_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "selector_distillation_report",
        "outputs": [
            "tables/selector_distillation_report.json",
            "tables/selector_distillation_report.md",
            "tables/selector_distillation_grid.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
            "tables/heldout2_failure_atlas.json",
        ],
        "scripts": ["scripts/export_selector_distillation_report.py"],
        "command": "python scripts/export_selector_distillation_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "claim_evidence_matrix",
        "outputs": [
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/CLAIM_EVIDENCE_MATRIX.md",
            "materials/CLAIM_EVIDENCE_MATRIX.csv",
        ],
        "inputs": [
            "tables/full_statistical_report.json",
            "tables/heldout_generalization.json",
            "tables/selector_calibration.json",
            "tables/selector_distillation_report.json",
            "tables/heldout2_candidate_expansion.json",
            "tables/heldout_v2_portfolio.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
            "tables/reproducibility_audit.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_claim_evidence_matrix.py"],
        "command": "python scripts/export_claim_evidence_matrix.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "claim_boundary_communication_pack",
        "outputs": [
            "materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json",
            "materials/CLAIM_DOWNGRADE_MAP.md",
            "materials/CLAIM_DOWNGRADE_MAP.csv",
            "materials/WHAT_THIS_PAPER_DOES_NOT_CLAIM.md",
            "materials/WHAT_THIS_PAPER_DOES_NOT_CLAIM.csv",
        ],
        "inputs": [
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "materials/RESEARCH_RISK_AND_SAFETY.md",
            "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md",
            "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md",
        ],
        "scripts": ["scripts/export_claim_boundary_communication_pack.py"],
        "command": "python scripts/export_claim_boundary_communication_pack.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "manuscript_results_discussion_draft",
        "outputs": ["materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md"],
        "inputs": [
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "tables/full_statistical_report.json",
            "tables/heldout_generalization.json",
            "tables/selector_calibration.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
            "figures/figure_manifest.json",
            "figures/figure_2_manifest.json",
        ],
        "scripts": ["scripts/export_manuscript_results_discussion.py"],
        "command": "python scripts/export_manuscript_results_discussion.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "manuscript_claim_qa",
        "outputs": [
            "materials/MANUSCRIPT_CLAIM_QA.json",
            "materials/MANUSCRIPT_CLAIM_QA.md",
            "materials/MANUSCRIPT_CLAIM_QA.csv",
        ],
        "inputs": [
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "manuscript/main.md",
            "materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
            "materials/MANUSCRIPT_OUTLINE.md",
            "materials/PUBLICATION_PACKAGE_SUMMARY.md",
            "materials/TOP_JOURNAL_READINESS_CHECKLIST.md",
            "materials/TOP_JOURNAL_READINESS_CHECKLIST.json",
            "materials/TOP_JOURNAL_READINESS_CHECKLIST.csv",
        ],
        "scripts": ["scripts/export_manuscript_claim_qa.py"],
        "command": "python scripts/export_manuscript_claim_qa.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "package_manifest",
        "outputs": ["manifest.json"],
        "inputs": [
            "tables/full_statistical_report.json",
            "tables/heldout_generalization.json",
            "tables/selector_calibration.json",
            "tables/artifact_provenance.json",
            "tables/reproducibility_audit.json",
            "figures/figure_2_manifest.json",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "tables/selector_distillation_report.json",
            "tables/heldout2_candidate_expansion.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
        ],
        "scripts": ["scripts/export_package_manifest.py"],
        "command": "python scripts/export_package_manifest.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "main_figure",
        "outputs": [
            "figures/figure_1_multicar_overtake_results.png",
            "figures/figure_1_multicar_overtake_results.pdf",
            "figures/figure_1_multicar_overtake_results.svg",
            "figures/figure_1_multicar_overtake_results.tiff",
            "figures/figure_1_source_data.csv",
            "figures/figure_manifest.json",
        ],
        "inputs": ["evaluations/multiseed_suite/multiseed_suite_summary.json", "ablations/ablation_summary.json"],
        "scripts": ["scripts/export_paper_figures.py"],
        "command": "python scripts/export_paper_figures.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "portfolio_selector_figure",
        "outputs": [
            "figures/figure_2_portfolio_selector_summary.png",
            "figures/figure_2_portfolio_selector_summary.pdf",
            "figures/figure_2_portfolio_selector_summary.svg",
            "figures/figure_2_portfolio_selector_summary.tiff",
            "figures/figure_2_source_data.csv",
            "figures/figure_2_manifest.json",
        ],
        "inputs": [
            "tables/full_statistical_report.json",
            "tables/portfolio_oracle.json",
            "tables/portfolio_selector_loso.json",
            "tables/portfolio_probe_selector.json",
            "tables/portfolio_probe_selector_1200.json",
            "tables/portfolio_probe_selector_1200_heldout.json",
            "tables/portfolio_probe_selector_1200_heldout_expert.json",
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
            "tables/heldout_generalization.json",
            "tables/selector_calibration.json",
            "tables/heldout_expert_fast_smoke_report.json",
        ],
        "scripts": ["scripts/export_supplementary_figure.py"],
        "command": "python scripts/export_supplementary_figure.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "figure_legends",
        "outputs": [
            "materials/FIGURE_LEGENDS.md",
            "materials/FIGURE_LEGENDS.json",
        ],
        "inputs": [
            "figures/figure_manifest.json",
            "figures/figure_2_manifest.json",
            "figures/figure_3_manifest.json",
        ],
        "scripts": ["scripts/export_figure_legends.py"],
        "command": "PYTHONPATH=. /home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_figure_legends.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reproducibility_audit",
        "outputs": ["tables/reproducibility_audit.md", "tables/reproducibility_audit.json"],
        "inputs": ["manifest.json", "materials/SUPPLEMENTARY_INDEX.md"],
        "scripts": ["scripts/export_reproducibility_audit.py"],
        "command": "python scripts/export_reproducibility_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "publication_package_summary",
        "outputs": [
            "materials/PUBLICATION_PACKAGE_SUMMARY.md",
            "materials/PUBLICATION_PACKAGE_SUMMARY.json",
            "materials/TOP_JOURNAL_READINESS_CHECKLIST.md",
            "materials/TOP_JOURNAL_READINESS_CHECKLIST.json",
            "materials/TOP_JOURNAL_READINESS_CHECKLIST.csv",
        ],
        "inputs": [
            "manifest.json",
            "tables/full_statistical_report.json",
            "tables/heldout_generalization.json",
            "tables/selector_calibration.json",
            "tables/heldout2_candidate_expansion.json",
            "tables/artifact_provenance.json",
            "tables/reproducibility_audit.json",
        ],
        "scripts": ["scripts/export_publication_package_summary.py"],
        "command": "python scripts/export_publication_package_summary.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "statistical_analysis_plan",
        "outputs": [
            "materials/STATISTICAL_ANALYSIS_PLAN.md",
            "materials/STATISTICAL_ANALYSIS_PLAN.json",
        ],
        "inputs": [
            "manifest.json",
            "tables/full_statistical_report.json",
            "tables/heldout_generalization.json",
            "tables/selector_calibration.json",
        ],
        "scripts": ["scripts/export_statistical_analysis_plan.py"],
        "command": "python scripts/export_statistical_analysis_plan.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "statistical_analysis_plan_audit",
        "outputs": [
            "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.md",
            "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.json",
            "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.csv",
        ],
        "inputs": [
            "materials/STATISTICAL_ANALYSIS_PLAN.json",
            "tables/full_statistical_report.json",
            "tables/cross_heldout_statistical_supplement.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.json",
            "materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/STATISTICAL_REPORTING_APPENDIX.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_statistical_analysis_plan_audit.py"],
        "command": "python scripts/export_statistical_analysis_plan_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "data_code_availability",
        "outputs": [
            "materials/DATA_CODE_AVAILABILITY.md",
            "materials/DATA_CODE_AVAILABILITY.json",
            "materials/DATA_CODE_AVAILABILITY.csv",
        ],
        "inputs": [
            "manifest.json",
            "tables/artifact_provenance.json",
            "tables/reproducibility_audit.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
        ],
        "scripts": ["scripts/export_data_code_availability.py"],
        "command": "python scripts/export_data_code_availability.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "heldout2_failure_atlas",
        "outputs": [
            "tables/heldout2_failure_atlas.md",
            "tables/heldout2_failure_atlas.json",
            "tables/heldout2_failure_atlas_seed_rows.csv",
            "tables/heldout2_failure_atlas_method_matrix.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
            "tables/selector_calibration.json",
            "tables/heldout_generalization.json",
            "evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_heldout2_failure_atlas.py"],
        "command": "python scripts/export_heldout2_failure_atlas.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "heldout2_candidate_expansion",
        "outputs": [
            "tables/heldout2_candidate_expansion.md",
            "tables/heldout2_candidate_expansion.json",
            "tables/heldout2_candidate_expansion_rows.csv",
        ],
        "inputs": [
            "tables/heldout2_failure_atlas.json",
            "tables/heldout2_overtake_conservative_traffic_targeted_report.json",
            "tables/heldout2_dagger_v2_recovery_conservative_suite_report.json",
            "tables/heldout2_dagger_v2_expert_more_graph_suite_report.json",
            "evaluations/heldout2_overtake_conservative_traffic_targeted/multiseed_suite_summary.json",
            "evaluations/heldout2_dagger_v2_recovery_conservative_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
        ],
        "scripts": ["scripts/export_heldout2_candidate_expansion.py"],
        "command": "python scripts/export_heldout2_candidate_expansion.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "manuscript_outline",
        "outputs": [
            "materials/MANUSCRIPT_OUTLINE.md",
            "materials/MANUSCRIPT_OUTLINE.json",
        ],
        "inputs": [
            "manifest.json",
            "tables/full_statistical_report.json",
            "tables/heldout_generalization.json",
            "tables/selector_calibration.json",
            "tables/heldout2_failure_atlas.json",
            "tables/heldout2_candidate_expansion.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
        ],
        "scripts": ["scripts/export_manuscript_outline.py"],
        "command": "python scripts/export_manuscript_outline.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reviewer_response_map",
        "outputs": [
            "materials/REVIEWER_RESPONSE_MAP.md",
            "materials/REVIEWER_RESPONSE_MAP.json",
            "materials/REVIEWER_RESPONSE_MAP.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/MANUSCRIPT_OUTLINE.json",
            "materials/STATISTICAL_ANALYSIS_PLAN.json",
            "tables/heldout2_failure_atlas.json",
            "tables/selector_calibration.json",
            "tables/heldout_generalization.json",
            "tables/full_statistical_report.json",
            "tables/artifact_provenance.json",
            "tables/reproducibility_audit.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
        ],
        "scripts": ["scripts/export_reviewer_response_map.py"],
        "command": "python scripts/export_reviewer_response_map.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "transparent_reporting_checklist",
        "outputs": [
            "materials/TRANSPARENT_REPORTING_CHECKLIST.md",
            "materials/TRANSPARENT_REPORTING_CHECKLIST.json",
            "materials/TRANSPARENT_REPORTING_CHECKLIST.csv",
        ],
        "inputs": [
            "manifest.json",
            "tables/reproducibility_audit.json",
            "tables/artifact_provenance.json",
            "tables/heldout_generalization.json",
            "tables/selector_calibration.json",
            "tables/heldout2_failure_atlas.json",
            "materials/STATISTICAL_ANALYSIS_PLAN.json",
            "materials/DATA_CODE_AVAILABILITY.json",
            "materials/REVIEWER_RESPONSE_MAP.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
        ],
        "scripts": ["scripts/export_transparent_reporting_checklist.py"],
        "command": "python scripts/export_transparent_reporting_checklist.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "policy_model_card",
        "outputs": [
            "materials/POLICY_MODEL_CARD.md",
            "materials/POLICY_MODEL_CARD.json",
            "materials/POLICY_MODEL_CARD.csv",
        ],
        "inputs": [
            "models/graph_bc/train_summary.json",
            "models/graph_dagger_recovery/train_summary.json",
            "models/graph_dagger_recovery_v2/train_summary.json",
            "models/heldout3_targeted_recovery/train_summary.json",
            "materials/METHODS.md",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "tables/full_statistical_report.json",
            "tables/learned_selector_report.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_policy_model_card.py"],
        "command": "python scripts/export_policy_model_card.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "study_protocol_and_deviations",
        "outputs": [
            "materials/STUDY_PROTOCOL_AND_DEVIATIONS.md",
            "materials/STUDY_PROTOCOL_AND_DEVIATIONS.json",
            "materials/STUDY_PROTOCOL_AND_DEVIATIONS.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/EXPERIMENT_REGISTRY.json",
            "materials/STATISTICAL_ANALYSIS_PLAN.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/POLICY_MODEL_CARD.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_study_protocol_and_deviations.py"],
        "command": "python scripts/export_study_protocol_and_deviations.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "baseline_fairness_audit",
        "outputs": [
            "materials/BASELINE_FAIRNESS_AUDIT.md",
            "materials/BASELINE_FAIRNESS_AUDIT.json",
            "materials/BASELINE_FAIRNESS_AUDIT.csv",
        ],
        "inputs": [
            "manifest.json",
            "tables/full_statistical_report.json",
            "materials/POLICY_MODEL_CARD.json",
            "materials/STUDY_PROTOCOL_AND_DEVIATIONS.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/compute_cost_report.json",
        ],
        "scripts": ["scripts/export_baseline_fairness_audit.py"],
        "command": "python scripts/export_baseline_fairness_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "software_dependency_license_audit",
        "outputs": [
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.md",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.csv",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_DEPENDENCIES.csv",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_METADATA.csv",
        ],
        "inputs": [
            "materials/repo_metadata/LICENSE",
            "materials/repo_metadata/AUTHORS",
            "materials/repo_metadata/setup.py",
            "materials/repo_metadata/environment.yml",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_software_dependency_license_audit.py"],
        "command": "python scripts/export_software_dependency_license_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "submission_gap_action_plan",
        "outputs": [
            "materials/SUBMISSION_GAP_ACTION_PLAN.md",
            "materials/SUBMISSION_GAP_ACTION_PLAN.json",
            "materials/SUBMISSION_GAP_ACTION_PLAN.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/TRANSPARENT_REPORTING_CHECKLIST.json",
            "materials/REVIEWER_RESPONSE_MAP.json",
            "tables/heldout2_failure_atlas.json",
            "tables/heldout2_candidate_expansion.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
        ],
        "scripts": ["scripts/export_submission_gap_action_plan.py"],
        "command": "python scripts/export_submission_gap_action_plan.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "compute_cost_report",
        "outputs": [
            "tables/compute_cost_report.md",
            "tables/compute_cost_report.json",
            "tables/compute_cost_suite_rows.csv",
            "tables/compute_cost_selector_rows.csv",
        ],
        "inputs": [
            "manifest.json",
            "evaluations/multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
        ],
        "scripts": ["scripts/export_compute_cost_report.py"],
        "command": "python scripts/export_compute_cost_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "release_archive_manifest",
        "outputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.md",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/README.md",
            "materials/REPRODUCTION_GUIDE.md",
            "tables/artifact_provenance.md",
            "tables/reproducibility_audit.md",
        ],
        "scripts": ["scripts/export_release_archive_manifest.py"],
        "command": "python scripts/export_release_archive_manifest.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "release_provenance_coverage_audit",
        "outputs": [
            "materials/RELEASE_PROVENANCE_COVERAGE_AUDIT.md",
            "materials/RELEASE_PROVENANCE_COVERAGE_AUDIT.json",
            "materials/RELEASE_PROVENANCE_COVERAGE_AUDIT.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "tables/artifact_provenance.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/DATA_DICTIONARY.json",
            "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json",
            "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json",
        ],
        "scripts": ["scripts/export_release_provenance_coverage_audit.py"],
        "command": "python scripts/export_release_provenance_coverage_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "final_checksum_freeze_record",
        "outputs": [
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.md",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.csv",
            "materials/FINAL_CHECKSUM_FREEZE_FILE_SNAPSHOTS.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "tables/artifact_provenance.json",
            "materials/DATA_DICTIONARY.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/CITATION_METADATA.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
        ],
        "scripts": ["scripts/export_final_checksum_freeze_record.py"],
        "command": "python scripts/export_final_checksum_freeze_record.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "environment_reproducibility_audit",
        "outputs": [
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/REPRODUCTION_GUIDE.md",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
        ],
        "scripts": ["scripts/export_environment_reproducibility_audit.py"],
        "command": "python scripts/export_environment_reproducibility_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "fair_archive_metadata",
        "outputs": [
            "materials/FAIR_ARCHIVE_METADATA.md",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/FAIR_ARCHIVE_METADATA.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/DATA_CODE_AVAILABILITY.json",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_SUMMARY.json",
            "materials/DATA_DICTIONARY.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_fair_archive_metadata.py"],
        "command": "python scripts/export_fair_archive_metadata.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "research_risk_and_safety",
        "outputs": [
            "materials/RESEARCH_RISK_AND_SAFETY.md",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/RESEARCH_RISK_AND_SAFETY.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/SUBMISSION_GAP_ACTION_PLAN.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json",
        ],
        "scripts": ["scripts/export_research_risk_and_safety_statement.py"],
        "command": "python scripts/export_research_risk_and_safety_statement.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "simulation_to_real_applicability",
        "outputs": [
            "materials/SIMULATION_TO_REAL_APPLICABILITY.md",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.json",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_simulation_to_real_applicability.py"],
        "command": "python scripts/export_simulation_to_real_applicability.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "top_journal_reporting_summary",
        "outputs": [
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/STATISTICAL_ANALYSIS_PLAN.json",
            "materials/DATA_CODE_AVAILABILITY.json",
            "materials/EXPERIMENT_REGISTRY.json",
            "tables/seed_outcome_ledger.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
        ],
        "scripts": ["scripts/export_top_journal_reporting_summary.py"],
        "command": "python scripts/export_top_journal_reporting_summary.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "editorial_submission_checklist",
        "outputs": [
            "materials/EDITORIAL_SUBMISSION_CHECKLIST.md",
            "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
            "materials/EDITORIAL_SUBMISSION_CHECKLIST.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_SUMMARY.json",
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/DATA_DICTIONARY.json",
            "manuscript/manuscript_manifest.json",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json",
        ],
        "scripts": ["scripts/export_editorial_submission_checklist.py"],
        "command": "python scripts/export_editorial_submission_checklist.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "significance_briefing",
        "outputs": [
            "materials/SIGNIFICANCE_BRIEFING.md",
            "materials/SIGNIFICANCE_BRIEFING.json",
            "materials/SIGNIFICANCE_BRIEFING.csv",
        ],
        "inputs": [
            "materials/MANUSCRIPT_OUTLINE.json",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/PUBLICATION_PACKAGE_SUMMARY.json",
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.json",
            "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_significance_briefing.py"],
        "command": "python scripts/export_significance_briefing.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "external_validity_boundary_audit",
        "outputs": [
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.csv",
        ],
        "inputs": [
            "tables/cross_heldout_validation_synthesis.json",
            "tables/cross_heldout_statistical_supplement.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
            "tables/heldout4_external_validation.json",
            "tables/heldout4_failure_atlas.json",
            "tables/learned_selector_report.json",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_external_validity_boundary_audit.py"],
        "command": "python scripts/export_external_validity_boundary_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "negative_results_failure_register",
        "outputs": [
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.md",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.csv",
        ],
        "inputs": [
            "tables/heldout2_failure_atlas.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
            "tables/heldout4_failure_atlas.json",
            "tables/heldout_expert_fast_smoke_report.json",
            "tables/heldout_expert_barrier_smoke_report.json",
            "tables/heldout_expert_recovery_smoke_report.json",
            "tables/dagger_failure_diagnosis.json",
            "tables/dagger_v2_heldout_failure_diagnosis.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_negative_results_failure_register.py"],
        "command": "python scripts/export_negative_results_failure_register.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "sample_size_sensitivity_brief",
        "outputs": [
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.md",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_STAGE_ROWS.csv",
            "materials/SAMPLE_SIZE_SENSITIVITY_PLANNING_GRID.csv",
            "materials/SAMPLE_SIZE_SENSITIVITY_THRESHOLD_GRID.csv",
        ],
        "inputs": [
            "tables/cross_heldout_statistical_supplement.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/STATISTICAL_ANALYSIS_PLAN.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_sample_size_sensitivity_brief.py"],
        "command": "python scripts/export_sample_size_sensitivity_brief.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "threats_to_validity_audit",
        "outputs": [
            "materials/THREATS_TO_VALIDITY_AUDIT.md",
            "materials/THREATS_TO_VALIDITY_AUDIT.json",
            "materials/THREATS_TO_VALIDITY_AUDIT.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/SEED_PARTITION_AUDIT.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/SELECTOR_DECISION_AUDIT.json",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/VISUAL_EVIDENCE_AUDIT.json",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/FIGURE_TECHNICAL_QC.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
        ],
        "scripts": ["scripts/export_threats_to_validity_audit.py"],
        "command": "python scripts/export_threats_to_validity_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "manuscript_limitation_integration_audit",
        "outputs": [
            "materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.md",
            "materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.json",
            "materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.csv",
        ],
        "inputs": [
            "manuscript/main.md",
            "materials/THREATS_TO_VALIDITY_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_manuscript_limitation_integration_audit.py"],
        "command": "python scripts/export_manuscript_limitation_integration_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "figure_source_data_audit",
        "outputs": [
            "materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.csv",
            "materials/FIGURE_SOURCE_DATA_FILE_EDGES.csv",
        ],
        "inputs": [
            "figures/figure_manifest.json",
            "figures/figure_2_manifest.json",
            "figures/figure_3_manifest.json",
            "figures/figure_1_source_data.csv",
            "figures/figure_2_source_data.csv",
            "figures/figure_3_source_data.csv",
            "materials/FIGURE_LEGENDS.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_figure_source_data_audit.py"],
        "command": "python scripts/export_figure_source_data_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "figure_technical_qc",
        "outputs": [
            "materials/FIGURE_TECHNICAL_QC.md",
            "materials/FIGURE_TECHNICAL_QC.json",
            "materials/FIGURE_TECHNICAL_QC.csv",
            "materials/FIGURE_TECHNICAL_QC_FILE_ROWS.csv",
        ],
        "inputs": [
            "figures/figure_manifest.json",
            "figures/figure_2_manifest.json",
            "figures/figure_3_manifest.json",
            "figures/figure_1_multicar_overtake_results.pdf",
            "figures/figure_1_multicar_overtake_results.tiff",
            "figures/figure_1_multicar_overtake_results.png",
            "figures/figure_1_multicar_overtake_results.svg",
            "figures/figure_2_portfolio_selector_summary.pdf",
            "figures/figure_2_portfolio_selector_summary.tiff",
            "figures/figure_2_portfolio_selector_summary.png",
            "figures/figure_2_portfolio_selector_summary.svg",
            "figures/figure_3_cross_heldout_validation.pdf",
            "figures/figure_3_cross_heldout_validation.tiff",
            "figures/figure_3_cross_heldout_validation.png",
            "figures/figure_3_cross_heldout_validation.svg",
            "figures/figure_1_source_data.csv",
            "figures/figure_2_source_data.csv",
            "figures/figure_3_source_data.csv",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_figure_technical_qc.py"],
        "command": "python scripts/export_figure_technical_qc.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "figure_accessibility_qc",
        "outputs": [
            "materials/FIGURE_ACCESSIBILITY_QC.md",
            "materials/FIGURE_ACCESSIBILITY_QC.json",
            "materials/FIGURE_ACCESSIBILITY_QC.csv",
        ],
        "inputs": [
            "materials/FIGURE_TECHNICAL_QC.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_figure_accessibility_qc.py"],
        "command": "python scripts/export_figure_accessibility_qc.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "statistical_consistency_audit",
        "outputs": [
            "materials/STATISTICAL_CONSISTENCY_AUDIT.md",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.csv",
        ],
        "inputs": [
            "tables/full_statistical_report.json",
            "tables/full_statistical_report_method_summary.csv",
            "tables/cross_heldout_validation_synthesis.json",
            "tables/cross_heldout_statistical_supplement.json",
            "tables/cross_heldout_statistical_supplement_rows.csv",
            "figures/figure_3_source_data.csv",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_statistical_consistency_audit.py"],
        "command": "python scripts/export_statistical_consistency_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "cross_material_consistency_audit",
        "outputs": [
            "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.md",
            "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json",
            "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "tables/artifact_provenance.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/DATA_DICTIONARY.json",
        ],
        "scripts": ["scripts/export_cross_material_consistency_audit.py"],
        "command": "python scripts/export_cross_material_consistency_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "narrative_numeric_consistency_audit",
        "outputs": [
            "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.md",
            "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json",
            "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/STATISTICAL_ANALYSIS_PLAN_AUDIT.json",
            "materials/DATA_DICTIONARY.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_narrative_numeric_consistency_audit.py"],
        "command": "python scripts/export_narrative_numeric_consistency_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "endpoint_sensitivity_audit",
        "outputs": [
            "materials/ENDPOINT_SENSITIVITY_AUDIT.md",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.json",
            "materials/ENDPOINT_SENSITIVITY_SCENARIO_ROWS.csv",
            "materials/ENDPOINT_SENSITIVITY_METHOD_SUMMARY.csv",
            "materials/ENDPOINT_SENSITIVITY_GATE_ROWS.csv",
            "materials/ENDPOINT_SENSITIVITY_NEAR_THRESHOLD_ROWS.csv",
        ],
        "inputs": [
            "evaluations/multiseed_suite/multiseed_suite_summary.json",
            "evaluations/adaptive_gate_suite/multiseed_suite_summary.json",
            "evaluations/recovery_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_dagger_v2_recovery_conservative_suite/multiseed_suite_summary.json",
            "evaluations/heldout2_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_traffic_adaptive_conservative_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_targeted_recovery_suite/multiseed_suite_summary.json",
            "evaluations/heldout3_targeted_recovery_conservative_traffic_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_multiseed_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_adaptive_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_expert_gate_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_graph_dagger_recovery_v2_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_dagger_v2_expert_more_graph_suite/multiseed_suite_summary.json",
            "evaluations/heldout4_traffic_adaptive_conservative_suite/multiseed_suite_summary.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_endpoint_sensitivity_audit.py"],
        "command": "python scripts/export_endpoint_sensitivity_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "selector_decision_audit",
        "outputs": [
            "materials/SELECTOR_DECISION_AUDIT.md",
            "materials/SELECTOR_DECISION_AUDIT.json",
            "materials/SELECTOR_DECISION_AUDIT_STAGE_ROWS.csv",
            "materials/SELECTOR_DECISION_AUDIT_ROWS.csv",
        ],
        "inputs": [
            "tables/portfolio_probe_selector.json",
            "tables/portfolio_probe_selector_1200.json",
            "tables/portfolio_probe_selector_1200_heldout_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout2_dagger_v2.json",
            "tables/portfolio_probe_selector_1200_heldout_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout2_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout3_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout3_targeted_expanded.json",
            "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_selector_decision_audit.py"],
        "command": "python scripts/export_selector_decision_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "seed_partition_audit",
        "outputs": [
            "materials/SEED_PARTITION_AUDIT.md",
            "materials/SEED_PARTITION_AUDIT.json",
            "materials/SEED_PARTITION_SEED_SETS.csv",
            "materials/SEED_PARTITION_OVERLAPS.csv",
            "materials/SEED_PARTITION_EXPERIMENT_ROWS.csv",
            "materials/SEED_PARTITION_PROTOCOL_ROWS.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/EXPERIMENT_REGISTRY.json",
            "materials/STUDY_PROTOCOL_AND_DEVIATIONS.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_seed_partition_audit.py"],
        "command": "python scripts/export_seed_partition_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "artifact_dependency_map",
        "outputs": [
            "materials/ARTIFACT_DEPENDENCY_MAP.md",
            "materials/ARTIFACT_DEPENDENCY_MAP.json",
            "materials/ARTIFACT_DEPENDENCY_MAP.csv",
            "materials/ARTIFACT_DEPENDENCY_FILE_EDGES.csv",
        ],
        "inputs": [
            "tables/artifact_provenance.json",
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
        ],
        "scripts": ["scripts/export_artifact_dependency_map.py"],
        "command": "python scripts/export_artifact_dependency_map.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "experiment_registry",
        "outputs": [
            "materials/EXPERIMENT_REGISTRY.md",
            "materials/EXPERIMENT_REGISTRY.json",
            "materials/EXPERIMENT_REGISTRY.csv",
        ],
        "inputs": [
            "manifest.json",
            "tables/full_statistical_report.json",
            "tables/heldout_generalization.json",
            "tables/expanded_selector_generalization.json",
            "tables/learned_selector_report.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
            "tables/heldout4_external_validation.json",
            "tables/cross_heldout_validation_synthesis.json",
            "tables/cross_heldout_statistical_supplement.json",
            "tables/artifact_provenance.json",
            "tables/reproducibility_audit.json",
        ],
        "scripts": ["scripts/export_experiment_registry.py"],
        "command": "python scripts/export_experiment_registry.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "publication_package_verification",
        "outputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.md",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.csv",
        ],
        "inputs": [
            "tables/artifact_provenance.json",
            "tables/reproducibility_audit.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
            "materials/EXPERIMENT_REGISTRY.json",
            "tables/seed_outcome_ledger.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/DATA_DICTIONARY.json",
            "materials/POLICY_MODEL_CARD.json",
            "materials/STUDY_PROTOCOL_AND_DEVIATIONS.json",
            "materials/BASELINE_FAIRNESS_AUDIT.json",
        ],
        "scripts": ["scripts/export_publication_package_verification.py"],
        "command": "python scripts/export_publication_package_verification.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "data_dictionary",
        "outputs": [
            "materials/DATA_DICTIONARY.md",
            "materials/DATA_DICTIONARY.json",
            "materials/DATA_DICTIONARY.csv",
        ],
        "inputs": [
            "tables/seed_outcome_ledger.csv",
            "tables/seed_outcome_ledger_stage_summary.csv",
            "materials/EXPERIMENT_REGISTRY.csv",
            "tables/cross_heldout_validation_synthesis_rows.csv",
            "tables/cross_heldout_statistical_supplement_rows.csv",
            "figures/figure_3_source_data.csv",
            "tables/heldout4_failure_atlas_seed_rows.csv",
            "tables/heldout4_failure_atlas_method_matrix.csv",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.csv",
            "materials/FAIR_ARCHIVE_METADATA.csv",
            "materials/RESEARCH_RISK_AND_SAFETY.csv",
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.csv",
            "materials/EDITORIAL_SUBMISSION_CHECKLIST.csv",
            "materials/SIGNIFICANCE_BRIEFING.csv",
            "materials/ARTIFACT_DEPENDENCY_MAP.csv",
            "materials/ARTIFACT_DEPENDENCY_FILE_EDGES.csv",
            "materials/TRANSPARENT_REPORTING_CHECKLIST.csv",
            "materials/CLAIM_EVIDENCE_MATRIX.csv",
            "materials/POLICY_MODEL_CARD.csv",
            "materials/STUDY_PROTOCOL_AND_DEVIATIONS.csv",
            "materials/BASELINE_FAIRNESS_AUDIT.csv",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.csv",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_DEPENDENCIES.csv",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_METADATA.csv",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.csv",
            "materials/ENDPOINT_SENSITIVITY_SCENARIO_ROWS.csv",
            "materials/ENDPOINT_SENSITIVITY_METHOD_SUMMARY.csv",
            "materials/ENDPOINT_SENSITIVITY_GATE_ROWS.csv",
            "materials/ENDPOINT_SENSITIVITY_NEAR_THRESHOLD_ROWS.csv",
            "materials/SELECTOR_DECISION_AUDIT_STAGE_ROWS.csv",
            "materials/SELECTOR_DECISION_AUDIT_ROWS.csv",
            "materials/SEED_PARTITION_SEED_SETS.csv",
            "materials/SEED_PARTITION_OVERLAPS.csv",
            "materials/SEED_PARTITION_EXPERIMENT_ROWS.csv",
            "materials/SEED_PARTITION_PROTOCOL_ROWS.csv",
        ],
        "scripts": ["scripts/export_data_dictionary.py"],
        "command": "python scripts/export_data_dictionary.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "manuscript_draft_package",
        "outputs": [
            "manuscript/main.md",
            "manuscript/README.md",
            "manuscript/references.bib",
            "manuscript/manuscript_manifest.json",
            "manuscript/figures/README.md",
        ],
        "inputs": [
            "manifest.json",
            "materials/MANUSCRIPT_OUTLINE.json",
            "materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
            "materials/CLAIM_EVIDENCE_MATRIX.md",
            "tables/heldout_generalization.json",
            "tables/selector_calibration.json",
            "tables/selector_distillation_report.json",
            "tables/heldout2_candidate_expansion.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_candidate_expansion.json",
            "tables/compute_cost_report.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
        ],
        "scripts": ["scripts/export_manuscript_draft_package.py"],
        "command": "python scripts/export_manuscript_draft_package.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "manuscript_source_package",
        "outputs": [
            "manuscript/main.tex",
            "manuscript/SOURCE_PACKAGE_README.md",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.md",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.json",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.csv",
        ],
        "inputs": [
            "manuscript/main.md",
            "manuscript/references.bib",
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_manuscript_source_package.py"],
        "command": "python scripts/export_manuscript_source_package.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "manuscript_compile_preflight",
        "outputs": [
            "materials/MANUSCRIPT_COMPILE_PREFLIGHT.md",
            "materials/MANUSCRIPT_COMPILE_PREFLIGHT.json",
            "materials/MANUSCRIPT_COMPILE_PREFLIGHT.csv",
        ],
        "inputs": [
            "manuscript/main.tex",
            "manuscript/references.bib",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_manuscript_compile_preflight.py"],
        "command": "python scripts/export_manuscript_compile_preflight.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "visual_evidence_audit",
        "outputs": [
            "materials/VISUAL_EVIDENCE_AUDIT.md",
            "materials/VISUAL_EVIDENCE_AUDIT.json",
            "materials/VISUAL_EVIDENCE_AUDIT.csv",
        ],
        "inputs": [
            "tables/main_results.csv",
            "materials/README.md",
            "materials/SUPPLEMENTARY_INDEX.md",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_visual_evidence_audit.py"],
        "command": "python scripts/export_visual_evidence_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "manuscript_cross_reference_audit",
        "outputs": [
            "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.md",
            "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.json",
            "materials/MANUSCRIPT_CROSS_REFERENCE_PATHS.csv",
            "materials/MANUSCRIPT_CROSS_REFERENCE_NUMERIC_CHECKS.csv",
        ],
        "inputs": [
            "manuscript/main.md",
            "materials/MANUSCRIPT_OUTLINE.md",
            "materials/MANUSCRIPT_RESULTS_DISCUSSION_DRAFT.md",
            "materials/PUBLICATION_PACKAGE_SUMMARY.md",
            "materials/SUPPLEMENTARY_INDEX.md",
            "tables/compute_cost_report.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_manuscript_cross_reference_audit.py"],
        "command": "python scripts/export_manuscript_cross_reference_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reference_readiness_audit",
        "outputs": [
            "materials/REFERENCE_READINESS_AUDIT.md",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/REFERENCE_READINESS_CITATIONS.csv",
            "materials/REFERENCE_READINESS_TOPICS.csv",
        ],
        "inputs": [
            "manuscript/main.md",
            "manuscript/references.bib",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_reference_readiness_audit.py"],
        "command": "python scripts/export_reference_readiness_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "external_archive_preflight",
        "outputs": [
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.md",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT_ROWS.csv",
            "materials/EXTERNAL_ARCHIVE_KEY_FILES.csv",
        ],
        "inputs": [
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/DATA_DICTIONARY.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
        ],
        "scripts": ["scripts/export_external_archive_preflight.py"],
        "command": "python scripts/export_external_archive_preflight.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "submission_metadata_draft",
        "outputs": [
            "materials/SUBMISSION_METADATA_DRAFT.md",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/SUBMISSION_METADATA_AUTHORS.csv",
            "materials/SUBMISSION_METADATA_CREDIT.csv",
            "materials/SUBMISSION_METADATA_DISCLOSURES.csv",
        ],
        "inputs": [
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
        ],
        "scripts": ["scripts/export_submission_metadata_draft.py"],
        "command": "python scripts/export_submission_metadata_draft.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "editorial_narrative_package",
        "outputs": [
            "materials/EDITORIAL_NARRATIVE_PACKAGE.md",
            "materials/EDITORIAL_NARRATIVE_PACKAGE.json",
            "materials/EDITORIAL_NARRATIVE_PACKAGE.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_SUMMARY.json",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/SIGNIFICANCE_BRIEFING.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
        ],
        "scripts": ["scripts/export_editorial_narrative_package.py"],
        "command": "python scripts/export_editorial_narrative_package.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "cover_letter_draft_package",
        "outputs": [
            "materials/COVER_LETTER_DRAFT_PACKAGE.md",
            "materials/COVER_LETTER_DRAFT_PACKAGE.json",
            "materials/COVER_LETTER_DRAFT_PACKAGE.csv",
            "materials/COVER_LETTER_AUTHOR_CHECKLIST.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_SUMMARY.json",
            "materials/EDITORIAL_NARRATIVE_PACKAGE.json",
            "materials/SIGNIFICANCE_BRIEFING.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
        ],
        "scripts": ["scripts/export_cover_letter_draft_package.py"],
        "command": "python scripts/export_cover_letter_draft_package.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "submission_portal_package_map",
        "outputs": [
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.md",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.csv",
            "materials/SUBMISSION_PORTAL_AUTHOR_ACTIONS.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/EDITORIAL_SUBMISSION_CHECKLIST.json",
            "materials/COVER_LETTER_DRAFT_PACKAGE.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/DATA_DICTIONARY.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
        ],
        "scripts": ["scripts/export_submission_portal_package_map.py"],
        "command": "python scripts/export_submission_portal_package_map.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "editorial_decision_brief",
        "outputs": [
            "materials/EDITORIAL_DECISION_BRIEF.md",
            "materials/EDITORIAL_DECISION_BRIEF.json",
            "materials/EDITORIAL_DECISION_BRIEF.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_SUMMARY.json",
            "materials/EDITORIAL_NARRATIVE_PACKAGE.json",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
            "materials/COVER_LETTER_DRAFT_PACKAGE.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
        ],
        "scripts": ["scripts/export_editorial_decision_brief.py"],
        "command": "python scripts/export_editorial_decision_brief.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "editorial_triage_and_reviewer_checklist",
        "outputs": [
            "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
            "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json",
            "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/EDITORIAL_DECISION_BRIEF.json",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.json",
            "materials/SELECTOR_DECISION_AUDIT.json",
            "materials/SEED_PARTITION_AUDIT.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/VISUAL_EVIDENCE_AUDIT.json",
            "materials/ARTIFACT_DEPENDENCY_MAP.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/BASELINE_FAIRNESS_AUDIT.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
        ],
        "scripts": ["scripts/export_editorial_triage_and_reviewer_checklist.py"],
        "command": "python scripts/export_editorial_triage_and_reviewer_checklist.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "title_abstract_highlights_package",
        "outputs": [
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.csv",
        ],
        "inputs": [
            "materials/MANUSCRIPT_OUTLINE.json",
            "materials/PUBLICATION_PACKAGE_SUMMARY.json",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
        ],
        "scripts": ["scripts/export_title_abstract_highlights_package.py"],
        "command": "python scripts/export_title_abstract_highlights_package.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "submission_readiness_dashboard",
        "outputs": [
            "materials/SUBMISSION_READINESS_DASHBOARD.md",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/DATA_DICTIONARY.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.json",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
            "materials/EDITORIAL_DECISION_BRIEF.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
            "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/VISUAL_EVIDENCE_AUDIT.json",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/THREATS_TO_VALIDITY_AUDIT.json",
            "materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.json",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
        ],
        "scripts": ["scripts/export_submission_readiness_dashboard.py"],
        "command": "python scripts/export_submission_readiness_dashboard.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reviewer_risk_response_dossier",
        "outputs": [
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.md",
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/SELECTOR_DECISION_AUDIT.json",
            "materials/SEED_PARTITION_AUDIT.json",
            "materials/BASELINE_FAIRNESS_AUDIT.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/VISUAL_EVIDENCE_AUDIT.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
        ],
        "scripts": ["scripts/export_reviewer_risk_response_dossier.py"],
        "command": "python scripts/export_reviewer_risk_response_dossier.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reviewer_response_seed_pack",
        "outputs": [
            "materials/REVIEWER_RESPONSE_SEED_PACK.md",
            "materials/REVIEWER_RESPONSE_SEED_PACK.json",
            "materials/REVIEWER_RESPONSE_SEED_PACK.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "tables/artifact_provenance.json",
            "materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json",
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
            "tables/seed_outcome_ledger.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
        ],
        "scripts": ["scripts/export_reviewer_response_seed_pack.py"],
        "command": "python scripts/export_reviewer_response_seed_pack.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "revision_response_execution_checklist",
        "outputs": [
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.md",
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.json",
            "materials/REVISION_RESPONSE_EXECUTION_CHECKLIST.csv",
        ],
        "inputs": [
            "materials/REVIEWER_RESPONSE_SEED_PACK.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json",
            "materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json",
        ],
        "scripts": ["scripts/export_revision_response_execution_checklist.py"],
        "command": "python scripts/export_revision_response_execution_checklist.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "portal_copyedit_lock_audit",
        "outputs": [
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.md",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.json",
            "materials/PORTAL_COPYEDIT_LOCK_AUDIT.csv",
        ],
        "inputs": [
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json",
            "materials/COVER_LETTER_DRAFT_PACKAGE.json",
            "materials/EDITORIAL_NARRATIVE_PACKAGE.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json",
            "materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json",
        ],
        "scripts": ["scripts/export_portal_copyedit_lock_audit.py"],
        "command": "python scripts/export_portal_copyedit_lock_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "blinded_review_anonymization_audit",
        "outputs": [
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.md",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.json",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.csv",
            "materials/BLINDED_REVIEW_ANONYMIZATION_SCAN_HITS.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/DATA_CODE_AVAILABILITY.json",
            "materials/CITATION_METADATA.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
        ],
        "scripts": ["scripts/export_blinded_review_anonymization_audit.py"],
        "command": "python scripts/export_blinded_review_anonymization_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "ai_tool_use_disclosure_audit",
        "outputs": [
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.json",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.csv",
            "materials/AI_TOOL_USE_DISCLOSURE_SCAN_HITS.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "tables/artifact_provenance.json",
            "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json",
            "materials/POLICY_MODEL_CARD.json",
            "materials/FIGURE_TECHNICAL_QC.json",
            "materials/FIGURE_PRODUCTION_HANDOFF.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.json",
        ],
        "scripts": ["scripts/export_ai_tool_use_disclosure_audit.py"],
        "command": "python scripts/export_ai_tool_use_disclosure_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "target_journal_compliance_matrix",
        "outputs": [
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.md",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/DATA_DICTIONARY.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
        ],
        "scripts": ["scripts/export_target_journal_compliance_matrix.py"],
        "command": "python scripts/export_target_journal_compliance_matrix.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "author_action_freeze_plan",
        "outputs": [
            "materials/AUTHOR_ACTION_FREEZE_PLAN.md",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
        ],
        "scripts": ["scripts/export_author_action_freeze_plan.py"],
        "command": "python scripts/export_author_action_freeze_plan.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "final_submission_file_bundle",
        "outputs": [
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.md",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/REVIEWER_RESPONSE_SEED_PACK.json",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
        ],
        "scripts": ["scripts/export_final_submission_file_bundle.py"],
        "command": "python scripts/export_final_submission_file_bundle.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "submission_upload_selection_plan",
        "outputs": [
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.md",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.csv",
        ],
        "inputs": [
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
        ],
        "scripts": ["scripts/export_submission_upload_selection_plan.py"],
        "command": "python scripts/export_submission_upload_selection_plan.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "target_journal_upload_decision_checklist",
        "outputs": [
            "materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.md",
            "materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.json",
            "materials/TARGET_JOURNAL_UPLOAD_DECISION_CHECKLIST.csv",
        ],
        "inputs": [
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/ARCHIVE_README.json",
            "materials/CITATION_METADATA.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
        ],
        "scripts": ["scripts/export_target_journal_upload_decision_checklist.py"],
        "command": "python scripts/export_target_journal_upload_decision_checklist.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "author_upload_decision_memo",
        "outputs": [
            "materials/AUTHOR_UPLOAD_DECISION_MEMO.md",
            "materials/AUTHOR_UPLOAD_DECISION_MEMO.json",
            "materials/AUTHOR_UPLOAD_DECISION_MEMO.csv",
        ],
        "inputs": [
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
            "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "tables/artifact_provenance.json",
            "materials/DATA_DICTIONARY.json",
        ],
        "scripts": ["scripts/export_author_upload_decision_memo.py"],
        "command": "python scripts/export_author_upload_decision_memo.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "submission_portal_field_completion_pack",
        "outputs": [
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.md",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.csv",
        ],
        "inputs": [
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/DATA_CODE_AVAILABILITY.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
        ],
        "scripts": ["scripts/export_submission_portal_field_completion_pack.py"],
        "command": "python scripts/export_submission_portal_field_completion_pack.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reviewer_evidence_trace_pack",
        "outputs": [
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.md",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.csv",
        ],
        "inputs": [
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/FIGURE_TECHNICAL_QC.json",
            "tables/seed_outcome_ledger.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/THREATS_TO_VALIDITY_AUDIT.json",
            "materials/MANUSCRIPT_LIMITATION_INTEGRATION_AUDIT.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/REVIEWER_RESPONSE_SEED_PACK.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/DATA_DICTIONARY.json",
        ],
        "scripts": ["scripts/export_reviewer_evidence_trace_pack.py"],
        "command": "python scripts/export_reviewer_evidence_trace_pack.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reviewer_quicklook_packet",
        "outputs": [
            "materials/REVIEWER_QUICKLOOK_PACKET.md",
            "materials/REVIEWER_QUICKLOOK_PACKET.json",
            "materials/REVIEWER_QUICKLOOK_PACKET.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
            "materials/REVIEWER_RESPONSE_SEED_PACK.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/DATA_DICTIONARY.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/REVIEWER_COMMAND_PREFLIGHT.json",
        ],
        "scripts": ["scripts/export_reviewer_quicklook_packet.py"],
        "command": "python scripts/export_reviewer_quicklook_packet.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "figure_production_handoff",
        "outputs": [
            "materials/FIGURE_PRODUCTION_HANDOFF.md",
            "materials/FIGURE_PRODUCTION_HANDOFF.json",
            "materials/FIGURE_PRODUCTION_HANDOFF.csv",
            "materials/FIGURE_PRODUCTION_HANDOFF_FILES.csv",
            "materials/FIGURE_PRODUCTION_HANDOFF_SOURCE_DATA.csv",
        ],
        "inputs": [
            "materials/FIGURE_TECHNICAL_QC.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/FIGURE_LEGENDS.json",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
        ],
        "scripts": ["scripts/export_figure_production_handoff.py"],
        "command": "python scripts/export_figure_production_handoff.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "methods_reproducibility_capsule",
        "outputs": [
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.md",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.json",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.csv",
        ],
        "inputs": [
            "materials/EXPERIMENT_REGISTRY.json",
            "materials/SEED_PARTITION_AUDIT.json",
            "materials/STATISTICAL_ANALYSIS_PLAN.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "tables/compute_cost_report.json",
            "materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/DATA_DICTIONARY.json",
        ],
        "scripts": ["scripts/export_methods_reproducibility_capsule.py"],
        "command": "python scripts/export_methods_reproducibility_capsule.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "methods_to_code_traceability",
        "outputs": [
            "materials/METHODS_TO_CODE_TRACEABILITY.md",
            "materials/METHODS_TO_CODE_TRACEABILITY.json",
            "materials/METHODS_TO_CODE_TRACEABILITY.csv",
        ],
        "inputs": [
            "tables/artifact_provenance.json",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.json",
            "materials/EXPERIMENT_REGISTRY.json",
            "materials/ARTIFACT_DEPENDENCY_MAP.json",
            "materials/REVIEWER_REPLICATION_ROUTE.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/DATA_DICTIONARY.json",
        ],
        "scripts": ["scripts/export_methods_to_code_traceability.py"],
        "command": "python scripts/export_methods_to_code_traceability.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "script_snapshot_integrity_audit",
        "outputs": [
            "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.md",
            "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.json",
            "materials/SCRIPT_SNAPSHOT_INTEGRITY_AUDIT.csv",
            "materials/SCRIPT_SNAPSHOT_EXTRA_FILES.csv",
        ],
        "inputs": [
            "tables/artifact_provenance.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
        ],
        "scripts": ["scripts/export_script_snapshot_integrity_audit.py"],
        "command": "python scripts/export_script_snapshot_integrity_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "machine_readable_table_integrity_audit",
        "outputs": [
            "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.md",
            "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.json",
            "materials/MACHINE_READABLE_TABLE_INTEGRITY_AUDIT.csv",
        ],
        "inputs": [
            "materials/DATA_DICTIONARY.json",
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.json",
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
        ],
        "scripts": ["scripts/export_machine_readable_table_integrity_audit.py"],
        "command": "python scripts/export_machine_readable_table_integrity_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "ethics_disclosure_readiness_pack",
        "outputs": [
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.md",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.json",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.csv",
        ],
        "inputs": [
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/SOFTWARE_DEPENDENCY_LICENSE_AUDIT.json",
            "materials/DATA_CODE_AVAILABILITY.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
        ],
        "scripts": ["scripts/export_ethics_disclosure_readiness_pack.py"],
        "command": "python scripts/export_ethics_disclosure_readiness_pack.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reporting_supplement_navigator",
        "outputs": [
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.md",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/DATA_DICTIONARY.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
            "materials/REVIEWER_RESPONSE_SEED_PACK.json",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.json",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.json",
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.json",
            "materials/ARCHIVE_README.json",
            "materials/FIGURE_TECHNICAL_QC.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/SEED_PARTITION_AUDIT.json",
            "materials/RESEARCH_RISK_AND_SAFETY.json",
            "materials/SIMULATION_TO_REAL_APPLICABILITY.json",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
            "materials/CITATION_METADATA.json",
        ],
        "scripts": ["scripts/export_reporting_supplement_navigator.py"],
        "command": "python scripts/export_reporting_supplement_navigator.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reviewer_replication_route",
        "outputs": [
            "materials/REVIEWER_REPLICATION_ROUTE.md",
            "materials/REVIEWER_REPLICATION_ROUTE.json",
            "materials/REVIEWER_REPLICATION_ROUTE.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
            "materials/FIGURE_TECHNICAL_QC.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/SELECTOR_DECISION_AUDIT.json",
            "materials/SEED_PARTITION_AUDIT.json",
            "tables/artifact_provenance.json",
            "tables/compute_cost_report.json",
            "materials/DATA_DICTIONARY.json",
        ],
        "scripts": ["scripts/export_reviewer_replication_route.py"],
        "command": "python scripts/export_reviewer_replication_route.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "manuscript_supplement_assembly_map",
        "outputs": [
            "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.md",
            "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json",
            "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.csv",
        ],
        "inputs": [
            "manuscript/manuscript_manifest.json",
            "materials/MANUSCRIPT_CROSS_REFERENCE_AUDIT.json",
            "materials/MANUSCRIPT_SOURCE_PACKAGE_AUDIT.json",
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.json",
            "materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
            "materials/REVIEWER_REPLICATION_ROUTE.json",
            "materials/METHODS_REPRODUCIBILITY_CAPSULE.json",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/FIGURE_TECHNICAL_QC.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "tables/artifact_provenance.json",
            "materials/DATA_DICTIONARY.json",
        ],
        "scripts": ["scripts/export_manuscript_supplement_assembly_map.py"],
        "command": "python scripts/export_manuscript_supplement_assembly_map.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "supplementary_table_legends",
        "outputs": [
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.md",
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.json",
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.csv",
        ],
        "inputs": [
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.json",
            "materials/DATA_DICTIONARY.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "tables/artifact_provenance.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
        ],
        "scripts": ["scripts/export_supplementary_table_legends.py"],
        "command": "python scripts/export_supplementary_table_legends.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "statistical_reporting_appendix",
        "outputs": [
            "materials/STATISTICAL_REPORTING_APPENDIX.md",
            "materials/STATISTICAL_REPORTING_APPENDIX.json",
            "materials/STATISTICAL_REPORTING_APPENDIX.csv",
        ],
        "inputs": [
            "tables/cross_heldout_statistical_supplement.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/ENDPOINT_SENSITIVITY_AUDIT.json",
            "materials/SEED_PARTITION_AUDIT.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_statistical_reporting_appendix.py"],
        "command": "python scripts/export_statistical_reporting_appendix.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "effect_size_uncertainty_summary",
        "outputs": [
            "materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.md",
            "materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.json",
            "materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.csv",
        ],
        "inputs": [
            "tables/cross_heldout_statistical_supplement.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/SEED_PARTITION_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_effect_size_uncertainty_summary.py"],
        "command": "python scripts/export_effect_size_uncertainty_summary.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "publication_smoke_test",
        "outputs": [
            "materials/PUBLICATION_SMOKE_TEST.md",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/PUBLICATION_SMOKE_TEST.csv",
        ],
        "inputs": [
            "manifest.json",
            "tables/artifact_provenance.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/STATISTICAL_CONSISTENCY_AUDIT.json",
            "materials/DATA_DICTIONARY.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/REVIEWER_EVIDENCE_TRACE_PACK.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
            "figures/figure_1_source_data.csv",
            "figures/figure_2_source_data.csv",
            "figures/figure_3_source_data.csv",
        ],
        "scripts": ["scripts/run_publication_smoke_test.py", "scripts/export_publication_smoke_test_report.py"],
        "command": "python scripts/run_publication_smoke_test.py --root outputs/paper_multicar_overtake_20260618 --write-report",
    },
    {
        "name": "supplementary_materials_index",
        "outputs": [
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.md",
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.json",
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/DATA_DICTIONARY.json",
            "materials/FIGURE_SOURCE_DATA_AUDIT.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
        ],
        "scripts": ["scripts/export_supplementary_materials_index.py"],
        "command": "python scripts/export_supplementary_materials_index.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "supplement_upload_decision_matrix",
        "outputs": [
            "materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.md",
            "materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.json",
            "materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.csv",
        ],
        "inputs": [
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.json",
            "materials/SUPPLEMENTARY_TABLE_LEGENDS.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_supplement_upload_decision_matrix.py"],
        "command": "python scripts/export_supplement_upload_decision_matrix.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "archive_readme",
        "outputs": [
            "materials/ARCHIVE_README.md",
            "materials/ARCHIVE_README.json",
            "materials/ARCHIVE_README.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/DATA_DICTIONARY.json",
            "materials/SUPPLEMENTARY_MATERIALS_INDEX.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
        ],
        "scripts": ["scripts/export_archive_readme.py"],
        "command": "python scripts/export_archive_readme.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "archive_size_budget_report",
        "outputs": [
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.md",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
            "materials/ARCHIVE_SIZE_BUDGET_CATEGORIES.csv",
            "materials/ARCHIVE_SIZE_BUDGET_UPLOAD_PARTITIONS.csv",
            "materials/ARCHIVE_SIZE_BUDGET_LARGEST_FILES.csv",
            "materials/ARCHIVE_SIZE_BUDGET_CHECKS.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
        ],
        "scripts": ["scripts/export_archive_size_budget_report.py"],
        "command": "python scripts/export_archive_size_budget_report.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "slim_submission_package_manifest",
        "outputs": [
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.md",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "materials/SLIM_SUBMISSION_PACKAGE_FILES.csv",
            "materials/SLIM_SUBMISSION_PACKAGE_ARCHIVE_ONLY.csv",
            "materials/SLIM_SUBMISSION_PACKAGE_PARTITIONS.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/DATA_DICTIONARY.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_slim_submission_package_manifest.py"],
        "command": "python scripts/export_slim_submission_package_manifest.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "citation_metadata",
        "outputs": [
            "materials/CITATION_METADATA.md",
            "materials/CITATION_METADATA.json",
            "materials/CITATION_METADATA.csv",
            "materials/CITATION.cff",
            "materials/CITATION.bib",
        ],
        "inputs": [
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
            "materials/ARCHIVE_README.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
        ],
        "scripts": ["scripts/export_citation_metadata.py"],
        "command": "python scripts/export_citation_metadata.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "novelty_positioning_matrix",
        "outputs": [
            "materials/NOVELTY_POSITIONING_MATRIX.md",
            "materials/NOVELTY_POSITIONING_MATRIX.json",
            "materials/NOVELTY_POSITIONING_MATRIX.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/REVIEWER_RISK_RESPONSE_DOSSIER.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
        ],
        "scripts": ["scripts/export_novelty_positioning_matrix.py"],
        "command": "python scripts/export_novelty_positioning_matrix.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "confirmatory_experiment_preregistration",
        "outputs": [
            "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.md",
            "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json",
            "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.csv",
        ],
        "inputs": [
            "manifest.json",
            "materials/SUBMISSION_GAP_ACTION_PLAN.json",
            "materials/STATISTICAL_ANALYSIS_PLAN.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/SEED_PARTITION_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_confirmatory_experiment_preregistration.py"],
        "command": "python scripts/export_confirmatory_experiment_preregistration.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "confirmatory_freeze_package",
        "outputs": [
            "configs/heldout5_frozen_selector.yaml",
            "materials/CONFIRMATORY_FREEZE_CONFIG.json",
            "materials/CONFIRMATORY_FREEZE_AUDIT.md",
            "materials/CONFIRMATORY_FREEZE_AUDIT.json",
            "materials/CONFIRMATORY_FREEZE_AUDIT.csv",
        ],
        "inputs": [
            "manifest.json",
            "tables/portfolio_probe_selector_1200_heldout4_targeted_expanded.json",
            "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json",
            "materials/GPU_RERUN_READINESS.json",
        ],
        "scripts": ["scripts/export_confirmatory_freeze_package.py"],
        "command": "python scripts/export_confirmatory_freeze_package.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "confirmatory_roadmap",
        "outputs": [
            "materials/CONFIRMATORY_ROADMAP.md",
            "materials/CONFIRMATORY_ROADMAP.json",
            "materials/CONFIRMATORY_ROADMAP.csv",
        ],
        "inputs": [
            "materials/TOP_JOURNAL_READINESS_CHECKLIST.json",
            "materials/CONFIRMATORY_EXPERIMENT_PREREGISTRATION.json",
            "materials/CONFIRMATORY_FREEZE_AUDIT.json",
            "materials/CONFIRMATORY_FREEZE_CONFIG.json",
            "materials/GPU_RERUN_READINESS.json",
            "materials/SAMPLE_SIZE_SENSITIVITY_BRIEF.json",
            "materials/EFFECT_SIZE_UNCERTAINTY_SUMMARY.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_confirmatory_roadmap.py"],
        "command": "python scripts/export_confirmatory_roadmap.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "claim_decision_tree",
        "outputs": [
            "materials/CLAIM_DECISION_TREE.md",
            "materials/CLAIM_DECISION_TREE.json",
            "materials/CLAIM_DECISION_TREE.csv",
        ],
        "inputs": [
            "materials/CLAIM_EVIDENCE_MATRIX.json",
            "materials/CLAIM_BOUNDARY_COMMUNICATION_PACK.json",
            "materials/TOP_JOURNAL_READINESS_CHECKLIST.json",
            "materials/CONFIRMATORY_ROADMAP.json",
            "tables/cross_heldout_validation_synthesis.json",
            "tables/seed_outcome_ledger.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.json",
        ],
        "scripts": ["scripts/export_claim_decision_tree.py"],
        "command": "python scripts/export_claim_decision_tree.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "failure_mode_atlas_summary",
        "outputs": [
            "materials/FAILURE_MODE_ATLAS_SUMMARY.md",
            "materials/FAILURE_MODE_ATLAS_SUMMARY.json",
            "materials/FAILURE_MODE_ATLAS_SUMMARY.csv",
        ],
        "inputs": [
            "tables/heldout2_failure_atlas.json",
            "tables/heldout3_external_validation.json",
            "tables/heldout3_targeted_selector_generalization.json",
            "tables/heldout3_targeted_meta_selector.json",
            "tables/heldout4_failure_atlas.json",
            "materials/NEGATIVE_RESULTS_FAILURE_REGISTER.json",
            "materials/CLAIM_DECISION_TREE.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_failure_mode_atlas_summary.py"],
        "command": "python scripts/export_failure_mode_atlas_summary.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "related_work_positioning_matrix",
        "outputs": [
            "materials/RELATED_WORK_POSITIONING_MATRIX.md",
            "materials/RELATED_WORK_POSITIONING_MATRIX.json",
            "materials/RELATED_WORK_POSITIONING_MATRIX.csv",
        ],
        "inputs": [
            "manuscript/main.md",
            "manuscript/references.bib",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/NOVELTY_POSITIONING_MATRIX.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_related_work_positioning_matrix.py"],
        "command": "python scripts/export_related_work_positioning_matrix.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "remaining_author_blockers_matrix",
        "outputs": [
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.md",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.csv",
        ],
        "inputs": [
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "materials/SUBMISSION_PORTAL_PACKAGE_MAP.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/REFERENCE_READINESS_AUDIT.json",
            "materials/RELATED_WORK_POSITIONING_MATRIX.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_remaining_author_blockers_matrix.py"],
        "command": "python scripts/export_remaining_author_blockers_matrix.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "archive_manifest_exclusion_audit",
        "outputs": [
            "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.md",
            "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json",
            "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
        ],
        "scripts": ["scripts/export_archive_manifest_exclusion_audit.py"],
        "command": "python scripts/export_archive_manifest_exclusion_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "author_owned_submission_integrity_audit",
        "outputs": [
            "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md",
            "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json",
            "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.csv",
        ],
        "inputs": [
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/SUBMISSION_METADATA_AUTHORS.csv",
            "materials/SUBMISSION_METADATA_CREDIT.csv",
            "materials/SUBMISSION_METADATA_DISCLOSURES.csv",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_author_owned_submission_integrity_audit.py"],
        "command": "python scripts/export_author_owned_submission_integrity_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "local_author_readiness_separation_audit",
        "outputs": [
            "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.md",
            "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json",
            "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.csv",
        ],
        "inputs": [
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/REPORTING_SUPPLEMENT_NAVIGATOR.json",
            "materials/MANUSCRIPT_SUPPLEMENT_ASSEMBLY_MAP.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/CROSS_MATERIAL_CONSISTENCY_AUDIT.json",
            "materials/NARRATIVE_NUMERIC_CONSISTENCY_AUDIT.json",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_local_author_readiness_separation_audit.py"],
        "command": "python scripts/export_local_author_readiness_separation_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "editorial_frontmatter_claim_audit",
        "outputs": [
            "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.md",
            "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.json",
            "materials/EDITORIAL_FRONTMATTER_CLAIM_AUDIT.csv",
        ],
        "inputs": [
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.md",
            "materials/COVER_LETTER_DRAFT_PACKAGE.md",
            "materials/SIGNIFICANCE_BRIEFING.md",
            "materials/EDITORIAL_NARRATIVE_PACKAGE.md",
            "materials/EDITORIAL_DECISION_BRIEF.md",
            "materials/EDITORIAL_TRIAGE_AND_REVIEWER_CHECKLIST.md",
            "materials/TOP_JOURNAL_REPORTING_SUMMARY.md",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/MANUSCRIPT_CLAIM_QA.json",
            "materials/LOCAL_AUTHOR_READINESS_SEPARATION_AUDIT.json",
        ],
        "scripts": ["scripts/export_editorial_frontmatter_claim_audit.py"],
        "command": "python scripts/export_editorial_frontmatter_claim_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "cross_report_freshness_audit",
        "outputs": [
            "materials/CROSS_REPORT_FRESHNESS_AUDIT.md",
            "materials/CROSS_REPORT_FRESHNESS_AUDIT.json",
            "materials/CROSS_REPORT_FRESHNESS_AUDIT.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/DATA_DICTIONARY.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_cross_report_freshness_audit.py"],
        "command": "python scripts/export_cross_report_freshness_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "stale_snapshot_boundary_audit",
        "outputs": [
            "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.md",
            "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.json",
            "materials/STALE_SNAPSHOT_BOUNDARY_AUDIT.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/DATA_DICTIONARY.json",
            "materials/CROSS_REPORT_FRESHNESS_AUDIT.json",
            "tables/artifact_provenance.json",
        ],
        "scripts": ["scripts/export_stale_snapshot_boundary_audit.py"],
        "command": "python scripts/export_stale_snapshot_boundary_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "final_author_handoff_checklist",
        "outputs": [
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.md",
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.json",
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/SUBMISSION_METADATA_DRAFT.json",
            "materials/EXTERNAL_ARCHIVE_PREFLIGHT.json",
            "materials/AI_TOOL_USE_DISCLOSURE_AUDIT.json",
            "materials/BLINDED_REVIEW_ANONYMIZATION_AUDIT.json",
        ],
        "scripts": ["scripts/export_final_author_handoff_checklist.py"],
        "command": "python scripts/export_final_author_handoff_checklist.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "reviewer_command_preflight",
        "outputs": [
            "materials/REVIEWER_COMMAND_PREFLIGHT.md",
            "materials/REVIEWER_COMMAND_PREFLIGHT.json",
            "materials/REVIEWER_COMMAND_PREFLIGHT_ROUTES.csv",
            "materials/REVIEWER_COMMAND_PREFLIGHT_COMMANDS.csv",
        ],
        "inputs": [
            "materials/REVIEWER_REPLICATION_ROUTE.json",
            "materials/GPU_RERUN_READINESS.json",
            "tables/artifact_provenance.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
        ],
        "scripts": ["scripts/export_reviewer_command_preflight.py"],
        "command": "python scripts/export_reviewer_command_preflight.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "author_upload_gap_closure_audit",
        "outputs": [
            "materials/AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.md",
            "materials/AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.json",
            "materials/AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "tables/artifact_provenance.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/AUTHOR_ACTION_FREEZE_PLAN.json",
            "materials/FINAL_AUTHOR_HANDOFF_CHECKLIST.json",
            "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.json",
            "materials/SUPPLEMENT_UPLOAD_DECISION_MATRIX.json",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "materials/SUBMISSION_READINESS_DASHBOARD.json",
            "materials/TARGET_JOURNAL_COMPLIANCE_MATRIX.json",
            "materials/CITATION_METADATA.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "materials/ETHICS_DISCLOSURE_READINESS_PACK.json",
            "materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.json",
            "materials/REMAINING_AUTHOR_BLOCKERS_MATRIX.json",
            "materials/REVIEWER_COMMAND_PREFLIGHT.json",
        ],
        "scripts": ["scripts/export_author_upload_gap_closure_audit.py"],
        "command": "python scripts/export_author_upload_gap_closure_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "public_archive_journal_upload_dry_run_audit",
        "outputs": [
            "materials/PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.md",
            "materials/PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.json",
            "materials/PUBLIC_ARCHIVE_JOURNAL_UPLOAD_DRY_RUN_AUDIT.csv",
        ],
        "inputs": [
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/FINAL_CHECKSUM_FREEZE_RECORD.json",
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "materials/FINAL_SUBMISSION_FILE_BUNDLE.json",
            "materials/SUBMISSION_UPLOAD_SELECTION_PLAN.json",
            "materials/SLIM_SUBMISSION_PACKAGE_MANIFEST.json",
            "materials/ARCHIVE_SIZE_BUDGET_REPORT.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/ARCHIVE_UPLOAD_READINESS_MATRIX.json",
            "materials/ARCHIVE_MANIFEST_EXCLUSION_AUDIT.json",
            "materials/AUTHOR_UPLOAD_GAP_CLOSURE_AUDIT.json",
            "materials/CITATION_METADATA.json",
            "materials/FAIR_ARCHIVE_METADATA.json",
            "tables/artifact_provenance.json",
            "materials/DATA_DICTIONARY.json",
        ],
        "scripts": ["scripts/export_public_archive_journal_upload_dry_run_audit.py"],
        "command": "python scripts/export_public_archive_journal_upload_dry_run_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
    {
        "name": "submission_text_freshness_audit",
        "outputs": [
            "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.md",
            "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.json",
            "materials/SUBMISSION_TEXT_FRESHNESS_AUDIT.csv",
        ],
        "inputs": [
            "materials/PUBLICATION_PACKAGE_VERIFICATION.json",
            "materials/PUBLICATION_SMOKE_TEST.json",
            "tables/artifact_provenance.json",
            "materials/RELEASE_ARCHIVE_MANIFEST.json",
            "materials/DATA_DICTIONARY.json",
            "materials/TITLE_ABSTRACT_HIGHLIGHTS_PACKAGE.json",
            "materials/SUBMISSION_PORTAL_FIELD_COMPLETION_PACK.json",
            "materials/SIGNIFICANCE_BRIEFING.json",
        ],
        "scripts": ["scripts/export_submission_text_freshness_audit.py"],
        "command": "python scripts/export_submission_text_freshness_audit.py --root outputs/paper_multicar_overtake_20260618",
    },
]


def rel_exists(root, rel_path):
    return (root / rel_path).exists()


def enrich(root, artifact):
    item = dict(artifact)
    item["outputs_status"] = {path: rel_exists(root, path) for path in artifact["outputs"]}
    item["inputs_status"] = {path: rel_exists(root, path) for path in artifact["inputs"]}
    item["scripts_status"] = {path: Path(path).exists() for path in artifact["scripts"]}
    item["material_script_snapshots"] = {
        path: rel_exists(root, f"materials/scripts/{Path(path).name}") for path in artifact["scripts"]
    }
    item["complete"] = (
        all(item["outputs_status"].values())
        and all(item["inputs_status"].values())
        and all(item["scripts_status"].values())
        and all(item["material_script_snapshots"].values())
    )
    return item


def write_markdown(report, path):
    lines = [
        "# Artifact Provenance",
        "",
        f"- Root: `{report['root']}`",
        f"- Complete artifacts: {report['complete_count']}/{len(report['artifacts'])}",
        "",
        "## Summary",
        "",
        "| artifact | complete | outputs | inputs | scripts |",
        "|---|---|---:|---:|---:|",
    ]
    for item in report["artifacts"]:
        lines.append(
            f"| {item['name']} | {item['complete']} | "
            f"{sum(item['outputs_status'].values())}/{len(item['outputs_status'])} | "
            f"{sum(item['inputs_status'].values())}/{len(item['inputs_status'])} | "
            f"{sum(item['material_script_snapshots'].values())}/{len(item['material_script_snapshots'])} |"
        )
    lines.extend(["", "## Reproduction Commands", ""])
    for item in report["artifacts"]:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                "Outputs:",
                "",
            ]
        )
        for output, ok in item["outputs_status"].items():
            lines.append(f"- [{'x' if ok else ' '}] `{output}`")
        lines.extend(["", "Inputs:", ""])
        for input_path, ok in item["inputs_status"].items():
            lines.append(f"- [{'x' if ok else ' '}] `{input_path}`")
        lines.extend(["", "Scripts:", ""])
        for script, ok in item["material_script_snapshots"].items():
            lines.append(f"- [{'x' if ok else ' '}] `{script}`")
        lines.extend(["", "Command:", "", "```bash", item["command"], "```", ""])
    if report["incomplete_artifacts"]:
        lines.extend(["", "## Incomplete Artifacts", ""])
        for item in report["incomplete_artifacts"]:
            lines.append(f"- {item['name']}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export artifact-level provenance and reproduction commands.")
    parser.add_argument("--root", default="outputs/paper_multicar_overtake_20260618")
    parser.add_argument("--out-prefix", default="artifact_provenance")
    args = parser.parse_args()
    root = Path(args.root)
    artifacts = [enrich(root, artifact) for artifact in ARTIFACTS]
    report = {
        "root": str(root),
        "artifacts": artifacts,
        "complete_count": sum(item["complete"] for item in artifacts),
        "incomplete_artifacts": [item for item in artifacts if not item["complete"]],
    }
    out_dir = root / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"{args.out_prefix}.json"
    out_md = out_dir / f"{args.out_prefix}.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, out_md)
    print(json.dumps({"json": str(out_json), "markdown": str(out_md), "complete": report["complete_count"]}, indent=2))


if __name__ == "__main__":
    main()
