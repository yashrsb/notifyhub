from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.notifications import NotificationCreateRequest, NotificationResponse
from app.services.notification_service import create_notification, get_notification, list_notifications

router = APIRouter()


@router.post("")
async def create(
    req: NotificationCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    notif = await create_notification(
        session=session,
        channel=req.channel,
        recipient=req.recipient,
        template_id=req.template_id,
        variables=req.variables,
    )
    return {"success": True, "data": NotificationResponse(
        id=notif.id,
        channel=notif.channel,
        recipient=notif.recipient,
        template_id=notif.template_id,
        rendered_subject=notif.rendered_subject,
        rendered_body=notif.rendered_body,
        status=notif.status,
        created_at=str(notif.created_at),
    ).model_dump()}


@router.get("")
async def list_(session: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    notifs = await list_notifications(session=session)
    data = [
        NotificationResponse(
            id=n.id,
            channel=n.channel,
            recipient=n.recipient,
            template_id=n.template_id,
            rendered_subject=n.rendered_subject,
            rendered_body=n.rendered_body,
            status=n.status,
            created_at=str(n.created_at),
        ).model_dump()
        for n in notifs
    ]
    return {"success": True, "data": data}


@router.get("/{notification_id}")
async def get(notification_id: uuid.UUID, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    notif = await get_notification(session=session, notification_id=notification_id)
    return {"success": True, "data": NotificationResponse(
        id=notif.id,
        channel=notif.channel,
        recipient=notif.recipient,
        template_id=notif.template_id,
        rendered_subject=notif.rendered_subject,
        rendered_body=notif.rendered_body,
        status=notif.status,
        created_at=str(notif.created_at),
    ).model_dump()}

