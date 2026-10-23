---
description: Plan your remaining semesters and timetable, find conflicts and the earliest thesis semester
argument-hint: "[what you want to plan, e.g. 'move Bestand to HS28']"
allowed-tools: Bash(uv run studyplan *)
---

Plan the remaining semesters with the student. All checks come from the CLI.

1. Run `uv run studyplan plan --json` and summarize: modules per semester, ECTS per semester, warnings, timetable conflicts, earliest semester for thesis admission and graduation.
2. If timetables in `my_study/inbox/timetable/` are not imported yet, offer to import them with `uv run studyplan timetable import "<file>"` (ICS, CSV, XLSX; ask the student for the column mapping of CSV and XLSX). PDF timetables go through `/import` first.
3. Apply the student's wishes from $ARGUMENTS or the conversation with `uv run studyplan plan add|move|remove`. Never edit `plan.yaml` by hand.
4. After every change run `uv run studyplan plan --json` again and report new warnings and conflicts.
5. If gaps remain, run `uv run studyplan suggest --json` and present the suggestions with the semesters they are offered in. Suggestions only; change the plan only when the student agrees.
6. Suggest `/check` with forecast mode and `/excel` at the end.
7. End with: "Not legally binding. The official study regulations and the program management decide."
