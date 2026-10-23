---
description: Add, correct or list your passed, failed and recognized modules
argument-hint: "[what you want to add or change, e.g. 'Python Basics HS25 passed B']"
allowed-tools: Bash(uv run studyplan *)
---

Help the student maintain `my_study/credits.yaml` through the CLI only.

1. Run `uv run studyplan credits list --json` and summarize the current entries briefly.
2. If a saved MyCampus "Meine Anmeldungen" page (`.html`) is in `my_study/inbox/transcript/`, offer to import it. Do not read the file yourself. Run `uv run studyplan credits import-mycampus "<file>" --json` (dry run), show the parsed rows without person names, explain rows with status `unmapped` or `running`, and only after the student agrees run it again with `--apply`.
3. Understand what else the student wants from: $ARGUMENTS
4. For every module the student mentions:
   - Identify the module by code. If the student gives only a title, search with `uv run studyplan modules --search "<text>" --json`. If several modules match, ask which one. If none matches, say so. Never pick by guess.
   - Ask for missing values: semester (HS/FS + year), grade (A to F or pass/fail), attempt number.
   - Run `uv run studyplan credits add` (or `edit` / `remove`) with explicit options.
5. Recognized credits from earlier education (for example a "Modulerlassung"):
   - Never read the decision document directly. Ask the student for each row of the decision: ECTS, area or category, module code if any, basis (for example HF diploma), date of the decision. If they want you to read it, run `uv run studyplan redact "<file>"` first (phase 2) and read only the redacted text.
   - If the decision is not unambiguous (approval box not ticked, row name and type column point to different categories), record it with `--status provisional`, use `--no-category` when the category is unclear, and describe the issue in `--open-issue`. Never decide the category yourself.
   - Run `uv run studyplan credits recognize add` with explicit options, then `uv run studyplan credits recognize list --json` to confirm.
6. If the CLI rejects an entry (unknown code, duplicate, ECTS mismatch), explain the message and ask the student how to proceed.
7. Finish with `uv run studyplan validate` and suggest `/check`.
