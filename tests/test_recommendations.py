"""Unit-style tests for the recommendations helper using mocked DB."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest


class _Row:
    def __init__(self, *values):
        self._values = values

    def __getitem__(self, idx):
        return self._values[idx]


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class _Result:
    def __init__(self, rows=None, scalars=None):
        self._rows = rows or []
        self._scalars = scalars or []

    def all(self):
        return list(self._rows)

    def scalars(self):
        return _ScalarResult(self._scalars)


class _Space:
    def __init__(self, sid):
        self.id = sid
        self.created_at = 0


def _make_db(execute_results):
    db = AsyncMock()
    iterator = iter(execute_results)

    async def _execute(_stmt):
        return next(iterator)

    db.execute.side_effect = _execute
    return db


@pytest.mark.asyncio
async def test_get_recommendations_falls_back_for_new_user():
    from spaces.recommendations import get_recommendations

    user_id = uuid.uuid4()
    s1, s2 = uuid.uuid4(), uuid.uuid4()
    other = uuid.uuid4()

    # 1. _all_bookings — current user has no rows
    rows = [(other, s1), (other, s2)]
    # 2. _popular_spaces: select space_id rows (for Counter)
    popular_rows = [(s1,), (s1,), (s2,)]
    # 3. _popular_spaces: select Space.id.in_(top_ids)
    popular_spaces = _Result(scalars=[_Space(s1), _Space(s2)])
    # 4. _popular_spaces fallback newest
    newest_spaces = _Result(scalars=[])

    db = _make_db(
        [
            _Result(rows=rows),
            _Result(rows=popular_rows),
            popular_spaces,
            newest_spaces,
        ]
    )

    result = await get_recommendations(user_id, db, limit=3)
    assert [s.id for s in result] == [s1, s2]


@pytest.mark.asyncio
async def test_get_recommendations_from_neighbours():
    from spaces.recommendations import get_recommendations

    me = uuid.uuid4()
    neighbour = uuid.uuid4()
    s1, s2, s3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    # me booked s1; neighbour booked s1, s2, s3 → recommend s2, s3 (limit=2)
    rows = [(me, s1), (neighbour, s1), (neighbour, s2), (neighbour, s3)]
    candidate_spaces = _Result(scalars=[_Space(s2), _Space(s3)])

    db = _make_db([_Result(rows=rows), candidate_spaces])

    result = await get_recommendations(me, db, limit=2)
    ids = [s.id for s in result]
    assert s2 in ids and s3 in ids
    assert s1 not in ids  # already booked by me
