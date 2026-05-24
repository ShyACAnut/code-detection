"""
认证API路由模块
==============

这个模块提供了用户认证相关的API端点，包括用户注册、登录和用户信息获取。

主要功能：
1. 用户注册 - 创建新用户账户
2. 用户登录 - 验证身份并获取JWT令牌
3. 获取当前用户信息 - 获取已登录用户的详细信息

安全特性：
- 密码哈希存储
- JWT令牌认证
- 用户名和邮箱唯一性验证
- OAuth2标准认证流程

API端点：
- POST /auth/register - 用户注册
- POST /auth/token - 用户登录
- GET /auth/me - 获取当前用户信息
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import models
import schemas 
from auth_utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    get_current_active_user,
    role_required,
    authenticate_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from database import get_db

# 创建认证路由器，设置前缀和标签
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    用户注册API端点
    ==============
    
    功能：
    - 创建新的用户账户
    - 验证用户名和邮箱的唯一性
    - 对密码进行安全哈希处理
    
    请求参数：
    - user: 用户创建数据（用户名、邮箱、密码、角色）
    
    返回值：
    - User: 创建成功的用户信息（不包含密码）
    
    异常处理：
    - 400: 用户名或邮箱已被注册
    
    安全特性：
    - 密码使用bcrypt哈希存储
    - 用户名和邮箱唯一性验证
    - 不返回明文密码
    """
    # 检查用户名或邮箱是否已存在
    db_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    
    # 如果用户已存在，抛出异常
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # 对密码进行哈希处理
    hashed_password = get_password_hash(user.password)
    
    # 创建新用户对象
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role
    )
    
    # 保存到数据库
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # 返回创建的用户信息
    return db_user

@router.post("/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    用户登录API端点
    ==============
    
    功能：
    - 验证用户身份
    - 生成JWT访问令牌
    - 支持OAuth2标准认证流程
    
    请求参数：
    - form_data: OAuth2密码表单数据（username, password）
    
    返回值：
    - Token: 包含访问令牌和令牌类型
    
    异常处理：
    - 400: 用户名或密码错误
    
    安全特性：
    - 使用JWT令牌进行身份验证
    - 令牌有过期时间限制
    - 遵循OAuth2标准
    """
    # 验证用户身份
    user = authenticate_user(db, form_data.username, form_data.password)
    print(f"用户查找结果: {user}")  # 检查是否存在
    # 如果验证失败，抛出异常
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    # 设置访问令牌过期时间
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 生成JWT访问令牌
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # 返回令牌信息
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    """
    获取当前用户信息API端点
    ========================
    
    功能：
    - 获取已登录用户的详细信息
    - 需要有效的JWT令牌
    - 自动验证用户身份
    
    请求头：
    - Authorization: Bearer <access_token>
    
    返回值：
    - User: 当前用户的详细信息
    
    安全特性：
    - 需要有效的JWT令牌
    - 自动验证令牌有效性
    - 不返回敏感信息（如密码）
    """
    # 直接返回当前用户信息
    return current_user