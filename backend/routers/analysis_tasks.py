from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import zipfile
import tempfile
import os

import models
import schemas
from auth_utils import get_current_active_user, role_required
from database import get_db

router = APIRouter(prefix="/analysis_tasks", tags=["analysis_tasks"])


@router.post("/", response_model=schemas.AnalysisTaskOut)
def create_analysis_task(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """创建分析任务（不上传文件，使用已有提交）"""
    if current_user.role not in ["teacher", "dean"]:
        raise HTTPException(status_code=403, detail="Only teachers can create analysis tasks")

    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    subs = (
        db.query(models.Submission)
        .filter(models.Submission.assignment_id == assignment_id)
        .count()
    )
    if subs < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 submissions to analyze")

    task = models.AnalysisTask(assignment_id=assignment_id, status="pending", total_pairs=0, processed_pairs=0)
    db.add(task)
    db.commit()
    db.refresh(task)

    db.add(
        models.AuditLog(
            actor_user_id=current_user.id,
            action="analysis_task_create",
            target_type="analysis_task",
            target_id=task.id,
            detail=f"assignment={assignment_id}",
        )
    )
    db.commit()

    from assignment_analysis import execute_analysis_task_thread
    import threading
    t = threading.Thread(target=execute_analysis_task_thread, args=(task.id,), daemon=True)
    t.start()

    return task


@router.post("/upload", response_model=schemas.AnalysisTaskOut)
async def create_analysis_task_with_files(
    file: UploadFile = File(...),
    assignment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """上传 JSON 或 ZIP 文件创建分析任务（独立检测，不需要绑定作业）"""
    if current_user.role not in ["teacher", "dean"]:
        raise HTTPException(status_code=403, detail="Only teachers can create analysis tasks")

    # 如果提供了作业ID，验证作业是否存在
    if assignment_id:
        assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

    content = await file.read()
    file_ext = file.filename.split(".")[-1].lower() if file.filename else ""

    file_content = None
    if file_ext == "json":
        try:
            data = json.loads(content)
            file_content = content.decode('utf-8')
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
    elif file_ext == "zip":
        # ZIP文件暂时不支持独立检测，需要保存到临时位置
        file_content = content.hex()  # 保存为十六进制字符串
    else:
        raise HTTPException(status_code=400, detail="Only JSON or ZIP files are supported")

    task = models.AnalysisTask(
        assignment_id=assignment_id,
        status="pending",
        total_pairs=0,
        processed_pairs=0,
        file_content=file_content
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    db.add(
        models.AuditLog(
            actor_user_id=current_user.id,
            action="analysis_task_create_with_files",
            target_type="analysis_task",
            target_id=task.id,
            detail=f"assignment={assignment_id}, file_type={file_ext}",
        )
    )
    db.commit()

    from assignment_analysis import execute_analysis_task_thread
    import threading
    t = threading.Thread(target=execute_analysis_task_thread, args=(task.id,), daemon=True)
    t.start()

    return task


@router.get("/{task_id}", response_model=schemas.AnalysisTaskOut)
def get_analysis_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    task = db.query(models.AnalysisTask).filter(models.AnalysisTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role not in ["teacher", "dean"]:
        raise HTTPException(status_code=403, detail="Only teachers can view analysis tasks")
    return task


@router.get("/latest/{assignment_id}", response_model=schemas.AnalysisTaskOut)
def get_latest_task_for_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if current_user.role not in ["teacher", "dean"]:
        raise HTTPException(status_code=403, detail="Only teachers can view analysis tasks")
    task = (
        db.query(models.AnalysisTask)
        .filter(models.AnalysisTask.assignment_id == assignment_id)
        .order_by(models.AnalysisTask.created_at.desc())
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/cancel")
def cancel_analysis_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if current_user.role not in ["teacher", "dean"]:
        raise HTTPException(status_code=403, detail="Only teachers can cancel tasks")
    task = db.query(models.AnalysisTask).filter(models.AnalysisTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in {"completed", "failed", "cancelled"}:
        return {"ok": True, "status": task.status}
    task.status = "cancelled"
    task.error_message = "已由教师手动取消"
    db.add(
        models.AuditLog(
            actor_user_id=current_user.id,
            action="analysis_task_cancel",
            target_type="analysis_task",
            target_id=task.id,
            detail=f"assignment={task.assignment_id}",
        )
    )
    db.commit()
    return {"ok": True, "status": task.status}


@router.get("/{task_id}/progress", response_model=schemas.AnalysisTaskProgress)
def get_analysis_task_progress(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    limit: int = 50,
):
    """获取分析任务进度和实时比对结果"""
    if current_user.role not in ["teacher", "dean"]:
        raise HTTPException(status_code=403, detail="Only teachers can view task progress")

    task = db.query(models.AnalysisTask).filter(models.AnalysisTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 根据任务ID查询比对结果
    results = (
        db.query(models.ComparisonResult)
        .filter(models.ComparisonResult.task_id == task.id)
        .order_by(models.ComparisonResult.id.desc())
        .limit(limit)
        .all()
    )

    result_items = []
    for r in results:
        details = {}
        try:
            details = json.loads(r.details) if isinstance(r.details, str) else r.details
        except:
            pass
        result_items.append(schemas.AnalysisTaskResultItem(
            submission_a_id=r.submission_id or r.id,
            submission_b_id=r.compared_with_id or r.id,
            similarity_score=r.similarity_score,
            reason=details.get("similarity_analysis", {}).get("reason") if details else None
        ))

    return schemas.AnalysisTaskProgress(
        task_id=task.id,
        assignment_id=task.assignment_id,
        status=task.status,
        total_pairs=task.total_pairs,
        processed_pairs=task.processed_pairs,
        results=result_items
    )
