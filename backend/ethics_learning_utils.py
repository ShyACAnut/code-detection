from database import get_db
from models import User
from sqlalchemy import text

HIGH_RISK_THRESHOLD = 80

def trigger_ethics_learning(student_id: int, db):
    """
    当学生相似度达到高风险或收到整改通知时，触发伦理学习要求

    参数:
        student_id: 学生ID
        db: 数据库会话
    """
    student = db.query(User).filter(User.id == student_id).first()
    if not student or student.role != 'student':
        return False

    student.requires_ethics_learning = 1
    student.required_cases_count = 3  # 默认要求学习3个案例
    
    # 重置之前的学习记录，确保每次触发都需要重新学习
    reset_ethics_learning_progress(student_id, db)
    
    db.commit()
    return True


def reset_ethics_learning_progress(student_id: int, db):
    """
    重置学生的伦理学习进度（清除所有已完成记录）
    
    当学生完成学习或重新触发学习要求时调用此函数。

    参数:
        student_id: 学生ID
        db: 数据库会话
    """
    from models import EthicsLearningRecord
    db.query(EthicsLearningRecord).filter(
        EthicsLearningRecord.student_id == student_id
    ).delete(synchronize_session=False)
    db.commit()

def check_and_notify_high_risk(submission_id: int, compared_with_id: int, similarity_score: float, db):
    """
    检查比对结果是否为高风险，如果是则触发伦理学习要求

    参数:
        submission_id: 提交ID
        compared_with_id: 被比较的提交ID
        similarity_score: 相似度得分
        db: 数据库会话
    """
    if similarity_score < HIGH_RISK_THRESHOLD:
        return

    from models import Submission
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return

    student = db.query(User).filter(User.id == submission.student_id).first()
    if not student or student.role != 'student':
        return

    if not student.requires_ethics_learning:
        trigger_ethics_learning(submission.student_id, db)
        print(f"[伦理学习触发] 学生 {submission.student_id} 的提交 {submission_id} 与提交 {compared_with_id} 相似度达到 {similarity_score}%，已触发伦理学习要求")

def check_ethics_learning_completed(student_id: int, db) -> bool:
    """
    检查学生是否已完成要求的伦理学习

    参数:
        student_id: 学生ID
        db: 数据库会话

    返回:
        True if completed, False otherwise
    """
    student = db.query(User).filter(User.id == student_id).first()
    if not student or not student.requires_ethics_learning:
        return True  # 不需要学习，视为完成

    # 获取已完成的案例数
    from models import EthicsLearningRecord
    completed_count = db.query(EthicsLearningRecord).filter(
        EthicsLearningRecord.student_id == student_id,
        EthicsLearningRecord.is_completed == 1
    ).count()

    return completed_count >= student.required_cases_count

def clear_ethics_learning_requirement(student_id: int, db):
    """
    清除学生的伦理学习要求（当完成学习后调用）

    参数:
        student_id: 学生ID
        db: 数据库会话
    """
    student = db.query(User).filter(User.id == student_id).first()
    if student:
        student.requires_ethics_learning = 0
        db.commit()

def get_student_ethics_status(student_id: int, db) -> dict:
    """
    获取学生的伦理学习状态

    返回:
        dict with keys: requires_learning, required_count, completed_count, remaining_count
    """
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        return {
            'requires_learning': False,
            'required_count': 0,
            'completed_count': 0,
            'remaining_count': 0
        }

    from models import EthicsLearningRecord
    completed_count = db.query(EthicsLearningRecord).filter(
        EthicsLearningRecord.student_id == student_id,
        EthicsLearningRecord.is_completed == 1
    ).count()

    if student.requires_ethics_learning:
        required_count = student.required_cases_count or 3
        return {
            'requires_learning': True,
            'required_count': required_count,
            'completed_count': completed_count,
            'remaining_count': max(0, required_count - completed_count)
        }
    else:
        return {
            'requires_learning': False,
            'required_count': 0,
            'completed_count': completed_count,
            'remaining_count': 0
        }
