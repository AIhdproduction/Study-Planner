---
description: Import documents from my_study/inbox (regulations, module descriptions, transcript)
allowed-tools: Bash(uv run studyplan *), Read(my_study/inbox/regulations/**), Read(my_study/inbox/modules/**), Read(my_study/imports/**), Edit(my_study/imports/**)
---

Import the student's documents into drafts, then let the student confirm them.

## 1. Inventory
Run `uv run studyplan inbox --json` and show every file with detected type and status. Skip files already processed with an unchanged hash.

## 2. Consent
Explain once: reading a file in Claude Code sends its content to Anthropic. Then ask per file whether it may be read. Log each answer with `uv run studyplan consent log --file "<name>" --decision yes|no`. Only process files with consent.

## 3. Deterministic parsing first
Run `uv run studyplan parse-modules` for module descriptions. Read the resulting draft and only fill fields marked `needs_agent`, using the saved page as the only source.

## 4. Personal documents
Transcripts and recognition decisions are never read directly. Run `uv run studyplan redact "<file>"`, tell the student which categories were removed, show the redacted text and ask for confirmation before reading it from `my_study/imports/redacted/`.

## 5. Extraction rules
For regulations, curricula, remaining module fields and redacted transcripts, write drafts to `my_study/imports/` following the schemas in `schemas/`:
- Use only the provided files. No outside knowledge about the university.
- Every item carries file name, page number and a source excerpt under 15 words.
- Missing values are `null` and go into `open_issues`. Never estimate.
- Identify the regulation version and the intake years it applies to.
- Transcript drafts contain module code, title, semester, ECTS, grade, passed flag and attempt only. No personal data.
- Use module codes exactly as written in the document. Code differences between documents are resolved by the CLI mapping table, not by you.

## 6. Validate
Run `uv run studyplan validate <draft>`. If it fails, correct the draft once using the error list. If it still fails, stop and report the errors.

## 7. Review with the student
Run `uv run studyplan diff <draft> --json`. Show new, changed and removed items. Ask which to accept, then run `uv run studyplan accept <draft>` with the chosen items. Imported items get status `unverified`; remind the student to verify them against the source.

## 8. Next step
Suggest `/check`.
