# Native dependency links between issues

## Problem Statement

Today, when one piece of work can't start until another finishes, the team records that prerequisite as free text inside the issue's description — "this depends on YTCLI-42". That prose is invisible to the tooling: `issue list` can't tell that an issue is blocked, an agent asking "what should I work on next?" happily picks up work whose prerequisites aren't done, and there's no structured way to see what a given issue unblocks. YouTrack already models this relationship natively (its built-in `Depend` link type), but the CLI doesn't expose it, so the structure never gets used.

## Solution

Teach the CLI to manage YouTrack's native **Dependency link**. A user writes `youtrack issue depend YTCLI-A --on YTCLI-B` to declare "A depends on B" (B `is required for` A), and `--remove` to undo it. Once dependencies are structured data instead of prose, the rest of the tooling can reason about them: `issue list` flags any issue with an unresolved prerequisite as `[BLOCKED]` (without hiding it), and `issue show` displays both directions — what an issue depends on and what it is required for — each with its resolution status. This turns "is this safe to start?" from a manual reading exercise into something the CLI answers directly, which is especially valuable for the agent-first `issue list` workflow.

## User Stories

1. [x] As a developer, I want to declare that issue A depends on issue B with one command, so that the prerequisite is structured data instead of a note buried in a description.
2. [x] As a developer, I want the command to read like natural English (`issue depend A --on B`), so that I don't have to remember which direction the link points.
3. [x] As a developer, I want to remove a dependency I created by mistake (`--remove`), so that a wrong link doesn't keep polluting my views.
4. [x] As an agent asking "what should I work on next?", I want `issue list` to mark issues that are blocked by an unresolved dependency, so that I don't pick up work I can't actually finish.
5. [x] As an agent, I want blocked issues to still appear in `issue list` (marked, not hidden), so that a mis-placed dependency never silently removes real work from my view.
6. [x] As a developer, I want `issue show` to list what an issue **depends on** with each prerequisite's resolved/unresolved status, so that I can tell at a glance whether I'm clear to start.
7. [x] As a developer, I want `issue show` to list what an issue is **required for**, so that I understand the downstream impact of closing it.
8. [x] As a developer, I want the blocking dependencies highlighted within the `Depends on` list, so that I can immediately see which prerequisite is the holdup.
9. [x] As a scripter, I want `--json` on `issue list` to include a `blocked` boolean, so that I can build automation that routes around blocked work.
10. [x] As a scripter, I want `--json` on `issue list` and `issue show` to include `depends_on` and `required_for` arrays, so that I can consume the dependency graph programmatically.
11. [x] As a developer, I want the dependency to be created through YouTrack's native link type, so that it shows up correctly in the YouTrack web UI and in any other YouTrack-aware tool.
12. [x] As a developer, I want a clear API error surfaced when I reference a non-existent issue or create an invalid dependency, so that I know the link wasn't created, without the CLI inventing its own rules.
13. [x] As a developer, I want the `[BLOCKED]` marker to consider only **unresolved** prerequisites, so that once I finish issue B, issue A stops showing as blocked automatically on the next listing.
14. [x] As a developer reading the project docs, I want a glossary entry for **Dependency link** and **Blocked**, so that the vocabulary is unambiguous across the codebase.
15. [x] As a maintainer, I want the existing `issue link` (subtask) command left untouched, so that adding dependencies doesn't risk regressing the PRD/Epic hierarchy workflow.
16. [x] As a developer, I want listing a large project to stay fast even with dependencies, so that fetching blocked status doesn't trigger a flood of extra API calls.

## Implementation Decisions

This PRD expands the domain model from one managed link type (Subtask) to two (Subtask + Dependency). See `docs/adr/0005-native-dependency-links.md`; the relevant terms and architecture notes are recorded in `CONTEXT.md`.

**Command surface**
- New dedicated verb `issue depend <ISSUE> --on <TARGET>`, read as "ISSUE depends on TARGET". A `--remove` flag deletes the link instead of creating it. The existing `issue link --parent` (subtask) command is not modified.
- No `--type`-style generic link command; one verb per link type, consistent with the noun-first style.

**Writer (thin, over `api/commands`)**
- `add_dependency(client, issue_id, target_id)` posts the native command `depends on <TARGET>` applied to `<ISSUE>`, mirroring the existing `link_subtask` helper.
- `remove_dependency(client, issue_id, target_id)` posts `remove depends on <TARGET>`.
- No client-side validation of cycles (A→B, B→A), self-dependencies, or missing IDs. The command is sent and YouTrack's error, if any, is surfaced as-is — consistent with the project-wide "no pre-validation" rule. Cycles are not detected at all.

**Link parser (deep module — the testable core)**
- A pure function takes the raw `links` array as returned by the YouTrack API and produces a structured view: the `depends_on` list (outgoing, what this issue needs), the `required_for` list (incoming, what it unblocks), and a derived `blocked` boolean. Each entry carries the linked issue's id, summary, and resolved status.
- `blocked` is true when at least one `depends_on` entry is unresolved. "Unresolved" uses the same `resolved`/`isResolved` notion already used for **Pending** / `#Unresolved`.
- The parser ignores link types it doesn't care about (e.g. subtask links), reading only the `Depend` type via the API's `direction` + `linkType(name)` fields.
- It does no I/O, so it is exercised with fixture JSON in isolation.

**Read-side wiring**
- `list_issues` adds `links(direction,linkType(name),issues(idReadable,resolved,summary))` to its requested `fields` and feeds each issue's `links` to the parser, setting `blocked` on the `Issue` dataclass. Because the link data comes back in the same page request, there is **no N+1** — no per-issue follow-up calls.
- `show_issue` requests the same `links` field and populates `depends_on` / `required_for` on the `IssueDetail` dataclass.
- The `Issue` dataclass gains a `blocked` field; `IssueDetail` gains `depends_on` and `required_for` fields. JSON output is produced via `asdict`, so the new fields appear in `--json` automatically.

**Formatting**
- `format_issues_table` prepends/annotates a row with a `[BLOCKED]` marker when `blocked` is true. The default result set and ordering are unchanged (blocked issues are marked, never filtered out).
- `format_issue_detail_table` renders a `Depends on:` section and a `Required for:` section, each line showing id, summary, and `[resolved]`/`[unresolved]`, marking which `Depends on` entries are currently blocking.

## Testing Decisions

A good test here asserts **external behavior**, not internal structure: given an input it checks the visible output, and does not assert on how data is stored or which private helpers were called. The link parser is pure, so its tests are pure input→output assertions over fixture JSON.

- **Link parser (primary target).** Unit tests with hand-written `links` fixtures covering: an unresolved outgoing dependency → `blocked` true and the entry in `depends_on`; a resolved outgoing dependency → not blocked; an incoming link → appears in `required_for`, never affects `blocked`; an issue with no links; links of an unrelated type (subtask) ignored; mixed resolved/unresolved prerequisites. This is the core logic and gets the most coverage.
- **`issue depend` CLI command.** Tests via Click's `CliRunner` (prior art: `tests/test_cli.py`), asserting the correct native command string is sent (`depends on <TARGET>` vs `remove depends on <TARGET>`), that `--on` is required, and that `--remove` switches to deletion. The HTTP client is mocked at the boundary as existing CLI tests do.
- **Formatters.** Tests that `[BLOCKED]` appears in the table exactly when `blocked` is true and is absent otherwise, and that the `Depends on:` / `Required for:` sections render with the right entries and resolution markers in the detail view (prior art: existing formatter assertions for the priority column).

Prior art to follow: `tests/test_issues.py` for parsing/helpers with a mocked client, and `tests/test_cli.py` for `CliRunner`-driven command tests.

## Out of Scope

- Unlinking subtasks (the CLI still cannot remove subtask links; only dependencies are removable). The asymmetry is intentional and may be revisited later.
- Hiding or reordering blocked issues in `issue list`, or a `--blocked`/`--unblocked` filter. The default is mark-don't-hide; filtering is deferred.
- Transitive/recursive blocking (treating A as blocked because its prerequisite B is itself blocked). Only direct, first-level dependencies are considered.
- Cycle detection or any other client-side validation.
- Other YouTrack link types (`relates to`, `duplicates`). Only the `Depend` type is added.
- A standalone `issue links` listing command; dependencies are surfaced through `issue show` and the `issue list` marker only.

## Further Notes

- "Blocked" is derived, never stored — it is recomputed from current resolution state on each read, so finishing a prerequisite clears the marker on the next listing with no extra action.
- The blocked computation inherits the same project-bundle assumptions as the priority/pending logic in ADR 0004 (it depends on YouTrack's `resolved` field).
- Suggested follow-up once this lands: a `--blocked` filter on `issue list` and, separately, an audit command to surface dependency cycles — both deliberately left out here.
