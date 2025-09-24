import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from src.main import app
from src.db.main import get_session

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)
TestingSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def override_get_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(init_models())


@pytest.fixture
async def client():
    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
