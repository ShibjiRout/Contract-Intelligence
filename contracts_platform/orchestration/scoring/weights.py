import time

from contracts_platform.core.logging import logger

DEFAULT_WEIGHTS = {"postgresql": 0.5, "qdrant": 0.3, "neo4j": 0.2}

_cache: dict = {}
_cache_ts: float = 0.0
TTL = 300  # 5 minutes


async def get_weights(jurisdiction: str, session) -> dict[str, float]:
    """
    Load from PostgreSQL rule_weights table for jurisdiction.
    Cache result for TTL seconds.
    Fall back to DEFAULT_WEIGHTS if DB unavailable.
    Returns {"postgresql": float, "qdrant": float, "neo4j": float}
    """
    global _cache, _cache_ts

    now = time.monotonic()
    if _cache.get(jurisdiction) and (now - _cache_ts) < TTL:
        logger.debug("weights.cache_hit", jurisdiction=jurisdiction)
        return _cache[jurisdiction]

    try:
        from contracts_platform.db.postgresql.repositories.rule_repo import get_weights as _get_weights

        raw = await _get_weights(session, jurisdiction)
        weights = {
            "postgresql": raw.get("postgresql_weight", DEFAULT_WEIGHTS["postgresql"]),
            "qdrant": raw.get("qdrant_weight", DEFAULT_WEIGHTS["qdrant"]),
            "neo4j": raw.get("neo4j_weight", DEFAULT_WEIGHTS["neo4j"]),
        }
        _cache[jurisdiction] = weights
        _cache_ts = now
        logger.info("weights.loaded", jurisdiction=jurisdiction, weights=weights)
        return weights
    except Exception as exc:
        logger.warning(
            "weights.load_failed",
            jurisdiction=jurisdiction,
            error=str(exc),
            fallback=DEFAULT_WEIGHTS,
        )
        return DEFAULT_WEIGHTS
