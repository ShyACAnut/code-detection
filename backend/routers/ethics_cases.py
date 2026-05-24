# backend/routers/ethics_cases.py
"""
编程伦理案例路由模块
====================

提供编程伦理和学术诚信案例的学习功能。

主要功能：
1. 案例列表查看
2. 案例详情查看
3. 学习进度记录
4. 案例管理（教师/管理员）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

import models
from auth_utils import role_required, get_current_active_user
from database import get_db
from ethics_learning_utils import check_ethics_learning_completed, clear_ethics_learning_requirement

router = APIRouter(prefix="/ethics-cases", tags=["ethics-cases"])


class EthicsCaseResponse(BaseModel):
    id: int
    title: str
    category: str
    description: str
    scenario: str
    outcome: str
    consequences: str
    prevention: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class EthicsCaseCreate(BaseModel):
    title: str
    category: str
    description: str
    scenario: str
    outcome: str
    consequences: str
    prevention: str
    is_active: bool = True


class LearningRecordResponse(BaseModel):
    id: int
    case_id: int
    is_completed: bool
    completed_at: Optional[str]
    created_at: str
    case_title: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[EthicsCaseResponse])
def list_cases(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    query = db.query(models.EthicsCase).filter(models.EthicsCase.is_active == 1)

    if category:
        query = query.filter(models.EthicsCase.category == category)

    cases = query.order_by(models.EthicsCase.created_at.desc()).all()
    
    # 如果是学生且没有伦理学习要求，隐藏案例详情（锁定状态）
    if current_user.role == "student" and not getattr(current_user, 'requires_ethics_learning', 0):
        return [
            EthicsCaseResponse(
                id=c.id,
                title=c.title,
                category=c.category,
                description="🔒 伦理学习内容已锁定",
                scenario="🔒 请完成学习要求后查看",
                outcome="🔒 请完成学习要求后查看",
                consequences="🔒 请完成学习要求后查看",
                prevention="🔒 请完成学习要求后查看",
                is_active=bool(c.is_active),
                created_at=c.created_at.strftime("%Y-%m-%d") if c.created_at else "",
            )
            for c in cases
        ]

    return [
        EthicsCaseResponse(
            id=c.id,
            title=c.title,
            category=c.category,
            description=c.description,
            scenario=c.scenario,
            outcome=c.outcome,
            consequences=c.consequences,
            prevention=c.prevention,
            is_active=bool(c.is_active),
            created_at=c.created_at.strftime("%Y-%m-%d") if c.created_at else "",
        )
        for c in cases
    ]


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    categories = db.query(models.EthicsCase.category).distinct().all()
    return [c[0] for c in categories if c[0]]


@router.get("/{case_id}", response_model=EthicsCaseResponse)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    case = db.query(models.EthicsCase).filter(
        models.EthicsCase.id == case_id
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")

    # 如果是学生且没有伦理学习要求，隐藏案例详情（锁定状态）
    if current_user.role == "student" and not getattr(current_user, 'requires_ethics_learning', 0):
        return EthicsCaseResponse(
            id=case.id,
            title=case.title,
            category=case.category,
            description="🔒 伦理学习内容已锁定",
            scenario="🔒 请完成学习要求后查看",
            outcome="🔒 请完成学习要求后查看",
            consequences="🔒 请完成学习要求后查看",
            prevention="🔒 请完成学习要求后查看",
            is_active=bool(case.is_active),
            created_at=case.created_at.strftime("%Y-%m-%d") if case.created_at else "",
        )

    return EthicsCaseResponse(
        id=case.id,
        title=case.title,
        category=case.category,
        description=case.description,
        scenario=case.scenario,
        outcome=case.outcome,
        consequences=case.consequences,
        prevention=case.prevention,
        is_active=bool(case.is_active),
        created_at=case.created_at.strftime("%Y-%m-%d") if case.created_at else "",
    )


@router.post("/{case_id}/complete")
def mark_case_completed(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("student")),
):
    # 检查学生是否有伦理学习要求
    if not getattr(current_user, 'requires_ethics_learning', 0):
        raise HTTPException(status_code=403, detail="当前没有伦理学习要求，无法标记完成")

    case = db.query(models.EthicsCase).filter(
        models.EthicsCase.id == case_id
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")

    record = db.query(models.EthicsLearningRecord).filter(
        models.EthicsLearningRecord.student_id == current_user.id,
        models.EthicsLearningRecord.case_id == case_id,
    ).first()

    if record:
        record.is_completed = 1
        record.completed_at = datetime.utcnow()
    else:
        record = models.EthicsLearningRecord(
            student_id=current_user.id,
            case_id=case_id,
            is_completed=1,
            completed_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(record)

    db.commit()

    # 检查是否已完成要求的伦理学习数量
    if check_ethics_learning_completed(current_user.id, db):
        clear_ethics_learning_requirement(current_user.id, db)
        # 重置学习记录，确保下次触发时需要重新学习
        from ethics_learning_utils import reset_ethics_learning_progress
        reset_ethics_learning_progress(current_user.id, db)
        return {"ok": True, "message": "学习完成，伦理学习要求已全部完成！"}

    return {"ok": True, "message": "学习完成"}


@router.get("/learning/progress")
def get_learning_progress(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("student")),
):
    total_cases = db.query(models.EthicsCase).filter(
        models.EthicsCase.is_active == 1
    ).count()

    completed_records = db.query(models.EthicsLearningRecord).filter(
        models.EthicsLearningRecord.student_id == current_user.id,
        models.EthicsLearningRecord.is_completed == 1,
    ).all()

    completed_count = len(completed_records)

    return {
        "total_cases": total_cases,
        "completed_count": completed_count,
        "progress_percentage": (completed_count / total_cases * 100) if total_cases > 0 else 0,
        "completed_cases": [r.case_id for r in completed_records],
    }


@router.get("/learning/history", response_model=List[LearningRecordResponse])
def get_learning_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("student")),
):
    records = db.query(models.EthicsLearningRecord).filter(
        models.EthicsLearningRecord.student_id == current_user.id,
    ).order_by(models.EthicsLearningRecord.created_at.desc()).all()

    result = []
    for record in records:
        case = db.query(models.EthicsCase).filter(
            models.EthicsCase.id == record.case_id
        ).first()

        result.append(LearningRecordResponse(
            id=record.id,
            case_id=record.case_id,
            is_completed=bool(record.is_completed),
            completed_at=record.completed_at.strftime("%Y-%m-%d %H:%M:%S") if record.completed_at else None,
            created_at=record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "",
            case_title=case.title if case else None,
        ))

    return result


# ==================== 管理员/教师接口 ====================

@router.post("/", response_model=EthicsCaseResponse)
def create_case(
    case_data: EthicsCaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("teacher")),
):
    new_case = models.EthicsCase(
        title=case_data.title,
        category=case_data.category,
        description=case_data.description,
        scenario=case_data.scenario,
        outcome=case_data.outcome,
        consequences=case_data.consequences,
        prevention=case_data.prevention,
        is_active=1 if case_data.is_active else 0,
        created_at=datetime.utcnow(),
    )

    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    return EthicsCaseResponse(
        id=new_case.id,
        title=new_case.title,
        category=new_case.category,
        description=new_case.description,
        scenario=new_case.scenario,
        outcome=new_case.outcome,
        consequences=new_case.consequences,
        prevention=new_case.prevention,
        is_active=bool(new_case.is_active),
        created_at=new_case.created_at.strftime("%Y-%m-%d") if new_case.created_at else "",
    )


@router.put("/{case_id}", response_model=EthicsCaseResponse)
def update_case(
    case_id: int,
    case_data: EthicsCaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("teacher")),
):
    case = db.query(models.EthicsCase).filter(
        models.EthicsCase.id == case_id
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")

    case.title = case_data.title
    case.category = case_data.category
    case.description = case_data.description
    case.scenario = case_data.scenario
    case.outcome = case_data.outcome
    case.consequences = case_data.consequences
    case.prevention = case_data.prevention
    case.is_active = 1 if case_data.is_active else 0

    db.commit()
    db.refresh(case)

    return EthicsCaseResponse(
        id=case.id,
        title=case.title,
        category=case.category,
        description=case.description,
        scenario=case.scenario,
        outcome=case.outcome,
        consequences=case.consequences,
        prevention=case.prevention,
        is_active=bool(case.is_active),
        created_at=case.created_at.strftime("%Y-%m-%d") if case.created_at else "",
    )


@router.delete("/{case_id}")
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("admin")),
):
    case = db.query(models.EthicsCase).filter(
        models.EthicsCase.id == case_id
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")

    db.delete(case)
    db.commit()

    return {"message": "案例已删除"}
