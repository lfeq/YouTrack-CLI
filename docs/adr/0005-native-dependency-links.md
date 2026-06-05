# Native dependency links between issues

Teams have been recording "issue A can't start until issue B is done" as free text in descriptions. YouTrack already models this natively with its built-in **Depend** link type (directed: `depends on` outward / `is required for` inward). This ADR makes the CLI manage that link type so dependencies become structured data the tooling can reason about, instead of prose a human has to read.

This deliberately expands the domain model: the CLI now manages **two** link types (Subtask, from ADR 0001, and Dependency), where CONTEXT.md previously stated Subtask was "the only link type the CLI manages" and listed "dependency" under _Avoid_. Both statements are revised.

## Decisions

- **Dedicated verb, not a generic `link`.** Dependencies are created with `issue depend <A> --on <B>`, read as "A depends on B" (so B `is required for` A). This mirrors the noun-first, one-verb-per-link-type style already used for subtasks (`issue link --parent`) rather than overloading `issue link` with a `--type` switch. The existing `issue link` command is untouched.
- **Native command under the hood.** Like `link_subtask`, the verb posts to `api/commands`: `depends on <B>` applied to issue `<A>`. Removal posts `remove depends on <B>`.
- **Removable from day one.** `issue depend <A> --on <B> --remove` deletes the link. Unlike subtasks (which the CLI still can't unlink), a stray dependency is visible — it paints `[BLOCKED]` and pollutes the agent's "what next?" view — so a quick undo is worth shipping immediately.
- **No client-side validation.** Self-dependencies, non-existent IDs, and cycles (A→B, B→A) are not checked locally; the command is sent and YouTrack's error, if any, is surfaced as-is. Consistent with the project-wide "surface API errors, no pre-validation" rule. Cycles are not detected at all.
- **`issue list` marks, does not hide.** A row gets a `[BLOCKED]` marker when the issue has at least one outgoing `depends on` link whose target is **unresolved** (the same `isResolved` notion as *Pending* / `#Unresolved`). The default result set is unchanged — blocked work still appears, the agent just sees it is blocked and decides. Hiding was rejected because a mis-placed dependency would silently remove real work from the list.
- **No N+1.** The blocked computation is fed by the same `issue list` query: the request asks for `links(direction,linkType(name),issues(idReadable,resolved))`, so resolution status of every dependency comes back in the original page fetch. No per-issue follow-up calls.
- **`issue show` shows both directions.** It renders `Depends on:` (what this issue needs) and `Required for:` (what closing it unblocks), each link listed with id, summary, and resolved/unresolved status, marking which ones are currently blocking. This keeps the "resume work from a single `show`" property.
- **Exposed in `--json`.** `issue list` and `issue show` add `depends_on` / `required_for` arrays and, for list rows, a `blocked` boolean — the same "make the ordering/decision visible" principle that put `priority` in JSON (ADR 0004).

## Consequences

- New term **Dependency link** and derived adjective **Blocked** enter CONTEXT.md's Language section; the **Subtask link** entry drops the "only link type" claim and the "dependency" avoid-word.
- `list_issues` must request and parse the `links` field and derive `blocked`; the table formatter gains the `[BLOCKED]` marker and the detail formatter gains the two dependency sections.
- A new `add_dependency` / `remove_dependency` helper (parallel to `link_subtask`) and an `issue depend` Click command are added.
- "Blocked" depends on the target's resolution state, which is a project-bundle concept; it inherits the same assumptions as ADR 0004's pending logic.
- The CLI still does not unlink subtasks; only dependencies are removable for now. That asymmetry is intentional (driven by the BLOCKED-visibility argument above) and can be revisited if subtask removal is later requested.
