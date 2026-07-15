from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

import uuid


from app.dependencies.auth import get_current_user

from app.db.session import get_db
from app.schemas.notifications import NotificationCreateRequest, NotificationResponse, NotificationAttemptResponse
from app.services.notification_worker_service import get_notification_with_attempts
from app.services.notification_service import create_notification
from app.tasks.notifications_tasks import process_notification_task


logger = logging.getLogger(__name__)



@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create(
    req: NotificationCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    notif = await create_notification(
        session=session,
        channel=str(req.channel),
        recipient=req.recipient,
        template_id=req.template_id,
        variables=req.variables,
    )

    # Enqueue async processing (API must not process directly).
    process_notification_task.delay(str(notif.id), 1)

    return {
        "success": True,
        "message": "Notification queued",
        "notification_id": notif.id,
    }




@router.get("")
async def list_(session: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    notifs = await get_notification_with_attempts(session=session)
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
            attempts=[
                NotificationAttemptResponse(attempt=a.attempt_number, status=a.status.value, error=a.error_message)
                for a in (n.attempts or [])
            ],

        ).model_dump()
        for n in notifs
    ]
    return {"success": True, "data": data}


@router.get("/{notification_id}")
async def get(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),

    current_user=Depends(get_current_user),
):
    notif = await get_notification_with_attempts(session=session, notification_id=notification_id)

    return {
        "success": True,
        "data": NotificationResponse(
            id=notif.id,
            channel=notif.channel,
            recipient=notif.recipient,
            template_id=notif.template_id,
            rendered_subject=notif.rendered_subject,
            rendered_body=notif.rendered_body,
            status=notif.status,

            created_at=str(notif.created_at),
            attempts=[
                NotificationAttemptResponse(attempt=a.attempt_number, status=a.status.value, error=a.error_message)
                for a in (notif.attempts or [])
            ],

        ).model_dump(),
    }


