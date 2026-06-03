# YouTrack CLI

A cross-platform command-line tool for interacting with YouTrack — creating issues and projects, moving issues through workflow states, managing tags, and listing/filtering issues.

## Language

**Issue**:
A work item inside a project, identified by a composite short ID (e.g., `DEMO-42`).
_Avoid_: Ticket, task, card

**Project**:
A YouTrack project container, identified by a short ID (e.g., `DEMO`).
_Avoid_: Workspace, board, space

**Status**:
The current workflow state of an issue (e.g., `Open`, `In Progress`, `Fixed`). Transitions are enforced by YouTrack; the CLI does not pre-validate them.
_Avoid_: State, stage, column

**Tag**:
A label attached to an issue for cross-project categorisation. Tags must exist before they can be applied — the CLI does not auto-create them on assignment.
_Avoid_: Label, category

**Token**:
A YouTrack permanent API token used to authenticate all requests. Stored in the config file and overridable via the `YOUTRACK_TOKEN` environment variable.
_Avoid_: Password, credential, API key

**Config file**:
A TOML file at `~/.config/youtrack-cli/config.toml` that stores the base URL and token for the configured instance.
_Avoid_: Settings file, credentials file

## Command structure

Commands follow a **noun-first** pattern: `youtrack <noun> <verb> [args] [flags]`.

### Nouns and their verbs

| Noun | Verbs |
|------|-------|
| `issue` | `create`, `list`, `move`, `tag` |
| `project` | `create`, `list` |
| `tag` | `create` |
| `login` | _(top-level command, no sub-verb)_ |

### Key flags

| Flag | Scope | Purpose |
|------|-------|---------|
| `--project` | `issue create`, `issue list` | Required project short ID |
| `--summary` | `issue create` | Required issue title |
| `--description` | `issue create` | Optional issue body |
| `--status` | `issue move` | Target status name |
| `--tag` | `issue tag`, `issue list` | Tag name |
| `--query` | `issue list` | Raw YouTrack query string (merged with other filters) |
| `--json` | All read commands | Emit JSON instead of human-readable output |

## Issue tracker

Issues for this project are tracked in YouTrack under project **YTCLI** at `https://lorenz-equihua.youtrack.cloud`.

Use the `youtrack` CLI to create, list, move, and tag issues:

```
youtrack issue list --project YTCLI
youtrack issue create --project YTCLI --summary "..."
youtrack issue move YTCLI-<n> --status "In Progress"
youtrack issue tag YTCLI-<n> --tag "AFK"
```

## Architecture decisions

- **Runtime**: Python, distributed via `pipx install youtrack-cli` (PyPI).
- **CLI framework**: `click` for command composition and help generation.
- **HTTP client**: `httpx` for YouTrack REST API calls.
- **Authentication**: Single instance; permanent token in config file + `YOUTRACK_TOKEN` env var override. Configured once via `youtrack login --url <base-url> --token <token>`.
- **Compatibility**: Both self-hosted YouTrack and YouTrack Cloud (youtrack.cloud). Base URL is stored in config — no code difference between the two.
- **Output**: Human-readable text/tables by default; `--json` flag for scripting.
- **Error handling**: API errors are surfaced as-is to the user. No client-side pre-validation of workflow transitions or tag existence (except tag assignment, which fails if the tag doesn't exist).
- **Profiles**: Single configured instance only. Multi-profile support deferred.
- **Filtering**: `issue list` supports specific flags (`--tag`, `--status`, `--assignee`) and a `--query` escape hatch for raw YouTrack query language. Both can be combined.
