import json
import os

MEMORY_FILE = "memory.json"


def load_history():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    with open(MEMORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def clear_history():
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
