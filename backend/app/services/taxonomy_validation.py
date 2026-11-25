from __future__ import annotations

from collections import Counter, defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Concept, Subject, Subtopic, Topic


def validate_taxonomy(db: Session) -> dict:
    issues: list[dict] = []

    subjects = db.scalars(select(Subject)).all()
    topics = db.scalars(select(Topic)).all()
    subtopics = db.scalars(select(Subtopic)).all()
    concepts = db.scalars(select(Concept)).all()

    # Duplicate subject codes/names
    for field_name, values in (("code", [s.code for s in subjects]), ("name", [s.name for s in subjects])):
        counts = Counter(values)
        for value, count in counts.items():
            if count > 1:
                issues.append({"type": f"duplicate_subject_{field_name}", "detail": value})

    # Orphan topics
    subject_ids = {s.id for s in subjects}
    for t in topics:
        if t.subject_id not in subject_ids:
            issues.append({"type": "orphan_topic", "detail": {"topic_id": t.id, "subject_id": t.subject_id}})

    # Orphan subtopics
    topic_ids = {t.id for t in topics}
    for st in subtopics:
        if st.topic_id not in topic_ids:
            issues.append({"type": "orphan_subtopic", "detail": {"subtopic_id": st.id, "topic_id": st.topic_id}})

    # Orphan concepts
    subtopic_ids = {st.id for st in subtopics}
    for c in concepts:
        if c.subtopic_id not in subtopic_ids:
            issues.append({"type": "orphan_concept", "detail": {"concept_id": c.id, "subtopic_id": c.subtopic_id}})

    # Duplicate topics within same subject
    seen_topics: set[tuple[int, str]] = set()
    for t in topics:
        key = (t.subject_id, t.name.strip().lower())
        if key in seen_topics:
            issues.append({"type": "duplicate_topic", "detail": {"subject_id": t.subject_id, "name": t.name}})
        seen_topics.add(key)

    # Duplicate subtopics within same topic
    seen_subtopics: set[tuple[int, str]] = set()
    for st in subtopics:
        key = (st.topic_id, st.name.strip().lower())
        if key in seen_subtopics:
            issues.append({"type": "duplicate_subtopic", "detail": {"topic_id": st.topic_id, "name": st.name}})
        seen_subtopics.add(key)

    return {
        "ok": not issues,
        "issues": issues,
        "counts": {
            "subjects": len(subjects),
            "topics": len(topics),
            "subtopics": len(subtopics),
            "concepts": len(concepts),
        },
    }