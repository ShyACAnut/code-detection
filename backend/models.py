# backend/models.py
"""
数据库模型定义
=============

这个文件定义了代码相似性检测系统的所有数据库模型。
使用SQLAlchemy ORM，支持SQLite数据库。

模型包括：
1. User - 用户模型（学生、教师、管理员、教学主任）
2. Assignment - 作业模型
3. Submission - 提交模型
4. SubmissionRevision - 提交修订历史
5. ComparisonResult - 比对结果
6. AnalysisTask - 分析任务
7. SystemConfig - 系统配置
8. DetectionEvidence - 检测证据
9. CodeIndexEntry - 代码索引条目
10. AuditLog - 审计日志

"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
from database import Base


class User(Base):
    """
    用户模型
    =======
    
    存储系统用户信息，包括学生、教师、管理员和教学主任。
    
    字段说明：
    - id: 用户唯一标识符
    - username: 用户名（唯一）
    - email: 邮箱地址（唯一）
    - hashed_password: bcrypt加密的密码
    - role: 用户角色（student/teacher/admin/dean）
    - created_at: 创建时间
    - requires_ethics_learning: 是否需要完成伦理学习（0=否，1=是）
    - required_cases_count: 需要完成的伦理案例数量
    
    关系：
    - submissions: 用户的所有提交记录
    - assignments: 教师创建的作业
    """
    __tablename__ = "users"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="student")  # 支持的角色：student, teacher, admin, dean
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 伦理学习相关字段
    requires_ethics_learning = Column(Integer, default=0)  # 是否需要完成伦理学习（0=否，1=是）
    required_cases_count = Column(Integer, default=3)  # 需要完成的伦理案例数量
    
    # 关系定义
    submissions = relationship("Submission", back_populates="student")  # 用户的所有提交
    assignments = relationship("Assignment", back_populates="teacher")  # 教师创建的作业


class Assignment(Base):
    """
    作业模型
    =======
    
    存储作业信息，包括标题、描述、语言、截止时间等。
    
    字段说明：
    - id: 作业唯一标识符
    - title: 作业标题
    - description: 作业描述
    - language: 编程语言（python/java/javascript/c/cpp/csharp）
    - deadline: 截止时间
    - created_by: 创建者用户ID
    - created_at: 创建时间
    
    关系：
    - teacher: 作业创建者（教师）
    - submissions: 该作业的所有提交
    """
    __tablename__ = "assignments"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)  # 作业标题
    description = Column(Text)  # 作业描述（支持长文本）
    language = Column(String)  # 编程语言：python / java / javascript / c / cpp / csharp
    deadline = Column(DateTime)  # 截止时间
    created_by = Column(Integer, ForeignKey("users.id"))  # 创建者用户ID
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    function_requirements = Column(Text, nullable=True)  # 功能需求描述
    scoring_guideline = Column(Text, nullable=True)  # 评分指南
    detection_threshold = Column(Float, default=80.0)  # 检测阈值（0-100），默认80%
    
    # 关系定义
    teacher = relationship("User", back_populates="assignments")  # 作业创建者
    submissions = relationship("Submission", back_populates="assignment")  # 该作业的所有提交


class Submission(Base):
    """
    提交模型
    =======
    
    存储学生作业提交信息，包括代码内容、提交时间等。
    
    字段说明：
    - id: 提交唯一标识符
    - student_id: 提交学生ID
    - assignment_id: 所属作业ID
    - code: 提交的代码内容
    - file_path: 文件上传路径（可选）
    - submitted_at: 提交时间
    - updated_at: 更新时间
    
    关系：
    - student: 提交学生
    - assignment: 所属作业
    - results: 该提交的所有比对结果
    - revisions: 该提交的修订历史
    """
    __tablename__ = "submissions"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))  # 提交学生ID
    assignment_id = Column(Integer, ForeignKey("assignments.id"))  # 所属作业ID
    code = Column(Text)  # 提交的代码内容
    file_path = Column(String)  # 如果是文件上传，保存路径
    submitted_at = Column(DateTime, default=datetime.utcnow)  # 提交时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    
    # 关系定义
    student = relationship("User", back_populates="submissions")  # 提交学生
    assignment = relationship("Assignment", back_populates="submissions")  # 所属作业
    results = relationship(
        "ComparisonResult",
        back_populates="submission",
        foreign_keys="[ComparisonResult.submission_id]"  # 明确指定使用 submission_id
    )  # 该提交的所有比对结果
    revisions = relationship("SubmissionRevision", back_populates="submission")  # 该提交的修订历史
    score = relationship("SubmissionScore", uselist=False, back_populates="submission")  # 该提交的评分


class SubmissionScore(Base):
    """
    学生提交评分模型
    ===============
    
    存储教师对学生作业的评分信息，包括总分和评语。
    
    字段说明：
    - id: 评分记录唯一标识符
    - submission_id: 所属提交ID
    - teacher_id: 评分教师ID
    - overall_score: 总分（100分制）
    - teacher_comments: 教师评语
    - criteria_scores: JSON格式存储各评分项得分
    - created_at: 创建时间
    - updated_at: 更新时间
    
    关系：
    - submission: 所属提交
    - teacher: 评分教师
    """
    __tablename__ = "submission_scores"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), unique=True)  # 与提交一对一
    teacher_id = Column(Integer, ForeignKey("users.id"))
    overall_score = Column(Float, nullable=False)
    teacher_comments = Column(Text, nullable=True)
    criteria_scores = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系定义
    submission = relationship("Submission", back_populates="score")
    teacher = relationship("User")


class SubmissionRevision(Base):
    """
    提交修订历史模型
    ===============
    
    存储代码提交的修订历史，用于版本控制和变更追踪。
    
    字段说明：
    - id: 修订记录唯一标识符
    - submission_id: 所属提交ID
    - code: 修订后的代码内容
    - file_path: 文件路径（可选）
    - edited_at: 编辑时间
    
    关系：
    - submission: 所属提交
    """
    __tablename__ = "submission_revisions"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), index=True)  # 所属提交ID
    code = Column(Text)  # 修订后的代码内容
    file_path = Column(String)  # 文件路径（可选）
    edited_at = Column(DateTime, default=datetime.utcnow)  # 编辑时间
    
    # 关系定义
    submission = relationship("Submission", back_populates="revisions")  # 所属提交


class ComparisonResult(Base):
    """
    比对结果模型
    ===========
    
    存储代码相似性比对的结果，包括相似度评分、分析详情等。
    
    字段说明：
    - id: 比对结果唯一标识符
    - submission_id: 被比对的提交ID（可选，用于关联作业提交）
    - compared_with_id: 与之比对的提交ID（可选）
    - task_id: 关联的分析任务ID（支持独立文件检测）
    - similarity_score: 相似度评分（0-100）
    - filter_layer: 过滤层标识
    - details: 详细分析结果（JSON格式）
    - created_at: 创建时间
    
    关系：
    - submission: 被比对的提交
    - compared_with: 与之比对的提交
    - task: 关联的分析任务
    """
    __tablename__ = "comparison_results"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)  # 被比对的提交ID（可选）
    compared_with_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)  # 与之比对的提交ID（可选）
    task_id = Column(Integer, ForeignKey("analysis_tasks.id"), nullable=True, index=True)  # 关联的分析任务ID
    similarity_score = Column(Float)  # 相似度评分（0-100）
    filter_layer = Column(String)  # 记录哪一层过滤得出的结果
    details = Column(Text)  # JSON存储详细分析结果
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    
    # 关系定义
    submission = relationship("Submission", foreign_keys=[submission_id], back_populates="results")  # 被比对的提交
    compared_with = relationship("Submission", foreign_keys=[compared_with_id])  # 与之比对的提交


class AnalysisTask(Base):
    """
    异步批量分析任务模型
    ==================
    
    存储作业维度的批量分析任务，支持异步处理。
    
    字段说明：
    - id: 任务唯一标识符
    - assignment_id: 关联的作业ID（可选，支持独立文件检测）
    - status: 任务状态（pending/running/completed/failed）
    - total_pairs: 总比对对数
    - processed_pairs: 已处理对数
    - error_message: 错误信息（可选）
    - file_content: 上传文件的内容（JSON格式，用于独立文件检测）
    - created_at: 创建时间
    - started_at: 开始运行时间
    - updated_at: 更新时间
    
    关系：
    - assignment: 关联的作业
    """
    __tablename__ = "analysis_tasks"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), index=True, nullable=True)  # 关联的作业ID（可选）
    status = Column(String, default="pending")  # 任务状态：pending/running/completed/failed
    total_pairs = Column(Integer, default=0)  # 总比对对数
    processed_pairs = Column(Integer, default=0)  # 已处理对数
    error_message = Column(Text, nullable=True)  # 错误信息（可选）
    file_content = Column(Text, nullable=True)  # 上传文件的内容（JSON格式）
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    started_at = Column(DateTime, nullable=True)  # 开始运行时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    
    # 关系定义
    assignment = relationship("Assignment")  # 关联的作业


class SystemConfig(Base):
    """
    系统配置模型
    ===========
    
    存储系统级别的配置参数，使用单例模式。
    
    字段说明：
    - id: 配置ID（固定为1）
    - similarity_threshold: 相似度阈值（0-100）
    - llm_model_name: LLM模型名称
    - syntax_weight: 语法权重（0-1）
    - semantic_weight: 语义权重（0-1）
    - updated_at: 更新时间
    
    注意：这是一个单例表，只有一条记录
    """
    __tablename__ = "system_config"
    
    # 基本字段
    id = Column(Integer, primary_key=True)  # 固定为1，单例模式
    similarity_threshold = Column(Float, default=80.0)  # 相似度阈值（0-100）
    llm_model_name = Column(String, default="glm-4.7")  # LLM模型名称
    syntax_weight = Column(Float, default=0.4)  # 语法权重（0-1）
    semantic_weight = Column(Float, default=0.6)  # 语义权重（0-1）
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间


class DetectionEvidence(Base):
    """
    检测证据模型
    ===========
    
    存储代码相似性检测的详细证据，用于分析和审计。
    
    字段说明：
    - id: 证据记录唯一标识符
    - comparison_result_id: 关联的比对结果ID
    - assignment_id: 关联的作业ID
    - submission_id: 提交ID
    - compared_with_id: 比对提交ID
    - language: 检测语言
    - syntax_score: 语法相似度评分
    - semantic_score: 语义相似度评分
    - final_score: 最终评分
    - model_name: 使用的模型名称
    - evidence_payload: 证据数据（JSON格式）
    - created_at: 创建时间
    
    关系：
    - comparison_result: 关联的比对结果
    """
    __tablename__ = "detection_evidences"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    comparison_result_id = Column(Integer, ForeignKey("comparison_results.id"), index=True)  # 关联的比对结果ID
    assignment_id = Column(Integer, ForeignKey("assignments.id"), index=True)  # 关联的作业ID
    submission_id = Column(Integer, ForeignKey("submissions.id"), index=True)  # 提交ID
    compared_with_id = Column(Integer, ForeignKey("submissions.id"), index=True)  # 比对提交ID
    language = Column(String)  # 检测语言
    syntax_score = Column(Float, default=-1.0)  # 语法相似度评分
    semantic_score = Column(Float, default=-1.0)  # 语义相似度评分
    final_score = Column(Float, default=-1.0)  # 最终评分
    model_name = Column(String, default="hybrid")  # 使用的模型名称
    evidence_payload = Column(Text)  # 证据数据（JSON格式）
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    
    # 关系定义
    comparison_result = relationship("ComparisonResult")  # 关联的比对结果


class CodeIndexEntry(Base):
    """
    代码索引条目模型
    ===============
    
    用于代码索引和快速检索，支持向量搜索的轻量级索引。
    
    字段说明：
    - id: 索引条目唯一标识符
    - submission_id: 关联的提交ID（唯一）
    - assignment_id: 关联的作业ID
    - language: 编程语言
    - normalized_hash: 归一化代码哈希
    - vector_stub: 向量占位符（用于ANN/milvus迁移）
    - updated_at: 更新时间
    
    关系：
    - submission: 关联的提交
    """
    __tablename__ = "code_index_entries"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), unique=True, index=True)  # 关联的提交ID（唯一）
    assignment_id = Column(Integer, ForeignKey("assignments.id"), index=True)  # 关联的作业ID
    language = Column(String)  # 编程语言
    normalized_hash = Column(String, index=True)  # 归一化代码哈希
    vector_stub = Column(Text)  # lightweight placeholder for ANN/milvus migration
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    
    # 关系定义
    submission = relationship("Submission")  # 关联的提交


class AuditLog(Base):
    """
    审计日志模型
    ===========
    
    记录系统操作日志，用于安全审计和问题追踪。
    
    字段说明：
    - id: 日志记录唯一标识符
    - actor_user_id: 操作用户ID（可选）
    - action: 操作类型
    - target_type: 目标类型（可选）
    - target_id: 目标ID（可选）
    - detail: 操作详情（可选）
    - ip_address: IP地址（可选）
    - user_agent: 用户代理（可选）
    - created_at: 创建时间
    
    索引：
    - action字段有索引，便于按操作类型查询
    """
    __tablename__ = "audit_logs"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)  # 操作用户ID（可选）
    action = Column(String, index=True)  # 操作类型
    target_type = Column(String, nullable=True)  # 目标类型（可选）
    target_id = Column(Integer, nullable=True)  # 目标ID（可选）
    detail = Column(Text, nullable=True)  # 操作详情（可选）
    ip_address = Column(String, nullable=True)  # IP地址（可选）
    user_agent = Column(String, nullable=True)  # 用户代理（可选）
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间


class CodeLibrary(Base):
    """
    代码库模型
    =========
    
    存储代码库中的代码文件，用于相似度检测的比对参考。
    
    字段说明：
    - id: 文件记录唯一标识符
    - filename: 文件名
    - language: 编程语言
    - content: 代码内容
    - file_size: 文件大小（字节）
    - is_public: 是否公开
    - uploaded_at: 上传时间
    """
    __tablename__ = "code_library"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)  # 文件名
    language = Column(String)  # 编程语言
    content = Column(Text)  # 代码内容
    file_size = Column(Integer)  # 文件大小（字节）
    is_public = Column(Integer, default=1)  # 是否公开（1=公开，0=私有）
    uploaded_at = Column(DateTime, default=datetime.utcnow)  # 上传时间


class Notification(Base):
    """
    整改通知模型
    ==========
    
    存储教师向学生发送的整改通知信息。
    
    字段说明：
    - id: 通知唯一标识符
    - student_id: 学生用户ID
    - teacher_id: 教师用户ID
    - assignment_id: 关联的作业ID
    - title: 通知标题
    - content: 通知内容
    - similarity_score: 相似度分数（可选）
    - priority: 优先级（low/normal/high）
    - is_read: 是否已读
    - created_at: 创建时间
    """
    __tablename__ = "notifications"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), index=True)  # 学生用户ID
    teacher_id = Column(Integer, ForeignKey("users.id"), index=True)  # 教师用户ID
    assignment_id = Column(Integer, ForeignKey("assignments.id"), index=True)  # 关联的作业ID
    title = Column(String)  # 通知标题
    content = Column(Text)  # 通知内容
    similarity_score = Column(Float, nullable=True)  # 相似度分数（可选）
    priority = Column(String, default="normal")  # 优先级：low/normal/high
    is_read = Column(Integer, default=0)  # 是否已读（0=未读，1=已读）
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    
    # 关系定义
    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])
    assignment = relationship("Assignment")


class LearningReport(Base):
    """
    学习报告推送模型
    ===============
    
    存储教师向学生推送的学习分析报告。
    
    字段说明：
    - id: 报告记录唯一标识符
    - student_id: 学生用户ID
    - teacher_id: 教师用户ID
    - report_content: 报告内容（JSON格式）
    - is_read: 学生是否已读
    - created_at: 创建时间
    - updated_at: 更新时间
    
    关系：
    - student: 关联的学生用户
    - teacher: 关联的教师用户
    """
    __tablename__ = "learning_reports"
    
    # 基本字段
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), index=True)  # 学生用户ID
    teacher_id = Column(Integer, ForeignKey("users.id"), index=True)  # 教师用户ID
    report_content = Column(Text)  # 报告内容（JSON格式）
    is_read = Column(Integer, default=0)  # 是否已读（0=未读，1=已读）
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间
    
    # 关系定义
    student = relationship("User", foreign_keys=[student_id])  # 关联的学生
    teacher = relationship("User", foreign_keys=[teacher_id])  # 关联的教师


class EthicsCase(Base):
    """
    编程伦理案例模型
    ==============
    
    存储编程伦理和学术诚信相关的学习案例。
    
    字段说明：
    - id: 案例唯一标识符
    - title: 案例标题
    - category: 案例类别（plagiarism/fair_use/attribution/collaboration/other）
    - description: 案例描述
    - scenario: 场景描述
    - outcome: 处理结果
    - consequences: 后果说明
    - prevention: 预防建议
    - is_active: 是否启用
    - created_at: 创建时间
    """
    __tablename__ = "ethics_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    category = Column(String, index=True)
    description = Column(Text)
    scenario = Column(Text)
    outcome = Column(Text)
    consequences = Column(Text)
    prevention = Column(Text)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class EthicsLearningRecord(Base):
    """
    伦理学习记录模型
    ==============
    
    记录学生的学习进度和查看历史。
    
    字段说明：
    - id: 记录唯一标识符
    - student_id: 学生用户ID
    - case_id: 案例ID
    - is_completed: 是否完成学习
    - completed_at: 完成时间
    - created_at: 查看时间
    """
    __tablename__ = "ethics_learning_records"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), index=True)
    case_id = Column(Integer, ForeignKey("ethics_cases.id"), index=True)
    is_completed = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("User")
    case = relationship("EthicsCase")


class AblationResult(Base):
    """
    消融实验结果模型
    ===============

    存储测试人员的批量检测结果，支持历史数据查询。

    字段说明：
    - id: 结果记录唯一标识符
    - user_id: 测试人员用户ID
    - mode: 检测模式（simple/vector/full/compare）
    - code_a_length: 代码A长度
    - code_b_length: 代码B长度
    - language: 编程语言
    - result_json: 完整检测结果（JSON格式）
    - similarity_score: 相似度评分（0-100）
    - comparison_time_ms: 比对耗时（毫秒）
    - obfuscation_type: 混淆类型（可选，用于自建数据集）
    - ground_truth_label: 人工标注的抄袭标签（0=原创，1=抄袭）
    - created_at: 创建时间

    关系：
    - user: 关联的测试人员
    """
    __tablename__ = "ablation_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    mode = Column(String, index=True)  # simple/vector/full/compare
    code_a_length = Column(Integer)
    code_b_length = Column(Integer)
    language = Column(String)
    result_json = Column(Text)  # 存储完整结果JSON
    similarity_score = Column(Float, nullable=True)  # 相似度评分（0-100）
    comparison_time_ms = Column(Float, nullable=True)  # 比对耗时（毫秒）
    obfuscation_type = Column(String, nullable=True)  # 混淆类型：变量重命名/冗余代码插入/循环递归互换/控制流平坦化
    ground_truth_label = Column(Integer, nullable=True)  # 人工标注：0=原创，1=抄袭
    error = Column(Text, nullable=True)  # 错误信息
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class AblationBatchTask(Base):
    """
    消融实验批量任务模型
    ===================
    
    存储批量检测任务的汇总信息，便于追踪和查看历史任务。
    
    字段说明：
    - id: 任务唯一标识符
    - user_id: 测试人员用户ID
    - mode: 检测模式
    - total_pairs: 总代码对数量
    - success_count: 成功数量
    - error_count: 失败数量
    - completion_rate: 完成率
    - summary_json: 汇总统计（JSON格式）
    - status: 任务状态（running/completed/failed）
    - created_at: 创建时间
    - completed_at: 完成时间（可选）
    
    关系：
    - user: 关联的测试人员
    """
    __tablename__ = "ablation_batch_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    mode = Column(String, index=True)
    total_pairs = Column(Integer)
    current_index = Column(Integer, default=0)  # 当前处理到的索引（用于断点续测）
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)
    summary_json = Column(Text)  # 汇总统计JSON
    status = Column(String, default="running")  # running/paused/completed/failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User")