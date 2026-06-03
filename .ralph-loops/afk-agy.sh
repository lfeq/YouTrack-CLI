#!/bin/zsh
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <iterations>"
  exit 1
fi

# Zsh-native loop syntax
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for i in {1..$1}; do
  echo "====== Starting Antigravity (agy) iteration $i of $1 in isolated sandbox... ======"

  # Run the agent loop step using the host agy binary with --sandbox and --dangerously-skip-permissions
  PROMPT_PATH="$SCRIPT_DIR/prompt.md"
  PROMPT=$(cat "$PROMPT_PATH")
  result=$(agy --dangerously-skip-permissions --sandbox -p "$PROMPT" < /dev/null)

  echo "$result"

  # Zsh sub-string matching structure
  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo "PRD complete after $i iterations."
    exit 0
  fi
done
