#!/bin/zsh
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <iterations>"
  exit 1
fi

SANDBOX_NAME="claude-ralph"

# Ensure the sandbox is created and running
if ! docker sandbox ls | grep -q "$SANDBOX_NAME"; then
  echo "Creating persistent Docker sandbox: $SANDBOX_NAME..."
  # Start the sandbox in the background with the current workspace mounted
  docker sandbox run --name "$SANDBOX_NAME" claude . -- --help >/dev/null
fi

# Self-healing check: Verify sandbox is logged in, and automatically copy host credentials if missing
if ! docker sandbox exec "$SANDBOX_NAME" claude -p "echo checking login status" &>/dev/null; then
  echo "Sandbox is not logged in. Automatically forwarding host credentials..."

  # Fetch credentials from macOS Keychain securely
  TOKEN_JSON=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null || true)

  if [ -n "$TOKEN_JSON" ]; then
    docker sandbox exec "$SANDBOX_NAME" mkdir -p /home/agent/.claude
    docker sandbox exec "$SANDBOX_NAME" sh -c "cat << 'EOF' > /home/agent/.claude/.credentials.json
$TOKEN_JSON
EOF"
    docker sandbox exec "$SANDBOX_NAME" chmod 600 /home/agent/.claude/.credentials.json
    echo "Host OAuth credentials successfully injected into sandbox '$SANDBOX_NAME'!"
  else
    echo "Warning: Could not retrieve Claude Code credentials from host macOS Keychain."
    echo "Please run 'docker sandbox run $SANDBOX_NAME' manually to log in."
  fi
fi

# Zsh-native loop syntax
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for i in {1..$1}; do
  echo "Starting Ralph iteration $i of $1 inside isolated Docker sandbox..."

  # Start the live event log streamer in the background to show real-time progress
  "$SCRIPT_DIR/../.claude/stream_sandbox_logs.py" &
  STREAMER_PID=$!

  # Run the agent loop step inside the persistent, isolated Docker sandbox
  PROMPT_PATH="$SCRIPT_DIR/../prompt.md"
  PROMPT=$(cat "$PROMPT_PATH")
  result=$(docker sandbox run "$SANDBOX_NAME" -- --permission-mode acceptEdits -p "$PROMPT")

  # Safely terminate the streamer once the iteration is complete
  kill "$STREAMER_PID" 2>/dev/null || true
  wait "$STREAMER_PID" 2>/dev/null || true

  echo "$result"

  # Zsh sub-string matching structure
  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo "PRD complete after $i iterations."
    exit 0
  fi
done
