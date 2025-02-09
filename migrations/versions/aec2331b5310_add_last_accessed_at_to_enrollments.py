"""Add last_accessed_at to enrollments

Revision ID: aec2331b5310
Revises: fe8102419bc3
Create Date: 2025-02-09 17:43:47.774499

"""
from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# Ідентифікатор цієї міграції
revision: str = 'aec2331b5310'
down_revision: Union[str, None] = 'fe8102419bc3'

def upgrade():
    # Видаляємо зовнішній ключ з таблиці grades
    op.drop_constraint('grades_task_upload_id_fkey', 'grades', type_='foreignkey')

    # Видаляємо саму таблицю task_uploads
    op.drop_table('task_uploads')

def downgrade():
    # Відновлюємо таблицю task_uploads
    op.create_table(
        'task_uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Відновлюємо зовнішній ключ у grades
    op.create_foreign_key(
        'grades_task_upload_id_fkey', 'grades', 'task_uploads',
        ['task_upload_id'], ['id'], ondelete='CASCADE'
    )
