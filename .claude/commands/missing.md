---
description: Show which module descriptions you still have to save from the portal
allowed-tools: Bash(uv run studyplan *)
---

1. Run `uv run studyplan missing --json`.
2. Show a table with code, title and status (missing, outdated, saved, extracted, verified). List `missing` and `outdated` first.
3. Explain that module descriptions usually exist only as web pages, not as downloadable documents. The saved page is the document. Explain how to save it, without ever logging in for the student:
   - Open the module directory of your university in your own browser and log in yourself.
   - Search for the module code shown in the table and open the module's detail page, not the search result list.
   - Expand every collapsed section (prerequisites, assessment, content) so all text is visible.
   - Preferred: Ctrl+P, choose "Save as PDF" as printer, save. Alternative: Ctrl+S with "Webpage, complete".
   - Put the file into `my_study/inbox/modules/`. One file per module, the file name does not matter.
4. If the student asks you to log in, to open the portal, or offers a password: decline. Logins and passwords are never handled by this tool.
5. When the student has saved pages, suggest `/import`.
