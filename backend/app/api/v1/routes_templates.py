from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.schemas.templates import TemplateCreateRequest, TemplateResponse, TemplateUpdateRequest
from app.schemas.auth import UserPublic
from app.services.templates_service import create_template, delete_template, get_template, list_templates, update_template

router = APIRouter()


@router.post("")
async def create(req: TemplateCreateRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    tpl = await create_template(
        session=session,
        created_by=current_user.id,
        name=req.name,
        subject=req.subject,
        body=req.body,
    )
    return {"success": True, "data": TemplateResponse(**{ 
        "id": tpl.id,
        "name": tpl.name,
        "subject": tpl.subject,
        "body": tpl.body,
        "created_by": tpl.created_by,
    }).model_dump()}


@router.get("")
async def list_(session: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    tpl_list = await list_templates(session=session)
    data = [
        TemplateResponse(
            id=tpl.id,
            name=tpl.name,
            subject=tpl.subject,
            body=tpl.body,
            created_by=tpl.created_by,
        ).model_dump()
        for tpl in tpl_list
    ]
    return {"success": True, "data": data}


@router.get("/{template_id}")
async def get(template_id: uuid.UUID, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    tpl = await get_template(session=session, template_id=template_id)
    return {"success": True, "data": TemplateResponse(
        id=tpl.id,
        name=tpl.name,
        subject=tpl.subject,
        body=tpl.body,
        created_by=tpl.created_by,
    ).model_dump()}


@router.put("/{template_id}")
async def update(
    template_id: uuid.UUID,
    req: TemplateUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tpl = await update_template(session=session, template_id=template_id, name=req.name, subject=req.subject, body=req.body)
    return {"success": True, "data": TemplateResponse(
        id=tpl.id,
        name=tpl.name,
        subject=tpl.subject,
        body=tpl.body,
        created_by=tpl.created_by,
    ).model_dump()}


@router.delete("/{template_id}")
async def delete(template_id: uuid.UUID, session: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await delete_template(session=session, template_id=template_id)
    return {"success": True, "data": {}}

