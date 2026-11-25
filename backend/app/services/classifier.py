"""Hybrid taxonomy classifier.

Signals, in order of importance:
1. Official syllabus taxonomy (subject -> section -> topic -> subtopic).
2. Discriminative keyword/phrase rules with word-boundary matching.
3. TF-IDF similarity against curated subtopic descriptions.
4. Optional LLM recommendation, used only as a bounded ranking adjustment.

Low-confidence results are never auto-accepted. They are placed in the review
queue with the classifier's candidate list preserved in the review notes.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Concept, Subject, Subtopic, Topic

STOPWORDS = {
    "a", "an", "the", "of", "is", "are", "was", "were", "be", "been", "in", "on",
    "at", "to", "for", "with", "and", "or", "if", "then", "else", "which", "what",
    "following", "consider", "question", "answer", "marks", "mark", "given", "let",
    "can", "will", "would", "should", "this", "that", "these", "those", "it", "its",
    "as", "by", "from", "not", "no", "all", "any", "each", "how", "many", "much",
    "using", "used", "use", "value", "number", "following", "statement", "statements",
    "true", "false", "correct", "incorrect", "option", "options", "select", "choose",
}


def _stem(token: str) -> str:
    for suffix in ("ing", "edly", "ed", "ies", "es", "s"):
        if len(token) > 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _tokens(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    tokens = re.findall(r"[a-z][a-z0-9+#._'-]{1,}", text)
    return [_stem(t) for t in tokens if t not in STOPWORDS and len(t) > 1]


def _phrase_pattern(phrase: str) -> re.Pattern | None:
    phrase = phrase.strip().lower()
    if not phrase or len(phrase) < 2:
        return None
    escaped = re.escape(phrase).replace(r"\ ", r"[\s\-]+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.I)


@dataclass
class SubtopicCandidate:
    subtopic_id: int
    subtopic_name: str
    topic_id: int
    topic_name: str
    subject_id: int
    subject_name: str
    section_id: int | None
    rule_score: float = 0.0
    tfidf_score: float = 0.0
    matched_terms: list[str] = field(default_factory=list)
    matched_concepts: list[int] = field(default_factory=list)
    total_score: float = 0.0


@dataclass
class ClassificationResult:
    subject_id: int | None
    section_id: int | None
    topic_id: int | None
    subtopic_id: int | None
    concept_ids: list[int]
    secondary_topic_ids: list[int]
    confidence: float
    method: str
    review_status: str
    out_of_syllabus: bool
    ambiguous: bool
    candidates: list[dict]
    explanation: str


class TaxonomyIndex:
    def __init__(self, db: Session):
        rows = db.scalars(
            select(Subtopic)
            .options(
                joinedload(Subtopic.topic).joinedload(Topic.subject),
                joinedload(Subtopic.concepts),
            )
        ).unique().all()
        self.subtopics = rows
        self.candidates: list[SubtopicCandidate] = []
        self.documents: list[Counter] = []
        self.phrases: dict[int, list[tuple[str, float]]] = {}
        self.concepts_by_subtopic: dict[int, list[Concept]] = {}
        for sub in rows:
            topic = sub.topic
            subject = topic.subject
            cand = SubtopicCandidate(
                subtopic_id=sub.id,
                subtopic_name=sub.name,
                topic_id=topic.id,
                topic_name=topic.name,
                subject_id=subject.id,
                subject_name=subject.name,
                section_id=topic.section_id,
            )
            self.candidates.append(cand)
            concept_terms = []
            for concept in sub.concepts:
                self.concepts_by_subtopic.setdefault(sub.id, []).append(concept)
                concept_terms.extend([concept.name, concept.keywords])
            doc_text = " ".join(
                [subject.name, topic.name, sub.name, sub.description, sub.keywords, *concept_terms]
            )
            self.documents.append(Counter(_tokens(doc_text)))
            weighted: list[tuple[str, float]] = []
            for phrase in _split_terms(sub.keywords):
                weight = 3.0 if len(phrase.split()) > 1 else 1.25
                weighted.append((phrase, weight))
            for phrase in _split_terms(topic.keywords):
                if len(phrase.split()) > 1:
                    weighted.append((phrase, 1.4))
            for concept in sub.concepts:
                for phrase in _split_terms(concept.keywords):
                    weighted.append((phrase, 0.55 if len(phrase.split()) == 1 else 1.1))
                weighted.append((concept.name, 1.5))
            weighted.append((sub.name, 2.5))
            # Deduplicate, keeping max weight.
            best: dict[str, float] = {}
            for phrase, weight in weighted:
                key = phrase.lower().strip()
                if len(key) < 2:
                    continue
                best[key] = max(best.get(key, 0), weight)
            self.phrases[sub.id] = list(best.items())

        n = max(1, len(self.documents))
        df: Counter = Counter()
        for doc in self.documents:
            for term in doc:
                df[term] += 1
        self.idf = {term: math.log((n + 1) / (count + 0.5)) + 1 for term, count in df.items()}

    def _tfidf(self, tokens: list[str], doc: Counter) -> float:
        if not tokens or not doc:
            return 0.0
        q = Counter(tokens)
        dot = 0.0
        q_norm = 0.0
        for term, count in q.items():
            weight = (1 + math.log(count)) * self.idf.get(term, 1.0)
            q_norm += weight * weight
            if term in doc:
                d_weight = (1 + math.log(doc[term])) * self.idf.get(term, 1.0)
                dot += weight * d_weight
        d_norm = sum(
            ((1 + math.log(c)) * self.idf.get(t, 1.0)) ** 2 for t, c in doc.items()
        )
        if q_norm <= 0 or d_norm <= 0:
            return 0.0
        return dot / math.sqrt(q_norm * d_norm)


def _split_terms(value: str | None) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in re.split(r"[,;]", value) if p.strip()]


def _concept_matches(concept: Concept, text: str) -> bool:
    for phrase in [concept.name, *_split_terms(concept.keywords)]:
        pattern = _phrase_pattern(phrase)
        if pattern and pattern.search(text):
            return True
    return False


def classify_question(
    db: Session,
    *,
    text: str,
    options: list[dict] | None = None,
    llm_recommendation: dict | None = None,
    review_threshold: float | None = None,
    accept_threshold: float | None = None,
) -> ClassificationResult:
    index = getattr(db, "_taxonomy_index", None)
    if index is None:
        index = TaxonomyIndex(db)
        db._taxonomy_index = index  # type: ignore[attr-defined]

    haystack = text + "\n" + "\n".join(o.get("text", "") for o in (options or []))
    lowered = haystack.lower()
    q_tokens = _tokens(haystack)

    ranked: list[SubtopicCandidate] = []
    for cand, doc in zip(index.candidates, index.documents, strict=False):
        score = 0.0
        matched: list[str] = []
        for phrase, weight in index.phrases.get(cand.subtopic_id, []):
            pattern = _phrase_pattern(phrase)
            if pattern and pattern.search(lowered):
                # Multi-word matches are stronger and repeated occurrences add little.
                score += weight
                matched.append(phrase)
        tfidf = index._tfidf(q_tokens, doc)
        cand.rule_score = score
        cand.tfidf_score = tfidf
        cand.total_score = score + 3.2 * tfidf
        cand.matched_terms = matched[:12]
        # Concept IDs from this subtopic.
        for concept in index.concepts_by_subtopic.get(cand.subtopic_id, []):
            if _concept_matches(concept, lowered):
                cand.matched_concepts.append(concept.id)
        ranked.append(cand)

    ranked.sort(key=lambda c: c.total_score, reverse=True)

    if llm_recommendation:
        llm_subtopic = _resolve_llm_candidate(llm_recommendation, ranked)
        if llm_subtopic is not None:
            llm_subtopic.total_score += 3.0
            ranked.sort(key=lambda c: c.total_score, reverse=True)

    top = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None
    if top is None or top.total_score < 1.5:
        return ClassificationResult(
            subject_id=None,
            section_id=None,
            topic_id=None,
            subtopic_id=None,
            concept_ids=[],
            secondary_topic_ids=[],
            confidence=0.0,
            method="rules+tfidf",
            review_status="out_of_syllabus",
            out_of_syllabus=True,
            ambiguous=True,
            candidates=_candidate_dicts(ranked[:3]),
            explanation="No sufficiently strong syllabus signal; not forced into a topic.",
        )

    evidence = min(1.0, top.total_score / 12.0)
    gap = top.total_score - (second.total_score if second else 0)
    separation = clamp01(gap / max(1.0, top.total_score))
    confidence = clamp01(0.12 + 0.62 * evidence + 0.24 * separation)
    if llm_recommendation:
        confidence = clamp01(confidence + 0.04)

    low = review_threshold if review_threshold is not None else 0.55
    high = accept_threshold if accept_threshold is not None else 0.72
    ambiguous = gap < 2.0 or confidence < low
    if confidence >= high and not ambiguous:
        review_status = "auto_accepted" if not llm_recommendation else "pending"
    elif confidence >= low:
        review_status = "pending"
    else:
        review_status = "pending"

    method = "rules+tfidf"
    if llm_recommendation:
        method = "hybrid"
        # An LLM opinion alone is never enough to auto-accept.
        if review_status == "auto_accepted":
            review_status = "pending"

    concept_ids = list(dict.fromkeys(top.matched_concepts))[:6]
    secondary: list[int] = []
    for cand in ranked[1:4]:
        if cand.topic_id != top.topic_id and cand.total_score >= top.total_score * 0.55:
            secondary.append(cand.topic_id)

    explanation = (
        f"Best match: {top.subject_name} → {top.topic_name} → {top.subtopic_name}. "
        f"Matched terms: {', '.join(top.matched_terms[:8]) or 'semantic similarity only'}. "
        f"Top score {top.total_score:.2f}; runner-up "
        f"{second.total_score:.2f} ({second.subtopic_name if second else 'none'})."
    )
    return ClassificationResult(
        subject_id=top.subject_id,
        section_id=top.section_id,
        topic_id=top.topic_id,
        subtopic_id=top.subtopic_id,
        concept_ids=concept_ids,
        secondary_topic_ids=list(dict.fromkeys(secondary)),
        confidence=round(confidence, 4),
        method=method,
        review_status=review_status,
        out_of_syllabus=False,
        ambiguous=ambiguous,
        candidates=_candidate_dicts(ranked[:5]),
        explanation=explanation,
    )


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _candidate_dicts(candidates: list[SubtopicCandidate]) -> list[dict]:
    return [
        {
            "subject_id": c.subject_id,
            "subject": c.subject_name,
            "topic_id": c.topic_id,
            "topic": c.topic_name,
            "subtopic_id": c.subtopic_id,
            "subtopic": c.subtopic_name,
            "score": round(c.total_score, 3),
            "matched_terms": c.matched_terms[:6],
        }
        for c in candidates
    ]


def _resolve_llm_candidate(
    recommendation: dict, candidates: list[SubtopicCandidate]
) -> SubtopicCandidate | None:
    names = {
        str(recommendation.get("subtopic_id", "")),
        str(recommendation.get("subtopic", "")).lower(),
        str(recommendation.get("subtopic_name", "")).lower(),
    }
    for cand in candidates:
        if (
            str(cand.subtopic_id) in names
            or cand.subtopic_name.lower() in names
        ):
            return cand
    return None


def benchmark_report(db: Session) -> dict:
    from app.models import ClassificationBenchmark, Question

    rows = db.scalars(select(ClassificationBenchmark)).all()
    total = len(rows)
    subject_ok = topic_ok = subtopic_ok = 0
    hv_subject_ok = hv_topic_ok = hv_subtopic_ok = hv_total = 0
    details = []
    for row in rows:
        question = db.get(Question, row.question_id)
        if question is None:
            continue
        s = question.subject_id == row.expected_subject_id
        t = question.topic_id == row.expected_topic_id
        st = question.subtopic_id == row.expected_subtopic_id
        subject_ok += int(s)
        topic_ok += int(t)
        subtopic_ok += int(st)
        is_human = getattr(row, "label_source", "ai_assisted") == "human_verified"
        if is_human:
            hv_total += 1
            hv_subject_ok += int(s)
            hv_topic_ok += int(t)
            hv_subtopic_ok += int(st)
        details.append(
            {
                "question_id": question.id,
                "question_no": question.question_no,
                "year": question.year,
                "predicted": {
                    "subject_id": question.subject_id,
                    "topic_id": question.topic_id,
                    "subtopic_id": question.subtopic_id,
                    "confidence": question.classification_confidence,
                },
                "expected": {
                    "subject_id": row.expected_subject_id,
                    "topic_id": row.expected_topic_id,
                    "subtopic_id": row.expected_subtopic_id,
                },
                "subject_correct": s,
                "topic_correct": t,
                "subtopic_correct": st,
                "label_source": getattr(row, "label_source", "ai_assisted"),
            }
        )
    return {
        "total": total,
        "subject_accuracy": round(subject_ok / total, 4) if total else None,
        "topic_accuracy": round(topic_ok / total, 4) if total else None,
        "subtopic_accuracy": round(subtopic_ok / total, 4) if total else None,
        "human_verified_count": hv_total,
        "human_verified_subject_accuracy": round(hv_subject_ok / hv_total, 4) if hv_total else None,
        "human_verified_topic_accuracy": round(hv_topic_ok / hv_total, 4) if hv_total else None,
        "human_verified_subtopic_accuracy": round(hv_subtopic_ok / hv_total, 4) if hv_total else None,
        "details": details,
        "note": "Benchmark is manually curated; accuracy measures agreement with your reviewed labels. AI-assisted labels are excluded from human-verified accuracy.",
    }


def taxonomy_tree(db: Session) -> list[dict]:
    subjects = db.scalars(
        select(Subject)
        .options(joinedload(Subject.topics).joinedload(Topic.subtopics).joinedload(Subtopic.concepts))
        .order_by(Subject.display_order)
    ).unique().all()
    tree = []
    for subject in subjects:
        s = {
            "id": subject.id,
            "code": subject.code,
            "name": subject.name,
            "description": subject.description,
            "color": subject.color,
            "topics": [],
        }
        for topic in subject.topics:
            t = {
                "id": topic.id,
                "name": topic.name,
                "section_id": topic.section_id,
                "subtopics": [
                    {
                        "id": sub.id,
                        "name": sub.name,
                        "concepts": [
                            {"id": c.id, "name": c.name, "description": c.description}
                            for c in sub.concepts
                        ],
                    }
                    for sub in topic.subtopics
                ],
            }
            s["topics"].append(t)
        tree.append(s)
    return tree
