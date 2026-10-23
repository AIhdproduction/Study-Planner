[Deutsch](README.de.md)

# Study Planner

Study Planner helps you check bachelor thesis admission and graduation requirements, plan your remaining semesters, and create an Excel workbook. You work locally in a cloned repository with Claude Code; the planner calculates results from versioned YAML data.

> Not legally binding. The official study regulations and the program management decide.

## What it does

- Checks thesis admission and graduation requirements from the selected regulation profile.
- Allocates each passed module to at most one category, even when it qualifies for several.
- Imports a saved MyCampus “Meine Anmeldungen” page locally.
- Records recognized credits from earlier education, including provisional decisions.
- Builds a semester plan with retakes, offering terms, deadlines, and the Basic-to-Advanced level gate.
- Creates a reviewable Excel workbook with the results and source references.
- Keeps study data in local, human-readable files; there is no web application or database.

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 | Study data, rule engine, CLI, and Excel export | Done |
| 1b | Semester-plan generator and plan sheets | Done |
| 2 | Document import, redaction, drafts, and consent workflow | Planned |
| 3 | Public-document fetch and change reporting | Planned |
| 4 | Timetable import, conflicts, and suggestions | Planned |

The slash commands that work today are `/setup`, `/credits`, `/check`, `/plan`, and `/excel`. `/missing` and `/import` need phase 2; `/update` needs phase 3; timetable import and suggestions need phase 4.

## Supported programs

The included profile covers HSLU Technik & Architektur, Bachelor Digital Construction, specialization Architecture, intake 2025, with a part-time model timetable. Profile facts are marked `unverified` until they have been checked against the official documents, so results can be provisional. To add another university or program, see [For contributors](#for-contributors).

## Requirements

- Windows 10 or 11
- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/)
- [Claude Code](https://code.claude.com/docs) and a Claude account
- Optional: LibreOffice, only for a developer Excel-parity test

## Quick start

1. Clone the repository.

   ```powershell
   git clone https://github.com/AIhdproduction/Study-Planner.git
   ```

2. Open the new `Study-Planner` folder in Explorer.
3. Double-click `start.bat`. It checks `uv` and Claude Code, synchronizes dependencies, and checks the local setup.
4. Use the menu.

   | Key | Action |
   |---|---|
   | `1` | Open the inbox folder for your documents. |
   | `2` | Create and open the workflow guide in Notepad. |
   | `3` | Start Claude Code in this repository. |
   | `4` | Open the output folder for Excel workbooks. |
   | `5` | Create an Excel workbook now, after setup. |
   | `Q` | Quit the menu. |

5. In Claude Code, type `/setup` and answer its questions.
6. `start.bat` uses German by default. To switch permanently, run `setx STUDYPLAN_LANG en` once; new windows use the setting. Alternatively, change the line `set "STUDYPLAN_LANG=de"` in `start.bat`. After `/setup`, the CLI uses the language stored in the study profile.

## Step 1: collect your documents

| Document | Where to get it | How to save it | Folder |
|---|---|---|---|
| Study regulation | Your university’s public website | Save the original PDF. | `my_study/inbox/regulations/` |
| Curriculum for your intake year | Your university’s public website | Save the original PDF. | `my_study/inbox/regulations/` |
| Model timetable | Your program’s public website, if available | Save the original PDF. | `my_study/inbox/timetable/` |
| MyCampus “Meine Anmeldungen” | Log in yourself and open the page | Remove the semester filter, then use `Ctrl+S` and choose “Webpage, complete”. | `my_study/inbox/transcript/` |
| Transcript of records | Download it yourself from the student portal | Save the original PDF. | `my_study/inbox/transcript/` |
| Recognition decision | The decision issued by your university | Save the original PDF. | `my_study/inbox/recognition/` |
| Module descriptions, including the thesis module | Open each module’s detail page yourself | Expand all sections, then use `Ctrl+P` and save as PDF, or use `Ctrl+S` for a complete webpage. | `my_study/inbox/modules/` |

- Log in to portals yourself. File names do not matter.
- Never share a password with Claude Code or put one into this repository.
- Study Planner does not upload `my_study/` and Git ignores it. Claude Code document reading is a separate, consent-based phase-2 feature; see [Privacy and security](#privacy-and-security).

```text
my_study/
  profile.yaml
  credits.yaml
  plan.yaml
  checklist.yaml
  inbox/
    regulations/
    modules/
    transcript/
    recognition/
    timetable/
  imports/
  output/
  logs/
  backups/
```

## Step 2: work with Claude Code

| Command | What it does | Example you can type |
|---|---|---|
| `/setup` | Selects the university, program, intake, study mode, and language. | `/setup I started Digital Construction in 2025 and study part time.` |
| `/credits` | Imports your saved MyCampus page locally or records passed, failed, and recognized credits. | `/credits Import my saved MyCampus page.` |
| `/check` | Shows the current result or a forecast with gaps. | `/check Show a forecast for my current plan.` |
| `/plan` | Generates and adjusts the remaining-semester plan. | `/plan Generate my first plan and show the warnings.` |
| `/excel` | Writes the Excel workbook. | `/excel Create my workbook in German.` |
| `/missing` | Lists module pages still needed. Available in phase 2. | `/missing Which module descriptions do I still need?` |
| `/import` | Creates reviewable import drafts after consent. Available in phase 2. | `/import Process the module pages I approved.` |
| `/update` | Fetches approved public-source updates. Available in phase 3. | `/update Check for public program updates.` |

Recommended order: `/setup`, `/credits`, `/check`, `/plan`, `/check forecast`, `/excel`. Add `/missing` and `/import` when phase 2 is available.

```text
You: /setup I started in 2025, study part time, and prefer English.
Claude Code: I will list the available profiles and create your local study profile.

You: /credits Import my saved MyCampus page.
Claude Code: I will first show a local dry run, then apply it only after you confirm.

You: /check Show a forecast.
Claude Code: I will run the rule engine and explain its gaps and provisional items.
```

The values in this example are invented.

## Step 3: your Excel workbook

| Sheet | Purpose |
|---|---|
| Overview | Overall result, goals, and key totals from the rule engine. |
| Rules | Every checked rule with current value, target, status, and source. |
| Modules | The curriculum modules and their categories. |
| My Credits | Passed and failed attempts, recognized credits, and simple Excel sums. |
| Allocation | The category assigned to every counted credit. |
| Gaps | Requirements that are still open. |
| Sources | Source-document and page references for rules. |
| Open Issues | Provisional and manual items needing review. |
| Study Plan | Planned modules, conditions, statuses, and source data. |
| Semester Overview | Semester totals, cumulative ECTS, violations, and earliest thesis admission. |

On the Study Plan sheet, passed rows are green, running rows blue, planned rows white, failed rows red, retakes orange, and elective placeholders yellow. Excel edits are not read back: correct credits and plan entries through Claude Code and the CLI, then create a new workbook.

## How the checks work

Rules and their source-document/page references come from the selected study-regulation profile. The included HSLU profile implements:

- 180 ECTS for graduation and 132 ECTS plus the program-specific manual requirement for thesis admission.
- Category minima: 90 Core, 39 Core-Project, 15 Related, and 15 Minor ECTS.
- All mandatory Core and Core-Project modules passed.
- At most three attempts, with a shared 12-ECTS third-attempt budget; the thesis has no third attempt.
- Advanced modules only after all mandatory Basic modules, and mandatory Basic modules within six completed semesters.
- At least 60 ECTS acquired at HSLU, recognition caps for an HF diploma and applicable professional practice, and a 12-semester maximum duration.

`eligible` means the automated rules for that goal are fulfilled. `not eligible` means at least one automated requirement is open. `provisional` means an outcome depends on unverified profile data or a provisional recognition; `manual` marks a requirement that needs your confirmation. Results remain provisional until the profile data is verified against the official documents. For modules that fit several categories, the rule engine uses OR-Tools CP-SAT to choose one allocation per module that satisfies the rules as well as possible.

## Privacy and security

- The planner stores data locally in `my_study/`; this folder is gitignored.
- In phase 2, Claude Code asks for consent before reading each document. Reading sends document content to Anthropic.
- In phase 2, transcripts and recognition decisions are redacted before Claude Code reads their text.
- `.claude/settings.json` denies direct reads of transcript and recognition inbox folders.
- The planner never asks for, stores, or uses passwords and never logs in to a website.
- Public fetching is planned for phase 3 and will respect robots.txt, source allowlists, and manual-source restrictions.

## FAQ and troubleshooting

**`uv` was not found.** Install [uv](https://docs.astral.sh/uv/), close and reopen the terminal, then run `start.bat` again.

**`claude` was not found.** Install Claude Code from [its documentation](https://code.claude.com/docs), sign in to your Claude account, and run `start.bat` again.

**`start.bat` closes immediately.** Start it from PowerShell in the repository folder so that the message remains visible: `.\\start.bat`. Check that `uv` and `claude` are on `PATH`.

**MyCampus import reports `unmapped`.** The saved code does not exactly match a curriculum code or an explicit mapping. Do not guess; record it only after a contributor has added and verified an entry in `profiles/hslu_ta/code_mapping.yaml`.

**My result is `provisional`.** Read the listed reasons. Common reasons are unverified profile facts, an unverified code mapping, a provisional recognition, or a manual thesis requirement.

**Excel shows a warning when opening.** This should not happen. Do not accept a repair silently; keep the original file and report the warning with the command you ran at [GitHub Issues](https://github.com/AIhdproduction/Study-Planner/issues). Do not include personal data or files from `my_study/`.

**How do I start over?** Run `uv run studyplan backup` first. Then manually delete or rename the YAML files in `my_study/`; `init` never overwrites an existing profile.

**How do I update?** In the repository folder, run `git pull`, then double-click `start.bat` so `uv sync` can update the environment.

**Where do I report a bug or suggest a program?** Open an issue at [GitHub Issues](https://github.com/AIhdproduction/Study-Planner/issues). Do not include personal data or files from `my_study/`.

## For contributors

```text
start.bat                  Windows launcher
src/studyplan/             CLI, rule engine, models, YAML I/O, Excel export, translations
profiles/                  University, program, and code-mapping profiles
schemas/                   Exported JSON Schemas
my_study/                  Local student state; ignored by Git
.claude/commands/          Student-facing Claude Code workflow
prompts/                   Phase-specific implementation scope
scripts/                   Maintainer utilities, including model-timetable extraction
tests/fixtures/synthetic/  Committed invented test data
tests/fixtures/real/       Private, ignored maintainer fixtures
```

### CLI reference

| Command | Description |
|---|---|
| `studyplan guide` | Print the student workflow and optionally write it to a file. |
| `studyplan doctor` | Check required local folders. |
| `studyplan profiles` | List available universities and programs. |
| `studyplan modules` | List modules in the selected program. |
| `studyplan init` | Create a study profile and empty state files. |
| `studyplan validate` | Validate study files and profile data. |
| `studyplan schema` | Export JSON Schemas. |
| `studyplan check` | Evaluate thesis admission and graduation requirements. |
| `studyplan credits` | Manage passed, failed, and recognized credits. |
| `studyplan credits list` | List saved credits and recognitions. |
| `studyplan credits add`, `edit`, `remove` | Add, change, or remove a module attempt. |
| `studyplan credits import-mycampus` | Locally parse a saved MyCampus page; dry run by default. |
| `studyplan credits recognize` | Manage recognized credits from earlier education. |
| `studyplan credits recognize add`, `list`, `remove` | Add, list, or remove a recognition. |
| `studyplan plan` | Check the saved semester plan. |
| `studyplan plan generate` | Generate a deterministic first plan. |
| `studyplan plan add`, `move`, `remove` | Manually edit plan items. |
| `studyplan timetable` | Reserve timetable functions for phase 4. |
| `studyplan timetable import` | Report that timetable import is not available yet. |
| `studyplan excel` | Export a reviewable Excel workbook. |
| `studyplan backup` | Write a portable JSON snapshot. |
| `studyplan restore` | Restore a validated backup. |

Use these development commands.

```powershell
uv sync
uv run ruff check
uv run ruff format --check
uv run pytest
```

`@pytest.mark.real` tests use private fixtures and skip cleanly when they are unavailable. `@pytest.mark.agent` is registered in `pyproject.toml` for optional tests that call an AI agent; run them explicitly with `uv run pytest -m agent`. No agent tests are currently part of the default run.

To add a university or program, start with `profiles/_template/`. Put the university rules in `university.yaml`, program curriculum in `programs/`, and explicit source-code stems in `code_mapping.yaml`. Mapping entries name their source (`mycampus`, `timetable`, or `module_directory`) and never rely on title-only matching. Use `scripts/extract_model_timetable.py` for the model-timetable extraction workflow. Follow `AGENTS.md`, implement only the requested phase in `prompts/`, and keep `tests/fixtures/real/` private and gitignored.

## License

MIT. See [LICENSE](LICENSE).

Not legally binding. The official study regulations and the program management decide.
