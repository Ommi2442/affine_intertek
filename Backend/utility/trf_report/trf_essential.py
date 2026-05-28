import json

import pandas as pd
from langchain_community.callbacks import get_openai_callback
from openai import RateLimitError
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_never,
    wait_exponential,
)


def print_retry_details(retry_state: RetryCallState):
    exception = retry_state.outcome.exception()
    wait_time = retry_state.next_action.sleep

    print(
        f"\n⚠️ Rate limit hit. Retrying attempt #{retry_state.attempt_number} in {wait_time:.1f} seconds..."
    )
    print(f"   → Error: {exception}\n")


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_never,  # Never stop, retry until available
    wait=wait_exponential(multiplier=2, min=5, max=300),
    before_sleep=print_retry_details,
)
def run_single_task(task, rag_image):
    return rag_image.invoke(task)


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_never,  # Never stop, retry until available
    wait=wait_exponential(multiplier=2, min=5, max=300),
    before_sleep=print_retry_details,
)
def run_single_task_stats(task, rag_image):
    with get_openai_callback() as cb:
        response = rag_image.invoke(task)

    response["_token_usage"] = {
        "prompt": cb.prompt_tokens,
        "completion": cb.completion_tokens,
        "total": cb.total_tokens,
    }
    return response


def results_to_dataframe(results):
    """Convert RAG results list into a structured pandas DataFrame.
    Extracts question, task_type, response, confidence, source_detected,
    text_support,    and image_support.

    Parameters:
        results (list): The list returned by your rag_image pipeline.
    Returns: pd.DataFrame:
        Clean dataframe with parsed fields."""
    rows = []
    for result in results:
        # Extract "answer" which contains JSON string
        raw_answer = result.get("answer", "")

        # Try to parse JSON
        parsed = {}
        try:
            parsed = json.loads(raw_answer)
        except Exception:
            parsed = {}

        # Construct one row
        row = {
            "question": result.get("question"),
            "task_type": result.get("task_type"),
            "response": parsed.get("response"),
            "confidence": parsed.get("confidence"),
            "source_detected": result.get("source_detected"),
            "text_support": result.get("text_support"),
            "image_support": result.get("image_support"),
        }

        rows.append(row)

    return pd.DataFrame(rows)


def update_verdict_dependencies(data):
    """
    Update all items with task_type = 'verdict_dependency'
    based on the values of items at dependency_rows.
    """

    print("\n🔍 Updating verdict_dependency items...\n")

    for table in data["Tables"]:
        items = table["Items"]

        # Build a lookup: answer_row → value at verdict column (col=3)
        verdict_map = {}
        for item in items:
            if item["answer_column"] == 3:  # verdict / verdict_dependency column
                verdict_map[item["answer_row"]] = item.get("value")

        # Now update verdict_dependency items
        for item in items:
            if item.get("task_type") != "verdict_dependency":
                continue

            dep_rows = item.get("dependency_rows")
            if not dep_rows:
                continue

            # Collect dependent values
            dep_vals = [verdict_map.get(row) for row in dep_rows if row in verdict_map]

            # Normalize empty → ""
            dep_vals = [v if v is not None else "" for v in dep_vals]

            # Apply rules
            if any(v == "" for v in dep_vals):
                final_val = ""
            elif any(v == "F" for v in dep_vals):
                final_val = "F"
            elif all(v == "N/A" for v in dep_vals):
                final_val = "N/A"
            elif all(v in ("P", "N/A") for v in dep_vals):
                final_val = "P"
            else:
                final_val = ""

            old_val = item.get("value")
            item["value"] = final_val

            # Print only if updated or changed
            print(f"Updated: {item['field']} → {final_val} (was: {old_val})")

    print("\n✅ Verdict dependency update complete.\n")
