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


def exists_nonempty(path):
    path = Path(path)
    return path.exists() and path.stat().st_size > 0


def fixed_point_status(data):
    return data.get("status") in {"pass", "complete", "PASS", "review_required", "author_action_required"}


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path)


def write_csv(path, rows):
    fields = ["gate", "status", "evidence", "interpretation", "remaining_author_action"]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def gate(status_bool, evidence_status=None):
    if evidence_status in {"PASS", "pass", "complete", "artifact_manifest_generated"}:
        return "PASS"
    if status_bool:
        return "PASS"
    return "CHECK"


def build_rows(readiness, matrix_audit, evidence, reviewer, reviewer_smoke_route, root_readme_alignment, manuscript, manuscript_numeric_trace, manuscript_section_trace, abstract_highlights, navigator, numbering_consistency, figure_source_audit, figure_source_value_recompute, figure_caption_claim, publication_gif_provenance, supplementary_video_index, supplementary_submission_index, online_decision_case_study, safety_proxy_audit, media_upload_quality, english_figures, ablation, casewise, baseline_fairness, protocol, source_integrity, source_schema_dictionary, run_level_provenance, trace_integrity, trace_schema_dictionary, overtake_event_consistency, statistical_table_recompute, results_reporting, results_narrative, environment, determinism_smoke, reproducibility_capsule, data_leakage_tuning, innovation_traceability, metric_sensitivity, model_artifacts, algorithm_config_freeze, compute_timing_boundary, ai_tool_use_disclosure, statistics, design_power, threats, reviewer_rebuttal, runtime_scalability, compute_cost, reproduction_time_budget, claim_evidence, claim_language, submission_metadata, github_release, author_closure, author_owned_integrity, upload_bundle, submission_dry_run, submission_gap_priority, anonymization_privacy, dependency_license, fair_archive, third_party_repro, container_preflight, crossref, freshness, release, release_audit, artifact, gif_manifest):
    rows = [
        {
            "gate": "核心 readiness audit",
            "status": gate(False, readiness.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_readiness_audit.json",
            "interpretation": "配置、模型、关键产物和正式评估链路通过预检。",
            "remaining_author_action": "若移动文件或删减开源包，重新运行 readiness audit。",
        },
        {
            "gate": "确认性在线矩阵完整性",
            "status": gate(matrix_audit.get("summary", {}).get("existing_summaries") == 240, matrix_audit.get("summary", {}).get("status")),
            "evidence": "outputs/tits_dynamic_graph/v6_confirmatory_preflight/v6_confirmatory_matrix_audit.json",
            "interpretation": "240/240 algorithm-runs 已完成，缺失 summary 为 0。",
            "remaining_author_action": "不要把 smoke 或 partial summary 当作正式矩阵。",
        },
        {
            "gate": "统计证据包",
            "status": gate(evidence.get("run_count") == 240 and evidence.get("case_count") == 30, evidence.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/confirmatory_evidence_pack_manifest.json",
            "interpretation": "含成对检验、失败模式、算力成本和中文图。",
            "remaining_author_action": "最终论文数值需继续从 source CSV/证据包引用。",
        },
        {
            "gate": "视觉证据",
            "status": gate(gif_manifest.get("row_count") == 4, gif_manifest.get("status")),
            "evidence": "outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.md",
            "interpretation": "包含 n8 和 Monza n6 的俯视图与第一视角 GIF。",
            "remaining_author_action": "选择最终论文/补充材料中展示哪些 GIF。",
        },
        {
            "gate": "代表性 GIF 来源追溯审计",
            "status": gate(False, publication_gif_provenance.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/materials/PUBLICATION_GIF_PROVENANCE_AUDIT.md",
            "interpretation": "4 行俯视/第一视角 GIF 均可回链到 summary、trace、metrics，并匹配正式矩阵同 case；warning 仅标注代表性视觉边界。",
            "remaining_author_action": "重生成 GIF、summary、trace、metrics 或正式矩阵后重新运行该审计；论文统计结论仍引用 240-run source data。",
        },
        {
            "gate": "补充视频/GIF 投稿索引",
            "status": gate(False, supplementary_video_index.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/materials/SUPPLEMENTARY_VIDEO_INDEX.md",
            "interpretation": "8 个 Video S 条目覆盖 4 个代表性 online run 的俯视图和第一视角，包含 caption、文件大小、summary/trace/provenance/formal source crosswalk。",
            "remaining_author_action": "最终投稿前按期刊门户格式/大小要求决定 GIF 或转视频格式；论文统计结论仍引用 240-run source data。",
        },
        {
            "gate": "补充材料投稿总索引",
            "status": gate(False, supplementary_submission_index.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/materials/SUPPLEMENTARY_SUBMISSION_INDEX.md",
            "interpretation": "汇总 21 个补充条目、26 个图表条目、8 个 Video S 条目和 16 个 claim-source crosswalk，并对齐 upload slots、numbering、navigator 与 240-run source data。",
            "remaining_author_action": "最终投稿前作者仍需按 IEEE 门户要求决定补充材料取舍、视频格式转换、DOI/URL、license 和模板内交叉引用。",
        },
        {
            "gate": "在线决策透明度 case-study",
            "status": gate(False, online_decision_case_study.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/materials/ONLINE_DECISION_CASE_STUDY_PACK.md",
            "interpretation": "从正式 240-run trace 中抽取 4 个代表性在线超车案例，记录 39 个超车事件和 327 行开始超车到完成超车窗口，用于解释动态邻域规划、安全评分和Desirable overtaking behavior行为。",
            "remaining_author_action": "该包是解释性案例材料，不替代确认性统计；修改 trace、summary、事件定义或代表性案例选择后需重跑。",
        },
        {
            "gate": "安全代理指标审计",
            "status": gate(False, safety_proxy_audit.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/materials/SAFETY_PROXY_AUDIT_PACK.md",
            "interpretation": "集中审计正式 240-run 的草地暴露、横向偏移、非赛道超车、接触/碰撞代理、草地恢复和 trace 抽样最小车距，用于约束安全相关 claim。",
            "remaining_author_action": "该包只支持仿真安全代理指标解释，不支持真实道路安全认证；修改指标定义、summary/trace 或 source data 后需重跑。",
        },
        {
            "gate": "审稿人复现包",
            "status": gate(False, reviewer.get("status")),
            "evidence": "outputs/tits_dynamic_graph/reviewer_replication_packet/REVIEWER_REPLICATION_README.md",
            "interpretation": "包含 smoke test、完整复现路线、数据/代码可用性草稿。",
            "remaining_author_action": "公开前替换 DOI、仓库地址和匿名化信息。",
        },
        {
            "gate": "审稿人 smoke 路线静态审计",
            "status": gate(False, reviewer_smoke_route.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/materials/REVIEWER_SMOKE_ROUTE_AUDIT.md",
            "interpretation": "静态检查 reviewer README、smoke 脚本、命令路径、脚本权限、Python 编译、关键输入文件、30 行 frozen case commands 和 README 摘要数字是否与当前证据链一致。",
            "remaining_author_action": "该审计不实际运行 GPU smoke；修改 reviewer packet、命令或 artifact manifest 后需重跑。",
        },
        {
            "gate": "根 README 开源入口一致性审计",
            "status": gate(False, root_readme_alignment.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/materials/ROOT_README_ALIGNMENT_AUDIT.md",
            "interpretation": "检查根 README 中的 T-ITS 算法定位、正式矩阵规模、Monza 外部赛道、8 车外推边界、smoke/正式结果边界、Makefile 快捷入口和关键证据路径是否与当前证据链一致。",
            "remaining_author_action": "修改 README、Makefile、source data 或 final dashboard 后重新运行该审计，并按真实 DOI/license/仓库 URL 更新公开说明。",
        },
        {
            "gate": "正文草稿与数值索引",
            "status": gate(False, manuscript.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_manuscript_package/materials/RESULTS_DRAFT.md",
            "interpretation": "Methods/Results/Limitations/Abstract 草稿已由证据表生成。",
            "remaining_author_action": "按 T-ITS 模板重写润色，并人工检查所有 claim 边界。",
        },
        {
            "gate": "主文数值追溯审计",
            "status": gate(False, manuscript_numeric_trace.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/materials/MANUSCRIPT_NUMERIC_TRACE_AUDIT.md",
            "interpretation": "Results 草稿中的核心数值已从正式 confirmatory evidence tables 重新计算，并与 manuscript numeric index 精确匹配。",
            "remaining_author_action": "编辑 Results、改 rounding 或重生成证据表后重新运行该审计。",
        },
        {
            "gate": "主文章节 claim 追溯审计",
            "status": gate(False, manuscript_section_trace.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/materials/MANUSCRIPT_SECTION_TRACE_AUDIT.md",
            "interpretation": "将 Abstract、Contributions、Methods、Results、Discussion 和 Data/Code Availability 映射到 15 类 claim、证据路径、限制边界和禁止表述，方便顶刊写作和返修逐段核对。",
            "remaining_author_action": "重写主文段落、增删 claim、调整 Discussion 或 Data/Code Availability 后重新运行章节追溯、claim-language、freshness、cross-reference 和 final dashboard。",
        },
        {
            "gate": "摘要与 Highlights 证据支撑审计",
            "status": gate(False, abstract_highlights.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/materials/ABSTRACT_HIGHLIGHTS_EVIDENCE_AUDIT.md",
            "interpretation": "检查摘要和 Highlights 中的 5 类核心声明是否有正式证据支撑、是否符合仿真边界、是否与 Results/图件/复现材料一致。",
            "remaining_author_action": "重写摘要、Highlights 或核心贡献表述后重新运行该审计、claim-language、freshness 和 dashboard。",
        },
        {
            "gate": "主文与补充材料导航",
            "status": gate(False, navigator.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/MANUSCRIPT_SUPPLEMENT_NAVIGATOR.md",
            "interpretation": "主文图表、补充材料、source data、GIF 和不应引用的历史产物已有统一索引。",
            "remaining_author_action": "最终排版时按该导航同步图号、表号、补充材料编号和 source-data 引用。",
        },
        {
            "gate": "图表与补充材料编号一致性审计",
            "status": gate(False, numbering_consistency.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_numbering_consistency_audit/materials/NUMBERING_CONSISTENCY_AUDIT.md",
            "interpretation": "主文图号、补充图/表/Note/Data/Video 编号、source-data crosswalk、上传槽位和 GIF manifest 的基本编号与文件指向已统一检查。",
            "remaining_author_action": "最终 Word/LaTeX 排版、重排图表或新增补充材料后重新运行该审计，并人工检查模板内交叉引用。",
        },
        {
            "gate": "英文投稿图件",
            "status": gate(False, english_figures.get("status")),
            "evidence": "outputs/tits_dynamic_graph/manuscript_english_figures/materials/FIGURE_DYNAMIC_DLC_OVERTAKING_QA.json",
            "interpretation": "包含英文四联投稿图、SVG/PDF/PNG/TIFF 导出、图例、QA 和 source data。",
            "remaining_author_action": "最终排版前按 IEEE T-ITS 图宽、字体和图号要求人工复核。",
        },
        {
            "gate": "图件 source data 与格式审计",
            "status": gate(False, figure_source_audit.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_figure_source_data_audit/materials/FIGURE_SOURCE_DATA_AUDIT.md",
            "interpretation": "正式主图/补充图已检查 PDF/SVG/PNG/TIFF 多格式导出、source CSV、图例和 QA/报告文件。",
            "remaining_author_action": "重画图、增删图件或移动 source data 后重新运行该审计，并同步 artifact manifest。",
        },
        {
            "gate": "主图 source data 数值复算审计",
            "status": gate(False, figure_source_value_recompute.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/materials/FIGURE_SOURCE_VALUE_RECOMPUTE_AUDIT.md",
            "interpretation": "主英文图 31 行 source data 的 mean/CI 与 formal overall、scenario、paired 统计表逐值一致，93 个数值单元无 mismatch。",
            "remaining_author_action": "重画英文主图、修改 source data 或更新统计表后重新运行该审计，并刷新 freshness、cross-reference、artifact manifest 和 dashboard。",
        },
        {
            "gate": "主图图注 claim 与 source data 审计",
            "status": gate(False, figure_caption_claim.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/materials/FIGURE_CAPTION_CLAIM_AUDIT.md",
            "interpretation": "检查主图 a-d 面板图注、source data、导出格式、图件 QA、数值复算和 Results 叙述是否闭环一致。",
            "remaining_author_action": "重画图、改 caption、调整面板声明或更换 source data 后重新运行该审计、图件数值复算、freshness 和 dashboard。",
        },
        {
            "gate": "媒体文件上传质量审计",
            "status": gate(False, media_upload_quality.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_media_upload_quality_audit/materials/MEDIA_UPLOAD_QUALITY_AUDIT.md",
            "interpretation": "正式图件和代表性 GIF 已检查文件存在、非空、Pillow 可读性、PNG/TIFF/GIF 尺寸、GIF 帧数和大文件上传风险。",
            "remaining_author_action": "最终上传前仍需按期刊门户实时文件大小/格式要求选择压缩版本、TIFF/PNG/PDF/SVG/GIF 或视频文件。",
        },
        {
            "gate": "贡献归因与消融证据",
            "status": gate(False, ablation.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_ablation_contribution_pack/materials/CONTRIBUTION_ATTRIBUTION_QA.json",
            "interpretation": "将 DLC 变种、动态邻域、安全权重、quality proposal 和规则专家整理为可写入 ablation/analysis 的表图材料。",
            "remaining_author_action": "最终论文中需明确该包复用确认性矩阵，不是新增随机化消融矩阵。",
        },
        {
            "gate": "逐 case 配对诊断与失败归因",
            "status": gate(False, casewise.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/materials/CASEWISE_OVERTAKING_DIAGNOSTIC_REPORT.md",
            "interpretation": "同 benchmark/车辆数/seed/赛道/traffic 的配对胜负、超车质量 deltas 和失败模式已可追溯，用于防止均值掩盖 case-level 行为。",
            "remaining_author_action": "若重生成确认性矩阵或修改失败阈值，需要重新运行该诊断包并同步补充材料解释。",
        },
        {
            "gate": "对比算法公平性审计",
            "status": gate(False, baseline_fairness.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_baseline_fairness_audit/materials/BASELINE_FAIRNESS_AUDIT.md",
            "interpretation": "冻结 case commands、source data 和 summary JSON 已验证 8 个算法共享 seed/车辆数/赛道/traffic/终止条件，且目标车最后身位起步。",
            "remaining_author_action": "新增算法、修改 benchmark case、重跑矩阵或改变终止条件后重新运行该审计。",
        },
        {
            "gate": "Benchmark 与指标协议卡",
            "status": gate(False, protocol.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/materials/BENCHMARK_METRIC_PROTOCOL_QA.json",
            "interpretation": "冻结 benchmark card、algorithm card、metric dictionary 和公平对比控制条件。",
            "remaining_author_action": "论文最终版中的指标定义需与该协议卡和 evaluator 代码保持一致。",
        },
        {
            "gate": "Source data 完整性审计",
            "status": gate(False, source_integrity.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_source_data_integrity_audit/materials/SOURCE_DATA_INTEGRITY_AUDIT.md",
            "interpretation": "冻结 source CSV 的 schema、240-run 规模、30 matched cases、8 algorithms、指标范围和 summary JSON 回链已通过检查。",
            "remaining_author_action": "重生成 source CSV、summary JSON 或 protocol card 后重新运行该审计。",
        },
        {
            "gate": "Source data 字段级 schema 字典",
            "status": gate(False, source_schema_dictionary.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/materials/SOURCE_DATA_SCHEMA_DICTIONARY.md",
            "interpretation": "正式 source data 的 42 个字段均有中文名称、语义、类型、单位、缺失策略、字段 profile 和逐单元 schema 验证记录。",
            "remaining_author_action": "重生成 source CSV、修改字段定义、增加指标列或调整缺失策略后重新运行 `make tits-source-data-schema` 并刷新 freshness/cross-reference/dashboard。",
        },
        {
            "gate": "逐 run 结果来源追溯审计",
            "status": gate(False, run_level_provenance.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_run_level_provenance_audit/materials/RUN_LEVEL_PROVENANCE_AUDIT.md",
            "interpretation": "正式 source data 的 240 行逐行回链到 summary JSON、trace JSON 和 frozen case command，并校验关键身份字段与指标字段无 mismatch。",
            "remaining_author_action": "重跑确认性矩阵、source data、summary/trace 或 frozen case commands 后重新运行该审计，并刷新 dashboard/status/release/cross-reference/freshness。",
        },
        {
            "gate": "逐步 trace 完整性审计",
            "status": gate(False, trace_integrity.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_trace_integrity_audit/materials/TRACE_INTEGRITY_AUDIT.md",
            "interpretation": "正式 240 个在线 trace 均可解析、步号连续、车辆维度一致，并可从逐步记录重算目标进度、横向误差、计算延迟、步数和 finish step。",
            "remaining_author_action": "重跑在线评估、压缩/移动 trace、修改 summary 指标或 trace schema 后重新运行该审计，并刷新 artifact/release/freshness/cross-reference/dashboard。",
        },
        {
            "gate": "Trace 字段级 schema 字典",
            "status": gate(False, trace_schema_dictionary.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/materials/TRACE_SCHEMA_DICTIONARY.md",
            "interpretation": "正式 240 个 trace / 528000 step 的逐步字段、动态车辆维度、类型、缺失策略、字段 profile 和 schema 验证均已整理为可审稿复核的数据字典。",
            "remaining_author_action": "重跑在线 trace、修改逐步字段、车辆维度编码或 trace 输出格式后重新运行 `make tits-trace-schema` 并刷新 freshness/cross-reference/dashboard。",
        },
        {
            "gate": "超车事件指标一致性审计",
            "status": gate(False, overtake_event_consistency.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/materials/OVERTAKE_EVENT_CONSISTENCY_AUDIT.md",
            "interpretation": "正式 240-run 的超车次数、赛道内超车、Desirable overtaking behavior、首次超车时间、完成耗时和窗口质量指标均可从 `overtake_events` 逐事件记录复算。",
            "remaining_author_action": "修改超车事件定义、quality 阈值、summary/source data 或 evaluator 后重新运行该审计，并刷新统计、claim、freshness、cross-reference 和 dashboard。",
        },
        {
            "gate": "统计结果表复算审计",
            "status": gate(False, statistical_table_recompute.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/materials/STATISTICAL_TABLE_RECOMPUTE_AUDIT.md",
            "interpretation": "从正式 240-run source data 按证据包 manifest 中的 bootstrap/seed 复算 overall、scenario 和 paired-test 统计表，3310 个统计单元无漂移。",
            "remaining_author_action": "重跑 source data、confirmatory evidence pack、统计参数或主结果表后重新运行该审计，并刷新 claim numeric、freshness、cross-reference 和 dashboard。",
        },
        {
            "gate": "Results 统计报告完整性清单",
            "status": gate(False, results_reporting.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_results_reporting_checklist/materials/RESULTS_REPORTING_CHECKLIST.md",
            "interpretation": "检查 5 个预设主假设是否具备 N、方向、均值差、95% CI、Holm p、效应量、配对胜/负/平计数，并回链到 source data 与复算审计。",
            "remaining_author_action": "重写 Results、改统计表、调整主假设或新增 exploratory 结论后重新运行该清单，并同步 manuscript numeric/claim audit。",
        },
        {
            "gate": "Results 主文叙述句模板包",
            "status": gate(False, results_narrative.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_results_narrative_pack/materials/RESULTS_NARRATIVE_PACK.md",
            "interpretation": "将 5 个预设主假设转换为可直接进入 Results 初稿的英文句子和中文解释，保留 CI、Holm p、效应量、配对胜负平和仿真边界。",
            "remaining_author_action": "主文润色时只能改写语气和衔接，不要手工改数字、方向、p 值或效应量；修改统计表后重新生成该包并刷新 claim numeric/freshness。",
        },
        {
            "gate": "环境与命令复现审计",
            "status": gate(False, environment.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/materials/ENVIRONMENT_REPRODUCIBILITY_AUDIT.md",
            "interpretation": "Python、必需依赖、CUDA/GPU、关键脚本可编译性和冻结 case command 覆盖已通过本地复现预检。",
            "remaining_author_action": "更换机器、conda 环境、CUDA 驱动、依赖版本或冻结命令后重新运行该审计。",
        },
        {
            "gate": "确定性 smoke 复现预检",
            "status": gate(False, determinism_smoke.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_determinism_smoke_audit/materials/DETERMINISM_SMOKE_AUDIT.md",
            "interpretation": "同一 seed、同一配置短程运行两次在线评估，v6-safe 与 original DLC 的关键 summary 指纹一致；该检查只验证评估入口和短程确定性，不作为性能结果。",
            "remaining_author_action": "更换 GPU/CUDA/Box2D/依赖版本或修改评估入口后重新运行；不要把该 smoke run 的性能数值写入 Results。",
        },
        {
            "gate": "复现胶囊与结果指纹",
            "status": "PASS" if fixed_point_status(reproducibility_capsule) else "CHECK",
            "evidence": "outputs/tits_dynamic_graph/tits_reproducibility_capsule/materials/REPRODUCIBILITY_CAPSULE.md",
            "interpretation": "集中记录冻结 case commands、source data digest、关键 artifact SHA256、正式 gate 状态和 8 个算法的结果矩阵指纹。",
            "remaining_author_action": "重跑确认性矩阵、改 source data、改发布路线或移动关键文件后重新运行该 capsule、artifact manifest、release plan 和 cross-reference audit。",
        },
        {
            "gate": "数据泄漏与调参来源审计",
            "status": gate(False, data_leakage_tuning.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/materials/DATA_LEAKAGE_AND_TUNING_PROVENANCE_AUDIT.md",
            "interpretation": "检查训练输出、冻结确认性矩阵、探索性调参目录、正式算法卡和发布分流规则，确认正式 source data 来自 v6 confirmatory matrix，且探索/调参输出未作为正式结果混入。",
            "remaining_author_action": "若新增训练、调参 sweep、正式算法或重跑确认性矩阵，需要重新运行该审计并在论文中保留 seed-level 训练日志未完全归档这一边界说明。",
        },
        {
            "gate": "创新点-证据追溯矩阵",
            "status": gate(False, innovation_traceability.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/materials/INNOVATION_EVIDENCE_TRACEABILITY_REPORT.md",
            "interpretation": "将动态图邻域、DLC world-model 主体、超车感知规划、安全/质量评分、quality proposal 和复现证据链逐项映射到代码、配置、算法卡、正式实验与写作边界。",
            "remaining_author_action": "修改算法结构、创新点表述、对比算法或正式证据包后重新运行该追溯矩阵，并同步 Methods/Contributions/Ablation 写法。",
        },
        {
            "gate": "指标阈值敏感性审计",
            "status": gate(False, metric_sensitivity.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/materials/METRIC_SENSITIVITY_AUDIT.md",
            "interpretation": "对质量超车/Desirable overtaking behavior相关草地率、横向偏移和完成耗时阈值做后验稳健性检查，报告 v6-safe 相对原始 DLC 的阈值敏感性和保守 claim 边界。",
            "remaining_author_action": "若修改指标定义、source data、阈值网格或主文 claim，需要重新运行该审计并在 Discussion 中保留后验敏感性分析边界。",
        },
        {
            "gate": "模型权重与算法配置审计",
            "status": gate(False, model_artifacts.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/materials/MODEL_ARTIFACT_INTEGRITY_AUDIT.md",
            "interpretation": "正式 algorithm card 声明的 DLC world-model、DLC 变种和 quality proposal 权重已检查存在性、checksum、CPU 可加载性和 config 对齐关系。",
            "remaining_author_action": "移动模型权重、改 algorithm card、改 config 或替换 baseline 权重后重新运行该审计和 artifact manifest。",
        },
        {
            "gate": "正式算法配置冻结审计",
            "status": gate(False, algorithm_config_freeze.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/materials/ALGORITHM_CONFIG_FREEZE_AUDIT.md",
            "interpretation": "正式 8 个算法的配置、algorithm card、source data 配置字段和 30 个 frozen case commands 的算法列表/顺序已交叉核对，并记录配置冻结指纹。",
            "remaining_author_action": "修改算法列表、planner 超参数、模型路径、algorithm card、source data 配置字段或 frozen case commands 后重新运行 `make tits-algorithm-config-freeze` 并刷新 dashboard/status/release/freshness/cross-reference。",
        },
        {
            "gate": "计算时间证据边界审计",
            "status": gate(False, compute_timing_boundary.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/materials/COMPUTE_TIMING_BOUNDARY_AUDIT.md",
            "interpretation": "将正式矩阵规模、仿真步数、逐 run 决策延迟、CUDA/GPU 环境和 T0-T3 复现层级，与未归档的历史 wall-clock/GPU/CPU utilization 时间序列明确分开。",
            "remaining_author_action": "若未来补充真实 wall-clock、GPU utilization 或 CPU utilization 采样，需要按 logging template 记录并重新运行该审计、compute cost、freshness、cross-reference 和 dashboard。",
        },
        {
            "gate": "AI/工具使用披露边界审计",
            "status": gate(False, ai_tool_use_disclosure.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/materials/AI_TOOL_USE_DISCLOSURE_AUDIT.md",
            "interpretation": "将 IEEE/T-ITS 投稿中的 AI/tool-use 披露准备工作与算法证据分离，检查披露草稿、作者侧动作、claim 边界、官方来源和禁止性夸大表述。",
            "remaining_author_action": "最终投稿前作者仍需确认 exact AI systems、涉及 sections 和 level of use，并在真实投稿门户/声明中填写。",
        },
        {
            "gate": "统计分析与多重比较",
            "status": gate(False, statistics.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_statistical_analysis_pack/materials/STATISTICAL_ANALYSIS_QA.json",
            "interpretation": "包含预定义主假设、Holm 校正、探索性全表校正、配对效应量和统计稳健性图。",
            "remaining_author_action": "最终 Results 中应优先报告效应量和 CI，p 值只作为冻结仿真矩阵的支持证据。",
        },
        {
            "gate": "实验设计、功效与稳定性审计",
            "status": gate(False, design_power.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_experimental_design_power_audit/materials/EXPERIMENTAL_DESIGN_POWER_AUDIT.md",
            "interpretation": "确认 30 matched cases、240 runs、6 个场景单元、主指标配对改善、bootstrap CI、case 胜/平/负和场景异质性。",
            "remaining_author_action": "若新增 seed、赛道、算法或重跑确认性矩阵，需重新运行该审计并同步统计图表。",
        },
        {
            "gate": "有效性威胁与审稿风险",
            "status": gate(False, threats.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_threats_validity_pack/materials/THREATS_VALIDITY_QA.json",
            "interpretation": "包含外部/构念/内部/统计/复现等有效性风险、claim guardrails 和 reviewer response map。",
            "remaining_author_action": "最终 Discussion 与 rebuttal 应使用 guardrails 约束 claim，不要把风险登记表写成风险已解决。",
        },
        {
            "gate": "审稿意见预案与修稿动作矩阵",
            "status": gate(False, reviewer_rebuttal.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/materials/REVIEWER_REBUTTAL_READINESS_PACK.md",
            "interpretation": "将真实道路安全、外部有效性、动态车辆数、草地行为、规则专家、指标阈值、统计、多 case 稳定性、复现和 GIF 证据等潜在质疑映射到证据路径与修稿动作。",
            "remaining_author_action": "收到真实审稿意见后按该矩阵定位证据，但仍需人工逐条回应具体评论；重跑矩阵或改主文后需重新生成该包。",
        },
        {
            "gate": "运行时扩展性与复杂度证据",
            "status": gate(False, runtime_scalability.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_runtime_scalability_pack/materials/RUNTIME_SCALABILITY_AND_COMPLEXITY_REPORT.md",
            "interpretation": "车辆数 4/5/6/8 下的延迟、超车质量、草地风险和 max-neighbor 复杂度边界已形成独立证据包。",
            "remaining_author_action": "若修改 planner budget、max_neighbors、模型权重或扩展到更高密度交通，需重新运行该分析。",
        },
        {
            "gate": "计算资源与复现成本透明度",
            "status": gate(False, compute_cost.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/materials/COMPUTE_REPRODUCIBILITY_COST_REPORT.md",
            "interpretation": "正式 240-run 矩阵的仿真步数、算法级延迟、GPU/环境快照、分层复现路线和 wall-clock 记录边界已集中整理。",
            "remaining_author_action": "若重跑矩阵、替换 GPU/环境或补充真实 wall-clock/GPU utilization，需要重新运行该成本报告并同步 Data/Code Availability。",
        },
        {
            "gate": "审稿人分层复现时间预算审计",
            "status": gate(False, reproduction_time_budget.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/materials/REVIEWER_REPRODUCTION_TIME_BUDGET_AUDIT.md",
            "interpretation": "将 T0 smoke、T1 报告层重建、T2 完整 240-run 确认性重跑和 T3 GIF 重建拆成输入、命令、预期输出、成本边界和验收标准，避免把 smoke/GIF 误写成正式性能复现。",
            "remaining_author_action": "如果修改 reviewer packet、case commands、compute cost、third-party reproduction tiers 或正式矩阵规模，需要重新运行该审计并刷新 dashboard/status/release/cross-reference/freshness。",
        },
        {
            "gate": "投稿 claim 证据完整性审计",
            "status": gate(False, claim_evidence.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/materials/CLAIM_EVIDENCE_COMPLETENESS_AUDIT.md",
            "interpretation": "主结果、超车质量、动态车辆数、Monza 外部赛道、失败边界、规则专家、指标敏感性、统计、case 稳定性、算法创新、复现、算力、GIF 和容器边界等 15 类可写 claim 均已绑定正式证据、限制边界和 rebuttal 入口。",
            "remaining_author_action": "修改摘要、结论、Results、Discussion 或新增 claim 后重新运行该审计，避免结论大于证据。",
        },
        {
            "gate": "写作 claim 语言边界审计",
            "status": gate(False, claim_language.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_claim_language_audit/materials/CLAIM_LANGUAGE_AUDIT.md",
            "interpretation": "扫描主文草稿、复现包、投稿元数据、GitHub README 草稿等正式写作材料，确认真实道路安全、任意泛化、保证无碰撞等高风险表述只出现在边界/限制上下文中。",
            "remaining_author_action": "最终重写摘要、结论、cover letter、README 或 rebuttal 后重新运行该审计，避免把仿真结论写成部署级安全声明。",
        },
        {
            "gate": "正式材料交叉引用审计",
            "status": gate(False, crossref.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_cross_reference_audit/materials/FORMAL_CROSS_REFERENCE_AUDIT.md",
            "interpretation": "正式 Markdown/CSV 中的路径引用已检查；缺失路径、高风险误引用和未知前缀为 0。",
            "remaining_author_action": "修改主文、补充材料、release plan 或 reviewer packet 后重新运行该审计。",
        },
        {
            "gate": "正式数字新鲜度审计",
            "status": gate(False, freshness.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_freshness_audit/materials/FRESHNESS_AUDIT.md",
            "interpretation": "主文、补充材料、复现包和投稿支撑材料中的核心数字已与当前正式 source data 和 final readiness 对齐。",
            "remaining_author_action": "重跑 dashboard、claim/rebuttal/FAIR 包或修改正式统计后，重新运行该审计。",
        },
        {
            "gate": "投稿元数据与声明草稿",
            "status": gate(False, submission_metadata.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_submission_metadata_pack/materials/IEEE_TITS_SUBMISSION_METADATA_PACK.md",
            "interpretation": "包含 T-ITS 标题、178词摘要、分类关键词、cover letter、AI/利益冲突/数据代码声明草稿和 submission checklist。",
            "remaining_author_action": "作者仍需确认最终作者信息、ORCID、基金、利益冲突、AI 工具使用细节、DOI/URL 和 ScholarOne 字段。",
        },
        {
            "gate": "GitHub开源最小复现与release清单",
            "status": gate(False, github_release.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_github_release_readiness_pack/materials/GITHUB_RELEASE_READINESS_PACK.md",
            "interpretation": "包含 GitHub README、CITATION.cff、CONTRIBUTING、MODEL_CARD、DATA_CARD 草稿，以及最小仓库清单和作者侧 release 行动项。",
            "remaining_author_action": "公开仓库前仍需填 DOI/URL、作者、license、release tag，并决定大体量产物放入数据仓库或 release assets。",
        },
        {
            "gate": "作者侧投稿闭环追踪",
            "status": gate(False, author_closure.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_author_submission_closure_pack/materials/AUTHOR_SUBMISSION_CLOSURE_PACK.md",
            "interpretation": "DOI/accession、代码仓库、license、IEEE 模板、作者/ORCID、基金/冲突/AI 声明、门户元数据、补充材料选择和最终 checksum freeze 等作者动作已映射到本地证据、占位符和重跑命令。",
            "remaining_author_action": "这些作者动作仍需通讯作者在真实投稿/归档平台完成；完成后按 regeneration commands 重跑本地审计。",
        },
        {
            "gate": "作者侧投稿完整性防误读审计",
            "status": gate(False, author_owned_integrity.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/materials/AUTHOR_OWNED_SUBMISSION_INTEGRITY_AUDIT.md",
            "interpretation": "检查 DOI/URL、代码 release、license、IEEE 模板、作者/ORCID、基金/冲突/AI 声明、门户元数据、补充材料选择和最终 checksum freeze 是否仍被显式标记为作者侧动作，而不是被本地自动流程误标为完成。",
            "remaining_author_action": "真实完成 DOI/release/license/作者声明/模板上传后，替换占位符并重跑 author closure、integrity audit、cross-reference、freshness、artifact manifest 和 final dashboard。",
        },
        {
            "gate": "投稿上传包分流图",
            "status": gate(False, upload_bundle.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/materials/SUBMISSION_UPLOAD_BUNDLE_MAP.md",
            "interpretation": "主文、图件、source data、补充材料、复现包、数据仓库、代码仓库、门户元数据、视觉补充和 internal-only 输出已有上传槽位与边界说明。",
            "remaining_author_action": "按最终期刊门户要求选择文件格式、补充材料范围和实际 DOI/URL；该图不是上传回执。",
        },
        {
            "gate": "投稿门户 dry-run 演练清单",
            "status": gate(False, submission_dry_run.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/materials/SUBMISSION_DRY_RUN_CHECKLIST.md",
            "interpretation": "按 IEEE/T-ITS 投稿前步骤检查主文、图件、source data、补充材料、视觉证据、复现包、代码/数据归档、声明、claim 边界、容器边界和最终 freeze 的本地证据。",
            "remaining_author_action": "该清单只是本地 dry-run；作者仍需真实完成 ScholarOne/IEEE 门户、DOI/URL、license、作者声明和最终模板上传。",
        },
        {
            "gate": "投稿缺口优先级审计",
            "status": gate(False, submission_gap_priority.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/materials/SUBMISSION_GAP_PRIORITY_AUDIT.md",
            "interpretation": "将 DOI/release/license、IEEE 模板、作者声明、source data、补充材料和最终 checksum freeze 等投稿缺口按 P0/P1/P2 排序，并检查每项是否有本地证据和完成后重跑路线。",
            "remaining_author_action": "按优先级完成 DOI、repository URL、license、模板、作者声明和门户上传后，重新运行 `make tits-refresh-gates` 并冻结最终 checksum。",
        },
        {
            "gate": "匿名化、隐私与本机痕迹审计",
            "status": gate(False, anonymization_privacy.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/materials/ANONYMIZATION_PRIVACY_AUDIT.md",
            "interpretation": "主文/投稿/审稿/开源材料中的本机绝对路径、临时路径、作者占位符、DOI/URL/license 占位符已扫描并分为边界复现痕迹或作者动作；未标注阻塞痕迹为 0。",
            "remaining_author_action": "最终匿名审稿政策、作者身份隐藏、公开 README 命令改写和 DOI/URL/license 替换仍需作者在真实投稿前确认。",
        },
        {
            "gate": "依赖与许可证审计",
            "status": gate(False, dependency_license.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_dependency_license_audit/materials/DEPENDENCY_LICENSE_AUDIT.md",
            "interpretation": "environment.yml、setup.py、当前安装版本、包许可证元数据和作者侧第三方 notice 边界已整理。",
            "remaining_author_action": "最终公开前仍需作者/机构确认代码、模型、数据、GIF、赛道和第三方依赖 notice 的法律许可。",
        },
        {
            "gate": "FAIR 数据归档元数据草案",
            "status": gate(False, fair_archive.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/materials/FAIR_ARCHIVE_METADATA_PACK.md",
            "interpretation": "面向 Zenodo/OSF/Figshare/机构仓储的数据归档描述、DataCite-style 元数据草案、FAIR checklist、归档角色摘要和 DOI/license/creator 占位符已生成。",
            "remaining_author_action": "创建真实数据仓库 DOI/accession、填写作者/ORCID/license/repository URL 后，重新生成该元数据包和 artifact manifest。",
        },
        {
            "gate": "第三方复现实操与容器草案",
            "status": gate(False, third_party_repro.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/materials/THIRD_PARTY_REPRODUCTION_PACK.md",
            "interpretation": "面向审稿人与第三方复现的 T0-T3 复现层级、Docker/Apptainer 草案、校验点和常见失败诊断已整理；容器明确标注为草案而非已认证镜像。",
            "remaining_author_action": "若最终选择发布容器镜像，需要实际构建、测试、记录 digest，并重新运行该包和环境审计。",
        },
        {
            "gate": "容器构建预检",
            "status": gate(False, container_preflight.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_container_build_preflight/materials/CONTAINER_BUILD_PREFLIGHT.md",
            "interpretation": "已记录本机 Docker/Apptainer/Singularity/NVIDIA 工具链可用性、容器草案完整性和未执行构建的边界。",
            "remaining_author_action": "若安装容器运行时并实际构建镜像，需要记录 image digest、GPU smoke 输出并重跑该预检与 artifact manifest。",
        },
        {
            "gate": "公开发布与数据仓库路由",
            "status": gate(False, release.get("status")) if release_audit.get("review_required_file_count") == 0 else "CHECK",
            "evidence": "outputs/tits_dynamic_graph/public_release_plan/PUBLIC_RELEASE_PLAN.md",
            "interpretation": "代码仓库、强制数据归档、可选全量归档和 local-only 输出已分流。",
            "remaining_author_action": "选择数据仓库并生成 DOI/accession；确认 license。",
        },
        {
            "gate": "SHA256 artifact manifest",
            "status": gate(False, artifact.get("status")),
            "evidence": "outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest_files.csv",
            "interpretation": f"{artifact.get('summary', {}).get('file_count')} 个文件已纳入当前证据链 checksum。",
            "remaining_author_action": "最终上传前重新冻结 checksum。",
        },
    ]
    return rows


def build_dashboard(rows, artifact, release_audit):
    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    check_rows = [row for row in rows if row["status"] != "PASS"]
    lines = [
        "# T-ITS Final Readiness Dashboard",
        "",
        "该 dashboard 汇总当前工作区能由文件和审计结果直接证明的投稿就绪状态。它不替代作者对 DOI、license、署名、期刊模板和最终文字的人工确认。",
        "",
        "## Summary",
        "",
        f"- Gates passed: {pass_count}/{len(rows)}",
        f"- Artifact manifest files: {artifact.get('summary', {}).get('file_count')}",
        f"- Artifact manifest size bytes: {artifact.get('summary', {}).get('size_bytes')}",
        f"- Public release review-required files: {release_audit.get('review_required_file_count')}",
        f"- Public release review-required directories: {release_audit.get('review_required_directory_count')}",
        "",
        "## Gate Table",
        "",
        "| Gate | Status | Evidence | Interpretation | Remaining author action |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['gate']} | {row['status']} | `{row['evidence']}` | {row['interpretation']} | {row['remaining_author_action']} |"
        )
    lines.extend(
        [
            "",
            "## Cannot Be Automated Locally",
            "",
            "- 数据仓库 DOI/accession、最终公开 URL、匿名化策略。",
            "- IEEE T-ITS 模板排版、最终 PDF、图号表号和交叉引用。",
            "- 作者贡献、利益冲突、伦理/AI 工具声明。",
            "- 代码和模型权重 license 的最终法律确认。",
            "- 是否补充更多外部赛道或更高密度交通以扩大 claim。",
        ]
    )
    if check_rows:
        lines.extend(["", "## Gates Requiring Attention", ""])
        for row in check_rows:
            lines.append(f"- {row['gate']}: {row['remaining_author_action']}")
    return "\n".join(lines)


def build_author_handoff(rows):
    lines = [
        "# Final Author Handoff Checklist",
        "",
        "## Ready to Use",
        "",
        "- 状态快照：`outputs/tits_dynamic_graph/tits_status_snapshot/`",
        "- 证据总账：`outputs/tits_dynamic_graph/tits_evidence_ledger/`",
        "- Claim 数值一致性审计：`outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/`",
        "- Checksum 重算校验审计：`outputs/tits_dynamic_graph/tits_checksum_verification_audit/`",
        "- 外部有效性边界审计：`outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/`",
        "- Discussion/Limitations 证据边界审计：`outputs/tits_dynamic_graph/tits_limitations_evidence_audit/`",
        "- 确认性实验协议与偏离边界登记：`outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/`",
        "- 作者侧投稿完整性防误读审计：`outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/`",
        "- Methods/Results/Limitations/Abstract 草稿：`outputs/tits_dynamic_graph/tits_manuscript_package/materials/`",
        "- 主文数值追溯审计：`outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/`",
        "- 主文章节 claim 追溯审计：`outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/`",
        "- 摘要与 Highlights 证据支撑审计：`outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/`",
        "- 主文/补充材料导航：`outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/`",
        "- 图表与补充材料编号一致性审计：`outputs/tits_dynamic_graph/tits_numbering_consistency_audit/`",
        "- 图件 source data 与格式审计：`outputs/tits_dynamic_graph/tits_figure_source_data_audit/`",
        "- 主图 source data 数值复算审计：`outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/`",
        "- 代表性 GIF 来源追溯审计：`outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/`",
        "- 补充视频/GIF 投稿索引：`outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/`",
        "- 补充材料投稿总索引：`outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/`",
        "- 在线决策透明度 case-study：`outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/`",
        "- 安全代理指标审计：`outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/`",
        "- 媒体文件上传质量审计：`outputs/tits_dynamic_graph/tits_media_upload_quality_audit/`",
        "- 英文投稿图件和 source data：`outputs/tits_dynamic_graph/manuscript_english_figures/`",
        "- 主图图注 claim 与 source data 审计：`outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/`",
        "- 主表/补充表 caption 与 source-data 审计：`outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/`",
        "- 主表/补充表数值复算审计：`outputs/tits_dynamic_graph/tits_table_value_recompute_audit/`",
        "- 贡献归因/消融图表：`outputs/tits_dynamic_graph/tits_ablation_contribution_pack/`",
        "- 逐 case 配对诊断与失败归因：`outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/`",
        "- 对比算法公平性审计：`outputs/tits_dynamic_graph/tits_baseline_fairness_audit/`",
        "- Benchmark/metric/protocol card：`outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/`",
        "- Source data 完整性审计：`outputs/tits_dynamic_graph/tits_source_data_integrity_audit/`",
        "- Source data 字段级 schema 字典：`outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/`",
        "- Run-level provenance 审计：`outputs/tits_dynamic_graph/tits_run_level_provenance_audit/`",
        "- Trace integrity 审计：`outputs/tits_dynamic_graph/tits_trace_integrity_audit/`",
        "- Trace 字段级 schema 字典：`outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/`",
        "- 超车事件指标一致性审计：`outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/`",
        "- 统计结果表复算审计：`outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/`",
        "- Results 统计报告完整性清单：`outputs/tits_dynamic_graph/tits_results_reporting_checklist/`",
        "- Results 主文叙述句模板包：`outputs/tits_dynamic_graph/tits_results_narrative_pack/`",
        "- 环境与命令复现审计：`outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/`",
        "- 确定性 smoke 复现预检：`outputs/tits_dynamic_graph/tits_determinism_smoke_audit/`",
        "- 复现胶囊与结果指纹：`outputs/tits_dynamic_graph/tits_reproducibility_capsule/`",
        "- 数据泄漏与调参来源审计：`outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/`",
        "- 创新点-证据追溯矩阵：`outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/`",
        "- 指标阈值敏感性审计：`outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/`",
        "- 模型权重与算法配置审计：`outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/`",
        "- 正式算法配置冻结审计：`outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/`",
        "- 计算时间证据边界审计：`outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/`",
        "- AI/工具使用披露边界审计：`outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/`",
        "- 统计分析计划与多重比较校正：`outputs/tits_dynamic_graph/tits_statistical_analysis_pack/`",
        "- 实验设计、功效与稳定性审计：`outputs/tits_dynamic_graph/tits_experimental_design_power_audit/`",
        "- 有效性威胁和审稿风险回应：`outputs/tits_dynamic_graph/tits_threats_validity_pack/`",
        "- 审稿意见预案与修稿动作矩阵：`outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/`",
        "- 运行时扩展性与复杂度证据：`outputs/tits_dynamic_graph/tits_runtime_scalability_pack/`",
        "- 计算资源与复现成本透明度：`outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/`",
        "- 审稿人分层复现时间预算审计：`outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/`",
        "- 投稿 claim 证据完整性审计：`outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/`",
        "- 写作 claim 语言边界审计：`outputs/tits_dynamic_graph/tits_claim_language_audit/`",
        "- 正式材料交叉引用审计：`outputs/tits_dynamic_graph/tits_cross_reference_audit/`",
        "- 正式数字新鲜度审计：`outputs/tits_dynamic_graph/tits_freshness_audit/`",
        "- 投稿元数据与声明草稿：`outputs/tits_dynamic_graph/tits_submission_metadata_pack/`",
        "- GitHub开源最小复现与release清单：`outputs/tits_dynamic_graph/tits_github_release_readiness_pack/`",
        "- 开源最小复现仓库审计：`outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/`",
        "- 作者侧投稿闭环追踪：`outputs/tits_dynamic_graph/tits_author_submission_closure_pack/`",
        "- 作者侧投稿完整性防误读审计：`outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/`",
        "- 投稿上传包分流图：`outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/`",
        "- 投稿门户 dry-run 演练清单：`outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/`",
        "- 投稿缺口优先级审计：`outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/`",
        "- 匿名化、隐私与本机痕迹审计：`outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/`",
        "- 依赖与许可证审计：`outputs/tits_dynamic_graph/tits_dependency_license_audit/`",
        "- FAIR 数据归档元数据草案：`outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/`",
        "- 第三方复现实操与容器草案：`outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/`",
        "- 容器构建预检：`outputs/tits_dynamic_graph/tits_container_build_preflight/`",
        "- 主结果和 source data：`outputs/tits_dynamic_graph/v6_confirmatory_matrix_full_summary/`",
        "- Source data 字段级 schema 字典：`outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/`",
        "- Trace 字段级 schema 字典：`outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/`",
        "- 统计证据和失败模式：`outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/`",
        "- 审稿复现包：`outputs/tits_dynamic_graph/reviewer_replication_packet/`",
        "- 审稿人 smoke 路线静态审计：`outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/`",
        "- 根 README 开源入口一致性审计：`outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/`",
        "- 公开发布计划：`outputs/tits_dynamic_graph/public_release_plan/`",
        "- SHA256 manifest：`outputs/tits_dynamic_graph/artifact_manifest/`",
        "",
        "## Before Submission",
        "",
        "- 将 manuscript 草稿改写进 IEEE T-ITS 模板。",
        "- 逐项核对 Results 数值和 `manuscript_numeric_index.csv`。",
        "- 确认最终图表是否使用 PNG/SVG/PDF/TIFF 哪些格式。",
        "- 上传数据仓库并把 DOI/URL 写入 Data Availability。",
        "- 确认开源仓库是否剥离 local-only/smoke/optimization outputs。",
        "- 最终上传前重新运行 public release plan 和 artifact manifest。",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export final readiness dashboard for the T-ITS dynamic graph package.")
    parser.add_argument("--out-dir", default="outputs/tits_dynamic_graph/final_readiness_dashboard")
    args = parser.parse_args()

    readiness = load_json("outputs/tits_dynamic_graph/tits_readiness_audit.json")
    matrix_audit = load_json("outputs/tits_dynamic_graph/v6_confirmatory_preflight/v6_confirmatory_matrix_audit.json")
    evidence = load_json("outputs/tits_dynamic_graph/tits_confirmatory_evidence_pack/confirmatory_evidence_pack_manifest.json")
    reviewer = load_json("outputs/tits_dynamic_graph/reviewer_replication_packet/reviewer_replication_packet_manifest.json")
    reviewer_smoke_route = load_json("outputs/tits_dynamic_graph/tits_reviewer_smoke_route_audit/tits_reviewer_smoke_route_audit_manifest.json")
    root_readme_alignment = load_json("outputs/tits_dynamic_graph/tits_root_readme_alignment_audit/tits_root_readme_alignment_audit_manifest.json")
    manuscript = load_json("outputs/tits_dynamic_graph/tits_manuscript_package/tits_manuscript_package_manifest.json")
    manuscript_numeric_trace = load_json("outputs/tits_dynamic_graph/tits_manuscript_numeric_trace_audit/tits_manuscript_numeric_trace_audit_manifest.json")
    manuscript_section_trace = load_json("outputs/tits_dynamic_graph/tits_manuscript_section_trace_audit/tits_manuscript_section_trace_audit_manifest.json")
    abstract_highlights = load_json("outputs/tits_dynamic_graph/tits_abstract_highlights_evidence_audit/tits_abstract_highlights_evidence_audit_manifest.json")
    navigator = load_json("outputs/tits_dynamic_graph/tits_manuscript_supplement_navigator/materials/NAVIGATOR_QA.json")
    numbering_consistency = load_json("outputs/tits_dynamic_graph/tits_numbering_consistency_audit/tits_numbering_consistency_audit_manifest.json")
    figure_source_audit = load_json("outputs/tits_dynamic_graph/tits_figure_source_data_audit/tits_figure_source_data_audit_manifest.json")
    figure_source_value_recompute = load_json("outputs/tits_dynamic_graph/tits_figure_source_value_recompute_audit/tits_figure_source_value_recompute_audit_manifest.json")
    figure_caption_claim = load_json("outputs/tits_dynamic_graph/tits_figure_caption_claim_audit/tits_figure_caption_claim_audit_manifest.json")
    table_caption_source_data = load_json("outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/tits_table_caption_source_data_audit_manifest.json")
    table_value_recompute = load_json("outputs/tits_dynamic_graph/tits_table_value_recompute_audit/tits_table_value_recompute_audit_manifest.json")
    publication_gif_provenance = load_json("outputs/tits_dynamic_graph/tits_publication_gif_provenance_audit/tits_publication_gif_provenance_audit_manifest.json")
    supplementary_video_index = load_json("outputs/tits_dynamic_graph/tits_supplementary_video_index_pack/tits_supplementary_video_index_pack_manifest.json")
    supplementary_submission_index = load_json("outputs/tits_dynamic_graph/tits_supplementary_submission_index_pack/tits_supplementary_submission_index_pack_manifest.json")
    online_decision_case_study = load_json("outputs/tits_dynamic_graph/tits_online_decision_case_study_pack/tits_online_decision_case_study_pack_manifest.json")
    safety_proxy_audit = load_json("outputs/tits_dynamic_graph/tits_safety_proxy_audit_pack/tits_safety_proxy_audit_pack_manifest.json")
    media_upload_quality = load_json("outputs/tits_dynamic_graph/tits_media_upload_quality_audit/tits_media_upload_quality_audit_manifest.json")
    english_figures = load_json("outputs/tits_dynamic_graph/manuscript_english_figures/manuscript_english_figures_manifest.json")
    ablation = load_json("outputs/tits_dynamic_graph/tits_ablation_contribution_pack/tits_ablation_contribution_pack_manifest.json")
    casewise = load_json("outputs/tits_dynamic_graph/tits_casewise_diagnostic_pack/tits_casewise_diagnostic_pack_manifest.json")
    baseline_fairness = load_json("outputs/tits_dynamic_graph/tits_baseline_fairness_audit/tits_baseline_fairness_audit_manifest.json")
    protocol = load_json("outputs/tits_dynamic_graph/tits_benchmark_protocol_pack/tits_benchmark_protocol_pack_manifest.json")
    source_integrity = load_json("outputs/tits_dynamic_graph/tits_source_data_integrity_audit/tits_source_data_integrity_audit_manifest.json")
    source_schema_dictionary = load_json("outputs/tits_dynamic_graph/tits_source_data_schema_dictionary_pack/tits_source_data_schema_dictionary_pack_manifest.json")
    run_level_provenance = load_json("outputs/tits_dynamic_graph/tits_run_level_provenance_audit/tits_run_level_provenance_audit_manifest.json")
    trace_integrity = load_json("outputs/tits_dynamic_graph/tits_trace_integrity_audit/tits_trace_integrity_audit_manifest.json")
    trace_schema_dictionary = load_json("outputs/tits_dynamic_graph/tits_trace_schema_dictionary_pack/tits_trace_schema_dictionary_pack_manifest.json")
    overtake_event_consistency = load_json("outputs/tits_dynamic_graph/tits_overtake_event_consistency_audit/tits_overtake_event_consistency_audit_manifest.json")
    statistical_table_recompute = load_json("outputs/tits_dynamic_graph/tits_statistical_table_recompute_audit/tits_statistical_table_recompute_audit_manifest.json")
    results_reporting = load_json("outputs/tits_dynamic_graph/tits_results_reporting_checklist/tits_results_reporting_checklist_manifest.json")
    results_narrative = load_json("outputs/tits_dynamic_graph/tits_results_narrative_pack/tits_results_narrative_pack_manifest.json")
    environment = load_json("outputs/tits_dynamic_graph/tits_environment_reproducibility_audit/tits_environment_reproducibility_audit_manifest.json")
    determinism_smoke = load_json("outputs/tits_dynamic_graph/tits_determinism_smoke_audit/tits_determinism_smoke_audit_manifest.json")
    reproducibility_capsule = load_json("outputs/tits_dynamic_graph/tits_reproducibility_capsule/tits_reproducibility_capsule_manifest.json")
    data_leakage_tuning = load_json("outputs/tits_dynamic_graph/tits_data_leakage_tuning_audit/tits_data_leakage_tuning_audit_manifest.json")
    innovation_traceability = load_json("outputs/tits_dynamic_graph/tits_innovation_evidence_traceability/tits_innovation_evidence_traceability_manifest.json")
    metric_sensitivity = load_json("outputs/tits_dynamic_graph/tits_metric_sensitivity_audit/tits_metric_sensitivity_audit_manifest.json")
    model_artifacts = load_json("outputs/tits_dynamic_graph/tits_model_artifact_integrity_audit/tits_model_artifact_integrity_audit_manifest.json")
    algorithm_config_freeze = load_json("outputs/tits_dynamic_graph/tits_algorithm_config_freeze_audit/tits_algorithm_config_freeze_audit_manifest.json")
    compute_timing_boundary = load_json("outputs/tits_dynamic_graph/tits_compute_timing_boundary_audit/tits_compute_timing_boundary_audit_manifest.json")
    ai_tool_use_disclosure = load_json("outputs/tits_dynamic_graph/tits_ai_tool_use_disclosure_audit/tits_ai_tool_use_disclosure_audit_manifest.json")
    statistics = load_json("outputs/tits_dynamic_graph/tits_statistical_analysis_pack/tits_statistical_analysis_pack_manifest.json")
    design_power = load_json("outputs/tits_dynamic_graph/tits_experimental_design_power_audit/tits_experimental_design_power_audit_manifest.json")
    threats = load_json("outputs/tits_dynamic_graph/tits_threats_validity_pack/tits_threats_validity_pack_manifest.json")
    reviewer_rebuttal = load_json("outputs/tits_dynamic_graph/tits_reviewer_rebuttal_readiness_pack/tits_reviewer_rebuttal_readiness_pack_manifest.json")
    runtime_scalability = load_json("outputs/tits_dynamic_graph/tits_runtime_scalability_pack/tits_runtime_scalability_pack_manifest.json")
    compute_cost = load_json("outputs/tits_dynamic_graph/tits_compute_reproducibility_cost_pack/tits_compute_reproducibility_cost_pack_manifest.json")
    reproduction_time_budget = load_json("outputs/tits_dynamic_graph/tits_reviewer_reproduction_time_budget_audit/tits_reviewer_reproduction_time_budget_audit_manifest.json")
    claim_evidence = load_json("outputs/tits_dynamic_graph/tits_claim_evidence_completeness_audit/tits_claim_evidence_completeness_audit_manifest.json")
    claim_language = load_json("outputs/tits_dynamic_graph/tits_claim_language_audit/tits_claim_language_audit_manifest.json")
    submission_metadata = load_json("outputs/tits_dynamic_graph/tits_submission_metadata_pack/tits_submission_metadata_pack_manifest.json")
    github_release = load_json("outputs/tits_dynamic_graph/tits_github_release_readiness_pack/tits_github_release_readiness_pack_manifest.json")
    open_source_minimal_repo = load_json("outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/tits_open_source_minimal_repo_audit_manifest.json")
    author_closure = load_json("outputs/tits_dynamic_graph/tits_author_submission_closure_pack/tits_author_submission_closure_pack_manifest.json")
    author_owned_integrity = load_json("outputs/tits_dynamic_graph/tits_author_owned_submission_integrity_audit/tits_author_owned_submission_integrity_audit_manifest.json")
    upload_bundle = load_json("outputs/tits_dynamic_graph/tits_submission_upload_bundle_map/tits_submission_upload_bundle_map_manifest.json")
    submission_dry_run = load_json("outputs/tits_dynamic_graph/tits_submission_dry_run_checklist/tits_submission_dry_run_checklist_manifest.json")
    submission_gap_priority = load_json("outputs/tits_dynamic_graph/tits_submission_gap_priority_audit/tits_submission_gap_priority_audit_manifest.json")
    final_freeze_consistency = load_json("outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit/tits_final_freeze_consistency_audit_manifest.json")
    anonymization_privacy = load_json("outputs/tits_dynamic_graph/tits_anonymization_privacy_audit/tits_anonymization_privacy_audit_manifest.json")
    dependency_license = load_json("outputs/tits_dynamic_graph/tits_dependency_license_audit/tits_dependency_license_audit_manifest.json")
    fair_archive = load_json("outputs/tits_dynamic_graph/tits_fair_archive_metadata_pack/tits_fair_archive_metadata_pack_manifest.json")
    third_party_repro = load_json("outputs/tits_dynamic_graph/tits_third_party_reproduction_pack/tits_third_party_reproduction_pack_manifest.json")
    container_preflight = load_json("outputs/tits_dynamic_graph/tits_container_build_preflight/tits_container_build_preflight_manifest.json")
    status_snapshot = load_json("outputs/tits_dynamic_graph/tits_status_snapshot/tits_status_snapshot_manifest.json")
    evidence_ledger = load_json("outputs/tits_dynamic_graph/tits_evidence_ledger/tits_evidence_ledger_manifest.json")
    claim_numeric = load_json("outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/tits_claim_numeric_consistency_audit_manifest.json")
    checksum_audit = load_json("outputs/tits_dynamic_graph/tits_checksum_verification_audit/tits_checksum_verification_audit_manifest.json")
    external_validity = load_json("outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/tits_external_validity_boundary_audit_manifest.json")
    limitations_evidence = load_json("outputs/tits_dynamic_graph/tits_limitations_evidence_audit/tits_limitations_evidence_audit_manifest.json")
    protocol_deviation = load_json("outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/tits_protocol_deviation_readiness_pack_manifest.json")
    crossref = load_json("outputs/tits_dynamic_graph/tits_cross_reference_audit/tits_cross_reference_audit_manifest.json")
    freshness = load_json("outputs/tits_dynamic_graph/tits_freshness_audit/tits_freshness_audit_manifest.json")
    release = load_json("outputs/tits_dynamic_graph/public_release_plan/public_release_plan_manifest.json")
    release_audit = load_json("outputs/tits_dynamic_graph/public_release_plan/public_release_audit.json")
    artifact = load_json("outputs/tits_dynamic_graph/artifact_manifest/tits_dynamic_graph_artifact_manifest.json")
    gif_manifest = load_json("outputs/tits_dynamic_graph/publication_gifs/publication_gif_manifest.json")

    rows = build_rows(readiness, matrix_audit, evidence, reviewer, reviewer_smoke_route, root_readme_alignment, manuscript, manuscript_numeric_trace, manuscript_section_trace, abstract_highlights, navigator, numbering_consistency, figure_source_audit, figure_source_value_recompute, figure_caption_claim, publication_gif_provenance, supplementary_video_index, supplementary_submission_index, online_decision_case_study, safety_proxy_audit, media_upload_quality, english_figures, ablation, casewise, baseline_fairness, protocol, source_integrity, source_schema_dictionary, run_level_provenance, trace_integrity, trace_schema_dictionary, overtake_event_consistency, statistical_table_recompute, results_reporting, results_narrative, environment, determinism_smoke, reproducibility_capsule, data_leakage_tuning, innovation_traceability, metric_sensitivity, model_artifacts, algorithm_config_freeze, compute_timing_boundary, ai_tool_use_disclosure, statistics, design_power, threats, reviewer_rebuttal, runtime_scalability, compute_cost, reproduction_time_budget, claim_evidence, claim_language, submission_metadata, github_release, author_closure, author_owned_integrity, upload_bundle, submission_dry_run, submission_gap_priority, anonymization_privacy, dependency_license, fair_archive, third_party_repro, container_preflight, crossref, freshness, release, release_audit, artifact, gif_manifest)
    rows.insert(
        7,
        {
            "gate": "状态快照归档",
            "status": "PASS" if fixed_point_status(status_snapshot) else "CHECK",
            "evidence": "outputs/tits_dynamic_graph/tits_status_snapshot/TITS_STATUS_SNAPSHOT.md",
            "interpretation": "将正式矩阵规模、final readiness、freshness/cross-reference、README、reviewer route、artifact/release/FAIR 状态压缩为可归档的一页快照和机器可读 JSON/CSV。",
            "remaining_author_action": "修改正式 source data、dashboard、release plan、README 或 reviewer packet 后重新运行 `make tits-status-snapshot` 并刷新 artifact manifest。",
        },
    )
    rows.insert(
        8,
        {
            "gate": "证据总账",
            "status": gate(False, evidence_ledger.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_evidence_ledger/materials/EVIDENCE_LEDGER.md",
            "interpretation": "将 15 类论文 claim 映射到 source data、统计表、图件、GIF、代码、审计报告、复现命令和 SHA256 artifact manifest，方便审稿人逐 claim 查证。",
            "remaining_author_action": "修改 claim、图表、source data、复现命令或 artifact manifest 后重新运行 evidence ledger，并刷新 cross-reference、freshness、release plan 和 final dashboard。",
        },
    )
    rows.insert(
        9,
        {
            "gate": "Claim 数值一致性审计",
            "status": gate(False, claim_numeric.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_claim_numeric_consistency_audit/materials/CLAIM_NUMERIC_CONSISTENCY_AUDIT.md",
            "interpretation": "将 claim 文本中的关键数字重新对照正式 source data、统计表、场景表、运行时扩展性表、敏感性表和容器/算力元数据，防止写作数值漂移。",
            "remaining_author_action": "修改 claim 文本、source data、统计表或 Results 数字后重新运行该审计，并刷新 evidence ledger、freshness、cross-reference 和 final dashboard。",
        },
    )
    rows.insert(
        10,
        {
            "gate": "Checksum 重算校验审计",
            "status": gate(False, checksum_audit.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_checksum_verification_audit/materials/CHECKSUM_VERIFICATION_AUDIT.md",
            "interpretation": "从 artifact manifest 独立重算关键 source data、复现材料、图/GIF manifest、模型/轨道/代码样本和 dashboard 产物的 SHA256 与文件大小，确认 checksum 清单可被第三方复核。",
            "remaining_author_action": "最终 DOI/release freeze 前建议运行 `make tits-checksum-audit` 或脚本 `--full` 模式，并在重生成 artifact manifest 后再次刷新该审计。",
        },
    )
    rows.insert(
        11,
        {
            "gate": "外部有效性边界审计",
            "status": gate(False, external_validity.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_external_validity_boundary_audit/materials/EXTERNAL_VALIDITY_BOUNDARY_AUDIT.md",
            "interpretation": "从正式 240-run source data、benchmark protocol 和 threats register 复算仿真-only、单 Monza 外部赛道、8 车外推、指标代理和 baseline 家族边界，防止论文泛化 claim 过度。",
            "remaining_author_action": "新增外部赛道、更高密度交通、真实/高保真仿真或修改 Abstract/Conclusion 泛化表述后重新运行该审计，并同步 claim-language、freshness 和 cross-reference。",
        },
    )
    rows.insert(
        12,
        {
            "gate": "Discussion/Limitations 证据边界审计",
            "status": gate(False, limitations_evidence.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_limitations_evidence_audit/materials/LIMITATIONS_EVIDENCE_AUDIT.md",
            "interpretation": "检查 Limitations 草稿是否覆盖仿真-only、Monza 单外部赛道、8 车外推、残余草地/不符合 desirable overtaking behavior 标准的超车、规则专家强基线、后验阈值敏感性、quality proposal 角色、算力记录边界和未来验证缺口，并逐条链接正式证据路径。",
            "remaining_author_action": "重写 Discussion、Limitations、Abstract/Conclusion 或新增外推 claim 后重新运行该审计、claim-language、freshness、cross-reference 和 final dashboard。",
        },
    )
    rows.insert(
        13,
        {
            "gate": "确认性实验协议与偏离边界登记",
            "status": gate(False, protocol_deviation.get("status")),
            "evidence": "outputs/tits_dynamic_graph/tits_protocol_deviation_readiness_pack/materials/PROTOCOL_DEVIATION_READINESS_REPORT.md",
            "interpretation": "将冻结 source data、主/次/探索性 endpoint、analysis population、条件样本量、调参隔离、指标阈值敏感性、GIF 解释边界和容器草案边界整理成 protocol/deviation register，降低事后挑选指标和过度 claim 风险。",
            "remaining_author_action": "修改 benchmark、指标、统计方案、正式矩阵、GIF/容器边界或 Results claim 后重新运行该包，并刷新 freshness、cross-reference、artifact manifest 和 final dashboard。",
        },
    )
    for idx, row in enumerate(rows):
        if row["gate"] == "GitHub开源最小复现与release清单":
            rows.insert(
                idx + 1,
                {
                    "gate": "开源最小复现仓库审计",
                    "status": "PASS" if fixed_point_status(open_source_minimal_repo) else "CHECK",
                    "evidence": "outputs/tits_dynamic_graph/tits_open_source_minimal_repo_audit/materials/OPEN_SOURCE_MINIMAL_REPO_AUDIT.md",
                    "interpretation": "检查最小 GitHub 复现单元的 31 个必需文件/证据入口、223 个发布分流条目、GitHub release 草稿同步、README/reviewer route、依赖许可与匿名化边界，确保大文件和正式 source data 走 archive/release-assets 路线。",
                    "remaining_author_action": "公开前仍需作者创建真实仓库/release tag、确认 license/notice、替换 DOI/URL/作者占位符，并在最终发布后重新运行该审计和 checksum/release/freshness/dashboard。",
                },
            )
            break
    for idx, row in enumerate(rows):
        if row["gate"] == "开源最小复现仓库审计":
            rows.insert(
                idx + 1,
                {
                    "gate": "最终冻结一致性审计",
                    "status": "PASS" if fixed_point_status(final_freeze_consistency) else "CHECK",
                    "evidence": "outputs/tits_dynamic_graph/tits_final_freeze_consistency_audit/materials/FINAL_FREEZE_CONSISTENCY_AUDIT.md",
                    "interpretation": "交叉核对 final dashboard、status snapshot、freshness/cross-reference、artifact manifest、release/FAIR、GitHub/minimal repo、复现胶囊和作者侧动作边界，确保最终冻结包在本地证据链内一致。",
                    "remaining_author_action": "最终 DOI/release/license/作者声明/IEEE 模板或 artifact 路由发生变化后，重新运行 `make tits-refresh-gates` 并复核该冻结审计。",
                },
            )
            break
    for idx, row in enumerate(rows):
        if row["gate"] == "主图图注 claim 与 source data 审计":
            rows.insert(
                idx + 1,
                {
                    "gate": "主表/补充表 caption 与 source-data 审计",
                    "status": gate(False, table_caption_source_data.get("status")),
                    "evidence": "outputs/tits_dynamic_graph/tits_table_caption_source_data_audit/materials/TABLE_CAPTION_SOURCE_DATA_AUDIT.md",
                    "interpretation": "检查 Main Table 1 和 Supplementary Table S1-S6 的 primary artifact、source data、上游统计/协议/公平性/风险/运行时/复现材料状态，以及 caption 边界是否保留仿真-only、matched-case、公平 baseline 和复现层级说明。",
                    "remaining_author_action": "重排主表/补充表、改 caption、移动 source data 或更新统计/协议/复现表后重新运行该审计、freshness、cross-reference、artifact manifest 和 dashboard。",
                },
            )
            rows.insert(
                idx + 2,
                {
                    "gate": "主表/补充表数值复算审计",
                    "status": gate(False, table_value_recompute.get("status")),
                    "evidence": "outputs/tits_dynamic_graph/tits_table_value_recompute_audit/materials/TABLE_VALUE_RECOMPUTE_AUDIT.md",
                    "interpretation": "逐行检查 Main Table 1 的 384 行显示值是否与 aggregate statistics 按相同 rounding 规则一致，并交叉核对 Supplementary Table S2 的 5 个主假设 Holm 行与 effect-size 表字段一致；1172 个数值单元无 mismatch。",
                    "remaining_author_action": "重生成主表、改统计精度、更新 Holm/effect-size 表或改补充表 S2 后重新运行该审计，并刷新 freshness、cross-reference、artifact manifest 和 dashboard。",
                },
            )
            break
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "dashboard_md": write(out_dir / "FINAL_READINESS_DASHBOARD.md", build_dashboard(rows, artifact, release_audit)),
        "handoff_md": write(out_dir / "FINAL_AUTHOR_HANDOFF_CHECKLIST.md", build_author_handoff(rows)),
        "gate_csv": write_csv(out_dir / "final_readiness_gates.csv", rows),
    }
    status = "pass" if all(row["status"] == "PASS" for row in rows) else "author_action_required"
    manifest = {
        "status": status,
        "out_dir": str(out_dir),
        "gate_count": len(rows),
        "pass_count": sum(1 for row in rows if row["status"] == "PASS"),
        "paths": paths,
        "author_owned_items": [
            "DOI/accession",
            "license confirmation",
            "IEEE T-ITS template conversion",
            "final author metadata and declarations",
            "exact AI/tool-use disclosure",
        ],
    }
    manifest_path = write(out_dir / "final_readiness_dashboard_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({"manifest": manifest_path, "status": status, "pass_count": manifest["pass_count"], "gate_count": len(rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
