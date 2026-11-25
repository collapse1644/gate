from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Formula,
    Question,
    QuestionAsset,
    Solution,
    Subject,
    Subtopic,
    Topic,
    VerificationCheck,
)


def question_summary(question: Question, db: Session, caches: dict | None = None) -> dict:
    caches = caches or {}
    subject = caches.get("subjects", {}).get(question.subject_id) or (
        db.get(Subject, question.subject_id) if question.subject_id else None
    )
    topic = caches.get("topics", {}).get(question.topic_id) or (
        db.get(Topic, question.topic_id) if question.topic_id else None
    )
    subtopic = caches.get("subtopics", {}).get(question.subtopic_id) or (
        db.get(Subtopic, question.subtopic_id) if question.subtopic_id else None
    )
    return {
        "id": question.id,
        "public_id": question.public_id,
        "year": question.year,
        "session": question.session,
        "paper_label": question.paper_label,
        "question_no": question.question_no,
        "question_type": question.question_type,
        "marks": question.marks,
        "negative_marks": question.negative_marks,
        "question_text": question.question_text,
        "raw_text": question.raw_text,
        "options": question.options or [],
        "official_answer": question.official_answer,
        "subject_id": question.subject_id,
        "subject": subject.name if subject else None,
        "topic_id": question.topic_id,
        "topic": topic.name if topic else None,
        "subtopic_id": question.subtopic_id,
        "subtopic": subtopic.name if subtopic else None,
        "concepts": [c.name for c in question.concepts],
        "difficulty": question.difficulty,
        "extraction_confidence": question.extraction_confidence,
        "classification_confidence": question.classification_confidence,
        "classification_method": question.classification_method,
        "review_status": question.review_status,
        "verification_status": question.verification_status,
        "import_status": question.import_status,
        "needs_review": question.needs_review,
        "is_bookmarked": question.is_bookmarked,
        "source_pdf": question.source_pdf,
        "source_page": question.source_page,
        "assets": [asset_payload(a) for a in question.assets],
        "solution_available": bool(question.solutions),
        "created_at": question.created_at.isoformat() if question.created_at else None,
    }


def asset_payload(asset: QuestionAsset) -> dict:
    return {
        "id": asset.id,
        "url": f"/api/assets/{asset.id}",
        "kind": asset.kind,
        "page": asset.page,
        "width": asset.width,
        "height": asset.height,
        "sha256": asset.sha256,
        "interpretation": asset.interpretation,
        "interpretation_status": asset.interpretation_status,
        "interpretation_model": asset.interpretation_model,
    }


def solution_payload(solution: Solution, include_checks: bool = True) -> dict:
    payload = {
        "id": solution.id,
        "version": solution.version,
        "provider": solution.provider,
        "model": solution.model,
        "learning_mode": solution.learning_mode,
        "content": solution.content,
        "final_answer": solution.final_answer,
        "verification_status": solution.verification_status,
        "is_current": solution.is_current,
        "is_verified_snapshot": solution.is_verified_snapshot,
        "reviewer": solution.reviewer,
        "review_notes": solution.review_notes,
        "created_at": solution.created_at.isoformat() if solution.created_at else None,
    }
    if include_checks:
        payload["checks"] = [check_payload(c) for c in solution.checks]
    return payload


def check_payload(check: VerificationCheck) -> dict:
    return {
        "id": check.id,
        "check_type": check.check_type,
        "tool": check.tool,
        "description": check.description,
        "expected": check.expected,
        "actual": check.actual,
        "passed": check.passed,
        "independent": check.independent,
        "notes": check.notes,
        "created_at": check.created_at.isoformat() if check.created_at else None,
    }


def question_detail(question: Question, db: Session) -> dict:
    payload = question_summary(question, db)
    payload["extraction_notes"] = question.extraction_notes or []
    payload["review_notes"] = question.review_notes
    payload["reviewed_by"] = question.reviewed_by
    payload["source_bbox"] = question.source_bbox
    payload["secondary_topics"] = [
        {"id": t.id, "name": t.name} for t in question.secondary_topics
    ]
    payload["solutions"] = [solution_payload(s) for s in question.solutions]
    payload["current_solution"] = next(
        (solution_payload(s) for s in question.solutions if s.is_current), None
    )
    return payload


def formula_payload(formula: Formula) -> dict:
    return {
        "id": formula.id,
        "name": formula.name,
        "latex": formula.latex,
        "subject_id": formula.subject_id,
        "topic_id": formula.topic_id,
        "subtopic_id": formula.subtopic_id,
        "variable_definitions": formula.variable_definitions or [],
        "units": formula.units,
        "applicability": formula.applicability,
        "derivation": formula.derivation,
        "common_mistakes": formula.common_mistakes,
        "related_concepts": formula.related_concepts,
        "pyq_references": formula.pyq_references or [],
        "verification_status": formula.verification_status,
        "is_bookmarked": formula.is_bookmarked,
        "reviewed_by": formula.reviewed_by,
    }
