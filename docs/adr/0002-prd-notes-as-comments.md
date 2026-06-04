# PRD progress notes are comments, not description edits

The workflow (including the Ralph loop's "update the PRD with the work that was done" step) repeatedly appends notes to a PRD as work proceeds. We split this into two separate commands: `issue comment` (append-only, timestamped) is the default for recording progress, and `issue update --description/--summary` (full replace, YouTrack-native) is a deliberate escape hatch for genuinely revising the PRD body.

## Considered Options

- **Description edit only** — rejected as the default: a full-replace body edit forces an LLM agent to read-modify-write, and a single mistake wipes the entire PRD.
- **Comment only** — rejected: sometimes the PRD spec itself must change, which a comment can't do.

## Consequences

- Agents should be steered onto `issue comment` for notes; the Ralph prompt's step 4 maps to it (a future prompt reword may make this explicit).
- `issue show` returns the Epic's description plus all comments in one call, so an agent resuming a PRD reads the spec and the running notes together.
