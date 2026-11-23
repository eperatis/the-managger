# The Managger

## Coding Helper

A lightweight terminal coding assistant for local projects using **Ollama**.

The tool lets you chat with an LLM about your codebase, inspect project files, and safely review any generated file changes before they are written to disk.

## Features

* Chat with a local Ollama model
* Automatically provides the model with a project file tree
* Uses Ollama's native tool calling: the model reads, searches and edits files through tools
* Search and inspect project files
* Supports optional `PROJECT.md` project instructions
* Edits are staged as small search/replace changes; you review each diff and accept all, none, or pick individual edits
* Save and restore chat sessions

## Requirements

* Python 3.10+
* Ollama running locally, with a model that supports tool calling (for example `qwen3.5:4b`)
* Required Python packages (such as `requests` and `rich`)

Configure the model and Ollama server in `config.py` or with environment variables:

```bash
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=qwen3.5:9b
export OLLAMA_CONTEXT_LENGTH_TOKENS=16384
```

On a 4 GB GPU, `qwen3.5:4b` handles edits; `qwen3.5:2b` uses the tools but often proposes wrong changes.

## Usage

Run the assistant from the root of the project you want to work on:

```bash
python main.py /path/to/project
```

Or use the current directory:

```bash
python main.py
```

The assistant will load the project structure and start an interactive terminal chat.

## Commands

| Command          | Description                |
| ---------------- | -------------------------- |
| `/help`          | Show available commands    |
| `/files`         | List project files         |
| `/search <text>` | Search the project         |
| `/project`       | Show `PROJECT.md`          |
| `/reload`        | Reload project context     |
| `/sessions`      | List saved sessions        |
| `/save [name]`   | Save current session       |
| `/load <name>`   | Load a saved session       |
| `/new`           | Start a new conversation   |
| `/delete <name>` | Delete a saved session     |
| `/rename <name>` | Rename the current session |
| `/exit`          | Exit the application       |

## Editing Files

The model never writes files directly. During a turn it changes files with the
`replace_in_file` and `create_file` tools, which stage each change after checking it
(the path must be inside the project, and the text being replaced must occur exactly once).

When the model finishes its reply:

1. Each staged edit is shown as a numbered, colored diff.
2. You choose `a` (apply all), `n` (none), or `c` (decide each edit with y/n).
3. Only accepted edits are written. If an accepted edit was made on top of one you declined, nothing is written.
4. The model is told which edits were applied and which were declined.
