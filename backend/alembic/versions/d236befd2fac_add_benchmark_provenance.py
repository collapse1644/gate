"""add_benchmark_provenance

Revision ID: d236befd2fac
Revises: 10878515b7ca
Create Date: 2026-11-06 11:31:31.739594
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd236befd2fac'
down_revision: Union[str, None] = '10878515b7ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("classification_benchmark", sa.Column("label_source", sa.String(32), nullable=False, server_default="ai_assisted"))
    op.add_column("classification_benchmark", sa.Column("reviewer", sa.String(120), nullable=True))
    op.add_column("classification_benchmark", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("classification_benchmark", "reviewed_at")
    op.drop_column("classification_benchmark", "reviewer")
    op.drop_column("classification_benchmark", "label_source")
