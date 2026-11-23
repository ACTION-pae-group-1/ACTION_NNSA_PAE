import json
import os

import httpx
import truststore

truststore.inject_into_ssl()

if __name__ != "__main__":
    import pytest

    pytest.skip(
        "Standalone live Ask Sage script; excluded from offline pytest",
        allow_module_level=True,
    )

if os.environ.get("RUN_LIVE_ASKSAGE_TESTS") != "1":
    raise SystemExit("Live Ask Sage testing requires explicit opt-in.")

if os.environ.get("LLM_BASE_URL") != ("https://api.nnsa.asksage.ai/server/openai/v1"):
    raise SystemExit("Exact approved NNSA Ask Sage endpoint required.")

BASE_URL = os.environ["LLM_BASE_URL"].rstrip("/")
API_KEY = os.environ["LLM_API_KEY"]

MODELS = [
    "gpt-5.4-gov",
    "gpt-4.1-mini-gov",
    "gpt-4.1-gov",
    "gpt-5.1-gov",
    "gpt-5.6-luna-gov",
    "gpt-5.6-sol-gov",
    "gpt-5.6-terra-gov",
]

TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_total",
        "description": "Calculate a total using two numbers.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    },
}

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def test_model(client, model, tool_choice):
    response = client.post(
        f"{BASE_URL}/chat/completions",
        headers=HEADERS,
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Use calculate_total to add "
                        "17 and 25. Do not calculate "
                        "the result yourself."
                    ),
                }
            ],
            "tools": [TOOL],
            "tool_choice": tool_choice,
        },
    )

    if response.status_code != 200:
        return (f"HTTP {response.status_code}", None)

    data = response.json()
    message = data["choices"][0]["message"]
    calls = message.get("tool_calls") or []

    for call in calls:
        function = call.get("function", {})
        if function.get("name") != "calculate_total":
            continue

        try:
            args = json.loads(function["arguments"])
        except (ValueError, TypeError, KeyError):
            return "INVALID ARGUMENTS", None

        if args.get("a") == 17 and args.get("b") == 25:
            return "PASS", data.get("model")

        return "WRONG ARGUMENTS", data.get("model")

    return "NO TOOL CALL", data.get("model")


with httpx.Client(timeout=120) as client:
    for model in MODELS:
        try:
            status, actual = test_model(client, model, "auto")

            # Retry with forced tool selection if auto
            # did not produce a successful tool call.
            if status in ("NO TOOL CALL", "WRONG ARGUMENTS"):
                forced = {"type": "function", "function": {"name": "calculate_total"}}
                status, actual = test_model(client, model, forced)

            print(f"{model}: {status}")
            if actual and actual != model:
                print(f"  Returned model: {actual}")

        except Exception as exc:
            print(f"\n{model}: ERROR")
            print(f"Type: {type(exc).__name__}")
            print(f"Details: {exc!r}")
            print(f"Cause: {exc.__cause__!r}")
