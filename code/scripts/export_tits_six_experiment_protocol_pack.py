#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


OUT_DIR = "outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack"

MAIN_METHOD = "v6_runtime_dynamic_neighborhood_safe"
PAPER_DLC_BASELINES = [
    "dlc_joint_transition_observer",
    "dlc_joint_transition",
    "dlc_individual_transition",
]
RL_BASELINES = ["ppo_continuous", "sac_continuous", "td3_continuous"]
RULE_BASELINES = ["rule_expert_gate", "rule_safety_gate"]
ABLATIONS = [
    "ours_full_v6_safe",
    "w_o_dynamic_neighborhood",
    "w_o_interaction_neighbor_selection",
    "w_o_quality_proposal",
    "w_o_risk_penalty",
    "w_o_safety_quality_terms",
    "w_o_overtake_aware_planner",
    "low_budget_planner",
]


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_json(path, data):
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def track_manifest():
    return [
        {"track_id": "procedural", "track_path": "procedural", "role": "main_in_distribution"},
        {"track_id": "monza", "track_path": "tracks/monza_scaled.npz", "role": "external_generalization"},
        {"track_id": "china_gp", "track_path": "tracks/china_gp_scaled.npz", "role": "external_generalization"},
        {"track_id": "imola", "track_path": "tracks/imola_scaled.npz", "role": "external_generalization"},
        {"track_id": "indianapolis_sp", "track_path": "tracks/indianapolis_sp_scaled.npz", "role": "external_generalization"},
        {"track_id": "monaco", "track_path": "tracks/monaco_scaled.npz", "role": "external_generalization"},
    ]


def experiment_rows():
    rows = []
    rows.append(
        {
            "experiment_id": "E1_basic_effectiveness",
            "title_cn": "基础有效性：分布内主地图 4-6 车",
            "claim": "主算法在训练/验证分布内优于原文DLC三设定、强化学习baseline和规则baseline。",
            "track_ids": "procedural",
            "vehicle_counts": "4,5,6",
            "seeds": "3,7,11,17,23",
            "algorithms": ",".join([MAIN_METHOD] + PAPER_DLC_BASELINES + RL_BASELINES[:2] + RULE_BASELINES),
            "reuse_existing_data": "partial: existing frozen source data supports V6-safe and rule_expert_gate, but original paper DLC-JTO/JT/IT and RL baselines need protocol-aligned runs.",
            "status": "needs_expanded_run",
        }
    )
    rows.append(
        {
            "experiment_id": "E2_environment_generalization",
            "title_cn": "环境泛化：多外部地图",
            "claim": "主算法在未见过的赛道几何上保持超车质量和安全优势。",
            "track_ids": "monza,china_gp,imola,indianapolis_sp,monaco",
            "vehicle_counts": "4,6,8",
            "seeds": "53,59,61,67,71",
            "algorithms": ",".join([MAIN_METHOD] + PAPER_DLC_BASELINES + RL_BASELINES[:2] + RULE_BASELINES),
            "reuse_existing_data": "partial: Monza 4/6 has frozen V6-safe/rule/engineering-DLC data; new maps and paper-DLC/RL baselines require new runs.",
            "status": "needs_new_external_track_matrix",
        }
    )
    rows.append(
        {
            "experiment_id": "E3_scale_extension",
            "title_cn": "规模扩展：4→6→8→10→12车",
            "claim": "运行时动态邻域使主算法在车辆数增加时无需重新训练仍能运行并保持相对优势。",
            "track_ids": "procedural,monza",
            "vehicle_counts": "4,6,8,10,12",
            "seeds": "31,37,41,43,47",
            "algorithms": ",".join([MAIN_METHOD] + PAPER_DLC_BASELINES + ["ppo_continuous"] + RULE_BASELINES),
            "reuse_existing_data": "partial: existing frozen matrix includes 4/5/6 procedural and 8-car procedural for V6-safe/rule/engineering-DLC only.",
            "status": "needs_10_12_vehicle_runs_and_paper_dlc_rl_baselines",
        }
    )
    rows.append(
        {
            "experiment_id": "E4_interaction_generalization",
            "title_cn": "交互泛化：多算法车同场运行",
            "claim": "主算法在混合控制器交通中仍能完成稳定超车；该实验用于补充交互展示，不作为主统计结论。",
            "track_ids": "procedural,monza,monaco",
            "vehicle_counts": "6,8",
            "seeds": "73,79,83,89,97",
            "algorithms": "mixed_controllers: ours + DLC-JTO + DLC-JT + PPO + rule",
            "reuse_existing_data": "none: current formal benchmark is independent target-controller evaluation, not simultaneous mixed-controller tournament.",
            "status": "needs_new_mixed_controller_runner",
        }
    )
    rows.append(
        {
            "experiment_id": "E5_mechanism_explanation",
            "title_cn": "机制解释：邻域、proposal、安全介入和第一视角",
            "claim": "动态图邻域、质量proposal和安全约束共同解释主算法的超车质量提升。",
            "track_ids": "selected_cases",
            "vehicle_counts": "4,5,6,8",
            "seeds": "representative frozen cases plus targeted reruns",
            "algorithms": MAIN_METHOD + ",dlc_joint_transition_observer,rule_expert_gate",
            "reuse_existing_data": "partial: current typical first-person case pack and frozen traces support part of this experiment; quality-proposal and safety-intervention replay diagnostics need finalization.",
            "status": "in_progress",
        }
    )
    rows.append(
        {
            "experiment_id": "E6_ablation",
            "title_cn": "消融实验：主算法核心组件",
            "claim": "动态邻域、交互邻车选择、质量proposal、风险惩罚、安全质量项和超车感知规划均有可测贡献。",
            "track_ids": "procedural,monza",
            "vehicle_counts": "4,6,8",
            "seeds": "101,103,107,109,113",
            "algorithms": ",".join(ABLATIONS),
            "reuse_existing_data": "none for formal ablation: prior candidate matrices were exploratory and have been cleaned; rerun under frozen ablation protocol.",
            "status": "needs_formal_ablation_matrix",
        }
    )
    return rows


def metric_rows():
    metrics = [
        ("overtake_success_rate", "完成超车率", "primary", "目标车是否完成至少一次有效超车或按事件定义归一化。"),
        ("on_track_overtake_rate", "赛道内超车率", "primary", "超车窗口内不依赖草地/越界完成超车。"),
        ("elegant_overtake_rate", "Desirable overtaking behavior rate", "primary", "赛道内、低草地、低横向偏移、低接触风险和无倒车的综合指标。"),
        ("overtake_start_to_complete_time", "超车完成耗时", "primary", "从超车开始到完成的步数，越小代表超车效率越高。"),
        ("overtake_window_grass_rate_mean", "超车窗口草地率", "primary", "解释不符合 desirable overtaking behavior 标准的超车和越界策略。"),
        ("target_grass_rate", "目标车全程草地率", "secondary", "全局驾驶质量和安全代理指标。"),
        ("collision_or_contact_proxy", "接触风险代理", "secondary", "最小车距低于阈值的比例。"),
        ("rank_gain", "名次提升", "secondary", "目标车相对初始最后身位的名次收益。"),
        ("compute_latency_ms", "在线决策延迟", "secondary", "每步控制计算耗时。"),
    ]
    return [{"metric": a, "name_cn": b, "tier": c, "definition": d} for a, b, c, d in metrics]


def command_rows(experiments):
    rows = []
    rows.append(
        {
            "command_id": "convert_new_tracks",
            "scope": "E2",
            "command": "python scripts/convert_csv_track.py --csv tracks/<track>.csv --out tracks/<track>_scaled.npz --target-span 280 --resample-spacing 3.5 --smooth-window 5",
            "status": "done_for_china_gp_imola_indianapolis_sp_monaco",
        }
    )
    rows.append(
        {
            "command_id": "paper_dlc_train",
            "scope": "E1,E2,E3",
            "command": "python -m dlc.experiment --seeds <train_seeds> --episodes <budget> --devices cuda:0,cuda:1,cuda:2,cuda:3 --out-dir outputs/tits_dynamic_graph_expanded/paper_dlc_baselines_training --resume",
            "status": "entry_ready_training_required",
        }
    )
    rows.append(
        {
            "command_id": "paper_dlc_freeze",
            "scope": "E1,E2,E3",
            "command": "python scripts/prepare_tits_paper_dlc_baselines.py --experiment-dir outputs/tits_dynamic_graph_expanded/paper_dlc_baselines_training --frozen-dir outputs/tits_dynamic_graph_expanded/paper_dlc_baselines --mode freeze",
            "status": "freezer_ready_requires_trained_checkpoints",
        }
    )
    rows.append(
        {
            "command_id": "rl_train",
            "scope": "E1,E2,E3",
            "command": "python scripts/train_tits_rl_baselines.py --mode run --algorithms ppo_continuous,sac_continuous,td3_continuous --devices cuda:0,cuda:1,cuda:2,cuda:3 --jobs 3 --total-timesteps <budget> --out-dir outputs/tits_dynamic_graph_expanded/rl_baselines",
            "status": "entry_ready_smoke_passed_requires_full_training",
        }
    )
    rows.append(
        {
            "command_id": "expanded_online_matrix",
            "scope": "E1,E2,E3,E6",
            "command": "python scripts/run_tits_expanded_benchmark_matrix.py --protocol outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/tables/six_experiment_matrix.csv --devices cuda:0,cuda:1,cuda:2,cuda:3 --jobs 4",
            "status": "runner_ready_smoke_passed",
        }
    )
    rows.append(
        {
            "command_id": "mixed_controller_tournament",
            "scope": "E4",
            "command": "python scripts/run_tits_mixed_controller_tournament.py --protocol outputs/tits_dynamic_graph/tits_six_experiment_protocol_pack/materials/six_experiment_protocol.json --devices cuda:0,cuda:1,cuda:2,cuda:3",
            "status": "runner_ready_case_smoke_passed",
        }
    )
    rows.append(
        {
            "command_id": "mechanism_case_pack",
            "scope": "E5",
            "command": "python scripts/export_tits_typical_first_person_case_pack.py --out-dir outputs/tits_dynamic_graph/tits_typical_first_person_case_pack",
            "status": "in_progress",
        }
    )
    return rows


def build_markdown(report):
    lines = [
        "# T-ITS 六类实验协议包",
        "",
        "该协议把后续工作固定为六类实验：基础有效性、环境泛化、规模扩展、交互泛化、机制解释和消融实验。主算法固定为 `v6_runtime_dynamic_neighborhood_safe`，原文 DLC baseline 固定为 `joint transition + observer`、`joint transition`、`individual transition`。",
        "",
        "## 实验分层",
        "",
        "- 确认性主实验：E1、E2、E3、E6。",
        "- 补充解释实验：E4、E5。",
        "- 已有 frozen 240-run 数据只能作为当前阶段的部分证据；扩展矩阵需要重新冻结 case/seed/算法后再运行。",
        "",
        "## Baseline 层级",
        "",
        "- 原文 DLC：DLC-JTO、DLC-JT、DLC-IT。",
        "- 强化学习：PPO、SAC，TD3 作为补充或算力允许时纳入主表。",
        "- 规则算法：rule expert 与 safety-gated rule expert。",
        "",
        "## 关键边界",
        "",
        "- E4 混合控制器同场运行存在交互耦合，建议作为 supplementary tournament，不作为主统计结论。",
        "- RL baseline 必须保存训练曲线、checkpoint、validation selection rule 和训练预算，避免弱 baseline 质疑。",
        "- 所有新实验必须输出 source data、summary、统计表、中文/英文图、manifest 和复现命令。",
        "",
        "## 文件",
        "",
        "- 实验矩阵：`tables/six_experiment_matrix.csv`",
        "- 地图清单：`tables/external_track_manifest.csv`",
        "- 指标字典：`tables/six_experiment_metric_dictionary.csv`",
        "- 命令路线：`tables/six_experiment_command_plan.csv`",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export the six-experiment T-ITS protocol pack.")
    parser.add_argument("--out-dir", default=OUT_DIR)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    experiments = experiment_rows()
    tracks = track_manifest()
    metrics = metric_rows()
    commands = command_rows(experiments)
    report = {
        "status": "protocol_ready",
        "main_method": MAIN_METHOD,
        "paper_dlc_baselines": PAPER_DLC_BASELINES,
        "rl_baselines": RL_BASELINES,
        "rule_baselines": RULE_BASELINES,
        "ablation_variants": ABLATIONS,
        "experiments": experiments,
        "tracks": tracks,
        "metrics": metrics,
        "commands": commands,
        "claim_boundary": "This is a protocol pack. It does not claim expanded-matrix results until the listed runs are executed and summarized.",
    }
    paths = {
        "experiment_matrix": write_csv(
            out_dir / "tables" / "six_experiment_matrix.csv",
            experiments,
            ["experiment_id", "title_cn", "claim", "track_ids", "vehicle_counts", "seeds", "algorithms", "reuse_existing_data", "status"],
        ),
        "track_manifest": write_csv(
            out_dir / "tables" / "external_track_manifest.csv",
            tracks,
            ["track_id", "track_path", "role"],
        ),
        "metric_dictionary": write_csv(
            out_dir / "tables" / "six_experiment_metric_dictionary.csv",
            metrics,
            ["metric", "name_cn", "tier", "definition"],
        ),
        "command_plan": write_csv(
            out_dir / "tables" / "six_experiment_command_plan.csv",
            commands,
            ["command_id", "scope", "command", "status"],
        ),
        "protocol_json": write_json(out_dir / "materials" / "six_experiment_protocol.json", report),
        "protocol_md": write_text(out_dir / "materials" / "SIX_EXPERIMENT_PROTOCOL.md", build_markdown(report)),
    }
    manifest = {
        "status": "pass",
        "out_dir": args.out_dir,
        "summary": {
            "experiment_count": len(experiments),
            "track_count": len(tracks),
            "metric_count": len(metrics),
            "command_count": len(commands),
        },
        "paths": paths,
        "claim_boundary": report["claim_boundary"],
    }
    paths["manifest"] = write_json(out_dir / "tits_six_experiment_protocol_pack_manifest.json", manifest)
    print(json.dumps({"manifest": paths["manifest"], "status": "pass", "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
