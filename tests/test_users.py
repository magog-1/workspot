"""Tests for the users module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from users.schemas import UserUpdate


class TestUserUpdateSchema:
    def test_all_fields_optional(self) -> None:
        u = UserUpdate()
        assert u.name is None
        assert u.email is None

    def test_partial_update(self) -> None:
        u = UserUpdate(name="New Name")
        assert u.name == "New Name"
        assert u.email is None

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdate(email="not-an-email")


@pytest.mark.integration
class TestUsersEndpoints:
    async def test_users_me_requires_auth(self, async_client) -> None:
        response = await async_client.get("/users/me")
        assert response.status_code == 401

    async def test_patch_users_me_requires_auth(self, async_client) -> None:
        response = await async_client.patch("/users/me", json={"name": "New"})
        assert response.status_code == 401

    async def test_profile_page_requires_auth(self, async_client) -> None:
        response = await async_client.get("/profile", follow_redirects=False)
        # redirected to login or 401
        assert response.status_code in (302, 401)
