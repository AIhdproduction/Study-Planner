# Phase 4: Semester Planner and Timetable

Read `AGENTS.md` completely before starting. Phases 1 to 3 are done and their tests pass. Implement only this phase.

## Goal
Students plan their remaining semesters together with Claude Code through `/plan`, see timetable conflicts and know whether the plan leads to thesis admission and graduation in time.

## Timetable Import
- `studyplan timetable import <file>`: ICS with icalendar, CSV and XLSX with a column mapping given as options (Claude Code asks the student and passes them).
- PDF timetables (for example the HSLU model timetable) go through the phase 2 import flow and produce a timetable draft.
- Entries are matched to modules by code through `code_mapping.yaml` (department prefix and type letter stripped). Unmatched entries land in a confirmation list. Matching by title only with explicit confirmation.

## Planner
- `plan.yaml` holds semester columns from the current semester until the maximum study duration, each with planned modules and optional timetable slots.
- `studyplan plan [--json]` runs these checks:
  - ECTS per semester against configurable target and warning thresholds per study mode (from the profile).
  - Module not offered in that semester or offering year, or no longer offered.
  - Prerequisite planned later than the dependent module.
  - Level gate and Basic deadline violations in the plan.
  - Timetable conflicts (overlapping slots, both modules named). Adjacent slots are not a conflict.
  - Forecast verdict from the rule engine and earliest semester in which thesis admission and graduation are reached.
- `studyplan suggest [--json]`: modules that close the remaining gaps, sorted by number of rules they help fulfill, with offered semesters. Suggestions only, never automatic changes.
- `studyplan plan add/move/remove` to edit `plan.yaml` with validation, so Claude Code never edits the file by hand.

## Slash Command
`.claude/commands/plan.md` is the contract.

## Excel Export Extension
Add sheets Plan (modules per semester with ECTS sums as formulas) and Timetable (weekly grid with conflicts marked red). Extend the parity test.

## Tests (Definition of Done)
- ICS import maps events to modules correctly, unknown events land in the confirmation list.
- Prefixed timetable codes (`DCA-K-`, `GR-K-`) map to curriculum codes through the mapping table.
- Overlapping slots are detected, adjacent slots are not.
- Module planned in a semester where it is not offered triggers a warning.
- Prerequisite order violation triggers a warning.
- Forecast verdict and earliest admission semester are correct for a synthetic plan.
- Suggestion list ranks a module that closes two gaps above one that closes one.

## Deliverables
Complete code, tests passing, final README covering all phases, limitations, disclaimer, how to add a university, and a final list of open issues.
