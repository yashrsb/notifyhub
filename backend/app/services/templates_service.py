from __future__ import annotations

import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.templates_repo import TemplatesRepository


logger = logging.getLogger(__name__)


async def _publish_template_audit_event(
    *,
    session: AsyncSession,
    entity_id: uuid.UUID,
    action: object,
    performed_by: uuid.UUID,
    metadata: dict,
) -> None:
    try:
        from app.models.audit_logs import AuditEntityType, AuditAction
        from app.services.audit_service import AuditService

        audit_service = AuditService(session=session)
        await audit_service.publish(
            entity_type=AuditEntityType.TEMPLATE,
            entity_id=str(entity_id),
            action=action,
            performed_by=str(performed_by),
            metadata=metadata,
        )
    except Exception:
        logger.exception(
            "Template audit log persistence failed",
            extra={
                "entity_id": str(entity_id),
                "action": str(action),
            },
        )
        return


async def create_template(
    *,
    session: AsyncSession,
    created_by: uuid.UUID,
    name: str,
    subject: str,
    body: str,
):
    repo = TemplatesRepository(session)
    tpl = await repo.create(created_by=created_by, name=name, subject=subject, body=body)

    # Audit (must never break business operation)
    from app.models.audit_logs import AuditAction

    await _publish_template_audit_event(
        session=session,
        entity_id=tpl.id,
        action=AuditAction.TEMPLATE_CREATED,
        performed_by=created_by,
        metadata={
            "template_id": str(tpl.id),
            "template_name": tpl.name,
            "channel": "email",
            "created_by": str(created_by),
        },
    )
    return tpl




async def list_templates(*, session: AsyncSession):
    repo = TemplatesRepository(session)
    return await repo.list()


async def get_template(*, session: AsyncSession, template_id: uuid.UUID):
    repo = TemplatesRepository(session)
    return await repo.get(template_id)


async def update_template(
    *,
    session: AsyncSession,
    template_id: uuid.UUID,
    name: str,
    subject: str,
    body: str,
    updated_by: uuid.UUID,
):
    repo = TemplatesRepository(session)
    tpl = await repo.update(template_id, name=name, subject=subject, body=body)

    from app.models.audit_logs import AuditAction

    await _publish_template_audit_event(
        session=session,
        entity_id=tpl.id,
        action=AuditAction.TEMPLATE_UPDATED,
        performed_by=updated_by,
        metadata={
            "template_id": str(tpl.id),
            "template_name": tpl.name,
            "channel": "email",
            "updated_fields": ["name", "subject", "body"],
        },
    )

    return tpl


async def delete_template(*, session: AsyncSession, template_id: uuid.UUID, deleted_by: uuid.UUID):
    repo = TemplatesRepository(session)
    tpl = await repo.get(template_id)

    from app.models.audit_logs import AuditAction

    # Perform delete first, but audit with captured info.
    await repo.delete(template_id)

    await _publish_template_audit_event(
        session=session,
        entity_id=tpl.id,
        action=AuditAction.TEMPLATE_DELETED,
        performed_by=deleted_by,
        metadata={
            "template_id": str(tpl.id),
            "template_name": tpl.name,
            "channel": "email",
        },
    )
    return None


