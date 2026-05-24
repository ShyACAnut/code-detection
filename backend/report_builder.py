from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List


@dataclass(frozen=True)
class ReportPair:
    submission_id: int
    compared_with_id: int
    similarity_score: float
    filter_layer: str
    details_json: str


def _safe_reason(details_json: str) -> str:
    try:
        parsed = json.loads(details_json)
        reason = str(parsed.get("similarity_analysis", {}).get("reason", "")).strip()
        # 检查是否是回退模式
        analysis_mode = parsed.get("analysis_mode") or parsed.get("metadata", {}).get("filter_layer", "")
        if analysis_mode == "fallback" or "传统" in reason or "规则" in reason:
            reason = f"[传统分析] {reason}" if reason else "[传统分析]仅供参考"
        elif analysis_mode == "llm_analysis" or "llm" in analysis_mode.lower():
            reason = f"[LLM分析] {reason}" if reason else "[LLM分析]"
        return reason
    except Exception:
        return "[数据解析失败]"


def _get_analysis_source(details_json: str) -> str:
    """获取分析来源标识"""
    try:
        parsed = json.loads(details_json)
        filter_layer = parsed.get("metadata", {}).get("filter_layer", "unknown")
        if filter_layer == "llm_analysis":
            return "LLM"
        elif filter_layer == "hash_filter":
            return "哈希"
        elif filter_layer == "structure_filter":
            return "结构"
        elif filter_layer == "hybrid_pipeline":
            return "混合"
        elif filter_layer == "agent_fallback":
            return "回退"
        else:
            return filter_layer
    except Exception:
        return "未知"


def build_assignment_report_markdown(
    *,
    assignment_title: str,
    assignment_language: str,
    generated_at: datetime,
    pairs: Iterable[ReportPair],
    high_risk_threshold: float = 80.0,
    top_n: int = 20,
) -> str:
    pairs_list: List[ReportPair] = list(pairs)
    scored = [p for p in pairs_list if p.similarity_score >= 0]
    scored_sorted = sorted(scored, key=lambda p: p.similarity_score, reverse=True)

    high_risk = [p for p in scored_sorted if p.similarity_score >= high_risk_threshold]

    avg = (sum(p.similarity_score for p in scored) / len(scored)) if scored else 0.0
    mx = max((p.similarity_score for p in scored), default=0.0)
    mn = min((p.similarity_score for p in scored), default=0.0)

    def fmt_pair_row(p: ReportPair) -> str:
        reason = _safe_reason(p.details_json)
        reason = reason.replace("\n", " ").strip()
        if len(reason) > 200:
            reason = reason[:200] + "..."
        source = _get_analysis_source(p.details_json)
        return f"| {p.submission_id} | {p.compared_with_id} | {p.similarity_score:.0f} | {source} | {reason} |"

    lines: List[str] = []
    lines.append(f"# 作业相似性检测报告\n")
    lines.append(f"- 作业：**{assignment_title}**")
    lines.append(f"- 语言：**{assignment_language}**")
    lines.append(f"- 生成时间：**{generated_at.strftime('%Y-%m-%d %H:%M:%S')}**\n")

    lines.append("## 概览")
    lines.append(f"- 总比对数：**{len(pairs_list)}**")
    lines.append(f"- 有效评分数：**{len(scored)}**")
    lines.append(f"- 平均相似度：**{avg:.2f}**")
    lines.append(f"- 最高相似度：**{mx:.0f}**")
    lines.append(f"- 最低相似度：**{mn:.0f}**")
    lines.append(f"- 高风险阈值：**{high_risk_threshold:.0f}**")
    lines.append(f"- 高风险对数量：**{len(high_risk)}**\n")

    lines.append(f"## 高风险对 Top {min(top_n, len(high_risk))}")
    lines.append("| 提交A | 提交B | 相似度 | 分析源 | 原因(摘要) |")
    lines.append("|---:|---:|---:|---|---|")
    for p in high_risk[:top_n]:
        lines.append(fmt_pair_row(p))
    if not high_risk:
        lines.append("| - | - | - | - | - |")
    lines.append("")

    lines.append(f"## 全部结果 Top {min(top_n, len(scored_sorted))}")
    lines.append("| 提交A | 提交B | 相似度 | 分析源 | 原因(摘要) |")
    lines.append("|---:|---:|---:|---|---|")
    for p in scored_sorted[:top_n]:
        lines.append(fmt_pair_row(p))
    if not scored_sorted:
        lines.append("| - | - | - | - | - |")
    lines.append("")

    return "\n".join(lines)

