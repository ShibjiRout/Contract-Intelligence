from __future__ import annotations

import re

# Lookahead split: keeps "CLAUSE X" at the start of each chunk.
# Case-sensitive + line-anchored so we only split on real headings,
# not on the word "clause" appearing mid-paragraph.
_CLAUSE_SPLIT_RE = re.compile(
    r"(?=^\s*(?:#+\s*)?(?:\*\*)?CLAUSE\s+[A-Z]\b)",
    re.MULTILINE,
)

# Minimum chars for a chunk to be worth sending to the LLM
_MIN_CHUNK_LEN = 50


def split_markdown_by_headings(markdown: str) -> list[dict]:
    """
    Split document text into per-clause chunks by splitting before every
    'CLAUSE A', 'CLAUSE 1', 'CLAUSE B —', etc. occurrence.

    Returns list of {"heading": str, "text": str}.
    """
    raw_chunks = _CLAUSE_SPLIT_RE.split(markdown)
    chunks: list[dict] = []
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if len(chunk) < _MIN_CHUNK_LEN:
            continue
        # First line of the chunk is the heading
        first_line = chunk.splitlines()[0].strip()
        heading = re.sub(r"[*#]+", "", first_line).strip()
        chunks.append({"heading": heading, "text": chunk})
    return chunks
