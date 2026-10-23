---
description: Set up your study profile (university, program, intake year, study mode)
allowed-tools: Bash(uv run studyplan *)
---

Set up the student's study profile.

1. Run `uv run studyplan doctor`. If it reports missing prerequisites, explain them and stop.
2. If `my_study/profile.yaml` already exists, show its content with `uv run studyplan validate` and ask whether the student wants to keep it. `init` never overwrites; to start over the student must rename the file themselves.
3. Run `uv run studyplan profiles --json` and offer only the universities, programs, specializations, intake years and study modes listed there.
4. Ask the student, one question at a time:
   - university and program (with specialization)
   - intake year (the year they started)
   - study mode (full time, part time, extra occupational)
   - start semester (for example HS25 or FS26)
   - semesters of interruption so far, if any
   - preferred language for reports (English or German)
5. If the program is not listed, explain that a program file has to be created first with `/import` from the official regulation and curriculum, and stop.
6. Run `uv run studyplan init` with all answers as options.
7. Run `uv run studyplan validate` and report the result.
8. Tell the student the next step: `/missing` to see which module descriptions to save, or `/credits` to enter modules by hand.

$ARGUMENTS
