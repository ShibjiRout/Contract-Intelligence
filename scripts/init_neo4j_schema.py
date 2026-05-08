import asyncio
from contracts_platform.db.neo4j.client import get_driver, close_driver


async def main() -> None:
    driver = await get_driver()
    async with driver.session() as session:
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Party) REQUIRE p.party_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Contract) REQUIRE c.contract_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (cl:Clause) REQUIRE cl.clause_id IS UNIQUE",
        ]
        for constraint in constraints:
            await session.run(constraint)
    await close_driver()
    print("Neo4j schema initialized.")


if __name__ == "__main__":
    asyncio.run(main())
