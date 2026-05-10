"""
Quick debug: shows what Azure DI returns and how the splitter chunks it.
Run: uv run python debug_splitter.py
"""
import asyncio
import re
from pathlib import Path


async def main():
    pdf_bytes = Path("data/Playbook.pdf").read_bytes()

    print("=" * 60)
    print("STEP 1 — Azure DI markdown output")
    print("=" * 60)

    from contracts_platform.pipeline.ocr.extractor import extract_markdown
    markdown = await extract_markdown(pdf_bytes, "Playbook.pdf")

    print(f"Total chars: {len(markdown)}")
    print("\n--- First 800 chars ---")
    print(markdown[:800])
    print("\n--- Last 400 chars ---")
    print(markdown[-400:])

    print("\n" + "=" * 60)
    print("STEP 2 — Lines that contain 'CLAUSE'")
    print("=" * 60)
    for i, line in enumerate(markdown.splitlines(), 1):
        if "clause" in line.lower():
            print(f"  line {i:3d}: {repr(line[:120])}")

    print("\n" + "=" * 60)
    print("STEP 3 — Splitter chunks")
    print("=" * 60)
    from contracts_platform.pipeline.ocr.splitter import split_markdown_by_headings
    chunks = split_markdown_by_headings(markdown)
    print(f"Total chunks: {len(chunks)}")
    for i, c in enumerate(chunks, 1):
        print(f"\n  chunk {i}: heading={repr(c['heading'][:80])}  chars={len(c['text'])}")
        print(f"  preview: {repr(c['text'][:200])}")


asyncio.run(main())
