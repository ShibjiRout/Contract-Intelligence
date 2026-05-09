import re
import uuid
from datetime import date


# Regex patterns
_PARTY_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z\s&,\.]+?)\s+(?:Ltd|Inc|LLC|plc|Limited)\b"
)
_ISO_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_COMMON_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|"
    r"August|September|October|November|December)\s+\d{4})\b",
    re.IGNORECASE,
)
_OBLIGATION_PATTERN = re.compile(
    r"[^.!?]*\b(?:shall|must|agrees?\s+to)\b[^.!?]*[.!?]",
    re.IGNORECASE,
)
_RISK_PATTERN = re.compile(
    r"[^.!?]*\b(?:terminat(?:e|ion)|breach|penalty|liable|liability)\b[^.!?]*[.!?]",
    re.IGNORECASE,
)


def _parse_dates(text: str) -> list[date]:
    """Extract ISO and common date strings, returning date objects."""
    found: list[date] = []
    for m in _ISO_DATE_PATTERN.finditer(text):
        try:
            found.append(date.fromisoformat(m.group(1)))
        except ValueError:
            pass
    return found


def parse_clause(contract_id: str, raw_text: str, page_num: int) -> dict:
    """
    Regex-based fallback parser for when LLM output fails Pydantic validation.

    Extracts:
    - parties_mentioned: company names preceding Ltd / Inc / LLC / plc / Limited
    - key_dates: ISO dates (YYYY-MM-DD)
    - key_obligations: sentences containing 'shall', 'must', 'agrees to'
    - risk_indicators: sentences containing 'terminate', 'breach', 'penalty', 'liable'

    Returns a dict compatible with ExtractedClause fields (clause_id auto-generated).
    """
    parties = list(dict.fromkeys(m.group(0).strip() for m in _PARTY_PATTERN.finditer(raw_text)))
    key_dates = _parse_dates(raw_text)
    obligations = [m.group(0).strip() for m in _OBLIGATION_PATTERN.finditer(raw_text)]
    risk_indicators = [m.group(0).strip() for m in _RISK_PATTERN.finditer(raw_text)]

    return {
        "clause_id": str(uuid.uuid4()),
        "clause_type": "CONFIDENTIALITY",  # safest default — callers should override
        "raw_text": raw_text,
        "start_page": page_num,
        "end_page": page_num,
        "parties_mentioned": parties,
        "key_dates": [d.isoformat() for d in key_dates],
        "key_obligations": obligations,
        "risk_indicators": risk_indicators,
        "confidence": 0.3,  # low confidence signal for fallback-parsed clauses
    }
