"""add_raw_text_to_questions

Revision ID: 10878515b7ca
Revises: c9b9e79f99cb
Create Date: 2026-11-06 11:25:10.887180
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '10878515b7ca'
down_revision: Union[str, None] = 'c9b9e79f99cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("raw_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "raw_text")
