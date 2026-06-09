from __future__ import annotations

import uuid

from pydantic import BaseModel


class TemplateBase(BaseModel):
    name: str
    subject: str
    body: str


class TemplateCreateRequest(TemplateBase):
    pass


class TemplateUpdateRequest(TemplateBase):
    pass


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    subject: str
    body: str
    created_by: uuid.UUID


