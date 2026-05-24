"""
认证工具模块
============

这个文件提供了完整的用户认证和授权功能。
支持密码哈希、JWT令牌生成和验证、角色权限控制。

主要功能：
1. 密码加密和验证
2. JWT令牌管理
3. 用户身份验证
4. 角色权限控制
5. 多种哈希算法支持

安全特性：
- bcrypt密码哈希
- JWT令牌认证
- 角色基础访问控制
- 密码长度限制
- 历史哈希兼容性
"""

from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db

# ============================================================================
# JWT配置
# ============================================================================

# JWT密钥和算法配置
# =================
# 注意：生产环境必须使用安全的密钥
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 1天 = 24 * 60 分钟

# 配置说明：
# - SECRET_KEY: JWT签名密钥，生产环境必须更改
# - ALGORITHM: JWT加密算法（HS256是标准算法）
# - ACCESS_TOKEN_EXPIRE_MINUTES: 令牌过期时间（分钟）

# ============================================================================
# 密码哈希配置
# ============================================================================

# bcrypt密码长度限制
# ==================
# bcrypt算法对明文密码有72字节限制（UTF-8编码）
# 超过限制的密码会被截断
BCRYPT_MAX_PASSWORD_BYTES = 72

# 历史哈希算法支持
# =================
# 仅用于校验数据库里历史argon2哈希（早期版本曾用argon2）
# 使用passlib的deprecated模式确保向后兼容
_argon2_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2配置
# ==========
# OAuth2密码Bearer令牌方案
# 用于JWT令牌的获取和验证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


# ============================================================================
# 密码处理函数
# ============================================================================

def _password_bytes_for_bcrypt(password: str) -> bytes:
    """
    将密码转换为bcrypt兼容的字节格式
    ================================
    
    功能：
    - 将字符串密码转换为UTF-8字节
    - 确保密码长度不超过bcrypt限制
    - 截断过长的密码
    
    参数：
    - password: 明文密码字符串
    
    返回值：
    - bytes: 符合bcrypt长度要求的密码字节
    
    安全说明：
    - bcrypt有72字节限制，超过部分会被截断
    - 这是bcrypt算法的已知限制
    """
    b = password.encode("utf-8")
    if len(b) > BCRYPT_MAX_PASSWORD_BYTES:
        return b[:BCRYPT_MAX_PASSWORD_BYTES]
    return b


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配哈希值
    =====================
    
    功能：
    - 验证明文密码与存储的哈希值是否匹配
    - 支持多种哈希算法（bcrypt和argon2）
    - 提供向后兼容性
    
    参数：
    - plain_password: 用户输入的明文密码
    - hashed_password: 数据库中存储的哈希密码
    
    返回值：
    - bool: 密码是否匹配
    
    算法支持：
    - bcrypt: 当前使用的算法（$2a$, $2b$等前缀）
    - argon2: 历史兼容算法（$argon2$前缀）
    
    异常处理：
    - 任何验证错误都返回False
    - 不暴露具体的错误信息
    """
    if not hashed_password:
        return False
    # 历史 argon2（passlib）
    if hashed_password.startswith("$argon2"):
        try:
            return _argon2_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    # bcrypt：直接用 bcrypt 库校验（兼容 $2a$/$2b$ 等）
    try:
        h = hashed_password.encode("utf-8")
        return bcrypt.checkpw(_password_bytes_for_bcrypt(plain_password), h)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    生成密码的bcrypt哈希值
    ====================
    
    功能：
    - 使用bcrypt算法生成密码哈希
    - 自动添加随机盐值
    - 返回可存储的字符串格式
    
    参数：
    - password: 明文密码
    
    返回值：
    - str: bcrypt哈希字符串（ASCII编码）
    
    安全特性：
    - 每次调用生成不同的哈希值（随机盐值）
    - 使用bcrypt.gensalt()生成安全盐值
    - 哈希值包含算法标识和参数
    """
    pw = _password_bytes_for_bcrypt(password)
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("ascii")

# ============================================================================
# 用户认证函数
# ============================================================================

def authenticate_user(db: Session, username: str, password: str):
    """
    用户身份验证函数
    ===============
    
    功能：
    - 验证用户名和密码是否正确
    - 查询数据库中的用户信息
    - 使用密码哈希验证
    
    参数：
    - db: 数据库会话
    - username: 用户名
    - password: 密码
    
    返回值：
    - User: 用户对象（验证成功）
    - False: 验证失败
    
    业务逻辑：
    - 先查询用户是否存在
    - 再验证密码是否正确
    - 两者都通过才返回用户对象
    """
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    """
    创建JWT访问令牌
    ===============
    
    功能：
    - 生成JWT令牌用于用户认证
    - 设置令牌过期时间
    - 包含用户身份信息
    
    参数：
    - data: 要编码的数据字典（包含用户信息）
    - expires_delta: 自定义过期时间（可选）
    
    返回值：
    - str: JWT令牌字符串
    
    令牌结构：
    - sub: 用户名（标准JWT字段）
    - exp: 过期时间（标准JWT字段）
    - 其他自定义字段
    
    安全说明：
    - 使用HS256算法签名
    - 包含过期时间防止令牌永久有效
    - 生产环境应使用更安全的密钥
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=3)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ============================================================================
# JWT令牌验证函数
# ============================================================================

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    获取当前用户（JWT令牌验证）
    ==========================
    
    功能：
    - 验证JWT令牌的有效性
    - 从令牌中提取用户信息
    - 查询数据库中的用户记录
    
    参数：
    - token: JWT令牌字符串（从Authorization头获取）
    - db: 数据库会话
    
    返回值：
    - User: 当前用户对象
    
    异常处理：
    - 令牌无效或过期：HTTP 401
    - 用户不存在：HTTP 401
    - 令牌格式错误：HTTP 401
    
    使用方式：
    - 在路由中使用：current_user: User = Depends(get_current_user)
    - FastAPI会自动处理令牌提取和验证
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码JWT令牌
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 查询用户记录
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    """
    获取当前活跃用户
    ===============
    
    功能：
    - 确保用户是活跃状态
    - 作为依赖注入函数使用
    - 可以扩展用户状态检查
    
    参数：
    - current_user: 已验证的用户对象
    
    返回值：
    - User: 当前活跃用户对象
    
    使用场景：
    - 需要确保用户活跃的路由
    - 可以在此添加用户状态检查逻辑
    - 例如：检查用户是否被禁用、是否需要验证邮箱等
    
    当前实现：
    - 简单返回用户对象
    - 可以扩展为更复杂的用户状态验证
    """
    return current_user

# ============================================================================
# 角色权限控制函数
# ============================================================================

def role_required(required_role: str):
    """
    单一角色权限装饰器
    =================
    
    功能：
    - 创建依赖注入函数，检查用户是否具有指定角色
    - 支持单一角色验证
    - 返回403错误当权限不足时
    
    参数：
    - required_role: 所需的角色字符串（如"teacher", "admin"等）
    
    返回值：
    - function: 依赖注入函数
    
    使用方式：
    - @app.get("/admin-only")
    - async def admin_endpoint(current_user: User = Depends(role_required("admin"))):
    -     return {"message": "Admin access granted"}
    
    错误处理：
    - 权限不足时返回HTTP 403状态码
    - 错误消息："Insufficient permissions"
    """
    def role_checker(current_user: models.User = Depends(get_current_active_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

def roles_required(required_roles: list):
    """
    多角色权限装饰器
    ===============
    
    功能：
    - 创建依赖注入函数，检查用户是否具有所需角色之一
    - 支持多个角色验证（OR逻辑）
    - 返回403错误当权限不足时
    
    参数：
    - required_roles: 允许的角色列表，例如 ['teacher', 'dean']
    
    返回值：
    - function: 依赖注入函数
    
    使用方式：
    - @app.get("/teacher-or-dean")
    - async def endpoint(current_user: User = Depends(roles_required(["teacher", "dean"]))):
    -     return {"message": "Access granted"}
    
    错误处理：
    - 权限不足时返回HTTP 403状态码
    - 错误消息包含所有允许的角色
    - 格式："Insufficient permissions. Required roles: role1, role2"
    
    业务逻辑：
    - 用户角色只要在required_roles列表中即可访问
    - 支持灵活的角色组合
    - 适合需要多种角色访问的场景
    """
    def role_checker(current_user: models.User = Depends(get_current_active_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient permissions. Required roles: {', '.join(required_roles)}"
            )
        return current_user
    return role_checker