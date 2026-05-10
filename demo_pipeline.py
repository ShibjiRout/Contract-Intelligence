"""
Demo: full pipeline on a sample contract PDF.

Shows in terminal:
  1. PDF text extraction (OCR)
  2. LLM clause extraction
  3. LangGraph orchestration per clause:
       - Playbook check  (PostgreSQL)
       - Vector check    (Qdrant)
       - Graph check     (Neo4j)
       - Risk level      (GREEN / AMBER / RED)

Run:
    uv run python demo_pipeline.py [path/to/contract.pdf]

Defaults to data/Contract_1.pdf if no arg given.
"""
import asyncio
import sys
import uuid
from pathlib import Path

# ── helpers ───────────────────────────────────────────────────────────────────

def sep(title: str = "", width: int = 70) -> None:
    if title:
        pad = (width - len(title) - 2) // 2
        print("\n" + "=" * pad + f" {title} " + "=" * pad)
    else:
        print("=" * width)


def risk_colour(level: str) -> str:
    colours = {"GREEN": "\033[92m", "AMBER": "\033[93m", "RED": "\033[91m"}
    reset = "\033[0m"
    return f"{colours.get(level, '')}{level}{reset}"


# ── main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/Contract_1.pdf")

    if not pdf_path.exists():
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)

    contract_id = str(uuid.uuid4())
    file_bytes  = pdf_path.read_bytes()

    print(f"\nContract file : {pdf_path}")
    print(f"Contract ID   : {contract_id}")
    print(f"File size     : {len(file_bytes):,} bytes")

    # ── STEP 1: OCR ───────────────────────────────────────────────────────────
    sep("STEP 1 — OCR TEXT EXTRACTION")

    from contracts_platform.pipeline.ocr.extractor import extract_text, extract_pages
    full_text = await extract_text(file_bytes, pdf_path.name)
    pages     = await extract_pages(file_bytes, pdf_path.name)

    print(f"Pages returned : {len(pages)}")
    for p in pages:
        print(f"  page {p['page_num']:2d} — {len(p['text']):,} chars  confidence={p['confidence']:.3f}")
    print(f"\nTotal text length: {len(full_text):,} chars")
    print("\n--- First 400 chars of extracted text ---")
    print(full_text[:400])

    # ── STEP 2: CLAUSE EXTRACTION ─────────────────────────────────────────────
    sep("STEP 2 — LLM CLAUSE EXTRACTION")

    from contracts_platform.pipeline.clause_extraction.extractor import extract_clauses
    clauses = await extract_clauses(contract_id, full_text)

    print(f"Clauses extracted: {len(clauses)}")
    for i, c in enumerate(clauses, 1):
        print(f"\n  [{i}] {c.get('clause_type','?'):30s}  confidence={c.get('confidence', 0):.2f}")
        print(f"       clause_id : {c.get('clause_id','')}")
        print(f"       raw_text  : {str(c.get('raw_text',''))[:120]}...")
        if c.get("parties_mentioned"):
            print(f"       parties   : {c['parties_mentioned']}")
        if c.get("risk_indicators"):
            print(f"       risks     : {c['risk_indicators'][0][:100]}")

    if not clauses:
        print("[WARN] No clauses extracted — cannot run orchestration.")
        return

    # ── STEP 3: LANGGRAPH ORCHESTRATION ───────────────────────────────────────
    sep("STEP 3 — LANGGRAPH ORCHESTRATION (per clause)")

    from contracts_platform.orchestration.graph import build_graph
    compiled = build_graph().compile()

    # Use first jurisdiction found in clauses, fallback to UK
    jurisdiction = "UK"

    summary_rows = []

    for i, clause in enumerate(clauses, 1):
        clause_id   = str(clause.get("clause_id", uuid.uuid4()))
        clause_type = clause.get("clause_type", "UNKNOWN")
        clause_text = clause.get("raw_text", "")

        print(f"\n{'─'*60}")
        print(f"Clause {i}/{len(clauses)}: {clause_type}  (id={clause_id[:8]}...)")
        print(f"  Text preview: {clause_text[:100]}...")

        state = {
            "contract_id"    : contract_id,
            "clause_id"      : clause_id,
            "clause_type"    : clause_type,
            "clause_text"    : clause_text,
            "jurisdiction"   : jurisdiction,
            "tenant_id"      : "demo",
            "playbook_result": None,
            "vector_result"  : None,
            "graph_result"   : None,
            "risk_level"     : "GREEN",
            "risk_score"     : 0.0,
            "degraded_mode"  : False,
            "failed_sources" : [],
            "missing_clauses": [],
            "recommendation" : None,
            "suggested_fix"  : None,
            "explanation"    : None,
            "messages"       : [],
        }

        try:
            final = await compiled.ainvoke(state)
        except Exception as exc:
            print(f"  [ERROR] Orchestration failed: {exc}")
            continue

        # ── Playbook check result
        pb = final.get("playbook_result") or {}
        print(f"\n  ① Playbook check (PostgreSQL)")
        print(f"     rules_checked : {pb.get('rules_checked', 0)}")
        print(f"     score         : {pb.get('score', 0):.3f}")
        for f in (pb.get("findings") or [])[:3]:
            print(f"     finding       : {f}")

        # ── Vector check result
        vc = final.get("vector_result") or {}
        print(f"\n  ② Vector check (Qdrant)")
        print(f"     similar_rejected : {vc.get('similar_rejected', 0)}")
        print(f"     score            : {vc.get('score', 0):.3f}")

        # ── Graph check result
        gc = final.get("graph_result") or {}
        print(f"\n  ③ Graph check (Neo4j)")
        print(f"     playbook_rules_checked : {gc.get('playbook_rules_checked', 0)}")
        print(f"     violations             : {len(gc.get('violations') or [])}")
        print(f"     counterparty_flags     : {gc.get('counterparty_flags', 0)}")
        print(f"     score                  : {gc.get('score', 0):.3f}")
        for v in (gc.get("violations") or [])[:2]:
            print(f"     violation : {v[:100]}")

        # ── Risk
        risk  = final.get("risk_level", "UNKNOWN")
        score = final.get("risk_score", 0.0)
        print(f"\n  ➜ RISK: {risk_colour(risk)}  score={score:.3f}")

        if final.get("recommendation"):
            print(f"  ➜ Recommendation: {str(final['recommendation'])[:120]}")
        if final.get("suggested_fix"):
            print(f"  ➜ Suggested fix : {str(final['suggested_fix'])[:120]}")
        if final.get("degraded_mode"):
            print(f"  ⚠  Degraded mode — failed sources: {final.get('failed_sources')}")

        summary_rows.append({
            "clause_type": clause_type,
            "risk"        : risk,
            "score"       : score,
        })

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    sep("SUMMARY")
    print(f"{'Clause Type':<35} {'Risk':<8} {'Score'}")
    print("─" * 60)
    for row in summary_rows:
        print(f"{row['clause_type']:<35} {risk_colour(row['risk']):<8}  {row['score']:.3f}")

    counts = {"GREEN": 0, "AMBER": 0, "RED": 0}
    for r in summary_rows:
        counts[r["risk"]] = counts.get(r["risk"], 0) + 1
    print(f"\nTotal clauses : {len(summary_rows)}")
    print(f"  GREEN : {counts['GREEN']}")
    print(f"  AMBER : {counts['AMBER']}")
    print(f"  RED   : {counts['RED']}")
    sep()


if __name__ == "__main__":
    asyncio.run(main())
