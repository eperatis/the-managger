import os

# Ollama server (Windows host, set in ~/.bashrc)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Model to use
MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

OLLAMA_CONNECT_TIMEOUT_SECONDS = 10
# Maximum wait between streamed chunks; generous because the first chunk waits for the model to load.
OLLAMA_READ_TIMEOUT_SECONDS = 300
