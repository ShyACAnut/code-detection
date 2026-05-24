from __future__ import annotations

import hashlib
import json

import models
from detectors.syntax_detector import normalize_code


def upsert_code_index_entry(db, submission: models.Submission, language: str) -> None:
    norm = normalize_code(submission.code or "")
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    stub = json.dumps({"len": len(norm), "head": norm[:120]}, ensure_ascii=False)

    row = db.query(models.CodeIndexEntry).filter(models.CodeIndexEntry.submission_id == submission.id).first()
    if row:
        row.assignment_id = submission.assignment_id
        row.language = language
        row.normalized_hash = h
        row.vector_stub = stub
    else:
        db.add(
            models.CodeIndexEntry(
                submission_id=submission.id,
                assignment_id=submission.assignment_id,
                language=language,
                normalized_hash=h,
                vector_stub=stub,
            )
        )
    db.commit()
