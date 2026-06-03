# YouTrack CLI

A cross-platform command-line tool for interacting with YouTrack. It allows you to create and list projects/issues, move issues through workflow states, manage tags, and list valid issue types—directly from your terminal.

> [!NOTE]
> This tool was developed using Claude Sonnet 4.6 and Gemini Flash 3.5 high, so there are no guarantees, though the MIT License outlines the official disclaimer.

---

## Installation

You can install the YouTrack CLI using either `pipx` or `uv`.

### Via pipx
```bash
pipx install youtrack-cli
```

### Via uv
```bash
uv tool install youtrack-cli
```

---

## Quickstart

### 1. Authenticate / Login
Configure the CLI with your YouTrack base URL and permanent API token:
```bash
youtrack login --url https://your-instance.youtrack.cloud --token perm:your-token-here
```
This command writes the credentials to the local config file.

### 2. Run Your First Command
List all projects to verify the connection:
```bash
youtrack project list
```

---

## Configuration

### Config File
The configuration is stored in a TOML file at:
`~/.config/youtrack-cli/config.toml`

It contains the base URL and API token under the `[default]` section:
```toml
[default]
url = "https://your-instance.youtrack.cloud"
token = "perm:your-token-here"
```

### Environment Variables
You can override the stored configuration using the following environment variables:
* **`YOUTRACK_TOKEN`**: Overrides the stored token. Useful for CI/CD pipelines.
* **`YOUTRACK_CONFIG_DIR`**: Overrides the directory where the CLI looks for or writes the `config.toml` file.

---

## Command Reference

The CLI commands follow a noun-first pattern: `youtrack <noun> <verb> [args] [flags]`.

| Noun | Verb | Description | Command Example |
| :--- | :--- | :--- | :--- |
| **`login`** | — | Configure base URL and API token. | `youtrack login --url <url> --token <token>` |
| **`project`** | **`list`** | List all projects. Support `--json` flag. | `youtrack project list` |
| **`project`** | **`create`** | Create a new project. | `youtrack project create --name "My Project" --id MP` |
| **`issue`** | **`list`** | List issues in a project. Support `--tag`, `--status`, `--assignee`, `--query`, and `--json` flags. | `youtrack issue list --project MP --status Open` |
| **`issue`** | **`create`** | Create a new issue. Support `--description`, `--assignee`, `--priority`, `--type`, `--tag` (repeatable), and `--json` flags. | `youtrack issue create --project MP --summary "Fix bug"` |
| **`issue`** | **`move`** | Move an issue to a different status. | `youtrack issue move MP-12 --status "In Progress"` |
| **`issue`** | **`tag`** | Apply an existing tag to an issue. | `youtrack issue tag MP-12 --tag Frontend` |
| **`issue`** | **`types`** | List the valid issue types configured for a project. Support `--json` flag. | `youtrack issue types --project MP` |
| **`tag`** | **`list`** | List all tags visible to the user. Support `--json` flag. | `youtrack tag list` |
| **`tag`** | **`create`** | Create a new tag. | `youtrack tag create --name Frontend` |

### Key Flags
* `--json`: Emit raw JSON instead of the human-readable formatted table (available on list/read commands).
* `--query`: Pass a raw YouTrack query string verbatim to filter issues in `issue list`.
* `--tag` (in `issue create`): Can be specified multiple times to assign multiple tags atomically during creation.

---

## Contributing

To set up a local development environment, make sure you have `uv` installed.

### Dev Setup
1. Clone the repository and navigate into the project directory.
2. Synchronize dependencies and set up the virtual environment:
   ```bash
   uv sync
   ```

### Running Tests
To run the full test suite, execute:
```bash
uv run pytest
```

### Running in Development
To run the CLI locally within the development environment:
```bash
uv run youtrack --help
```
