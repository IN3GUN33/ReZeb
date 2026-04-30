from collections.abc import AsyncGenerator

import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

settings = get_settings()
TEST_DB_URL = settings.database_url.replace("/rezeb", "/rezeb_test")

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def db_setup() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(db_setup: None) -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
