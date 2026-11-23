import json

import requests

from config import OLLAMA_HOST, OLLAMA_MODEL_NAME, OLLAMA_CONNECT_TIMEOUT_SECONDS, OLLAMA_READ_TIMEOUT_SECONDS
from terminal_text import strip_terminal_control_characters

OLLAMA_CHAT_URL = OLLAMA_HOST + "/api/chat"


def chat(messages):
    """Stream the model's reply to stdout as it arrives and return the full reply text."""
    payload = {"model": OLLAMA_MODEL_NAME, "messages": messages, "stream": True}
    response = requests.post(
        OLLAMA_CHAT_URL,
        json=payload,
        stream=True,
        timeout=(OLLAMA_CONNECT_TIMEOUT_SECONDS, OLLAMA_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()

    full_reply = ""
    for line in response.iter_lines():
        if not line:
            continue
        response_chunk = json.loads(line.decode("utf-8"))
        if "error" in response_chunk:
            raise RuntimeError(f"Ollama error: {response_chunk['error']}")
        reply_text_chunk = response_chunk["message"]["content"]
        print(strip_terminal_control_characters(reply_text_chunk), end="", flush=True)
        full_reply += reply_text_chunk
        if response_chunk["done"]:
            break
    print()
    return full_reply
