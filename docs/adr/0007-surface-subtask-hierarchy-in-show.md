# Surface the subtask hierarchy in `issue show`

The CLI already *creates* the parent/child hierarchy: `issue create --parent <epic>` and
`issue link` establish a **Subtask link** (`parent for` on the Epic, `subtask of` on the
child, per ADR 0001). But the hierarchy was **write-only from the caller's perspective** —
`issue show --json` exposed only `depends_on` / `required_for`, with no `parent` or
`subtasks` field, so a caller could create a subtask link but had no way to read it back
and verify the hierarchy programmatically (the only check was an `issue list --query
"subtask of: <id>"` round-trip).

The data was already being fetched and then thrown away. `show_issue` requests
`links(direction,linkType(name),issues(idReadable,resolved,summary))`, which returns
**all** link types — but `parse_dependency_links` keeps only `linkType.name == "Depend"`
and discards the `Subtask` rows. So exposing the hierarchy needs **no extra API call**,
only parsing the rows already in the payload.

This mirrors ADR 0005 exactly: that ADR exposed the already-creatable `Depend` link type
in `issue show`; this one does the same for the already-creatable `Subtask` link type.

Direction semantics were verified against the live instance (Epic `YTCLI-39` ↔ child
`YTCLI-40`): the `Subtask` link type has `sourceToTarget = "parent for"`,
`targetToSource = "subtask of"`, and relative to the queried issue, `OUTWARD` points to a
**subtask** (this issue is "parent for" it) while `INWARD` points to the **parent** (this
issue is "subtask of" it).

## Decisions

- **Sibling parser, not an extended one.** A new `parse_subtask_links(links) ->
  (parent, subtasks)` runs alongside `parse_dependency_links`, over the same
  `data.get("links")`. `parse_dependency_links` is named and shaped around `Depend` (it
  returns the `blocked` boolean and is also called by `list_issues`, which does not want
  subtask parsing), so it is left untouched. Two passes over a handful of links is
  irrelevant. This follows the per-link-type-helper idiom ADR 0005 established.
- **`OUTWARD → subtasks`, `INWARD → parent`.** Matches the verified direction semantics
  and parallels the dependency parser's `OUTWARD → depends_on`. `direction == "BOTH"` is
  skipped (it cannot mean parent-and-child of the same issue), and only
  `linkType.name == "Subtask"` rows are considered, so dependency and subtask parsing do
  not bleed into each other.
- **`parent` is single-or-`null`; `subtasks` is a list.** YouTrack's hierarchy is a tree:
  an issue has at most one parent but many subtasks. `parent` is therefore a single object
  (or `null`), `subtasks` a list. If the API ever returns multiple inward Subtask links,
  the **first inward wins** and the rest are ignored — no client-side validation or
  raising, consistent with the project-wide "surface YouTrack as-is" rule.
- **Same entry shape as dependencies.** Each parent/subtask entry is
  `{id, summary, resolved}`, reusing the established dependency-entry shape. `resolved` is
  meaningful here: it lets a caller see subtask completion and whether the parent Epic is
  closed.
- **Exposed in both `--json` and the table.** `IssueDetail` gains `parent` and `subtasks`;
  `--json` emits them, and `format_issue_detail_table` renders `Parent:` (near the top,
  after Assignee — orienting context) and `Subtasks:` (alongside the dependency sections),
  each with the `[resolved]`/`[unresolved]` marker. Rendering only in JSON would make
  `issue show` display dependency links but silently omit subtask links in the same view.
  This keeps the "resume work from a single `show`" property: an agent sees an Epic's
  children and their status, and a child sees its parent Epic, in one call.
- **`issue list` is untouched.** `Depend` earned a `[BLOCKED]` marker in the list because
  blocking changes whether a row is actionable *now*; parent/child membership does not.
  Adding a hierarchy column would widen every row for data that only matters when focused
  on a single issue, and `--query "subtask of: <id>"` already filters the list by
  hierarchy on demand. The change is confined to `show` + the parser + `IssueDetail`.

## Rejected alternatives

- **Unify into one `parse_links` pass.** Fewer iterations, but one function would own two
  distinct link-type concerns and a wider return tuple, and would entangle the
  `list_issues` call path. Rejected for the single-purpose sibling.
- **`parent` as a list (multi-parent).** Contradicts the tree hierarchy of ADR 0001 and
  would complicate every caller. Rejected; first-inward-wins instead.
- **Expose hierarchy in `issue list`** (column / marker / row JSON). Out of scope; not
  decision-relevant to "what should I work on next?" the way `[BLOCKED]` is.

## Consequences

- No new domain term: `parent`/`subtasks` reuse the existing **Subtask link** language.
  CONTEXT.md's **PRD workflow** bullet is extended to note `issue show` now returns the
  parent and subtasks (with resolved status), and the **Subtask link** glossary entry
  notes the relationship is now readable via `issue show` / `--json`.
- `IssueDetail` gains `parent: Optional[dict] = None` and `subtasks: List[dict]`; the JSON
  and table formatters render them.
- No extra API call — the `links` field already fetched by `show_issue` carries the
  Subtask rows.
- The separate UTF-8 output-encoding fix (ADR 0006) is unrelated and tracked separately.
