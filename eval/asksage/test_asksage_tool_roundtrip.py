"""Opt-in live test of Ask Sage tool calling and tool-result handling."""

import json
import os
import time

import httpx
import truststore

APPROVED_BASE_URL = "https://api.nnsa.asksage.ai/server/openai/v1"

MODELS = [
    "gpt-5.4-gov",
    "gpt-5.6-luna-gov",
    "gpt-5.6-sol-gov",
    "gpt-5.6-terra-gov",
]

TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_total",
        "description": "Add two numbers and return their total.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    },
}


def send_request(client, model, messages, headers, tools=None):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    if tools:
        payload["tools"] = tools

    response = client.post(
        f"{APPROVED_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        follow_redirects=False,
    )
    response.raise_for_status()
    return response.json()


def evaluate_model(client, model, headers):
    started = time.perf_counter()

    messages = [
        {
            "role": "system",
            "content": (
                "You are testing an external calculator. "
                "Use the provided tool for arithmetic. "
                "After receiving the tool result, "
                "report the result accurately."
            ),
        },
        {
            "role": "user",
            "content": "Use calculate_total to add 17 and 25. What is the total?",
        },
    ]

    first = send_request(client, model, messages, headers, [TOOL])

    assistant = first["choices"][0]["message"]
    calls = assistant.get("tool_calls") or []

    if not calls:
        return "FAIL: No tool call", None

    tool_messages = []

    for call in calls:
        if call.get("type") != "function":
            return "FAIL: Unsupported tool type", None

        function = call["function"]

        if function["name"] != "calculate_total":
            return "FAIL: Unexpected tool", None

        args = json.loads(function["arguments"])

        if (
            set(args) != {"a", "b"}
            or type(args["a"]) not in (int, float)
            or type(args["b"]) not in (int, float)
            or args["a"] != 17
            or args["b"] != 25
        ):
            return "FAIL: Incorrect arguments", None

        result = args["a"] + args["b"]

        tool_messages.append(
            {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps({"result": result}),
            }
        )

    messages.append(
        {
            "role": "assistant",
            "content": assistant.get("content"),
            "tool_calls": calls,
        }
    )
    messages.extend(tool_messages)

    second = send_request(client, model, messages, headers)

    final_message = second["choices"][0]["message"]
    final_answer = final_message.get("content") or ""
    elapsed = time.perf_counter() - started

    if final_message.get("tool_calls"):
        return "FAIL: Unexpected additional tool call", elapsed

    if "42" not in final_answer:
        return "FAIL: Incorrect final answer", elapsed

    return "PASS", elapsed


def main():
    if os.environ.get("RUN_LIVE_ASKSAGE_TESTS") != "1":
        raise SystemExit(
            "Live Ask Sage evaluation is disabled. "
            "Set RUN_LIVE_ASKSAGE_TESTS=1 to opt in."
        )

    base_url = os.environ.get("LLM_BASE_URL", "")
    if base_url != APPROVED_BASE_URL:
        raise SystemExit(
            "LLM_BASE_URL must exactly match the approved NNSA Ask Sage endpoint."
        )

    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        raise SystemExit("LLM_API_KEY is required.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    truststore.inject_into_ssl()

    with httpx.Client(timeout=120, follow_redirects=False, trust_env=False) as client:
        for model in MODELS:
            print(f"\nTesting {model}...", flush=True)

            try:
                status, elapsed = evaluate_model(client, model, headers)
                print(f"Result: {status}")

                if elapsed is not None:
                    print(f"Time: {elapsed:.2f} seconds")

            except httpx.HTTPStatusError as exc:
                print(f"Result: HTTP {exc.response.status_code}")

            except Exception as exc:
                print(f"Result: ERROR ({type(exc).__name__})")
                print(f"Details: {str(exc)[:200]}")


if __name__ == "__main__":
    main()
