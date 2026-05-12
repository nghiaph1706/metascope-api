"""Tests for meta router endpoints."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestMetaRouter:
    """Tests for /api/v1/meta endpoints."""

    @pytest.mark.asyncio
    async def test_calculate_stats_returns_result(self) -> None:
        """POST /calculate-stats dispatches to stats_service."""

        async def mock_calculate_all_stats(*args, **kwargs):
            return {
                "champions": {"patch": "14.1", "champions": 5},
                "items": {"patch": "14.1", "items": 10},
                "augments": {"patch": "14.1", "augments": 3},
            }

        async def mock_cache_delete(pattern):
            pass

        with patch("app.meta.router.cache.cache_delete_pattern", side_effect=mock_cache_delete):
            with patch(
                "app.meta.router.stats_service.calculate_all_stats",
                side_effect=mock_calculate_all_stats,
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.post("/api/v1/meta/calculate-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["champions"]["champions"] == 5
        assert data["items"]["items"] == 10
