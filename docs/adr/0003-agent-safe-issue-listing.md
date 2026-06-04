# Agent-safe issue listing: `--unresolved` and a default `--top` cap

Because this CLI is driven by LLM agents, an `issue list` against a large project can flood the agent's context with hundreds of rows. We added two guards. `--unresolved` filters to "pending" work by mapping to YouTrack's `#Unresolved` (any State whose `isResolved` flag is false) rather than hard-coding state names — "pending" spans five states (`Submitted`, `Open`, `In Progress`, `To be discussed`, `Reopened`) and stays correct if new states are added. `--top` caps the result count and defaults to 50, so even an unfiltered call stays bounded; `--top 0` opts out.

## Consequences

- `list_issues` must apply the default cap itself — previously it fetched every match unbounded.
- `--unresolved` composes with the existing `--status`, `--tag`, `--assignee`, and `--query` filters.
