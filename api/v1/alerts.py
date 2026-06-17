from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db
from services.notification_service import get_unread_alerts, mark_alerts_read

router = APIRouter(prefix="/api/v1", tags=["alerts"])


class MarkReadRequest(BaseModel):
    alert_ids: list[int]


@router.get("/alerts/{user_id}")
async def list_alerts(user_id: str, include_read: bool = False, db: AsyncSession = Depends(get_db)):
    rows = await get_unread_alerts(db, user_id)
    return {"alerts": rows}


@router.post("/alerts/{user_id}/mark-read")
async def mark_read(user_id: str, body: MarkReadRequest, db: AsyncSession = Depends(get_db)):
    await mark_alerts_read(db, user_id, body.alert_ids)
    return {"status": "ok"}
