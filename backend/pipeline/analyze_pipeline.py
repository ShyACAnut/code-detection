from __future__ import annotations

import os
import numpy as np
from dataclasses import dataclass
from typing import Optional

from detectors.syntax_detector import syntax_similarity
from detectors.semantic_detector import semantic_similarity

VECTOR_PREFILTER_THRESHOLD = 0.3  # 从0.15提高到0.3，跳过更多低相似度的对
VECTOR_MIN_THRESHOLD = 0.05

_agent = None


def _get_code_agent():
    global _agent
    if _agent is None:
        try:
            from agent_provider import get_code_detection_agent
            _agent = get_code_detection_agent()
        except Exception as e:
            print(f"[向量预筛选] 初始化向量库失败: {e}")
            _agent = False
    return _agent if _agent else None


def _vector_prefilter(code_a: str, code_b: str, language: str) -> Optional[float]:
    """
    向量库预筛选
    使用代码向量化技术快速判断两段代码是否可能相似

    返回值:
        None: 向量库不可用
        float: 向量相似度分数 (0.0 - 1.0)
            - < 0.05: 极低相似度，直接判定为不相似
            - 0.05 - 0.3: 低相似度，跳过LLM深度分析
            - 0.3 - 0.6: 中等相似度，需要LLM分析
            - > 0.6: 高相似度，需要LLM深度分析确认
    """
    agent = _get_code_agent()
    if agent is None:
        return None

    try:
        if not hasattr(agent, 'vectorstore') or agent.vectorstore is None:
            return None

        vector_count = agent.vectorstore.index.ntotal if hasattr(agent.vectorstore, 'index') else 0
        if vector_count == 0:
            print("[向量预筛选] 向量库为空，跳过预筛选")
            return None

        combined_code = f"{code_a}\n---\n{code_b}"
        docs_and_scores = agent.vectorstore.similarity_search_with_score(combined_code, k=5)

        if not docs_and_scores:
            return None

        distances = [score for _, score in docs_and_scores]
        avg_distance = np.mean(distances)

        vector_sim = max(0.0, min(1.0, 1.0 - avg_distance / 100.0))

        return vector_sim

    except Exception as e:
        print(f"[向量预筛选] 向量检索失败: {e}")
        return None


@dataclass
class PipelineWeights:
    syntax_weight: float = 0.4
    semantic_weight: float = 0.6


def analyze_pair(code_a: str, code_b: str, language: str, weights: PipelineWeights | None = None, skip_vector_filter: bool = False) -> dict:
    w = weights or PipelineWeights()

    vector_score = None
    if not skip_vector_filter:
        vector_score = _vector_prefilter(code_a, code_b, language)

    if vector_score is not None and vector_score < VECTOR_MIN_THRESHOLD:
        return {
            "final_score": round(vector_score * 100, 2),
            "syntax_score": 0.0,
            "semantic_score": round(vector_score * 100, 2),
            "reason": "向量库预筛选：代码相似度极低，跳过深度分析",
            "matched_lines": [],
            "filter_layer": "vector_prefilter",
            "vector_score": round(vector_score, 4),
            "metadata": {
                "language": language,
                "weights": {"syntax": w.syntax_weight, "semantic": w.semantic_weight, "vector": 1.0},
                "prefilter_skipped": skip_vector_filter,
            },
            "raw": {"syntax": {}, "semantic": {}, "vector_prefilter": vector_score},
        }

    syntax = syntax_similarity(code_a, code_b, language=language)
    semantic = semantic_similarity(code_a, code_b, language)

    syn = max(0.0, float(syntax.get("score", 0.0)))
    sem = max(0.0, float(semantic.get("score", 0.0)))

    if vector_score is not None and vector_score > VECTOR_PREFILTER_THRESHOLD:
        adjusted_sem = sem * 0.8 + vector_score * 100 * 0.2
    else:
        adjusted_sem = sem

    final = round((w.syntax_weight * syn + w.semantic_weight * adjusted_sem), 2)
    final = max(0.0, min(100.0, final))

    return {
        "final_score": final,
        "syntax_score": syn,
        "semantic_score": round(adjusted_sem, 2),
        "reason": semantic.get("reason") or "融合语法与语义评分",
        "matched_lines": syntax.get("matched_lines", []),
        "filter_layer": "hybrid_pipeline" if vector_score is None else f"hybrid_pipeline_with_vector_{'high' if vector_score and vector_score > VECTOR_PREFILTER_THRESHOLD else 'low'}",
        "vector_score": round(vector_score, 4) if vector_score is not None else None,
        "metadata": {
            "language": language,
            "weights": {"syntax": w.syntax_weight, "semantic": w.semantic_weight},
            "prefilter_skipped": skip_vector_filter,
        },
        "raw": {"syntax": syntax, "semantic": semantic.get("raw", {}), "vector_prefilter": vector_score},
    }