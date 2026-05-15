"""Unit tests for the grammar checker service.

All LLM calls go through FakeLLMClient — no network traffic.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.grammar import GrammarIssue, GrammarRequest, IssueCategory
from app.services.grammar_service import (
    _compute_scores,
    _derive_issues,
    _LLMGrammarPayload,
    _LLMIssueItem,
    check_grammar,
)
from app.services.llm.fakes import FakeLLMClient


def _make_validation_error() -> ValidationError:
    try:
        _LLMGrammarPayload.model_validate({"issues": [{"bad": "field"}]})
    except ValidationError as exc:
        return exc
    # fallback: force via required missing
    try:
        _LLMGrammarPayload.model_validate(None)
    except ValidationError as exc:
        return exc
    raise AssertionError("should have raised")  # pragma: no cover


def _simple_payload(original: str = "walked", replacement: str = "walk") -> _LLMGrammarPayload:
    return _LLMGrammarPayload(
        issues=[
            _LLMIssueItem(
                category="grammar",
                original=original,
                replacement=replacement,
                short_label="Change verb tense",
                explanation="Present-tense narration needs present-tense verb.",
            )
        ]
    )


# ---------------------------------------------------------------------------
# _derive_issues
# ---------------------------------------------------------------------------


def test_derive_issues_happy_path() -> None:
    text = "Yesterday I walked to school."
    payload = _LLMGrammarPayload(
        issues=[
            _LLMIssueItem(
                category="grammar",
                original="walked",
                replacement="walk",
                short_label="Fix verb tense",
                explanation="Use present tense.",
            )
        ]
    )
    issues = _derive_issues(text, payload.issues)
    assert len(issues) == 1
    assert issues[0].start == text.index("walked")
    assert issues[0].end == issues[0].start + len("walked")
    assert text[issues[0].start : issues[0].end] == "walked"
    assert issues[0].category.value == "grammar"


def test_derive_issues_drops_missing_original() -> None:
    text = "The cat sat on the mat."
    payload = _LLMGrammarPayload(
        issues=[
            _LLMIssueItem(
                category="spelling",
                original="NONEXISTENT",
                replacement="fix",
                short_label="Fix spelling",
                explanation="Not in text.",
            )
        ]
    )
    issues = _derive_issues(text, payload.issues)
    assert issues == []


def test_derive_issues_deduplicates_same_span() -> None:
    text = "The cat sat."
    item = _LLMIssueItem(
        category="grammar",
        original="cat",
        replacement="cats",
        short_label="Fix noun",
        explanation="Should be plural.",
    )
    payload = _LLMGrammarPayload(issues=[item, item])
    issues = _derive_issues(text, payload.issues)
    assert len(issues) == 1


# ---------------------------------------------------------------------------
# _compute_scores
# ---------------------------------------------------------------------------


def test_compute_scores_perfect_no_issues() -> None:
    scores = _compute_scores([], word_count=100)
    assert scores.grammar == 100
    assert scores.spelling == 100
    assert scores.punctuation == 100
    assert scores.style == 100
    assert scores.overall == 100
    assert scores.overall_label == "Great"


def test_compute_scores_empty_text_no_issues() -> None:
    scores = _compute_scores([], word_count=0)
    assert scores.overall == 100
    assert scores.overall_label == "Great"


def test_compute_scores_low_score_needs_work() -> None:
    # 7 grammar issues in 10 words: 7 * 3 * 100 // 10 = 210, capped at 0
    issues = [
        GrammarIssue(
            id=str(i),
            category=IssueCategory.grammar,
            start=i * 5,
            end=i * 5 + 4,
            original="word",
            replacement="words",
            short_label="Fix it",
            explanation="Because.",
        )
        for i in range(7)
    ]
    scores = _compute_scores(issues, word_count=10)
    assert scores.grammar == 0
    assert scores.overall == 0
    assert scores.overall_label == "Needs work"


def test_compute_scores_overall_is_min_of_categories() -> None:
    # 1 spelling issue in 200 words: 1 * 4 * 100 // 200 = 2, score 98
    issues = [
        GrammarIssue(
            id="0",
            category=IssueCategory.spelling,
            start=0,
            end=4,
            original="word",
            replacement="words",
            short_label="Fix",
            explanation=".",
        )
    ]
    scores = _compute_scores(issues, word_count=200)
    assert scores.spelling == 98
    assert scores.grammar == 100
    assert scores.overall == 98  # limited by spelling
    assert scores.overall_label == "Great"


def _make_grammar_issues(n: int) -> list[GrammarIssue]:
    return [
        GrammarIssue(
            id=str(i),
            category=IssueCategory.grammar,
            start=i * 5,
            end=i * 5 + 4,
            original="word",
            replacement="fix",
            short_label="Fix",
            explanation=".",
        )
        for i in range(n)
    ]


def test_compute_scores_label_great() -> None:
    # 5 grammar issues in 100 words: 5 * 3 * 100 // 100 = 15, score 85 → Great
    scores = _compute_scores(_make_grammar_issues(5), word_count=100)
    assert scores.grammar == 85
    assert scores.overall_label == "Great"


def test_compute_scores_label_good() -> None:
    # 10 grammar issues in 100 words: 10 * 3 * 100 // 100 = 30, score 70 → Good
    scores = _compute_scores(_make_grammar_issues(10), word_count=100)
    assert scores.grammar == 70
    assert scores.overall_label == "Good"


def test_compute_scores_label_fair() -> None:
    # 15 grammar issues in 100 words: 15 * 3 * 100 // 100 = 45, score 55 → Fair
    scores = _compute_scores(_make_grammar_issues(15), word_count=100)
    assert scores.grammar == 55
    assert scores.overall_label == "Fair"


def test_compute_scores_label_needs_work() -> None:
    # 20 grammar issues in 100 words: 20 * 3 * 100 // 100 = 60, score 40 → Needs work
    scores = _compute_scores(_make_grammar_issues(20), word_count=100)
    assert scores.grammar == 40
    assert scores.overall_label == "Needs work"


def test_compute_scores_realistic_paragraph_grammar() -> None:
    # 11 grammar issues in 145 words: 11 * 3 * 100 // 145 = 22, score 78
    scores = _compute_scores(_make_grammar_issues(11), word_count=145)
    assert scores.grammar == 78
    assert scores.grammar >= 60


def test_compute_scores_zero_issues_all_100() -> None:
    scores = _compute_scores([], word_count=145)
    assert scores.grammar == 100
    assert scores.overall == 100


def test_compute_scores_saturated_collapses_to_zero() -> None:
    # 50 grammar issues in 100 words: 50 * 3 = 150 > 100, clamped to 0
    scores = _compute_scores(_make_grammar_issues(50), word_count=100)
    assert scores.grammar == 0
    assert scores.overall == 0


# ---------------------------------------------------------------------------
# check_grammar (service integration)
# ---------------------------------------------------------------------------


async def test_check_grammar_happy_path() -> None:
    text = "Yesterday I walked to school and I seen my friend."
    payload = _simple_payload("walked", "walk")
    fake = FakeLLMClient(structured_responses=[payload])

    req = GrammarRequest(text=text)
    response = await check_grammar(req, fake)

    assert response.document_id is None
    assert len(response.issues) == 1
    assert response.issues[0].original == "walked"
    assert response.issues[0].replacement == "walk"
    assert response.word_count == len(text.split())
    assert 0 <= response.scores.overall <= 100


async def test_check_grammar_retries_on_validation_error() -> None:
    error = _make_validation_error()
    payload = _simple_payload()
    fake = FakeLLMClient(structured_responses=[error, payload])

    req = GrammarRequest(text="I walked to school.")
    response = await check_grammar(req, fake)

    assert len(response.issues) == 1
    assert fake._structured_cursor == 2


async def test_check_grammar_raises_after_two_validation_failures() -> None:
    error = _make_validation_error()
    fake = FakeLLMClient(structured_responses=[error, error])

    req = GrammarRequest(text="I walked to school.")
    with pytest.raises(ValidationError):
        await check_grammar(req, fake)


async def test_check_grammar_drops_bad_offsets() -> None:
    """Issue whose original isn't in the text is silently dropped."""
    payload = _LLMGrammarPayload(
        issues=[
            _LLMIssueItem(
                category="spelling",
                original="GHOST_WORD",
                replacement="fix",
                short_label="Fix",
                explanation="Not real.",
            )
        ]
    )
    fake = FakeLLMClient(structured_responses=[payload])
    req = GrammarRequest(text="The quick brown fox.")
    response = await check_grammar(req, fake)
    assert response.issues == []
    assert response.scores.overall == 100


async def test_check_grammar_empty_issues() -> None:
    """No issues → all scores 100, label Great."""
    payload = _LLMGrammarPayload(issues=[])
    fake = FakeLLMClient(structured_responses=[payload])
    req = GrammarRequest(text="A well written sentence.")
    response = await check_grammar(req, fake)
    assert response.issues == []
    assert response.scores.overall == 100
    assert response.scores.overall_label == "Great"
