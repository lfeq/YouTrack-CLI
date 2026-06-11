#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT_PATH="$SCRIPT_DIR/prompt.md"

# 1. Read the file into an uppercase variable
PROMPT=$(cat "$PROMPT_PATH")

# 2. Match the case ($PROMPT) and remove the /dev/null redirection
#    so you can actually interact with the CLI tool.
agy --prompt-interactive "$PROMPT"