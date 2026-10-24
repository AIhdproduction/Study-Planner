[English](README.md)

# Study Planner

Study Planner hilft dir, die Zulassung zur Bachelorarbeit und den Studienabschluss zu prüfen, die verbleibenden Semester zu planen und eine Excel-Arbeitsmappe zu erstellen. Du arbeitest lokal in einem geklonten Repository mit Claude Code; der Planer berechnet Ergebnisse aus versionierten YAML-Daten.

> Nicht rechtsverbindlich. Es gelten das offizielle Studienreglement und die Entscheide der Studiengangleitung.

## Was der Planer macht

- Prüft Zulassung zur Bachelorarbeit und Studienabschluss anhand des gewählten Reglementsprofils.
- Teilt jedes bestandene Modul höchstens einer Kategorie zu, auch wenn es für mehrere Kategorien infrage kommt.
- Importiert eine gespeicherte MyCampus-Seite „Meine Anmeldungen“ lokal.
- Erfasst Anerkennungen aus früheren Ausbildungen, auch vorläufige Entscheide.
- Erstellt einen Semesterplan mit Wiederholungen, Angebotssemestern, Fristen und der Stufenvoraussetzung Basic zu Advanced.
- Erstellt eine nachvollziehbare Excel-Arbeitsmappe mit Ergebnissen und Quellenangaben.
- Hält Studiendaten in lokalen, lesbaren Dateien; es gibt keine Webanwendung und keine Datenbank.

## Status

| Phase | Umfang | Status |
|---|---|---|
| 1 | Studiendaten, Regelwerk, CLI und Excel-Export | Erledigt |
| 1b | Generator für Semesterplan und Plan-Tabellenblätter | Erledigt |
| 2 | Dokumentimport, Schwärzung, Entwürfe und Einwilligungsablauf | Geplant |
| 3 | Abruf öffentlicher Dokumente und Änderungsbericht | Geplant |
| 4 | Stundenplanimport, Konflikte und Vorschläge | Geplant |

Heute funktionieren die Slash-Commands `/setup`, `/credits`, `/check`, `/plan` und `/excel`. `/missing` und `/import` benötigen Phase 2, `/update` benötigt Phase 3, Stundenplanimport und Vorschläge benötigen Phase 4.

## Unterstützte Studiengänge

Das enthaltene Profil deckt HSLU Technik & Architektur, Bachelor Digital Construction, Vertiefung Architecture, Eintritt 2025, mit einem Teilzeit-Modellstundenplan ab. Profilangaben sind bis zur Prüfung anhand der offiziellen Dokumente als `unverified` markiert; deshalb können Ergebnisse vorläufig sein. Hinweise zum Ergänzen einer Hochschule oder eines Studiengangs stehen unter [Für Mitwirkende](#für-mitwirkende).

## Voraussetzungen

- Windows 10 oder 11
- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/)
- [Claude Code](https://code.claude.com/docs) und ein Claude-Konto
- Optional: LibreOffice, nur für einen Entwickler-Test zur Excel-Parität

## Schnellstart

1. Klone das Repository.

   ```powershell
   git clone https://github.com/AIhdproduction/Study-Planner.git
   ```

2. Öffne den neuen Ordner `Study-Planner` im Explorer.
3. Doppelklicke auf `start.bat`. Das Skript prüft `uv` und Claude Code, synchronisiert Abhängigkeiten und prüft die lokale Einrichtung.
4. Verwende das Menü.

   | Taste | Aktion |
   |---|---|
   | `1` | Öffnet den Inbox-Ordner für deine Dokumente. |
   | `2` | Erstellt und öffnet die Ablaufanleitung in Notepad. |
   | `3` | Startet Claude Code in diesem Repository. |
   | `4` | Öffnet den Output-Ordner für Excel-Arbeitsmappen. |
   | `5` | Erstellt nach dem Setup sofort eine Excel-Arbeitsmappe. |
   | `Q` | Beendet das Menü. |

5. Gib in Claude Code `/setup` ein. Der Befehl beginnt mit einer Dokumentenprüfung und fragt dann alles ab, was er braucht.
6. `start.bat` verwendet standardmässig Deutsch. Für eine dauerhafte Umstellung führe einmal `setx STUDYPLAN_LANG en` aus; neue Fenster übernehmen die Einstellung. Alternativ änderst du die Zeile `set "STUDYPLAN_LANG=de"` in `start.bat`. Nach `/setup` verwendet die CLI die im Studienprofil gespeicherte Sprache.

## Schritt 1: Dokumente sammeln

| Dokument | Woher | Speichern | Ordner |
|---|---|---|---|
| Studienreglement | Öffentliche Website deiner Hochschule | Original-PDF speichern. | `my_study/inbox/regulations/` |
| Curriculum deines Eintrittsjahrs | Öffentliche Website deiner Hochschule | Original-PDF speichern. | `my_study/inbox/regulations/` |
| Modellstundenplan | Öffentliche Website deines Studiengangs, falls vorhanden | Original-PDF speichern. | `my_study/inbox/timetable/` |
| MyCampus „Meine Anmeldungen“ | Selbst anmelden und die Seite öffnen | Semesterfilter entfernen, dann `Strg+S` und „Webseite, vollständig“ wählen. | `my_study/inbox/transcript/` |
| Leistungsübersicht | Selbst aus dem Studienportal herunterladen | Original-PDF speichern. | `my_study/inbox/transcript/` |
| Anerkennungsentscheid | Entscheid deiner Hochschule | Original-PDF speichern. | `my_study/inbox/recognition/` |
| Modulbeschreibungen, einschliesslich Bachelorarbeit | Jede Moduldetailseite selbst öffnen | Alle Bereiche aufklappen, dann mit `Strg+P` als PDF speichern oder `Strg+S` für eine vollständige Webseite verwenden. | `my_study/inbox/modules/` |

- Melde dich selbst in Portalen an. Dateinamen sind unwichtig.
- Teile Claude Code nie ein Passwort mit und speichere keines im Repository.
- Study Planner lädt `my_study/` nicht hoch und Git ignoriert den Ordner. Das Lesen von Dokumenten durch Claude Code ist eine einwilligungsbasierte Funktion von Phase 2; siehe [Datenschutz und Sicherheit](#datenschutz-und-sicherheit).

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

## Schritt 2: Mit Claude Code arbeiten

| Befehl | Funktion | Beispiel, das du eingeben kannst |
|---|---|---|
| `/setup` | Prüft deine Unterlagen und fragt dann nach Studiengang, Eintrittsjahr, Studienform und Startsemester. | `/setup` |
| `/credits` | Importiert die gespeicherte MyCampus-Seite lokal oder erfasst bestandene, nicht bestandene und anerkannte Leistungen. | `/credits` |
| `/check` | Zeigt den aktuellen Stand oder eine Prognose mit Lücken. | `/check` oder `/check Prognose` |
| `/plan` | Erstellt und passt den Plan für die verbleibenden Semester an. | `/plan` |
| `/excel` | Schreibt die Excel-Arbeitsmappe. | `/excel` |
| `/missing` | Listet noch benötigte Modulseiten. Verfügbar ab Phase 2. | `/missing` |
| `/import` | Erstellt nach Einwilligung prüfbare Importentwürfe. Verfügbar ab Phase 2. | `/import` |
| `/update` | Ruft Aktualisierungen zugelassener öffentlicher Quellen ab. Verfügbar ab Phase 3. | `/update` |

Empfohlene Reihenfolge: `/setup`, `/credits`, `/check`, `/plan`, `/check Prognose`, `/excel`. Ergänze `/missing` und `/import`, sobald Phase 2 verfügbar ist.

```text
Du: /setup
Claude Code: Ich habe deine Inbox geprüft: 2 Dokumente gefunden, Studienreglement und Stundenplan fehlen. Welchen Studiengang studierst du?

Du: /credits
Claude Code: Hier ist der Testlauf deines MyCampus-Imports. Soll ich diese Leistungen übernehmen?
```

Die Werte in diesem Beispiel sind erfunden.

## Schritt 3: Deine Excel-Arbeitsmappe

| Tabellenblatt | Zweck |
|---|---|
| Übersicht | Gesamtergebnis, Ziele und wichtige Summen aus dem Regelwerk. |
| Regeln | Jede geprüfte Regel mit aktuellem Wert, Vorgabe, Status und Quelle. |
| Module | Die Module des Curriculums und ihre Kategorien. |
| Meine Leistungen | Bestandene und nicht bestandene Versuche, Anerkennungen und einfache Excel-Summen. |
| Zuteilung | Die Kategorie, die jeder angerechneten Leistung zugeteilt wurde. |
| Lücken | Noch offene Anforderungen. |
| Quellen | Dokument- und Seitenverweise für Regeln. |
| Offene Punkte | Vorläufige und manuelle Punkte zur Prüfung. |
| Studienplan | Geplante Module, Bedingungen, Status und Quelldaten. |
| Semesterübersicht | Semestersummen, kumulierte ECTS, Verstösse und früheste Zulassung zur Bachelorarbeit. |

Im Tabellenblatt Studienplan sind bestandene Zeilen grün, laufende blau, geplante weiss, nicht bestandene rot, Wiederholungen orange und Wahlmodul-Platzhalter gelb. Änderungen in Excel werden nicht zurückgelesen: Korrigiere Leistungen und Plan über Claude Code und die CLI und erstelle danach eine neue Arbeitsmappe.

## So funktionieren die Prüfungen

Die Regeln und ihre Dokument-/Seitenverweise stammen aus dem gewählten Studienreglementsprofil. Das enthaltene HSLU-Profil setzt Folgendes um:

- 180 ECTS für den Abschluss und 132 ECTS plus die manuell geprüfte, studiengangsspezifische Voraussetzung für die Zulassung zur Bachelorarbeit.
- Kategorienminima: 90 ECTS Kern, 39 ECTS Projekt, 15 ECTS Erweiterung und 15 ECTS Zusatz.
- Alle obligatorischen Kern- und Projektmodule bestanden.
- Höchstens drei Versuche mit einem gemeinsamen Budget von 12 ECTS für dritte Versuche; für die Bachelorarbeit gibt es keinen dritten Versuch.
- Advanced-Module erst nach allen obligatorischen Basic-Modulen sowie obligatorische Basic-Module innerhalb von sechs abgeschlossenen Semestern.
- Mindestens 60 ECTS an der HSLU erworben, Anerkennungsobergrenzen für HF-Diplom und anwendbare Berufspraxis sowie höchstens zwölf Semester Studiendauer.

`eligible` bedeutet, dass die automatischen Regeln für dieses Ziel erfüllt sind. `not eligible` bedeutet, dass mindestens eine automatische Voraussetzung offen ist. `provisional` bedeutet, dass ein Ergebnis von ungeprüften Profildaten oder einer vorläufigen Anerkennung abhängt; `manual` markiert eine Anforderung, die du bestätigen musst. Ergebnisse bleiben vorläufig, bis die Profildaten mit den offiziellen Dokumenten verifiziert sind. Für Module, die in mehrere Kategorien passen, verwendet das Regelwerk OR-Tools CP-SAT und wählt pro Modul genau eine möglichst passende Zuteilung.

## Datenschutz und Sicherheit

- Der Planer speichert Daten lokal in `my_study/`; dieser Ordner ist in Git ignoriert.
- In Phase 2 fragt Claude Code vor dem Lesen jedes Dokuments nach deiner Einwilligung. Beim Lesen werden Dokumentinhalte an Anthropic übertragen.
- In Phase 2 werden Leistungsübersichten und Anerkennungsentscheide geschwärzt, bevor Claude Code ihren Text liest.
- `.claude/settings.json` verbietet direkte Lesezugriffe auf die Inbox-Ordner für Leistungsübersichten und Anerkennungen.
- Der Planer verlangt, speichert und verwendet keine Passwörter und meldet sich nie auf einer Website an.
- Der geplante öffentliche Abruf in Phase 3 respektiert robots.txt, Quell-Listen und Einschränkungen manueller Quellen.

## FAQ und Fehlerbehebung

**`uv` wurde nicht gefunden.** Installiere [uv](https://docs.astral.sh/uv/), schliesse und öffne das Terminal erneut und starte dann `start.bat`.

**`claude` wurde nicht gefunden.** Installiere Claude Code gemäss [Dokumentation](https://code.claude.com/docs), melde dich bei deinem Claude-Konto an und starte `start.bat` erneut.

**`start.bat` schliesst sofort.** Starte die Datei im Repository-Ordner aus PowerShell, damit die Meldung sichtbar bleibt: `.\\start.bat`. Prüfe, ob `uv` und `claude` auf `PATH` liegen.

**Der MyCampus-Import meldet `unmapped`.** Der gespeicherte Code stimmt weder genau mit einem Curriculum-Code noch mit einer expliziten Zuordnung überein. Nicht raten: Erfasse den Code erst, wenn eine mit Quelle geprüfte Zuordnung in `profiles/hslu_ta/code_mapping.yaml` ergänzt wurde.

**Mein Ergebnis ist `provisional`.** Lies die aufgeführten Gründe. Häufig sind Profildaten, Code-Zuordnungen oder Anerkennungen noch ungeprüft, oder eine Voraussetzung für die Bachelorarbeit ist manuell zu prüfen.

**Excel zeigt beim Öffnen eine Warnung.** Das sollte nicht passieren. Akzeptiere eine Reparatur nicht stillschweigend, behalte die Originaldatei und melde die Warnung zusammen mit dem ausgeführten Befehl unter [GitHub Issues](https://github.com/AIhdproduction/Study-Planner/issues). Füge keine persönlichen Daten oder Dateien aus `my_study/` bei.

**Wie beginne ich von vorn?** Führe zuerst `uv run studyplan backup` aus. Lösche oder benenne danach die YAML-Dateien in `my_study/` manuell um; `init` überschreibt kein bestehendes Profil.

**Wie aktualisiere ich?** Führe im Repository-Ordner `git pull` aus und doppelklicke danach auf `start.bat`, damit `uv sync` die Umgebung aktualisieren kann.

**Wo melde ich einen Fehler oder schlage einen Studiengang vor?** Eröffne ein Issue unter [GitHub Issues](https://github.com/AIhdproduction/Study-Planner/issues). Füge keine persönlichen Daten oder Dateien aus `my_study/` bei.

## Für Mitwirkende

```text
start.bat                  Windows-Startskript
src/studyplan/             CLI, Regelwerk, Modelle, YAML-I/O, Excel-Export, Übersetzungen
profiles/                  Profile für Hochschulen, Studiengänge und Code-Zuordnungen
schemas/                   Exportierte JSON-Schemas
my_study/                  Lokaler Studierendenstand; von Git ignoriert
.claude/commands/          Ablauf für Studierende in Claude Code
prompts/                   Phasenspezifischer Implementierungsumfang
scripts/                   Maintainer-Hilfen, inklusive Extraktion des Modellstundenplans
tests/fixtures/synthetic/  Versionierte erfundene Testdaten
tests/fixtures/real/       Private, ignorierte Maintainer-Fixtures
```

### CLI-Referenz

| Befehl | Beschreibung |
|---|---|
| `studyplan guide` | Gibt den Studienablauf aus und kann ihn in eine Datei schreiben. |
| `studyplan doctor` | Prüft erforderliche lokale Ordner. |
| `studyplan doctor --inbox` | Zeigt, welche erwarteten Unterlagen in der Inbox liegen, ohne Dateinamen. |
| `studyplan profiles` | Listet verfügbare Hochschulen und Studiengänge. |
| `studyplan modules` | Listet Module des gewählten Studiengangs. |
| `studyplan init` | Erstellt ein Studienprofil und leere Zustandsdateien. |
| `studyplan validate` | Validiert Studiendateien und Profildaten. |
| `studyplan schema` | Exportiert JSON-Schemas. |
| `studyplan check` | Prüft Zulassung zur Bachelorarbeit und Studienabschluss. |
| `studyplan credits` | Verwaltet bestandene, nicht bestandene und anerkannte Leistungen. |
| `studyplan credits list` | Listet gespeicherte Leistungen und Anerkennungen. |
| `studyplan credits add`, `edit`, `remove` | Fügt einen Modulversuch hinzu, ändert oder entfernt ihn. |
| `studyplan credits import-mycampus` | Liest eine gespeicherte MyCampus-Seite lokal; standardmässig nur Testlauf. |
| `studyplan credits recognize` | Verwaltet Anerkennungen aus früheren Ausbildungen. |
| `studyplan credits recognize add`, `list`, `remove` | Fügt Anerkennungen hinzu, listet oder entfernt sie. |
| `studyplan plan` | Prüft den gespeicherten Semesterplan. |
| `studyplan plan generate` | Erstellt einen deterministischen ersten Plan. |
| `studyplan plan add`, `move`, `remove` | Bearbeitet Planpunkte manuell. |
| `studyplan timetable` | Reserviert Stundenplanfunktionen für Phase 4. |
| `studyplan timetable import` | Meldet, dass Stundenplanimport noch nicht verfügbar ist. |
| `studyplan excel` | Exportiert eine nachvollziehbare Excel-Arbeitsmappe. |
| `studyplan backup` | Schreibt eine portable JSON-Sicherung. |
| `studyplan restore` | Stellt eine validierte Sicherung wieder her. |

Verwende diese Entwicklungsbefehle.

```powershell
uv sync
uv run ruff check
uv run ruff format --check
uv run pytest
```

Tests mit `@pytest.mark.real` verwenden private Fixtures und werden sauber übersprungen, wenn sie fehlen. `@pytest.mark.agent` ist in `pyproject.toml` für optionale Tests registriert, die einen KI-Agenten aufrufen; führe sie gezielt mit `uv run pytest -m agent` aus. Aktuell sind keine Agenten-Tests Teil des Standardlaufs.

Zum Ergänzen einer Hochschule oder eines Studiengangs beginne mit `profiles/_template/`. Lege Hochschulregeln in `university.yaml`, das Curriculum in `programs/` und explizite Quellcode-Stämme in `code_mapping.yaml` ab. Zuordnungseinträge nennen ihre Quelle (`mycampus`, `timetable` oder `module_directory`) und verwenden nie eine Zuordnung nur über Titel. Nutze `scripts/extract_model_timetable.py` für den Ablauf zur Extraktion des Modellstundenplans. Befolge `AGENTS.md`, implementiere nur die angeforderte Phase aus `prompts/` und halte `tests/fixtures/real/` privat und von Git ignoriert.

## Lizenz

MIT. Siehe [LICENSE](LICENSE).

Nicht rechtsverbindlich. Es gelten das offizielle Studienreglement und die Entscheide der Studiengangleitung.
