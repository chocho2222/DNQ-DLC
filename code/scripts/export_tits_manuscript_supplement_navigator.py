#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import json
from pathlib import Path


def load_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_csv_rows(path):
    path = Path(path)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in csv.DictReader(handle)))


def exists_nonempty(path):
    path = Path(path)
    return path.exists() and path.is_file() and path.stat().st_size > 0


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


def figure_table_plan():
    return [
        {
            "placement": "Main Fig. 1",
            "title_cn": "优化 DLC world model 的算法框架",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/METHODS_DRAFT.md",
            "source_data": "configs/tits_dynamic_graph_experiments.json; dlc/graph_world_model.py; dlc/policies.py",
            "recommended_use": "用文字或重新绘制的框图展示：遥测观测、运行时动态邻域图、graph world model、候选轨迹规划、风险/不确定性/草地/车道质量评分、安全执行。",
            "claim_supported": "说明本文算法是 DLC world model 的运行时动态图与安全规划增强，而不是纯规则车或独立 imitation policy。",
            "boundary": "该图是方法示意图，不提供额外实验结果。",
            "status": "planned_from_existing_material",
        },
        {
            "placement": "Main Fig. 2",
            "title_cn": "主要在线超车性能",
            "primary_artifact": "outputs/tits_dynamic_graph/manuscript_english_figures/figures/figure_dynamic_dlc_overtaking_english.pdf",
            "source_data": "outputs/tits_dynamic_graph/manuscript_english_figures/tables/figure_dynamic_dlc_overtaking_source_data.csv",
            "recommended_use": "作为英文投稿主结果图，展示成功率、desirable/on-track超车、草地暴露、完成耗时等主指标。",
            "claim_supported": "v6 dynamic-neighborhood DLC-safe 相比原始 DLC world model 在冻结在线矩阵中提升超车质量与效率。",
            "boundary": "图中结果来自仿真 benchmark，不代表真实道路部署。",
            "status": "ready",
        },
        {
            "placement": "Main Fig. 3 or Supplement Fig. S1",
            "title_cn": "贡献归因与消融",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/figures/figure_dynamic_dlc_contribution_attribution.pdf",
            "source_data": "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tables/ablation_contribution_overall.csv; outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tables/ablation_contribution_paired.csv",
            "recommended_use": "如果主文篇幅允许，放入主文 Fig. 3；若受限，放入补充材料并在主文 Results 引用。",
            "claim_supported": "动态邻域、安全规划、quality proposal 与 DLC 变种的贡献边界。",
            "boundary": "该归因包复用确认性矩阵和变种结果，不应写成新的随机化训练消融矩阵。",
            "status": "ready",
        },
        {
            "placement": "Supplement Fig. S2",
            "title_cn": "统计稳健性与多重比较",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/figures/figure_tits_statistical_robustness.pdf",
            "source_data": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv; outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_effect_sizes.csv",
            "recommended_use": "补充 Results 中的效应量、置信区间和 Holm 校正。",
            "claim_supported": "5 个预定义主假设在 Holm 校正后均显著。",
            "boundary": "这是冻结矩阵后的 reporting-layer 校正，不要称为实验前注册。",
            "status": "ready",
        },
        {
            "placement": "Supplement Fig. S2b",
            "title_cn": "实验设计、功效与稳定性审计",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/figures/figure_experimental_design_power_audit_cn.pdf",
            "source_data": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/experimental_design_coverage.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/primary_metric_stability.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/scenario_level_stability.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/case_influence_summary.csv",
            "recommended_use": "补充解释 30 matched cases、240 runs、6 个场景单元、主指标配对改善、case 胜/平/负和场景异质性。",
            "claim_supported": "主结论来自完整 matched-case 设计，但存在场景异质性，需要在 Results/Discussion 中保守表述。",
            "boundary": "该审计复用 frozen source data，不是新增仿真矩阵，也不替代更多外部赛道/高密度交通验证。",
            "status": "ready",
        },
        {
            "placement": "Supplement Fig. S2c",
            "title_cn": "leave-one-case 影响度审计",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/figures/figure_case_influence_audit_cn.pdf",
            "source_data": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/leave_one_case_influence.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/case_influence_summary.csv",
            "recommended_use": "补充说明主指标不是由单个 seed/case 主导；报告最高相对影响 case，并明确移除任一 case 后主指标方向仍保持。",
            "claim_supported": "逐 case leave-one-out 后主指标方向保持为正，但少数程序赛道 case 对成功率主效应影响较大，需要作为稳健性边界报告。",
            "boundary": "该审计仍基于已有 30 matched cases，不替代更多随机种子或新增外部赛道。",
            "status": "ready",
        },
        {
            "placement": "Supplement Fig. S3",
            "title_cn": "中文确认性证据图",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/figures/figure_confirmatory_overtake_evidence_cn.pdf",
            "source_data": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_overall_statistics.csv; outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_scenario_statistics.csv",
            "recommended_use": "中文汇报或补充材料使用；英文投稿主文优先使用英文图。",
            "claim_supported": "跨算法、跨场景的确认性结果概览。",
            "boundary": "中文图不替代 source data 和英文主图。",
            "status": "ready",
        },
        {
            "placement": "Supplement Videos V1-V4",
            "title_cn": "俯视图与第一视角动图",
            "primary_artifact": "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md",
            "source_data": "outputs/tits_dynamic_graph/publication_gifs/*/summaries/*.summary.json; outputs/tits_dynamic_graph/publication_gifs/*/traces/*.trace.json",
            "recommended_use": "展示 n8 外推和 Monza n6 外部赛道中 v6-safe 与原始 DLC 的代表性在线运行。",
            "claim_supported": "视觉验证目标车在线决策、赛道行为和第一视角行为差异。",
            "boundary": "GIF 是代表性可视化，不是统计主证据。",
            "status": "ready",
        },
        {
            "placement": "Supplement Fig. S4",
            "title_cn": "运行时扩展性与复杂度",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/figures/figure_runtime_scalability_cn.pdf",
            "source_data": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_scalability_by_vehicle_count.csv; outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_complexity_crosswalk.csv",
            "recommended_use": "补充 Results 中关于 n=8 外推、延迟和 max-neighbor 复杂度边界的表述。",
            "claim_supported": "运行时动态邻域在固定 max_neighbors=3 的模型输入下支持 4/5/6/8 车在线评估，并给出延迟-质量折中。",
            "boundary": "这是当前仿真矩阵中的经验扩展性证据，不证明任意车辆密度实时可行。",
            "status": "ready",
        },
        {
            "placement": "Supplementary Reproducibility Table",
            "title_cn": "计算资源与复现成本透明度",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.md",
            "source_data": "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_cost_by_algorithm.csv; outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_environment_snapshot.csv; outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tables/compute_reproduction_tiers.csv",
            "recommended_use": "用于 Methods/Reproducibility 或补充表，报告正式 240-run 矩阵的仿真步数、算法级延迟、GPU/环境快照、分层复现路线和 wall-clock 记录边界。",
            "claim_supported": "正式结果具备可复现命令、环境快照和计算规模说明，便于审稿人区分 smoke、reporting-layer 复核、完整在线矩阵重跑和视觉证据重建。",
            "boundary": "该报告不新增性能实验；其中 workload proxy 是由延迟和仿真步数派生，不等同于真实 wall-clock 训练/评估耗时或 GPU utilization。",
            "status": "ready",
        },
        {
            "placement": "Supplementary QC",
            "title_cn": "图件 source data 与格式审计",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "source_data": "outputs/tits_dynamic_graph/tits_figure_source_data_audit/tables/figure_source_data_checks.csv; outputs/tits_dynamic_graph/tits_figure_source_data_audit/tables/figure_source_table_checks.csv",
            "recommended_use": "作为投稿前图件质控材料，证明主图和补充图均有多格式导出、source table、图例和 QA/报告文件。",
            "claim_supported": "图件可追溯到 source data，便于审稿人和读者复查。",
            "boundary": "该审计不替代最终 IEEE 版式、caption、字号、色盲友好性和 PDF 合规检查。",
            "status": "ready",
        },
        {
            "placement": "Supplementary QC",
            "title_cn": "复现胶囊与结果指纹",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md",
            "source_data": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/tables/reproducibility_artifact_fingerprints.csv; outputs/tits_dynamic_graph/tits_reproducibility_capsule/tables/reproducibility_result_metric_fingerprints.csv; outputs/tits_dynamic_graph/tits_reproducibility_capsule/tables/reproducibility_gate_status.csv",
            "recommended_use": "作为审稿人快速核对复现路线、source data digest、case command digest、关键 artifact SHA256 和结果矩阵指纹的入口。",
            "claim_supported": "当前正式证据链具备集中式 provenance、integrity 和 gate 状态索引，便于第三方复查。",
            "boundary": "该 capsule 不新增实验结果；重跑确认性矩阵后 digest 可能变化，需重新生成。",
            "status": "ready",
        },
        {
            "placement": "Supplementary QC",
            "title_cn": "确定性 smoke 复现预检",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/materials/DETERMINISM_SMOKE_AUDIT.md",
            "source_data": "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tables/determinism_smoke_comparison.csv; outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tables/determinism_smoke_field_details.csv",
            "recommended_use": "作为审稿人本地复现入口的短程确定性预检，证明同 seed 短程在线评估关键 summary 指纹一致。",
            "claim_supported": "当前环境下 v6-safe 与 original DLC 的短程 smoke 评估可重复生成一致关键 summary 指纹。",
            "boundary": "该检查是 smoke-only，不作为论文性能结果；更换 GPU/CUDA/Box2D/依赖版本后需重跑。",
            "status": "ready",
        },
        {
            "placement": "Supplementary QC",
            "title_cn": "数据泄漏与调参来源审计",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/materials/DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md",
            "source_data": "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/case_split_boundary.csv; outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/exploratory_output_boundary.csv; outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/training_command_boundary.csv",
            "recommended_use": "投稿前说明训练输出、探索性调参输出和冻结确认性矩阵的边界，防止把 smoke/sweep/partial summary 写成正式结果。",
            "claim_supported": "正式 source data 来自 v6 confirmatory matrix；训练输出目录不重叠；8 车和 Monza 是有边界的外推/外部验证；探索输出仅作 provenance。",
            "boundary": "该审计不能证明训练时每个程序化 episode seed 与验证 seed 完全不重叠，因为历史训练日志未归档全部 episode seed。",
            "status": "ready",
        },
        {
            "placement": "Supplementary QC / Methods",
            "title_cn": "创新点-证据追溯矩阵",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md",
            "source_data": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_to_code_map.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_to_experiment_map.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_section_writing_matrix.csv",
            "recommended_use": "用于 Methods、Contributions、Ablation 和 Discussion 写作前核对每个创新点对应的代码、配置、正式证据、可写 claim 和禁止 claim。",
            "claim_supported": "当前算法创新点可以从代码、配置、算法卡、确认性矩阵和审计材料逐项追溯。",
            "boundary": "该矩阵是证据路由和写作约束材料，不是新增仿真实验结果。",
            "status": "ready",
        },
        {
            "placement": "Supplement Fig. S5 / Discussion QC",
            "title_cn": "指标阈值敏感性审计",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/figures/figure_metric_sensitivity_cn.pdf",
            "source_data": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/quality_threshold_sensitivity_grid.csv; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/paired_threshold_sensitivity_vs_dlc.csv; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/robustness_summary_by_algorithm.csv",
            "recommended_use": "用于补充说明desirable behavior/质量超车结论对草地率、横向偏移和完成耗时阈值的敏感性，并约束主文 claim 不写成任意指标定义下均最优。",
            "claim_supported": "v6-safe 相对原始 DLC 的优势在大多数质量阈值设置下保持，但存在后验阈值边界，需要保守表述。",
            "boundary": "这是后验敏感性分析，不是预注册主指标，也不新增仿真样本。",
            "status": "ready",
        },
        {
            "placement": "Supplementary QC",
            "title_cn": "写作 claim 语言边界审计",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_claim_language_audit/materials/CLAIM_LANGUAGE_AUDIT.md",
            "source_data": "outputs/tits_dynamic_graph/tits_claim_language_audit/tables/claim_language_scan_rows.csv; outputs/tits_dynamic_graph/tits_claim_language_audit/tables/claim_guardrail_trace.csv",
            "recommended_use": "投稿前检查摘要、结果、讨论、复现包和 README 是否出现真实道路安全、任意泛化、保证无碰撞等越界表述。",
            "claim_supported": "当前正式写作材料中的高风险短语均处于边界/限制上下文，没有未加限定的部署级安全 claim。",
            "boundary": "该审计是写作风险筛查，不证明科学正确性；最终改写 manuscript 或 rebuttal 后需重跑。",
            "status": "ready",
        },
        {
            "placement": "Supplementary QC / Claim Audit",
            "title_cn": "投稿 claim 证据完整性审计",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/materials/CLAIM_EVIDENCE_COMPLETENESS_AUDIT.md",
            "source_data": "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/tables/claim_evidence_completeness_matrix.csv; outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/tables/claim_evidence_path_index.csv; outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/tables/claim_boundary_requirements.csv",
            "recommended_use": "投稿前逐条检查摘要、Results、Methods、Discussion 和 rebuttal 中可写 claim 是否有正式 source data、统计证据、图表/补充材料、限制边界和 rebuttal 入口支撑。",
            "claim_supported": "主结果、超车质量、动态车辆数、Monza 外部赛道、失败边界、规则专家、指标敏感性、统计、case 稳定性、算法创新、复现、算力和 GIF 等核心 claim 已完成证据完整性路由。",
            "boundary": "该审计不新增实验，也不替代人工写作判断；若新增 claim、重写摘要/结论或重跑矩阵，需重新生成。",
            "status": "ready",
        },
        {
            "placement": "Reviewer Response Preparation",
            "title_cn": "审稿意见预案与修稿动作矩阵",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/materials/REVIEWER_REBUTTAL_READINESS_PACK.md",
            "source_data": "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/tables/reviewer_rebuttal_matrix.csv; outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/tables/manuscript_revision_action_items.csv; outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/tables/reviewer_rebuttal_evidence_index.csv",
            "recommended_use": "用于投稿前预演和返修阶段，将真实道路安全、外部有效性、动态车辆数、草地行为、规则专家、指标阈值、统计、多 case 稳定性、复现和 GIF 证据等潜在质疑对应到证据路径与修稿动作。",
            "claim_supported": "当前正式证据链已经整理成审稿问题-证据-可写回应-禁止夸大表述的闭环，便于作者准备 T-ITS rebuttal 和 manuscript revision。",
            "boundary": "该材料不新增实验，也不能替代作者对真实审稿意见的逐条人工回应；重跑矩阵、改主文或更新证据包后需重新生成。",
            "status": "ready",
        },
        {
            "placement": "Submission Metadata",
            "title_cn": "T-ITS投稿元数据与声明草稿",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/IEEE_TITS_SUBMISSION_METADATA_PACK.md",
            "source_data": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/keyword_plan.csv; outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/submission_portal_checklist.csv",
            "recommended_use": "用于 ScholarOne/IEEE 模板填写前的标题、摘要、关键词、cover letter、AI disclosure、数据代码可用性和作者行动项整理。",
            "claim_supported": "投稿元数据和声明草稿已和当前证据链对齐。",
            "boundary": "作者仍需最终确认作者信息、ORCID、基金、利益冲突、AI工具细节、DOI/URL 和模板 PDF。",
            "status": "ready",
        },
        {
            "placement": "Open-source Release",
            "title_cn": "GitHub开源最小复现与release清单",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md",
            "source_data": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tables/github_repository_inventory.csv; outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tables/github_release_author_actions.csv",
            "recommended_use": "用于开源仓库首页、引用文件、贡献指南、模型卡、数据卡和release行动项准备。",
            "claim_supported": "当前材料已经整理成可公开复现的最小仓库结构草稿，并与正式证据链、manifest 和 release plan 对齐。",
            "boundary": "该包是作者侧开源发布准备材料，不是新增实验结果；最终 DOI、URL、license、作者信息和 release tag 仍需人工确认。",
            "status": "ready",
        },
        {
            "placement": "Submission Closure",
            "title_cn": "作者侧投稿闭环追踪",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/materials/AUTHOR_SUBMISSION_CLOSURE_PACK.md",
            "source_data": "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_owned_action_matrix.csv; outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_placeholder_inventory.csv; outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/post_author_action_regeneration_commands.csv",
            "recommended_use": "用于最终投稿前把 DOI/accession、代码仓库、license、IEEE模板、作者/ORCID、基金/冲突/AI声明、门户元数据、补充材料选择和最终 checksum freeze 串成可执行闭环。",
            "claim_supported": "本地技术证据已经准备好支撑作者完成真实投稿和归档动作，并明确每个作者动作完成后应重跑哪些审计。",
            "boundary": "该包不表示 DOI、license、ScholarOne 填报或最终 IEEE 模板已经完成；这些仍需作者侧真实操作。",
            "status": "ready",
        },
        {
            "placement": "Data Archive Metadata",
            "title_cn": "FAIR 数据归档元数据草案",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/materials/FAIR_ARCHIVE_METADATA_PACK.md",
            "source_data": "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/materials/datacite_metadata_draft.json; outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tables/fair_archive_checklist.csv; outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tables/fair_archive_release_role_summary.csv",
            "recommended_use": "用于 Zenodo/OSF/Figshare/机构仓储上传前填写 DataCite-style 元数据、关键词、资源类型、license/creator/DOI 占位符和 FAIR checklist。",
            "claim_supported": "正式归档内容、source data、模型、图件、GIF、checksum、复现材料和复用边界已经整理为数据仓库可读的元数据草案。",
            "boundary": "该包不创建 DOI/accession，也不替代作者确认 license、ORCID、仓库 URL 和归档平台字段。",
            "status": "ready",
        },
        {
            "placement": "Third-party Reproduction",
            "title_cn": "第三方复现实操与容器草案",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md",
            "source_data": "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/Dockerfile.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/apptainer.def.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/tables/third_party_reproduction_tiers.csv; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/tables/third_party_reproduction_troubleshooting.csv; outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md",
            "recommended_use": "用于审稿人或第三方在不同机器上复现时理解 T0 smoke、T1 reporting-layer rebuild、T2 full matrix rerun、T3 GIF rebuild 的差异，并处理 CUDA/Box2D/Gym 常见问题。",
            "claim_supported": "当前证据链不仅给出 source data 和 checksums，也提供跨环境复现实操路线、容器草案、失败诊断和本机容器运行时预检。",
            "boundary": "Dockerfile/Apptainer 文件只是草案；本机预检记录当前服务器未安装 Docker/Apptainer，因此不能写成已发布、已构建或已认证容器。",
            "status": "ready",
        },
        {
            "placement": "Main Table 1",
            "title_cn": "主要 benchmark 汇总表",
            "primary_artifact": "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_main_results.md",
            "source_data": "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
            "recommended_use": "主文报告所有算法在冻结 30 cases × 8 algorithms 上的核心指标均值和区间。",
            "claim_supported": "当前算法与 DLC world model 变种、规则专家的整体对比。",
            "boundary": "不要把 partial summary 或 smoke summary 合并进该表。",
            "status": "ready",
        },
        {
            "placement": "Supplement Table S1-S6",
            "title_cn": "协议、统计、风险、复现与发布表",
            "primary_artifact": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv",
            "source_data": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/*.csv; outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/*.csv; outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/*.csv",
            "recommended_use": "补充材料中集中放置 benchmark cards、algorithm cards、metric dictionary、Holm 表、effect sizes、claim guardrails。",
            "claim_supported": "实验协议透明、统计报告完整、claim 边界清晰。",
            "boundary": "协议表是复现定义，不是额外性能结果。",
            "status": "ready",
        },
    ]


def supplement_index():
    return [
        {
            "supplement_id": "Supplementary Note 1",
            "title_cn": "算法与实现细节",
            "entry_file": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/METHODS_DRAFT.md",
            "include_files": "configs/tits_dynamic_graph_experiments.json; dlc/graph_world_model.py; dlc/graph_policy.py; dlc/policies.py",
            "purpose": "支撑方法部分：dynamic-neighborhood graph、world model rollout、proposal scoring 和安全执行。",
            "reviewer_route": "先读 Methods draft，再核对配置与代码入口。",
        },
        {
            "supplement_id": "Supplementary Note 2",
            "title_cn": "Benchmark 与指标定义",
            "entry_file": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_CARD.md",
            "include_files": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/benchmark_cards.csv; outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv; outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/metric_dictionary.csv",
            "purpose": "定义 30 个 case、8 个算法、42 个 source-data 字段和公平对比边界。",
            "reviewer_route": "审查 benchmark cards 和 metric dictionary 是否与 evaluator 一致。",
        },
        {
            "supplement_id": "Supplementary Note 2b",
            "title_cn": "对比算法公平性审计",
            "entry_file": "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md",
            "include_files": "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tables/fairness_command_checks.csv; outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tables/fairness_summary_run_checks.csv; outputs/tits_dynamic_graph/v6_confirmatory_preflight/tables/v6_confirmatory_case_commands.csv",
            "purpose": "证明同一 case 下 8 个算法共享 seed、车辆数、赛道、traffic、终止条件、观测类型和邻居预算，且目标车最后身位起步。",
            "reviewer_route": "先读 fairness audit，再核对 frozen case commands 和 summary-run checks。",
        },
        {
            "supplement_id": "Supplementary Note 3",
            "title_cn": "统计分析与主假设",
            "entry_file": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_PLAN.md",
            "include_files": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv; outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_effect_sizes.csv",
            "purpose": "说明 paired tests、Holm 校正、效应量和探索性比较。",
            "reviewer_route": "优先检查 primary Holm 表和 effect-size 表。",
        },
        {
            "supplement_id": "Supplementary Note 3b",
            "title_cn": "实验设计、功效与稳定性",
            "entry_file": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md",
            "include_files": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/experimental_design_coverage.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/primary_metric_stability.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/leave_one_case_influence.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/case_influence_summary.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/figures/figure_experimental_design_power_audit_cn.pdf; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/figures/figure_case_influence_audit_cn.pdf",
            "purpose": "说明确认性矩阵的 matched-case 设计、场景覆盖、主指标配对稳定性、场景异质性和逐 case 影响度。",
            "reviewer_route": "先读 design/power audit，再核对 source CSV、primary metric stability 和 leave-one-case influence 表。",
        },
        {
            "supplement_id": "Supplementary Note 4",
            "title_cn": "失败模式与有效性威胁",
            "entry_file": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/materials/FAILURE_ATLAS.md",
            "include_files": "outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_TO_VALIDITY_DOSSIER.md; outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/claim_language_guardrails.csv",
            "purpose": "记录槽底率、草地暴露、外部有效性、构念有效性和仿真到真实边界。",
            "reviewer_route": "用 failure atlas 定位失败，再用 guardrails 限制论文 claim。",
        },
        {
            "supplement_id": "Supplementary Note 5",
            "title_cn": "运行时扩展性与复杂度",
            "entry_file": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md",
            "include_files": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_scalability_by_vehicle_count.csv; outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tables/runtime_complexity_crosswalk.csv; outputs/tits_dynamic_graph/tits_runtime_scalability_pack/figures/figure_runtime_scalability_cn.pdf",
            "purpose": "报告 4/5/6/8 车下的延迟、超车质量、草地风险和 max-neighbor 复杂度边界。",
            "reviewer_route": "先读 runtime report，再核对 source CSV、config 中 max_neighbors 和邻域打包代码。",
        },
        {
            "supplement_id": "Supplementary Note 6",
            "title_cn": "图件 source data 与格式质控",
            "entry_file": "outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "include_files": "outputs/tits_dynamic_graph/tits_figure_source_data_audit/tables/figure_source_data_checks.csv; outputs/tits_dynamic_graph/tits_figure_source_data_audit/tables/figure_source_table_checks.csv",
            "purpose": "证明正式主图/补充图具备 PDF/SVG/PNG/TIFF、多张 source table、图例和 QA/报告文件。",
            "reviewer_route": "先读 figure source-data audit，再按表中路径打开各图和 source CSV。",
        },
        {
            "supplement_id": "Supplementary Note 7",
            "title_cn": "复现胶囊与结果指纹",
            "entry_file": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md",
            "include_files": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/tables/reproducibility_artifact_fingerprints.csv; outputs/tits_dynamic_graph/tits_reproducibility_capsule/tables/reproducibility_result_metric_fingerprints.csv; outputs/tits_dynamic_graph/tits_reproducibility_capsule/run_reproducibility_capsule_check.sh",
            "purpose": "把冻结命令、source data digest、关键 artifact SHA256、gate 状态和算法级结果指纹集中成一个复现入口。",
            "reviewer_route": "先读 reproducibility capsule，再运行 run_reproducibility_capsule_check.sh 检查当前工作区是否与 capsule 一致。",
        },
        {
            "supplement_id": "Supplementary Note 7a",
            "title_cn": "确定性 smoke 复现预检",
            "entry_file": "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/materials/DETERMINISM_SMOKE_AUDIT.md",
            "include_files": "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tables/determinism_smoke_comparison.csv; outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tables/determinism_smoke_field_details.csv",
            "purpose": "提供短程同 seed 评估复现检查，作为 reviewer smoke route 的补充。",
            "reviewer_route": "先读 determinism smoke audit，再查看 comparison CSV；不要把 smoke performance 当成正式结果。",
        },
        {
            "supplement_id": "Supplementary Note 7b",
            "title_cn": "数据泄漏与调参来源审计",
            "entry_file": "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/materials/DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md",
            "include_files": "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/case_split_boundary.csv; outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/algorithm_training_boundary.csv; outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/exploratory_output_boundary.csv",
            "purpose": "说明训练、调参探索、正式确认性矩阵和外推/外部验证之间的证据边界。",
            "reviewer_route": "先读 data leakage/tuning audit，再核对 benchmark cards、public release plan 和 cross-reference audit。",
        },
        {
            "supplement_id": "Supplementary Note 7c",
            "title_cn": "创新点-证据追溯矩阵",
            "entry_file": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md",
            "include_files": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_to_code_map.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_to_experiment_map.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_claim_boundaries.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/method_section_writing_matrix.csv",
            "purpose": "把动态图邻域、DLC world-model 主体、超车感知规划、安全/质量评分、quality proposal 和复现证据链映射到代码、实验与写作边界。",
            "reviewer_route": "先读 traceability report，再核对 code map、experiment map 和 method writing matrix。",
        },
        {
            "supplement_id": "Supplementary Note 7d",
            "title_cn": "指标阈值敏感性审计",
            "entry_file": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md",
            "include_files": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/quality_threshold_sensitivity_grid.csv; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/paired_threshold_sensitivity_vs_dlc.csv; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/robustness_summary_by_algorithm.csv; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/figures/figure_metric_sensitivity_cn.pdf",
            "purpose": "检查desirable behavior/质量超车结论对后验草地率、横向偏移和完成耗时阈值的敏感性，支撑 Discussion 中的稳健性和边界表述。",
            "reviewer_route": "先读 metric sensitivity audit，再查看 paired threshold table 和 robustness summary。",
        },
        {
            "supplement_id": "Supplementary Note 8",
            "title_cn": "写作 claim 语言边界审计",
            "entry_file": "outputs/tits_dynamic_graph/tits_claim_language_audit/materials/CLAIM_LANGUAGE_AUDIT.md",
            "include_files": "outputs/tits_dynamic_graph/tits_claim_language_audit/tables/claim_language_scan_rows.csv; outputs/tits_dynamic_graph/tits_claim_language_audit/tables/claim_guardrail_trace.csv; outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/claim_language_guardrails.csv",
            "purpose": "检查正式写作材料是否把仿真 benchmark claim 写成真实道路、任意泛化或安全认证 claim。",
            "reviewer_route": "先读 claim-language audit，再核对 threats-to-validity guardrails 和 manuscript/reviewer-facing text。",
        },
        {
            "supplement_id": "Supplementary Data 1",
            "title_cn": "在线 benchmark source data",
            "entry_file": "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
            "include_files": "outputs/tits_dynamic_graph/v6_confirmatory_matrix/**/*.summary.json; outputs/tits_dynamic_graph/v6_confirmatory_matrix_run_results_ledger.csv",
            "purpose": "作为全部主结果图表的主数据源。",
            "reviewer_route": "从 source CSV 回溯每个 run 的 summary JSON。",
        },
        {
            "supplement_id": "Supplementary Videos 1-4",
            "title_cn": "代表性在线运行 GIF",
            "entry_file": "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md",
            "include_files": "outputs/tits_dynamic_graph/publication_gifs/**/*.gif",
            "purpose": "提供俯视图与第一视角视觉证据。",
            "reviewer_route": "按 manifest 打开 n8 与 Monza n6 的 v6-safe / DLC 对比 GIF。",
        },
        {
            "supplement_id": "Reviewer Package",
            "title_cn": "审稿复现路线",
            "entry_file": "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md",
            "include_files": "outputs/tits_dynamic_graph/reviewer_replication_packet/run_reviewer_smoke.sh; outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv",
            "purpose": "给审稿人提供最短 smoke test、完整矩阵复现路线、checksum 和数据/代码可用性草稿。",
            "reviewer_route": "先运行 smoke test，再按 frozen case commands 选择是否复现实验矩阵。",
        },
        {
            "supplement_id": "Submission Metadata",
            "title_cn": "T-ITS投稿元数据、cover letter与声明草稿",
            "entry_file": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/IEEE_TITS_SUBMISSION_METADATA_PACK.md",
            "include_files": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/TITLE_ABSTRACT_KEYWORDS_DRAFT.md; outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/COVER_LETTER_DRAFT.md; outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/AUTHOR_DECLARATIONS_AND_AI_DISCLOSURE_DRAFT.md",
            "purpose": "把当前证据链转换为可编辑投稿元数据和声明草稿。",
            "reviewer_route": "作者侧使用；不作为实验结果证据。",
        },
        {
            "supplement_id": "Open-source Release",
            "title_cn": "GitHub开源最小复现与release清单",
            "entry_file": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md",
            "include_files": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_README_DRAFT.md; outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/CITATION_cff_DRAFT.md; outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tables/github_repository_inventory.csv",
            "purpose": "把正式证据链整理为 GitHub 开源仓库 README、citation、贡献指南、model/data card 和 release 行动清单。",
            "reviewer_route": "作者侧用于公开发布；审稿人可用来判断复现材料是否可被打包和归档。",
        },
        {
            "supplement_id": "FAIR Archive Metadata",
            "title_cn": "FAIR 数据归档元数据草案",
            "entry_file": "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/materials/FAIR_ARCHIVE_METADATA_PACK.md",
            "include_files": "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/materials/datacite_metadata_draft.json; outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tables/fair_archive_checklist.csv; outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tables/fair_archive_citation_placeholders.csv",
            "purpose": "为数据仓库上传提供 DataCite-style 元数据、FAIR checklist、归档内容摘要和引用占位符。",
            "reviewer_route": "作者侧用于 DOI/accession 归档；审稿人可用来理解 archive scope 和复用边界。",
        },
        {
            "supplement_id": "Third-party Reproduction",
            "title_cn": "第三方复现实操与容器草案",
            "entry_file": "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md",
            "include_files": "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/Dockerfile.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/apptainer.def.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/tables/third_party_reproduction_checkpoints.csv; outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md",
            "purpose": "提供第三方复现实操路线、容器草案、校验点、故障排查表和本机容器构建条件预检。",
            "reviewer_route": "审稿人可先运行 T0 smoke，再按 T1/T2/T3 选择是否重建报告层、完整矩阵或视觉证据。",
        },
    ]


def source_crosswalk():
    return [
        {
            "claim_id": "C1",
            "claim_cn": "运行时动态邻域图支持不同车辆数在线构图，不需要针对 8 车重新训练。",
            "primary_source": "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
            "secondary_source": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md; outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/tables/confirmatory_claim_evidence_matrix.csv",
            "recommended_location": "Methods + Results",
            "boundary": "覆盖 4/5/6 车训练分布与 8 车外推；不声称任意密度无限泛化。",
        },
        {
            "claim_id": "C2",
            "claim_cn": "优化后的 DLC world model 在 Monza 外部赛道上优于原始 DLC world model。",
            "primary_source": "outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
            "secondary_source": "outputs/tits_dynamic_graph/publication_gifs/monza_n6_seed53_v6safe_vs_dlc/",
            "recommended_location": "Results + Supplementary Videos",
            "boundary": "Monza 是单一外部 CSV 赛道，仍需更多真实赛道或闭源仿真器验证。",
        },
        {
            "claim_id": "C3",
            "claim_cn": "当前方法提升的不只是速度，还包括on-track/desirable超车质量。",
            "primary_source": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tables/statistical_primary_holm.csv",
            "secondary_source": "outputs/tits_dynamic_graph/manuscript_english_figures/tables/figure_dynamic_dlc_overtaking_source_data.csv",
            "recommended_location": "Results",
            "boundary": "小车队 n4 程序赛道仍有desirable overtaking behavior quality不足，不能写成所有场景均优。",
        },
        {
            "claim_id": "C4",
            "claim_cn": "规则专家是强基线但不是本文 world-model 算法替代品。",
            "primary_source": "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tables/ablation_contribution_overall.csv",
            "secondary_source": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tables/algorithm_cards.csv",
            "recommended_location": "Ablation/Analysis",
            "boundary": "规则专家延迟低、部分场景Desirable overtaking behavior rate高，但缺乏 learned world model 泛化机制。",
        },
        {
            "claim_id": "C5",
            "claim_cn": "当前系统具备可复现的顶刊实验材料基础。",
            "primary_source": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md",
            "secondary_source": "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv; outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md; outputs/tits_dynamic_graph/final_readiness_dashboard/FINAL_READINESS_DASHBOARD.md; outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md; outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "recommended_location": "Data/Code Availability + Supplement",
            "boundary": "DOI、license、匿名化、最终 IEEE 模板仍需作者确认。",
        },
        {
            "claim_id": "C6",
            "claim_cn": "主结果来自完整 matched-case 设计，但需要披露场景异质性。",
            "primary_source": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/primary_metric_stability.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/scenario_level_stability.csv; outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tables/case_influence_summary.csv",
            "recommended_location": "Experiments + Results + Discussion",
            "boundary": "不要写成所有场景和所有 seed 均匀提升；应报告 n=4 程序赛道等弱场景和相对影响度最高的 case。",
        },
        {
            "claim_id": "C6b",
            "claim_cn": "正式写作材料没有未加限定的部署级安全、任意泛化或保证式 claim。",
            "primary_source": "outputs/tits_dynamic_graph/tits_claim_language_audit/materials/CLAIM_LANGUAGE_AUDIT.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_claim_language_audit/tables/claim_language_scan_rows.csv; outputs/tits_dynamic_graph/tits_threats_validity_pack/tables/claim_language_guardrails.csv",
            "recommended_location": "Discussion + Limitations + Data/Code Availability",
            "boundary": "这是写作层面的风险筛查，不替代实验外推验证或真实道路安全证明。",
        },
        {
            "claim_id": "C6c",
            "claim_cn": "正式结果与训练/调参探索输出已分流，正式 source data 来自冻结确认性矩阵。",
            "primary_source": "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/materials/DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/case_split_boundary.csv; outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tables/exploratory_output_boundary.csv; outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv",
            "recommended_location": "Experiments + Reproducibility + Limitations",
            "boundary": "历史训练日志未归档逐 episode procedural seeds，因此不要声称 seed-level 训练/验证完全可证明不重叠。",
        },
        {
            "claim_id": "C6d",
            "claim_cn": "同 seed 短程在线评估 smoke run 在当前环境下可重复生成一致关键 summary 指纹。",
            "primary_source": "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/materials/DETERMINISM_SMOKE_AUDIT.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tables/determinism_smoke_comparison.csv",
            "recommended_location": "Reproducibility supplement",
            "boundary": "这是短程 smoke 复现检查，不是 paper-scale 性能结果，也不替代 240-run confirmatory matrix。",
        },
        {
            "claim_id": "C6e",
            "claim_cn": "当前算法的创新点可逐项追溯到实现代码、配置、正式实验和写作边界。",
            "primary_source": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_to_code_map.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_to_experiment_map.csv; outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tables/innovation_claim_boundaries.csv",
            "recommended_location": "Methods + Contributions + Ablation + Supplement",
            "boundary": "这是写作和审稿追溯材料，不是新增性能结果；算法 claim 仍需引用确认性矩阵和统计分析。",
        },
        {
            "claim_id": "C6f",
            "claim_cn": "desirable behavior/质量超车结论对阈值选择具有一定稳健性，但不应写成任意质量定义下均最优。",
            "primary_source": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/paired_threshold_sensitivity_vs_dlc.csv; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tables/robustness_summary_by_algorithm.csv; outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/figures/figure_metric_sensitivity_cn.pdf",
            "recommended_location": "Supplementary Results + Discussion",
            "boundary": "该分析是后验稳健性审计，不能替代预定义主指标、确认性矩阵或事件级轨迹重算。",
        },
        {
            "claim_id": "C7",
            "claim_cn": "投稿元数据和声明草稿已与当前证据链对齐，但仍需作者最终确认。",
            "primary_source": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/IEEE_TITS_SUBMISSION_METADATA_PACK.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/tables/submission_portal_checklist.csv; outputs/tits_dynamic_graph/ieee_tits_compliance/IEEE_TITS_COMPLIANCE_MATRIX.md",
            "recommended_location": "Submission portal + cover letter + declarations",
            "boundary": "不能替代 ScholarOne 填报、作者身份、ORCID、基金、利益冲突、AI工具细节、DOI/URL 和最终PDF检查。",
        },
        {
            "claim_id": "C8",
            "claim_cn": "开源仓库最小复现材料已经形成草稿，并与 artifact manifest 和 public release plan 对齐。",
            "primary_source": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tables/github_repository_inventory.csv; outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tables/github_release_author_actions.csv",
            "recommended_location": "Code/Data Availability + release checklist",
            "boundary": "该 claim 只说明本地开源准备材料齐备；不替代 DOI、GitHub URL、license、作者信息和 release tag。",
        },
        {
            "claim_id": "C9",
            "claim_cn": "作者侧投稿闭环已形成可执行清单，但 DOI、license、ScholarOne、作者声明和最终模板仍需作者真实完成。",
            "primary_source": "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/materials/AUTHOR_SUBMISSION_CLOSURE_PACK.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_owned_action_matrix.csv; outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/author_placeholder_inventory.csv; outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tables/post_author_action_regeneration_commands.csv",
            "recommended_location": "Author handoff + submission checklist",
            "boundary": "不能把该闭环表写成本地已经完成真实投稿、真实归档或法律/license 确认。",
        },
        {
            "claim_id": "C10",
            "claim_cn": "数据归档 FAIR/元数据草案已准备好，但真实 DOI、license、作者/ORCID 和 repository URL 仍需作者侧填入。",
            "primary_source": "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/materials/FAIR_ARCHIVE_METADATA_PACK.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/materials/datacite_metadata_draft.json; outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tables/fair_archive_checklist.csv; outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tables/fair_archive_citation_placeholders.csv",
            "recommended_location": "Data/Code Availability + archive upload",
            "boundary": "不能把元数据草案写成 DOI 已生成、license 已法律确认或数据已上传。",
        },
        {
            "claim_id": "C11",
            "claim_cn": "第三方复现实操路线、容器草案和本机容器运行时预检已准备好，但容器镜像尚未实际构建或认证。",
            "primary_source": "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md",
            "secondary_source": "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/Dockerfile.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/apptainer.def.draft; outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/tables/third_party_reproduction_tiers.csv; outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md",
            "recommended_location": "Reproducibility + Data/Code Availability",
            "boundary": "不能把容器草案或本机预检写成已发布、已测试、带 digest 的正式镜像。",
        },
    ]


def files_to_check(plan_rows, supplement_rows, crosswalk_rows):
    files = set()
    for row in plan_rows + supplement_rows:
        for key in ("primary_artifact", "entry_file"):
            if row.get(key) and "*" not in row[key]:
                files.add(row[key])
    for row in crosswalk_rows:
        for key in ("primary_source",):
            if row.get(key) and "*" not in row[key]:
                files.add(row[key])
    files.update(
        [
            "outputs/tits_dynamic_graph/tits_manuscript_package/tits_manuscript_package_manifest.json",
            "outputs/tits_dynamic_graph/manuscript_english_figures/manuscript_english_figures_manifest.json",
            "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tits_ablation_contribution_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tits_statistical_analysis_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tits_benchmark_protocol_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/confirmatory_evidence_pack_manifest.json",
            "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json",
            "outputs/tits_dynamic_graph/tits_figure_source_data_audit/tits_figure_source_data_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tits_experimental_design_power_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tits_determinism_smoke_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_reproducibility_capsule/tits_reproducibility_capsule_manifest.json",
            "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tits_data_leakage_tuning_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tits_innovation_evidence_traceability_manifest.json",
            "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tits_metric_sensitivity_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_claim_language_audit/tits_claim_language_audit_manifest.json",
            "outputs/tits_dynamic_graph/tits_submission_metadata_pack/tits_submission_metadata_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tits_github_release_readiness_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tits_author_submission_closure_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tits_fair_archive_metadata_pack_manifest.json",
            "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/tits_third_party_reproduction_pack_manifest.json",
        ]
    )
    return sorted(files)


def build_navigator_md(manifest, plan_rows, supplement_rows, crosswalk_rows):
    lines = [
        "# T-ITS Manuscript and Supplement Navigator",
        "",
        "该导航文件把当前优化后的 DLC world model 证据链整理成投稿写作时可直接使用的主文/补充材料路线。它不新增实验结果，只规定哪些文件应作为正式证据、哪些文件只保留为调试或历史来源。",
        "",
        "## Summary",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Planned main/supplement figure-table entries: {manifest['summary']['figure_table_entries']}",
        f"- Supplement entries: {manifest['summary']['supplement_entries']}",
        f"- Source-data claim crosswalk rows: {manifest['summary']['source_crosswalk_rows']}",
        f"- Checked evidence files: {manifest['summary']['checked_files']}",
        f"- Missing evidence files: {manifest['summary']['missing_files']}",
        f"- Confirmatory source-data rows: {manifest['summary']['confirmatory_source_rows']}",
        "",
        "## Recommended Main Manuscript Structure",
        "",
        "1. Methods: 使用 Main Fig. 1 解释优化后的 DLC world model。重点写 runtime dynamic-neighborhood graph、interaction-priority neighbor selection、graph world model rollout、overtake-aware candidate planning、risk/uncertainty/lane/grass quality scoring 与 safety execution。",
        "2. Experiments: 使用 benchmark protocol pack 定义 30 cases × 8 algorithms、程序赛道、8 车外推、Monza CSV 外部赛道、固定最大步数和 `finish-mode any`。",
            "3. Results: 使用 Main Table 1 和 Main Fig. 2 报告在线成功率、desirable/on-track超车、开始到完成超车时间、草地暴露和延迟；使用 experimental-design audit 约束场景异质性表述。",
        "4. Ablation/Analysis: 使用 Fig. 3 或 Supplement Fig. S1 解释 DLC world model 变种、quality proposal、动态邻域与安全规划的贡献边界。",
        "5. Discussion: 使用 threats-to-validity pack 明确仿真、oracle/telemetry、单一 Monza 外部赛道、真实部署和无限车辆数泛化限制。",
        "",
        "## Main and Supplement Placement",
        "",
        "| Placement | Title | Primary artifact | Recommended use | Boundary |",
        "|---|---|---|---|---|",
    ]
    for row in plan_rows:
        lines.append(
            f"| {row['placement']} | {row['title_cn']} | `{row['primary_artifact']}` | {row['recommended_use']} | {row['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Source-Data Claim Crosswalk",
            "",
            "| Claim | Primary source | Recommended location | Boundary |",
            "|---|---|---|---|",
        ]
    )
    for row in crosswalk_rows:
        lines.append(
            f"| {row['claim_cn']} | `{row['primary_source']}` | {row['recommended_location']} | {row['boundary']} |"
        )
    lines.extend(
        [
            "",
            "## Do Not Cite as Formal Evidence",
            "",
            "- `outputs/tits_dynamic_graph/smoke*`：只用于环境和代码路径检查。",
            "- `outputs/tits_dynamic_graph/optimization_checks/`：只用于调参和安全规划诊断。",
            "- `outputs/tits_dynamic_graph/quality_aux*`、`quality_guided*`、`quality_proposal*_matrix_summary`：历史质量模型探索，除非在 provenance 中单独说明。",
            "- `outputs/tits_dynamic_graph/v6_confirmatory_matrix_partial_summary/`：中间结果，正式结果使用 `v6_confirmatory_matrix_full_summary/`。",
            "- `outputs/tits_dynamic_graph/online_evaluation_matrix*`：早期在线矩阵，正式论文优先引用 frozen confirmatory matrix。",
            "",
            "## Figure Source-Data QC",
            "",
            "- 图件 source data 与格式审计：`outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md`。",
            "- 它检查正式图是否具备 PDF/SVG/PNG/TIFF、多张 source CSV、图例和 QA/报告文件；最终排版仍需按 IEEE T-ITS 模板人工复核。",
            "",
            "## Submission Metadata",
            "",
            "- 投稿元数据与声明草稿：`outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/IEEE_TITS_SUBMISSION_METADATA_PACK.md`。",
            "- 该包只提供作者侧草稿；最终作者信息、ORCID、基金、利益冲突、AI工具细节、DOI/URL 和 ScholarOne 字段仍需人工确认。",
            "",
            "## Regeneration Command",
            "",
            "```bash",
            "/home/itrc/.conda/envs/vlm_planner/bin/python scripts/export_tits_manuscript_supplement_navigator.py --out-dir outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator",
            "```",
        ]
    )
    return "\n".join(lines)


def build_supplement_md(manifest, supplement_rows):
    lines = [
        "# Supplementary Materials Index",
        "",
        "该索引用于把补充材料组织成审稿人可检查的模块，而不是把全部输出目录无差别上传。",
        "",
        "| Supplement ID | Title | Entry file | Purpose | Reviewer route |",
        "|---|---|---|---|---|",
    ]
    for row in supplement_rows:
        lines.append(
            f"| {row['supplement_id']} | {row['title_cn']} | `{row['entry_file']}` | {row['purpose']} | {row['reviewer_route']} |"
        )
    lines.extend(
        [
            "",
            "## Upload Priority",
            "",
            "1. 必须上传：source data、确认性矩阵 summary、主图 source data、图件 source-data audit、实验设计稳定性审计、统计表、benchmark/metric cards、artifact manifest；投稿前使用 submission metadata pack 完成 portal 元数据和声明。",
            "2. 强烈建议上传：publication GIF、failure atlas、threats-to-validity、reviewer replication packet。",
            "3. 可选归档：完整 traces、旧 online matrix、代表性历史 GIF。",
            "4. 不建议作为正式补充材料：smoke、optimization checks、历史 sweep 和 partial summary。",
        ]
    )
    return "\n".join(lines)


def build_placement_md(plan_rows):
    lines = [
        "# Figure and Table Placement Plan",
        "",
        "## Placement Table",
        "",
        "| Placement | Artifact | Source data | Claim supported | Status |",
        "|---|---|---|---|---|",
    ]
    for row in plan_rows:
        lines.append(
            f"| {row['placement']} | `{row['primary_artifact']}` | `{row['source_data']}` | {row['claim_supported']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Caption Guidance",
            "",
            "- 主图 caption 应明确“online simulation benchmark”和“optimized DLC world model with runtime dynamic neighborhoods”。",
            "- 所有性能数值都从 `online_benchmark_source_data.csv` 或对应 figure source data 引用。",
            "- 动图 caption 应写成 representative visual evidence，不能替代统计结果。",
            "- 消融 caption 应说明该图是 contribution attribution over the frozen matrix，不是新增训练矩阵。",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export manuscript/supplement navigator for the T-ITS dynamic DLC package.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    materials_dir = out_dir / "materials"
    tables_dir = out_dir / "tables"
    materials_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    plan_rows = figure_table_plan()
    supplement_rows = supplement_index()
    crosswalk_rows = source_crosswalk()
    checked = files_to_check(plan_rows, supplement_rows, crosswalk_rows)
    missing = [path for path in checked if not exists_nonempty(path)]

    manifests = {
        "manuscript_package": load_json("outputs/tits_dynamic_graph/tits_manuscript_package/tits_manuscript_package_manifest.json").get("status"),
        "english_figures": load_json("outputs/tits_dynamic_graph/manuscript_english_figures/manuscript_english_figures_manifest.json").get("status"),
        "ablation": load_json("outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tits_ablation_contribution_pack_manifest.json").get("status"),
        "statistics": load_json("outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tits_statistical_analysis_pack_manifest.json").get("status"),
        "benchmark_protocol": load_json("outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tits_benchmark_protocol_pack_manifest.json").get("status"),
        "evidence_pack": load_json("outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/confirmatory_evidence_pack_manifest.json").get("status"),
        "publication_gifs": load_json("outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json").get("status"),
        "determinism_smoke": load_json("outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tits_determinism_smoke_audit_manifest.json").get("status"),
        "reproducibility_capsule": load_json("outputs/tits_dynamic_graph/tits_reproducibility_capsule/tits_reproducibility_capsule_manifest.json").get("status"),
        "data_leakage_tuning": load_json("outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tits_data_leakage_tuning_audit_manifest.json").get("status"),
        "innovation_traceability": load_json("outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tits_innovation_evidence_traceability_manifest.json").get("status"),
        "metric_sensitivity": load_json("outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tits_metric_sensitivity_audit_manifest.json").get("status"),
        "claim_language": load_json("outputs/tits_dynamic_graph/tits_claim_language_audit/tits_claim_language_audit_manifest.json").get("status"),
        "github_release": load_json("outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tits_github_release_readiness_pack_manifest.json").get("status"),
    }
    source_rows = count_csv_rows("outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/tables/online_benchmark_source_data.csv")
    status = "pass" if not missing and all(value in {"complete", "pass"} for value in manifests.values()) and source_rows == 240 else "review_required"
    manifest = {
        "status": status,
        "out_dir": str(out_dir),
        "summary": {
            "figure_table_entries": len(plan_rows),
            "supplement_entries": len(supplement_rows),
            "source_crosswalk_rows": len(crosswalk_rows),
            "checked_files": len(checked),
            "missing_files": len(missing),
            "confirmatory_source_rows": source_rows,
        },
        "upstream_status": manifests,
        "missing_files": missing,
        "paths": {},
        "note": "Navigator is a manuscript/supplement routing layer; it does not create new empirical results.",
    }

    manifest["paths"] = {
        "navigator_md": write_text(materials_dir / "MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md", build_navigator_md(manifest, plan_rows, supplement_rows, crosswalk_rows)),
        "supplement_index_md": write_text(materials_dir / "SUPPLEMENTARY_MATERIALS_INDEX.md", build_supplement_md(manifest, supplement_rows)),
        "placement_plan_md": write_text(materials_dir / "FIGURE_TABLE_PLACEMENT_PLAN.md", build_placement_md(plan_rows)),
        "figure_table_plan_csv": write_csv(
            tables_dir / "manuscript_figure_table_plan.csv",
            plan_rows,
            ["placement", "title_cn", "primary_artifact", "source_data", "recommended_use", "claim_supported", "boundary", "status"],
        ),
        "supplement_index_csv": write_csv(
            tables_dir / "supplementary_materials_index.csv",
            supplement_rows,
            ["supplement_id", "title_cn", "entry_file", "include_files", "purpose", "reviewer_route"],
        ),
        "source_crosswalk_csv": write_csv(
            tables_dir / "source_data_crosswalk.csv",
            crosswalk_rows,
            ["claim_id", "claim_cn", "primary_source", "secondary_source", "recommended_location", "boundary"],
        ),
    }
    manifest["paths"]["qa_json"] = write_json(materials_dir / "NAVIGATOR_QA.json", manifest)
    manifest_path = write_json(out_dir / "tits_manuscript_supplement_navigator_manifest.json", manifest)
    print(json.dumps({"manifest": manifest_path, "status": status, "missing_files": len(missing)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
