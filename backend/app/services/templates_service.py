from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.templates_repo import TemplatesRepository


async def create_template(
    *,
    session: AsyncSession,
    created_by: uuid.UUID,
    name: str,
    subject: str,
    body: str,
):
    repo = TemplatesRepository(session)
    return await repo.create(created_by=created_by, name=name, subject=subject, body=body)


async def list_templates(*, session: AsyncSession):
    repo = TemplatesRepository(session)
    return await repo.list()


async def get_template(*, session: AsyncSession, template_id: uuid.UUID):
    repo = TemplatesRepository(session)
    return await repo.get(template_id)


async def update_template(*, session: AsyncSession, template_id: uuid.UUID, name: str, subject: str, body: str):
    repo = TemplatesRepository(session)
    return await repo.update(template_id, name=name, subject=subject, body=body)


async def delete_template(*, session: AsyncSession, template_id: uuid.UUID):
    repo = TemplatesRepository(session)
    return await repo.delete(template_id)

