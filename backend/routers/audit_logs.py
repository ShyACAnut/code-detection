# backend/routers/audit_logs.py
"""
审计日志路由模块
================

提供系统操作审计日志的查询和管理功能。

主要功能：
1. 记录系统操作日志
2. 查询操作日志列表
3. 按用户、时间、操作类型筛选日志
4. 导出审计报告

角色权限：
- 管理员和教学主任可以查看所有日志
- 教师可以查看与自己相关的日志
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

import models
from auth_utils import role_required, get_current_active_user
from database import get_db

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


class AuditLogResponse(BaseModel):
    """审计日志响应模型"""
    id: int
    actor_user_id: Optional[int]
    action: str
    target_type: Optional[str]
    target_id: Optional[int]
    detail: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[AuditLogResponse])
def list_audit_logs(
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    user_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("admin")),
):
    """
    获取审计日志列表

    支持按操作类型、目标类型、用户ID、时间范围筛选
    """
    query = db.query(models.AuditLog)

    if action:
        query = query.filter(models.AuditLog.action == action)

    if target_type:
        query = query.filter(models.AuditLog.target_type == target_type)

    if user_id:
        query = query.filter(models.AuditLog.actor_user_id == user_id)

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(models.AuditLog.created_at >= start)
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            end = end + timedelta(days=1)
            query = query.filter(models.AuditLog.created_at < end)
        except ValueError:
            pass

    logs = query.order_by(models.AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return [
        AuditLogResponse(
            id=log.id,
            actor_user_id=log.actor_user_id,
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            detail=log.detail,
            ip_address=getattr(log, 'ip_address', None),
            user_agent=getattr(log, 'user_agent', None),
            created_at=log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
        )
        for log in logs
    ]


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("admin")),
):
    """
    获取单个审计日志详情
    """
    log = db.query(models.AuditLog).filter(models.AuditLog.id == log_id).first()

    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")

    return AuditLogResponse(
        id=log.id,
        actor_user_id=log.actor_user_id,
        action=log.action,
        target_type=log.target_type,
        target_id=log.target_id,
        detail=log.detail,
        ip_address=getattr(log, 'ip_address', None),
        user_agent=getattr(log, 'user_agent', None),
        created_at=log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
    )


@router.get("/actions/list")
def list_actions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("admin")),
):
    """
    获取所有操作类型列表
    """
    actions = db.query(models.AuditLog.action).distinct().all()
    return [action[0] for action in actions if action[0]]


@router.get("/stats/summary")
def get_audit_stats(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("admin")),
):
    """
    获取审计统计摘要
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    total_count = db.query(models.AuditLog).filter(
        models.AuditLog.created_at >= start_date
    ).count()

    action_counts = db.query(
        models.AuditLog.action,
        db.func.count(models.AuditLog.id)
    ).filter(
        models.AuditLog.created_at >= start_date
    ).group_by(models.AuditLog.action).all()

    user_counts = db.query(
        models.AuditLog.actor_user_id,
        db.func.count(models.AuditLog.id)
    ).filter(
        models.AuditLog.created_at >= start_date,
        models.AuditLog.actor_user_id.isnot(None)
    ).group_by(models.AuditLog.actor_user_id).order_by(
        db.func.count(models.AuditLog.id).desc()
    ).limit(10).all()

    return {
        "total_count": total_count,
        "days": days,
        "action_distribution": {action: count for action, count in action_counts},
        "top_users": [{"user_id": uid, "count": count} for uid, count in user_counts],
    }


def log_action(
    db: Session,
    action: str,
    actor_user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """
    记录操作日志的辅助函数

    在需要进行审计的地方调用此函数记录日志
    """
    log = models.AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()