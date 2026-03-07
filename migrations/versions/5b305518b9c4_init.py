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
    """Create all initial tables."""

    # ------------------------------------------------------------------
    # Enums
    # ------------------------------------------------------------------
    userrole = sa.Enum("user", "admin", name="userrole")
    bookingstatus = sa.Enum("active", "cancelled", name="bookingstatus")
    userrole.create(op.get_bind(), checkfirst=True)
    bookingstatus.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "admin", name="userrole", create_type=False),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # spaces
    # ------------------------------------------------------------------
    op.create_table(
        "spaces",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("city", sa.String(100), nullable=False, server_default="Москва"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price_per_hour", sa.Numeric(10, 2), nullable=False),
        sa.Column("capacity", sa.Integer, nullable=False),
        sa.Column(
            "amenities",
            sa.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column(
            "photos",
            sa.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ------------------------------------------------------------------
    # timeslots
    # ------------------------------------------------------------------
    op.create_table(
        "timeslots",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "space_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("time_from", sa.Time, nullable=False),
        sa.Column("time_to", sa.Time, nullable=False),
        sa.Column("is_booked", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_timeslots_space_id", "timeslots", ["space_id"])
    op.create_index("ix_timeslots_date", "timeslots", ["date"])

    # ------------------------------------------------------------------
    # bookings
    # ------------------------------------------------------------------
    op.create_table(
        "bookings",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "space_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "slot_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("timeslots.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "cancelled", name="bookingstatus", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slot_id", name="uq_booking_slot"),
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])
    op.create_index("ix_bookings_space_id", "bookings", ["space_id"])


def downgrade() -> None:
    """Drop all initial tables."""
    op.drop_table("bookings")
    op.drop_index("ix_timeslots_date", "timeslots")
    op.drop_index("ix_timeslots_space_id", "timeslots")
    op.drop_table("timeslots")
    op.drop_table("spaces")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")

    sa.Enum(name="bookingstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
