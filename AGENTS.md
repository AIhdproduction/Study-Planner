# AGENTS.md

Persistent rules for every task that changes code or data in this repository. Read this file completely before any work.

Students who only use the planner do not need this file. Their workflow is in `CLAUDE.md` and `.claude/commands/`.

## Project
Open source study planner that students clone from GitHub and drive with Claude Code. It checks whether a student meets all requirements for bachelor thesis admission and graduation, plans the remaining semesters and timetable, and writes a clean Excel workbook. Universal design, first profile: HSLU Technik & Architektur (Lucerne University of Applied Sciences and Arts, School of Engineering and Architecture), program selectable, primary test case: Digital Construction, specialization Architecture, intake 2025.

### Claude-Code-first architecture
- The repository is a clean template. Each student clones it, puts personal documents into `my_study/inbox/` and works through slash commands in Claude Code (`/setup`, `/credits`, `/check`, `/excel`, `/missing`, `/import`, `/update`, `/plan`).
- Claude Code is the user interface and the document reader. It talks to the student, reads documents the student consented to, and writes draft YAML files.
- A Python command line tool `studyplan` is the single source of truth for every verdict. Slash commands only call it, read its output and explain it. Claude Code never computes a verdict, a sum or an allocation itself.
- There is no web UI and no database. All state lives in human readable YAML files validated by Pydantic.

The work is split into four phases plus phase 1b (study plan, pulled forward from phase 4). Each phase has its own prompt in `prompts/`. Only implement the phase you are asked for. Never implement features of later phases in advance, but keep interfaces open for them.

## Working Rules
- Deliver complete files. No placeholders, no TODOs, no omitted code, no "rest unchanged".
- Before using a library API or CLI flag, verify the current version and API in official docs or via `--help`. No deprecated APIs.
- If information is missing or ambiguous, stop and list the questions. Do not guess. Never invent regulation values, ECTS numbers, module codes or category names.
- Start each phase with a written plan (files, data structures, tests, open questions). Wait for confirmation before implementing. A task brief that contains the line `Plan approved: proceed without asking.` counts as that confirmation: do the work in the same run and list the plan in your final report.
- After each implementation step run `uv run ruff check`, `uv run ruff format --check` and `uv run pytest`. Fix all failures before continuing.
- End each phase with: list of changed files, test results, assumptions made, items the user must verify.
- The slash commands in `.claude/commands/` are the contract between Claude Code and the CLI. The CLI must provide every subcommand, option and output field a command file uses. If a command file needs a change, report it instead of silently diverging.

## Tech Stack (fixed)
- Python 3.12+, managed with `uv` (`pyproject.toml` and `uv.lock` committed). Package in `src/studyplan/`, console script `studyplan`, run as `uv run studyplan ...`.
- CLI: Typer. Console output: Rich, with a `--json` option on every read command for machine readable output.
- Data files: YAML via ruamel.yaml (round trip, keeps user comments). Validation: Pydantic v2. JSON Schema exported from the Pydantic models.
- Excel: openpyxl.
- Allocation solver: OR-Tools CP-SAT.
- PDF: pypdf. HTML: selectolax. HTTP (phase 3 only): httpx. Calendar: icalendar.
- Tests: pytest. Lint and format: ruff. Type hints everywhere.
- Code, identifiers, comments and logs in English. CLI messages and Excel output in English and German via an i18n dictionary (`--lang en|de`, default from `my_study/profile.yaml`).

## Architecture Principles
- The rule engine (`src/studyplan/engine/`) is pure Python, has no I/O dependencies and is fully unit tested.
- Excel is a report. It shows engine results as values and uses formulas only for simple, transparent sums the user edits. A parity test guarantees both match.
- University specific knowledge lives only in `profiles/` and in the slash command texts. No university logic in Python code.
- Module categories are data, never hardcoded enums. Category names come from the official regulations.
- A module may qualify for several categories but counts only once. Allocation is solved as an optimization problem, never greedily.
- Every rule and module carries a source reference (document, URL or file, page, version, retrieval date) and a verification status (`unverified`, `verified`, `edited`).
- Regulations depend on the student's intake year. Always store which regulation version and which curriculum apply.
- Data written by Claude Code (imports) always lands in `my_study/imports/` as a draft first. Only `studyplan accept` merges drafts after the student confirmed them. Nothing overwrites `verified` or `edited` items without explicit confirmation.

## CLI Contract
| Subcommand | Phase | Purpose |
|---|---|---|
| `studyplan doctor` | 1 | Check prerequisites (Python, uv, optional LibreOffice) and the `my_study/` layout. |
| `studyplan doctor --inbox [--json]` | 1 | Document check for `/setup`: per expected document present or missing, counts only, never file names. |
| `studyplan guide [--lang] [--output]` | 1 | Print the student workflow (documents, commands, result) for copying. |
| `studyplan profiles` | 1 | List available universities, programs, intake years and study modes from `profiles/`. |
| `studyplan modules [--search <text>] [--category <id>]` | 1 | List or search the modules of the student's program (code, title, type, level, ECTS, mandatory). |
| `studyplan init` | 1 | Create `my_study/profile.yaml`, `credits.yaml`, `plan.yaml`, `checklist.yaml` for the chosen program. Never overwrites existing files. |
| `studyplan validate` | 1 | Validate all YAML files in `my_study/` and `profiles/` against the schemas. Errors with file, line and fix hint. |
| `studyplan credits add/edit/remove/list` | 1 | Manual credit entry with validation against the curriculum (unknown code, duplicate, wrong ECTS). |
| `studyplan credits recognize add/list/remove` | 1 | Recognized credits from earlier education, with or without module code, status confirmed or provisional. |
| `studyplan credits import-mycampus <file> [--apply]` | 1 | Deterministic local import of a saved MyCampus "Meine Anmeldungen" page. Dry run by default. |
| `studyplan check --mode current\|forecast` | 1 | Rule engine verdict, rule results, allocation with explanation, gap list, manual checklist. |
| `studyplan excel` | 1 | Write `my_study/output/study_plan_<YYYY-MM-DD>.xlsx`. |
| `studyplan backup` / `studyplan restore <file>` | 1 | JSON backup of the complete student state in `my_study/backups/`. |
| `studyplan schema` | 1 | Export JSON Schemas to `schemas/` (committed) for Claude Code imports. |
| `studyplan missing` | 2 | Checklist of module descriptions still to save (mandatory plus planned modules) with code, title and portal search term. |
| `studyplan inbox` | 2 | List inbox files with detected type and processing status. |
| `studyplan parse-modules` | 2 | Deterministic parse of saved module pages into drafts. |
| `studyplan redact <file>` | 2 | Write a redacted text version of a transcript or recognition decision to `my_study/imports/redacted/`. |
| `studyplan diff <draft>` / `studyplan accept <draft>` | 2 | Show and merge a draft after confirmation. |
| `studyplan consent log --file <name> --decision yes\|no` | 2 | Append a consent decision to `my_study/logs/consent.log`. |
| `studyplan fetch` / `studyplan report` | 3 | Fetch public program documents and show the change report. |
| `studyplan plan generate` | 1b | Build a first semester plan from credits, running modules and the model timetable. |
| `studyplan plan` / `studyplan plan add\|move\|remove` | 1b | Check `plan.yaml` (ECTS per semester, offering terms, level gate, deadlines, earliest admission semester) and edit it. |
| `studyplan timetable import <file>` | 4 | Import ICS, CSV, XLSX timetables. |
| `studyplan suggest` | 4 | Gap closing suggestions; timetable conflicts added to `studyplan plan`. |

Exit codes: `0` success, `1` validation or rule errors found (output still complete), `2` usage or file errors.

## Data Protection and Legal
- Grades, transcripts and recognition decisions are personal data. They stay local in `my_study/`, which is gitignored except for its empty folder skeleton.
- Never request, store or transmit passwords. Never access pages behind a login. Never automate a login. This also applies to Claude Code with browser tools.
- Login protected sources are captured only by the student: the student opens the page in their own browser and saves it as HTML (Ctrl+S, complete page) or PDF (Ctrl+P) into `my_study/inbox/modules/`. For HSLU this is the module directory `modulverzeichnis.hslu.ch` (login required, crawlers disallowed in robots.txt) and ILIAS. Neither the CLI nor Claude Code fetches these pages.
- `studyplan missing` tells the student exactly which pages to save.
- Reading a file in Claude Code sends its content to Anthropic. Slash commands ask for consent per file before reading. Transcripts and recognition decisions are only read in their redacted form from `studyplan redact`. `.claude/settings.json` denies direct reads of `my_study/inbox/transcript/` and `my_study/inbox/recognition/`.
- Consent decisions are logged with timestamp in `my_study/logs/consent.log`.
- Official documents and the maintainer's real fixtures are never committed. Extracted facts (codes, ECTS, rules) with source references may be committed in `profiles/`. Respect robots.txt, rate limit requests, use a clear user agent.
- CLI output and Excel always show: "Not legally binding. The official study regulations and the program management decide."

## Profiles
```
profiles/
  _template/                          copy to start a new university
  hslu_ta/
    university.yaml                   regulation versions, categories, rules, sources, manual_sources
    programs/
      <program>_<specialization>_<intake>.yaml   curriculum: modules, types, levels, ECTS, mandatory flag, program rules
    code_mapping.yaml                 timetable and module directory codes to curriculum codes, each entry verifiable
```
The maintainer extracts and verifies the profile once per program and intake year. Students of a covered program reuse it. Students of other programs create a new program file with `/import`.

## Test Fixtures
- `tests/fixtures/real/` contains a developer's own real documents (for example regulation, curriculum, model timetable, saved portal pages, recognition decisions, a planning workbook, `golden.yaml`, and a local `NOTES.md` with findings). It is gitignored. Nothing about the person behind these files may appear in committed files. Tests using it are marked `@pytest.mark.real` and skip cleanly when files are missing.
- `tests/fixtures/synthetic/` contains small invented test data. Committed. Every rule type and edge case must be covered here.
- `tests/fixtures/golden_template.yaml` defines the format of `tests/fixtures/real/golden.yaml`.
- Before designing the data model, read and inventory all files in `tests/fixtures/real/`. Report structure, module types, category names, rule wording and anything that does not fit the planned model.
- A student's own planning workbook, if present, is known to contain errors (wrong sums, outdated module list, module names instead of codes, deviating names). It is input data to be corrected by the tool, never a reference for expected results. Report every deviation between the workbook and the official documents as a finding.
- Expected results in `golden.yaml` come only from official documents (regulation, curriculum, official transcript, recognition decision), never from the planning workbook.
- Timetable codes carry a department prefix and type letter (for example `DCA-K-`, `DCS-P-`, `A-K-`, `G-K-`, `B-E-`, `GR-K-`, `IA-K-`). Strip them before matching. Module directory codes carry a version suffix (for example `.21`). Codes may also differ by suffixes such as `_MM` or `_SZ`. Match only by code, never by title alone, never by silent fuzzy matching:
  1. Strip the documented source pattern: `mycampus` trailing run suffix `.<H|F><yy><run>` (for example `.H2601`); `module_directory` trailing version suffix `.<nn>` (for example `.21`); `timetable` leading department and type prefix (for example `DCA-K-`). The result is the code stem.
  2. If the stem is identical to a curriculum code, it matches directly.
  3. Otherwise only an explicit entry in `code_mapping.yaml` for this source and stem maps it. No entry means `unmapped`.

`code_mapping.yaml` format (stems only, never run or version suffixes; `curriculum_code: null` means "exists in the source but not in this curriculum"):
```yaml
mappings:
  - source: mycampus            # mycampus | timetable | module_directory
    foreign_code: TA.BA_DATA1_K # stem after step 1
    curriculum_code: TA.BA_DATA1_MM
    source_document: {document: "MyCampus Meine Anmeldungen", page: null}
    evidence: "Same module title in source and curriculum."
    verification_status: unverified
```
Synthetic test data never goes into `profiles/`; tests use their own profile folder via `--profiles-dir`.
- Saved portal pages contain the student's name and lecturer names. Never copy them into synthetic fixtures, logs, profiles or exports.

## Windows Requirements
- Paths with spaces and umlauts must work. Use `pathlib` everywhere.
- Console output UTF-8 (`chcp 65001` in batch files, `PYTHONUTF8=1`).
- Batch files never install anything silently. Missing prerequisites produce a clear message with the install link and `pause`.

## Project Structure
```
start.bat                 checks uv and Claude Code, runs uv sync and doctor, starts Claude Code
pyproject.toml
uv.lock
AGENTS.md                 rules for development
CLAUDE.md                 rules for Claude Code when a student uses the planner
README.md
.claude/
  settings.json           project permissions (privacy deny rules)
  commands/               slash commands, the student workflow
src/studyplan/
  cli.py                  Typer entry point
  engine/                 rule engine and allocation solver
  models/                 Pydantic schemas
  io/                     YAML load and save, profile loading
  importers/              manual entry, module page parser, redaction, drafts, ICS
  exporters/              Excel, JSON backup
  fetch/                  public source crawler (phase 3)
  i18n/
schemas/                  exported JSON Schemas
profiles/
my_study/                 personal data, gitignored, only the folder skeleton is committed
  profile.yaml  credits.yaml  plan.yaml  checklist.yaml
  inbox/regulations/  inbox/modules/  inbox/transcript/  inbox/recognition/  inbox/timetable/
  imports/  output/  logs/  backups/
sources/                  downloaded public documents (phase 3), gitignored
prompts/                  phase prompts for development
tests/
  fixtures/real/          gitignored
  fixtures/synthetic/
  fixtures/golden_template.yaml
```
