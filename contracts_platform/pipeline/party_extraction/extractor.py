from __future__ import annotations

import re

from contracts_platform.pipeline.party_extraction.normalizer import (
    generate_party_id,
    normalize_party_name,
)

_BETWEEN_RE = re.compile(
    r"\bbetween\s+(?P<first>.+?)\s+(?:and|&)\s+(?P<second>.+?)(?:\.|\n|,|\s+dated\b|\s+whereas\b)",
    re.IGNORECASE | re.DOTALL,
)

_ROLE_HINTS = (
    ("supplier", ("supplier", "vendor", "provider", "seller")),
    ("customer", ("customer", "client", "buyer", "purchaser")),
    ("contractor", ("contractor", "consultant")),
)


def _clean_candidate(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"^(?:the\s+)?(?:company|agreement|contract)\s+", "", value, flags=re.IGNORECASE)
    return value.strip(" \t\r\n,;:.()")


def _infer_role(name: str, index: int) -> str:
    lower_name = name.lower()
    for role, hints in _ROLE_HINTS:
        if any(hint in lower_name for hint in hints):
            return role
    return "party_a" if index == 0 else "party_b"


def _to_party(name: str, index: int) -> dict:
    normalized_name = normalize_party_name(name)
    return {
        "party_id": generate_party_id(normalized_name),
        "name": name,
        "normalized_name": normalized_name,
        "role": _infer_role(name, index),
    }


def extract_parties(text: str) -> list[dict]:
    """Extract parties from simple 'between X and Y' contract introductions."""
    match = _BETWEEN_RE.search(text or "")
    if not match:
        return []

    names = [
        _clean_candidate(match.group("first")),
        _clean_candidate(match.group("second")),
    ]

    parties: list[dict] = []
    seen: set[str] = set()
    for index, name in enumerate(names):
        normalized = normalize_party_name(name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        parties.append(_to_party(name, index))
    return parties
