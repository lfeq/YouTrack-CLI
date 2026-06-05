# Priority-ordered, pending-by-default issue listing

For v1.0 the `issue list` command becomes opinionated toward its primary consumer — an LLM agent asking "what should I work on next?". Instead of returning every issue in YouTrack's natural order, the default now (a) filters to pending work and (b) sorts so the most important, freshest work is at the top of the `--top` window.

## Decisions

- **Pending by default.** With no explicit scope flags, `issue list` appends `#Unresolved`, the same `isResolved`-based filter introduced in ADR 0003. The agent never has to remember to ask for pending work. The new `--all` flag removes this filter to return resolved issues too. The default is also suppressed when the caller expresses their own resolution intent via `--status` or a raw `--query`, because filtering "pending AND Fixed" would silently return nothing.
- **Priority-ordered, ascending.** The query appends `sort by: priority asc, State asc`. Counter-intuitively the direction is **`asc`, not `desc`**: YouTrack sorts an enum field by its bundle ordinal, and in the Priority bundle `Show-stopper` is ordinal 0 (highest) while `Minor` is the largest ordinal (lowest). Verified live against `YTCLI`: `sort by: priority desc` surfaced `Minor` first. `asc` puts `Show-stopper`/`Critical` on top.
- **Submitted first within a priority tier.** The secondary key `State asc` breaks ties by workflow state ordinal. In the State bundle `Submitted` is ordinal 0, so brand-new, unstarted work rises to the top of each priority tier — matching the intuition that a high-priority Submitted issue is the next thing to grab. (Order among the unresolved states: `Submitted`, `Open`, `In Progress`, `To be discussed`, `Reopened`.)
- **Server-side sort, then cap.** Sorting is done by YouTrack inside the query, not in Python, so the `--top` cap (default 50) trims *after* ordering. A client-side sort would cap an arbitrary 50 rows and then reorder them, hiding the most important work below the cut.
- **Priority is now visible.** Because the agent is being asked to trust an ordering, it must see the key: `Issue` gains a `priority` field parsed from the `Priority` custom field, rendered as a `PRIORITY` column in the table and included in `--json`.
- **Raw `sort by` wins.** If the caller's `--query` already contains `sort by`, the default sort is not appended, so an explicit ordering is never silently overridden.

## Consequences

- `issue list`'s default result set changes: resolved issues no longer appear unless `--all` (or an explicit status/resolution filter) is given. This is a deliberate, breaking-ish default change justified by the agent-first design.
- The `--unresolved` flag from ADR 0003 is now redundant — the default already does it. It is kept as a no-op alias for backward compatibility rather than removed.
- `list_issues` must assemble the `#Unresolved` and `sort by` clauses conditionally, honoring the suppression rules above, and parse the Priority custom field into the `Issue` dataclass.
- The ordering depends on the project's Priority and State bundles using YouTrack's conventional ordinal direction (highest priority at ordinal 0, `Submitted` at State ordinal 0). This held for `YTCLI`; a project that re-orders its bundles would re-order these results.
