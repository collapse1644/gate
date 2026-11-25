"""PDF extraction tests. No OCR is used anywhere in this pipeline."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from app.services.pdf_extract import inspect_pdf


def write_pdf(path: Path, lines: list[str], *, start_y: float = 60) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    y = start_y
    for line in lines:
        page.insert_text((50, y), line, fontsize=10)
        y += 18
    doc.save(path)
    doc.close()
    return path


QUESTION_LINES = [
    "GATE 2027",
    "Q.1 to Q.2 carry 1 mark each.",
    "Q.1 Consider the following recurrence relation T(n) = 2T(n/2) + n.",
    "(A) O(n)",
    "(B) O(n log n)",
    "(C) O(n squared)",
    "(D) O(log n)",
    "Q.2 Which of the following is a tautology in propositional logic?",
    "(A) P and not P",
    "(B) P or not P",
    "(C) P and Q",
    "(D) P implies Q",
]


def test_question_paper_parsing(tmp_path):
    pdf = write_pdf(tmp_path / "CS_GATE2027_Question_Paper.pdf", QUESTION_LINES)
    info = inspect_pdf(pdf)
    assert info.kind == "question_paper"
    assert info.year == 2027
    assert info.has_text_layer is True
    assert [q.question_no for q in info.questions] == [1, 2]

    first = info.questions[0]
    assert "recurrence relation" in first.text
    assert [o["key"] for o in first.options] == ["A", "B", "C", "D"]
    assert first.marks == 1.0
    assert first.question_type == "MCQ"
    assert first.negative_marks == pytest.approx(-1 / 3)
    assert first.confidence > 0.5


def test_answer_key_parsing(tmp_path):
    pdf = write_pdf(
        tmp_path / "CS_GATE2027_Answer_Key.pdf",
        ["GATE 2027 Answer Key", "1 B", "2 B", "3 42", "4 MTA"],
    )
    info = inspect_pdf(pdf)
    assert info.kind == "answer_key"
    answers = {a.question_no: a.answer for a in info.answers}
    assert answers == {1: "B", 2: "B", 3: "42", 4: "MTA"}


def test_scanned_pdf_is_flagged_not_ocrd(tmp_path):
    pdf = tmp_path / "scan.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(40, 40, 400, 300), color=(0, 0, 0))
    doc.save(pdf)
    doc.close()

    info = inspect_pdf(pdf)
    assert info.has_text_layer is False
    assert info.questions == []
    assert any("OCR was not run" in warning for warning in info.warnings)


def test_figure_is_clipped_and_associated(tmp_path):
    pdf = tmp_path / "CS_GATE2027_Question_Paper_figures.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 60), "Q.1 The circuit shown below implements a multiplexer.", fontsize=10)
    page.insert_text((50, 96), "(A) 2 to 1", fontsize=10)
    page.insert_text((50, 114), "(B) 4 to 1", fontsize=10)
    page.insert_text((50, 132), "(C) 8 to 1", fontsize=10)
    page.insert_text((50, 150), "(D) 16 to 1", fontsize=10)
    draw = pymupdf.Rect(60, 180, 260, 280)
    page.draw_rect(draw, color=(0, 0, 0), width=1.5)
    page.draw_line((60, 230), (260, 230), color=(0, 0, 0), width=1)
    doc.save(pdf)
    doc.close()

    assets = tmp_path / "assets"
    info = inspect_pdf(pdf, output_assets_dir=assets)
    assert len(info.questions) == 1
    question = info.questions[0]
    assert question.assets, "the diagram region should be preserved as an asset"
    asset = question.assets[0]
    saved = Path(asset["path"])
    assert saved.is_file()
    assert saved.stat().st_size > 0
    assert asset["sha256"]
    assert asset["page"] == 1


def test_instruction_lines_do_not_become_questions(tmp_path):
    pdf = write_pdf(
        tmp_path / "CS_GATE2027_Question_Paper_2.pdf",
        ["GATE 2027", "Q.1 to Q.2 carry 2 marks each.", "Q.1 Explain paging in one paragraph of text."],
    )
    info = inspect_pdf(pdf)
    assert len(info.questions) == 1
    assert "paging" in info.questions[0].text.lower()
    assert info.questions[0].marks == 2.0
