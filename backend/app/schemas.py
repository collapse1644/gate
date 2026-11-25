from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class BookmarkUpdate(BaseModel):
    is_bookmarked: bool


class ClassificationUpdate(BaseModel):
    subject_id: int | None = None
    topic_id: int | None = None
    subtopic_id: int | None = None
    concept_ids: list[int] = Field(default_factory=list)
    reason: str = ""
    accept: bool = True


class QuestionPatch(BaseModel):
    needs_review: bool | None = None
    review_notes: str | None = None
    difficulty: float | None = Field(default=None, ge=0, le=1)
    official_answer: str | None = None
    question_type: Literal["MCQ", "MSQ", "NAT"] | None = None


class AttemptCreate(BaseModel):
    selected_answer: str | None = None
    mode: str = "practice"
    time_spent_seconds: int = Field(default=0, ge=0, le=86400)
    working_text: str = ""
    confidence: Literal["low", "medium", "high"] | None = None
    practice_session_id: int | None = None


class SolutionRequest(BaseModel):
    mode: Literal["knows", "wrong", "unknown"] = "unknown"
    working_text: str = ""


class TutorSessionCreate(BaseModel):
    mode: Literal["knows", "wrong", "unknown", "concept", "doubt"] = "doubt"
    question_id: int | None = None
    subject_id: int | None = None
    topic_id: int | None = None
    subtopic_id: int | None = None
    title: str | None = None


class TutorMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    include_figures: bool = True


class ClassificationAIRequest(BaseModel):
    use_llm: bool = True


class VerificationRequest(BaseModel):
    generate_plan: bool = True
    ambiguous: bool = False
    plan: dict | None = None


class ManualCheckRequest(BaseModel):
    passed: bool
    notes: str = ""
    reviewer: str = "user"
    check_type: Literal["expert_review", "numeric", "symbolic", "unit", "boundary"] = "expert_review"


class SolutionReviewRequest(BaseModel):
    reviewer: str = "user"
    notes: str = ""
    approve: bool = True


class FormulaCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    latex: str
    subject_id: int | None = None
    topic_id: int | None = None
    subtopic_id: int | None = None
    variable_definitions: list[dict] | None = None
    units: str = ""
    applicability: str = ""
    derivation: str = ""
    common_mistakes: str = ""
    related_concepts: str = ""
    pyq_references: list[int] | None = None
    verification_status: Literal["proposed", "verified", "rejected"] = "proposed"


class FormulaUpdate(BaseModel):
    name: str | None = None
    latex: str | None = None
    units: str | None = None
    applicability: str | None = None
    derivation: str | None = None
    common_mistakes: str | None = None
    related_concepts: str | None = None
    verification_status: Literal["proposed", "verified", "rejected"] | None = None
    is_bookmarked: bool | None = None


class PracticeCreate(BaseModel):
    mode: Literal[
        "subtopic",
        "topic",
        "subject",
        "year",
        "random",
        "incorrect",
        "unattempted",
        "revision",
        "full_paper",
    ] = "random"
    subject_id: int | None = None
    topic_id: int | None = None
    subtopic_id: int | None = None
    concept_id: int | None = None
    year: int | None = None
    paper_id: int | None = None
    question_type: Literal["MCQ", "MSQ", "NAT"] | None = None
    marks: float | None = None
    difficulty_min: float | None = None
    difficulty_max: float | None = None
    verification_status: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    limit: int = Field(default=20, ge=1, le=65)
    shuffle: bool = False
    preserve_order: bool = True


class PracticeAnswer(BaseModel):
    question_id: int
    selected_answer: str | None = None
    time_spent_seconds: int = Field(default=0, ge=0)
    working_text: str = ""


class ProgressStatusUpdate(BaseModel):
    manual_status: Literal["not_started", "learning", "practising", "strong", "needs_revision"] | None = None


class BenchmarkCreate(BaseModel):
    expected_subject_id: int | None = None
    expected_topic_id: int | None = None
    expected_subtopic_id: int | None = None
    expected_concepts: list[str] | None = None
    notes: str = ""
    label_source: str = "ai_assisted"
    reviewer: str | None = None


class ApproveRequest(BaseModel):
    reviewer: str = "user"


class RejectRequest(BaseModel):
    reviewer: str = "user"
    reason: str = ""


class VisionRequest(BaseModel):
    asset_id: int | None = None


class FormulaExtractRequest(BaseModel):
    solution_id: int | None = None


class ConceptLessonRequest(BaseModel):
    subject_id: int | None = None
    topic_id: int | None = None
    subtopic_id: int | None = None


class BackupRequest(BaseModel):
    label: str = "manual"


class RestoreRequest(BaseModel):
    filename: str


class SettingsUpdate(BaseModel):
    values: dict[str, Any]

    @field_validator("values")
    @classmethod
    def _limit(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 100:
            raise ValueError("Too many settings in one request.")
        return value
