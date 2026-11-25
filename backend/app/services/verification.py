"""Independent verification pipeline.

Verification is deliberately evidence-based. An LLM response is never treated as
proof. Computational checks are evaluated in a separate, isolated Python process
with a strict expression whitelist and a hard timeout. The worker cannot import
modules or execute arbitrary LLM-generated statements.

Status policy (strict):
- VERIFIED requires all applicable checks to pass, the solution to agree with the
  official key when one exists, and at least one *independent* check (a
  deterministic computation or a recorded human expert review). Two language
  models agreeing is never sufficient.
- DISPUTED is used when an independent derivation/check contradicts the official
  key.
- Conceptual questions without computable checks remain PARTIALLY VERIFIED or
  NEEDS REVIEW until a human reviewer records an expert check.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Question, Solution, VerificationCheck

STATUSES = ["UNVERIFIED", "PARTIALLY VERIFIED", "VERIFIED", "NEEDS REVIEW", "DISPUTED"]

ALLOWED_CHECK_TYPES = {
    "official_answer_match",
    "option_validity",
    "numeric",
    "symbolic",
    "unit",
    "range",
    "boundary",
    "algorithmic",
    "expert_review",
}


@dataclass
class CheckOutcome:
    check_type: str
    tool: str
    description: str
    passed: bool | None
    expected: str | None = None
    actual: str | None = None
    independent: bool = True
    notes: str = ""
    input_data: dict | None = None


def normalize_answer(value: str | None) -> str:
    if value is None:
        return ""
    value = value.strip().upper()
    value = value.replace("MTA", "MTA")
    letters = sorted(set(re.findall(r"[A-D]", value))) if re.fullmatch(r"[\s,;()A-D]+", value) else []
    if letters:
        return ",".join(letters)
    try:
        number = float(value)
        return format_number(number)
    except ValueError:
        return re.sub(r"\s+", "", value)


def format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.10g}"


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", value.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def answers_match(expected: str | None, actual: str | None, tolerance: float = 1e-6) -> bool | None:
    if expected is None or actual is None:
        return None
    exp = normalize_answer(expected)
    act = normalize_answer(actual)
    if not exp or not act:
        return None
    if exp == act:
        return True
    exp_num, act_num = _parse_float(exp), _parse_float(act)
    if exp_num is not None and act_num is not None:
        return abs(exp_num - act_num) <= tolerance * max(1.0, abs(exp_num))
    return False


def extract_final_answer(solution_text: str) -> str | None:
    boxed = re.findall(r"\\boxed\{([^{}]+)\}", solution_text)
    if boxed:
        return boxed[-1].strip()
    patterns = [
        r"(?im)^\s*(?:final answer|answer)\s*[:：]\s*(.+)$",
        r"(?im)^\s*\\textbf\{(?:final answer|answer)\}\s*[:：]?\s*(.+)$",
        r"(?im)^\s*\*\*(?:final answer|answer)\*\*\s*[:：]?\s*(.+)$",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, solution_text)
        if matches:
            candidate = matches[-1].strip()
            candidate = re.sub(r"^\**\s*", "", candidate)
            if len(candidate) <= 300:
                return candidate
    return None


def structural_checks(question: Question, solution: Solution) -> list[CheckOutcome]:
    outcomes: list[CheckOutcome] = []
    official = question.official_answer
    final_answer = extract_final_answer(solution.content) or solution.final_answer
    if official:
        match = answers_match(official, final_answer)
        outcomes.append(
            CheckOutcome(
                check_type="official_answer_match",
                tool="internal",
                description="Generated final answer compared with the extracted official answer key.",
                passed=match,
                expected=official,
                actual=final_answer,
                independent=False,
                notes=(
                    "Agreement with the official key is necessary but not sufficient for VERIFIED."
                    if match is not None
                    else "No explicit final answer could be extracted from the solution."
                ),
            )
        )
    else:
        outcomes.append(
            CheckOutcome(
                check_type="official_answer_match",
                tool="internal",
                description="Official answer availability.",
                passed=None,
                expected=None,
                actual=final_answer,
                independent=False,
                notes="No official answer is associated with this question; expert or computational verification is required.",
            )
        )

    if official and question.options:
        valid = _option_validity(question, official)
        outcomes.append(
            CheckOutcome(
                check_type="option_validity",
                tool="internal",
                description="Official answer is a valid option set for the question type.",
                passed=valid,
                expected=question.question_type,
                actual=official,
                independent=True,
                notes="Checks MCQ single-option / MSQ subset / NAT numeric form.",
            )
        )
    return outcomes


def _option_validity(question: Question, official: str) -> bool:
    letters = sorted(set(re.findall(r"[A-D]", official.upper())))
    keys = {opt.get("key") for opt in (question.options or [])}
    if question.question_type == "MCQ":
        return len(letters) == 1 and letters[0] in keys
    if question.question_type == "MSQ":
        return bool(letters) and set(letters).issubset(keys)
    if question.question_type == "NAT":
        return _parse_float(official) is not None or official.upper() == "MTA"
    return False


def run_plan_checks(plan: dict | None, *, independent: bool = False) -> list[CheckOutcome]:
    if not plan:
        return []
    outcomes: list[CheckOutcome] = []
    for raw in plan.get("checks", [])[:12]:
        check_type = str(raw.get("check_type", "")).lower()
        if check_type not in ALLOWED_CHECK_TYPES or check_type in {
            "official_answer_match",
            "option_validity",
            "expert_review",
        }:
            continue
        if raw.get("applicable") is False:
            outcomes.append(
                CheckOutcome(
                    check_type=check_type,
                    tool="internal",
                    description=str(raw.get("description", ""))[:500],
                    passed=None,
                    expected=raw.get("expected"),
                    actual=raw.get("actual_from_solution"),
                    independent=independent,
                    notes="Marked not applicable by the verification plan: "
                    + str(raw.get("notes", ""))[:300],
                )
            )
            continue
        expression = raw.get("expression")
        expected = raw.get("expected")
        tolerance = raw.get("tolerance")
        if not expression or expected is None:
            outcomes.append(
                CheckOutcome(
                    check_type=check_type,
                    tool="internal",
                    description=str(raw.get("description", ""))[:500],
                    passed=None,
                    expected=expected,
                    actual=None,
                    independent=independent,
                    notes="Check lacked a pure expression or expected value; not executed.",
                )
            )
            continue
        result = safe_compare(str(expression), str(expected), tolerance)
        outcomes.append(
            CheckOutcome(
                check_type=check_type,
                tool="sympy-sandbox",
                description=str(raw.get("description", ""))[:500],
                passed=result.get("passed"),
                expected=str(expected)[:300],
                actual=str(result.get("actual", ""))[:300],
                independent=independent,
                notes=str(result.get("error") or raw.get("notes", ""))[:800],
                input_data={"expression": str(expression)[:1000]},
            )
        )
    return outcomes


def safe_compare(expression: str, expected: str, tolerance: float | None = None) -> dict:
    worker = Path(__file__).with_name("verification_worker.py")
    payload = {
        "expression": expression[:2000],
        "expected": expected[:2000],
        "tolerance": tolerance if tolerance is not None else 1e-9,
    }
    try:
        completed = subprocess.run(  # noqa: S603
            [sys.executable, "-I", str(worker)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=8,
            cwd=str(worker.parent),
        )
    except subprocess.TimeoutExpired:
        return {"passed": False, "error": "Verification timed out after 8 seconds."}
    if completed.returncode != 0:
        return {
            "passed": False,
            "error": (completed.stderr or "Verification worker failed.")[:500],
        }
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"passed": False, "error": "Verification worker returned invalid output."}


def decide_status(
    question: Question,
    checks: list[CheckOutcome],
    *,
    has_plan: bool,
    ambiguous: bool = False,
) -> tuple[str, str]:
    executed = [c for c in checks if c.passed is not None]
    failed = [c for c in executed if c.passed is False]
    independent = [c for c in executed if c.independent]
    official_check = next((c for c in checks if c.check_type == "official_answer_match"), None)
    official_match = official_check.passed if official_check else None

    if not executed:
        return "UNVERIFIED", "No completed checks."

    disputes = [
        c
        for c in failed
        if c.independent
        and c.check_type in {"official_answer_match", "numeric", "symbolic", "algorithmic"}
    ]
    if disputes:
        return (
            "DISPUTED",
            "An independent check disagrees with the derived/official answer. "
            "The disagreement is preserved for manual resolution.",
        )
    if failed:
        return "NEEDS REVIEW", "One or more checks failed or were inconclusive."
    if ambiguous:
        return "NEEDS REVIEW", "Question is flagged ambiguous; verification cannot be completed automatically."

    if not independent:
        return (
            "PARTIALLY VERIFIED",
            "Structural/LLM-derived checks passed, but no independent computational or expert check was recorded.",
        )

    if question.official_answer and official_match is not True:
        if official_match is False and independent:
            return (
                "DISPUTED",
                "Independent checks pass but the solution disagrees with the official key.",
            )
        return "NEEDS REVIEW", "Official answer is missing from the comparison."

    if any(c.check_type == "expert_review" and c.independent and c.passed for c in executed):
        return "VERIFIED", "Independent expert review recorded and all applicable checks passed."

    if has_plan and any(c.tool == "sympy-sandbox" and c.independent for c in executed):
        return "VERIFIED", "All applicable deterministic checks passed, including an independent computation."

    return (
        "PARTIALLY VERIFIED",
        "Checks passed, but the pipeline cannot establish full independent verification. "
        "A reviewer must confirm the final answer.",
    )


def verify_solution(
    db: Session,
    solution: Solution,
    question: Question,
    *,
    plan: dict | None = None,
    plan_source: str = "llm",
    ambiguous: bool = False,
) -> Solution:
    # Never silently destroy a previous verified snapshot.
    checks = structural_checks(question, solution)
    checks.extend(run_plan_checks(plan, independent=(plan_source == "manual")))
    for outcome in checks:
        db.add(
            VerificationCheck(
                solution_id=solution.id,
                check_type=outcome.check_type,
                tool=outcome.tool,
                description=outcome.description,
                input_data=outcome.input_data,
                expected=outcome.expected,
                actual=outcome.actual,
                passed=outcome.passed,
                independent=outcome.independent,
                notes=outcome.notes,
            )
        )
    status, reason = decide_status(question, checks, has_plan=bool(plan), ambiguous=ambiguous)
    solution.verification_status = status
    existing_verified = any(
        other.id != solution.id and other.verification_status == "VERIFIED"
        for other in question.solutions
    )
    # Do not silently downgrade a question that already has a preserved verified
    # solution. New disagreements are still surfaced on the new solution itself.
    if not existing_verified or status in {"VERIFIED", "DISPUTED"}:
        question.verification_status = status
    if status == "VERIFIED":
        solution.is_verified_snapshot = True
    db.commit()
    db.refresh(solution)
    return solution


def add_manual_check(
    db: Session,
    solution: Solution,
    question: Question,
    *,
    passed: bool,
    reviewer: str,
    notes: str,
    check_type: str = "expert_review",
) -> Solution:
    if check_type not in ALLOWED_CHECK_TYPES:
        check_type = "expert_review"
    db.add(
        VerificationCheck(
            solution_id=solution.id,
            check_type=check_type,
            tool="manual",
            description="Manual reviewer check recorded in the verification audit trail.",
            passed=passed,
            independent=True,
            notes=f"Reviewer: {reviewer}. {notes}"[:2000],
        )
    )
    db.commit()
    checks = [
        CheckOutcome(
            check_type=c.check_type,
            tool=c.tool,
            description=c.description,
            passed=c.passed,
            expected=c.expected,
            actual=c.actual,
            independent=c.independent,
            notes=c.notes,
        )
        for c in solution.checks
    ]
    status, _ = decide_status(
        question,
        checks,
        has_plan=True,
        ambiguous=bool(question.needs_review and not passed),
    )
    solution.verification_status = status
    existing_verified = any(
        other.id != solution.id and other.verification_status == "VERIFIED"
        for other in question.solutions
    )
    if not existing_verified or status in {"VERIFIED", "DISPUTED"}:
        question.verification_status = status
    if status == "VERIFIED":
        solution.is_verified_snapshot = True
    db.commit()
    db.refresh(solution)
    return solution
