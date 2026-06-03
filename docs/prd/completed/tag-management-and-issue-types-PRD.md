# PRD: Tag Management and Issue Types

## Problem Statement

When using automated tools (such as the `to-issues` skill) to create issues in YouTrack, users need to assign tags like `AFK` and `HITL` at creation time and discover what issue types are available in a project. Currently:

- `youtrack issue create` does not accept a `--tag` flag, so tagging requires a separate `youtrack issue tag` command after creation — a two-step process that is fragile in scripts.
- There is no `youtrack tag list` command, so users cannot verify which tags exist before attempting to assign them.
- While `youtrack issue create --type` already accepts a type value, there is no command to list the valid type values for a given project, forcing users to guess or check the YouTrack UI.

## Solution

Add three capabilities to the YouTrack CLI:

1. [x] **`youtrack tag list`** — list all tags visible to the authenticated user, so scripts and skills can verify tag existence before assignment.
2. [x] **`--tag` flag on `youtrack issue create`** — apply one or more existing tags atomically at issue creation time, in a single command.
3. [x] **`youtrack issue types --project X`** — list the valid issue type values configured for a project, so users can pass the correct value to `--type`.

## User Stories

1. [x] As a developer using the `to-issues` skill, I want to create an issue and tag it with `AFK` in one command, so that I don't have to manage a two-step create-then-tag flow in my scripts.
2. [x] As a developer using the `to-issues` skill, I want to create an issue and tag it with `HITL` in one command, so that issues requiring human interaction are correctly labelled without extra steps.
3. [x] As a developer, I want to apply multiple tags to an issue at creation time, so that issues can be categorised across multiple dimensions from the start.
4. [x] As a developer, I want a clear error message when a tag I try to assign does not exist, so that I know exactly which tag to create first.
5. [x] As a developer, I want to list all available tags, so that I can verify a tag exists before trying to assign it.
6. [x] As a developer, I want the tag list output as a human-readable table by default, so that I can quickly scan it in the terminal.
7. [x] As a developer, I want the tag list output as JSON with `--json`, so that I can parse it in scripts.
8. [x] As a developer, I want to list the issue types configured for a project, so that I can know which values are valid for `--type` on `issue create`.
9. [x] As a developer, I want the issue types list output as a human-readable table by default, so that I can scan it easily.
10. [x] As a developer, I want the issue types list output as JSON with `--json`, so that I can parse it in scripts.
11. [x] As an automated agent, I want to create an issue with a type and tags in a single command invocation, so that issue creation is atomic and idempotent in scripts.
12. [x] As a developer, I want the tag and type listing commands to follow the same output pattern as `issue list` and `project list`, so that the CLI feels consistent.

## Implementation Decisions

### Modules to build / modify

**`tags.py`**
- Add `list_tags(client) -> List[Tag]` — calls `GET api/tags?fields=id,name` and returns all tags visible to the authenticated user. (The `Tag` dataclass already exists.)

**`issues.py`**
- Modify `create_issue(...)` to accept an optional `tags: Optional[List[str]] = None` parameter (list of tag names).
- Before POSTing the issue, resolve each tag name to its ID by fetching `GET api/tags?fields=id,name`. If any name is not found, raise `YouTrackAPIError` with the message: `Tag '{name}' not found. Create it first with: youtrack tag create --name {name}`.
- Include resolved tag IDs in the POST body as `"tags": [{"id": "..."}, ...]`.
- Add `list_issue_types(client, project_short_name) -> List[str]` — resolves the project ID (same lookup as `create_issue`), then calls `GET api/admin/projects/{projectId}/customFields?fields=field(name),bundle(values(name))`, filters for the custom field whose `field.name == "Type"`, and returns the list of value name strings from `bundle.values`.

**`formatters.py`**
- Add `format_tags_table(tags: List[Tag]) -> str` — single-column table of tag names, consistent with `format_projects_table`.
- Add `format_tags_json(tags: List[Tag]) -> str` — JSON array.
- Add `format_issue_types_table(types: List[str]) -> str` — single-column table of type names.
- Add `format_issue_types_json(types: List[str]) -> str` — JSON array of strings.

**`cli.py`**
- Add `youtrack tag list [--json]` command under the existing `tag` group.
- Add `--tag` (repeatable, `multiple=True` in Click) to `issue create`. Passes collected names as a list to `create_issue`.
- Add `youtrack issue types --project X [--json]` command under the existing `issue` group.

### Key behavioural decisions

- **Tag resolution on `issue create`**: tags are resolved by name before the issue POST. If any tag is missing the whole command fails before creating the issue — no partial state.
- **Fail-fast with actionable message**: the error message for a missing tag names the exact `youtrack tag create` command the user needs to run.
- **Single API call for tag lookup**: when multiple `--tag` values are given, all names are resolved in a single `GET api/tags` call (fetch once, look up all names in-memory).
- **Issue types are project-scoped**: `youtrack issue types` requires `--project` because type values differ per project.
- **No auto-creation of tags**: consistent with the existing `issue tag` command and CONTEXT.md — the CLI never creates a tag implicitly.

## Testing Decisions

Good tests in this codebase verify the external behaviour of each module function against a mocked `YouTrackClient._request`. They assert exact call signatures (method, URL, params/json) and exact return values, without testing internal loops or conditionals directly. See `test_issues.py` and `test_tags.py` for prior art.

### Modules to test

**`tags.py` — `list_tags`**
- Returns a `List[Tag]` parsed from the API response.
- Makes exactly one `GET api/tags?fields=id,name` call.

**`issues.py` — `create_issue` with tags**
- With one `--tag`: fetches tags, resolves the ID, includes `"tags"` in the POST payload.
- With multiple `--tag` values: single tag-fetch call, all IDs included.
- Tag not found: raises `YouTrackAPIError` with the expected message before POSTing the issue.

**`issues.py` — `list_issue_types`**
- Returns a list of type name strings from the custom fields response.
- Project not found: raises `YouTrackAPIError`.
- Project has no Type custom field: returns an empty list.

**`formatters.py`**
- `format_tags_table`: empty list returns a "No tags found." message; non-empty list includes a header and one row per tag.
- `format_issue_types_table`: empty list returns "No types found."; non-empty list shows each type name.
- JSON variants produce valid JSON with the expected shape.

## Out of Scope

- Auto-creating tags when they don't exist during `issue create`.
- Deleting or renaming tags.
- Listing tags scoped to a specific project (YouTrack tags are global, visible to the authenticated user).
- Managing other custom field value lists beyond issue types (e.g., listing valid Priority or State values).
- Multi-select tag filtering on `issue list` (the existing single `--tag` filter is unchanged).

## Further Notes

- The `to-issues` skill that motivated this PRD should be updated after implementation to use `youtrack issue create --tag AFK` (or `--tag HITL`) directly, and to call `youtrack tag create` first if the tag may not exist.
- The YouTrack REST API endpoint for project custom field bundles may vary between self-hosted and Cloud instances — the implementation should be tested against the target instance.
