from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import create_app
from app.core.config import settings


@pytest.fixture(scope="session")
def test_db_url() -> str:
    # Allows overriding from environment when running tests.
    return os.getenv(
        "TEST_DATABASE_URL",
        settings.database_url,
    )


@pytest.fixture(scope="session")
def event_loop() -> Generator:  # noqa: ANN201
    # pytest-asyncio with asyncio_mode=auto should handle this, but keep compatibility.
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def async_engine(test_db_url: str) -> AsyncEngine:
    return create_async_engine(test_db_url, pool_pre_ping=True)


@pytest.fixture(scope="session")
def async_session_maker(async_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:  # type: ignore[name-defined]
        yield session


@pytest.fixture()
def app() -> FastAPI:
    return create_app()


@pytest.fixture()
def fastapi_app(app: FastAPI) -> FastAPI:
    # override db dependency
    return app


@pytest.fixture()
def _session_override(async_session_maker: async_sessionmaker[AsyncSession]):
    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_maker() as session:
            yield session

    return _get_db_override


@pytest.fixture()
def client_app(app: FastAPI, _session_override):
    app.dependency_overrides[get_db] = _session_override
    return app


@pytest.fixture()
async def client(client_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=client_app, base_url="http://test") as ac:
        yield ac

