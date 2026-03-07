import os
from typing import Any

import psycopg
from psycopg.types.json import Json


class PostgresConversationTracer:
    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self.event_index = 0
        self.enabled = True
        self.connection = None

        self._connect()

    def _connect(self) -> None:
        if not self.enabled:
            return

        try:
            self.connection = psycopg.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=os.getenv("POSTGRES_DB", "chatbotDb"),
                user=os.getenv("POSTGRES_USER", "jose"),
                password=os.getenv("POSTGRES_PASSWORD", "myTheOrganizationPassword"),
                autocommit=True,
            )
        except Exception as error:
            self.enabled = False
            self.connection = None
            print(f"Tracing disabled: could not connect to PostgreSQL ({error})")

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if not self.enabled or self.connection is None:
            return

        self.event_index += 1

        insert_sql = """
        INSERT INTO chatbot_trace_events (trace_id, event_index, event_type, payload)
        VALUES (%s, %s, %s, %s)
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    insert_sql,
                    (self.trace_id, self.event_index, event_type, Json(payload)),
                )
        except Exception as error:
            self.enabled = False
            print(f"Tracing disabled: failed to write trace event ({error})")

    def close(self) -> None:
        if self.connection is None:
            return

        try:
            self.connection.close()
        except Exception:
            pass
