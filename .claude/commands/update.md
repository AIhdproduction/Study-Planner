---
description: Fetch the latest public documents of your program and import changes
allowed-tools: Bash(uv run studyplan *)
---

1. Run `uv run studyplan fetch` and then `uv run studyplan report --json`.
2. Report the number of new, changed and unchanged documents and any errors.
3. If the crawler found nothing, you may search the web for official documents, but only on the allowed domains listed in the report. Return candidate URLs to the student with a reason each. After the student agrees, download them with `uv run studyplan fetch --url "<url>"`. Never open login pages or portals listed under manual sources.
4. If the report shows a new regulation version, ask the student whether it applies to their intake year. Never switch the version yourself.
5. For manual sources (for example the module directory), point the student to `/missing`.
6. If new or changed documents landed in the inbox, suggest `/import`.
