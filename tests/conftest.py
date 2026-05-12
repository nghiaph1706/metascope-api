"""Shared pytest fixtures."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.main import app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings override cho test environment."""
    return Settings(
        environment="test",
        riot_api_key="RGAPI-test-key-not-real",
        database_url="postgresql+asyncpg://metascope:metascope@localhost:5432/metascope_test",
        sync_database_url="postgresql://metascope:metascope@localhost:5432/metascope_test",
        redis_url="redis://localhost:6379/15",
        log_level="WARNING",
    )


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Async DB session with rollback after each test."""
    engine = create_async_engine(
        "postgresql+asyncpg://metascope:metascope@localhost:5432/metascope_test",
        echo=False,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """Async HTTP client for testing FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_riot_client() -> MagicMock:
    """Mock RiotClient for unit tests."""
    client = MagicMock()
    client.get_account_by_riot_id = AsyncMock()
    client.get_tft_match_list = AsyncMock()
    client.get_match_detail = AsyncMock()
    return client


@pytest.fixture
def sample_summoner_response() -> dict:
    """Sample Riot Account API response."""
    return {
        "puuid": "Cst5vZKHi4Pxj_XDzFJjj_aAbkPcNKRnXbD3JvUhAH2EAlM7bMQsF2Q_TEST",
        "gameName": "TestPlayer",
        "tagLine": "VN2",
    }


@pytest.fixture
def sample_match_response() -> dict:
    """Sample Riot TFT Match API response."""
    return {
        "metadata": {
            "data_version": "5",
            "match_id": "VN2_123456789",
            "participants": ["Cst5vZKHi4Pxj_TEST"],
        },
        "info": {
            "game_datetime": 1705312200000,
            "game_length": 1823.5,
            "game_variation": "",
            "queue_id": 1100,
            "tft_set_number": 13,
            "tft_set_core_name": "TFTSet13",
            "participants": [
                {
                    "puuid": "Cst5vZKHi4Pxj_TEST",
                    "placement": 1,
                    "level": 9,
                    "gold_left": 12,
                    "last_round": 28,
                    "players_eliminated": 3,
                    "total_damage_to_players": 187,
                    "time_eliminated": 1823.5,
                    "augments": ["TFT13_Augment_SpellBlade2"],
                    "traits": [
                        {
                            "name": "Set13_Void",
                            "num_units": 4,
                            "style": 3,
                            "tier_current": 3,
                            "tier_total": 3,
                        }
                    ],
                    "units": [
                        {
                            "character_id": "TFT13_Yone",
                            "itemNames": ["TFT_Item_Bloodthirster", "TFT_Item_GuinsoosRageblade"],
                            "name": "",
                            "rarity": 3,
                            "tier": 2,
                        }
                    ],
                }
            ],
        },
    }


@pytest.fixture
def sample_match_id_list() -> list[str]:
    """Sample match ID list."""
    return [
        "VN2_123456789",
        "VN2_123456790",
        "VN2_123456791",
    ]
