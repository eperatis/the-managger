import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")

# Ollama's own default on a 4 GB GPU is 4096 tokens, which one large read_file result can exceed;
# Ollama then rejects every further request in the session. Qwen 3.5 small models use almost no
# extra VRAM for a larger context.
OLLAMA_CONTEXT_LENGTH_TOKENS = int(os.getenv("OLLAMA_CONTEXT_LENGTH_TOKENS", "16384"))

OLLAMA_CONNECT_TIMEOUT_SECONDS = 10
# Maximum wait between streamed chunks; generous because the first chunk waits for the model to load.
OLLAMA_READ_TIMEOUT_SECONDS = 300
