"""add last_login_at to users

Revision ID: 0015
Revises: 0014
Create Date: 2026-03-26 09:06:24.540953

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_login_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        schema="auth",
    )


def downgrade() -> None:
    op.drop_column("users", "last_login_at", schema="auth")
