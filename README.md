# Study Planner

Study Planner is an open source tool that helps students check bachelor thesis admission and graduation requirements, plan remaining semesters and timetables, and create an Excel workbook. Students clone the repository and work with it through Claude Code. The first profile targets HSLU Technik & Architektur, Digital Construction, specialization Architecture, intake 2025.

## Disclaimer

Not legally binding. The official study regulations and the program management decide.

## Status

Phases 1 and 1b are done. The working slash commands are `/setup`, `/credits` (including the local MyCampus import), `/check`, `/plan`, and `/excel`. The remaining commands become available with their respective phases.

| Phase | Scope | Status |
|---|---|---|
| 1 | Data model, rule engine, CLI, and Excel export | done |
| 1b | Semester plan generator, conditions, and Excel plan sheets | done |
| 2 | Document import through Claude Code | planned |
| 3 | Public program-data fetch and change reporting | planned |
| 4 | Semester planning and timetable support | planned |

## Prerequisites

- Windows
- [uv](https://docs.astral.sh/uv/)
- [Claude Code](https://code.claude.com/docs)
- git
- Optional: LibreOffice for the Excel parity test

## Quick start

1. Clone the repository:

   ~~~powershell
   git clone REPOSITORY-URL
   ~~~

2. Open the cloned folder.
3. Run `start.bat`. It checks for uv and Claude Code, runs `uv sync` and `uv run studyplan doctor`, then starts Claude Code.
4. In Claude Code, type `/setup`.

## Using phase 1

All values below are invented examples. Replace paths and values with your own study data.

```powershell
uv run studyplan init --university hslu_ta --program digital_construction_architecture_2025 --intake-year 2025 --study-mode part_time --start-semester HS25
uv run studyplan credits import-mycampus "my_study/inbox/transcript/example.html"
uv run studyplan credits add --code TA.BA_NABA --semester HS25 --ects 3 --grade B
uv run studyplan credits recognize add --ects 3 --basis "Example prior study" --category related --document "example-decision.pdf" --status confirmed
uv run studyplan check --mode current
uv run studyplan excel --mode current
uv run studyplan backup
```

## Study plan

All values below are invented examples. Generate a first plan from your saved credits and the published model timetable, review its checks, then adjust individual modules if needed.

```powershell
uv run studyplan plan generate --current-semester HS29
uv run studyplan plan --json
uv run studyplan plan move --code SYN.EXAMPLE --semester FS30
uv run studyplan excel --mode forecast
```

`plan generate` preserves manual choices. The Excel workbook includes the Study Plan and Semester Overview sheets with planned ECTS, conditions, status colors, and the earliest thesis-admission semester. Timetable-slot imports remain unavailable until phase 4.

## What to tell Claude Code

Use the commands in this order. The examples are ordinary sentences you can type after the slash command.

1. Run `start.bat`, then type `/setup`.
   Example: `/setup I study Digital Construction, started in 2025, full time.`
2. Type `/credits` to enter modules or import the saved MyCampus page locally.
   Example: `/credits import my MyCampus page.`
3. Once phase 2 is available, type `/missing` to learn which module descriptions to save.
   Example: `/missing show the module descriptions I still need.`
4. Type `/check` to see your current status or a forecast.
   Example: `/check forecast.`
5. Type `/excel` to create your workbook.
   Example: `/excel create my study plan workbook.`
6. Once phase 2 is available, use `/import` after saving documents; once phase 4 is available, use `/plan` for your remaining semesters.
   Examples: `/import read my saved module descriptions.` and `/plan move my remaining modules into future semesters.`

In phase 1, use `/setup`, `/credits`, `/check`, and `/excel`; `/missing`, `/import`, and `/plan` are not available until their stated phases.

## Workflow

| Step | Command | What happens |
|---|---|---|
| 1 | `/setup` | Choose university, program, intake year and study mode. Creates `my_study/profile.yaml`. |
| 2 | `/credits` | Import the saved MyCampus page locally, or add and correct passed, failed, and recognized modules. |
| 3 | `/missing` | Shows which module descriptions the student must save from the portal. Available in phase 2. |
| 4 | `/import` | Reads documents from `my_study/inbox/` after consent and creates drafts the student confirms. Available in phase 2. |
| 5 | `/check` | Thesis admission and graduation check with gap list. |
| 6 | `/plan` | Plan the remaining semesters and the timetable, find conflicts. Available in phase 4. |
| 7 | `/excel` | Write the Excel workbook to `my_study/output/`. |
| any | `/update` | Fetch the latest public documents of the program. Available in phase 3. |

## What to collect and where to put it

Collect the following documents before asking Claude Code to work with them.

1. **Study regulation of your school**
   - What it is: the official study regulation that defines the rules for your degree.
   - Where to get it: download the public PDF from your university website.
   - How to save it: save the original PDF without changing it.
   - Target folder: `my_study/inbox/regulations/`
2. **Curriculum of your program and intake year**
   - What it is: the official curriculum for the program and year in which you started.
   - Where to get it: download the public PDF from your university website.
   - How to save it: save the original PDF without changing it.
   - Target folder: `my_study/inbox/regulations/`
3. **Model timetable of your program and study mode**
   - What it is: the published recommended semester sequence, if your university provides one.
   - Where to get it: download the public PDF from your university website.
   - How to save it: save the original PDF without changing it.
   - Target folder: `my_study/inbox/timetable/`
4. **MyCampus page "Meine Anmeldungen"**
   - What it is: your registration overview, including all semesters.
   - Where to get it: log in yourself in your own browser and open "Meine Anmeldungen".
   - How to save it: remove the semester filter so that all semesters are shown, press `Ctrl+S`, and choose "Webpage, complete". Put the resulting `.html` file in the target folder. The extra `_files` folder may stay next to it or be deleted.
   - Target folder: `my_study/inbox/transcript/`
   - It is parsed locally with `uv run studyplan credits import-mycampus`; Claude Code never reads it directly.
5. **Official transcript of records**
   - What it is: your official record of completed assessments, if you have one.
   - Where to get it: download the PDF from your university portal yourself.
   - How to save it: save the original PDF without changing it.
   - Target folder: `my_study/inbox/transcript/`
6. **Recognition decisions for earlier education**
   - What it is: decisions that recognize credits from earlier education, for example a "Modulerlassung" form.
   - Where to get it: use the PDF issued by your school.
   - How to save it: save the original PDF without changing it.
   - Target folder: `my_study/inbox/recognition/`
7. **Module descriptions from the login-protected module directory**
   - What it is: the detailed page for every module that `/missing` lists, and at least the bachelor thesis module. The thesis module contains the program-specific thesis admission requirements.
   - Where to get it: log in yourself in your own browser and open the module detail page, not the result list.
   - How to save it: expand all collapsed sections, press `Ctrl+P`, and choose "Save as PDF". As an alternative, press `Ctrl+S` and choose "Webpage, complete". Save one file per module.
   - Target folder: `my_study/inbox/modules/`

- File names do not matter.
- Never rename codes that appear in documents.
- Never put files from other students in your folder.
- Nothing in `my_study/` is uploaded to GitHub.

~~~text
my_study/
  inbox/regulations/   study regulation, curriculum (PDF)
  inbox/modules/       module descriptions saved from the portal (Ctrl+S complete page, or Ctrl+P as PDF)
  inbox/transcript/    MyCampus "Meine Anmeldungen" page (Ctrl+S) and official transcript of records (PDF)
  inbox/recognition/   recognition decisions for external credits (PDF)
  inbox/timetable/     timetables (PDF, ICS, CSV, XLSX)
  output/              generated Excel workbooks
~~~

## Privacy

- `my_study/` is never committed: it is gitignored, apart from the empty folder skeleton.
- The planner never requests, stores, or transmits passwords; it never logs in or accesses pages behind a login, including the module directory and ILIAS.
- Claude Code asks for consent for each file before reading it, because reading sends its content to Anthropic.
- Transcripts and recognition decisions are read only in redacted form.
- `.claude/settings.json` denies direct reads from `my_study/inbox/transcript/` and `my_study/inbox/recognition/`.

## Repository structure

~~~text
start.bat
pyproject.toml
uv.lock
AGENTS.md
CLAUDE.md
.claude/
  settings.json
  commands/
src/studyplan/
  cli.py
  engine/
  models/
  io/
  importers/
  exporters/
  fetch/
  i18n/
schemas/
profiles/
my_study/
sources/
prompts/
tests/
  fixtures/real/
  fixtures/synthetic/
  fixtures/golden_template.yaml
~~~

## Contributing / adding a university

Start from `profiles/_template/`. A university profile uses `profiles/your-university/university.yaml`, a `programs/` directory, and `code_mapping.yaml`.

Developers must read `AGENTS.md` first and implement one phase prompt at a time. `ruff` and `pytest` must pass.

## Kurzanleitung (Deutsch)

1. Besorge Studienreglement und Curriculum für deinen Studiengang und Eintrittsjahrgang als öffentliche PDFs und speichere sie in `my_study/inbox/regulations/`.
2. Speichere den Modellstundenplan, falls vorhanden, als öffentliches PDF in `my_study/inbox/timetable/`.
3. Melde dich selbst in MyCampus an, öffne "Meine Anmeldungen", entferne den Semesterfilter, speichere mit `Strg+S` als "Webseite, vollständig" und lege die `.html`-Datei in `my_study/inbox/transcript/` ab. Der `_files`-Ordner ist optional.
4. Lege dein offizielles Transcript als PDF in `my_study/inbox/transcript/` und Anerkennungsentscheide als PDF in `my_study/inbox/recognition/` ab.
5. Für jedes von `/missing` genannte Modul und mindestens für das Bachelorarbeitsmodul: Detailseite selbst öffnen, alle Bereiche aufklappen, mit `Strg+P` „Als PDF speichern“ auswählen und je eine Datei in `my_study/inbox/modules/` ablegen.
6. Dateinamen sind egal. Modulcodes nie umbenennen, keine Dateien anderer Studierender ablegen und nichts aus `my_study/` zu GitHub hochladen.
7. Starte `start.bat`, dann verwende `/setup`, `/credits`, `/missing`, `/check` und `/excel` in dieser Reihenfolge.
8. Beispiele: `/setup Ich habe 2025 angefangen.`, `/credits Importiere meine MyCampus-Seite.`, `/missing Zeig mir die fehlenden Module.`, `/check Prognose.`, `/excel Erstelle meine Arbeitsmappe.`
9. `/missing` und `/import` stehen ab Phase 2 bereit; `/plan` für die Semesterplanung ab Phase 4. In Phase 1 funktionieren `/setup`, `/credits`, `/check` und `/excel`.

## License

MIT License. See [LICENSE](LICENSE).
