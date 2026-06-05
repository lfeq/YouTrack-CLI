# Priority-ordered, pending-by-default issue listing

## Problem Statement

The YouTrack CLI is driven primarily by LLM agents. When an agent picks up work on a project it runs `issue list` and asks, in effect, "what should I work on next?". Today that command is a poor answer to that question:

- It returns **every** issue, including resolved ones, padding the agent's context with finished work.
- It returns them in YouTrack's natural order, so the most important work is **not** at the top — and with the default `--top 50` cap, genuinely high-priority issues can be trimmed below the cut while low-priority noise survives.
- It does not even **show** the Priority of an issue, so neither the agent nor a human can tell why one issue should be picked before another.

The Priority field already exists on `issue create` (and `issue priorities` lists the valid values), but nothing downstream consumes it. The result is that an agent cannot reliably find the highest-priority pending work in a single, bounded call.

## Solution

Make `issue list` opinionated toward its primary consumer. By default it now answers "what should I work on next?" directly:

- [x] It scopes to **pending** work (YouTrack `#Unresolved`), hiding resolved issues unless asked.
- [x] It **sorts** results so the highest-priority, freshest work is at the top — `Show-stopper`/`Critical` before `Minor`, and within a priority tier, `Submitted` (brand-new, unstarted) issues first.
- [x] It does the sort **server-side**, so the `--top` cap trims *after* ordering and the most important work is never hidden below the cut.
- [x] It **shows Priority** as a column and in JSON, so the ordering is legible.

Escape hatches keep the command honest: `--all` brings back resolved issues, and any explicit resolution intent (`--status`, or a raw `--query`) steps out of the way of the defaults rather than fighting them.

## User Stories

1. [x] As an agent starting work on a project, I want `issue list` to return only pending issues by default, so that resolved work doesn't fill my context.
2. [x] As an agent, I want `issue list` to put the highest-priority issues at the top by default, so that the first rows are the ones that matter most.
3. [x] As an agent, I want issues of equal priority to be ordered with `Submitted` (new, unstarted) first, so that I grab fresh high-priority work before work that is already underway.
4. [x] As an agent, I want the priority ordering applied server-side before the `--top` cap, so that the most important issues are never trimmed away below the cut.
5. [x] As an agent, I want each listed issue to show its Priority, so that I can see why the list is ordered the way it is and justify which issue I pick.
6. [x] As a developer scripting against the CLI, I want Priority included in `--json` output, so that my tooling can read and act on it.
7. [x] As a developer, I want a `--all` flag on `issue list`, so that I can include resolved issues when I am auditing completed work.
8. [x] As a developer, I want passing `--status Fixed` (or any explicit status) to automatically drop the default pending filter, so that asking for a resolved status does not silently return nothing.
9. [x] As a power user, I want a raw `--query` to suppress the default pending filter, so that I retain full control of the query when I opt into the escape hatch.
10. [x] As a power user, I want a raw `--query` that already contains `sort by` to suppress the default sort, so that my explicit ordering is never overridden by a second sort clause.
11. [x] As an agent, I want the default `--top 50` cap to still apply after sorting, so that a large project never floods my context.
12. [x] As an agent that really does want everything, I want `--top 0` to remove the cap, so that I can opt out when I need the full set.
13. [x] As an existing user of the old `--unresolved` flag, I want it to keep working as a harmless no-op, so that my existing commands and scripts don't break.
14. [x] As a developer, I want the default filters and sort to compose with `--tag` and `--assignee`, so that I can express "pending issues assigned to me, by priority" in one call.
15. [x] As a developer, I want "pending" to map to YouTrack's `#Unresolved` rather than hard-coded state names, so that it stays correct across the five pending states and any future ones.
16. [x] As a developer, I want the priority sort to use `sort by: priority asc` (not `desc`), so that the highest-priority bundle value (`Show-stopper`, ordinal 0) sorts to the top instead of the bottom.
17. [x] As a maintainer, I want the `asc`-not-`desc` rationale documented, so that nobody "fixes" the direction into a silent bug later.
18. [x] As an agent, I want a single `issue list` call to be a complete answer to "what should I work on next?", so that I don't need to chain multiple filtered calls.

## Implementation Decisions

- **New deep module `build_issue_list_query()`.** A pure function that takes the listing inputs (project, tag, status, assignee, raw query, `all`, plus whatever is needed to decide the cap) and returns the YouTrack query string. It owns *all* the decision logic — there is no query assembly left inline in `list_issues`. This keeps the rules in one pure, I/O-free place. Its responsibilities:
  - Always start from `project: <shortName>` and append `--tag`, `--status`, `--assignee`, and raw `--query` parts as today.
  - Append `#Unresolved` **unless** any of these is true: `--all` is set, an explicit `--status` was given, or a raw `--query` was given.
  - Append `sort by: priority asc, State asc` **unless** the raw `--query` already contains `sort by` (case-insensitive).
- **Sort direction is `asc`, deliberately.** YouTrack orders an enum custom field by its bundle ordinal. In the Priority bundle `Show-stopper` is ordinal 0 (highest) and `Minor` is the largest ordinal (lowest), so `asc` surfaces the highest priority first. Verified live against `YTCLI`: `sort by: priority desc` returned `Minor` first. See ADR 0004.
- **Secondary sort `State asc` = Submitted first.** In the State bundle `Submitted` is ordinal 0, so the secondary key naturally surfaces brand-new, unstarted work at the top of each priority tier. Order among unresolved states: `Submitted`, `Open`, `In Progress`, `To be discussed`, `Reopened`.
- **Server-side sort, then cap.** The `sort by` clause goes in the YouTrack query so `$top` trims after ordering. Sorting must never be done client-side after the cap.
- **`list_issues()` becomes shallow.** It calls `build_issue_list_query()`, makes the request, and parses the response. It gains an `all: bool` parameter (default `False`). The existing `unresolved` parameter is retained but no longer changes behavior (the default already filters to pending).
- **`Issue` dataclass gains `priority: Optional[str]`.** Parsed from the `Priority` single-enum custom field in the same loop that already extracts `State` and `Assignee`. Because the field flows through `asdict`, it appears in `--json` automatically.
- **`format_issues_table()` gains a `PRIORITY` column.** Proposed column order: `ID | PRIORITY | STATUS | SUMMARY | ASSIGNEE`.
- **CLI changes on `issue list`.** Add `--all` (flag, removes the pending filter). Keep `--unresolved` as a no-op alias retained for backward compatibility (documented as redundant). Wire `--all` through to `list_issues`.
- **No new network round-trips.** The Priority value is already requested by the existing `customFields(name,value(name,login))` field selector; only parsing is added.

## Testing Decisions

- **What makes a good test here:** assert on external behavior — the query string produced for a given set of inputs — not on how the function is structured internally. `build_issue_list_query()` is a pure function, so tests pass inputs and assert on the returned string (substring/clause presence and absence), with no HTTP mocking required.
- **Module under test: `build_issue_list_query()` only.** Cases to cover:
  - Default (only `--project`): output contains `#Unresolved` **and** `sort by: priority asc, State asc`.
  - `--all`: output does **not** contain `#Unresolved`; still contains the sort.
  - Explicit `--status`: output does **not** contain `#Unresolved` (suppressed); still contains the sort.
  - Raw `--query` (without `sort by`): `#Unresolved` suppressed; default sort still appended.
  - Raw `--query` containing `sort by ...`: default sort **not** appended (no double sort clause); the user's clause is preserved.
  - Composition: `--tag` and `--assignee` parts present alongside the default `#Unresolved` + sort.
  - `--status`/`--all` interaction sanity (explicit status with `--all` still suppresses pending; no contradictory `#Unresolved`).
- **Prior art:** follow the existing unit-test style in `tests/test_issues.py`. Because the query builder is pure, these tests are simpler than the existing ones — no mocked client needed at all.
- **Explicitly not tested in this PRD:** the `Priority` parsing in `list_issues`, the `PRIORITY` column in `format_issues_table`, and CLI flag wiring. (Decision: keep the test surface focused on the decision-rich pure module.)

## Out of Scope

- Configurable or per-project sort orders. The ordering is fixed (`priority asc, State asc`); there is no flag to change the sort key or direction.
- A `--sort`/`--order` flag or a `--resolved`-only filter. The only new opt-out is `--all`; finer control is available through the raw `--query` escape hatch.
- Changing how Priority is set on issues — `issue create --priority` and `issue priorities` already exist and are unchanged.
- Filtering by priority (e.g. "only Critical"). This PRD orders by priority; it does not add a priority filter flag (a user can still do it via `--query`).
- Tests for `list_issues` parsing, the formatter column, and CLI wiring.
- Multi-project listing, pagination beyond `$top`, or caching.

## Further Notes

- The default behavior change is mildly breaking: callers who relied on `issue list` returning resolved issues must now pass `--all`. This is intentional and justified by the agent-first design; it is documented in ADR 0004 and CONTEXT.md.
- The ordering depends on the project's Priority and State bundles using YouTrack's conventional ordinal direction (highest priority at ordinal 0, `Submitted` at State ordinal 0). This held for `YTCLI`; a project that re-orders its bundles would re-order these results. This is an accepted trade-off, not a bug.
- Empirically verified against `YTCLI`: Priority bundle order is `Show-stopper, Critical, Major, Normal, Minor`; the unresolved States are `Submitted, Open, In Progress, To be discussed, Reopened`. The default pending filter currently returns empty on `YTCLI` because every issue is `Fixed` — the correct, expected result.
- See `docs/adr/0004-priority-ordered-default-issue-listing.md` and the updated `CONTEXT.md` (Language: **Priority**, **Pending**; Architecture: Agent-safe listing).

## Documentation

- [x] Update the README with a full command reference documenting every `youtrack` command and flag currently available, reflecting the new `issue list` defaults, priority sorting, columns, and json structure.

