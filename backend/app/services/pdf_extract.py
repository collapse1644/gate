"""PDF extraction for official GATE question papers and answer keys.

Text is extracted from the PDF text layer. OCR is deliberately not used. Pages
with no text layer are flagged for manual review. Figures are preserved by
clipping the original PDF page (so vector diagrams and embedded raster images
are kept exactly as published).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from app.utils import clamp, content_hash, normalize_text, slugify

QUESTION_START = re.compile(r"^\s*(?:Q\.?\s*)(\d{1,3})\b|^\s*(\d{1,3})[\.\)]\s+")
OPTION_MARKER = re.compile(r"\(([A-D])\)")
HEADER_PATTERNS = [
    re.compile(r"^\s*GATE\s*20\d\d\b", re.I),
    re.compile(r"^\s*Computer Science\s*(?:&|and)?\s*Information Technology\s*$", re.I),
    re.compile(r"^\s*CS\s*$", re.I),
    re.compile(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", re.I),
    re.compile(r"^\s*\d{1,3}\s*$"),
    re.compile(r"IIT\s+(?:Madras|Bombay|Delhi|Kanpur|Kharagpur|Roorkee|Guwahati)", re.I),
]
SESSION_PATTERNS = [
    re.compile(r"\b(?:session|shift)\s*[-:]?\s*([12])\b", re.I),
    re.compile(r"\b(forenoon|afternoon|morning|evening)\b", re.I),
    re.compile(r"\b(FN|AN)\b"),
]


@dataclass
class TextLine:
    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class QuestionDraft:
    question_no: int
    text: str
    options: list[dict]
    question_type: str
    marks: float | None
    negative_marks: float | None
    marks_source: str
    page_start: int
    page_end: int
    y_start: float
    y_end: float
    confidence: float
    notes: list[str] = field(default_factory=list)
    assets: list[dict] = field(default_factory=list)


@dataclass
class AnswerDraft:
    question_no: int
    answer: str
    page: int
    section: str | None = None
    section: str | None = None


@dataclass
class PdfInfo:
    kind: str
    year: int | None
    session: str | None
    page_count: int
    has_text_layer: bool
    text: str
    questions: list[QuestionDraft] = field(default_factory=list)
    answers: list[AnswerDraft] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Metadata detection
# ---------------------------------------------------------------------------
def detect_year_session(filename: str, text: str) -> tuple[int | None, str | None]:
    file_years = [int(y) for y in re.findall(r"(?<!\d)(20[12]\d)(?!\d)", filename)]
    file_years = [y for y in file_years if 2010 <= y <= 2030]
    year = None
    if file_years:
        year = max(set(file_years), key=file_years.count)
    else:
        years = [int(y) for y in re.findall(r"(?<!\d)(20[12]\d)(?!\d)", text[:4000])]
        plausible = [y for y in years if 2010 <= y <= 2030]
        if plausible:
            year = max(set(plausible), key=plausible.count)

    haystack = f"{filename}\n{text[:4000]}"
    session = None
    # GATE uses Set 1 / Set 2 (also called sessions).
    set_match = re.search(r"\bset\s*[-_ ]?\s*([12])\b", haystack, re.I)
    if not set_match:
        set_match = re.search(r"(?<![A-Za-z])CS\s*([12])(?![0-9])", haystack, re.I)
    if set_match:
        session = f"Set {set_match.group(1)}"
    else:
        for pattern in SESSION_PATTERNS:
            match = pattern.search(haystack)
            if match:
                token = match.group(1).lower()
                if token in {"1", "2"}:
                    session = f"Set {token}"
                elif token in {"fn", "forenoon", "morning"}:
                    session = "Forenoon"
                elif token in {"an", "afternoon", "evening"}:
                    session = "Afternoon"
                break
    return year, session

def detect_kind(filename: str, text: str) -> tuple[str, float]:
    lower = filename.lower()
    head = text[:12000].lower()
    if "answer key" in head or "answer-key" in lower or re.search(r"\banswer\s*key", head):
        return "answer_key", 0.98
    if re.search(r"(answer|key)", lower) and "question" not in lower:
        return "answer_key", 0.8
    if re.search(r"(question\s*paper|paper)", lower):
        return "question_paper", 0.9
    q_count = sum(1 for line in text.splitlines() if QUESTION_START.match(line))
    if q_count >= 3 and ("(a)" in head or "(A)" in text[:12000]):
        return "question_paper", 0.8
    if q_count >= 3:
        return "question_paper", 0.6
    return "unknown", 0.2


# ---------------------------------------------------------------------------
# Text/line extraction
# ---------------------------------------------------------------------------
def _extract_lines(doc: pymupdf.Document) -> list[TextLine]:
    lines: list[TextLine] = []
    for page_index, page in enumerate(doc):
        data = page.get_text("dict")
        page_lines: list[TextLine] = []
        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                text = "".join(span.get("text", "") for span in line.get("spans", []))
                text = normalize_text(text)
                if not text:
                    continue
                x0, y0, x1, y1 = line.get("bbox", (0, 0, 0, 0))
                page_lines.append(TextLine(page_index, text, x0, y0, x1, y1))
        page_lines.sort(key=lambda ln: (round(ln.y0, 1), ln.x0))
        lines.extend(page_lines)
    return lines


def _strip_headers(lines: list[TextLine], page_count: int) -> list[TextLine]:
    from collections import Counter

    counts = Counter(ln.text for ln in lines)
    result = []
    for line in lines:
        text = line.text.strip()
        if any(p.match(text) for p in HEADER_PATTERNS):
            continue
        if counts[text] >= max(3, page_count) and len(text) < 90 and not OPTION_MARKER.search(text):
            continue
        result.append(line)
    return result


def _join_lines(lines: list[TextLine]) -> str:
    pieces: list[str] = []
    for line in lines:
        text = line.text.strip()
        if not text:
            continue
        pieces.append(text)
    # Preserve line structure for code blocks while removing page-header noise.
    joined = "\n".join(pieces)
    joined = re.sub(r"[ \t]+", " ", joined)
    return joined.strip()


# ---------------------------------------------------------------------------
# Marks / type maps
# ---------------------------------------------------------------------------
def build_marks_map(full_text: str) -> tuple[dict[int, tuple[float, str]], dict[int, str]]:
    marks: dict[int, tuple[float, str]] = {}
    types: dict[int, str] = {}
    WORD_MARKS = {"one": 1.0, "two": 2.0, "1": 1.0, "2": 2.0}
    for match in re.finditer(
        r"(?:(?:Q\.?\s*)?)(\d{1,3})\s*(?:to|[-–])\s*(?:Q\.?\s*)?(\d{1,3})\s*(?:carry|carries|carrying)?\s*(?:(\d|one|two)\s*marks?|MCQ|MSQ|NAT)?",
        full_text,
        re.I,
    ):
        start_q, end_q = int(match.group(1)), int(match.group(2))
        if not (1 <= start_q <= end_q <= 100):
            continue
        tail_start = match.end()
        tail = full_text[tail_start : tail_start + 220]
        mark_match = re.search(r"(\d|one|two)\s*marks?", tail, re.I)
        if mark_match:
            token = mark_match.group(1).lower()
            mark = WORD_MARKS.get(token)
            if mark is not None:
                for q in range(start_q, end_q + 1):
                    marks.setdefault(q, (mark, "paper_instructions"))
        type_match = re.search(r"\b(MCQ|MSQ|NAT)\b", tail, re.I)
        if type_match:
            for q in range(start_q, end_q + 1):
                types.setdefault(q, type_match.group(1).upper())
    for match in re.finditer(
        r"(\d{1,3})\s*(?:to|[-–])\s*(?:Q\.?\s*)?(\d{1,3})\s*(?:carry|carries)\s*(\d|one|two)\s*marks?",
        full_text,
        re.I,
    ):
        start_q, end_q = int(match.group(1)), int(match.group(2))
        token = match.group(3).lower()
        mark = WORD_MARKS.get(token)
        if mark is None:
            continue
        if 1 <= start_q <= end_q <= 100:
            for q in range(start_q, end_q + 1):
                marks.setdefault(q, (mark, "paper_instructions"))
    return marks, types


def negative_for(question_type: str, marks: float | None) -> float | None:
    if marks is None or question_type != "MCQ":
        return 0.0 if question_type in {"MSQ", "NAT"} else None
    if marks == 1:
        return -1 / 3
    if marks == 2:
        return -2 / 3
    return None


# ---------------------------------------------------------------------------
# Question parsing
# ---------------------------------------------------------------------------
def parse_questions(
    doc: pymupdf.Document,
    lines: list[TextLine],
    full_text: str,
    *,
    year: int | None,
    session: str | None,
) -> list[QuestionDraft]:
    marks_map, type_map = build_marks_map(full_text)
    starts: list[tuple[int, int, int]] = []  # (line index, qno, page)
    expected = 1
    for idx, line in enumerate(lines):
        match = QUESTION_START.match(line.text)
        if not match:
            continue
        qno = int(match.group(1) or match.group(2))
        if not (1 <= qno <= 100):
            continue
        # "Q.1 to Q.5 carry 1 mark each" is an instruction, not a question.
        if re.search(r"\b(?:carry|carries|carrying)\b", line.text, re.I) and re.search(
            r"\bmarks?\b", line.text, re.I
        ):
            continue
        explicit = line.text.lstrip().upper().startswith("Q")
        if not explicit and qno not in {expected, expected + 1}:
            continue
        if starts and qno <= starts[-1][1]:
            continue
        starts.append((idx, qno, line.page))
        expected = qno + 1

    drafts: list[QuestionDraft] = []
    for pos, (idx, qno, page) in enumerate(starts):
        end_idx = starts[pos + 1][0] if pos + 1 < len(starts) else len(lines)
        segment = lines[idx:end_idx]
        if not segment:
            continue
        text, options, option_note = _parse_segment(segment)
        if len(text) < 8:
            continue
        marks, marks_source = marks_map.get(qno, (None, "unknown"))
        qtype = type_map.get(qno)
        if qtype is None:
            qtype = "MCQ" if len(options) >= 2 else "NAT"
        # Multi-select questions are identified from the answer key later.
        negative = negative_for(qtype, marks)
        confidence, notes = _score_extraction(text, options, marks, segment)
        if len(text) < 25:
            notes.append("Very short question text; extraction may have missed content.")
            confidence -= 0.2
        if not options and qtype == "MCQ":
            notes.append("No options detected; check the original PDF.")
            confidence -= 0.25
        if option_note:
            notes.append(option_note)
        if marks is None:
            notes.append("Marks not found in paper instructions.")
        last = segment[-1]
        drafts.append(
            QuestionDraft(
                question_no=qno,
                text=text,
                options=options,
                question_type=qtype,
                marks=marks,
                negative_marks=negative,
                marks_source=marks_source,
                page_start=page + 1,
                page_end=last.page + 1,
                y_start=segment[0].y0,
                y_end=last.y1,
                confidence=clamp(confidence),
                notes=notes,
            )
        )
    return drafts


def _parse_segment(segment: list[TextLine]) -> tuple[str, list[dict], str | None]:
    combined = "\n".join(ln.text for ln in segment)
    marker_positions = list(OPTION_MARKER.finditer(combined))
    # A real options block starts at (A) and contains at least B.
    start_match = None
    for i, match in enumerate(marker_positions):
        if match.group(1) == "A":
            later = {m.group(1) for m in marker_positions[i + 1 : i + 6]}
            if "B" in later:
                start_match = match
                break
    if start_match is None:
        return normalize_text(combined), [], None

    question_text = normalize_text(combined[: start_match.start()])
    option_blob = combined[start_match.start() :]
    parts = re.split(r"\(([A-D])\)", option_blob)
    options: list[dict] = []
    # parts[0] is empty text before (A); then letter, text, letter, text...
    for i in range(1, len(parts) - 1, 2):
        letter = parts[i]
        value = normalize_text(parts[i + 1])
        if options and letter <= options[-1]["key"]:
            # Markers out of order: append text to previous option instead.
            options[-1]["text"] = normalize_text(options[-1]["text"] + " " + f"({letter})" + value)
            continue
        options.append({"key": letter, "text": value})

    expected = ["A", "B", "C", "D"]
    got = [o["key"] for o in options]
    note = None
    if len(options) < 4:
        note = f"Only {len(options)} options detected."
    if got != expected[: len(got)]:
        note = "Options were not in A-D order."
    # Drop accidental option fragments that are only a marker.
    options = [o for o in options if o["text"]]
    return question_text, options, note


def _score_extraction(
    text: str, options: list[dict], marks: float | None, segment: list[TextLine]
) -> tuple[float, list[str]]:
    score = 0.35
    notes: list[str] = []
    if len(text) >= 40:
        score += 0.2
    if len(text) >= 100:
        score += 0.1
    if len(options) == 4:
        score += 0.2
    elif len(options) >= 2:
        score += 0.1
    if marks is not None:
        score += 0.1
    if len(segment) >= 2:
        score += 0.05
    if re.search(r"\b(?:figure|diagram|shown below|circuit|graph)\b", text, re.I):
        notes.append("Question references a visual; verify the associated figure.")
    return clamp(score), notes


# ---------------------------------------------------------------------------
# Answer keys
# ---------------------------------------------------------------------------
def parse_answers(doc: pymupdf.Document, full_text: str) -> list[AnswerDraft]:
    answers: list[AnswerDraft] = []
    lines = full_text.splitlines()
    # Locate the answer-key section.
    start_idx = None
    for i, line in enumerate(lines):
        if "answer key" in line.lower():
            start_idx = i
            break
    if start_idx is None:
        return answers

    section_lines = lines[start_idx:]
    # Detect tabular layout (GATE 2020+ style).
    joined = "\n".join(section_lines).lower()
    tabular = "que.type" in joined or "que. type" in joined or "sec. name" in joined

    if tabular:
        # State machine over non-empty lines.
        i = 0
        n = len(section_lines)
        # skip header lines until first question number
        while i < n:
            # find next integer question number
            while i < n and not section_lines[i].strip().isdigit():
                i += 1
            if i >= n:
                break
            qno = int(section_lines[i].strip())
            if not (1 <= qno <= 100):
                i += 1
                continue
            # session
            i += 1
            while i < n and not section_lines[i].strip():
                i += 1
            if i >= n:
                break
            session = section_lines[i].strip()
            i += 1
            while i < n and not section_lines[i].strip():
                i += 1
            if i >= n:
                break
            qtype = section_lines[i].strip().upper()
            i += 1
            while i < n and not section_lines[i].strip():
                i += 1
            if i >= n:
                break
            sec = section_lines[i].strip()
            i += 1
            # accumulate key until a lone marks value (1 or 2) followed by qno/end
            key_parts: list[str] = []
            while i < n:
                cur = section_lines[i].strip()
                if not cur:
                    i += 1
                    continue
                # marks value?
                if cur in {"1", "2"}:
                    j = i + 1
                    while j < n and not section_lines[j].strip():
                        j += 1
                    nxt = section_lines[j].strip().lower() if j < n else ""
                    if j >= n or nxt.isdigit() or "copyright" in nxt or "gate" in nxt or not nxt:
                        marks = cur
                        i += 1
                        break
                key_parts.append(cur)
                i += 1
            else:
                marks = ""
            answer = " ".join(key_parts).strip()
            # normalise answer: if multiple letters separated by spaces -> comma list
            if "MTA" in answer.upper().split():
                answer = "MTA"
            else:
                letters = sorted(set(re.findall(r"[A-D]", answer.upper())))
                if qtype == "MSQ" and len(letters) > 1:
                    answer = ",".join(letters)
                elif qtype == "MCQ" and len(letters) == 1 and answer.upper() in {"A","B","C","D"}:
                    answer = letters[0]
                elif qtype == "NAT":
                    pass
            page = 0
            # page unknown from text; leave 0
            answers.append(AnswerDraft(qno, answer, page, section=sec))
    else:
        # fallback: simple line-based parser
        ans_map: dict[int, str] = {}
        for page_index, page in enumerate(doc):
            text = page.get_text("text")
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                for match in re.finditer(
                    r"(?:Q\.?\s*)?(\d{1,3})\s*[\.\):\-]?\s*(?:\(([A-D])\)|\b([A-D]{1,4})\b|\b(MTA|M)\b|(-?\d+(?:\.\d+)?))",
                    stripped,
                    re.I,
                ):
                    qno = int(match.group(1))
                    if not (1 <= qno <= 100):
                        continue
                    letter = match.group(2)
                    if letter:
                        answer = letter.upper()
                    elif match.group(3):
                        token = match.group(3).upper()
                        if token in {"MTA", "M"}:
                            answer = "MTA"
                        elif len(token) <= 4 and set(token) <= {"A", "B", "C", "D"}:
                            answer = ",".join(sorted(set(token)))
                        else:
                            continue
                    elif match.group(4):
                        answer = "MTA"
                    else:
                        answer = match.group(5)
                    existing = ans_map.get(qno)
                    if existing and existing != answer:
                        continue
                    ans_map[qno] = answer
                    answers.append(AnswerDraft(qno, answer, page_index))
        # dedupe by qno keeping first
        seen = set()
        deduped = []
        for a in answers:
            if a.question_no in seen:
                continue
            seen.add(a.question_no)
            deduped.append(a)
        answers = deduped

    # Detect conflicting duplicate answers (same qno, different answer/section) -> keep all but mark? We keep all; caller decides.
    return answers

# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _cluster_rects(
    rects: list[pymupdf.Rect], page_rect: pymupdf.Rect
) -> list[pymupdf.Rect]:
    if not rects:
        return []
    expanded = []
    for rect in rects:
        width, height = rect.width, rect.height
        if width < 6 and height < 6:
            continue
        if rect.width * rect.height < 80:
            continue
        # Ignore full-page rules/backgrounds.
        if rect.width > page_rect.width * 0.94 and rect.height > page_rect.height * 0.94:
            continue
        expanded.append(rect)

    changed = True
    while changed:
        changed = False
        merged: list[pymupdf.Rect] = []
        while expanded:
            current = expanded.pop()
            i = 0
            while i < len(expanded):
                other = expanded[i]
                pad = pymupdf.Rect(current.x0 - 14, current.y0 - 14, current.x1 + 14, current.y1 + 14)
                if _overlaps(tuple(current), tuple(other)) or pad.contains(other):
                    current |= other
                    expanded.pop(i)
                    changed = True
                else:
                    i += 1
            merged.append(current)
        expanded = merged
    return expanded


def extract_figures(
    doc: pymupdf.Document,
    drafts: list[QuestionDraft],
    output_dir: Path,
    asset_key: str,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for page_index, page in enumerate(doc):
        page_rect = page.rect
        regions: list[tuple[pymupdf.Rect, str]] = []
        for image in page.get_images(full=True):
            xref = image[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception:  # noqa: BLE001
                continue
            for rect in rects:
                if rect.width * rect.height < 1200:
                    continue
                if rect.width > page_rect.width * 0.9 and rect.height > page_rect.height * 0.9:
                    continue
                regions.append((rect, "image"))
        drawings = []
        for drawing in page.get_drawings():
            rect = drawing.get("rect")
            if rect is not None:
                drawings.append(rect)
        for rect in _cluster_rects(drawings, page_rect):
            if rect.width * rect.height < 1500:
                continue
            if rect.height < 12 or rect.width < 12:
                continue
            regions.append((rect, "vector"))
        # Merge overlapping image/vector regions.
        all_rects = _cluster_rects([rect for rect, _ in regions], page_rect)
        for region in all_rects:
            # Keep regions that are plausibly diagrams, not page furniture.
            if region.height < 18 or region.width < 18:
                continue
            clip = pymupdf.Rect(
                max(page_rect.x0, region.x0 - 6),
                max(page_rect.y0, region.y0 - 6),
                min(page_rect.x1, region.x1 + 6),
                min(page_rect.y1, region.y1 + 6),
            )
            question = _question_for_region(drafts, page_index, clip)
            if question is None:
                continue
            filename = f"q{question.question_no:03d}_p{page_index + 1}_{count}.png"
            path = output_dir / filename
            pix = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(2, 2), alpha=False)
            pix.save(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            question.assets.append(
                {
                    "path": str(path),
                    "kind": "figure",
                    "page": page_index + 1,
                    "bbox": [round(v, 2) for v in clip],
                    "width": pix.width,
                    "height": pix.height,
                    "sha256": digest,
                }
            )
            count += 1
    return count


def _question_for_region(
    drafts: list[QuestionDraft], page_index: int, region: pymupdf.Rect
) -> QuestionDraft | None:
    candidates = [d for d in drafts if d.page_start <= page_index + 1 <= d.page_end]
    if not candidates:
        return None
    center = (region.y0 + region.y1) / 2
    best: tuple[float, QuestionDraft] | None = None
    for draft in candidates:
        if draft.page_start == draft.page_end == page_index + 1:
            low, high = draft.y_start - 8, draft.y_end + 8
        elif draft.page_start == page_index + 1:
            low, high = draft.y_start - 8, 10000
        elif draft.page_end == page_index + 1:
            low, high = 0, draft.y_end + 8
        else:
            low, high = 0, 10000
        if low <= center <= high:
            distance = 0
        else:
            distance = min(abs(center - low), abs(center - high))
        if best is None or distance < best[0]:
            best = (distance, draft)
    if best and best[0] < 140:
        return best[1]
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def inspect_pdf(
    path: Path,
    *,
    output_assets_dir: Path | None = None,
    asset_key: str = "paper",
) -> PdfInfo:
    doc = pymupdf.open(path)
    pages_text = [page.get_text("text") for page in doc]
    full_text = "\n".join(pages_text)
    # An answer key can be short. Only treat the file as a scan when no page
    # contains a meaningful amount of real text (page numbers don't count).
    has_text = any(len(t.strip()) >= 30 for t in pages_text)
    kind, _ = detect_kind(path.name, full_text)
    year, session = detect_year_session(path.name, full_text)
    warnings: list[str] = []
    if not has_text:
        warnings.append(
            "This PDF has no usable text layer. It was flagged for manual review; OCR was not run."
        )
        return PdfInfo(
            kind=kind,
            year=year,
            session=session,
            page_count=len(doc),
            has_text_layer=False,
            text="",
            warnings=warnings,
        )

    lines = _strip_headers(_extract_lines(doc), len(doc))
    info = PdfInfo(
        kind=kind,
        year=year,
        session=session,
        page_count=len(doc),
        has_text_layer=True,
        text=full_text,
        warnings=warnings,
    )
    if kind == "answer_key":
        info.answers = parse_answers(doc, full_text)
        if not info.answers:
            warnings.append("No answer-key entries were parsed; manual review required.")
    elif kind == "question_paper":
        info.questions = parse_questions(
            doc, lines, full_text, year=year, session=session
        )
        if not info.questions:
            warnings.append(
                "No question boundaries were detected. Extraction was not forced; manual review required."
            )
        if output_assets_dir is not None:
            try:
                extract_figures(doc, info.questions, output_assets_dir, asset_key)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Figure extraction failed: {exc}")
        numbers = [q.question_no for q in info.questions]
        if numbers and len(numbers) == len(set(numbers)):
            gaps = sorted(set(range(min(numbers), max(numbers) + 1)) - set(numbers))
            if gaps:
                warnings.append(f"Missing question numbers in extracted sequence: {gaps[:12]}")
    else:
        warnings.append("File type could not be determined; it was not imported automatically.")
    return info
