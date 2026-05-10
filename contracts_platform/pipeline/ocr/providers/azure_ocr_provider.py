import asyncio
import base64
from functools import partial

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
from azure.core.credentials import AzureKeyCredential

from contracts_platform.core.config import settings
from contracts_platform.core.logging import logger

# Paragraph roles that map to markdown section headings
_HEADING_ROLES = {"sectionHeading", "title"}


def _analyze_sync_pages(file_bytes: bytes) -> list[dict]:
    """prebuilt-layout, plain text per page — used by contract OCR pipeline."""
    client = DocumentIntelligenceClient(
        endpoint=settings.AZURE_OCR_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_OCR_KEY),
    )
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(bytes_source=base64.b64encode(file_bytes).decode()),
    )
    result = poller.result()

    page_confidence: dict[int, float] = {}
    for page in result.pages or []:
        words = page.words or []
        page_confidence[page.page_number] = (
            sum(w.confidence for w in words) / len(words) if words else 1.0
        )

    page_tables: dict[int, list[dict]] = {}
    for table in result.tables or []:
        table_pages = {r.page_number for r in (table.bounding_regions or [])}
        max_col = max((c.column_index for c in table.cells), default=-1) + 1
        max_row = max((c.row_index for c in table.cells), default=-1) + 1
        grid: list[list[str]] = [[""] * max_col for _ in range(max_row)]
        for cell in table.cells:
            grid[cell.row_index][cell.column_index] = cell.content or ""
        headers = grid[0] if max_row > 0 else []
        rows = grid[1:] if max_row > 1 else []
        for pn in table_pages:
            page_tables.setdefault(pn, []).append({"headers": headers, "rows": rows})

    page_paragraphs: dict[int, list[str]] = {}
    for para in result.paragraphs or []:
        content = (para.content or "").strip()
        if not content:
            continue
        pn = para.bounding_regions[0].page_number if para.bounding_regions else 1
        page_paragraphs.setdefault(pn, []).append(content)

    all_page_nums = sorted(set(page_paragraphs) | set(page_confidence) | set(page_tables))
    return [
        {
            "page_num": pn,
            "text": "\n\n".join(page_paragraphs.get(pn, [])),
            "confidence": page_confidence.get(pn, 1.0),
            "tables": page_tables.get(pn, []),
        }
        for pn in all_page_nums
    ]


def _analyze_sync_markdown(file_bytes: bytes) -> str:
    """prebuilt-layout with markdown output — returns full document as markdown string."""
    client = DocumentIntelligenceClient(
        endpoint=settings.AZURE_OCR_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_OCR_KEY),
    )
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(bytes_source=base64.b64encode(file_bytes).decode()),
        output_content_format=DocumentContentFormat.MARKDOWN,
    )
    result = poller.result()
    return result.content or ""


async def analyze_document(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Analyze a document — returns per-page dicts:
        {page_num: int, text: str, confidence: float, tables: list[dict]}
    """
    logger.info("azure_ocr.start", filename=filename, size_bytes=len(file_bytes))
    loop = asyncio.get_event_loop()
    pages = await loop.run_in_executor(None, partial(_analyze_sync_pages, file_bytes))
    logger.info("azure_ocr.complete", filename=filename, pages=len(pages))
    return pages


async def analyze_document_markdown(file_bytes: bytes, filename: str) -> str:
    """
    Analyze a document and return the full text as Azure-generated markdown.
    Section headings are rendered as '# ' or '## ' by Azure DI automatically.
    Use this for playbook ingestion where heading-based splitting is needed.
    """
    logger.info("azure_ocr.markdown.start", filename=filename, size_bytes=len(file_bytes))
    loop = asyncio.get_event_loop()
    markdown = await loop.run_in_executor(None, partial(_analyze_sync_markdown, file_bytes))
    logger.info("azure_ocr.markdown.complete", filename=filename, chars=len(markdown))
    return markdown
