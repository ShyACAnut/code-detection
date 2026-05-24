"""
数据验证模式定义
===============

这个文件定义了Pydantic数据验证模式，用于API请求和响应的数据验证。
使用Pydantic v2语法，支持类型提示和自动序列化。

主要功能：
1. 用户相关数据验证
2. 作业相关数据验证  
3. 提交相关数据验证
4. 比对结果数据验证
5. 系统配置数据验证
6. 管理员统计数据验证

每个模式都包含详细的字段说明和业务逻辑注释。
"""

from pydantic import BaseModel, field_serializer
from typing import Optional, List
from datetime import datetime
from pydantic import ConfigDict

# ============================================================================
# 用户相关数据验证模式
# ============================================================================

class UserBase(BaseModel):
    """
    用户基础数据模式
    ==============
    
    功能：
    - 定义用户的基本信息字段
    - 作为其他用户模式的基类
    
    字段说明：
    - username: 用户名（必填，唯一）
    - email: 邮箱地址（必填，唯一）
    - role: 用户角色（可选，默认为"student"）
    """
    username: str
    email: str
    role: str = "student"

class UserCreate(UserBase):
    """
    用户创建数据模式
    ==============
    
    功能：
    - 用于创建新用户时的数据验证
    - 继承UserBase的所有字段
    - 添加密码字段用于初始设置
    
    字段说明：
    - password: 明文密码（将在后端进行bcrypt加密）
    """
    password: str

class User(UserBase):
    """
    用户响应数据模式
    ==============
    
    功能：
    - 用于返回用户信息给前端
    - 包含数据库生成的字段
    - 支持从ORM对象自动序列化
    
    字段说明：
    - id: 用户唯一标识符（数据库生成）
    - created_at: 用户创建时间（数据库生成）
    """
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# ============================================================================
# 认证相关数据验证模式
# ============================================================================

class Token(BaseModel):
    """
    JWT令牌响应模式
    ==============
    
    功能：
    - 用于返回JWT认证令牌给前端
    - 包含访问令牌和令牌类型
    
    字段说明：
    - access_token: JWT访问令牌字符串
    - token_type: 令牌类型（固定为"bearer"）
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    JWT令牌数据模式
    ==============
    
    功能：
    - 用于解析JWT令牌中的数据
    - 包含用户身份验证信息
    
    字段说明：
    - username: 从令牌中提取的用户名（可选）
    """
    username: Optional[str] = None

# ============================================================================
# 作业相关数据验证模式
# ============================================================================

class AssignmentBase(BaseModel):
    """
    作业基础数据模式
    ==============
    
    功能：
    - 定义作业的基本信息字段
    - 作为其他作业模式的基类
    
    字段说明：
    - title: 作业标题（必填）
    - description: 作业描述（必填）
    - language: 编程语言（必填，如"python", "java", "c++"等）
    - deadline: 截止时间（必填，datetime格式）
    - function_requirements: 功能需求描述（可选）
    - scoring_guideline: 评分指南（可选）
    - detection_threshold: 检测阈值（可选，0-100，默认80）
    """
    title: str
    description: str
    language: str
    deadline: datetime
    function_requirements: Optional[str] = None
    scoring_guideline: Optional[str] = None
    detection_threshold: Optional[float] = 80.0

class AssignmentCreate(AssignmentBase):
    """
    作业创建数据模式
    ==============
    
    功能：
    - 用于创建新作业时的数据验证
    - 继承AssignmentBase的所有字段
    - 不需要额外字段，因为创建者信息由后端自动填充
    
    使用说明：
    - 创建作业时，后端会自动填充created_by字段
    """
    pass

class Assignment(AssignmentBase):
    """
    作业响应数据模式
    ==============
    
    功能：
    - 用于返回作业信息给前端
    - 包含数据库生成的字段
    - 支持从ORM对象自动序列化
    
    字段说明：
    - id: 作业唯一标识符（数据库生成）
    - created_by: 创建者用户ID（数据库生成）
    - created_at: 作业创建时间（数据库生成）
    """
    id: int
    created_by: int
    created_at: datetime
    class Config:
        from_attributes = True

class AssignmentWithCreator(Assignment):
    """
    作业列表响应模式（含创建者信息）
    ================================
    
    功能：
    - 用于作业列表页面显示
    - 扩展Assignment模式，添加创建者信息
    - 包含提交统计信息和检测阈值
    
    字段说明：
    - creator_name: 创建者用户名（可选，用于显示）
    - submission_count: 该作业的提交数量（可选，用于统计）
    - detection_threshold: 检测阈值（0-100，默认80）
    """
    creator_name: Optional[str] = None
    submission_count: Optional[int] = 0
    detection_threshold: Optional[float] = 80.0

# ============================================================================
# 提交相关数据验证模式
# ============================================================================

class SubmissionBase(BaseModel):
    """
    提交基础数据模式
    ==============
    
    功能：
    - 定义代码提交的基本信息字段
    - 作为其他提交模式的基类
    
    字段说明：
    - code: 提交的代码内容（必填，字符串格式）
    - assignment_id: 关联的作业ID（必填，外键）
    """
    code: str
    assignment_id: int

class SubmissionCreate(SubmissionBase):
    """
    提交创建数据模式
    ==============
    
    功能：
    - 用于创建新提交时的数据验证
    - 继承SubmissionBase的所有字段
    - 不需要额外字段，因为学生信息由后端自动填充
    
    使用说明：
    - 创建提交时，后端会自动填充student_id字段
    - 自动设置submitted_at和updated_at时间戳
    """
    pass

class Submission(SubmissionBase):
    """
    提交响应数据模式
    ==============
    
    功能：
    - 用于返回提交信息给前端
    - 包含数据库生成的字段
    - 支持从ORM对象自动序列化
    
    字段说明：
    - id: 提交唯一标识符（数据库生成）
    - student_id: 提交学生用户ID（数据库生成）
    - submitted_at: 提交时间（数据库生成）
    - updated_at: 最后更新时间（可选，数据库生成）
    """
    id: int
    student_id: int
    submitted_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class SubmissionRevision(BaseModel):
    """
    提交修订历史模式
    ================
    
    功能：
    - 用于记录代码提交的修订历史
    - 支持代码版本管理和回溯
    - 支持从ORM对象自动序列化
    
    字段说明：
    - id: 修订记录唯一标识符
    - submission_id: 关联的提交ID
    - code: 修订后的代码内容
    - file_path: 代码文件路径（可选，用于文件存储）
    - edited_at: 修订时间
    
    使用场景：
    - 学生修改已提交的代码时创建新修订
    - 教师查看代码修改历史
    - 代码版本控制和审计
    """
    id: int
    submission_id: int
    code: str
    file_path: Optional[str] = None
    edited_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# 比对结果相关数据验证模式
# ============================================================================

class ComparisonResultBase(BaseModel):
    """
    比对结果基础数据模式
    ===================
    
    功能：
    - 定义代码比对结果的基本信息字段
    - 作为其他比对结果模式的基类
    
    字段说明：
    - similarity_score: 相似度得分（0.0-1.0之间的浮点数）
    - filter_layer: 过滤层说明（如"语法层"、"语义层"等）
    - details: 比对详情描述（JSON格式字符串）
    """
    similarity_score: float
    filter_layer: str
    details: str

class ComparisonResult(ComparisonResultBase):
    """
    比对结果完整数据模式
    ====================
    
    功能：
    - 用于存储和返回完整的比对结果信息
    - 包含数据库生成的字段
    - 支持从ORM对象自动序列化
    
    字段说明：
    - id: 比对结果唯一标识符（数据库生成）
    - submission_id: 被比对的提交ID（外键）
    - compared_with_id: 与之比对的提交ID（外键）
    - created_at: 比对创建时间（数据库生成）
    
    业务逻辑：
    - 每个结果记录两个提交之间的比对
    - similarity_score越高表示相似度越大
    - details字段包含具体的匹配信息
    """
    id: int
    submission_id: int
    compared_with_id: int
    created_at: datetime
    class Config:
       from_attributes = True


class SubmissionWithStudent(Submission):
    """
    提交列表响应模式（含学生信息）
    =============================
    
    功能：
    - 用于教师查看作业提交列表
    - 扩展Submission模式，添加学生信息
    - 支持从ORM对象自动序列化
    
    字段说明：
    - student_name: 学生用户名（用于显示）
    
    使用场景：
    - 教师查看某个作业的所有提交
    - 显示提交者和提交时间
    """
    student_name: str


class SubmissionWithAssignmentTitle(Submission):
    """
    我的提交列表响应模式（含作业信息）
    ===============================
    
    功能：
    - 用于学生查看自己的提交历史
    - 扩展Submission模式，添加作业信息
    - 包含分析状态和相似度信息
    
    字段说明：
    - assignment_title: 作业标题（用于显示）
    - analysis_status: 分析状态（pending|running|completed）
    - highest_similarity: 最高相似度得分（可选）
    - analysis_reason: 分析原因说明（可选）
    
    使用场景：
    - 学生查看自己的提交历史
    - 显示作业标题和分析进度
    - 展示相似度检测结果
    """
    assignment_title: str
    analysis_status: Optional[str] = None  # pending | running | completed
    highest_similarity: Optional[float] = None
    analysis_reason: Optional[str] = None


class ComparisonResultPublic(BaseModel):
    """
    比对结果公开数据模式
    ===================
    
    功能：
    - 用于不同角色查看比对结果
    - 根据角色显示不同级别的信息
    - 支持从ORM对象自动序列化
    
    字段说明：
    - id: 比对结果唯一标识符
    - submission_id: 被比对的提交ID
    - similarity_score: 相似度得分
    - filter_layer: 过滤层说明
    - details: 比对详情描述
    - created_at: 比对创建时间
    - compared_with_id: 与之比对的提交ID（可选，学生端匿名）
    - peer_label: 对方标签（可选，用于显示对方身份）
    
    角色差异：
    - 学生端：compared_with_id和peer_label可能为空（匿名）
    - 教师端：显示完整的比对信息
    """
    id: int
    submission_id: int
    similarity_score: float
    filter_layer: str
    details: str
    created_at: datetime
    compared_with_id: Optional[int] = None
    peer_label: Optional[str] = None


# ============================================================================
# 分析任务相关数据验证模式
# ============================================================================

class AnalysisTaskOut(BaseModel):
    """
    分析任务输出数据模式
    ==================
    
    功能：
    - 用于返回代码分析任务的状态和进度
    - 支持从ORM对象自动序列化
    
    字段说明：
    - id: 任务唯一标识符
    - assignment_id: 关联的作业ID
    - status: 任务状态（pending|running|completed|failed）
    - total_pairs: 需要比对的总对数
    - processed_pairs: 已处理的对数
    - error_message: 错误信息（可选，任务失败时）
    - created_at: 任务创建时间
    - started_at: 任务开始运行时间（可选）
    - updated_at: 任务最后更新时间
    
    使用场景：
    - 查看分析任务进度
    - 监控批量比对任务状态
    - 显示任务完成百分比
    """
    id: int
    assignment_id: Optional[int] = None
    status: str
    total_pairs: int
    processed_pairs: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('created_at', 'started_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        # 添加UTC时区标记
        if dt.tzinfo is None:
            return dt.isoformat() + "Z"
        return dt.isoformat()


class AnalysisTaskCreateWithFiles(BaseModel):
    """创建分析任务并上传文件"""
    assignment_id: Optional[int] = None
    file_type: str  # "json" or "zip"


class AnalysisTaskResultItem(BaseModel):
    """分析任务中的单个比对结果项"""
    submission_a_id: int
    submission_b_id: int
    similarity_score: float
    reason: Optional[str] = None


class AnalysisTaskProgress(BaseModel):
    """分析任务进度和实时结果"""
    task_id: int
    assignment_id: Optional[int] = None
    status: str
    total_pairs: int
    processed_pairs: int
    results: List[AnalysisTaskResultItem] = []


# ============================================================================
# 管理员相关数据验证模式
# ============================================================================

class AdminUserOut(BaseModel):
    """
    管理员用户输出数据模式
    =====================
    
    功能：
    - 用于管理员查看用户信息
    - 包含用户的基本信息
    - 支持从ORM对象自动序列化
    
    字段说明：
    - id: 用户唯一标识符
    - username: 用户名
    - email: 邮箱地址
    - role: 用户角色（student|teacher|admin|dean）
    - created_at: 用户创建时间
    
    使用场景：
    - 管理员用户管理界面
    - 用户列表显示
    - 用户信息查询
    """
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class ResetPasswordBody(BaseModel):
    """
    密码重置请求数据模式
    ===================
    
    功能：
    - 用于管理员重置用户密码
    - 验证新密码的格式
    
    字段说明：
    - new_password: 新密码（明文，将在后端进行bcrypt加密）
    
    使用场景：
    - 管理员重置用户密码
    - 用户忘记密码时重置
    """
    new_password: str


# ============================================================================
# 系统配置相关数据验证模式
# ============================================================================

class SystemConfigOut(BaseModel):
    """
    系统配置输出数据模式
    ==================
    
    功能：
    - 用于返回系统当前配置信息
    - 包含相似度检测的参数设置
    - 支持从ORM对象自动序列化
    
    字段说明：
    - similarity_threshold: 相似度阈值（0.0-1.0，超过此值认为相似）
    - llm_model_name: 使用的LLM模型名称
    - syntax_weight: 语法权重（可选，用于加权计算）
    - semantic_weight: 语义权重（可选，用于加权计算）
    - updated_at: 配置最后更新时间（可选）
    
    使用场景：
    - 系统配置管理界面
    - 查看当前检测参数
    - 配置修改历史记录
    """
    similarity_threshold: float
    llm_model_name: str
    syntax_weight: Optional[float] = None
    semantic_weight: Optional[float] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SystemConfigUpdate(BaseModel):
    """
    系统配置更新数据模式
    ===================
    
    功能：
    - 用于更新系统配置参数
    - 所有字段都是可选的，支持部分更新
    - 验证输入参数的格式和范围
    
    字段说明：
    - similarity_threshold: 相似度阈值（可选，0.0-1.0范围）
    - llm_model_name: LLM模型名称（可选）
    - syntax_weight: 语法权重（可选，非负数）
    - semantic_weight: 语义权重（可选，非负数）
    
    使用场景：
    - 管理员修改系统配置
    - 批量配置更新
    - 配置回滚操作
    """
    similarity_threshold: Optional[float] = None
    llm_model_name: Optional[str] = None
    syntax_weight: Optional[float] = None
    semantic_weight: Optional[float] = None


# ============================================================================
# 管理员统计相关数据验证模式
# ============================================================================

class AdminStatsOut(BaseModel):
    """
    管理员统计数据输出模式
    =====================
    
    功能：
    - 用于返回系统统计信息
    - 包含用户、作业、提交和比对的数量统计
    - 支持从ORM对象自动序列化
    
    字段说明：
    - user_count: 系统用户总数
    - assignment_count: 作业总数
    - submission_count: 提交总数
    - comparison_count: 比对结果总数
    - avg_similarity: 平均相似度得分（可选）
    
    使用场景：
    - 管理员仪表板
    - 系统使用情况统计
    - 数据分析和报告
    """
    user_count: int
    assignment_count: int
    submission_count: int
    comparison_count: int
    avg_similarity: Optional[float] = None


# ============================================================================
# 评分相关数据验证模式
# ============================================================================

class SubmissionScoreBase(BaseModel):
    """
    评分基础数据模式
    ===============
    
    功能：
    - 定义评分的基本信息字段
    - 作为其他评分模式的基类
    
    字段说明：
    - overall_score: 总分（0-100）
    - teacher_comments: 教师评语（可选）
    - criteria_scores: 各评分项得分JSON（可选）
    """
    overall_score: float
    teacher_comments: Optional[str] = None
    criteria_scores: Optional[dict] = None


class SubmissionScoreCreate(SubmissionScoreBase):
    """
    评分创建/更新数据模式
    ====================
    
    功能：
    - 用于教师创建或更新评分
    - 继承SubmissionScoreBase的所有字段
    - submission_id由URL路径参数提供
    """
    pass


class SubmissionScoreOut(SubmissionScoreBase):
    """
    评分响应数据模式
    ===============
    
    功能：
    - 用于返回评分信息给前端
    - 包含数据库生成的字段
    - 支持从ORM对象自动序列化
    
    字段说明：
    - id: 评分记录ID
    - submission_id: 所属提交ID
    - teacher_id: 评分教师ID
    - teacher_name: 评分教师用户名（可选，用于显示）
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    id: int
    submission_id: int
    teacher_id: int
    teacher_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubmissionWithScore(BaseModel):
    """
    提交详情（含评分）数据模式
    =========================
    
    功能：
    - 用于返回包含评分信息的提交详情
    - 包含提交信息和评分信息
    - 用于学生查看自己的评分
    """
    id: int
    student_name: str
    code: str
    submitted_at: datetime
    score: Optional[SubmissionScoreOut] = None
    
    class Config:
        from_attributes = True