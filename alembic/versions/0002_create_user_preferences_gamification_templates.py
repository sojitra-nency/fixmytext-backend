"""create user_preferences, user_gamification, user_templates tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-16 13:15:33.828499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_gamification',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('xp', sa.Integer(), nullable=False),
    sa.Column('streak_current', sa.Integer(), nullable=False),
    sa.Column('streak_last_date', sa.String(length=10), nullable=True),
    sa.Column('total_ops', sa.Integer(), nullable=False),
    sa.Column('total_chars', sa.Integer(), nullable=False),
    sa.Column('tools_used', sa.Text(), nullable=False),
    sa.Column('discovered_tools', sa.Text(), nullable=False),
    sa.Column('achievements', sa.Text(), nullable=False),
    sa.Column('favorites', sa.Text(), nullable=False),
    sa.Column('saved_pipelines', sa.Text(), nullable=False),
    sa.Column('completed_quests', sa.Text(), nullable=False),
    sa.Column('daily_quest_id', sa.String(length=50), nullable=True),
    sa.Column('daily_quest_date', sa.String(length=10), nullable=True),
    sa.Column('daily_quest_completed', sa.Boolean(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('user_preferences',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('theme', sa.String(length=10), nullable=False),
    sa.Column('persona', sa.String(length=50), nullable=True),
    sa.Column('theme_skin', sa.String(length=50), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('user_templates',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('user_templates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_templates_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('user_templates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_templates_user_id'))

    op.drop_table('user_templates')
    op.drop_table('user_preferences')
    op.drop_table('user_gamification')
