#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <iterations>"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT_PATH="$SCRIPT_DIR/prompt.md"
PROMPT=$(cat "$PROMPT_PATH")

for ((i=1; i<=$1; i++)); do
    echo "====== Starting Claude iteration $i of $1 in isolated sandbox... ======"

    result=$(claude --permission-mode bypassPermissions --model claude-sonnet-4-6 -p "$PROMPT")

    echo "$result"

    if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo "PRD complete after $i iterations."
    exit 0
    fi
done
