"""
Persistência das preferências de tema do usuário (tabela public.user_preferences).
A tabela é criada por sql/001_user_preferences.sql.
"""
from typing import List

import psycopg


def get_user_topics(conn_str: str, user_id: str) -> List[str]:
    with psycopg.connect(conn_str) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT topics FROM public.user_preferences WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        return list(row[0]) if row and row[0] else []


def set_user_topics(conn_str: str, user_id: str, topics: List[str]) -> List[str]:
    with psycopg.connect(conn_str) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.user_preferences (user_id, topics, updated_at)
            VALUES (%s, %s, now())
            ON CONFLICT (user_id)
            DO UPDATE SET topics = EXCLUDED.topics, updated_at = now()
            RETURNING topics
            """,
            (user_id, topics),
        )
        row = cur.fetchone()
        conn.commit()
        return list(row[0]) if row else []
