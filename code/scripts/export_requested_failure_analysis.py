#!/usr/bin/env python
"""Turn retained failure-atlas rows into a reviewer-facing analysis table."""
import argparse
import csv
from pathlib import Path


TEMPLATES = {
    "off_track_overtake": (
        "邻车在短时窗内被识别为可超越，但候选动作的横向偏移累积过快",
        "动态选择优先保留交互车辆，却没有足够的几何余量；质量项对短期前向收益的偏好压过了赛道边界惩罚",
        "增加曲率/横向余量门控，并单独报告 on-track 与 total success"
    ),
    "high_grass_exposure": (
        "超车完成但目标车长时间处于草地或边界附近",
        "质量评分使用预测 on-track/grass 信号，模型误差使边界状态被低估；恢复动作触发滞后",
        "校准 grass 概率、提高边界状态权重，并按恢复时间分层"
    ),
    "long_overtake_window": (
        "前车间距变化缓慢，超车事件持续时间远超正常窗口",
        "邻域选择在车辆相对速度快速变化时存在滞后，proposal 与世界模型滚动预测不一致",
        "记录邻域切换频率和 closing-speed 误差，增加超时退出候选"
    ),
    "non_elegant_overtake": (
        "成功超车但横向误差、航向误差或草地暴露不满足 desirable 标准",
        "成功率目标与质量约束目标不一致，单一 scalar score 允许以不优雅轨迹换取进度",
        "将 desirable rate 设为共同主终点，避免只报告 overtake success"
    ),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    rows = []
    with Path(args.input_csv).open("r", encoding="utf-8") as handle:
        rows.extend(csv.DictReader(handle))
    ranked = sorted(rows, key=lambda row: float(row.get("severity_score") or 0.0), reverse=True)
    selected = []
    seen = set()
    for row in ranked:
        modes = set((row.get("active_failure_modes") or "").split(";"))
        for mode, template in TEMPLATES.items():
            if mode in modes and mode not in seen:
                selected.append({
                    "case_id": row.get("case_id"),
                    "benchmark": row.get("benchmark"),
                    "num_agents": row.get("num_agents"),
                    "seed": row.get("seed"),
                    "severity_score": row.get("severity_score"),
                    "failure_mode": mode,
                    "trigger": template[0],
                    "why_selection_or_quality_fails": template[1],
                    "testable_followup": template[2],
                    "summary_file": row.get("summary_file"),
                })
                seen.add(mode)
                break
        if len(selected) >= args.limit:
            break
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fields = list(selected[0]) if selected else ["case_id", "failure_mode"]
    with (out / "requested_failure_analysis.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(selected)
    lines = ["# Requested Failure Analysis", "", "仅基于已保留 failure atlas 行；不新增经验结论。", ""]
    for item in selected:
        lines.extend([
            f"## {item['failure_mode']}: {item['case_id']}",
            f"- 触发条件：{item['trigger']}",
            f"- 失效解释：{item['why_selection_or_quality_fails']}",
            f"- 可验证后续：{item['testable_followup']}",
            f"- 源摘要：{item['summary_file']}",
            "",
        ])
    (out / "requested_failure_analysis.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"selected={len(selected)} output={out}")


if __name__ == "__main__":
    main()
