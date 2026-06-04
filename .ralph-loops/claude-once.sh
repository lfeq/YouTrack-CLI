#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT_PATH="$SCRIPT_DIR/prompt.md"
PROMPT=$(cat "$PROMPT_PATH")
claude --permission-mode acceptEdits --model claude-sonnet-4-6 "$PROMPT"
