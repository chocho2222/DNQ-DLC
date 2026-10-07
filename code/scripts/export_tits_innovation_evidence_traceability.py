#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


PYTHON_CMD = "/home/itrc/.conda/envs/vlm_planner/bin/python"


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def path_tokens(value):
    tokens = []
    for token in str(value or "").replace("\n", ";").split(";"):
        token = token.strip().strip("`")
        if token and not token.startswith("http") and "*" not in token:
            tokens.append(token)
    return tokens


def existing_status(root, refs):
    missing = []
    checked = []
    for ref in refs:
        for token in path_tokens(ref):
            checked.append(token)
            if not (root / token).exists():
                missing.append(token)
    return checked, missing


def source_summary(root):
    source_path = root / "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv"
    rows = read_csv(source_path)
    algorithms = sorted({row.get("algorithm", "") for row in rows if row.get("algorithm")})
    cases = sorted(
        {
            "|".join(
                [
                    row.get("_benchmark", ""),
                    row.get("num_agents", ""),
                    row.get("seed", ""),
                    row.get("track_path", ""),
                    row.get("traffic_profile", ""),
                ]
            )
            for row in rows
            if row.get("_benchmark", "") and row.get("seed", "")
        }
    )
    return {
        "path": source_path.as_posix() if source_path.is_absolute() else str(source_path),
        "row_count": len(rows),
        "algorithm_count": len(algorithms),
        "case_count": len(cases),
        "algorithms": algorithms,
    }


def innovation_rows():
    return [
        {
            "innovation_id": "I1",
            "innovation_cn": "运行时动态邻域图构建",
            "short_name": "runtime dynamic-neighborhood graph",
            "method_writeup_cn": (
                "目标车每个决策步不使用固定车辆槽位，而是根据相对距离、前后关系、横向偏移和潜在交互风险动态选择邻居。"
                "模型输入仍保持固定的最大邻居预算 max_neighbors=3，通过 slot mask 表示有效邻居，因此同一个训练好的图世界模型可以在线处理 4/5/6/8 车场景。"
            ),
            "code_refs": "gym_multi_car_racing/multi_car_racing.py; dlc/graph_policy.py; dlc/graph_world_model.py; dlc/policies.py",
            "config_refs": "configs/tits_dynamic_graph_experiments.json",
            "algorithm_refs": "v6_runtime_dynamic_neighborhood; v6_runtime_dynamic_neighborhood_safe; quality_proposal_dlc_world_v1",
            "evidence_refs": (
                "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md; "
                "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv; "
                "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/CONFIRMATORY_EVIDENCE_REPORT.md"
            ),
            "metric_focus": "车辆数外推、决策延迟、Desirable overtaking behavior rate、草地率",
            "safe_claim_cn": "在当前仿真 benchmark 中，固定 max-neighbors 的运行时邻域选择支持多车辆数量在线评估，并改善 DLC world model 的交互建模质量。",
            "boundary_cn": "最多只证明当前 4/5/6/8 车和 Monza 设置；不证明任意交通密度实时可行。",
            "forbidden_claim_cn": "不能写成无需限制即可泛化到任意车辆数或真实道路交通。",
        },
        {
            "innovation_id": "I2",
            "innovation_cn": "以 DLC-style graph world model 为算法主体",
            "short_name": "DLC-style graph world model core",
            "method_writeup_cn": (
                "当前方法不是纯规则算法，也不是单独的行为克隆策略；它保留 DLC world model 的想象 rollout 和风险预测主题，"
                "并把优化集中在动态图输入、候选规划、风险/质量评分和执行约束上。"
            ),
            "code_refs": "dlc/graph_world_model.py; dlc/graph_policy.py; scripts/train_graph_risk_world_model.py",
            "config_refs": "configs/tits_dynamic_graph_experiments.json",
            "algorithm_refs": "v6_runtime_dynamic_neighborhood_safe; dlc_world_original; dlc_world_balanced; dlc_world_safety; dlc_world_fast",
            "evidence_refs": (
                "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/materials/MODEL_ARTIFACT_INTEGRITY_AUDIT.md; "
                "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv; "
                "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md"
            ),
            "metric_focus": "与原始 DLC 和三个 DLC 变种的成对比较",
            "safe_claim_cn": "优化方法仍属于 DLC world-model family，可与原始 DLC 及其调参变种进行同族对比。",
            "boundary_cn": "不能把规则专家或 quality proposal 分支混写成 DLC world model 消融本体。",
            "forbidden_claim_cn": "不能声称当前模型是完全不同范式并与 DLC baseline 无关。",
        },
        {
            "innovation_id": "I3",
            "innovation_cn": "超车感知候选规划与评分",
            "short_name": "overtake-aware candidate planning",
            "method_writeup_cn": (
                "在线 planner 从 world model rollout、基础 actor 和 quality proposal 中组织候选动作，"
                "并在评分中显式考虑目标车相对前车的进度、开始超车到完成超车的时间和安全可行性，而不是只追求瞬时速度。"
            ),
            "code_refs": "dlc/graph_world_model.py; dlc/policies.py; scripts/run_tits_dynamic_graph_evaluation.py",
            "config_refs": "configs/tits_dynamic_graph_experiments.json",
            "algorithm_refs": "v6_runtime_dynamic_neighborhood_safe; ours_no_overtake_aware_planner; quality_proposal_dlc_world_v1",
            "evidence_refs": (
                "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md; "
                "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md; "
                "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_paired_tests_vs_dlc.csv"
            ),
            "metric_focus": "超车成功率、开始到完成超车时间、case-level 胜负",
            "safe_claim_cn": "相对原始 DLC，超车感知规划显著缩短完成超车时间，并提升完成质量。",
            "boundary_cn": "若某些 case 中前车过快或间隙不足，planner 仍可能选择保守跟车或失败。",
            "forbidden_claim_cn": "不能声称每个 case 都一定完成Desirable overtaking behavior。",
        },
        {
            "innovation_id": "I4",
            "innovation_cn": "安全、草地、车道质量联合约束",
            "short_name": "risk/lane/grass quality scoring",
            "method_writeup_cn": (
                "v6-safe 在 DLC 风险预测基础上增加不确定性、草地惩罚、车道质量和近距间隙惩罚，"
                "用硬安全执行和软质量评分共同抑制绕远、长时间草地行驶和贴车高风险超车。"
            ),
            "code_refs": "dlc/graph_world_model.py; dlc/policies.py",
            "config_refs": "configs/tits_dynamic_graph_experiments.json",
            "algorithm_refs": "v6_runtime_dynamic_neighborhood_safe; v6_runtime_dynamic_neighborhood; dlc_world_safety",
            "evidence_refs": (
                "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/FAILURE_ATLAS.md; "
                "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tables/ablation_contribution_paired.csv; "
                "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv"
            ),
            "metric_focus": "Desirable overtaking behavior rate、赛道内超车率、草地率、恢复时间",
            "safe_claim_cn": "安全/质量评分把收益从单纯超车成功转向赛道内和Desirable overtaking behavior质量。",
            "boundary_cn": "安全权重带来质量/成功率/延迟折中，不应写成无代价提升。",
            "forbidden_claim_cn": "不能写成保证无碰撞、保证不出赛道或真实道路安全验证。",
        },
        {
            "innovation_id": "I5",
            "innovation_cn": "质量 proposal 辅助分支",
            "short_name": "quality proposal branch",
            "method_writeup_cn": (
                "质量 proposal 是一个图 BC 辅助 actor，用于向 DLC world-model planner 提供质量过滤候选动作。"
                "确认性矩阵显示它可提高完成率，但独立使用时desirable overtaking behavior quality不如 v6-safe，因此更适合作为候选生成分支。"
            ),
            "code_refs": "dlc/graph_world_model.py; scripts/train_graph_bc.py",
            "config_refs": "configs/tits_dynamic_graph_experiments.json",
            "algorithm_refs": "quality_proposal_dlc_world_v1; v6_runtime_dynamic_neighborhood_safe",
            "evidence_refs": (
                "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md; "
                "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/tables/model_artifact_inventory.csv"
            ),
            "metric_focus": "成功率与Desirable overtaking behavior rate之间的差异",
            "safe_claim_cn": "quality proposal 提供有用候选，但不能单独替代风险/质量规划。",
            "boundary_cn": "质量分支当前仍依赖仿真数据和遥测观察，不是视觉端到端驾驶策略。",
            "forbidden_claim_cn": "不能写成 quality proposal 本身就是最终最优算法。",
        },
        {
            "innovation_id": "I6",
            "innovation_cn": "顶刊级可复现证据链",
            "short_name": "journal-grade reproducibility chain",
            "method_writeup_cn": (
                "围绕 30 matched cases × 8 algorithms 的冻结确认性矩阵，建立 source data、case commands、checksum、"
                "环境审计、确定性 smoke、泄漏/调参边界、release plan 和 reviewer packet，使 Methods、Results、图件和开源材料互相可追溯。"
            ),
            "code_refs": (
                "scripts/export_tits_confirmatory_evidence_pack.py; scripts/export_tits_reproducibility_capsule.py; "
                "scripts/export_tits_public_release_plan.py; scripts/export_tits_reviewer_replication_packet.py"
            ),
            "config_refs": "configs/tits_dynamic_graph_experiments.json; docs/tits_dynamic_graph_reproducibility_protocol.md",
            "algorithm_refs": "all formal algorithms",
            "evidence_refs": (
                "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md; "
                "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.md; "
                "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/materials/DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md; "
                "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md"
            ),
            "metric_focus": "复现性、完整性、审稿风险控制",
            "safe_claim_cn": "当前材料支持第三方按冻结命令和 source data 复查仿真 benchmark 与图表生成链路。",
            "boundary_cn": "DOI、license、最终作者声明、IEEE 模板和公开仓库发布仍需作者侧完成。",
            "forbidden_claim_cn": "不能把本地审计 PASS 写成论文已可接收或真实部署已验证。",
        },
    ]


def build_code_map(innovations):
    rows = []
    for item in innovations:
        for ref in path_tokens(item["code_refs"]):
            rows.append(
                {
                    "innovation_id": item["innovation_id"],
                    "innovation_cn": item["innovation_cn"],
                    "code_or_config_path": ref,
                    "role": "implementation",
                    "evidence_type": "source_code",
                }
            )
        for ref in path_tokens(item["config_refs"]):
            rows.append(
                {
                    "innovation_id": item["innovation_id"],
                    "innovation_cn": item["innovation_cn"],
                    "code_or_config_path": ref,
                    "role": "configuration_or_protocol",
                    "evidence_type": "config_doc",
                }
            )
    return rows


def build_experiment_map(innovations):
    rows = []
    for item in innovations:
        for ref in path_tokens(item["evidence_refs"]):
            rows.append(
                {
                    "innovation_id": item["innovation_id"],
                    "innovation_cn": item["innovation_cn"],
                    "algorithm_refs": item["algorithm_refs"],
                    "experiment_or_artifact": ref,
                    "metric_focus": item["metric_focus"],
                    "supporting_result": item["safe_claim_cn"],
                    "formal_status": "formal_evidence_or_formal_audit",
                    "source_data": "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
                }
            )
    return rows


def build_boundaries(innovations):
    return [
        {
            "innovation_id": item["innovation_id"],
            "innovation_cn": item["innovation_cn"],
            "safe_claim_cn": item["safe_claim_cn"],
            "boundary_cn": item["boundary_cn"],
            "forbidden_claim_cn": item["forbidden_claim_cn"],
            "recommended_manuscript_location": "Methods / Experiments / Results / Discussion",
        }
        for item in innovations
    ]


def build_method_matrix():
    return [
        {
            "method_subsection_cn": "问题定义与观测",
            "writing_point_cn": "定义目标车最后身位起步、周边车动态出现、telemetry_dynamic 观测和固定邻居预算。",
            "code_refs": "gym_multi_car_racing/multi_car_racing.py; configs/tits_dynamic_graph_experiments.json",
            "figure_table_refs": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv",
            "result_refs": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_CARD.md",
            "caution_cn": "说明这是仿真遥测设定，不是视觉传感器真实感知。",
        },
        {
            "method_subsection_cn": "动态邻域图编码",
            "writing_point_cn": "描述 interaction-priority 邻居选择、slot mask、max_neighbors=3 和车辆数量外推机制。",
            "code_refs": "dlc/graph_policy.py; dlc/graph_world_model.py",
            "figure_table_refs": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_complexity_crosswalk.csv",
            "result_refs": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md",
            "caution_cn": "不要声称无限车辆泛化，只写固定预算局部交互建模。",
        },
        {
            "method_subsection_cn": "DLC graph world model",
            "writing_point_cn": "说明主算法保留 DLC world-model rollout、risk prediction 和图策略结构，并以原始 DLC 与 DLC 变种为主要对比。",
            "code_refs": "dlc/graph_world_model.py; scripts/train_graph_risk_world_model.py",
            "figure_table_refs": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv",
            "result_refs": "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/materials/MODEL_ARTIFACT_INTEGRITY_AUDIT.md",
            "caution_cn": "把规则专家写作 baseline，不写成 world-model 消融。",
        },
        {
            "method_subsection_cn": "超车感知在线规划",
            "writing_point_cn": "说明 planner_horizon、planner_candidates、候选动作来源、进度/间隙/完成时间相关评分。",
            "code_refs": "dlc/graph_world_model.py; scripts/run_tits_dynamic_graph_evaluation.py",
            "figure_table_refs": "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/figures/figure_dynamic_dlc_contribution_attribution.pdf",
            "result_refs": "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md",
            "caution_cn": "把失败 case 和保守行为作为限制，而不是隐藏。",
        },
        {
            "method_subsection_cn": "安全与质量评分",
            "writing_point_cn": "说明 risk/uncertainty/lane/grass/close-gap 权重与 hard safety shield 如何影响候选选择。",
            "code_refs": "dlc/graph_world_model.py; configs/tits_dynamic_graph_experiments.json",
            "figure_table_refs": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/figures/figure_confirmatory_overtake_evidence_cn.pdf",
            "result_refs": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/FAILURE_ATLAS.md",
            "caution_cn": "不要使用保证式安全语言。",
        },
        {
            "method_subsection_cn": "实验与复现协议",
            "writing_point_cn": "描述 30 matched cases、8 algorithms、source data、case commands、统计分析和 GIF 只作为代表性视觉证据。",
            "code_refs": "scripts/run_tits_dynamic_graph_evaluation.py; scripts/summarize_tits_dynamic_graph_online.py",
            "figure_table_refs": "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/FIGURE_TABLE_PLACEMENT_PLAN.md",
            "result_refs": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md",
            "caution_cn": "smoke、partial summary、调参 sweep 不进入正式 Results。",
        },
    ]


def build_algorithm_box_rows():
    return [
        {
            "step_id": "A1",
            "step_name_cn": "读取在线遥测状态",
            "operation_cn": "从仿真器读取目标车和周边车辆的进度、相对位置、速度、航向、草地/赛道质量等遥测量。",
            "main_inputs": "simulator telemetry state",
            "main_outputs": "ego state and candidate neighbor states",
            "code_refs": "gym_multi_car_racing/multi_car_racing.py; scripts/run_tits_dynamic_graph_evaluation.py",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/materials/TRACE_SCHEMA_DICTIONARY.md",
            "writing_boundary_cn": "说明这是 simulator telemetry，不写成真实传感器感知。",
        },
        {
            "step_id": "A2",
            "step_name_cn": "运行时选择交互邻居",
            "operation_cn": "按相对进度、距离、横向偏移和潜在交互风险排序周边车辆，保留最多 max_neighbors=3 个邻居。",
            "main_inputs": "ego state; all surrounding vehicle states; max_neighbors",
            "main_outputs": "ordered local neighbor set",
            "code_refs": "dlc/graph_policy.py; dlc/policies.py",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_complexity_crosswalk.csv",
            "writing_boundary_cn": "写成固定预算局部邻域，不写成无限车辆全图推理。",
        },
        {
            "step_id": "A3",
            "step_name_cn": "构建带 mask 的局部图输入",
            "operation_cn": "把目标车作为 ego node，把有效邻居填入固定槽位，并用 slot mask 标记 padding 与有效车辆。",
            "main_inputs": "ego state; ordered local neighbor set",
            "main_outputs": "graph observation tensor and valid-neighbor mask",
            "code_refs": "dlc/graph_policy.py; dlc/graph_world_model.py",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv",
            "writing_boundary_cn": "强调同一模型输入宽度通过 mask 处理 4/5/6/8 车评估。",
        },
        {
            "step_id": "A4",
            "step_name_cn": "生成候选动作序列",
            "operation_cn": "从 DLC actor、world-model planner 和 quality proposal 分支组织候选 steering/throttle/brake 序列。",
            "main_inputs": "graph observation; actor proposal; planner budget",
            "main_outputs": "candidate action sequences",
            "code_refs": "dlc/graph_world_model.py; dlc/policies.py",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_REPORT.md",
            "writing_boundary_cn": "quality proposal 是候选来源，不写成独立最终最优控制器。",
        },
        {
            "step_id": "A5",
            "step_name_cn": "世界模型短视域评估",
            "operation_cn": "使用 DLC-style graph world model 对候选动作进行短视域 rollout，预测进度、风险、不确定性和质量相关量。",
            "main_inputs": "graph observation; candidate action sequences",
            "main_outputs": "predicted progress/risk/quality scores",
            "code_refs": "dlc/graph_world_model.py; scripts/train_graph_risk_world_model.py",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/materials/MODEL_ARTIFACT_INTEGRITY_AUDIT.md",
            "writing_boundary_cn": "保持 DLC world-model lineage，不写成与 DLC baseline 无关的新范式。",
        },
        {
            "step_id": "A6",
            "step_name_cn": "超车感知安全/质量评分",
            "operation_cn": "联合进度收益、开始到完成超车时间、草地暴露、车道质量、近距风险和不确定性惩罚，对候选序列排序。",
            "main_inputs": "world-model predictions; overtake metrics; safety weights",
            "main_outputs": "ranked candidate sequences",
            "code_refs": "dlc/graph_world_model.py; configs/tits_dynamic_graph_experiments.json",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md",
            "writing_boundary_cn": "不能写成保证无碰撞或保证不出赛道。",
        },
        {
            "step_id": "A7",
            "step_name_cn": "执行首个动作并记录轨迹",
            "operation_cn": "执行评分最高序列的首个连续控制动作，推进仿真一步，并记录 summary、trace、事件和延迟。",
            "main_inputs": "best candidate sequence",
            "main_outputs": "control action; next simulator state; provenance trace",
            "code_refs": "scripts/run_tits_dynamic_graph_evaluation.py",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/materials/RUN_LEVEL_PROVENANCE_AUDIT.md; outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/materials/OVERTAKE_EVENT_CONSISTENCY_AUDIT.md",
            "writing_boundary_cn": "GIF 只作代表性视觉证据，正式 claim 来自 240-run source data。",
        },
    ]


def build_notation_rows():
    return [
        {"symbol": "s_t", "meaning_cn": "t 时刻仿真遥测状态", "used_in": "problem formulation; online decision loop", "boundary_cn": "telemetry-only simulator state"},
        {"symbol": "e_t", "meaning_cn": "目标车 ego 节点状态", "used_in": "dynamic graph construction", "boundary_cn": "target vehicle starts from last grid position"},
        {"symbol": "V_t", "meaning_cn": "t 时刻可观测周边车辆集合", "used_in": "neighbor selection", "boundary_cn": "simulated traffic vehicles only"},
        {"symbol": "K", "meaning_cn": "最大邻居预算，当前确认性实验为 max_neighbors=3", "used_in": "fixed-width graph input", "boundary_cn": "not unlimited-density reasoning"},
        {"symbol": "N_t", "meaning_cn": "由 interaction priority 选出的局部邻居集合，|N_t| <= K", "used_in": "runtime dynamic-neighborhood graph", "boundary_cn": "padded slots are masked"},
        {"symbol": "m_t", "meaning_cn": "slot mask，标记有效邻居与 padding", "used_in": "graph model input", "boundary_cn": "supports evaluated 4/5/6/8-car settings"},
        {"symbol": "a_t", "meaning_cn": "连续控制动作 steering/throttle/brake", "used_in": "candidate execution", "boundary_cn": "simulator action space"},
        {"symbol": "H", "meaning_cn": "world-model planner horizon", "used_in": "short-horizon rollout", "boundary_cn": "configured per algorithm card"},
        {"symbol": "C", "meaning_cn": "每步候选动作序列数量", "used_in": "online planner budget", "boundary_cn": "latency/quality trade-off"},
        {"symbol": "J(a_{t:t+H})", "meaning_cn": "候选序列评分函数，综合进度、风险、草地、车道质量、不确定性和超车项", "used_in": "candidate ranking", "boundary_cn": "benchmark-tuned scoring, not certified safety objective"},
        {"symbol": "r_g", "meaning_cn": "草地/离赛道暴露率", "used_in": "quality and safety metrics", "boundary_cn": "simulation proxy"},
        {"symbol": "T_o", "meaning_cn": "开始超车到完成超车的时间步数", "used_in": "primary overtake efficiency metric", "boundary_cn": "conditional on both algorithms completing the event"},
    ]


def build_complexity_rows():
    return [
        {
            "component": "runtime neighbor selection",
            "dominant_terms": "O(M log M) sort or O(MK) top-K scoring",
            "current_bound": "M <= evaluated traffic count minus ego; K=3",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md",
            "boundary_cn": "复杂度随可观测周边车数量增加，但模型输入保持固定 K 槽位。",
        },
        {
            "component": "graph world-model inference",
            "dominant_terms": "O(C * H * f(K))",
            "current_bound": "planner candidates and horizon fixed by algorithm card",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv",
            "boundary_cn": "延迟 claim 只覆盖确认性矩阵中的 4/5/6/8 车设置。",
        },
        {
            "component": "candidate scoring and safety filtering",
            "dominant_terms": "O(C * H)",
            "current_bound": "v6-safe uses moderate candidate budget and stronger risk/grass weights",
            "evidence_refs": "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/materials/COMPUTE_TIMING_BOUNDARY_AUDIT.md",
            "boundary_cn": "历史完整 wall-clock/GPU 利用率不可用；使用决策延迟和复现成本代理。",
        },
    ]


def build_report(
    manifest,
    innovations,
    code_map,
    experiment_map,
    boundaries,
    method_matrix,
    algorithm_box_rows,
    notation_rows,
    complexity_rows,
):
    lines = [
        "# 创新点-证据追溯矩阵",
        "",
        "该文件把当前优化后的 DLC world model 的核心创新点逐项连接到代码、配置、对比算法、正式实验和写作边界。它的作用是让 Methods、Ablation、Results、Discussion 和审稿复现材料能互相校验，而不是新增实验结果。",
        "",
        "## 总览",
        "",
        f"- 状态: `{manifest['status']}`",
        f"- 创新点数量: {manifest['summary']['innovation_count']}",
        f"- 代码/配置映射行数: {manifest['summary']['code_map_rows']}",
        f"- 实验证据映射行数: {manifest['summary']['experiment_map_rows']}",
        f"- 正式 source data 行数: {manifest['summary']['source_data_rows']}",
        f"- 正式算法数: {manifest['summary']['source_data_algorithm_count']}",
        f"- 缺失引用数: {manifest['summary']['missing_reference_count']}",
        "",
        "## 创新点详述",
        "",
    ]
    for item in innovations:
        lines.extend(
            [
                f"### {item['innovation_id']}. {item['innovation_cn']}",
                "",
                f"**方法写法**：{item['method_writeup_cn']}",
                "",
                f"**关联算法**：{item['algorithm_refs']}",
                "",
                f"**代码/配置**：{item['code_refs']}; {item['config_refs']}",
                "",
                f"**证据入口**：{item['evidence_refs']}",
                "",
                f"**指标重点**：{item['metric_focus']}",
                "",
                f"**可写 claim**：{item['safe_claim_cn']}",
                "",
                f"**边界**：{item['boundary_cn']}",
                "",
                f"**禁止写法**：{item['forbidden_claim_cn']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Methods 写作矩阵",
            "",
            "| 小节 | 写作要点 | 代码入口 | 证据/图表 | 注意事项 |",
            "|---|---|---|---|---|",
        ]
    )
    for row in method_matrix:
        lines.append(
            f"| {row['method_subsection_cn']} | {row['writing_point_cn']} | `{row['code_refs']}` | `{row['result_refs']}` | {row['caution_cn']} |"
        )
    lines.extend(
        [
            "",
            "## Algorithm Box 文字版",
            "",
            "该表可直接改写为论文 Methods 中的 Algorithm 1。它描述在线执行流程，不新增训练或实验结果。",
            "",
            "| Step | Operation | Inputs | Outputs | Code route | Writing boundary |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in algorithm_box_rows:
        lines.append(
            f"| {row['step_id']} {row['step_name_cn']} | {row['operation_cn']} | {row['main_inputs']} | {row['main_outputs']} | `{row['code_refs']}` | {row['writing_boundary_cn']} |"
        )
    lines.extend(
        [
            "",
            "## Methods 符号表",
            "",
            "| Symbol | 含义 | 用于 | 边界 |",
            "|---|---|---|---|",
        ]
    )
    for row in notation_rows:
        lines.append(f"| `{row['symbol']}` | {row['meaning_cn']} | {row['used_in']} | {row['boundary_cn']} |")
    lines.extend(
        [
            "",
            "## 复杂度与实时性写作边界",
            "",
            "| Component | Dominant terms | Current bound | Evidence | Boundary |",
            "|---|---|---|---|---|",
        ]
    )
    for row in complexity_rows:
        lines.append(
            f"| {row['component']} | `{row['dominant_terms']}` | {row['current_bound']} | `{row['evidence_refs']}` | {row['boundary_cn']} |"
        )
    lines.extend(
        [
            "",
            "## 与顶刊写作的关系",
            "",
            "- Methods 中应把算法主题明确写成“optimized DLC-style graph world model”，再展开动态图邻域、候选规划和安全/质量评分。",
            "- Ablation/Analysis 中把 DLC-balanced、DLC-safety、DLC-fast 作为原始 DLC world model 的调参变种，把 rule expert 作为强规则 baseline。",
            "- Results 中优先报告 overtake success、desirable/on-track overtake、start-to-completion time、grass rate、latency 和 paired deltas。",
            "- Discussion 中明确限制：仿真遥测观测、有限车辆数、单一 Monza 外部赛道、真实道路安全未验证、历史训练 seed 日志不完整。",
            "- Algorithm box、符号表和复杂度段落必须和 algorithm cards、runtime scalability、trace schema、casewise diagnostics 互相一致。",
            "",
            "## 生成命令",
            "",
            "```bash",
            f"{PYTHON_CMD} scripts/export_tits_innovation_evidence_traceability.py --out-dir outputs/tits_dynamic_graph/tits_innovation_evidence_traceability",
            "```",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export innovation-to-evidence traceability material for the T-ITS dynamic DLC package.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_innovation_evidence_traceability")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = root / args.out_dir
    materials_dir = out_dir / "materials"
    tables_dir = out_dir / "tables"
    materials_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    innovations = innovation_rows()
    code_map = build_code_map(innovations)
    experiment_map = build_experiment_map(innovations)
    boundaries = build_boundaries(innovations)
    method_matrix = build_method_matrix()
    algorithm_box_rows = build_algorithm_box_rows()
    notation_rows = build_notation_rows()
    complexity_rows = build_complexity_rows()
    src = source_summary(root)

    all_refs = []
    for item in innovations:
        all_refs.extend([item["code_refs"], item["config_refs"], item["evidence_refs"]])
    for row in method_matrix:
        all_refs.extend([row["code_refs"], row["figure_table_refs"], row["result_refs"]])
    for row in algorithm_box_rows:
        all_refs.extend([row["code_refs"], row["evidence_refs"]])
    for row in complexity_rows:
        all_refs.append(row["evidence_refs"])
    checked, missing = existing_status(root, all_refs)

    qa = {
        "status": "pass" if not missing and src["row_count"] == 240 and src["algorithm_count"] >= 8 else "review_required",
        "checked_reference_count": len(checked),
        "missing_reference_count": len(missing),
        "missing_references": sorted(set(missing)),
        "source_data": src,
        "note": "This traceability package routes existing formal evidence; it does not add new simulation runs.",
    }
    manifest = {
        "status": qa["status"],
        "out_dir": args.out_dir,
        "summary": {
            "innovation_count": len(innovations),
            "code_map_rows": len(code_map),
            "experiment_map_rows": len(experiment_map),
            "claim_boundary_rows": len(boundaries),
            "method_matrix_rows": len(method_matrix),
            "algorithm_box_rows": len(algorithm_box_rows),
            "notation_rows": len(notation_rows),
            "complexity_rows": len(complexity_rows),
            "source_data_rows": src["row_count"],
            "source_data_algorithm_count": src["algorithm_count"],
            "missing_reference_count": len(missing),
        },
        "paths": {},
        "qa": qa,
    }

    manifest["paths"] = {
        "report_md": write_text(
            materials_dir / "INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md",
            build_report(
                manifest,
                innovations,
                code_map,
                experiment_map,
                boundaries,
                method_matrix,
                algorithm_box_rows,
                notation_rows,
                complexity_rows,
            ),
        ),
        "qa_json": write_json(materials_dir / "INNOVATION_EVIDENCE_TRACEABILITY_QA.json", qa),
        "innovation_to_code_map_csv": write_csv(
            tables_dir / "innovation_to_code_map.csv",
            code_map,
            ["innovation_id", "innovation_cn", "code_or_config_path", "role", "evidence_type"],
        ),
        "innovation_to_experiment_map_csv": write_csv(
            tables_dir / "innovation_to_experiment_map.csv",
            experiment_map,
            [
                "innovation_id",
                "innovation_cn",
                "algorithm_refs",
                "experiment_or_artifact",
                "metric_focus",
                "supporting_result",
                "formal_status",
                "source_data",
            ],
        ),
        "innovation_claim_boundaries_csv": write_csv(
            tables_dir / "innovation_claim_boundaries.csv",
            boundaries,
            [
                "innovation_id",
                "innovation_cn",
                "safe_claim_cn",
                "boundary_cn",
                "forbidden_claim_cn",
                "recommended_manuscript_location",
            ],
        ),
        "method_section_writing_matrix_csv": write_csv(
            tables_dir / "method_section_writing_matrix.csv",
            method_matrix,
            [
                "method_subsection_cn",
                "writing_point_cn",
                "code_refs",
                "figure_table_refs",
                "result_refs",
                "caution_cn",
            ],
        ),
        "method_algorithm_box_csv": write_csv(
            tables_dir / "method_algorithm_box.csv",
            algorithm_box_rows,
            [
                "step_id",
                "step_name_cn",
                "operation_cn",
                "main_inputs",
                "main_outputs",
                "code_refs",
                "evidence_refs",
                "writing_boundary_cn",
            ],
        ),
        "method_notation_table_csv": write_csv(
            tables_dir / "method_notation_table.csv",
            notation_rows,
            ["symbol", "meaning_cn", "used_in", "boundary_cn"],
        ),
        "method_complexity_boundary_csv": write_csv(
            tables_dir / "method_complexity_boundary.csv",
            complexity_rows,
            ["component", "dominant_terms", "current_bound", "evidence_refs", "boundary_cn"],
        ),
    }
    manifest_path = write_json(out_dir / "tits_innovation_evidence_traceability_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": manifest["status"], "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
