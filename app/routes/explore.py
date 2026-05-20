from fastapi import APIRouter, HTTPException

from app.models.conversation import ExploreRequest, ExploreResponse
from app.services.exploration import explore_topic

router = APIRouter(tags=["explore"])

@router.post("/explore", response_model=ExploreResponse)
async def explore(payload: ExploreRequest):
    try:
        return await explore_topic(
            query=payload.query,
            session_id=payload.session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc