from contracts_platform.core.logging import logger
from contracts_platform.pipeline.ocr import confidence as conf_module
from contracts_platform.pipeline.ocr.providers import azure_ocr_provider


async def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Main OCR entry point called by ocr_task.

    1. Calls azure_ocr_provider.analyze_document()
    2. Scores confidence per page
    3. Logs a warning for any low-confidence pages
    4. Concatenates all page text into a single full_text string
    5. Returns full_text
    """
    pages = await azure_ocr_provider.analyze_document(file_bytes, filename)

    low_conf_pages = conf_module.find_low_confidence_pages(pages)
    if low_conf_pages:
        logger.warning(
            "ocr.low_confidence_pages",
            filename=filename,
            page_numbers=low_conf_pages,
            threshold=conf_module.CONFIDENCE_THRESHOLD,
        )

    overall = conf_module.overall_confidence(pages)
    logger.info(
        "ocr.confidence_summary",
        filename=filename,
        overall_confidence=round(overall, 4),
        total_pages=len(pages),
    )

    full_text = "\n\n".join(p.get("text", "") for p in pages)
    return full_text
