# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-06-10

### Added
- Added pure subtask links parser `parse_subtask_links` in `src/youtrack_cli/issues.py` to extract parent and subtasks from the API payload.
- Added `parent` and `subtasks` fields to `IssueDetail` dataclass and populated them during `show_issue` calls.
- Extended the human-readable detail table formatter `format_issue_detail_table` in `src/youtrack_cli/formatters.py` to display the `Parent:` line and the `Subtasks:` section.
- Added comprehensive unit and integration tests in `tests/test_issues.py` to verify subtask parsing, show command integration, and detail table/JSON formatting.

## [1.0.1] - 2026-06-10

### Added
- Created a new startup chokepoint console helper in `src/youtrack_cli/console.py` to reconfigure standard streams (`stdout`, `stderr`) to use UTF-8 output encoding unconditionally.
- Added graceful guard clauses to prevent failures when reconfiguring streams that do not support `.reconfigure` or when `ValueError`/`OSError` exceptions are raised during stream reconfiguration.
- Added comprehensive unit and regression tests in `tests/test_console.py` to verify the reconfigure behavior and ensure non-cp1252 characters (e.g. `→`) print correctly and do not crash on legacy Windows consoles.

### Changed
- Integrated stream reconfiguration on startup inside the main command group callback in `src/youtrack_cli/cli.py`.
