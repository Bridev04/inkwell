"""Business logic for the grammar checker endpoint.

Builds LLM prompts, calls generate_structured with a retry on validation
failure, derives character offsets from the returned originals, and
computes deterministic category scores before returning GrammarResponse.
"""

from __future__ import annotations

import logging
import time
from typing import Literal, cast
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from app.schemas.grammar import (
    GrammarIssue,
    GrammarRequest,
    GrammarResponse,
    GrammarScores,
    IssueCategory,
)
from app.services.llm.base import LLMClient
from app.services.llm.schemas import TokenUsage

logger = logging.getLogger(__name__)

# Points deducted per issue per 100 words (scaled to actual word count).
_PENALTY: dict[str, int] = {
    "grammar": 15,
    "spelling": 18,
    "punctuation": 12,
    "style": 8,
}

_SYSTEM_PROMPT = """\
You are a meticulous copy-editor. Identify every grammar, spelling, punctuation, \
and style issue in the submitted text.

For each issue provide:
  - category: exactly one of "grammar", "spelling", "punctuation", "style"
  - original: the exact verbatim substring that is wrong (a word or short phrase)
  - replacement: the corrected text that should replace it
  - short_label: a 3-7 word imperative label (e.g. "Change the verb tense")
  - explanation: one concise sentence explaining why it is wrong

Rules:
- "original" must be copied exactly from the text, including surrounding spaces only \
if they are part of the error.
- Do not report the same span twice.
- If the text has no issues, return an empty list.
"""


class _LLMIssueItem(BaseModel):
    category: Literal["grammar", "spelling", "punctuation", "style"]
    original: str
    replacement: str
    short_label: str
    explanation: str


class _LLMGrammarPayload(BaseModel):
    issues: list[_LLMIssueItem] = Field(default_factory=list)


def _word_count(text: str) -> int:
    return len(text.split()) if text.strip() else 0


def _compute_scores(issues: list[GrammarIssue], word_count: int) -> GrammarScores:
    """Derive per-category scores and an overall label from issue counts.

    Formula: score = max(0, 100 - count * penalty * 100 // word_count).
    A penalty of 15 for grammar means one grammar error in a 100-word document
    costs 15 points; the same error in a 500-word document costs only 3 points.
    overall = min of the four category scores.
    """
    wc = max(word_count, 1)
    counts: dict[str, int] = {k: 0 for k in _PENALTY}
    for issue in issues:
        counts[issue.category.value] += 1

    def _score(kind: str) -> int:
        return max(0, 100 - counts[kind] * _PENALTY[kind] * 100 // wc)

    g = _score("grammar")
    s = _score("spelling")
    p = _score("punctuation")
    st = _score("style")
    overall = min(g, s, p, st)

    label: Literal["Needs work", "Fair", "Good", "Great"]
    if overall >= 85:
        label = "Great"
    elif overall >= 70:
        label = "Good"
    elif overall >= 50:
        label = "Fair"
    else:
        label = "Needs work"

    return GrammarScores(
        grammar=g,
        spelling=s,
        punctuation=p,
        style=st,
        overall=overall,
        overall_label=label,
    )


def _derive_issues(text: str, llm_issues: list[_LLMIssueItem]) -> list[GrammarIssue]:
    """Locate each LLM-reported original in text and build GrammarIssue objects.

    Issues whose original string cannot be found in text, or whose
    text[start:end] != original, are silently dropped — the LLM sometimes
    hallucinates spans that don't exist verbatim.
    """
    result: list[GrammarIssue] = []
    seen_spans: set[tuple[int, int]] = set()

    for item in llm_issues:
        if not item.original:
            continue
        pos = text.find(item.original)
        if pos < 0:
            continue
        end = pos + len(item.original)
        # Validate the slice (guards against multi-byte edge cases).
        if text[pos:end] != item.original:
            continue
        span = (pos, end)
        if span in seen_spans:
            continue
        seen_spans.add(span)
        result.append(
            GrammarIssue(
                id=str(len(result)),
                category=IssueCategory(item.category),
                start=pos,
                end=end,
                original=item.original,
                replacement=item.replacement,
                short_label=item.short_label,
                explanation=item.explanation,
            )
        )

    return result


def _build_prompt(req: GrammarRequest) -> str:
    return "\n".join(
        [
            "Please check the following text and return a list of issues.",
            "",
            "--- TEXT START ---",
            req.text,
            "--- TEXT END ---",
        ]
    )


async def check_grammar(req: GrammarRequest, llm: LLMClient) -> GrammarResponse:
    """Run a grammar check on the submitted text.

    Retries once on ValidationError before propagating. All other exceptions
    (provider timeouts, rate limits) propagate immediately to the route handler.
    """
    request_id = uuid4()
    start_ts = time.monotonic()
    prompt = _build_prompt(req)

    result: tuple[BaseModel, TokenUsage, str] | None = None
    last_error: ValidationError | None = None

    for _ in range(2):
        try:
            result = await llm.generate_structured(
                prompt=prompt,
                response_schema=_LLMGrammarPayload,
                system=_SYSTEM_PROMPT,
            )
            break
        except ValidationError as exc:
            logger.warning(
                "event=grammar_check_retry reason=validation_error request_id=%s",
                request_id,
            )
            last_error = exc

    if result is None:
        if last_error is not None:
            raise last_error
        raise RuntimeError("generate_structured returned no result")  # unreachable

    raw, _token_usage, _model_name = result
    payload = cast(_LLMGrammarPayload, raw)

    wc = _word_count(req.text)
    issues = _derive_issues(req.text, payload.issues)
    scores = _compute_scores(issues, wc)

    latency_ms = int((time.monotonic() - start_ts) * 1000)
    logger.info(
        "event=grammar_check text_len=%d issues=%d overall=%d overall_label=%s latency_ms=%d",
        len(req.text),
        len(issues),
        scores.overall,
        scores.overall_label,
        latency_ms,
    )

    return GrammarResponse(
        issues=issues,
        scores=scores,
        word_count=wc,
        document_id=None,
    )
