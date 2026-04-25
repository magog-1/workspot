"""Tests for the bookings module."""

from __future__ import annotations

import uuid

import pytest

from bookings.models import BookingStatus
from bookings.schemas import BookingCreate


class TestBookingSchemas:
    def test_booking_create_accepts_uuid(self) -> None:
        slot_id = uuid.uuid4()
        bc = BookingCreate(slot_id=slot_id)
        assert bc.slot_id == slot_id


class TestBookingStatusEnum:
    def test_active_value(self) -> None:
        assert BookingStatus.active.value == "active"

    def test_cancelled_value(self) -> None:
        assert BookingStatus.cancelled.value == "cancelled"

    def test_status_is_string_enum(self) -> None:
        assert BookingStatus.active == "active"


@pytest.mark.integration
class TestBookingsEndpoints:
    async def test_create_booking_requires_auth(self, async_client) -> None:
        response = await async_client.post("/bookings", data={"slot_id": str(uuid.uuid4())})
        assert response.status_code == 401

    async def test_my_bookings_requires_auth(self, async_client) -> None:
        response = await async_client.get("/bookings/my")
        assert response.status_code == 401

    async def test_cancel_booking_requires_auth(self, async_client) -> None:
        response = await async_client.post(f"/bookings/{uuid.uuid4()}/cancel")
        assert response.status_code == 401

    async def test_delete_booking_requires_auth(self, async_client) -> None:
        response = await async_client.delete(f"/bookings/{uuid.uuid4()}")
        assert response.status_code == 401
