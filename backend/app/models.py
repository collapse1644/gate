from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# ---------------------------------------------------------------------------
# Syllabus and taxonomy
# ---------------------------------------------------------------------------
class SyllabusVersion(Base):
    __tablename__ = "syllabus_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam: Mapped[str] = mapped_column(String(32), default="GATE")
    year: Mapped[int] = mapped_column(Integer)
    paper_code: Mapped[str] = mapped_column(String(8), default="CS")
    title: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(String(512))
    source_sha256: Mapped[str] = mapped_column(String(64))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    sections: Mapped[list["SyllabusSection"]] = relationship(back_populates="version")


class SyllabusSection(Base):
    __tablename__ = "syllabus_sections"
    __table_args__ = (UniqueConstraint("version_id", "code", name="uq_section_version_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("syllabus_versions.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), default="Core")
    official_text: Mapped[str] = mapped_column(Text, default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    version: Mapped[SyllabusVersion] = relationship(back_populates="sections")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    section_code: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(16), default="#3b82f6")
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    topics: Mapped[list["Topic"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan", order_by="Topic.display_order"
    )


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("subject_id", "slug", name="uq_topic_subject_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("syllabus_sections.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    subject: Mapped[Subject] = relationship(back_populates="topics")
    subtopics: Mapped[list["Subtopic"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan", order_by="Subtopic.display_order"
    )


class Subtopic(Base):
    __tablename__ = "subtopics"
    __table_args__ = (UniqueConstraint("topic_id", "slug", name="uq_subtopic_topic_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(220))
    slug: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    topic: Mapped[Topic] = relationship(back_populates="subtopics")
    concepts: Mapped[list["Concept"]] = relationship(
        back_populates="subtopic", cascade="all, delete-orphan", order_by="Concept.display_order"
    )


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("subtopic_id", "slug", name="uq_concept_subtopic_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subtopic_id: Mapped[int] = mapped_column(ForeignKey("subtopics.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(220))
    slug: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    subtopic: Mapped[Subtopic] = relationship(back_populates="concepts")


# ---------------------------------------------------------------------------
# Papers and questions
# ---------------------------------------------------------------------------
class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    session: Mapped[str | None] = mapped_column(String(80))
    paper_code: Mapped[str] = mapped_column(String(16), default="CS")
    label: Mapped[str] = mapped_column(String(255), default="")
    source_pdf: Mapped[str] = mapped_column(String(512), default="")
    source_sha256: Mapped[str] = mapped_column(String(64), default="")
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    total_marks: Mapped[float | None] = mapped_column(Float)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    questions: Mapped[list["Question"]] = relationship(back_populates="paper")


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=new_uuid)
    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id", ondelete="SET NULL"))

    year: Mapped[int] = mapped_column(Integer, index=True)
    exam: Mapped[str] = mapped_column(String(24), default="GATE")
    paper_code: Mapped[str] = mapped_column(String(16), default="CS")
    session: Mapped[str | None] = mapped_column(String(80))
    paper_label: Mapped[str] = mapped_column(String(160), default="")
    question_no: Mapped[int] = mapped_column(Integer)
    subpart: Mapped[str | None] = mapped_column(String(8))
    question_type: Mapped[str] = mapped_column(String(8), default="MCQ")
    marks: Mapped[float | None] = mapped_column(Float)
    negative_marks: Mapped[float | None] = mapped_column(Float)
    marks_source: Mapped[str] = mapped_column(String(32), default="unknown")

    question_text: Mapped[str] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    options: Mapped[list | None] = mapped_column(JSON)
    official_answer: Mapped[str | None] = mapped_column(String(64))
    answer_explanation: Mapped[str | None] = mapped_column(Text)

    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"))
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("syllabus_sections.id", ondelete="SET NULL")
    )
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    subtopic_id: Mapped[int | None] = mapped_column(ForeignKey("subtopics.id", ondelete="SET NULL"))
    concept_text: Mapped[str] = mapped_column(Text, default="")

    difficulty: Mapped[float | None] = mapped_column(Float)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    extraction_notes: Mapped[list | None] = mapped_column(JSON, default=list)
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    classification_method: Mapped[str] = mapped_column(String(40), default="unclassified")
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")
    review_notes: Mapped[str] = mapped_column(Text, default="")

    source_pdf: Mapped[str] = mapped_column(String(512), default="")
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_bbox: Mapped[list | None] = mapped_column(JSON)
    source_question_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL")
    )

    solution_text: Mapped[str | None] = mapped_column(Text)
    import_status: Mapped[str] = mapped_column(String(16), default="staged", index=True)
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(80))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    paper: Mapped[Paper | None] = relationship(back_populates="questions")
    concepts: Mapped[list[Concept]] = relationship(
        secondary="question_concepts", lazy="selectin"
    )
    secondary_topics: Mapped[list[Topic]] = relationship(
        secondary="question_secondary_topics", lazy="selectin"
    )
    assets: Mapped[list["QuestionAsset"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", lazy="selectin"
    )
    solutions: Mapped[list["Solution"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="Solution.version.desc()"
    )
    verified_answer: Mapped["VerifiedAnswer | None"] = relationship(
        back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class QuestionConcept(Base):
    __tablename__ = "question_concepts"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class QuestionSecondaryTopic(Base):
    __tablename__ = "question_secondary_topics"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )


class QuestionAsset(Base):
    __tablename__ = "question_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(String(512))
    kind: Mapped[str] = mapped_column(String(32), default="figure")
    page: Mapped[int] = mapped_column(Integer)
    bbox: Mapped[list | None] = mapped_column(JSON)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    interpretation: Mapped[str | None] = mapped_column(Text)
    interpretation_status: Mapped[str] = mapped_column(String(24), default="not_interpreted")
    interpretation_model: Mapped[str | None] = mapped_column(String(120))

    question: Mapped[Question] = relationship(back_populates="assets")


class AnswerKeyEntry(Base):
    __tablename__ = "answer_key_entries"
    __table_args__ = (
        UniqueConstraint("paper_id", "question_no", name="uq_answer_paper_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"))
    question_no: Mapped[int] = mapped_column(Integer)
    answer: Mapped[str] = mapped_column(String(64))
    source_pdf: Mapped[str] = mapped_column(String(512), default="")
    source_page: Mapped[int | None] = mapped_column(Integer)


class VerifiedAnswer(Base):
    """Manually verified answer for a question, with provenance tracking.

    Used when an official answer key is available externally (not from ingested
    PDFs) and a user with appropriate privileges verifies it. Distinct from
    AnswerKeyEntry (which comes from ingested answer-key PDFs) and from
    AI-generated solutions (which are UNVERIFIED until independently checked).
    """

    __tablename__ = "verified_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), unique=True
    )
    answer: Mapped[str] = mapped_column(String(64))
    verification_status: Mapped[str] = mapped_column(String(32), default="verified")
    reviewer: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    question: Mapped[Question] = relationship(back_populates="verified_answer")


# ---------------------------------------------------------------------------
# Learning, progress, revision
# ---------------------------------------------------------------------------
class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    selected_answer: Mapped[str | None] = mapped_column(String(128))
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    marks_awarded: Mapped[float | None] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String(32), default="practice")
    confidence: Mapped[str | None] = mapped_column(String(16))
    working_text: Mapped[str] = mapped_column(Text, default="")
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Progress(Base):
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("level", "ref_id", name="uq_progress_level_ref"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(16))  # subject/topic/subtopic/concept
    ref_id: Mapped[int] = mapped_column(Integer)
    attempted: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    incorrect: Mapped[int] = mapped_column(Integer, default=0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    distinct_questions: Mapped[int] = mapped_column(Integer, default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manual_status: Mapped[str | None] = mapped_column(String(24))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class RevisionItem(Base):
    __tablename__ = "revision_items"
    __table_args__ = (UniqueConstraint("question_id", name="uq_revision_question"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    ease: Mapped[float] = mapped_column(Float, default=2.5)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(40))
    filters: Mapped[dict | None] = mapped_column(JSON)
    question_ids: Mapped[list] = mapped_column(JSON)
    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id", ondelete="SET NULL"))
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# AI, solutions, verification
# ---------------------------------------------------------------------------
class AIRun(Base):
    __tablename__ = "ai_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(120))
    task: Mapped[str] = mapped_column(String(40))
    question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL")
    )
    mode: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default="success")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    request_sha256: Mapped[str] = mapped_column(String(64), default="")
    response_sha256: Mapped[str] = mapped_column(String(64), default="")
    request_excerpt: Mapped[str | None] = mapped_column(Text)
    response_excerpt: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    fallback_from: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TutorSession(Base):
    __tablename__ = "tutor_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL")
    )
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"))
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    mode: Mapped[str] = mapped_column(String(32), default="doubt")
    title: Mapped[str] = mapped_column(String(255), default="Tutor session")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["TutorMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="TutorMessage.id"
    )


class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("tutor_sessions.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(120))
    verification_status: Mapped[str | None] = mapped_column(String(32))
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_runs.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[TutorSession] = relationship(back_populates="messages")


class Solution(Base):
    __tablename__ = "solutions"
    __table_args__ = (UniqueConstraint("question_id", "version", name="uq_solution_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(120))
    learning_mode: Mapped[str] = mapped_column(String(40), default="solution")
    content: Mapped[str] = mapped_column(Text)
    final_answer: Mapped[str | None] = mapped_column(String(256))
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified_snapshot: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewer: Mapped[str | None] = mapped_column(String(80))
    review_notes: Mapped[str] = mapped_column(Text, default="")
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_runs.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    question: Mapped[Question] = relationship(back_populates="solutions")
    checks: Mapped[list["VerificationCheck"]] = relationship(
        back_populates="solution", cascade="all, delete-orphan", order_by="VerificationCheck.id"
    )


class VerificationCheck(Base):
    __tablename__ = "verification_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    solution_id: Mapped[int] = mapped_column(ForeignKey("solutions.id", ondelete="CASCADE"))
    check_type: Mapped[str] = mapped_column(String(64))
    tool: Mapped[str] = mapped_column(String(32), default="internal")
    description: Mapped[str] = mapped_column(Text, default="")
    input_data: Mapped[dict | None] = mapped_column(JSON)
    expected: Mapped[str | None] = mapped_column(Text)
    actual: Mapped[str | None] = mapped_column(Text)
    passed: Mapped[bool | None] = mapped_column(Boolean)
    independent: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    solution: Mapped[Solution] = relationship(back_populates="checks")


class ClassificationHistory(Base):
    __tablename__ = "classification_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    old_subject_id: Mapped[int | None] = mapped_column(Integer)
    old_topic_id: Mapped[int | None] = mapped_column(Integer)
    old_subtopic_id: Mapped[int | None] = mapped_column(Integer)
    old_confidence: Mapped[float | None] = mapped_column(Float)
    old_method: Mapped[str | None] = mapped_column(String(40))
    new_subject_id: Mapped[int | None] = mapped_column(Integer)
    new_topic_id: Mapped[int | None] = mapped_column(Integer)
    new_subtopic_id: Mapped[int | None] = mapped_column(Integer)
    new_confidence: Mapped[float | None] = mapped_column(Float)
    new_method: Mapped[str | None] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(80), default="user")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ClassificationBenchmark(Base):
    __tablename__ = "classification_benchmark"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), unique=True
    )
    expected_subject_id: Mapped[int | None] = mapped_column(Integer)
    expected_topic_id: Mapped[int | None] = mapped_column(Integer)
    expected_subtopic_id: Mapped[int | None] = mapped_column(Integer)
    expected_concepts: Mapped[list | None] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(Text, default="")
    verified_by: Mapped[str] = mapped_column(String(80), default="user")
    label_source: Mapped[str] = mapped_column(String(32), default="ai_assisted")
    reviewer: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Formula(Base, TimestampMixin):
    __tablename__ = "formulas"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"))
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    subtopic_id: Mapped[int | None] = mapped_column(
        ForeignKey("subtopics.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255))
    latex: Mapped[str] = mapped_column(Text)
    variable_definitions: Mapped[list | None] = mapped_column(JSON)
    units: Mapped[str] = mapped_column(Text, default="")
    applicability: Mapped[str] = mapped_column(Text, default="")
    derivation: Mapped[str] = mapped_column(Text, default="")
    common_mistakes: Mapped[str] = mapped_column(Text, default="")
    related_concepts: Mapped[str] = mapped_column(Text, default="")
    pyq_references: Mapped[list | None] = mapped_column(JSON)
    verification_status: Mapped[str] = mapped_column(String(24), default="proposed")
    source_solution_id: Mapped[int | None] = mapped_column(
        ForeignKey("solutions.id", ondelete="SET NULL")
    )
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(80))


# ---------------------------------------------------------------------------
# Ingestion, settings, audit
# ---------------------------------------------------------------------------
class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    stored_path: Mapped[str] = mapped_column(String(512), default="")
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    stage: Mapped[str] = mapped_column(String(48), default="queued")
    stats: Mapped[dict | None] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    files: Mapped[list["IngestionFile"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class IngestionFile(Base):
    __tablename__ = "ingestion_files"
    __table_args__ = (UniqueConstraint("job_id", "relative_path", name="uq_job_file"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("ingestion_jobs.id", ondelete="CASCADE"))
    relative_path: Mapped[str] = mapped_column(String(512))
    stored_path: Mapped[str] = mapped_column(String(512), default="")
    sha256: Mapped[str] = mapped_column(String(64), default="")
    file_kind: Mapped[str] = mapped_column(String(32), default="unknown")
    status: Mapped[str] = mapped_column(String(24), default="pending")
    year: Mapped[int | None] = mapped_column(Integer)
    session: Mapped[str | None] = mapped_column(String(80))
    page_count: Mapped[int | None] = mapped_column(Integer)
    questions_found: Mapped[int] = mapped_column(Integer, default=0)
    answers_found: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    warnings: Mapped[list | None] = mapped_column(JSON, default=list)
    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id", ondelete="SET NULL"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped[IngestionJob] = relationship(back_populates="files")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
