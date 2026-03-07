import argparse
import json
import os

import psycopg


def get_connection() -> psycopg.Connection:
    # Create a PostgreSQL connection using environment variables with local defaults.
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "chatbotDb"),
        user=os.getenv("POSTGRES_USER", "jose"),
        password=os.getenv("POSTGRES_PASSWORD", "myTheOrganizationPassword"),
    )


def resolve_trace_id(trace_id: str | None) -> str:
    # Use the provided trace ID when available.
    if trace_id:
        return trace_id

    raise ValueError("Provide --trace-id")


def fetch_trace_events(connection: psycopg.Connection, trace_id: str) -> list[dict]:
    # Retrieve all events for one trace in the original conversation order.
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT trace_id, event_index, event_type, payload, created_at
            FROM chatbot_trace_events
            WHERE trace_id = %s
            ORDER BY event_index ASC
            """,
            (trace_id,),
        )
        rows = cursor.fetchall()

    # Convert raw DB rows into JSON-serializable dictionaries for printing.
    events = []
    for trace_id_value, event_index, event_type, payload, created_at in rows:
        events.append(
            {
                "trace_id": trace_id_value,
                "event_index": event_index,
                "event_type": event_type,
                "payload": payload,
                "created_at": created_at.isoformat() if created_at else None,
            }
        )
    return events


def main() -> None:
    # Parse CLI flags so users can request a specific trace.
    parser = argparse.ArgumentParser(description="Show full chatbot trace from PostgreSQL")
    parser.add_argument("--trace-id", help="Trace ID to retrieve")
    args = parser.parse_args()

    # Open DB connection, resolve target trace ID, and print the trace as JSON.
    connection = get_connection()
    try:
        selected_trace_id = resolve_trace_id(trace_id=args.trace_id)
        events = fetch_trace_events(connection=connection, trace_id=selected_trace_id)

        if not events:
            print(json.dumps({"trace_id": selected_trace_id, "events": []}, indent=2))
            return

        # Build one structured JSON payload containing metadata and event list.
        output = {
            "trace_id": selected_trace_id,
            "events_count": len(events),
            "events": events,
        }

        print(json.dumps(output, indent=2, default=str))
    finally:
        # Always close the DB connection before exiting.
        connection.close()


if __name__ == "__main__":
    main()
