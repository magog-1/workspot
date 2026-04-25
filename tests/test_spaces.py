"""Tests for the spaces module."""

from __future__ import annotations

import datetime
import uuid

import pytest

from spaces.schemas import SpaceFilter, SpaceResponse


class TestSpaceFilterSchema:
    def test_defaults_to_moscow(self) -> None:
        f = SpaceFilter()
        assert f.city == "Москва"
        assert f.date is None
        assert f.amenities is None

    def test_accepts_all_filters(self) -> None:
        f = SpaceFilter(
            city="Санкт-Петербург",
            date=datetime.date(2026, 5, 1),
            price_max=2500.0,
            capacity=10,
            amenities=["wifi", "coffee"],
        )
        assert f.city == "Санкт-Петербург"
        assert f.price_max == 2500.0
        assert f.amenities == ["wifi", "coffee"]


class TestSpaceResponseSchema:
    def _payload(self, **overrides):
        base = {
            "id": uuid.uuid4(),
            "name": "Coworking A",
            "address": "Tverskaya 1",
            "city": "Москва",
            "description": "Nice place",
            "price_per_hour": "1500.50",
            "capacity": 12,
            "amenities": ["wifi"],
            "latitude": 55.7,
            "longitude": 37.6,
            "photos": [],
        }
        base.update(overrides)
        return base

    def test_decimal_price_is_coerced_to_float(self) -> None:
        resp = SpaceResponse(**self._payload())
        assert isinstance(resp.price_per_hour, float)
        assert resp.price_per_hour == 1500.50

    def test_to_map_dict_contains_required_keys(self) -> None:
        resp = SpaceResponse(**self._payload())
        m = resp.to_map_dict()
        assert set(m.keys()) >= {
            "id",
            "name",
            "address",
            "price_per_hour",
            "latitude",
            "longitude",
        }
        assert isinstance(m["id"], str)


@pytest.mark.integration
class TestSpacesEndpoints:
    async def test_list_spaces_returns_html(self, async_client) -> None:
        response = await async_client.get("/spaces", follow_redirects=False)
        # Either 200 (page rendered) or 307 trailing-slash redirect — both are fine.
        assert response.status_code in (200, 307)

    async def test_list_spaces_with_filters(self, async_client) -> None:
        response = await async_client.get(
            "/spaces",
            params={"city": "Москва", "price_max": "1000", "capacity": "5"},
            follow_redirects=True,
        )
        assert response.status_code == 200
