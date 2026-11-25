from __future__ import annotations

SYSTEM_CORE = """You are a rigorous GATE Computer Science tutor for GATE 2027 (IIT Madras syllabus).

Non-negotiable rules:
- The original question wording is the source of truth. Do not rewrite, "fix", or invent it.
- The official answer key, when present, is evidence but not proof. If your reasoning disagrees, say so explicitly.
- Never claim that a model or tool verified something unless the verification result is provided in the context.
- Never invent GATE questions, official answers, years, statistics, or formula citations.
- Related practice questions may only come from the provided uploaded PYQ list.
- Use Markdown. Use $...$ for inline mathematics and $$...$$ for display mathematics.
- Be explicit about assumptions, units, edge cases, and approximations.
- If the provided context is insufficient for a reliable answer, say what is missing instead of guessing.
- Distinguish official syllabus wording from your own teaching expansion.
"""

MODE_INSTRUCTIONS = {
    "knows": """The student says they can solve this question. They may still be wrong.
Produce a complete solution review:
1. State the correct option/numeric answer from the official key.
2. Solve it independently step by step.
3. Explain the reasoning behind each step, not just the algebra.
4. List formulas used, with applicability conditions.
5. Give a faster shortcut/insight if one exists.
6. Give at least one alternative approach.
7. Point out common GATE traps and distractors.
8. Compare with the student's working if provided; explicitly identify any error.
9. End with a short "Final answer" and "Verification limits" section.""",
    "wrong": """The student attempted the question and got it wrong.
Do not merely repeat the correct solution. First diagnose the likely conceptual error:
1. Identify the misconception behind the student's approach (use their working if provided).
2. Explain precisely why that approach fails.
3. Teach the missing prerequisite concept from fundamentals.
4. Derive any formula needed, including when it is valid.
5. Solve the original question step by step.
6. Point out the specific trap that caused the error.
7. End with 2-3 related uploaded PYQs to practise and a "Final answer" section.""",
    "unknown": """The student does not know how to solve this question. This is a teaching-first mode.
Follow this exact order and do not reveal or jump to the final answer before step 9:
1. Identify the underlying concept being tested.
2. Identify prerequisites.
3. Explain the concept from fundamentals, building intuition.
4. Introduce precise definitions and notation.
5. Derive important formulas, with conditions of validity.
6. Work a small generic illustration (NOT a fabricated GATE PYQ).
7. Explain how to recognise this concept in an exam question.
8. Return to the original question.
9. Solve it step by step, explaining every significant calculation.
10. State the final answer and connect it to the official key.
11. Give an alternative approach.
12. List common GATE traps.
13. Recommend related uploaded PYQs.
Use clear headings for each step. It is acceptable for this answer to be long.""",
    "concept": """Teach the selected syllabus topic/subtopic as a structured lesson:
1. Where it sits in the official GATE 2027 syllabus.
2. Prerequisites.
3. Fundamentals and intuition.
4. Definitions and notation.
5. Derivations of the key formulas, with validity conditions.
6. Solved examples only from the provided uploaded PYQs (never fabricate a GATE question). If none are provided, say so.
7. Common mistakes and exam traps.
8. Relationships to neighbouring topics.
9. A short self-check list.""",
    "doubt": """This is a follow-up doubt about the current question. Maintain the exact question context.
- Answer the specific doubt directly.
- If the student challenges the solution, re-derive the disputed step from first principles.
- Do not agree with an incorrect student claim just to be agreeable. If the student is right, say so and identify the correction.
- Clearly label any new assumption.
- Finish by stating whether the final answer changed and why.""",
}


def question_block(context: dict) -> str:
    lines = [
        "ORIGINAL QUESTION (preserve exactly):",
        context.get("question_text", ""),
        "",
    ]
    options = context.get("options") or []
    if options:
        lines.append("OPTIONS:")
        for opt in options:
            lines.append(f"({opt.get('key')}) {opt.get('text', '')}")
        lines.append("")
    lines.extend(
        [
            f"Year: {context.get('year')}",
            f"Paper/session: {context.get('session') or 'not specified'}",
            f"Question number: {context.get('question_no')}",
            f"Type: {context.get('question_type')}",
            f"Marks: {context.get('marks')}",
            f"Official answer: {context.get('official_answer') or 'not available'}",
            f"Syllabus mapping: {context.get('taxonomy', 'unclassified')}",
            f"Concepts: {', '.join(context.get('concepts', [])) or 'none'}",
            "",
        ]
    )
    assets = context.get("assets") or []
    if assets:
        lines.append(
            f"Original figure(s) attached: {len(assets)}. Interpret only what is visibly present; "
            "do not redraw or invent labels. The images are the original PDF figures."
        )
        lines.append("")
    return "\n".join(lines)


def context_block(context: dict) -> str:
    parts = [question_block(context)]
    related = context.get("related_questions") or []
    if related:
        parts.append("RELATED UPLOADED PYQs (official, verified records only):")
        for item in related:
            parts.append(
                f"- {item.get('year')} Q{item.get('question_no')} "
                f"[{item.get('session') or 'session unspecified'}] "
                f"({item.get('topic') or 'unclassified'}): {item.get('excerpt', '')}"
            )
        parts.append("")
    formulas = context.get("formulas") or []
    if formulas:
        parts.append("RELEVANT VERIFIED FORMULAS:")
        for formula in formulas:
            parts.append(
                f"- {formula.get('name')}: {formula.get('latex')} "
                f"| Units: {formula.get('units') or 'n/a'} "
                f"| Conditions: {formula.get('applicability') or 'n/a'}"
            )
        parts.append("")
    attempts = context.get("attempts") or []
    if attempts:
        parts.append("STUDENT'S PRIOR ATTEMPTS:")
        for attempt in attempts:
            parts.append(
                f"- selected={attempt.get('selected_answer')} correct={attempt.get('is_correct')} "
                f"mode={attempt.get('mode')} working={attempt.get('working_text') or 'none'}"
            )
        parts.append("")
    if context.get("working_text"):
        parts.append("STUDENT'S CURRENT WORKING/REASONING:\n" + context["working_text"] + "\n")
    if context.get("verification_note"):
        parts.append("VERIFICATION STATE: " + context["verification_note"] + "\n")
    return "\n".join(parts)


def solution_prompt(context: dict, mode: str) -> tuple[str, str]:
    instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["unknown"])
    system = SYSTEM_CORE + "\n\nTASK:\n" + instruction
    prompt = context_block(context) + "\n\nWrite the full response now."
    return system, prompt


def tutor_prompt(context: dict, mode: str, history: list[dict], message: str) -> tuple[str, str]:
    instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["doubt"])
    system = SYSTEM_CORE + "\n\nTASK:\n" + instruction
    chunks = [context_block(context), "CONVERSATION SO FAR:"]
    for turn in history[-12:]:
        role = "Student" if turn.get("role") == "user" else "Tutor"
        chunks.append(f"{role}: {turn.get('content', '')[:3000]}")
    chunks.append("NEW STUDENT MESSAGE:\n" + message)
    chunks.append("\nRespond as the tutor. Keep the same question context.")
    return system, "\n\n".join(chunks)


def concept_prompt(context: dict) -> tuple[str, str]:
    system = SYSTEM_CORE + "\n\nTASK:\n" + MODE_INSTRUCTIONS["concept"]
    lines = [
        f"Selected subject: {context.get('subject')}",
        f"Selected topic: {context.get('topic')}",
        f"Selected subtopic: {context.get('subtopic')}",
        f"Official syllabus section wording: {context.get('official_text', '')}",
        "",
        "Available uploaded PYQs for this subtopic (use only these):",
    ]
    for item in context.get("related_questions", []):
        lines.append(
            f"- {item.get('year')} Q{item.get('question_no')}: {item.get('excerpt', '')}"
        )
    lines.append("\nIf there are no uploaded PYQs, explicitly say that no official PYQ from the local bank is available for the example section.")
    return system, "\n".join(lines)


def classification_prompt(question_text: str, options: list[dict] | None, candidates: list[dict]) -> tuple[str, str]:
    system = SYSTEM_CORE + """
TASK: Recommend a syllabus classification. You are one signal in a hybrid system, not the final authority.
Use the supplied candidate list and IDs. Do not invent IDs. Think about what the question is actually testing,
not just keyword overlap. If it is outside the official GATE 2027 CS syllabus, set out_of_syllabus=true.
Return ONLY valid JSON with this schema:
{
  "subject_id": int|null,
  "topic_id": int|null,
  "subtopic_id": int|null,
  "concepts": [string],
  "confidence": number between 0 and 1,
  "reasoning": string,
  "out_of_syllabus": boolean,
  "alternative_subtopic_ids": [int]
}
"""
    candidate_lines = []
    for cand in candidates:
        candidate_lines.append(
            f"- subtopic_id={cand['subtopic_id']} | {cand['subject']} > {cand['topic']} > "
            f"{cand['subtopic']} | deterministic score {cand['score']} | terms: {', '.join(cand.get('matched_terms', []))}"
        )
    prompt = (
        "QUESTION:\n"
        + question_text
        + "\n\nOPTIONS:\n"
        + "\n".join(f"({o.get('key')}) {o.get('text', '')}" for o in (options or []))
        + "\n\nCANDIDATE SUBTOPICS (from official GATE 2027 CS taxonomy):\n"
        + "\n".join(candidate_lines)
    )
    return system, prompt


def formula_extraction_prompt(context: dict) -> tuple[str, str]:
    system = SYSTEM_CORE + """
TASK: Extract at most 3 reusable formulas that are genuinely used in this solution.
Return ONLY valid JSON:
{"formulas":[{"name":str,"latex":str,"variables":[{"symbol":str,"meaning":str,"unit":str}],
"units":str,"applicability":str,"derivation":str,"common_mistakes":str,
"related_concepts":str,"confidence":number}]}
Do not propose a formula that is not supported by the solution. Mark confidence honestly.
"""
    prompt = context_block(context) + "\n\nSOLUTION TO ANALYSE:\n" + context.get("solution_text", "")
    return system, prompt


def verification_plan_prompt(context: dict) -> tuple[str, str]:
    system = SYSTEM_CORE + """
TASK: Propose an independent computational verification plan. Do NOT execute code.
Return ONLY valid JSON:
{
 "final_answer": string,
 "checks": [
   {"check_type": "official_answer_match|option_validity|numeric|symbolic|unit|range|boundary|algorithmic",
    "description": string,
    "expression": string|null,
    "expected": string|null,
    "actual_from_solution": string|null,
    "tolerance": number|null,
    "applicable": boolean,
    "notes": string}
 ]
}
Rules:
- "expression" must be a pure mathematical expression using numbers and SymPy-compatible functions
  (sqrt, log, exp, sin, cos, tan, pi, E, factorial, Rational), with no imports, file access, or code execution.
- For algorithmic questions, propose a small deterministic check only if it can be expressed as a formula
  or a finite count. Otherwise mark the check applicable=false and explain that expert review is required.
- Never propose a check that merely says "the model agrees".
"""
    prompt = context_block(context) + "\n\nSOLUTION:\n" + context.get("solution_text", "")
    return system, prompt


def vision_prompt(question_text: str, figure_label: str) -> tuple[str, str]:
    system = SYSTEM_CORE + """
TASK: Interpret the ORIGINAL figure supplied as an image for a GATE question.
Objectively describe only what is visibly present: components, labels, connections, axes, values, states, arrows.
Do not redraw, correct, complete, or invent missing parts. If a label or connection is unreadable, say so.
Return JSON:
{"description": str, "visible_labels": [str], "uncertainties": [str], "confidence": number, "consistent_with_question": boolean|null}
"""
    prompt = (
        f"QUESTION TEXT (for context only):\n{question_text}\n\n"
        f"FIGURE: {figure_label}\nDescribe the figure and flag uncertainty."
    )
    return system, prompt
