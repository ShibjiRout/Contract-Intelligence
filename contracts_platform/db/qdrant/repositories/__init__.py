from contracts_platform.db.qdrant.repositories import clause_vector_repo, clause_repo
from contracts_platform.db.qdrant.repositories.clause_repo import (
    get_accepted_wording,
    search_similar_clauses,
    upsert_clause,
)
from contracts_platform.db.qdrant.repositories.tenant_manager import ensure_tenant_collection

__all__ = [
    # sub-modules (used by callers that import the module object directly)
    "clause_vector_repo",
    "clause_repo",
    # flat function exports from clause_repo
    "search_similar_clauses",
    "upsert_clause",
    "get_accepted_wording",
    # tenant helper
    "ensure_tenant_collection",
]
