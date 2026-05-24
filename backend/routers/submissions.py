# backend/routers/submissions.py
from datetime import datetime
from pathlib import Path
import os
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional

import models
import schemas
from auth_utils import get_current_active_user
from database import get_db
from indexing.incremental_index import upsert_code_index_entry

router = APIRouter(prefix="/submissions", tags=["submissions"])


def _utcnow_naive():
    return datetime.utcnow()


def _validate_deadline(assignment: models.Assignment):
    if _utcnow_naive() > assignment.deadline:
        raise HTTPException(status_code=403, detail="作业已过截止时间，无法提交")


async def _parse_and_store_file(
    *,
    assignment_id: int,
    student_id: int,
    file: UploadFile,
) -> tuple[str, str]:
    suffix = Path(file.filename or "").suffix.lower()
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="文件为空")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="仅支持 UTF-8 编码文本文件")

    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", f"a_{assignment_id}"))
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"stu_{student_id}_{int(datetime.utcnow().timestamp())}{suffix}"
    abs_path = os.path.join(upload_dir, filename)
    with open(abs_path, "wb") as f:
        f.write(raw)
    return text, abs_path


def _upsert_submission(
    *,
    db: Session,
    assignment: models.Assignment,
    student_id: int,
    code: str,
    file_path: str | None,
) -> models.Submission:
    existing = (
        db.query(models.Submission)
        .filter(
            models.Submission.assignment_id == assignment.id,
            models.Submission.student_id == student_id,
        )
        .order_by(models.Submission.submitted_at.desc())
        .first()
    )

    now = _utcnow_naive()
    if existing:
        # 保留每次修改快照
        db.add(
            models.SubmissionRevision(
                submission_id=existing.id,
                code=existing.code or "",
                file_path=existing.file_path,
                edited_at=now,
            )
        )
        existing.code = code
        existing.file_path = file_path
        existing.submitted_at = now
        db.commit()
        db.refresh(existing)
        upsert_code_index_entry(db, existing, assignment.language)
        db.add(
            models.AuditLog(
                actor_user_id=student_id,
                action="submission_overwrite",
                target_type="submission",
                target_id=existing.id,
                detail=f"assignment={assignment.id}",
            )
        )
        db.commit()
        return existing

    db_submission = models.Submission(
        student_id=student_id,
        assignment_id=assignment.id,
        code=code,
        file_path=file_path,
        submitted_at=now,
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    upsert_code_index_entry(db, db_submission, assignment.language)
    db.add(
        models.AuditLog(
            actor_user_id=student_id,
            action="submission_create",
            target_type="submission",
            target_id=db_submission.id,
            detail=f"assignment={assignment.id}",
        )
    )
    db.commit()
    return db_submission


# 学生提交作业
@router.post("/", response_model=schemas.Submission)
def create_submission(
    submission: schemas.SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can submit")

    assignment = db.query(models.Assignment).filter(models.Assignment.id == submission.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    _validate_deadline(assignment)
    return _upsert_submission(
        db=db,
        assignment=assignment,
        student_id=current_user.id,
        code=submission.code,
        file_path=None,
    )


@router.post("/upload", response_model=schemas.Submission)
async def upload_submission_file(
    assignment_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can submit")

    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _validate_deadline(assignment)

    suffix = Path(file.filename or "").suffix.lower()
    allow_map = {
        "python": [".py"],
        "java": [".java"],
        "javascript": [".js"],
        "c": [".c", ".h"],
        "cpp": [".cpp", ".cc", ".cxx", ".h"],
        "csharp": [".cs"],
        "go": [".go"],
    }
    allow = allow_map.get((assignment.language or "").lower(), [".py", ".java", ".js", ".c", ".cpp", ".cs", ".go"])
    if suffix not in allow:
        raise HTTPException(status_code=400, detail=f"文件类型不匹配，{assignment.language} 作业仅支持: {', '.join(allow)}")
    text, abs_path = await _parse_and_store_file(
        assignment_id=assignment_id,
        student_id=current_user.id,
        file=file,
    )

    return _upsert_submission(
        db=db,
        assignment=assignment,
        student_id=current_user.id,
        code=text,
        file_path=abs_path,
    )


@router.get("/{assignment_id}/latest", response_model=schemas.Submission)
def get_latest_submission_for_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can query latest submission here")

    latest = (
        db.query(models.Submission)
        .filter(
            models.Submission.assignment_id == assignment_id,
            models.Submission.student_id == current_user.id,
        )
        .order_by(models.Submission.submitted_at.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No previous submission")
    return latest


@router.post("/{assignment_id}", response_model=schemas.Submission)
async def upload_or_update_submission(
    assignment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    学生端标准接口：
    - 选择文件后点击提交，再调用此接口
    - 截止前多次提交会覆盖旧提交
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can submit")

    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _validate_deadline(assignment)

    suffix = Path(file.filename or "").suffix.lower()
    allow_map = {
        "python": [".py"],
        "java": [".java"],
        "javascript": [".js"],
        "c": [".c", ".h"],
        "cpp": [".cpp", ".cc", ".cxx", ".h"],
        "csharp": [".cs"],
        "go": [".go"],
    }
    allow = allow_map.get((assignment.language or "").lower(), [".py", ".java", ".js", ".c", ".cpp", ".cs", ".go"])
    if suffix not in allow:
        raise HTTPException(status_code=400, detail=f"文件类型不匹配，{assignment.language} 作业仅支持: {', '.join(allow)}")

    text, abs_path = await _parse_and_store_file(
        assignment_id=assignment_id,
        student_id=current_user.id,
        file=file,
    )
    return _upsert_submission(
        db=db,
        assignment=assignment,
        student_id=current_user.id,
        code=text,
        file_path=abs_path,
    )


# 学生查看自己的提交历史（含作业标题）
@router.get("/", response_model=List[schemas.SubmissionWithAssignmentTitle])
def get_my_submissions(
    assignment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    q = (
        db.query(models.Submission, models.Assignment.title)
        .join(models.Assignment, models.Submission.assignment_id == models.Assignment.id)
        .filter(models.Submission.student_id == current_user.id)
    )
    if assignment_id:
        q = q.filter(models.Submission.assignment_id == assignment_id)

    rows = q.order_by(models.Submission.submitted_at.desc()).all()
    out: List[schemas.SubmissionWithAssignmentTitle] = []
    for s, title in rows:
        related_results = (
            db.query(models.ComparisonResult)
            .filter(
                (models.ComparisonResult.submission_id == s.id)
                | (models.ComparisonResult.compared_with_id == s.id)
            )
            .all()
        )
        if related_results:
            valid = [r for r in related_results if r.similarity_score >= 0]
            best = max(valid, key=lambda x: x.similarity_score) if valid else None
            status = "已完成"
            highest_similarity = float(best.similarity_score) if best else None
            reason = None
            if best:
                try:
                    parsed = json.loads(best.details or "{}")
                    reason = parsed.get("similarity_analysis", {}).get("reason")
                except Exception:
                    reason = None
        else:
            latest_task = (
                db.query(models.AnalysisTask)
                .filter(models.AnalysisTask.assignment_id == s.assignment_id)
                .order_by(models.AnalysisTask.created_at.desc())
                .first()
            )
            if latest_task and latest_task.status in {"pending", "running"}:
                status = "检测中"
            else:
                status = "待检测"
            highest_similarity = None
            reason = None

        out.append(
            schemas.SubmissionWithAssignmentTitle(
                id=s.id,
                student_id=s.student_id,
                assignment_id=s.assignment_id,
                code=s.code,
                submitted_at=s.submitted_at,
                assignment_title=title,
                analysis_status=status,
                highest_similarity=highest_similarity,
                analysis_reason=reason,
            )
        )
    return out


# 获取单次提交详情（含权限检查）
@router.get("/{submission_id}", response_model=schemas.Submission)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.student_id != current_user.id and current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not allowed")
    return submission


# 获取提交的评分信息
@router.get("/{submission_id}/score", response_model=Optional[schemas.SubmissionScoreOut])
def get_submission_score(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # 学生只能查看自己的评分，教师可以查看所有评分
    if submission.student_id != current_user.id and current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not allowed")
    
    score = db.query(models.SubmissionScore).filter(models.SubmissionScore.submission_id == submission_id).first()
    if not score:
        # 如果没有评分记录，返回 None 而不是 404 错误
        return None
    
    teacher = db.query(models.User).filter(models.User.id == score.teacher_id).first()
    
    return schemas.SubmissionScoreOut(
        id=score.id,
        submission_id=score.submission_id,
        teacher_id=score.teacher_id,
        teacher_name=teacher.username if teacher else None,
        overall_score=score.overall_score,
        teacher_comments=score.teacher_comments,
        criteria_scores=score.criteria_scores,
        created_at=score.created_at,
        updated_at=score.updated_at,
    )


# 获取某次提交的比对结果列表（学生端匿名）
@router.get("/{submission_id}/results", response_model=List[schemas.ComparisonResultPublic])
def get_comparison_results(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.student_id != current_user.id and current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not allowed")

    results = (
        db.query(models.ComparisonResult)
        .filter(
            (models.ComparisonResult.submission_id == submission_id)
            | (models.ComparisonResult.compared_with_id == submission_id)
        )
        .all()
    )

    if current_user.role == "teacher":
        return [
            schemas.ComparisonResultPublic(
                id=r.id,
                submission_id=r.submission_id,
                compared_with_id=r.compared_with_id,
                peer_label=None,
                similarity_score=r.similarity_score,
                filter_layer=r.filter_layer,
                details=r.details,
                created_at=r.created_at,
            )
            for r in results
        ]

    return [
        schemas.ComparisonResultPublic(
            id=r.id,
            submission_id=r.submission_id,
            compared_with_id=None,
            peer_label="其他同学",
            similarity_score=r.similarity_score,
            filter_layer=r.filter_layer,
            details=r.details,
            created_at=r.created_at,
        )
        for r in results
    ]


@router.get("/{submission_id}/history", response_model=List[schemas.SubmissionRevision])
def get_submission_history(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.student_id != current_user.id and current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not allowed")

    return (
        db.query(models.SubmissionRevision)
        .filter(models.SubmissionRevision.submission_id == submission_id)
        .order_by(models.SubmissionRevision.edited_at.desc())
        .all()
    )


# ============================================================================
# 评分相关 API
# ============================================================================

@router.post("/{submission_id}/score", response_model=schemas.SubmissionScoreOut)
def create_or_update_score(
    submission_id: int,
    score_data: schemas.SubmissionScoreCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    教师为学生提交创建或更新评分
    """
    if current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if score_data.overall_score < 0 or score_data.overall_score > 100:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 100")
    
    existing_score = (
        db.query(models.SubmissionScore)
        .filter(models.SubmissionScore.submission_id == submission_id)
        .first()
    )
    
    if existing_score:
        existing_score.overall_score = score_data.overall_score
        existing_score.teacher_comments = score_data.teacher_comments
        existing_score.criteria_scores = json.dumps(score_data.criteria_scores) if score_data.criteria_scores else None
        existing_score.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_score)
        score = existing_score
    else:
        new_score = models.SubmissionScore(
            submission_id=submission_id,
            teacher_id=current_user.id,
            overall_score=score_data.overall_score,
            teacher_comments=score_data.teacher_comments,
            criteria_scores=json.dumps(score_data.criteria_scores) if score_data.criteria_scores else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_score)
        db.commit()
        db.refresh(new_score)
        score = new_score
    
    criteria_scores = json.loads(score.criteria_scores) if score.criteria_scores else None
    
    return schemas.SubmissionScoreOut(
        id=score.id,
        submission_id=score.submission_id,
        teacher_id=score.teacher_id,
        teacher_name=current_user.username,
        overall_score=score.overall_score,
        teacher_comments=score.teacher_comments,
        criteria_scores=criteria_scores,
        created_at=score.created_at,
        updated_at=score.updated_at,
    )


@router.get("/{submission_id}/score", response_model=schemas.SubmissionScoreOut)
def get_submission_score(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    获取指定提交的评分
    """
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.student_id != current_user.id and current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    score = (
        db.query(models.SubmissionScore)
        .filter(models.SubmissionScore.submission_id == submission_id)
        .first()
    )
    
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    
    teacher = db.query(models.User).filter(models.User.id == score.teacher_id).first()
    criteria_scores = json.loads(score.criteria_scores) if score.criteria_scores else None
    
    return schemas.SubmissionScoreOut(
        id=score.id,
        submission_id=score.submission_id,
        teacher_id=score.teacher_id,
        teacher_name=teacher.username if teacher else None,
        overall_score=score.overall_score,
        teacher_comments=score.teacher_comments,
        criteria_scores=criteria_scores,
        created_at=score.created_at,
        updated_at=score.updated_at,
    )


@router.get("/{submission_id}/with-score", response_model=schemas.SubmissionWithScore)
def get_submission_with_score(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    获取指定提交的详情（包含评分）
    """
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.student_id != current_user.id and current_user.role not in ["teacher", "admin", "dean"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    student = db.query(models.User).filter(models.User.id == submission.student_id).first()
    score = (
        db.query(models.SubmissionScore)
        .filter(models.SubmissionScore.submission_id == submission_id)
        .first()
    )
    
    score_out = None
    if score:
        teacher = db.query(models.User).filter(models.User.id == score.teacher_id).first()
        criteria_scores = json.loads(score.criteria_scores) if score.criteria_scores else None
        score_out = schemas.SubmissionScoreOut(
            id=score.id,
            submission_id=score.submission_id,
            teacher_id=score.teacher_id,
            teacher_name=teacher.username if teacher else None,
            overall_score=score.overall_score,
            teacher_comments=score.teacher_comments,
            criteria_scores=criteria_scores,
            created_at=score.created_at,
            updated_at=score.updated_at,
        )
    
    return schemas.SubmissionWithScore(
        id=submission.id,
        student_name=student.username if student else "Unknown",
        code=submission.code or "",
        submitted_at=submission.submitted_at,
        score=score_out,
    )
