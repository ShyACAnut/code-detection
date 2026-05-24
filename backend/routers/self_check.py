# backend/routers/self_check.py
"""
代码自查路由模块
================

提供学生代码自查功能的API端点，允许学生在提交作业前检查代码相似度。

主要功能：
1. 接收学生提交的代码
2. 与代码库中的代码进行比对
3. 返回相似度评分和改进建议
4. 不保存检测记录，保护学生隐私

注意：自查功能仅供参考，正式提交后教师将进行全面检测。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

import models
import schemas
from auth_utils import get_current_active_user, role_required
from database import get_db
from detectors.syntax_detector import syntax_similarity
from detectors.semantic_detector import semantic_similarity

router = APIRouter(prefix="/self-check", tags=["self-check"])


class SelfCheckRequest(BaseModel):
    """
    代码自查请求模型
    """
    code: str
    language: Optional[str] = "python"


class SelfCheckResponse(BaseModel):
    """
    代码自查响应模型
    """
    similarity_score: float
    compared_with_count: int
    details: str
    suggestions: list[str]


@router.post("/", response_model=SelfCheckResponse)
def self_check(
    request: SelfCheckRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("student")),
):
    """
    学生代码自查接口
    
    学生可以在提交作业前检查自己的代码与已有提交的相似度。
    
    参数：
    - code: 要检测的代码内容
    - language: 编程语言（可选，默认python）
    
    返回：
    - similarity_score: 最高相似度评分（0-100）
    - compared_with_count: 比对的提交数量
    - details: 检测详情描述
    - suggestions: 改进建议列表
    """
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="请提供代码内容")
    
    # 获取所有公开的代码提交作为比对库
    submissions = db.query(models.Submission).all()
    
    if not submissions:
        return {
            "similarity_score": 0.0,
            "compared_with_count": 0,
            "details": "当前代码库中暂无提交记录，无法进行比对。",
            "suggestions": ["代码库为空，请稍后再试。"]
        }
    
    max_similarity = 0.0
    compared_count = 0
    
    # 与每个提交进行比对
    for submission in submissions:
        if submission.code and submission.id != current_user.id:
            compared_count += 1
            try:
                # 使用语法检测
                syntax_result = syntax_similarity(request.code, submission.code, request.language)
                syntax_score = syntax_result.get('score', 0)
                
                # 使用语义检测（如果可用）
                semantic_score = 0
                try:
                    semantic_result = semantic_similarity(request.code, submission.code, request.language)
                    semantic_score = semantic_result.get('score', 0)
                except Exception:
                    # 语义检测失败时只使用语法检测
                    pass
                
                # 综合评分
                combined_score = (syntax_score * 0.4) + (semantic_score * 0.6)
                if combined_score > max_similarity:
                    max_similarity = combined_score
            except Exception:
                continue
    
    # 生成建议
    suggestions = generate_suggestions(max_similarity)
    
    return {
        "similarity_score": round(max_similarity, 2),
        "compared_with_count": compared_count,
        "details": generate_details(max_similarity, compared_count),
        "suggestions": suggestions
    }


def generate_details(similarity: float, count: int) -> str:
    """
    根据相似度生成检测详情描述
    """
    if similarity >= 80:
        return f"您的代码与代码库中已有提交的最高相似度为 {similarity:.1f}%，存在较高的抄袭风险。建议您重新审视代码，确保代码的原创性。"
    elif similarity >= 50:
        return f"您的代码与代码库中已有提交的最高相似度为 {similarity:.1f}%，存在一定的相似性。建议检查是否有不必要的代码重复。"
    elif similarity > 0:
        return f"您的代码与代码库中已有提交的最高相似度为 {similarity:.1f}%，相似度较低。"
    else:
        return f"未找到显著相似的代码，共比对了 {count} 个提交。"


def generate_suggestions(similarity: float) -> list[str]:
    """
    根据相似度生成改进建议
    """
    suggestions = []
    
    if similarity >= 80:
        suggestions = [
            "建议重新编写核心算法和逻辑",
            "使用不同的变量命名和代码结构",
            "添加更多的注释和文档说明",
            "考虑使用不同的实现方法"
        ]
    elif similarity >= 50:
        suggestions = [
            "检查代码中是否存在不必要的重复",
            "尝试重构部分代码逻辑",
            "添加更多个性化的实现细节",
            "确保代码注释完整且有意义"
        ]
    else:
        suggestions = [
            "代码相似度较低，继续保持良好的编码习惯",
            "确保代码注释清晰完整",
            "可以考虑添加更多的错误处理"
        ]
    
    return suggestions
