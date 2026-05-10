from neo4j import AsyncGraphDatabase, AsyncDriver
from contracts_platform.core.config import settings


async def get_driver() -> AsyncDriver:
    return AsyncGraphDatabase.driver(
        settings.NEO4J_URL,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


async def close_driver() -> None:
    pass
