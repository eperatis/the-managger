import requests
import json
from config import OLLAMA_HOST, MODEL, OLLAMA_CONNECT_TIMEOUT_SECONDS, OLLAMA_READ_TIMEOUT_SECONDS
from terminal_text import strip_terminal_control_characters

OLLAMA_URL = OLLAMA_HOST + "/api/chat"


def chat(messages, stream=True):
    """Send messages to Ollama and stream the reply."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": stream,
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        stream=stream,
        timeout=(OLLAMA_CONNECT_TIMEOUT_SECONDS, OLLAMA_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()

    full_reply = ""
    if stream:
        for line in response.iter_lines():
            if not line:
                continue
            data = json.loads(line.decode("utf-8"))
            if "error" in data:
                raise RuntimeError(f"Ollama error: {data['error']}")
            chunk = data["message"]["content"]
            print(strip_terminal_control_characters(chunk), end="", flush=True)
            full_reply += chunk
            if data["done"]:
                break
        print()
    else:
        data = response.json()
        full_reply = data["message"]["content"]
        print(strip_terminal_control_characters(full_reply))

    return full_reply
