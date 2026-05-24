# backend/routers/reports.py
"""
报告生成路由模块
================

提供各类报告的生成和下载功能，包括：
1. 自查报告生成
2. 学习报告生成
3. 相似度报告导出

注意：这些报告主要用于存档和下载，不涉及敏感信息展示。
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import io
import json

import models
from auth_utils import get_current_active_user, role_required
from database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


def generate_self_check_report(
    code: str,
    language: str,
    similarity_score: float,
    compared_count: int,
    details: str,
    suggestions: list,
) -> str:
    """
    生成自查报告文本

    返回格式化的自查报告内容
    """
    score_level = "高风险" if similarity_score >= 80 else "中等" if similarity_score >= 50 else "低风险"
    score_color = "🔴" if similarity_score >= 80 else "🟡" if similarity_score >= 50 else "🟢"

    report_lines = [
        "=" * 60,
        "                    代码自查报告",
        "=" * 60,
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"编程语言: {language.upper()}",
        f"代码行数: {len(code.split(chr(10)))}",
        "",
        "-" * 60,
        "                    检测结果摘要",
        "-" * 60,
        "",
        f"  {score_color} 相似度评分: {similarity_score:.2f}% - {score_level}",
        f"  📊 比对提交数: {compared_count} 个",
        "",
        "-" * 60,
        "                    检测详情",
        "-" * 60,
        "",
        details,
        "",
        "-" * 60,
        "                    改进建议",
        "-" * 60,
        "",
    ]

    for i, suggestion in enumerate(suggestions, 1):
        report_lines.append(f"  {i}. {suggestion}")

    report_lines.extend([
        "",
        "-" * 60,
        "                    代码片段预览",
        "-" * 60,
        "",
    ])

    lines = code.split('\n')
    preview_lines = lines[:20]
    for i, line in enumerate(preview_lines, 1):
        report_lines.append(f"  {i:3d}: {line[:80]}")
    if len(lines) > 20:
        report_lines.append(f"  ... (还有 {len(lines) - 20} 行)")

    report_lines.extend([
        "",
        "=" * 60,
        "                    报告说明",
        "=" * 60,
        "",
        "  1. 本报告仅供参考，正式提交后教师将进行全面检测",
        "  2. 相似度评分基于与代码库中已有提交的对比",
        "  3. 建议根据改进建议优化代码后再提交",
        "",
        "=" * 60,
        "",
    ])

    return '\n'.join(report_lines)


def generate_learning_report(
    student_name: str,
    teacher_name: str,
    assignment_title: str,
    overall_progress: float,
    strengths: list,
    weaknesses: list,
    recommendations: list,
) -> str:
    """
    生成学习分析报告文本
    """
    report_lines = [
        "=" * 60,
        "                    学习分析报告",
        "=" * 60,
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"学生姓名: {student_name}",
        f"指导教师: {teacher_name}",
        f"作业标题: {assignment_title}",
        "",
        "-" * 60,
        "                    学习进度",
        "-" * 60,
        "",
        f"  总体进度: {overall_progress:.1f}%",
        "",
        "-" * 60,
        "                    优势分析",
        "-" * 60,
        "",
    ]

    for i, strength in enumerate(strengths, 1):
        report_lines.append(f"  ✅ {strength}")

    report_lines.extend([
        "",
        "-" * 60,
        "                    不足之处",
        "-" * 60,
        "",
    ])

    for i, weakness in enumerate(weaknesses, 1):
        report_lines.append(f"  ⚠️ {weakness}")

    report_lines.extend([
        "",
        "-" * 60,
        "                    改进建议",
        "-" * 60,
        "",
    ])

    for i, rec in enumerate(recommendations, 1):
        report_lines.append(f"  {i}. {rec}")

    report_lines.extend([
        "",
        "=" * 60,
        "",
    ])

    return '\n'.join(report_lines)


@router.get("/self-check/{check_id}")
def download_self_check_report(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    下载自查报告

    根据check_id获取自查记录并生成报告
    """
    # 注意：这里需要存储自查记录才能精确获取
    # 目前简化处理，返回通用报告格式

    report_content = f"""代码自查报告
================

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
用户: {current_user.username}

说明: 请在自查页面重新生成报告
"""

    stream = io.StringIO(report_content)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=self_check_report_{check_id}.txt"
        },
    )


@router.post("/self-check/generate")
def generate_self_check_report_api(
    code: str,
    language: str,
    similarity_score: float,
    compared_count: int,
    details: str,
    suggestions: list,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("student")),
):
    """
    生成自查报告

    接收自查数据，生成并返回报告内容
    """
    report = generate_self_check_report(
        code=code,
        language=language,
        similarity_score=similarity_score,
        compared_count=compared_count,
        details=details,
        suggestions=suggestions,
    )

    return {
        "report": report,
        "generated_at": datetime.now().isoformat(),
    }


@router.post("/learning-report/generate")
def generate_learning_report_api(
    student_id: int,
    assignment_id: int,
    overall_progress: float,
    strengths: list,
    weaknesses: list,
    recommendations: list,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("teacher")),
):
    """
    生成学习分析报告

    教师为学生生成学习分析报告
    """
    # 获取学生信息
    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    # 获取作业信息
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")

    report = generate_learning_report(
        student_name=student.username,
        teacher_name=current_user.username,
        assignment_title=assignment.title,
        overall_progress=overall_progress,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
    )

    # 可选：保存报告到数据库
    learning_report = models.LearningReport(
        student_id=student_id,
        teacher_id=current_user.id,
        report_content=json.dumps({
            "overall_progress": overall_progress,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }),
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(learning_report)
    db.commit()

    return {
        "report": report,
        "report_id": learning_report.id,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/learning-report/{report_id}")
def download_learning_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    下载学习分析报告
    """
    report = db.query(models.LearningReport).filter(
        models.LearningReport.id == report_id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 检查权限：学生只能查看自己的报告，教师可以查看自己发送的报告
    if current_user.role == "student" and report.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限查看此报告")
    if current_user.role == "teacher" and report.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限查看此报告")

    content = report.report_content
    if isinstance(content, str):
        content_dict = json.loads(content)
    else:
        content_dict = content

    student = db.query(models.User).filter(models.User.id == report.student_id).first()
    teacher = db.query(models.User).filter(models.User.id == report.teacher_id).first()
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first() if hasattr(report, 'assignment_id') else None

    full_report = generate_learning_report(
        student_name=student.username if student else "未知",
        teacher_name=teacher.username if teacher else "未知",
        assignment_title=assignment.title if assignment else "未知作业",
        overall_progress=content_dict.get("overall_progress", 0),
        strengths=content_dict.get("strengths", []),
        weaknesses=content_dict.get("weaknesses", []),
        recommendations=content_dict.get("recommendations", []),
    )

    stream = io.StringIO(full_report)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=learning_report_{report_id}.txt"
        },
    )


@router.get("/student/{student_id}/reports")
def list_student_reports(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    获取学生的学习报告列表
    """
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="无权限访问")

    reports = db.query(models.LearningReport).filter(
        models.LearningReport.student_id == student_id
    ).order_by(models.LearningReport.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "teacher_id": r.teacher_id,
            "is_read": bool(r.is_read),
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
            "content": json.loads(r.report_content) if isinstance(r.report_content, str) else r.report_content,
        }
        for r in reports
    ]