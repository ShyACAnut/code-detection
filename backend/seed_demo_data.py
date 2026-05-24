"""
向 SQLite 数据库写入大量演示数据（教师、学生、作业、提交、比对结果）。
用法（在 backend 目录下）:
  python seed_demo_data.py
  python seed_demo_data.py --reset   # 先删除 demo_ 前缀账号及相关作业数据再写入

登录示例:
  教师: demo_teacher / demo123456
  学生: demo_student_001 / demo123456
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone

from database import Base, SessionLocal, engine
from auth_utils import get_password_hash
import models

# 规模（可按需调大）
NUM_STUDENTS = 35
NUM_ASSIGNMENTS = 8
# 每份作业有多少名学生提交（<= NUM_STUDENTS）
SUBMITTERS_PER_ASSIGNMENT = 28

DEMO_PREFIX = "demo_"


def _ensure_tables():
    Base.metadata.create_all(bind=engine)


def _reset_demo_data(db):
    """删除用户名以 demo_ 开头的用户及其关联数据（SQLite 无外键级联时需按顺序删）"""
    users = db.query(models.User).filter(models.User.username.like(f"{DEMO_PREFIX}%")).all()
    uids = [u.id for u in users]
    if not uids:
        print("没有 demo_ 用户需要清理。")
        return

    aids = [a.id for a in db.query(models.Assignment).filter(models.Assignment.created_by.in_(uids)).all()]
    q_sub = db.query(models.Submission).filter(
        (models.Submission.assignment_id.in_(aids)) | (models.Submission.student_id.in_(uids))
    )
    sids = [s.id for s in q_sub.all()]

    if sids:
        db.query(models.ComparisonResult).filter(
            (models.ComparisonResult.submission_id.in_(sids))
            | (models.ComparisonResult.compared_with_id.in_(sids))
        ).delete(synchronize_session=False)
        db.query(models.Submission).filter(models.Submission.id.in_(sids)).delete(synchronize_session=False)

    if aids:
        db.query(models.Assignment).filter(models.Assignment.id.in_(aids)).delete(synchronize_session=False)

    db.query(models.User).filter(models.User.id.in_(uids)).delete(synchronize_session=False)
    db.commit()
    print(f"已清理 demo 用户 {len(uids)} 个及相关作业/提交/比对。")


def _sample_code(language: str, student_idx: int, assign_idx: int) -> str:
    """生成略有差异的代码片段，便于列表里看出区别"""
    if language == "java":
        return f"""public class Main_{student_idx}_{assign_idx} {{
    public static void main(String[] args) {{
        int s = 0;
        for (int i = 1; i <= {10 + (student_idx % 5)}; i++) s += i;
        System.out.println(s);
    }}
}}"""
    return f"""def task_{assign_idx}_s{student_idx}(n: int = {20 + student_idx}) -> int:
    total = 0
    for x in range(1, n + 1):
        total += x ** {1 + (assign_idx % 2)}
    return total

if __name__ == "__main__":
    print(task_{assign_idx}_s{student_idx}())
"""


def _fake_details_json(score: float, layer: str) -> str:
    return json.dumps(
        {
            "similarity_analysis": {
                "score": int(round(score)),
                "reason": "演示数据：随机生成的比对摘要，用于教师端列表与导出预览。",
                "function_summary": "seed",
            },
            "metadata": {"filter_layer": layer, "language": "python"},
        },
        ensure_ascii=False,
    )


def seed(*, skip_if_demo_exists: bool = True):
    _ensure_tables()
    db = SessionLocal()
    try:
        pw = get_password_hash("demo123456")

        existing_teacher = db.query(models.User).filter(models.User.username == f"{DEMO_PREFIX}teacher").first()
        if existing_teacher and skip_if_demo_exists:
            ac = (
                db.query(models.Assignment)
                .filter(models.Assignment.created_by == existing_teacher.id)
                .count()
            )
            if ac > 0:
                print(
                    f"已存在演示教师账号及 {ac} 份作业，跳过写入。\n"
                    "若要清空并重新生成，请执行: python seed_demo_data.py --reset"
                )
                return

        teacher = db.query(models.User).filter(models.User.username == f"{DEMO_PREFIX}teacher").first()
        if not teacher:
            teacher = models.User(
                username=f"{DEMO_PREFIX}teacher",
                email=f"{DEMO_PREFIX}teacher@example.com",
                hashed_password=pw,
                role="teacher",
            )
            db.add(teacher)
            db.commit()
            db.refresh(teacher)
            print("已创建教师:", teacher.username)
        else:
            print("已存在教师:", teacher.username)

        students: list[models.User] = []
        for i in range(1, NUM_STUDENTS + 1):
            uname = f"{DEMO_PREFIX}student_{i:03d}"
            u = db.query(models.User).filter(models.User.username == uname).first()
            if not u:
                u = models.User(
                    username=uname,
                    email=f"{DEMO_PREFIX}s{i:03d}@example.com",
                    hashed_password=pw,
                    role="student",
                )
                db.add(u)
                students.append(u)
            else:
                students.append(u)
        db.commit()
        for u in students:
            db.refresh(u)
        print(f"学生账号数量: {len(students)}（含已存在的）")

        now = datetime.now(timezone.utc).replace(tzinfo=None)  # 与 SQLite 存 utc  naive 一致
        assignments: list[models.Assignment] = []
        langs = ["python", "java"]

        for a in range(1, NUM_ASSIGNMENTS + 1):
            title = f"第{a}次实验 — 算法与实现（演示 #{a}）"
            desc = (
                f"【演示作业】共 {NUM_STUDENTS} 名学生账号；"
                f"本作业约 {SUBMITTERS_PER_ASSIGNMENT} 人提交；"
                "教师端可查看提交列表、批量检测、结果表与导出。"
            )
            ass = models.Assignment(
                title=title,
                description=desc,
                language=langs[a % 2],
                deadline=now + timedelta(days=14 - (a % 7)),
                created_by=teacher.id,
                created_at=now - timedelta(days=NUM_ASSIGNMENTS - a),
            )
            db.add(ass)
            assignments.append(ass)
        db.commit()
        for x in assignments:
            db.refresh(x)
        print(f"已创建作业: {len(assignments)} 份")

        # 每个作业选择若干学生提交（轮换，使数据更“满”）
        all_submissions: dict[int, list[models.Submission]] = {}
        rnd = random.Random(42)
        for assign_idx, ass in enumerate(assignments, start=1):
            subs: list[models.Submission] = []
            indices = list(range(len(students)))
            rnd.shuffle(indices)
            pick = indices[: min(SUBMITTERS_PER_ASSIGNMENT, len(students))]
            for order, si in enumerate(pick):
                st = students[si]
                sub = models.Submission(
                    student_id=st.id,
                    assignment_id=ass.id,
                    code=_sample_code(ass.language, si + 1, assign_idx),
                    submitted_at=now - timedelta(hours=48 - order, minutes=order * 3),
                )
                db.add(sub)
                subs.append(sub)
            db.commit()
            for s in subs:
                db.refresh(s)
            all_submissions[ass.id] = subs
            print(f"  作业 id={ass.id} 提交数: {len(subs)}")

        # 为每个作业生成两两比对结果（演示用，不调用 LLM）
        total_pairs = 0
        layers = ["hash", "ast", "vector", "llm"]
        for ass in assignments:
            subs = all_submissions[ass.id]
            if len(subs) < 2:
                continue
            for i in range(len(subs)):
                for j in range(i + 1, len(subs)):
                    a, b = subs[i], subs[j]
                    score = float(rnd.uniform(12, 96))
                    layer = layers[int(score) % len(layers)]
                    db.add(
                        models.ComparisonResult(
                            submission_id=a.id,
                            compared_with_id=b.id,
                            similarity_score=round(score, 2),
                            filter_layer=layer,
                            details=_fake_details_json(score, layer),
                        )
                    )
                    total_pairs += 1
            db.commit()
        print(f"已写入比对结果行数: {total_pairs}")

        print("\n=== 完成 ===")
        print("教师登录: demo_teacher / demo123456")
        print("学生登录: demo_student_001 ~ demo_student_{:03d} / demo123456".format(NUM_STUDENTS))
        print("打开教师端「作业管理」→「查看提交」即可看到列表与结果。")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="先删除所有 demo_ 用户及其作业数据")
    args = parser.parse_args()

    _ensure_tables()
    if args.reset:
        db = SessionLocal()
        try:
            _reset_demo_data(db)
        finally:
            db.close()

    seed(skip_if_demo_exists=not args.reset)


if __name__ == "__main__":
    main()
