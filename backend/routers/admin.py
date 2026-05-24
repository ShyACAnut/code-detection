from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi.responses import PlainTextResponse

import models
import schemas
from auth_utils import get_password_hash, role_required
from database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

# 文件扩展名到语言的映射
LANGUAGE_EXTENSIONS = {
    '.py': 'python',
    '.java': 'java',
    '.js': 'javascript',
    '.go': 'go',
    '.cpp': 'cpp',
    '.c': 'c',
    '.cs': 'csharp',
}


def get_language_from_filename(filename: str) -> str:
    """
    根据文件名推断编程语言
    """
    import os
    _, ext = os.path.splitext(filename)
    return LANGUAGE_EXTENSIONS.get(ext.lower(), 'python')


def _get_or_create_config(db: Session) -> models.SystemConfig:
    row = db.query(models.SystemConfig).filter(models.SystemConfig.id == 1).first()
    if not row:
        row = models.SystemConfig(id=1, similarity_threshold=80.0, llm_model_name="glm-4.7")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/users", response_model=List[schemas.AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(role_required("admin")),
):
    users = db.query(models.User).order_by(models.User.id.asc()).all()
    return users


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    body: schemas.ResetPasswordBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("admin")),
):
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.hashed_password = get_password_hash(body.new_password)
    db.commit()
    return {"ok": True}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("admin")),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    # 删除该用户相关提交与比对（按依赖顺序）
    sub_ids = [s.id for s in db.query(models.Submission.id).filter(models.Submission.student_id == user_id).all()]
    if sub_ids:
        db.query(models.ComparisonResult).filter(
            (models.ComparisonResult.submission_id.in_(sub_ids))
            | (models.ComparisonResult.compared_with_id.in_(sub_ids))
        ).delete(synchronize_session=False)
        db.query(models.Submission).filter(models.Submission.id.in_(sub_ids)).delete(synchronize_session=False)

    aids = [a.id for a in db.query(models.Assignment.id).filter(models.Assignment.created_by == user_id).all()]
    if aids:
        for aid in aids:
            sids = [s.id for s in db.query(models.Submission.id).filter(models.Submission.assignment_id == aid).all()]
            if sids:
                db.query(models.ComparisonResult).filter(
                    (models.ComparisonResult.submission_id.in_(sids))
                    | (models.ComparisonResult.compared_with_id.in_(sids))
                ).delete(synchronize_session=False)
                db.query(models.Submission).filter(models.Submission.id.in_(sids)).delete(synchronize_session=False)
            db.query(models.AnalysisTask).filter(models.AnalysisTask.assignment_id == aid).delete(synchronize_session=False)
        db.query(models.Assignment).filter(models.Assignment.id.in_(aids)).delete(synchronize_session=False)

    db.query(models.User).filter(models.User.id == user_id).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}


@router.get("/stats", response_model=schemas.AdminStatsOut)
def admin_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(role_required("admin")),
):
    user_count = db.query(func.count(models.User.id)).scalar() or 0
    assignment_count = db.query(func.count(models.Assignment.id)).scalar() or 0
    submission_count = db.query(func.count(models.Submission.id)).scalar() or 0
    comparison_count = db.query(func.count(models.ComparisonResult.id)).scalar() or 0
    avg = (
        db.query(func.avg(models.ComparisonResult.similarity_score))
        .filter(models.ComparisonResult.similarity_score >= 0)
        .scalar()
    )
    return schemas.AdminStatsOut(
        user_count=int(user_count),
        assignment_count=int(assignment_count),
        submission_count=int(submission_count),
        comparison_count=int(comparison_count),
        avg_similarity=float(avg) if avg is not None else None,
    )


@router.get("/config", response_model=schemas.SystemConfigOut)
def get_config(
    db: Session = Depends(get_db),
    _: models.User = Depends(role_required("admin")),
):
    c = _get_or_create_config(db)
    return schemas.SystemConfigOut(
        similarity_threshold=c.similarity_threshold,
        llm_model_name=c.llm_model_name,
        syntax_weight=c.syntax_weight,
        semantic_weight=c.semantic_weight,
        updated_at=c.updated_at,
    )


@router.put("/config", response_model=schemas.SystemConfigOut)
def put_config(
    body: schemas.SystemConfigUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(role_required("admin")),
):
    c = _get_or_create_config(db)
    if body.similarity_threshold is not None:
        if not 0 <= body.similarity_threshold <= 100:
            raise HTTPException(status_code=400, detail="similarity_threshold must be 0-100")
        c.similarity_threshold = body.similarity_threshold
    if body.llm_model_name is not None:
        c.llm_model_name = body.llm_model_name.strip() or c.llm_model_name
    if body.syntax_weight is not None:
        if not 0 <= body.syntax_weight <= 1:
            raise HTTPException(status_code=400, detail="syntax_weight must be 0-1")
        c.syntax_weight = body.syntax_weight
    if body.semantic_weight is not None:
        if not 0 <= body.semantic_weight <= 1:
            raise HTTPException(status_code=400, detail="semantic_weight must be 0-1")
        c.semantic_weight = body.semantic_weight
    if abs((c.syntax_weight or 0) + (c.semantic_weight or 0) - 1.0) > 1e-6:
        raise HTTPException(status_code=400, detail="syntax_weight + semantic_weight must equal 1")
    db.commit()
    db.refresh(c)
    return schemas.SystemConfigOut(
        similarity_threshold=c.similarity_threshold,
        llm_model_name=c.llm_model_name,
        syntax_weight=c.syntax_weight,
        semantic_weight=c.semantic_weight,
        updated_at=c.updated_at,
    )


# ==================== 代码库管理 API ====================

@router.get("/code-library")
def list_code_library(
    db: Session = Depends(get_db),
    _: models.User = Depends(role_required("admin")),
):
    """
    获取代码库文件列表
    """
    items = db.query(models.CodeLibrary).order_by(models.CodeLibrary.uploaded_at.desc()).all()
    return [
        {
            "id": item.id,
            "filename": item.filename,
            "language": item.language,
            "file_size": item.file_size,
            "is_public": bool(item.is_public),
            "uploaded_at": item.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if item.uploaded_at else None,
        }
        for item in items
    ]


@router.post("/code-library/upload")
async def upload_code_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: models.User = Depends(role_required("admin")),
):
    """
    上传代码文件到代码库
    """
    content = await file.read()
    file_size = len(content)
    
    # 检查文件大小（限制10MB）
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过10MB")
    
    # 创建代码库记录
    library_item = models.CodeLibrary(
        filename=file.filename or "unknown.txt",
        language=get_language_from_filename(file.filename or ""),
        content=content.decode("utf-8"),
        file_size=file_size,
        is_public=1,
        uploaded_at=datetime.utcnow(),
    )
    
    db.add(library_item)
    db.commit()
    db.refresh(library_item)
    
    return {"ok": True, "id": library_item.id}


@router.get("/code-library/{file_id}/content")
def get_code_content(
    file_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(role_required("admin")),
):
    """
    获取代码文件内容
    """
    item = db.query(models.CodeLibrary).filter(models.CodeLibrary.id == file_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return {"content": item.content, "filename": item.filename}


@router.get("/code-library/{file_id}/download", response_class=PlainTextResponse)
def download_code_file(
    file_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(role_required("admin")),
):
    """
    下载代码文件
    """
    item = db.query(models.CodeLibrary).filter(models.CodeLibrary.id == file_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return PlainTextResponse(
        content=item.content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={item.filename}"},
    )


@router.delete("/code-library/{file_id}")
def delete_code_file(
    file_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(role_required("admin")),
):
    """
    删除代码文件
    """
    item = db.query(models.CodeLibrary).filter(models.CodeLibrary.id == file_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    db.delete(item)
    db.commit()
    
    return {"ok": True}
