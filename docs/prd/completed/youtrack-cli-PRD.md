# YouTrack CLI — PRD

## Problem Statement

Developers who use YouTrack daily must switch to the browser to perform routine operations — creating issues, updating workflow states, tagging items, and checking what's in a project. This context-switching breaks flow and slows down teams that prefer terminal-centric workflows. There is no official cross-platform CLI that covers these day-to-day operations.

## Solution

A cross-platform command-line tool (`youtrack`) that lets developers interact with YouTrack — both self-hosted and Cloud — directly from the terminal. It covers the most frequent operations: creating and listing projects and issues, moving issues through workflow states, and managing tags. Output is human-readable by default with a `--json` flag for scripting.

## User Stories

1. As a developer, I want to configure the CLI with my YouTrack base URL and token in a single command, so that I can start using it immediately without editing config files manually.
2. As a developer, I want my token and base URL stored in a local config file, so that I don't have to re-enter credentials on every invocation.
3. As a developer, I want to override the stored token with a `YOUTRACK_TOKEN` environment variable, so that I can use the CLI in CI/CD pipelines without a config file on the build server.
4. As a developer, I want the CLI to work against both self-hosted YouTrack instances and YouTrack Cloud, so that my whole team can use it regardless of how YouTrack is deployed.
5. As a developer, I want to install the CLI with a single `pipx install youtrack-cli` command, so that onboarding is frictionless on any OS.
6. As a developer, I want the CLI to work identically on macOS, Windows, and Linux, so that the whole team can adopt it regardless of platform.
7. As a developer, I want to create a new project by providing a short ID and name, so that I can set up new work streams without opening the browser.
8. As a developer, I want to list all projects in my YouTrack instance, so that I can look up a project short ID without leaving the terminal.
9. As a developer, I want to create an issue by providing a project short ID and summary, so that I can log new work items instantly from the terminal.
10. As a developer, I want to optionally add a description when creating an issue, so that I can provide context beyond the summary.
11. As a developer, I want to optionally set an assignee when creating an issue, so that ownership is clear from the moment the issue is created.
12. As a developer, I want to optionally set a priority when creating an issue, so that the team knows what to tackle first without a follow-up edit.
13. As a developer, I want to optionally set a type when creating an issue, so that it is properly categorised from creation.
14. As a developer, I want to see the created issue's short ID printed after creation, so that I can reference it immediately in other commands.
15. As a developer, I want to list issues in a project, so that I can see what work is tracked without switching to the browser.
16. As a developer, I want to filter listed issues by tag, so that I can quickly find issues belonging to a specific concern.
17. As a developer, I want to filter listed issues by status, so that I can see only open, in-progress, or completed items.
18. As a developer, I want to filter listed issues by assignee, so that I can view my own or a colleague's workload.
19. As a developer, I want to filter listed issues using YouTrack's native query language via a `--query` flag, so that I can perform complex searches without the CLI reimplementing query syntax.
20. As a developer, I want to combine specific filter flags with `--query`, so that I can layer simple flags on top of a base query.
21. As a developer, I want to move an issue to a different status using its short ID and the target status name, so that I can update workflow state without leaving the terminal.
22. As a developer, I want the CLI to surface YouTrack's error message when a status transition is invalid, so that I understand why the move was rejected.
23. As a developer, I want to add an existing tag to an issue using its short ID and tag name, so that I can categorise issues without opening the browser.
24. As a developer, I want the CLI to fail with a clear error when I try to add a tag that doesn't exist, so that typos don't silently create orphaned tags.
25. As a developer, I want to create a new tag by name, so that I can extend the tag vocabulary from the terminal before assigning it to issues.
26. As a developer, I want human-readable table output by default, so that I can scan results at a glance.
27. As a developer, I want a `--json` flag on all read commands, so that I can pipe output into `jq` or other scripts.
28. As a developer, I want clear, actionable error messages when API calls fail, so that I can diagnose and fix problems quickly.
29. As a developer, I want `--help` on every command and sub-command, so that I can discover available options without consulting external documentation.

## Implementation Decisions

### Module breakdown

- **`config`** — reads and writes `~/.config/youtrack-cli/config.toml`. Owns all filesystem access for configuration. Resolves the active token by checking `YOUTRACK_TOKEN` env var first, falling back to the stored token. Single instance only; no profile switching.

- **`client`** — thin wrapper around `httpx`. Attaches the auth header and base URL to every request. Translates HTTP errors (4xx, 5xx) into typed exceptions that upper layers can handle without knowing about HTTP. No other module touches `httpx` directly.

- **`issues`** — logic for create, list (with filters), move status, and add tag. Accepts structured arguments, calls `client`, returns typed domain objects. Merges specific filter flags with a raw `--query` string when both are provided.

- **`projects`** — logic for create and list. Same pattern as `issues`.

- **`tags`** — logic for create. Minimal scope for now.

- **`formatters`** — converts domain objects (issues, projects, tags) into human-readable tables or JSON strings. No business logic; purely display concern. Keeps output decisions out of all other modules.

- **`cli`** — `click` command tree wiring all nouns and verbs to the modules above. Contains no logic: parse args, call module, pass result to formatter, print.

### Command structure

Noun-first: `youtrack <noun> <verb> [args] [flags]`

| Command | Required args/flags | Optional flags |
|---|---|---|
| `youtrack login` | `--url`, `--token` | — |
| `youtrack project create` | `--name`, `--id` | — |
| `youtrack project list` | — | `--json` |
| `youtrack issue create` | `--project`, `--summary` | `--description`, `--assignee`, `--priority`, `--type`, `--json` |
| `youtrack issue list` | `--project` | `--tag`, `--status`, `--assignee`, `--query`, `--json` |
| `youtrack issue move` | issue ID (positional), `--status` | — |
| `youtrack issue tag` | issue ID (positional), `--tag` | — |
| `youtrack tag create` | `--name` | — |

### Auth

- Config file: `~/.config/youtrack-cli/config.toml` with `[default]` section containing `url` and `token`.
- `YOUTRACK_TOKEN` env var takes precedence over stored token.
- `youtrack login` writes the config file on first run.

### Error handling

- API errors are caught in `client` and re-raised as typed exceptions with the YouTrack error message preserved.
- `cli` layer catches exceptions and prints a human-readable message to stderr, then exits with a non-zero code.
- No client-side pre-validation of workflow transitions or tag existence (except tag assignment, which relies on the API rejecting an unknown tag).

### Output

- Human-readable tables/summary lines by default.
- `--json` flag on all read commands emits a JSON array to stdout.
- Success confirmations (create, move, tag) print the affected entity's short ID.

### Distribution

- Published to PyPI as `youtrack-cli`.
- Installed via `pipx install youtrack-cli`.
- Entry point: `youtrack`.

## Testing Decisions

**What makes a good test:** tests assert on externally observable behaviour — return values, raised exceptions, and stdout/stderr output — not on internal implementation details like which private method was called or how many times `httpx` was invoked.

### Modules to test

- **`config`** — test reading and writing the config file, env var override precedence, and missing-file behaviour. Use a temporary directory so tests don't touch the real config.

- **`client`** — test that requests carry the correct auth header and base URL, and that HTTP error responses are converted into the expected typed exceptions. Use `httpx`'s built-in `MockTransport` or `respx` to avoid real network calls.

- **`issues`** — test create, list (with various filter combinations including merged `--query`), move, and tag operations. Mock `client` at the boundary so tests are fast and deterministic. Assert on the domain objects returned, not on raw HTTP payloads.

### Modules not unit-tested

- **`formatters`** — covered implicitly by CLI integration tests; isolated unit tests would just assert that a table library formats a dict, which adds little value.
- **`cli`** — covered by `click`'s `CliRunner`-based integration tests that exercise the full command→module→formatter chain end-to-end.
- **`projects`** and **`tags`** — follow the same pattern as `issues`; add unit tests if logic grows beyond simple pass-through calls.

## Out of Scope

- Multi-profile / multi-instance support (single configured instance only).
- Client-side workflow transition validation (the API handles this).
- Auto-creating tags during issue tag assignment.
- Editing or deleting issues, projects, or tags.
- Attaching files or comments to issues.
- User/member management.
- Agile board or sprint operations.
- Webhook or automation configuration.
- A TUI (terminal UI) or interactive mode.

## Further Notes

- The YouTrack REST API is identical between self-hosted and Cloud deployments; the base URL in the config file is the only difference.
- YouTrack issue short IDs (`DEMO-42`) and project short IDs (`DEMO`) are the primary identifiers throughout — full names are never used as command arguments.
- The `--query` flag passes YouTrack's native query language verbatim to the API, giving users access to the full query surface without the CLI reimplementing it.

## Implementation Status

- [x] **01 — Project scaffold + `youtrack login`** (Completed 2026-06-03)
- [x] **02 — `youtrack project list` + `youtrack project create`** (Completed 2026-06-03)
- [x] **03 — `youtrack issue create`** (Completed 2026-06-03)
- [x] **04 — `youtrack issue list` with filtering** (Completed 2026-06-03)
- [x] **05 — `youtrack issue move`** (Completed 2026-06-03)
- [x] **06 — `youtrack tag create` + `youtrack issue tag`** (Completed 2026-06-03)
- [x] **10 — Migrate build tooling to uv** (Completed 2026-06-03)
- [x] **11 — Write README and add MIT license** (Completed 2026-06-03)



