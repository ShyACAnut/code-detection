from __future__ import annotations

from functools import lru_cache

from code_agent import CodeDetectionAgent


@lru_cache(maxsize=1)
def get_code_detection_agent() -> CodeDetectionAgent:
    return CodeDetectionAgent()

