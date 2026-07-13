# The Managger

## Coding Helper

A lightweight terminal coding assistant for local projects using **Ollama**.

The tool lets you chat with an LLM about your codebase, inspect project files, and safely review any generated file changes before they are written to disk.

## Features

* Chat with a local Ollama model
* Automatically provides the model with a project file tree
* Search and inspect project files
* Supports optional `PROJECT.md` project instructions
* Shows colored diffs before applying changes
* Save and restore chat sessions

## Requirements

* Python 3.10+
* Ollama running locally
* Required Python packages (such as `requests` and `rich`)

Configure the model and Ollama server in `config.py` or with environment variables:

```bash
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=qwen3.5:9b
```

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

When the assistant proposes file changes:

1. A colored diff is displayed.
2. You choose whether to apply the changes.
3. Files are only written after confirmation.

This provides a simple review step before modifying your project.
