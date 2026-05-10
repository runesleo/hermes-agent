"""Natural-language rewrites for explicit model-switch requests.

The goal is deliberately narrow: recognize short imperative phrases like
"换成 opus" or "switch to gpt 5.4" and rewrite them into the existing
``/model ...`` slash command pipeline. Ambiguous discussion about models
should remain ordinary conversation.
"""

from __future__ import annotations

import re
from typing import Optional

_GLOBAL_PATTERNS = (
    re.compile(
        r"^\s*(?:默认|以后(?:都)?|全局|永久|一直)\s*(?:用|切(?:到|换到)?|换成|改成|设为|设置为)\s*(?P<target>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:set|make)\s+(?:the\s+)?default(?:\s+model)?\s+(?:to|as)\s+(?P<target>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*default(?:\s+model)?\s+(?:to|as)\s+(?P<target>.+?)\s*$",
        re.IGNORECASE,
    ),
)

_SESSION_PATTERNS = (
    re.compile(
        r"^\s*(?:请|麻烦|帮我|直接|给我|现在|先)?\s*(?:切(?:换)?(?:回|到)?|换(?:回|到|成)?|改(?:回|到|成)?|调(?:回|到)?|设(?:为|成)?|设置为|用|改用|换用|回到)\s*(?:模型)?\s*(?:到|成|为)?\s*(?P<target>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:please\s+)?(?:(?:switch|change|move|go)\s+(?:the\s+)?model\s+(?:to|back\s+to)|(?:set|use|try|run)\s+(?:the\s+model\s+)?(?:to\s+)?)\s*(?P<target>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:please\s+)?(?:switch|change|move|go)\s+(?:to|back\s+to)\s*(?P<target>.+?)\s*$",
        re.IGNORECASE,
    ),
)

_AMBIGUOUS_TARGET_RE = re.compile(r"\b(?:or|and)\b|或者|还是|以及", re.IGNORECASE)
_TRAILING_NOISE_RE = re.compile(
    r"(?:[。！!,.?？]+|(?:一下|吧|谢谢|thanks|thank you|pls|please))+$",
    re.IGNORECASE,
)


def _clean_target(target: str) -> str:
    text = (target or "").strip()
    text = text.strip("`\"'“”‘’")
    text = _TRAILING_NOISE_RE.sub("", text).strip()
    return text


def _normalize_target(target: str) -> Optional[str]:
    cleaned = _clean_target(target)
    if not cleaned:
        return None
    if _AMBIGUOUS_TARGET_RE.search(cleaned):
        return None

    lowered = re.sub(r"\s+", " ", cleaned.lower()).strip()

    exact_mappings = (
        (r"^(?:openai\s*)?gpt[- ]?5(?:[. ]?4)?$", "gpt-5.4"),
        (r"^5[. ]?4$", "gpt-5.4"),
        (r"^(?:openai\s*)?gpt[- ]?4(?:[. ]?1)?$", "gpt-4.1"),
        (r"^4[. ]?1$", "gpt-4.1"),
        (r"^(?:openai\s*)?gpt[- ]?5$", "gpt5"),
        (r"^(?:claude\s*)?opus(?:\s*4(?:[. ]?6)?)?$", "opus"),
        (r"^(?:claude\s*)?sonnet(?:\s*4(?:[. ]?6)?)?$", "sonnet"),
        (r"^(?:claude\s*)?haiku$", "haiku"),
        (r"^grok(?:[- ]?\d.*)?$", "grok"),
        (r"^glm(?:[- ]?\d.*)?$", "glm"),
        (r"^qwen(?:[- ]?.*)?$", "qwen"),
        (r"^kimi(?:[- ]?.*)?$", "kimi"),
    )
    for pattern, canonical in exact_mappings:
        if re.fullmatch(pattern, lowered, re.IGNORECASE):
            return canonical

    # Allow explicit provider/model or full model IDs through as-is.
    if re.fullmatch(r"[A-Za-z0-9._:/-]+", cleaned):
        return cleaned
    return None


def maybe_build_model_switch_command(text: str) -> Optional[str]:
    """Rewrite an explicit natural-language switch request to ``/model``.

    Returns ``None`` when the message looks like regular discussion rather than
    an imperative switch request.
    """
    stripped = (text or "").strip()
    if not stripped or stripped.startswith("/") or "\n" in stripped:
        return None

    for pattern in _GLOBAL_PATTERNS:
        match = pattern.match(stripped)
        if match:
            target = _normalize_target(match.group("target"))
            return f"/model {target} --global" if target else None

    for pattern in _SESSION_PATTERNS:
        match = pattern.match(stripped)
        if match:
            target = _normalize_target(match.group("target"))
            return f"/model {target}" if target else None

    return None
