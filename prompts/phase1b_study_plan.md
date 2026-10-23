# Phase 1b: Study Plan (when, which module, what must be passed)

Read `AGENTS.md` completely before starting. Phase 1 is done and its tests pass. Implement only this phase. This phase pulls the semester planner of phase 4 forward, without timetable slots and without ICS, CSV or XLSX timetable import (those stay in phase 4).

## Goal
The student gets a clean Excel list that shows for every module of the program in which semester it is passed, running or planned, and which conditions must be met before it can be taken or before the thesis is admitted. `studyplan plan generate` builds a first plan automatically; the student adjusts it with `/plan`.

## Profile data: model timetable
- Extend the program file with `model_timetables`: per study mode and start term (`HS` or `FS`), the recommended relative semester (1, 2, 3, ...) of each module, with source reference and status `unverified`.
- Extract it for `part_time`, start `HS`, from `tests/fixtures/real/DCA Musterstundenplan Arch Teilzeit.pdf` (public model timetable, 8 semesters). The PDF is a grid with semester columns; use word coordinates (for example pdfplumber or pypdf visitor functions, verify the API) to assign each module code to its semester column. Blockwochen and asynchronous modules listed in the semester headers belong to that semester. Report every module you could not place.
- Electives shown in the model timetable (marked `WAHL`) are recommendations, not mandatory. Store them with `recommended: true`.
- Offering term: a module recommended in semester n of an `HS` start is offered in `HS` if n is odd and in `FS` if n is even. Store this as `offered_terms` with status `unverified` unless the profile already has better data.

## Plan model
`my_study/plan.yaml` holds semester entries from the start semester until the maximum study duration. Each item: module code or placeholder, target semester, status (`passed`, `running`, `planned`, `failed`, `retake`), origin (`credits`, `generated`, `manual`), optional note. Placeholders describe missing electives: category, ECTS still needed, suggested module codes.

## Generator `studyplan plan generate [--current-semester HS26] [--force]`
Deterministic, no AI. Steps:
1. Current semester: from the option, else from today's date (HS from August 1, FS from February 1).
2. Passed credits and running registrations go into their real semesters.
3. A failed module without a later pass gets a retake in the next semester of the same offering term after the failure that is not in the past. Mark it `retake` with the attempt number.
4. Every open mandatory module goes to its recommended semester mapped to the calendar (relative semester 1 = start semester). If that semester is in the past, use the next semester of the same offering term that is not in the past.
5. Level gate: Advanced modules may not be planned before the semester after the last planned Basic mandatory module (including retakes). Shift them to the next matching offering term.
6. Basic deadline: if a Basic mandatory module would end up after the allowed number of semesters, keep it in the earliest possible semester and raise a violation.
7. Thesis: plan it in its recommended semester, but not before the first semester in which the ECTS passed at the start of that semester reach the thesis admission threshold under the plan's forecast. Mark it with the admission condition.
8. Elective gaps: after placing all mandatory modules, compute remaining category gaps with the engine in forecast mode and add placeholders with suggested elective codes (recommended model timetable electives first, then other eligible modules offered in that term), spread over semesters with the lowest planned ECTS.
9. Items with origin `manual` are never moved or removed. Without `--force`, an existing plan with manual items is merged, not replaced.

## Checks `studyplan plan [--json]`
- ECTS per semester and cumulative ECTS; thresholds per study mode from the profile if present, otherwise only shown.
- Module planned in a term where it is not offered.
- Level gate, Basic deadline, retake budget, maximum attempts, maximum study duration.
- Prerequisites from module data; if a module has no description data, the condition says "prerequisites unknown, module description missing".
- Forecast verdict per goal and the earliest semester in which thesis admission and graduation are reached.
- `studyplan plan add|move|remove` edit `plan.yaml` with validation and set origin `manual`.

## Excel
- New sheet "Study Plan" (German "Studienplan"), one row per plan item, sorted by semester then code: semester, code, title, category, level, ECTS, mandatory or elective, status, grade, attempt, condition (plain text built from the rules: level gate with the blocking modules named, Basic deadline semester, retake rules, thesis admission threshold and program requirements, prerequisites or "module description missing"), source. Placeholders as highlighted rows. Status colors: passed green, running blue, planned white, failed red, retake orange, placeholder yellow. Frozen header, auto filter, column widths.
- New sheet "Semester Overview" (German "Semesterübersicht"): per semester ECTS planned and passed, cumulative ECTS, ECTS per category cumulative against the targets, violations count, and a highlighted row for the earliest thesis admission semester. Sums as simple formulas over the Study Plan sheet where transparent; verdict cells as engine values.
- Fix the label bug in gap texts: Core-Project must show the localized display name (German "Projekt"), never a mix such as "Kern-Project".
- All texts localized (en, de).

## Slash command
`.claude/commands/plan.md` is the contract. Phase 1b provides `plan generate`, `plan`, `plan add|move|remove` and `suggest` is optional; `timetable import` stays phase 4 and must report "not available yet".

## Tests (Definition of Done), separate functions, none optional
1. Model timetable extraction from the real PDF (`@pytest.mark.real`): every mandatory module of the curriculum is placed in exactly one semester 1-8; the report lists unplaced modules.
2. Calendar mapping: relative semester to HS/FS for HS and FS starts.
3. Retake placement: module failed in FS26 is planned in FS27 when the current semester is HS26.
4. Past recommended semester moves to the next matching term.
5. Level gate shifts an Advanced module behind the last Basic retake.
6. Basic deadline violation raised when impossible.
7. Thesis not planned before the threshold is reached.
8. Placeholders for category gaps with suggestions; recommended electives first.
9. Manual items survive `generate`; `--force` replaces generated items only.
10. `plan add|move|remove` set origin manual and validate codes and terms.
11. `plan --json` contains per-semester ECTS, cumulative ECTS, violations, earliest admission semester.
12. Excel: both new sheets exist, status colors present, condition texts contain the blocking module names, Semester Overview marks the earliest admission semester, German labels, no "Kern-Project".
13. Real end-to-end (`@pytest.mark.real`): with the real MyCampus page imported into a temporary study folder, `plan generate --current-semester HS26` produces a plan in which the failed Basic module is retaken in the next matching term and no Advanced module is planned before it.

## Deliverables
Complete code, updated profile with model timetable (unverified, sources), updated schemas, tests passing, README section "Study plan", list of assumptions and items to verify.
