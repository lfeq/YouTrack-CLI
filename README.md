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

## Updating

### Via pipx
```bash
pipx upgrade youtrack-cli
```

### Via uv
```bash
uv tool upgrade youtrack-cli
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

### Global Options

* `--version`: Show the version and exit.
* `--help`: Show the help message and exit.

### Command Summary Table

| Noun | Verb | Description | Command Example |
| :--- | :--- | :--- | :--- |
| **`login`** | — | Configure the base URL and API token. | `youtrack login --url <url> --token <token>` |
| **`project`** | **`list`** | List all projects. | `youtrack project list` |
| **`project`** | **`create`** | Create a new project. | `youtrack project create --name "My Project" --id YTCLI` |
| **`tag`** | **`list`** | List all tags visible to the user. | `youtrack tag list` |
| **`tag`** | **`create`** | Create a new tag. | `youtrack tag create --name Frontend` |
| **`issue`** | **`list`** | List issues in a project with priority ordering and status/tag filtering. | `youtrack issue list --project YTCLI` |
| **`issue`** | **`create`** | Create a new issue (optionally linking to an Epic, assigning tags, priority, type, etc.). | `youtrack issue create --project YTCLI --summary "Fix bug"` |
| **`issue`** | **`show`** | Show details of a single issue, including all comments. | `youtrack issue show YTCLI-42` |
| **`issue`** | **`move`** | Move an issue to a different status. | `youtrack issue move YTCLI-42 --status "In Progress"` |
| **`issue`** | **`tag`** | Apply an existing tag to an issue. | `youtrack issue tag YTCLI-42 --tag Frontend` |
| **`issue`** | **`link`** | Link a child issue to a parent Epic. | `youtrack issue link YTCLI-42 --parent YTCLI-100` |
| **`issue`** | **`depend`** | Create or remove a dependency link between two issues. | `youtrack issue depend YTCLI-42 --on YTCLI-43` |
| **`issue`** | **`comment`** | Append a comment to an issue. | `youtrack issue comment YTCLI-42 --message "Worked on feature"` |
| **`issue`** | **`update`** | Update an issue's description and/or summary. | `youtrack issue update YTCLI-42 --description "New body"` |
| **`issue`** | **`types`** | List valid issue types configured for a project. | `youtrack issue types --project YTCLI` |
| **`issue`** | **`priorities`** | List valid priority values configured for a project. | `youtrack issue priorities --project YTCLI` |

---

### Command Directory

#### `login`
Configure the CLI with your YouTrack base URL and API token. Credentials are saved in your config file.
* **Usage**: `youtrack login --url <url> --token <token>`
* **Options**:
  * `--url TEXT` (Required): The base URL of your YouTrack instance (e.g., `https://your-instance.youtrack.cloud`).
  * `--token TEXT` (Required): Your permanent API token.

#### `project list`
List all projects accessible to the authenticated user.
* **Usage**: `youtrack project list [flags]`
* **Flags**:
  * `--json`: Emit a JSON array of projects instead of a human-readable table.

#### `project create`
Create a new project.
* **Usage**: `youtrack project create --name <name> --id <id>`
* **Options**:
  * `--name TEXT` (Required): The name of the project.
  * `--id TEXT` (Required): The project short ID (e.g., `YTCLI`).

#### `tag list`
List all tags visible to the authenticated user.
* **Usage**: `youtrack tag list [flags]`
* **Flags**:
  * `--json`: Emit a JSON array of tags instead of a human-readable table.

#### `tag create`
Create a new tag. Note that tags must exist before they can be assigned to issues.
* **Usage**: `youtrack tag create --name <name>`
* **Options**:
  * `--name TEXT` (Required): The name of the new tag to create.

#### `issue list`
List issues in a project, featuring smart defaults and filtering.
* **Usage**: `youtrack issue list --project <project_id> [options]`
* **Options**:
  * `--project TEXT` (Required): The project short ID (e.g., `YTCLI`).
  * `--tag TEXT`: Filter by tag name.
  * `--status TEXT`: Filter by status name (e.g., `Open`).
  * `--assignee TEXT`: Filter by assignee username.
  * `--query TEXT`: Raw YouTrack query string to merge with filters.
  * `--unresolved`: Restrict to unresolved (pending) issues (redundant no-op alias kept for backwards compatibility).
  * `--all`: Include resolved issues.
  * `--top INTEGER`: Cap the number of issues returned (default `50`; `0` for no cap).
  * `--json`: Emit a JSON array of issues instead of a human-readable table.
* **Smart Defaults & Ordering Behavior**:
  * **Pending Issues Only**: By default, `issue list` only returns pending issues (i.e. unresolved issues where `isResolved` is false). This covers status values such as `Submitted`, `Open`, `In Progress`, `To be discussed`, and `Reopened`.
  * **Priority Ordering**: Results are sorted server-side so that the highest-priority work is at the top. The query uses `sort by: priority asc, State asc`.
    * **Priority asc**: Surfaces the highest-priority issues first. In YouTrack's custom Priority enum bundle, the highest priority (`Show-stopper`) has the lowest ordinal value (`0`), while `Minor` has the highest. Hence, ascending sort correctly places the highest-priority work first.
    * **State asc**: A secondary sort that surfaces brand-new, unstarted work (Status `Submitted`, ordinal 0) at the top of each priority tier.
  * **Server-Side Sort & Cap**: The sort clause is sent to the server, ensuring the `--top` cap (default `50`) truncates the list *after* sorting. High-priority issues are never hidden below the cut.
  * **Suppressing Defaults**:
    * The default pending filter (`#Unresolved`) is automatically dropped if you pass `--all`, filter by an explicit status using `--status`, or use the raw `--query` escape hatch.
    * The default sort is automatically dropped if you use a raw `--query` that contains its own `sort by` clause.
  * **Outputs**: Displays a `PRIORITY` column between the `ID` and `STATUS` columns in the CLI table view, and exports a `priority` string field in JSON output.

#### `issue create`
Create a new issue in a project.
* **Usage**: `youtrack issue create --project <project_id> --summary <summary> [options]`
* **Options**:
  * `--project TEXT` (Required): The project short ID (e.g., `YTCLI`).
  * `--summary TEXT` (Required): A concise summary/title.
  * `--description TEXT`: Detailed description of the issue. Use this for publishing Epics (e.g., PRD bodies).
  * `--assignee TEXT`: Username of the assignee.
  * `--priority TEXT`: Priority value (e.g., `Critical`, `Major`, `Normal`, `Minor`). Discover valid values with `youtrack issue priorities`.
  * `--type TEXT`: Issue type (e.g., `Bug`, `Feature`, `Task`, `Epic`). Discover valid values with `youtrack issue types`.
  * `--tag TEXT` (Repeatable option): Tag name to apply. Can be specified multiple times to assign multiple tags atomically. The CLI verifies that the tags exist and will fail-fast if any tag is missing.
  * `--parent TEXT`: Composite ID of a parent Epic (e.g., `YTCLI-100`). Creates a subtask link from the new issue to the parent Epic.
  * `--json`: Emit a JSON object of the created issue.

#### `issue show`
Retrieve details of a single issue, including its priority, status, description, assignee, type, tags, and all comments.
* **Usage**: `youtrack issue show <issue_id> [flags]`
* **Arguments**:
  * `ISSUE_ID` (Required): The composite short ID (e.g., `YTCLI-42`).
* **Flags**:
  * `--json`: Emit a JSON representation of the issue details and comments.

#### `issue move`
Move an issue to a different status.
* **Usage**: `youtrack issue move <issue_id> --status <status>`
* **Arguments**:
  * `ISSUE_ID` (Required): The composite short ID (e.g., `YTCLI-42`).
* **Options**:
  * `--status TEXT` (Required): Target status name (e.g., `In Progress`, `Fixed`). Transitions are checked and enforced by YouTrack.

#### `issue tag`
Apply an existing tag to an issue.
* **Usage**: `youtrack issue tag <issue_id> --tag <tag_name>`
* **Arguments**:
  * `ISSUE_ID` (Required): The composite short ID (e.g., `YTCLI-42`).
* **Options**:
  * `--tag TEXT` (Required): The name of the tag to apply. The tag must already exist.

#### `issue link`
Link a child issue under a parent Epic by establishing a parent/subtask link.
* **Usage**: `youtrack issue link <child_id> --parent <parent_id>`
* **Arguments**:
  * `CHILD_ID` (Required): The composite short ID of the child issue (e.g., `YTCLI-42`).
* **Options**:
  * `--parent TEXT` (Required): The composite short ID of the parent Epic (e.g., `YTCLI-100`).

#### `issue depend`
Create or remove a dependency link between two issues.
* **Usage**: `youtrack issue depend <issue_id> --on <target_id> [flags]`
* **Arguments**:
  * `ISSUE_ID` (Required): The composite short ID of the issue (e.g., `YTCLI-42`).
* **Options**:
  * `--on TEXT` (Required): The composite short ID of the target issue this issue depends on (e.g., `YTCLI-43`).
* **Flags**:
  * `--remove`: Remove the dependency link instead of creating it.


#### `issue comment`
Append a progress comment to an issue. Adding a comment is the safe, append-only way to log updates without altering the issue's description.
* **Usage**: `youtrack issue comment <issue_id> --message <message>`
* **Arguments**:
  * `ISSUE_ID` (Required): The composite short ID of the issue (e.g., `YTCLI-42`).
* **Options**:
  * `--message TEXT` (Required): The comment body to append.

#### `issue update`
Update the description and/or summary of an issue. Use this to revise the body of a PRD Epic.
* **Usage**: `youtrack issue update <issue_id> [options]`
* **Arguments**:
  * `ISSUE_ID` (Required): The composite short ID of the issue (e.g., `YTCLI-42`).
* **Options**:
  * `--description TEXT`: New description for full replacement.
  * `--summary TEXT`: New summary/title for full replacement.
  * *Note*: At least one option must be provided.

#### `issue types`
List the valid issue types configured for a project.
* **Usage**: `youtrack issue types --project <project_id> [flags]`
* **Options**:
  * `--project TEXT` (Required): The project short ID (e.g., `YTCLI`).
* **Flags**:
  * `--json`: Emit a JSON array of type names.

#### `issue priorities`
List the valid priority values configured for a project.
* **Usage**: `youtrack issue priorities --project <project_id> [flags]`
* **Options**:
  * `--project TEXT` (Required): The project short ID (e.g., `YTCLI`).
* **Flags**:
  * `--json`: Emit a JSON array of priority names.

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
