import requests
import json
from config import OLLAMA_HOST, MODEL

OLLAMA_URL = OLLAMA_HOST + "/api/chat"


def chat(messages, stream=True):
    """Send messages to Ollama and stream the reply."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": stream,
    }

    response = requests.post(OLLAMA_URL, json=payload, stream=stream)
    response.raise_for_status()

    full_reply = ""
    if stream:
        for line in response.iter_lines():
            if not line:
                continue
            data = json.loads(line.decode("utf-8"))
            chunk = data.get("message", {}).get("content", "")
            print(chunk, end="", flush=True)
            full_reply += chunk
            if data.get("done"):
                break
        print()
    else:
        data = response.json()
        full_reply = data["message"]["content"]
        print(full_reply)

    return full_reply
