"""Seed the official GATE 2027 CS syllabus and the expanded taxonomy.

Idempotent: safe to run after upgrades. Existing taxonomy rows are updated in
place; IDs (and therefore historical question mappings) are preserved.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.db import SessionLocal, init_fts
from app.models import Concept, Subject, Subtopic, SyllabusSection, SyllabusVersion, Topic
from app.taxonomy_seed import OFFICIAL_SECTIONS, TAXONOMY
from app.utils import file_sha256, slugify

SOURCE_URL = "https://gate2027.iitm.ac.in/exam_papers_and_syllabus"
CS_URL = "https://gate2027.iitm.ac.in/static/doc/GATE2027_Syllabus/CS_GATE2027_Syllabus.pdf"
GA_URL = "https://gate2027.iitm.ac.in/static/doc/GATE2027_Syllabus/GA_GATE2027_Syllabus.pdf"


def seed(db: Session) -> dict:
    official_dir = settings.official_dir
    official_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for name in ("CS_GATE2027_Syllabus.pdf", "GA_GATE2027_Syllabus.pdf"):
        src = BASE_DIR / "data" / name
        if src.exists():
            dst = official_dir / name
            if not dst.exists() or file_sha256(dst) != file_sha256(src):
                shutil.copy2(src, dst)
            copied.append(dst)

    combined = b""
    for path in copied:
        combined += path.read_bytes()
    sha = file_sha256(copied[0]) if copied else "unavailable"
    if len(copied) == 2:
        import hashlib

        combined_hash = hashlib.sha256()
        for path in copied:
            combined_hash.update(path.read_bytes())
        sha = combined_hash.hexdigest()

    version = db.scalar(
        select(SyllabusVersion).where(
            SyllabusVersion.year == 2027,
            SyllabusVersion.paper_code == "CS",
            SyllabusVersion.is_active.is_(True),
        )
    )
    if version is None:
        version = SyllabusVersion(
            year=2027,
            paper_code="CS",
            title="GATE 2027 Computer Science & Information Technology (official)",
            source_url=SOURCE_URL,
            source_sha256=sha,
        )
        db.add(version)
        db.flush()

    section_by_code: dict[str, SyllabusSection] = {}
    for order, item in enumerate(OFFICIAL_SECTIONS):
        section = db.scalar(
            select(SyllabusSection).where(
                SyllabusSection.version_id == version.id, SyllabusSection.code == item["code"]
            )
        )
        if section is None:
            section = SyllabusSection(version_id=version.id, code=item["code"])
            db.add(section)
        section.title = item["title"]
        section.category = item["category"]
        section.official_text = item["text"]
        section.display_order = order
        section_by_code[item["code"]] = section
    db.flush()

    for order, subject_def in enumerate(TAXONOMY):
        subject = db.scalar(select(Subject).where(Subject.code == subject_def["code"]))
        if subject is None:
            subject = Subject(code=subject_def["code"])
            db.add(subject)
        subject.name = subject_def["name"]
        subject.section_code = ",".join(subject_def["sections"])
        subject.description = subject_def["description"]
        subject.color = subject_def["color"]
        subject.display_order = order
        db.flush()

        for t_order, topic_def in enumerate(subject_def["topics"]):
            topic = db.scalar(
                select(Topic).where(
                    Topic.subject_id == subject.id, Topic.slug == slugify(topic_def["name"])
                )
            )
            if topic is None:
                topic = Topic(subject_id=subject.id, slug=slugify(topic_def["name"]))
                db.add(topic)
            topic.name = topic_def["name"]
            topic.section_id = section_by_code[topic_def["section"]].id
            topic.description = topic_def.get("description", "")
            topic.keywords = topic_def.get("keywords", "")
            topic.display_order = t_order
            db.flush()

            for s_order, sub_def in enumerate(topic_def["subtopics"]):
                sub = db.scalar(
                    select(Subtopic).where(
                        Subtopic.topic_id == topic.id, Subtopic.slug == slugify(sub_def["name"])
                    )
                )
                if sub is None:
                    sub = Subtopic(topic_id=topic.id, slug=slugify(sub_def["name"]))
                    db.add(sub)
                sub.name = sub_def["name"]
                sub.description = sub_def.get("description", "")
                sub.keywords = sub_def.get("keywords", "")
                sub.display_order = s_order
                db.flush()

                for c_order, (c_name, c_desc, c_keywords) in enumerate(sub_def["concepts"]):
                    concept = db.scalar(
                        select(Concept).where(
                            Concept.subtopic_id == sub.id, Concept.slug == slugify(c_name)
                        )
                    )
                    if concept is None:
                        concept = Concept(subtopic_id=sub.id, slug=slugify(c_name))
                        db.add(concept)
                    concept.name = c_name
                    concept.description = c_desc
                    concept.keywords = c_keywords
                    concept.display_order = c_order

    db.commit()
    init_fts()
    return {
        "syllabus_version_id": version.id,
        "syllabus_sha256": sha,
        "subjects": len(TAXONOMY),
        "topics": sum(len(s["topics"]) for s in TAXONOMY),
        "subtopics": sum(len(t["subtopics"]) for s in TAXONOMY for t in s["topics"]),
        "concepts": sum(
            len(st["concepts"]) for s in TAXONOMY for t in s["topics"] for st in t["subtopics"]
        ),
        "official_pdfs": [str(p.name) for p in copied],
    }


def main() -> None:
    with SessionLocal() as db:
        stats = seed(db)
    print("Seeded GATE 2027 taxonomy:", stats)


if __name__ == "__main__":
    main()
