# backend/main.py
"""
代码相似性检测系统 - 主应用文件
===================================

这个文件是FastAPI应用程序的入口点，负责：
1. 初始化数据库和表结构
2. 配置CORS中间件
3. 注册所有API路由
4. 初始化代码检测智能体
5. 提供健康检查和语言检测接口

"""

import os
from sqlalchemy import text
from datetime import datetime
from fastapi.encoders import jsonable_encoder

# 设置环境变量，用于离线模式运行
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")  # 使用HuggingFace镜像
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")  # 启用离线模式
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # 启用Hugging Hub离线模式

# 导入必要的模块
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

# 导入路由模块
from routers import admin, analysis_tasks, assignments, auth, submissions, statistics, self_check, notifications, reports, audit_logs, ethics_cases
from database import engine, Base
from code_agent import CodeDetectionAgent
from pipeline.analyze_pipeline import analyze_pair
from language_detector import detect_code_language, validate_code_language

# 加载环境变量
load_dotenv()

# 创建数据库表
Base.metadata.create_all(bind=engine)


def _sqlite_column_exists(conn, table: str, column: str) -> bool:
    """
    检查SQLite表中是否存在指定列
    
    Args:
        conn: 数据库连接
        table: 表名
        column: 列名
        
    Returns:
        bool: 列是否存在
    """
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def _ensure_legacy_sqlite_migration():
    """
    轻量级数据库迁移函数
    ======================
    
    功能:
    - 兼容旧SQLite库缺少新列/新表的情况
    - 避免每次修改模型都需要手动删库
    - 自动创建缺失的表和列
    
    迁移内容:
    1. submissions表添加updated_at列
    2. 创建submission_revisions表
    3. system_config表添加权重配置列
    4. 创建detection_evidences表
    5. 创建code_index_entries表
    6. 创建audit_logs表
    """
    db_url = str(engine.url)
    if not db_url.startswith("sqlite"):
        return  # 只对SQLite进行迁移

    with engine.begin() as conn:
        # 1. 为submissions表添加updated_at列
        if not _sqlite_column_exists(conn, "submissions", "updated_at"):
            conn.execute(text("ALTER TABLE submissions ADD COLUMN updated_at DATETIME"))

        # 2. 创建submission_revisions表（用于存储代码修订历史）
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS submission_revisions (
                    id INTEGER NOT NULL PRIMARY KEY,
                    submission_id INTEGER,
                    code TEXT,
                    file_path VARCHAR,
                    edited_at DATETIME,
                    FOREIGN KEY(submission_id) REFERENCES submissions (id)
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_submission_revisions_submission_id ON submission_revisions (submission_id)"
            )
        )

        # 3. 为system_config表添加权重配置列
        if not _sqlite_column_exists(conn, "system_config", "syntax_weight"):
            conn.execute(text("ALTER TABLE system_config ADD COLUMN syntax_weight FLOAT DEFAULT 0.4"))
        if not _sqlite_column_exists(conn, "system_config", "semantic_weight"):
            conn.execute(text("ALTER TABLE system_config ADD COLUMN semantic_weight FLOAT DEFAULT 0.6"))

        # 4. 创建detection_evidences表（存储检测结果证据）
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS detection_evidences (
                    id INTEGER NOT NULL PRIMARY KEY,
                    comparison_result_id INTEGER,
                    assignment_id INTEGER,
                    submission_id INTEGER,
                    compared_with_id INTEGER,
                    language VARCHAR,
                    syntax_score FLOAT,
                    semantic_score FLOAT,
                    final_score FLOAT,
                    model_name VARCHAR,
                    evidence_payload TEXT,
                    created_at DATETIME,
                    FOREIGN KEY(comparison_result_id) REFERENCES comparison_results (id)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_detection_evidences_assignment_id ON detection_evidences (assignment_id)"))

        # 5. 创建code_index_entries表（用于代码索引和快速检索）
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS code_index_entries (
                    id INTEGER NOT NULL PRIMARY KEY,
                    submission_id INTEGER UNIQUE,
                    assignment_id INTEGER,
                    language VARCHAR,
                    normalized_hash VARCHAR,
                    vector_stub TEXT,
                    updated_at DATETIME,
                    FOREIGN KEY(submission_id) REFERENCES submissions (id)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_code_index_entries_assignment_id ON code_index_entries (assignment_id)"))

        # 6. 创建audit_logs表（用于审计日志）
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER NOT NULL PRIMARY KEY,
                    actor_user_id INTEGER,
                    action VARCHAR,
                    target_type VARCHAR,
                    target_id INTEGER,
                    detail TEXT,
                    created_at DATETIME
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action)"))

        # 7. 为assignments表添加评分相关列
        if not _sqlite_column_exists(conn, "assignments", "function_requirements"):
            conn.execute(text("ALTER TABLE assignments ADD COLUMN function_requirements TEXT"))
        if not _sqlite_column_exists(conn, "assignments", "scoring_guideline"):
            conn.execute(text("ALTER TABLE assignments ADD COLUMN scoring_guideline TEXT"))

        # 8. 创建submission_scores表（用于存储学生提交评分）
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS submission_scores (
                    id INTEGER NOT NULL PRIMARY KEY,
                    submission_id INTEGER UNIQUE,
                    teacher_id INTEGER,
                    overall_score FLOAT NOT NULL,
                    teacher_comments TEXT,
                    criteria_scores TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY(submission_id) REFERENCES submissions (id),
                    FOREIGN KEY(teacher_id) REFERENCES users (id)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_submission_scores_submission_id ON submission_scores (submission_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_submission_scores_teacher_id ON submission_scores (teacher_id)"))

        # 9. 为ablation_results表添加新列（相似度评分、比对时间、混淆类型、标注标签）
        if not _sqlite_column_exists(conn, "ablation_results", "similarity_score"):
            conn.execute(text("ALTER TABLE ablation_results ADD COLUMN similarity_score FLOAT"))
        if not _sqlite_column_exists(conn, "ablation_results", "comparison_time_ms"):
            conn.execute(text("ALTER TABLE ablation_results ADD COLUMN comparison_time_ms FLOAT"))
        if not _sqlite_column_exists(conn, "ablation_results", "obfuscation_type"):
            conn.execute(text("ALTER TABLE ablation_results ADD COLUMN obfuscation_type VARCHAR"))
        if not _sqlite_column_exists(conn, "ablation_results", "ground_truth_label"):
            conn.execute(text("ALTER TABLE ablation_results ADD COLUMN ground_truth_label INTEGER"))


# 执行数据库迁移
_ensure_legacy_sqlite_migration()

# 创建自定义JSON编码器，确保datetime返回UTC时间带时区标记
def custom_json_encoder(obj):
    if isinstance(obj, datetime):
        # 如果datetime没有时区信息，添加UTC时区标记
        if obj.tzinfo is None:
            return obj.isoformat() + "Z"
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# 创建FastAPI应用实例
app = FastAPI(
    title="代码相似性检测API", 
    description="基于大模型与AST的智能代码分析后端服务"
)

# 注册自定义JSON编码器
from fastapi.responses import ORJSONResponse, JSONResponse
import json

class CustomJSONResponse(JSONResponse):
    media_type = "application/json"
    
    def render(self, content: any) -> bytes:
        return json.dumps(content, default=custom_json_encoder, ensure_ascii=False).encode("utf-8")

# 设置默认响应类
app.default_response_class = CustomJSONResponse

# 配置CORS中间件
_cors = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_origins = [o.strip() for o in _cors.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有API路由
app.include_router(auth.router)      # 认证相关路由
app.include_router(assignments.router)  # 作业管理路由
app.include_router(submissions.router)  # 提交管理路由
app.include_router(analysis_tasks.router)  # 分析任务路由
app.include_router(admin.router)      # 管理员路由
app.include_router(statistics.router)  # 统计分析路由
app.include_router(self_check.router)  # 代码自查路由
app.include_router(notifications.router)  # 整改通知路由
app.include_router(reports.router)  # 报告生成路由
app.include_router(audit_logs.router)  # 审计日志路由
app.include_router(ethics_cases.router)  # 编程伦理案例路由

# 初始化代码检测智能体
try:
    agent = CodeDetectionAgent()
    print("[OK] 成功初始化 CodeDetectionAgent")
except Exception as e:
    print(f"[ERROR] 初始化 CodeDetectionAgent 失败: {e}")
    # 创建一个降级版本的智能体，使用传统分析方法
    class CodeDetectionAgent:
        def analyze_code_similarity(self, code_a: str, code_b: str, language: str):
            print(f"[降级模式] 使用传统方法分析 {language} 代码")
            try:
                from pipeline.analyze_pipeline import analyze_pair
                result = analyze_pair(code_a, code_b, language)
                return {
                    "similarity_analysis": {
                        "score": result["final_score"],
                        "reason": result.get("reason", "传统方法分析结果"),
                        "function_summary": f"{language} 传统语义分析"
                    },
                    "metadata": {
                        "language": language,
                        "filter_layer": "fallback_traditional"
                    }
                }
            except Exception as inner_e:
                return {"error": f"传统分析方法失败: {str(inner_e)}"}
        
        def batch_analyze(self, *args, **kwargs):
            return {"error": "批量分析功能在降级模式下不可用"}
    
    agent = CodeDetectionAgent()


# 根路径路由
@app.get("/")
async def root():
    """
    根路径 - API服务信息
    
    Returns:
        dict: API服务状态和基本信息
    """
    return {
        "message": "代码相似性检测后端服务正在运行",
        "status": "active",
        "available_endpoint": "POST /api/analyze",
        "version": "1.0.0"
    }


# 健康检查路由
@app.get("/health")
async def health_check():
    """
    健康检查接口
    
    Returns:
        dict: 服务健康状态
    """
    return {"status": "healthy", "service": "code-detection-api"}


# 语言检测接口
@app.post("/api/detect-language")
async def detect_language(request: dict):
    """
    自动检测代码的编程语言类型
    
    Args:
        request: {"code": "代码字符串"}
        
    Returns:
        {
            "detected_language": "python/java/javascript/c/cpp/csharp",
            "confidence": 0.0-1.0,
            "reason": "检测原因"
        }
    """
    try:
        code = request.get("code", "").strip()
        
        if not code:
            return {
                "detected_language": None,
                "confidence": 0.0,
                "reason": "代码为空"
            }
        
        # 调用语言检测函数
        detected_lang, confidence, reason = detect_code_language(code)
        
        return {
            "detected_language": detected_lang,
            "confidence": confidence,
            "reason": reason
        }
        
    except Exception as e:
        error_msg = f"语言检测失败: {str(e)}"
        print(f"[API] 语言检测出错: {error_msg}")
        return {
            "detected_language": None,
            "confidence": 0.0,
            "reason": error_msg
        }


# 代码分析接口
def convert_numpy_types(obj):
    """递归转换numpy类型为Python原生类型"""
    import numpy as np
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    elif isinstance(obj, tuple):
        return [convert_numpy_types(item) for item in obj]
    return obj

@app.post("/api/analyze")
async def analyze_code(request: dict):
    """
    代码相似性分析接口
    
    Args:
        request: {
            "code_a": "代码片段A",
            "code_b": "代码片段B", 
            "language": "编程语言",
            "auto_detect": "是否自动检测语言"
        }
        
    Returns:
        dict: 分析结果，包含相似度评分、分析原因等
    """
    try:
        # 解析请求参数
        code_a = request.get("code_a", "").strip()
        code_b = request.get("code_b", "").strip()
        language = request.get("language", "python").lower()
        auto_detect = request.get("auto_detect", False)

        # 参数验证
        if not code_a or not code_b:
            return {"error": "请求必须包含非空的 'code_a' 和 'code_b' 字段"}
        
        if language not in ["python", "java", "javascript", "c", "cpp", "csharp", "go"]:
            return {"error": f"暂不支持的语言 '{language}'"}

        # 自动检测语言模式
        if auto_detect:
            detected_a, conf_a, reason_a = detect_code_language(code_a)
            detected_b, conf_b, reason_b = detect_code_language(code_b)
            
            # 检测失败处理
            if detected_a is None:
                return {
                    "error": f"代码A语言识别失败：{reason_a}。请检查代码格式或手动选择语言。",
                    "detected_language_a": None,
                    "detected_language_b": detected_b
                }
            
            if detected_b is None:
                return {
                    "error": f"代码B语言识别失败：{reason_b}。请检查代码格式或手动选择语言。",
                    "detected_language_a": detected_a,
                    "detected_language_b": None
                }
            
            # 语言一致性检查
            if detected_a != detected_b:
                lang_names = {
                    'python': 'Python',
                    'java': 'Java',
                    'javascript': 'JavaScript',
                    'c': 'C',
                    'cpp': 'C++',
                    'csharp': 'C#'
                }
                return {
                    "error": f"代码类型不一致！代码A是 {lang_names.get(detected_a, detected_a)}，代码B是 {lang_names.get(detected_b, detected_b)}。请确保两段代码使用相同的编程语言。",
                    "detected_language_a": detected_a,
                    "detected_language_b": detected_b
                }
            
            language = detected_a
            print(f"[API] 自动检测语言: {language} (A: {conf_a:.1%}, B: {conf_b:.1%})")
        else:
            # 手动选择语言模式 - 优先使用检测到的语言
            detected_a, conf_a, _ = detect_code_language(code_a)
            detected_b, conf_b, _ = detect_code_language(code_b)
            
            # 如果检测到语言且置信度较高，优先使用检测到的语言
            lang_names = {
                'python': 'Python',
                'java': 'Java',
                'javascript': 'JavaScript',
                'c': 'C',
                'cpp': 'C++',
                'csharp': 'C#'
            }
            
            # 优先使用检测到的语言（如果置信度 > 70% 且两段代码检测结果一致）
            if detected_a and detected_b and detected_a == detected_b and conf_a > 0.7 and conf_b > 0.7:
                if detected_a != language:
                    print(f"[INFO] 检测到代码语言为 {lang_names.get(detected_a, detected_a)} (A: {conf_a:.1%}, B: {conf_b:.1%})，将使用检测到的语言进行分析")
                    language = detected_a
                else:
                    print(f"[API] 手动选择语言: {language} (与检测结果一致)")
            else:
                # 语言不匹配警告
                if detected_a and detected_a != language:
                    print(f"[WARNING] 代码A检测到的是 {lang_names.get(detected_a, detected_a)}，但用户选择了 {lang_names.get(language, language)}。将使用用户选择的语言进行分析。")
                
                if detected_b and detected_b != language:
                    print(f"[WARNING] 代码B检测到的是 {lang_names.get(detected_b, detected_b)}，但用户选择了 {lang_names.get(language, language)}。将使用用户选择的语言进行分析。")
                
                print(f"[API] 手动选择语言: {language}")

        # 记录分析请求
        print(f"[API] 收到分析请求，语言: {language}, 代码A长度: {len(code_a)}, 代码B长度: {len(code_b)}")
        
        # 所有语言都使用智能体进行深度分析
        try:
            result = agent.analyze_code_similarity(code_a, code_b, language)
        except Exception as e:
            # 如果智能体分析失败，使用传统管道分析作为回退
            print(f"[API] 智能体分析失败，使用传统分析: {e}")
            p = analyze_pair(code_a, code_b, language)
            result = {
                "similarity_analysis": {
                    "score": p["final_score"],
                    "reason": p.get("reason", "智能体分析失败，使用传统分析"),
                    "function_summary": f"{language} 传统语义分析",
                },
                "metadata": {
                    "language": language,
                    "ast_a_root_type": p.get("ast_a_root_type", "unknown"),
                    "ast_b_root_type": p.get("ast_b_root_type", "unknown"),
                    "filter_layer": "agent_fallback",
                },
            }

        return convert_numpy_types(result)

    except Exception as e:
        error_msg = f"分析失败: {str(e)}"
        print(f"[API] 分析出错: {error_msg}")
        import traceback
        print(f"[API] 详细错误信息: {traceback.format_exc()}")
        return {"error": error_msg}