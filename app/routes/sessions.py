import uuid

from fastapi import APIRouter, HTTPException, Query

from app.db.sessions import create_session, delete_session, get_session, list_sessions
from app.db.history import get_history, get_tool_calls_for_session
from app.models.session import Session, SessionCreate, SessionList
from app.models.conversation import Message

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=Session)
async def create_new_session(payload: SessionCreate):
    return await create_session(payload.title)

@router.get("/{session_id}", response_model=Session)
async def get_session_by_id(session_id: uuid.UUID):
    session = await get_session(session_id)
    
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

@router.get("", response_model=SessionList)
async def list_all_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    sessions, total = await list_sessions(limit=limit, offset=offset)
    return {"sessions": sessions, "total": total}

@router.delete("/{session_id}")
async def delete_session_by_id(session_id: uuid.UUID):
    deleted = await delete_session(session_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"deleted": True}

@router.get("/{session_id}/history", response_model=list[Message])
async def get_session_history(
    session_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
):
    session = await get_session(session_id)
    
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return await get_history(session_id=session_id, limit=limit)

@router.get("/{session_id}/tool-calls")
async def get_session_tool_calls(session_id: uuid.UUID):
    session = await get_session(session_id)
    
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return await get_tool_calls_for_session(session_id=session_id)