# UTF-8 output encoding to fix Windows cp1252 UnicodeEncodeError

## Problem Statement

`youtrack issue show <ID>` crashes with `UnicodeEncodeError` on a legacy Windows console (default code page cp1252) whenever the issue text contains a character outside cp1252 — e.g. `→` (U+2192), or any non-Latin-1 glyph, emoji, or box-drawing character. The failure is purely in the output layer. `format_issue_detail_table` emits the issue's summary/description/comment text as raw Unicode, `click.echo` writes it to a stdout stream bound to cp1252, and the underlying `file.write` raises because the glyph is not representable.

`issue show --json` survives only by accident, because `json.dumps` defaults to `ensure_ascii=True` and escapes the offending glyph to plain ASCII.

The same latent bug sits behind every table path — `issue list`, `project list`, `tag list`, and `issue show` — not just the one in the report. The crash also fires on redirection (`... > out.txt`), because a redirected stream uses the locale code page (still cp1252 on Windows), not just on the interactive console.

## Solution

The CLI forces all of its output to UTF-8. At startup it reconfigures standard output and standard error to use UTF-8 encoding with a `backslashreplace` error handler, so:

- non-cp1252 characters (arrows, emoji, accented text, CJK) print correctly on any modern terminal on any OS;
- output is one deterministic encoding everywhere — interactive console, pipe, and redirected file — regardless of platform;
- in the rare case a stream still cannot accept UTF-8, an unrepresentable character degrades to a visible escape (e.g. `\u2192`) instead of crashing the command.

From the user's perspective, `youtrack issue show <ID>` (and every other command) just works on Windows the way it already works on macOS and Linux, with no environment variables, no `chcp`, and no need to drop to `--json`.

## User Stories

1. [x] As a Windows user, I want `youtrack issue show <ID>` to print issues whose text contains `→`, so that I can read the issue instead of getting a traceback.
2. [x] As a Windows user, I want `issue show` to work for issues containing emoji, accented characters, or CJK text, so that international content is never a crash.
3. [x] As a Windows user, I want `youtrack issue list` to render rows whose summaries contain non-cp1252 characters, so that the list view never crashes mid-table.
4. [x] As a Windows user, I want `youtrack project list` and `youtrack tag list` to tolerate non-cp1252 names, so that no table command can crash on a stray glyph.
5. [x] As a user redirecting output to a file (`youtrack issue show <ID> > out.txt`), I want the command to succeed and write UTF-8, so that piping and file capture work the same as on-screen output.
6. [x] As a scripter, I want output encoding to be deterministic and platform-independent, so that downstream tooling reading the CLI's output never has to guess the code page.
7. [x] As a user on a terminal that genuinely cannot display a character, I want it to show as an escape sequence rather than abort the command, so that I still see the rest of the issue.
8. [x] As a user, I want error messages (which may also contain non-cp1252 text from the API) to print rather than crash, so that I can read the error instead of a second traceback.
9. [x] As a macOS/Linux user, I want my existing behavior unchanged, so that the Windows fix does not regress the platforms that already work.
10. [x] As a user, I want `--json` to keep working exactly as before, so that the fix to the table path does not alter the scripting contract.
11. [x] As a maintainer, I want the encoding behavior isolated in one small, testable module, so that I can verify it without spinning up a Windows console.
12. [x] As a maintainer, I want a regression test that reproduces the original cp1252 crash cross-platform, so that the bug can never silently come back.
13. [x] As a maintainer, I want the fix applied at a single startup chokepoint, so that future commands inherit safe output without per-command work.

## Implementation Decisions

- **New deep module `console.py`.** A new module (`src/youtrack_cli/console.py`) encapsulates all output-encoding logic behind a one-call interface. It exposes `_configure_output_encoding()`, which loops over `sys.stdout` and `sys.stderr` and delegates each to a per-stream core, `_reconfigure_stream(stream)`. The per-stream core is separated specifically so tests can drive a single stream directly.
- **UTF-8 + `backslashreplace`.** Each stream is reconfigured with `encoding="utf-8", errors="backslashreplace"`. UTF-8 is the primary fix (deterministic, cross-platform, matches the project's cross-platform goal and `--json`'s already ASCII-safe output); `backslashreplace` is the safety net so no future glyph can crash the CLI even on a stream that cannot take UTF-8.
- **Both streams.** `stderr` is reconfigured as well as `stdout`, because error output (`click.echo(..., err=True)`) can carry API text with the same characters and would crash identically.
- **Unconditional — no `isatty()` gate.** The reconfigure runs whether or not stdout is a terminal, because the crash also occurs on redirect/pipe and scripters want deterministic UTF-8 to files. Gating on `isatty()` would leave the redirect failure mode unfixed and make encoding depend on whether output is piped.
- **Defensive guarding.** `sys.stdout`/`sys.stderr` are not always real `TextIOWrapper` objects (pytest capture, Click's `CliRunner`, already-detached streams). The per-stream core checks for a `.reconfigure` attribute and swallows `ValueError`/`OSError`, leaving a non-reconfigurable stream untouched rather than turning the fix into a new crash.
- **Single wiring point.** `cli.py`'s `main()` Click group callback calls `_configure_output_encoding()` once, before any subcommand runs, so all current and future commands inherit safe output. No formatter changes are needed.
- **No domain-model change.** This is an architecture/output-layer decision, not a new glossary term. It is recorded in `docs/adr/0006-utf8-output-encoding.md` and as an "Output encoding" bullet under Architecture decisions in `CONTEXT.md`; the Language section is unchanged.

## Testing Decisions

- **What makes a good test here:** assert externally observable behavior — that a stream no longer raises on a non-cp1252 character, and that the reconfigure is requested with the agreed parameters — not internal control flow.
- **Module under test:** `console.py` only (the formatters and CLI commands are unchanged in behavior; the single `main()` call is wiring).
- **Layer 1 — guard/behavior unit tests (spy-style):** feed the per-stream core fakes and assert: (a) a stream whose `reconfigure` records its kwargs is called with `encoding="utf-8", errors="backslashreplace"`; (b) a stream with no `.reconfigure` attribute returns cleanly without error; (c) a stream whose `.reconfigure` raises `ValueError`/`OSError` is swallowed.
- **Layer 2 — cp1252 regression test (the headline test):** bind a `TextIOWrapper` to a `BytesIO` with `encoding="cp1252"`, assert that writing `"Pending → Processing"` raises `UnicodeEncodeError` (reproducing the real defect cross-platform), then apply the per-stream reconfigure to a fresh cp1252-bound stream and assert the same write now succeeds.
- **Prior art:** the existing test suite under `tests/` (e.g. `tests/test_cli.py`, `tests/test_issues.py`) uses pytest and Click's `CliRunner` for command-level behavior; the new tests follow the same pytest conventions, exercising the helper directly rather than through the network.

## Out of Scope

- **Surfacing `parent`/`subtasks` in `issue show --json`.** The separately reported gap (the subtask hierarchy created via `--parent` is not exposed in JSON) is a data-model + fetch change intersecting ADR 0001 and the **Subtask link** term. It is being designed and tracked as its own PRD and is explicitly excluded here.
- **ASCII-folding or transliterating issue text** (e.g. `→` to `->`). The offending text is arbitrary user content in any language, so folding cannot be a general fix; it was considered and rejected (see ADR 0006).
- **Changing the `--json` output contract.** JSON is already ASCII-safe via `ensure_ascii=True` and is untouched.
- **Version bump / release.** Versioning is handled at release time, not in this PRD.
