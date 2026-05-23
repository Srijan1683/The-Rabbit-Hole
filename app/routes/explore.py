import uuid

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.models.conversation import ExploreRequest, ExploreResponse
from app.services.exploration import explore_topic
from app.services.streaming import stream_exploration
from app.core.errors import NotFoundError

router = APIRouter(tags=["explore"])

@router.post("/explore", response_model=ExploreResponse)
async def explore(payload: ExploreRequest):
    try:
        return await explore_topic(
            query=payload.query,
            session_id=payload.session_id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/explore/stream")
async def stream_new_explore(
    query: str = Query(..., min_length=1),
):
    return EventSourceResponse(
        stream_exploration(
            query=query,
            session_id=None,
        )
    )

@router.get("/explore/{session_id}/stream")
async def stream_existing_session_explore(
    session_id: uuid.UUID,
    query: str = Query(..., min_length=1),
):
    return EventSourceResponse(
        stream_exploration(
            query=query,
            session_id=session_id,
        )
    )