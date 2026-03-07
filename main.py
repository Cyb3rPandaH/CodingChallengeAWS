import argparse
import uuid

from the_organization_chatbot.application.chatbot import TheOrganizationChatbot
from the_organization_chatbot.infrastructure.tracing import PostgresConversationTracer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the organization chatbot in terminal")
    parser.add_argument("--model", help="Model name (for example: gpt-5-mini)")
    parser.add_argument("--temperature", type=float, help="Model temperature")
    args = parser.parse_args()

    # A single trace ID is generated once per terminal run and reused for all events in that conversation.
    trace_id = str(uuid.uuid4())
    tracer = PostgresConversationTracer(trace_id=trace_id)
    tracer.log_event(
        event_type="session_start",
        payload={
            "trace_id": trace_id,
            "model": args.model,
            "temperature": args.temperature,
        },
    )

    chatbot = TheOrganizationChatbot(
        model=args.model,
        temperature=args.temperature,
        trace_id=trace_id,
        tracer=tracer,
    )

    print(f"the organization Chatbot (type 'exit' to quit) | trace_id={trace_id}")
    print(f"Model: {chatbot.model_name}")

    try:
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting chatbot.")
                tracer.log_event(
                    event_type="session_end",
                    payload={
                        "trace_id": trace_id,
                        "reason": "keyboard_interrupt_or_eof",
                    },
                )
                break

            if user_input.lower() in {"exit", "quit", "q"}:
                print("Exiting chatbot.")
                tracer.log_event(
                    event_type="session_end",
                    payload={
                        "trace_id": trace_id,
                        "reason": "user_exit",
                    },
                )
                break

            if not user_input:
                continue

            try:
                response = chatbot.generate_response(user_input)
                content = getattr(response, "content", response)
                print(f"Assistant: {content}")
            except Exception as error:
                tracer.log_event(
                    event_type="assistant_error",
                    payload={
                        "trace_id": trace_id,
                        "error": str(error),
                    },
                )
                print(f"Assistant Error: {error}")
    finally:
        tracer.close()


if __name__ == "__main__":
    main()
