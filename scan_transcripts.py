import json, os, re
from collections import Counter

projects_dir = os.path.expanduser("~/.claude/projects")
jsonl_files = []
for root, dirs, files in os.walk(projects_dir):
    for f in files:
        if f.endswith(".jsonl"):
            fp = os.path.join(root, f)
            jsonl_files.append((os.path.getmtime(fp), fp))

jsonl_files.sort(reverse=True)
jsonl_files = [fp for _, fp in jsonl_files[:50]]

bash_counter = Counter()
mcp_counter = Counter()

def leading_token(cmd):
    cmd = cmd.strip()
    cmd = re.sub(r'^([A-Z_]+=\S+\s+)+', '', cmd)
    tokens = cmd.split()
    if not tokens:
        return None
    t0 = tokens[0]
    if t0 in ('sudo', 'timeout') and len(tokens) > 1:
        t0 = tokens[1]
        tokens = tokens[1:]
    two_word = {'git', 'gh', 'docker', 'kubectl', 'npm', 'yarn', 'pnpm', 'bun', 'uv', 'youtrack', 'pytest'}
    if t0 in two_word and len(tokens) > 1:
        return f"{t0} {tokens[1]}"
    return t0

for fp in jsonl_files:
    try:
        with open(fp) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "assistant":
                    continue
                msg = obj.get("message", {})
                for item in msg.get("content", []):
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") != "tool_use":
                        continue
                    name = item.get("name", "")
                    inp = item.get("input", {})
                    if name == "Bash":
                        cmd = inp.get("command", "")
                        parts = re.split(r'[|;]+|&&', cmd)
                        for part in parts:
                            tok = leading_token(part.strip())
                            if tok:
                                bash_counter[tok] += 1
                    elif name.startswith("mcp__"):
                        mcp_counter[name] += 1
    except Exception:
        pass

print("=== BASH COMMANDS ===")
for cmd, count in bash_counter.most_common(40):
    print(f"{count:4d}  {cmd}")

print("\n=== MCP TOOLS ===")
for tool, count in mcp_counter.most_common(20):
    print(f"{count:4d}  {tool}")
