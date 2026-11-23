import json

import requests

from config import (OLLAMA_HOST, OLLAMA_MODEL_NAME, OLLAMA_CONTEXT_LENGTH_TOKENS,
                    OLLAMA_CONNECT_TIMEOUT_SECONDS, OLLAMA_READ_TIMEOUT_SECONDS)
from terminal_text import strip_terminal_control_characters

OLLAMA_CHAT_URL = OLLAMA_HOST + "/api/chat"


def chat(messages, tools):
    """Stream the reply text to stdout as it arrives; return the assistant message, including any tool_calls."""
    # Thinking output is never shown or kept, and it multiplies response time on small local models.
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "messages": messages,
        "tools": tools,
        "stream": True,
        "think": False,
        "options": {"num_ctx": OLLAMA_CONTEXT_LENGTH_TOKENS},
    }
    response = requests.post(
        OLLAMA_CHAT_URL,
        json=payload,
        stream=True,
        timeout=(OLLAMA_CONNECT_TIMEOUT_SECONDS, OLLAMA_READ_TIMEOUT_SECONDS),
    )
    if not response.ok:
        # Ollama explains failures (such as a prompt longer than the context) in the body.
        raise RuntimeError(f"Ollama returned HTTP {response.status_code}: {response.text.strip()}")

    full_reply = ""
    tool_calls = []
    for line in response.iter_lines():
        if not line:
            continue
        response_chunk = json.loads(line.decode("utf-8"))
        if "error" in response_chunk:
            raise RuntimeError(f"Ollama error: {response_chunk['error']}")
        reply_text_chunk = response_chunk["message"]["content"]
        print(strip_terminal_control_characters(reply_text_chunk), end="", flush=True)
        full_reply += reply_text_chunk
        # Only chunks that carry tool calls have this key.
        tool_calls.extend(response_chunk["message"].get("tool_calls", []))
        if response_chunk["done"]:
            break
    if full_reply:
        print()

    assistant_message = {"role": "assistant", "content": full_reply}
    if tool_calls:
        assistant_message["tool_calls"] = tool_calls
    return assistant_message
