"""Deterministic normalization helpers for entity resolution. No AI here —
this is exactly the kind of string/attribute comparison CLAUDE.md and
docs/AI_POLICY.md §3 require to stay code, not a model call.
"""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")
_LATIN_PAREN = re.compile(r"\(([A-Za-z0-9\-\s]+)\)")
_NON_ALNUM = re.compile(r"[^0-9a-zA-Z]+")


def normalize_token(value: str) -> str:
    """Lowercase, strip non-alphanumerics. Used for model numbers/identifiers
    that are written identically regardless of surrounding-text language."""
    return _NON_ALNUM.sub("", value).lower()


def normalize_brand(value: str | None) -> str | None:
    """Best-effort brand normalization across mixed-language labels like
    "써모스(THERMOS)" or "올파(OLFA)". Prefers a parenthetical Latin token
    (common when a KR/JP listing glosses a foreign brand name), else
    normalizes the raw string as-is. This is a heuristic, not a translation —
    it will not equate two brand strings with no shared Latin token (e.g.
    "써모스" alone vs "オルファ"); that case is exactly why deterministic
    Stage 2 falls back to model_number/dimensions rather than requiring a
    brand-string match (see packages/entities/stages/attributes.py).
    """
    if not value:
        return None
    m = _LATIN_PAREN.search(value)
    if m:
        return normalize_token(m.group(1))
    if re.fullmatch(r"[A-Za-z0-9\-\s]+", value):
        return normalize_token(value)
    return normalize_token(value)  # non-Latin, no parenthetical gloss — normalized as-is


def tokenize_title(title: str) -> set[str]:
    """Extract alphanumeric tokens (>=2 chars) for overlap comparison.
    Deliberately language-agnostic: it captures Latin/numeric tokens (model
    codes, brand codes) shared across a ja/ko pair, and CJK runs get split
    into individual multi-character sequences by whitespace only — this is
    weak for CJK title similarity by design (see Stage 3 docstring); cross-
    lingual semantic similarity is Stage 5/7's job, not Stage 3's.
    """
    normalized = _WHITESPACE.sub(" ", title.strip())
    tokens = set()
    for raw_tok in normalized.split(" "):
        cleaned = _NON_ALNUM.sub("", raw_tok).lower()
        if len(cleaned) >= 2:
            tokens.add(cleaned)
    return tokens
