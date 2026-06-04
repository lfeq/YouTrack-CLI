# PRDs are modelled as Epic issues with a subtask hierarchy

We needed a way to publish a PRD to YouTrack and attach its implementation issues to it. Rather than introduce a new `prd` noun/entity, we model a PRD as an ordinary **Issue** of type `Epic` (the project already has `Epic` and `Feature` configured; `Epic` is YouTrack's top-level container) whose description holds the PRD markdown. Implementation issues attach to it via the **Subtask** link type (`parent for` / `subtask of`), not "relates to", because we want a real hierarchy with rollup and board visibility — "relates to" is only a soft cross-reference.

## Considered Options

- **A new `prd` command/entity** — rejected: the glossary deliberately resists new synonyms for work items, and a PRD is a document convention (type + body template), not a new domain concept.
- **Feature instead of Epic** — rejected: Features normally sit *under* an Epic, so using Feature as the roof would muddy the hierarchy.
- **"Relates to" instead of Subtask** — rejected: no hierarchy or rollup; an agent asking "what's left on this PRD?" couldn't answer cleanly.

## Consequences

- The subtask link is exposed two ways over one shared `link_subtask(client, child_id, parent_id)` module: `--parent` on `issue create` (link at birth, the `to-issues` path) and a standalone `issue link` (connect pre-existing issues / re-parent).
- Sibling `depends on` ("Blocked by") links remain prose-only and out of scope.
