import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv


async def main() -> None:
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("Missing DATABASE_URL")

    migration_path = Path("migrations/001_initial_schema.sql")
    migration_sql = migration_path.read_text(encoding="utf-8")

    connection = await asyncpg.connect(database_url)

    try:
        existing_schema = await connection.fetchval("SELECT to_regclass('public.sessions')")

        if existing_schema:
            print("Migrations already applied")
            return

        await connection.execute(migration_sql)
    finally:
        await connection.close()

    print("Migrations applied")


if __name__ == "__main__":
    asyncio.run(main())
