# UTF-8 output encoding for all human-readable output

`youtrack issue show <ID>` crashes with `UnicodeEncodeError` on a legacy Windows
console (default code page **cp1252**) whenever the issue text contains a character
outside cp1252 — e.g. `→` (U+2192), or any non-Latin-1 glyph, emoji, or box-drawing
character. The data and the API call are fine; the failure is purely in the output
layer. `format_issue_detail_table` emits the issue's `summary`/`description`/comment
text as raw Unicode, `click.echo` writes it to a stdout stream bound to cp1252, and
the underlying `file.write` raises because the glyph is not representable.

`issue show --json` survives only **by accident**: `json.dumps` defaults to
`ensure_ascii=True`, so `→` is escaped to `→` and the JSON path is pure ASCII.
The same latent bug therefore sits behind **every** table path — `issue list`,
`project list`, `tag list`, and `issue show` — not just the one in the report. The
crash also fires on **redirection** (`... > out.txt`), because a redirected stream
uses the locale code page (still cp1252 on Windows), not just on the interactive
console.

## Decisions

- **Force UTF-8 on output, globally.** At startup the CLI reconfigures `sys.stdout`
  and `sys.stderr` to `encoding="utf-8"`. This makes Windows behave like macOS/Linux
  and produces one deterministic output encoding everywhere — console, pipe, and
  file — consistent with the project's "cross-platform tool" goal and with `--json`'s
  already-ASCII-safe behavior. `stderr` is included because error messages
  (`click.echo(..., err=True)`) can carry API text with the same characters and would
  crash identically.
- **`backslashreplace` as the safety net.** The reconfigure also sets
  `errors="backslashreplace"`, so a stream that still cannot accept UTF-8 degrades an
  unrepresentable glyph to a visible `→` escape instead of raising. No future
  glyph can crash the CLI.
- **Unconditional — no `isatty()` gate.** The reconfigure runs whether or not stdout
  is a terminal, because the crash also occurs on redirect/pipe and a scripter piping
  to a file wants deterministic UTF-8, not locale-dependent encoding. Gating on
  `isatty()` would leave half the reported failure mode unfixed.
- **Isolated, testable helper.** The logic lives in `src/youtrack_cli/console.py`
  (`_configure_output_encoding()` looping over both streams, delegating to a per-stream
  core `_reconfigure_stream(stream)`), called once from the `main()` Click group
  callback. It is not buried in the CLI callback so it can be unit-tested directly.
- **Defensive guarding.** `sys.stdout` is not always a real `TextIOWrapper` (pytest
  capture, Click's `CliRunner`, already-detached streams). The helper checks for a
  `.reconfigure` attribute and swallows `ValueError`/`OSError`, so a stream that
  cannot be reconfigured is left as-is rather than turning the fix into a new crash.

## Rejected alternatives

- **Keep the console's native encoding, only set `errors="backslashreplace"`.** Avoids
  a crash without forcing UTF-8, but yields escaped/mixed output on legacy consoles and
  keeps output encoding platform-dependent. Rejected in favor of one predictable
  encoding everywhere.
- **ASCII-fold the renderer (`→` → `->`).** The offending text is arbitrary user
  content in any language, so folding CJK/emoji is impossible; this can only sanitize
  CLI chrome, not the data, so it cannot be the primary fix. Rejected.

## Consequences

- No domain-language change: this is an architecture/output-layer decision, not a new
  glossary term. CONTEXT.md gains one **Output encoding** bullet under Architecture
  decisions pointing here; the Language section is untouched.
- On a genuine legacy Windows console, non-cp1252 glyphs may render as mojibake or as
  `\u….` escapes, but the command always completes — degrade, never crash.
- All four table commands are fixed by a single chokepoint; no per-formatter changes
  are needed for the crash.
- Tests cover both the guard branches (spy-style fakes for the call, missing
  `.reconfigure`, and a raising `.reconfigure`) and the genuine defect via a
  cross-platform regression test that binds a `TextIOWrapper` to cp1252, proves `→`
  raises `UnicodeEncodeError`, then proves the reconfigured stream no longer raises.
- Scope is limited to output encoding. The separate observation that `issue show
  --json` omits `parent`/`subtasks` is tracked and designed independently.
