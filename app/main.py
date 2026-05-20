from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.pool import close_pool, create_pool
from app.routes.sessions import router as sessions_router
from app.routes.explore import router as explore_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(title="The Rabbit Hole", lifespan=lifespan)
app.include_router(sessions_router)
app.include_router(explore_router)