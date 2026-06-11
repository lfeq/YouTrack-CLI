# Surface parent/subtasks hierarchy in issue show (JSON + table)

## Problem Statement

The CLI can *create* a parent/child hierarchy — `issue create --parent <epic>` and
`issue link` establish a **Subtask link** (`parent for` on the Epic, `subtask of` on the
child) — but a caller cannot *read it back*. `youtrack issue show <ID> --json` exposes only
`depends_on` and `required_for`; there is no `parent` or `subtasks` field, and the
human-readable `issue show` table shows no hierarchy either. So an agent or script that
attaches an implementation issue to its PRD Epic has no programmatic way to confirm the
link took, short of a separate `issue list --query "subtask of: <id>"` round-trip. The
hierarchy is effectively write-only from the caller's side.

This is doubly surprising because the **Dependency link** type *is* surfaced in both
`issue show` JSON and table (ADR 0005), so the same view that shows dependency links
silently omits subtask links.

## Solution

`issue show` surfaces the subtask hierarchy in both output modes. For any issue it reports:

- its **parent** Epic (or `null` if it has none), and
- its **subtasks** (the children linked beneath it),

each entry carrying `id`, `summary`, and `resolved` status. `--json` adds a `parent`
(single object or `null`) and a `subtasks` (array) field; the human-readable table gains a
`Parent:` line and a `Subtasks:` section with `[resolved]`/`[unresolved]` markers.

From the user's perspective: after linking an implementation issue to its PRD Epic with
`--parent`, `youtrack issue show <child> --json` immediately shows the `parent`, and
`youtrack issue show <epic> --json` shows the `subtasks` with their completion status — the
hierarchy can be verified from a single call, with no extra round-trip. This needs no extra
API request: `issue show` already fetches all link types in one call and was simply
discarding the Subtask rows.

## User Stories

1. [x] As an agent, I want `issue show <child> --json` to include a `parent` field, so that I
   can confirm an implementation issue is attached to its PRD Epic without a second query.
2. [x] As an agent, I want `issue show <epic> --json` to include a `subtasks` array, so that I
   can enumerate the implementation issues beneath a PRD Epic programmatically.
3. [x] As an agent, I want each subtask entry to carry `resolved`, so that I can compute how
   much of an Epic is done without fetching every child individually.
4. [x] As an agent, I want the `parent` entry to carry `resolved`, so that I can tell whether
   the parent Epic is already closed.
5. [x] As an agent, I want `parent` to be a single object or `null` (not a list), so that I can
   rely on the tree hierarchy without handling a multi-parent case.
6. [x] As an agent, I want the `parent`/`subtasks` entries to use the same `{id, summary,
   resolved}` shape as `depends_on`/`required_for`, so that I can parse all links uniformly.
7. [x] As a user, I want `issue show` (table) to print a `Parent:` line, so that I can see at a
   glance which Epic an issue belongs to.
8. [x] As a user, I want `issue show` (table) to print a `Subtasks:` section with resolved
   markers, so that I can see an Epic's children and their status in one view.
9. [x] As a user, I want an issue that is both a child and a parent (an Epic nested under a
   larger Epic) to show both its `parent` and its `subtasks`, so that mid-tree issues read
   correctly.
10. [x] As a user, I want an issue with no hierarchy to show `parent: null` and `subtasks: []`
    (table: no Parent line / empty Subtasks), so that the absence of links is unambiguous.
11. [x] As an agent, I want `issue show` to keep returning `depends_on`/`required_for`
    unchanged alongside the new fields, so that adding hierarchy does not regress
    dependency reporting.
12. [x] As an agent, I want the hierarchy verifiable from a single `issue show` call, so that I
    can resume work on a PRD Epic — body, comments, dependencies, and subtasks — in one
    request.
13. [x] As a maintainer, I want subtask parsing isolated in its own pure function, so that I
    can test all direction/cardinality cases without the network.
14. [x] As a maintainer, I want subtask and dependency parsing to not interfere on a shared
    `links` payload, so that one link type's rows never leak into the other's fields.

## Implementation Decisions

- **New deep module: a pure `parse_subtask_links(links)` parser** in the issues module,
  returning `(parent, subtasks)`. It runs alongside the existing `parse_dependency_links`
  over the same already-fetched `links` data. It considers only rows whose link type is
  `Subtask`, maps `direction == "OUTWARD"` to **subtasks** (this issue is "parent for"
  them) and `direction == "INWARD"` to the **parent** (this issue is "subtask of" it), and
  skips `direction == "BOTH"`.
- **Direction semantics verified against the live instance.** The `Subtask` link type has
  `sourceToTarget = "parent for"`, `targetToSource = "subtask of"`; relative to the queried
  issue, `OUTWARD` is a child and `INWARD` is the parent. (Confirmed empirically on the
  Epic↔child pair created during planning.)
- **Sibling parser, not an extended one.** `parse_dependency_links` is named and shaped
  around the `Depend` link type (it returns the `blocked` boolean and is also used by the
  issue-list path, which must not gain subtask parsing), so it is left untouched. Two
  passes over a handful of links is negligible. This follows the per-link-type-helper idiom
  established by ADR 0005.
- **`parent` is single-or-`null`; `subtasks` is a list.** YouTrack's hierarchy is a tree:
  at most one parent, many subtasks. If the API ever returns multiple inward Subtask links,
  the **first inward wins** and the rest are ignored — no client-side validation or
  raising, consistent with the project-wide "surface YouTrack as-is" rule.
- **Entry shape mirrors dependencies:** each parent/subtask entry is `{id, summary,
  resolved}`, the same shape already used for `depends_on`/`required_for`.
- **`IssueDetail` gains `parent` and `subtasks` fields**, populated by `show_issue` from
  the parser. No new API call — `show_issue` already requests all link types in one
  request and was discarding the Subtask rows.
- **Surfaced in both `--json` and the table.** JSON emits the new fields automatically from
  the dataclass. The detail table renderer adds a `Parent:` line (near the top, after
  Assignee — orienting context) and a `Subtasks:` section (alongside the dependency
  sections), each entry marked `[resolved]`/`[unresolved]`.
- **`issue list` is untouched.** Parent/child membership is not decision-relevant to "what
  should I work on next?" the way `[BLOCKED]` is, and `--query "subtask of: <id>"` already
  filters the list by hierarchy on demand. The change is confined to `issue show` + the
  parser + `IssueDetail` + the detail formatter.
- Documented in `docs/adr/0007-surface-subtask-hierarchy-in-show.md`; CONTEXT.md's **PRD
  workflow** bullet and **Subtask link** glossary entry are updated. No new domain term —
  `parent`/`subtasks` reuse existing language.

## Testing Decisions

- **What makes a good test here:** assert the externally observable result — the parsed
  `(parent, subtasks)` structure and the rendered JSON/table output — not internal
  iteration. No network; reuse the existing mock-client pattern rather than new HTTP mocks.
- **Module under test (primary): `parse_subtask_links`**, exhaustively, mirroring
  `test_parse_dependency_links`: `None`/`[]` → `(None, [])`; one INWARD → `parent` set; one
  and many OUTWARD → `subtasks` list; both present → both populated; **multiple INWARD →
  first wins**; `BOTH` skipped; non-`Subtask` link types (e.g. a `Depend` link in the same
  list) ignored.
- **`show_issue` integration test**, mirroring `test_show_issue_with_dependencies`: a
  mock-client response whose `links` contains both a Subtask and a Depend link; assert
  `parent`/`subtasks` populate correctly *and* `depends_on`/`required_for` still work —
  proving the two parsers coexist on one payload.
- **Formatter tests:** the detail table renders `Parent:`/`Subtasks:` sections with
  resolved markers (mirroring `test_format_issue_detail_table_dependencies`); the detail
  JSON includes `parent`/`subtasks` with the right shape (extending
  `test_format_issue_detail_json`).
- **Prior art:** `tests/test_issues.py` already contains `test_parse_dependency_links`,
  `test_show_issue_with_dependencies`, `test_format_issue_detail_table_dependencies`, and
  `test_format_issue_detail_json` — the new tests follow these one-for-one (pytest, mock
  client, no network).

## Out of Scope

- **Surfacing hierarchy in `issue list`** (a column, an Epic marker, or `parent`/`subtasks`
  on list-row JSON). Considered and rejected — not decision-relevant to list usage.
- **Multi-parent support.** The hierarchy is a tree; `parent` is single-or-`null`,
  first-inward-wins. Not modeling multiple parents.
- **Creating, moving, or removing subtask links.** This PRD is read-only exposure; link
  creation (`--parent`, `issue link`) is unchanged.
- **The UTF-8 output-encoding fix** (separate PRD / ADR 0006) — unrelated.

## Further Notes

- Root cause confirmed in code: `show_issue` requests
  `links(direction,linkType(name),issues(idReadable,resolved,summary))` — all link types —
  but `parse_dependency_links` keeps only `linkType.name == "Depend"` and discards the
  `Subtask` rows. The fix parses rows already present in the payload; there is no extra
  network cost.
- This is the read-side mirror of ADR 0005 (which exposed the already-creatable `Depend`
  link type); ADR 0007 does the same for the already-creatable `Subtask` link type.
- Design decisions and rejected alternatives are in
  `docs/adr/0007-surface-subtask-hierarchy-in-show.md`.
