# Phase 1: Data Model, Rule Engine, CLI, Excel Export

Read `AGENTS.md` completely before starting. Implement only this phase.

## Goal
A working `studyplan` CLI without AI document import. The student chooses a program from `profiles/`, imports credits deterministically from a saved MyCampus page or enters them manually (directly or through the `/credits` slash command), sees the thesis admission and graduation verdict and exports an Excel workbook. The slash commands `/setup`, `/credits`, `/check` and `/excel` in `.claude/commands/` work end to end against this CLI.

## Step 0: Inventory (no code yet)
1. Read every file in `tests/fixtures/real/` (whatever is present: study regulation, curriculum, model timetable, saved module directory pages, saved MyCampus "Meine Anmeldungen" page, recognition decisions, a planning workbook) and `tests/fixtures/real/NOTES.md` if present.
2. Report: which documents exist, regulation version and intake years, module categories with their exact official names, ECTS values, all rules relevant for thesis admission and graduation with page references, special cases (caps, alternatives, prerequisites, repetition rules, maximum study duration, study interruptions, transition rules between regulation versions, recognized external credits, credits from professional practice, modules that award ECTS only to some students, modules no longer offered).
3. List everything the planned data model below cannot express.
4. List every deviation between the planning workbook and the official documents as a finding.
5. Propose the final data model and wait for confirmation.

## Known Facts from the Fixtures (verify in Step 0, do not hardcode in code)
- The regulation names the module types Core, Core-Project, Related and Minor (Art. 13, Art. 17). The curriculum uses the letters K, P, E, Z and the timetable legend uses Kernmodul, Projektmodul, Erweiterungsmodul. The mapping K=Core, P=Core-Project, E=Related, Z=Minor is an assumption. Report the evidence and mark it `unverified`.
- Art. 33: thesis admission requires at least 132 credits plus "Vorgaben des Studiengangs". These program requirements are not in the regulation. They come from the thesis module description `TA.BA_BAA_DC`. If that file is missing, model them as `custom_note` and list them as an open issue.
- Art. 32 lists the graduation conditions, Art. 15 the repetition rules and the Basic level deadline, Art. 20 Abs. 2 the level gate for Advanced modules, Art. 28 and 29 the maximum study duration and interruptions, Art. 2 and 25 caps for recognized credits.
- The curriculum marks mandatory modules with `X` and electives with `(X)`. Some rows carry remarks (ECTS only for incoming or foreign students, "ab HS26 nicht mehr im Angebot"). These are data, not code.
- Codes differ between documents: curriculum `TA.BA_PYTHON_MM`, timetable `GR-K-TA.BA_PYTHON`, module directory `TA.BA_PYTHON_MM.21`; curriculum `TA.BA_WST+BAS` versus directory `TA.BA_WST+BAS_MM.25`; curriculum `TA.BA_SP1` versus directory `TA.BA_SP1_SZ.08`; curriculum `TA.BA_PRAX_DCA_3` versus directory `TA.BA_PRAX_DCA_3F26.26`. Build `profiles/hslu_ta/code_mapping.yaml` as an explicit, user verifiable table. No silent fuzzy matching.
- The module directory lists some modules twice with different validity periods. Keep both versions and select by semester date.
- The timetable shows ECTS per time slot, not per module (for example `TA.BA_AT_TEAM | 3` twice for a 6 ECTS module). Use the curriculum for ECTS.
- Saved portal pages contain the student's name and lecturer names. Never copy them into anything.
- MyCampus "Meine Anmeldungen" (saved with Ctrl+S) lists one block per registration: an `h2` with title, a table with "ECTS-Punkte" and optional "Bewertung" (grade letter plus text, for example "B sehr gut", "F nicht bestanden"), and a table with "Nummer" (`<code>.<H|F><yy><run>`, for example `.H2502` = HS25), "Dauer" (weekday and time slots) and "Leitung". Codes there carry their own suffixes (for example `_K` where the curriculum has `_MM`). Non-module events without ECTS (for example introduction days) are ignored. Registrations without a grade are running or future modules. A module can appear several times (attempts).
- selectolax 1.0 removed the old `selectolax.parser` backend. Use `selectolax.lexbor.LexborHTMLParser`.
- Recognition decisions can grant lump sums per category without a module code ("Pauschale Modulerlassung im <Bereich>"). The data model must support recognized credits without a module code, with category, basis, decision document and date. If a decision is contradictory (for example the row name points to one category and the type column to another), do not resolve it: keep the category as an open issue and the result `provisional` until the official transcript shows the booking.
- HSLU recognition forms name the areas "Zusatzbereich" (Z) and "Erweiterungsbereich" (E). Together with the timetable legend this supports K=Kern, P=Projekt, E=Erweiterung, Z=Zusatz. The link to the official names Core, Core-Project, Related, Minor stays `unverified`.
- Recognized credits do not count toward `min_ects_at_institution` (Art. 32 d) and are capped by `max_recognized_ects` (Art. 2 Abs. 2: 30 for an HF diploma).
- `tests/fixtures/real/NOTES.md` (gitignored, may be missing) contains findings about the developer's own fixtures. Read it if present. Nothing from it may end up in committed files.

## Decisions after Step 0 (binding)
The Step 0 report lives in `tests/fixtures/real/phase1_inventory.md` (private). Use its data model proposal (section 10), its curriculum table (section 4) and its code mapping candidates (section 5) as the basis. The following decisions answer its open questions:
1. Thesis program requirements: `custom_note` rule `thesis_program_requirements` in the program file until the thesis module description is available.
2. Initial profile scope: only regulation version `bachelor_2025` (Studienreglement vom 1. September 2025) and program `digital_construction_architecture_2025`. The model must allow more versions and intakes later.
3. Category letter mapping K=Core, P=Core-Project, E=Related, Z=Minor is stored with status `unverified`. Every rule that depends on it is therefore `provisional` until the maintainer sets the categories to `verified`. This is intended behavior.
4. Recognized credits count toward the total ECTS and toward their category (Art. 32 a), never toward `min_ects_at_institution`. A recognized credit whose decision is not unambiguous (blank approval boxes, contradictory category) gets `status: provisional`, counts toward the total, and if its category is `null` it counts toward no category. Any goal touched by a provisional recognized credit is at best `provisional`.
5. All code mappings from the report go into `code_mapping.yaml` with status `unverified`. Unverified mappings are used for matching but mark derived results `provisional`. Directory codes that exist in no curriculum (for example `TA.BA_IDENT`, `TA.BA_NANOTECH`, `TA.BA_POLITIK`) are not mapped and are reported as `not_in_curriculum`, not as errors.
6. Overlapping module directory validity rows: select the row whose validity covers the semester start date; if several do, take the one with the latest `valid_from`; an open end date means valid indefinitely.
7. Curriculum titles are stored verbatim, including spelling errors. Matching is by code only.
8. The planning workbook deviation "mind. 54 ECTS" for project modules is the sum of mandatory Core-Project modules (incl. thesis), not the Art. 17 minimum of 39. Report both values, do not treat 54 as a category minimum.

## Data Model
Pydantic v2 models in `src/studyplan/models/`, persisted as YAML. Export JSON Schemas to `schemas/` with `studyplan schema`.

Profile side (`profiles/`, committed):
- `University` (id, name, regulation versions, sources, manual sources with instructions).
- `RegulationVersion` (id, document reference, valid intake years, retrieval date, transition rules as text plus structured link to the previous version).
- `Program` (id, name, specialization, degree, total ECTS, intake year, study modes with standard and maximum duration, regulation version).
- `ModuleCategory` (id, official name, curriculum letter, description, source, verification status).
- `Module` (code, title, ECTS, eligible categories, level, mandatory flag, semesters offered, offering frequency, prerequisites, language, ECTS restriction note, offered until, predecessor and successor codes, source, verification status).
- `Rule` (id, type, parameters, description, source, verification status).
- `CodeMapping` (foreign code, source document, curriculum code, verification status).

Student side (`my_study/`, gitignored):
- `profile.yaml`: university, program id, intake year, study mode, start semester, regulation version, language, interruption semesters.
- `credits.yaml`: module code, semester, ECTS, grade (A to F or pass/fail), passed flag, attempt number, optional forced category with reason, recognized external credit flag with basis and reason.
- `plan.yaml`: planned modules with target semester (phase 4 extends this file).
- `checklist.yaml`: ticks for `custom_note` rules with date and note.

## Rule Types
Implement all with full parameter validation:
- `min_ects_total`
- `min_ects_in_category`
- `max_ects_in_category` (counting cap, ECTS above the cap do not count)
- `required_module`
- `required_all_mandatory` (all modules flagged mandatory in given categories passed)
- `required_one_of`
- `min_modules_in_category`
- `prerequisite`
- `max_attempts` (module failed too often blocks the result)
- `retake_budget` (shared ECTS budget for third attempts across the whole program, with modules excluded from a third attempt)
- `level_gate` (modules of one level may only be taken after all mandatory modules of another level are passed)
- `level_deadline` (all mandatory modules of a level must be passed within n semesters from study start)
- `min_ects_at_institution` (recognized credits excluded)
- `max_recognized_ects` (cap per recognition basis, optionally per study mode)
- `max_study_duration` (per study mode, interruptions excluded, cap on total interruptions)
- `composite` (named goal such as `thesis_admission` or `graduation`, references other rules with AND and OR)
- `custom_note` (not machine checkable, shown as manual checklist item)

## Rule Engine
- Pure Python, package `src/studyplan/engine/`.
- Input: program, rules, modules, categories, student profile, credits, planned modules, checklist.
- Allocation: modules eligible for several categories are assigned with OR-Tools CP-SAT so that each passed module counts once and the number of fulfilled rules is maximized. Ties resolved deterministically. Forced categories are hard constraints. Return the chosen allocation with an explanation per module.
- Two modes: `current` (passed credits) and `forecast` (passed plus planned).
- Result per rule: `fulfilled`, `not_fulfilled`, `provisional` (depends on unverified data), `manual` (custom_note not ticked). With current value, target value and gap text.
- Verdict per goal (`thesis_admission`, `graduation`): `eligible`, `not_eligible` with full gap list, or `provisional`.

## CLI (Phase 1 subcommands from the AGENTS.md contract)
`doctor`, `profiles`, `modules`, `init`, `validate`, `credits add/edit/remove/list`, `check`, `excel`, `backup`, `restore`, `schema`.
- Every read command supports `--json`. The JSON output of `check` is a documented, versioned schema in `schemas/`, because `/check` relies on it.
- `init` takes all choices as options so Claude Code can call it non interactively, and never overwrites existing files.
- `validate` reports file, line and a fix hint for every error.
- `credits import-mycampus <file> [--apply] [--json]`: deterministic local parser for a saved MyCampus "Meine Anmeldungen" page (no AI, no network). Default is a dry run that prints every parsed registration: code as found, mapped curriculum code (through `code_mapping.yaml`), semester, attempt order, ECTS, grade, passed flag, status (`new`, `already_present`, `unmapped`, `ignored_event`, `running`). `--apply` adds only `new` rows through the same validation as `credits add`. Unmapped codes are never guessed. Graded rows become credits with attempt numbers derived from the order of the same module; ungraded rows of the current or a future semester are reported as running and added to `plan.yaml` only with `--apply`. Names of persons are never stored or printed.
- Every output ends with the disclaimer from AGENTS.md.

## Profiles
- `profiles/_template/` with commented example files for a new university.
- `profiles/hslu_ta/university.yaml`, `profiles/hslu_ta/programs/digital_construction_architecture_2025.yaml`, `profiles/hslu_ta/code_mapping.yaml`. Only facts found in the fixtures, each with source reference (document, page, retrieval date) and status `unverified` until the maintainer verifies them. Unknown values stay empty and are listed as open issues.

## Excel Export
Sheets: Overview, Rules, Modules, My Credits, Allocation, Gaps, Sources, Open Issues.
- Overview shows engine results as values with the label "computed by rule engine on <date>".
- My Credits is an Excel table with data validation dropdowns for module code and category. Simple sums per category as formulas.
- Frozen headers, auto filter, column widths, conditional formatting: green fulfilled, red missing, orange provisional, grey manual.
- openpyxl does not compute formulas. Write a parity test that recalculates the file with LibreOffice headless (`soffice --headless --convert-to xlsx`) and compares the sums with the engine. Skip the test if LibreOffice is not installed.

## Launcher
`start.bat`: UTF-8 console, check `uv` and `claude` on PATH (clear message with install link and `pause` if missing), `uv sync`, `uv run studyplan doctor`, then start `claude` in the repository root. Works from a path with spaces and umlauts.

## Tests (Definition of Done)
Synthetic fixtures must cover:
1. Total ECTS reached, one category short: `not_eligible`, gap text names the category and missing ECTS.
2. Module eligible for two categories: solver assigns it to the category where it fulfills a rule.
3. Category cap: ECTS above the cap do not count toward the total.
4. `required_one_of` fulfilled by the second alternative.
5. Failed module with attempts above the limit: `not_eligible`.
6. Recognized external credit with forced category: counted correctly.
7. One relevant rule unverified: verdict `provisional`.
8. Forecast mode: planned modules close all gaps, verdict `eligible` in forecast and `not_eligible` in current.
9. Renamed module: credit for the old code counts for the successor module.
10. Level gate: an Advanced module planned before all Basic mandatory modules are passed triggers a violation.
11. Level deadline: a Basic mandatory module still open after the allowed number of semesters triggers `not_eligible`.
12. Retake budget: third attempts above the shared ECTS budget, or a third attempt on an excluded module, trigger `not_eligible`.
13. Recognized credits do not count toward `min_ects_at_institution`.
14. Interruption semesters do not count toward the maximum study duration.
15. `required_all_mandatory`: one open mandatory Core module blocks `graduation` but not `thesis_admission` if the program rules say so.
16. `init` never overwrites, `validate` reports file and line for a broken YAML file.
17. `check --json` output validates against its schema.
17a. `credits import-mycampus` on a synthetic saved page (invented codes, invented person names): parses grades, semesters from the run suffix and attempts, ignores events without ECTS, reports unmapped codes, never outputs the person names, dry run changes no file, `--apply` is idempotent.
17b. Lump-sum recognized credit without module code counts toward its category, not toward `min_ects_at_institution`, and respects `max_recognized_ects`.
18. Excel file opens, contains all sheets, dropdowns and conditional formatting.

Real fixture tests (`@pytest.mark.real`):
- Load `tests/fixtures/real/golden.yaml` (format in `tests/fixtures/golden_template.yaml`). The engine result must match the expected verdict and the expected missing items exactly. Skip if the file is missing.
- `credits import-mycampus` on the real saved MyCampus page finds every graded registration and maps every curriculum module; output contains no person name from the page.

## Deliverables
Complete code, `pyproject.toml`, `uv.lock`, `start.bat`, profiles, schemas, synthetic fixtures, tests passing, README section for phase 1, list of assumptions and items to verify.
