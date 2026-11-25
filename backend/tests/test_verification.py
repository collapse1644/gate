"""Verification policy and sandbox tests."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.verification import CheckOutcome, decide_status, safe_compare


def test_sandbox_computes_symbolic_and_numeric_results():
    exact = safe_compare("Rational(1, 3) + Rational(2, 3)", "1")
    assert exact["passed"] is True
    numeric = safe_compare("sqrt(2)**2", "2")
    assert numeric["passed"] is True
    assert safe_compare("2**10", "1024")["passed"] is True


def test_sandbox_blocks_imports_and_attribute_access():
    imported = safe_compare("__import__('os').system('echo pwned')", "0")
    assert imported["passed"] is False
    assert "whitelisted" in imported["error"] or "Disallowed" in imported["error"]

    attribute = safe_compare("(1).__class__", "1")
    assert attribute["passed"] is False
    assert "Disallowed" in attribute["error"]


def test_sandbox_rejects_unknown_names():
    result = safe_compare("open('/etc/passwd').read()", "''")
    assert result["passed"] is False
    assert "whitelisted" in result["error"] or "Disallowed" in result["error"]


def independent_numeric():
    return CheckOutcome(
        check_type="numeric",
        tool="sympy-sandbox",
        description="computed independently",
        passed=True,
        independent=True,
    )


def test_status_requires_independent_checks_for_verified():
    question = SimpleNamespace(official_answer=None)
    status, reason = decide_status(question, [independent_numeric()], has_plan=True)
    assert status == "VERIFIED"
    assert "independent" in reason.lower()

    non_independent = CheckOutcome(
        check_type="numeric",
        tool="llm-plan",
        description="LLM proposed check",
        passed=True,
        independent=False,
    )
    status, _ = decide_status(question, [non_independent], has_plan=True)
    assert status == "PARTIALLY VERIFIED"


def test_disagreement_is_disputed_and_preserved():
    question = SimpleNamespace(official_answer=None)
    failed = CheckOutcome(
        check_type="numeric",
        tool="sympy-sandbox",
        description="independent computation",
        passed=False,
        independent=True,
    )
    status, reason = decide_status(question, [failed], has_plan=True)
    assert status == "DISPUTED"
    assert "preserved" in reason.lower()


def test_no_executed_checks_is_unverified():
    question = SimpleNamespace(official_answer="B")
    status, _ = decide_status(question, [], has_plan=False)
    assert status == "UNVERIFIED"


def test_official_answer_mismatch_is_disputed():
    question = SimpleNamespace(official_answer="B")
    official = CheckOutcome(
        check_type="official_answer_match",
        tool="internal",
        description="compare official key",
        passed=False,
        independent=True,
    )
    status, _ = decide_status(question, [official, independent_numeric()], has_plan=True)
    assert status == "DISPUTED"
