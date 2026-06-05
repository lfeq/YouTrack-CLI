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

**Priority**:
An ordered enum custom field on an **Issue** (`Show-stopper`, `Critical`, `Major`, `Normal`, `Minor` — highest first). Set at creation with `--priority` and discoverable per project via `issue priorities`. `issue list` orders results by Priority so the most important pending work surfaces first. _Note_: YouTrack sorts by bundle ordinal, so "highest first" is `sort by: priority asc`.
_Avoid_: Severity, importance, rank

**Pending**:
The set of **Issues** whose **Status** is unresolved (`isResolved` false) — `Submitted`, `Open`, `In Progress`, `To be discussed`, `Reopened`. This is the default scope of `issue list`; `--all` widens it to include resolved issues.
_Avoid_: Open (ambiguous with the `Open` state), active, todo

**Tag**:
A label attached to an issue for cross-project categorisation. Tags must exist before they can be applied — the CLI does not auto-create them on assignment.
_Avoid_: Label, category

**Epic**:
An **Issue** of type `Epic`. A **PRD** is modelled as an Epic — there is no separate `prd` entity or command. The PRD markdown lives in the Epic's description, and the issues that implement it are linked beneath it as subtasks.
_Avoid_: PRD-as-a-noun, document, parent ticket

**Subtask link**:
A directed parent/child relationship between two **Issues** (`parent for` on the Epic, `subtask of` on the child). It is how implementation issues attach to their PRD Epic. One of two link types the CLI manages, alongside the **Dependency link**.
_Avoid_: "relates to", reference

**Dependency link**:
A directed `depends on` (outward) / `is required for` (inward) relationship between two **Issues**, backed by YouTrack's native `Depend` link type. "A depends on B" means B must resolve before A can proceed. Created with `issue depend A --on B` and removed with `--remove`. Replaces recording prerequisites as free text in descriptions.
_Avoid_: blocker, prerequisite, "relates to", relation

**Blocked**:
Derived adjective for an **Issue** that has at least one outgoing `depends on` (**Dependency link**) whose target is still unresolved (same `isResolved` notion as **Pending**). `issue list` flags such issues with a `[BLOCKED]` marker but still shows them.
_Avoid_: stuck, waiting, on hold

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
| `issue` | `create`, `list`, `show`, `move`, `tag`, `link`, `depend`, `comment`, `update`, `types`, `priorities` |
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
| `--on` | `issue depend` | Target issue this issue depends on (`issue depend A --on B` = "A depends on B") |
| `--remove` | `issue depend` | Delete the dependency link instead of creating it |
| `--message` | `issue comment` | Comment body to append to an issue |
| `--description` / `--summary` | `issue update` | New PRD body / title (full replace) |
| `--all` | `issue list` | Include resolved issues (removes the default `#Unresolved` filter) |
| `--unresolved` | `issue list` | No-op alias kept for compatibility — pending-only is now the default |
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
- **Filtering**: `issue list` supports specific flags (`--tag`, `--status`, `--assignee`, `--all`) and a `--query` escape hatch for raw YouTrack query language. All can be combined. "Pending" maps to YouTrack's `#Unresolved` (any State where `isResolved` is false) rather than hard-coding state names, because it spans several states (`Submitted`, `Open`, `In Progress`, `To be discussed`, `Reopened`).
- **Agent-safe listing**: `issue list` is tuned for an agent asking "what should I work on next?". By default it (1) filters to pending work (`#Unresolved`), (2) sorts `sort by: priority asc, State asc` so the highest-priority, freshest (`Submitted`-first) issues sit at the top, and (3) caps results at `--top` (default 50) so a call against a large project never floods the agent's context. The sort is server-side so the cap trims *after* ordering; `--top 0` opts out of the cap. `--all` removes the pending filter; passing `--status` or a raw `--query` also suppresses the default pending filter (and a `sort by` inside `--query` suppresses the default sort). Priority is shown as a `PRIORITY` column and in `--json`. The direction is `asc` because YouTrack orders enum fields by bundle ordinal and `Show-stopper` is ordinal 0. See `docs/adr/0004`.
- **Dependency links**: The CLI manages YouTrack's native `Depend` link type via `issue depend A --on B` ("A depends on B"; B `is required for` A), removable with `--remove`. Both are sent through `api/commands` (`depends on B` / `remove depends on B`), mirroring the subtask helper. No client-side validation of cycles, self-dependencies, or missing IDs — YouTrack's errors are surfaced as-is. `issue list` flags any issue with an unresolved outgoing dependency as `[BLOCKED]` (computed from `links(...,issues(...,resolved))` requested in the same page query, so no N+1) but does not hide it. `issue show` lists both directions (`Depends on:` / `Required for:`) with each link's resolution status. `--json` exposes `depends_on` / `required_for` arrays and a `blocked` boolean. See `docs/adr/0005`.
- **PRD workflow**: A PRD is published as an Epic issue (`issue create --type Epic --description <prd>`). Implementation issues are linked beneath it with `--parent <epic-id>` (at creation) or `issue link` (after the fact), forming a subtask hierarchy. Progress is recorded with `issue comment` (append-only, the safe default); the PRD body itself is revised with `issue update`. `issue show` returns the Epic's body and all comments together so an agent can resume work from a single call. See `docs/adr/0001`–`0003`.
