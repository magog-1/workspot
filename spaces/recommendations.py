"""Simplified user-based KNN recommender for spaces."""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookings.models import Booking, BookingStatus
from spaces.models import Space


async def _all_bookings(db: AsyncSession) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """Return list of (user_id, space_id) for active bookings."""
    result = await db.execute(
        select(Booking.user_id, Booking.space_id).where(
            Booking.status == BookingStatus.active
        )
    )
    return [(row[0], row[1]) for row in result.all()]


async def _popular_spaces(db: AsyncSession, limit: int = 3) -> list[Space]:
    """Top spaces by number of active bookings; falls back to newest spaces."""
    result = await db.execute(
        select(Booking.space_id).where(Booking.status == BookingStatus.active)
    )
    counts = Counter(row[0] for row in result.all())
    top_ids = [sid for sid, _ in counts.most_common(limit)]
    spaces: list[Space] = []
    if top_ids:
        res = await db.execute(select(Space).where(Space.id.in_(top_ids)))
        spaces = list(res.scalars().all())
        spaces.sort(key=lambda s: top_ids.index(s.id))
    if len(spaces) < limit:
        existing = {s.id for s in spaces}
        res = await db.execute(
            select(Space).order_by(Space.created_at.desc()).limit(limit * 2)
        )
        for sp in res.scalars().all():
            if sp.id in existing:
                continue
            spaces.append(sp)
            if len(spaces) >= limit:
                break
    return spaces[:limit]


async def get_recommendations(
    user_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 3,
) -> list[Space]:
    """Recommend up to ``limit`` spaces for ``user_id``.

    Algorithm:
      1. Build user → set(space) map from active bookings.
      2. If user has no history → return popular spaces.
      3. Otherwise: pick top-5 neighbours by Jaccard similarity (intersection
         size), aggregate their bookings (excluding current user's history),
         return the ``limit`` most frequently booked.
    """
    rows = await _all_bookings(db)
    user_to_spaces: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for uid, sid in rows:
        user_to_spaces[uid].add(sid)

    my_spaces = user_to_spaces.get(user_id, set())
    if not my_spaces:
        return await _popular_spaces(db, limit)

    # Find top-5 similar users by overlap size.
    scored: list[tuple[uuid.UUID, int]] = []
    for other_id, other_spaces in user_to_spaces.items():
        if other_id == user_id:
            continue
        overlap = len(my_spaces & other_spaces)
        if overlap > 0:
            scored.append((other_id, overlap))
    scored.sort(key=lambda x: x[1], reverse=True)
    neighbours = [uid for uid, _ in scored[:5]]

    if not neighbours:
        return await _popular_spaces(db, limit)

    # Aggregate candidate spaces from neighbours, exclude already-booked.
    candidate_counts: Counter[uuid.UUID] = Counter()
    for nid in neighbours:
        for sid in user_to_spaces[nid]:
            if sid in my_spaces:
                continue
            candidate_counts[sid] += 1

    if not candidate_counts:
        return await _popular_spaces(db, limit)

    top_ids = [sid for sid, _ in candidate_counts.most_common(limit)]
    res = await db.execute(select(Space).where(Space.id.in_(top_ids)))
    spaces = list(res.scalars().all())
    spaces.sort(key=lambda s: top_ids.index(s.id))

    # Pad with popular if we don't have enough.
    if len(spaces) < limit:
        existing = {s.id for s in spaces}
        for sp in await _popular_spaces(db, limit * 2):
            if sp.id in existing or sp.id in my_spaces:
                continue
            spaces.append(sp)
            if len(spaces) >= limit:
                break
    return spaces[:limit]
