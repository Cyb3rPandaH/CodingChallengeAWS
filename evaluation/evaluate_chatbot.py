import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

from langchain_openai import ChatOpenAI

# Ensure project root is importable when running this file directly.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from the_organization_chatbot.application.chatbot import TheOrganizationChatbot
from the_organization_chatbot.infrastructure.tracing import PostgresConversationTracer


# Load the evaluation dataset from JSON.
# Each item is expected to include: id, type, question, and ground_truth.
def load_eval_set(eval_set_path: Path) -> list[dict]:
    with eval_set_path.open("r", encoding="utf-8") as file:
        return json.load(file)


# Normalize model/library outputs to plain text.
# Some LangChain responses expose the answer in `.content`.
def to_text(response) -> str:
    return str(getattr(response, "content", response)).strip()


# Safely convert values to float and clamp to a valid range.
# This protects metric aggregation from malformed judge outputs.
def _to_float_in_range(value, min_value: float, max_value: float, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default

    if numeric < min_value:
        return min_value
    if numeric > max_value:
        return max_value
    return numeric


# Ask the judge model to evaluate one chatbot answer.
# Returns both correctness and quality dimensions.
def judge_answer(judge_chat: ChatOpenAI, question: str, ground_truth: str, chatbot_answer: str) -> dict:
    judge_prompt = f"""
You are an evaluation judge.

Step 1: Determine correctness by comparing the chatbot answer with ground truth.
Step 2: Score response quality.

Question:
{question}

Ground truth:
{ground_truth}

Chatbot answer:
{chatbot_answer}

Respond only as strict JSON with this schema:
{{
  "verdict": "correct|partially_correct|incorrect",
    "reason": "short explanation",
    "relevance": 0,
    "coherence": 0,
    "conciseness": 0
}}

Quality scoring rules:
- relevance: 1-5
- coherence: 1-5
- conciseness: 1-5
""".strip()

    raw = to_text(judge_chat.invoke(judge_prompt))

    # Parse judge response as strict JSON. If parsing fails, mark as incorrect.
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "verdict": "incorrect",
            "score": 0.0,
            "reason": f"Judge output was not valid JSON: {raw}",
        }

    verdict = parsed.get("verdict", "incorrect")
    if verdict not in {"correct", "partially_correct", "incorrect"}:
        verdict = "incorrect"

    # Map textual verdict to a numeric correctness score.
    if verdict == "correct":
        correctness_score = 1.0
    elif verdict == "partially_correct":
        correctness_score = 0.5
    else:
        correctness_score = 0.0

    relevance = _to_float_in_range(parsed.get("relevance", 0), 0, 5, 0)
    coherence = _to_float_in_range(parsed.get("coherence", 0), 0, 5, 0)
    conciseness = _to_float_in_range(parsed.get("conciseness", 0), 0, 5, 0)

    return {
        "verdict": verdict,
        "correctness_score": correctness_score,
        "reason": parsed.get("reason", ""),
        "relevance": relevance,
        "coherence": coherence,
        "conciseness": conciseness,
        "raw_judge_output": raw,
    }


# Aggregate metrics overall and by question type.
# Accuracy uses correctness_score where correct=1, partial=0.5, incorrect=0.
def _aggregate_metrics(results: list[dict]) -> dict:
    # Compute summary metrics for a subset of results.
    def build_metrics(items: list[dict]) -> dict:
        count = len(items)
        if count == 0:
            return {
                "count": 0,
                "accuracy_pct": 0.0,
                "correct_count": 0,
                "partially_correct_count": 0,
                "incorrect_count": 0,
                "avg_latency_ms": 0.0,
                "avg_llm_rounds": 0.0,
                "avg_relevance": 0.0,
                "avg_coherence": 0.0,
                "avg_conciseness": 0.0,
            }

        correctness_total = 0.0
        correct_count = 0
        partially_correct_count = 0
        incorrect_count = 0
        latency_total = 0.0
        llm_rounds_total = 0.0
        relevance_total = 0.0
        coherence_total = 0.0
        conciseness_total = 0.0

        for item in items:
            judgment = item.get("judgment", {})
            verdict = judgment.get("verdict", "incorrect")

            correctness_total += float(judgment.get("correctness_score", 0.0))
            latency_total += float(item.get("latency_ms", 0.0))
            llm_rounds_total += float(item.get("llm_rounds", 0.0))
            relevance_total += float(judgment.get("relevance", 0.0))
            coherence_total += float(judgment.get("coherence", 0.0))
            conciseness_total += float(judgment.get("conciseness", 0.0))

            if verdict == "correct":
                correct_count += 1
            elif verdict == "partially_correct":
                partially_correct_count += 1
            else:
                incorrect_count += 1

        return {
            "count": count,
            "accuracy_pct": (correctness_total / count) * 100,
            "correct_count": correct_count,
            "partially_correct_count": partially_correct_count,
            "incorrect_count": incorrect_count,
            "avg_latency_ms": latency_total / count,
            "avg_llm_rounds": llm_rounds_total / count,
            "avg_relevance": relevance_total / count,
            "avg_coherence": coherence_total / count,
            "avg_conciseness": conciseness_total / count,
        }

    overall = build_metrics(results)

    # Group by question type (direct/comparison/complex).
    grouped: dict[str, list[dict]] = {}
    for result in results:
        question_type = str(result.get("type", "unknown"))
        grouped.setdefault(question_type, []).append(result)

    by_type = {question_type: build_metrics(items) for question_type, items in grouped.items()}

    return {
        "overall": overall,
        "by_type": by_type,
    }


def main() -> None:
    # CLI arguments for dataset/model/runtime/output controls.
    parser = argparse.ArgumentParser(description="Evaluate chatbot responses and score correctness/quality")
    parser.add_argument(
        "--eval-set",
        default="evaluation/eval_set.json",
        help="Path to evaluation set JSON file",
    )
    parser.add_argument(
        "--model", 
        default="gpt-5-mini",
        help="Model name (for example: gpt-5-mini)")
    parser.add_argument(
        "--judge-model",
        default="gpt-5-mini",
        help="Model used as evaluator/judge",
    )
    parser.add_argument(
        "--temperature", 
        type=float, 
        default=0.0)
    parser.add_argument(
        "--output",
        default="evaluation/last_eval_results.json",
        help="Path to save evaluation results JSON",
    )
    args = parser.parse_args()

    # Load full evaluation set.
    eval_set_path = Path(args.eval_set)
    questions = load_eval_set(eval_set_path)

    resolved_api_key = os.getenv("OPENAI_API_KEY")
    if not resolved_api_key:
        raise ValueError("OPENAI_API_KEY is required")

    # Judge model is used only for validation (step 2).
    judge_model = args.judge_model or os.getenv("OPENAI_JUDGE_MODEL", "gpt-5-mini")
    judge_chat = ChatOpenAI(
        model=judge_model,
        temperature=args.temperature or os.getenv("OPENAI_JUDGE_TEMPERATURE", 0.0),
        api_key=resolved_api_key,
        stream_usage=True,
    )

    results = []
    generated_responses = []
    chat_model = args.model or os.getenv("OPENAI_MODEL", "gpt-5-mini")

    # Step 1: obtain chatbot responses (one trace_id per question).
    # We create a new tracer and chatbot per question so each run has an isolated trace_id.
    for item in questions:
        question_id = item.get("id")
        question_type = item.get("type")
        question_text = item.get("question", "")
        ground_truth = item.get("ground_truth", "")

        trace_id = str(uuid.uuid4())
        tracer = PostgresConversationTracer(trace_id=trace_id)
        tracer.log_event(
            event_type="session_start",
            payload={
                "trace_id": trace_id,
                "model": chat_model,
                "temperature": args.temperature,
                "question_id": question_id,
                "question_type": question_type,
            },
        )

        chatbot = TheOrganizationChatbot(
            model=chat_model,
            temperature=args.temperature,
            trace_id=trace_id,
            tracer=tracer,
        )

        started_at = time.perf_counter()
        chatbot_error = None
        chatbot_answer = ""
        llm_rounds = 0
        unique_tools_executed: list[str] = []

        # Measure end-to-end response latency for this question.
        try:
            chatbot_response = chatbot.generate_response(question_text)
            chatbot_answer = to_text(chatbot_response)
            generation_stats = getattr(chatbot, "last_generation_stats", {})
            llm_rounds = int(generation_stats.get("llm_rounds", 0))
            unique_tools_executed = list(generation_stats.get("unique_tools_executed", []))
        except Exception as error:
            chatbot_error = str(error)
            tracer.log_event(
                event_type="assistant_error",
                payload={
                    "trace_id": trace_id,
                    "error": chatbot_error,
                    "question_id": question_id,
                },
            )
        finally:
            latency_ms = (time.perf_counter() - started_at) * 1000
            tracer.log_event(
                event_type="session_end",
                payload={
                    "trace_id": trace_id,
                    "reason": "evaluation_question_completed",
                    "question_id": question_id,
                    "question_type": question_type,
                    "latency_ms": latency_ms,
                },
            )
            tracer.close()

        # Persist raw generation outcome. Validation happens in step 2.
        generated_responses.append(
            {
                "id": question_id,
                "type": question_type,
                "question": question_text,
                "ground_truth": ground_truth,
                "trace_id": trace_id,
                "latency_ms": latency_ms,
                "llm_rounds": llm_rounds,
                "unique_tools_executed": unique_tools_executed,
                "chatbot_answer": chatbot_answer,
                "chatbot_error": chatbot_error,
            }
        )

        print(
            f"[step1][{question_id}] type={question_type} latency_ms={latency_ms:.2f} trace_id={trace_id}"
        )
        print(f"Q: {question_text}")
        print(f"A: {chatbot_answer}")
        if chatbot_error:
            print(f"Chatbot Error: {chatbot_error}")
        print("-" * 80)

    # Step 2: validate correctness and quality with judge model.
    # This is intentionally separated from generation for clearer debugging and trace inspection.
    for item in generated_responses:
        question_id = item.get("id")
        question_type = item.get("type")
        question_text = item.get("question", "")
        ground_truth = item.get("ground_truth", "")
        chatbot_answer = item.get("chatbot_answer", "")
        chatbot_error = item.get("chatbot_error")

        if chatbot_error:
            # If generation failed, we mark as incorrect and skip judge inference.
            judgment = {
                "verdict": "incorrect",
                "correctness_score": 0.0,
                "reason": f"Chatbot execution failed: {chatbot_error}",
                "relevance": 0.0,
                "coherence": 0.0,
                "conciseness": 0.0,
                "raw_judge_output": "",
            }
        else:
            judgment = judge_answer(
                judge_chat=judge_chat,
                question=question_text,
                ground_truth=ground_truth,
                chatbot_answer=chatbot_answer,
            )

        # Merge generation details with judge output into final per-question result.
        result = dict(item)
        result["judgment"] = judgment
        results.append(result)

        print(
            f"[step2][{question_id}] type={question_type} verdict={judgment['verdict']} "
            f"correctness={judgment['correctness_score']}"
        )
        print(f"Reason: {judgment['reason']}")
        print("-" * 80)

    # Build overall and per-type aggregates.
    metrics = _aggregate_metrics(results)

    # Final report payload saved to disk for later analysis.
    summary = {
        "chat_model": chat_model,
        "judge_model": judge_model,
        "count": len(results),
        "metrics": metrics,
        "results": results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Print concise run summary in terminal.
    overall = metrics["overall"]
    print(
        "\nEvaluation completed. "
        f"Accuracy={overall['accuracy_pct']:.2f}% "
        f"AvgLatency={overall['avg_latency_ms']:.2f}ms "
        f"Rel={overall['avg_relevance']:.2f} Coh={overall['avg_coherence']:.2f} Con={overall['avg_conciseness']:.2f}"
    )
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
