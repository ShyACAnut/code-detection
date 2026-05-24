"""
数据库配置模块
=============

这个文件配置了SQLAlchemy数据库连接和会话管理。
使用SQLite作为数据库，支持多线程访问。

主要功能：
1. 数据库连接配置
2. 会话工厂设置
3. 基类声明
4. 依赖注入函数

配置说明：
- 使用SQLite数据库文件
- 支持多线程访问
- 自动管理会话生命周期
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ============================================================================
# 数据库连接配置
# ============================================================================

# 数据库 URL（可根据环境变量配置）
# 格式：sqlite:///./数据库名.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./code_detection.db"

# 创建数据库引擎
# =================
# SQLAlchemy引擎负责管理数据库连接池和连接参数
# SQLite需要特殊配置以支持多线程访问
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# 配置说明：
# - check_same_thread=False: 允许多个线程使用同一个连接
# - 这是SQLite的特殊要求，其他数据库不需要此参数
# - 生产环境建议使用PostgreSQL或MySQL等更强大的数据库

# ============================================================================
# 会话工厂配置
# ============================================================================

# 创建会话本地类
# ===============
# SessionLocal用于创建数据库会话实例
# 配置说明：
# - autocommit=False: 手动提交事务（默认）
# - autoflush=False: 不自动刷新会话（提高性能）
# - bind=engine: 绑定到数据库引擎
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# ============================================================================
# 基类声明
# ============================================================================

# 声明基类
# ========
# Base是所有SQLAlchemy模型的基类
# 提供了ORM映射的基础功能
Base = declarative_base()

# ============================================================================
# 依赖注入函数
# ============================================================================

def get_db():
    """
    数据库会话依赖函数
    =================
    
    功能：
    - 为FastAPI路由提供数据库会话
    - 自动管理会话的生命周期
    - 确保会话正确关闭
    
    使用方式：
    - 在路由函数中使用：db: Session = Depends(get_db)
    - FastAPI会自动处理会话的创建和关闭
    
    返回值：
    - db: 数据库会话实例
    
    异常处理：
    - 会自动回滚未提交的事务
    - 确保资源被正确释放
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()