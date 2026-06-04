# PRD: Publishing PRDs to YouTrack and Agent-Friendly Issue Workflow

> Status: Completed

## Problem Statement

I drive this YouTrack CLI mostly through LLM agents (the `to-prd`, `to-issues`, and Ralph-loop skills). Today the CLI can create, list, move, and tag issues, but it can't support the document-driven workflow I actually use:

- When an agent turns a conversation into a PRD, there's no first-class way to **put that PRD into YouTrack** as a parent work item that the implementation issues hang off of. The PRD and its issues end up as disconnected items with no hierarchy.
- As an agent works through a PRD, the workflow calls for **recording progress against the PRD** ("update the PRD with the work that was done"). The CLI has no way to add a note to an issue, and no safe way to do so — the only conceivable path (rewriting the description) risks an agent wiping the entire PRD on a bad read-modify-write.
- There's no way to **read a PRD and its accumulated notes back** in a single call, so an agent resuming work can't cheaply reconstruct context.
- `issue list` returns **every** matching issue with no cap. Against a project with hundreds of issues, an agent listing them floods its own context window with rows it doesn't need, and there's no concise "just the pending work" filter.

## Solution

Extend the existing `issue` command surface so the full PRD lifecycle lives in YouTrack, modelled entirely on top of the existing **Issue** concept (no new entity or noun):

- [x] **Publish a PRD** as an **Issue of type `Epic`** whose description holds the PRD markdown — using the existing `issue create --type Epic --description ...` path.
- [x] **Link implementation issues** beneath the PRD Epic as a **Subtask** hierarchy, either at creation time (`issue create --parent <epic-id>`) or after the fact (`issue link <child> --parent <epic>`).
- [x] **Record progress safely** with `issue comment <id> --message "..."` — append-only, so an agent can never clobber the PRD body. Keep `issue update <id> [--description ...] [--summary ...]` as a deliberate full-replace escape hatch for genuinely revising the spec. (Both comment and update commands completed).
- [x] **Read back** the PRD body and all its notes together with `issue show <id>` (one call, `--json` for machines), so an agent can resume work from a single command.
- [x] **Keep agent context lean** on `issue list` with `--unresolved` (the "pending work" filter, mapped to YouTrack's `#Unresolved`) and `--top N` (a result cap defaulting to 50, with `--top 0` to opt out).

The skills are updated to use this: `to-prd` publishes the PRD as an Epic and emits its short ID; `to-issues` accepts that ID and passes `--parent` to each child it creates.

## User Stories

1. [x] As an agent running `to-prd`, I want to publish a PRD as an Epic issue, so that the PRD lives in YouTrack as a trackable parent work item.
2. [x] As an agent running `to-prd`, I want the PRD markdown to be stored verbatim in the Epic's description, so that the full spec is readable from YouTrack.
3. [x] As an agent running `to-prd`, I want the command to print back the new Epic's short ID (e.g. `YTCLI-50`), so that I can pass it to the next step.
4. [x] As a developer, I want a PRD to be an ordinary Issue of type `Epic` rather than a new entity, so that the CLI and domain model stay small.
5. [x] As an agent running `to-issues`, I want to create an implementation issue already linked under a PRD Epic in one command, so that I don't need a separate linking step per issue.
6. [x] As an agent, I want `issue create --parent YTCLI-50` to attach the new issue beneath the Epic as a subtask, so that the Epic shows its children and rolls up progress.
7. [x] As a developer, I want the parent relationship to be a true Subtask link (`parent for` / `subtask of`), not a loose "relates to", so that the hierarchy is real and visible on the board.
8. [x] As an agent, I want to link two pre-existing issues with `issue link <child> --parent <epic>`, so that I can attach issues to a PRD that was written after them, or re-parent an issue.
9. [x] As an agent working through a PRD, I want to append a progress note with `issue comment <id> --message "..."`, so that I can record what was done without touching the PRD body.
10. [x] As a developer, I want comments to be append-only, so that a faulty agent can never overwrite or delete the PRD spec while recording progress.
11. [x] As an agent, I want each comment to be timestamped and attributed by YouTrack, so that the note history is meaningful when read back.
12. [x] As an agent that genuinely needs to revise the PRD spec, I want `issue update <id> --description "..."`, so that I can replace the PRD body deliberately.
13. [x] As an agent, I want `issue update <id> --summary "..."`, so that I can correct an issue or PRD title.
14. [x] As a developer, I want `issue update` to be a full replace (YouTrack-native semantics), so that the behaviour is predictable and not a fragile partial merge.
15. [x] As an agent resuming work on a PRD, I want `issue show <id>` to return the Epic's description plus all its comments in one call, so that I can reconstruct context cheaply.
16. [x] As an agent, I want `issue show <id> --json` to emit a machine-readable view of the issue, its description, and its comments, so that I can parse it programmatically.
17. [x] As a human, I want `issue show <id>` to print a readable layout of the issue with its notes, so that I can inspect any issue's full detail from the terminal.
18. [x] As an agent listing issues on a large project, I want `issue list --unresolved` to return only pending work, so that resolved issues don't fill my context.
19. [x] As a developer, I want `--unresolved` to map to YouTrack's `#Unresolved` rather than hard-coded state names, so that it stays correct across the five pending states (`Submitted`, `Open`, `In Progress`, `To be discussed`, `Reopened`) and any future states.
20. [x] As an agent, I want `issue list --top 50` (and a default cap of 50) to bound the number of rows returned, so that an unfiltered list never floods my context with hundreds of issues.
21. [x] As an agent that really does want everything, I want `issue list --top 0` to remove the cap, so that I can opt out when I need the full set.
22. [x] As an agent, I want `--unresolved` and `--top` to combine with the existing `--tag`, `--status`, `--assignee`, and `--query` filters, so that I can express precise queries like "pending issues assigned to me, capped at 20".
23. [x] As a developer, I want all new read commands to support `--json`, so that the CLI stays scriptable and agent-friendly.
24. [x] As a developer, I want new commands to surface YouTrack API errors as-is (no client-side pre-validation), so that error handling stays consistent with the rest of the CLI (completed for `issue link`, `issue comment`, `issue show`, and `issue update`).
25. [x] As an agent, I want modifying commands (`issue link`, `issue comment`, `issue update`) to confirm success in plain language (e.g. "Linked YTCLI-43 under YTCLI-50"), so that I can verify the action without a follow-up call (completed).
26. [x] As a user reading help, I want `issue link`, `issue comment`, `issue update`, and `issue show` to appear in `youtrack issue --help`, so that the new capabilities are discoverable (completed).


## Implementation Decisions

### Domain model (per CONTEXT.md and ADRs 0001–0003)

- A **PRD** is an **Issue** of type `Epic`. No new CLI noun, no new entity. (ADR 0001)
- Implementation issues attach to the PRD Epic via the **Subtask** link type (`parent for` on the Epic, `subtask of` on the child). This is the only link type the CLI manages. Sibling `depends on` ("Blocked by") links stay prose-only and out of scope. (ADR 0001)
- Progress is recorded with **Comments** (append-only); revising the PRD body uses a separate full-replace update. (ADR 0002)
- "Pending" is YouTrack's `#Unresolved`, not a hard-coded state; `issue list` is capped by `--top` (default 50). (ADR 0003)

### Modules to build/modify

All work concentrates in the existing `issues` module (deep, behind the `YouTrackClient._request` seam), the `formatters` module (rendering), and the `cli` module (thin command wiring). The deep modules are the issue-operation functions; they encapsulate YouTrack's request/response shape behind small, stable signatures and are unit-testable in isolation against a mocked client.

- **`link_subtask(client, child_id, parent_id) -> None`** (new, deep). Creates a Subtask link making `child_id` a subtask of `parent_id`. Single responsibility, stable signature; this is the shared core that both `issue create --parent` and `issue link` call. Surfaces API errors as-is.
- **`create_issue(...)`** (modify). Add an optional `parent` parameter. When provided, after the issue is created, call `link_subtask(client, new_issue_id, parent)` so the child is linked at birth. Creation and linking are two API calls; if linking fails the created issue still exists and the error is surfaced (partial-failure behaviour is acceptable and explicit, not hidden).
- **`add_comment(client, issue_id, message) -> Comment`** (new, deep). Appends a comment to an issue and returns the created comment. Never reads or rewrites the description.
- **`update_issue(client, issue_id, description=None, summary=None) -> Issue`** (new, deep). Full-replace update of the provided fields. At least one of `description`/`summary` must be provided; passing neither is a usage error raised before any API call.
- **`show_issue(client, issue_id) -> IssueDetail`** (new, deep). Fetches one issue including its `description` and its `comments` (text, author, created timestamp) in a single request. Returns a richer structure than the list `Issue`.
- **`list_issues(...)`** (modify). Add `unresolved: bool` and `top: int` parameters. `unresolved=True` appends `#Unresolved` to the assembled query (composing with existing filter parts). `top` maps to YouTrack's `$top` pagination parameter; the CLI defaults it to 50 and treats `top=0` (or `None`) as "no cap".

### Data model additions

- **`Comment`** dataclass: at minimum `id`, `text`, `author`, `created`.
- **`IssueDetail`** (or an extension of the existing `Issue`) carrying the issue fields plus a `comments: list[Comment]`. Kept distinct from the lightweight list `Issue` so that `issue list` stays lean.

### Formatters

- `format_comment(...)` / confirmation strings for `issue comment` and `issue link`.
- `format_issue_detail_table(...)` and `format_issue_detail_json(...)` for `issue show`, rendering the body and the comment list together. JSON variants reuse the existing `asdict` + `json.dumps(..., indent=2)` convention.

### CLI surface (noun-first `youtrack issue <verb>`)

- `issue create ... --parent <epic-id>` — new optional flag.
- `issue link <child-id> --parent <epic-id>` — new command.
- `issue comment <id> --message <text>` — new command.
- `issue update <id> [--description <text>] [--summary <text>]` — new command.
- `issue show <id> [--json]` — new command.
- `issue list ... --unresolved --top <n>` — new flags (`--top` default 50).

### Skills (in scope)

- `to-prd`: publish the PRD with `issue create --type Epic --description <prd>` and emit the resulting Epic short ID.
- `to-issues`: accept a PRD Epic short ID as its argument and pass `--parent <epic-id>` to each child `issue create`.
- (Follow-up, not this PRD: reword the Ralph-loop prompt step 4 to steer agents to `issue comment` rather than "update the PRD".)

### API contracts (abstract — exact field selectors live in code)

- Subtask link: created via YouTrack's issue-links/commands mechanism so that the child gains a `subtask of` relationship to the parent Epic.
- Comment: created via the issue comments collection; response carries id, text, author, and created timestamp.
- Update: full replace of `description`/`summary` on the issue resource.
- Show: a single issue fetch whose field selector includes `description` and a `comments(text,author(login,name),created)` projection.
- List cap/filter: `$top` for the cap; `#Unresolved` merged into the `query`.

## Testing Decisions

**What makes a good test here:** assert external behaviour, not internals. Following the existing prior art in `tests/test_issues.py`, each test mocks `YouTrackClient` (via `MagicMock(spec=YouTrackClient)`), drives the function, and asserts (a) the exact `_request` calls made — method, URL, and JSON/params payload — and (b) the parsed return value. Error paths assert that `YouTrackAPIError` (or a usage error) is raised and that no mutating `POST` is issued when validation fails early (see `test_create_issue_tag_not_found`, which asserts no `POST` occurs). Formatter tests assert exact rendered strings for both populated and empty inputs (see `test_format_issue_types_table_*`).

**Modules to test:**

- `link_subtask` — issues the correct link request for child→parent; surfaces API errors.
- `create_issue` with `parent` — after creation, makes the link call with the new issue's ID; when linking fails the creation call still happened (partial-failure path).
- `add_comment` — posts the message to the correct issue and returns a parsed `Comment`; does **not** issue any description read/write.
- `update_issue` — full-replace request for `--description` and `--summary` (and combined); raises a usage error with no API call when neither field is given.
- `show_issue` — single request with the description+comments field selector; parses an `IssueDetail` with its comment list (including the empty-comments case).
- `list_issues` with `unresolved` — `#Unresolved` is merged into the query string alongside existing filters (extends `test_list_issues_query_merging`).
- `list_issues` with `top` — `$top` is sent with the default 50, with an explicit value, and omitted/uncapped when `top=0`.
- Formatters — `format_issue_detail_table`/`_json` and the comment/link confirmation strings, for populated and empty inputs.

**Prior art:** `tests/test_issues.py` (mock-client request/payload assertions, error-path assertions, query-merging assertions) and the formatter string tests at the bottom of that file. New tests should mirror these patterns directly.

## Out of Scope

- A standalone `prd` noun/entity or command — a PRD is just an Epic issue.
- Sibling `depends on` / "Blocked by" links between issues — remains prose-only in the issue template.
- Appending to an issue description (read-modify-write merge) — `issue update` is a deliberate full replace; appending notes is what `issue comment` is for.
- Editing or deleting existing comments — comments are append-only in this scope.
- Multi-level Epic nesting beyond a single PRD→issue parent/child layer.
- Rewording the Ralph-loop prompt (noted as a follow-up, tracked separately).
- Filtering by parent Epic on `issue list` (e.g. "all children of YTCLI-50") — not requested; the Epic's own subtask panel and `issue show` cover the immediate need.

## Further Notes

- Empirically verified against the `YTCLI` project: type `Epic` exists; the unresolved States are `Submitted` (default for new issues), `Open`, `In Progress`, `To be discussed`, `Reopened`, and the resolved States are `Can't Reproduce`, `Duplicate`, `Fixed`, `Won't fix`, `Incomplete`, `Obsolete`, `Verified`. This is why `--unresolved` keys off `isResolved`/`#Unresolved` rather than any single state name.
- This change is a natural set of tracer-bullet vertical slices (each new command = schema/function + formatter + CLI verb + tests). Suggested slice order: `link_subtask` + `issue link` → `--parent` on `issue create` → `issue comment` → `issue show` → `issue update` → `issue list --unresolved`/`--top` → skills wiring.
- Decisions are recorded in `CONTEXT.md` and `docs/adr/0001`–`0003`.
