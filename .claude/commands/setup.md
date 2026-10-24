---
description: Check your documents and set up your study profile step by step
allowed-tools: Bash(uv run studyplan *)
---

Guide the student through the setup. The student only types `/setup`; you ask for everything else. Do not expect or require any arguments. If the student wrote something after `/setup`, use it only as a hint and still confirm every value.

## 1. Check the environment
Run `uv run studyplan doctor`. If it reports missing prerequisites, explain them in plain words and stop.

## 2. Check the documents
Run `uv run studyplan doctor --inbox --json`. Never list, open or read the files yourself; file names can contain personal data, and the command reports only counts and status.
Show the result as a short table: document, folder, status (present or missing), what it is used for. Then, for every missing item, explain in two or three lines where to get it, how to save it and which folder it goes into:
- Study regulation and curriculum (public PDFs from the university website) -> `my_study\inbox\regulations`
- Model timetable of the program and study mode (public PDF) -> `my_study\inbox\timetable`
- MyCampus page "Meine Anmeldungen": log in yourself in your own browser, remove the semester filter so all semesters are shown, Ctrl+S, "Webpage, complete" -> `my_study\inbox\transcript`
- Official transcript of records (PDF, if available) -> `my_study\inbox\transcript`
- Recognition decisions for earlier education (PDF, if any) -> `my_study\inbox\recognition`
- Module descriptions, at least the bachelor thesis module: open the module detail page, expand all sections, Ctrl+P, "Save as PDF" -> `my_study\inbox\modules`
Tell the student that menu item 1 in `start.bat` opens the inbox folder, that file names do not matter, and that nothing in `my_study` is uploaded. Never ask for passwords and never offer to log in for them.
Ask whether they want to add missing documents first (then wait and run the check again when they say they are done) or continue without them. Only the MyCampus page is recommended for a useful result; everything else is optional at this stage.

## 3. Existing profile
If `my_study/profile.yaml` already exists, run `uv run studyplan validate`, summarize the stored profile and ask whether to keep it. `init` never overwrites; to start over the student must rename or delete the file themselves.

## 4. Ask the profile questions
Run `uv run studyplan profiles --json` and offer only what is listed there. Ask one question at a time and offer the listed options as choices:
1. University
2. Program and specialization
3. Intake year (the year they started)
4. Study mode (full time, part time, extra occupational)
5. Start semester (HS or FS plus year)
6. Semesters of interruption so far, if any
7. Language for reports (German or English)
If their program is not listed, explain that a program file must be created first from the official regulation and curriculum (phase 2, `/import`) and stop.

## 5. Create the profile
Run `uv run studyplan init` with all answers as options, then `uv run studyplan validate`, and report the result in one or two sentences.

## 6. Next steps
Based on the document check, suggest the next command:
- MyCampus page present: `/credits` to import the grades.
- Recognition decision present: `/credits` to record the recognized credits.
- Then `/plan` for the semester plan and `/excel` for the workbook.

End with: "Not legally binding. The official study regulations and the program management decide."
