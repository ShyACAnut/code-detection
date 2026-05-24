from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from assignment_analysis import run_pairwise_batch_and_persist
from report_builder import ReportPair, build_assignment_report_markdown


class WorkflowState(TypedDict, total=False):
    assignment_id: int
    export_format: Optional[str]
    push_to_students: bool
    submissions_count: int
    comparisons_created: int
    report_markdown: str
    exported_file_path: Optional[str]
    skipped_analysis: bool
    pushed_students: List[str]


def check_existing_analysis(db: Session, assignment_id: int) -> tuple[bool, int, int]:
    """
    检查是否已有分析结果
    返回: (是否有分析结果, 提交数, 比对结果数)
    """
    submissions = db.query(models.Submission.id).filter(
        models.Submission.assignment_id == assignment_id
    ).all()
    submission_ids = [row[0] for row in submissions]

    if len(submission_ids) < 2:
        return False, len(submission_ids), 0

    results_count = db.query(models.ComparisonResult).filter(
        models.ComparisonResult.submission_id.in_(submission_ids),
        models.ComparisonResult.compared_with_id.in_(submission_ids)
    ).count()

    has_analysis = results_count > 0
    return has_analysis, len(submission_ids), results_count


def run_assignment_workflow(
    db: Session, 
    assignment_id: int, 
    export_format: Optional[str] = None,
    push_to_students: bool = False
) -> WorkflowState:
    """
    LangGraph workflow: 
    1. 检查是否已有分析结果，有则跳过分析，无则重新分析
    2. 生成报告
    3. (可选) 导出为PDF/Word
    4. (可选) 推送给学生
    """
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph

    def check_and_analyze(state: WorkflowState) -> WorkflowState:
        has_existing, sub_count, result_count = check_existing_analysis(db, assignment_id)

        if has_existing:
            state["skipped_analysis"] = True
            state["submissions_count"] = sub_count
            state["comparisons_created"] = result_count
            return state

        state["skipped_analysis"] = False
        out = run_pairwise_batch_and_persist(db, assignment_id)
        state["submissions_count"] = out["submissions"]
        state["comparisons_created"] = out["comparisons_created"]
        return state

    def build_report(state: WorkflowState) -> WorkflowState:
        assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
        submissions = db.query(models.Submission.id).filter(
            models.Submission.assignment_id == assignment_id
        ).all()
        submission_ids = [row[0] for row in submissions]

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
        state["report_markdown"] = md
        return state

    def export_report(state: WorkflowState) -> WorkflowState:
        import subprocess
        fmt = (state.get("export_format") or "").lower().strip()
        if not fmt or fmt == "md":
            state["exported_file_path"] = None
            return state

        if fmt not in {"pdf", "docx"}:
            raise HTTPException(status_code=400, detail="export_format must be pdf, docx, md, or null")

        reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
        os.makedirs(reports_dir, exist_ok=True)

        safe_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_base = os.path.join(reports_dir, f"assignment_{assignment_id}_{safe_ts}")
        md_path = f"{out_base}.md"
        output_path = f"{out_base}.{fmt}"
        md_path_existed = False

        try:
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(state["report_markdown"])
            md_path_existed = True

            if fmt == "pdf":
                # 策略1：尝试使用纯Python的reportlab生成PDF（不依赖pandoc）
                reportlab_success = False
                try:
                    from pdf_generator import markdown_to_pdf, check_pdf_capability
                    capability = check_pdf_capability()

                    if capability["can_generate_pdf"]:
                        success = markdown_to_pdf(
                            state["report_markdown"],
                            output_path,
                            title=f"作业相似性检测报告 - {assignment_id}"
                        )

                        if success and os.path.exists(output_path):
                            reportlab_success = True
                            print(f"[工作流] 使用reportlab成功生成PDF: {output_path}")
                except ImportError:
                    print("[工作流] pdf_generator模块未找到，尝试pandoc")
                except Exception as e:
                    print(f"[工作流] reportlab生成PDF失败: {e}")

                # 如果reportlab失败，尝试pandoc
                if not reportlab_success:
                    pandoc_success = False
                    pdf_engines = ["wkhtmltopdf", "weasyprint", "prince", "context", "pdfroff"]
                    cmd = ["pandoc", md_path, "-o", output_path]

                    for engine in pdf_engines:
                        try:
                            test_cmd = ["pandoc", f"--pdf-engine={engine}", "--version"]
                            subprocess.run(test_cmd, check=True, capture_output=True, timeout=2)
                            cmd = ["pandoc", md_path, f"--pdf-engine={engine}", "-o", output_path]
                            print(f"[工作流] 使用PDF引擎: {engine}")
                            break
                        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                            continue
                    else:
                        # 所有引擎都失败，尝试生成HTML
                        html_path = f"{out_base}.html"
                        try:
                            html_cmd = ["pandoc", md_path, "-o", html_path, "--standalone", "--self-contained"]
                            subprocess.run(html_cmd, check=True, capture_output=True, text=True)
                            print("[工作流] PDF引擎不可用，提供HTML文件作为替代")
                            output_path = html_path
                            fmt = "html"
                            pandoc_success = True
                        except Exception:
                            pass

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
                # docx格式使用pandoc
                try:
                    cmd = ["pandoc", md_path, "-o", output_path]
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    raise HTTPException(
                        status_code=500,
                        detail="Word文档导出失败，请安装pandoc或使用Markdown格式导出。"
                    ) from e

            # 清理临时文件
            if md_path_existed and os.path.exists(md_path):
                os.unlink(md_path)

            state["exported_file_path"] = output_path
            return state

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

    def push_to_students_if_needed(state: WorkflowState) -> WorkflowState:
        push_flag = state.get("push_to_students", False)
        if not push_flag:
            state["pushed_students"] = []
            return state

        assignment = db.query(models.Assignment).filter(
            models.Assignment.id == assignment_id
        ).first()
        if not assignment:
            state["pushed_students"] = []
            return state

        submissions = db.query(models.Submission).filter(
            models.Submission.assignment_id == assignment_id
        ).all()

        student_ids = set(sub.student_id for sub in submissions)
        pushed_students: List[str] = []

        for student_id in student_ids:
            try:
                student = db.query(models.User).filter(
                    models.User.id == student_id,
                    models.User.role == "student"
                ).first()
                if not student:
                    continue

                from statistics import StatisticsService
                report_data = StatisticsService.generate_student_report(db, student_id)

                def convert_datetime(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    elif isinstance(obj, dict):
                        return {k: convert_datetime(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_datetime(item) for item in obj]
                    else:
                        return obj

                report_data_serializable = convert_datetime(report_data)

                report = models.LearningReport(
                    student_id=student_id,
                    teacher_id=1,
                    report_content=json.dumps(report_data_serializable, ensure_ascii=False, indent=2),
                    is_read=0
                )
                db.add(report)
                pushed_students.append(student.username)
            except Exception as e:
                print(f"推送报告给学生 {student_id} 失败: {e}")
                continue

        db.commit()
        state["pushed_students"] = pushed_students
        return state

    checkpointer = MemorySaver()
    graph = StateGraph(WorkflowState)
    graph.add_node("check_and_analyze", check_and_analyze)
    graph.add_node("report", build_report)
    graph.add_node("export", export_report)
    graph.add_node("push", push_to_students_if_needed)

    graph.set_entry_point("check_and_analyze")
    graph.add_edge("check_and_analyze", "report")
    graph.add_edge("report", "export")
    graph.add_edge("export", "push")
    graph.add_edge("push", END)

    app = graph.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": f"assignment_{assignment_id}"}}
    initial: WorkflowState = {
        "assignment_id": assignment_id, 
        "export_format": export_format,
        "push_to_students": push_to_students
    }
    return app.invoke(initial, config=config)
