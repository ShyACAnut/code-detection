# backend/routers/assignments.py
import json
import os
import shutil
import subprocess
import tempfile
import threading
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from auth_utils import get_current_active_user, role_required, roles_required
from database import get_db
from report_builder import ReportPair, build_assignment_report_markdown
from assignment_analysis import execute_analysis_task_thread, run_pairwise_batch_and_persist

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("/", response_model=List[schemas.AssignmentWithCreator])
def get_assignments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    获取作业列表 - 根据角色过滤
    
    - 学生(student): 可以看到所有已发布的作业
    - 教师(teacher): 只能看到自己创建的作业
    - 教学主任(dean): 可以看到所有已发布的作业
    """
    query = db.query(models.Assignment)
    
    # 根据角色过滤
    if current_user.role == "teacher":
        # 教师只能看到自己创建的作业
        query = query.filter(models.Assignment.created_by == current_user.id)
    elif current_user.role == "student":
        # 学生可以看到所有作业（已发布的）
        pass
    elif current_user.role == "dean":
        # 教学主任可以看到所有作业
        pass
    elif current_user.role == "admin":
        # 管理员可以看到所有作业
        pass
    else:
        # 其他角色返回空列表
        return []
    
    assignments = query.order_by(models.Assignment.created_at.desc()).all()
    
    # 获取创建者信息和提交数量
    result = []
    for assignment in assignments:
        # 获取创建者用户名
        creator = db.query(models.User).filter(models.User.id == assignment.created_by).first()
        creator_name = creator.username if creator else "未知"
        
        # 获取提交数量
        submission_count = db.query(models.Submission).filter(
            models.Submission.assignment_id == assignment.id
        ).count()
        
        result.append(schemas.AssignmentWithCreator(
            id=assignment.id,
            title=assignment.title,
            description=assignment.description,
            language=assignment.language,
            deadline=assignment.deadline,
            created_by=assignment.created_by,
            created_at=assignment.created_at,
            creator_name=creator_name,
            submission_count=submission_count,
            detection_threshold=getattr(assignment, 'detection_threshold', 80.0)
        ))
    
    return result


# 获取单个作业详情
@router.get("/{assignment_id}", response_model=schemas.AssignmentWithCreator)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # 获取创建者用户名
    creator = db.query(models.User).filter(models.User.id == assignment.created_by).first()
    creator_name = creator.username if creator else "未知"
    
    # 获取提交数量
    submission_count = db.query(models.Submission).filter(
        models.Submission.assignment_id == assignment.id
    ).count()
    
    return schemas.AssignmentWithCreator(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        language=assignment.language,
        deadline=assignment.deadline,
        created_by=assignment.created_by,
        created_at=assignment.created_at,
        creator_name=creator_name,
        submission_count=submission_count,
        detection_threshold=getattr(assignment, 'detection_threshold', 80.0)
    )


# 获取某个作业的提交列表（含学生用户名）
@router.get("/{assignment_id}/submissions", response_model=List[schemas.SubmissionWithStudent])
def get_assignment_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")


    latest_time_subquery = (
        db.query(
            models.Submission.student_id.label("student_id"),
            models.Submission.assignment_id.label("assignment_id"),
            func.max(models.Submission.submitted_at).label("latest_submitted_at"),
        )
        .filter(models.Submission.assignment_id == assignment_id)
        .group_by(models.Submission.student_id, models.Submission.assignment_id)
        .subquery()
    )

    q = (
        db.query(models.Submission, models.User.username)
        .join(
            latest_time_subquery,
            (models.Submission.student_id == latest_time_subquery.c.student_id)
            & (models.Submission.assignment_id == latest_time_subquery.c.assignment_id)
            & (models.Submission.submitted_at == latest_time_subquery.c.latest_submitted_at),
        )
        .join(models.User, models.Submission.student_id == models.User.id)
    )
    
    # 根据角色过滤提交列表
    # 学生只能看到自己的提交，教师和教学主任可以看到所有提交
    if current_user.role == "student":
        q = q.filter(models.Submission.student_id == current_user.id)

    rows = q.order_by(models.Submission.submitted_at.desc()).all()
    return [
        schemas.SubmissionWithStudent(
            id=s.id,
            student_id=s.student_id,
            assignment_id=s.assignment_id,
            code=s.code,
            submitted_at=s.submitted_at,
            student_name=username,
        )
        for s, username in rows
    ]


# 教师/教学主任：异步批量分析 — 返回 task_id
@router.post("/{assignment_id}/analyze")
def analyze_assignment_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(roles_required(["teacher", "dean"])),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    subs = (
        db.query(models.Submission)
        .filter(models.Submission.assignment_id == assignment_id)
        .count()
    )
    if subs < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 submissions to analyze")

    task = models.AnalysisTask(assignment_id=assignment_id, status="pending", total_pairs=0, processed_pairs=0)
    db.add(task)
    db.commit()
    db.refresh(task)
    db.add(
        models.AuditLog(
            actor_user_id=current_user.id,
            action="analysis_task_create",
            target_type="analysis_task",
            target_id=task.id,
            detail=f"assignment={assignment_id}",
        )
    )
    db.commit()

    t = threading.Thread(target=execute_analysis_task_thread, args=(task.id,), daemon=True)
    t.start()

    return {"task_id": task.id, "status": "pending", "assignment_id": assignment_id}


# 教师/教学主任：从 ZIP 导入代码为提交（轮询学生账号），再可调用 analyze
@router.post("/{assignment_id}/import-zip")
async def import_zip_submissions(
    assignment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(roles_required(["teacher", "dean"])),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="只支持 ZIP 文件")

    students = (
        db.query(models.User)
        .filter(models.User.role == "student")
        .order_by(models.User.id.asc())
        .all()
    )
    if not students:
        raise HTTPException(
            status_code=400,
            detail="系统中没有学生账号，请先注册学生或手动创建学生后再导入",
        )

    language = (assignment.language or "python").lower()
    ext_map = {
        "python": [".py"],
        "java": [".java"],
        "javascript": [".js"],
        "c": [".c", ".h"],
        "cpp": [".cpp", ".cc", ".cxx", ".h"],
        "csharp": [".cs"],
        "go": [".go"],
    }
    valid_exts = ext_map.get(language, [".py", ".java", ".js", ".c", ".cpp", ".cs", ".go"])

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, file.filename or "upload.zip")
        try:
            with open(zip_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存文件失败: {e}")

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"解压失败: {e}")

        code_files: list[tuple[str, str]] = []
        for root, _, files in os.walk(tmpdir):
            for fn in files:
                if any(fn.lower().endswith(ext) for ext in valid_exts):
                    full = os.path.join(root, fn)
                    try:
                        with open(full, "r", encoding="utf-8") as cf:
                            code_files.append((os.path.relpath(full, tmpdir), cf.read()))
                    except Exception:
                        pass

        if len(code_files) < 1:
            raise HTTPException(status_code=400, detail="ZIP 中未找到有效的代码文件")

        created = 0
        for i, (_, content) in enumerate(code_files):
            stu = students[i % len(students)]
            sub = models.Submission(
                student_id=stu.id,
                assignment_id=assignment_id,
                code=content,
                file_path=None,
            )
            db.add(sub)
            created += 1
        db.commit()

    return {
        "assignment_id": assignment_id,
        "files_imported": created,
        "message": "已写入 submissions，可在作业详情发起「一键批量检测」",
    }


@router.get("/{assignment_id}/evidences")
def get_assignment_evidences(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(roles_required(["teacher", "dean"])),
):
    rows = (
        db.query(models.DetectionEvidence)
        .filter(models.DetectionEvidence.assignment_id == assignment_id)
        .order_by(models.DetectionEvidence.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "comparison_result_id": r.comparison_result_id,
            "submission_id": r.submission_id,
            "compared_with_id": r.compared_with_id,
            "language": r.language,
            "syntax_score": r.syntax_score,
            "semantic_score": r.semantic_score,
            "final_score": r.final_score,
            "model_name": r.model_name,
            "evidence_payload": r.evidence_payload,
            "created_at": r.created_at,
        }
        for r in rows
    ]


# 教师/教学主任：获取某个作业的所有比对结果
@router.get("/{assignment_id}/results")
def get_assignment_results(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(roles_required(["teacher", "dean"])),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="Not allowed")

    submissions = (
        db.query(models.Submission.id, models.User.username)
        .join(models.User, models.Submission.student_id == models.User.id)
        .filter(models.Submission.assignment_id == assignment_id)
        .all()
    )
    if not submissions:
        return []

    submission_ids = [row[0] for row in submissions]
    submission_id_to_username = {row[0]: row[1] for row in submissions}

    results = (
        db.query(models.ComparisonResult)
        .filter(models.ComparisonResult.submission_id.in_(submission_ids))
        .filter(models.ComparisonResult.compared_with_id.in_(submission_ids))
        .order_by(models.ComparisonResult.similarity_score.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "submission_id": r.submission_id,
            "submission_username": submission_id_to_username.get(r.submission_id, str(r.submission_id)),
            "compared_with_id": r.compared_with_id,
            "compared_with_username": submission_id_to_username.get(r.compared_with_id, str(r.compared_with_id)),
            "similarity_score": int(r.similarity_score),
            "filter_layer": r.filter_layer,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in results
    ]


@router.get("/{assignment_id}/matrix")
def get_assignment_matrix(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(roles_required(["teacher", "dean"])),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="Not allowed")

    submissions = (
        db.query(models.Submission.id, models.User.username)
        .join(models.User, models.Submission.student_id == models.User.id)
        .filter(models.Submission.assignment_id == assignment_id)
        .order_by(models.Submission.id.asc())
        .all()
    )
    if not submissions:
        return []

    submission_ids = [row[0] for row in submissions]
    submission_id_to_username = {row[0]: row[1] for row in submissions}

    results = (
        db.query(models.ComparisonResult)
        .filter(models.ComparisonResult.submission_id.in_(submission_ids))
        .filter(models.ComparisonResult.compared_with_id.in_(submission_ids))
        .all()
    )

    matrix_map: dict[int, dict[int, float]] = {sid: {} for sid in submission_ids}
    for sid in submission_ids:
        matrix_map[sid][sid] = 100.0

    for r in results:
        a = int(r.submission_id)
        b = int(r.compared_with_id)
        s = float(r.similarity_score)
        matrix_map.setdefault(a, {})[b] = s
        matrix_map.setdefault(b, {})[a] = s

    matrix_rows = []
    for sid in submission_ids:
        username = submission_id_to_username[sid]
        row = {"student": username}
        for other in submission_ids:
            other_username = submission_id_to_username[other]
            if other == sid:
                row[other_username] = 100
            else:
                val = matrix_map.get(sid, {}).get(other)
                row[other_username] = int(val) if val is not None else None
        matrix_rows.append(row)

    return matrix_rows


@router.post("/{assignment_id}/report")
def export_assignment_report(
    assignment_id: int,
    format: str = "pdf",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(roles_required(["teacher", "dean"])),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    submissions = db.query(models.Submission.id).filter(models.Submission.assignment_id == assignment_id).all()
    submission_ids = [row[0] for row in submissions]
    if len(submission_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 submissions to export report")

    results = (
        db.query(models.ComparisonResult)
        .filter(models.ComparisonResult.submission_id.in_(submission_ids))
        .filter(models.ComparisonResult.compared_with_id.in_(submission_ids))
        .order_by(models.ComparisonResult.similarity_score.desc())
        .all()
    )

    md = build_assignment_report_markdown(
        assignment_title=assignment.title,
        assignment_language=assignment.language,
        generated_at=datetime.now(),
        pairs=[
            ReportPair(
                submission_id=r.submission_id,
                compared_with_id=r.compared_with_id,
                similarity_score=r.similarity_score,
                filter_layer=r.filter_layer,
                details_json=r.details,
            )
            for r in results
        ],
    )

    fmt = (format or "pdf").lower()
    if fmt == "md":
        return PlainTextResponse(md, media_type="text/markdown")

    reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
    os.makedirs(reports_dir, exist_ok=True)

    safe_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"assignment_{assignment_id}_{safe_ts}"
    out_base = os.path.join(reports_dir, base_name)

    if fmt not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="format must be pdf, docx, or md")

    # 直接使用pandoc命令转换
    md_path = f"{out_base}.md"
    output_path = f"{out_base}.{fmt}"
    md_path_existed = False

    try:
        # 写入Markdown文件
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md)
        md_path_existed = True

        # 执行pandoc命令
        if fmt == "pdf":
            # 策略1：优先使用纯Python的reportlab生成PDF
            reportlab_success = False
            try:
                from pdf_generator import markdown_to_pdf, check_pdf_capability
                capability = check_pdf_capability()

                if capability["can_generate_pdf"]:
                    success = markdown_to_pdf(
                        md,
                        output_path,
                        title=f"作业相似性检测报告 - {assignment.title}"
                    )

                    if success and os.path.exists(output_path):
                        reportlab_success = True
                        print(f"[导出] 使用reportlab成功生成PDF: {output_path}")
            except ImportError:
                print("[导出] pdf_generator模块未找到，尝试pandoc")
            except Exception as e:
                print(f"[导出] reportlab生成PDF失败: {e}")

            # 如果reportlab失败，尝试pandoc
            if not reportlab_success:
                pdf_engines = ["wkhtmltopdf", "weasyprint", "prince", "context", "pdfroff"]
                cmd = ["pandoc", md_path, "-o", output_path]
                pandoc_success = False

                # 尝试不同的PDF引擎
                for engine in pdf_engines:
                    try:
                        test_cmd = ["pandoc", f"--pdf-engine={engine}", "--version"]
                        subprocess.run(test_cmd, check=True, capture_output=True, timeout=2)
                        cmd = ["pandoc", md_path, f"--pdf-engine={engine}", "-o", output_path]
                        print(f"[导出] 使用PDF引擎: {engine}")
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                        continue
                else:
                    # 如果没有找到可用的PDF引擎，提供HTML文件作为替代
                    html_path = f"{out_base}.html"
                    try:
                        # 转换为HTML
                        html_cmd = ["pandoc", md_path, "-o", html_path, "--standalone", "--self-contained"]
                        subprocess.run(html_cmd, check=True, capture_output=True, text=True)
                        print("[导出] PDF引擎不可用，提供HTML文件作为替代")
                        output_path = html_path
                        fmt = "html"
                        pandoc_success = True
                    except Exception as e:
                        print(f"[导出] HTML转换也失败: {e}")

                # 尝试执行pandoc命令
                if fmt != "html":
                    try:
                        subprocess.run(cmd, check=True, capture_output=True, text=True)
                        pandoc_success = True
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        pandoc_success = False

                # 如果pandoc也失败，抛出错误
                if not pandoc_success and not os.path.exists(output_path):
                    raise HTTPException(
                        status_code=500,
                        detail="PDF生成失败。请执行: pip install reportlab"
                    )
        else:
            cmd = ["pandoc", md_path, "-o", output_path]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                raise HTTPException(
                    status_code=500,
                    detail="Word文档导出失败，请安装pandoc或使用Markdown格式导出。"
                ) from e

        # 删除临时Markdown文件
        if md_path_existed and os.path.exists(md_path):
            os.unlink(md_path)

        file_path = output_path
    except HTTPException:
        # 清理临时文件
        if md_path_existed and os.path.exists(md_path):
            os.unlink(md_path)
        raise
    except FileNotFoundError as e:
        # 清理临时文件
        if md_path_existed and os.path.exists(md_path):
            os.unlink(md_path)
        raise HTTPException(
            status_code=500,
            detail="PDF生成失败。请执行: pip install reportlab"
        ) from e
    except Exception as e:
        # 清理临时文件
        if md_path_existed and os.path.exists(md_path):
            os.unlink(md_path)
        raise HTTPException(
            status_code=500,
            detail=f"导出失败: {e}"
        ) from e

    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Exported file not found")

    filename = os.path.basename(file_path)
    media_type = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path=file_path, media_type=media_type, filename=filename)


@router.post("/{assignment_id}/workflow")
def run_assignment_workflow_endpoint(
    assignment_id: int,
    export_format: str | None = None,
    push_to_students: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(roles_required(["teacher", "dean"])),
):
    from workflow.assignment_workflow import run_assignment_workflow

    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="Not allowed")

    result = run_assignment_workflow(db, assignment_id, export_format, push_to_students)
    md = result.get("report_markdown") or ""
    return {
        "assignment_id": result.get("assignment_id", assignment_id),
        "submissions_count": result.get("submissions_count"),
        "comparisons_created": result.get("comparisons_created"),
        "skipped_analysis": result.get("skipped_analysis", False),
        "report_markdown_chars": len(md),
        "exported_file_path": result.get("exported_file_path"),
        "pushed_students": result.get("pushed_students", []),
    }


# 教师创建作业
@router.post("/", response_model=schemas.Assignment)
def create_assignment(
    assignment: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("teacher")),
):
    db_assignment = models.Assignment(
        title=assignment.title,
        description=assignment.description,
        language=assignment.language,
        deadline=assignment.deadline,
        created_by=current_user.id,
        function_requirements=assignment.function_requirements,
        scoring_guideline=assignment.scoring_guideline,
        detection_threshold=assignment.detection_threshold or 80.0,
    )
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment


# 更新作业信息（包含检测阈值配置）
@router.put("/{assignment_id}", response_model=schemas.Assignment)
def update_assignment(
    assignment_id: int,
    assignment_update: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("teacher")),
):
    db_assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    if db_assignment.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this assignment")
    
    if assignment_update.title is not None:
        db_assignment.title = assignment_update.title
    if assignment_update.description is not None:
        db_assignment.description = assignment_update.description
    if assignment_update.language is not None:
        db_assignment.language = assignment_update.language
    if assignment_update.deadline is not None:
        db_assignment.deadline = assignment_update.deadline
    if assignment_update.function_requirements is not None:
        db_assignment.function_requirements = assignment_update.function_requirements
    if assignment_update.scoring_guideline is not None:
        db_assignment.scoring_guideline = assignment_update.scoring_guideline
    if assignment_update.detection_threshold is not None:
        if not 0 <= assignment_update.detection_threshold <= 100:
            raise HTTPException(status_code=400, detail="Detection threshold must be between 0 and 100")
        db_assignment.detection_threshold = assignment_update.detection_threshold
    
    db.commit()
    db.refresh(db_assignment)
    return db_assignment


# 获取作业所有提交的评分列表
@router.get("/{assignment_id}/scores")
def get_assignment_scores(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(roles_required(["teacher", "dean"])),
):
    """
    教师/教学主任获取作业所有提交的评分列表
    """
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    submissions = (
        db.query(models.Submission)
        .filter(models.Submission.assignment_id == assignment_id)
        .all()
    )
    
    result = []
    for sub in submissions:
        student = db.query(models.User).filter(models.User.id == sub.student_id).first()
        score = (
            db.query(models.SubmissionScore)
            .filter(models.SubmissionScore.submission_id == sub.id)
            .first()
        )
        
        teacher_name = None
        if score:
            teacher = db.query(models.User).filter(models.User.id == score.teacher_id).first()
            teacher_name = teacher.username if teacher else None
        
        result.append({
            "submission_id": sub.id,
            "student_id": sub.student_id,
            "student_name": student.username if student else "Unknown",
            "code": sub.code,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            "score": {
                "id": score.id,
                "overall_score": score.overall_score,
                "teacher_comments": score.teacher_comments,
                "teacher_name": teacher_name,
                "created_at": score.created_at.isoformat() if score.created_at else None,
                "updated_at": score.updated_at.isoformat() if score.updated_at else None,
            } if score else None
        })
    
    return result


# 教师删除作业（级联删除子表）
@router.delete("/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(role_required("teacher")),
):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    subs = db.query(models.Submission.id).filter(models.Submission.assignment_id == assignment_id).all()
    sids = [row[0] for row in subs]

    try:
        db.query(models.AnalysisTask).filter(models.AnalysisTask.assignment_id == assignment_id).delete(
            synchronize_session=False
        )
        if sids:
            db.query(models.ComparisonResult).filter(
                (models.ComparisonResult.submission_id.in_(sids))
                | (models.ComparisonResult.compared_with_id.in_(sids))
            ).delete(synchronize_session=False)
            db.query(models.SubmissionScore).filter(
                models.SubmissionScore.submission_id.in_(sids)
            ).delete(synchronize_session=False)
            db.query(models.Submission).filter(models.Submission.id.in_(sids)).delete(synchronize_session=False)
        db.query(models.Assignment).filter(models.Assignment.id == assignment_id).delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {"ok": True}
