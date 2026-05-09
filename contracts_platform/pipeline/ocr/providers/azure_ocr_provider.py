import asyncio
from functools import partial

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger


def _analyze_sync(file_bytes: bytes) -> list[dict]:
    """Synchronous Azure Document Intelligence call."""
    client = DocumentAnalysisClient(
        endpoint=settings.AZURE_OCR_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_OCR_KEY),
    )
    poller = client.begin_analyze_document(
        model_id="prebuilt-document",
        document=file_bytes,
    )
    result = poller.result()

    pages = []
    for page in result.pages:
        page_num = page.page_number
        lines = page.lines or []
        text = "\n".join(line.content for line in lines)

        # Aggregate word-level confidence for the page
        words = page.words or []
        if words:
            confidence = sum(w.confidence for w in words) / len(words)
        else:
            confidence = 0.0

        # Extract tables that belong to this page
        tables = []
        for table in (result.tables or []):
            # Check if table spans this page
            table_pages = {r.page_number for r in (table.bounding_regions or [])}
            if page_num not in table_pages:
                continue
            # Build headers from first row
            max_col = max((c.column_index for c in table.cells), default=-1) + 1
            max_row = max((c.row_index for c in table.cells), default=-1) + 1
            grid: list[list[str]] = [[""] * max_col for _ in range(max_row)]
            for cell in table.cells:
                grid[cell.row_index][cell.column_index] = cell.content
            headers = grid[0] if max_row > 0 else []
            rows = grid[1:] if max_row > 1 else []
            tables.append({"headers": headers, "rows": rows})

        pages.append(
            {
                "page_num": page_num,
                "text": text,
                "confidence": confidence,
                "tables": tables,
            }
        )

    return pages


async def analyze_document(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Analyze a document with Azure AI Document Intelligence.

    Returns a list of page dicts:
        {page_num: int, text: str, confidence: float, tables: list[dict]}
    """
    logger.info("azure_ocr.start", filename=filename, size_bytes=len(file_bytes))
    loop = asyncio.get_event_loop()
    pages = await loop.run_in_executor(None, partial(_analyze_sync, file_bytes))
    logger.info("azure_ocr.complete", filename=filename, pages=len(pages))
    return pages
