---
description: Check thesis admission and graduation requirements and show what is missing
argument-hint: "[current|forecast]"
allowed-tools: Bash(uv run studyplan *)
---

Run the rule engine and explain the result. Never compute anything yourself.

1. Run `uv run studyplan validate`. If there are errors, explain them and stop.
2. Run `uv run studyplan check --mode current --json`. If $ARGUMENTS is `forecast`, or `my_study/plan.yaml` contains planned modules, also run `uv run studyplan check --mode forecast --json`.
3. Report, using only values from the JSON:
   - Verdict per goal (thesis admission, graduation): eligible, not eligible or provisional.
   - Total ECTS and ECTS per category against the targets.
   - Every gap as a short bullet with what is missing.
   - Rules that are `provisional` and which unverified data they depend on.
   - Manual checklist items (`custom_note`) the student still has to confirm in `my_study/checklist.yaml`.
   - For modules counted in a category different from what the student might expect, the allocation explanation.
4. If current and forecast differ, explain which planned modules close which gaps.
5. Suggest the next step: `/credits` to fix entries, `/plan` to close gaps, `/excel` for the workbook.
6. End with: "Not legally binding. The official study regulations and the program management decide."
