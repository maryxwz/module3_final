from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '[будет автоматически создан]'
down_revision: str = '06ce698f9f32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO chats (subject_id, name, is_group)
        SELECT 
            s.id,
            s.title || ' Chat',
            TRUE
        FROM subjects s
        LEFT JOIN chats c ON s.id = c.subject_id
        WHERE c.id IS NULL;
    """)

    op.execute("""
        INSERT INTO chat_participants (chat_id, user_id)
        SELECT 
            c.id,
            s.teacher_id
        FROM chats c
        JOIN subjects s ON c.subject_id = s.id
        LEFT JOIN chat_participants cp ON c.id = cp.chat_id AND s.teacher_id = cp.user_id
        WHERE cp.id IS NULL;
    """)


def downgrade() -> None:
    pass
