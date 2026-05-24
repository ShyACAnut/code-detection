"""
统计分析API路由
===============

提供系统统计分析功能，包括：
1. 学生成绩统计和导出
2. 作业完成情况分析
3. 学习行为分析
4. AI生成学习报告
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_
import pandas as pd
import json
import io
import os

from database import get_db
from auth_utils import get_current_active_user
import models
import schemas

router = APIRouter(prefix="/statistics", tags=["statistics"])


class StatisticsService:
    """统计分析服务类"""
    
    @staticmethod
    def get_student_performance_stats(db: Session, student_id: int) -> Dict[str, Any]:
        """获取学生成绩统计"""
        # 获取学生基本信息
        student = db.query(models.User).filter(models.User.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")
        
        # 统计提交情况
        submission_stats = db.query(
            func.count(models.Submission.id).label("total_submissions"),
            func.count(models.Assignment.id.distinct()).label("total_assignments"),
            func.avg(models.ComparisonResult.similarity_score).label("avg_similarity"),
            func.max(models.Submission.submitted_at).label("last_submission")
        ).join(
            models.Assignment, models.Submission.assignment_id == models.Assignment.id
        ).outerjoin(
            models.ComparisonResult, models.Submission.id == models.ComparisonResult.submission_id
        ).filter(
            models.Submission.student_id == student_id
        ).first()
        
        # 获取高风险提交（相似度≥80）
        high_risk_submissions = db.query(
            models.ComparisonResult
        ).join(
            models.Submission, models.ComparisonResult.submission_id == models.Submission.id
        ).filter(
            models.Submission.student_id == student_id,
            models.ComparisonResult.similarity_score >= 80
        ).count()
        
        # 获取最近5次提交的时间分布
        recent_submissions = db.query(
            models.Submission.submitted_at,
            models.Assignment.title
        ).join(
            models.Assignment, models.Submission.assignment_id == models.Assignment.id
        ).filter(
            models.Submission.student_id == student_id
        ).order_by(desc(models.Submission.submitted_at)).limit(5).all()
        
        return {
            "student_info": {
                "id": student.id,
                "username": student.username,
                "email": student.email,
                "role": student.role
            },
            "performance_stats": {
                "total_submissions": submission_stats.total_submissions or 0,
                "total_assignments": submission_stats.total_assignments or 0,
                "avg_similarity": round(submission_stats.avg_similarity or 0, 2),
                "high_risk_count": high_risk_submissions,
                "last_submission": submission_stats.last_submission
            },
            "recent_submissions": [
                {
                    "submitted_at": sub.submitted_at,
                    "assignment_title": sub.title
                }
                for sub in recent_submissions
            ]
        }
    
    @staticmethod
    def get_assignment_statistics(db: Session, assignment_id: int) -> Dict[str, Any]:
        """获取作业统计信息"""
        assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
        if not assignment:
            raise HTTPException(status_code=404, detail="作业不存在")
        
        # 统计提交情况
        submission_stats = db.query(
            func.count(models.Submission.id).label("total_submissions"),
            func.count(models.User.id.distinct()).label("total_students"),
            func.avg(models.ComparisonResult.similarity_score).label("avg_similarity"),
            func.max(models.Submission.submitted_at).label("last_submission")
        ).join(
            models.User, models.Submission.student_id == models.User.id
        ).outerjoin(
            models.ComparisonResult, models.Submission.id == models.ComparisonResult.submission_id
        ).filter(
            models.Submission.assignment_id == assignment_id
        ).first()
        
        # 获取高风险对数量
        high_risk_pairs = db.query(
            models.ComparisonResult
        ).join(
            models.Submission, models.ComparisonResult.submission_id == models.Submission.id
        ).filter(
            models.Submission.assignment_id == assignment_id,
            models.ComparisonResult.similarity_score >= 80
        ).count()
        
        # 获取提交时间分布
        submission_time_dist = db.query(
            func.date(models.Submission.submitted_at).label("submission_date"),
            func.count(models.Submission.id).label("count")
        ).filter(
            models.Submission.assignment_id == assignment_id
        ).group_by(
            func.date(models.Submission.submitted_at)
        ).order_by("submission_date").all()
        
        return {
            "assignment_info": {
                "id": assignment.id,
                "title": assignment.title,
                "language": assignment.language,
                "deadline": assignment.deadline,
                "created_at": assignment.created_at
            },
            "submission_stats": {
                "total_submissions": submission_stats.total_submissions or 0,
                "total_students": submission_stats.total_students or 0,
                "avg_similarity": round(submission_stats.avg_similarity or 0, 2),
                "high_risk_pairs": high_risk_pairs,
                "submission_rate": round((submission_stats.total_students or 0) / 
                                        db.query(models.User).filter(models.User.role == "student").count() * 100, 2)
            },
            "time_distribution": [
                {
                    "date": dist.submission_date,
                    "count": dist.count
                }
                for dist in submission_time_dist
            ]
        }
    
    @staticmethod
    def generate_student_report(db: Session, student_id: int) -> Dict[str, Any]:
        """生成学生学习报告"""
        # 获取学生基本信息
        student = db.query(models.User).filter(models.User.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")
        
        # 获取所有提交记录
        submissions = db.query(
            models.Submission,
            models.Assignment
        ).join(
            models.Assignment, models.Submission.assignment_id == models.Assignment.id
        ).filter(
            models.Submission.student_id == student_id
        ).order_by(desc(models.Submission.submitted_at)).all()
        
        # 获取相似性分析结果
        comparison_results = db.query(
            models.ComparisonResult
        ).join(
            models.Submission, models.ComparisonResult.submission_id == models.Submission.id
        ).filter(
            models.Submission.student_id == student_id
        ).all()
        
        # 计算统计指标
        total_submissions = len(submissions)
        total_assignments = len(set([sub.Assignment.id for sub in submissions]))
        
        # 计算按时提交率
        on_time_submissions = sum(
            1 for sub in submissions 
            if sub.Submission.submitted_at <= sub.Assignment.deadline
        )
        on_time_rate = round(on_time_submissions / total_submissions * 100, 2) if total_submissions > 0 else 0
        
        # 计算高风险提交比例
        high_risk_count = sum(
            1 for result in comparison_results 
            if result.similarity_score >= 80
        )
        high_risk_rate = round(high_risk_count / len(comparison_results) * 100, 2) if comparison_results else 0
        
        # 生成AI分析报告
        ai_analysis = StatisticsService._generate_ai_analysis(
            student, submissions, comparison_results
        )
        
        return {
            "student_info": {
                "username": student.username,
                "email": student.email,
                "total_submissions": total_submissions,
                "total_assignments": total_assignments
            },
            "performance_summary": {
                "on_time_rate": on_time_rate,
                "high_risk_rate": high_risk_rate,
                "avg_similarity": round(
                    sum([r.similarity_score for r in comparison_results]) / len(comparison_results) 
                    if comparison_results else 0, 2
                )
            },
            "submission_details": [
                {
                    "assignment_title": sub.Assignment.title,
                    "language": sub.Assignment.language,
                    "submitted_at": sub.Submission.submitted_at,
                    "deadline": sub.Assignment.deadline,
                    "is_on_time": sub.Submission.submitted_at <= sub.Assignment.deadline
                }
                for sub in submissions
            ],
            "ai_analysis": ai_analysis,
            "generated_at": datetime.utcnow()
        }
    
    @staticmethod
    def _generate_ai_analysis(student, submissions, comparison_results) -> Dict[str, Any]:
        """使用大模型生成学生分析报告"""
        if not submissions:
            return {
                "summary": "该学生尚未提交任何作业",
                "strengths": [],
                "improvements": ["建议学生积极参与作业提交"],
                "recommendations": ["鼓励学生按时完成作业"]
            }

        total_submissions = len(submissions)
        on_time_count = sum(1 for sub in submissions
                           if sub.Submission.submitted_at <= sub.Assignment.deadline)
        high_risk_count = sum(1 for result in comparison_results
                             if result.similarity_score >= 80)
        avg_similarity = sum(r.similarity_score for r in comparison_results) / len(comparison_results) if comparison_results else 0

        assignments_data = []
        for sub in submissions:
            assignments_data.append({
                "title": sub.Assignment.title,
                "language": sub.Assignment.language,
                "deadline": sub.Assignment.deadline.strftime("%Y-%m-%d") if sub.Assignment.deadline else "无",
                "submitted_at": sub.Submission.submitted_at.strftime("%Y-%m-%d %H:%M"),
                "is_on_time": sub.Submission.submitted_at <= sub.Assignment.deadline
            })

        prompt = f"""
你是资深教育分析师。请根据以下学生学习数据，生成一份详细的学习分析报告。

学生信息：{student.username}
统计数据：
- 总提交数：{total_submissions}
- 按时提交数：{on_time_count}
- 按时提交率：{round(on_time_count/total_submissions*100, 1)}%
- 高风险提交数：{high_risk_count}（相似度≥80%）
- 平均相似度：{round(avg_similarity, 2)}%

作业提交详情：
{json.dumps(assignments_data, ensure_ascii=False, indent=2)}

请生成一份JSON格式的分析报告，包含以下字段：
{{
  "summary": "学生学习整体概况描述（2-3句话）",
  "strengths": ["优点1", "优点2", "优点3"],
  "improvements": ["改进建议1", "改进建议2"],
  "recommendations": ["具体行动建议1", "具体行动建议2"]
}}

要求：
1. summary要基于真实数据生成，语言自然流畅
2. strengths和improvements要具体且有针对性
3. recommendations要可操作、可执行
4. 只输出JSON，不要有其他内容
"""

        try:
            from langchain_community.chat_models import ChatZhipuAI
            from dotenv import load_dotenv
            load_dotenv()

            llm = ChatZhipuAI(
                api_key=os.getenv("ZHIPUAI_API_KEY"),
                model="glm-4.5-air",
                temperature=0.3,
                max_tokens=2048
            )

            response = llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    "summary": analysis.get("summary", ""),
                    "strengths": analysis.get("strengths", []),
                    "improvements": analysis.get("improvements", []),
                    "recommendations": analysis.get("recommendations", [])
                }
        except Exception as e:
            print(f"[WARNING] LLM分析失败，使用规则生成: {str(e)[:200]}")

        summary = f"该学生共提交了{total_submissions}次作业，按时提交率为{round(on_time_count/total_submissions*100, 1)}%。"

        if high_risk_count > 0:
            summary += f"检测到{high_risk_count}次高风险相似性提交，建议关注代码原创性。"

        strengths = []
        if on_time_count > total_submissions * 0.8:
            strengths.append("按时交作业的习惯良好")
        if high_risk_count == 0:
            strengths.append("代码原创性较高")
        if total_submissions >= 5:
            strengths.append("学习态度积极")

        improvements = []
        if high_risk_count > 0:
            improvements.append("提高代码原创性，独立完成编程任务")
        if on_time_count < total_submissions * 0.8:
            improvements.append("改善时间管理，避免最后时刻匆忙提交")
        if avg_similarity > 50:
            improvements.append("注意代码风格多样化，避免与他人代码过度相似")

        recommendations = []
        if high_risk_count > 0:
            recommendations.append("建议深入理解算法原理，而非简单模仿")
        if total_submissions < 5:
            recommendations.append("增加编程练习量，多完成作业")
        recommendations.append("定期进行代码自我审查，提高代码质量")

        return {
            "summary": summary,
            "strengths": strengths if strengths else ["学习态度有待观察"],
            "improvements": improvements if improvements else ["建议积极参与编程练习"],
            "recommendations": recommendations
        }
    
    @staticmethod
    def export_student_grades(db: Session, format_type: str = "csv") -> bytes:
        """导出学生成绩数据"""
        # 获取所有学生和他们的提交记录
        students = db.query(models.User).filter(models.User.role == "student").all()
        
        data = []
        for student in students:
            # 获取学生的提交统计
            submission_stats = db.query(
                func.count(models.Submission.id).label("total_submissions"),
                func.count(models.Assignment.id.distinct()).label("completed_assignments"),
                func.avg(models.ComparisonResult.similarity_score).label("avg_similarity")
            ).join(
                models.Assignment, models.Submission.assignment_id == models.Assignment.id
            ).outerjoin(
                models.ComparisonResult, models.Submission.id == models.ComparisonResult.submission_id
            ).filter(
                models.Submission.student_id == student.id
            ).first()
            
            # 获取高风险提交数量
            high_risk_count = db.query(
                models.ComparisonResult
            ).join(
                models.Submission, models.ComparisonResult.submission_id == models.Submission.id
            ).filter(
                models.Submission.student_id == student.id,
                models.ComparisonResult.similarity_score >= 80
            ).count()
            
            data.append({
                "学生ID": student.id,
                "用户名": student.username,
                "邮箱": student.email,
                "总提交数": submission_stats.total_submissions or 0,
                "完成作业数": submission_stats.completed_assignments or 0,
                "平均相似度": round(submission_stats.avg_similarity or 0, 2),
                "高风险提交数": high_risk_count,
                "创建时间": student.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # 转换为指定格式
        if format_type == "csv":
            df = pd.DataFrame(data)
            output = io.BytesIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            return output.getvalue()
        elif format_type == "json":
            return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        else:
            raise HTTPException(status_code=400, detail="不支持的格式类型")


# API路由定义

# 学生报告相关路由 - 需要放在更具体的路由前面
@router.get("/student/reports")
def get_student_reports(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """学生获取自己的学习报告列表"""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="只有学生可以查看自己的学习报告")
    
    reports = db.query(models.LearningReport).filter(
        models.LearningReport.student_id == current_user.id
    ).options(
        joinedload(models.LearningReport.teacher)
    ).order_by(desc(models.LearningReport.created_at)).all()
    
    result = []
    for report in reports:
        try:
            # 安全地解析JSON内容
            report_content = json.loads(report.report_content) if report.report_content else {}
            
            result.append({
                "id": report.id,
                "teacher_name": report.teacher.username,
                "report_content": report_content,
                "is_read": bool(report.is_read),
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "updated_at": report.updated_at.isoformat() if report.updated_at else None
            })
        except json.JSONDecodeError:
            # 如果JSON解析失败，使用空内容
            result.append({
                "id": report.id,
                "teacher_name": report.teacher.username,
                "report_content": {},
                "is_read": bool(report.is_read),
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "updated_at": report.updated_at.isoformat() if report.updated_at else None
            })
    
    return result


@router.get("/student/{student_id}", response_model=Dict[str, Any])
def get_student_statistics(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取学生统计信息"""
    if current_user.role not in ["teacher", "admin", "dean"] and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="权限不足")
    
    return StatisticsService.get_student_performance_stats(db, student_id)


@router.get("/assignment/{assignment_id}", response_model=Dict[str, Any])
def get_assignment_statistics(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取作业统计信息"""
    if current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    return StatisticsService.get_assignment_statistics(db, assignment_id)


@router.get("/student/{student_id}/report", response_model=Dict[str, Any])
def generate_student_report(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """生成学生学习报告"""
    if current_user.role not in ["teacher", "admin", "dean"] and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="权限不足")
    
    return StatisticsService.generate_student_report(db, student_id)





@router.post("/student/{student_id}/report/ai")
def generate_student_ai_report(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """使用大模型生成学生AI分析报告"""
    if current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="权限不足")

    student = db.query(models.User).filter(
        models.User.id == student_id,
        models.User.role == "student"
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    # 获取所有提交记录
    submissions = db.query(
        models.Submission,
        models.Assignment
    ).join(
        models.Assignment, models.Submission.assignment_id == models.Assignment.id
    ).filter(
        models.Submission.student_id == student_id
    ).order_by(models.Submission.submitted_at).all()

    # 获取相似性分析结果
    comparison_results = db.query(
        models.ComparisonResult
    ).join(
        models.Submission, models.ComparisonResult.submission_id == models.Submission.id
    ).filter(
        models.Submission.student_id == student_id
    ).all()

    # 计算统计指标
    total_submissions = len(submissions)
    completed_assignments = len(set([sub.Assignment.id for sub in submissions]))
    
    if total_submissions > 0:
        on_time_count = sum(1 for sub in submissions 
                           if sub.Submission.submitted_at <= sub.Assignment.deadline)
        on_time_rate = round(on_time_count / total_submissions * 100, 1)
    else:
        on_time_rate = 0

    if comparison_results:
        high_risk_count = sum(1 for r in comparison_results if r.similarity_score >= 80)
        high_risk_rate = round(high_risk_count / len(comparison_results) * 100, 1)
    else:
        high_risk_rate = 0

    # 生成AI分析
    ai_analysis = StatisticsService._generate_ai_analysis(student, submissions, comparison_results)

    # 整理详细提交记录
    detailed_records = []
    for sub in submissions:
        # 查找该提交的相似度结果
        similarity = 0
        result = next((r for r in comparison_results 
                      if r.submission_id == sub.Submission.id), None)
        if result:
            similarity = result.similarity_score

        # 判断状态
        status = "待改进"
        if similarity < 50:
            if sub.Submission.submitted_at <= sub.Assignment.deadline:
                status = "优秀"
            else:
                status = "良好"
        elif similarity < 80:
            status = "及格"

        detailed_records.append({
            "assignment_name": sub.Assignment.title,
            "submission_time": sub.Submission.submitted_at.strftime("%Y-%m-%d %H:%M"),
            "status": status,
            "similarity": round(similarity, 1)
        })

    # 生成表现总结
    performance_summary = "表现良好"
    if on_time_rate == 100 and high_risk_rate == 0:
        performance_summary = "表现优秀"
    elif on_time_rate >= 80 and high_risk_rate < 30:
        performance_summary = "表现良好"
    elif on_time_rate >= 60:
        performance_summary = "表现一般"
    else:
        performance_summary = "需要关注"

    # 格式化AI分析报告
    ai_analysis_text = f"""总结：{ai_analysis.get('summary', '')}

优点：
{chr(10).join(f"- {s}" for s in ai_analysis.get('strengths', []))}

改进建议：
{chr(10).join(f"- {s}" for s in ai_analysis.get('improvements', []))}

行动建议：
{chr(10).join(f"- {s}" for s in ai_analysis.get('recommendations', []))}"""

    return {
        "basic_info": {
            "student_name": student.username,
            "total_submissions": total_submissions,
            "completed_assignments": completed_assignments,
            "on_time_rate": on_time_rate,
            "high_risk_rate": high_risk_rate
        },
        "performance_summary": performance_summary,
        "ai_analysis": ai_analysis_text,
        "detailed_records": detailed_records
    }


@router.get("/export/grades")
def export_student_grades(
    format: str = Query("csv", regex="^(csv|json)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """导出学生成绩数据"""
    if current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    data = StatisticsService.export_student_grades(db, format)
    
    if format == "csv":
        return {
            "filename": f"学生成绩_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "content": data,
            "media_type": "text/csv"
        }
    else:
        return {
            "filename": f"学生成绩_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "content": data,
            "media_type": "application/json"
        }


@router.post("/student/{student_id}/report/push")
def push_student_report(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """推送学生学习报告给学生"""
    if current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查学生是否存在
    student = db.query(models.User).filter(
        models.User.id == student_id, 
        models.User.role == "student"
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # 生成学习报告
    report_data = StatisticsService.generate_student_report(db, student_id)
    
    # 转换datetime对象为字符串，确保JSON序列化
    def convert_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: convert_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_datetime(item) for item in obj]
        else:
            return obj
    
    report_data_serializable = convert_datetime(report_data)
    
    # 创建学习报告记录
    report = models.LearningReport(
        student_id=student_id,
        teacher_id=current_user.id,
        report_content=json.dumps(report_data_serializable, ensure_ascii=False, indent=2),
        is_read=0
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # 记录审计日志
    audit_log = models.AuditLog(
        actor_user_id=current_user.id,
        action="push_learning_report",
        target_type="student",
        target_id=student_id,
        detail=f"教师 {current_user.username} 向学生 {student.username} 推送了学习报告"
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "message": "学习报告已成功推送给学生",
        "report_id": report.id,
        "student_name": student.username,
        "pushed_at": report.created_at
    }


@router.put("/student/reports/{report_id}/read")
def mark_report_as_read(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """学生标记报告为已读"""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="只有学生可以标记报告")
    
    report = db.query(models.LearningReport).filter(
        models.LearningReport.id == report_id,
        models.LearningReport.student_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    report.is_read = 1
    db.commit()
    
    return {"message": "报告已标记为已读"}


@router.get("/teacher/reports")
def get_teacher_pushed_reports(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """教师获取自己推送的报告列表"""
    if current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    reports = db.query(models.LearningReport).filter(
        models.LearningReport.teacher_id == current_user.id
    ).options(
        joinedload(models.LearningReport.student)
    ).order_by(desc(models.LearningReport.created_at)).all()
    
    result = []
    for report in reports:
        try:
            # 安全地解析JSON内容
            report_content = json.loads(report.report_content) if report.report_content else {}
            
            result.append({
                "id": report.id,
                "student_name": report.student.username,
                "student_email": report.student.email,
                "report_content": report_content,
                "is_read": bool(report.is_read),
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "updated_at": report.updated_at.isoformat() if report.updated_at else None
            })
        except json.JSONDecodeError:
            # 如果JSON解析失败，使用空内容
            result.append({
                "id": report.id,
                "student_name": report.student.username,
                "student_email": report.student.email,
                "report_content": {},
                "is_read": bool(report.is_read),
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "updated_at": report.updated_at.isoformat() if report.updated_at else None
            })
    
    return result


@router.get("/students", response_model=List[Dict[str, Any]])
def get_students_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取学生列表（教师、管理员、主任权限）"""
    if current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    students = db.query(models.User).filter(models.User.role == "student").all()
    
    return [
        {
            "id": student.id,
            "username": student.username,
            "email": student.email,
            "role": student.role,
            "created_at": student.created_at
        }
        for student in students
    ]


@router.get("/overview", response_model=Dict[str, Any])
def get_system_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取系统概览统计"""
    if current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 用户统计
    user_stats = db.query(
        models.User.role,
        func.count(models.User.id).label("count")
    ).group_by(models.User.role).all()
    
    # 作业统计
    assignment_stats = db.query(
        func.count(models.Assignment.id).label("total_assignments"),
        func.count(models.Submission.id.distinct()).label("total_submissions")
    ).first()
    
    # 相似性统计
    similarity_stats = db.query(
        func.avg(models.ComparisonResult.similarity_score).label("avg_similarity"),
        func.count(models.ComparisonResult.id).label("total_comparisons")
    ).first()
    
    return {
        "user_statistics": {
            role: count for role, count in user_stats
        },
        "assignment_statistics": {
            "total_assignments": assignment_stats.total_assignments or 0,
            "total_submissions": assignment_stats.total_submissions or 0,
            "submission_rate": round(
                (assignment_stats.total_submissions or 0) / 
                (db.query(models.User).filter(models.User.role == "student").count() * 
                 (assignment_stats.total_assignments or 1)) * 100, 2
            )
        },
        "similarity_statistics": {
            "avg_similarity": round(similarity_stats.avg_similarity or 0, 2),
            "total_comparisons": similarity_stats.total_comparisons or 0
        },
        "generated_at": datetime.utcnow()
    }