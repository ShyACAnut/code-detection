from __future__ import annotations

import json
import os
import re
import time

from agent_provider import get_code_detection_agent
from langchain_community.chat_models import ChatZhipuAI


def _extract_json(text: str) -> dict:
    t = text.strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r"\{.*\}", t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def _llm_semantic_for_any_language(code_a: str, code_b: str, language: str) -> dict:
    """
    使用增强重试机制的LLM语义分析
    """
    llm = ChatZhipuAI(
        api_key=os.getenv("ZHIPUAI_API_KEY"),
        model="glm-4.5-air",
        temperature=0.1,
        max_tokens=4096,
    )
    prompt = f"""
你是资深代码审查专家。请分析两段{language}代码在"功能与逻辑"上的相似度。
忽略变量名、注释、格式差异，重点看算法意图、控制流程、数据处理过程。
只输出一个 JSON 对象，字段固定为：
{{
  "score": 0-100 的整数,
  "reason": "一句话理由",
  "function_summary": "两段代码的功能概括"
}}

代码A:
```{language}
{code_a}
```

代码B:
```{language}
{code_b}
```
"""
    
    # 使用增强的重试机制
    last_err = None
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            # 添加请求间隔控制
            if attempt > 0:
                wait_time = min(2 ** (attempt + 1) + attempt, 30)
                print(f"[语义检测器] 等待{wait_time}秒后重试... (尝试 {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            
            out = llm.invoke(prompt)
            text = out.content if hasattr(out, "content") else str(out)
            obj = _extract_json(text if isinstance(text, str) else str(text))
            if not obj:
                raise ValueError("LLM返回非JSON格式")
            score = float(obj.get("score", -1))
            reason = str(obj.get("reason", "")).strip()
            return {
                "score": score,
                "reason": reason or "LLM 语义分析完成",
                "raw": {"similarity_analysis": obj, "metadata": {"filter_layer": "llm_analysis", "language": language}},
            }
        except Exception as e:
            last_err = e
            error_str = str(e).lower()
            
            # 检查是否是可重试错误
            retryable = False
            retryable_codes = [429, 500, 502, 503, 504]
            
            # 检查错误码
            if any(str(code) in error_str for code in retryable_codes):
                retryable = True
            if 'rate limit' in error_str or 'too many requests' in error_str:
                retryable = True
            if 'timeout' in error_str or 'gateway' in error_str:
                retryable = True
            
            if not retryable or attempt == max_retries - 1:
                # 不可重试错误或达到最大重试次数
                print(f"[语义检测器] LLM分析失败: {str(e)[:200]}")
                # 使用传统分析方法作为回退
                return _traditional_semantic_analysis(code_a, code_b, language)
    
    # 如果所有重试都失败，使用传统分析方法
    return _traditional_semantic_analysis(code_a, code_b, language)

def _traditional_semantic_analysis(code_a: str, code_b: str, language: str) -> dict:
    """
    传统语义分析方法（回退方案）
    注意：此方法仅在大模型不可用时作为备选使用
    """
    # 基于代码长度、结构等简单特征进行分析
    len_a = len(code_a)
    len_b = len(code_b)
    len_similarity = 1.0 - abs(len_a - len_b) / max(len_a, len_b, 1)

    # 计算行数相似度
    lines_a = len([line for line in code_a.split('\n') if line.strip()])
    lines_b = len([line for line in code_b.split('\n') if line.strip()])
    lines_similarity = 1.0 - abs(lines_a - lines_b) / max(lines_a, lines_b, 1)

    # 综合评分
    score = (len_similarity * 0.3 + lines_similarity * 0.7) * 100

    return {
        "score": max(0, min(100, score)),
        "reason": "【注意】大模型分析不可用，此为传统规则分析结果，仅供参考",
        "analysis_mode": "fallback",
        "raw": {"similarity_analysis": {"score": score}, "metadata": {"filter_layer": "traditional_analysis"}}
    }


def semantic_similarity(code_a: str, code_b: str, language: str) -> dict:
    lang = (language or "").lower()
    if lang in {"python", "java", "go"}:
        agent = get_code_detection_agent()
        result = agent.analyze_code_similarity(code_a or "", code_b or "", lang)
        if "error" in result:
            return {"score": -1.0, "reason": result["error"], "raw": result}
        score = float(result.get("similarity_analysis", {}).get("score", -1))
        reason = result.get("similarity_analysis", {}).get("reason", "")
        return {"score": score, "reason": reason, "raw": result}

    # javascript/c/cpp/csharp 等语言：同样走 LLM 语义分析
    return _llm_semantic_for_any_language(code_a or "", code_b or "", lang or "code")
