from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import prompts
from app.ai.base import AIError, RateLimited
from app.ai.router import generate
from app.db import get_db
from app.models import Question, Solution
from app.schemas import ManualCheckRequest, SolutionReviewRequest, VerificationRequest
from app.serializers import solution_payload
from app.services.rag import build_question_context
from app.services.verification import STATUSES, add_manual_check, verify_solution

router = APIRouter(tags=["verification"])


def _get_solution(db: Session, solution_id: int) -> tuple[Solution, Question]:
    solution = db.get(Solution, solution_id)
    if solution is None:
        raise HTTPException(status_code=404, detail="Solution not found")
    question = db.get(Question, solution.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return solution, question


@router.get("/verification/statuses")
def statuses() -> dict:
    return {
        "statuses": STATUSES,
        "rules": [
            "UNVERIFIED: no completed independent checks.",
            "PARTIALLY VERIFIED: structural or model-proposed checks passed, but no independent check exists.",
            "VERIFIED: all applicable checks passed, the official key agrees when present, and at least one independent computation or expert review is recorded.",
            "NEEDS REVIEW: ambiguity, missing evidence, or failed/inconclusive checks.",
            "DISPUTED: independent evidence contradicts the official answer. Never hidden.",
        ],
        "never_sufficient": [
            "Two LLMs agreeing.",
            "A model agreeing with the official key without independent computation.",
            "A high model confidence score.",
        ],
    }


@router.post("/solutions/{solution_id}/verify")
async def run_verification(
    solution_id: int, payload: VerificationRequest, db: Session = Depends(get_db)
) -> dict:
    solution, question = _get_solution(db, solution_id)
    plan = payload.plan
    plan_source = "manual" if payload.plan else "llm"
    if plan is None and payload.generate_plan:
        context = build_question_context(db, question)
        context["solution_text"] = solution.content
        system, prompt = prompts.verification_plan_prompt(context)
        try:
            result = await generate(
                db,
                task="verification_plan",
                system=system,
                prompt=prompt,
                json_mode=True,
                question_id=question.id,
            )
            plan = json.loads(result.text)
        except RateLimited as exc:
            raise HTTPException(
                status_code=429,
                detail={"error": str(exc), "retry_after": exc.retry_after},
            ) from exc
        except (AIError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=502,
                detail={"error": f"Verification plan failed: {exc}"},
            ) from exc
    solution = verify_solution(
        db,
        solution,
        question,
        plan=plan,
        plan_source=plan_source,
        ambiguous=payload.ambiguous,
    )
    return {
        "solution": solution_payload(solution),
        "plan_source": plan_source,
        "notice": (
            "Checks proposed by a language model are recorded as non-independent. "
            "VERIFIED requires an independent computation or recorded expert review."
        ),
    }


@router.post("/solutions/{solution_id}/manual-check")
def manual_check(
    solution_id: int, payload: ManualCheckRequest, db: Session = Depends(get_db)
) -> dict:
    solution, question = _get_solution(db, solution_id)
    solution.reviewer = payload.reviewer
    solution.review_notes = payload.notes
    solution = add_manual_check(
        db,
        solution,
        question,
        passed=payload.passed,
        reviewer=payload.reviewer,
        notes=payload.notes,
        check_type=payload.check_type,
    )
    return {
        "solution": solution_payload(solution),
        "notice": "Manual checks are recorded in the audit trail with reviewer identity.",
    }


@router.post("/solutions/{solution_id}/review")
def review_solution(
    solution_id: int, payload: SolutionReviewRequest, db: Session = Depends(get_db)
) -> dict:
    solution, question = _get_solution(db, solution_id)
    solution.reviewer = payload.reviewer
    solution.review_notes = payload.notes
    solution = add_manual_check(
        db,
        solution,
        question,
        passed=payload.approve,
        reviewer=payload.reviewer,
        notes=payload.notes
        + (" Approved as an expert-reviewed solution." if payload.approve else " Approval withheld."),
    )
    return {
        "solution": solution_payload(solution),
        "notice": (
            "A new review check and status were appended. Previous solution versions and audit checks were preserved."
        ),
    }


@router.get("/solutions/{solution_id}")
def get_solution(solution_id: int, db: Session = Depends(get_db)) -> dict:
    solution, _question = _get_solution(db, solution_id)
    return solution_payload(solution)


@router.get("/questions/{question_id}/solutions")
def list_solutions(question_id: int, db: Session = Depends(get_db)) -> dict:
    solutions = db.scalars(
        select(Solution)
        .where(Solution.question_id == question_id)
        .order_by(Solution.version.desc())
    ).all()
    return {"items": [solution_payload(s) for s in solutions]}
