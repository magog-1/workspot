"""init — create users, spaces, timeslots, bookings tables

Revision ID: 5b305518b9c4
Revises: 
Create Date: 2026-03-07 05:59:28.089023

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b305518b9c4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables using raw SQL to bypass SQLAlchemy type events."""

    # ------------------------------------------------------------------
    # Enums — DO block is idempotent and works with asyncpg
    # ------------------------------------------------------------------
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('user', 'admin');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """))
    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE bookingstatus AS ENUM ('active', 'cancelled');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """))

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS users (
            id          UUID         PRIMARY KEY,
            email       VARCHAR(255) NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            name        VARCHAR(255) NOT NULL,
            role        userrole     NOT NULL DEFAULT 'user',
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """))
    op.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)"
    ))

    # ------------------------------------------------------------------
    # spaces
    # ------------------------------------------------------------------
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS spaces (
            id             UUID           PRIMARY KEY,
            name           VARCHAR(255)   NOT NULL,
            address        VARCHAR(500)   NOT NULL,
            city           VARCHAR(100)   NOT NULL DEFAULT 'Москва',
            description    TEXT,
            price_per_hour NUMERIC(10,2)  NOT NULL,
            capacity       INTEGER        NOT NULL,
            amenities      TEXT[]         NOT NULL DEFAULT '{}',
            latitude       DOUBLE PRECISION,
            longitude      DOUBLE PRECISION,
            photos         TEXT[]         NOT NULL DEFAULT '{}',
            created_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW()
        )
    """))

    # ------------------------------------------------------------------
    # timeslots
    # ------------------------------------------------------------------
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS timeslots (
            id        UUID    PRIMARY KEY,
            space_id  UUID    NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
            date      DATE    NOT NULL,
            time_from TIME    NOT NULL,
            time_to   TIME    NOT NULL,
            is_booked BOOLEAN NOT NULL DEFAULT FALSE
        )
    """))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_timeslots_space_id ON timeslots(space_id)"
    ))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_timeslots_date ON timeslots(date)"
    ))

    # ------------------------------------------------------------------
    # bookings
    # ------------------------------------------------------------------
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS bookings (
            id         UUID          PRIMARY KEY,
            user_id    UUID          NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
            space_id   UUID          NOT NULL REFERENCES spaces(id)    ON DELETE CASCADE,
            slot_id    UUID          NOT NULL REFERENCES timeslots(id) ON DELETE CASCADE,
            status     bookingstatus NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_booking_slot UNIQUE (slot_id)
        )
    """))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_bookings_user_id  ON bookings(user_id)"
    ))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_bookings_space_id ON bookings(space_id)"
    ))


def downgrade() -> None:
    """Drop all initial tables."""
    op.execute(sa.text("DROP TABLE IF EXISTS bookings"))
    op.execute(sa.text("DROP INDEX  IF EXISTS ix_timeslots_date"))
    op.execute(sa.text("DROP INDEX  IF EXISTS ix_timeslots_space_id"))
    op.execute(sa.text("DROP TABLE  IF EXISTS timeslots"))
    op.execute(sa.text("DROP TABLE  IF EXISTS spaces"))
    op.execute(sa.text("DROP INDEX  IF EXISTS ix_users_email"))
    op.execute(sa.text("DROP TABLE  IF EXISTS users"))
    op.execute(sa.text("DROP TYPE   IF EXISTS bookingstatus"))
    op.execute(sa.text("DROP TYPE   IF EXISTS userrole"))
