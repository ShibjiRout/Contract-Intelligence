from __future__ import annotations

import hashlib
import re

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"^[\s,;:.]+|[\s,;:.]+$")


def normalize_party_name(name: str) -> str:
    """Return a stable lowercase party name for matching across contracts."""
    normalized = name.replace("\n", " ").replace("\r", " ")
    normalized = _TRAILING_PUNCT_RE.sub("", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip().lower()


def generate_party_id(normalized_name: str) -> str:
    digest = hashlib.sha256(normalized_name.encode("utf-8")).hexdigest()[:16]
    return f"party_{digest}"
