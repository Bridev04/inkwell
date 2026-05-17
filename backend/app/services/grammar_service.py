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
# Calibrated so that ~10 errors in a 100-word document scores in the 60s-70s
# and a single error never drops a category below ~95.
_PENALTY: dict[str, int] = {
    "grammar": 3,
    "spelling": 4,
    "punctuation": 2,
    "style": 1,
}

_SYSTEM_PROMPT = """\
You are a meticulous copy-editor. Identify every grammar, spelling, punctuation, \
and style issue in the submitted text, and return a fully corrected version.

For each issue provide:
  - category: exactly one of "grammar", "spelling", "punctuation", "style"
  - original: the EXACT verbatim substring copied character-for-character from the text
  - replacement: the corrected text that should replace it
  - short_label: a 3-7 word imperative label (e.g. "Change the verb tense")
  - explanation: one concise sentence explaining why it is wrong

Also return:
  - corrected_text: the complete input text with every single issue corrected

Rules:
- "original" must be copied verbatim — do not paraphrase, add quotes, or change case.
- "corrected_text" must be the FULL input text with all corrections applied.
- Do not report the same span twice.
- If the text has no issues, return an empty list and set corrected_text equal to the input.
"""


class _LLMIssueItem(BaseModel):
    category: Literal["grammar", "spelling", "punctuation", "style"]
    original: str
    replacement: str
    short_label: str
    explanation: str


class _LLMGrammarPayload(BaseModel):
    corrected_text: str = ""
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

    Issues whose original string cannot be found in text are dropped, but a
    .strip() fallback is attempted first to tolerate LLM-added whitespace.
    The search cursor advances past each matched span so repeated words map
    to distinct positions rather than all collapsing to the first occurrence.
    """
    result: list[GrammarIssue] = []
    seen_spans: set[tuple[int, int]] = set()
    search_from = 0

    for item in llm_issues:
        if not item.original:
            continue

        # Try exact match from current cursor; fall back to stripped version.
        canonical = item.original
        pos = text.find(canonical, search_from)
        if pos < 0:
            stripped = canonical.strip()
            if stripped and stripped != canonical:
                pos = text.find(stripped, search_from)
                if pos >= 0:
                    canonical = stripped
            # If still not found, try from the beginning of the text (the
            # LLM may return issues out of order).
            if pos < 0:
                pos = text.find(canonical)
            if pos < 0 and canonical != item.original.strip():
                pos = text.find(item.original.strip())
                if pos >= 0:
                    canonical = item.original.strip()

        if pos < 0:
            logger.warning(
                "event=grammar_issue_dropped reason=not_found original=%r",
                item.original,
            )
            continue

        end = pos + len(canonical)
        if text[pos:end] != canonical:
            logger.warning(
                "event=grammar_issue_dropped reason=slice_mismatch original=%r",
                item.original,
            )
            continue

        span = (pos, end)
        if span in seen_spans:
            # Advance one character and retry so repeated-word issues get
            # distinct positions rather than being silently discarded.
            retry_pos = text.find(canonical, pos + 1)
            if retry_pos >= 0:
                retry_span = (retry_pos, retry_pos + len(canonical))
                if retry_span not in seen_spans:
                    pos, end, span = retry_pos, retry_pos + len(canonical), retry_span
                else:
                    continue
            else:
                continue

        seen_spans.add(span)
        search_from = pos + 1
        result.append(
            GrammarIssue(
                id=str(len(result)),
                category=IssueCategory(item.category),
                start=pos,
                end=end,
                original=canonical,
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
                max_tokens=8192,
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
    dropped = len(payload.issues) - len(issues)
    logger.info(
        "event=grammar_check text_len=%d llm_issues=%d derived=%d dropped=%d "
        "overall=%d overall_label=%s latency_ms=%d",
        len(req.text),
        len(payload.issues),
        len(issues),
        dropped,
        scores.overall,
        scores.overall_label,
        latency_ms,
    )

    return GrammarResponse(
        corrected_text=payload.corrected_text,
        issues=issues,
        scores=scores,
        word_count=wc,
        document_id=None,
    )
