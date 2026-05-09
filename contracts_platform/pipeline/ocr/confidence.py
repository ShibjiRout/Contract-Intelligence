CONFIDENCE_THRESHOLD = 0.85


def score_page(page_dict: dict) -> float:
    """Extract confidence from an Azure page result dict. Return 0.0 if missing."""
    return float(page_dict.get("confidence", 0.0))


def find_low_confidence_pages(pages: list[dict]) -> list[int]:
    """Return page_num list for pages below CONFIDENCE_THRESHOLD."""
    return [p["page_num"] for p in pages if score_page(p) < CONFIDENCE_THRESHOLD]


def overall_confidence(pages: list[dict]) -> float:
    """Return mean confidence across all pages. Returns 0.0 for empty input."""
    if not pages:
        return 0.0
    return sum(score_page(p) for p in pages) / len(pages)
