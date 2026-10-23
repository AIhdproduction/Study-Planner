---
description: Plan your remaining semesters and timetable, find conflicts and the earliest thesis semester
argument-hint: "[what you want to plan, e.g. 'move Bestand to HS28']"
allowed-tools: Bash(uv run studyplan *)
---

Plan the remaining semesters with the student. All checks come from the CLI.

1. If `my_study/plan.yaml` has no generated or manual items yet, explain that a first plan is built from the passed and running modules and the program's model timetable, then run `uv run studyplan plan generate`. Never use `--force` without asking; it replaces generated items (manual ones always stay).
2. Run `uv run studyplan plan --json` and summarize: modules per semester, ECTS per semester and cumulative, retakes, violations (level gate, Basic deadline, offering term), placeholders for missing electives, earliest semester for thesis admission and graduation.
3. If timetables in `my_study/inbox/timetable/` are not imported yet, offer to import them with `uv run studyplan timetable import "<file>"` (ICS, CSV, XLSX; ask the student for the column mapping of CSV and XLSX). PDF timetables go through `/import` first.
4. Apply the student's wishes from $ARGUMENTS or the conversation with `uv run studyplan plan add|move|remove`. Never edit `plan.yaml` by hand. For placeholders ("choose 12 ECTS Related"), show the suggested modules and let the student pick.
5. After every change run `uv run studyplan plan --json` again and report new warnings and conflicts.
6. If gaps remain, run `uv run studyplan suggest --json` and present the suggestions with the semesters they are offered in. Suggestions only; change the plan only when the student agrees.
7. Suggest `/check` with forecast mode and `/excel` at the end; the Excel sheets "Studienplan" and "Semesterübersicht" show the plan with all conditions.
8. End with: "Not legally binding. The official study regulations and the program management decide."
