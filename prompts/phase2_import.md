# Phase 2: Document Import through Claude Code

Read `AGENTS.md` completely before starting. Phase 1 is done and its tests pass. Implement only this phase.

## Goal
The student drops documents into `my_study/inbox/` (regulations, curricula, saved module descriptions, transcript, recognition decision). The student's own Claude Code session extracts them into draft YAML files through the `/import` slash command. The CLI parses what it can deterministically, redacts personal data, validates drafts, shows diffs and merges only after confirmation. `/missing` tells the student which module pages to save.

There is no headless `claude -p` subprocess. The interactive session the student already runs does the reading. The CLI never calls an AI service.

## Inbox Layout
- `my_study/inbox/regulations/`: study regulations and curricula (PDF).
- `my_study/inbox/modules/`: module descriptions saved by the student from the login protected module directory (HTML via Ctrl+S or PDF via Ctrl+P).
- `my_study/inbox/transcript/`: official transcript (PDF).
- `my_study/inbox/recognition/`: recognition decisions (PDF).
- `my_study/inbox/timetable/`: timetables, used in phase 4.

## CLI (Phase 2 subcommands from the AGENTS.md contract)
- `studyplan missing [--json]`: all mandatory modules of the program plus all planned modules whose description is not yet in the inbox or is outdated. Columns: code, title, status (`missing`, `saved`, `extracted`, `verified`, `outdated`), search term for the portal. A saved page older than the current semester is `outdated`.
- `studyplan inbox [--json]`: every inbox file with detected type (regulation, curriculum, module description, module list, transcript, recognition, timetable, unknown), SHA-256 hash, processing status.
- `studyplan parse-modules`: parse saved HTML with selectolax and PDF text with pypdf deterministically. Extract per module: code, title, ECTS, type, level, semester offered, prerequisites (Eintrittsvoraussetzungen), assessment form, language, validity period, each field with file name and source excerpt under 15 words. Fields the parser cannot find are listed in the draft as `needs_agent` so `/import` can fill them. Strip personal data and portal navigation (user name, student ID, session elements) before writing the draft.
- `studyplan redact <file>`: extract text from a transcript or recognition decision, remove name, student ID, date of birth and address, write the result to `my_study/imports/redacted/<name>.txt` and print what was removed by category (never the removed values).
- `studyplan validate <draft>`: validate a draft against the schemas from phase 1. On error print a compact error list that Claude Code can use for exactly one correction attempt.
- `studyplan diff <draft> [--json]`: new, changed and removed categories, modules, rules and credits compared with the accepted state.
- `studyplan accept <draft> [--items ...] [--all]`: merge accepted items. Imported items get status `unverified`. Nothing overwrites `verified` or `edited` items unless the item is named explicitly. Credits from transcripts are merged per row.

## Drafts
- Location `my_study/imports/<YYYY-MM-DD_HHMMSS>_<type>.yaml`. Each draft records input file names and hashes, the extraction method (`parser` or `agent`), and `open_issues`.
- Every extracted item carries file name, page number and a short source excerpt under 15 words.
- Missing values are `null` and go into `open_issues`. Never estimated.
- Program drafts identify the regulation version and the intake years it applies to.
- Transcript drafts contain module code, title, semester, ECTS, grade, passed flag, attempt. No personal data.

## Slash Commands
`.claude/commands/import.md` and `.claude/commands/missing.md` are the contract. The CLI must provide every option and output field they use. Privacy rules in those files (consent per file, redaction first, consent log) are mandatory.

## Privacy
- Consent decisions are written by `studyplan consent log --file <name> --decision yes|no` to `my_study/logs/consent.log` with timestamp. Add this subcommand.
- `.claude/settings.json` denies direct reads of `my_study/inbox/transcript/` and `my_study/inbox/recognition/`. Verify the rule syntax against the current Claude Code permission docs.

## Tests (Definition of Done)
- Module page parser extracts all fields from a synthetic saved HTML page and a synthetic PDF, and marks missing fields as `needs_agent`.
- Parser and redaction remove a synthetic user name, student ID and date of birth.
- `missing` lists mandatory modules without a saved page, marks an old page as `outdated`, and hides verified ones.
- `validate` on an invalid draft returns exit code 1 and a compact error list.
- `diff` detects new, changed and removed items correctly.
- `accept` never overwrites verified items without explicit naming.
- Inbox type detection for every inbox folder plus an unknown file.
- Real fixture test (`@pytest.mark.real`): `parse-modules` on `tests/fixtures/real/modulverzeichnis.hslu.ch.html` finds the listed module codes and never outputs the student's name.

## Deliverables
Complete code, tests passing, README section for phase 2, assumptions and items to verify.
