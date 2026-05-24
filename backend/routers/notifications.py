# backend/routers/notifications.py
"""
整改通知路由模块
================

提供整改通知的创建、发送和管理功能。

主要功能：
1. 创建整改通知
2. 发送通知给学生
3. 查看通知列表
4. 标记通知已读/未读
5. 通知状态跟踪

角色权限：
- 教师：创建和发送通知
- 学生：查看自己的通知
- 管理员：查看所有通知
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

import models
from auth_utils import role_required, get_current_active_user
from database import get_db
from ethics_learning_utils import trigger_ethics_learning

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    """创建通知的请求模型"""
    student_id: int
    assignment_id: int
    title: str
    content: str
    similarity_score: Optional[float] = None
    priority: str = "normal"


class NotificationResponse(BaseModel):
    """通知响应模型"""
    id: int
    student_id: int
    teacher_id: int
    assignment_id: int
    title: str
    content: str
    similarity_score: Optional[float]
    priority: str
    is_read: bool
    created_at: str

    class Config:
        from_attributes = True


class NotificationUpdate(BaseModel):
    """更新通知的请求模型"""
    is_read: Optional[bool] = None


class StudentListItem(BaseModel):
    """学生列表项模型"""
    id: int
    username: str
    email: str


@router.post("/", response_model=NotificationResponse)
def create_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("teacher")),
):
    """
    创建并发送整改通知

    教师可以为某个学生的作业创建整改通知。
    发送通知时会自动触发该学生的伦理学习要求。
    """
    # 验证学生存在
    student = db.query(models.User).filter(
        models.User.id == notification.student_id,
        models.User.role == "student"
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    # 验证作业存在
    assignment = db.query(models.Assignment).filter(
        models.Assignment.id == notification.assignment_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")

    # 创建通知
    db_notification = models.Notification(
        student_id=notification.student_id,
        teacher_id=current_user.id,
        assignment_id=notification.assignment_id,
        title=notification.title,
        content=notification.content,
        similarity_score=notification.similarity_score,
        priority=notification.priority,
        is_read=False,
        created_at=datetime.utcnow(),
    )

    db.add(db_notification)

    # 自动触发伦理学习要求
    trigger_ethics_learning(notification.student_id, db)

    db.commit()
    db.refresh(db_notification)

    return NotificationResponse(
        id=db_notification.id,
        student_id=db_notification.student_id,
        teacher_id=db_notification.teacher_id,
        assignment_id=db_notification.assignment_id,
        title=db_notification.title,
        content=db_notification.content,
        similarity_score=db_notification.similarity_score,
        priority=db_notification.priority,
        is_read=db_notification.is_read,
        created_at=db_notification.created_at.strftime("%Y-%m-%d %H:%M:%S") if db_notification.created_at else "",
    )


@router.get("/", response_model=List[NotificationResponse])
def list_notifications(
    assignment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    获取通知列表

    - 教师：获取自己发送的所有通知
    - 学生：获取发给自己的所有通知
    - 管理员：获取所有通知
    """
    query = db.query(models.Notification)

    if current_user.role == "teacher":
        query = query.filter(models.Notification.teacher_id == current_user.id)
    elif current_user.role == "student":
        query = query.filter(models.Notification.student_id == current_user.id)
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限访问此资源")

    if assignment_id:
        query = query.filter(models.Notification.assignment_id == assignment_id)

    notifications = query.order_by(models.Notification.created_at.desc()).all()

    return [
        NotificationResponse(
            id=n.id,
            student_id=n.student_id,
            teacher_id=n.teacher_id,
            assignment_id=n.assignment_id,
            title=n.title,
            content=n.content,
            similarity_score=n.similarity_score,
            priority=n.priority,
            is_read=n.is_read,
            created_at=n.created_at.strftime("%Y-%m-%d %H:%M:%S") if n.created_at else "",
        )
        for n in notifications
    ]


@router.get("/students", response_model=List[StudentListItem])
def get_students_for_teacher(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("teacher")),
):
    """
    获取学生列表（教师可用）
    教师可以使用此接口获取所有学生列表，用于发送整改通知
    """
    students = db.query(models.User).filter(
        models.User.role == "student"
    ).order_by(models.User.username).all()

    return [
        StudentListItem(
            id=s.id,
            username=s.username,
            email=s.email,
        )
        for s in students
    ]


@router.get("/students/{student_id}/notifications")
def get_student_notifications(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    获取某个学生的所有通知（教师或管理员可用）
    """
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="无权限访问此资源")

    notifications = db.query(models.Notification).filter(
        models.Notification.student_id == student_id
    ).order_by(models.Notification.created_at.desc()).all()

    return [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "similarity_score": n.similarity_score,
            "priority": n.priority,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S") if n.created_at else "",
        }
        for n in notifications
    ]


@router.put("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: int,
    update: NotificationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    更新通知状态（如标记已读/未读）
    """
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    # 学生只能更新自己的通知
    if current_user.role == "student" and notification.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限更新此通知")

    if update.is_read is not None:
        notification.is_read = update.is_read

    db.commit()
    db.refresh(notification)

    return NotificationResponse(
        id=notification.id,
        student_id=notification.student_id,
        teacher_id=notification.teacher_id,
        assignment_id=notification.assignment_id,
        title=notification.title,
        content=notification.content,
        similarity_score=notification.similarity_score,
        priority=notification.priority,
        is_read=notification.is_read,
        created_at=notification.created_at.strftime("%Y-%m-%d %H:%M:%S") if notification.created_at else "",
    )


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("teacher")),
):
    """
    删除通知（仅教师和管理员可用）
    """
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    # 只有发送通知的教师或管理员可以删除
    if current_user.role == "teacher" and notification.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限删除此通知")

    db.delete(notification)
    db.commit()

    return {"message": "通知已删除"}


@router.get("/ethics/status")
def get_ethics_learning_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    获取当前学生的伦理学习状态
    包括：是否需要学习、需要完成的数量、已完成的数量
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可以访问此接口")

    from ethics_learning_utils import get_student_ethics_status
    status = get_student_ethics_status(current_user.id, db)
    return status


class EthicsLearningStatusResponse(BaseModel):
    requires_learning: bool
    required_count: int
    completed_count: int
    remaining_count: int