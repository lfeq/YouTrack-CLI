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

**Epic**:
An **Issue** of type `Epic`. A **PRD** is modelled as an Epic — there is no separate `prd` entity or command. The PRD markdown lives in the Epic's description, and the issues that implement it are linked beneath it as subtasks.
_Avoid_: PRD-as-a-noun, document, parent ticket

**Subtask link**:
A directed parent/child relationship between two **Issues** (`parent for` on the Epic, `subtask of` on the child). This is the only link type the CLI manages, and it is how implementation issues attach to their PRD Epic.
_Avoid_: "relates to", reference, dependency

**Comment**:
An append-only, timestamped note attached to an **Issue**. Adding a comment never alters the issue's description, so it is the safe way for an agent to record progress on a PRD. Distinct from editing the description, which replaces the PRD body.
_Avoid_: Note, annotation, remark

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
| `issue` | `create`, `list`, `show`, `move`, `tag`, `link`, `comment`, `update`, `types`, `priorities` |
| `project` | `create`, `list` |
| `tag` | `create`, `list` |
| `login` | _(top-level command, no sub-verb)_ |

### Key flags

| Flag | Scope | Purpose |
|------|-------|---------|
| `--project` | `issue create`, `issue list`, `issue types`, `issue priorities` | Required project short ID |
| `--summary` | `issue create` | Required issue title |
| `--description` | `issue create` | Optional issue body |
| `--status` | `issue move`, `issue list` | Target/filter status name |
| `--tag` | `issue tag`, `issue list` | Tag name |
| `--parent` | `issue create`, `issue link` | Parent Epic short ID; creates a subtask link from the child to the Epic |
| `--message` | `issue comment` | Comment body to append to an issue |
| `--description` / `--summary` | `issue update` | New PRD body / title (full replace) |
| `--unresolved` | `issue list` | Restrict to unresolved (pending) issues via `#Unresolved` |
| `--top` | `issue list` | Cap the number of issues returned (default 50; `--top 0` for no cap) |
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
- **Filtering**: `issue list` supports specific flags (`--tag`, `--status`, `--assignee`, `--unresolved`) and a `--query` escape hatch for raw YouTrack query language. All can be combined. `--unresolved` maps to YouTrack's `#Unresolved` (any State where `isResolved` is false) rather than hard-coding state names, because "pending" spans several states (`Submitted`, `Open`, `In Progress`, `To be discussed`, `Reopened`).
- **Agent-safe listing**: `issue list` caps results at `--top` (default 50) so an unfiltered call against a large project never floods an LLM agent's context with hundreds of rows. `--top 0` opts out of the cap.
- **PRD workflow**: A PRD is published as an Epic issue (`issue create --type Epic --description <prd>`). Implementation issues are linked beneath it with `--parent <epic-id>` (at creation) or `issue link` (after the fact), forming a subtask hierarchy. Progress is recorded with `issue comment` (append-only, the safe default); the PRD body itself is revised with `issue update`. `issue show` returns the Epic's body and all comments together so an agent can resume work from a single call. See `docs/adr/0001`–`0003`.
