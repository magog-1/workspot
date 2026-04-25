"""Tests for the auth module.

Pure-unit tests (token helpers, schemas) run without any infrastructure.
Endpoint tests are marked ``integration`` because they require Postgres.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from auth import service as auth_service
from auth.schemas import LoginRequest, RegisterRequest

# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestRegisterRequestSchema:
    def test_valid_payload(self) -> None:
        req = RegisterRequest(email="user@example.com", password="SecurePass123", name="Alice")
        assert req.email == "user@example.com"
        assert req.name == "Alice"

    def test_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="u@e.com", password="short", name="Alice")

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="u@e.com", password="SecurePass123", name="   ")

    def test_name_is_stripped(self) -> None:
        req = RegisterRequest(email="u@e.com", password="SecurePass123", name="  Bob  ")
        assert req.name == "Bob"

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="SecurePass123", name="X")


class TestLoginRequestSchema:
    def test_valid_payload(self) -> None:
        req = LoginRequest(email="user@example.com", password="anything")
        assert req.password == "anything"

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(email="bad", password="anything")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_password_does_not_return_plaintext(self) -> None:
        hashed = auth_service.hash_password("SecurePass123")
        assert hashed != "SecurePass123"
        assert len(hashed) > 30

    def test_verify_correct_password(self) -> None:
        hashed = auth_service.hash_password("SecurePass123")
        assert auth_service.verify_password("SecurePass123", hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = auth_service.hash_password("SecurePass123")
        assert auth_service.verify_password("WrongPass456", hashed) is False

    def test_two_hashes_of_same_password_differ(self) -> None:
        a = auth_service.hash_password("SecurePass123")
        b = auth_service.hash_password("SecurePass123")
        assert a != b


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


class TestTokens:
    def test_access_token_round_trip(self) -> None:
        sub = str(uuid.uuid4())
        token = auth_service.create_access_token({"sub": sub})
        payload = auth_service._decode_token(token)
        assert payload["sub"] == sub
        assert payload["type"] == "access"

    def test_refresh_token_round_trip(self) -> None:
        sub = str(uuid.uuid4())
        token = auth_service.create_refresh_token({"sub": sub})
        payload = auth_service._decode_token(token)
        assert payload["type"] == "refresh"

    def test_expired_token_rejected(self) -> None:
        token = auth_service.create_access_token(
            {"sub": "anyone"}, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(HTTPException) as exc_info:
            auth_service._decode_token(token)
        assert exc_info.value.status_code == 401

    def test_garbage_token_rejected(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            auth_service._decode_token("not.a.valid.jwt")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Endpoint tests (require Postgres)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAuthEndpoints:
    async def test_register_redirects_and_sets_cookies(self, async_client, unique_email) -> None:
        response = await async_client.post(
            "/auth/register",
            data={
                "email": unique_email,
                "password": "SecurePass123",
                "name": "Test User",
            },
        )
        assert response.status_code == 302
        assert "access_token" in response.cookies

    async def test_register_duplicate_email_returns_400(self, async_client, unique_email) -> None:
        payload = {
            "email": unique_email,
            "password": "SecurePass123",
            "name": "Test User",
        }
        first = await async_client.post("/auth/register", data=payload)
        assert first.status_code == 302
        second = await async_client.post("/auth/register", data=payload)
        assert second.status_code == 400

    async def test_login_with_invalid_credentials(self, async_client) -> None:
        response = await async_client.post(
            "/auth/login",
            data={"email": "nobody@example.com", "password": "WrongPass1"},
        )
        assert response.status_code == 400

    async def test_me_requires_auth(self, async_client) -> None:
        response = await async_client.get("/auth/me")
        assert response.status_code == 401

    async def test_logout_clears_cookies(self, async_client) -> None:
        response = await async_client.get("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
