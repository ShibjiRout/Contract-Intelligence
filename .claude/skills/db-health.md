# /db-health

Check all database and service connections with latency reporting.

## Usage
```
/db-health [--verbose] [--fix]
```

## Checks
| Service | Check Method |
|---------|-------------|
| MongoDB | `ping` command |
| PostgreSQL | `SELECT 1` |
| Qdrant | `GET /healthz` |
| Neo4j | `RETURN 1` Cypher |
| Redis | `PING` command |

## Output
```
Service       Status    Latency    Error
────────────────────────────────────────
MongoDB       ✓ OK      12ms       —
PostgreSQL    ✓ OK      8ms        —
Qdrant        ✓ OK      23ms       —
Neo4j         ✗ FAIL    —          Connection refused (localhost:7687)
Redis         ✓ OK      2ms        —
```

## --fix Flag
If any service fails, attempt to re-initialize:
- Qdrant: re-create collections from `db/qdrant/collections.py`
- MongoDB: re-create indexes from `db/mongodb/migrations/`
- PostgreSQL: run pending Alembic migrations
- Does NOT attempt to start stopped Docker containers

## Rules
- Timeout per check: 5 seconds
- Does not modify any data (read-only checks, except with --fix)
- Reads connection config from environment variables only
