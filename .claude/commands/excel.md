---
description: Create the Excel workbook with modules, credits, allocation and gaps
allowed-tools: Bash(uv run studyplan *)
---

1. Run `uv run studyplan validate`. If there are errors, explain them and stop.
2. Run `uv run studyplan excel`.
3. Tell the student the path of the new file in `my_study/output/` and what the sheets contain: Overview, Rules, Modules, My Credits, Allocation, Gaps, Sources, Open Issues (and Plan and Timetable if available).
4. Explain that values on the Overview sheet are computed by the rule engine, and that only the simple sums in My Credits are Excel formulas. Changes made in Excel are not read back; corrections go through `/credits`.
5. End with: "Not legally binding. The official study regulations and the program management decide."
