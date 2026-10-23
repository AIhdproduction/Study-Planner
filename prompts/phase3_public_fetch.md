# Phase 3: Fetch Public Program Data

Read `AGENTS.md` completely before starting. Phases 1 and 2 are done and their tests pass. Implement only this phase.

## Goal
`studyplan fetch` downloads the current public documents of the selected program (study regulations, curricula, public module lists, public semester schedules). Changed documents go through the phase 2 import flow via the `/update` slash command.

## Source Discovery
- `profiles/<id>/university.yaml` gets a `sources` section: start URLs, allowed domains, document patterns, document types.
- Deterministic crawler (httpx + selectolax), limited to allowed domains and patterns from the profile.
- If the crawler finds nothing, `/update` may let Claude Code search the web for candidate document URLs on the allowed domains. Claude Code returns only URLs. The CLI downloads them itself with `studyplan fetch --url <url>` after checking the domain allowlist.
- Respect robots.txt, one request per second maximum, clear user agent with contact address from the profile. No login pages, no session cookies.
- Domains that require a login or disallow crawling (HSLU: `modulverzeichnis.hslu.ch`, ILIAS) are listed under `manual_sources` with a short instruction for the student. The crawler skips them and points to `studyplan missing`.

## Download and Change Detection
- Store files in `sources/raw/<YYYY-MM-DD>/` (gitignored) with SHA-256 hash and metadata (URL, retrieval time, content type, size).
- Skip unchanged files by hash.
- Copy new or changed documents into `my_study/inbox/regulations/` and list them for `/import`.
- Detect a new regulation version and ask the student whether it applies to their intake year. Never switch versions automatically.
- `studyplan report [--json]` shows the last fetch: date, number of new, changed and unchanged documents, errors. Reports are stored in `sources/reports/<date>.md`.

## Slash Command
`.claude/commands/update.md` is the contract.

## Tests (Definition of Done)
- Crawler respects robots.txt, domain allowlist and rate limit (local test server, no real network).
- `fetch --url` rejects a URL outside the allowlist.
- Unchanged files are skipped by hash.
- A changed document lands in the inbox and in the report.
- New regulation version produces the confirmation item and does not switch automatically.
- Network errors and timeouts produce clean messages, partial results are kept.

## Deliverables
Complete code, extended HSLU profile with sources section (only URLs verified as reachable and official, each with a note where it was found), tests passing, README section for phase 3, assumptions and items to verify.
