"""Shared assignment pairwise analysis: DB submissions -> agent -> ComparisonResult rows."""
from __future__ import annotations

import json
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import numpy as np
from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from database import SessionLocal
from pipeline.analyze_pipeline import analyze_pair, PipelineWeights
from ethics_learning_utils import trigger_ethics_learning, check_and_notify_high_risk


def _convert_numpy_types(obj):
    """递归转换numpy类型为Python原生类型"""
    if isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    elif isinstance(obj, tuple):
        return [_convert_numpy_types(item) for item in obj]
    return obj


def _update_task(
    task_id: int,
    *,
    status: Optional[str] = None,
    total_pairs: Optional[int] = None,
    processed_pairs: Optional[int] = None,
    error_message: Optional[str] = None,
    started_at: Optional[datetime] = None,
) -> None:
    s = SessionLocal()
    try:
        t = s.query(models.AnalysisTask).filter(models.AnalysisTask.id == task_id).first()
        if not t:
            return
        if status is not None:
            t.status = status
            if status == "running" and t.started_at is None:
                t.started_at = datetime.utcnow()
        if total_pairs is not None:
            t.total_pairs = total_pairs
        if processed_pairs is not None:
            t.processed_pairs = processed_pairs
        if error_message is not None:
            t.error_message = error_message
        if started_at is not None:
            t.started_at = started_at
        t.updated_at = datetime.utcnow()
        s.commit()
    finally:
        s.close()


def _get_task_status(task_id: int) -> Optional[str]:
    s = SessionLocal()
    try:
        t = s.query(models.AnalysisTask).filter(models.AnalysisTask.id == task_id).first()
        return t.status if t else None
    finally:
        s.close()


def run_pairwise_batch_and_persist(
    db: Session,
    assignment_id: int,
    *,
    task_id: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """
    Load submissions, pairwise compare, persist ComparisonResult.
    If task_id or progress_callback is set, uses per-pair analyze_code_similarity (supports progress).
    Otherwise uses batch_analyze (faster single batch for sync/workflow).
    """
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    submissions = (
        db.query(models.Submission)
        .filter(models.Submission.assignment_id == assignment_id)
        .order_by(models.Submission.id.asc())
        .all()
    )
    if len(submissions) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 submissions to analyze")

    submission_ids = [s.id for s in submissions]
    n = len(submissions)
    total_pairs = n * (n - 1) // 2

    (
        db.query(models.ComparisonResult)
        .filter(models.ComparisonResult.submission_id.in_(submission_ids))
        .filter(models.ComparisonResult.compared_with_id.in_(submission_ids))
        .delete(synchronize_session=False)
    )
    db.commit()

    if task_id is not None:
        _update_task(task_id, status="running", total_pairs=total_pairs, processed_pairs=0, error_message=None)

    use_progress = task_id is not None or progress_callback is not None
    cfg = db.query(models.SystemConfig).filter(models.SystemConfig.id == 1).first()
    weights = PipelineWeights(
        syntax_weight=(cfg.syntax_weight if cfg else 0.4),
        semantic_weight=(cfg.semantic_weight if cfg else 0.6),
    )
    created = 0

    if use_progress:
        # 多线程并发处理版本
        processed = 0
        created = 0
        lock = Lock()
        
        def analyze_pair_wrapper(a, b, language, weights, cfg):
            """单个代码对分析的包装函数，用于多线程调用"""
            pipeline = analyze_pair(a.code or "", b.code or "", language, weights=weights)
            similarity_score = float(pipeline.get("final_score", -1))
            filter_layer = "hybrid_pipeline"
            
            return {
                "a": a,
                "b": b,
                "pipeline": pipeline,
                "similarity_score": similarity_score,
                "filter_layer": filter_layer,
                "cfg": cfg
            }
        
        # 准备所有需要处理的任务
        tasks = []
        for i in range(n):
            for j in range(i + 1, n):
                tasks.append((submissions[i], submissions[j], assignment.language, weights, cfg))
        
        # 使用多线程并发处理
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 提交所有任务
            futures = [executor.submit(analyze_pair_wrapper, *task) for task in tasks]
            
            for future in as_completed(futures):
                # 检查任务是否被取消
                if task_id is not None and _get_task_status(task_id) == "cancelled":
                    # 取消所有剩余任务
                    for f in futures:
                        f.cancel()
                    return {
                        "assignment_id": assignment_id,
                        "submissions": len(submissions),
                        "comparisons_created": created,
                        "summary": None,
                    }
                
                try:
                    result = future.result()
                    a, b = result["a"], result["b"]
                    pipeline = result["pipeline"]
                    similarity_score = result["similarity_score"]
                    filter_layer = result["filter_layer"]
                    cfg = result["cfg"]
                    
                    # 数据库操作需要加锁
                    with lock:
                        result_data = {
                            "similarity_analysis": {"score": similarity_score, "reason": pipeline.get("reason", "")},
                            "metadata": {
                                "filter_layer": filter_layer,
                                "language": assignment.language,
                                "syntax_score": pipeline.get("syntax_score"),
                                "semantic_score": pipeline.get("semantic_score"),
                            },
                            "matched_lines": pipeline.get("matched_lines", []),
                            "raw": pipeline.get("raw", {}),
                        }
                        
                        comp = models.ComparisonResult(
                            submission_id=a.id,
                            compared_with_id=b.id,
                            task_id=task_id,
                            similarity_score=similarity_score,
                            filter_layer=filter_layer,
                            details=json.dumps(_convert_numpy_types(result_data), ensure_ascii=False),
                        )
                        db.add(comp)
                        db.flush()
                        db.add(
                            models.DetectionEvidence(
                                comparison_result_id=comp.id,
                                assignment_id=assignment_id,
                                submission_id=a.id,
                                compared_with_id=b.id,
                                language=assignment.language,
                                syntax_score=float(pipeline.get("syntax_score", -1)),
                                semantic_score=float(pipeline.get("semantic_score", -1)),
                                final_score=similarity_score,
                                model_name=(cfg.llm_model_name if cfg else "hybrid"),
                                evidence_payload=json.dumps(
                                    _convert_numpy_types({
                                        "matched_lines": pipeline.get("matched_lines", []),
                                        "reason": pipeline.get("reason"),
                                        "weights": pipeline.get("metadata", {}).get("weights", {}),
                                    }),
                                    ensure_ascii=False,
                                ),
                            )
                        )
                        created += 1
                        processed += 1
                        db.commit()
                        
                        check_and_notify_high_risk(a.id, b.id, similarity_score, db)
                        
                        if progress_callback:
                            progress_callback(processed, total_pairs)
                        if task_id is not None:
                            _update_task(task_id, processed_pairs=processed, total_pairs=total_pairs, status="running")
                
                except Exception as e:
                    print(f"Error analyzing pair {a.id} vs {b.id}: {str(e)}")
                    with lock:
                        processed += 1
        
        if task_id is not None and _get_task_status(task_id) != "cancelled":
            _update_task(task_id, status="completed", processed_pairs=total_pairs, total_pairs=total_pairs)
    else:
        # sync mode也走统一 pipeline，保证证据链一致
        for i in range(n):
            for j in range(i + 1, n):
                a, b = submissions[i], submissions[j]
                pipeline = analyze_pair(a.code or "", b.code or "", assignment.language, weights=weights)
                similarity_score = float(pipeline.get("final_score", -1))
                filter_layer = "hybrid_pipeline"
                result = {
                    "similarity_analysis": {"score": similarity_score, "reason": pipeline.get("reason", "")},
                    "metadata": {
                        "filter_layer": filter_layer,
                        "language": assignment.language,
                        "syntax_score": pipeline.get("syntax_score"),
                        "semantic_score": pipeline.get("semantic_score"),
                    },
                    "matched_lines": pipeline.get("matched_lines", []),
                    "raw": pipeline.get("raw", {}),
                }
                comp = models.ComparisonResult(
                    submission_id=a.id,
                    compared_with_id=b.id,
                    task_id=task_id,
                    similarity_score=similarity_score,
                    filter_layer=filter_layer,
                    details=json.dumps(_convert_numpy_types(result), ensure_ascii=False),
                )
                db.add(comp)
                db.flush()
                db.add(
                    models.DetectionEvidence(
                        comparison_result_id=comp.id,
                        assignment_id=assignment_id,
                        submission_id=a.id,
                        compared_with_id=b.id,
                        language=assignment.language,
                        syntax_score=float(pipeline.get("syntax_score", -1)),
                        semantic_score=float(pipeline.get("semantic_score", -1)),
                        final_score=similarity_score,
                        model_name=(cfg.llm_model_name if cfg else "hybrid"),
                        evidence_payload=json.dumps(
                            _convert_numpy_types({
                                "matched_lines": pipeline.get("matched_lines", []),
                                "reason": pipeline.get("reason"),
                                "weights": pipeline.get("metadata", {}).get("weights", {}),
                            }),
                            ensure_ascii=False,
                        ),
                    )
                )
                check_and_notify_high_risk(a.id, b.id, similarity_score, db)
                created += 1
        db.commit()

    return {
        "assignment_id": assignment_id,
        "submissions": len(submissions),
        "comparisons_created": created,
        "summary": None,
    }


def execute_analysis_task_thread(task_id: int) -> None:
    """后台线程入口：跑完更新任务状态。"""
    db = SessionLocal()
    try:
        task = db.query(models.AnalysisTask).filter(models.AnalysisTask.id == task_id).first()
        if not task:
            return
        assignment_id = task.assignment_id
        db.expunge(task)

        if assignment_id:
            # 有作业ID，使用传统方式处理
            run_pairwise_batch_and_persist(db, assignment_id, task_id=task_id)
        else:
            # 没有作业ID，直接处理上传的文件内容（独立文件检测）
            process_uploaded_files(db, task_id)
    except HTTPException as e:
        detail = e.detail
        msg = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)
        _update_task(task_id, status="failed", error_message=msg)
    except Exception as e:
        _update_task(task_id, status="failed", error_message=f"{e}\n{traceback.format_exc()}")
    finally:
        db.close()


def process_uploaded_files(db: Session, task_id: int):
    """处理上传的文件内容进行独立检测（不需要作业ID）"""
    import json
    import os
    
    # 获取任务信息
    task = db.query(models.AnalysisTask).filter(models.AnalysisTask.id == task_id).first()
    if not task:
        return

    # 更新任务状态为运行中
    _update_task(task_id, status="running", total_pairs=0, processed_pairs=0, error_message=None)

    # 读取任务详情中的文件内容
    if not task.file_content:
        _update_task(task_id, status="failed", error_message="没有上传文件内容")
        return

    # 解析文件内容
    try:
        data = json.loads(task.file_content)
    except json.JSONDecodeError:
        _update_task(task_id, status="failed", error_message="无法解析文件内容")
        return

    # 验证数据格式
    if not isinstance(data, list):
        _update_task(task_id, status="failed", error_message="文件内容必须是数组格式")
        return

    # 提取代码对
    code_pairs = []
    for item in data:
        if isinstance(item, dict) and "code_a" in item and "code_b" in item:
            code_pairs.append({
                "code_a": item["code_a"],
                "code_b": item["code_b"]
            })

    if not code_pairs:
        _update_task(task_id, status="failed", error_message="没有有效的代码对")
        return

    total_pairs = len(code_pairs)
    _update_task(task_id, status="running", total_pairs=total_pairs, processed_pairs=0)

    # 获取系统配置
    cfg = db.query(models.SystemConfig).filter(models.SystemConfig.id == 1).first()
    weights = PipelineWeights(
        syntax_weight=(cfg.syntax_weight if cfg else 0.4),
        semantic_weight=(cfg.semantic_weight if cfg else 0.6),
    )

    # 多线程并发处理
    processed = 0
    lock = Lock()
    
    def analyze_single_pair(code_a, code_b, language, weights):
        """分析单个代码对"""
        pipeline = analyze_pair(code_a, code_b, language, weights=weights)
        similarity_score = float(pipeline.get("final_score", -1))
        filter_layer = "hybrid_pipeline"
        
        return {
            "code_a": code_a,
            "code_b": code_b,
            "pipeline": pipeline,
            "similarity_score": similarity_score,
            "filter_layer": filter_layer,
        }
    
    # 准备任务列表
    tasks = [(pair["code_a"], pair["code_b"], "python", weights) for pair in code_pairs]
    
    # 使用多线程并发处理
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(analyze_single_pair, *task) for task in tasks]
        
        for future in as_completed(futures):
            # 检查任务是否被取消
            if _get_task_status(task_id) == "cancelled":
                for f in futures:
                    f.cancel()
                return
            
            try:
                result = future.result()
                pipeline = result["pipeline"]
                similarity_score = result["similarity_score"]
                filter_layer = result["filter_layer"]
                
                with lock:
                    result_data = {
                        "similarity_analysis": {"score": similarity_score, "reason": pipeline.get("reason", "")},
                        "metadata": {
                            "filter_layer": filter_layer,
                            "language": "python",
                            "syntax_score": pipeline.get("syntax_score"),
                            "semantic_score": pipeline.get("semantic_score"),
                        },
                        "matched_lines": pipeline.get("matched_lines", []),
                        "raw": pipeline.get("raw", {}),
                    }

                    # 保存比对结果
                    comp = models.ComparisonResult(
                        task_id=task_id,
                        similarity_score=similarity_score,
                        filter_layer=filter_layer,
                        details=json.dumps(_convert_numpy_types(result_data), ensure_ascii=False),
                    )
                    db.add(comp)
                    db.commit()

                    processed += 1
                    _update_task(task_id, processed_pairs=processed)
            
            except Exception as e:
                print(f"Error analyzing pair: {str(e)}")
                with lock:
                    processed += 1
                    _update_task(task_id, processed_pairs=processed)

    # 完成任务
    _update_task(task_id, status="completed", processed_pairs=total_pairs)
