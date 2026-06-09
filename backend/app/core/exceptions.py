from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.response import error_response


class AppError(Exception):
    status_code: int = 400
    message: str = "Application error"


@dataclass(frozen=True)
class NotFoundError(AppError):
    message: str = "Not found"
    status_code: int = 404


@dataclass(frozen=True)
class ConflictError(AppError):
    message: str = "Conflict"
    status_code: int = 409


@dataclass(frozen=True)
class AuthError(AppError):
    message: str = "Unauthorized"
    status_code: int = 401


@dataclass(frozen=True)
class BadRequestError(AppError):
    message: str = "Bad request"
    status_code: int = 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_response(exc.message))

    @app.exception_handler(PydanticValidationError)
    async def pydantic_error_handler(_: Request, exc: PydanticValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content=error_response(str(exc)))

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        # Avoid leaking internals in production; keep message generic.
        return JSONResponse(status_code=500, content=error_response("Internal server error"))

