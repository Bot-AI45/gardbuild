from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

DEFAULT_MASK = "[REDACTED]"

DEFAULT_PATTERNS: dict[str, str] = {
    # Card numbers go first: a 16-digit PAN also satisfies the phone pattern.
    "credit_card": r"\b(?:\d[ -]?){12,18}\d\b",
    "api_key": r"\b(?:sk|pk|rk)-[A-Za-z0-9]{16,}\b|\b(?:AKIA|gh[pous]_)[A-Za-z0-9]{16,}\b",
    "secret": r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|bearer)\b\s*[:=]?\s*[A-Za-z0-9._+/=-]{12,}",
    "email": r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
    "phone": r"(?<!\w)(?:\+\d{1,3}[ -]?)?(?:\(\d{3}\)|\d{3})[ -]?\d{3}[ -]?\d{4}(?!\w)",
}


class PiiGuard:
    """Replaces personal and secret data with a mask.

    Text, mappings, lists and tuples are scrubbed recursively. ``patterns``
    adds or overrides rules by name, and ``masks`` overrides the replacement
    used for a named rule. Payloads nested deeper than ``MAX_DEPTH`` levels
    raise ValueError instead of passing through unsanitized.
    """

    MAX_DEPTH = 64

    def __init__(
        self,
        mask: str = DEFAULT_MASK,
        patterns: Mapping[str, str] | None = None,
        masks: Mapping[str, str] | None = None,
    ) -> None:
        self.mask = mask
        self._masks = dict(masks or {})
        self._patterns = {
            name: re.compile(source)
            for name, source in {**DEFAULT_PATTERNS, **(patterns or {})}.items()
        }

    def scrub(self, value: Any, _depth: int = 0) -> Any:
        """Return a copy of ``value`` with every match replaced by a mask."""
        if _depth >= self.MAX_DEPTH:
            raise ValueError("payload nesting exceeds MAX_DEPTH")
        if isinstance(value, str):
            return self._scrub_text(value)
        if isinstance(value, Mapping):
            return {key: self.scrub(item, _depth + 1) for key, item in value.items()}
        if isinstance(value, list):
            return [self.scrub(item, _depth + 1) for item in value]
        if isinstance(value, tuple):
            return tuple(self.scrub(item, _depth + 1) for item in value)
        return value

    def _scrub_text(self, text: str) -> str:
        for name, pattern in self._patterns.items():
            text = pattern.sub(self._masks.get(name, self.mask), text)
        return text
