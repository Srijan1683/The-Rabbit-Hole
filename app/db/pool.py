import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

pool = None

async def create_pool():
    global pool
    pool = await asyncpg.create_pool(
        os.getenv("DATABASE_URL"),
        min_size=2,
        max_size=10
        )
    print("Database pool created")
    
async def close_pool():
    global pool
    if pool is not None:
        await pool.close()
    print("Database pool closed")
    
def get_pool():
    return pool